---
name: cicd-pipeline-builder
description: >
  Guide and enforce Staff-level CI/CD pipeline design for <Skills user> (DevOps/Cloud Architect). Trigger whenever <Skills user> asks to create, review, audit, or improve any pipeline, delivery workflow, deployment strategy, or release process. Also trigger for: GitHub Actions or GitLab CI design, Java/Spring Boot/Docker/Terraform/Ansible pipelines, Blue-Green/Canary/Rolling deployments, GitOps with ArgoCD/FluxCD, artifact promotion, DevSecOps gates (SAST/Trivy/Cosign/Checkov), post-deployment validation, semantic versioning (Nyx), monorepo CI, or DORA metrics. Trigger even if <Skills user> just says "help me with my pipeline" or "how do I deploy this". Enforces: immutable artifacts, build-once, CI/CD separation, security-by-default, and production-readiness.
---

# CI/CD Pipeline Builder - Staff Engineer Standards

> Think in delivery principles, not tools.
> Core question: How do we move a change to production quickly, safely, reproducibly, and reliably?

---

## Initial Assessment - Ask the Right Questions First

Before any design work, always assess context:

1. Application stack - Java/Spring Boot? Node.js? Go? Multi-stack?
2. Deployment target - ECS Fargate? Kubernetes? EC2? Lambda? VPS?
3. Environments - How many? (dev/staging/prod or more?)
4. CI/CD platform - GitHub Actions? GitLab CI? Jenkins? other?
5. Registry - GHCR? ECR? Docker Hub? Harbor?
6. IaC - Terraform/Terragrunt? Pulumi? CloudFormation?
7. Target deployment strategy - Rolling? Blue-Green? Canary?
8. Current maturity - Is there an existing pipeline? What are the gaps?
9. Constraints - Required manual approvals? SOC2/PCI compliance?
10. Monorepo or polyrepo? - Strong impact on pipeline architecture.

If several answers are unknown, recommend the most conservative architecture and document assumptions.

---

## The 10 Non-Negotiable Rules

These rules apply regardless of tools, language, or target platform:

| # | Rule | Why |
|---|---|---|
| 1 | Single main branch (main) | Trunk-Based Development lowers integration risk |
| 2 | Build once | What is tested must be what is deployed |
| 3 | Immutable artifact | Never mutate artifacts after creation |
| 4 | Promote artifact, do not rebuild | Same image from dev to prod |
| 5 | Separate CI and CD | CI creates artifacts, CD deploys them |
| 6 | Git is the source of truth | Infra and delivery state must be in Git |
| 7 | Security is built-in | Shift-left controls at every gate |
| 8 | Automatic post-deploy validation | Smoke tests + health checks are mandatory |
| 9 | Rollback is simple and tested | Rollback must be as automated as deploy |
| 10 | Measure to improve | DORA metrics over subjective feelings |

---

## Universal CI/CD Pattern

```text
Developer -> Git Push -> Pull Request
                              |
                              v
                    +-----------------------------------------+
                    |                 CI                      |
                    | Lint -> Test -> Build -> Security Scan |
                    | -> Package Artifact -> Publish Registry |
                    +------------------+----------------------+
                                       |
                                       v Versioned artifact
                    +-----------------------------------------+
                    |                 CD                      |
                    | Deploy Dev -> Smoke Test               |
                    | -> Deploy Staging -> Acceptance Test   |
                    | -> Optional Manual Approval            |
                    | -> Deploy Prod -> Smoke Test + Monitor |
                    +-----------------------------------------+
```

CI/CD separation rule: CI produces backend:1.4.2. CD promotes that exact artifact across environments without rebuilding.

---

## Artifact Promotion Pattern

```text
Build image -> backend:1.4.2
  |
  v
Registry (GHCR / ECR)
  |
  v
Deploy DEV -> Automated tests -> PASS
  |
  v
Deploy STAGING -> Functional tests -> PASS
  |
  v
Manual approval gate
  |
  v
Deploy PROD -> Smoke Test -> Monitor
```

The artifact remains identical at every stage. Only runtime configuration changes by environment.

---

## Immutable Artifact Pattern

```yaml
# ANTI-PATTERN - mutate a running container
docker exec container apt install something

# GOOD PATTERN - build a new image for every change
docker build -t backend:1.4.3 .
docker push ghcr.io/org/backend:1.4.3
```

Corollary: never use latest in production. Always use semantic tags, commit SHA tags, or both.

---

## Deployment Strategies

Full details: references/pattern.md

| Strategy | Rollback | Risk | Typical use case |
|---|---|---|---|
| Rolling Update | Slow | Medium | Kubernetes default |
| Blue-Green | Instant | Low | Critical production systems |
| Canary | Auto rollback | Very low | Progressive rollout |
| Feature Flags | Instant toggle | Near zero | Decouple deploy from release |

Recommended by context:
- ECS Fargate: Blue-Green with CodeDeploy or task replacement
- Kubernetes: Canary with Argo Rollouts or Flagger
- VPS: Simple Blue-Green or Rolling
- Lambda: Weighted alias traffic shifting

---

## Security Gates - DevSecOps

Every gate must fail the pipeline when it fails:

```text
SAST (Semgrep / SpotBugs)         -> source code
Dependency Scan (OWASP)           -> dependencies
Container Scan (Trivy)            -> Docker image
IaC Scan (Checkov / tfsec)        -> Terraform/Ansible
Image Signing (Cosign)            -> after registry push
DAST (OWASP ZAP)                  -> staging environment
```

