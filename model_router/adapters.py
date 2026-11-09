"""Pure, fail-closed preparation for Codex and Claude Code agent model settings.

No function in this module edits a file, launches an agent, or changes a model.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Collection, Optional

MODES = frozenset({"NATIVE", "CONFIG_GENERATED", "ADVISORY"})
ENVIRONMENTS = frozenset({"codex", "claude-code"})
AGENT_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}$")


@dataclass(frozen=True)
class AdapterResult:
    mode: str
    environment: str
    agent_name: str
    requested_model: str
    target: Optional[str]
    snippet: Optional[str]
    status: str
    reason: str


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    requested_model: str
    executed_model: Optional[str]
    reason: str


def prepare_adapter(
    environment: str,
    agent_name: str,
    model_id: str,
    existing_text: Optional[str] = None,
    mode: str = "CONFIG_GENERATED",
) -> AdapterResult:
    """Produce a reviewable native field snippet, never an applied configuration.

    ``NATIVE`` is not available as a preparation result: a verified invocation
    must be reconciled separately. All fields are checked before interpolation.
    """
    if environment not in ENVIRONMENTS:
        raise ValueError("Unsupported execution environment")
    if mode not in MODES:
        raise ValueError("Unsupported adapter mode")
    if not AGENT_RE.fullmatch(agent_name) or not MODEL_RE.fullmatch(model_id):
        raise ValueError("Invalid agent name or model identifier")
    if existing_text is not None and not isinstance(existing_text, str):
        raise ValueError("existing_text must be text")
    if mode == "NATIVE":
        raise ValueError("NATIVE requires a verified execution observation")

    if mode == "ADVISORY":
        return AdapterResult(mode, environment, agent_name, model_id, None, None,
                             "RECOMMENDED", "Recommendation only; no configuration produced")

    if environment == "codex":
        target = f".codex/agents/{agent_name}.toml"
        pattern = re.compile(r'^\s*model\s*=\s*(.+?)\s*$', re.MULTILINE)
        snippet = f'model = "{model_id}"'
    else:
        target = f".claude/agents/{agent_name}.md"
        pattern = re.compile(r'^\s*model\s*:\s*(.+?)\s*$', re.MULTILINE)
        snippet = f"model: {model_id}"
        if existing_text is not None:
            if not existing_text.startswith("---\n") or "\n---" not in existing_text[4:]:
                raise ValueError("Claude agent lacks recognizable YAML frontmatter")
            existing_text = existing_text[4:].split("\n---", 1)[0]

    if existing_text is not None:
        matches = pattern.findall(existing_text)
        if len(matches) > 1:
            raise ValueError("Existing agent has multiple model fields")
        if matches:
            existing = matches[0].strip().strip('"\'')
            if existing != model_id:
                return AdapterResult(mode, environment, agent_name, model_id, target,
                                     snippet, "CONFLICT",
                                     f"Existing model {existing!r} requires explicit review")
            return AdapterResult(mode, environment, agent_name, model_id, target,
                                 snippet, "ALREADY_CONFIGURED", "Matching field found; execution unverified")

    return AdapterResult(mode, environment, agent_name, model_id, target, snippet,
                         "READY_FOR_REVIEW", "Snippet generated; not applied or executed")


def reconcile_execution(
    requested_model: str,
    executed_model: Optional[str],
    observation_verified: bool,
    approved_models: Collection[str],
) -> ExecutionResult:
    """Classify observed native execution; never infer it from a generated snippet.

    The caller must independently obtain and verify ``executed_model`` from
    the host. Both requested and observed IDs must be explicitly approved.
    """
    if not MODEL_RE.fullmatch(requested_model):
        raise ValueError("Invalid requested model")
    if isinstance(approved_models, (str, bytes)) or not isinstance(approved_models, Collection) or any(
        not isinstance(item, str) or not MODEL_RE.fullmatch(item) for item in approved_models
    ):
        raise ValueError("approved_models must be a collection of exact model identifiers")
    if requested_model not in approved_models:
        return ExecutionResult("BLOCKED", requested_model, executed_model,
                               "Requested model is not approved")
    if not observation_verified or not executed_model:
        return ExecutionResult("UNVERIFIED", requested_model, executed_model,
                               "No independently verified execution identity")
    if not MODEL_RE.fullmatch(executed_model):
        raise ValueError("Invalid observed model")
    if executed_model not in approved_models:
        return ExecutionResult("BLOCKED", requested_model, executed_model,
                               "Executed model is not approved; stop before using its result")
    if executed_model != requested_model:
        return ExecutionResult("BLOCKED", requested_model, executed_model,
                               "Host substituted a different model; re-authorize the route")
    return ExecutionResult("VERIFIED_NATIVE", requested_model, executed_model,
                           "Requested model matches independently verified execution")
