# Reliability operations

Read this reference for incident management, recovery, capacity, chaos, and reliability investment.

## Incident roles and state

For incidents requiring coordination, establish an incident lead, operations owner, communications owner, shared channel, and timestamped state document. Small incidents do not need a heavyweight structure, but ownership and next action should remain clear.

Prioritize reversible mitigation and user impact. Preserve evidence where possible, but do not keep an outage running solely to find root cause.

## Post-incident work

Record impact, detection, timeline, mitigation, contributing conditions, what helped or delayed response, and owned actions. Prefer actions that change the system or process over reminders to be more careful.

An action is useful when it has an owner, due date, verification method, and a risk reduction tied to the incident.

## Disaster recovery

Define service-specific RTO and RPO before choosing replication or backup architecture. Test restoration, credentials, dependencies, DNS/traffic switch, and operator access—not only backup creation.

A recovery plan is incomplete until a representative restore has been timed and validated.

## Capacity

Use demand, saturation, queueing, dependency limits, growth, and failure headroom. CPU alone is not a capacity model. Separate average demand from peaks and consider how redundancy changes usable capacity during maintenance or failure.

## Chaos and resilience tests

Run experiments to validate a stated hypothesis, with bounded blast radius, abort criteria, observability, and owner authorization. Start in the safest representative environment. Do not use chaos as a substitute for known missing backups, limits, or failover tests.

## Reliability investment

Prioritize work using user impact, recurrence, detection gap, mitigation time, engineering cost, and operational burden. Error budgets can inform the tradeoff when a meaningful SLO exists; they need not be forced onto every internal tool.

## Cost

Treat cost as an operational signal alongside reliability. Attribute major spend, identify idle or overprovisioned capacity, and verify that optimization does not remove required failure headroom or retention.
