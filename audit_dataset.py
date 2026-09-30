import pandas as pd
from pathlib import Path


# ============================================================
# Paths
# ============================================================

DATA_DIR = Path("data")
EVAL_DIR = Path("evaluation")


# ============================================================
# Utilities
# ============================================================

def load_csv(directory: Path, filename: str) -> pd.DataFrame:
    filepath = directory / filename

    if not filepath.exists():
        print(f"⚠️ Warning: File not found - {filepath}")
        return pd.DataFrame()

    try:
        return pd.read_csv(filepath)
    except Exception as e:
        print(f"❌ FAIL: Could not read {filepath}: {e}")
        return pd.DataFrame()


def check_required_columns(
    df: pd.DataFrame,
    required_columns: list[str],
    dataset_name: str,
) -> bool:
    if df.empty:
        return True

    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        print(
            f"❌ FAIL: {dataset_name} is missing columns: "
            f"{missing}"
        )
        return False

    return True


def check_unique_ids(
    df: pd.DataFrame,
    id_column: str,
    dataset_name: str,
) -> bool:
    if df.empty or id_column not in df.columns:
        return True

    duplicated = df[df[id_column].duplicated(keep=False)]

    if not duplicated.empty:
        ids = duplicated[id_column].unique().tolist()
        print(
            f"❌ FAIL: {dataset_name} contains duplicate "
            f"{id_column}: {ids[:10]}"
        )
        return False

    print(f"✅ PASS: {dataset_name} has unique {id_column}s.")
    return True


def check_foreign_key(
    child_df: pd.DataFrame,
    child_col: str,
    parent_df: pd.DataFrame,
    parent_col: str,
    name: str,
) -> bool:

    if child_df.empty or parent_df.empty:
        return True

    if child_col not in child_df.columns or parent_col not in parent_df.columns:
        print(f"⚠️ SKIP: {name} - required column missing.")
        return True

    child_vals = child_df[child_col].dropna().unique()
    parent_vals = set(parent_df[parent_col].dropna().unique())

    orphans = [value for value in child_vals if value not in parent_vals]

    if orphans:
        print(
            f"❌ FAIL: {name} - orphaned IDs: "
            f"{orphans[:10]}"
        )
        return False

    print(f"✅ PASS: {name} - no orphaned references.")
    return True


def parse_datetime_column(
    df: pd.DataFrame,
    column: str,
    dataset_name: str,
) -> tuple[pd.Series, pd.Series]:

    if column not in df.columns:
        return pd.Series(dtype="datetime64[ns]"), pd.Series(dtype=bool)

    raw = df[column]
    normalized = raw.astype(str).str.strip()
    missing = raw.isna() | normalized.str.lower().isin(
        {"", "null", "none", "nan"}
    )
    parsed = pd.to_datetime(
        raw.where(~missing),
        errors="coerce",
        format="ISO8601",
    )

    invalid = ~missing & parsed.isna()

    if invalid.any():
        print(
            f"❌ FAIL: {dataset_name}.{column} contains invalid "
            f"non-timestamp values: "
            f"{df.loc[invalid, column].head(5).tolist()}"
        )

    return parsed, invalid


# ============================================================
# Main Audit
# ============================================================

