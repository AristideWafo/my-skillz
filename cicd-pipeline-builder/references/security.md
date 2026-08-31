# Delivery security decisions

Read this reference for workflows that handle credentials, publish artifacts, run third-party code, or deploy to protected environments.

## Threat model first

Identify which inputs are controlled by an untrusted contributor: branch names, commit messages, pull-request titles, changed files, build scripts, test output, generated paths, and artifacts from earlier jobs. Do not interpolate untrusted values into shell commands or privileged workflow expressions without safe handling.

## Third-party actions and workflows

- Pin third-party actions to a reviewed full commit SHA. A tag or branch can move.
- Record the human-readable release in a comment or dependency-management configuration.
- Verify the SHA belongs to the upstream repository and review security advisories before updating.
- Prefer a small, auditable script over an unnecessary third-party action.
- Apply the same review to reusable workflows, container actions, downloaded binaries, and installer scripts.

Never publish a supposedly production-ready template with `@master` or `@main`.

## Tokens and credentials

- Set workflow and job permissions explicitly; start with no write permission.
- Use OIDC or workload identity for cloud access where supported.
- Scope credentials to the environment, repository, operation, and duration required.
- Keep production credentials out of untrusted pull-request workflows.
- Masking is not a substitute for preventing secrets from reaching logs or child processes.

When a workflow may have executed compromised code, identify every accessible credential and rotate according to the incident scope.

## Artifact integrity

Depending on risk, combine:

- immutable digest-based deployment;
- provenance attestations;
- SBOM generation;
- vulnerability and license evaluation;
- signature verification at admission or deployment;
- retention of build evidence.

Signing does not make untrusted build inputs safe. Protect the build identity and runner before relying on its signature.

## Security gates

A blocking gate needs:

- a signal with acceptable false-positive and false-negative behavior;
- a documented severity policy;
- ownership and response time;
- a time-bounded exception with rationale;
- evidence that the scanner actually covered the intended artifact.

Do not block every finding indiscriminately. Consider exploitability, reachability, available fixes, environment exposure, and compensating controls. Do not silently downgrade accepted risk either.

## High-risk workflow features

Review carefully:

- privileged or persistent self-hosted runners;
- `pull_request_target` or equivalent privileged events;
- write-capable repository tokens;
- Docker socket access;
- artifacts crossing trust boundaries;
- dynamic workflow or command generation;
- production environments without independent approval;
- credentials shared across environments.

## Maintenance

Action versions, runner runtimes, scanners, and provider authentication change frequently. Verify current primary documentation and advisories whenever a workflow is created or materially updated; do not treat examples in this repository as a version catalog.
