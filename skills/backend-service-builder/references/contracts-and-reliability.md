# Contracts and reliability

Read this reference for externally visible APIs, asynchronous work, or dependency calls.

## API boundary

Specify required and optional fields, validation, authorization, success and error shapes, pagination or streaming behavior, and compatibility expectations. Avoid returning internal database or framework objects as accidental public contracts.

For changed fields, distinguish omitted, null, empty, and default values. Inspect existing consumers before changing enum values, ordering, numeric precision, timestamp zones, or error codes. For pagination over changing data, define stable ordering and tie-breakers; do not promise a snapshot unless the implementation provides one. Bound page size and serialization cost.

## Dependency calls

Set explicit timeouts, classify retryable failures, add jittered bounded retries only where repetition is safe, and propagate cancellation when the framework supports it. A circuit breaker or cache is justified by an observed failure mode and clear stale-data behavior, not by default.

Allocate dependency time within the caller's total deadline. Check whether a client library, proxy, job runner, and application each retry: their combined attempts can multiply load. Honor supported server retry guidance, distinguish overload from permanent validation failure, and stop retrying when the budget is exhausted. Cancellation should release resources where possible, but does not prove an external write was canceled.

For caches, define key scope, invalidation, maximum tolerated staleness, and behavior during a miss storm. Use stale results only when the business and authorization semantics permit them.

## Asynchronous work

Define delivery semantics, deduplication or idempotency, ordering needs, poison-message handling, retry budget, and observability. Acknowledgement should reflect the system's actual durability boundary.

Observe queue age and exhausted retries as well as throughput. If strict ordering matters, specify its scope and how poison messages affect later work. Include a safe replay procedure that preserves the original operation identity.

## Concurrency

Identify the resource or invariant shared across requests. Use database constraints, conditional writes, transactions, locks, or serialization at the narrowest reliable boundary. Add a test that can fail under the previous race rather than relying only on code inspection.
