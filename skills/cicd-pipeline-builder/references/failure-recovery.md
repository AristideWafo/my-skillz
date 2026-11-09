# Delivery failure and recovery

Read when a workflow publishes, deploys, migrates, or coordinates competing runs. For validation-only jobs, use the relevant small subset.

## Give each side effect an identity

Track candidate commit, artifact digest, destination, configuration revision, and operation/run identity across jobs. A job display name or mutable tag cannot distinguish two candidates. Promotion should reference the tested artifact rather than silently rebuilding it with possibly different dependencies.

When consuming an artifact from another job or workflow, establish its producer and trust level. A valid digest proves byte identity, not that the producing code was trusted. Prevent a low-trust build from supplying scripts or deployment metadata to a privileged executor without the intended verification boundary.

## Decide retry behavior per operation

| Operation | Replay decision |
|---|---|
| Deterministic tests or configuration validation | Fix the failure; repeated runs do not make a failed check reliable |
| Download or registry read | Bounded retries with timeout and useful error context |
| Publish an immutable release | Query whether the same identity already exists; accept only matching content |
| Deployment request with unknown response | Query deployed/queued state before submitting again |
| Database migration | Use the application's migration ownership and completion mechanism; inspect partial state |
| Notification or external ticket creation | Deduplicate if supported; do not replay the entire release just to resend it |

Choose a finite retry budget and a state at which human or external recovery is necessary. A network timeout is an unknown outcome, not a rollback.

## Concurrency and cancellation

Separate replaceable validation work from stateful production work. Cancelling an obsolete test run is often appropriate; cancelling a deployment can leave capacity drained, a migration running, or a release partially published.

Define the concurrency boundary from the resource being changed, such as service plus environment. Serializing only by branch can allow two branches to mutate the same production resource. Locks need observable ownership and recovery for abandoned runs; do not add a distributed lock service if the platform's existing control suffices.

Before promotion, verify the run is still the intended candidate. Define whether newer candidates supersede older ones and prevent an older delayed approval from unexpectedly replacing a newer deployment. Bind approvals to the candidate and environment according to the actual platform's behavior.

Cleanup should release temporary resources and preserve evidence. It must not delete persistent data, declare success after failure, or automatically send traffic to a version that failed verification.

## Migration and rollback compatibility

Inspect the complete state that reverting binaries would encounter: schema, transformed data, queued events, configuration, flags, and credential compatibility. A previously healthy image may no longer be compatible with that state.

For staged changes, record the earliest and latest compatible application versions at each step. Delay destructive contraction until old producers and consumers have stopped and the rollback window is intentionally closed. A backup is a recovery option only if restoration time and data loss fit the service objective; do not describe it as instant rollback.

Use a forward fix or isolation plan when reversal would corrupt data or restore a known vulnerability. Preserve the failed candidate and evidence for diagnosis rather than overwriting its release identity.

## Verification that can reject a bad rollout

Define the observed signal, comparison baseline, minimum evidence, observation window, and response. Use representative user behavior alongside process health when a release can pass health checks yet fail its purpose. Low request volume or missing telemetry is inconclusive rather than a clean canary.

Select thresholds from the service's normal variation and objective; do not invent universal percentages. A threshold breach should identify whether the workflow halts, reverts a compatible artifact, or calls for intervention. Record who or what owns that action.

## Test the transitions

Use a stub publisher/deployer or isolated environment when possible. Exercise only meaningful transitions for the change:

- failed or skipped prerequisite cannot authorize publication or deployment;
- partial publication followed by retry neither overwrites a different release nor duplicates effects;
- cancellation during deployment leaves an identifiable state and recovery path;
- two candidates cannot accidentally race on the same environment;
- missing health data does not count as success;
- migration compatibility prevents an unsafe binary rollback;
- the recorded deployed digest matches the approved and verified digest.

Report configuration checks separately from actual platform execution. Required-check behavior, environment approvals, runner identities, and cancellation semantics must be verified on the target platform; repository syntax alone does not establish them.
