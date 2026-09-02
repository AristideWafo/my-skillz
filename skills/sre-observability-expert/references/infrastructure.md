# Infrastructure diagnosis

Read this reference when symptoms involve hosts, containers, Kubernetes, networks, cloud resources, or databases.

## Start from impact and recent change

Establish what is failing, for whom, since when, and what changed near that time. Compare affected and healthy instances when possible; a difference is often more useful than an isolated value.

## Evidence by layer

Use the cheapest relevant evidence first:

| Layer | Evidence |
|---|---|
| Service | user-visible errors, latency, request rate, dependency failures |
| Workload | events, restarts, exit reasons, resource use, probes, logs |
| Host | CPU pressure, memory and OOM, disk latency/capacity, process and cgroup state |
| Network | DNS result and timing, route, connection state, TLS handshake, packet loss |
| Dependency | saturation, pool/queue depth, error codes, timeouts, maintenance events |
| Change | deploy, configuration, secret/certificate, scaling, provider event |

Do not follow this table mechanically when a high-confidence signal points directly to a safer mitigation.

## Kubernetes

Distinguish startup, readiness, and liveness. A strict liveness probe can amplify overload; readiness should remove a workload from traffic without necessarily restarting it. Inspect events, scheduling, resource pressure, rollout history, and dependency health before increasing replicas.

Treat deletes, forced rollouts, node drains, scaling, and edits to shared controllers as production changes. Confirm namespace, context, target set, disruption budget, and recovery path.

## Containers and hosts

Before attaching `strace`, `perf`, a debugger, or a packet capture, estimate overhead and bound duration and output. Prefer a representative replica when possible. Verify the effective container limits rather than comparing process use only to host capacity.

## Network

Separate DNS, routing, transport, TLS, proxy/load balancer, and application behavior. Use packet capture only when cheaper evidence cannot distinguish hypotheses, and protect credentials and payload data in captures.

## Databases and queues

Check connection saturation, lock or queue wait, slow operations, storage latency, replication state, and recent schema/configuration changes. Avoid failover, index creation, vacuum/rebuild, queue purge, or data repair without identifying lock impact, backup/recovery, and ownership.

## Cloud

Inspect provider events, quotas, throttling, identity failures, regional dependencies, and managed-service metrics before adding new infrastructure. Choose provider-native or self-managed solutions from availability, control, cost, compliance, and operating burden—not from a universal preference.
