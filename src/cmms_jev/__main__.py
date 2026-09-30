"""Terminal entry point for the first Jev decision."""

from __future__ import annotations

import argparse
import json

from .data import CMMSRepository, EntityNotFoundError
from .decisions.classification import CLASSIFICATION_CRITERIA, classify_work_order
from .decisions.duplicate import DUPLICATE_CRITERIA, detect_duplicate
from .decisions.inspection import INSPECTION_CRITERIA, disposition_inspection
from .decisions.replenishment import REPLENISHMENT_CRITERIA, assess_replenishment
from .decisions.routing import ROUTING_CRITERIA, route_work_order
from .decisions.spare import SPARE_CRITERIA, assess_spare_relevance
from .jev import JevCallError, JevConfigurationError
from .evaluation import EVALUATION_FILES, run_evaluation
from .workflows.demo import run_cp400_demo


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a CMMS Jev decision.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    def add_dry_run(command: argparse.ArgumentParser) -> None:
        command.add_argument(
            "--dry-run", action="store_true",
            help="Print the deterministic Jev payload without making a network call.",
        )

    classify = subparsers.add_parser("classify", help="Classify a work order with Jev.")
    classify.add_argument("work_order_id")
    add_dry_run(classify)
    route = subparsers.add_parser("route", help="Route a work order with Jev.")
    route.add_argument("work_order_id")
    add_dry_run(route)
    duplicate = subparsers.add_parser("duplicate", help="Compare two work orders with Jev.")
    duplicate.add_argument("primary_work_order_id")
    duplicate.add_argument("candidate_work_order_id")
    add_dry_run(duplicate)
    inspect = subparsers.add_parser("inspect", help="Disposition an inspection with Jev.")
    inspect.add_argument("inspection_id")
    add_dry_run(inspect)
    spare = subparsers.add_parser("spare", help="Assess a material request with Jev.")
    spare.add_argument("request_id")
    add_dry_run(spare)
    replenish = subparsers.add_parser("replenish", help="Assess inventory attention with Jev.")
    replenish.add_argument("item_id")
    add_dry_run(replenish)
    evaluate = subparsers.add_parser("evaluate", help="Run one live evaluation dataset.")
    evaluate.add_argument("decision", choices=sorted(EVALUATION_FILES))
    demo = subparsers.add_parser("demo", help="Run a read-only CMMS decision workflow demo.")
    demo.add_argument("scenario", choices=["cp-400"])
    args = parser.parse_args()

    repository = CMMSRepository()
    if args.command == "evaluate":
        try:
            summary = run_evaluation(args.decision, repository)
        except (EntityNotFoundError, JevConfigurationError, JevCallError, ValueError) as exc:
            parser.error(str(exc))
        print(json.dumps(summary.to_dict(), indent=2))
        return 0
    if args.command == "demo":
        try:
            demo_result = run_cp400_demo(repository)
        except (EntityNotFoundError, JevConfigurationError, JevCallError) as exc:
            parser.error(str(exc))
        print(json.dumps(demo_result, indent=2))
        return 0
    try:
        if args.command == "classify":
            context = repository.work_order_context(args.work_order_id)
            question, criteria, execute = "classification", CLASSIFICATION_CRITERIA, classify_work_order
        elif args.command == "route":
            context = repository.work_order_context(args.work_order_id)
            question, criteria, execute = "routing", ROUTING_CRITERIA, route_work_order
        elif args.command == "duplicate":
            context = {
                "primary": repository.work_order_context(args.primary_work_order_id),
                "candidate": repository.work_order_context(args.candidate_work_order_id),
            }
            question, criteria, execute = "duplicate_detection", DUPLICATE_CRITERIA, detect_duplicate
        elif args.command == "inspect":
            context = repository.inspection_context(args.inspection_id)
            question, criteria, execute = "inspection_disposition", INSPECTION_CRITERIA, disposition_inspection
        elif args.command == "spare":
            context = repository.material_request_context(args.request_id)
            question, criteria, execute = "spare_relevance", SPARE_CRITERIA, assess_spare_relevance
        else:
            context = repository.replenishment_context(args.item_id)
            question, criteria, execute = "replenishment_attention", REPLENISHMENT_CRITERIA, assess_replenishment
    except EntityNotFoundError as exc:
        parser.error(str(exc))

    if args.dry_run:
        print(json.dumps({
            "state": context,
            "question": question,
            "criteria": criteria,
        }, indent=2))
        return 0
    try:
        result = execute(context)
    except (JevConfigurationError, JevCallError) as exc:
        parser.error(str(exc))
    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
