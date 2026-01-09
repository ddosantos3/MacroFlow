import os
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class ConfigColetor:
    caminho_excel: str = os.path.join(os.path.expanduser("~"), "Documents", "MacroFlow_Dados.xlsx")
    periodo_yahoo: str = "60d"
    intervalo_yahoo: str = "60m"
    rsi_periodo: int = 14
    lookback_swing_barras_4h: int = 60
    fred_serie_dxy: str = "DTWEXBGS"
    fred_serie_us10y: str = "DGS10"
    score_minimo_operar: int = 65
    passo_nivel_padrao: float = 1.0
    casas_nivel_padrao: int = 2


@dataclass
class ConfigAgente:
    caminho_excel: str = os.path.join(os.path.expanduser("~"), "Documents", "MacroFlow_Dados.xlsx")
    aba_snapshots: str = "SNAPSHOTS"

    # Mapeia “ativos operacionais” para o prefixo que existe no Excel.
    # Hoje seu coletor grava USDBRL como proxy público (spot).
    # Quando você plugar WDO/WIN real, basta trocar o prefixo aqui.
    prefixo_mini_dolar: str = "usdbrl"
    prefixo_mini_indice: str = "bra50"

    # Score mínimo para operar (deve bater com a camada do coletor)
    score_minimo_operar: int = 65


ATIVOS_YAHOO: Dict[str, str] = {
    "USA500": "^GSPC",
    "USAIND": "^DJI",
    "NDX": "^NDX",
    "SPX": "^GSPC",
    "BRA50": "^BVSP",
    "USDBRL": "BRL=X",
}


PASSOS_NIVEIS_FIXOS: Dict[str, Tuple[float, int]] = {
    "USDBRL": (0.25, 3),
    "BRA50": (250.0, 0),
}
