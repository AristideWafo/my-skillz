# Observability stack decisions

Read this reference when selecting or changing telemetry collection, storage, and correlation.

## Start from questions

Define the decisions the system must support:

- Is user impact occurring now?
- Which request, tenant, region, or dependency is affected?
- What changed before the symptom?
- Is a resource saturated or work queued?
- Can an operator move from an alert to useful evidence quickly?

Collect telemetry that answers these questions. More data is not automatically more observable.

## Signals

- **Metrics**: efficient aggregation, trends, SLOs, and alerting; limited high-cardinality detail.
- **Logs**: discrete events and diagnostic context; require structure, retention, and sensitive-data controls.
- **Traces**: request paths and distributed latency; require propagation, sampling, and service identity discipline.
- **Profiles**: code-level resource attribution; use continuously or on demand according to overhead and risk.

Choose the minimum signal set that answers the objective. A simple service may not need every signal type.

## Collection and ownership

Prefer standard instrumentation and a vendor-neutral collection boundary when it reduces lock-in or duplicated agents. OpenTelemetry is useful when its operational cost is justified; it is not mandatory for a small native stack.

Define service naming, environment, version, correlation identifiers, timestamp behavior, and ownership centrally enough to permit cross-signal navigation.

## Cardinality and volume

Do not use unbounded values such as user IDs, request IDs, raw URLs, or error messages as metric labels. Keep high-cardinality detail in logs or traces with controlled retention.

Estimate ingestion, storage, query, and egress cost before increasing sampling or retention. Preserve enough data to support incident and compliance needs.

## Alerts

Page on actionable impact or imminent exhaustion. Route lower-urgency conditions to tickets or dashboards. Each page should identify the affected service, evidence, likely owner, and first safe action.

## Version drift

Query languages, schemas, agents, and backend limits evolve. Inspect installed versions and current primary documentation before generating configuration. Preserve existing working conventions unless a concrete limitation requires migration.

## Validation

Generate representative traffic or failure, then verify collection, labels, timestamps, correlation, query results, retention, access control, and alert routing end to end.
