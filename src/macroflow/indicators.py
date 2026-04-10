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
    frame["RSI"] = calcular_rsi(frame["Close"], 14)
    frame["POSITIVE_CLOSE"] = (frame["Close"] > frame["Open"]) | (frame["Close"] > frame["Close"].shift(1))
    frame["NEGATIVE_CLOSE"] = (frame["Close"] < frame["Open"]) | (frame["Close"] < frame["Close"].shift(1))
    frame["TOUCH_EMA_SLOW"] = (
        ((frame["Low"] <= frame["EMA_SLOW"]) & (frame["High"] >= frame["EMA_SLOW"]))
        | (((frame["Close"] - frame["EMA_SLOW"]).abs() / frame["EMA_SLOW"]) <= touch_tolerance_pct)
        | (((frame["PMD"] - frame["EMA_SLOW"]).abs() / frame["EMA_SLOW"]) <= touch_tolerance_pct)
    )
    frame["TREND_SIGN"] = np.sign(frame["EMA_FAST"] - frame["EMA_SLOW"]).replace(0, np.nan).ffill().fillna(0)
    return frame


def preco_tipico(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=float)
    return (frame["High"] + frame["Low"] + frame["Close"]) / 3


def calcular_vwap_intraday(frame: pd.DataFrame) -> pd.Series:
    frame = normalizar_ohlc(frame)
    if frame.empty or "Volume" not in frame.columns:
        return pd.Series(dtype=float, index=frame.index)
    volume = frame["Volume"].astype(float).clip(lower=0)
    price_volume = preco_tipico(frame) * volume
    if isinstance(frame.index, pd.DatetimeIndex):
        session = frame.index.normalize()
        acumulado_volume = volume.groupby(session).cumsum().replace(0, np.nan)
        acumulado_price_volume = price_volume.groupby(session).cumsum()
        return acumulado_price_volume / acumulado_volume
    acumulado_volume = volume.cumsum().replace(0, np.nan)
    return price_volume.cumsum() / acumulado_volume


def calcular_vwap_rolling(frame: pd.DataFrame, janela: int = 20) -> pd.Series:
    frame = normalizar_ohlc(frame)
    if frame.empty or "Volume" not in frame.columns:
        return pd.Series(dtype=float, index=frame.index)
    janela = max(int(janela), 1)
    volume = frame["Volume"].astype(float).clip(lower=0)
    volume_rolling = volume.rolling(janela, min_periods=1).sum().replace(0, np.nan)
    pv_rolling = (preco_tipico(frame) * volume).rolling(janela, min_periods=1).sum()
    return pv_rolling / volume_rolling


def calcular_poc(frame: pd.DataFrame, bins: int = 24, value_area_pct: float = 0.70) -> dict[str, float]:
    frame = normalizar_ohlc(frame)
    if frame.empty or "Volume" not in frame.columns:
        return {"poc": float("nan"), "vah": float("nan"), "val": float("nan")}

    price = preco_tipico(frame).dropna()
    volume = frame.loc[price.index, "Volume"].astype(float).clip(lower=0)
    valid = price.notna() & volume.notna() & (volume > 0)
    price = price[valid]
    volume = volume[valid]
    if price.empty or volume.sum() <= 0:
        return {"poc": float("nan"), "vah": float("nan"), "val": float("nan")}

    min_price = float(price.min())
    max_price = float(price.max())
    if min_price == max_price:
        return {"poc": min_price, "vah": min_price, "val": min_price}

    bins = max(int(bins), 1)
    edges = np.linspace(min_price, max_price, bins + 1)
    bucket = pd.cut(price, bins=edges, include_lowest=True)
    volume_profile = volume.groupby(bucket, observed=True).sum()
    if volume_profile.empty:
        return {"poc": float("nan"), "vah": float("nan"), "val": float("nan")}

    poc_interval = volume_profile.idxmax()
    poc = float((poc_interval.left + poc_interval.right) / 2)
    target_volume = float(volume_profile.sum()) * min(max(float(value_area_pct), 0.0), 1.0)
    selected = volume_profile.sort_values(ascending=False)
    accumulated = 0.0
    intervals = []
    for interval, vol in selected.items():
        intervals.append(interval)
        accumulated += float(vol)
        if accumulated >= target_volume:
            break
    vah = float(max(interval.right for interval in intervals)) if intervals else float("nan")
    val = float(min(interval.left for interval in intervals)) if intervals else float("nan")
    return {"poc": poc, "vah": vah, "val": val}


