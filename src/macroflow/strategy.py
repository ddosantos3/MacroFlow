from __future__ import annotations

from dataclasses import asdict
from typing import Any

import pandas as pd

from .config import ASSET_LABELS
from .domain import Direction, ExecutionStatus, MacroContext, PositionSizing, Regime, StrategyDecision
from .indicators import candle_history, formatar_numero


def calcular_score_regime(dxy_rsi14: float, us10y_delta: float, spx_delta: float) -> tuple[str, int]:
    score_delta = 0
    if dxy_rsi14 >= 55:
        score_delta += 30
    elif dxy_rsi14 <= 45:
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
        return Regime.RISK_OFF.value, score
    if score <= 40:
        return Regime.RISK_ON.value, score
    return Regime.NEUTRO.value, score


def regra_nao_operar(
    regime: str,
    score: int,
    score_minimo: int,
    dxy_us10y_divergente: bool,
    volume_fraco: bool,
) -> tuple[bool, str]:
    if score < score_minimo:
        return True, f"Score abaixo do mínimo ({score} < {score_minimo})."
    if regime == Regime.NEUTRO.value:
        return True, "Regime NEUTRO, sem direção macro validada."
    if dxy_us10y_divergente:
        return True, "DXY e US10Y divergentes, cenário macro inconsistente."
    if volume_fraco:
        return True, "SPX com volume fraco no proxy 4H."
    return False, "Macro alinhado para operar."


def direcao_macro_por_ativo(regime: str, score: int, dxy_rsi14: float) -> dict[str, str]:
    directions = {"USDBRL": Direction.NEUTRO.value, "BRA50": Direction.NEUTRO.value}
    if regime == Regime.RISK_ON.value and dxy_rsi14 <= 45:
        directions["USDBRL"] = Direction.VENDA.value
    elif regime == Regime.RISK_OFF.value and dxy_rsi14 >= 55:
        directions["USDBRL"] = Direction.COMPRA.value

    if regime == Regime.RISK_ON.value and score >= 70:
        directions["BRA50"] = Direction.COMPRA.value
    elif regime == Regime.RISK_OFF.value and score >= 70:
        directions["BRA50"] = Direction.VENDA.value
    return directions


def construir_macro_context(
    dxy_value: float,
    dxy_rsi14: float,
    dxy_delta: float,
    us10y_value: float,
    us10y_delta: float,
    spx_delta: float,
    spx_volume_4h: float,
    spx_volume_media_50: float,
    score_minimo_operar: int,
    dados_fred_ok: bool,
    spx_ok: bool,
) -> MacroContext:
    dxy_us10y_divergente = (dxy_delta == dxy_delta and us10y_delta != 0) and (
        (dxy_delta > 0 and us10y_delta < 0) or (dxy_delta < 0 and us10y_delta > 0)
    )
    volume_fraco = (
        spx_volume_4h == spx_volume_4h
        and spx_volume_media_50 == spx_volume_media_50
        and spx_volume_media_50 != 0
        and spx_volume_4h < (0.6 * spx_volume_media_50)
    )

    if dados_fred_ok and spx_ok and dxy_rsi14 == dxy_rsi14:
        regime, score = calcular_score_regime(dxy_rsi14=dxy_rsi14, us10y_delta=us10y_delta, spx_delta=spx_delta)
    else:
        regime, score = Regime.NEUTRO.value, 0

    nao_operar, motivo = regra_nao_operar(
        regime=regime,
        score=score,
        score_minimo=score_minimo_operar,
        dxy_us10y_divergente=dxy_us10y_divergente,
        volume_fraco=volume_fraco,
    )
    motivos_bloqueio = []
    if not dados_fred_ok:
        motivos_bloqueio.append("FRED indisponível")
    if not spx_ok:
        motivos_bloqueio.append("SPX indisponível")
    if motivos_bloqueio:
        motivo_dados = "Dados macro incompletos: " + ", ".join(motivos_bloqueio)
        motivo = f"{motivo} | {motivo_dados}" if motivo else motivo_dados
        nao_operar = True

    macro_directions = direcao_macro_por_ativo(regime, score, dxy_rsi14)
    headline = f"{regime} | score {score} | {'NÃO OPERAR' if nao_operar else 'OPERÁVEL'}"
    return MacroContext(
        regime=regime,
        score=score,
        nao_operar=nao_operar,
        motivo_nao_operar=motivo,
        dxy_fred=dxy_value,
        dxy_rsi14=dxy_rsi14,
        us10y_fred=us10y_value,
        us10y_delta_5d=us10y_delta,
        spx_delta_5x4h=spx_delta,
        spx_volume_4h=spx_volume_4h,
        spx_volume_media_50=spx_volume_media_50,
        dxy_us10y_divergente=dxy_us10y_divergente,
        volume_fraco_proxy=volume_fraco,
        macro_directions=macro_directions,
        headline=headline,
    )


