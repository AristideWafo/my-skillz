# Docker Compose decisions

Read this reference when changing multi-container development, test, or single-host deployment definitions.

## Preserve the existing model

Inspect all Compose files and the fully merged result before editing. Determine which files are base definitions, local overrides, production overlays, generated files, or examples.

Use additional files only when they make environment differences explicit without creating surprising merge behavior. Validate each supported combination:

```bash
docker compose -f compose.yaml -f compose.production.yaml config --quiet
```

## Images and builds

- Development may build locally when fast iteration requires it.
- Production may pull a prebuilt artifact identified by an immutable digest or controlled version.
- Do not hide a production fallback to `latest` in variable expansion.
- Keep build-only mounts and source bind mounts out of production overlays.

## Configuration and secrets

Environment files are configuration transport, not automatically secure secret storage. Avoid committing secret values. Reuse Docker secrets or the deployment environment's secret mechanism when available.

Document required variables and fail early when a production value is missing rather than silently using a development default.

## Dependencies and health

`depends_on` controls startup ordering; readiness conditions require meaningful healthchecks. Startup order does not guarantee that an external dependency is semantically ready or will remain healthy. Applications still need bounded connection retries and failure handling.

Do not assume minimal or distroless images contain `curl`, `wget`, or a shell for health commands.

## Networks and ports

Expose only ports required by the host or external clients. Internal service-to-service traffic should use named networks and service names. Add network separation when it enforces a real trust boundary; avoid decorative network proliferation.

## Volumes and data

Before changing a named volume, mount path, database image, or UID, identify data ownership, backup state, migration behavior, and recovery. Removing a volume or recreating a stateful service can be destructive even when the Compose edit looks small.

## Production scope

Compose can support suitable single-host production deployments. It does not itself provide multi-host scheduling, automatic rescheduling across failed hosts, or cluster-level high availability. Choose it when those limits meet the service objective.

## Validation

Review `docker compose config`, start from an empty project state, exercise dependency failure and restart behavior, verify persistence, and confirm shutdown does not corrupt data. For production overlays, verify the exact image identity and secret sources before deployment.
