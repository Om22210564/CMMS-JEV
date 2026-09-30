#!/usr/bin/env python3
"""Deterministically normalize bulk work orders into the canonical CMMS schema.

This script intentionally does not alter any source dataset.  It is a small,
repeatable data-engineering boundary between the bulk generator and the
canonical work-order data used by the application.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import pandas as pd


DATA_DIR = Path("data")
CANONICAL_FILE = DATA_DIR / "work_orders.csv"
GENERATED_FILE = DATA_DIR / "work_orders_generated.csv"
MERGED_FILE = DATA_DIR / "work_orders_merged.csv"
REPORT_FILE = DATA_DIR / "work_orders_normalization_report.md"

GENERATED_REQUIRED_COLUMNS = [
    "work_order_id", "asset_id", "location_id", "work_order_type", "title",
    "description", "created_at", "requested_by", "assigned_team", "status",
    "failure_mode",
]
VALID_STATUSES = {"OPEN", "IN_PROGRESS", "ON_HOLD", "COMPLETED", "CANCELLED"}
# These aliases are intentionally limited to unambiguous vocabulary variants.
STATUS_ALIASES = {"PENDING": "OPEN", "IN-PROGRESS": "IN_PROGRESS", "ON HOLD": "ON_HOLD"}
FAILURE_CAUSES = {
    "BEARING_FAILURE": "COMPONENT_DEGRADATION",
    "BEARING_WEAR": "NORMAL_WEAR",
    "BELT_MISALIGNMENT": "MISALIGNMENT",
    "MOTOR_OVERHEATING": "OVERHEATING",
    "LUBRICATION_FAILURE": "INADEQUATE_LUBRICATION",
    "SEAL_FAILURE": "COMPONENT_DEGRADATION",
}


def read_csv(path: Path) -> pd.DataFrame:
    """Read strings exactly enough to preserve source field values and blanks."""
    if not path.exists():
        raise ValueError(f"Required file is missing: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def stable_pick(values: list[str], key: str) -> str:
    """Select an existing value reproducibly, independent of Python hash randomization."""
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return values[int(digest, 16) % len(values)]


def iso_timestamp(value: pd.Timestamp) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S")


def value_set(df: pd.DataFrame, column: str) -> set[str]:
    return {value for value in df[column].tolist() if value != ""}


def is_missing(value: str) -> bool:
    return value.strip().lower() in {"", "null", "none", "nan", "false"}


def sanitize_canonical_contracts(
    canonical: pd.DataFrame,
    manager_ids: list[str],
) -> tuple[pd.DataFrame, list[str]]:
    """Apply only operational contract repairs needed in merged output.

    Source CSVs are never changed.  These repairs make the operational merged
    file conform to the documented manager, verification, and cancellation
    contracts when curated source rows contain legacy placeholders.
    """
    sanitized = canonical.copy()
    changes: list[str] = []
    manager_set = set(manager_ids)

    for index, row in sanitized.iterrows():
        wo_id = row["work_order_id"]
        status = row["status"].strip().upper()
        created_at = pd.to_datetime(row["created_at"], errors="coerce", format="ISO8601")

        accepted_by = row["accepted_by"]
        if accepted_by and accepted_by not in manager_set:
            sanitized.at[index, "accepted_by"] = stable_pick(manager_ids, f"accepted:{wo_id}")
            changes.append(f"{wo_id}: replaced non-manager accepted_by {accepted_by!r} with a deterministic manager")

        if status == "COMPLETED":
            if is_missing(row["verified_at"]):
                if pd.isna(created_at):
                    changes.append(f"{wo_id}: cannot derive verified_at because created_at is invalid")
                else:
                    sanitized.at[index, "verified_at"] = iso_timestamp(created_at + pd.Timedelta(hours=2))
                    changes.append(f"{wo_id}: derived missing verified_at")
            if row["verified_by"] not in manager_set:
                sanitized.at[index, "verified_by"] = stable_pick(manager_ids, f"verified:{wo_id}")
                changes.append(f"{wo_id}: assigned deterministic verification manager")
        else:
            # Canonical non-completed rows have no explicit verification data.
            # Preserve any valid explicit value rather than inventing one.
            pass

        if status != "CANCELLED":
            if not is_missing(row["cancelled_at"]) or not is_missing(row["cancellation_reason"]):
                changes.append(f"{wo_id}: cleared cancellation fields for non-CANCELLED status")
            sanitized.at[index, "cancelled_at"] = ""
            sanitized.at[index, "cancellation_reason"] = ""
        else:
            cancelled_at = row["cancelled_at"]
            parsed_cancelled_at = pd.to_datetime(cancelled_at, errors="coerce", format="ISO8601")
            if is_missing(cancelled_at) or pd.isna(parsed_cancelled_at):
                if pd.isna(created_at):
                    changes.append(f"{wo_id}: cannot derive cancelled_at because created_at is invalid")
                else:
                    sanitized.at[index, "cancelled_at"] = iso_timestamp(created_at + pd.Timedelta(hours=1))
                    changes.append(f"{wo_id}: derived missing/invalid cancelled_at")
            if is_missing(row["cancellation_reason"]):
                sanitized.at[index, "cancellation_reason"] = "Cancelled before work commenced"
                changes.append(f"{wo_id}: derived missing cancellation_reason")

    return sanitized, changes


def validate_temporal(df: pd.DataFrame) -> list[str]:
    """Return explicit temporal problems; optional hold fields are supported if present."""
    errors: list[str] = []
    parsed: dict[str, pd.Series] = {}
    columns = ["created_at", "accepted_at", "verified_at", "cancelled_at"]
    for column in columns:
        if column not in df.columns:
            continue
        raw = df[column].replace("", pd.NA)
        parsed[column] = pd.to_datetime(raw, errors="coerce", format="ISO8601")
        invalid = raw.notna() & parsed[column].isna()
        errors.extend(f"{work_order_id}: invalid {column} timestamp {raw_value!r}"
                      for work_order_id, raw_value in df.loc[invalid, ["work_order_id", column]].itertuples(index=False, name=None))

    def check_after(later: str, earlier: str) -> None:
        if later not in parsed or earlier not in parsed:
            return
        invalid = parsed[later].notna() & parsed[earlier].notna() & (parsed[later] < parsed[earlier])
        errors.extend(f"{work_order_id}: {later} is before {earlier}"
                      for work_order_id in df.loc[invalid, "work_order_id"].tolist())

    check_after("accepted_at", "created_at")
    check_after("verified_at", "created_at")
    check_after("cancelled_at", "created_at")
    check_after("verified_at", "accepted_at")
    return errors


def validate_state(df: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    for row in df.to_dict(orient="records"):
        wo_id, status = row["work_order_id"], row["status"]
        verified = is_missing(row["verified_at"]) or is_missing(row["verified_by"])
        cancelled = not is_missing(row["cancelled_at"]) or not is_missing(row["cancellation_reason"])
        if status == "COMPLETED" and verified:
            errors.append(f"{wo_id}: COMPLETED without verification timestamp and manager")
        if status == "CANCELLED":
            if is_missing(row["cancelled_at"]) or is_missing(row["cancellation_reason"]):
                errors.append(f"{wo_id}: CANCELLED without cancellation timestamp and reason")
            if not is_missing(row["verified_at"]) or not is_missing(row["verified_by"]):
                errors.append(f"{wo_id}: CANCELLED has verification fields")
        elif cancelled:
            errors.append(f"{wo_id}: non-CANCELLED has cancellation fields")
    return errors


def normalize(args: argparse.Namespace) -> tuple[str, int]:
    canonical = read_csv(CANONICAL_FILE)
    generated = read_csv(GENERATED_FILE)
    assets = read_csv(DATA_DIR / "assets.csv")
    locations = read_csv(DATA_DIR / "locations.csv")
    managers = read_csv(DATA_DIR / "managers.csv")
    technicians = read_csv(DATA_DIR / "technicians.csv")
    teams = read_csv(DATA_DIR / "maintenance_teams.csv")
    pm_executions = read_csv(DATA_DIR / "pm_executions.csv")
    maintenance_history = read_csv(DATA_DIR / "maintenance_history.csv")

    columns = canonical.columns.tolist()
    missing = [column for column in GENERATED_REQUIRED_COLUMNS if column not in generated.columns]
    if missing:
        raise ValueError(f"Generated source is missing required columns: {missing}")

    canonical_ids = value_set(canonical, "work_order_id")
    generated_ids = value_set(generated, "work_order_id")
    collisions = sorted(canonical_ids & generated_ids)
    if collisions:
        raise ValueError(f"FAIL: work-order ID collisions between sources: {collisions}")
    duplicate_generated = generated.loc[generated["work_order_id"].duplicated(keep=False), "work_order_id"].tolist()
    if duplicate_generated:
        raise ValueError(f"FAIL: duplicate generated work-order IDs: {sorted(set(duplicate_generated))}")

    asset_ids, location_ids = value_set(assets, "asset_id"), value_set(locations, "location_id")
    team_ids, manager_ids = value_set(teams, "team_id"), sorted(value_set(managers, "manager_id"))
    technician_ids, pm_execution_ids = value_set(technicians, "technician_id"), value_set(pm_executions, "pm_execution_id")
    if not manager_ids:
        raise ValueError("No managers are available for required completed-work-order verification.")
    sanitized_canonical, curated_contract_changes = sanitize_canonical_contracts(
        canonical, manager_ids
    )
    techs_by_team = {
        team: sorted(technicians.loc[technicians["team_id"] == team, "technician_id"].tolist())
        for team in team_ids
    }

    accepted: list[dict[str, str]] = []
    rejected: dict[str, list[str]] = {}
    warnings: list[str] = []
    derived_fields = [
        "accepted_at: created_at + 30 minutes for completed/in-progress/on-hold WOs with a team-matched technician",
        "accepted_by: stable SHA-256 work-order-ID selection from managers.csv when accepted_at is derived",
        "assigned_technician: stable SHA-256 work-order-ID selection among technicians assigned to assigned_team",
        "failure_cause: conservative mapping for recognized failure modes; UNKNOWN otherwise",
        "total_hold_time: 0; downtime_minutes: 0; material_required: false",
        "verified_at: created_at + 2 hours for COMPLETED WOs; verified_by: stable manager selection",
        "cancelled_at: created_at + 1 hour only for CANCELLED WOs",
    ]

    for source in generated.to_dict(orient="records"):
        wo_id = source["work_order_id"]
        reasons: list[str] = []
        if not wo_id:
            reasons.append("work_order_id is blank")
        for field, valid_values in (("asset_id", asset_ids), ("location_id", location_ids), ("assigned_team", team_ids)):
            if source[field] not in valid_values:
                reasons.append(f"invalid {field}: {source[field]!r}")
        status_raw = source["status"].strip().upper()
        status = STATUS_ALIASES.get(status_raw, status_raw)
        if status not in VALID_STATUSES:
            reasons.append(f"unsupported status: {source['status']!r}")
        created_at = pd.to_datetime(source["created_at"], errors="coerce")
        if pd.isna(created_at):
            reasons.append(f"invalid created_at timestamp: {source['created_at']!r}")
        if reasons:
            rejected[wo_id or "<blank work_order_id>"] = reasons
            continue

        assigned_technician = ""
        candidates = techs_by_team.get(source["assigned_team"], [])
        if candidates:
            assigned_technician = stable_pick(candidates, wo_id)
        elif status in {"COMPLETED", "IN_PROGRESS", "ON_HOLD"}:
            warnings.append(f"{wo_id}: no technician belongs to {source['assigned_team']}; acceptance fields left blank")

        acceptance_implied = status in {"COMPLETED", "IN_PROGRESS", "ON_HOLD"} and bool(assigned_technician)
        accepted_at = iso_timestamp(created_at + pd.Timedelta(minutes=30)) if acceptance_implied else ""
        accepted_by = stable_pick(manager_ids, f"accepted:{wo_id}") if acceptance_implied else ""
        completed = status == "COMPLETED"
        row = {column: "" for column in columns}
        for column in GENERATED_REQUIRED_COLUMNS:
            if column in row:
                row[column] = source[column]
        row.update({
            "status": status,
            "accepted_at": accepted_at,
            "accepted_by": accepted_by,
            "assigned_technician": assigned_technician,
            "failure_cause": FAILURE_CAUSES.get(source["failure_mode"].strip().upper(), "UNKNOWN"),
            # The generic generator text does not establish a specific repair or PM relation.
            "corrective_action": "",
            "total_hold_time": "0",
            "hold_reason": "Awaiting operational release" if status == "ON_HOLD" else "",
            "downtime_minutes": "0",
            "verified_at": iso_timestamp(created_at + pd.Timedelta(hours=2)) if completed else "",
            "verified_by": stable_pick(manager_ids, f"verified:{wo_id}") if completed else "",
            "material_required": "false",
            "cancelled_at": iso_timestamp(created_at + pd.Timedelta(hours=1)) if status == "CANCELLED" else "",
            "cancellation_reason": "Cancelled before work commenced" if status == "CANCELLED" else "",
            "related_pm_execution_id": "",
        })
        accepted.append(row)

    normalized = pd.DataFrame(accepted, columns=columns)
    merged = pd.concat([sanitized_canonical, normalized], ignore_index=True)
    temporal_errors = validate_temporal(merged)
    state_errors = validate_state(merged)
    # Validate every populated reference in the complete operational dataset.
    fk_errors: list[str] = []
    for row in merged.to_dict(orient="records"):
        for field, valid_values in (("asset_id", asset_ids), ("location_id", location_ids), ("assigned_team", team_ids),
                                    ("assigned_technician", technician_ids), ("accepted_by", set(manager_ids)),
                                    ("verified_by", set(manager_ids)), ("related_pm_execution_id", pm_execution_ids)):
            if row[field] and row[field] not in valid_values:
                fk_errors.append(f"{row['work_order_id']}: invalid {field}: {row[field]!r}")

    history_ids = value_set(maintenance_history, "work_order_id")
    before_orphans = sorted(history_ids - canonical_ids)
    after_orphans = sorted(history_ids - value_set(merged, "work_order_id"))
    report_lines = [
        "# Work-order normalization report", "",
        "## Source rows", f"- canonical: {len(canonical)}", f"- generated: {len(generated)}", "",
        "## Output rows", f"- merged: {len(merged)}", f"- generated rows accepted: {len(accepted)}", f"- generated rows rejected: {len(rejected)}", "",
        "## Rejected work orders",
    ]
    report_lines += ["- None" if not rejected else ""]
    for wo_id, reasons in rejected.items():
        report_lines.append(f"- {wo_id}: {'; '.join(reasons)}")
    report_lines += ["", "## Columns normalized", "- Generated source fields were mapped directly into the identically named canonical columns.",
                    "- The remaining canonical fields were populated only by the derivations below or left blank.", "",
                    "## Fields derived"] + [f"- {item}" for item in derived_fields]
    report_lines += ["", "## Foreign-key validation", f"- Merged FK errors: {len(fk_errors)}"]
    report_lines += [f"- {item}" for item in fk_errors] or ["- All populated merged references resolve to supplied supporting datasets."]
    report_lines += ["", "## Temporal validation", f"- Errors across merged rows: {len(temporal_errors)}"]
    report_lines += [f"- {item}" for item in temporal_errors] or ["- All checked timestamps obey causal ordering."]
    report_lines += ["", "## State validation", f"- Errors across merged rows: {len(state_errors)}"]
    report_lines += [f"- {item}" for item in state_errors] or ["- All checked work-order states are coherent."]
    report_lines += ["", "## Maintenance-history orphan count", f"- before: {len(before_orphans)}", f"- after: {len(after_orphans)}"]
    if before_orphans:
        preview = ", ".join(before_orphans[:20])
        suffix = " ..." if len(before_orphans) > 20 else ""
        report_lines.append(f"- orphan IDs before (first 20): {preview}{suffix}")
    if after_orphans:
        report_lines.append(f"- orphan IDs after: {', '.join(after_orphans)}")
    if curated_contract_changes:
        warnings.append(
            "Merged-output contract repairs applied without modifying source rows: "
            + "; ".join(curated_contract_changes)
        )
    report_lines += ["", "## Duplicate IDs", "- Source intersection: none", "- Generated duplicate IDs: none", "",
                    "## Warnings"]
    report_lines += [f"- {item}" for item in warnings] or ["- None"]
    report = "\n".join(report_lines) + "\n"

    if not args.validate_only:
        merged.to_csv(MERGED_FILE, index=False, columns=columns)
        REPORT_FILE.write_text(report, encoding="utf-8")
    print(report)
    return report, 1 if rejected or fk_errors or temporal_errors or state_errors or after_orphans else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize bulk CMMS work orders into canonical schema.")
    parser.add_argument("--validate-only", action="store_true", help="Validate and print the report without writing output files.")
    args = parser.parse_args()
    try:
        _, exit_code = normalize(args)
        return exit_code
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
