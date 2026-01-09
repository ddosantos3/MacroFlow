import os
import time
import math
import argparse
from datetime import datetime
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf
from fredapi import Fred

from src.settings import ConfigColetor, ATIVOS_YAHOO, PASSOS_NIVEIS_FIXOS

# =========================================================
# MacroFlow Coletor – salva dados macro + proxies em Excel
# =========================================================
# Fontes:
# - FRED: DXY proxy (DTWEXBGS) e US10Y (DGS10)
# - Yahoo Finance (yfinance): SPX, NDX, DJI, IBOV, USDBRL (proxies)
#
# Saída:
# - Excel: SNAPSHOTS (linha por execução) + OHLC_<ATIVO> (4h reamostrado)
#
# Observação:
# - WIN/WDO (B3 futuros) em tempo real exige fonte paga (corretora/Nelogica).
#   Este coletor já deixa o pipeline pronto para plugar esse provider depois.
# =========================================================



def calcular_rsi(series: pd.Series, periodo: int = 14) -> pd.Series:
    delta = series.diff()
    ganho = delta.clip(lower=0)
    perda = -delta.clip(upper=0)
    media_ganho = ganho.ewm(alpha=1 / periodo, adjust=False).mean()
    media_perda = perda.ewm(alpha=1 / periodo, adjust=False).mean()
    rs = media_ganho / (media_perda.replace(0, np.nan))
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


def resample_para_4h(df_ohlc: pd.DataFrame) -> pd.DataFrame:
    if df_ohlc.empty:
        return df_ohlc
    df = df_ohlc.copy()
    df.index = pd.to_datetime(df.index)
    df.index = remover_timezone_index(df.index)
    required_cols = ["Open", "High", "Low", "Close"]
    if not set(required_cols).issubset(df.columns):
        return pd.DataFrame()
    resampled = pd.DataFrame({
        "Open": df["Open"].resample("4h").first(),
        "High": df["High"].resample("4h").max(),
        "Low": df["Low"].resample("4h").min(),
        "Close": df["Close"].resample("4h").last(),
    })
    if "Volume" in df.columns:
        resampled["Volume"] = df["Volume"].resample("4h").sum()
    return resampled.dropna(subset=required_cols)


def encontrar_swing_ultimos(df_4h: pd.DataFrame, lookback: int) -> Optional[Tuple[float, float]]:
    if df_4h.empty or len(df_4h) < 5:
        return None
    janela = df_4h.tail(lookback)
    maximo = float(janela["High"].max())
    minimo = float(janela["Low"].min())
    if math.isclose(maximo, minimo):
        return None
    return minimo, maximo


def calcular_niveis_percentuais(minimo: float, maximo: float) -> Dict[str, float]:
    rng = maximo - minimo
    return {
        "nivel_0": minimo,
        "nivel_25": minimo + 0.25 * rng,
        "nivel_50": minimo + 0.50 * rng,
        "nivel_75": minimo + 0.75 * rng,
        "nivel_100": maximo,
    }


def calcular_niveis_fixos(preco_atual: float, passo: float) -> Dict[str, float]:
    return calcular_niveis_fixos_com_casas(preco_atual, passo, 0)


def _quantizar_decimal(valor: Decimal, casas: int) -> Decimal:
    if casas < 0:
        casas = 0
    escala = Decimal("1").scaleb(-casas)
    return valor.quantize(escala, rounding=ROUND_HALF_UP)


def calcular_niveis_fixos_com_casas(preco_atual: float, passo: float, casas: int) -> Dict[str, float]:
    if passo <= 0 or np.isnan(preco_atual):
        return {k: np.nan for k in ["nivel_0", "nivel_25", "nivel_50", "nivel_75", "nivel_100"]}
    p = Decimal(str(passo))
    faixa = p * 4
    x = Decimal(str(preco_atual))
    base = (x / faixa).to_integral_value(rounding=ROUND_FLOOR) * faixa
    base = _quantizar_decimal(base, casas)
    p_q = _quantizar_decimal(p, casas)
    fator = _quantizar_decimal(p * 2, casas)
    tres_quartos = _quantizar_decimal(p * 3, casas)
    faixa_q = _quantizar_decimal(p * 4, casas)
    return {
        "nivel_0": float(base),
        "nivel_25": float(base + p_q),
        "nivel_50": float(base + fator),
        "nivel_75": float(base + tres_quartos),
        "nivel_100": float(base + faixa_q),
    }


def formatar_preco(valor: float, casas: int) -> str:
    if np.isnan(valor):
        return "nan"
    return f"{valor:.{casas}f}"


