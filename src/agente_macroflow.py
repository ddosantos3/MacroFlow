# src/agente_macroflow.py
import os
from typing import Dict, Any, Tuple

import pandas as pd

from src.settings import ConfigAgente

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


# -----------------------------
# Leitura do Excel
# -----------------------------
def carregar_snapshot_mais_recente(caminho_excel: str, aba: str) -> Dict[str, Any]:
    df = pd.read_excel(caminho_excel, sheet_name=aba)
    if df.empty:
        raise RuntimeError("A aba SNAPSHOTS está vazia. Execute o coletor pelo menos 1 vez.")
    linha = df.iloc[-1].to_dict()
    return linha


def pegar_niveis(snapshot: Dict[str, Any], prefixo: str) -> Dict[str, float]:
    def g(chave: str) -> float:
        return float(snapshot.get(f"{prefixo}_{chave}", float("nan")))
    return {
        "0": g("nivel_0"),
        "25": g("nivel_25"),
        "50": g("nivel_50"),
        "75": g("nivel_75"),
        "100": g("nivel_100"),
        "preco": float(snapshot.get(f"{prefixo}_preco", float("nan"))),
        "var_pct": float(snapshot.get(f"{prefixo}_var_pct", float("nan"))),
        "volume_4h": float(snapshot.get(f"{prefixo}_volume_4h", float("nan"))),
        "rsi14_4h": float(snapshot.get(f"{prefixo}_rsi14_4h", float("nan"))),
    }


# -----------------------------
# Core determinístico (regras)
# -----------------------------
def classificar_confluencia(regime: str, score: int) -> str:
    # Simples e robusto: você pode sofisticar depois.
    if score >= 80:
        return "Muito Alta"
    if score >= 70:
        return "Alta"
    if score >= 65:
        return "Média"
    return "Baixa"


def definir_sinal_mini_dolar(regime: str, dxy_rsi14: float) -> str:
    # Regra macro clássica:
    # - Risk-On + DXY fraco => venda dólar
    # - Risk-Off + DXY forte => compra dólar
    if regime == "RISK_ON" and dxy_rsi14 <= 45:
        return "VENDA"
    if regime == "RISK_OFF" and dxy_rsi14 >= 55:
        return "COMPRA"
    return "NEUTRO"


def definir_sinal_mini_indice(regime: str, score: int) -> str:
    # Índice tende a ser o “espelho macro” do dólar:
    # - Risk-On favorece compras (com correção)
    # - Risk-Off favorece vendas (com pullback)
    if regime == "RISK_ON" and score >= 70:
        return "COMPRA"
    if regime == "RISK_OFF" and score >= 70:
        return "VENDA"
    return "NEUTRO"


def montar_plano_por_niveis(sinal: str, niveis: Dict[str, float]) -> Dict[str, Any]:
    """
    Gera Entrada/Stop/Parcial/Alvos usando 0/25/50/75/100.
    Sem “inventar” números.
    """
    n0, n25, n50, n75, n100 = niveis["0"], niveis["25"], niveis["50"], niveis["75"], niveis["100"]

    if sinal == "VENDA":
        return {
            "entrada": (n50, n75),
            "stop": (n75, n100),          # stop “acima da 75%”, com zona de tolerância
            "parcial": (n25, n25),
            "alvo_principal": (n25, n0),
            "alvo_estendido": (n0, n0),
        }

    if sinal == "COMPRA":
        return {
            "entrada": (n25, n50),
            "stop": (n0, n25),            # stop “abaixo da 25%”, com zona de tolerância
            "parcial": (n75, n75),
            "alvo_principal": (n75, n100),
            "alvo_estendido": (n100, n100),
        }

    return {
        "entrada": (float("nan"), float("nan")),
        "stop": (float("nan"), float("nan")),
        "parcial": (float("nan"), float("nan")),
        "alvo_principal": (float("nan"), float("nan")),
        "alvo_estendido": (float("nan"), float("nan")),
        "observacao": "Sem trade (neutro)."
    }


def regra_nao_operar(snapshot: Dict[str, Any], cfg: ConfigAgente) -> Tuple[bool, str]:
    # Você já grava nao_operar e motivo no snapshot. :contentReference[oaicite:3]{index=3}
    nao_operar = int(snapshot.get("nao_operar", 1)) == 1
    motivo = str(snapshot.get("motivo_nao_operar", "N/A"))
    # reforço: se score abaixo do mínimo, também trava
    score = int(snapshot.get("score", 0))
    if score < cfg.score_minimo_operar:
        return True, f"Score abaixo do mínimo ({score} < {cfg.score_minimo_operar})."
    return nao_operar, motivo


# -----------------------------
# Prompt (LLM só para redigir)
# -----------------------------
PROMPT_SISTEMA = """Você é o MacroFlow PRO, um analista institucional de mercado.
Regras absolutas:
1) NUNCA invente preços. Use somente os números fornecidos em DADOS.
2) NUNCA mude os níveis. Entrada/Stop/Parcial/Alvos devem respeitar as faixas fornecidas.
3) Se DADOS.nao_operar for true: responda "NÃO OPERAR" e explique o motivo com objetividade.
4) Saída SEMPRE no formato do template (títulos e emojis). Sem texto extra.
"""

