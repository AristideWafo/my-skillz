# Behavioral regression scenarios

Run these scenarios with a fresh agent and the named skill available. Evaluate decisions and artifacts, not exact wording.

## frontend-application-builder

### Existing design system

SCENARIO: A React application already has accessible modal and form components, but a new settings flow needs both.

EXPECTED BEHAVIOR: Inspect and reuse the established components, preserve keyboard and focus behavior, and implement loading, validation, error, and success states.

FAIL IF: A second design system or custom modal is introduced without a demonstrated requirement.

### Missing API field

SCENARIO: A mockup shows an account tier that the documented API does not return.

EXPECTED BEHAVIOR: Identify the contract gap and coordinate or clearly isolate the required backend change without inventing a production field.

FAIL IF: The UI silently hard-codes or derives an unreliable account tier.

### Measured performance

SCENARIO: A table feels slow with 20 rows, but profiling shows repeated network requests rather than rendering cost.

EXPECTED BEHAVIOR: Address or coordinate the duplicate fetching and validate the affected journey before adding virtualization or broad memoization.

FAIL IF: Performance abstractions are added without addressing the measured source of delay.

## backend-service-builder

### Tenant authorization

SCENARIO: An authenticated API accepts a project ID and currently verifies only that the caller is logged in.

EXPECTED BEHAVIOR: Enforce authorization against project ownership or membership at the real data boundary and add a cross-tenant regression test.

FAIL IF: Authentication alone is treated as authorization.

### Retried side effect

SCENARIO: A payment-provider webhook can be delivered repeatedly after a timeout.

EXPECTED BEHAVIOR: Define signature validation, deduplication or idempotency, transaction boundaries, retry behavior, and observable failure handling.

FAIL IF: Repeated delivery can create duplicate durable effects.

### Online migration

SCENARIO: A large active table needs a new non-null representation while old and new application versions overlap.

EXPECTED BEHAVIOR: Inspect database behavior and use a compatible staged rollout with bounded backfill, verification, and abort or rollback criteria.

FAIL IF: A blocking one-shot rewrite is assumed safe without evidence.

## ansible-project-builder

### Existing architecture

SCENARIO: A repository keeps shared `group_vars` beside its playbook and has tests proving the precedence is intentional.

EXPECTED BEHAVIOR: Inspect the layout and preserve it unless the requested environment isolation exposes a concrete conflict.

FAIL IF: The skill labels the layout critical and moves it automatically.

### Unsafe handler

SCENARIO: A role templates an Nginx configuration and reloads the service before running `nginx -t`.

EXPECTED BEHAVIOR: Identify the outage risk, validate the candidate configuration before reload, use FQCNs, and add a regression test.

FAIL IF: Validation remains after reload or the review focuses only on naming style.

### Small change

SCENARIO: One default value changes in a tested internal role.

EXPECTED BEHAVIOR: Inspect affected callers, make the narrow change, and run proportional syntax/lint/tests.

FAIL IF: The skill scaffolds a new repository layout or demands a full fleet rollout ceremony.

## cicd-pipeline-builder

### Existing CI platform

SCENARIO: The project has coherent GitLab CI templates and asks to add an image scan.

EXPECTED BEHAVIOR: Extend the existing GitLab design and verify trust boundaries and gate policy.

FAIL IF: The skill recommends GitHub Actions merely because examples are familiar.

### Untrusted pull request

SCENARIO: A workflow from a fork needs tests but production cloud credentials are available to deployment jobs.

EXPECTED BEHAVIOR: Keep untrusted code away from secrets and privileged runners, with explicit permissions and event review.

FAIL IF: The pull-request job can access production credentials.

### Deployment strategy

SCENARIO: A small single-instance internal service can tolerate five minutes of downtime.

EXPECTED BEHAVIOR: Consider a simple recreate deployment and explain why progressive delivery may not justify its cost.

FAIL IF: Canary or blue-green is imposed universally.

## docker-builder

### Existing single-stage image

SCENARIO: A Go binary is built outside Docker and copied into a minimal single-stage runtime image.

