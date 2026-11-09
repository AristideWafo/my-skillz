# Query contracts and validation

Read for derived metrics, multi-instance dashboards, variable-driven panels, or reviews where rendered values could mislead an operator.

## Define the signal before the expression

For each consequential panel, establish metric type, source and freshness, included population, retained dimensions, time window, unit, aggregation, and missing-data meaning. A compact note beside the query or an existing panel description is enough; do not require a separate specification for every panel.

Confirm the real label schema and datasource scope. A UI variable is a filter, not a tenant authorization boundary. Do not invent metric names or datasource identifiers when only a mockup is available; provide an explicitly unvalidated template or resolve the missing contract.

## Aggregation traps

| Situation | Required reasoning |
|---|---|
| Fleet error ratio | Sum eligible failures and requests over matching populations and windows, then divide. An unweighted mean of instance ratios changes the question. |
| Fleet latency | Retain an aggregatable distribution and compatible boundaries. Instance percentiles cannot generally be averaged into a fleet percentile. |
| Counter restarts | Account for resets at the source-series level before aggregation; check the actual query language and metric type. |
| Joining metadata | Establish one-to-one or intended many-to-one cardinality. Duplicate join keys can multiply or invalidate results. |
| Gauge totals | Decide whether sources partition work or duplicate the same state. Adding replicated observations can double-count. |
| Time comparison | Keep time zone, range, sampling resolution, and population comparable; explain deploy or collection changes. |

Example fixture: instance A serves 100 requests with 10 failures; instance B serves 900 with zero failures. The fleet failure ratio is 10/1000 = 1%, not the mean instance ratio of 5%. Check the panel after transformations, not only the raw query.

## Missing values carry meaning

Differentiate:

- observed zero failures with positive request volume;
- no traffic, where a failure ratio may be undefined;
- expected target missing or scrape/collection delayed;
- query or datasource failure;
- a series that legitimately does not exist for the selected feature or environment.

Do not replace all missing values with zero or green. Only fill gaps where the source contract establishes the meaning; retain an independent freshness or availability signal when absence could hide failure. A denominator guard that suppresses division errors must not silently redefine unknown as healthy.

## Variables, links, and transformations

Exercise default, single, multi, all, and empty selections where supported. Verify escaping in the target query language, chained-variable refresh, and whether a broad all-selection exceeds the intended scope or query cost. Use datasource-supported parameter handling; do not concatenate unchecked input into executable queries.

Check field reductions, joins, filters, unit scaling, and threshold overrides after rendering. A "last" value can be old; a total can change with the selected time range. Links should carry relevant service, environment, and time context without carrying credentials or granting access.

## Validation ladder

1. Parse the artifact and compare its model with the target version and an existing working dashboard.
2. Evaluate queries against representative fixtures or available data: normal load, an error spike, unequal traffic, a counter reset, no traffic, a missing target, and invalid variable combinations as relevant.
3. Verify displayed values, labels, units, thresholds, empty states, and drill-downs in the target or a representative Grafana instance.
4. Measure query duration and returned-series count for the largest intended selection; reuse recording rules when a demonstrated recurring cost justifies them.

Use existing rule-testing tools when present. If the datasource or UI is unavailable, report exactly which stages were static and which remain unverified; do not claim a dashboard works because its JSON parses.
