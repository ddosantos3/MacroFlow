from __future__ import annotations

import json
import logging
from typing import Any

import requests

from .config import AppSettings


logger = logging.getLogger("macroflow.llm")


def gerar_explicacao_local(report: dict[str, Any]) -> str:
    signal = report.get("signal", "HOLD")
    status = report.get("status", "SEM_SINAL")
    blocks = report.get("block_reasons") or []
    if blocks:
        block_text = " Bloqueios: " + " | ".join(str(item) for item in blocks)
    else:
        block_text = ""
    return (
        f"{report.get('label', report.get('ativo'))}: regime quant {report.get('regime')}, "
        f"score {report.get('score')}, tendencia {report.get('tendencia')}, "
        f"volume {report.get('volume')} e volatilidade {report.get('volatilidade')}. "
        f"O sinal deterministico atual e {signal} ({status}).{block_text}"
    )


def _extract_response_text(payload: dict[str, Any]) -> str:
    if payload.get("output_text"):
        return str(payload["output_text"]).strip()
    chunks: list[str] = []
    for output in payload.get("output", []) or []:
        for content in output.get("content", []) or []:
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(str(content["text"]))
    return "\n".join(chunks).strip()


def gerar_explicacao_llm(report: dict[str, Any], settings: AppSettings) -> str:
    fallback = gerar_explicacao_local(report)
    if not settings.llm.enabled:
        return fallback
    if settings.llm.provider != "openai":
        logger.warning("Provider LLM nao suportado: %s", settings.llm.provider)
        return fallback
    if not settings.llm.api_key:
        logger.warning("LLM habilitado, mas OPENAI_API_KEY nao foi configurada.")
        return fallback

    prompt = (
        "Voce e uma camada explicativa do MacroFlow. Interprete os dados abaixo para o usuario, "
        "mas nao decida entrada, nao altere sinal, nao recomende trade fora dos campos deterministicos "
        "e nao ignore bloqueios macro/risco. Escreva em portugues do Brasil, direto e operacional.\n\n"
        f"Relatorio deterministico:\n{json.dumps(report, ensure_ascii=False, default=str)}"
    )
    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {settings.llm.api_key}",
                "Content-Type": "application/json",
            },
            json={"model": settings.llm.model, "input": prompt, "store": False},
            timeout=settings.llm.timeout_seconds,
        )
        response.raise_for_status()
        text = _extract_response_text(response.json())
        return text or fallback
    except Exception as exc:
        logger.exception("Falha ao gerar explicacao LLM; usando fallback local: %s", exc)
        return fallback
