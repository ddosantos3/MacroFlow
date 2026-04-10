import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_project_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return

    project_env = PROJECT_ROOT / ".env"
    if project_env.exists():
        load_dotenv(project_env, override=False)
        return

    load_dotenv(override=False)


def _env_float(name: str) -> float | None:
    value = os.getenv(name, "").strip()
    if not value:
        return None
    return float(value.replace(",", "."))


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    return int(value) if value else default


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "sim", "on"}


def _env_str(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value if value else default


def _env_yahoo_period(name: str, default: str) -> str:
    value = _env_str(name, default).lower()
    if value.isdigit():
        return f"{value}d"
    return value


@dataclass(slots=True)
class StorageConfig:
    project_root: Path = PROJECT_ROOT
    runtime_dir: Path = PROJECT_ROOT / "data" / "runtime"
    excel_path: Path = PROJECT_ROOT / "data" / "runtime" / "MacroFlow_Dados.xlsx"
    dashboard_state_path: Path = PROJECT_ROOT / "data" / "runtime" / "dashboard_state.json"
    snapshot_history_path: Path = PROJECT_ROOT / "data" / "runtime" / "snapshots.jsonl"


@dataclass(slots=True)
class MarketConfig:
    yahoo_intraday_period: str = "60d"
    yahoo_intraday_interval: str = "60m"
    yahoo_daily_period: str = "1y"
    yahoo_daily_interval: str = "1d"
    chart_default_timeframe: str = "4H"
    rsi_period: int = 14
    macro_delta_bars: int = 5
    volume_lookback: int = 50
    strategy_ema_fast: int = 9
    strategy_ema_slow: int = 21
    score_minimo_operar: int = 65
    risco_maximo_por_operacao: float = 0.01
    capital_total_brl: float | None = None
    stop_buffer_pct: float = 0.005
    touch_tolerance_pct: float = 0.0025
    fred_serie_dxy: str = "DTWEXBGS"
    fred_serie_us10y: str = "DGS10"
    fred_api_key: str = ""


@dataclass(slots=True)
class QuantConfig:
    vwap_rolling_window: int = 20
    poc_bins: int = 24
    value_area_pct: float = 0.70
    atr_period: int = 14
    bb_period: int = 20
    bb_std: float = 2.0
    squeeze_window: int = 20
    volume_average_window: int = 20
    volume_spike_factor: float = 1.5
    adx_period: int = 14
    ema_fast: int = 8
    ema_mid: int = 21
    ema_slow: int = 80
    ema_long: int = 200
    atr_high_quantile_window: int = 60
    atr_high_quantile: float = 0.75
    risk_percent: float = 0.01
    max_risk_percent: float = 0.02
    stop_atr_multiple: float = 2.0
    target_atr_multiple: float = 3.0


@dataclass(slots=True)
class EmailConfig:
    enabled: bool = False
    host: str = "smtp.gmail.com"
    port: int = 587
    user: str = ""
    password: str = ""
    to: str = ""
    send_mode: str = "signal_or_daily"
    use_tls: bool = True


@dataclass(slots=True)
class LLMConfig:
    enabled: bool = False
    provider: str = "openai"
    api_key: str = ""
    model: str = "gpt-4.1-mini"
    timeout_seconds: int = 20


@dataclass(slots=True)
class CalendarConfig:
    enabled: bool = True
    provider: str = "forexfactory"
    api_key: str = "guest:guest"
    countries: str = "United States,Brazil,Euro Area,China"
    importance_min: int = 1
    days_back: int = 1
    days_ahead: int = 7
    timeout_seconds: int = 15
    max_events: int = 80


@dataclass(slots=True)
class JarvisConfig:
    prompt_path: Path = PROJECT_ROOT / "prompt.txt"
    max_history_messages: int = 8
    max_context_events: int = 12
    max_context_assets: int = 6


@dataclass(slots=True)
class AppSettings:
    storage: StorageConfig = field(default_factory=StorageConfig)
    market: MarketConfig = field(default_factory=MarketConfig)
    quant: QuantConfig = field(default_factory=QuantConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    calendar: CalendarConfig = field(default_factory=CalendarConfig)
    jarvis: JarvisConfig = field(default_factory=JarvisConfig)
    host: str = "127.0.0.1"
    port: int = 8000


ATIVOS_YAHOO: Dict[str, str] = {
    "USA500": "^GSPC",
    "USAIND": "^DJI",
    "NDX": "^NDX",
    "SPX": "^GSPC",
    "BRA50": "^BVSP",
    "USDBRL": "BRL=X",
}


ASSET_LABELS: Dict[str, str] = {
    "USA500": "S&P 500",
    "USAIND": "Dow Jones",
    "NDX": "Nasdaq 100",
    "SPX": "S&P 500 Spot",
    "BRA50": "Mini Índice (proxy IBOV)",
    "USDBRL": "Mini Dólar (proxy BRL=X)",
}


ASSET_DESCRIPTIONS: Dict[str, str] = {
    "USA500": "Proxy amplo de apetite ao risco nos Estados Unidos.",
    "USAIND": "Leitura industrial e direcional das blue chips americanas.",
    "NDX": "Sensibilidade maior a tecnologia, growth e liquidez global.",
    "SPX": "Ativo de referência usado na camada macro do MacroFlow.",
    "BRA50": "Proxy operacional para leitura do mini índice até feed real de WIN.",
    "USDBRL": "Proxy operacional para leitura do mini dólar até feed real de WDO.",
}


PASSOS_NIVEIS_FIXOS: Dict[str, Tuple[float, int]] = {
    "USDBRL": (0.25, 3),
    "BRA50": (250.0, 0),
}


def load_settings() -> AppSettings:
    _load_project_dotenv()
    storage = StorageConfig()
    runtime_dir = Path(_env_str("MACROFLOW_RUNTIME_DIR", str(storage.runtime_dir))).expanduser()
    storage.runtime_dir = runtime_dir
    storage.excel_path = Path(_env_str("MACROFLOW_EXCEL_PATH", str(runtime_dir / "MacroFlow_Dados.xlsx"))).expanduser()
    storage.dashboard_state_path = Path(
        _env_str("MACROFLOW_DASHBOARD_STATE_PATH", str(runtime_dir / "dashboard_state.json"))
    ).expanduser()
    storage.snapshot_history_path = Path(
        _env_str("MACROFLOW_SNAPSHOT_HISTORY_PATH", str(runtime_dir / "snapshots.jsonl"))
    ).expanduser()

    market = MarketConfig(
        yahoo_intraday_period=_env_yahoo_period("MACROFLOW_YAHOO_INTRADAY_PERIOD", "60d"),
        yahoo_intraday_interval=_env_str("MACROFLOW_YAHOO_INTRADAY_INTERVAL", "60m"),
        yahoo_daily_period=_env_yahoo_period("MACROFLOW_YAHOO_DAILY_PERIOD", "1y"),
        yahoo_daily_interval=_env_str("MACROFLOW_YAHOO_DAILY_INTERVAL", "1d"),
        chart_default_timeframe=_env_str("MACROFLOW_CHART_DEFAULT_TIMEFRAME", "4H").upper(),
        rsi_period=_env_int("MACROFLOW_RSI_PERIODO", 14),
        macro_delta_bars=_env_int("MACROFLOW_MACRO_DELTA_BARS", 5),
        volume_lookback=_env_int("MACROFLOW_VOLUME_LOOKBACK", 50),
        strategy_ema_fast=_env_int("MACROFLOW_EMA_FAST", 9),
        strategy_ema_slow=_env_int("MACROFLOW_EMA_SLOW", 21),
        score_minimo_operar=_env_int("MACROFLOW_SCORE_MINIMO_OPERAR", 65),
        risco_maximo_por_operacao=_env_float("MACROFLOW_RISCO_MAXIMO_POR_OPERACAO") or 0.01,
        capital_total_brl=_env_float("MACROFLOW_CAPITAL_TOTAL_BRL"),
        stop_buffer_pct=_env_float("MACROFLOW_STOP_BUFFER_PCT") or 0.005,
        touch_tolerance_pct=_env_float("MACROFLOW_TOUCH_TOLERANCE_PCT") or 0.0025,
        fred_serie_dxy=_env_str("MACROFLOW_FRED_DXY", "DTWEXBGS"),
        fred_serie_us10y=_env_str("MACROFLOW_FRED_US10Y", "DGS10"),
        fred_api_key=os.getenv("FRED_API_KEY", "").strip(),
    )

    quant = QuantConfig(
        vwap_rolling_window=_env_int("MACROFLOW_VWAP_ROLLING_WINDOW", 20),
        poc_bins=_env_int("MACROFLOW_POC_BINS", 24),
        value_area_pct=_env_float("MACROFLOW_VALUE_AREA_PCT") or 0.70,
        atr_period=_env_int("MACROFLOW_ATR_PERIOD", 14),
        bb_period=_env_int("MACROFLOW_BB_PERIOD", 20),
        bb_std=_env_float("MACROFLOW_BB_STD") or 2.0,
        squeeze_window=_env_int("MACROFLOW_SQUEEZE_WINDOW", 20),
        volume_average_window=_env_int("MACROFLOW_VOLUME_AVERAGE_WINDOW", 20),
        volume_spike_factor=_env_float("MACROFLOW_VOLUME_SPIKE_FACTOR") or 1.5,
        adx_period=_env_int("MACROFLOW_ADX_PERIOD", 14),
        ema_fast=_env_int("MACROFLOW_QUANT_EMA_FAST", 8),
        ema_mid=_env_int("MACROFLOW_QUANT_EMA_MID", 21),
        ema_slow=_env_int("MACROFLOW_QUANT_EMA_SLOW", 80),
        ema_long=_env_int("MACROFLOW_QUANT_EMA_LONG", 200),
        atr_high_quantile_window=_env_int("MACROFLOW_ATR_HIGH_QUANTILE_WINDOW", 60),
        atr_high_quantile=_env_float("MACROFLOW_ATR_HIGH_QUANTILE") or 0.75,
        risk_percent=_env_float("MACROFLOW_QUANT_RISK_PERCENT") or market.risco_maximo_por_operacao,
        max_risk_percent=_env_float("MACROFLOW_QUANT_MAX_RISK_PERCENT") or 0.02,
        stop_atr_multiple=_env_float("MACROFLOW_STOP_ATR_MULTIPLE") or 2.0,
        target_atr_multiple=_env_float("MACROFLOW_TARGET_ATR_MULTIPLE") or 3.0,
    )
    email = EmailConfig(
        enabled=_env_bool("EMAIL_ENABLED", False),
        host=_env_str("EMAIL_HOST", "smtp.gmail.com"),
        port=_env_int("EMAIL_PORT", 587),
        user=os.getenv("EMAIL_USER", "").strip(),
        password=os.getenv("EMAIL_PASSWORD", "").strip(),
        to=os.getenv("EMAIL_TO", "").strip(),
        send_mode=_env_str("EMAIL_SEND_MODE", "signal_or_daily"),
        use_tls=_env_bool("EMAIL_USE_TLS", True),
    )
    llm = LLMConfig(
        enabled=_env_bool("MACROFLOW_LLM_ENABLED", False),
        provider=_env_str("MACROFLOW_LLM_PROVIDER", "openai").lower(),
        api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        model=_env_str("OPENAI_MODEL", "gpt-4.1-mini"),
        timeout_seconds=_env_int("MACROFLOW_LLM_TIMEOUT_SECONDS", 20),
    )
    calendar = CalendarConfig(
        enabled=_env_bool("MACROFLOW_CALENDAR_ENABLED", True),
        provider=_env_str("MACROFLOW_CALENDAR_PROVIDER", "forexfactory").lower(),
        api_key=_env_str("TRADING_ECONOMICS_API_KEY", "guest:guest"),
        countries=_env_str("MACROFLOW_CALENDAR_COUNTRIES", "United States,Brazil,Euro Area,China"),
        importance_min=_env_int("MACROFLOW_CALENDAR_IMPORTANCE_MIN", 1),
        days_back=_env_int("MACROFLOW_CALENDAR_DAYS_BACK", 1),
        days_ahead=_env_int("MACROFLOW_CALENDAR_DAYS_AHEAD", 7),
        timeout_seconds=_env_int("MACROFLOW_CALENDAR_TIMEOUT_SECONDS", 15),
        max_events=_env_int("MACROFLOW_CALENDAR_MAX_EVENTS", 80),
    )
    jarvis_prompt_path = Path(_env_str("MACROFLOW_JARVIS_PROMPT_PATH", str(PROJECT_ROOT / "prompt.txt"))).expanduser()
    if not jarvis_prompt_path.is_absolute():
        jarvis_prompt_path = PROJECT_ROOT / jarvis_prompt_path
    jarvis = JarvisConfig(
        prompt_path=jarvis_prompt_path,
        max_history_messages=_env_int("MACROFLOW_JARVIS_MAX_HISTORY_MESSAGES", 8),
        max_context_events=_env_int("MACROFLOW_JARVIS_MAX_CONTEXT_EVENTS", 12),
        max_context_assets=_env_int("MACROFLOW_JARVIS_MAX_CONTEXT_ASSETS", 6),
    )

    return AppSettings(
        storage=storage,
        market=market,
        quant=quant,
        email=email,
        llm=llm,
        calendar=calendar,
        jarvis=jarvis,
        host=_env_str("MACROFLOW_HOST", "127.0.0.1"),
        port=_env_int("MACROFLOW_PORT", 8000),
    )
