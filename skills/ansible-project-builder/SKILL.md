---
name: ansible-project-builder
description: Design, review, or refactor Ansible playbooks, roles, inventories, variables, tests, and Ansible-specific delivery workflows. Use for concrete Ansible artifacts; use the CI/CD skill for platform-wide delivery design.
---

# Ansible Project Builder

Produce the smallest safe Ansible change that fits the repository's existing architecture. Prefer evidence from the project over this skill's defaults.

## Workflow

1. Inspect `ansible.cfg`, collection and role requirements, inventories, playbooks, roles, lint configuration, and tests relevant to the request. Do not read unrelated roles by default.
2. Determine the execution model, supported environments and hosts, Ansible/collection versions, secret source, and operational risk from repository evidence. Ask only for material unknowns that cannot be discovered.
3. Classify the task as read, plan, change, or destructive change. For production, credential, inventory-wide, or irreversible work, state the blast radius and recovery path before acting.
4. Preserve coherent project conventions. Introduce a new layout, collection, plugin, or dependency only when the existing approach causes a concrete correctness, security, or maintenance problem.
5. Implement the narrowest change and validate it in proportion to risk.

## Decision rules

- Prefer idempotent modules. Use `command` or `shell` only when no suitable module exists; define accurate change and failure conditions.
- Use fully qualified collection names in new or modernized content unless the repository deliberately supports an older Ansible version.
- Keep public role inputs in `defaults`; reserve role `vars` for values callers should not override. Prefix role-owned variables when collisions are plausible.
- Keep environment-specific variables beside their inventory when strict environment isolation is required. Playbook-relative `group_vars` and `host_vars` are valid when intentional and documented.
- Keep secrets out of plaintext repositories and logs. Reuse the project's secret manager or vault convention; do not invent a new secret backend without need.
- Validate configuration before any reload or restart. Do not rely on handler ordering to make an unsafe configuration safe.
- Treat a zero-change second run as the default idempotence test. Document intentional non-idempotent operations instead of hiding them.
- Tune forks, fact gathering, caching, serial batches, and strategy from measurements and target constraints rather than fixed universal values.

## Read references selectively

- Role boundaries and validation: [references/roles.md](references/roles.md)
- Variable placement and precedence: [references/variables.md](references/variables.md)
- Idempotence failures: [references/idempotence.md](references/idempotence.md)
- Secrets and privilege boundaries: [references/security.md](references/security.md)
- Large inventories and performance: [references/performance.md](references/performance.md)
- Molecule and Ansible-specific CI: [references/cicd.md](references/cicd.md)
- Pull-mode architecture: [references/ansible-pull.md](references/ansible-pull.md)
- Review heuristics: [references/anti-patterns.md](references/anti-patterns.md)

## Validation and done

Use the checks supported by the repository. A material change is done when:

- YAML and inventory parse successfully;
- `ansible-playbook --syntax-check` passes for affected playbooks;
- configured lint rules pass, or exceptions are documented;
- check mode and diff are reviewed when the modules support them;
- affected Molecule or integration scenarios pass when available;
- a safe second run reports no unexpected changes;
- secrets are absent from diffs and logs;
- rollout and rollback are explicit for production-impacting changes.

Report assumptions, skipped checks, residual risk, and the exact files changed.
