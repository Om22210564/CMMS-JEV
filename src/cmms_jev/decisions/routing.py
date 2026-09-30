"""Semantic maintenance-team routing."""

from __future__ import annotations

from typing import Any

from ..jev import decide_choice
from ..models import DecisionResult


ROUTING_CRITERIA = {
    "TEAM-MECH": "Physical mechanisms, rotating equipment, hydraulics, pneumatics, bearings, belts, and seals.",
    "TEAM-ELEC": "Electrical power, motors, VFDs, MCCs, wiring, and protection.",
    "TEAM-INST": "Sensors, transmitters, PLC/control feedback, calibration, and measurement systems.",
    "TEAM-GEN": "Routine general maintenance not requiring a specialist domain.",
}


def route_work_order(context: dict[str, Any]) -> DecisionResult:
    result = decide_choice(
        state=context,
        question="routing",
        instructions="Route the work order from its technical evidence and asset context.",
        criteria=ROUTING_CRITERIA,
    )
    return result.with_evidence(
        work_order_id=context["work_order"]["work_order_id"],
        asset_id=context["asset"]["asset_id"],
    )
