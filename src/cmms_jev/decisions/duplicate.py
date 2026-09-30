"""Contextual duplicate work-order detection."""

from __future__ import annotations

from typing import Any

from ..jev import decide_choice
from ..models import DuplicateDecision


DUPLICATE_CRITERIA = {
    "DUPLICATE": "The records describe the same unresolved maintenance event.",
    "NOT_DUPLICATE": "The records are separate events, assets, components, or maintenance cycles.",
}


def detect_duplicate(context: dict[str, Any]) -> DuplicateDecision:
    result = decide_choice(
        state=context,
        question="duplicate_detection",
        instructions="Decide whether these two work orders represent the same maintenance event.",
        criteria=DUPLICATE_CRITERIA,
    )
    primary = context["primary"]["work_order"]["work_order_id"]
    candidate = context["candidate"]["work_order"]["work_order_id"]
    duplicate = result.decision == "DUPLICATE"
    return DuplicateDecision(
        is_duplicate=duplicate,
        matched_work_order_id=candidate if duplicate else None,
        confidence=result.confidence,
        question=result.question,
        model=result.model,
        rationale="Jev returned a constrained duplicate decision from the two CMMS contexts.",
        evidence={"primary_work_order_id": primary, "candidate_work_order_id": candidate},
    )
