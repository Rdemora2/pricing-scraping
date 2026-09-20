from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ReviewProfileTests(unittest.TestCase):
    def test_reviewers_cannot_invoke_shell_write_or_child_agents(self):
        for role in ("reviewer", "security-reviewer"):
            content = (ROOT / ".claude" / "agents" / (role + ".md")).read_text()
            header = content.split("---", 2)[1]
            tools = next(line for line in header.splitlines() if line.startswith("tools:"))
            self.assertEqual(tools, "tools: Read, Grep, Glob")
            self.assertIn("disallowedTools: Edit, Write, NotebookEdit, Bash, Agent, Task", header)
            self.assertIn("docs/ai/review-protocol.md", content)
