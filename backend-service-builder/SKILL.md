---
name: backend-service-builder
description: Build, extend, or debug backend services, APIs, jobs, and data access while preserving the project's architecture, contracts, security, and operational conventions. Use for concrete server-side implementation; use system-design guidance when the primary task is architecture exploration rather than code.
---

# Backend Service Builder

Deliver server behavior that is correct under normal use, failure, retries, concurrency, and operational recovery.

## Workflow

1. Inspect the runtime, framework, module boundaries, API style, data ownership, authentication and authorization model, migrations, jobs, tests, and operational signals before changing code.
2. Establish the caller, trust boundary, input and output contract, consistency needs, failure semantics, scale assumptions, and rollout constraints from available evidence.
3. Trace the real request or event path and preserve coherent project patterns. Introduce a new layer, service, datastore, queue, or dependency only for a demonstrated requirement.
4. Implement the smallest complete vertical behavior, including validation, authorization, errors, observability, and tests appropriate to the risk.
5. Verify the contract and important failure modes. For schema or externally visible changes, define compatibility, rollout, and rollback before release.

## Contract and data rules

- Validate untrusted input at the boundary and keep domain invariants in the layer that owns them.
- Make authentication, authorization, tenancy, and data ownership explicit. A valid identity is not automatically authorized for a resource.
- Preserve backward compatibility unless the user accepts a coordinated breaking change. Version only when coexistence or migration requires it.
- Define retry and idempotency behavior for operations that may be delivered more than once. Bound retries and use timeouts appropriate to the dependency.
- Keep transactions aligned with consistency boundaries. Do not hold them across slow network calls without a demonstrated need.
- Treat migrations as production changes: inspect volume, locks, defaults, backfill, mixed-version behavior, and recovery.

## Security and operations

- Keep credentials and sensitive data out of source, logs, traces, errors, fixtures, and generated examples. Use the project's secret mechanism.
- Use parameterized data access and established escaping or serialization libraries. Do not build executable queries from untrusted strings.
- Expose useful structured errors without leaking internals. Log enough correlation and ownership context to diagnose failures while respecting data policy.
- Add metrics or traces when they answer an operational question; avoid high-cardinality or sensitive attributes.
- Require authorization before destructive data operations, production migrations, live traffic changes, or irreversible external side effects.

## Read references selectively

- API boundaries, authorization, jobs, and dependency behavior: [references/contracts-and-reliability.md](references/contracts-and-reliability.md)
- Database changes and safe rollout: [references/data-migrations.md](references/data-migrations.md)

## Validation and done

The change is done when contracts are explicit, authorization and validation cover the actual trust boundary, relevant concurrency and failure behavior is understood, tests pass at the appropriate layers, operational signals are sufficient, and rollout or rollback is defined when compatibility or data is at risk.
