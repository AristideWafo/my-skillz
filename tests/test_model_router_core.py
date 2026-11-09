"""Deterministic policy tests use simulated models, never paid APIs."""
import copy
import unittest

from model_router.core import ConfigError, profile_task, select_model


def model(ident="safe", **overrides):
    base = dict(id=ident, provider="approved", availability="CONFIRMED", environments=["codex"], privacy="CONFIDENTIAL", tools=["shell"], context_tokens=500000, permissions=["read", "write"], profiles=["FAST", "BALANCED", "HIGH_REASONING", "SECURITY_CRITICAL", "LONG_CONTEXT"], input_usd_per_million=2.0, output_usd_per_million=10.0, billing_basis="SIMULATED", source="https://example.invalid/verified", verified_at="2026-11-09")
    return {**base, **overrides}


def inputs():
    registry = {"schema_version": 1, "models": [model()]}
    request = dict(agent="backend-implementer", profile="BALANCED", required_tools=["shell"], min_context_tokens=200000, privacy="INTERNAL", required_permissions=["read", "write"], environment="codex")
    policy = dict(allowed_providers=["approved"], allowed_environments=["codex"], allowed_privacy=["INTERNAL"], available_permissions=["read", "write"], max_cost_usd=1.0, estimated_input_tokens=100000, estimated_output_tokens=10000, billing_basis="SIMULATED", billing_verified=True)
    return registry, request, policy


class RouterTests(unittest.TestCase):
    def test_selects_authorized_model(self):
        self.assertEqual(select_model(*inputs())["model_id"], "safe")

    def test_forbidden_provider_no_fallback(self):
        registry, request, policy = inputs()
        registry["models"].append(model("cheap", provider="forbidden", input_usd_per_million=0))
        policy["allowed_providers"] = []
        result = select_model(registry, request, policy)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("provider not allowed", result["excluded"]["cheap"])

    def test_missing_candidate_explains_reason(self):
        registry, request, policy = inputs()
        request["min_context_tokens"] = 600000
        result = select_model(registry, request, policy)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("context too small", result["excluded"]["safe"])

    def test_privacy_restriction(self):
        registry, request, policy = inputs()
        request["privacy"] = "LOCAL_ONLY"
        policy["allowed_privacy"] = ["LOCAL_ONLY"]
        self.assertIn("privacy requirement unmet", select_model(registry, request, policy)["excluded"]["safe"])

    def test_unknown_model_is_never_selected(self):
        registry, request, policy = inputs()
        registry["models"][0]["availability"] = "UNKNOWN"
        self.assertEqual(select_model(registry, request, policy)["status"], "BLOCKED")

    def test_invalid_configuration_rejected(self):
        registry, request, policy = inputs()
        registry["models"][0]["extra"] = "unrecognized"
        with self.assertRaises(ConfigError):
            select_model(registry, request, policy)

    def test_budget_is_hard_limit(self):
        registry, request, policy = inputs()
        policy["max_cost_usd"] = 0.01
        self.assertIn("budget exceeded", select_model(registry, request, policy)["excluded"]["safe"])

    def test_unverified_or_mismatched_billing_blocks_selection(self):
        registry, request, policy = inputs()
        policy["billing_verified"] = False
        self.assertIn("billing basis unverified or incompatible", select_model(registry, request, policy)["excluded"]["safe"])
        policy["billing_verified"] = True
        policy["billing_basis"] = "API"
        self.assertIn("billing basis unverified or incompatible", select_model(registry, request, policy)["excluded"]["safe"])

    def test_local_only_cannot_be_inferred_from_registry_label(self):
        registry, request, policy = inputs()
        registry["models"][0]["privacy"] = "LOCAL_ONLY"
        request["privacy"] = "LOCAL_ONLY"
        policy["allowed_privacy"] = ["LOCAL_ONLY"]
        self.assertIn("local execution not verified by V0.1 adapters", select_model(registry, request, policy)["excluded"]["safe"])

    def test_profile_requires_matching_model(self):
        registry, request, policy = inputs()
        registry["models"].append(model("fast-only", profiles=["FAST"], input_usd_per_million=0))
        request["profile"] = "HIGH_REASONING"
        self.assertEqual(select_model(registry, request, policy)["model_id"], "safe")
        self.assertEqual(profile_task("solution-architect"), "HIGH_REASONING")
        self.assertEqual(profile_task("backend-implementer", complexity="simple"), "FAST")
        self.assertEqual(profile_task("backend-implementer", security_critical=True, long_context=True), "SECURITY_CRITICAL")

    def test_tool_permissions_and_environment_are_hard_limits(self):
        registry, request, policy = inputs()
        request["required_tools"] = ["browser"]
        request["required_permissions"] = ["production"]
        request["environment"] = "claude"
        reasons = select_model(registry, request, policy)["excluded"]["safe"]
        self.assertIn("required tools unavailable", reasons)
        self.assertIn("required permissions unavailable", reasons)
        self.assertIn("environment incompatible", reasons)

    def test_cheapest_only_after_hard_filter(self):
        registry, request, policy = inputs()
        registry["models"].append(model("ineligible-cheap", provider="forbidden", input_usd_per_million=0, output_usd_per_million=0))
        registry["models"].append(model("eligible-cheap", input_usd_per_million=1, output_usd_per_million=5))
        self.assertEqual(select_model(registry, request, policy)["model_id"], "eligible-cheap")

    def test_duplicate_identity_and_nonfinite_price_rejected(self):
        registry, request, policy = inputs()
        registry["models"].append(copy.deepcopy(registry["models"][0]))
        with self.assertRaises(ConfigError):
            select_model(registry, request, policy)
        registry["models"].pop()
        registry["models"][0]["input_usd_per_million"] = float("nan")
        with self.assertRaises(ConfigError):
            select_model(registry, request, policy)


if __name__ == "__main__":
    unittest.main()