def obter_cfg_niveis_fixos(nome: str, cfg: ConfigColetor) -> Tuple[float, int]:
    return PASSOS_NIVEIS_FIXOS.get(nome, (cfg.passo_nivel_padrao, cfg.casas_nivel_padrao))


def ultimo_valor(series: pd.Series) -> float:
    return float(series.iloc[-1]) if series is not None and len(series) > 0 else np.nan


def log_status(icone: str, mensagem: str) -> None:
    print(f"{icone} {mensagem}")


def calcular_variacao(df_4h: pd.DataFrame) -> Tuple[float, float, float, float]:
    if df_4h.empty:
        return (np.nan, np.nan, np.nan, np.nan)
    close = df_4h["Close"]
    preco_atual = float(close.iloc[-1])
    preco_anterior = float(close.iloc[-2]) if len(close) >= 2 else preco_atual
    variacao_abs = preco_atual - preco_anterior
    variacao_pct = (variacao_abs / preco_anterior) * 100 if preco_anterior != 0 else np.nan
    volume_4h = float(df_4h["Volume"].iloc[-1]) if "Volume" in df_4h.columns else np.nan
    return (preco_atual, variacao_abs, variacao_pct, volume_4h)


def calcular_score_regime(dxy_rsi: float, us10y_delta: float, spx_delta: float) -> Tuple[str, int]:
    score_delta = 0
    if dxy_rsi >= 55:
        score_delta += 30
    elif dxy_rsi <= 45:
        score_delta -= 20

    if us10y_delta > 0:
        score_delta += 30
    elif us10y_delta < 0:
        score_delta -= 15

    if spx_delta < 0:
        score_delta += 20
    elif spx_delta > 0:
        score_delta -= 10

    score = int(max(0, min(100, 50 + score_delta)))
    if score >= 70:
        return "RISK_OFF", score
    if score <= 40:
        return "RISK_ON", score
    return "NEUTRO", score


def regra_nao_operar(regime: str, score: int, score_minimo: int,
                     dxy_us10y_divergente: bool, volume_fraco: bool) -> Tuple[bool, str]:
    if score < score_minimo:
        return True, f"Score abaixo do mínimo ({score} < {score_minimo})."
    if regime == "NEUTRO":
        return True, "Regime NEUTRO (sem direção macro)."
    if dxy_us10y_divergente:
        return True, "DXY e US10Y divergentes (macro inconsistente)."
    if volume_fraco:
        return True, "Volume fraco (participação baixa)."
    return False, "Liberado para operar (macro alinhado)."


def baixar_yahoo(ticker: str, periodo: str, intervalo: str) -> pd.DataFrame:
    for tentativa in range(1, 4):
        try:
            df = yf.download(ticker, period=periodo, interval=intervalo,
                             auto_adjust=False, progress=False)
            if df is None or df.empty:
                return pd.DataFrame()
            if isinstance(df.columns, pd.MultiIndex):
                if ticker in df.columns.get_level_values(0):
                    df = df.xs(ticker, axis=1, level=0)
                elif ticker in df.columns.get_level_values(1):
                    df = df.xs(ticker, axis=1, level=1)
                else:
                    df.columns = df.columns.get_level_values(0)
            if isinstance(df, pd.Series):
                df = df.to_frame()
            if not isinstance(df, pd.DataFrame):
                return pd.DataFrame()
            df = df.loc[:, ~df.columns.duplicated()]
            required_cols = ["Open", "High", "Low", "Close"]
            if not set(required_cols).issubset(df.columns):
                return pd.DataFrame()
            df = df.dropna(subset=required_cols)
            return df
        except Exception:
            if tentativa == 3:
                return pd.DataFrame()
            time.sleep(1.5 * tentativa)
    return pd.DataFrame()


def baixar_fred_series(fred: Fred, serie: str, ultimos_dias: int = 180) -> pd.Series:
    try:
        s = pd.Series(fred.get_series(serie)).dropna()
    except Exception:
        return pd.Series(dtype=float)
    s.index = pd.to_datetime(s.index)
    if len(s) > ultimos_dias:
        s = s.iloc[-ultimos_dias:]
    return s


def anexar_snapshot_excel(caminho_excel: str, linha: Dict[str, object]) -> None:
    df_nova = pd.DataFrame([linha])
    if os.path.exists(caminho_excel):
        with pd.ExcelWriter(caminho_excel, engine="openpyxl", mode="a", if_sheet_exists="overlay") as writer:
            try:
                df_exist = pd.read_excel(caminho_excel, sheet_name="SNAPSHOTS")
                df_final = pd.concat([df_exist, df_nova], ignore_index=True)
            except Exception:
                df_final = df_nova
            df_final.to_excel(writer, sheet_name="SNAPSHOTS", index=False)
    else:
        with pd.ExcelWriter(caminho_excel, engine="openpyxl") as writer:
            df_nova.to_excel(writer, sheet_name="SNAPSHOTS", index=False)