def _ultimo_indice_true(mask: pd.Series):
    valid = mask[mask].index
    return valid[-1] if len(valid) else None


def _timestamp_or_none(value) -> str | None:
    if value is None:
        return None
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def _encontrar_setup(frame: pd.DataFrame, direction: str):
    if frame.empty:
        return None, None, None
    if direction == Direction.COMPRA.value:
        cross_mask = (frame["TREND_SIGN"] > 0) & (frame["TREND_SIGN"].shift(1).fillna(0) <= 0)
        trend_ok = bool(frame["TREND_SIGN"].iloc[-1] > 0)
        confirm_col = "POSITIVE_CLOSE"
    else:
        cross_mask = (frame["TREND_SIGN"] < 0) & (frame["TREND_SIGN"].shift(1).fillna(0) >= 0)
        trend_ok = bool(frame["TREND_SIGN"].iloc[-1] < 0)
        confirm_col = "NEGATIVE_CLOSE"

    if not trend_ok:
        return None, None, None

    cross_index = _ultimo_indice_true(cross_mask)
    if cross_index is None:
        cross_index = frame.index[0]

    analysis = frame.loc[cross_index:]
    touch_index = _ultimo_indice_true(analysis["TOUCH_EMA_SLOW"])
    if touch_index is None:
        return cross_index, None, None

    touch_pos = analysis.index.get_loc(touch_index)
    confirmation_index = None
    for position in [touch_pos, touch_pos + 1]:
        if position >= len(analysis):
            continue
        row = analysis.iloc[position]
        if bool(row[confirm_col]):
            confirmation_index = analysis.index[position]
            break
    return cross_index, touch_index, confirmation_index


def _build_position_sizing(
    capital_total: float | None,
    risco_maximo_por_operacao: float,
    entry_price: float | None,
    stop_price: float | None,
) -> PositionSizing:
    if capital_total is None:
        return PositionSizing(
            capital_total=None,
            risco_maximo_reais=None,
            risco_por_unidade=None,
            quantidade=None,
            exposicao_estimada=None,
            observacao="Defina MACROFLOW_CAPITAL_TOTAL_BRL para habilitar o sizing de risco.",
        )
    if entry_price is None or stop_price is None:
        return PositionSizing(
            capital_total=capital_total,
            risco_maximo_reais=capital_total * risco_maximo_por_operacao,
            risco_por_unidade=None,
            quantidade=None,
            exposicao_estimada=None,
            observacao="Sem entrada/stop confirmados, sizing ainda indisponível.",
        )
    risco_por_unidade = abs(entry_price - stop_price)
    if risco_por_unidade == 0:
        return PositionSizing(
            capital_total=capital_total,
            risco_maximo_reais=capital_total * risco_maximo_por_operacao,
            risco_por_unidade=0.0,
            quantidade=None,
            exposicao_estimada=None,
            observacao="Entrada e stop coincidem; sizing bloqueado para evitar divisão por zero.",
        )
    risco_maximo = capital_total * risco_maximo_por_operacao
    quantidade = risco_maximo / risco_por_unidade
    exposicao = quantidade * entry_price
    return PositionSizing(
        capital_total=capital_total,
        risco_maximo_reais=risco_maximo,
        risco_por_unidade=risco_por_unidade,
        quantidade=quantidade,
        exposicao_estimada=exposicao,
        observacao="Dimensionamento calculado pelo risco máximo de 1% do capital por operação.",
    )


