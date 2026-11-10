# my-skillz

Portable skills, specialized development agents, and deterministic hooks for Claude and Codex.

## Model Router V0.1

The portable, standard-library router in [model_router/](model_router/) assigns
requirements to the five existing agents, filters models through hard policy
constraints, and prepares a Codex or Claude Code model field for review. Its
bundled catalog marks account availability `UNKNOWN`; confirm a model, its
permissions, billing basis, and data handling before enabling it. No global
configuration or user project is changed by a routing decision.

The installer turns each role's default profile into a native Codex
`model_reasoning_effort` (`HIGH_REASONING`/`SECURITY_CRITICAL` → `high`,
`BALANCED` → `medium`, `FAST` → `low`; `LONG_CONTEXT` stays inherited), so the
reviewer reasons deeply and implementers stay economical; `solution-architect` pins
`medium` in its TOML to bound exploration. A value
already pinned in an agent TOML is kept. Agents no longer read the router guide on
every run; they consult it only when asked to select a model.

See [the Model Router guide](docs/model-router-v01.md) for an example request,
policy, adapter modes, limits, and the verification boundary. Run its simulated
tests with `python3 -m unittest discover -s tests -p 'test_model_router_*.py'`
(`py -3` on Windows).

Each skill uses a shared portable core:

```text
skill-name/
├── SKILL.md              # Claude and Codex instructions
├── references/           # Loaded only when the task needs them
└── agents/openai.yaml    # Optional Codex UI metadata; ignored by Claude
```

## Skills

| Skill | Use for | Route elsewhere when |
|---|---|---|
| `frontend-application-builder` | Browser-facing features, accessibility, responsive UI, frontend tests | The primary work is backend behavior or system architecture |
| `backend-service-builder` | APIs, services, jobs, authorization, persistence, migrations | The primary work is frontend presentation or architecture exploration |
| `ansible-project-builder` | Ansible playbooks, roles, inventories, variables, tests | The task is wider delivery-system design |
| `cicd-pipeline-builder` | CI/CD workflows, releases, promotion, deployment strategy | The change is inside a Docker image or Ansible artifact |
| `docker-builder` | Dockerfiles, images, build contexts, Compose | The task is the wider delivery pipeline |
| `grafana-dashboard-builder` | Grafana dashboards, panels, variables, queries | The task is cross-system observability or incident diagnosis |
| `sre-observability-expert` | Incidents, reliability, performance, SLI/SLO, observability design | A concrete artifact has a specialized skill |
| `doc-coauthoring` | Technical documents, RFCs, proposals, decision records | The request is a trivial one-paragraph edit |

## Agents

Five equivalent project-scoped agents are provided in Claude and Codex formats:

| Agent | Responsibility | Default boundary |
|---|---|---|
| `frontend-implementer` | Implement bounded browser-facing work | Frontend files and contracts |
| `backend-implementer` | Implement bounded server-side work | Backend files, data, and APIs |
| `platform-release-engineer` | Delivery, containers, infrastructure, deployment, observability | Route through the relevant DevOps skill |
| `software-reviewer` | Independent correctness, security, and test review | Read-only |
| `solution-architect` | Cross-boundary contracts and architecture decisions | Read-only |

Claude discovers `.claude/agents/*.md`. Codex discovers `.codex/agents/*.toml`. Agent descriptions are intentionally narrow so small tasks stay with the primary agent and parallel agents do not edit overlapping files; Claude descriptions also say when to use each agent proactively.

To keep token use low, every agent returns a handoff of at most 15 lines (files changed, decisions, validation run, open risks) instead of code dumps, and `software-reviewer` reviews only the diff and the call paths it touches. Each subagent starts with its own context, so delegation is reserved for substantial work.

### Manager mode

[manager/AGENTS.md](manager/AGENTS.md) makes the primary agent the manager. Because each subagent starts a new context and costs about as much as a new session, it does the work itself by default and delegates only when:

| Trigger | Delegation |
|---|---|
| User explicitly asks for agents, a review, or an architecture decision | As asked |
| Cross-boundary change with an undecided contract | `solution-architect` first, then the primary agent implements |
| Auth, authorization, secrets, payments, or data migrations | One `software-reviewer` pass at the end, on the diff |

Hard limits: at most 2 subagents per request in total, strictly one after the other, the architect never in parallel with implementation, and the reviewer at most once. Briefs are at most 10 lines. To enforce one agent at a time in Codex itself, not only through instructions, add to `~/.codex/config.toml`:

```toml
[agents]
max_threads = 1   # one open subagent at a time
max_depth = 1     # subagents cannot spawn agents
```

The installer never edits `config.toml`; add these lines by hand. Spawned subagents ignore these rules and never spawn agents. Every agent stays inside the files named in its brief, aims to finish within about 20 tool calls, and returns a handoff of at most 15 lines; the architect's decision is at most 30 lines.

## Hooks

Claude and Codex both run the same dependency-free Python handlers:

- `SessionStart`: injects a small stack, branch, and routing snapshot without reading secrets;
- `PreToolUse`: blocks a narrow set of catastrophic local deletion, Git, Docker, formatting, and raw-device commands;
- `PostToolUse`: reports syntax errors after direct edits to JSON, TOML, Python, or Markdown.

