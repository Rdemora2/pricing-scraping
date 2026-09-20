import copy
import importlib.util
import io
from pathlib import Path
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location(
    "review_result", Path(__file__).resolve().parents[1] / "review_result.py"
)
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)


class ReviewReceiptTests(unittest.TestCase):
    def setUp(self):
        self.receipt = {
            "role": "reviewer", "scope_fingerprint": "a" * 64,
            "status": "complete", "verdict": "APROVAR_LOCALMENTE",
            "summary": "Checked the changed gate and its regression tests.",
            "checked": ["execution_control.select_gates"], "pending": [], "findings": [],
        }

    def test_complete_matching_receipt_passes(self):
        self.assertTrue(review.validate(self.receipt, "a" * 64, "reviewer"))

    def test_cutoff_missing_verdict_or_stale_receipt_cannot_approve(self):
        for key in self.receipt:
            receipt = copy.deepcopy(self.receipt)
            del receipt[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                review.validate(receipt, "a" * 64, "reviewer")
        for scope, role in (("b" * 64, "reviewer"), ("a" * 64, "security-reviewer")):
            with self.assertRaises(ValueError):
                review.validate(self.receipt, scope, role)

    def test_pending_incomplete_and_high_findings_block(self):
        for field, value in (
            ("status", "incomplete"), ("verdict", "CORRIGIR"), ("verdict", "BLOQUEAR"),
            ("pending", ["Proof not executed"]), ("checked", []),
            ("findings", [{"severity": "high", "summary": "Execution escape",
                           "evidence": "select_gates permits full"}]),
        ):
            receipt = {**self.receipt, field: value}
            with self.subTest(field=field, value=value):
                self.assertFalse(review.validate(receipt, "a" * 64, "reviewer"))

    def test_invalid_truncated_or_duplicate_json_fails_closed(self):
        for raw in ("", "I will read the docs.", "{", '{"role":"reviewer","role":"reviewer"}',
                    "x" * 65_537):
            with mock.patch("sys.stdin", io.StringIO(raw)):
                self.assertEqual(review.main(["--scope", "a" * 64, "--role", "reviewer"]), 2)
