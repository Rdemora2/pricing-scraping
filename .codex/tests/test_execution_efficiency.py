"""Regression proofs for multi-root isolation, routing and scoped evidence."""
from __future__ import annotations

import json
from contextlib import nullcontext
import os
import py_compile
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".codex"))
import execution_control as control
import gate_cache
import policy_contract


class EfficiencyTests(unittest.TestCase):
    def test_real_governance_cache_reuse_and_invalidation(self):
        import shutil
        for name in ("execution_control.py", "gate_cache.py", "policy_contract.py", "config.toml", "execution-policy.json"):
            shutil.copyfile(ROOT / ".codex" / name, self.root / ".codex" / name)
        self.assertEqual(policy_contract.validate(self.root), [])
        gate = {**self.policy['gates']['evidence_gates']['governance_contract'],
                'key': 'governance_contract'}
        gate['command'] = ' '.join(gate['argv'])
        self.assertEqual(control.run_gates(self.root, self.policy, [gate], "real"), 0)
        with mock.patch.object(control.subprocess, "run", side_effect=AssertionError("must reuse")):
            self.assertEqual(control.run_gates(self.root, self.policy, [gate], "real"), 0)
        config = self.root / ".codex/config.toml"
        config.write_text(config.read_text().replace("fast_mode = false", "fast_mode = true"))
        self.assertNotEqual(control.run_gates(self.root, self.policy, [gate], "real"), 0)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "inputs").mkdir()
        (self.root / "inputs/a.py").write_text("before")
        (self.root / ".codex").mkdir()
        for name in ("execution_control.py", "gate_cache.py"):
            (self.root / ".codex" / name).write_text("# fixture\n")
        self.gate = {"key": "unit", "cwd": ".", "argv": ["python3", "-I", "-S", "-B", "-V"],
                     "cache": {"kind": "isolated-python-v1", "inputs": ["inputs"]}}
        self.policy = control.load_policy(ROOT)

    def fingerprint(self):
        return control.gate_fingerprint(self.root, self.gate, [])

    def test_roots_never_share_evidence(self):
        with tempfile.TemporaryDirectory() as other:
            second = Path(other)
            with mock.patch.object(control, "gate_fingerprint", return_value="abc"), mock.patch.object(gate_cache, "execution_root", return_value=nullcontext(self.root)), mock.patch.object(control.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
                control.run_gates(self.root, self.policy, [self.gate], "same-task")
                control.run_gates(second, self.policy, [self.gate], "same-task")
                control.run_gates(self.root, self.policy, [self.gate], "same-task")
                self.assertEqual(run.call_count, 2)

    def test_operational_roles_are_stages_not_mandatory_agents(self):
        for risk, roles in (("low", ["worker"]), ("medium", ["worker", "reviewer"]),
                            ("high", ["worker", "reviewer", "security-reviewer"])):
            profile = self.policy["routing"]["profiles"][risk]
            self.assertEqual(profile["roles"], roles)
            self.assertEqual(profile["operational_stages"], ["verifier", "delivery-manager"])
        self.assertTrue(self.policy["routing"]["profiles"]["critical"]["read_only"])

    def test_fast_disabled_in_config_policy_and_cli(self):
        config = tomllib.loads((ROOT / ".codex/config.toml").read_text())
        self.assertIs(config["features"]["fast_mode"], False)
        self.assertNotIn(config.get("service_tier"), ("fast", "priority", "ultrafast"))
        self.assertNotIn("fast", self.policy["gates"]["levels"])
        with self.assertRaises(SystemExit):
            control.build_parser().parse_args(["gates", "--level", "fast"])
        self.policy["routing"]["profiles"]["low"]["gate_level"] = "fast"
        (self.root / ".codex/execution-policy.json").write_text(json.dumps(self.policy))
        with self.assertRaises(SystemExit):
            control.load_policy(self.root)

    def test_unrelated_docs_git_and_changed_file_list_do_not_invalidate(self):
        before = self.fingerprint()
        self.assertIsNotNone(before)
        (self.root / "README.md").write_text("unrelated")
        with mock.patch.object(control, "git_output", side_effect=AssertionError("no Git")):
            self.assertEqual(before, control.gate_fingerprint(self.root, self.gate, ["README.md"]))

    def test_content_addition_rename_and_deletion_invalidate(self):
        before = self.fingerprint()
        first = self.root / "inputs/a.py"
        first.write_text("after")
        changed = self.fingerprint()
        self.assertNotEqual(before, changed)
        second = self.root / "inputs/b.py"
        second.write_text("dependency not in changed-files")
        added = self.fingerprint()
        self.assertNotEqual(changed, added)
        renamed = self.root / "inputs/c.py"
        second.rename(renamed)
        self.assertNotEqual(added, self.fingerprint())
        renamed.unlink()
        self.assertEqual(changed, self.fingerprint())

    def test_command_and_controller_changes_invalidate(self):
        before = self.fingerprint()
        self.gate["argv"].append("extra")
        self.assertNotEqual(before, self.fingerprint())
        before = self.fingerprint()
        (self.root / ".codex/execution_control.py").write_text("changed")
        self.assertNotEqual(before, self.fingerprint())

    def test_missing_private_symlink_unreadable_and_large_inputs_disable_reuse(self):
        for name in ("missing", ".env", "private"):
            self.gate["cache"]["inputs"] = [name]
            self.assertIsNone(self.fingerprint())
        self.gate["cache"]["inputs"] = ["inputs"]
        with mock.patch.object(gate_cache, "_digest", side_effect=PermissionError):
            self.assertIsNone(self.fingerprint())
        with mock.patch.object(gate_cache, "MAX_BYTES", 1):
            self.assertIsNone(self.fingerprint())
        try:
            (self.root / "inputs/link").symlink_to(self.root / "inputs/a.py")
        except OSError:
            self.skipTest("symlinks unavailable")
        self.assertIsNone(self.fingerprint())

    def test_no_manifest_means_no_cache(self):
        del self.gate["cache"]
        self.assertIsNone(self.fingerprint())
        self.assertIsNone(gate_cache.execution_environment(self.gate))

    def test_cache_environment_is_closed_and_python_is_current_runtime(self):
        with mock.patch.dict(os.environ, {"PYTHONPATH": "/untrusted", "CI": "true", "DATABASE_URL": "synthetic"}):
            env = gate_cache.execution_environment(self.gate)
            self.assertNotIn("PYTHONPATH", env)
            self.assertNotIn("CI", env)
            self.assertNotIn("DATABASE_URL", env)
            self.assertEqual(gate_cache.command(self.gate)[0], sys.executable)

    def test_changed_during_run_failure_legacy_and_disabled_evidence_never_reuse(self):
        for mode in ("changed", "failure", "legacy", "disabled", "malformed"):
            with self.subTest(mode=mode):
                evidence = control.evidence_path(self.root, mode, "unit")
                if mode == "legacy":
                    evidence.write_text(json.dumps({"schema_version": 1, "fingerprint": "abc", "outcome": "success"}))
                if mode == "malformed":
                    evidence.write_text("[]")
                fingerprints = ["abc", "def", "abc", "def"] if mode == "changed" else None
                value = None if mode == "disabled" else "abc"
                result = subprocess.CompletedProcess([], 1 if mode == "failure" else 0, "", "")
                with mock.patch.object(control, "gate_fingerprint", side_effect=fingerprints, return_value=value), mock.patch.object(gate_cache, "execution_root", return_value=nullcontext(self.root)), mock.patch.object(control.subprocess, "run", return_value=result) as run:
                    control.run_gates(self.root, self.policy, [self.gate], mode)
                    self.assertEqual(run.call_count, 1)
                    if mode not in ("legacy", "malformed"):
                        control.run_gates(self.root, self.policy, [self.gate], mode)
                        self.assertEqual(run.call_count, 2)

    def test_aba_worktree_change_cannot_certify_different_bytes(self):
        source = self.root / "inputs/a.py"
        source.write_text("INVALID A")
        observed = []

        def execute(argv, *, cwd, **kwargs):
            self.assertNotEqual(cwd, self.root)
            source.write_text("VALID B")
            consumed = (cwd / "inputs/a.py").read_text()
            observed.append(cwd)
            source.write_text("INVALID A")
            return subprocess.CompletedProcess(argv, 0 if consumed == "VALID B" else 1, "", "")

        with mock.patch.object(control.subprocess, "run", side_effect=execute) as run:
            self.assertEqual(control.run_gates(self.root, self.policy, [self.gate], "aba"), 1)
            self.assertEqual(control.run_gates(self.root, self.policy, [self.gate], "aba"), 1)
            self.assertEqual(run.call_count, 2)
        self.assertTrue(all(not directory.exists() for directory in observed))

    def test_snapshot_rejects_changes_before_capture(self):
        expected = self.fingerprint()
        (self.root / "inputs/a.py").write_text("new")
        with self.assertRaises(ValueError):
            with gate_cache.execution_root(self.root, self.gate, expected):
                self.fail("must not execute inconsistent snapshot")

    def test_existing_divergent_bytecode_is_not_consumed_by_snapshot(self):
        dependency = self.root / "inputs/dependency.py"
        dependency.write_text("VALUE = 1\n")
        py_compile.compile(str(dependency), doraise=True,
                           invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
        dependency.write_text("VALUE = 0\n")
        script = self.root / "inputs/check.py"
        script.write_text(
            "import importlib.util, pathlib, sys\n"
            "spec = importlib.util.spec_from_file_location('dep', pathlib.Path(__file__).with_name('dependency.py'))\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(module)\n"
            "sys.exit(0 if module.VALUE == 1 else 1)\n"
        )
        self.gate["argv"] = ["python3", "-I", "-S", "-B", "inputs/check.py"]
        live = subprocess.run(gate_cache.command(self.gate), cwd=self.root,
                              env=gate_cache.execution_environment(self.gate), capture_output=True)
        self.assertEqual(live.returncode, 0, "falsifier must consume the divergent bytecode")
        self.assertEqual(control.run_gates(self.root, self.policy, [self.gate], "bytecode"), 1)


if __name__ == "__main__":
    unittest.main()
