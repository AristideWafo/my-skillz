---
name: cicd-pipeline-builder
description: Design, review, or improve CI/CD workflows, release processes, artifact promotion, deployment strategies, and delivery security. Use for repository delivery systems; route container-image internals to the Docker skill and Ansible content to the Ansible skill.
---

# CI/CD Pipeline Builder

Improve the existing delivery path without changing platforms or architecture unless evidence shows that the current design cannot meet the requirement.

## Workflow

1. Inspect existing workflows, reusable jobs, branch and release conventions, build files, deployment manifests, environments, and repository protection settings.
2. Trace one change from commit to production: what is built, tested, published, approved, deployed, observed, and rolled back.
3. Identify constraints that materially affect design: artifact type, deployment target, backwards compatibility, data migrations, compliance, availability objective, and team ownership.
4. Classify the requested work as read, plan, change, or production/destructive change. Do not trigger a production deployment, rollback, release, credential rotation, or environment mutation without explicit authorization.
5. Choose the smallest design that closes the observed gap, implement it using existing conventions, and validate the workflow plus the deployed outcome when in scope.

## Decision rules

- Build once and promote the same immutable artifact when the platform supports artifact promotion. Keep runtime configuration outside the artifact.
- Preserve an existing CI/CD platform and reusable workflow architecture when it is coherent. A tool migration requires a demonstrated benefit and migration plan.
- Pin third-party actions and reusable workflows to reviewed immutable revisions. Verify current versions and security advisories from primary sources before adding or updating them.
- Grant each job the minimum token and cloud permissions it needs. Prefer workload identity or OIDC over long-lived credentials.
- Treat untrusted pull-request content as hostile. Do not expose secrets or privileged runners to it.
- Make gates proportional to risk. A blocker needs a reliable signal, an owner, and an exception process; informational findings should not masquerade as hard gates.
- Select rolling, blue-green, canary, or feature-flag delivery from compatibility, rollback speed, traffic control, cost, and observability—not from a universal preference.
- Design database and contract changes for mixed-version operation when rollout is progressive.
- Add timeouts, concurrency controls, cancellation behavior, and explicit rollback criteria to deployment jobs.
- Measure delivery performance from timestamped deployment and incident events. Do not optimize teams toward stale benchmark tables.

## Read references selectively

- Delivery and rollback choices: [references/pattern.md](references/pattern.md)
- Platform-neutral pipeline shapes: [references/pipelines.md](references/pipelines.md)
- Supply-chain and credential controls: [references/security.md](references/security.md)
- Current DORA measurement model: [references/dora.md](references/dora.md)

## Validation and done

A pipeline change is done when applicable syntax or local validation passes, referenced actions and images are immutable or explicitly justified, permissions are reviewed, representative triggers are tested, artifacts are traceable, and failure paths do not silently deploy. For deployment changes, also verify health signals and rollback behavior in a safe environment.

Report skipped checks, external settings the repository cannot prove, and any step that still requires a human approval or production window.
