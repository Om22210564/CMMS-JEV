import unittest

from cmms_jev.data import CMMSRepository
from cmms_jev.models import DecisionResult, DecisionValidationError


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


if __name__ == "__main__":
    unittest.main()
