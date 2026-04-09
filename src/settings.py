from dataclasses import dataclass

from src.macroflow.config import ATIVOS_YAHOO, PASSOS_NIVEIS_FIXOS, load_settings


_settings = load_settings()


@dataclass
class ConfigColetor:
    caminho_excel: str = str(_settings.storage.excel_path)
    periodo_yahoo: str = _settings.market.yahoo_intraday_period
    intervalo_yahoo: str = _settings.market.yahoo_intraday_interval
    rsi_periodo: int = _settings.market.rsi_period
    lookback_swing_barras_4h: int = _settings.market.volume_lookback
    fred_serie_dxy: str = _settings.market.fred_serie_dxy
    fred_serie_us10y: str = _settings.market.fred_serie_us10y
    score_minimo_operar: int = _settings.market.score_minimo_operar
    passo_nivel_padrao: float = 1.0
    casas_nivel_padrao: int = 2


@dataclass
class ConfigAgente:
    caminho_excel: str = str(_settings.storage.excel_path)
    aba_snapshots: str = "SNAPSHOTS"
    prefixo_mini_dolar: str = "usdbrl"
    prefixo_mini_indice: str = "bra50"
    score_minimo_operar: int = _settings.market.score_minimo_operar
