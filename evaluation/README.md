# Evaluation Ground Truth

This directory contains deterministic human-labelled ground truth for evaluating the AI.

**Important Architecture Note:**
The labels in these files represent the _expected outputs_ of the Jev AI engine. They are purposefully omitted from the core CMMS CSV files so the AI cannot "cheat" by reading the answer.

**Difficulty Levels:**

- **EASY:** Direct keyword overlap (e.g., "Pump shaking" -> Mechanical).
- **MEDIUM:** Requires semantic inference (e.g., "Motor hot" -> Electrical, not mechanical friction).
- **HARD:** Requires synthesizing multiple tables (e.g., Replenishment relies on QOH, Safety Stock, open WOs, open POs, AND asset criticality).
