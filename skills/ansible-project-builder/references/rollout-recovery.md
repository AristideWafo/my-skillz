# Partial rollout and recovery

Read when changing running services, shared state, cluster membership, or recovering an interrupted play. A local variable correction does not require this workflow.

## Establish the unit of change

Record the intended inventory, revision, effective configuration, and host selection before mutation. Resolve dynamic inventory near execution; compare the resulting host set with the authorized scope without printing secret variables.

Distinguish per-host work from shared operations such as a load-balancer update, database migration, or credential rotation. A task delegated to one host is not necessarily safe to repeat, and a controller failure can leave its completion unknown. Use a durable completion marker or query the authoritative system before replaying shared work.

Choose a batch from remaining service capacity and failure domains. Preserve quorum and avoid taking every replica in one failure domain out at once. A nominally small batch can still remove the only writable primary or a unique service instance.

## Model the transitions

For a disruptive service update, adapt this sequence to the actual runtime:

1. Confirm prerequisites and the candidate configuration before taking capacity away.
2. Drain or isolate the selected instance if the service requires it.
3. Apply and activate the change.
4. Verify the real service through its expected client path.
5. Return capacity only after that verification succeeds.

Define which transition is reversible and the evidence needed before starting the next batch. A process being active is insufficient if it cannot reach its database or has not rejoined its cluster. Avoid automatic continuation when health evidence is unavailable.

## Failure decisions

| Observed state | Next action | Avoid |
|---|---|---|
| Candidate validation fails before activation | Preserve the running configuration; correct the candidate | Reloading in an unconditional cleanup block |
| Activation fails after changing files | Determine running versus on-disk version; restore a compatible known-good configuration when authorized | Assuming a successful file copy means a healthy service |
| Controller loses contact during mutation | Reconnect and inspect state before retrying | Treating timeout as evidence that nothing happened |
| Some hosts succeed and others fail | Freeze further batches, group hosts by observed state, recover the affected cohort | Re-running destructive tasks on healthy hosts |
| Recovery succeeds but rollout failed | Report recovered service and failed rollout separately | Converting recovery into a successful deployment result |
| Data or cluster state is incompatible with old binaries | Stop automatic reversal and use the planned recovery or forward-fix path | Restoring old packages merely because they are available |

Rescue and cleanup paths are not transactions. Review what they do for the project's supported Ansible version, especially for unreachable hosts, handler execution, tags, and nested blocks. Preserve the original failure and the recovery result in the final report.

## Safe resumption

Prefer reconciling desired state through idempotent tasks over skipping directly to a late task. Skipping can omit prerequisite facts, validation, registration, or notifications. If a targeted resume is necessary, prove those prerequisites for the selected hosts.

For retried imperative operations, define a state query, bounded retry count, and termination condition. Do not use a file marker that can be written before the operation actually commits. Confirm that an asynchronous operation has stopped or completed before launching its replacement.

Check mode may omit or predict effects differently from a real run. Review secret-bearing diffs before enabling them and use disposable targets for mutation tests.

## Evidence to collect

For a material rollout, retain revision, host cohort, changed/failed/unreachable status, activation result, health result, and recovery result. Keep credentials and rendered secrets out of this evidence. State any host whose final state remains unknown.

Useful tests in disposable targets include failure before activation, failed health verification, loss of contact during a mutation, recovery followed by rerun, and a second successful convergence with no unexpected changes. Choose the cases connected to the changed behavior; do not provision a fleet for a documentation-only edit.
