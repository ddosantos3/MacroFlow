from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import StrEnum
from typing import Any
from zoneinfo import ZoneInfo


class IntradayAssetClass(StrEnum):
    INDEX = "INDEX"
    DOLLAR = "DOLLAR"


class TradeSide(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    NONE = "NONE"


class CorrelationState(StrEnum):
    STRONG_LONG_BIAS = "STRONG_LONG_BIAS"
    WEAK_LONG_BIAS = "WEAK_LONG_BIAS"
    NEUTRAL = "NEUTRAL"
    WEAK_SHORT_BIAS = "WEAK_SHORT_BIAS"
    STRONG_SHORT_BIAS = "STRONG_SHORT_BIAS"


class IntradayDecisionStatus(StrEnum):
    NO_TRADE = "NO_TRADE"
    ARMED_LONG = "ARMED_LONG"
    ARMED_SHORT = "ARMED_SHORT"
    ENTER_LONG = "ENTER_LONG"
    ENTER_SHORT = "ENTER_SHORT"
    MANAGE_POSITION = "MANAGE_POSITION"
    EXIT_POSITION = "EXIT_POSITION"
    BLOCKED = "BLOCKED"


class BlockReason(StrEnum):
    STALE_DATA = "STALE_DATA"
    MISSING_PROXY = "MISSING_PROXY"
    ORDERFLOW_UNAVAILABLE = "ORDERFLOW_UNAVAILABLE"
    INVALID_RANGE = "INVALID_RANGE"
    LOW_LIQUIDITY = "LOW_LIQUIDITY"
    OUTSIDE_TRADING_WINDOW = "OUTSIDE_TRADING_WINDOW"
    MACRO_CONFLICT = "MACRO_CONFLICT"
    MICRO_CONFLICT = "MICRO_CONFLICT"
    BAD_PRICE_LOCATION = "BAD_PRICE_LOCATION"
    COMPRESSED_SESSION_RANGE = "COMPRESSED_SESSION_RANGE"
    RSI_CONFLICT = "RSI_CONFLICT"
    LOW_PARTICIPATION = "LOW_PARTICIPATION"
    FLOW_NOT_CONFIRMED = "FLOW_NOT_CONFIRMED"
    BAD_RISK_REWARD = "BAD_RISK_REWARD"
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_TIMEFRAME = "INVALID_TIMEFRAME"
    INVALID_STOP = "INVALID_STOP"
    INVALID_RISK_CONFIG = "INVALID_RISK_CONFIG"
    RISK_LIMIT_EXCEEDED = "RISK_LIMIT_EXCEEDED"
    MISSING_EXPECTANCY = "MISSING_EXPECTANCY"
    NEGATIVE_EXPECTANCY = "NEGATIVE_EXPECTANCY"
    HIGH_IMPACT_NEWS_WINDOW = "HIGH_IMPACT_NEWS_WINDOW"


@dataclass(slots=True)
class IntradayDecisionConfig:
    rules_version: str = "macroflow-v2.0.0"
    context_timeframe_minutes: int = 60
    execution_timeframe_minutes: int = 5
    timezone: str = "America/Sao_Paulo"
    trading_start: str = "09:05"
    trading_end: str = "17:25"
    no_trade_first_minutes: int = 5
    no_new_entries_before_close_minutes: int = 10
    max_data_latency_seconds: int = 90
    proxy_max_latency_seconds: int = 600
    orderflow_max_latency_seconds: int = 30
    min_session_range_default: float = 0.0
    min_session_range_by_asset: dict[str, float] = field(
        default_factory=lambda: {
            "BRA50": 250.0,
            "WIN": 250.0,
            "INDICE": 250.0,
            "USDBRL": 0.01,
            "WDO": 0.01,
            "DOLAR": 0.01,
        }
    )
    stop_buffer_points_by_asset: dict[str, float] = field(default_factory=dict)
    min_rvol: float = 1.20
    imbalance_long_threshold: float = 0.15
    imbalance_short_threshold: float = -0.15
    min_risk_reward: float = 2.0
    weak_bias_threshold: float = 0.25
    strong_bias_threshold: float = 0.80
    max_stop_atr_multiple: float = 2.5
    default_risk_percent: float = 0.005
    daily_risk_percent: float = 0.02
    max_trades_per_asset: int = 3
    max_consecutive_losses: int = 2
    required_proxies: tuple[str, ...] = ("DXY", "US10Y", "SPX", "USDBRL")
    asset_classes: dict[str, str] = field(
        default_factory=lambda: {
            "BRA50": IntradayAssetClass.INDEX.value,
            "WIN": IntradayAssetClass.INDEX.value,
            "IBOV": IntradayAssetClass.INDEX.value,
            "INDICE": IntradayAssetClass.INDEX.value,
            "USDBRL": IntradayAssetClass.DOLLAR.value,
            "WDO": IntradayAssetClass.DOLLAR.value,
            "DOLAR": IntradayAssetClass.DOLLAR.value,
        }
    )


@dataclass(slots=True)
class MarketBar:
    timestamp: datetime
    timeframe_minutes: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    average_price: float


@dataclass(slots=True)
class IntradayMarketState:
    asset: str
    asset_class: str
    execution_bar: MarketBar
    context_bar: MarketBar
    session_open: float
    session_high: float
    session_low: float
    vwap: float
    execution_ema9: float
    execution_ema21: float
    context_ema9: float
    context_ema21: float
    rsi14: float
    previous_rsi14: float
    atr: float
    average_volume_same_time: float | None = None
    average_financial_volume_window: float | None = None
    last_swing_low: float | None = None
    last_swing_high: float | None = None
    next_structural_support: float | None = None
    next_structural_resistance: float | None = None
    data_latency_seconds: float | None = None


@dataclass(slots=True)
class ProxyState:
    symbol: str
    value: float
    short_return: float
    timestamp: datetime
    normalized_return: float | None = None
    max_latency_seconds: float | None = None


@dataclass(slots=True)
class OrderFlowSnapshot:
    timestamp: datetime
    aggressor_buy: float
    aggressor_sell: float
    short_window_volume: float
    trade_velocity: float | None = None
    max_latency_seconds: float | None = None


@dataclass(slots=True)
class RiskState:
    capital: float
    risk_percent: float
    point_value: float
    daily_realized_loss: float = 0.0
    daily_risk_limit: float | None = None
    trades_today: int = 0
    max_trades_per_asset: int | None = None
    consecutive_losses: int = 0
    max_consecutive_losses: int | None = None


@dataclass(slots=True)
class IntradayDecisionInput:
    asset: str
    timestamp: datetime
    market: IntradayMarketState | None
    proxies: dict[str, ProxyState]
    order_flow: OrderFlowSnapshot | None
    risk: RiskState | None
    requested_side: str | None = None
    setup_win_probability: float | None = None
    high_impact_news_active: bool = False


@dataclass(slots=True)
class GateResult:
    name: str
    approved: bool
    code: str | None
    detail: str


@dataclass(slots=True)
class IntradayDecision:
    asset: str
    timestamp: str
    context_timeframe: str
    execution_timeframe: str
    asset_context: str
    zone: float | None
    price_vs_vwap: str
    ema9: float | None
    ema21: float | None
    rsi: float | None
    rvol: float | None
    imbalance: float | None
    allowed_side: str
    requested_side: str
    entry_status: str
    reason: str
    block_reasons: list[str]
    entry_price: float | None
    stop_price: float | None
    target_price: float | None
    financial_risk: float | None
    risk_reward: float | None
    quantity: int | None
    operational_confidence: str
    rules_version: str
    gates: list[GateResult] = field(default_factory=list)
    features: dict[str, Any] = field(default_factory=dict)
    audit: dict[str, Any] = field(default_factory=dict)


def _finite(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def _num(value: Any) -> float | None:
    if not _finite(value):
        return None
    return float(value)


def _seconds_between(left: datetime, right: datetime) -> float:
    if left.tzinfo is None and right.tzinfo is not None:
        left = left.replace(tzinfo=right.tzinfo)
    if right.tzinfo is None and left.tzinfo is not None:
        right = right.replace(tzinfo=left.tzinfo)
    return abs((left - right).total_seconds())


def _parse_hhmm(value: str) -> time:
    return time.fromisoformat(value.strip())


def _asset_class_for(asset: str, market: IntradayMarketState | None, config: IntradayDecisionConfig) -> str:
    if market and market.asset_class:
        return str(market.asset_class)
    return config.asset_classes.get(asset.upper(), IntradayAssetClass.INDEX.value)


def _side_from_state(state: str) -> TradeSide:
    if state in {CorrelationState.STRONG_LONG_BIAS.value, CorrelationState.WEAK_LONG_BIAS.value}:
        return TradeSide.LONG
    if state in {CorrelationState.STRONG_SHORT_BIAS.value, CorrelationState.WEAK_SHORT_BIAS.value}:
        return TradeSide.SHORT
    return TradeSide.NONE


def _normalize_side(value: str | None) -> TradeSide:
    if not value:
        return TradeSide.NONE
    normalized = value.strip().upper()
    if normalized in {"LONG", "BUY", "COMPRA"}:
        return TradeSide.LONG
    if normalized in {"SHORT", "SELL", "VENDA"}:
        return TradeSide.SHORT
    return TradeSide.NONE


def _correlation_weights(asset_class: str) -> dict[str, float]:
    if asset_class == IntradayAssetClass.DOLLAR.value:
        return {"DXY": 1.0, "US10Y": 1.0, "SPX": -1.0, "USDBRL": 1.0}
    return {"SPX": 1.0, "DXY": -1.0, "US10Y": -1.0, "USDBRL": -1.0}


def classify_correlation_state(
    asset_class: str,
    proxies: dict[str, ProxyState],
    config: IntradayDecisionConfig | None = None,
) -> tuple[str, float, dict[str, float]]:
    config = config or IntradayDecisionConfig()
    weights = _correlation_weights(asset_class)
    contributions: dict[str, float] = {}
    total = 0.0
    for symbol, weight in weights.items():
        proxy = proxies.get(symbol)
        if proxy is None:
            continue
        raw = proxy.normalized_return if proxy.normalized_return is not None else proxy.short_return
        if not _finite(raw):
            continue
        contribution = float(raw) * weight
        contributions[symbol] = contribution
        total += contribution

    if total >= config.strong_bias_threshold:
        state = CorrelationState.STRONG_LONG_BIAS.value
    elif total >= config.weak_bias_threshold:
        state = CorrelationState.WEAK_LONG_BIAS.value
    elif total <= -config.strong_bias_threshold:
        state = CorrelationState.STRONG_SHORT_BIAS.value
    elif total <= -config.weak_bias_threshold:
        state = CorrelationState.WEAK_SHORT_BIAS.value
    else:
        state = CorrelationState.NEUTRAL.value
    return state, total, contributions


def _market_missing_fields(market: IntradayMarketState) -> list[str]:
    fields: dict[str, Any] = {
        "session_open": market.session_open,
        "session_high": market.session_high,
        "session_low": market.session_low,
        "vwap": market.vwap,
        "execution_ema9": market.execution_ema9,
        "execution_ema21": market.execution_ema21,
        "context_ema9": market.context_ema9,
        "context_ema21": market.context_ema21,
        "rsi14": market.rsi14,
        "previous_rsi14": market.previous_rsi14,
        "atr": market.atr,
        "execution_open": market.execution_bar.open,
        "execution_high": market.execution_bar.high,
        "execution_low": market.execution_bar.low,
        "execution_close": market.execution_bar.close,
        "execution_volume": market.execution_bar.volume,
        "execution_average_price": market.execution_bar.average_price,
        "context_open": market.context_bar.open,
        "context_high": market.context_bar.high,
        "context_low": market.context_bar.low,
        "context_close": market.context_bar.close,
        "context_volume": market.context_bar.volume,
        "context_average_price": market.context_bar.average_price,
    }
    return [name for name, value in fields.items() if not _finite(value)]


def _invalid_ohlc(bar: MarketBar) -> bool:
    values = [bar.open, bar.high, bar.low, bar.close, bar.volume, bar.average_price]
    if any(not _finite(value) for value in values):
        return True
    if bar.high < bar.low:
        return True
    if not (bar.low <= bar.open <= bar.high and bar.low <= bar.close <= bar.high):
        return True
    return bar.volume <= 0 or bar.average_price <= 0


def _outside_trading_window(payload: IntradayDecisionInput, config: IntradayDecisionConfig) -> str | None:
    tz = ZoneInfo(config.timezone)
    timestamp = payload.timestamp if payload.timestamp.tzinfo else payload.timestamp.replace(tzinfo=tz)
    timestamp = timestamp.astimezone(tz)
    current = timestamp.time()
    start = _parse_hhmm(config.trading_start)
    end = _parse_hhmm(config.trading_end)
    if current < start or current > end:
        return f"Fora da janela configurada {config.trading_start}-{config.trading_end}."

    minutes_from_start = (
        timestamp.hour * 60
        + timestamp.minute
        - (start.hour * 60 + start.minute)
    )
    minutes_to_end = end.hour * 60 + end.minute - (timestamp.hour * 60 + timestamp.minute)
    if minutes_from_start < config.no_trade_first_minutes:
        return "Primeiros minutos de abertura bloqueados."
    if minutes_to_end <= config.no_new_entries_before_close_minutes:
        return "Nova entrada perto do encerramento bloqueada."
    if payload.high_impact_news_active:
        return "Janela de noticia de alto impacto ativa."
    return None


def _rsi_confirms(side: TradeSide, current: float, previous: float) -> bool:
    if side == TradeSide.LONG:
        return (previous < 30 <= current) or (current > 50 and current >= previous)
    if side == TradeSide.SHORT:
        return (previous > 70 >= current) or (current < 50 and current <= previous)
    return False


def _candle_confirms(side: TradeSide, bar: MarketBar) -> bool:
    candle_range = bar.high - bar.low
    if candle_range <= 0:
        return False
    body = abs(bar.close - bar.open)
    upper_wick = bar.high - max(bar.open, bar.close)
    lower_wick = min(bar.open, bar.close) - bar.low
    close_position = (bar.close - bar.low) / candle_range

    if side == TradeSide.LONG:
        rejection = lower_wick >= max(body, candle_range * 0.25) and bar.close > bar.open
        consistent_close = bar.close > bar.open and close_position >= 0.60
        return rejection or consistent_close

    if side == TradeSide.SHORT:
        rejection = upper_wick >= max(body, candle_range * 0.25) and bar.close < bar.open
        consistent_close = bar.close < bar.open and close_position <= 0.40
        return rejection or consistent_close
    return False


def _calculate_stop(side: TradeSide, market: IntradayMarketState, config: IntradayDecisionConfig) -> float | None:
    entry = market.execution_bar.close
    buffer = float(config.stop_buffer_points_by_asset.get(market.asset.upper(), 0.0))
    if side == TradeSide.LONG:
        candidates = [market.execution_bar.low]
        if _finite(market.last_swing_low):
            candidates.append(float(market.last_swing_low))
        valid = [candidate for candidate in candidates if candidate < entry]
        return max(valid) - buffer if valid else None

    if side == TradeSide.SHORT:
        candidates = [market.execution_bar.high]
        if _finite(market.last_swing_high):
            candidates.append(float(market.last_swing_high))
        valid = [candidate for candidate in candidates if candidate > entry]
        return min(valid) + buffer if valid else None
    return None


def _calculate_target(side: TradeSide, market: IntradayMarketState, entry: float, risk_distance: float) -> float | None:
    if risk_distance <= 0:
        return None
    if side == TradeSide.LONG:
        candidates = [entry + (2.0 * risk_distance)]
        if _finite(market.next_structural_resistance) and float(market.next_structural_resistance) > entry:
            candidates.append(float(market.next_structural_resistance))
        if market.session_high > entry:
            candidates.append(market.session_high)
        return min(candidates) if candidates else None

    if side == TradeSide.SHORT:
        candidates = [entry - (2.0 * risk_distance)]
        if _finite(market.next_structural_support) and float(market.next_structural_support) < entry:
            candidates.append(float(market.next_structural_support))
        if market.session_low < entry:
            candidates.append(market.session_low)
        return max(candidates) if candidates else None
    return None


def _price_vs_vwap(price: float | None, vwap: float | None) -> str:
    if price is None or vwap is None:
        return "UNKNOWN"
    if price > vwap:
        return "ABOVE_VWAP"
    if price < vwap:
        return "BELOW_VWAP"
    return "AT_VWAP"


def evaluate_intraday_decision(
    payload: IntradayDecisionInput,
    config: IntradayDecisionConfig | None = None,
) -> IntradayDecision:
    config = config or IntradayDecisionConfig()
    gates: list[GateResult] = []
    block_reasons: list[str] = []
    features: dict[str, Any] = {}
    requested_side = _normalize_side(payload.requested_side)
    allowed_side = TradeSide.NONE
    status = IntradayDecisionStatus.NO_TRADE
    reason = "NO_TRADE"
    entry_price: float | None = None
    stop_price: float | None = None
    target_price: float | None = None
    financial_risk: float | None = None
    risk_reward: float | None = None
    quantity: int | None = None
    zone: float | None = None
    rvol: float | None = None
    imbalance: float | None = None

    def reject(code: BlockReason, detail: str, gate: str) -> None:
        if code.value not in block_reasons:
            block_reasons.append(code.value)
        gates.append(GateResult(gate, False, code.value, detail))

    def approve(gate: str, detail: str) -> None:
        gates.append(GateResult(gate, True, None, detail))

    def finish(final_status: IntradayDecisionStatus, final_reason: str) -> IntradayDecision:
        market = payload.market
        price = _num(market.execution_bar.close) if market else None
        vwap = _num(market.vwap) if market else None
        approved = [gate.name for gate in gates if gate.approved]
        rejected = [
            {"gate": gate.name, "code": gate.code, "detail": gate.detail}
            for gate in gates
            if not gate.approved
        ]
        latency = {
            "market_seconds": market.data_latency_seconds if market else None,
            "orderflow_seconds": payload.order_flow.max_latency_seconds if payload.order_flow else None,
            "proxies_seconds": {
                symbol: proxy.max_latency_seconds for symbol, proxy in payload.proxies.items()
            },
        }
        confidence = "BLOCKED"
        if final_status in {IntradayDecisionStatus.ENTER_LONG, IntradayDecisionStatus.ENTER_SHORT}:
            bias = str(features.get("correlation_state") or "")
            confidence = "STRONG_CONFIRMED" if bias.startswith("STRONG") else "WEAK_CONFIRMED"
        elif final_status in {IntradayDecisionStatus.ARMED_LONG, IntradayDecisionStatus.ARMED_SHORT}:
            confidence = "ARMED"

        return IntradayDecision(
            asset=payload.asset,
            timestamp=payload.timestamp.isoformat(),
            context_timeframe=f"{config.context_timeframe_minutes}m",
            execution_timeframe=f"{config.execution_timeframe_minutes}m",
            asset_context=str(features.get("correlation_state") or CorrelationState.NEUTRAL.value),
            zone=zone,
            price_vs_vwap=_price_vs_vwap(price, vwap),
            ema9=_num(market.execution_ema9) if market else None,
            ema21=_num(market.execution_ema21) if market else None,
            rsi=_num(market.rsi14) if market else None,
            rvol=rvol,
            imbalance=imbalance,
            allowed_side=allowed_side.value,
            requested_side=requested_side.value,
            entry_status=final_status.value,
            reason=final_reason,
            block_reasons=block_reasons.copy(),
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            financial_risk=financial_risk,
            risk_reward=risk_reward,
            quantity=quantity,
            operational_confidence=confidence,
            rules_version=config.rules_version,
            gates=gates.copy(),
            features=features.copy(),
            audit={
                "input_latency": latency,
                "approved_rules": approved,
                "rejected_rules": rejected,
                "decision_final": final_status.value,
                "order_sent": False,
                "broker_response": None,
                "slippage": None,
                "decision_execution_divergence": None,
                "state_reconciliation_required": False,
            },
        )

    market = payload.market
    if market is None:
        reject(BlockReason.MISSING_FIELD, "Estado de mercado do ativo ausente.", "Gate 1 - Integridade de dados")
    else:
        missing = _market_missing_fields(market)
        if missing:
            reject(
                BlockReason.MISSING_FIELD,
                "Campos obrigatórios ausentes: " + ", ".join(missing),
                "Gate 1 - Integridade de dados",
            )
        if market.execution_bar.timeframe_minutes != config.execution_timeframe_minutes:
            reject(
                BlockReason.INVALID_TIMEFRAME,
                f"Candle de execução em {market.execution_bar.timeframe_minutes}m, esperado {config.execution_timeframe_minutes}m.",
                "Gate 1 - Integridade de dados",
            )
        if market.context_bar.timeframe_minutes != config.context_timeframe_minutes:
            reject(
                BlockReason.INVALID_TIMEFRAME,
                f"Candle de contexto em {market.context_bar.timeframe_minutes}m, esperado {config.context_timeframe_minutes}m.",
                "Gate 1 - Integridade de dados",
            )
        if _invalid_ohlc(market.execution_bar) or _invalid_ohlc(market.context_bar):
            reject(BlockReason.INVALID_RANGE, "OHLC inconsistente ou volume/preço médio inválido.", "Gate 1 - Integridade de dados")
        if market.session_high <= market.session_low:
            reject(BlockReason.INVALID_RANGE, "Máxima e mínima da sessão não formam range válido.", "Gate 1 - Integridade de dados")
        if market.data_latency_seconds is not None and market.data_latency_seconds > config.max_data_latency_seconds:
            reject(BlockReason.STALE_DATA, "Feed do ativo excedeu a latência máxima configurada.", "Gate 1 - Integridade de dados")
        if _seconds_between(payload.timestamp, market.execution_bar.timestamp) > config.max_data_latency_seconds:
            reject(BlockReason.STALE_DATA, "Candle de execução defasado.", "Gate 1 - Integridade de dados")

    missing_proxies = [symbol for symbol in config.required_proxies if symbol not in payload.proxies]
    invalid_proxies = [
        symbol
        for symbol, proxy in payload.proxies.items()
        if not _finite(proxy.value) or not _finite(proxy.short_return)
    ]
    stale_proxies = [
        symbol
        for symbol, proxy in payload.proxies.items()
        if _seconds_between(payload.timestamp, proxy.timestamp)
        > (proxy.max_latency_seconds or config.proxy_max_latency_seconds)
    ]
    if missing_proxies or invalid_proxies:
        details = []
        if missing_proxies:
            details.append("ausentes: " + ", ".join(missing_proxies))
        if invalid_proxies:
            details.append("inválidos: " + ", ".join(invalid_proxies))
        reject(BlockReason.MISSING_PROXY, "; ".join(details), "Gate 1 - Integridade de dados")
    if stale_proxies:
        reject(BlockReason.STALE_DATA, "Proxies defasados: " + ", ".join(stale_proxies), "Gate 1 - Integridade de dados")

    flow = payload.order_flow
    if flow is None:
        reject(BlockReason.ORDERFLOW_UNAVAILABLE, "Snapshot real de agressão/fluxo ausente.", "Gate 1 - Integridade de dados")
    else:
        if not all(_finite(value) for value in [flow.aggressor_buy, flow.aggressor_sell, flow.short_window_volume]):
            reject(BlockReason.ORDERFLOW_UNAVAILABLE, "Agressão compradora/vendedora ou volume curto inválido.", "Gate 1 - Integridade de dados")
        if flow.aggressor_buy + flow.aggressor_sell <= 0:
            reject(BlockReason.ORDERFLOW_UNAVAILABLE, "Agressão total zerada.", "Gate 1 - Integridade de dados")
        if _seconds_between(payload.timestamp, flow.timestamp) > (flow.max_latency_seconds or config.orderflow_max_latency_seconds):
            reject(BlockReason.STALE_DATA, "Fluxo/agressão defasado.", "Gate 1 - Integridade de dados")

    if block_reasons:
        return finish(IntradayDecisionStatus.NO_TRADE, block_reasons[0])
    approve("Gate 1 - Integridade de dados", "Todos os feeds obrigatórios estão presentes, atuais e coerentes.")

    outside_reason = _outside_trading_window(payload, config)
    if outside_reason:
        code = BlockReason.OUTSIDE_TRADING_WINDOW
        reject(code, outside_reason, "Gate 1b - Janela operacional")
        return finish(IntradayDecisionStatus.NO_TRADE, code.value)
    approve("Gate 1b - Janela operacional", "Horário operacional liberado para nova decisão.")

    assert market is not None
    assert flow is not None

    asset_class = _asset_class_for(payload.asset, market, config)
    correlation_state, correlation_score, contributions = classify_correlation_state(asset_class, payload.proxies, config)
    allowed_side = _side_from_state(correlation_state)
    features.update(
        {
            "asset_class": asset_class,
            "correlation_state": correlation_state,
            "correlation_score": correlation_score,
            "correlation_contributions": contributions,
        }
    )
    if allowed_side == TradeSide.NONE:
        reject(BlockReason.MACRO_CONFLICT, "Correlação resultou em NEUTRAL.", "Gate 2 - Contexto macro e correlação")
        return finish(IntradayDecisionStatus.NO_TRADE, BlockReason.MACRO_CONFLICT.value)
    if requested_side != TradeSide.NONE and requested_side != allowed_side:
        reject(
            BlockReason.MACRO_CONFLICT,
            f"Lado solicitado {requested_side.value} conflita com lado permitido {allowed_side.value}.",
            "Gate 2 - Contexto macro e correlação",
        )
        return finish(IntradayDecisionStatus.BLOCKED, BlockReason.MACRO_CONFLICT.value)
    approve("Gate 2 - Contexto macro e correlação", f"{correlation_state} permite {allowed_side.value}.")

    entry_side = requested_side if requested_side != TradeSide.NONE else allowed_side
    session_range = market.session_high - market.session_low
    min_range = config.min_session_range_by_asset.get(payload.asset.upper(), config.min_session_range_default)
    features["session_range"] = session_range
    features["min_session_range"] = min_range
    if session_range < min_range:
        reject(BlockReason.COMPRESSED_SESSION_RANGE, "Range da sessão abaixo do mínimo configurado.", "Gate 3 - Estrutura e zona")
        return finish(IntradayDecisionStatus.NO_TRADE, BlockReason.COMPRESSED_SESSION_RANGE.value)
    if not (market.session_low <= market.execution_bar.close <= market.session_high):
        reject(BlockReason.INVALID_RANGE, "Preço atual fora da máxima/mínima da sessão.", "Gate 3 - Estrutura e zona")
        return finish(IntradayDecisionStatus.NO_TRADE, BlockReason.INVALID_RANGE.value)

    zone = (market.execution_bar.close - market.session_low) / session_range
    features["zone"] = zone
    if entry_side == TradeSide.LONG and zone > 0.25:
        reject(BlockReason.BAD_PRICE_LOCATION, "Compra fora da região barata (0.00-0.25).", "Gate 3 - Estrutura e zona")
        return finish(IntradayDecisionStatus.BLOCKED, BlockReason.BAD_PRICE_LOCATION.value)
    if entry_side == TradeSide.SHORT and zone < 0.75:
        reject(BlockReason.BAD_PRICE_LOCATION, "Venda fora da região cara (0.75-1.00).", "Gate 3 - Estrutura e zona")
        return finish(IntradayDecisionStatus.BLOCKED, BlockReason.BAD_PRICE_LOCATION.value)

    price = market.execution_bar.close
    structure_ok = (
        price > market.vwap
        and market.execution_ema9 > market.execution_ema21
        and market.context_ema9 > market.context_ema21
        and market.context_bar.close > market.context_bar.open
    )
    if entry_side == TradeSide.SHORT:
        structure_ok = (
            price < market.vwap
            and market.execution_ema9 < market.execution_ema21
            and market.context_ema9 < market.context_ema21
            and market.context_bar.close < market.context_bar.open
        )
    if not structure_ok:
        reject(BlockReason.MICRO_CONFLICT, "Preço, VWAP, EMAs ou candle de 60m não alinham com o lado.", "Gate 3 - Estrutura e zona")
        return finish(IntradayDecisionStatus.BLOCKED, BlockReason.MICRO_CONFLICT.value)

    if not _rsi_confirms(entry_side, market.rsi14, market.previous_rsi14):
        reject(BlockReason.RSI_CONFLICT, "RSI contradiz ou não confirma a retomada do contexto.", "Gate 3 - Estrutura e zona")
        return finish(IntradayDecisionStatus.BLOCKED, BlockReason.RSI_CONFLICT.value)
    approve("Gate 3 - Estrutura e zona", "Estrutura, VWAP, EMAs, RSI e localização de preço alinhados.")

    financial_volume = market.execution_bar.average_price * market.execution_bar.volume
    features["financial_volume"] = financial_volume
    if market.execution_bar.volume <= 0 or financial_volume <= 0:
        reject(BlockReason.LOW_LIQUIDITY, "Volume ou volume financeiro zerado.", "Gate 4 - Participação")
        return finish(IntradayDecisionStatus.NO_TRADE, BlockReason.LOW_LIQUIDITY.value)
    if market.average_volume_same_time and market.average_volume_same_time > 0:
        rvol = market.execution_bar.volume / market.average_volume_same_time
    financial_volume_ok = (
        market.average_financial_volume_window is not None
        and market.average_financial_volume_window > 0
        and financial_volume > market.average_financial_volume_window
    )
    rvol_ok = rvol is not None and rvol >= config.min_rvol
    if rvol is None and market.average_financial_volume_window is None:
        reject(BlockReason.MISSING_FIELD, "Benchmarks reais de RVOL/volume financeiro não foram fornecidos.", "Gate 4 - Participação")
        return finish(IntradayDecisionStatus.NO_TRADE, BlockReason.MISSING_FIELD.value)
    if not (rvol_ok or financial_volume_ok):
        reject(BlockReason.LOW_PARTICIPATION, "RVOL e volume financeiro abaixo do mínimo.", "Gate 4 - Participação")
        return finish(IntradayDecisionStatus.BLOCKED, BlockReason.LOW_PARTICIPATION.value)
    approve("Gate 4 - Participação", "RVOL ou volume financeiro confirmam participação real.")

    imbalance = (flow.aggressor_buy - flow.aggressor_sell) / (flow.aggressor_buy + flow.aggressor_sell)
    features["imbalance"] = imbalance
    if entry_side == TradeSide.LONG and imbalance < config.imbalance_long_threshold:
        reject(BlockReason.FLOW_NOT_CONFIRMED, "Agressão líquida não confirma compra.", "Gate 5 - Fluxo")
        return finish(IntradayDecisionStatus.BLOCKED, BlockReason.FLOW_NOT_CONFIRMED.value)
    if entry_side == TradeSide.SHORT and imbalance > config.imbalance_short_threshold:
        reject(BlockReason.FLOW_NOT_CONFIRMED, "Agressão líquida não confirma venda.", "Gate 5 - Fluxo")
        return finish(IntradayDecisionStatus.BLOCKED, BlockReason.FLOW_NOT_CONFIRMED.value)
    approve("Gate 5 - Fluxo", "Desequilíbrio de agressão confirma o lado permitido.")

    if not _candle_confirms(entry_side, market.execution_bar):
        status = IntradayDecisionStatus.ARMED_LONG if entry_side == TradeSide.LONG else IntradayDecisionStatus.ARMED_SHORT
        gates.append(
            GateResult(
                "Gate 6 - Candle de confirmação",
                False,
                BlockReason.MICRO_CONFLICT.value,
                "Candle de 5m ainda não confirmou gatilho.",
            )
        )
        return finish(status, "CANDLE_NOT_CONFIRMED")
    approve("Gate 6 - Candle de confirmação", "Candle de 5m confirmou rejeição/fechamento consistente.")

    entry_price = market.execution_bar.close
    stop_price = _calculate_stop(entry_side, market, config)
    if stop_price is None:
        reject(BlockReason.INVALID_STOP, "Stop estrutural válido não localizado.", "Gate 7 - Risco e auditoria")
        return finish(IntradayDecisionStatus.NO_TRADE, BlockReason.INVALID_STOP.value)
    risk_distance = abs(entry_price - stop_price)
    if risk_distance <= 0 or (_finite(market.atr) and risk_distance > market.atr * config.max_stop_atr_multiple):
        reject(BlockReason.INVALID_STOP, "Distância do stop inválida ou excessiva contra ATR.", "Gate 7 - Risco e auditoria")
        return finish(IntradayDecisionStatus.NO_TRADE, BlockReason.INVALID_STOP.value)

    target_price = _calculate_target(entry_side, market, entry_price, risk_distance)
    if target_price is None:
        reject(BlockReason.BAD_RISK_REWARD, "Alvo objetivo não localizado.", "Gate 7 - Risco e auditoria")
        return finish(IntradayDecisionStatus.NO_TRADE, BlockReason.BAD_RISK_REWARD.value)
    target_distance = abs(target_price - entry_price)
    risk_reward = target_distance / risk_distance if risk_distance else None
    if risk_reward is None or risk_reward < config.min_risk_reward:
        reject(BlockReason.BAD_RISK_REWARD, "Relação risco-retorno abaixo de 2R.", "Gate 7 - Risco e auditoria")
        return finish(IntradayDecisionStatus.BLOCKED, BlockReason.BAD_RISK_REWARD.value)

    probability = payload.setup_win_probability
    if probability is None or not _finite(probability):
        reject(BlockReason.MISSING_EXPECTANCY, "Probabilidade real/backtestada do setup ausente.", "Gate 7 - Risco e auditoria")
        return finish(IntradayDecisionStatus.NO_TRADE, BlockReason.MISSING_EXPECTANCY.value)
    probability = float(probability)
    if probability <= 0 or probability >= 1:
        reject(BlockReason.MISSING_EXPECTANCY, "Probabilidade do setup fora do intervalo aberto 0-1.", "Gate 7 - Risco e auditoria")
        return finish(IntradayDecisionStatus.NO_TRADE, BlockReason.MISSING_EXPECTANCY.value)
    expectancy = (probability * target_distance) - ((1 - probability) * risk_distance)
    features["expectancy"] = expectancy
    features["setup_win_probability"] = probability
    if expectancy <= 0:
        reject(BlockReason.NEGATIVE_EXPECTANCY, "Expectativa operacional não é positiva.", "Gate 7 - Risco e auditoria")
        return finish(IntradayDecisionStatus.BLOCKED, BlockReason.NEGATIVE_EXPECTANCY.value)

    risk = payload.risk
    if risk is None or not all(_finite(value) for value in [risk.capital, risk.risk_percent, risk.point_value]):
        reject(BlockReason.INVALID_RISK_CONFIG, "Capital, risco percentual ou valor por ponto ausente.", "Gate 7 - Risco e auditoria")
        return finish(IntradayDecisionStatus.NO_TRADE, BlockReason.INVALID_RISK_CONFIG.value)
    if risk.capital <= 0 or risk.risk_percent <= 0 or risk.point_value <= 0:
        reject(BlockReason.INVALID_RISK_CONFIG, "Configuração de risco não positiva.", "Gate 7 - Risco e auditoria")
        return finish(IntradayDecisionStatus.NO_TRADE, BlockReason.INVALID_RISK_CONFIG.value)
    max_trades = risk.max_trades_per_asset or config.max_trades_per_asset
    max_losses = risk.max_consecutive_losses or config.max_consecutive_losses
    daily_limit = risk.daily_risk_limit if risk.daily_risk_limit is not None else risk.capital * config.daily_risk_percent
    if risk.trades_today >= max_trades:
        reject(BlockReason.RISK_LIMIT_EXCEEDED, "Número máximo de operações do ativo atingido.", "Gate 7 - Risco e auditoria")
        return finish(IntradayDecisionStatus.NO_TRADE, BlockReason.RISK_LIMIT_EXCEEDED.value)
    if risk.consecutive_losses >= max_losses:
        reject(BlockReason.RISK_LIMIT_EXCEEDED, "Máximo de perdas consecutivas atingido.", "Gate 7 - Risco e auditoria")
        return finish(IntradayDecisionStatus.NO_TRADE, BlockReason.RISK_LIMIT_EXCEEDED.value)
    if risk.daily_realized_loss >= daily_limit:
        reject(BlockReason.RISK_LIMIT_EXCEEDED, "Limite de perda diária atingido.", "Gate 7 - Risco e auditoria")
        return finish(IntradayDecisionStatus.NO_TRADE, BlockReason.RISK_LIMIT_EXCEEDED.value)

    risk_per_contract = risk_distance * risk.point_value
    allowed_financial_risk = risk.capital * risk.risk_percent
    quantity = math.floor(allowed_financial_risk / risk_per_contract) if risk_per_contract > 0 else 0
    financial_risk = quantity * risk_per_contract
    features["risk_per_contract"] = risk_per_contract
    features["allowed_financial_risk"] = allowed_financial_risk
    if quantity < 1:
        reject(BlockReason.RISK_LIMIT_EXCEEDED, "Risco por contrato excede o risco financeiro permitido.", "Gate 7 - Risco e auditoria")
        return finish(IntradayDecisionStatus.NO_TRADE, BlockReason.RISK_LIMIT_EXCEEDED.value)
    approve("Gate 7 - Risco e auditoria", "Stop, alvo, expectativa positiva, sizing e limites operacionais aprovados.")

    status = IntradayDecisionStatus.ENTER_LONG if entry_side == TradeSide.LONG else IntradayDecisionStatus.ENTER_SHORT
    return finish(status, status.value)


def build_unavailable_intraday_decision(
    asset: str,
    timestamp: str | datetime,
    reasons: list[str] | None = None,
    config: IntradayDecisionConfig | None = None,
) -> IntradayDecision:
    config = config or IntradayDecisionConfig()
    parsed_timestamp = timestamp if isinstance(timestamp, datetime) else datetime.fromisoformat(str(timestamp))
    block_reasons = reasons or [BlockReason.ORDERFLOW_UNAVAILABLE.value]
    gates = [
        GateResult(
            name="Gate 1 - Integridade de dados",
            approved=False,
            code=block_reasons[0],
            detail="Motor v2 exige feed real de 5m/60m, proxies monitorados e fluxo/agressão real.",
        )
    ]
    return IntradayDecision(
        asset=asset,
        timestamp=parsed_timestamp.isoformat(),
        context_timeframe=f"{config.context_timeframe_minutes}m",
        execution_timeframe=f"{config.execution_timeframe_minutes}m",
        asset_context=CorrelationState.NEUTRAL.value,
        zone=None,
        price_vs_vwap="UNKNOWN",
        ema9=None,
        ema21=None,
        rsi=None,
        rvol=None,
        imbalance=None,
        allowed_side=TradeSide.NONE.value,
        requested_side=TradeSide.NONE.value,
        entry_status=IntradayDecisionStatus.NO_TRADE.value,
        reason=block_reasons[0],
        block_reasons=block_reasons,
        entry_price=None,
        stop_price=None,
        target_price=None,
        financial_risk=None,
        risk_reward=None,
        quantity=None,
        operational_confidence="BLOCKED",
        rules_version=config.rules_version,
        gates=gates,
        features={"production_feed_required": True},
        audit={
            "approved_rules": [],
            "rejected_rules": [{"gate": gates[0].name, "code": gates[0].code, "detail": gates[0].detail}],
            "decision_final": IntradayDecisionStatus.NO_TRADE.value,
            "order_sent": False,
            "broker_response": None,
            "slippage": None,
            "decision_execution_divergence": None,
            "state_reconciliation_required": True,
        },
    )


def summarize_intraday_decisions(decisions: list[IntradayDecision]) -> dict[str, Any]:
    status_counter = Counter(decision.entry_status for decision in decisions)
    reason_counter = Counter(reason for decision in decisions for reason in decision.block_reasons)
    entries = sum(1 for decision in decisions if decision.entry_status in {"ENTER_LONG", "ENTER_SHORT"})
    return {
        "decisions_count": len(decisions),
        "entries_count": entries,
        "entry_rate": entries / len(decisions) if decisions else 0.0,
        "status_counts": dict(status_counter),
        "block_reason_counts": dict(reason_counter),
        "rules_version": decisions[0].rules_version if decisions else IntradayDecisionConfig().rules_version,
    }
