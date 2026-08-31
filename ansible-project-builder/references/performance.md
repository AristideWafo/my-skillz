# Ansible performance decisions

Read this reference only when scale or runtime is an observed problem.

## Measure first

Capture total runtime and identify whether time is spent in connection setup, fact gathering, package metadata, file transfer, slow modules, serial constraints, or target-side work. Do not tune `forks` from host count alone.

## Levers

- **Forks**: increase only within controller CPU/memory, network, bastion, and target limits.
- **Pipelining and connection reuse**: useful when compatible with privilege escalation and security policy.
- **Fact gathering**: disable or subset facts for plays that do not use them; use caching when cross-host or repeated facts justify the operational dependency.
- **Serial batches**: choose from service capacity and rollback needs, not a universal percentage.
- **Async operations**: use for independent long-running tasks when result collection and failure handling remain reliable.
- **Package operations**: avoid refreshing metadata repeatedly across several tasks.
- **Templates and loops**: reduce repeated expensive lookups and controller-side computation when profiling shows they matter.

## Cache safety

Fact caches can contain topology and sensitive data. Define access control, retention, availability, invalidation, and failure behavior before introducing Redis or another shared service.

## Validation

Compare representative before/after runs with the same inventory slice and task path. Confirm that faster execution did not increase failure rate, overload dependencies, leak data, or make rollbacks unsafe.
