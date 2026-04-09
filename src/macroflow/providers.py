import logging
import time
from datetime import datetime

import pandas as pd
import yfinance as yf
from fredapi import Fred

from .indicators import normalizar_ohlc


logger = logging.getLogger("macroflow.providers")


def baixar_yahoo(ticker: str, periodo: str, intervalo: str) -> pd.DataFrame:
    for tentativa in range(1, 4):
        try:
            df = yf.download(
                ticker,
                period=periodo,
                interval=intervalo,
                auto_adjust=False,
                progress=False,
                threads=False,
            )
            frame = normalizar_ohlc(df)
            if frame.empty:
                return pd.DataFrame()
            return frame
        except Exception as exc:
            logger.warning("Falha ao baixar %s no Yahoo (tentativa %s): %s", ticker, tentativa, exc)
            if tentativa == 3:
                return pd.DataFrame()
            time.sleep(1.5 * tentativa)
    return pd.DataFrame()


def baixar_fred_series(api_key: str, serie: str, ultimos_dias: int = 365) -> pd.Series:
    if not api_key:
        return pd.Series(dtype=float)
    try:
        fred = Fred(api_key=api_key)
        series = pd.Series(fred.get_series(serie)).dropna()
    except Exception as exc:
        logger.warning("Falha ao baixar %s no FRED: %s", serie, exc)
        return pd.Series(dtype=float)
    series.index = pd.to_datetime(series.index)
    if len(series) > ultimos_dias:
        series = series.iloc[-ultimos_dias:]
    return series


def data_mais_recente(df: pd.DataFrame | pd.Series) -> str | None:
    if df is None or len(df) == 0:
        return None
    index = pd.to_datetime(df.index)
    return index[-1].to_pydatetime().strftime("%Y-%m-%d %H:%M:%S")


def timestamp_local() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