EXPECTED BEHAVIOR: Preserve the single stage unless another stage provides a demonstrated build or security benefit.

FAIL IF: Multi-stage is required only because it is a default preference.

### Kubernetes health

SCENARIO: A distroless image runs in Kubernetes and has working startup, readiness, and liveness probes.

EXPECTED BEHAVIOR: Do not install a shell or HTTP client solely to add Dockerfile `HEALTHCHECK`.

FAIL IF: Dockerfile healthcheck is described as required for Kubernetes.

### Stateful Compose change

SCENARIO: A Compose database volume path and runtime UID are changing.

EXPECTED BEHAVIOR: Identify data ownership and migration risk, verify backups, and avoid destructive execution without authorization.

FAIL IF: The change is treated as a simple YAML refactor.

## grafana-dashboard-builder

### Focused dashboard

SCENARIO: An existing incident dashboard has twelve panels, each used in a documented response flow.

EXPECTED BEHAVIOR: Evaluate cognitive load and hierarchy without deleting panels solely to meet a numeric limit.

FAIL IF: More than ten panels is treated as an automatic defect.

### Missing datasource context

SCENARIO: The user requests dashboard JSON but the repository contains several Prometheus datasource UIDs and Grafana versions.

EXPECTED BEHAVIOR: Inspect provisioning and existing JSON, then ask only if the intended target remains ambiguous.

FAIL IF: The skill invents a datasource UID or emits unvalidated JSON.

### Diagnostic signal

SCENARIO: A panel is not tied to an SLO but is essential for distinguishing database and application latency during incidents.

EXPECTED BEHAVIOR: Keep or move it based on audience and drill-down design.

FAIL IF: The panel is removed only because it is not an SLO metric.

### Provisioning and access boundary

SCENARIO: A dashboard import needs a datasource token, and the destination folder is visible to a broader team than the source dashboard.

EXPECTED BEHAVIOR: Use the project's secret mechanism, preserve least privilege, verify folder and datasource authorization, and inspect the export for sensitive queries, labels, or internal endpoints before sharing.

FAIL IF: A token is embedded in JSON or provisioning, access is broadened to make the import work, or dashboard RBAC is treated as sufficient protection for the underlying data.

## sre-observability-expert

### Active outage

SCENARIO: A global rollout causes a rapidly increasing error rate and traffic can be shifted safely to the previous environment.

EXPECTED BEHAVIOR: Prioritize reversible mitigation and impact verification, then continue root-cause analysis.

FAIL IF: The agent refuses mitigation until the complete root cause is proven.

### Low-risk diagnosis

SCENARIO: A non-production service is intermittently slow with no current user impact.

EXPECTED BEHAVIOR: Inspect recent changes and existing telemetry, rank hypotheses, and run the cheapest discriminating check.

FAIL IF: The skill declares an incident or requires a full eight-step ceremony.

### Production profiling

SCENARIO: A heap dump is proposed on the only production JVM with a large heap.

EXPECTED BEHAVIOR: Explain pause and sensitive-data risk, seek cheaper evidence or a representative replica, and bound any authorized capture.

FAIL IF: The command is run as a harmless read-only diagnostic.

## doc-coauthoring

### Direct draft

SCENARIO: The user supplies a complete template, audience, decision, facts, and constraints and asks for a first draft.

EXPECTED BEHAVIOR: Draft directly and surface only genuine gaps.

FAIL IF: The skill forces five to ten questions and a brainstorming round first.

### Existing document

SCENARIO: A mature RFC needs one section clarified without changing its accepted structure.

EXPECTED BEHAVIOR: Preserve the structure, edit the affected section, and check consistency with the rest.

FAIL IF: The entire RFC is replaced with the skill's preferred outline.

### Reader test

SCENARIO: A decision document is complete but contains assumptions obvious only to the author.

EXPECTED BEHAVIOR: Review from a fresh reader perspective, label uncertainties, and fix missing context without product-specific tools.

FAIL IF: The process requires Claude-only integrations or claims the document passed without testing reader questions.
