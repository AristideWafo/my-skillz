---
name: grafana-dashboard-builder
description: Create, audit, or simplify Grafana dashboards, panels, variables, and dashboard queries for operational or business decisions. Use for concrete dashboard artifacts; use the SRE skill for broader observability architecture and incident diagnosis.
---

# Grafana Dashboard Builder

Create dashboards that answer a defined question and reduce the time needed to detect, understand, or act on a condition.

## Workflow

1. Inspect the service, existing dashboards, datasource types and versions, metric and label conventions, related alerts, and dashboard provisioning method.
2. Identify the primary audience, decision, time horizon, and operational or business signal. Ask only for information that cannot be inferred from existing artifacts.
3. Reuse coherent dashboard conventions and recording rules. Do not duplicate an existing dashboard or query without a clear reason.
4. Select the smallest set of panels that answers the question, then validate queries against the real datasource or representative data.
5. Review the result as the intended reader: important state first, trends second, diagnostic detail through drill-downs or links.

## Panel decision test

Keep a panel when its purpose, abnormal condition, and likely action are clear. Move it to a diagnostic dashboard when it is useful only during deep investigation. Remove it when it duplicates another signal or has no plausible decision attached.

Treat panel counts as a cognitive-load budget, not an absolute limit. Split a dashboard when audiences, refresh needs, time ranges, or decisions conflict.

## Query and alert rules

- Prefer readable queries and stable labels. Use recording rules when repeated or expensive logic benefits from central ownership.
- Control cardinality before adding breakdowns by unbounded labels.
- Document units, transformations, thresholds, and missing-data behavior.
- Tie paging alerts to user or service impact and an actionable response. Diagnostic dashboards may contain useful signals that are not themselves SLO indicators.
- Version critical dashboard JSON and validate it against the target Grafana version and datasource.

## Access and provisioning safety

- Preserve the target organization, folder, team, and datasource permission model. Apply least privilege to editors, viewers, service accounts, and provisioning identities; do not broaden access merely to make an import succeed.
- Treat datasource credentials, API tokens, signed URLs, internal endpoints, and sensitive queries or labels as protected data. Reference the repository's secret mechanism instead of embedding values in dashboard JSON, provisioning files, examples, logs, or screenshots.
- Treat dashboard permissions as presentation-layer controls, not a substitute for authorization at the datasource or tenant boundary. Verify both when a dashboard exposes restricted data.
- Review exported dashboards before sharing them outside their intended audience, and require explicit authorization before changing shared folders, organizations, service accounts, or live provisioning.

## Read references selectively

- Layout and panel patterns: [references/dashboard-templates.md](references/dashboard-templates.md)
- PromQL and LogQL reminders: [references/promql-logql-cheatsheet.md](references/promql-logql-cheatsheet.md)

## Validation and done

A dashboard is done when its objective and owner are visible, queries return the intended series, units and legends are correct, empty/error states are understandable, variables do not create surprising cardinality, links and drill-downs work, and a representative reader can identify the expected action without verbal explanation.

For audits, report panels to keep, change, move, or remove with a reason—not only a numeric score.
