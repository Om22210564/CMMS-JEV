"""Minimal synchronous TypeSafe AI Jev choice adapter."""

from __future__ import annotations

from typing import Any, Mapping

from .config import Settings
from .models import DecisionResult


class JevConfigurationError(RuntimeError):
    """Raised when a live Jev call cannot be configured locally."""


class JevCallError(RuntimeError):
    """Raised when the SDK cannot complete a Jev decision."""


def decide_choice(
    *,
    state: Mapping[str, Any],
    question: str,
    instructions: str,
    criteria: Mapping[str, str],
    settings: Settings | None = None,
) -> DecisionResult:
    """Ask Jev one constrained choice question and validate its typed answer."""
    settings = settings or Settings.from_environment()
    if not settings.api_key:
        raise JevConfigurationError(
            "TYPESAFE_API_KEY is required for a live Jev call. "
            "Use --dry-run to inspect the deterministic payload."
        )
    try:
        from typesafe_sdk import Choice, TypeSafeClient
    except ImportError as exc:
        raise JevConfigurationError(
            "typesafe-sdk is not installed. Install the project dependencies first."
        ) from exc

    try:
        with TypeSafeClient() as client:
            request: dict[str, Any] = {
                "state": dict(state),
                "questions": {
                    question: Choice(
                        instructions=instructions,
                        criteria=dict(criteria),
                    )
                },
            }
            if settings.model:
                request["model"] = settings.model
            response = client.system_one(**request)
            answer = response.choices[question]
            result = DecisionResult(
                decision=str(answer.choice),
                confidence=float(answer.confidence),
                question=question,
                model=settings.model,
            )
    except JevConfigurationError:
        raise
    except Exception as exc:  # SDK/network errors are surfaced without state changes.
        raise JevCallError(f"Jev choice call failed: {exc}") from exc

    return result.validate(criteria)