def calcular_atr(frame: pd.DataFrame, periodo: int = 14) -> pd.Series:
    frame = normalizar_ohlc(frame)
    if frame.empty:
        return pd.Series(dtype=float, index=frame.index)
    periodo = max(int(periodo), 1)
    previous_close = frame["Close"].shift(1)
    true_range = pd.concat(
        [
            frame["High"] - frame["Low"],
            (frame["High"] - previous_close).abs(),
            (frame["Low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / periodo, adjust=False, min_periods=periodo).mean()


def calcular_bollinger_bands(
    series: pd.Series,
    periodo: int = 20,
    desvio_padrao: float = 2.0,
) -> pd.DataFrame:
    if series.empty:
        return pd.DataFrame(index=series.index, columns=["BB_MIDDLE", "BB_UPPER", "BB_LOWER", "BB_BANDWIDTH"])
    periodo = max(int(periodo), 1)
    middle = series.rolling(periodo, min_periods=periodo).mean()
    rolling_std = series.rolling(periodo, min_periods=periodo).std(ddof=0)
    upper = middle + (rolling_std * desvio_padrao)
    lower = middle - (rolling_std * desvio_padrao)
    bandwidth = (upper - lower) / middle.replace(0, np.nan)
    return pd.DataFrame(
        {
            "BB_MIDDLE": middle,
            "BB_UPPER": upper,
            "BB_LOWER": lower,
            "BB_BANDWIDTH": bandwidth,
        },
        index=series.index,
    )


def detectar_squeeze(bandwidth: pd.Series, janela: int = 20) -> pd.Series:
    if bandwidth.empty:
        return pd.Series(dtype=bool, index=bandwidth.index)
    janela = max(int(janela), 1)
    threshold = bandwidth.rolling(janela, min_periods=janela).quantile(0.20)
    return (bandwidth <= threshold).fillna(False)


def calcular_obv(frame: pd.DataFrame) -> pd.Series:
    frame = normalizar_ohlc(frame)
    if frame.empty or "Volume" not in frame.columns:
        return pd.Series(dtype=float, index=frame.index)
    direction = np.sign(frame["Close"].diff()).fillna(0)
    return (direction * frame["Volume"].astype(float).fillna(0)).cumsum()


def calcular_volume_media(frame: pd.DataFrame, janela: int = 20) -> pd.Series:
    frame = normalizar_ohlc(frame)
    if frame.empty or "Volume" not in frame.columns:
        return pd.Series(dtype=float, index=frame.index)
    janela = max(int(janela), 1)
    return frame["Volume"].astype(float).rolling(janela, min_periods=1).mean()


def detectar_volume_spike(volume: pd.Series, media_volume: pd.Series, fator: float = 1.5) -> pd.Series:
    if volume.empty or media_volume.empty:
        return pd.Series(dtype=bool, index=volume.index)
    fator = max(float(fator), 0.0)
    return (volume.astype(float) > (media_volume.astype(float) * fator)).fillna(False)


def calcular_adx(frame: pd.DataFrame, periodo: int = 14) -> pd.Series:
    frame = normalizar_ohlc(frame)
    if frame.empty:
        return pd.Series(dtype=float, index=frame.index)
    periodo = max(int(periodo), 1)
    high = frame["High"].astype(float)
    low = frame["Low"].astype(float)

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
        index=frame.index,
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
        index=frame.index,
    )
    atr = calcular_atr(frame, periodo=periodo).replace(0, np.nan)
    plus_di = 100 * plus_dm.ewm(alpha=1 / periodo, adjust=False, min_periods=periodo).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / periodo, adjust=False, min_periods=periodo).mean() / atr
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)).clip(0, 100)
    return dx.ewm(alpha=1 / periodo, adjust=False, min_periods=periodo).mean()


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


def serialize_ohlc(frame: pd.DataFrame, limit: int = 80) -> list[dict[str, object]]:
    if frame.empty:
        return []
    candles = []
    for timestamp, row in frame.tail(limit).iterrows():
        candles.append(
            {
                "timestamp": pd.Timestamp(timestamp).strftime("%Y-%m-%d %H:%M"),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": float(row["Volume"]) if "Volume" in row and pd.notna(row["Volume"]) else None,
            }
        )
    return candles


def serialize_indicator_frame(frame: pd.DataFrame, limit: int = 120) -> list[dict[str, object]]:
    if frame.empty:
        return []
    points = []
    for timestamp, row in frame.tail(limit).iterrows():
        points.append(
            {
                "timestamp": pd.Timestamp(timestamp).strftime("%Y-%m-%d"),
                "close": float(row["Close"]),
                "pmd": float(row["PMD"]) if "PMD" in row and pd.notna(row["PMD"]) else None,
                "ema_fast": float(row["EMA_FAST"]) if "EMA_FAST" in row and pd.notna(row["EMA_FAST"]) else None,
                "ema_slow": float(row["EMA_SLOW"]) if "EMA_SLOW" in row and pd.notna(row["EMA_SLOW"]) else None,
                "rsi": float(row["RSI"]) if "RSI" in row and pd.notna(row["RSI"]) else None,
            }
        )
    return points


def formatar_numero(valor: float | None, casas: int = 4) -> str:
    if valor is None:
        return "-"
    if isinstance(valor, float) and math.isnan(valor):
        return "-"
    return f"{valor:.{casas}f}".rstrip("0").rstrip(".")
