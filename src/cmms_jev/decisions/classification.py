"""First minimal CMMS decision: classify a work order."""

from __future__ import annotations

from typing import Any

from ..jev import decide_choice
from ..models import DecisionResult


CLASSIFICATION_CRITERIA = {
    "MECHANICAL": "Rotating equipment, hydraulics, pneumatics, seals, belts, bearings, or other physical mechanisms.",
    "ELECTRICAL": "Power, motors, VFDs, MCCs, wiring, electrical protection, or electrical heat faults.",
    "INSTRUMENTATION": "Sensors, transmitters, PLC/control feedback, calibration, or measurement disagreement.",
    "GENERAL": "Routine or general maintenance not better explained by the specialist categories.",
}


def classify_work_order(context: dict[str, Any]) -> DecisionResult:
    result = decide_choice(
        state=context,
        question="classification",
        instructions=(
            "Classify the maintenance problem from the work order, asset, and location context. "
            "Use the most specific supported maintenance domain."
        ),
        criteria=CLASSIFICATION_CRITERIA,
    )
    return result.with_evidence(
        work_order_id=context["work_order"]["work_order_id"],
        asset_id=context["asset"]["asset_id"],
    )
