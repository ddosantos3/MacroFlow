import numpy as np
import pandas as pd

from src.macroflow.config import AppSettings, MarketConfig, QuantConfig
from src.macroflow.domain import MacroContext
from src.macroflow.quant import classify_regime, gerar_relatorio_quant


def _macro_context(direction: str = "COMPRA") -> MacroContext:
    return MacroContext(
        regime="RISK_OFF" if direction == "COMPRA" else "RISK_ON",
        score=82,
        nao_operar=False,
        motivo_nao_operar="Macro alinhado para operar.",
        dxy_fred=105.0,
        dxy_rsi14=62.0,
        us10y_fred=4.55,
        us10y_delta_5d=0.18,
        spx_delta_5x4h=-35.0,
        spx_volume_4h=120000.0,
        spx_volume_media_50=150000.0,
        dxy_us10y_divergente=False,
        volume_fraco_proxy=False,
        macro_directions={"USDBRL": direction, "BRA50": "VENDA" if direction == "COMPRA" else "COMPRA"},
        headline="macro ok",
    )


def _trend_frame(direction: str = "up") -> pd.DataFrame:
    index = pd.date_range("2026-03-01 09:00", periods=140, freq="h")
    close = np.linspace(100.0, 135.0, len(index)) if direction == "up" else np.linspace(135.0, 100.0, len(index))
    volume = np.full(len(index), 1000.0)
    volume[-1] = 5000.0
    return pd.DataFrame(
        {
            "Open": close - 0.15 if direction == "up" else close + 0.15,
            "High": close + 0.60,
            "Low": close - 0.60,
            "Close": close,
            "Volume": volume,
        },
        index=index,
    )


def test_quant_report_generates_buy_with_risk_payload() -> None:
    settings = AppSettings(
        market=MarketConfig(capital_total_brl=100000.0),
        quant=QuantConfig(volume_spike_factor=2.0),
    )

    report = gerar_relatorio_quant(
        asset="USDBRL",
        ticker="BRL=X",
        frame=_trend_frame("up"),
        macro_context=_macro_context("COMPRA"),
        settings=settings,
    )

    assert report["signal"] == "BUY"
    assert report["status"] == "SINAL_BUY"
    assert report["regime"] == "trend_clean"
    assert report["entrada"] is not None
    assert report["stop"] < report["entrada"] < report["alvo"]
    assert round(report["risk_reward"], 2) == 1.5
    assert report["position_size"] is not None
    assert report["score"] > 60


def test_quant_report_generates_sell_when_conditions_are_inverted() -> None:
    settings = AppSettings(
        market=MarketConfig(capital_total_brl=100000.0),
        quant=QuantConfig(volume_spike_factor=2.0),
    )

    report = gerar_relatorio_quant(
        asset="USDBRL",
        ticker="BRL=X",
        frame=_trend_frame("down"),
        macro_context=_macro_context("VENDA"),
        settings=settings,
    )

    assert report["signal"] == "SELL"
    assert report["status"] == "SINAL_SELL"
    assert report["regime"] == "trend_clean"
    assert report["alvo"] < report["entrada"] < report["stop"]
    assert round(report["risk_reward"], 2) == 1.5


def test_quant_blocks_when_macro_is_blocked() -> None:
    context = _macro_context("COMPRA")
    context.nao_operar = True
    context.motivo_nao_operar = "Score abaixo do minimo."

    report = gerar_relatorio_quant(
        asset="USDBRL",
        ticker="BRL=X",
        frame=_trend_frame("up"),
        macro_context=context,
        settings=AppSettings(quant=QuantConfig(volume_spike_factor=2.0)),
    )

    assert report["raw_signal"] == "BUY"
    assert report["signal"] == "HOLD"
    assert report["status"] == "BLOQUEADO_QUANT"
    assert any("Macro bloqueado" in reason for reason in report["block_reasons"])


def test_classify_regime_uses_chaotic_before_range_when_atr_is_high() -> None:
    assert classify_regime({"ADX": 12, "EMA_21": 100, "EMA_80": 100, "ATR_HIGH": True}) == "chaotic"
    assert classify_regime({"ADX": 12, "EMA_21": 100, "EMA_80": 100, "ATR_HIGH": False}) == "range"
