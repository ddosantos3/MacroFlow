import argparse

import uvicorn

from src.macroflow import executar_coleta, gerar_recomendacao, load_settings
from src.macroflow.api import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Orquestrador principal do MacroFlow.")
    parser.add_argument("command", nargs="?", default="run", choices=["run", "collect", "agent", "serve"])
    parser.add_argument("--host", default=None, help="Host do servidor web.")
    parser.add_argument("--port", type=int, default=None, help="Porta do servidor web.")
    args = parser.parse_args()

    settings = load_settings()
    if args.host:
        settings.host = args.host
    if args.port:
        settings.port = args.port

    if args.command == "collect":
        resultado = executar_coleta(settings)
        print("\n" + str(resultado["terminal_report"]) + "\n")
        return

    if args.command == "agent":
        print("\n" + gerar_recomendacao(settings) + "\n")
        return

    if args.command == "serve":
        uvicorn.run(create_app(settings), host=settings.host, port=settings.port)
        return

    resultado = executar_coleta(settings)
    print("\n" + str(resultado["terminal_report"]) + "\n")


if __name__ == "__main__":
    main()