def salvar_ohlc_excel(caminho_excel: str, nome_aba: str, df_ohlc: pd.DataFrame) -> None:
    df = df_ohlc.copy()
    df.index = remover_timezone_index(df.index)
    df = df.reset_index()
    if "DataHora" not in df.columns and len(df.columns) > 0:
        df = df.rename(columns={df.columns[0]: "DataHora"})
    if "DataHora" in df.columns:
        df["DataHora"] = remover_timezone_series(df["DataHora"])
    tz_cols = df.select_dtypes(include=["datetimetz"]).columns
    for col in tz_cols:
        df[col] = remover_timezone_series(df[col])
    if os.path.exists(caminho_excel):
        with pd.ExcelWriter(caminho_excel, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            df.to_excel(writer, sheet_name=nome_aba, index=False)
    else:
        with pd.ExcelWriter(caminho_excel, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name=nome_aba, index=False)


def executar_coleta(cfg: ConfigColetor) -> None:
    log_status("🧭", "Iniciando coleta MacroFlow...")
    fred_api_key = os.getenv("FRED_API_KEY", "").strip()
    if not fred_api_key:
        raise RuntimeError("FRED_API_KEY não encontrada. Configure no .env ou variável de ambiente.")

    fred = Fred(api_key=fred_api_key)
    falhas: list[str] = []

    serie_dxy = baixar_fred_series(fred, cfg.fred_serie_dxy)
    serie_us10y = baixar_fred_series(fred, cfg.fred_serie_us10y)
    dados_fred_ok = not serie_dxy.empty and not serie_us10y.empty
    if dados_fred_ok:
        log_status("✅", "FRED OK (DXY/US10Y).")
    else:
        log_status("⚠️", "FRED falhou (DXY/US10Y).")
        falhas.append("FRED (DXY/US10Y)")

    if dados_fred_ok:
        dxy_rsi_series = calcular_rsi(serie_dxy, cfg.rsi_periodo)
        dxy_rsi = float(dxy_rsi_series.iloc[-1]) if not dxy_rsi_series.empty else np.nan
        us10y_delta = float(serie_us10y.iloc[-1] - serie_us10y.iloc[-5]) if len(serie_us10y) >= 6 else 0.0
        dxy_delta = float(serie_dxy.iloc[-1] - serie_dxy.iloc[-5]) if len(serie_dxy) >= 6 else 0.0
        dxy_us10y_divergente = (dxy_delta > 0 and us10y_delta < 0) or (dxy_delta < 0 and us10y_delta > 0)
    else:
        dxy_rsi = np.nan
        us10y_delta = 0.0
        dxy_delta = 0.0
        dxy_us10y_divergente = False

    spx_df_60m = baixar_yahoo(ATIVOS_YAHOO["SPX"], cfg.periodo_yahoo, cfg.intervalo_yahoo)
    spx_4h = resample_para_4h(spx_df_60m)
    spx_ok = not spx_4h.empty and "Close" in spx_4h.columns
    if spx_ok:
        spx_close = spx_4h["Close"].dropna()
        spx_delta = float(spx_close.iloc[-1] - spx_close.iloc[-5]) if len(spx_close) >= 6 else 0.0
        log_status("✅", "SPX OK (Yahoo).")
    else:
        spx_delta = 0.0
        log_status("⚠️", "SPX falhou (Yahoo).")
        falhas.append("SPX (Yahoo)")

    if dados_fred_ok and spx_ok and not np.isnan(dxy_rsi):
        regime, score = calcular_score_regime(dxy_rsi=dxy_rsi, us10y_delta=us10y_delta, spx_delta=spx_delta)
    else:
        regime, score = "NEUTRO", 0

    vol_atual = float(spx_4h["Volume"].iloc[-1]) if not spx_4h.empty else np.nan
    vol_med = float(spx_4h["Volume"].tail(50).mean()) if len(spx_4h) >= 50 else vol_atual
    volume_fraco = bool(vol_atual < 0.6 * vol_med) if (not np.isnan(vol_atual) and not np.isnan(vol_med) and vol_med != 0) else False

    nao_operar, motivo_nao_operar = regra_nao_operar(
        regime=regime,
        score=score,
        score_minimo=cfg.score_minimo_operar,
        dxy_us10y_divergente=dxy_us10y_divergente,
        volume_fraco=volume_fraco
    )
    motivos_bloqueio = []
    if not dados_fred_ok:
        motivos_bloqueio.append("FRED (DXY/US10Y) indisponível")
    if not spx_ok:
        motivos_bloqueio.append("SPX (Yahoo) indisponível")
    if motivos_bloqueio:
        motivo_dados = "Dados macro incompletos: " + ", ".join(motivos_bloqueio)
        if motivo_nao_operar:
            motivo_nao_operar = f"{motivo_nao_operar} | {motivo_dados}"
        else:
            motivo_nao_operar = motivo_dados
        nao_operar = True

    agora = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")

    snapshot: Dict[str, object] = {
        "timestamp_local": agora,
        "regime": regime,
        "score": score,
        "nao_operar": int(nao_operar),
        "motivo_nao_operar": motivo_nao_operar,
        "dxy_fred": ultimo_valor(serie_dxy),
        "dxy_rsi14": dxy_rsi,
        "us10y_fred": ultimo_valor(serie_us10y),
        "us10y_delta_5d": us10y_delta,
        "spx_delta_5x4h": spx_delta,
        "spx_volume_4h": vol_atual,
        "spx_volume_media_50": vol_med,
        "dxy_us10y_divergente": int(dxy_us10y_divergente),
        "volume_fraco_proxy": int(volume_fraco),
    }

    for nome, ticker in ATIVOS_YAHOO.items():
        df_60m = baixar_yahoo(ticker, cfg.periodo_yahoo, cfg.intervalo_yahoo)
        if df_60m.empty:
            log_status("⚠️", f"Yahoo sem dados para {nome} ({ticker}).")
            falhas.append(f"Yahoo:{nome}")
        df_4h = resample_para_4h(df_60m)

        preco, var_abs, var_pct, vol_4h = calcular_variacao(df_4h)
        rsi_4h = float(calcular_rsi(df_4h["Close"], cfg.rsi_periodo).iloc[-1]) if not df_4h.empty else np.nan

        passo, casas = obter_cfg_niveis_fixos(nome, cfg)
        niveis = calcular_niveis_fixos_com_casas(preco, passo, casas)
        print(
            f"[NIVEIS] {nome} preco_atual={formatar_preco(preco, casas)} "
            f"0%={formatar_preco(niveis['nivel_0'], casas)} "
            f"25%={formatar_preco(niveis['nivel_25'], casas)} "
            f"50%={formatar_preco(niveis['nivel_50'], casas)} "
            f"75%={formatar_preco(niveis['nivel_75'], casas)} "
            f"100%={formatar_preco(niveis['nivel_100'], casas)}"
        )

        prefixo = nome.lower()
        snapshot.update({
            f"{prefixo}_preco": preco,
            f"{prefixo}_var": var_abs,
            f"{prefixo}_var_pct": var_pct,
            f"{prefixo}_volume_4h": vol_4h,
            f"{prefixo}_rsi14_4h": rsi_4h,
            f"{prefixo}_nivel_0": niveis["nivel_0"],
            f"{prefixo}_nivel_25": niveis["nivel_25"],
            f"{prefixo}_nivel_50": niveis["nivel_50"],
            f"{prefixo}_nivel_75": niveis["nivel_75"],
            f"{prefixo}_nivel_100": niveis["nivel_100"],
        })

        salvar_ohlc_excel(cfg.caminho_excel, f"OHLC_{nome}", df_4h)

    anexar_snapshot_excel(cfg.caminho_excel, snapshot)

    log_status("✅", f"Excel atualizado: {cfg.caminho_excel}")
    log_status("ℹ️", f"Regime: {regime} | Score: {score} | Não operar: {nao_operar} ({motivo_nao_operar})")
    if falhas:
        falhas_unicas = ", ".join(sorted(set(falhas)))
        log_status("⚠️", f"Coleta concluída com falhas: {falhas_unicas}.")
    else:
        log_status("✅", "Coleta concluída com sucesso. Todas as fontes responderam.")


def main():
    parser = argparse.ArgumentParser(description="MacroFlow Coletor – salva dados macro em Excel.")
    parser.add_argument("--excel", type=str, default=None, help="Caminho do Excel de saída.")
    parser.add_argument("--periodo", type=str, default=None, help="Período Yahoo (ex: 60d).")
    parser.add_argument("--intervalo", type=str, default=None, help="Intervalo Yahoo (ex: 60m).")
    args = parser.parse_args()

    # carrega .env se disponível
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

    cfg = ConfigColetor()
    if args.excel:
        cfg.caminho_excel = args.excel
    if args.periodo:
        cfg.periodo_yahoo = args.periodo
    if args.intervalo:
        cfg.intervalo_yahoo = args.intervalo

    executar_coleta(cfg)


if __name__ == "__main__":
    main()
