"""Model selection with hard policy exclusions and no network side effects."""

from __future__ import annotations

import json
import math
from pathlib import Path


PROFILES = {"FAST", "BALANCED", "HIGH_REASONING", "SECURITY_CRITICAL", "LONG_CONTEXT"}
PRIVACY = {"PUBLIC": 0, "INTERNAL": 1, "CONFIDENTIAL": 2, "LOCAL_ONLY": 3}
MODEL_KEYS = {"id", "provider", "availability", "environments", "privacy", "tools", "context_tokens", "permissions", "profiles", "input_usd_per_million", "output_usd_per_million", "billing_basis", "source", "verified_at"}
REQUEST_KEYS = {"agent", "profile", "required_tools", "min_context_tokens", "privacy", "required_permissions", "environment"}
POLICY_KEYS = {"allowed_providers", "allowed_environments", "allowed_privacy", "available_permissions", "max_cost_usd", "estimated_input_tokens", "estimated_output_tokens", "billing_basis", "billing_verified"}


class ConfigError(ValueError):
    """Raised for malformed registry, request or policy; never silently default it."""


def _keys(value, required, allowed, label):
    if not isinstance(value, dict):
        raise ConfigError(f"{label} must be an object")
    missing, extra = required - value.keys(), value.keys() - allowed
    if missing or extra:
        raise ConfigError(f"{label} keys invalid: missing={sorted(missing)}, extra={sorted(extra)}")


def _string(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{label} must be a nonempty string")


def _strings(value, label):
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value) or len(value) != len(set(value)):
        raise ConfigError(f"{label} must be a list of unique strings")


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ConfigError(f"{label} must be a finite nonnegative number")


def validate_registry(registry: dict) -> dict:
    _keys(registry, {"schema_version", "models"}, {"schema_version", "models"}, "registry")
    if type(registry["schema_version"]) is not int or registry["schema_version"] != 1:
        raise ConfigError("unsupported registry schema_version")
    if not isinstance(registry["models"], list):
        raise ConfigError("models must be a list")
    seen = set()
    for index, model in enumerate(registry["models"]):
        label = f"models[{index}]"
        _keys(model, MODEL_KEYS, MODEL_KEYS, label)
        for key in ("id", "provider", "source", "verified_at"):
            _string(model[key], f"{label}.{key}")
        if model["billing_basis"] not in ("API", "SUBSCRIPTION", "SIMULATED"):
            raise ConfigError(f"{label}.billing_basis invalid")
        if model["id"] in seen:
            raise ConfigError(f"duplicate model id: {model['id']}")
        seen.add(model["id"])
        if model["availability"] not in ("CONFIRMED", "UNKNOWN", "UNAVAILABLE"):
            raise ConfigError(f"{label}.availability invalid")
        if model["privacy"] not in PRIVACY:
            raise ConfigError(f"{label}.privacy invalid")
        for key in ("environments", "tools", "permissions", "profiles"):
            _strings(model[key], f"{label}.{key}")
        if not model["environments"] or not model["profiles"] or not set(model["profiles"]) <= PROFILES:
            raise ConfigError(f"{label} environments/profiles invalid")
        for key in ("context_tokens", "input_usd_per_million", "output_usd_per_million"):
            _number(model[key], f"{label}.{key}")
        if type(model["context_tokens"]) is not int or model["context_tokens"] <= 0:
            raise ConfigError(f"{label}.context_tokens must be positive integer")
    return registry