The platform adapters are `.claude/settings.json` and `.codex/hooks.json`. Hooks do not auto-deploy, auto-approve, or replace normal sandbox and permission controls. Both platforms require project trust before local hooks run.

## Design conventions

- Inspect the project before introducing a new convention.
- Preserve coherent project architecture unless a concrete defect justifies migration.
- Keep discovery descriptions short and discriminating.
- Put decision logic and safety boundaries in `SKILL.md`; put conditional detail in `references/`.
- Use absolute language only for genuine security, data-integrity, authorization, or workflow invariants.
- Verify version-sensitive guidance from primary documentation when making a material change.
- Define completion through checks proportional to the task and report anything not verified.
- Keep product-specific metadata outside the portable `SKILL.md` body.

## Validation

Run the dependency-free repository validator:

```bash
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests -p "test_*.py"
python3 -m unittest discover -s tools/claude-usage-monitor/tests
```

It checks folder/frontmatter compatibility, required files, reference links, unfinished placeholders, fence balance, portable entrypoints, and unsafe mutable action examples.

Skill regression cases are in [tests/behavioral-scenarios.md](tests/behavioral-scenarios.md), and delegation cases are in [tests/agent-scenarios.md](tests/agent-scenarios.md). They evaluate behavior and boundaries, not wording snapshots.

Deeper failure-mode fixtures cover
[application behavior](tests/app-skill-scenarios.md),
[delivery and recovery](tests/delivery-skill-scenarios.md), and
[operations and document evidence](tests/ops-docs-skill-scenarios.md).
These are agent evaluation cases, not executable unit tests. Record the actual
response and checks performed when running them; structural validation does not
prove model behavior or live platform compatibility.

## Installing or using

For a personal installation from this checkout, preview first, then apply:

```bash
python3 scripts/install_local.py
python3 scripts/install_local.py --apply
```

On Windows, use `py -3` instead of `python3`. Choose `--target codex` or
`--target claude` to install only one adapter; the default installs both.
The installer copies complete skills to `~/.agents/skills` (Codex) and
`~/.claude/skills` (Claude), plus the five agents to each product's user agents
directory. It installs the document skill as `my-skillz-doc-coauthoring` to avoid
colliding with a synced `doc-coauthoring`, and adjusts installed agent references.
Agents receive exact local entrypoint paths and load only relevant references.

For Codex, the installer also writes `manager/AGENTS.md` to `~/.codex/AGENTS.md`.
It makes the primary agent act as a manager in every repository: it works alone by
default and delegates on its own only under the triggers and limits of
[Manager mode](#manager-mode). Spawned subagents ignore these rules and never spawn further agents. An
existing unmanaged `~/.codex/AGENTS.md` stops the installation; merge it by hand.
Claude Code picks subagents from their descriptions, which say when to use them
proactively, so `~/.claude/CLAUDE.md` is never touched.

Installation is preview-only unless `--apply` is supplied. An inventory with
SHA-256 hashes lives in `~/.my-skillz/manifest.json`; updates back up managed files
under `~/.my-skillz/backups`. Unmanaged conflicts and locally modified files stop
the installation before any planned write. No hooks or global permissions are
installed or changed. Removed upstream files are not automatically deleted.
Open a fresh session after the first installation to load the new agents.
The installer also places the Model Router Python package and five-role profile
map under `~/.my-skillz/model_router/`, its guide under `~/.my-skillz/`, and
points installed agents to those paths. To import it outside this checkout,
add `~/.my-skillz` to Python's module search path. The installer does not
activate automatic model switching or install a background service.

Codex custom agents inherit the parent session's sandbox and approval settings;
the reviewer and architect's no-edit instructions are behavioral constraints,
not separate permission sandboxes. For an enforced read-only review, select
read-only permissions on the parent session. See the official
[Codex agent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[Codex skill locations](https://learn.chatgpt.com/docs/build-skills), and
[Claude agent documentation](https://code.claude.com/docs/en/sub-agents).

Copy or link the desired skill directories into the skill location supported by the current Claude or Codex installation. Keep each directory intact so `SKILL.md`, references, and optional metadata remain together.

Claude and Codex both discover skills from the `name` and `description` frontmatter and load the body and references on demand. `agents/openai.yaml` improves Codex presentation but is not required by the portable workflow.

For project-scoped use, copy the relevant `.claude/agents`, `.codex/agents`, `hooks`, and hook configuration into the target repository, then review and trust the hook definitions in each product. Merge settings into existing configuration rather than overwriting unrelated hooks or permissions. For personal use across every repository, install the agent files in `~/.claude/agents/` and `~/.codex/agents/`; use absolute paths for globally configured hook scripts.

## Maintenance

When changing a skill:

1. reproduce the decision failure or add a realistic scenario;
2. make the narrowest instruction or reference change that fixes it;
3. run `python3 scripts/validate_skills.py`;
4. review cross-skill routing and version-sensitive claims;
5. avoid adding generic explanations the agent already knows.

The latest repository-wide audit is documented in [docs/quality-audit-2026-08-31.md](docs/quality-audit-2026-08-31.md).

## License

MIT. See [LICENSE](LICENSE).
