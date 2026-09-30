"""Small typed boundary between Jev answers and deterministic Python."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping


class DecisionValidationError(ValueError):
    """Raised when an SDK response cannot be used by a CMMS workflow."""


@dataclass(frozen=True)
class DecisionResult:
    decision: str
    confidence: float
    question: str
    model: str | None = None

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

    def to_dict(self) -> dict[str, str | float | None]:
        return asdict(self)
