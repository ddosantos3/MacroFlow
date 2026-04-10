from datetime import date

from src.macroflow.config import AppSettings, CalendarConfig, StorageConfig
from src.macroflow.economic_calendar import fetch_economic_calendar


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> list[dict[str, object]]:
        return [
            {
                "CalendarId": "1",
                "Date": "2026-04-10T12:30:00",
                "Country": "United States",
                "Category": "Inflation Rate",
                "Event": "Core CPI YoY",
                "Actual": "3.4%",
                "Forecast": "3.1%",
                "Previous": "3.0%",
                "Importance": 3,
                "Source": "Trading Economics",
                "URL": "/united-states/core-inflation-rate",
            },
            {
                "CalendarId": "2",
                "Date": "2026-04-10T13:00:00",
                "Country": "Brazil",
                "Category": "Business",
                "Event": "Low impact survey",
                "Actual": "",
                "Forecast": "",
                "Previous": "",
                "Importance": 1,
            },
        ]


def test_fetch_economic_calendar_normalizes_events_and_bias(monkeypatch) -> None:
    monkeypatch.setattr("src.macroflow.economic_calendar.requests.get", lambda *args, **kwargs: FakeResponse())
    settings = AppSettings(
        calendar=CalendarConfig(
            provider="tradingeconomics",
            countries="United States,Brazil",
            importance_min=2,
            days_back=0,
            days_ahead=1,
            max_events=10,
        )
    )

    payload = fetch_economic_calendar(settings, today=date(2026, 4, 10))

    assert payload["ok"] is True
    assert payload["status"] == "online"
    assert len(payload["events"]) == 1
    event = payload["events"][0]
    assert event["country"] == "United States"
    assert event["importance"] == 3
    assert event["market_bias"] == "risk_off"
    assert event["theme"] == "inflation"
    assert payload["risk_bias"] == "risk_off"


def test_fetch_economic_calendar_returns_safe_payload_on_failure(monkeypatch, tmp_path) -> None:
    def raise_error(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr("src.macroflow.economic_calendar.requests.get", raise_error)

    payload = fetch_economic_calendar(
        AppSettings(
            storage=StorageConfig(
                project_root=tmp_path,
                runtime_dir=tmp_path,
                excel_path=tmp_path / "MacroFlow_Dados.xlsx",
                dashboard_state_path=tmp_path / "dashboard_state.json",
                snapshot_history_path=tmp_path / "snapshots.jsonl",
            )
        ),
        today=date(2026, 4, 10),
    )

    assert payload["ok"] is False
    assert payload["status"] == "indisponivel"
    assert payload["events"] == []


def test_fetch_forexfactory_calendar_maps_impact_to_bulls(monkeypatch) -> None:
    class ForexFactoryResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, object]]:
            return [
                {
                    "title": "CPI m/m",
                    "country": "USD",
                    "date": "2026-04-10T08:30:00-04:00",
                    "impact": "High",
                    "forecast": "0.3%",
                    "previous": "0.2%",
                }
            ]

    monkeypatch.setattr(
        "src.macroflow.economic_calendar.requests.get",
        lambda *args, **kwargs: ForexFactoryResponse(),
    )
    settings = AppSettings(
        calendar=CalendarConfig(
            provider="forexfactory",
            countries="United States",
            importance_min=1,
            days_back=0,
            days_ahead=1,
        )
    )

    payload = fetch_economic_calendar(settings, today=date(2026, 4, 10))

    assert payload["ok"] is True
    assert payload["source"] == "Fair Economy / Forex Factory"
    assert payload["events"][0]["country"] == "United States"
    assert payload["events"][0]["currency"] == "USD"
    assert payload["events"][0]["importance"] == 3
