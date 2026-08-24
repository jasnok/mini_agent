import unittest
from unittest.mock import patch

from workflow import parking_workflow


class ParkingWorkflowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.calls = []

        def check_vehicle(vehicle_number):
            self.calls.append(("check_vehicle", {"vehicle_number": vehicle_number}))
            records = {
                "12가3456": {"registered": True, "status": "APPROVED"},
                "56다7890": {"registered": True, "status": "BLOCKED"},
            }
            vehicle = records.get(vehicle_number, {"registered": False, "status": "NOT_FOUND"})
            return {"vehicle_number": vehicle_number, **vehicle}

        def open_gate(vehicle_number):
            self.calls.append(("open_gate", {"vehicle_number": vehicle_number}))
            return {
                "success": True,
                "vehicle_number": vehicle_number,
                "gate_opened": True,
                "message": "문이 열렸습니다.",
            }

        def deny_gate(vehicle_number, reason):
            self.calls.append(("deny_gate", {"vehicle_number": vehicle_number, "reason": reason}))
            message = "차단 차량은 출입할 수 없습니다." if reason == "BLOCKED" else "등록되지 않은 차량입니다."
            return {
                "success": True,
                "vehicle_number": vehicle_number,
                "gate_opened": False,
                "message": message,
            }

        self.patchers = [
            patch.object(parking_workflow, "check_vehicle", check_vehicle),
            patch.object(parking_workflow, "open_gate", open_gate),
            patch.object(parking_workflow, "deny_gate", deny_gate),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_approved_vehicle_calls_check_then_open(self) -> None:
        result = parking_workflow.run_parking_workflow("12가3456")

        self.assertTrue(result["success"])
        self.assertEqual(result["vehicle_status"], "APPROVED")
        self.assertTrue(result["gate_opened"])
        self.assertEqual(result["execution_type"], "workflow")
        self.assertEqual(result["termination_reason"], "completed")
        self.assertEqual([name for name, _ in self.calls], ["check_vehicle", "open_gate"])

    def test_blocked_and_unknown_vehicles_call_check_then_deny(self) -> None:
        cases = [
            ("56다7890", "BLOCKED", True),
            ("99가9999", "NOT_FOUND", False),
        ]
        for vehicle_number, expected_status, expected_registered in cases:
            with self.subTest(vehicle_number=vehicle_number):
                self.calls.clear()
                result = parking_workflow.run_parking_workflow(vehicle_number)

                self.assertTrue(result["success"])
                self.assertEqual(result["status"], "rejected")
                self.assertEqual(result["vehicle_status"], expected_status)
                self.assertIs(result["registered"], expected_registered)
                self.assertFalse(result["gate_opened"])
                self.assertEqual(result["termination_reason"], "policy_rejected")
                self.assertEqual([name for name, _ in self.calls], ["check_vehicle", "deny_gate"])
                self.assertEqual(self.calls[-1][1]["reason"], expected_status)

    def test_missing_vehicle_number_calls_no_tool(self) -> None:
        for vehicle_number in (None, "", "   "):
            with self.subTest(vehicle_number=vehicle_number):
                self.calls.clear()
                result = parking_workflow.run_parking_workflow(vehicle_number)

                self.assertFalse(result["success"])
                self.assertEqual(result["status"], "needs_clarification")
                self.assertEqual(result["termination_reason"], "needs_clarification")
                self.assertEqual(result["error"]["code"], "TOOL_VALIDATION_ERROR")
                self.assertEqual(self.calls, [])

    def test_shared_validation_error_calls_no_gate(self) -> None:
        def invalid_arguments(vehicle_number):
            return {
                "success": False,
                "error": {"code": "TOOL_VALIDATION_ERROR", "message": vehicle_number},
            }

        with patch.object(parking_workflow, "check_vehicle", invalid_arguments):
            result = parking_workflow.run_parking_workflow("invalid")

        self.assertFalse(result["success"])
        self.assertEqual(result["termination_reason"], "tool_validation_error")
        self.assertEqual(
            result["error"],
            {"code": "TOOL_VALIDATION_ERROR", "message": "Tool 입력값이 유효하지 않습니다."},
        )
        self.assertEqual(self.calls, [])

    def test_shared_tool_normalization_is_used_for_gate_and_result(self) -> None:
        def normalized_vehicle(vehicle_number):
            self.calls.append(("check_vehicle", {"vehicle_number": vehicle_number}))
            return {"vehicle_number": "12가3456", "registered": True, "status": "APPROVED"}

        with patch.object(parking_workflow, "check_vehicle", normalized_vehicle):
            result = parking_workflow.run_parking_workflow("12가-3456")

        self.assertEqual(result["vehicle_number"], "12가3456")
        self.assertEqual(self.calls[-1], ("open_gate", {"vehicle_number": "12가3456"}))

    def test_database_error_is_not_changed_to_not_found(self) -> None:
        class DatabaseUnavailable(RuntimeError):
            code = "DATABASE_UNAVAILABLE"

        def unavailable(vehicle_number):
            raise DatabaseUnavailable(f"postgresql://secret@host/{vehicle_number}")

        with patch.object(parking_workflow, "check_vehicle", unavailable):
            result = parking_workflow.run_parking_workflow("12가3456")

        self.assertFalse(result["success"])
        self.assertIsNone(result["vehicle_status"])
        self.assertEqual(result["termination_reason"], "database_unavailable")
        self.assertEqual(result["error"]["code"], "DATABASE_UNAVAILABLE")
        self.assertNotIn("secret", result["message"])
        self.assertEqual(self.calls, [])

    def test_gate_error_does_not_fall_back_to_other_gate(self) -> None:
        def broken_gate(vehicle_number):
            raise RuntimeError(f"device details: {vehicle_number}")

        with patch.object(parking_workflow, "open_gate", broken_gate):
            result = parking_workflow.run_parking_workflow("12가3456")

        self.assertFalse(result["success"])
        self.assertEqual(result["termination_reason"], "tool_execution_error")
        self.assertFalse(result["gate_opened"])
        self.assertEqual([name for name, _ in self.calls], ["check_vehicle"])

    def test_trace_records_tool_order(self) -> None:
        result = parking_workflow.run_parking_workflow("12가3456")

        self.assertEqual(
            [item["stage"] for item in result["trace"]],
            ["input_validation", "vehicle_check", "policy_decision", "tool_execution"],
        )
        self.assertEqual(
            [item.get("tool_name") for item in result["trace"]],
            [None, "check_vehicle", None, "open_gate"],
        )


if __name__ == "__main__":
    unittest.main()
