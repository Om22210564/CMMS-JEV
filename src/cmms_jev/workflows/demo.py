"""End-to-end, read-only CP-400 decision-layer demonstration."""

from __future__ import annotations

from typing import Any

from ..data import CMMSRepository
from ..decisions.classification import classify_work_order
from ..decisions.duplicate import detect_duplicate
from ..decisions.inspection import disposition_inspection
from ..decisions.replenishment import assess_replenishment
from ..decisions.routing import route_work_order
from ..decisions.spare import assess_spare_relevance
from .handlers import (
    handle_classification,
    handle_duplicate,
    handle_inspection,
    handle_replenishment,
    handle_routing,
    handle_spare_relevance,
)


def run_cp400_demo(repository: CMMSRepository | None = None) -> dict[str, Any]:
    """Run the established CP-400 lifecycle plus its duplicate-detection scenario."""
    repository = repository or CMMSRepository()
    team_ids = set(repository.load("maintenance_teams.csv")["team_id"])

    inspection = disposition_inspection(repository.inspection_context("INSP-001"))
    work_order_context = repository.work_order_context("WO-002")
    classification = classify_work_order(work_order_context)
    routing = route_work_order(work_order_context)
    spare = assess_spare_relevance(repository.material_request_context("MR-001"))
    replenishment = assess_replenishment(repository.replenishment_context("P-102"))
    duplicate = detect_duplicate(
        {
            "primary": repository.work_order_context("WO-030"),
            "candidate": repository.work_order_context("WO-031"),
        }
    )
    return {
        "scenario": "CP-400 cooling-water pump",
        "mutates_data": False,
        "steps": [
            {"name": "inspection_disposition", "decision": inspection.to_dict(), "workflow": handle_inspection(inspection).to_dict()},
            {"name": "work_order_classification", "decision": classification.to_dict(), "workflow": handle_classification(classification).to_dict()},
            {"name": "work_order_routing", "decision": routing.to_dict(), "workflow": handle_routing(routing, team_ids).to_dict()},
            {"name": "spare_part_relevance", "decision": spare.to_dict(), "workflow": handle_spare_relevance(spare).to_dict()},
            {"name": "replenishment_attention", "decision": replenishment.to_dict(), "workflow": handle_replenishment(replenishment).to_dict()},
            {"name": "duplicate_detection", "decision": duplicate.to_dict(), "workflow": handle_duplicate(duplicate).to_dict()},
        ],
    }
