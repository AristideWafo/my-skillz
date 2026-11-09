# Asynchronous state and API contracts

Read when changing fetching, search, navigation, autosave, optimistic updates, account switching, or persistent client caches. Reuse the framework's established data layer before inventing request orchestration.

## Requests have identity

Tie each result to the query parameters, resource, and security context that requested it. When the user changes the query or navigates away, abort obsolete work where supported and prevent stale completions from committing state. A response may already have arrived or a callback may continue after abort; use the data layer's supported identity or sequencing mechanism as needed.

Cache keys must include every dimension that changes the answer, including tenant or user where applicable. On logout or account switch, prevent previous-context results and cached privileged data from appearing. Inspect server-rendered initial data and persistent storage as well as in-memory caches.

Debouncing reduces requests but does not by itself solve response ordering. Do not clear useful existing data merely because a background refresh begins; distinguish initial loading, refreshing, empty success, and failed refresh when it helps the user.

## Mutations and uncertain results

| Situation | Decision |
|---|---|
| Cheap reversible change with a clear server contract | Optimistic UI may be appropriate; reconcile with the returned canonical value |
| Irreversible or high-consequence effect | Keep status truthful; show pending or uncertain state until the authoritative result is known |
| Timeout after submission | Do not assume failure; reconcile status or retry using the same logical operation identity when supported |
| Older mutation fails after a newer one succeeds | Roll back only the older change, or refetch/reconcile; do not restore an entire stale snapshot |
| User changes data while a save is pending | Track the submitted revision separately from the current draft; a save completion must not mark unsaved edits as saved |

Prevent accidental duplicate submission in the UI, but require server-side idempotency where duplicate durable effects matter. Preserve the original key across retries of the same logical operation when the API supports it. If safe reconciliation requires an absent endpoint or contract, report that gap rather than inventing success.

## Navigation, session expiry, and recovery

Preserve appropriate draft state across recoverable failures and login renewal, while respecting sensitive-data retention. Do not place confidential drafts or credentials in URLs or unrestricted persistent storage. Define the source of truth for filters and pagination so back/forward navigation and deep links remain coherent.

Check whether subscriptions, observers, timers, and streaming connections stop or change ownership when the route or account changes. Distinguish a disconnected stream from an empty result; reconcile missed updates using the application's supported cursor or refresh behavior.

## Rendered content and contract checks

Use actual schema or representative fixtures for optional fields, nulls, long text, large numbers, dates, and permission states. Rendering untrusted rich content requires the application's established sanitization policy; do not bypass escaping to make a fixture look correct. Validate destination schemes and existing navigation policy for externally supplied links.

For server rendering, inspect browser-only APIs, locale/time assumptions, and initial data consistency when hydration differs. Do not hide hydration warnings as a substitute for finding the mismatch.

## Targeted tests

Force request B to complete before request A, then assert that B stays visible. Test switching accounts during a pending request. For optimistic writes, force an older failure after a newer success. Test a save finishing after further edits, and a timeout followed by reconciliation. Control responses or clocks in tests instead of relying on arbitrary sleeps.
