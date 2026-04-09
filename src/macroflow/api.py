from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import AppSettings, load_settings
from .domain import to_plain
from .pipeline import executar_coleta
from .storage import ArtifactStore


def _empty_state(settings: AppSettings) -> dict[str, object]:
    return {
        "generated_at": None,
        "summary": {
            "headline": "Aguardando primeira coleta",
            "blocked": True,
            "has_actionable_trade": False,
            "excel_path": str(settings.storage.excel_path),
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
    }


def create_app(settings: AppSettings | None = None) -> FastAPI:
    settings = settings or load_settings()
    store = ArtifactStore(
        excel_path=settings.storage.excel_path,
        dashboard_state_path=settings.storage.dashboard_state_path,
        snapshot_history_path=settings.storage.snapshot_history_path,
    )

    app = FastAPI(title="MacroFlow", version="2.0.0")
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
                "headline": "Macro intelligence para decisão e execução disciplinada",
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
