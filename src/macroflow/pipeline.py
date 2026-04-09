import logging
from typing import Any

import pandas as pd

from .config import ATIVOS_YAHOO, PASSOS_NIVEIS_FIXOS, AppSettings, load_settings
from .domain import DashboardState, SourceHealth
from .indicators import (
    calcular_niveis_fixos,
    calcular_rsi,
    calcular_variacao,
    preparar_frame_diario,
    resample_para_4h,
    ultimo_valor,
)
from .providers import baixar_fred_series, baixar_yahoo, data_mais_recente, timestamp_local
from .storage import ArtifactStore
from .strategy import (
    analisar_ativo_operacional,
    construir_macro_context,
    montar_relatorio_terminal,
    snapshot_from_state,
)


logger = logging.getLogger("macroflow.pipeline")


def _configure_logging() -> None:
    if logging.getLogger().handlers:
        return
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def executar_coleta(settings: AppSettings | None = None) -> dict[str, Any]:
    _configure_logging()
    settings = settings or load_settings()
    store = ArtifactStore(
        excel_path=settings.storage.excel_path,
        dashboard_state_path=settings.storage.dashboard_state_path,
        snapshot_history_path=settings.storage.snapshot_history_path,
    )

    generated_at = timestamp_local()
    intraday_frames: dict[str, pd.DataFrame] = {}
    daily_frames: dict[str, pd.DataFrame] = {}
    source_health: list[SourceHealth] = []

    dxy_series = baixar_fred_series(settings.market.fred_api_key, settings.market.fred_serie_dxy)
    us10y_series = baixar_fred_series(settings.market.fred_api_key, settings.market.fred_serie_us10y)
    dados_fred_ok = not dxy_series.empty and not us10y_series.empty
    source_health.append(
        SourceHealth(
            source="FRED",
            ok=dados_fred_ok,
            message="DXY e US10Y carregados com sucesso." if dados_fred_ok else "FRED indisponível ou sem API key.",
            last_updated=data_mais_recente(dxy_series if not dxy_series.empty else us10y_series),
        )
    )

    dxy_rsi = float(calcular_rsi(dxy_series, settings.market.rsi_period).iloc[-1]) if not dxy_series.empty else float("nan")
    dxy_delta = (
        float(dxy_series.iloc[-1] - dxy_series.iloc[-settings.market.macro_delta_bars])
        if len(dxy_series) > settings.market.macro_delta_bars
        else 0.0
    )
    us10y_delta = (
        float(us10y_series.iloc[-1] - us10y_series.iloc[-settings.market.macro_delta_bars])
        if len(us10y_series) > settings.market.macro_delta_bars
        else 0.0
    )
    dxy_value = ultimo_valor(dxy_series)
    us10y_value = ultimo_valor(us10y_series)

    for nome, ticker in ATIVOS_YAHOO.items():
        intraday = baixar_yahoo(ticker, settings.market.yahoo_intraday_period, settings.market.yahoo_intraday_interval)
        diario = baixar_yahoo(ticker, settings.market.yahoo_daily_period, settings.market.yahoo_daily_interval)
        intraday_4h = resample_para_4h(intraday)
        intraday_frames[nome] = intraday_4h
        daily_frame = preparar_frame_diario(
            diario,
            ema_fast=settings.market.strategy_ema_fast,
            ema_slow=settings.market.strategy_ema_slow,
            touch_tolerance_pct=settings.market.touch_tolerance_pct,
        )
        daily_frames[nome] = daily_frame

        ok = not intraday_4h.empty and not daily_frame.empty
        message = "Yahoo intraday + diário OK." if ok else "Yahoo sem dados suficientes para intraday ou diário."
        source_health.append(
            SourceHealth(
                source=f"Yahoo:{nome}",
                ok=ok,
                message=message,
                last_updated=data_mais_recente(daily_frame if not daily_frame.empty else intraday_4h),
            )
        )

    spx_4h = intraday_frames.get("SPX", pd.DataFrame())
    spx_ok = not spx_4h.empty and "Close" in spx_4h.columns
    spx_close = spx_4h["Close"].dropna() if spx_ok else pd.Series(dtype=float)
    spx_delta = (
        float(spx_close.iloc[-1] - spx_close.iloc[-settings.market.macro_delta_bars])
        if len(spx_close) > settings.market.macro_delta_bars
        else 0.0
    )
    spx_volume_4h = float(spx_4h["Volume"].iloc[-1]) if spx_ok and "Volume" in spx_4h.columns else float("nan")
    spx_volume_media_50 = (
        float(spx_4h["Volume"].tail(settings.market.volume_lookback).mean())
        if spx_ok and "Volume" in spx_4h.columns
        else float("nan")
    )

    macro_context = construir_macro_context(
        dxy_value=dxy_value,
        dxy_rsi14=dxy_rsi,
        dxy_delta=dxy_delta,
        us10y_value=us10y_value,
        us10y_delta=us10y_delta,
        spx_delta=spx_delta,
        spx_volume_4h=spx_volume_4h,
        spx_volume_media_50=spx_volume_media_50,
        score_minimo_operar=settings.market.score_minimo_operar,
        dados_fred_ok=dados_fred_ok,
        spx_ok=spx_ok,
    )

    decisions = []
    for asset in ("USDBRL", "BRA50"):
        intraday_4h = intraday_frames.get(asset, pd.DataFrame())
        preco_atual, _, variacao_pct, volume_4h = calcular_variacao(intraday_4h)
        step, casas = PASSOS_NIVEIS_FIXOS.get(asset, (1.0, 2))
        fixed_levels = calcular_niveis_fixos(preco_atual, step, casas)
        decisions.append(
            analisar_ativo_operacional(
                asset=asset,
                ticker=ATIVOS_YAHOO[asset],
                frame_diario=daily_frames.get(asset, pd.DataFrame()),
                preco_atual=preco_atual,
                variacao_pct=variacao_pct,
                volume_4h=volume_4h,
                fixed_levels=fixed_levels,
                macro_context=macro_context,
                capital_total_brl=settings.market.capital_total_brl,
                risco_maximo_por_operacao=settings.market.risco_maximo_por_operacao,
                stop_buffer_pct=settings.market.stop_buffer_pct,
            )
        )

    terminal_report = montar_relatorio_terminal(macro_context, decisions)
    dashboard_state = DashboardState(
        generated_at=generated_at,
        macro_context=macro_context,
        asset_decisions=decisions,
        source_health=source_health,
        terminal_report=terminal_report,
        summary={
            "headline": macro_context.headline,
            "has_actionable_trade": any(
                decision.execution_status in {"PRONTO_PARA_EXECUTAR", "EM_ACOMPANHAMENTO"} and decision.macro_aligned
                for decision in decisions
            ),
            "blocked": macro_context.nao_operar,
            "excel_path": str(settings.storage.excel_path),
        },
    )

    snapshot = snapshot_from_state(macro_context, decisions, generated_at)
    store.save_excel_artifacts(snapshot, intraday_frames, daily_frames)
    store.append_snapshot_history(snapshot)
    store.save_dashboard_state(dashboard_state)

    logger.info("Estado do dashboard atualizado em %s", settings.storage.dashboard_state_path)
    logger.info("Excel atualizado em %s", settings.storage.excel_path)
    return {
        "dashboard_state": dashboard_state,
        "snapshot": snapshot,
        "terminal_report": terminal_report,
    }


def gerar_recomendacao(settings: AppSettings | None = None) -> str:
    settings = settings or load_settings()
    store = ArtifactStore(
        excel_path=settings.storage.excel_path,
        dashboard_state_path=settings.storage.dashboard_state_path,
        snapshot_history_path=settings.storage.snapshot_history_path,
    )
    state = store.load_dashboard_state()
    if not state:
        raise RuntimeError("Nenhum estado local encontrado. Execute a coleta antes de pedir a recomendação.")
    return str(state.get("terminal_report", "Sem relatório disponível."))


def pipeline_completo(settings: AppSettings | None = None) -> str:
    result = executar_coleta(settings=settings)
    return str(result["terminal_report"])
