from __future__ import annotations

import json
import logging
from typing import Any

import requests

from .config import AppSettings


logger = logging.getLogger("macroflow.jarvis")


DEFAULT_JARVIS_PROMPT = (
    "Voce e o Jarvis - Trader Quantitativo do MacroFlow. Analise somente os dados fornecidos, "
    "priorize gestao de risco e deixe claro quando a resposta exigir nova coleta."
)


def load_jarvis_prompt(settings: AppSettings) -> str:
    prompt_path = settings.jarvis.prompt_path
    if not prompt_path.exists():
        logger.warning("Prompt do Jarvis nao encontrado em %s; usando fallback.", prompt_path)
        return DEFAULT_JARVIS_PROMPT
    return prompt_path.read_text(encoding="utf-8").strip() or DEFAULT_JARVIS_PROMPT


def build_jarvis_context(state: dict[str, Any], settings: AppSettings) -> dict[str, Any]:
    news_center = state.get("news_center") or {}
    events = news_center.get("events") or []
    quant_reports = state.get("quant_reports") or []
    return {
        "generated_at": state.get("generated_at"),
        "macro_context": state.get("macro_context") or {},
        "asset_decisions": state.get("asset_decisions") or [],
        "quant_reports": quant_reports[: settings.jarvis.max_context_assets],
        "news_center": {
            "status": news_center.get("status"),
            "risk_bias": news_center.get("risk_bias"),
            "high_impact_count": news_center.get("high_impact_count"),
            "events": events[: settings.jarvis.max_context_events],
            "agent_context_note": news_center.get("agent_context_note"),
        },
        "guardrails": [
            "Nao inventar dados ausentes.",
            "Nao transformar noticia isolada em ordem operacional.",
            "Sinal, stop, alvo e sizing deterministico prevalecem sobre opiniao textual.",
            "Quando houver conflito ou baixa qualidade de setup, responder NAO OPERAR.",
        ],
    }


def _extract_response_text(payload: dict[str, Any]) -> str:
    if payload.get("output_text"):
        return str(payload["output_text"]).strip()
    chunks: list[str] = []
    for output in payload.get("output", []) or []:
        for content in output.get("content", []) or []:
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(str(content["text"]))
    return "\n".join(chunks).strip()


def _fallback_response(message: str, context: dict[str, Any]) -> str:
    macro = context.get("macro_context") or {}
    quant_reports = context.get("quant_reports") or []
    news_center = context.get("news_center") or {}
    actionable = [report for report in quant_reports if report.get("signal") in {"BUY", "SELL"}]
    blocked = [report for report in quant_reports if report.get("status") == "BLOQUEADO_QUANT"]
    top_events = news_center.get("events") or []
    high_impact = [event for event in top_events if int(event.get("importance") or 0) == 3]

    if actionable:
        signal_text = "; ".join(
            f"{item.get('label', item.get('ativo'))}: {item.get('signal')} score {item.get('score')}"
            for item in actionable[:3]
        )
    else:
        signal_text = "sem sinal deterministico liberado no snapshot atual"

    if high_impact:
        event_text = "; ".join(
            f"{event.get('country')} - {event.get('event')} ({event.get('importance_label')}, vies {event.get('market_bias')})"
            for event in high_impact[:3]
        )
    else:
        event_text = "sem evento de 3 touros no contexto carregado"

    blocked_text = f"{len(blocked)} ativos bloqueados pela camada quant/macro." if blocked else "Nao ha bloqueio quant relevante no recorte carregado."
    return (
        "Jarvis em modo local: ainda sem LLM habilitado, entao vou me limitar ao estado coletado.\n\n"
        f"Pergunta recebida: {message}\n\n"
        f"Macro: {macro.get('regime', 'N/A')} | score {macro.get('score', 'N/A')} | "
        f"{'NAO OPERAR' if macro.get('nao_operar') else 'OPERAVEL'}.\n"
        f"Sinais: {signal_text}.\n"
        f"Calendario: vies agregado {news_center.get('risk_bias', 'neutro')}; {event_text}.\n"
        f"Risco: {blocked_text}\n\n"
        "Leitura: enquanto houver bloqueio macro, conflito de sinal ou ausencia de confluencia estatistica, o plano conservador e NAO OPERAR. "
        "Se quiser um relatorio completo por ativo, pergunte por exemplo: 'analise USDBRL' ou 'compare WDO e indice'."
    )


def generate_jarvis_reply(
    message: str,
    history: list[dict[str, str]] | None,
    dashboard_state: dict[str, Any],
    settings: AppSettings,
) -> dict[str, Any]:
    clean_message = message.strip()[:4000]
    if not clean_message:
        return {"reply": "Envie uma pergunta objetiva para o Jarvis analisar o snapshot atual.", "mode": "validation"}

    prompt = load_jarvis_prompt(settings)
    context = build_jarvis_context(dashboard_state, settings)
    safe_history = (history or [])[-settings.jarvis.max_history_messages :]
    if not settings.llm.enabled or not settings.llm.api_key or settings.llm.provider != "openai":
        return {
            "reply": _fallback_response(clean_message, context),
            "mode": "local",
            "context_generated_at": context.get("generated_at"),
        }

    llm_input = {
        "prompt": prompt,
        "context": context,
        "history": safe_history,
        "user_message": clean_message,
    }
    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {settings.llm.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.llm.model,
                "input": json.dumps(llm_input, ensure_ascii=False, default=str),
                "store": False,
            },
            timeout=settings.llm.timeout_seconds,
        )
        response.raise_for_status()
        reply = _extract_response_text(response.json())
        if not reply:
            reply = _fallback_response(clean_message, context)
        return {
            "reply": reply,
            "mode": "llm",
            "context_generated_at": context.get("generated_at"),
        }
    except Exception as exc:
        logger.exception("Falha no chat Jarvis; usando fallback local: %s", exc)
        return {
            "reply": _fallback_response(clean_message, context),
            "mode": "local_fallback",
            "context_generated_at": context.get("generated_at"),
        }
