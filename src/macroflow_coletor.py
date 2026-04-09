import argparse
from pathlib import Path

from src.macroflow import executar_coleta, load_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa a coleta refatorada do MacroFlow.")
    parser.add_argument("--excel", type=str, default=None, help="Sobrescreve o caminho do Excel.")
    parser.add_argument("--periodo", type=str, default=None, help="Período do Yahoo intraday.")
    parser.add_argument("--intervalo", type=str, default=None, help="Intervalo do Yahoo intraday.")
    args = parser.parse_args()

    settings = load_settings()
    if args.excel:
        settings.storage.excel_path = Path(args.excel)
    if args.periodo:
        settings.market.yahoo_intraday_period = args.periodo
    if args.intervalo:
        settings.market.yahoo_intraday_interval = args.intervalo

    resultado = executar_coleta(settings)
    print("\n" + str(resultado["terminal_report"]) + "\n")


if __name__ == "__main__":
    main()