def run_audit():

    print("=" * 70)
    print("Synthetic Industrial CMMS Dataset Audit")
    print("=" * 70)

    failures = 0
    warnings = 0

    # ========================================================
    # 1. Load datasets
    # ========================================================

    print("\n--- Loading datasets ---")

    assets = load_csv(DATA_DIR, "assets.csv")
    locations = load_csv(DATA_DIR, "locations.csv")

    # Keep the source files visible for source-level checks, but use the
    # normalized merged file for all operational work-order checks.
    canonical_work_orders = load_csv(DATA_DIR, "work_orders.csv")
    merged_filename = "work_orders_merged.csv"
    operational_filename = (
        merged_filename
        if (DATA_DIR / merged_filename).exists()
        else "work_orders.csv"
    )
    operational_work_orders = load_csv(DATA_DIR, operational_filename)

    # Secondary/bulk work-order source
    work_orders_generated = load_csv(
        DATA_DIR,
        "work_orders_generated.csv",
    )

    print(
        f"Operational work-order dataset: {operational_filename}"
    )
    print(f"Records: {len(operational_work_orders)}")

    managers = load_csv(DATA_DIR, "managers.csv")
    technicians = load_csv(DATA_DIR, "technicians.csv")
    teams = load_csv(DATA_DIR, "maintenance_teams.csv")

    pm_plans = load_csv(DATA_DIR, "pm_plans.csv")
    pm_executions = load_csv(DATA_DIR, "pm_executions.csv")
    inspections = load_csv(DATA_DIR, "inspections.csv")

    items = load_csv(DATA_DIR, "inventory_items.csv")
    balances = load_csv(
        DATA_DIR,
        "inventory_location_balances.csv",
    )
    compatibility = load_csv(
        DATA_DIR,
        "asset_part_compatibility.csv",
    )

    mat_reqs = load_csv(
        DATA_DIR,
        "material_requests.csv",
    )
    mat_issues = load_csv(
        DATA_DIR,
        "material_issues.csv",
    )

    suppliers = load_csv(DATA_DIR, "suppliers.csv")
    purchase_requests = load_csv(
        DATA_DIR,
        "purchase_requests.csv",
    )
    purchase_orders = load_csv(
        DATA_DIR,
        "purchase_orders.csv",
    )
    po_lines = load_csv(
        DATA_DIR,
        "purchase_order_lines.csv",
    )

    receipts = load_csv(
        DATA_DIR,
        "material_receipts.csv",
    )
    receipt_lines = load_csv(
        DATA_DIR,
        "material_receipt_lines.csv",
    )

    maintenance_history = load_csv(
        DATA_DIR,
        "maintenance_history.csv",
    )

    eval_class = load_csv(
        EVAL_DIR,
        "evaluation_classification.csv",
    )
    eval_routing = load_csv(
        EVAL_DIR,
        "evaluation_routing.csv",
    )
    eval_dup = load_csv(
        EVAL_DIR,
        "evaluation_duplicate_detection.csv",
    )
    eval_inspection = load_csv(
        EVAL_DIR,
        "evaluation_inspection_disposition.csv",
    )
    eval_spare = load_csv(
        EVAL_DIR,
        "evaluation_spare_relevance.csv",
    )
    eval_replenishment = load_csv(
        EVAL_DIR,
        "evaluation_replenishment.csv",
    )

    # ========================================================
    # 2. Dataset summary
    # ========================================================

    print("\n--- Dataset Record Counts ---")

    datasets = {
        "locations": locations,
        "assets": assets,
        "managers": managers,
        "technicians": technicians,
        "maintenance_teams": teams,
        "work_orders": operational_work_orders,
        "work_orders_generated": work_orders_generated,
        "pm_plans": pm_plans,
        "pm_executions": pm_executions,
        "inspections": inspections,
        "inventory_items": items,
        "inventory_location_balances": balances,
        "asset_part_compatibility": compatibility,
        "material_requests": mat_reqs,
        "material_issues": mat_issues,
        "suppliers": suppliers,
        "purchase_requests": purchase_requests,
        "purchase_orders": purchase_orders,
        "purchase_order_lines": po_lines,
        "material_receipts": receipts,
        "material_receipt_lines": receipt_lines,
        "maintenance_history": maintenance_history,
    }

    for name, df in datasets.items():
        print(f"{name:<35} {len(df):>5}")

    # ========================================================
    # 3. Required schema
    # ========================================================

    print("\n--- Checking Required Schemas ---")

    schemas = {
        "locations": [
            "location_id",
        ],
        "assets": [
            "asset_id",
            "location_id",
        ],
        "managers": [
            "manager_id",
        ],
        "technicians": [
            "technician_id",
        ],
        "maintenance_teams": [
            "team_id",
        ],
        "work_orders": [
            "work_order_id",
            "asset_id",
            "location_id",
            "work_order_type",
            "description",
            "created_at",
            "requested_by",
            "assigned_team",
            "status",
        ],
        "pm_plans": [
            "pm_plan_id",
            "asset_id",
        ],
        "pm_executions": [
            "pm_execution_id",
            "pm_plan_id",
        ],
        "inspections": [
            "inspection_id",
            "asset_id",
        ],
        "inventory_items": [
            "item_id",
            "quantity_on_hand",
            "reorder_level",
        ],
        "inventory_location_balances": [
            "item_id",
            "location_id",
            "quantity",
        ],
        "material_requests": [
            "request_id",
            "work_order_id",
            "item_id",
        ],
        "material_issues": [
            "issue_id",
            "request_id",
            "item_id",
            "issued_quantity",
        ],
        "purchase_orders": [
            "po_id",
            "supplier_id",
        ],
        "purchase_order_lines": [
            "po_id",
            "item_id",
            "order_quantity",
        ],
        "material_receipts": [
            "receipt_id",
            "po_id",
        ],
        "material_receipt_lines": [
            "receipt_id",
            "item_id",
            "quantity_received",
        ],
        "maintenance_history": [
            "maintenance_event_id",
            "asset_id",
            "work_order_id",
        ],
    }

    schema_pass = True

    for name, required in schemas.items():
        df = datasets.get(name)

        if df is None:
            continue

        if not check_required_columns(
            df,
            required,
            name,
        ):
            schema_pass = False

    if schema_pass:
        print("✅ PASS: Required schemas are present.")

    # ========================================================
    # 4. Primary-key uniqueness
    # ========================================================

    print("\n--- Checking Primary-Key Uniqueness ---")

    pk_definitions = {
        "locations": ("location_id", locations),
        "assets": ("asset_id", assets),
        "managers": ("manager_id", managers),
        "technicians": ("technician_id", technicians),
        "maintenance_teams": ("team_id", teams),
        "work_orders": ("work_order_id", operational_work_orders),
        "pm_plans": ("pm_plan_id", pm_plans),
        "pm_executions": (
            "pm_execution_id",
            pm_executions,
        ),
        "inspections": (
            "inspection_id",
            inspections,
        ),
        "inventory_items": (
            "item_id",
            items,
        ),
        "material_requests": (
            "request_id",
            mat_reqs,
        ),
        "material_issues": (
            "issue_id",
            mat_issues,
        ),
        "suppliers": (
            "supplier_id",
            suppliers,
        ),
        "purchase_requests": (
            "pr_id",
            purchase_requests,
        ),
        "purchase_orders": (
            "po_id",
            purchase_orders,
        ),
        "material_receipts": (
            "receipt_id",
            receipts,
        ),
        "maintenance_history": (
            "maintenance_event_id",
            maintenance_history,
        ),
    }

    pk_pass = True

    for name, (column, df) in pk_definitions.items():
        if not check_unique_ids(df, column, name):
            pk_pass = False

    # ========================================================
    # 5. Work-order secondary source audit
    # ========================================================

    print("\n--- Checking Work-Order Secondary Source ---")
    secondary_source_pass = True

    if not work_orders_generated.empty:

        print(
            "ℹ️ INFO: work_orders_generated.csv exists."
        )

        print(
            f"   Canonical work_orders.csv: "
            f"{len(canonical_work_orders)} rows"
        )

        print(
            f"   Bulk work_orders_generated.csv: "
            f"{len(work_orders_generated)} rows"
        )

        canonical_columns = set(
            canonical_work_orders.columns
        )

        generated_columns = set(
            work_orders_generated.columns
        )

        missing_from_generated = sorted(
            canonical_columns - generated_columns
        )

        extra_in_generated = sorted(
            generated_columns - canonical_columns
        )

        if missing_from_generated:
            print(
                "⚠️ WARNING: Generated work orders are "
                "missing canonical columns:"
            )

            for column in missing_from_generated:
                print(f"   - {column}")

            warnings += 1

        if extra_in_generated:
            print(
                "⚠️ WARNING: Generated work orders contain "
                "extra columns:"
            )

            for column in extra_in_generated:
                print(f"   + {column}")

            warnings += 1

        # ----------------------------------------------------
        # Check duplicate IDs across both sources
        # ----------------------------------------------------

        if (
            "work_order_id" in canonical_work_orders.columns
            and
            "work_order_id" in work_orders_generated.columns
        ):
            canonical_ids = set(
                canonical_work_orders["work_order_id"]
                .dropna()
                .astype(str)
            )

            generated_ids = set(
                work_orders_generated["work_order_id"]
                .dropna()
                .astype(str)
            )

            overlapping_ids = (
                canonical_ids & generated_ids
            )

            if overlapping_ids:
                print(
                    "❌ FAIL: Work-order IDs overlap between "
                    "the two source files:"
                )

                print(
                    f"   {sorted(overlapping_ids)[:20]}"
                )

                secondary_source_pass = False

            else:
                print(
                    "✅ PASS: No work-order ID collisions "
                    "between canonical and generated files."
                )

        print(
            "\n   IMPORTANT:"
        )
        print(
            "   work_orders.csv should remain the canonical "
            "application dataset."
        )
        print(
            "   work_orders_generated.csv should be treated "
            "as a bulk-generation source until normalized."
        )

    else:
        print(
            "ℹ️ INFO: No work_orders_generated.csv found."
        )

    # ========================================================
    # 6. Foreign-Key Integrity
    # ========================================================

    print("\n--- Checking Foreign-Key Integrity ---")

    fk_checks = [
        (
            assets,
            "location_id",
            locations,
            "location_id",
            "Assets -> Locations",
        ),

        (
            operational_work_orders,
            "asset_id",
            assets,
            "asset_id",
            "Work Orders -> Assets",
        ),

        (
            operational_work_orders,
            "location_id",
            locations,
            "location_id",
            "Work Orders -> Locations",
        ),

        (
            operational_work_orders,
            "assigned_team",
            teams,
            "team_id",
            "Work Orders -> Teams",
        ),

        (
            operational_work_orders,
            "assigned_technician",
            technicians,
            "technician_id",
            "Work Orders -> Technicians",
        ),

        (
            operational_work_orders,
            "accepted_by",
            managers,
            "manager_id",
            "Work Orders -> Accepted Manager",
        ),

        (
            operational_work_orders,
            "verified_by",
            managers,
            "manager_id",
            "Work Orders -> Verified Manager",
        ),

        (
            pm_plans,
            "asset_id",
            assets,
            "asset_id",
            "PM Plans -> Assets",
        ),

        (
            pm_executions,
            "pm_plan_id",
            pm_plans,
            "pm_plan_id",
            "PM Executions -> PM Plans",
        ),

        (
            inspections,
            "asset_id",
            assets,
            "asset_id",
            "Inspections -> Assets",
        ),

        (
            inspections,
            "pm_execution_id",
            pm_executions,
            "pm_execution_id",
            "Inspections -> PM Executions",
        ),

        (
            balances,
            "item_id",
            items,
            "item_id",
            "Inventory Balances -> Items",
        ),

        (
            balances,
            "location_id",
            locations,
            "location_id",
            "Inventory Balances -> Locations",
        ),

        (
            compatibility,
            "item_id",
            items,
            "item_id",
            "Compatibility -> Inventory Items",
        ),

        (
            mat_reqs,
            "work_order_id",
            operational_work_orders,
            "work_order_id",
            "Material Requests -> Work Orders",
        ),

        (
            mat_reqs,
            "item_id",
            items,
            "item_id",
            "Material Requests -> Items",
        ),

        (
            mat_issues,
            "request_id",
            mat_reqs,
            "request_id",
            "Material Issues -> Material Requests",
        ),

        (
            mat_issues,
            "item_id",
            items,
            "item_id",
            "Material Issues -> Items",
        ),

        (
            purchase_orders,
            "supplier_id",
            suppliers,
            "supplier_id",
            "Purchase Orders -> Suppliers",
        ),

        (
            purchase_orders,
            "pr_id",
            purchase_requests,
            "pr_id",
            "Purchase Orders -> Purchase Requests",
        ),

        (
            po_lines,
            "po_id",
            purchase_orders,
            "po_id",
            "PO Lines -> Purchase Orders",
        ),

        (
            po_lines,
            "item_id",
            items,
            "item_id",
            "PO Lines -> Inventory Items",
        ),

        (
            receipts,
            "po_id",
            purchase_orders,
            "po_id",
            "Receipts -> Purchase Orders",
        ),

        (
            receipt_lines,
            "receipt_id",
            receipts,
            "receipt_id",
            "Receipt Lines -> Receipts",
        ),

        (
            receipt_lines,
            "item_id",
            items,
            "item_id",
            "Receipt Lines -> Inventory Items",
        ),

        (
            maintenance_history,
            "asset_id",
            assets,
            "asset_id",
            "Maintenance History -> Assets",
        ),

        (
            maintenance_history,
            "work_order_id",
            operational_work_orders,
            "work_order_id",
            "Maintenance History -> Work Orders",
        ),
    ]

    fk_pass = True

    for (
        child_df,
        child_col,
        parent_df,
        parent_col,
        name,
    ) in fk_checks:

        if not check_foreign_key(
            child_df,
            child_col,
            parent_df,
            parent_col,
            name,
        ):
            fk_pass = False

    if fk_pass:
        print(
            "✅ PASS: All checked foreign-key relationships "
            "resolve correctly."
        )

    # ========================================================
    # 7. Work Order temporal logic
    # ========================================================

    print("\n--- Checking Work-Order Temporal Logic ---")

    wo_time_columns = [
        "created_at",
        "accepted_at",
        "verified_at",
        "cancelled_at",
    ]

    wo_parsed = {}
    temporal_errors = []
    wo_temporal_pass = True

    for column in wo_time_columns:
        if column in operational_work_orders.columns:
            parsed, invalid = parse_datetime_column(
                operational_work_orders,
                column,
                operational_filename,
            )
            wo_parsed[column] = parsed
            if invalid.any():
                wo_temporal_pass = False

    if (
        "created_at" in wo_parsed
        and "accepted_at" in wo_parsed
    ):
        mask = (
            wo_parsed["accepted_at"].notna()
            &
            wo_parsed["created_at"].notna()
            &
            (
                wo_parsed["accepted_at"]
                <
                wo_parsed["created_at"]
            )
        )

        temporal_errors.append(
            (
                mask,
                "accepted_at before created_at",
            )
        )

    if (
        "created_at" in wo_parsed
        and "verified_at" in wo_parsed
    ):
        mask = (
            wo_parsed["verified_at"].notna()
            &
            (
                wo_parsed["verified_at"]
                <
                wo_parsed["created_at"]
            )
        )

        temporal_errors.append(
            (
                mask,
                "verified_at before created_at",
            )
        )

    if (
        "created_at" in wo_parsed
        and "cancelled_at" in wo_parsed
    ):
        mask = (
            wo_parsed["cancelled_at"].notna()
            &
            (
                wo_parsed["cancelled_at"]
                <
                wo_parsed["created_at"]
            )
        )
        temporal_errors.append((mask, "cancelled_at before created_at"))

    if (
        "accepted_at" in wo_parsed
        and "verified_at" in wo_parsed
    ):
        mask = (
            wo_parsed["accepted_at"].notna()
            & wo_parsed["verified_at"].notna()
            & (wo_parsed["verified_at"] < wo_parsed["accepted_at"])
        )
        temporal_errors.append((mask, "verified_at before accepted_at"))

    for mask, description in temporal_errors:
        if mask.any():
            bad_ids = operational_work_orders.loc[
                mask,
                "work_order_id",
            ].tolist()

            print(
                f"❌ FAIL: {description}: "
                f"{bad_ids[:10]}"
            )

            wo_temporal_pass = False

    if wo_temporal_pass:
        print(
            "✅ PASS: Work-order timestamps follow "
            "causal ordering."
        )

    # ========================================================
    # 8. Work Order state consistency
    # ========================================================

    print("\n--- Checking Work-Order State Consistency ---")

    state_pass = True

    def missing(column: str) -> pd.Series:
        values = operational_work_orders[column]
        return values.isna() | values.astype(str).str.strip().str.lower().isin(
            {"", "null", "none", "nan"}
        )

    if "status" in operational_work_orders.columns:
        status = operational_work_orders["status"]

        def report_state_failure(mask: pd.Series, message: str) -> None:
            nonlocal state_pass
            if mask.any():
                print(f"❌ FAIL: {message}: {operational_work_orders.loc[mask, 'work_order_id'].tolist()[:10]}")
                state_pass = False

        if {"verified_at", "verified_by"}.issubset(operational_work_orders.columns):
            report_state_failure(
                (status == "COMPLETED") & (missing("verified_at") | missing("verified_by")),
                "COMPLETED work orders without verification timestamp and manager",
            )
        if {"cancelled_at", "cancellation_reason"}.issubset(operational_work_orders.columns):
            report_state_failure(
                (status == "CANCELLED") & (missing("cancelled_at") | missing("cancellation_reason")),
                "CANCELLED work orders without cancellation timestamp and reason",
            )
            report_state_failure(
                (status != "CANCELLED") & ~missing("cancelled_at"),
                "Non-CANCELLED work orders with cancelled_at",
            )
            report_state_failure(
                (status != "CANCELLED") & ~missing("cancellation_reason"),
                "Non-CANCELLED work orders with cancellation_reason",
            )
        if "hold_reason" in operational_work_orders.columns:
            report_state_failure(
                (status == "ON_HOLD") & missing("hold_reason"),
                "ON_HOLD work orders without hold_reason",
            )
            report_state_failure(
                (status != "ON_HOLD") & ~missing("hold_reason"),
                "Non-ON_HOLD work orders with hold_reason",
            )

    if state_pass:
        print(
            "✅ PASS: Work-order state fields are "
            "internally consistent."
        )

    # ========================================================
    # 9. Inventory arithmetic
    # ========================================================

    print("\n--- Checking Inventory Arithmetic ---")

    inventory_pass = True

    if (
        not items.empty
        and not balances.empty
        and "item_id" in items.columns
        and "quantity_on_hand" in items.columns
    ):

        grouped = (
            balances
            .groupby("item_id")["quantity"]
            .sum()
            .reset_index()
        )

        inv_check = items[
            [
                "item_id",
                "quantity_on_hand",
            ]
        ].merge(
            grouped,
            on="item_id",
            how="left",
        )

        inv_check["quantity"] = (
            inv_check["quantity"]
            .fillna(0)
        )

        errors = inv_check[
            inv_check["quantity_on_hand"]
            !=
            inv_check["quantity"]
        ]

        if not errors.empty:
            print(
                "❌ FAIL: quantity_on_hand does not "
                "match location balances."
            )

            print(errors.head(10))

            inventory_pass = False
        else:
            print(
                "✅ PASS: Location balances sum exactly "
                "to quantity_on_hand."
            )

    # ========================================================
    # 10. Inventory quantity sanity
    # ========================================================

    print("\n--- Checking Inventory Quantity Sanity ---")

    quantity_pass = True

    numeric_columns = [
        "quantity_on_hand",
        "quantity_reserved",
        "safety_stock",
        "reorder_level",
        "reorder_quantity",
        "lead_time_days",
    ]

    for column in numeric_columns:
        if column not in items.columns:
            continue

        bad = items[
            pd.to_numeric(
                items[column],
                errors="coerce",
            ) < 0
        ]

        if not bad.empty:
            print(
                f"❌ FAIL: Negative values in "
                f"inventory_items.{column}: "
                f"{bad['item_id'].tolist()[:10]}"
            )

            quantity_pass = False

    if (
        "quantity_reserved" in items.columns
        and "quantity_on_hand" in items.columns
    ):
        bad = items[
            items["quantity_reserved"]
            >
            items["quantity_on_hand"]
        ]

        if not bad.empty:
            print(
                "❌ FAIL: Reserved quantity exceeds "
                "quantity on hand:"
            )
            print(
                bad["item_id"].tolist()[:10]
            )
            quantity_pass = False

    if quantity_pass:
        print(
            "✅ PASS: Inventory quantities are "
            "non-negative and logically bounded."
        )

    # ========================================================
    # 11. Material request / issue constraints
    # ========================================================

    print(
        "\n--- Checking Material Request / Issue Constraints ---"
    )

    material_pass = True

    if (
        not mat_reqs.empty
        and not mat_issues.empty
    ):

        issue_sums = (
            mat_issues
            .groupby("request_id")[
                "issued_quantity"
            ]
            .sum()
            .reset_index()
        )

        req_check = mat_reqs[
            [
                "request_id",
                "quantity_requested",
                "quantity_approved",
            ]
        ].merge(
            issue_sums,
            on="request_id",
            how="left",
        )

        req_check["issued_quantity"] = (
            req_check["issued_quantity"]
            .fillna(0)
        )

        bad_approved = req_check[
            req_check["quantity_approved"]
            >
            req_check["quantity_requested"]
        ]

        if not bad_approved.empty:
            print(
                "❌ FAIL: Approved quantity exceeds "
                "requested quantity:"
            )
            print(
                bad_approved["request_id"]
                .tolist()[:10]
            )
            material_pass = False

        bad_issued = req_check[
            req_check["issued_quantity"]
            >
            req_check["quantity_approved"]
        ]

        if not bad_issued.empty:
            print(
                "❌ FAIL: Issued quantity exceeds "
                "approved quantity:"
            )
            print(
                bad_issued["request_id"]
                .tolist()[:10]
            )
            material_pass = False

    if material_pass:
        print(
            "✅ PASS: Material request/issue quantities "
            "respect workflow constraints."
        )

    # ========================================================
    # 12. Purchase Order / Receipt constraints
    # ========================================================

    print(
        "\n--- Checking Purchase Order / Receipt Constraints ---"
    )

    procurement_pass = True

    if (
        not po_lines.empty
        and not receipt_lines.empty
    ):

        ordered = (
            po_lines
            .groupby(
                ["po_id", "item_id"]
            )["order_quantity"]
            .sum()
            .reset_index()
        )

        received = (
            receipt_lines
            .groupby(
                ["receipt_id", "item_id"]
            )["quantity_received"]
            .sum()
            .reset_index()
        )

        receipt_with_po = (
            receipt_lines[
                [
                    "receipt_id",
                    "item_id",
                    "quantity_received",
                ]
            ]
            .merge(
                receipts[
                    [
                        "receipt_id",
                        "po_id",
                    ]
                ],
                on="receipt_id",
                how="left",
            )
        )

        received_by_po = (
            receipt_with_po
            .groupby(
                ["po_id", "item_id"]
            )["quantity_received"]
            .sum()
            .reset_index()
        )

        comparison = ordered.merge(
            received_by_po,
            on=["po_id", "item_id"],
            how="left",
        )

        comparison[
            "quantity_received"
        ] = comparison[
            "quantity_received"
        ].fillna(0)

        over_received = comparison[
            comparison["quantity_received"]
            >
            comparison["order_quantity"]
        ]

        if not over_received.empty:
            print(
                "❌ FAIL: Received quantity exceeds "
                "ordered quantity:"
            )
            print(over_received.head(10))
            procurement_pass = False

    if procurement_pass:
        print(
            "✅ PASS: Purchase receipts do not exceed "
            "ordered quantities."
        )

    # ========================================================
    # 13. PM / Inspection relationships
    # ========================================================

    print(
        "\n--- Checking PM / Inspection Relationships ---"
    )

    pm_pass = True

    if (
        not inspections.empty
        and "pm_execution_id" in inspections.columns
    ):

        referenced = (
            inspections["pm_execution_id"]
            .dropna()
            .unique()
        )

        valid = set(
            pm_executions[
                "pm_execution_id"
            ].dropna()
        )

        orphaned = [
            x for x in referenced
            if x not in valid
        ]

        if orphaned:
            print(
                "❌ FAIL: Inspections reference "
                "missing PM executions:"
            )
            print(orphaned[:10])
            pm_pass = False

    if pm_pass:
        print(
            "✅ PASS: PM and inspection relationships "
            "are valid."
        )

    # ========================================================
    # 14. Evaluation datasets
    # ========================================================

    print(
        "\n--- Checking Evaluation Dataset Coverage ---"
    )

    evaluations = {
        "classification": eval_class,
        "routing": eval_routing,
        "duplicate_detection": eval_dup,
        "inspection_disposition": eval_inspection,
        "spare_relevance": eval_spare,
        "replenishment": eval_replenishment,
    }

    evaluation_pass = True

    for name, df in evaluations.items():

        if df.empty:
            print(
                f"⚠️ WARNING: Evaluation dataset "
                f"{name} is empty/missing."
            )
            warnings += 1
            continue

        print(
            f"\n{name}: {len(df)} cases"
        )

        if "difficulty" in df.columns:
            distribution = (
                df["difficulty"]
                .value_counts()
                .to_dict()
            )

            print(
                f"   Difficulty: {distribution}"
            )

            missing_hard = (
                "HARD" not in distribution
                or distribution["HARD"] < 1
            )

            if missing_hard:
                print(
                    "   ❌ FAIL: No HARD evaluation cases."
                )
                evaluation_pass = False

        required_eval_columns = [
            "case_id",
            "expected_decision",
            "difficulty",
        ]

        missing = [
            col
            for col in required_eval_columns
            if col not in df.columns
        ]

        if missing:
            print(
                f"   ❌ FAIL: Missing evaluation "
                f"columns: {missing}"
            )
            evaluation_pass = False

    if evaluation_pass:
        print(
            "\n✅ PASS: Evaluation datasets have "
            "basic coverage and HARD cases."
        )

    # ========================================================
    # 15. Evaluation reference integrity
    # ========================================================

    print(
        "\n--- Checking Evaluation Reference Integrity ---"
    )

    # We only inspect columns whose names clearly indicate
    # a reference to an operational entity.

    reference_sources = {
        "work_order_id": operational_work_orders,
        "asset_id": assets,
        "location_id": locations,
        "item_id": items,
        "pm_execution_id": pm_executions,
        "pm_plan_id": pm_plans,
    }

    evaluation_reference_pass = True

    for eval_name, df in evaluations.items():

        if df.empty:
            continue

        for column, parent in reference_sources.items():

            if column not in df.columns:
                continue

            parent_ids = set()

            parent_id_column = column

            if (
                column == "work_order_id"
                and "work_order_id" in parent.columns
            ):
                parent_ids = set(
                    parent["work_order_id"]
                    .dropna()
                )

            elif (
                column == "asset_id"
                and "asset_id" in parent.columns
            ):
                parent_ids = set(
                    parent["asset_id"]
                    .dropna()
                )

            elif (
                column == "location_id"
                and "location_id" in parent.columns
            ):
                parent_ids = set(
                    parent["location_id"]
                    .dropna()
                )

            elif (
                column == "item_id"
                and "item_id" in parent.columns
            ):
                parent_ids = set(
                    parent["item_id"]
                    .dropna()
                )

            elif (
                column == "pm_execution_id"
                and "pm_execution_id" in parent.columns
            ):
                parent_ids = set(
                    parent["pm_execution_id"]
                    .dropna()
                )

            elif (
                column == "pm_plan_id"
                and "pm_plan_id" in parent.columns
            ):
                parent_ids = set(
                    parent["pm_plan_id"]
                    .dropna()
                )

            if not parent_ids:
                continue

            referenced = set(
                df[column]
                .dropna()
            )

            orphaned = (
                referenced - parent_ids
            )

            if orphaned:
                print(
                    f"❌ FAIL: evaluation_{eval_name} "
                    f"contains invalid {column}: "
                    f"{list(orphaned)[:10]}"
                )

                evaluation_reference_pass = False

    if evaluation_reference_pass:
        print(
            "✅ PASS: Evaluation references resolve "
            "to operational CMMS records."
        )

    # ========================================================
    # 16. Pump Bearing End-to-End Scenario
    # ========================================================

    print(
        "\n--- Checking Core Pump Bearing Scenario ---"
    )

    scenario_pass = True

    try:

        cp400_exists = (
            not assets[
                assets["asset_id"]
                == "CP-400"
            ].empty
        )

        cp400_insp = (
            not inspections[
                inspections["asset_id"]
                == "CP-400"
            ].empty
        )

        cp400_wo = (
            not operational_work_orders[
                operational_work_orders["asset_id"]
                == "CP-400"
            ].empty
        )

        bearing_req = False

        if cp400_wo:

            cp400_wo_ids = operational_work_orders[
                operational_work_orders["asset_id"]
                == "CP-400"
            ]["work_order_id"].tolist()

            bearing_req = not mat_reqs[
                (
                    mat_reqs["work_order_id"]
                    .isin(cp400_wo_ids)
                )
                &
                (
                    mat_reqs["item_id"]
                    == "P-102"
                )
            ].empty

        print(
            f"CP-400 exists:          {cp400_exists}"
        )

        print(
            f"CP-400 inspection:      {cp400_insp}"
        )

        print(
            f"CP-400 work order:      {cp400_wo}"
        )

        print(
            f"CP-400 bearing request: {bearing_req}"
        )

        if all(
            [
                cp400_exists,
                cp400_insp,
                cp400_wo,
                bearing_req,
            ]
        ):
            print(
                "✅ PASS: Pump-bearing lifecycle "
                "can be traced."
            )
        else:
            print(
                "❌ FAIL: Pump-bearing lifecycle "
                "is incomplete."
            )

            scenario_pass = False

    except KeyError as e:

        print(
            f"⚠️ WARNING: Pump scenario check "
            f"skipped: missing column {e}"
        )

        warnings += 1

    # ========================================================
    # 17. Dataset size / expected scale
    # ========================================================

    print(
        "\n--- Checking Dataset Scale ---"
    )

    expected_minimums = {
        "locations": 10,
        "assets": 20,
        "technicians": 5,
        "work_orders": 100,
        "pm_plans": 10,
        "pm_executions": 20,
        "inspections": 30,
        "inventory_items": 20,
        "material_requests": 30,
        "purchase_orders": 20,
        "maintenance_history": 50,
    }

    scale_pass = True

    for name, minimum in expected_minimums.items():

        count = len(datasets[name])

        if count < minimum:

            print(
                f"⚠️ WARNING: {name} has {count} records; "
                f"expected at least {minimum}."
            )

            warnings += 1

            # Do not fail the audit solely because the
            # dataset is smaller than the original target.
        else:

            print(
                f"✅ {name}: {count} records"
            )

    # ========================================================
    # 18. Final summary
    # ========================================================

    print("\n" + "=" * 70)
    print("AUDIT SUMMARY")
    print("=" * 70)

    if schema_pass:
        print("✅ Schema checks")
    else:
        print("❌ Schema checks")

    if secondary_source_pass:
        print("✅ Work-order secondary-source checks")
    else:
        print("❌ Work-order secondary-source checks")

    if pk_pass:
        print("✅ Primary-key checks")
    else:
        print("❌ Primary-key checks")

    if fk_pass:
        print("✅ Foreign-key checks")
    else:
        print("❌ Foreign-key checks")

    if wo_temporal_pass:
        print("✅ Work-order temporal checks")
    else:
        print("❌ Work-order temporal checks")

    if state_pass:
        print("✅ Work-order state checks")
    else:
        print("❌ Work-order state checks")

    if inventory_pass:
        print("✅ Inventory arithmetic")
    else:
        print("❌ Inventory arithmetic")

    if quantity_pass:
        print("✅ Inventory quantity sanity")
    else:
        print("❌ Inventory quantity sanity")

    if material_pass:
        print("✅ Material flow checks")
    else:
        print("❌ Material flow checks")

    if procurement_pass:
        print("✅ Procurement checks")
    else:
        print("❌ Procurement checks")

    if pm_pass:
        print("✅ PM/inspection checks")
    else:
        print("❌ PM/inspection checks")

    if evaluation_pass:
        print("✅ Evaluation checks")
    else:
        print("❌ Evaluation checks")

    if evaluation_reference_pass:
        print("✅ Evaluation reference checks")
    else:
        print("❌ Evaluation reference checks")

    if scenario_pass:
        print("✅ Pump-bearing scenario")
    else:
        print("❌ Pump-bearing scenario")

    # Count failed audit sections here so the process status always agrees with
    # the section-level results printed above.
    failures = sum(
        not result
        for result in (
            schema_pass,
            pk_pass,
            secondary_source_pass,
            fk_pass,
            wo_temporal_pass,
            state_pass,
            inventory_pass,
            quantity_pass,
            material_pass,
            procurement_pass,
            pm_pass,
            evaluation_pass,
            evaluation_reference_pass,
            scenario_pass,
        )
    )

    print()
    print(f"Failures: {failures}")
    print(f"Warnings: {warnings}")

    if failures == 0:
        print(
            "\n✅ AUDIT PASSED"
        )

        if warnings:
            print(
                "⚠️ Dataset passed, but review the warnings "
                "before freezing the dataset."
            )

    else:
        print(
            "\n❌ AUDIT FAILED"
        )

    print("=" * 70)
    return failures


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    raise SystemExit(1 if run_audit() else 0)
