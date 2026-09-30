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

    def inspection_context(self, inspection_id: str) -> dict[str, Any]:
        inspection = self._record(
            self.load("inspections.csv"), "inspection_id", inspection_id
        )
        asset = self._record(self.load("assets.csv"), "asset_id", inspection["asset_id"])
        context: dict[str, Any] = {"inspection": inspection, "asset": asset}
        if inspection["pm_execution_id"]:
            execution = self._record(
                self.load("pm_executions.csv"),
                "pm_execution_id",
                inspection["pm_execution_id"],
            )
            context["pm_execution"] = execution
            context["pm_plan"] = self._record(
                self.load("pm_plans.csv"), "pm_plan_id", execution["pm_plan_id"]
            )
        return context

    def material_request_context(self, request_id: str) -> dict[str, Any]:
        request = self._record(
            self.load("material_requests.csv"), "request_id", request_id
        )
        item = self._record(self.load("inventory_items.csv"), "item_id", request["item_id"])
        context: dict[str, Any] = {"material_request": request, "item": item}
        if request["work_order_id"]:
            context["work_order_context"] = self.work_order_context(request["work_order_id"])
        return context

    def replenishment_context(self, item_id: str) -> dict[str, Any]:
        item = self._record(self.load("inventory_items.csv"), "item_id", item_id)
        requests = self.load("material_requests.csv")
        open_requests = requests[
            (requests["item_id"] == item_id)
            & (requests["status"] == "APPROVED")
        ].copy()
        open_requests["remaining_quantity"] = (
            pd.to_numeric(open_requests["quantity_approved"])
            - pd.to_numeric(open_requests["quantity_issued"])
        )
        orders = self.load("purchase_orders.csv")
        lines = self.load("purchase_order_lines.csv")
        incoming = lines.merge(orders[["po_id", "status"]], on="po_id")
        incoming = incoming[
            (incoming["item_id"] == item_id)
            & incoming["status"].isin({"CREATED", "SENT_TO_SUPPLIER", "PARTIALLY_RECEIVED"})
        ]
        return {
            "inventory_item": item,
            "deterministic_inventory_facts": {
                "available_quantity": str(
                    int(item["quantity_on_hand"]) - int(item["quantity_reserved"])
                ),
                "open_approved_demand": str(
                    int(open_requests["remaining_quantity"].sum())
                ),
                "incoming_order_quantity": str(
                    int(pd.to_numeric(incoming["order_quantity"]).sum())
                ),
                "open_request_ids": open_requests["request_id"].tolist(),
                "incoming_po_ids": incoming["po_id"].tolist(),
            },
        }
