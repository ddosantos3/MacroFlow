from pathlib import Path

from fastapi.testclient import TestClient

from src.macroflow.api import create_app
from src.macroflow.config import AppSettings, MarketConfig, StorageConfig


def test_dashboard_endpoint_returns_empty_state(tmp_path: Path) -> None:
    settings = AppSettings(
        storage=StorageConfig(
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


def test_root_page_renders_dashboard_shell(tmp_path: Path) -> None:
    settings = AppSettings(
        storage=StorageConfig(
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
    assert "Command Center" in response.text


def test_health_endpoint_exposes_artifact_paths(tmp_path: Path) -> None:
    settings = AppSettings(
        storage=StorageConfig(
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
