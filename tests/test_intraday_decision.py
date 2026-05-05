from datetime import datetime
from zoneinfo import ZoneInfo

from src.macroflow.intraday_decision import (
    IntradayAssetClass,
    IntradayDecisionConfig,
    IntradayDecisionInput,
    IntradayMarketState,
    MarketBar,
    OrderFlowSnapshot,
    ProxyState,
    RiskState,
    classify_correlation_state,
    evaluate_intraday_decision,
)


def _ts() -> datetime:
    return datetime(2026, 5, 5, 10, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))


def _proxies(ts: datetime) -> dict[str, ProxyState]:
    return {
        "DXY": ProxyState("DXY", 105.0, 0.003, ts, normalized_return=0.30),
        "US10Y": ProxyState("US10Y", 4.6, 0.002, ts, normalized_return=0.30),
        "SPX": ProxyState("SPX", 5200.0, -0.004, ts, normalized_return=-0.30),
        "USDBRL": ProxyState("USDBRL", 5.18, 0.004, ts, normalized_return=0.30),
    }


def _market(ts: datetime, close: float = 104.0) -> IntradayMarketState:
    return IntradayMarketState(
        asset="USDBRL",
        asset_class=IntradayAssetClass.DOLLAR.value,
        execution_bar=MarketBar(
            timestamp=ts,
            timeframe_minutes=5,
            open=close - 0.5,
            high=close + 0.5,
            low=close - 1.2,
            close=close,
            volume=1500.0,
            average_price=close,
        ),
        context_bar=MarketBar(
            timestamp=ts,
            timeframe_minutes=60,
            open=102.0,
            high=105.0,
            low=101.5,
            close=104.2,
            volume=12000.0,
            average_price=103.5,
        ),
        session_open=101.0,
        session_high=120.0,
        session_low=100.0,
        vwap=close - 1.0,
        execution_ema9=close + 0.4,
        execution_ema21=close - 0.4,
        context_ema9=103.7,
        context_ema21=102.9,
        rsi14=52.0,
        previous_rsi14=45.0,
        atr=1.0,
        average_volume_same_time=1000.0,
        average_financial_volume_window=100000.0,
        last_swing_low=close - 1.6,
        next_structural_resistance=110.0,
        data_latency_seconds=3.0,
    )


def _flow(ts: datetime) -> OrderFlowSnapshot:
    return OrderFlowSnapshot(
        timestamp=ts,
        aggressor_buy=650.0,
        aggressor_sell=350.0,
        short_window_volume=1000.0,
        trade_velocity=120.0,
    )


def _risk() -> RiskState:
    return RiskState(
        capital=100000.0,
        risk_percent=0.005,
        point_value=10.0,
        daily_realized_loss=0.0,
        trades_today=0,
        consecutive_losses=0,
    )


def _payload(close: float = 104.0) -> IntradayDecisionInput:
    ts = _ts()
    return IntradayDecisionInput(
        asset="USDBRL",
        timestamp=ts,
        market=_market(ts, close=close),
        proxies=_proxies(ts),
        order_flow=_flow(ts),
        risk=_risk(),
        requested_side="LONG",
        setup_win_probability=0.45,
    )


def test_intraday_v2_enters_long_when_all_gates_pass() -> None:
    decision = evaluate_intraday_decision(_payload())

    assert decision.entry_status == "ENTER_LONG"
    assert decision.allowed_side == "LONG"
    assert decision.reason == "ENTER_LONG"
    assert decision.zone is not None and decision.zone <= 0.25
    assert decision.imbalance is not None and decision.imbalance >= 0.15
    assert decision.stop_price is not None and decision.stop_price < decision.entry_price
    assert decision.target_price is not None and decision.target_price > decision.entry_price
    assert decision.risk_reward == 2.0
    assert decision.quantity is not None and decision.quantity > 0
    assert decision.block_reasons == []


def test_intraday_v2_blocks_when_orderflow_is_missing() -> None:
    payload = _payload()
    payload.order_flow = None

    decision = evaluate_intraday_decision(payload)

    assert decision.entry_status == "NO_TRADE"
    assert decision.reason == "ORDERFLOW_UNAVAILABLE"
    assert "ORDERFLOW_UNAVAILABLE" in decision.block_reasons
    assert decision.entry_price is None


def test_intraday_v2_blocks_bad_price_location() -> None:
    decision = evaluate_intraday_decision(_payload(close=110.0))

    assert decision.entry_status == "BLOCKED"
    assert decision.reason == "BAD_PRICE_LOCATION"
    assert "BAD_PRICE_LOCATION" in decision.block_reasons


def test_intraday_v2_requires_real_positive_expectancy() -> None:
    payload = _payload()
    payload.setup_win_probability = None

    decision = evaluate_intraday_decision(payload)

    assert decision.entry_status == "NO_TRADE"
    assert decision.reason == "MISSING_EXPECTANCY"


def test_correlation_logic_differs_between_index_and_dollar() -> None:
    config = IntradayDecisionConfig()
    proxies = _proxies(_ts())

    dollar_state, dollar_score, _ = classify_correlation_state("DOLLAR", proxies, config)
    index_state, index_score, _ = classify_correlation_state("INDEX", proxies, config)

    assert dollar_state == "STRONG_LONG_BIAS"
    assert dollar_score > 0
    assert index_state == "STRONG_SHORT_BIAS"
    assert index_score < 0