def analisar_ativo_operacional(
    asset: str,
    ticker: str,
    frame_diario: pd.DataFrame,
    preco_atual: float,
    variacao_pct: float,
    volume_4h: float,
    fixed_levels: dict[str, float],
    macro_context: MacroContext,
    capital_total_brl: float | None,
    risco_maximo_por_operacao: float,
    stop_buffer_pct: float,
) -> StrategyDecision:
    label = ASSET_LABELS.get(asset, asset)
    macro_direction = macro_context.macro_directions.get(asset, Direction.NEUTRO.value)

    if frame_diario.empty:
        return StrategyDecision(
            asset=asset,
            label=label,
            proxy_ticker=ticker,
            macro_direction=macro_direction,
            technical_direction=Direction.NEUTRO.value,
            macro_aligned=False,
            execution_status=ExecutionStatus.SEM_DADOS.value,
            stage_reason="Sem candles diários suficientes para calcular PMD/MME9/MME21.",
            price=preco_atual,
            change_pct=variacao_pct,
            volume_4h=volume_4h,
            pmd=float("nan"),
            ema_fast=float("nan"),
            ema_slow=float("nan"),
            trend_cross_at=None,
            touch_detected_at=None,
            confirmation_at=None,
            entry_price=None,
            stop_price=None,
            trailing_stop=None,
            exit_condition="Sem dados operacionais.",
            fixed_levels=fixed_levels,
            position_sizing=_build_position_sizing(capital_total_brl, risco_maximo_por_operacao, None, None),
            history=[],
            technical_notes=["A coleta diária precisa responder para liberar decisão técnica."],
        )

    latest = frame_diario.iloc[-1]
    if latest["EMA_FAST"] > latest["EMA_SLOW"]:
        technical_direction = Direction.COMPRA.value
    elif latest["EMA_FAST"] < latest["EMA_SLOW"]:
        technical_direction = Direction.VENDA.value
    else:
        technical_direction = Direction.NEUTRO.value

    cross_index, touch_index, confirmation_index = _encontrar_setup(frame_diario, technical_direction)
    macro_aligned = macro_direction == technical_direction and technical_direction != Direction.NEUTRO.value

    touch_row = frame_diario.loc[touch_index] if touch_index is not None else None
    confirmation_row = frame_diario.loc[confirmation_index] if confirmation_index is not None else None
    trailing_stop = float(latest["EMA_SLOW"]) if latest["EMA_SLOW"] == latest["EMA_SLOW"] else None

    entry_price = None
    stop_price = None
    technical_notes = [
        f"PMD atual em {formatar_numero(float(latest['PMD']))}.",
        f"MME rápida em {formatar_numero(float(latest['EMA_FAST']))}.",
        f"MME lenta em {formatar_numero(float(latest['EMA_SLOW']))}.",
    ]

    if touch_row is not None:
        if technical_direction == Direction.COMPRA.value:
            stop_price = float(touch_row["Low"] * (1 - stop_buffer_pct))
        elif technical_direction == Direction.VENDA.value:
            stop_price = float(touch_row["High"] * (1 + stop_buffer_pct))
    if confirmation_row is not None:
        entry_price = float(confirmation_row["Close"])

    if technical_direction == Direction.NEUTRO.value:
        status = ExecutionStatus.SEM_DADOS.value
        reason = "MME9 e MME21 ainda não definiram tendência operacional."
    elif macro_context.nao_operar or not macro_aligned:
        status = ExecutionStatus.BLOQUEADO_MACRO.value
        if macro_context.nao_operar:
            reason = f"Bloqueado pela camada macro: {macro_context.motivo_nao_operar}"
        else:
            reason = f"Macro aponta {macro_direction}, mas o técnico está em {technical_direction}."
    elif touch_index is None:
        status = ExecutionStatus.AGUARDANDO_PULLBACK.value
        reason = "Tendência validada, porém ainda aguardando o preço tocar a MME21."
    elif confirmation_index is None:
        status = ExecutionStatus.AGUARDANDO_CONFIRMACAO.value
        reason = "Preço tocou a MME21; agora a regra exige candle de confirmação no mesmo dia ou no próximo."
    else:
        post_confirmation = frame_diario.loc[confirmation_index:]
        if technical_direction == Direction.COMPRA.value:
            exit_hit = bool((post_confirmation["Close"] < post_confirmation["EMA_SLOW"]).any())
        else:
            exit_hit = bool((post_confirmation["Close"] > post_confirmation["EMA_SLOW"]).any())
        if exit_hit:
            status = ExecutionStatus.SAIDA_ACIONADA.value
            reason = "Houve fechamento contrário à MME21 após o gatilho; setup encerrado."
        else:
            candles_since_confirmation = len(post_confirmation) - 1
            status = (
                ExecutionStatus.PRONTO_PARA_EXECUTAR.value
                if candles_since_confirmation <= 1
                else ExecutionStatus.EM_ACOMPANHAMENTO.value
            )
            reason = "Setup confirmado e ainda respeitando a MME21 como stop móvel."

    exit_condition = (
        "Fechar abaixo da MME21 para long."
        if technical_direction == Direction.COMPRA.value
        else "Fechar acima da MME21 para short."
        if technical_direction == Direction.VENDA.value
        else "Sem condição de saída definida."
    )
    technical_notes.append(exit_condition)

    return StrategyDecision(
        asset=asset,
        label=label,
        proxy_ticker=ticker,
        macro_direction=macro_direction,
        technical_direction=technical_direction,
        macro_aligned=macro_aligned,
        execution_status=status,
        stage_reason=reason,
        price=preco_atual,
        change_pct=variacao_pct,
        volume_4h=volume_4h,
        pmd=float(latest["PMD"]),
        ema_fast=float(latest["EMA_FAST"]),
        ema_slow=float(latest["EMA_SLOW"]),
        trend_cross_at=_timestamp_or_none(cross_index),
        touch_detected_at=_timestamp_or_none(touch_index),
        confirmation_at=_timestamp_or_none(confirmation_index),
        entry_price=entry_price,
        stop_price=stop_price,
        trailing_stop=trailing_stop,
        exit_condition=exit_condition,
        fixed_levels=fixed_levels,
        position_sizing=_build_position_sizing(capital_total_brl, risco_maximo_por_operacao, entry_price, stop_price),
        history=candle_history(frame_diario),
        technical_notes=technical_notes,
    )


