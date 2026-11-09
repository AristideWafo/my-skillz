"""Regression tests for discovery and validation of the actual repository layout."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("validator", ROOT / "scripts/validate_skills.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class DiscoveryTests(unittest.TestCase):
    def test_discovers_nested_skills_and_rejects_incomplete_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            valid = root / "skills" / "valid-skill"
            valid.mkdir(parents=True)
            (valid / "SKILL.md").write_text("content", encoding="utf-8")
            (root / "skills" / "broken-skill").mkdir()
            (root / "tools").mkdir()
            (root / "tools" / "README.md").write_text("not a skill", encoding="utf-8")
            errors = []
            self.assertEqual(validator.discover_skills(root, errors), [valid])
            self.assertEqual(errors, ["skills/broken-skill: missing SKILL.md"])

    def test_missing_skills_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors = []
            self.assertEqual(validator.discover_skills(Path(tmp), errors), [])
            self.assertTrue(errors)

    def test_real_skills_are_each_validated(self):
        errors, warnings = [], []
        found = validator.discover_skills(ROOT, errors)
        self.assertTrue(found)
        for skill in found:
            validator.validate_skill(skill, errors, warnings)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
