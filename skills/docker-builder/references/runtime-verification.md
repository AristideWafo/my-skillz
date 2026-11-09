# Verify the shipped container

Read when changing runtime dependencies, users, mounts, entrypoints, resource limits, health behavior, or stateful services. Select checks from the change; do not turn every Dockerfile edit into a platform migration.

## Build evidence and runtime evidence differ

A successful build proves that its steps completed in the build environment. It does not prove that the final stage contains the right executable, shared libraries, certificates, assets, permissions, or default configuration.

Test the final image without source bind mounts or developer caches. Identify the tested image by digest or immutable local image identity and record the target platform. A successful emulated build is not equivalent to native execution on every claimed architecture; label which platforms were actually exercised.

## Acceptance matrix

| Change | Observable acceptance test |
|---|---|
| Base image or runtime dependencies | Start the real process and exercise code paths needing native libraries, TLS, DNS, or timezone data |
| UID/GID or filesystem permissions | Run as the intended identity against both empty and representative existing volumes |
| Read-only root filesystem | Exercise required writes with explicit temporary or persistent mounts; observe failures outside them |
| Entrypoint or process wrapper | Send normal termination, observe draining and exit status, verify child processes terminate |
| Build context or copy rules | Build from a clean checkout and verify required assets are present without host mounts |
| Resource limits | Exercise representative load and failure behavior within the intended memory/process budget |
| Health behavior | Distinguish startup delay, inability to serve, and recoverable dependency failure |
| Stateful image upgrade | Test data compatibility, ownership, restart, and a deliberately chosen recovery path on disposable data |

## Signals and shutdown

Run a bounded request or background job, request normal termination, and observe whether the application completes, cancels, or safely requeues it according to its contract. Check the exit result and whether forced termination was needed. A wrapper should forward signals and preserve useful exit status; adding an init does not fix application-level shutdown logic.

Derive the grace period from the work and platform limits. Do not increase it indefinitely to hide a process that ignores termination. If shutdown can interrupt a durable write, verify recovery after interruption on disposable data.

## Dependency and health behavior

Test slow or unavailable dependencies with bounded retries and useful diagnostics. Startup order does not remove the need to handle later dependency loss.

Choose health signals according to the platform's action: removing traffic, delaying readiness, or restarting the process are different responses. A transient external outage should not automatically cause every otherwise healthy replica to restart. Avoid probes that mutate state, expose secrets, or place excessive load on dependencies.

Do not label a container production-ready solely because a local port opens. Verify one representative application interaction and any required dependency contract.

## Existing volumes and recovery

An empty-volume test can miss ownership and migration failures on existing data. Before changing a UID, mount path, database version, or persistence layout, inspect the expected owner, on-disk format, active writers, and backup/recovery method.

Avoid recursive ownership changes across an unknown host mount. Scope adjustments to application-owned paths and account for their cost on large volumes. Do not delete volumes to make an upgrade test pass.

For an upgrade, establish whether old and new images can read the resulting data. Restoring an old digest does not undo a database migration. When backward compatibility is absent, name the recovery artifact, expected data loss, duration, and verification instead of promising a simple rollback.

Use isolated Compose project names, disposable directories, and non-conflicting ports for tests. Verify the exact project resources before cleanup; never use broad prune commands as routine test teardown.

## Security evidence without secret leakage

Inspect the intended final artifact and its build inputs. Redact environment/configuration output and avoid copying credential-bearing command output into reports. A history scan alone cannot prove that credentials never entered a layer or exported build cache; use synthetic sentinel values for leakage tests when a build-secret path changes.

Test with the actual runtime restrictions before recommending a permission exception. Record the operation that fails and the smallest required writable path, capability, or network access. Avoid escalating to privileged mode to make a failing test green.

## Completion report

State image identity, platform exercised, startup/shutdown outcome, effective user, mount/data checks, and relevant security or vulnerability result. Distinguish controls present in the image from those enforced by the orchestrator, and state checks that need unavailable infrastructure.
