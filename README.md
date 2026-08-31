# my-skillz

Portable skills, specialized development agents, and deterministic hooks for Claude and Codex.

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

Claude discovers `.claude/agents/*.md`. Codex discovers `.codex/agents/*.toml`. Agent descriptions are intentionally narrow so small tasks stay with the primary agent and parallel agents do not edit overlapping files.

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
python3 -m unittest tests/test_hooks.py
```

It checks folder/frontmatter compatibility, required files, reference links, unfinished placeholders, fence balance, portable entrypoints, and unsafe mutable action examples.

Skill regression cases are in [tests/behavioral-scenarios.md](tests/behavioral-scenarios.md), and delegation cases are in [tests/agent-scenarios.md](tests/agent-scenarios.md). They evaluate behavior and boundaries, not wording snapshots.

## Installing or using

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
