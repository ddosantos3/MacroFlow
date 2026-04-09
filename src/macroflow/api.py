from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import AppSettings, load_settings
from .domain import to_plain
from .pipeline import executar_coleta
from .settings_store import build_settings_payload, reload_settings, update_env_file
from .storage import ArtifactStore


def _empty_state(settings: AppSettings) -> dict[str, object]:
    settings_panel = build_settings_payload(settings)
    return {
        "generated_at": None,
        "summary": {
            "headline": "Aguardando primeira coleta",
            "blocked": True,
            "has_actionable_trade": False,
            "excel_path": str(settings.storage.excel_path),
            "default_chart_timeframe": settings.market.chart_default_timeframe,
        },
        "macro_context": {
            "regime": "NEUTRO",
            "score": 0,
            "nao_operar": True,
            "motivo_nao_operar": "Execute a coleta para materializar o dashboard e o plano operacional.",
            "dxy_fred": None,
            "dxy_rsi14": None,
            "us10y_fred": None,
            "us10y_delta_5d": None,
            "spx_delta_5x4h": None,
            "spx_volume_4h": None,
            "spx_volume_media_50": None,
            "dxy_us10y_divergente": False,
            "volume_fraco_proxy": False,
            "macro_directions": {"USDBRL": "NEUTRO", "BRA50": "NEUTRO"},
            "headline": "Sem dados carregados",
        },
        "asset_decisions": [],
        "source_health": [],
        "terminal_report": "Sem coleta executada.",
        "market_overview": {
            "title": "Menu Principal",
            "subtitle": "Panorama geral do mercado e a proposta operacional do MacroFlow.",
            "headline": "Sem dados carregados",
            "cards": [],
            "macroflow_does": [
                "Lê o macro antes de aceitar qualquer trade.",
                "Converte PMD, MME9 e MME21 em uma rotina operacional auditável.",
                "Entrega leitura local com persistência em JSON e Excel.",
            ],
            "market_notes": [
                "Use o botão Iniciar Macroflow para carregar o primeiro estado do dashboard.",
            ],
        },
        "market_assets": [],
        "news_center": {
            "title": "Notícias do Mercado Financeiro",
            "status": "Backlog estruturado para implementação",
            "summary": "Este módulo ainda será conectado a fontes externas e classificação de viés.",
            "sources": [],
            "bias_framework": [],
            "implementation_tasks": [],
        },
        "settings_panel": settings_panel,
    }


def create_app(settings: AppSettings | None = None) -> FastAPI:
    settings = settings or load_settings()
    store = ArtifactStore(
        excel_path=settings.storage.excel_path,
        dashboard_state_path=settings.storage.dashboard_state_path,
        snapshot_history_path=settings.storage.snapshot_history_path,
    )

    app = FastAPI(title="MacroFlow", version="2.1.0")
    web_root = Path(__file__).resolve().parent / "web"
    templates = Jinja2Templates(directory=str(web_root / "templates"))
    app.mount("/static", StaticFiles(directory=str(web_root / "static")), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "app_name": "MacroFlow",
                "headline": "Módulos visuais separados para leitura macro, análise gráfica e operação",
            },
        )

    @app.get("/api/dashboard")
    async def dashboard_state() -> JSONResponse:
        state = store.load_dashboard_state() or _empty_state(settings)
        return JSONResponse(state)

    @app.post("/api/refresh")
    async def refresh_state() -> JSONResponse:
        try:
            result = executar_coleta(settings=settings)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return JSONResponse({"ok": True, "state": to_plain(result["dashboard_state"])})

    @app.get("/api/settings")
    async def get_settings() -> JSONResponse:
        return JSONResponse(build_settings_payload(settings))

    @app.post("/api/settings")
    async def save_settings(request: Request) -> JSONResponse:
        payload = await request.json()
        values = payload.get("values", payload)
        if not isinstance(values, dict):
            raise HTTPException(status_code=400, detail="Payload de configurações inválido.")
        try:
            update_env_file(values, project_root=settings.storage.project_root)
            reload_settings(settings)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Falha ao salvar configurações: {exc}") from exc
        return JSONResponse({"ok": True, "settings": build_settings_payload(settings)})

    @app.get("/health")
    async def health() -> JSONResponse:
        state = store.load_dashboard_state()
        return JSONResponse(
            {
                "status": "ok",
                "has_state": bool(state),
                "excel_path": str(settings.storage.excel_path),
                "dashboard_state_path": str(settings.storage.dashboard_state_path),
            }
        )

    return app
