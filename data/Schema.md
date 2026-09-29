# Schema Overview

- **Locations:** Hierarchical operational nodes (`location_id` PK).
- **Assets:** Physical equipment (`asset_id` PK, FK `location_id`).
- **People/Teams:** `technician_id`, `manager_id`, `team_id`.
- **Work Orders:** Maintenance tasks (`work_order_id` PK, FK `asset_id`, `location_id`).
- **Inventory & Supply Chain:**
  - `inventory_items` (Master catalog)
  - `inventory_location_balances` (Physical distribution)
  - `asset_part_compatibility` (Technical BOM restrictions)
  - `suppliers`, `purchase_requests`, `purchase_orders`, `material_receipts`.
- **Maintenance Execution:**
  - `pm_plans` -> `pm_executions` -> `inspections`.
  - `material_requests` -> `material_issues`.
