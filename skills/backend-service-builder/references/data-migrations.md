# Data migrations

Read this reference when changing schemas, stored representations, indexes, ownership, or retention.

## Plan

Inspect data volume, write rate, engine and version, lock behavior, replicas, backup and restore evidence, application compatibility, and the repository's migration tooling.

Prefer expand-and-contract when old and new application versions overlap:

1. add a backward-compatible representation;
2. deploy code that can tolerate the mixed state;
3. backfill in bounded, observable batches;
4. verify correctness and lag;
5. switch reads or ownership;
6. remove the old representation only after rollback no longer depends on it.

This is a pattern, not a ceremony. A small transactional migration may be safer when its lock and rollback behavior are known.

## Backfill correctness

Choose a stable cursor or key range and a durable checkpoint. Make rerunning a batch safe. If live writers can change a row after it was read, use conditional updates, version checks, or a reconciliation pass so the backfill cannot overwrite fresher data. Define how deletes and newly inserted rows are handled.

Verify more than row counts: compare representative values, nulls, duplicates, constraints, and application reads, using bounded checks on large datasets. Separate data mismatch from expected replication lag. Set batch size and pacing from measured load and lock duration.

## Compatibility and recovery

Check old-code/new-schema and new-code/mixed-data combinations that will exist during deployment. Delay destructive column or representation removal until old workers, scheduled jobs, and rollback versions no longer depend on it.

Distinguish application rollback from data recovery. Reverting code does not reverse a lossy transformation or undo newly accepted writes. For irreversible steps, state the point after which recovery needs a restore, forward repair, or reconciliation, and identify the evidence required before crossing it. Verify engine/version-specific DDL and transactional behavior against primary documentation before choosing migration commands.

## Safety

Avoid unbounded table rewrites, one-shot backfills, silent truncation, and destructive cleanup without authorization. Define pause and abort criteria, monitor saturation and replication impact, and verify backups through a recovery path proportional to the data risk.
