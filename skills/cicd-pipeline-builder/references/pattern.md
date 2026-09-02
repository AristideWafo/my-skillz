# Delivery and rollback decisions

Read this reference when choosing a deployment or release pattern.

## Start from constraints

Establish these facts before selecting a strategy:

- Can old and new application versions run concurrently?
- Are API, event, and database changes backward compatible?
- Can traffic be shifted gradually and observed by version?
- How quickly must rollback complete?
- Is rollback safe after a schema or data change?
- What extra capacity and operational complexity are acceptable?

## Strategy selection

| Strategy | Prefer when | Avoid or adapt when |
|---|---|---|
| Rolling | Mixed versions are compatible and incremental replacement is acceptable | A mixed-version window breaks contracts or rollback is slow |
| Blue-green | Fast environment-level switch and extra capacity are available | Stateful cutover or schema changes make switching back unsafe |
| Canary | Traffic can be segmented and version-specific health is observable | Volume is too low for reliable comparison or routing cannot isolate risk |
| Feature flag | Release timing must be separated from deployment | Flag lifecycle and ownership cannot be maintained |
| Recreate | Downtime is acceptable and simplicity is more valuable than continuity | Availability objectives prohibit an outage |

Do not add progressive delivery machinery to a low-risk system unless the reduced deployment risk justifies its operating cost.

## Compatibility sequence

For APIs, events, and schemas, prefer expand-and-contract:

1. Add backward-compatible capability.
2. Deploy producers and consumers that tolerate both forms.
3. Migrate or backfill with bounded, observable work.
4. Verify old usage has stopped.
5. Remove the obsolete form in a later deployment.

Treat irreversible data transformations as a separate change with backups, validation, and an explicit recovery decision.

## Rollback design

Define rollback before production deployment:

- trigger signals and evaluation window;
- operator or automated owner;
- artifact or configuration to restore;
- data compatibility after restoration;
- maximum acceptable rollback time;
- verification that user-facing impact has recovered.

Rollback is not always the safest response. A forward fix may be preferable after an irreversible migration or when reverting would reintroduce a security defect. State that decision explicitly.

## GitOps

Use GitOps when reconciliation, auditability, drift control, and declarative rollback match the operating model. Keep build credentials out of the deployment reconciler, and keep cluster credentials out of ordinary CI jobs. Do not add GitOps solely to avoid writing a small deployment job.

## Production authorization

Designing or editing a deployment workflow does not authorize executing it. Before a live release, verify the requested environment, artifact identity, approval state, maintenance window, and rollback owner.
