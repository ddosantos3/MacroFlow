import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _env_float(name: str) -> float | None:
    value = os.getenv(name, "").strip()
    if not value:
        return None
    return float(value.replace(",", "."))


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    return int(value) if value else default


def _env_str(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value if value else default


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
class AppSettings:
    storage: StorageConfig = field(default_factory=StorageConfig)
    market: MarketConfig = field(default_factory=MarketConfig)
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
    "USDBRL": "Mini Dólar (proxy BRL=X)",
    "BRA50": "Mini Índice (proxy IBOV)",
}


PASSOS_NIVEIS_FIXOS: Dict[str, Tuple[float, int]] = {
    "USDBRL": (0.25, 3),
    "BRA50": (250.0, 0),
}


def load_settings() -> AppSettings:
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
        yahoo_intraday_period=_env_str("MACROFLOW_YAHOO_INTRADAY_PERIOD", "60d"),
        yahoo_intraday_interval=_env_str("MACROFLOW_YAHOO_INTRADAY_INTERVAL", "60m"),
        yahoo_daily_period=_env_str("MACROFLOW_YAHOO_DAILY_PERIOD", "1y"),
        yahoo_daily_interval=_env_str("MACROFLOW_YAHOO_DAILY_INTERVAL", "1d"),
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

    return AppSettings(
        storage=storage,
        market=market,
        host=_env_str("MACROFLOW_HOST", "127.0.0.1"),
        port=_env_int("MACROFLOW_PORT", 8000),
    )
