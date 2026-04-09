from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, AppSettings, MarketConfig, StorageConfig, load_settings


FIELD_GROUPS: list[dict[str, Any]] = [
    {
        "id": "core",
        "title": "Núcleo Operacional",
        "description": "Parâmetros que afetam o filtro macro, risco e o comportamento central do MacroFlow.",
        "fields": [
            {
                "env": "FRED_API_KEY",
                "label": "FRED API Key",
                "type": "password",
                "placeholder": "Cole sua chave do FRED",
                "help": "Usada para DXY e US10Y. Se ficar em branco, o MacroFlow trava por desenho.",
                "secret": True,
            },
            {
                "env": "MACROFLOW_CAPITAL_TOTAL_BRL",
                "label": "Capital total (R$)",
                "type": "number",
                "step": "0.01",
                "help": "Base para o sizing de risco por operação.",
            },
            {
                "env": "MACROFLOW_SCORE_MINIMO_OPERAR",
                "label": "Score mínimo para operar",
                "type": "number",
                "step": "1",
                "help": "Trava institucional mínima para liberar setup.",
            },
            {
                "env": "MACROFLOW_RISCO_MAXIMO_POR_OPERACAO",
                "label": "Risco máximo por operação",
                "type": "number",
                "step": "0.001",
                "help": "Percentual do capital aceito em uma única operação. Ex: 0.01 = 1%.",
            },
        ],
    },
    {
        "id": "indicadores",
        "title": "Indicadores Técnicos",
        "description": "Parâmetros da leitura técnica baseada em PMD, RSI e médias exponenciais.",
        "fields": [
            {
                "env": "MACROFLOW_RSI_PERIODO",
                "label": "Período do RSI",
                "type": "number",
                "step": "1",
                "help": "Define a sensibilidade do momentum.",
            },
            {
                "env": "MACROFLOW_EMA_FAST",
                "label": "MME rápida",
                "type": "number",
                "step": "1",
                "help": "Padrão atual do documento: 9 períodos sobre o PMD.",
            },
            {
                "env": "MACROFLOW_EMA_SLOW",
                "label": "MME lenta",
                "type": "number",
                "step": "1",
                "help": "Padrão atual do documento: 21 períodos sobre o PMD.",
            },
            {
                "env": "MACROFLOW_STOP_BUFFER_PCT",
                "label": "Buffer do stop",
                "type": "number",
                "step": "0.0001",
                "help": "Margem extra aplicada acima/abaixo da máxima ou mínima do candle de toque.",
            },
            {
                "env": "MACROFLOW_TOUCH_TOLERANCE_PCT",
                "label": "Tolerância do toque na MME21",
                "type": "number",
                "step": "0.0001",
                "help": "Ajuda a reconhecer toques próximos da média sem perder setups relevantes.",
            },
        ],
    },
    {
        "id": "timeframes",
        "title": "Timeframes e Coleta",
        "description": "Controla os horizontes usados na coleta dos gráficos e a visualização padrão.",
        "fields": [
            {
                "env": "MACROFLOW_YAHOO_INTRADAY_PERIOD",
                "label": "Período intraday",
                "type": "text",
                "placeholder": "60d",
                "help": "Janela histórica usada para montar candles intraday.",
            },
            {
                "env": "MACROFLOW_YAHOO_INTRADAY_INTERVAL",
                "label": "Intervalo intraday",
                "type": "text",
                "placeholder": "60m",
                "help": "Intervalo-base do Yahoo antes da reamostragem para 4H.",
            },
            {
                "env": "MACROFLOW_YAHOO_DAILY_PERIOD",
                "label": "Período diário",
                "type": "text",
                "placeholder": "1y",
                "help": "Janela histórica para a leitura do setup diário.",
            },
            {
                "env": "MACROFLOW_YAHOO_DAILY_INTERVAL",
                "label": "Intervalo diário",
                "type": "text",
                "placeholder": "1d",
                "help": "Intervalo-base da leitura diária.",
            },
            {
                "env": "MACROFLOW_CHART_DEFAULT_TIMEFRAME",
                "label": "Timeframe padrão do dashboard",
                "type": "select",
                "options": ["4H", "1D"],
                "help": "Define qual visão o dashboard abre por padrão nas abas gráficas.",
            },
            {
                "env": "MACROFLOW_MACRO_DELTA_BARS",
                "label": "Janela de delta macro",
                "type": "number",
                "step": "1",
                "help": "Quantidade de barras usadas para medir deslocamento de DXY, US10Y e SPX.",
            },
            {
                "env": "MACROFLOW_VOLUME_LOOKBACK",
                "label": "Lookback de volume",
                "type": "number",
                "step": "1",
                "help": "Janela usada para comparar o volume atual com a média recente.",
            },
        ],
    },
]


