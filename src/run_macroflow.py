# src/run_macroflow.py
"""
MacroFlow Runner (1 comando)
1) Coleta dados (macroflow_coletor) e atualiza o Excel
2) Executa o agente (agente_macroflow) e imprime a recomendação no terminal
"""

# 🔹 CARREGA .ENV PRIMEIRO (ANTES DE QUALQUER COISA)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from src.macroflow_coletor import executar_coleta
from src.agente_macroflow import gerar_recomendacao
from src.settings import ConfigColetor, ConfigAgente


def main():
    print("\n==============================")
    print("   MACROFLOW PRO — RUNNER")
    print("==============================\n")

    # 1) Coleta
    print("⏳ Coletando dados e atualizando Excel...\n")
    cfg_coletor = ConfigColetor()
    executar_coleta(cfg_coletor)

    # 2) Agente
    print("\n🧠 Gerando recomendação institucional...\n")
    cfg_agente = ConfigAgente(caminho_excel=cfg_coletor.caminho_excel)
    resposta = gerar_recomendacao(cfg_agente, usar_llm=False)

    print("\n📌 RECOMENDAÇÃO FINAL")
    print("----------------------------------------")
    print(resposta)
    print("----------------------------------------\n")

    print("✅ Pipeline concluído.\n")


if __name__ == "__main__":
    main()
