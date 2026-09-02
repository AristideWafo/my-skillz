# Measuring software delivery performance

Last reviewed: 2026-08-31 against DORA's five-metric model.

Read this reference when defining delivery measurements. Use the current [DORA metric history](https://dora.dev/insights/dora-metrics-history/) as the primary source when definitions may have changed.

## Five metrics

### Throughput

- **Change lead time**: elapsed time from a defined change point, commonly commit, to successful production deployment.
- **Deployment frequency**: frequency of successful production deployments for the service.
- **Failed deployment recovery time**: elapsed time from a deployment-caused impairment to restored service.

### Instability

- **Change fail rate**: proportion of production deployments that cause impairment and require remediation.
- **Deployment rework rate**: proportion of deployments that are unplanned work to correct a recent deployment.

Use consistent service, environment, and time-window definitions. Do not mix incidents unrelated to deployments into failed deployment recovery time.

## Event model

Prefer timestamped events over inferred counters:

```text
change {service, change_id, commit, started_at}
deployment {service, environment, artifact_digest, started_at, completed_at, result}
impairment {service, deployment_id, detected_at, restored_at}
rework {service, deployment_id, corrective_deployment_id}
```

Derive durations from paired timestamps. A ratio of alert counts is not a recovery-time metric.

## Example calculations

For a defined service and period:

```text
change_lead_time = successful_prod_deployment.completed_at - change.started_at
failed_deployment_recovery_time = impairment.restored_at - impairment.detected_at
change_fail_rate = impaired_prod_deployments / prod_deployments
deployment_rework_rate = corrective_prod_deployments / prod_deployments
deployment_frequency = successful_prod_deployments / period
```

Choose median and tail percentiles for duration distributions when averages hide outliers.

## Interpretation

- Compare a service to its own baseline before comparing teams.
- Segment by service and deployment model; aggregation can hide constraints.
- Use metrics to find bottlenecks, not as individual performance targets.
- Investigate definition or instrumentation changes before claiming improvement.
- Pair delivery metrics with user outcomes, reliability, and work sustainability.

The collection should not hard-code annual performance clusters as universal goals. If benchmarks are requested, retrieve the current report and explain its cohort and limitations.