def _current_value(settings: AppSettings, env_name: str) -> str:
    mapping = {
        "FRED_API_KEY": settings.market.fred_api_key,
        "MACROFLOW_CAPITAL_TOTAL_BRL": settings.market.capital_total_brl,
        "MACROFLOW_SCORE_MINIMO_OPERAR": settings.market.score_minimo_operar,
        "MACROFLOW_RISCO_MAXIMO_POR_OPERACAO": settings.market.risco_maximo_por_operacao,
        "MACROFLOW_RSI_PERIODO": settings.market.rsi_period,
        "MACROFLOW_EMA_FAST": settings.market.strategy_ema_fast,
        "MACROFLOW_EMA_SLOW": settings.market.strategy_ema_slow,
        "MACROFLOW_STOP_BUFFER_PCT": settings.market.stop_buffer_pct,
        "MACROFLOW_TOUCH_TOLERANCE_PCT": settings.market.touch_tolerance_pct,
        "MACROFLOW_YAHOO_INTRADAY_PERIOD": settings.market.yahoo_intraday_period,
        "MACROFLOW_YAHOO_INTRADAY_INTERVAL": settings.market.yahoo_intraday_interval,
        "MACROFLOW_YAHOO_DAILY_PERIOD": settings.market.yahoo_daily_period,
        "MACROFLOW_YAHOO_DAILY_INTERVAL": settings.market.yahoo_daily_interval,
        "MACROFLOW_CHART_DEFAULT_TIMEFRAME": settings.market.chart_default_timeframe,
        "MACROFLOW_MACRO_DELTA_BARS": settings.market.macro_delta_bars,
        "MACROFLOW_VOLUME_LOOKBACK": settings.market.volume_lookback,
    }
    value = mapping.get(env_name, "")
    return "" if value is None else str(value)


def build_settings_payload(settings: AppSettings) -> dict[str, Any]:
    groups: list[dict[str, Any]] = []
    for group in FIELD_GROUPS:
        normalized_fields = []
        for field in group["fields"]:
            current = _current_value(settings, field["env"])
            normalized_fields.append(
                {
                    **field,
                    "value": "" if field.get("secret") else current,
                    "configured": bool(current) if field.get("secret") else None,
                }
            )
        groups.append(
            {
                "id": group["id"],
                "title": group["title"],
                "description": group["description"],
                "fields": normalized_fields,
            }
        )
    return {
        "groups": groups,
        "save_label": "Salvar configurações",
        "runtime_note": "As alterações são gravadas no .env local e passam a valer no próximo refresh do MacroFlow.",
        "operational_button_label": "Iniciar Macroflow",
    }


def _env_path(project_root: Path | None = None) -> Path:
    return (project_root or PROJECT_ROOT) / ".env"


def _read_env_map(project_root: Path | None = None) -> dict[str, str]:
    env_path = _env_path(project_root)
    if not env_path.exists():
        return {}
    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, raw_value = stripped.split("=", 1)
        values[key.strip()] = raw_value.strip()
    return values


def update_env_file(values: dict[str, Any], project_root: Path | None = None) -> None:
    env_path = _env_path(project_root)
    existing_lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    indexed_keys: dict[str, int] = {}
    for idx, line in enumerate(existing_lines):
        if "=" in line and not line.strip().startswith("#"):
            indexed_keys[line.split("=", 1)[0].strip()] = idx

    for key, raw_value in values.items():
        value = "" if raw_value is None else str(raw_value).strip()
        if key == "FRED_API_KEY" and value == "":
            continue
        new_line = f"{key}={value}"
        if key in indexed_keys:
            existing_lines[indexed_keys[key]] = new_line
        else:
            existing_lines.append(new_line)

    env_path.write_text("\n".join(existing_lines).rstrip() + "\n", encoding="utf-8")