def _format_asset_report(decision: StrategyDecision) -> str:
    sizing = decision.position_sizing or PositionSizing(None, None, None, None, None, "-")
    linhas = [
        f"{decision.label}",
        f"- Macro: {decision.macro_direction} | Técnico: {decision.technical_direction} | Status: {decision.execution_status}",
        f"- Contexto: {decision.stage_reason}",
        f"- Preço: {formatar_numero(decision.price)} | PMD: {formatar_numero(decision.pmd)} | MME9: {formatar_numero(decision.ema_fast)} | MME21: {formatar_numero(decision.ema_slow)}",
        f"- Entrada: {formatar_numero(decision.entry_price)} | Stop: {formatar_numero(decision.stop_price)} | Stop móvel: {formatar_numero(decision.trailing_stop)}",
        f"- Sizing: qty {formatar_numero(sizing.quantidade or float('nan'), 2)} | risco/unidade {formatar_numero(sizing.risco_por_unidade or float('nan'))}",
    ]
    return "\n".join(linhas)


def montar_relatorio_terminal(macro_context: MacroContext, decisions: list[StrategyDecision]) -> str:
    header = [
        "MACROFLOW COMMAND CENTER",
        f"Regime: {macro_context.regime}",
        f"Score: {macro_context.score}",
        f"Status macro: {'NÃO OPERAR' if macro_context.nao_operar else 'OPERÁVEL'}",
        f"Motivo: {macro_context.motivo_nao_operar}",
        "",
    ]
    body = [_format_asset_report(decision) for decision in decisions]
    return "\n\n".join(header + body)


def snapshot_from_state(macro_context: MacroContext, decisions: list[StrategyDecision], generated_at: str) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "timestamp_local": generated_at,
        "regime": macro_context.regime,
        "score": macro_context.score,
        "nao_operar": int(macro_context.nao_operar),
        "motivo_nao_operar": macro_context.motivo_nao_operar,
        "dxy_fred": macro_context.dxy_fred,
        "dxy_rsi14": macro_context.dxy_rsi14,
        "us10y_fred": macro_context.us10y_fred,
        "us10y_delta_5d": macro_context.us10y_delta_5d,
        "spx_delta_5x4h": macro_context.spx_delta_5x4h,
        "spx_volume_4h": macro_context.spx_volume_4h,
        "spx_volume_media_50": macro_context.spx_volume_media_50,
        "dxy_us10y_divergente": int(macro_context.dxy_us10y_divergente),
        "volume_fraco_proxy": int(macro_context.volume_fraco_proxy),
    }
    for decision in decisions:
        prefix = decision.asset.lower()
        snapshot.update(
            {
                f"{prefix}_preco": decision.price,
                f"{prefix}_var_pct": decision.change_pct,
                f"{prefix}_volume_4h": decision.volume_4h,
                f"{prefix}_pmd": decision.pmd,
                f"{prefix}_ema_fast": decision.ema_fast,
                f"{prefix}_ema_slow": decision.ema_slow,
                f"{prefix}_macro_direction": decision.macro_direction,
                f"{prefix}_technical_direction": decision.technical_direction,
                f"{prefix}_macro_aligned": int(decision.macro_aligned),
                f"{prefix}_execution_status": decision.execution_status,
                f"{prefix}_entry_price": decision.entry_price,
                f"{prefix}_stop_price": decision.stop_price,
                f"{prefix}_trailing_stop": decision.trailing_stop,
                f"{prefix}_touch_detected_at": decision.touch_detected_at,
                f"{prefix}_confirmation_at": decision.confirmation_at,
                f"{prefix}_trend_cross_at": decision.trend_cross_at,
            }
        )
        for level_name, value in decision.fixed_levels.items():
            snapshot[f"{prefix}_{level_name}"] = value
        if decision.position_sizing:
            sizing = asdict(decision.position_sizing)
            for key, value in sizing.items():
                snapshot[f"{prefix}_risk_{key}"] = value
    return snapshot
