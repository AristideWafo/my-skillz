# Contracts and reliability

Read this reference for externally visible APIs, asynchronous work, or dependency calls.

## API boundary

Specify required and optional fields, validation, authorization, success and error shapes, pagination or streaming behavior, and compatibility expectations. Avoid returning internal database or framework objects as accidental public contracts.

## Dependency calls

Set explicit timeouts, classify retryable failures, add jittered bounded retries only where repetition is safe, and propagate cancellation when the framework supports it. A circuit breaker or cache is justified by an observed failure mode and clear stale-data behavior, not by default.

## Asynchronous work

Define delivery semantics, deduplication or idempotency, ordering needs, poison-message handling, retry budget, and observability. Acknowledgement should reflect the system's actual durability boundary.

## Concurrency

Identify the resource or invariant shared across requests. Use database constraints, conditional writes, transactions, locks, or serialization at the narrowest reliable boundary. Add a test that can fail under the previous race rather than relying only on code inspection.
