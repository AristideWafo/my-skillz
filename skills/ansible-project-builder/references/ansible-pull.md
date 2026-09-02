# Ansible pull-mode decisions

Read this reference when hosts fetch and apply configuration themselves.

## Use pull mode when it fits

Pull mode can fit intermittently connected, inbound-SSH-restricted, edge, or autoscaled nodes that can authenticate to a configuration source. It adds distributed scheduling, credential, observability, and rollout responsibilities; it is not automatically better at a particular host count.

## Required design decisions

- immutable revision, signed release, or controlled channel to apply;
- host identity and least-privilege source access;
- secret retrieval that does not place decryption material in the repository;
- lock preventing concurrent local runs;
- jitter and backoff to avoid synchronized load;
- bounded timeout and failure handling;
- local log retention plus centralized success/failure signal;
- rollout rings or staged channels;
- recovery to a known-good revision.

Do not track a mutable production branch without a deliberate promotion and rollback model.

## Wrapper behavior

A wrapper should acquire a local lock, fetch the approved revision, verify integrity if required, run with a bounded timeout, preserve useful logs, emit the applied revision and result, and release the lock on every exit path.

Avoid automatically retrying a deterministic configuration failure in a tight loop. Use backoff and keep the previous known-good service state where possible.

## Monitoring

Track at least last attempt, last success, applied revision, duration, and result per node or cohort. Alert thresholds should derive from the expected run interval and service risk rather than a fixed one-hour rule.

## Validation

Test concurrent invocation, unreachable source, invalid revision, expired identity, secret lookup failure, partial task failure, reboot, and rollback. Verify that a failed run cannot silently report success.
