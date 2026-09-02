# Dockerfile decisions

Read this reference when choosing a base image, build stages, cache layout, or process model.

## Base image

Evaluate:

- runtime and native-library compatibility;
- supported CPU architectures;
- patch cadence and provenance;
- package-manager and certificate needs;
- debugging and incident-response requirements;
- vulnerability and compliance policy;
- size and pull-time constraints.

`alpine`, `slim`, distroless, and `scratch` are options, not quality levels. Test native dependencies and operational tooling before changing libc or removing the shell.

For immutable inputs, pin a digest while retaining a readable tag:

```dockerfile
FROM example/runtime:VERSION@sha256:REVIEWED_DIGEST
```

Pair digest pinning with an update process so security patches are not frozen indefinitely.

## Build stages

Use separate stages when they prevent compilers, package managers, source, or credentials from entering the runtime image. A single-stage image can be appropriate for an already self-contained artifact when another stage adds no isolation or size benefit.

Copy only the runtime artifact from the builder. Verify that build-time secret mounts and caches are not copied into later stages.

## Cache order

Copy dependency manifests and lockfiles before frequently changing source when the build tool can restore dependencies independently. Use BuildKit cache mounts for expensive package caches when CI exports and scopes them safely.

Avoid assuming a warm cache in correctness tests. A clean build must still succeed.

## User and filesystem

- Create or select a stable non-root UID/GID where ownership across volumes matters.
- Set ownership during `COPY` when possible instead of adding corrective layers.
- Grant write access only to required paths.
- Verify behavior with a read-only root filesystem if the target platform enforces it.

## Entrypoint and signals

Use exec form so the application receives signals directly:

```dockerfile
ENTRYPOINT ["application"]
CMD ["--default-argument"]
```

Add `tini` or another init only if the process spawns children without reaping them or mishandles signal forwarding.

## Health

A Dockerfile `HEALTHCHECK` is useful only when the runtime consumes it and the image contains a suitable probe implementation. Do not install a large shell or HTTP client solely for a check if the platform can probe the service externally.

Kubernetes health behavior belongs in startup, readiness, and liveness probes in workload manifests.

## Validation

Build from a clean context, inspect history and configuration, run as the intended UID, exercise startup and graceful shutdown, and test the artifact on every claimed architecture. Use lint and vulnerability tools under the project's current policy.