Full setup: references/security.md

---

## Post-Deployment Validation - Mandatory Pattern

Often missed, always required:

```bash
# Minimal smoke test - adapt to your stack
for i in 1 2 3; do
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    https://api.example.com/actuator/health)

  if [ "$HTTP_STATUS" -eq 200 ]; then
    echo "Health check $i passed"
  else
    echo "Health check $i failed (HTTP $HTTP_STATUS)"
    # Trigger automatic rollback
    exit 1
  fi
  sleep 5
done
```

Complete pattern: Deploy -> Smoke Test (3x) -> Health Check -> Monitoring Validation -> Rollback on failure.

---

## Pipelines by Tech Stack

Ready-to-use templates: references/pipelines.md

| Stack | Section |
|---|---|
| Java / Spring Boot (GitHub Actions) | pipelines.md#java-github-actions |
| Generic Docker | pipelines.md#docker |
| Terraform / Terragrunt | pipelines.md#terraform |
| Ansible | pipelines.md#ansible |
| GitOps (ArgoCD) | pipelines.md#gitops-argocd |
| Monorepo (path filtering) | pipelines.md#monorepo |
| Semantic Versioning (Nyx) | pipelines.md#semver |

---

## GitOps Pattern

Instead of running kubectl apply directly in CI:

```text
CI Pipeline
  -> Push image v1.4.2
  -> Update Kubernetes manifest in Git
  -> (kustomize patch or Helm values.yaml)
ArgoCD / FluxCD
  -> Detect git change
  -> Sync cluster automatically
  -> Post-sync health check
```

Benefits: full auditability, rollback via git revert, and Git as full environment truth.

---

## Secrets Management in Pipelines

```yaml
# ANTI-PATTERN - plain secrets in workflow
env:
  DB_PASSWORD: "mysecretpassword"

# GOOD PATTERN - OIDC + cloud secret manager
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789:role/github-actions-role
    aws-region: eu-west-1

- name: Get secret from SSM
  run: |
    DB_PASSWORD=$(aws ssm get-parameter \
      --name /prod/db/password \
      --with-decryption \
      --query Parameter.Value \
      --output text)
    echo "::add-mask::$DB_PASSWORD"
```

Rule: never store static cloud credentials in CI variables. Use OIDC + secret manager by default.

---

## Pipeline Caching - Performance

```yaml
# Java / Maven
- uses: actions/cache@v3
  with:
    path: ~/.m2/repository
    key: ${{ runner.os }}-maven-${{ hashFiles('**/pom.xml') }}

# Docker layers (BuildKit)
- uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

Caching can reduce build time by up to 3x. Cache keys should always include dependency lock files.

---

## DORA Metrics - Measure Delivery Maturity

Details and benchmarks: references/dora.md

| Metric | Elite | High | Medium | Low |
|---|---|---|---|---|
| Deployment Frequency | On-demand | Weekly | Monthly | Less than monthly |
| Lead Time for Changes | < 1 hour | < 1 day | 1 week to 1 month | > 1 month |
| Change Failure Rate | < 5% | < 10% | 10% to 15% | > 15% |
| MTTR | < 1 hour | < 1 day | < 1 week | > 1 week |

Source: DORA State of DevOps Report + DevOps Handbook.

---

## Anti-Patterns - Immediate Red Flags

| Anti-pattern | Severity | Correction |
|---|---|---|
| Rebuilding image per environment | Critical | Build once, promote everywhere |
| latest tag in production | Critical | Use versioned semantic tags |
| Static AWS credentials in CI | Critical | OIDC + IAM role |
| No post-deploy smoke test | Critical | Add health checks + auto rollback |
| CI and CD in same job | Important | Split workflows |
| Secrets in env variables | Important | Use SSM or Vault |
| Feature branches live > 1 week | Important | Trunk-Based Development |
| docker push latest only | Important | Use sha + semver tags |
| Terraform apply without review | Important | Manual approval gate |
| No CI cache | Recommended | Cache Maven/npm/Docker layers |
| Tests only local | Recommended | Run tests in isolated CI environment |
| Monolithic pipeline | Recommended | Parallelize jobs by domain |

---

## Pre-Production Checklist

- [ ] Build produces one versioned artifact?
- [ ] Artifact is never rebuilt between environments?
- [ ] AWS credentials via OIDC (no static keys)?
- [ ] Trivy scan blocks HIGH/CRITICAL findings?
- [ ] Image signed with Cosign?
- [ ] Post-deploy smoke test with automatic rollback?
- [ ] Environment-specific variables (no hardcoded values)?
- [ ] Pipeline is idempotent (safe rerun)?
- [ ] Manual approval gate before prod?
- [ ] Rollback documented and tested?
- [ ] DORA metrics instrumented?

---

## What This Skill Produces

When <Skills user> asks to create or improve a pipeline:

Full pipeline - GitHub Actions or GitLab CI workflow ready to use, adapted to stack, with parallel jobs, cache strategy, security gates, and smoke tests.

Critical review - Audit of existing pipeline with severity and concrete corrective actions.

Architecture decision - Deployment strategy recommendation based on SLA, team size, and platform constraints.

Security upgrade - Add missing DevSecOps controls to an existing pipeline.

DORA baseline - Define what to measure first and realistic target ranges.
