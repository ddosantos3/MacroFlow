from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from .config import AppSettings, ASSET_LABELS
from .domain import MacroContext
from .indicators import (
    calcular_adx,
    calcular_atr,
    calcular_bollinger_bands,
    calcular_obv,
    calcular_poc,
    calcular_volume_media,
    calcular_vwap_intraday,
    calcular_vwap_rolling,
    detectar_squeeze,
    detectar_volume_spike,
    normalizar_ohlc,
    preco_tipico,
)


def _num(value: Any, default: float = float("nan")) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _finite(value: Any) -> bool:
    return math.isfinite(_num(value))


def _clip(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def enriquecer_frame_quant(frame: pd.DataFrame, settings: AppSettings) -> pd.DataFrame:
    enriched = normalizar_ohlc(frame)
    if enriched.empty:
        return enriched

    enriched = enriched.copy()
    quant = settings.quant
    if "Volume" not in enriched.columns:
        enriched["Volume"] = np.nan

    enriched["TYPICAL_PRICE"] = preco_tipico(enriched)
    enriched["VWAP"] = calcular_vwap_intraday(enriched)
    enriched["VWAP_ROLLING"] = calcular_vwap_rolling(enriched, quant.vwap_rolling_window)

    poc_payload = calcular_poc(enriched, bins=quant.poc_bins, value_area_pct=quant.value_area_pct)
    enriched["POC"] = poc_payload["poc"]
    enriched["VAH"] = poc_payload["vah"]
    enriched["VAL"] = poc_payload["val"]

    enriched["ATR"] = calcular_atr(enriched, quant.atr_period)
    bands = calcular_bollinger_bands(enriched["Close"], quant.bb_period, quant.bb_std)
    enriched = enriched.join(bands)
    enriched["SQUEEZE"] = detectar_squeeze(enriched["BB_BANDWIDTH"], quant.squeeze_window)
    enriched["OBV"] = calcular_obv(enriched)
    enriched["VOLUME_AVG"] = calcular_volume_media(enriched, quant.volume_average_window)
    enriched["VOLUME_SPIKE"] = detectar_volume_spike(
        enriched["Volume"],
        enriched["VOLUME_AVG"],
        quant.volume_spike_factor,
    )

    enriched["EMA_8"] = enriched["Close"].ewm(span=quant.ema_fast, adjust=False).mean()
    enriched["EMA_21"] = enriched["Close"].ewm(span=quant.ema_mid, adjust=False).mean()
    enriched["EMA_80"] = enriched["Close"].ewm(span=quant.ema_slow, adjust=False).mean()
    enriched["EMA_200"] = enriched["Close"].ewm(span=quant.ema_long, adjust=False).mean()
    enriched["ADX"] = calcular_adx(enriched, quant.adx_period)

    atr_reference = enriched["ATR"].dropna().tail(max(quant.atr_high_quantile_window, 1))
    if len(atr_reference) >= max(quant.atr_period, 5):
        threshold = float(atr_reference.quantile(_clip(quant.atr_high_quantile, 0.0, 1.0)))
        enriched["ATR_HIGH"] = enriched["ATR"] >= threshold
    else:
        enriched["ATR_HIGH"] = False
    return enriched


def classify_regime(data: pd.Series | dict[str, Any]) -> str:
    adx = _num(data.get("ADX"))
    ema_21 = _num(data.get("EMA_21"))
    ema_80 = _num(data.get("EMA_80"))
    atr_high = bool(data.get("ATR_HIGH", False))

    if adx > 25 and ema_21 > ema_80:
        return "trend_clean"
    if adx > 25 and ema_21 < ema_80:
        return "trend_clean"
    if atr_high:
        return "chaotic"
    if adx < 20:
        return "range"
    return "transition"


def _trend_label(row: pd.Series | dict[str, Any]) -> str:
    ema_21 = _num(row.get("EMA_21"))
    ema_80 = _num(row.get("EMA_80"))
    if ema_21 > ema_80:
        return "alta"
    if ema_21 < ema_80:
        return "baixa"
    return "lateral"


def _component_scores(row: pd.Series | dict[str, Any], macro_context: MacroContext) -> dict[str, float]:
    price = _num(row.get("Close"))
    vwap = _num(row.get("VWAP"))
    poc = _num(row.get("POC"))
    volume = _num(row.get("Volume"))
    volume_avg = _num(row.get("VOLUME_AVG"))
    adx = _num(row.get("ADX"))
    ema_21 = _num(row.get("EMA_21"))
    ema_80 = _num(row.get("EMA_80"))
    squeeze = bool(row.get("SQUEEZE", False))
    atr_high = bool(row.get("ATR_HIGH", False))
    volume_spike = bool(row.get("VOLUME_SPIKE", False))

    trend_score = 20.0 if adx > 25 and ema_21 != ema_80 else 10.0 if adx >= 20 else 4.0
    volume_score = 20.0 if volume_spike else 12.0 if _finite(volume) and _finite(volume_avg) and volume > volume_avg else 5.0
    volatility_score = 0.0 if atr_high else 8.0 if squeeze else 20.0
    macro_score = _clip(float(getattr(macro_context, "score", 0)), 0.0, 100.0) * 0.20

    trend = _trend_label(row)
    if trend == "alta":
        position_vs_vwap = 10.0 if _finite(price) and _finite(vwap) and price > vwap else 0.0
        position_vs_poc = 10.0 if _finite(price) and _finite(poc) and price > poc else 0.0
    elif trend == "baixa":
        position_vs_vwap = 10.0 if _finite(price) and _finite(vwap) and price < vwap else 0.0
        position_vs_poc = 10.0 if _finite(price) and _finite(poc) and price < poc else 0.0
    else:
        position_vs_vwap = 5.0 if _finite(price) and _finite(vwap) else 0.0
        position_vs_poc = 5.0 if _finite(price) and _finite(poc) else 0.0

    return {
        "trend_score": trend_score,
        "volume_score": volume_score,
        "volatility_score": volatility_score,
        "macro_score": macro_score,
        "position_vs_vwap": position_vs_vwap,
        "position_vs_poc": position_vs_poc,
    }


def calcular_score_quantitativo(row: pd.Series | dict[str, Any], macro_context: MacroContext) -> tuple[int, dict[str, float]]:
    components = _component_scores(row, macro_context)
    score = int(round(_clip(sum(components.values()), 0.0, 100.0)))
    return score, components


def _raw_signal(row: pd.Series | dict[str, Any]) -> str:
    price = _num(row.get("Close"))
    vwap = _num(row.get("VWAP"))
    poc = _num(row.get("POC"))
    ema_21 = _num(row.get("EMA_21"))
    ema_80 = _num(row.get("EMA_80"))
    adx = _num(row.get("ADX"))
    volume_spike = bool(row.get("VOLUME_SPIKE", False))

    if price > vwap and price > poc and ema_21 > ema_80 and adx > 25 and volume_spike:
        return "BUY"
    if price < vwap and price < poc and ema_21 < ema_80 and adx > 25 and volume_spike:
        return "SELL"
    return "HOLD"


def _macro_direction_conflict(asset: str, signal: str, macro_context: MacroContext) -> str | None:
    if signal == "HOLD":
        return None
    macro_direction = macro_context.macro_directions.get(asset)
    if not macro_direction:
        return None
    if macro_direction == "NEUTRO":
        return f"Direcao macro neutra para {asset}."
    if signal == "BUY" and macro_direction != "COMPRA":
        return f"Direcao macro {macro_direction} conflita com BUY."
    if signal == "SELL" and macro_direction != "VENDA":
        return f"Direcao macro {macro_direction} conflita com SELL."
    return None


def _apply_trade_blocks(asset: str, signal: str, regime: str, row: pd.Series, macro_context: MacroContext) -> list[str]:
    blocks: list[str] = []
    if regime == "chaotic":
        blocks.append("Regime chaotic bloqueia trade por volatilidade.")
    if macro_context.nao_operar:
        blocks.append(f"Macro bloqueado: {macro_context.motivo_nao_operar}")
    conflict = _macro_direction_conflict(asset, signal, macro_context)
    if conflict:
        blocks.append(conflict)
    if signal != "HOLD" and not _finite(row.get("ATR")):
        blocks.append("ATR indisponivel para calcular stop, alvo e sizing.")
    return blocks


def _risk_payload(signal: str, entry: float, atr: float, settings: AppSettings) -> dict[str, Any]:
    risk_percent = _clip(float(settings.quant.risk_percent), 0.0, min(float(settings.quant.max_risk_percent), 0.02))
    if signal not in {"BUY", "SELL"} or not _finite(entry) or not _finite(atr) or atr <= 0:
        return {
            "entrada": None,
            "stop": None,
            "alvo": None,
            "position_size": None,
            "risk_reward": None,
            "risk_percent": risk_percent,
        }

    stop_distance = settings.quant.stop_atr_multiple * atr
    target_distance = settings.quant.target_atr_multiple * atr
    if signal == "BUY":
        stop = entry - stop_distance
        target = entry + target_distance
    else:
        stop = entry + stop_distance
        target = entry - target_distance

    capital = settings.market.capital_total_brl
    position_size = (capital * risk_percent / atr) if capital is not None and atr > 0 else None
    return {
        "entrada": entry,
        "stop": stop,
        "alvo": target,
        "position_size": position_size,
        "risk_reward": abs(target - entry) / abs(entry - stop) if entry != stop else None,
        "risk_percent": risk_percent,
    }


def gerar_relatorio_quant(
    asset: str,
    ticker: str,
    frame: pd.DataFrame,
    macro_context: MacroContext,
    settings: AppSettings,
) -> dict[str, Any]:
    label = ASSET_LABELS.get(asset, asset)
    enriched = enriquecer_frame_quant(frame, settings)
    if enriched.empty:
        return {
            "ativo": asset,
            "label": label,
            "ticker": ticker,
            "regime": "sem_dados",
            "score": 0,
            "tendencia": "indefinida",
            "vwap": None,
            "poc": None,
            "entrada": None,
            "stop": None,
            "alvo": None,
            "volume": "sem dados",
            "volatilidade": "sem dados",
            "risk_reward": None,
            "confianca": "baixa",
            "signal": "HOLD",
            "status": "SEM_DADOS",
            "block_reasons": ["Sem candles suficientes para analise quant."],
            "explanation": "",
        }

    latest = enriched.iloc[-1]
    regime = classify_regime(latest)
    score, components = calcular_score_quantitativo(latest, macro_context)
    candidate_signal = _raw_signal(latest)
    blocks = _apply_trade_blocks(asset, candidate_signal, regime, latest, macro_context)
    signal = "HOLD" if blocks else candidate_signal
    status = "SEM_SINAL" if candidate_signal == "HOLD" and not blocks else "BLOQUEADO_QUANT" if blocks else f"SINAL_{signal}"

    price = _num(latest.get("Close"))
    atr = _num(latest.get("ATR"))
    risk = _risk_payload(signal, price, atr, settings)
    volume = _num(latest.get("Volume"))
    volume_avg = _num(latest.get("VOLUME_AVG"))
    if bool(latest.get("VOLUME_SPIKE", False)):
        volume_label = "acima da media"
    elif _finite(volume) and _finite(volume_avg) and volume < volume_avg:
        volume_label = "abaixo da media"
    else:
        volume_label = "na media"

    volatility_label = "alta" if regime == "chaotic" else "comprimida" if bool(latest.get("SQUEEZE", False)) else "controlada"
    confidence = "alta" if score >= 80 else "moderada" if score >= 60 else "baixa"

    return {
        "ativo": asset,
        "label": label,
        "ticker": ticker,
        "regime": regime,
        "score": score,
        "tendencia": _trend_label(latest),
        "vwap": _num(latest.get("VWAP"), None),
        "vwap_rolling": _num(latest.get("VWAP_ROLLING"), None),
        "poc": _num(latest.get("POC"), None),
        "vah": _num(latest.get("VAH"), None),
        "val": _num(latest.get("VAL"), None),
        "atr": _num(latest.get("ATR"), None),
        "adx": _num(latest.get("ADX"), None),
        "ema_8": _num(latest.get("EMA_8"), None),
        "ema_21": _num(latest.get("EMA_21"), None),
        "ema_80": _num(latest.get("EMA_80"), None),
        "ema_200": _num(latest.get("EMA_200"), None),
        "obv": _num(latest.get("OBV"), None),
        "volume_atual": _num(latest.get("Volume"), None),
        "volume_medio": _num(latest.get("VOLUME_AVG"), None),
        "volume_spike": bool(latest.get("VOLUME_SPIKE", False)),
        "entrada": risk["entrada"],
        "stop": risk["stop"],
        "alvo": risk["alvo"],
        "volume": volume_label,
        "volatilidade": volatility_label,
        "risk_reward": risk["risk_reward"],
        "position_size": risk["position_size"],
        "risk_percent": risk["risk_percent"],
        "confianca": confidence,
        "signal": signal,
        "raw_signal": candidate_signal,
        "status": status,
        "block_reasons": blocks,
        "score_components": components,
        "macro_score": macro_context.score,
        "macro_regime": macro_context.regime,
        "macro_nao_operar": macro_context.nao_operar,
        "macro_direction": macro_context.macro_directions.get(asset),
        "llm_decision_guardrail": "LLM apenas explica; sinal e risco sao deterministicos.",
        "explanation": "",
    }


def gerar_relatorios_quant(
    frames: dict[str, pd.DataFrame],
    tickers: dict[str, str],
    macro_context: MacroContext,
    settings: AppSettings,
) -> list[dict[str, Any]]:
    reports = []
    for asset, ticker in tickers.items():
        reports.append(
            gerar_relatorio_quant(
                asset=asset,
                ticker=ticker,
                frame=frames.get(asset, pd.DataFrame()),
                macro_context=macro_context,
                settings=settings,
            )
        )
    return reports


def serialize_quant_indicator_frame(frame: pd.DataFrame, settings: AppSettings, limit: int = 120) -> list[dict[str, Any]]:
    enriched = enriquecer_frame_quant(frame, settings)
    if enriched.empty:
        return []
    points = []
    columns = [
        "Close",
        "VWAP",
        "VWAP_ROLLING",
        "POC",
        "ATR",
        "ADX",
        "OBV",
        "VOLUME_AVG",
        "EMA_8",
        "EMA_21",
        "EMA_80",
        "EMA_200",
        "BB_UPPER",
        "BB_LOWER",
    ]
    for timestamp, row in enriched.tail(limit).iterrows():
        payload = {"timestamp": pd.Timestamp(timestamp).strftime("%Y-%m-%d %H:%M")}
        for column in columns:
            payload[column.lower()] = _num(row.get(column), None)
        payload["volume_spike"] = bool(row.get("VOLUME_SPIKE", False))
        payload["squeeze"] = bool(row.get("SQUEEZE", False))
        points.append(payload)
    return points
