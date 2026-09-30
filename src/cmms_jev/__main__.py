"""Terminal entry point for the first Jev decision."""

from __future__ import annotations

import argparse
import json

from .data import CMMSRepository
from .decisions.classification import CLASSIFICATION_CRITERIA, classify_work_order
from .jev import JevCallError, JevConfigurationError


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a CMMS Jev decision.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    classify = subparsers.add_parser("classify", help="Classify a work order with Jev.")
    classify.add_argument("work_order_id")
    classify.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the deterministic Jev payload without making a network call.",
    )
    args = parser.parse_args()

    context = CMMSRepository().work_order_context(args.work_order_id)
    if args.dry_run:
        print(json.dumps({
            "state": context,
            "question": "classification",
            "criteria": CLASSIFICATION_CRITERIA,
        }, indent=2))
        return 0
    try:
        result = classify_work_order(context)
    except (JevConfigurationError, JevCallError) as exc:
        parser.error(str(exc))
    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
