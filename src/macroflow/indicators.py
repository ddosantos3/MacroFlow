import math
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP

import numpy as np
import pandas as pd


def calcular_rsi(series: pd.Series, periodo: int = 14) -> pd.Series:
    if series.empty:
        return pd.Series(dtype=float)
    delta = series.diff()
    ganho = delta.clip(lower=0)
    perda = -delta.clip(upper=0)
    media_ganho = ganho.ewm(alpha=1 / periodo, adjust=False).mean()
    media_perda = perda.ewm(alpha=1 / periodo, adjust=False).mean()
    rs = media_ganho / media_perda.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.bfill().clip(0, 100)


def remover_timezone_index(index: pd.Index) -> pd.Index:
    if isinstance(index, pd.DatetimeIndex) and index.tz is not None:
        return index.tz_localize(None)
    return index


def remover_timezone_series(series: pd.Series) -> pd.Series:
    dt_index = pd.DatetimeIndex(pd.to_datetime(series, errors="coerce"))
    if dt_index.tz is not None:
        dt_index = dt_index.tz_localize(None)
    return pd.Series(dt_index, index=series.index, name=series.name)


def normalizar_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    frame = df.copy()
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    required = {"Open", "High", "Low", "Close"}
    if not required.issubset(frame.columns):
        return pd.DataFrame()
    frame.index = pd.to_datetime(frame.index)
    frame.index = remover_timezone_index(frame.index)
    frame = frame.loc[:, ~frame.columns.duplicated()]
    frame = frame.dropna(subset=list(required))
    return frame.sort_index()


def resample_para_4h(df_ohlc: pd.DataFrame) -> pd.DataFrame:
    df = normalizar_ohlc(df_ohlc)
    if df.empty:
        return df
    resampled = pd.DataFrame(
        {
            "Open": df["Open"].resample("4h").first(),
            "High": df["High"].resample("4h").max(),
            "Low": df["Low"].resample("4h").min(),
            "Close": df["Close"].resample("4h").last(),
        }
    )
    if "Volume" in df.columns:
        resampled["Volume"] = df["Volume"].resample("4h").sum()
    return resampled.dropna(subset=["Open", "High", "Low", "Close"])


def preparar_frame_diario(df_diario: pd.DataFrame, ema_fast: int, ema_slow: int, touch_tolerance_pct: float) -> pd.DataFrame:
    frame = normalizar_ohlc(df_diario)
    if frame.empty:
        return frame
    frame = frame.copy()
    frame["PMD"] = (frame["High"] + frame["Low"]) / 2
    frame["EMA_FAST"] = frame["PMD"].ewm(span=ema_fast, adjust=False).mean()
    frame["EMA_SLOW"] = frame["PMD"].ewm(span=ema_slow, adjust=False).mean()
    frame["POSITIVE_CLOSE"] = (frame["Close"] > frame["Open"]) | (frame["Close"] > frame["Close"].shift(1))
    frame["NEGATIVE_CLOSE"] = (frame["Close"] < frame["Open"]) | (frame["Close"] < frame["Close"].shift(1))
    frame["TOUCH_EMA_SLOW"] = (
        ((frame["Low"] <= frame["EMA_SLOW"]) & (frame["High"] >= frame["EMA_SLOW"]))
        | (((frame["Close"] - frame["EMA_SLOW"]).abs() / frame["EMA_SLOW"]) <= touch_tolerance_pct)
        | (((frame["PMD"] - frame["EMA_SLOW"]).abs() / frame["EMA_SLOW"]) <= touch_tolerance_pct)
    )
    frame["TREND_SIGN"] = np.sign(frame["EMA_FAST"] - frame["EMA_SLOW"]).replace(0, np.nan).ffill().fillna(0)
    return frame


def calcular_variacao(df_4h: pd.DataFrame) -> tuple[float, float, float, float]:
    if df_4h.empty:
        return (float("nan"), float("nan"), float("nan"), float("nan"))
    close = df_4h["Close"]
    preco_atual = float(close.iloc[-1])
    preco_anterior = float(close.iloc[-2]) if len(close) >= 2 else preco_atual
    variacao_abs = preco_atual - preco_anterior
    variacao_pct = (variacao_abs / preco_anterior) * 100 if preco_anterior else float("nan")
    volume_4h = float(df_4h["Volume"].iloc[-1]) if "Volume" in df_4h.columns else float("nan")
    return (preco_atual, variacao_abs, variacao_pct, volume_4h)


def _quantizar_decimal(valor: Decimal, casas: int) -> Decimal:
    casas = max(casas, 0)
    escala = Decimal("1").scaleb(-casas)
    return valor.quantize(escala, rounding=ROUND_HALF_UP)


def calcular_niveis_fixos(preco_atual: float, passo: float, casas: int) -> dict[str, float]:
    if passo <= 0 or np.isnan(preco_atual):
        return {chave: float("nan") for chave in ["nivel_0", "nivel_25", "nivel_50", "nivel_75", "nivel_100"]}
    p = Decimal(str(passo))
    faixa = p * 4
    x = Decimal(str(preco_atual))
    base = (x / faixa).to_integral_value(rounding=ROUND_FLOOR) * faixa
    base = _quantizar_decimal(base, casas)
    return {
        "nivel_0": float(base),
        "nivel_25": float(base + _quantizar_decimal(p, casas)),
        "nivel_50": float(base + _quantizar_decimal(p * 2, casas)),
        "nivel_75": float(base + _quantizar_decimal(p * 3, casas)),
        "nivel_100": float(base + _quantizar_decimal(p * 4, casas)),
    }


def ultimo_valor(series: pd.Series) -> float:
    return float(series.iloc[-1]) if series is not None and len(series) > 0 else float("nan")


def candle_history(frame: pd.DataFrame, limit: int = 90) -> list[dict[str, object]]:
    if frame.empty:
        return []
    data = []
    for timestamp, row in frame.tail(limit).iterrows():
        data.append(
            {
                "timestamp": timestamp.strftime("%Y-%m-%d"),
                "close": float(row["Close"]),
                "ema_fast": float(row.get("EMA_FAST", float("nan"))),
                "ema_slow": float(row.get("EMA_SLOW", float("nan"))),
                "pmd": float(row.get("PMD", float("nan"))),
            }
        )
    return data


def formatar_numero(valor: float | None, casas: int = 4) -> str:
    if valor is None:
        return "-"
    if isinstance(valor, float) and math.isnan(valor):
        return "-"
    return f"{valor:.{casas}f}".rstrip("0").rstrip(".")
