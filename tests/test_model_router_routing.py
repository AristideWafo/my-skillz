"""Cross-module checks for role mapping, policy gating, and adapter preparation."""
import unittest

from model_router.adapters import reconcile_execution
from model_router.core import ConfigError, load_registry
from model_router.routing import route_task
from test_model_router_core import inputs
from pathlib import Path


class RoutingTests(unittest.TestCase):
    def test_bundled_unknown_models_cannot_be_routed(self):
        registry = load_registry(Path(__file__).resolve().parents[1] / "model_router/registry.json")
        _, request, policy = inputs()
        request["required_tools"] = ["shell"]
        policy["allowed_providers"] = ["openai"]
        result = route_task(registry, request, policy)
        self.assertEqual(result["decision"]["status"], "BLOCKED")
        self.assertIsNone(result["adapter"])

    def test_role_default_reaches_adapter_as_unapplied_snippet(self):
        registry, request, policy = inputs()
        request.pop("profile")
        result = route_task(registry, request, policy)
        self.assertEqual(result["decision"]["profile"], "BALANCED")
        self.assertEqual(result["adapter"].status, "READY_FOR_REVIEW")
        self.assertEqual(result["adapter"].mode, "CONFIG_GENERATED")

    def test_high_reasoning_override_excludes_fast_candidate(self):
        registry, request, policy = inputs()
        registry["models"][0]["profiles"] = ["FAST", "BALANCED"]
        request["profile"] = "HIGH_REASONING"
        result = route_task(registry, request, policy)
        self.assertEqual(result["decision"]["status"], "BLOCKED")
        self.assertIsNone(result["adapter"])

    def test_unknown_role_and_unallowed_override_rejected(self):
        registry, request, policy = inputs()
        request["agent"] = "invented-agent"
        with self.assertRaises(ConfigError):
            route_task(registry, request, policy)
        request["agent"] = []
        with self.assertRaises(ConfigError):
            route_task(registry, request, policy)
        request["agent"] = "software-reviewer"
        request["profile"] = "FAST"
        with self.assertRaises(ConfigError):
            route_task(registry, request, policy)

    def test_requested_model_is_not_executed_model(self):
        registry, request, policy = inputs()
        result = route_task(registry, request, policy)
        model = result["decision"]["model_id"]
        self.assertEqual(reconcile_execution(model, None, False, [model]).status, "UNVERIFIED")
        self.assertEqual(reconcile_execution(model, "other", True, [model]).status, "BLOCKED")
        with self.assertRaises(ValueError):
            reconcile_execution(model, model, True, model + "-other")


if __name__ == "__main__":
    unittest.main()
