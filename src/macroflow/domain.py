import math
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class Regime(StrEnum):
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF"
    NEUTRO = "NEUTRO"


class Direction(StrEnum):
    COMPRA = "COMPRA"
    VENDA = "VENDA"
    NEUTRO = "NEUTRO"


class ExecutionStatus(StrEnum):
    SEM_DADOS = "SEM_DADOS"
    BLOQUEADO_MACRO = "BLOQUEADO_MACRO"
    AGUARDANDO_PULLBACK = "AGUARDANDO_PULLBACK"
    AGUARDANDO_CONFIRMACAO = "AGUARDANDO_CONFIRMACAO"
    PRONTO_PARA_EXECUTAR = "PRONTO_PARA_EXECUTAR"
    EM_ACOMPANHAMENTO = "EM_ACOMPANHAMENTO"
    SAIDA_ACIONADA = "SAIDA_ACIONADA"


@dataclass(slots=True)
class SourceHealth:
    source: str
    ok: bool
    message: str
    last_updated: str | None = None
    stale: bool = False


@dataclass(slots=True)
class PositionSizing:
    capital_total: float | None
    risco_maximo_reais: float | None
    risco_por_unidade: float | None
    quantidade: float | None
    exposicao_estimada: float | None
    observacao: str


@dataclass(slots=True)
class MacroContext:
    regime: str
    score: int
    nao_operar: bool
    motivo_nao_operar: str
    dxy_fred: float
    dxy_rsi14: float
    us10y_fred: float
    us10y_delta_5d: float
    spx_delta_5x4h: float
    spx_volume_4h: float
    spx_volume_media_50: float
    dxy_us10y_divergente: bool
    volume_fraco_proxy: bool
    macro_directions: dict[str, str]
    headline: str


@dataclass(slots=True)
class StrategyDecision:
    asset: str
    label: str
    proxy_ticker: str
    macro_direction: str
    technical_direction: str
    macro_aligned: bool
    execution_status: str
    stage_reason: str
    price: float
    change_pct: float
    volume_4h: float
    pmd: float
    ema_fast: float
    ema_slow: float
    trend_cross_at: str | None
    touch_detected_at: str | None
    confirmation_at: str | None
    entry_price: float | None
    stop_price: float | None
    trailing_stop: float | None
    exit_condition: str
    fixed_levels: dict[str, float] = field(default_factory=dict)
    position_sizing: PositionSizing | None = None
    history: list[dict[str, Any]] = field(default_factory=list)
    technical_notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DashboardState:
    generated_at: str
    macro_context: MacroContext
    asset_decisions: list[StrategyDecision]
    source_health: list[SourceHealth]
    terminal_report: str
    summary: dict[str, Any] = field(default_factory=dict)
    market_overview: dict[str, Any] = field(default_factory=dict)
    market_assets: list[dict[str, Any]] = field(default_factory=list)
    news_center: dict[str, Any] = field(default_factory=dict)
    settings_panel: dict[str, Any] = field(default_factory=dict)
    quant_reports: list[dict[str, Any]] = field(default_factory=list)
    email_status: dict[str, Any] = field(default_factory=dict)


def to_plain(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_plain(item) for key, item in asdict(value).items()}
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_plain(item) for item in value]
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            return value
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value
