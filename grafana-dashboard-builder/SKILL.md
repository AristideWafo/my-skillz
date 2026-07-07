---
name: grafana-dashboard-builder
description: >
  Create, audit, and simplify Grafana dashboards with a strict KISS philosophy for <Skills user> (Cloud Architect/DevOps). Trigger for: creating a dashboard, Grafana dashboard JSON, dashboard review/audit, overloaded dashboards, panel design, PromQL/LogQL for dashboards, Grafana variables, SLO/burn-rate alerting, alert fatigue, incident-response dashboards, deciding which metrics to keep, or simplifying an existing dashboard. Trigger even when the word dashboard is not explicit if <Skills user> describes a noisy monitoring screen or asks what metrics to show for a service. Do not use this skill for general observability theory (SLI/SLO, stack choice, OpenTelemetry); route that to sre-observability-expert.
---

# Grafana Dashboard Builder - KISS: Create, Audit, Simplify

> Golden rule: If it does not help detect or resolve incidents faster, it does not belong on the dashboard.

This skill does exactly three things: create useful dashboards, audit existing dashboards, and simplify overloaded dashboards.

For observability theory, use sre-observability-expert. This skill applies the theory to practical dashboard construction.

---

## Mandatory Method - In This Exact Order

Never start with which panels to add. Start from the need:

1. Understand the system (service, architecture, dependencies)
2. Identify business objective (what decisions this dashboard enables)
3. Define relevant SLO (or ask if missing)
4. Choose minimal metrics that support that SLO
5. Build dashboard with readability hierarchy
6. Challenge each panel with Dashboard Critic questions
7. Simplify by removing anything that fails the test

If context is missing, ask one targeted question rather than guessing.

---

## Strict KISS Rules - Non-Negotiable

One dashboard equals one objective.
Valid examples: API Health, DB Performance, Error Monitoring.
A multi-topic dashboard must be split.

### Forbidden
- More than 10 panels on one dashboard
- Multi-topic dashboards
- Complex PromQL/LogQL without justification
- Duplicate metrics displayed in multiple forms without purpose
- Decorative panels that drive no action

### Simplification Rules
- If a metric does not support a decision, remove it
- If it needs verbal explanation to be understood, it is too complex
- If an on-call SRE must think hard to parse it, design is poor
- Target 3 to 5 top KPIs max; keep details in drill-down views

---

## Dashboard Critic - Apply to Every Panel

Before adding or keeping any panel, answer all four questions:

1. Why does this metric exist?
2. Which incident can it detect?
3. What action does it trigger when abnormal?
4. Is it correlated to an existing SLO?

If one answer is unclear, remove or move the panel to a secondary debug dashboard.

During audits, classify panels as remove / review / justified.

---

## Readability Hierarchy - Standard Structure

```text
+-------------------------------------+
| TOP - KPI layer (3-5 max)           |
| Golden Signals for this service     |
+-------------------------------------+
| MIDDLE - Trend layer                |
| Time comparison, rates, evolution   |
+-------------------------------------+
| BOTTOM - Debug layer                |
| Breakdown by instance/endpoint/pod  |
+-------------------------------------+
```

Validation test: an on-call SRE must understand service state within 10 seconds using the TOP section only.

Panel templates: references/dashboard-templates.md

---

## Grafana Practice - Essential Only

- Structured JSON, versioned in Git, provisioned for critical dashboards
- Variables for env/service/namespace only when they reduce complexity
- Prefer simple, readable PromQL/LogQL
- Split over-complex queries into recording rules when needed
- Identify noisy panels with no clear threshold or action

Query cheatsheet: references/promql-logql-cheatsheet.md

---

## Smart Alerting - Tied to Dashboards

- Alert on SLO and burn rate, not arbitrary technical thresholds
- Use multi-window burn-rate alerts to balance speed and false positives
- One alert must map to one action
- Alert fatigue means too many non-actionable alerts and requires audit

---

## Anti-Patterns - Quick Review

| Anti-pattern | Correction |
|---|---|
| Everything-on-one-screen dashboard | Split by objective |
| Metric not tied to SLO | Remove or map to explicit SLO |
| Random threshold alerts | Replace with SLO/burn-rate logic |
| Over-complex undocumented query | Simplify or justify |
| Decorative non-actionable gauge | Remove |
| Dashboard not updated after incidents | Review after every postmortem |

---

## What This Skill Produces

Creation - structured dashboard (JSON or panel blueprint) with top/middle/bottom hierarchy and clear metric intent.

Audit - panel-by-panel review using Dashboard Critic with keep/remove guidance.

Simplification - overloaded dashboard refactored into a clean, incident-friendly version.

Always respond in English unless explicitly asked otherwise.
