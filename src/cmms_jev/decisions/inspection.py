"""Inspection finding disposition."""

from __future__ import annotations

from typing import Any

from ..jev import decide_choice
from ..models import DecisionResult


INSPECTION_CRITERIA = {
    "NO_ACTION_NEEDED": "Finding is acceptable or a false-positive-looking observation with no maintenance action needed.",
    "MONITOR": "Finding warrants a planned recheck or trend monitoring but not immediate corrective work.",
    "REQUIRES_WORK_ORDER": "Finding warrants corrective maintenance attention.",
}


def disposition_inspection(context: dict[str, Any]) -> DecisionResult:
    result = decide_choice(
        state=context,
        question="inspection_disposition",
        instructions="Choose the appropriate disposition for this inspection finding.",
        criteria=INSPECTION_CRITERIA,
    )
    return result.with_evidence(
        inspection_id=context["inspection"]["inspection_id"],
        asset_id=context["asset"]["asset_id"],
    )
