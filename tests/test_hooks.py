#!/usr/bin/env python3
"""Behavior tests for cross-platform command hooks."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_hook(script: str, payload: dict) -> tuple[int, str, str]:
    result = subprocess.run(
        [sys.executable, str(ROOT / "hooks" / script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    return result.returncode, result.stdout, result.stderr


class SafetyGuardTests(unittest.TestCase):
    def payload(self, command: str) -> dict:
        return {
            "cwd": str(ROOT),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
        }

    def test_allows_scoped_cleanup(self) -> None:
        code, stdout, _ = run_hook("safety_guard.py", self.payload("rm -rf node_modules"))
        self.assertEqual(code, 0)
        self.assertEqual(stdout, "")

    def test_blocks_repository_deletion(self) -> None:
        code, stdout, _ = run_hook("safety_guard.py", self.payload("rm -rf ."))
        self.assertEqual(code, 0)
        decision = json.loads(stdout)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")

    def test_blocks_hard_reset(self) -> None:
        _, stdout, _ = run_hook("safety_guard.py", self.payload("git reset --hard HEAD~1"))
        self.assertEqual(json.loads(stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_blocks_forced_git_clean_with_separate_flags(self) -> None:
        _, stdout, _ = run_hook("safety_guard.py", self.payload("git clean -f -d"))
        self.assertEqual(json.loads(stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_blocks_forced_git_clean_with_combined_flags(self) -> None:
        _, stdout, _ = run_hook("safety_guard.py", self.payload("git clean -fdx"))
        self.assertEqual(json.loads(stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_blocks_docker_prune_all(self) -> None:
        _, stdout, _ = run_hook("safety_guard.py", self.payload("docker system prune --all"))
        self.assertEqual(json.loads(stdout)["hookSpecificOutput"]["permissionDecision"], "deny")


class ContextHookTests(unittest.TestCase):
    def test_emits_session_context(self) -> None:
        code, stdout, _ = run_hook(
            "session_context.py",
            {"cwd": str(ROOT), "hook_event_name": "SessionStart", "source": "startup"},
        )
        self.assertEqual(code, 0)
        output = json.loads(stdout)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "SessionStart")
        self.assertIn("software-reviewer", output["additionalContext"])


class PostEditCheckTests(unittest.TestCase):
    def test_reports_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            path = Path(temporary) / "invalid.json"
            path.write_text("{", encoding="utf-8")
            payload = {
                "cwd": str(ROOT),
                "hook_event_name": "PostToolUse",
                "tool_name": "Write",
                "tool_input": {"file_path": str(path)},
            }
            code, stdout, _ = run_hook("post_edit_check.py", payload)
        self.assertEqual(code, 0)
        self.assertIn("Post-edit syntax check", json.loads(stdout)["systemMessage"])

    def test_accepts_valid_toml(self) -> None:
        payload = {
            "cwd": str(ROOT),
            "hook_event_name": "PostToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": str(ROOT / ".codex" / "agents" / "software-reviewer.toml")},
        }
        code, stdout, _ = run_hook("post_edit_check.py", payload)
        self.assertEqual(code, 0)
        self.assertEqual(stdout, "")


if __name__ == "__main__":
    unittest.main()
