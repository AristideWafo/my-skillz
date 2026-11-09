# Model Router V0.1 — native adapter boundary

## Run a policy decision

The Python package uses only the standard library. In a trusted copy of this
repository, provide a model registry and policy for the actual environment:

```python
from pathlib import Path
from model_router import load_registry, route_task

registry = load_registry(Path("model_router/registry.json"))
request = {
    "agent": "backend-implementer",
    "environment": "codex",
    "privacy": "PUBLIC",
    "required_tools": ["shell"],
    "required_permissions": ["read"],
    "min_context_tokens": 100_000,
}
policy = {
    "allowed_providers": ["openai"],
    "allowed_environments": ["codex"],
    "allowed_privacy": ["PUBLIC"],
    "available_permissions": ["read"],
    "max_cost_usd": 1.0,
    "estimated_input_tokens": 100_000,
    "estimated_output_tokens": 10_000,
    "billing_basis": "API",
    "billing_verified": False,
}
result = route_task(registry, request, policy)
print(result["decision"]["status"])  # BLOCKED with the bundled UNKNOWN entries
```

The role's default profile is read from `model_router/agent_profiles.json`.
An explicit override must be allowed for that role. The selector returns all
candidate exclusion reasons, including unconfirmed availability, forbidden
provider, insufficient context, missing tools or permissions, privacy mismatch,
and budget. It never retries with a forbidden provider. An empty or invalid
policy fails before selection.

To use a model for real, an operator must verify account access and the
environment's effective capabilities, then set its registry availability to
`CONFIRMED` with current source and verification date. The bundled prices are
published API prices; they do not establish subscription cost, invoice amount,
latency, quality, or regional privacy guarantees. Treat the budget calculation
as an estimate for the documented pricing basis. Selection blocks when
`billing_verified` is false or the policy and model billing bases differ.
Mark it true only after independently verifying the applicable billing basis;
the token estimate still cannot guarantee a final invoice. If an enforceable
monetary ceiling is required but the applicable cost is unknown, leave the
model `UNKNOWN` or exclude it through policy. `CONFIDENTIAL` tasks need an
independently verified privacy classification. V0.1 always blocks
`LOCAL_ONLY`: neither native adapter verifies local processing or egress.

The five role profiles are task requirements. The default is `HIGH_REASONING`
for architect and reviewer and `BALANCED` for the three implementers. Explicit
escalation is limited to each role's `elevate_on` list. Profile membership in a
model registry is an operator judgment pending independent benchmark evidence;
V0.1 does not learn quality or latency scores.

## Apply or observe an adapter

The router chooses an approved model before an adapter is called. The adapter
does not decide eligibility. Invoke it only when the selection result is
`SELECTED`; never pass a model from a `BLOCKED` result to a host.

`model_router.adapters.prepare_adapter(environment, agent_name, model_id,
existing_text=None, mode="CONFIG_GENERATED")` returns a structured result.
`environment` is `codex` or `claude-code`. `CONFIG_GENERATED` returns the
single native model field and the repository-relative agent path for review.
It does **not** write it. `ADVISORY` returns a recommendation without a path
or snippet. Requesting `NATIVE` from this preparation function fails because
the module never launches an agent. If a target agent already has another
model, the result is `CONFLICT` and its existing configuration is preserved.

For Codex, review the proposed `model = "<id>"` in the matching agent's TOML.
For Claude Code, review `model: <id>` in that agent's YAML frontmatter. Add
only the relevant field after reviewing the complete file and account policy;
the generated snippet is intentionally not a whole agent definition. Codex
also supports a reasoning-effort field, but V0.1 leaves it inherited and does
not presume every model supports the same effort. Neither adapter sets or
overrides parent permissions, credentials, or provider access. Codex custom
agents inherit their parent session permissions. Claude Code can override an
agent's model at invocation, and organization allowlists may substitute it.

After a host invocation, call
`reconcile_execution(requested_model, executed_model, observation_verified,
approved_models)`. Supply an observed ID only from a trusted host mechanism;
do not derive it from the snippet. The result is `VERIFIED_NATIVE` only when
the observation was independently verified and the ID exactly matches the
approved request. An absent observation is `UNVERIFIED`. Any substitution,
including another approved model, is `BLOCKED` pending a new routing decision.
The result must not be used if the host chose a forbidden model. For Claude
Code, its task view reports the subagent's actual model on supported releases.

No adapter in V0.1 calls an API, discovers account entitlements, deploys a
config, or gathers private prompts. Local files under `.codex/agents` and
`.claude/agents` remain the source of truth. Integration tests use simulated
observations. Real host application and model availability require a later
bounded integration check.

Sources verified 2026-11-09:

- [Codex custom subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Claude Code subagents and model resolution](https://code.claude.com/docs/en/sub-agents)

## Architecture decisions and V0.2 boundary

1. The registry is versioned data and never authorizes a model by itself.
   `UNKNOWN` availability is excluded until account access is checked.
2. Provider, privacy, permission, tool, context, environment, profile, and
   budget filters run before ranking. There is no automatic cross-provider
   fallback. In V0.1, eligible candidates rank by documented estimated token
   cost; quality and latency comparisons need benchmark evidence.
3. Agent profiles encode requirements, not model IDs. The five existing agent
   files point to the shared mapping; no role was replaced or given a fixed
   model. A task can use only its role's default or allowed elevation.
4. Adapter preparation is pure and cannot claim `NATIVE`. Native execution is
   recognized only after independently observed model identity is reconciled.
5. `LOCAL_ONLY` always blocks until an adapter can prove local processing and
   the policy can verify the endpoint and egress boundary.

Independent review found and prompted corrections for local privacy inference,
caller-controlled role profiles, unverifiable billing basis, and substring
membership in approved model IDs. Regression tests now cover these cases.

V0.2 candidates: verified account availability refresh with expiry; a trusted
local-processing adapter; measured quality and latency ranking; cost tracking
from actual billing data; a bounded host integration test for executed-model
identity; and policy-controlled escalation after failed evaluations. Each needs
its own authorization and evidence before becoming an automatic route.
