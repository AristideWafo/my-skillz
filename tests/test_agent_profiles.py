"""The five installed agent roles retain portable, model-independent profiles."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {"FAST", "BALANCED", "HIGH_REASONING", "SECURITY_CRITICAL", "LONG_CONTEXT"}


class AgentProfileTests(unittest.TestCase):
    def test_exact_existing_roles_and_valid_profiles(self):
        data = json.loads((ROOT / "model_router/agent_profiles.json").read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], 1)
        codex = {p.stem for p in (ROOT / ".codex/agents").glob("*.toml")}
        claude = {p.stem for p in (ROOT / ".claude/agents").glob("*.md")}
        self.assertEqual(set(data["agents"]), codex)
        self.assertEqual(set(data["agents"]), claude)
        for role, mapping in data["agents"].items():
            self.assertIn(mapping["default"], PROFILES, role)
            self.assertTrue(set(mapping["elevate_on"]) <= PROFILES, role)
            for platform, extension in (("codex", "toml"), ("claude", "md")):
                instructions = (ROOT / f".{platform}/agents/{role}.{extension}").read_text(encoding="utf-8")
                self.assertIn("model_router/agent_profiles.json", instructions)


if __name__ == "__main__":
    unittest.main()
