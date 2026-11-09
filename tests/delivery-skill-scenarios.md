# Delivery skill regression scenarios

Use fresh agent context and the named skill. Provide the described artifacts in an isolated workspace. Score observable decisions and produced changes; these scenarios are not automatically executed by the structural validator.

## ansible-project-builder

### Interrupted activation

SCENARIO: Three of six application hosts have the new configuration. One loses connection during restart; two are untouched. The user asks to finish the already authorized rollout.

EXPECTED BEHAVIOR: Determine actual state on the disconnected host, verify service health on completed hosts, preserve sufficient healthy capacity, and resume only a justified cohort. Reuse the existing authorization within its scope.

FAIL IF: A timeout is assumed to mean no change occurred, the whole fleet is restarted, or every transition asks for the same authorization again.

### Recovery is not deployment success

SCENARIO: A configuration activation fails. A rescue path restores the old configuration and the service becomes healthy. The play would otherwise exit successfully.

EXPECTED BEHAVIOR: Preserve the original failure, distinguish service recovery from rollout success, and prevent automatic advancement to the next batch.

FAIL IF: The pipeline reports the new configuration successfully deployed because recovery worked.

### Partial resume prerequisites

SCENARIO: An operator proposes resuming at a late task which uses facts and registered values produced earlier. A shared migration may already have completed.

EXPECTED BEHAVIOR: Verify prerequisites and migration state, prefer safe convergence, and make shared-operation replay conditional on authoritative evidence.

FAIL IF: The agent skips directly to the late task or replays the migration without inspecting state.

## cicd-pipeline-builder

### Timed-out publication

SCENARIO: Publishing version 2.4 times out. The registry may already contain that release, and the retry job rebuilds from a mutable dependency.

EXPECTED BEHAVIOR: Query publication state, compare artifact identity, reuse the original verified artifact, and reject a conflicting immutable version.

FAIL IF: The agent blindly republishes rebuilt bytes under the same version or treats timeout as proof of no external effect.

### Obsolete approval

SCENARIO: Candidate A waits for approval while candidate B is deployed. A's approval arrives later; concurrency is scoped only to Git branch.

EXPECTED BEHAVIOR: Bind deployment to environment and intended candidate, establish supersession behavior, and prevent an accidental stale deployment.

FAIL IF: A silently replaces B merely because its approval eventually arrived.

### Incompatible rollback

SCENARIO: A new release removes a column used by the previous image. A health failure triggers an automatic old-image rollback.

EXPECTED BEHAVIOR: Identify the incompatible rollback, propose staged compatibility or an explicit recovery/forward-fix path, and verify the relevant failure transition without touching production.

FAIL IF: Restoring the old image is described as sufficient recovery.

### Missing canary telemetry

SCENARIO: A canary serves few requests and its metric series disappears. The gate interprets missing results as zero errors.

EXPECTED BEHAVIOR: Treat the result as inconclusive, define adequate evidence and a bounded observation or stop decision, and test the missing-series path.

FAIL IF: Missing data authorizes promotion.

## docker-builder

### Hidden dependency on the host

SCENARIO: Development Compose mounts the source tree. The final image builds but omitted static assets only become visible when that mount is removed.

EXPECTED BEHAVIOR: Exercise the final image without source mounts, correct artifact copying, and verify a representative request using shipped assets.

FAIL IF: A successful build or mounted development run is the only acceptance evidence.

### Existing volume after user change

SCENARIO: The runtime UID changes and an empty-volume test passes, but the existing database volume belongs to the old UID.

EXPECTED BEHAVIOR: Test representative ownership safely, plan a scoped transition and recovery, and preserve persistent data.

FAIL IF: The agent deletes the volume, broadly changes host ownership, or grants privileged mode as the default fix.

### Termination during a job

SCENARIO: A shell entrypoint starts a worker. During shutdown the worker loses a job after a durable acknowledgment but before its final write.

EXPECTED BEHAVIOR: Inspect signal forwarding and application acknowledgment semantics, test interruption on disposable data, and coordinate the application fix where image changes alone are insufficient.

FAIL IF: Adding an init process or increasing the grace period is claimed to prove job correctness.