def reload_settings(target: AppSettings) -> AppSettings:
    if target.storage.project_root == PROJECT_ROOT:
        fresh = load_settings()
    else:
        env_map = _read_env_map(target.storage.project_root)

        def env_str(name: str, fallback: str) -> str:
            return env_map.get(name, fallback)

        def env_int(name: str, fallback: int) -> int:
            value = env_map.get(name, "")
            return int(value) if value else fallback

        def env_float(name: str, fallback: float | None) -> float | None:
            value = env_map.get(name, "")
            return float(value.replace(",", ".")) if value else fallback

        runtime_dir = Path(env_str("MACROFLOW_RUNTIME_DIR", str(target.storage.runtime_dir)))
        fresh = AppSettings(
            storage=StorageConfig(
                project_root=target.storage.project_root,
                runtime_dir=runtime_dir,
                excel_path=Path(env_str("MACROFLOW_EXCEL_PATH", str(runtime_dir / "MacroFlow_Dados.xlsx"))),
                dashboard_state_path=Path(
                    env_str("MACROFLOW_DASHBOARD_STATE_PATH", str(runtime_dir / "dashboard_state.json"))
                ),
                snapshot_history_path=Path(
                    env_str("MACROFLOW_SNAPSHOT_HISTORY_PATH", str(runtime_dir / "snapshots.jsonl"))
                ),
            ),
            market=MarketConfig(
                yahoo_intraday_period=env_str("MACROFLOW_YAHOO_INTRADAY_PERIOD", target.market.yahoo_intraday_period),
                yahoo_intraday_interval=env_str("MACROFLOW_YAHOO_INTRADAY_INTERVAL", target.market.yahoo_intraday_interval),
                yahoo_daily_period=env_str("MACROFLOW_YAHOO_DAILY_PERIOD", target.market.yahoo_daily_period),
                yahoo_daily_interval=env_str("MACROFLOW_YAHOO_DAILY_INTERVAL", target.market.yahoo_daily_interval),
                chart_default_timeframe=env_str(
                    "MACROFLOW_CHART_DEFAULT_TIMEFRAME", target.market.chart_default_timeframe
                ).upper(),
                rsi_period=env_int("MACROFLOW_RSI_PERIODO", target.market.rsi_period),
                macro_delta_bars=env_int("MACROFLOW_MACRO_DELTA_BARS", target.market.macro_delta_bars),
                volume_lookback=env_int("MACROFLOW_VOLUME_LOOKBACK", target.market.volume_lookback),
                strategy_ema_fast=env_int("MACROFLOW_EMA_FAST", target.market.strategy_ema_fast),
                strategy_ema_slow=env_int("MACROFLOW_EMA_SLOW", target.market.strategy_ema_slow),
                score_minimo_operar=env_int("MACROFLOW_SCORE_MINIMO_OPERAR", target.market.score_minimo_operar),
                risco_maximo_por_operacao=env_float(
                    "MACROFLOW_RISCO_MAXIMO_POR_OPERACAO", target.market.risco_maximo_por_operacao
                ) or target.market.risco_maximo_por_operacao,
                capital_total_brl=env_float("MACROFLOW_CAPITAL_TOTAL_BRL", target.market.capital_total_brl),
                stop_buffer_pct=env_float("MACROFLOW_STOP_BUFFER_PCT", target.market.stop_buffer_pct)
                or target.market.stop_buffer_pct,
                touch_tolerance_pct=env_float("MACROFLOW_TOUCH_TOLERANCE_PCT", target.market.touch_tolerance_pct)
                or target.market.touch_tolerance_pct,
                fred_serie_dxy=env_str("MACROFLOW_FRED_DXY", target.market.fred_serie_dxy),
                fred_serie_us10y=env_str("MACROFLOW_FRED_US10Y", target.market.fred_serie_us10y),
                fred_api_key=env_str("FRED_API_KEY", target.market.fred_api_key),
            ),
            host=env_str("MACROFLOW_HOST", target.host),
            port=env_int("MACROFLOW_PORT", target.port),
        )
    target.storage = fresh.storage
    target.market = fresh.market
    target.host = fresh.host
    target.port = fresh.port
    return target
