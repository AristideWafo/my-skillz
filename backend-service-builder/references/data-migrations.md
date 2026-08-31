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

## Safety

Avoid unbounded table rewrites, one-shot backfills, silent truncation, and destructive cleanup without authorization. Define pause and abort criteria, monitor saturation and replication impact, and verify backups through a recovery path proportional to the data risk.
