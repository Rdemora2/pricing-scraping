import argparse
import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / ".codex" / "execution_control.py"
SPEC = importlib.util.spec_from_file_location("execution_control", MODULE_PATH)
execution_control = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(execution_control)


class ExecutionControlTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(
            (ROOT / ".codex" / "execution-policy.json").read_text(encoding="utf-8")
        )

    def test_astra_escalation_is_selective_and_does_not_leak(self):
        before = json.dumps(self.policy, sort_keys=True)
        for signal, role in (
            ("architecture-complex", "reviewer"),
            ("contract-conflict", "reviewer"),
            ("diagnosis-exhausted", "explorer"),
        ):
            with self.subTest(signal=signal):
                route = execution_control.classify(self.policy, [], [signal])
                self.assertEqual(route["risk"], "high")
                self.assertEqual(route["profile"]["gate_level"], "full")
                overrides = route["profile"]["model_overrides"]
                self.assertEqual(overrides[role], "gpt-6-astra/high")
                self.assertEqual(
                    [r for r, m in overrides.items() if m.startswith("gpt-6-astra")],
                    [role],
                )
                self.assertEqual(overrides["worker"], "gpt-5.6-sol/high")
                self.assertNotIn("verifier", overrides)
                self.assertNotIn("delivery-manager", overrides)
        self.assertEqual(json.dumps(self.policy, sort_keys=True), before)
        routine = execution_control.classify(self.policy, ["README.md"], [])
        self.assertFalse(routine["profile"].get("model_overrides"))
        migration = execution_control.classify(self.policy, [], ["migration"])
        self.assertNotIn("gpt-6-astra/high", migration["profile"]["model_overrides"].values())

    def test_astra_signals_preserve_critical_read_only_boundary(self):
        route = execution_control.classify(
            self.policy, [], ["production", "architecture-complex", "diagnosis-exhausted"]
        )
        self.assertEqual(route["risk"], "critical")
        self.assertTrue(route["profile"]["read_only"])
        self.assertEqual(route["profile"]["roles"], ["security-reviewer"])
        self.assertFalse(route["profile"].get("model_overrides"))

    def test_read_only_rejects_every_executable_gate_override(self):
        route = execution_control.classify(self.policy, [], ["production"])
        self.assertEqual(execution_control.select_gates(self.policy, route), [])
        self.assertEqual(execution_control.select_gates(self.policy, route, "none"), [])
        for level in ("fast", "relevant", "full"):
            with self.subTest(level=level), self.assertRaises(SystemExit):
                execution_control.select_gates(self.policy, route, level)

    def test_read_only_cli_never_dispatches_runner(self):
        for extra in ([], ["--level", "full"]):
            with self.subTest(extra=extra):
                with mock.patch.object(execution_control, "run_gates") as runner:
                    with self.assertRaises(SystemExit):
                        with mock.patch("sys.argv", ["execution_control", "--root", str(ROOT),
                                        "gates", "--file", "README.md",
                                        "--signal", "production", "--run", *extra]):
                            execution_control.main()
                    runner.assert_not_called()

    def test_routing_uses_paths_and_explicit_risk_signals(self):
        docs_route = execution_control.classify(self.policy, ["docs/guide.md"], [])
        code_route = execution_control.classify(self.policy, ["internal/order/service.go"], [])
        auth_route = execution_control.classify(
            self.policy, ["internal/order/service.go"], ["auth"]
        )
        critical_route = execution_control.classify(self.policy, [], ["production"])

        self.assertEqual(docs_route["risk"], "low")
        self.assertEqual(code_route["risk"], "medium")
        self.assertEqual(auth_route["risk"], "high")
        self.assertEqual(
            auth_route["profile"]["model_overrides"]["worker"],
            "gpt-5.6-sol/high",
        )
        self.assertEqual(critical_route["risk"], "critical")
        self.assertTrue(critical_route["profile"]["read_only"])

    def test_gate_selection_is_incremental_deduplicated_and_skips_todo(self):
        policy = json.loads(json.dumps(self.policy))
        policy["gates"]["commands"].update(
            {
                "test_fast": "go test ./...",
                "lint": "go vet ./...",
                "typecheck": "go vet ./...",
                "test_full": "go test -race ./...",
                "build": "TODO",
            }
        )
        route = execution_control.classify(policy, ["internal/order/service.go"], [])

        selected = execution_control.select_gates(policy, route)

        self.assertEqual(
            selected,
            [
                {"key": "test_fast", "command": "go test ./..."},
                {"key": "lint", "command": "go vet ./..."},
            ],
        )
        docs_route = execution_control.classify(policy, ["README.md"], [])
        self.assertEqual(execution_control.select_gates(policy, docs_route), [])

        high_route = execution_control.classify(policy, ["internal/auth/login.go"], [])
        with self.assertRaises(SystemExit):
            execution_control.select_gates(policy, high_route, "fast")

    def test_scope_rejects_absolute_and_parent_paths(self):
        with self.assertRaises(SystemExit):
            execution_control.normalize_files(["../secret.txt"])
        with self.assertRaises(SystemExit):
            execution_control.normalize_files(["/tmp/secret.txt"])

    def test_gate_runner_stops_on_first_failure_and_prints_only_tail(self):
        policy = json.loads(json.dumps(self.policy))
        policy["gates"]["failure_tail_lines"] = 2
        selected = [
            {"key": "test_fast", "command": "fake-test"},
            {"key": "lint", "command": "fake-lint"},
        ]
        failure = subprocess.CompletedProcess(
            args="fake-test",
            returncode=7,
            stdout="line-1\nline-2\nline-3\n",
            stderr="",
        )

        output = io.StringIO()
        with mock.patch.object(execution_control.subprocess, "run", return_value=failure) as run:
            with contextlib.redirect_stdout(output):
                result = execution_control.run_gates(Path.cwd(), policy, selected)

        self.assertEqual(result, 7)
        self.assertEqual(run.call_count, 1)
        self.assertNotIn("line-1", output.getvalue())
        self.assertIn("line-2", output.getvalue())
        self.assertIn("line-3", output.getvalue())

    @unittest.skipUnless(shutil.which("git"), "Git é necessário para fingerprint de estado")
    def test_context_capsule_is_idempotent_and_invalidated_by_scoped_change(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".codex").mkdir()
            shutil.copy2(ROOT / ".codex" / "execution-policy.json", root / ".codex")
            source = root / "service.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "Valiant Test"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
            subprocess.run(["git", "-C", str(root), "add", "service.py"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "chore(test): baseline"], check=True)
            args = argparse.Namespace(
                task_id="UNIT-01",
                goal="Alterar valor observável",
                acceptance=["Teste demonstra o novo valor"],
                file=["service.py"],
                signal=["behavior"],
            )

            context, first_changed = execution_control.prepare_context(root, self.policy, args)
            _, second_changed = execution_control.prepare_context(root, self.policy, args)
            source.write_text("VALUE = 2\n", encoding="utf-8")
            _, third_changed = execution_control.prepare_context(root, self.policy, args)

            self.assertTrue(first_changed)
            self.assertFalse(second_changed)
            self.assertTrue(third_changed)
            self.assertIn("Contexto compacto", context.read_text(encoding="utf-8"))

    def test_telemetry_records_only_bounded_operational_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            args = argparse.Namespace(
                task_id="UNIT-02",
                stage="verify",
                outcome="success",
                model="gpt-5.6-terra",
                effort="low",
                cycles=1,
                tool_calls=3,
                duration_seconds=4.5,
                promoted=False,
            )

            path = execution_control.record_metric(root, self.policy, args)
            summary = execution_control.summarize_metrics(root, self.policy, 100)
            record = json.loads(path.read_text(encoding="utf-8"))

            self.assertNotIn("goal", record)
            self.assertNotIn("prompt", record)
            self.assertEqual(summary["records"], 1)
            self.assertEqual(summary["first_pass_success_rate"], 1.0)
            self.assertEqual(summary["tool_calls"], 3)


if __name__ == "__main__":
    unittest.main()
