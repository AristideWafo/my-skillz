# PromQL and LogQL review guide

Read this reference for query design and review. Verify syntax and function behavior against the deployed Prometheus, Loki, and Grafana versions.

## PromQL

- Use rates for counters over a window appropriate to scrape interval and decision horizon.
- Preserve required labels explicitly when aggregating.
- Compare histogram quantiles only when bucket boundaries and aggregation are compatible.
- Decide whether missing series means zero, no traffic, scrape failure, or unknown before filling values.
- Avoid regex and joins over unbounded label sets without checking query cost.
- Use recording rules for repeated expensive expressions with clear ownership and tests.

Review questions:

1. Is the metric a counter, gauge, classic histogram, or native histogram?
2. Are numerator and denominator aggregated over the same labels and time window?
3. Can resets, sparse traffic, or missing targets distort the result?
4. Does the query preserve the dimensions the panel promises?
5. Is the range long enough for the event rate but short enough for the intended response?

## LogQL

- Filter streams with indexed labels before parsing line content.
- Parse only the fields needed for the question.
- Keep high-cardinality values in parsed fields rather than stream labels.
- Bound query time and volume; a broad regex across long retention can be expensive.
- Separate log-volume or error-rate metrics from exemplar lines when both are useful.

## Validation

Run queries against representative normal, failure, no-traffic, and missing-data periods. Check returned labels, units, cardinality, query duration, and whether dashboard transformations alter the meaning.
