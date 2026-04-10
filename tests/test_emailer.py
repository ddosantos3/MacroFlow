from src.macroflow.config import EmailConfig
from src.macroflow.emailer import (
    build_email_body,
    send_email_report,
    should_send_email,
    update_alert_state_after_send,
)


def _report(signal: str = "BUY") -> dict[str, object]:
    return {
        "ativo": "USDBRL",
        "label": "Mini Dolar",
        "signal": signal,
        "status": f"SINAL_{signal}" if signal != "HOLD" else "SEM_SINAL",
        "entrada": 5.12,
        "stop": 5.08,
        "alvo": 5.20,
        "score": 78,
        "regime": "trend_clean",
        "confianca": "moderada",
        "vwap": 5.10,
        "poc": 5.08,
        "adx": 28.0,
        "atr": 0.02,
        "volume": "acima da media",
        "volatilidade": "controlada",
        "risk_reward": 1.5,
        "explanation": "Leitura deterministica favoravel.",
    }


def test_should_send_email_on_daily_or_new_signal() -> None:
    reports = [_report("BUY")]
    state: dict[str, object] = {}

    should_send, reasons = should_send_email(reports, "2026-04-10 09:00:00", state)
    assert should_send is True
    assert "daily" in reasons
    assert "new_signal" in reasons

    state = update_alert_state_after_send(reports, "2026-04-10 09:00:00", state, reasons)
    should_send_again, reasons_again = should_send_email(reports, "2026-04-10 10:00:00", state)
    assert should_send_again is False
    assert reasons_again == []


def test_build_email_body_contains_quant_summary() -> None:
    body = build_email_body([_report("BUY")], "2026-04-10 09:00:00")

    assert "MacroFlow - Relatorio de Mercado" in body
    assert "Mini Dolar" in body
    assert "Sinal deterministico: BUY" in body
    assert "VWAP" in body
    assert "o LLM apenas explica" in body


def test_send_email_report_uses_smtp_without_real_network(monkeypatch) -> None:
    calls: list[str] = []

    class FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            calls.append(f"connect:{host}:{port}:{timeout}")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            calls.append("close")

        def starttls(self) -> None:
            calls.append("tls")

        def login(self, user: str, password: str) -> None:
            calls.append(f"login:{user}:{bool(password)}")

        def send_message(self, msg) -> None:
            calls.append(f"send:{msg['To']}")

    monkeypatch.setattr("src.macroflow.emailer.smtplib.SMTP", FakeSMTP)

    sent = send_email_report(
        EmailConfig(
            enabled=True,
            host="smtp.example.com",
            port=587,
            user="sender@example.com",
            password="secret-token",
            to="dest@example.com",
        ),
        "[MacroFlow] Relatorio",
        "body",
    )

    assert sent is True
    assert calls == [
        "connect:smtp.example.com:587:20",
        "tls",
        "login:sender@example.com:True",
        "send:dest@example.com",
        "close",
    ]
