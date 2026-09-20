import json
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class GovernanceContractTests(unittest.TestCase):
    def test_agents_pin_model_and_role_effort(self):
        agents = sorted((ROOT / ".codex" / "agents").glob("*.toml"))
        self.assertGreaterEqual(len(agents), 7)
        self.assertTrue({"worker", "verifier", "reviewer", "delivery-manager"} <= {p.stem for p in agents})
        expected_effort = {
            "delivery-manager": "low",
            "explorer": "medium",
            "reviewer": "medium",
            "security-reviewer": "high",
            "test-designer": "medium",
            "verifier": "low",
            "worker": "medium",
        }
        expected_model = {
            "delivery-manager": "gpt-5.6-terra",
            "explorer": "gpt-5.6-terra",
            "reviewer": "gpt-5.6-terra",
            "security-reviewer": "gpt-5.6-sol",
            "test-designer": "gpt-5.6-terra",
            "verifier": "gpt-5.6-terra",
            "worker": "gpt-5.6-terra",
        }
        for path in agents:
            config = tomllib.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(config["model"], expected_model[path.stem])
            self.assertEqual(config["model_reasoning_effort"], expected_effort[path.stem])
            self.assertEqual(config["approval_policy"], "never")

    def test_reasoning_policy_is_adaptive_and_bounded(self):
        policy = (ROOT / "docs" / "ai" / "reasoning-policy.md").read_text(
            encoding="utf-8"
        )
        for fragment in ("Gatilhos para `sol`", "Rebaixamento obrigatório", "não integra o", "roteamento automático"):
            self.assertIn(fragment, policy)

    def test_execution_control_contract_is_present_and_machine_readable(self):
        policy = json.loads(
            (ROOT / ".codex" / "execution-policy.json").read_text(encoding="utf-8")
        )
        self.assertEqual(policy["schema_version"], 1)
        self.assertEqual(policy["managed_by"], "valiant-codex-kit")
        self.assertTrue((ROOT / ".codex" / "execution_control.py").is_file())
        self.assertTrue((ROOT / "docs" / "ai" / "execution-contract.md").is_file())
        self.assertEqual(policy["routing"]["profiles"]["critical"]["read_only"], True)

    def test_delivery_state_contract_is_complete(self):
        delivery = ROOT / "docs" / "ai" / "delivery"
        required = {
            "BASELINE.md", "LOCAL_ACTIVATION.md", "MULTI_ROOT.md", "QUALITY_GATES.md",
            "QUEUE.md", "STATUS.md", "WORKFLOW.md", "evidence/README.md",
        }
        observed = {p.relative_to(delivery).as_posix() for p in delivery.rglob("*.md")}
        self.assertTrue(required <= observed)
        states = (delivery / "STATUS.md").read_text(encoding="utf-8")
        for state in ("WAITING", "READY", "IN_PROGRESS", "IN_REVIEW", "VERIFIED", "REOPENED", "STALE", "BLOCKED_EXTERNAL", "BLOCKED_TECHNICAL"):
            self.assertIn(state, states)

    def test_security_and_delivery_guardrails_remain_present(self):
        rules = (ROOT / ".codex" / "rules" / "default.rules").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn('decision = "allow"', rules)
        for fragment in ("rebase", "--no-verify", "--force-with-lease"):
            self.assertIn(fragment, rules)
        self.assertIn("Nunca invoque Codex Security", agents)


if __name__ == "__main__":
    unittest.main()