def load_registry(path: str | Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot load registry: {exc}") from exc
    return validate_registry(data)


def profile_task(agent: str, *, complexity: str = "standard", security_critical: bool = False, long_context: bool = False) -> str:
    _string(agent, "agent")
    if complexity not in ("simple", "standard", "complex") or type(security_critical) is not bool or type(long_context) is not bool:
        raise ConfigError("invalid task classification")
    if security_critical:
        return "SECURITY_CRITICAL"
    if long_context:
        return "LONG_CONTEXT"
    if complexity == "complex" or agent in ("solution-architect", "software-reviewer") and complexity != "simple":
        return "HIGH_REASONING"
    return "FAST" if complexity == "simple" else "BALANCED"


def _request(value):
    _keys(value, {"agent", "profile", "required_tools", "min_context_tokens", "privacy", "required_permissions", "environment"}, REQUEST_KEYS, "request")
    for key in ("agent", "environment"):
        _string(value[key], f"request.{key}")
    if value["profile"] not in PROFILES or value["privacy"] not in PRIVACY:
        raise ConfigError("invalid request profile/privacy")
    for key in ("required_tools", "required_permissions"):
        _strings(value[key], f"request.{key}")
    _number(value["min_context_tokens"], "request.min_context_tokens")
    if type(value["min_context_tokens"]) is not int:
        raise ConfigError("request.min_context_tokens must be integer")


def _policy(value):
    _keys(value, POLICY_KEYS, POLICY_KEYS, "policy")
    for key in ("allowed_providers", "allowed_environments", "allowed_privacy", "available_permissions"):
        _strings(value[key], f"policy.{key}")
    if not set(value["allowed_privacy"]) <= PRIVACY.keys():
        raise ConfigError("policy.allowed_privacy invalid")
    for key in ("max_cost_usd", "estimated_input_tokens", "estimated_output_tokens"):
        _number(value[key], f"policy.{key}")
    for key in ("estimated_input_tokens", "estimated_output_tokens"):
        if type(value[key]) is not int:
            raise ConfigError(f"policy.{key} must be integer")
    if value["billing_basis"] not in ("API", "SUBSCRIPTION", "SIMULATED") or type(value["billing_verified"]) is not bool:
        raise ConfigError("policy billing configuration invalid")


def select_model(registry: dict, request: dict, policy: dict) -> dict:
    validate_registry(registry)
    _request(request)
    _policy(policy)
    excluded, candidates = {}, []
    privacy = request["privacy"]
    for model in registry["models"]:
        reasons = []
        if model["availability"] != "CONFIRMED":
            reasons.append("availability not confirmed")
        if model["provider"] not in policy["allowed_providers"]:
            reasons.append("provider not allowed")
        if request["environment"] not in policy["allowed_environments"] or request["environment"] not in model["environments"]:
            reasons.append("environment incompatible")
        if privacy not in policy["allowed_privacy"] or PRIVACY[model["privacy"]] < PRIVACY[privacy]:
            reasons.append("privacy requirement unmet")
        if privacy == "LOCAL_ONLY":
            reasons.append("local execution not verified by V0.1 adapters")
        if not set(request["required_tools"]) <= set(model["tools"]):
            reasons.append("required tools unavailable")
        if not set(request["required_permissions"]) <= set(model["permissions"]) or not set(request["required_permissions"]) <= set(policy["available_permissions"]):
            reasons.append("required permissions unavailable")
        if model["context_tokens"] < request["min_context_tokens"]:
            reasons.append("context too small")
        if request["profile"] not in model["profiles"]:
            reasons.append("profile unsupported")
        estimated = (model["input_usd_per_million"] * policy["estimated_input_tokens"] + model["output_usd_per_million"] * policy["estimated_output_tokens"]) / 1_000_000
        if model["billing_basis"] != policy["billing_basis"] or not policy["billing_verified"]:
            reasons.append("billing basis unverified or incompatible")
        if estimated > policy["max_cost_usd"]:
            reasons.append("budget exceeded")
        if reasons:
            excluded[model["id"]] = reasons
        else:
            candidates.append((estimated, model["id"]))
    if not candidates:
        return {"status": "BLOCKED", "model_id": None, "profile": request["profile"], "reasons": ["no compatible authorized model"], "excluded": excluded}
    _, chosen = min(candidates)
    return {"status": "SELECTED", "model_id": chosen, "profile": request["profile"], "reasons": ["all mandatory constraints satisfied", "lowest documented estimated cost among eligible candidates; quality not benchmarked"], "excluded": excluded}
