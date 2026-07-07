---
name: docker-builder
description: >
  Guide and enforce expert-level Docker image design, Dockerfile patterns, and Docker Compose architecture for <Skills user>. Trigger whenever <Skills user> asks about Dockerfiles, Docker Compose, containerization, image building, container security, image optimization, or multi-stage builds. Also trigger for: writing or reviewing a Dockerfile, designing a Compose stack, optimizing image size or build time, securing containers, setting up healthchecks, choosing a base image, managing dev vs prod environments with Compose, or thinking about production-ready containerization. Trigger even if <Skills user> just says "help me containerize this", "review my Dockerfile", or "my image is too big". Enforces: single responsibility, immutable images, explicit tags, non-root execution, layer cache strategy, observable containers, and build-once deploy-everywhere.
---

# Docker Builder - Expert Standards

> The right question is not How do I write a Dockerfile?
> It is How do I build an image that is reproducible, secure, maintainable, and deployable everywhere?
>
> A Dockerfile is a contract between build and runtime. It must still be readable six months later.

---

## Initial Assessment - Context Before Design

Before writing a single Dockerfile line:

1. Language/runtime - JVM? Node? Go? Python?
2. Artifact type - fat JAR? static binary? npm bundle?
3. Deployment target - ECS Fargate? Kubernetes? VPS?
4. Size constraints - limited network? registry cost constraints?
5. Multi-platform - ARM + AMD64 required?
6. Compose usage - local dev? full stack? production?

---

## Four Properties of a Production-Ready Image

Every Dockerfile decision should serve at least one of these properties:

### 1) Reproducible
Same source + same Dockerfile = same image, always.
- Pin base image tags (node:22.18.0-alpine, never node:latest)
- Lock dependencies (package-lock.json, pinned Maven versions)
- Deterministic build steps

### 2) Immutable
Image is frozen after build; config is injected at runtime.
- Configure via ENV and runtime env vars
- Never hardcode environment-specific values in build layers
- Same image across dev/staging/prod

### 3) Secure
Minimal attack surface and least privilege.
- Always run as non-root
- Use minimal official base images
- Never bake secrets into image layers
- Pinned tags enable predictable CVE management

### 4) Observable
The platform must know if container is alive and healthy.
- Define HEALTHCHECK
- Log to stdout/stderr only
- Add OCI labels (version, maintainer, source)

---

## Mental Model: Layer Cake

Each RUN/COPY/ADD creates a layer, and Docker caches layers.
Rule: put rarely changing steps first, frequently changing steps later.

```text
FROM base-image
COPY dependency-file .
RUN install-dependencies
COPY source-code .
RUN build
USER non-root
HEALTHCHECK
ENTRYPOINT/CMD
```

If COPY . . comes before dependency install, every code change invalidates dependency cache. This is one of the most common anti-patterns.

---

## Multi-Stage Build - Mandatory Pattern

Build stage contains compilers and toolchains that must never ship to production.

```text
BUILD stage   -> heavy image with toolchain
RUNTIME stage -> minimal image with runtime artifact only
```

Typical result: 500MB to 80MB.

Multi-stage patterns by stack are in references/dockerfile.md

---

## Choosing a Base Image

| Need | Recommended image | Avoid |
|---|---|---|
| JVM production | eclipse-temurin:21-jre-alpine | ubuntu + apt install java |
| JVM high security | gcr.io/distroless/java21 | untrusted non-official images |
| Node.js | node:22-alpine | node:latest |
| Go | scratch or distroless/static | full distro image with shell |
| Python | python:3.12-slim | python:3.12 full |
| Nginx | nginx:1.27-alpine | ubuntu + apt install nginx |

Absolute rule: official image and explicit version tag.

---

## Docker Compose - What It Is and What It Is Not

Compose is local orchestration, not a production orchestrator.

```text
Compose is good for:
- Local multi-service development
- Integration tests
- Demo stacks
- CI service dependencies

Compose is not for:
- Production HA orchestration
- Advanced load balancing
- Auto-scaling
```

Production pattern: CI builds image, pushes to registry, runtime pulls and restarts. Never build in production.

Compose patterns are in references/compose.md

---

## Six Gold Questions

Before docker build or docker compose up:

1. Is this reproducible six months from now?
2. Is this immutable at runtime?
3. Is this secure (non-root, no secrets, minimal image)?
4. Is this observable (healthcheck + stdout logs)?
5. Can the same image run in dev/staging/prod?
6. Can someone understand this Dockerfile quickly later?

---

## Anti-Patterns - Immediate Red Flags

| Anti-pattern | Severity | Violated principle | Fix |
|---|---|---|---|
| FROM ubuntu for a simple API | Critical | Security + size | Use minimal official base image |
| FROM node:latest | Critical | Reproducibility | Pin explicit version |
| COPY . . before npm install | Critical | Cache strategy | Copy dependency files first |
| Secrets in ENV or RUN | Critical | Security | Use secret manager/runtime injection |
| Running as root | Critical | Security | Create user + USER instruction |
| Missing .dockerignore | Important | Performance + security | Exclude .git, node_modules, .env |
| Missing HEALTHCHECK | Important | Observability | Add healthcheck before entrypoint |
| No multi-stage build | Important | Security + size | Split build and runtime stages |
| docker build in production | Important | Immutability | Build in CI, deploy pulled image |
| ADD from URL blindly | Recommended | Reproducibility | Prefer COPY --from or verified curl |
| Missing OCI labels | Recommended | Traceability | Add org.opencontainers.image labels |
| Unpinned apt package versions | Recommended | Reproducibility | Pin versions where possible |

---

## Container Security - Core Principles

Detailed hardening patterns are in references/security.md.

Summary:
- Least privilege
- Minimal attack surface
- Immutable filesystem when possible
- Network isolation by default

---

## Production-Ready Image Checklist

Dockerfile:
- [ ] Official base image with pinned tag
- [ ] Multi-stage build
- [ ] Dependency copy/install before source copy
- [ ] .dockerignore present
- [ ] Non-root USER defined
- [ ] HEALTHCHECK present
- [ ] OCI labels present
- [ ] No secrets in layers
- [ ] ENTRYPOINT uses exec form

Compose:
- [ ] Base + dev/prod override separation
- [ ] Variables in env files, not hardcoded
- [ ] Named networks by functional domain
- [ ] Named volumes for persistent data
- [ ] healthcheck + service_healthy dependencies
- [ ] No build in production compose

---

## What This Skill Produces

Complete Dockerfile - Multi-stage, non-root, healthcheck-enabled, label-compliant, cache-optimized.

Critical review - Dockerfile/Compose audit with severity and concrete fixes.

Compose architecture - base + overrides, networks, volumes, profile strategy.

Optimization plan - image size reduction and build acceleration.

Security upgrade - hardening recommendations and implementation steps.
