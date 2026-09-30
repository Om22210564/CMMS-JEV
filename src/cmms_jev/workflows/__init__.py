"""Deterministic workflow boundary. No workflow mutates CSV data directly."""

from .handlers import WorkflowOutcome
from .demo import run_cp400_demo

__all__ = ["WorkflowOutcome", "run_cp400_demo"]
