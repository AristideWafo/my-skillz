"""Join the five agent profiles, policy decision, and native adapter preparation."""
from __future__ import annotations

import json
from pathlib import Path

from .adapters import prepare_adapter
from .core import ConfigError, PROFILES, select_model

PROFILE_PATH = Path(__file__).with_name("agent_profiles.json")


def load_agent_profiles(path: str | Path = PROFILE_PATH) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot load agent profiles: {exc}") from exc
    if not isinstance(data, dict) or set(data) != {"schema_version", "agents"} or type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ConfigError("invalid agent profile schema")
    agents = data["agents"]
    if not isinstance(agents, dict) or not agents:
        raise ConfigError("agent profiles must be a nonempty object")
    for name, mapping in agents.items():
        if not isinstance(name, str) or not name or not isinstance(mapping, dict) or set(mapping) != {"default", "elevate_on"}:
            raise ConfigError("invalid agent profile mapping")
        if not isinstance(mapping["default"], str) or mapping["default"] not in PROFILES or not isinstance(mapping["elevate_on"], list) or any(not isinstance(item, str) or item not in PROFILES for item in mapping["elevate_on"]):
            raise ConfigError(f"invalid profiles for {name}")
    return agents


def route_task(registry: dict, request: dict, policy: dict, *, mode: str = "CONFIG_GENERATED", existing_text: str | None = None) -> dict:
    """Return a policy decision and optional reviewable adapter result; never execute."""
    if not isinstance(request, dict):
        raise ConfigError("request must be an object")
    profiles = load_agent_profiles()
    agent = request.get("agent")
    if not isinstance(agent, str) or not agent:
        raise ConfigError("request.agent must be a nonempty string")
    if agent not in profiles:
        raise ConfigError("unknown agent role")
    mapping = profiles[agent]
    chosen_profile = request.get("profile", mapping["default"])
    if chosen_profile != mapping["default"] and chosen_profile not in mapping["elevate_on"]:
        raise ConfigError("profile override not allowed for agent")
    full_request = {**request, "profile": chosen_profile}
    decision = select_model(registry, full_request, policy)
    if decision["status"] != "SELECTED":
        return {"decision": decision, "adapter": None}
    try:
        adapter = prepare_adapter(full_request["environment"], agent, decision["model_id"], existing_text, mode)
    except ValueError as exc:
        raise ConfigError(f"adapter preparation failed: {exc}") from exc
    return {"decision": decision, "adapter": adapter}
