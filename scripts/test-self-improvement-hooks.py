#!/usr/bin/env python3
"""Exercise the detector's public stdin/stdout contract, without agent runtimes."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


DETECTOR = Path(__file__).resolve().parents[1] / "skills/self-improvement/scripts/error-detector.sh"


class FailureHooks(unittest.TestCase):
    def run_hook(self, agent, payload):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                ["bash", str(DETECTOR), agent],
                input=json.dumps(payload), text=True, capture_output=True, cwd=directory,
            )
            self.assertEqual(list(Path(directory).iterdir()), [], "hooks must not write learnings")
            return result

    def test_failure_context_uses_the_host_contract(self):
        cases = [
            ("claude-code", {"hook_event_name": "PostToolUseFailure", "tool_name": "Bash", "error": "Exit code 7"}),
            ("claude-code", {"hook_event_name": "PostToolUseFailure", "tool_name": "Bash", "error": "Unable to start process"}),
            ("github-copilot", {"toolName": "bash", "error": "Process terminated with status 7"}),
            ("github-copilot", {"toolName": "powershell", "error": "Process terminated with status 7"}),
            ("github-copilot", {"hook_event_name": "PostToolUseFailure", "tool_name": "bash", "error": "Process terminated with status 7"}),
        ]
        for agent, payload in cases:
            with self.subTest(agent=agent, payload=payload):
                result = self.run_hook(agent, payload)
                self.assertEqual(result.stderr, "")
                if agent == "claude-code":
                    self.assertEqual(result.returncode, 0)
                    output = json.loads(result.stdout)["hookSpecificOutput"]
                    self.assertEqual(output["hookEventName"], "PostToolUseFailure")
                    reminder = output["additionalContext"]
                else:
                    self.assertEqual(result.returncode, 2)
                    reminder = result.stdout
                    self.assertTrue(reminder.startswith("<error-detected>"))
                self.assertIn("self-healing", reminder)
                self.assertIn(".learnings/ERRORS.md", reminder)
                self.assertNotIn(payload["error"], reminder, "do not echo potentially sensitive diagnostics")

    def test_success_interruptions_and_other_tools_are_silent(self):
        cases = [
            ("claude-code", {"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_response": "Error: example; 0 failed"}),
            ("claude-code", {"hook_event_name": "PostToolUseFailure", "tool_name": "Bash", "error": "Exit code 130", "is_interrupt": True}),
            ("claude-code", {"hook_event_name": "PostToolUseFailure", "tool_name": "Read", "error": "Permission denied"}),
            ("github-copilot", {"toolName": "bash", "toolResult": {"resultType": "success", "textResultForLlm": "Error: example; 0 failed"}}),
            ("github-copilot", {"hook_event_name": "PostToolUse", "tool_name": "bash", "tool_result": {"result_type": "success", "text_result_for_llm": "Error: example"}}),
            ("github-copilot", {"toolName": "read_file", "error": "Permission denied"}),
        ]
        for agent, payload in cases:
            with self.subTest(agent=agent, payload=payload):
                result = self.run_hook(agent, payload)
                self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))

    def test_invalid_input_is_not_copilot_recovery_guidance(self):
        for payload in ([], None):
            with self.subTest(payload=payload):
                result = self.run_hook("github-copilot", payload)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertTrue(result.stderr)


if __name__ == "__main__":
    unittest.main()
