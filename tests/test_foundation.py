import unittest

from cmms_jev.data import CMMSRepository
from cmms_jev.decisions.duplicate import detect_duplicate
from cmms_jev.decisions.inspection import INSPECTION_CRITERIA
from cmms_jev.decisions.replenishment import REPLENISHMENT_CRITERIA
from cmms_jev.decisions.routing import ROUTING_CRITERIA
from cmms_jev.decisions.spare import SPARE_CRITERIA
from cmms_jev.evaluation import run_evaluation
from cmms_jev.models import DecisionResult, DecisionValidationError
from cmms_jev.workflows.handlers import handle_inspection, handle_routing


class FoundationTests(unittest.TestCase):
    def test_work_order_context_contains_joined_entities(self) -> None:
        context = CMMSRepository().work_order_context("WO-001")
        self.assertEqual(context["work_order"]["work_order_id"], "WO-001")
        self.assertEqual(context["asset"]["asset_id"], "CP-400")
        self.assertEqual(context["location"]["location_id"], "LOC-UTL-01")

    def test_result_rejects_unexpected_choice(self) -> None:
        with self.assertRaises(DecisionValidationError):
            DecisionResult("UNKNOWN", 0.5, "classification").validate(
                {"MECHANICAL": "Physical maintenance"}
            )

    def test_all_decision_contexts_are_constructible(self) -> None:
        repository = CMMSRepository()
        self.assertIn("TEAM-MECH", ROUTING_CRITERIA)
        self.assertIn("REQUIRES_WORK_ORDER", INSPECTION_CRITERIA)
        self.assertIn("RELEVANT", SPARE_CRITERIA)
        self.assertIn("HEALTHY", REPLENISHMENT_CRITERIA)
        self.assertEqual(
            repository.inspection_context("INSP-001")["asset"]["asset_id"], "CP-400"
        )
        self.assertEqual(
            repository.material_request_context("MR-001")["item"]["item_id"], "P-102"
        )
        self.assertEqual(
            repository.replenishment_context("P-102")["inventory_item"]["item_id"], "P-102"
        )
        candidate_context = repository.spare_candidate_context("WO-002", "P-102")
        self.assertEqual(candidate_context["candidate_item"]["item_id"], "P-102")

    def test_evaluation_runner_reports_metrics_without_live_calls(self) -> None:
        def expected_runner(_: str, row: dict[str, str], __: CMMSRepository) -> str:
            return row["expected_decision"]

        summary = run_evaluation(
            "routing", CMMSRepository(), decision_runner=expected_runner
        )
        self.assertEqual(summary.total_cases, 30)
        self.assertEqual(summary.correct, 30)
        self.assertEqual(summary.accuracy, 1.0)
        self.assertEqual(summary.representative_failures, [])

    def test_workflow_handlers_remain_non_mutating_outcomes(self) -> None:
        routed = handle_routing(
            DecisionResult("TEAM-MECH", 0.9, "routing").with_evidence(
                work_order_id="WO-002"
            ),
            {"TEAM-MECH"},
        )
        inspected = handle_inspection(
            DecisionResult(
                "REQUIRES_WORK_ORDER", 0.9, "inspection_disposition"
            ).with_evidence(inspection_id="INSP-001")
        )
        self.assertEqual(routed.action, "PROPOSE_TEAM_ASSIGNMENT")
        self.assertTrue(routed.accepted)
        self.assertEqual(inspected.action, "FLAG_CORRECTIVE_WORK_ORDER_REQUIRED")


if __name__ == "__main__":
    unittest.main()
