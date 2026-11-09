# Concurrent writes and external effects

Read for shared counters, reservations, duplicate submissions, webhooks, queues, or writes spanning systems. Start from the invariant and the system's existing durability mechanism; do not introduce a queue or distributed lock merely to follow this reference.

## Choose the boundary that can enforce the invariant

| Failure | Candidate mechanism | Evidence to collect |
|---|---|---|
| Two requests create the same logical record | Unique constraint or equivalent conditional insertion | One durable record after simultaneous attempts; duplicate maps to a stable response |
| Two requests consume the last unit | Atomic conditional update, appropriate transaction, or serialized owner | Capacity never becomes negative; exactly one request succeeds |
| A stale editor overwrites newer data | Version comparison or conditional write | Stale update is rejected or merged under an explicit policy |
| Several records must change together | Transaction within the datastore's supported boundary | No externally visible partial state after injected failure |

Check the actual database's isolation and locking behavior before choosing syntax or claiming a guarantee. An in-memory lock cannot coordinate independent processes. A lock lease expiring while work continues requires a stale-owner strategy, such as a supported fencing mechanism; a timeout alone does not guarantee exclusive ownership.

## Define an idempotency contract

For commands that may be repeated, establish:

- Key scope: caller or tenant, operation, and logical attempt. Do not deduplicate unrelated commands globally.
- Payload identity: distinguish a replay from reuse of the same key for different input; reject incompatible reuse.
- Atomic claim: simultaneous requests cannot both become the owner through a check-then-insert race.
- State and response: distinguish in-progress, completed, and recoverable failure; replay the original result where the contract requires it.
- Retention: cover the supported replay window; describe behavior after expiration rather than promising indefinite deduplication.
- Recovery: if execution stops after claiming the key, define reconciliation or ownership recovery instead of leaving an eternal in-progress entry.

Disabling a UI button is useful interaction behavior, not server-side duplicate protection. A random key generated anew on every retry does not identify the same logical attempt.

## Cross-system writes

Draw the commit points before choosing a mechanism. A database commit and a remote payment or message publish normally do not share a transaction.

- If durable local state must cause eventual publication, consider the project's transactional outbox or equivalent recoverable mechanism. Test interruption after commit but before publish, and after publish but before marking completion.
- Expect repeated publication and consumption when delivery is at least once. Consumers still need a suitable deduplication or idempotent effect boundary.
- For a remote call with an ambiguous result, use the provider's supported idempotency or status lookup when available. Do not classify a timeout as proof of failure.
- Where partial success is permissible, expose it as a state with an owner and reconciliation path. Compensation is a new operation that may itself fail; it is not an automatic rollback of the original effect.
- Acknowledge a job only after the intended durability boundary. Bound retries and define who handles exhausted or poison messages.

## Prove the failure behavior

Use independent connections or workers and a synchronization barrier to force overlapping attempts; sleeps alone make race tests unreliable. Assert durable outcomes, not only response codes. Add interruption tests at the relevant commit boundaries, and test duplicate requests with both equal and different payloads. Keep tests local or in a designated test environment; do not create real external effects merely to demonstrate resilience.
