import unittest

from model_router.adapters import prepare_adapter, reconcile_execution


class AdapterTests(unittest.TestCase):
    def test_codex_generates_only_native_model_field(self):
        result = prepare_adapter("codex", "backend-implementer", "gpt-6.1-sol",
                                 'name = "backend-implementer"\ndeveloper_instructions = """Stay scoped."""')
        self.assertEqual(result.mode, "CONFIG_GENERATED")
        self.assertEqual(result.status, "READY_FOR_REVIEW")
        self.assertEqual(result.snippet, 'model = "gpt-6.1-sol"')
        self.assertEqual(result.target, ".codex/agents/backend-implementer.toml")

    def test_claude_existing_model_conflicts_without_overwrite(self):
        result = prepare_adapter("claude-code", "software-reviewer", "claude-opus-5-5",
                                 "---\nname: software-reviewer\nmodel: claude-sonnet-5-5\n---\nReview")
        self.assertEqual(result.status, "CONFLICT")
        self.assertIn("requires explicit review", result.reason)

    def test_advisory_never_claims_applied(self):
        result = prepare_adapter("codex", "solution-architect", "gpt-6-astra", mode="ADVISORY")
        self.assertEqual(result.status, "RECOMMENDED")
        self.assertIsNone(result.target)
        self.assertIsNone(result.snippet)

    def test_native_requires_independent_observation(self):
        with self.assertRaises(ValueError):
            prepare_adapter("codex", "solution-architect", "gpt-6-astra", mode="NATIVE")
        result = reconcile_execution("gpt-6-astra", None, False, {"gpt-6-astra"})
        self.assertEqual(result.status, "UNVERIFIED")

    def test_verified_native_only_after_exact_match(self):
        result = reconcile_execution("gpt-6-astra", "gpt-6-astra", True, {"gpt-6-astra"})
        self.assertEqual(result.status, "VERIFIED_NATIVE")

    def test_substitution_blocks_even_when_other_model_approved(self):
        result = reconcile_execution("gpt-6-astra", "gpt-6.1-sol", True,
                                     {"gpt-6-astra", "gpt-6.1-sol"})
        self.assertEqual(result.status, "BLOCKED")

    def test_unapproved_executed_model_blocks(self):
        result = reconcile_execution("gpt-6-astra", "gpt-6-luna", True, {"gpt-6-astra"})
        self.assertEqual(result.status, "BLOCKED")

    def test_invalid_fields_rejected(self):
        for env, agent, model in (("other", "good", "good"),
                                  ("codex", "../escape", "good"),
                                  ("codex", "good", 'bad"\nmodel = "other')):
            with self.assertRaises(ValueError):
                prepare_adapter(env, agent, model)


if __name__ == "__main__":
    unittest.main()
