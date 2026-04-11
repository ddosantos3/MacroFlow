from pathlib import Path

from fastapi.testclient import TestClient

from src.macroflow.api import create_app
from src.macroflow.config import AppSettings, JarvisConfig, MarketConfig, StorageConfig


def test_dashboard_endpoint_returns_empty_state(tmp_path: Path) -> None:
    settings = AppSettings(
        storage=StorageConfig(
            project_root=tmp_path,
            runtime_dir=tmp_path,
            excel_path=tmp_path / "MacroFlow_Dados.xlsx",
            dashboard_state_path=tmp_path / "dashboard_state.json",
            snapshot_history_path=tmp_path / "snapshots.jsonl",
        ),
        market=MarketConfig(),
    )
    client = TestClient(create_app(settings))

    response = client.get("/api/dashboard")
    payload = response.json()

    assert response.status_code == 200
    assert payload["summary"]["blocked"] is True
    assert payload["macro_context"]["regime"] == "NEUTRO"
    assert payload["settings_panel"]["operational_button_label"] == "Iniciar Macroflow"


def test_root_page_renders_dashboard_shell(tmp_path: Path) -> None:
    settings = AppSettings(
        storage=StorageConfig(
            project_root=tmp_path,
            runtime_dir=tmp_path,
            excel_path=tmp_path / "MacroFlow_Dados.xlsx",
            dashboard_state_path=tmp_path / "dashboard_state.json",
            snapshot_history_path=tmp_path / "snapshots.jsonl",
        ),
        market=MarketConfig(),
    )
    client = TestClient(create_app(settings))

    response = client.get("/")

    assert response.status_code == 200
    assert "MacroFlow" in response.text
    assert "Menu Principal" in response.text
    assert "Configurações" in response.text
    assert "jarvis-toggle" in response.text
    assert "styles.css?v=" in response.text
    assert "app.js?v=" in response.text


def test_settings_endpoint_returns_groups(tmp_path: Path) -> None:
    settings = AppSettings(
        storage=StorageConfig(
            project_root=tmp_path,
            runtime_dir=tmp_path,
            excel_path=tmp_path / "MacroFlow_Dados.xlsx",
            dashboard_state_path=tmp_path / "dashboard_state.json",
            snapshot_history_path=tmp_path / "snapshots.jsonl",
        ),
        market=MarketConfig(),
    )
    client = TestClient(create_app(settings))

    response = client.get("/api/settings")
    payload = response.json()

    assert response.status_code == 200
    assert payload["operational_button_label"] == "Iniciar Macroflow"
    assert len(payload["groups"]) >= 3


def test_settings_endpoint_persists_values(tmp_path: Path) -> None:
    settings = AppSettings(
        storage=StorageConfig(
            project_root=tmp_path,
            runtime_dir=tmp_path,
            excel_path=tmp_path / "MacroFlow_Dados.xlsx",
            dashboard_state_path=tmp_path / "dashboard_state.json",
            snapshot_history_path=tmp_path / "snapshots.jsonl",
        ),
        market=MarketConfig(),
    )
    client = TestClient(create_app(settings))

    response = client.post("/api/settings", json={"values": {"MACROFLOW_SCORE_MINIMO_OPERAR": "70"}})
    payload = response.json()

    assert response.status_code == 200
    assert payload["ok"] is True
    score_field = next(
        field
        for group in payload["settings"]["groups"]
        for field in group["fields"]
        if field["env"] == "MACROFLOW_SCORE_MINIMO_OPERAR"
    )
    assert score_field["value"] == "70"


def test_settings_endpoint_normalizes_numeric_yahoo_period(tmp_path: Path) -> None:
    settings = AppSettings(
        storage=StorageConfig(
            project_root=tmp_path,
            runtime_dir=tmp_path,
            excel_path=tmp_path / "MacroFlow_Dados.xlsx",
            dashboard_state_path=tmp_path / "dashboard_state.json",
            snapshot_history_path=tmp_path / "snapshots.jsonl",
        ),
        market=MarketConfig(),
    )
    client = TestClient(create_app(settings))

    response = client.post("/api/settings", json={"values": {"MACROFLOW_YAHOO_INTRADAY_PERIOD": "30"}})
    payload = response.json()

    assert response.status_code == 200
    period_field = next(
        field
        for group in payload["settings"]["groups"]
        for field in group["fields"]
        if field["env"] == "MACROFLOW_YAHOO_INTRADAY_PERIOD"
    )
    assert period_field["value"] == "30d"


def test_health_endpoint_exposes_artifact_paths(tmp_path: Path) -> None:
    settings = AppSettings(
        storage=StorageConfig(
            project_root=tmp_path,
            runtime_dir=tmp_path,
            excel_path=tmp_path / "MacroFlow_Dados.xlsx",
            dashboard_state_path=tmp_path / "dashboard_state.json",
            snapshot_history_path=tmp_path / "snapshots.jsonl",
        ),
        market=MarketConfig(),
    )
    client = TestClient(create_app(settings))

    response = client.get("/health")
    payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "ok"
    assert str(tmp_path / "MacroFlow_Dados.xlsx") == payload["excel_path"]


def test_jarvis_chat_endpoint_uses_local_snapshot(tmp_path: Path) -> None:
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("Voce e o Jarvis de teste.", encoding="utf-8")
    settings = AppSettings(
        storage=StorageConfig(
            project_root=tmp_path,
            runtime_dir=tmp_path,
            excel_path=tmp_path / "MacroFlow_Dados.xlsx",
            dashboard_state_path=tmp_path / "dashboard_state.json",
            snapshot_history_path=tmp_path / "snapshots.jsonl",
        ),
        market=MarketConfig(),
        jarvis=JarvisConfig(prompt_path=prompt_path),
    )
    client = TestClient(create_app(settings))

    response = client.post("/api/jarvis/chat", json={"message": "Qual o vies agora?", "history": []})
    payload = response.json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["mode"] == "local"
    assert "Jarvis" in payload["reply"]
