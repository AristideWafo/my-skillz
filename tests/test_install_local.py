"""Exercise installation in isolated homes, never the user's settings."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("installer", ROOT / "scripts/install_local.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def test_preview_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = installer.install(ROOT, home, ["codex", "claude"])
            self.assertGreater(result["changed"], 0)
            self.assertEqual(list(home.iterdir()), [])

    def test_install_is_repeatable_and_preserves_settings_and_original_doc(self):
        with tempfile.TemporaryDirectory(prefix="skills home ") as tmp:
            home = Path(tmp)
            config = home / ".claude/settings.json"
            config.parent.mkdir()
            config.write_text('{"unrelated":true}', encoding="utf-8")
            original = home / ".agents/skills/doc-coauthoring/SKILL.md"
            original.parent.mkdir(parents=True)
            original.write_text("original", encoding="utf-8")
            first = installer.install(ROOT, home, ["codex", "claude"], True)
            second = installer.install(ROOT, home, ["codex", "claude"], True)
            self.assertTrue(first["verified"])
            self.assertEqual(second["changed"], 0)
            self.assertEqual(original.read_text(), "original")
            self.assertEqual(json.loads(config.read_text()), {"unrelated": True})
            for platform in (".agents", ".claude"):
                doc = home / platform / "skills" / installer.DOC_ALIAS / "SKILL.md"
                self.assertIn("name: " + installer.DOC_ALIAS, doc.read_text(encoding="utf-8"))
            agent = (home / ".codex/agents/solution-architect.toml").read_text(encoding="utf-8")
            self.assertIn(installer.DOC_ALIAS, agent)
            self.assertIn(home.as_posix(), agent)
            profiles = home / ".my-skillz/model_router/agent_profiles.json"
            self.assertTrue(profiles.is_file())
            self.assertIn(profiles.as_posix(), agent)
            self.assertTrue((home / ".my-skillz/model_router/core.py").is_file())
            self.assertTrue((home / ".my-skillz/model-router-v01.md").is_file())

    def test_conflict_aborts_before_writing_other_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            existing = home / ".codex/agents/backend-implementer.toml"
            existing.parent.mkdir(parents=True)
            existing.write_text("custom", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "preserved"):
                installer.install(ROOT, home, ["codex"], True)
            self.assertEqual(existing.read_text(), "custom")
            self.assertFalse((home / ".agents").exists())

    def test_local_modification_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            installer.install(ROOT, home, ["codex"], True)
            edited = home / ".agents/skills/docker-builder/SKILL.md"
            edited.write_text("personal changes", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "locally modified"):
                installer.install(ROOT, home, ["codex"], True)
            self.assertEqual(edited.read_text(), "personal changes")

    def test_identical_unmanaged_file_is_not_silently_adopted(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            plan = installer.build_plan(ROOT, home, ["codex"])
            path, data = next(iter(plan.items()))
            path.parent.mkdir(parents=True)
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, "Unmanaged"):
                installer.install(ROOT, home, ["codex"], True)
            self.assertFalse((home / ".my-skillz/manifest.json").exists())

    def test_write_failure_restores_previous_installation(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            installer.install(ROOT, home, ["codex"], True)
            manifest = home / ".my-skillz/manifest.json"
            before = manifest.read_bytes()
            original = installer.atomic_write
            def fail_manifest_once(path, data):
                if path == manifest and not getattr(fail_manifest_once, "failed", False):
                    fail_manifest_once.failed = True
                    raise OSError("simulated disk failure")
                original(path, data)
            with patch.object(installer, "atomic_write", side_effect=fail_manifest_once):
                with self.assertRaisesRegex(OSError, "simulated"):
                    installer.install(ROOT, home, ["codex", "claude"], True)
            self.assertEqual(manifest.read_bytes(), before)
            self.assertFalse(any((home / ".claude").rglob("SKILL.md")))

    def test_managed_update_has_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            installer.install(ROOT, home, ["codex"], True)
            edited = home / ".agents/skills/docker-builder/SKILL.md"
            edited.write_bytes(b"old managed version")
            manifest = home / ".my-skillz/manifest.json"
            state = json.loads(manifest.read_text())
            state["files"][edited.relative_to(home).as_posix()] = installer.digest(edited.read_bytes())
            manifest.write_text(json.dumps(state))
            result = installer.install(ROOT, home, ["codex"], True)
            backup = Path(result["backup"]) / edited.relative_to(home)
            self.assertEqual(backup.read_bytes(), b"old managed version")

    def test_destination_must_stay_in_selected_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            with self.assertRaises(ValueError):
                installer.contained(home, home / ".." / "outside")


if __name__ == "__main__":
    unittest.main()
