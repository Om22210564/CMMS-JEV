"""Deterministic CSV loading and decision-context preparation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


class EntityNotFoundError(KeyError):
    """Raised when a requested CMMS entity does not exist."""


class CMMSRepository:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parents[2]
        self.data_dir = self.root / "data"

    def load(self, filename: str) -> pd.DataFrame:
        path = self.data_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"CMMS data file not found: {path}")
        return pd.read_csv(path, dtype=str, keep_default_na=False)

    def operational_work_orders(self) -> pd.DataFrame:
        filename = (
            "work_orders_merged.csv"
            if (self.data_dir / "work_orders_merged.csv").exists()
            else "work_orders.csv"
        )
        return self.load(filename)

    @staticmethod
    def _record(frame: pd.DataFrame, key: str, value: str) -> dict[str, str]:
        matches = frame.loc[frame[key] == value]
        if matches.empty:
            raise EntityNotFoundError(f"No {key}={value!r} record exists")
        return matches.iloc[0].to_dict()

    def work_order_context(self, work_order_id: str) -> dict[str, Any]:
        work_order = self._record(
            self.operational_work_orders(), "work_order_id", work_order_id
        )
        asset = self._record(self.load("assets.csv"), "asset_id", work_order["asset_id"])
        location = self._record(
            self.load("locations.csv"), "location_id", work_order["location_id"]
        )
        return {
            "work_order": work_order,
            "asset": asset,
            "location": location,
        }
