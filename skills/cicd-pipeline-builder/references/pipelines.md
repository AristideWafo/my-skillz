# Pipeline shapes and verification

Read this reference when creating or restructuring a pipeline. Adapt the shape to the repository instead of copying a platform template blindly.

## A minimal delivery graph

```text
change
  -> fast validation
  -> build immutable artifact
  -> artifact and dependency checks
  -> publish with traceable identity
  -> deploy to a safe environment
  -> verify behavior
  -> approval or policy decision
  -> production rollout
  -> verify and observe
```

Jobs may run in parallel when they do not depend on one another. Keep the dependency graph visible so a failed or skipped prerequisite cannot silently permit deployment.

## Repository inspection

Before adding jobs, inspect:

- existing reusable workflows and composite actions;
- package manager caches and lockfiles;
- artifact registry and naming conventions;
- release tags and generated version files;
- environments, approvals, protected branches, and required checks;
- self-hosted runner trust boundaries;
- deployment manifests and rollback commands.

## Workflow controls

For each job, decide deliberately:

- minimal `permissions`;
- timeout and cancellation behavior;
- concurrency group and whether an older run should be cancelled;
- trusted versus untrusted event context;
- artifacts consumed and produced;
- retry behavior for transient operations;
- logs and evidence retained after failure.

Do not retry deterministic test failures. Bound retries for network or provider operations and make duplicate execution safe.

## Artifact identity

Publish an artifact with a unique identity such as a digest or commit-derived version. Record:

- source commit;
- build workflow/run;
- dependency lock state;
- artifact digest;
- provenance or attestation when required;
- environments to which that identity was deployed.

Do not infer the production artifact from a mutable `latest` tag.

## Monorepos

Use path filtering only when dependencies between components are known. A shared library or root build configuration change may need to invalidate several components. Keep a full validation path available for dependency-graph or filter changes.

## Validation

Validate pipeline changes at the cheapest useful layer:

1. parse and lint configuration;
2. exercise pull-request or dry-run paths without privileged secrets;
3. verify artifact publication in a non-production target;
4. deploy to an isolated or staging environment;
5. test failure, cancellation, and rollback paths;
6. inspect final permissions and environment protection settings outside the repository.

Repository files cannot prove organization settings, runner hardening, secret scopes, or environment approval rules. Report these as external checks rather than assuming them.
