"""Spare-part relevance decision."""

from __future__ import annotations

from typing import Any

from ..jev import decide_choice
from ..models import RelevanceDecision


SPARE_CRITERIA = {
    "RELEVANT": "The requested item is supported by the asset, fault, and maintenance context.",
    "NOT_RELEVANT": "The item does not address the maintenance problem or is a misleading near match.",
}


def assess_spare_relevance(context: dict[str, Any]) -> RelevanceDecision:
    result = decide_choice(
        state=context,
        question="spare_relevance",
        instructions="Decide whether the requested item is relevant to the maintenance need.",
        criteria=SPARE_CRITERIA,
    )
    request = context.get("material_request")
    if request:
        evidence = {"request_id": request["request_id"], "item_id": request["item_id"]}
    else:
        evidence = {
            "work_order_id": context["work_order_context"]["work_order"]["work_order_id"],
            "item_id": context["candidate_item"]["item_id"],
        }
    return RelevanceDecision(
        is_relevant=result.decision == "RELEVANT",
        confidence=result.confidence,
        question=result.question,
        model=result.model,
        rationale="Jev returned a constrained relevance decision from the request and CMMS context.",
        evidence=evidence,
    )
