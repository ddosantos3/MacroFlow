import json
from pathlib import Path
from typing import Any

import pandas as pd

from .domain import DashboardState, to_plain
from .indicators import remover_timezone_index, remover_timezone_series


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _safe_sheet_name(name: str) -> str:
    return name[:31]


class ArtifactStore:
    def __init__(self, excel_path: Path, dashboard_state_path: Path, snapshot_history_path: Path) -> None:
        self.excel_path = excel_path
        self.dashboard_state_path = dashboard_state_path
        self.snapshot_history_path = snapshot_history_path

    def save_dashboard_state(self, state: DashboardState | dict[str, Any]) -> None:
        plain = to_plain(state)
        _ensure_parent(self.dashboard_state_path)
        with self.dashboard_state_path.open("w", encoding="utf-8") as file:
            json.dump(plain, file, indent=2, ensure_ascii=False, allow_nan=False)

    def load_dashboard_state(self) -> dict[str, Any] | None:
        if not self.dashboard_state_path.exists():
            return None
        with self.dashboard_state_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def append_snapshot_history(self, snapshot: dict[str, Any]) -> None:
        plain = to_plain(snapshot)
        _ensure_parent(self.snapshot_history_path)
        with self.snapshot_history_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(plain, ensure_ascii=False, allow_nan=False) + "\n")

    def save_excel_artifacts(
        self,
        snapshot_row: dict[str, Any],
        intraday_frames: dict[str, pd.DataFrame],
        daily_frames: dict[str, pd.DataFrame],
    ) -> None:
        _ensure_parent(self.excel_path)
        mode = "a" if self.excel_path.exists() else "w"
        if_sheet_exists = "overlay" if self.excel_path.exists() else None

        with pd.ExcelWriter(
            self.excel_path,
            engine="openpyxl",
            mode=mode,
            if_sheet_exists=if_sheet_exists,
        ) as writer:
            self._write_snapshot_sheet(writer, snapshot_row)
            for name, frame in intraday_frames.items():
                self._write_frame(writer, _safe_sheet_name(f"OHLC4H_{name}"), frame)
            for name, frame in daily_frames.items():
                self._write_frame(writer, _safe_sheet_name(f"OHLC1D_{name}"), frame)

    def _write_snapshot_sheet(self, writer: pd.ExcelWriter, snapshot_row: dict[str, Any]) -> None:
        new_row = pd.DataFrame([to_plain(snapshot_row)])
        if self.excel_path.exists():
            try:
                existing = pd.read_excel(self.excel_path, sheet_name="SNAPSHOTS")
                final = pd.concat([existing, new_row], ignore_index=True)
            except Exception:
                final = new_row
        else:
            final = new_row
        final.to_excel(writer, sheet_name="SNAPSHOTS", index=False)

    def _write_frame(self, writer: pd.ExcelWriter, sheet_name: str, frame: pd.DataFrame) -> None:
        df = frame.copy()
        if df.empty:
            pd.DataFrame().to_excel(writer, sheet_name=sheet_name, index=False)
            return
        df.index = remover_timezone_index(df.index)
        df = df.reset_index()
        if "DataHora" not in df.columns and len(df.columns) > 0:
            df = df.rename(columns={df.columns[0]: "DataHora"})
        if "DataHora" in df.columns:
            df["DataHora"] = remover_timezone_series(df["DataHora"])
        for column in df.select_dtypes(include=["datetimetz"]).columns:
            df[column] = remover_timezone_series(df[column])
        df.to_excel(writer, sheet_name=sheet_name, index=False)
