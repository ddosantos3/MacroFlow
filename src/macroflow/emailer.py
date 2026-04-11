from __future__ import annotations

import json
import logging
import smtplib
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from .config import AppSettings, EmailConfig


logger = logging.getLogger("macroflow.emailer")


def _format_value(value: Any, digits: int = 4) -> str:
    try:
        if value is None:
            return "-"
        number = float(value)
    except (TypeError, ValueError):
        return str(value) if value not in {None, ""} else "-"
    return f"{number:.{digits}f}".rstrip("0").rstrip(".")


def build_email_body(reports: list[dict[str, Any]], generated_at: str) -> str:
    lines = [
        "MacroFlow - Relatorio de Mercado",
        f"Data: {generated_at}",
        "",
    ]
    for report in reports:
        lines.extend(
            [
                f"Ativo: {report.get('label', report.get('ativo'))} ({report.get('ativo')})",
                f"Regime: {report.get('regime')} | Score: {report.get('score')} | Confianca: {report.get('confianca')}",
                f"Sinal deterministico: {report.get('signal')} | Status: {report.get('status')}",
                f"Entrada sugerida: {_format_value(report.get('entrada'))}",
                f"Stop: {_format_value(report.get('stop'))}",
                f"Alvo: {_format_value(report.get('alvo'))}",
                f"Risk/reward: {_format_value(report.get('risk_reward'), 2)}",
                "Indicadores:",
                f"- VWAP: {_format_value(report.get('vwap'))}",
                f"- POC: {_format_value(report.get('poc'))}",
                f"- ADX: {_format_value(report.get('adx'), 2)}",
                f"- ATR: {_format_value(report.get('atr'))}",
                f"- Volume: {report.get('volume')}",
                f"- Volatilidade: {report.get('volatilidade')}",
                f"Analise: {report.get('explanation') or 'Sem explicacao disponivel.'}",
                "",
            ]
        )
    lines.append("Observacao: o LLM apenas explica. Sinal, stop, alvo e sizing sao calculados de forma deterministica.")
    return "\n".join(lines)


def send_email_report(config: EmailConfig, subject: str, body: str) -> bool:
    if not config.enabled:
        return False
    missing = [name for name, value in {"EMAIL_HOST": config.host, "EMAIL_USER": config.user, "EMAIL_PASSWORD": config.password, "EMAIL_TO": config.to}.items() if not value]
    if missing:
        logger.warning("E-mail habilitado, mas configuracao incompleta: %s", ", ".join(missing))
        return False

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = config.user
    msg["To"] = config.to

    try:
        with smtplib.SMTP(config.host, config.port, timeout=20) as server:
            if config.use_tls:
                server.starttls()
            server.login(config.user, config.password)
            server.send_message(msg)
        logger.info("Relatorio MacroFlow enviado por e-mail para %s", config.to)
        return True
    except Exception as exc:
        logger.exception("Erro no envio de e-mail MacroFlow: %s", exc)
        return False


def load_alert_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Estado de alertas corrompido em %s; reiniciando.", path)
        return {}


def save_alert_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _signal_signature(report: dict[str, Any]) -> str:
    entry = _format_value(report.get("entrada"), 6)
    score = report.get("score", "-")
    return f"{report.get('ativo')}:{report.get('signal')}:{entry}:{score}"


def should_send_email(
    reports: list[dict[str, Any]],
    generated_at: str,
    state: dict[str, Any],
    send_mode: str = "signal_or_daily",
) -> tuple[bool, list[str]]:
    mode = (send_mode or "signal_or_daily").lower()
    today = generated_at[:10]
    reasons: list[str] = []

    if mode in {"daily", "signal_or_daily"} and state.get("last_daily_date") != today:
        reasons.append("daily")

    if mode in {"signal", "signal_or_daily"}:
        signatures = state.get("last_signal_signatures", {})
        for report in reports:
            if report.get("signal") not in {"BUY", "SELL"}:
                continue
            asset = str(report.get("ativo"))
            signature = _signal_signature(report)
            if signatures.get(asset) != signature:
                reasons.append("new_signal")
                break

    return bool(reasons), reasons


def update_alert_state_after_send(
    reports: list[dict[str, Any]],
    generated_at: str,
    state: dict[str, Any],
    reasons: list[str],
) -> dict[str, Any]:
    state = dict(state)
    state["last_sent_at"] = generated_at
    if "daily" in reasons:
        state["last_daily_date"] = generated_at[:10]
    signatures = dict(state.get("last_signal_signatures", {}))
    for report in reports:
        if report.get("signal") in {"BUY", "SELL"}:
            signatures[str(report.get("ativo"))] = _signal_signature(report)
    state["last_signal_signatures"] = signatures
    return state


def processar_alertas_email(
    reports: list[dict[str, Any]],
    generated_at: str,
    settings: AppSettings,
) -> dict[str, Any]:
    if not settings.email.enabled:
        return {"enabled": False, "sent": False, "reasons": []}

    state_path = settings.storage.runtime_dir / "email_alert_state.json"
    alert_state = load_alert_state(state_path)
    should_send, reasons = should_send_email(reports, generated_at, alert_state, settings.email.send_mode)
    if not should_send:
        logger.info("E-mail MacroFlow nao enviado; nenhum gatilho ativo.")
        return {"enabled": True, "sent": False, "reasons": []}

    subject = f"[MacroFlow] Relatorio de Mercado - {generated_at[:10]}"
    body = build_email_body(reports, generated_at)
    sent = send_email_report(settings.email, subject, body)
    if sent:
        new_state = update_alert_state_after_send(reports, generated_at, alert_state, reasons)
        save_alert_state(state_path, new_state)
    return {"enabled": True, "sent": sent, "reasons": reasons}
