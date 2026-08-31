---
name: docker-builder
description: Create, review, secure, or optimize Dockerfiles, container images, build contexts, and Docker Compose configurations. Use for container build and runtime artifacts; use the CI/CD skill for broader delivery pipelines.
---

# Docker Builder

Produce a container artifact that fits the application and deployment platform while minimizing unnecessary runtime content and privilege.

## Workflow

1. Inspect the application build, current Dockerfiles and Compose files, lockfiles, `.dockerignore`, target platform, and existing image conventions.
2. Determine runtime requirements, supported architectures, debugging needs, health model, secret/configuration injection, and supply-chain policy from project evidence.
3. Preserve a coherent existing build strategy unless a measurable security, correctness, size, or build-time problem justifies change.
4. Implement the smallest improvement, then build and exercise the image as the target runtime will use it.

## Decision rules

- Choose a base image from compatibility, maintenance, vulnerability posture, size, and operability. Alpine, slim, distroless, and scratch each have tradeoffs.
- Use multi-stage builds when they remove build-only dependencies, reduce attack surface, or improve artifact separation. Do not add stages that provide no meaningful benefit.
- Use digests when reproducibility or supply-chain integrity requires immutable inputs. A version tag alone is mutable; pair updates with an intentional refresh process.
- Run as a non-root user unless the process has a documented need for elevated privileges. Drop capabilities and prefer a read-only filesystem when the workload supports them.
- Keep secrets out of build arguments, layers, images, and committed Compose files. Use the target platform's secret mechanism.
- Use exec-form entrypoints when correct signal forwarding matters. Add an init process only when the application does not reap or forward signals correctly.
- Define health checks where the runtime consumes them and the signal is meaningful. Kubernetes startup, readiness, and liveness probes belong in workload manifests; they are not replaced by a Dockerfile `HEALTHCHECK`.
- Use Compose for development, tests, and suitable single-host deployments. Do not claim it provides multi-host high availability or scheduling features it does not have.
- Optimize caching after correctness. Copy stable dependency metadata before frequently changing source when that matches the build tool.

## Read references selectively

- Base images, stages, cache, entrypoints: [references/dockerfile.md](references/dockerfile.md)
- Compose environments, networks, volumes, health: [references/compose.md](references/compose.md)
- Image and runtime hardening: [references/security.md](references/security.md)

## Validation and done

A change is done when the image builds from a clean context, expected startup and shutdown work, the intended user and filesystem permissions are verified, required ports and health signals work, no secret is present in history or configuration, and relevant lint or vulnerability checks pass under the project's policy. For Compose, validate the fully merged configuration for each affected environment.

Report image identity, tests run, size or security changes when relevant, and any platform-specific checks that remain.
