# Dashboard composition patterns

Read this reference after the audience and dashboard question are known.

## Service health

Use a top-to-bottom path:

1. user-impact summary or SLO state;
2. request rate, errors, and latency distribution;
3. saturation and dependency health;
4. version, region, instance, or endpoint drill-down;
5. links to logs, traces, runbooks, and related dashboards.

Not every service needs every layer. Keep only signals that help the intended reader decide or investigate.

## Resource or platform dashboard

Lead with capacity and saturation for the managed resource, then show demand and errors. Normalize comparisons when instances differ in size. Separate workloads whose magnitude would hide smaller but important series.

## Business process dashboard

Define the process outcome and time window before choosing technical signals. Show volume, success/failure, processing delay, backlog, and data freshness when they affect the decision.

## Incident overview

Optimize for rapid shared understanding:

- current impact and affected scope;
- start time and recent changes;
- traffic, errors, latency, saturation;
- affected dependencies and regions;
- annotations for deploys and mitigations;
- links to the incident record and detailed views.

## Panel review

For each panel, record purpose, query owner, unit, expected range, abnormal interpretation, action or drill-down, and missing-data behavior. Move deep diagnostic detail away from the primary view when it overwhelms incident recognition.

## JSON generation

Inspect the target Grafana version, datasource UID/type, provisioning method, existing JSON model, variables, and library panels before generating JSON. Validate imported JSON in a non-production Grafana instance or with the repository's schema/tooling.

Keep credentials and tokens outside dashboard JSON and provisioning files. Reuse the project's secret references and service-account pattern. Confirm the destination organization, folder, and datasource permissions before import; an apparently harmless dashboard can reveal restricted metrics, logs, labels, internal URLs, or annotations.
