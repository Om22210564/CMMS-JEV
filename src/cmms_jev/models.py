"""Small typed boundary between Jev answers and deterministic Python."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Mapping


class DecisionValidationError(ValueError):
    """Raised when an SDK response cannot be used by a CMMS workflow."""


@dataclass(frozen=True)
class DecisionResult:
    decision: str
    confidence: float
    question: str
    model: str | None = None
    rationale: str | None = None
    evidence: dict[str, str] = field(default_factory=dict)

    def validate(self, criteria: Mapping[str, str]) -> "DecisionResult":
        if self.decision not in criteria:
            raise DecisionValidationError(
                f"Decision {self.decision!r} is not one of {sorted(criteria)}"
            )
        if not 0.0 <= self.confidence <= 1.0:
            raise DecisionValidationError(
                f"Confidence must be between 0 and 1, got {self.confidence!r}"
            )
        return self

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def with_evidence(self, **evidence: str) -> "DecisionResult":
        """Attach deterministic context identifiers without changing Jev's choice."""
        return replace(
            self,
            rationale=(
                "Jev returned a constrained choice; inspect the linked CMMS "
                "entities for the deterministic evidence context."
            ),
            evidence=evidence,
        )


@dataclass(frozen=True)
class DuplicateDecision:
    is_duplicate: bool
    matched_work_order_id: str | None
    confidence: float
    question: str
    model: str | None = None
    rationale: str | None = None
    evidence: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RelevanceDecision:
    is_relevant: bool
    confidence: float
    question: str
    model: str | None = None
    rationale: str | None = None
    evidence: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
