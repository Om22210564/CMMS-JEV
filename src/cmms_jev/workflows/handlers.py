"""Deterministic workflow actions derived from validated Jev decisions.

These handlers deliberately return proposed workflow actions. They do not mutate
the synthetic CSV source of record.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from ..models import DecisionResult, DuplicateDecision, RelevanceDecision


@dataclass(frozen=True)
class WorkflowOutcome:
    action: str
    accepted: bool
    decision: str
    confidence: float
    evidence: dict[str, str]
    reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def handle_classification(result: DecisionResult) -> WorkflowOutcome:
    return WorkflowOutcome(
        action="CLASSIFY_WORK_ORDER",
        accepted=True,
        decision=result.decision,
        confidence=result.confidence,
        evidence=result.evidence,
        reason="Validated constrained classification is available for the work-order workflow.",
    )


def handle_routing(result: DecisionResult, valid_team_ids: set[str]) -> WorkflowOutcome:
    accepted = result.decision in valid_team_ids
    return WorkflowOutcome(
        action="PROPOSE_TEAM_ASSIGNMENT" if accepted else "FLAG_INVALID_TEAM_DECISION",
        accepted=accepted,
        decision=result.decision,
        confidence=result.confidence,
        evidence=result.evidence,
        reason=(
            "Selected maintenance team is present in the CMMS team master."
            if accepted
            else "Selected maintenance team is not present in the CMMS team master."
        ),
    )


def handle_duplicate(result: DuplicateDecision) -> WorkflowOutcome:
    accepted = result.is_duplicate and result.confidence >= 0.7
    return WorkflowOutcome(
        action="FLAG_POSSIBLE_DUPLICATE" if accepted else "KEEP_SEPARATE_WORK_ORDERS",
        accepted=accepted,
        decision="DUPLICATE" if result.is_duplicate else "NOT_DUPLICATE",
        confidence=result.confidence,
        evidence=result.evidence,
        reason=(
            "Duplicate is above the deterministic review threshold."
            if accepted
            else "No sufficiently confident duplicate link will be proposed."
        ),
    )


def handle_inspection(result: DecisionResult) -> WorkflowOutcome:
    actions = {
        "REQUIRES_WORK_ORDER": "FLAG_CORRECTIVE_WORK_ORDER_REQUIRED",
        "MONITOR": "ADD_TO_INSPECTION_MONITORING",
        "NO_ACTION_NEEDED": "CLOSE_INSPECTION_WITHOUT_ACTION",
    }
    return WorkflowOutcome(
        action=actions[result.decision],
        accepted=True,
        decision=result.decision,
        confidence=result.confidence,
        evidence=result.evidence,
        reason="Inspection disposition maps to a deterministic non-mutating CMMS action.",
    )


def handle_spare_relevance(result: RelevanceDecision) -> WorkflowOutcome:
    return WorkflowOutcome(
        action="ACCEPT_MATERIAL_REQUEST" if result.is_relevant else "FLAG_MATERIAL_REQUEST",
        accepted=result.is_relevant,
        decision="RELEVANT" if result.is_relevant else "NOT_RELEVANT",
        confidence=result.confidence,
        evidence=result.evidence,
        reason="Only relevant spares progress without planner review.",
    )


def handle_replenishment(result: DecisionResult) -> WorkflowOutcome:
    action = {
        "REQUIRES_ATTENTION": "RAISE_REPLENISHMENT_ATTENTION",
        "MONITOR": "MONITOR_INVENTORY_POSITION",
        "HEALTHY": "NO_REPLENISHMENT_ACTION",
    }[result.decision]
    return WorkflowOutcome(
        action=action,
        accepted=result.decision != "REQUIRES_ATTENTION",
        decision=result.decision,
        confidence=result.confidence,
        evidence=result.evidence,
        reason="Jev attention level is translated into a deterministic planner action.",
    )
