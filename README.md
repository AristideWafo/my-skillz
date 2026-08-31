# my-skillz

Portable agent skills for Claude and Codex, focused on DevOps, delivery, containers, observability, Ansible, Grafana, and technical writing.

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
| `ansible-project-builder` | Ansible playbooks, roles, inventories, variables, tests | The task is wider delivery-system design |
| `cicd-pipeline-builder` | CI/CD workflows, releases, promotion, deployment strategy | The change is inside a Docker image or Ansible artifact |
| `docker-builder` | Dockerfiles, images, build contexts, Compose | The task is the wider delivery pipeline |
| `grafana-dashboard-builder` | Grafana dashboards, panels, variables, queries | The task is cross-system observability or incident diagnosis |
| `sre-observability-expert` | Incidents, reliability, performance, SLI/SLO, observability design | A concrete artifact has a specialized skill |
| `doc-coauthoring` | Technical documents, RFCs, proposals, decision records | The request is a trivial one-paragraph edit |

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
```

It checks folder/frontmatter compatibility, required files, reference links, unfinished placeholders, fence balance, portable entrypoints, and unsafe mutable action examples.

Behavioral regression cases are in [tests/behavioral-scenarios.md](tests/behavioral-scenarios.md). They are review scenarios, not wording snapshots.

## Installing or using

Copy or link the desired skill directories into the skill location supported by the current Claude or Codex installation. Keep each directory intact so `SKILL.md`, references, and optional metadata remain together.

Claude and Codex both discover skills from the `name` and `description` frontmatter and load the body and references on demand. `agents/openai.yaml` improves Codex presentation but is not required by the portable workflow.

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