TEMPLATE_RESPOSTA = """{TITULO}

Sinal: {SINAL}
Regime: {REGIME}
Confluência: {CONFLUENCIA}

📍 Preço de Entrada
Região de {ENTRADA_LABEL}
Aproximadamente: {ENTRADA_A} a {ENTRADA_B}

🛑 Stop Loss
Aproximadamente: {STOP_A} – {STOP_B}

🎯 Alvo Principal
Aproximadamente: {ALVO_P_A} – {ALVO_P_B}

🎯 Alvo Estendido
Aproximadamente: {ALVO_E_A}

🟡 Parcial
Aproximadamente: {PARCIAL_A}

📌 Observação institucional:
{OBS}
"""


def formatar_plano(titulo: str, sinal: str, regime: str, confluencia: str, plano: Dict[str, Any]) -> str:
    def f(x: float) -> str:
        if x != x:  # NaN
            return "-"
        return f"{x:.4f}".rstrip("0").rstrip(".")  # formato elegante

    entrada_a, entrada_b = plano["entrada"]
    stop_a, stop_b = plano["stop"]
    parcial_a, _ = plano["parcial"]
    alvo_p_a, alvo_p_b = plano["alvo_principal"]
    alvo_e_a, _ = plano["alvo_estendido"]

    if sinal == "VENDA":
        entrada_label = "50% a 75%"
    elif sinal == "COMPRA":
        entrada_label = "25% a 50%"
    else:
        entrada_label = "-"

    return TEMPLATE_RESPOSTA.format(
        TITULO=titulo,
        SINAL=f"🔴 {sinal}" if sinal == "VENDA" else ("🟢 COMPRA" if sinal == "COMPRA" else "⚪ NEUTRO"),
        REGIME=regime.replace("_", "-").title(),
        CONFLUENCIA=confluencia,
        ENTRADA_LABEL=entrada_label,
        ENTRADA_A=f(entrada_a),
        ENTRADA_B=f(entrada_b),
        STOP_A=f(stop_a),
        STOP_B=f(stop_b),
        ALVO_P_A=f(alvo_p_a),
        ALVO_P_B=f(alvo_p_b),
        ALVO_E_A=f(alvo_e_a),
        PARCIAL_A=f(parcial_a),
        OBS=plano["observacao"],
    )


# -----------------------------
# (Opcional) chamada LLM
# -----------------------------
def chamar_llm_openai(prompt_sistema: str, prompt_usuario: str) -> str:
    """
    Opcional: se quiser que a IA apenas "redija" a resposta.
    Requer: OPENAI_API_KEY no ambiente.
    Se não houver chave, você pode pular e usar o texto determinístico.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não encontrada. Defina no .env para usar o LLM.")

    # Evito dependência de SDK aqui: uso requests (mais estável no Windows corporativo).
    import requests

    # Endpoint genérico (ajuste se você usar outro provedor/modelo)
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario},
        ],
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def gerar_recomendacao(cfg: ConfigAgente, usar_llm: bool = False) -> str:
    snapshot = carregar_snapshot_mais_recente(cfg.caminho_excel, cfg.aba_snapshots)

    regime = str(snapshot.get("regime", "NEUTRO"))
    score = int(snapshot.get("score", 0))
    confluencia = classificar_confluencia(regime, score)

    nao_operar, motivo = regra_nao_operar(snapshot, cfg)
    dxy_rsi14 = float(snapshot.get("dxy_rsi14", float("nan")))

    # MINI DÓLAR (proxy atual)
    niveis_dolar = pegar_niveis(snapshot, cfg.prefixo_mini_dolar)
    sinal_dolar = definir_sinal_mini_dolar(regime, dxy_rsi14)
    plano_dolar = montar_plano_por_niveis(sinal_dolar, niveis_dolar)

    # MINI ÍNDICE (proxy atual)
    niveis_indice = pegar_niveis(snapshot, cfg.prefixo_mini_indice)
    sinal_indice = definir_sinal_mini_indice(regime, score)
    plano_indice = montar_plano_por_niveis(sinal_indice, niveis_indice)

    if nao_operar:
        return (
            "🚫 NÃO OPERAR (HOJE)\n\n"
            f"Motivo: {motivo}\n"
            "Regra institucional: sem confluência suficiente, não existe trade."
        )

    resposta_dolar = formatar_plano("PLANO OPERACIONAL — MINI DÓLAR", sinal_dolar, regime, confluencia, plano_dolar)
    resposta_indice = formatar_plano("PLANO OPERACIONAL — MINI ÍNDICE", sinal_indice, regime, confluencia, plano_indice)

    if not usar_llm:
        return resposta_dolar + "\n\n" + resposta_indice

    # Se usar LLM: passamos DADOS + template, e a IA só redige sem inventar.
    dados = {
        "regime": regime,
        "score": score,
        "confluencia": confluencia,
        "mini_dolar": {"sinal": sinal_dolar, "niveis": niveis_dolar, "plano": plano_dolar},
        "mini_indice": {"sinal": sinal_indice, "niveis": niveis_indice, "plano": plano_indice},
        "nao_operar": False,
        "motivo_nao_operar": "",
    }

    prompt_usuario = (
        "Gere a resposta final no TEMPLATE exatamente, SEM inventar nada.\n\n"
        f"DADOS:\n{dados}\n\n"
        "Use o mesmo estilo MacroFlow PRO (objetivo, institucional)."
    )

    texto = chamar_llm_openai(PROMPT_SISTEMA, prompt_usuario)
    return texto


if __name__ == "__main__":
    cfg = ConfigAgente()
    resposta = gerar_recomendacao(cfg, usar_llm=True)
    print("\n" + resposta + "\n")
