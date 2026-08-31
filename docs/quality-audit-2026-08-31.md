# Repository quality audit — 2026-08-31

## Initial health

- Skills announced: 6
- Valid portable `SKILL.md` entrypoints: 0
- Main blockers: angle-bracket placeholders in five descriptions; missing `SKILL.md` for `doc-coauthoring`
- Highest-risk defects: unsafe Ansible handler ordering, mutable CI actions, stale DORA model and invalid MTTR query, Docker tag/reproducibility confusion, root-cause-before-mitigation incident flow
- Systemic issues: overlapping triggers, project-specific identity, excessive absolutes, large entrypoints, version drift, and no regression suite

## Initial quality scores

| Skill | Scope | Trigger | Decisions | Reuse | Context | Validation | Safety | Maintainability |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ansible-project-builder | 7 | 6 | 5 | 5 | 4 | 7 | 5 | 4 |
| cicd-pipeline-builder | 7 | 6 | 4 | 5 | 3 | 5 | 3 | 3 |
| docker-builder | 7 | 7 | 5 | 6 | 5 | 6 | 5 | 4 |
| grafana-dashboard-builder | 8 | 8 | 7 | 7 | 8 | 6 | 7 | 7 |
| sre-observability-expert | 5 | 4 | 6 | 7 | 8 | 6 | 6 | 7 |
| doc-coauthoring | 7 | 7 | 4 | 3 | 2 | 6 | 6 | 3 |

Scores are diagnostic rather than scientific. The pre-refactor overall assessment was 5.5/10: useful content, insufficient operational reliability.

## Classification and disposition

### ansible-project-builder

- PROJECT-SPECIFIC: employer/user profile and one prescribed repository layout — removed.
- DETERMINISTIC: syntax, lint, Molecule, idempotence — retained as proportional validation and CI candidates.
- REDUNDANT: long tutorials and repeated anti-pattern lists — compressed into focused references.
- TOO ABSOLUTE: inventory placement, fixed forks, disabled facts, handler conventions — replaced with decision criteria.
- MISSING: risk classification and safe handler validation — added.

### cicd-pipeline-builder

- PROJECT-SPECIFIC: assumed platforms, registries, branches, and deployment targets — removed from the portable core.
- DETERMINISTIC: workflow parsing, immutable revision checks, permissions review — encoded in validation guidance.
- REDUNDANT: large copy-ready platform templates — replaced with platform-neutral delivery graphs.
- TOO ABSOLUTE: every gate blocks, trunk-only, universal strategy choices — made risk-based.
- MISSING: untrusted-PR boundary, action pinning, timeouts, concurrency, production authorization — added.

### docker-builder

- PROJECT-SPECIFIC: fixed runtime versions and preferred images — removed.
- DETERMINISTIC: build, merged Compose config, UID/history/scan checks — retained as completion checks.
- REDUNDANT: extensive syntax examples — reduced.
- TOO ABSOLUTE: Alpine, multi-stage, healthcheck, no production Compose — replaced with tradeoffs.
- MISSING: digest/update balance and orchestrator probe distinction — added.

### grafana-dashboard-builder

- PROJECT-SPECIFIC: user placeholder and language rule — removed.
- DETERMINISTIC: JSON, datasource, query, empty-state validation — added.
- REDUNDANT: minimal.
- TOO ABSOLUTE: ten-panel cap and SLO-only value test — converted to a cognitive-load and decision test.
- MISSING: version, datasource, owner, cardinality, and missing-data checks — added.

### sre-observability-expert

- PROJECT-SPECIFIC: preferred cloud and user profile — removed.
- DETERMINISTIC: bounded diagnostics and end-to-end signal checks — kept in references.
- REDUNDANT: domain primers — shortened.
- TOO ABSOLUTE: fixed eight-step method and native-first default — made mode- and evidence-dependent.
- MISSING: mitigation-first incident mode, authorization boundary, known/inferred/unknown distinction — added.

### doc-coauthoring

- PROJECT-SPECIFIC: Claude.ai, Claude Code, and named tool calls — removed.
- DETERMINISTIC: placeholders, links, formatting, reader questions — kept as completion checks.
- REDUNDANT: repeated five-to-twenty item cycles — deleted.
- TOO ABSOLUTE: forced three-stage ceremony — replaced with three collaboration modes.
- MISSING: a valid `SKILL.md` and portable tool behavior — added.

## Repository decisions

- KEEP: all six capabilities; each has a distinct useful purpose after routing cleanup.
- MERGE: none. Docker, delivery, Ansible, Grafana, SRE, and document work have different decision boundaries.
- SPLIT: none. Conditional detail moved to references instead.
- DELETE: product-specific legacy `doc-coauthoring.md` and obsolete copy-ready reference catalogs.
- ADD: Codex UI metadata, a dependency-free validator, CI validation, behavioral regression scenarios, and this audit record.
- NEW SKILLS: none. The current scope did not demonstrate a missing capability worth another automatic trigger.

## Final repository health target

The refactor is complete when all six skills pass structural validation, no portable entrypoint assumes Claude- or Codex-specific tools, references resolve, mutable action branches are absent from executable examples, each skill has behavioral scenarios, and the repository validator passes locally and in CI.
