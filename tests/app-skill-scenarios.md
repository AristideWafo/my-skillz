# Application skill forward-test scenarios

Use each request with a fresh agent and only the named skill plus the described fixture. These are behavioral evaluation cases, not evidence that an automated evaluation has run. Judge artifacts and observable outcomes; do not require matching wording or a preferred implementation.

## backend-service-builder

### Concurrent final reservation

REQUEST: Fix occasional overselling in an endpoint that reads remaining capacity, then inserts a reservation and decrements capacity. The service runs with multiple workers. Supply a minimal database-backed fixture with capacity one and two independent request connections.

PASS: The solution protects the capacity invariant at a shared durable boundary, returns a defined loser response, and demonstrates overlapping attempts with one durable reservation and no negative capacity.

FAIL: It relies on a UI guard, in-process lock, or sequential test; it hides an exception after creating the duplicate effect.

### Ambiguous payment result

REQUEST: Make checkout retries safe when the provider accepts a payment but the connection closes before the response. Supply a fake provider that records the effect before timing out and supports lookup or idempotency.

PASS: The implementation preserves the logical operation identity, handles simultaneous repeats and incompatible key reuse, and reconciles interruption without a second charge.

FAIL: Every retry receives a new key, timeout means definitely unpaid, or an in-progress record can remain unrecoverable forever.

### Tenant cache isolation

REQUEST: Fix an export endpoint that authenticates the caller, authorizes the project on cache miss, and caches by project slug. Supply two tenants with equal slugs and an existing populated cache.

PASS: Access and cached data remain tenant-scoped on both hit and miss; denied requests produce no export or data disclosure. Tests cover cross-tenant cache reuse and legitimate access.

FAIL: Only the detail route is protected or an authorization error occurs after producing the export.

### Backfill races with live writes

REQUEST: Add a restartable backfill of a normalized field while the existing application continues changing source values. Supply a fixture that updates one source row between the batch read and write.

PASS: The newer value is preserved or deterministically reconciled, rerunning a batch is safe, and mixed-version compatibility and recovery limits are stated.

FAIL: A stale backfill overwrites newer data, only row counts are checked, or code rollback is claimed to reverse a lossy transformation.

## frontend-application-builder

### Search results arrive out of order

REQUEST: Fix a search screen where typing a second query sometimes shows results from the first. Supply controllable promises for queries A and B, completing B first.

PASS: B remains visible after A completes; useful pending/error behavior is retained and a deterministic regression test demonstrates the ordering.

FAIL: Debouncing alone is the fix, or a fixed sleep is used as evidence that the race disappeared.

### Newer edit survives older save failure

REQUEST: Fix optimistic autosave that restores a whole snapshot when any save fails. Supply two edits where the newer save succeeds before the older one fails.

PASS: The latest accepted value and any unsaved draft survive; status accurately reflects the submitted versus current revision. Recovery uses the actual API contract.

FAIL: The old snapshot erases the newer edit, a pending draft is marked saved, or an absent reconciliation endpoint is invented.

### Account changes during a request

REQUEST: Prevent an account-switching dashboard from briefly showing the previous account's data. Supply a cached result and a pending response for account A, then switch to B.

PASS: Both cached and late A data are prevented from appearing under B; the existing data layer is reused and legitimate B results still load.

FAIL: Only the current component is cleared while shared cache or late responses still leak A data.

### Dialog validation recovery

REQUEST: Make a settings dialog usable with a keyboard when server validation rejects a field below the fold. Supply the existing modal component and a form with preserved input, an error response, and a removable trigger.

PASS: The existing component is reused, error association and recovery are usable, input is preserved, focused controls remain visible, and closing returns focus to a logical surviving target. Browser evidence is distinguished from static checks.

FAIL: A second modal system is added, focus disappears, input is erased, or an automated scanner alone is claimed to prove full accessibility.
