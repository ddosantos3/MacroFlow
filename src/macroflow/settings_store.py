from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import EmailConfig, LLMConfig, PROJECT_ROOT, AppSettings, MarketConfig, QuantConfig, StorageConfig, load_settings


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
    {
        "id": "quant",
        "title": "Motor Quantitativo",
        "description": "Parametros de VWAP, POC, volatilidade, volume, tendencia, score e risco por ATR.",
        "fields": [
            {"env": "MACROFLOW_VWAP_ROLLING_WINDOW", "label": "Janela VWAP rolling", "type": "number", "step": "1", "help": "Janela usada no VWAP rolling."},
            {"env": "MACROFLOW_POC_BINS", "label": "Faixas do POC", "type": "number", "step": "1", "help": "Quantidade de buckets da distribuicao de volume por preco."},
            {"env": "MACROFLOW_VALUE_AREA_PCT", "label": "Value area (%)", "type": "number", "step": "0.01", "help": "Percentual de volume usado para VAH/VAL. Ex: 0.70."},
            {"env": "MACROFLOW_ATR_PERIOD", "label": "Periodo ATR", "type": "number", "step": "1", "help": "Janela do ATR usado na gestao de risco."},
            {"env": "MACROFLOW_BB_PERIOD", "label": "Periodo Bollinger", "type": "number", "step": "1", "help": "Janela das Bandas de Bollinger."},
            {"env": "MACROFLOW_BB_STD", "label": "Desvio Bollinger", "type": "number", "step": "0.1", "help": "Multiplicador de desvio padrao das bandas."},
            {"env": "MACROFLOW_VOLUME_AVERAGE_WINDOW", "label": "Media de volume", "type": "number", "step": "1", "help": "Janela de media de volume para detectar spike."},
            {"env": "MACROFLOW_VOLUME_SPIKE_FACTOR", "label": "Fator volume spike", "type": "number", "step": "0.1", "help": "Volume atual precisa superar media x fator."},
            {"env": "MACROFLOW_ADX_PERIOD", "label": "Periodo ADX", "type": "number", "step": "1", "help": "Janela do ADX para classificar tendencia."},
            {"env": "MACROFLOW_SQUEEZE_WINDOW", "label": "Janela squeeze", "type": "number", "step": "1", "help": "Janela para detectar compressao de volatilidade."},
            {"env": "MACROFLOW_QUANT_EMA_FAST", "label": "EMA quant curta", "type": "number", "step": "1", "help": "Media curta da camada quant. Padrao: 8."},
            {"env": "MACROFLOW_QUANT_EMA_MID", "label": "EMA quant media", "type": "number", "step": "1", "help": "Media de referencia para tendencia. Padrao: 21."},
            {"env": "MACROFLOW_QUANT_EMA_SLOW", "label": "EMA quant lenta", "type": "number", "step": "1", "help": "Media estrutural para regime. Padrao: 80."},
            {"env": "MACROFLOW_QUANT_EMA_LONG", "label": "EMA quant longa", "type": "number", "step": "1", "help": "Media longa de contexto. Padrao: 200."},
            {"env": "MACROFLOW_QUANT_RISK_PERCENT", "label": "Risco quant por operacao", "type": "number", "step": "0.001", "help": "Risco por trade no motor quant. Maximo efetivo: 0.02."},
            {"env": "MACROFLOW_QUANT_MAX_RISK_PERCENT", "label": "Teto de risco quant", "type": "number", "step": "0.001", "help": "Teto configuravel. O codigo ainda limita a 0.02 por seguranca."},
            {"env": "MACROFLOW_STOP_ATR_MULTIPLE", "label": "Stop em ATR", "type": "number", "step": "0.1", "help": "Multiplicador de ATR para o stop."},
            {"env": "MACROFLOW_TARGET_ATR_MULTIPLE", "label": "Alvo em ATR", "type": "number", "step": "0.1", "help": "Multiplicador de ATR para o alvo."},
        ],
    },
    {
        "id": "alertas",
        "title": "Alertas e LLM",
        "description": "Envio automatico de e-mail e camada explicativa do LLM, sem alterar a decisao deterministica.",
        "fields": [
            {"env": "EMAIL_ENABLED", "label": "Habilitar e-mail", "type": "select", "options": ["false", "true"], "help": "Ativa envio quando houver sinal novo ou relatorio diario."},
            {"env": "EMAIL_HOST", "label": "SMTP host", "type": "text", "placeholder": "smtp.gmail.com", "help": "Servidor SMTP usado para envio."},
            {"env": "EMAIL_PORT", "label": "SMTP porta", "type": "number", "step": "1", "help": "Porta SMTP. Gmail normalmente usa 587."},
            {"env": "EMAIL_USER", "label": "E-mail usuario", "type": "text", "help": "Conta usada como remetente."},
            {"env": "EMAIL_PASSWORD", "label": "Senha/token SMTP", "type": "password", "help": "Senha de app ou token SMTP.", "secret": True},
            {"env": "EMAIL_TO", "label": "Destinatario", "type": "text", "help": "E-mail que recebera os relatorios."},
            {"env": "EMAIL_SEND_MODE", "label": "Modo de envio", "type": "select", "options": ["signal_or_daily", "signal", "daily"], "help": "Define o gatilho de envio automatico."},
            {"env": "EMAIL_USE_TLS", "label": "Usar TLS", "type": "select", "options": ["true", "false"], "help": "Mantem STARTTLS ativo por padrao."},
            {"env": "MACROFLOW_LLM_ENABLED", "label": "Habilitar LLM", "type": "select", "options": ["false", "true"], "help": "Quando falso, usa explicacao local deterministica."},
            {"env": "MACROFLOW_LLM_PROVIDER", "label": "Provider LLM", "type": "text", "placeholder": "openai", "help": "Provider da camada explicativa. Hoje: openai."},
            {"env": "OPENAI_API_KEY", "label": "OpenAI API Key", "type": "password", "help": "Usada apenas para explicacao textual, nunca para decidir trade.", "secret": True},
            {"env": "OPENAI_MODEL", "label": "Modelo OpenAI", "type": "text", "placeholder": "gpt-4.1-mini", "help": "Modelo usado na camada explicativa."},
            {"env": "MACROFLOW_LLM_TIMEOUT_SECONDS", "label": "Timeout LLM", "type": "number", "step": "1", "help": "Timeout da chamada HTTP ao LLM."},
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
        "MACROFLOW_VWAP_ROLLING_WINDOW": settings.quant.vwap_rolling_window,
        "MACROFLOW_POC_BINS": settings.quant.poc_bins,
        "MACROFLOW_VALUE_AREA_PCT": settings.quant.value_area_pct,
        "MACROFLOW_ATR_PERIOD": settings.quant.atr_period,
        "MACROFLOW_BB_PERIOD": settings.quant.bb_period,
        "MACROFLOW_BB_STD": settings.quant.bb_std,
        "MACROFLOW_VOLUME_AVERAGE_WINDOW": settings.quant.volume_average_window,
        "MACROFLOW_VOLUME_SPIKE_FACTOR": settings.quant.volume_spike_factor,
        "MACROFLOW_ADX_PERIOD": settings.quant.adx_period,
        "MACROFLOW_SQUEEZE_WINDOW": settings.quant.squeeze_window,
        "MACROFLOW_QUANT_EMA_FAST": settings.quant.ema_fast,
        "MACROFLOW_QUANT_EMA_MID": settings.quant.ema_mid,
        "MACROFLOW_QUANT_EMA_SLOW": settings.quant.ema_slow,
        "MACROFLOW_QUANT_EMA_LONG": settings.quant.ema_long,
        "MACROFLOW_QUANT_RISK_PERCENT": settings.quant.risk_percent,
        "MACROFLOW_QUANT_MAX_RISK_PERCENT": settings.quant.max_risk_percent,
        "MACROFLOW_STOP_ATR_MULTIPLE": settings.quant.stop_atr_multiple,
        "MACROFLOW_TARGET_ATR_MULTIPLE": settings.quant.target_atr_multiple,
        "EMAIL_ENABLED": str(settings.email.enabled).lower(),
        "EMAIL_HOST": settings.email.host,
        "EMAIL_PORT": settings.email.port,
        "EMAIL_USER": settings.email.user,
        "EMAIL_PASSWORD": settings.email.password,
        "EMAIL_TO": settings.email.to,
        "EMAIL_SEND_MODE": settings.email.send_mode,
        "EMAIL_USE_TLS": str(settings.email.use_tls).lower(),
        "MACROFLOW_LLM_ENABLED": str(settings.llm.enabled).lower(),
        "MACROFLOW_LLM_PROVIDER": settings.llm.provider,
        "OPENAI_API_KEY": settings.llm.api_key,
        "OPENAI_MODEL": settings.llm.model,
        "MACROFLOW_LLM_TIMEOUT_SECONDS": settings.llm.timeout_seconds,
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
    secret_keys = {"FRED_API_KEY", "EMAIL_PASSWORD", "OPENAI_API_KEY"}
    for idx, line in enumerate(existing_lines):
        if "=" in line and not line.strip().startswith("#"):
            indexed_keys[line.split("=", 1)[0].strip()] = idx

    for key, raw_value in values.items():
        value = "" if raw_value is None else str(raw_value).strip()
        if key in secret_keys and value == "":
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

        def env_bool(name: str, fallback: bool) -> bool:
            value = env_map.get(name, "").strip().lower()
            if not value:
                return fallback
            return value in {"1", "true", "yes", "sim", "on"}

        def env_yahoo_period(name: str, fallback: str) -> str:
            value = env_str(name, fallback).lower()
            if value.isdigit():
                return f"{value}d"
            return value

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
                yahoo_intraday_period=env_yahoo_period("MACROFLOW_YAHOO_INTRADAY_PERIOD", target.market.yahoo_intraday_period),
                yahoo_intraday_interval=env_str("MACROFLOW_YAHOO_INTRADAY_INTERVAL", target.market.yahoo_intraday_interval),
                yahoo_daily_period=env_yahoo_period("MACROFLOW_YAHOO_DAILY_PERIOD", target.market.yahoo_daily_period),
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
            quant=QuantConfig(
                vwap_rolling_window=env_int("MACROFLOW_VWAP_ROLLING_WINDOW", target.quant.vwap_rolling_window),
                poc_bins=env_int("MACROFLOW_POC_BINS", target.quant.poc_bins),
                value_area_pct=env_float("MACROFLOW_VALUE_AREA_PCT", target.quant.value_area_pct) or target.quant.value_area_pct,
                atr_period=env_int("MACROFLOW_ATR_PERIOD", target.quant.atr_period),
                bb_period=env_int("MACROFLOW_BB_PERIOD", target.quant.bb_period),
                bb_std=env_float("MACROFLOW_BB_STD", target.quant.bb_std) or target.quant.bb_std,
                volume_average_window=env_int(
                    "MACROFLOW_VOLUME_AVERAGE_WINDOW", target.quant.volume_average_window
                ),
                volume_spike_factor=env_float(
                    "MACROFLOW_VOLUME_SPIKE_FACTOR", target.quant.volume_spike_factor
                )
                or target.quant.volume_spike_factor,
                adx_period=env_int("MACROFLOW_ADX_PERIOD", target.quant.adx_period),
                squeeze_window=env_int("MACROFLOW_SQUEEZE_WINDOW", target.quant.squeeze_window),
                ema_fast=env_int("MACROFLOW_QUANT_EMA_FAST", target.quant.ema_fast),
                ema_mid=env_int("MACROFLOW_QUANT_EMA_MID", target.quant.ema_mid),
                ema_slow=env_int("MACROFLOW_QUANT_EMA_SLOW", target.quant.ema_slow),
                ema_long=env_int("MACROFLOW_QUANT_EMA_LONG", target.quant.ema_long),
                risk_percent=env_float("MACROFLOW_QUANT_RISK_PERCENT", target.quant.risk_percent)
                or target.quant.risk_percent,
                max_risk_percent=env_float("MACROFLOW_QUANT_MAX_RISK_PERCENT", target.quant.max_risk_percent)
                or target.quant.max_risk_percent,
                stop_atr_multiple=env_float("MACROFLOW_STOP_ATR_MULTIPLE", target.quant.stop_atr_multiple)
                or target.quant.stop_atr_multiple,
                target_atr_multiple=env_float("MACROFLOW_TARGET_ATR_MULTIPLE", target.quant.target_atr_multiple)
                or target.quant.target_atr_multiple,
            ),
            email=EmailConfig(
                enabled=env_bool("EMAIL_ENABLED", target.email.enabled),
                host=env_str("EMAIL_HOST", target.email.host),
                port=env_int("EMAIL_PORT", target.email.port),
                user=env_str("EMAIL_USER", target.email.user),
                password=env_str("EMAIL_PASSWORD", target.email.password),
                to=env_str("EMAIL_TO", target.email.to),
                send_mode=env_str("EMAIL_SEND_MODE", target.email.send_mode),
                use_tls=env_bool("EMAIL_USE_TLS", target.email.use_tls),
            ),
            llm=LLMConfig(
                enabled=env_bool("MACROFLOW_LLM_ENABLED", target.llm.enabled),
                provider=env_str("MACROFLOW_LLM_PROVIDER", target.llm.provider),
                api_key=env_str("OPENAI_API_KEY", target.llm.api_key),
                model=env_str("OPENAI_MODEL", target.llm.model),
                timeout_seconds=env_int("MACROFLOW_LLM_TIMEOUT_SECONDS", target.llm.timeout_seconds),
            ),
            host=env_str("MACROFLOW_HOST", target.host),
            port=env_int("MACROFLOW_PORT", target.port),
        )
    target.storage = fresh.storage
    target.market = fresh.market
    target.quant = fresh.quant
    target.email = fresh.email
    target.llm = fresh.llm
    target.host = fresh.host
    target.port = fresh.port
    return target
