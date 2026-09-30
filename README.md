# CMMS + Jev

A small, terminal-first synthetic CMMS decision system powered by TypeSafe AI
Jev. The CSV dataset is the operational source of truth; Jev supplies
constrained semantic judgments where maintenance language is ambiguous.

## Problem

Maintenance reports mix symptoms, equipment context, and operator language.
For example, a pump trip can sound electrical while the underlying bearing
failure is mechanical. This project separates that semantic judgment from the
deterministic CMMS controls that validate and act on it.

## Six Jev decisions

### Why use Jev / an LLM?

The CMMS already has deterministic facts: IDs, timestamps, stock quantities,
approved quantities, team records, and compatibility records. Python validates
and calculates those facts reliably. What rules alone cannot robustly resolve
is the meaning of inconsistent human language in context: whether a "trip" is
an electrical issue or the effect of a seized bearing; whether two differently
worded reports describe the same event; or whether two similar-looking parts
are functionally interchangeable.

Jev is used only for that bounded semantic step. Each call receives prepared
CMMS context and must choose from a small allowed vocabulary. Python validates
the result against real CMMS entities and turns it into a non-mutating workflow
proposal. It does not let an LLM calculate inventory, create records, or update
the source CSVs.

| Decision | Maintenance problem | Why Jev helps | Deterministic workflow boundary |
| --- | --- | --- | --- |
| Work-order classification | Operator descriptions may mention heat, alarms, or noise without identifying the responsible maintenance domain. | Interprets symptoms with asset and failure context to choose `MECHANICAL`, `ELECTRICAL`, `INSTRUMENTATION`, or `GENERAL`. | Validates the constrained class before making it available to the work-order workflow. |
| Work-order routing | The right destination depends on the responsible subsystem, not the most obvious surface keyword. | Resolves mixed evidence into one existing maintenance team, such as `TEAM-MECH` for the CP-400 bearing scenario. | Verifies the selected team exists before proposing assignment. |
| Duplicate detection | Two reports can describe one fault using different terms; conversely, the same wording can be recurring but distinct events. | Compares asset, location, timing, symptoms, and descriptions semantically. | Only flags a possible duplicate at or above the deterministic confidence threshold; it never merges work orders. |
| Inspection finding disposition | A reading may be abnormal, borderline, or misleading without the finding text explicitly saying what action is needed. | Weighs finding, severity, measurement, PM context, and recent maintenance history. | Maps the decision to flag corrective work, monitor, or close without creating a work order automatically. |
| Spare-part relevance | Part names can be close but incompatible, while some compatible parts require contextual interpretation. | Assesses the work-order fault, asset model, candidate item, and compatibility evidence together. | Accepts a relevant request or flags it for planner review; no inventory is issued. |
| Replenishment attention | Low stock alone is insufficient: reserved stock, open demand, incoming orders, lead time, and criticality change the urgency. | Interprets the significance of deterministic inventory facts as `REQUIRES_ATTENTION`, `MONITOR`, or `HEALTHY`. | Python calculates all quantities; Jev only produces a planner-attention proposal. |

## Architecture

```text
CMMS Data
   ↓
Deterministic Context Preparation
   ↓
Jev constrained semantic decision
   ↓
Python validation and business rules
   ↓
Proposed CMMS workflow action
```

> Jev provides semantic decisions; deterministic Python validates and executes
> CMMS workflows.

No Jev decision writes to the CMMS CSVs. Workflow commands return structured,
proposed actions only.

## CP-400 end-to-end scenario

The built-in cooling-water pump scenario demonstrates the decision layer:

```text
CP-400 vibration inspection
   ↓  REQUIRES_WORK_ORDER
WO-002 bearing-fault classification
   ↓  MECHANICAL
Maintenance-team routing
   ↓  TEAM-MECH
Bearing-request relevance
   ↓  RELEVANT
P-102 inventory attention
   ↓  REQUIRES_ATTENTION
```

The same demo also evaluates the established `WO-030` / `WO-031` duplicate
pair and flags it for review. Run it with:

```bash
python -m cmms_jev demo cp-400
```

## Evaluation

Each decision has a 30-case evaluation dataset with EASY, MEDIUM, and HARD
cases. The complete captured live output is available in
[artifacts/results.txt](artifacts/results.txt). The latest captured live run
reported:

| Decision | Correct | Accuracy |
| --- | ---: | ---: |
| Classification | 28 / 30 | 93.3% |
| Routing | 30 / 30 | 100.0% |
| Duplicate detection | 25 / 30 | 83.3% |
| Inspection disposition | 29 / 30 | 96.7% |
| Spare relevance | 20 / 30 | 66.7% |
| Replenishment attention | 25 / 30 | 83.3% |

The captured results intentionally retain visible improvement areas. In
particular, spare relevance is weak on HARD near-match cases, and replenishment
is weakest on MEDIUM borderline cases. That is why Jev outputs remain proposals
inside deterministic CMMS controls rather than autonomous state changes. Run
any evaluation to obtain current metrics and representative failures:

```bash
python -m cmms_jev evaluate classification
python -m cmms_jev evaluate routing
python -m cmms_jev evaluate duplicate_detection
python -m cmms_jev evaluate inspection_disposition
python -m cmms_jev evaluate spare_relevance
python -m cmms_jev evaluate replenishment
```

Each command makes one Jev call per case and prints total cases, accuracy,
difficulty breakdown, and up to five representative failures.

## Run the project

Create the environment and install the project:

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
export TYPESAFE_API_KEY="..."
```

Run individual decisions:

```bash
python -m cmms_jev classify WO-001
python -m cmms_jev route WO-001
python -m cmms_jev duplicate WO-030 WO-031
python -m cmms_jev inspect INSP-001
python -m cmms_jev spare MR-001
python -m cmms_jev replenish P-102
```

Append `--dry-run` to any individual-decision command to inspect its
deterministic context and criteria without calling Jev.

Validate the underlying CMMS dataset separately:

```bash
python audit_dataset.py
```
