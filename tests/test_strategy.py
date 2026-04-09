from pathlib import Path

import pandas as pd

from src.macroflow.config import AppSettings, MarketConfig, StorageConfig
from src.macroflow.domain import MacroContext
from src.macroflow.strategy import analisar_ativo_operacional, construir_macro_context


def _frame_bull_ready() -> pd.DataFrame:
    index = pd.date_range("2026-03-01", periods=4, freq="D")
    return pd.DataFrame(
        {
            "Open": [10.0, 10.1, 10.4, 10.5],
            "High": [10.2, 10.6, 10.9, 10.8],
            "Low": [9.8, 10.0, 10.3, 10.4],
            "Close": [9.9, 10.4, 10.7, 10.75],
            "PMD": [10.0, 10.3, 10.6, 10.6],
            "EMA_FAST": [9.9, 10.2, 10.5, 10.62],
            "EMA_SLOW": [10.0, 10.1, 10.3, 10.55],
            "POSITIVE_CLOSE": [False, True, True, True],
            "NEGATIVE_CLOSE": [True, False, False, False],
            "TOUCH_EMA_SLOW": [False, False, False, True],
            "TREND_SIGN": [-1, 1, 1, 1],
        },
        index=index,
    )


def test_macro_context_blocks_when_data_missing() -> None:
    context = construir_macro_context(
        dxy_value=float("nan"),
        dxy_rsi14=float("nan"),
        dxy_delta=0.0,
        us10y_value=float("nan"),
        us10y_delta=0.0,
        spx_delta=0.0,
        spx_volume_4h=float("nan"),
        spx_volume_media_50=float("nan"),
        score_minimo_operar=65,
        dados_fred_ok=False,
        spx_ok=False,
    )
    assert context.nao_operar is True
    assert "Dados macro incompletos" in context.motivo_nao_operar


def test_strategy_ready_when_macro_and_setup_align() -> None:
    macro_context = MacroContext(
        regime="RISK_OFF",
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
        macro_directions={"USDBRL": "COMPRA", "BRA50": "VENDA"},
        headline="RISK_OFF | score 82 | OPERÁVEL",
    )

    decision = analisar_ativo_operacional(
        asset="USDBRL",
        ticker="BRL=X",
        frame_diario=_frame_bull_ready(),
        preco_atual=5.48,
        variacao_pct=0.6,
        volume_4h=5000.0,
        fixed_levels={"nivel_0": 5.25, "nivel_25": 5.5},
        macro_context=macro_context,
        capital_total_brl=50000.0,
        risco_maximo_por_operacao=0.01,
        stop_buffer_pct=0.005,
    )

    assert decision.execution_status == "PRONTO_PARA_EXECUTAR"
    assert decision.macro_aligned is True
    assert decision.technical_direction == "COMPRA"
    assert decision.entry_price == 10.75
    assert decision.stop_price is not None
    assert decision.position_sizing is not None
    assert decision.position_sizing.quantidade is not None


def test_strategy_blocks_when_macro_direction_conflicts() -> None:
    macro_context = MacroContext(
        regime="RISK_ON",
        score=80,
        nao_operar=False,
        motivo_nao_operar="Macro alinhado para operar.",
        dxy_fred=98.0,
        dxy_rsi14=38.0,
        us10y_fred=4.1,
        us10y_delta_5d=-0.2,
        spx_delta_5x4h=44.0,
        spx_volume_4h=210000.0,
        spx_volume_media_50=180000.0,
        dxy_us10y_divergente=False,
        volume_fraco_proxy=False,
        macro_directions={"USDBRL": "VENDA", "BRA50": "COMPRA"},
        headline="RISK_ON | score 80 | OPERÁVEL",
    )

    decision = analisar_ativo_operacional(
        asset="USDBRL",
        ticker="BRL=X",
        frame_diario=_frame_bull_ready(),
        preco_atual=5.48,
        variacao_pct=0.6,
        volume_4h=5000.0,
        fixed_levels={},
        macro_context=macro_context,
        capital_total_brl=None,
        risco_maximo_por_operacao=0.01,
        stop_buffer_pct=0.005,
    )

    assert decision.execution_status == "BLOQUEADO_MACRO"
    assert decision.macro_aligned is False
    assert "Macro aponta VENDA" in decision.stage_reason
