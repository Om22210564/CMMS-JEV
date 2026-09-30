"""Inventory replenishment-attention decision."""

from __future__ import annotations

from typing import Any

from ..jev import decide_choice
from ..models import DecisionResult


REPLENISHMENT_CRITERIA = {
    "REQUIRES_ATTENTION": "Inventory risk needs procurement or planner attention.",
    "MONITOR": "Inventory is borderline or context-dependent and should be watched.",
    "HEALTHY": "Inventory context does not currently require attention.",
}


def assess_replenishment(context: dict[str, Any]) -> DecisionResult:
    result = decide_choice(
        state=context,
        question="replenishment_attention",
        instructions="Interpret the deterministic inventory facts and choose the appropriate attention level.",
        criteria=REPLENISHMENT_CRITERIA,
    )
    return result.with_evidence(item_id=context["inventory_item"]["item_id"])
