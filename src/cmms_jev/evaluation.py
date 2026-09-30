"""Small, transparent runner for the six CMMS Jev evaluation CSVs."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from .data import CMMSRepository
from .decisions.classification import classify_work_order
from .decisions.duplicate import detect_duplicate
from .decisions.inspection import disposition_inspection
from .decisions.replenishment import assess_replenishment
from .decisions.routing import route_work_order
from .decisions.spare import assess_spare_relevance


EVALUATION_FILES = {
    "classification": "evaluation_classification.csv",
    "routing": "evaluation_routing.csv",
    "duplicate_detection": "evaluation_duplicate_detection.csv",
    "inspection_disposition": "evaluation_inspection_disposition.csv",
    "spare_relevance": "evaluation_spare_relevance.csv",
    "replenishment": "evaluation_replenishment.csv",
}


@dataclass(frozen=True)
class EvaluationSummary:
    decision: str
    total_cases: int
    correct: int
    incorrect: int
    accuracy: float
    by_difficulty: dict[str, dict[str, int | float]]
    representative_failures: list[dict[str, str]]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _actual_decision(task: str, row: dict[str, str], repository: CMMSRepository) -> str:
    if task == "classification":
        return classify_work_order(repository.work_order_context(row["input_wo_id"])).decision
    if task == "routing":
        return route_work_order(repository.work_order_context(row["input_wo_id"])).decision
    if task == "duplicate_detection":
        result = detect_duplicate(
            {
                "primary": repository.work_order_context(row["input_wo_id_1"]),
                "candidate": repository.work_order_context(row["input_wo_id_2"]),
            }
        )
        return "DUPLICATE" if result.is_duplicate else "NOT_DUPLICATE"
    if task == "inspection_disposition":
        return disposition_inspection(repository.inspection_context(row["input_inspection_id"])).decision
    if task == "spare_relevance":
        result = assess_spare_relevance(
            repository.spare_candidate_context(
                row["work_order_id"], row["candidate_item_id"]
            )
        )
        return "RELEVANT" if result.is_relevant else "NOT_RELEVANT"
    if task == "replenishment":
        return assess_replenishment(repository.replenishment_context(row["item_id"])).decision
    raise ValueError(f"Unsupported evaluation task: {task}")


def run_evaluation(
    task: str,
    repository: CMMSRepository | None = None,
    decision_runner: Callable[[str, dict[str, str], CMMSRepository], str] = _actual_decision,
) -> EvaluationSummary:
    """Run one live Jev evaluation set and return concise deterministic metrics."""
    if task not in EVALUATION_FILES:
        raise ValueError(f"Unsupported evaluation task: {task}")
    repository = repository or CMMSRepository()
    path = repository.root / "evaluation" / EVALUATION_FILES[task]
    cases = pd.read_csv(path, dtype=str, keep_default_na=False).to_dict("records")
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "correct": 0})
    failures: list[dict[str, str]] = []
    correct = 0
    for row in cases:
        actual = decision_runner(task, row, repository)
        passed = actual == row["expected_decision"]
        difficulty = row["difficulty"]
        counts[difficulty]["total"] += 1
        counts[difficulty]["correct"] += int(passed)
        correct += int(passed)
        if not passed and len(failures) < 5:
            failures.append(
                {
                    "case_id": row["case_id"],
                    "expected": row["expected_decision"],
                    "actual": actual,
                    "difficulty": difficulty,
                }
            )
    total = len(cases)
    by_difficulty = {
        difficulty: {
            "total": values["total"],
            "correct": values["correct"],
            "incorrect": values["total"] - values["correct"],
            "accuracy": values["correct"] / values["total"],
        }
        for difficulty, values in sorted(counts.items())
    }
    return EvaluationSummary(
        decision=task,
        total_cases=total,
        correct=correct,
        incorrect=total - correct,
        accuracy=correct / total if total else 0.0,
        by_difficulty=by_difficulty,
        representative_failures=failures,
    )
