# Frontend testing and performance

Read this reference when choosing validation depth or addressing a measured frontend bottleneck.

## Test by risk

- Use unit tests for deterministic transformations and local state transitions.
- Use component or integration tests for rendering, interaction, accessibility roles, and boundary behavior.
- Use browser tests for critical journeys, routing, storage, real network behavior, and regressions that depend on layout or browser APIs.
- Prefer assertions on user-visible behavior over implementation details and fragile snapshots.

For a defect, reproduce the failure before fixing it when practical and add the narrowest test that would have caught it.

Choose checks from the actual risk rather than running every test category by default:

| Change | Most useful evidence |
|---|---|
| Pure formatting or deterministic mapping | Small input/output test including meaningful boundary data |
| Form or control behavior | Role/name-based interaction test plus keyboard and error recovery |
| Request race or mutation ordering | Controlled response ordering and assertions on final visible state |
| Routing, auth transition, storage, or hydration | Browser journey with realistic session and navigation behavior |
| Visual or responsive change | Comparison to the accepted reference at layouts where content is under pressure |

Mock the network boundary when it enables controlled failures; avoid mocking away the state transition under test. Confirm fixtures against the real schema or an agreed contract. An accessibility scanner can find a subset of issues, but cannot establish that focus order, announcements, and task completion are usable.

## Browser evidence

Inspect console errors, failed requests, focus order, keyboard operation, responsive layout, and relevant accessibility output. Use screenshots for visual comparison only when they have a stable source of truth and review process.

Exercise the consequential recovery path as well as the happy path: failed save and retry, expired session, empty search, or unavailable dependency as relevant. Record environment and representative data. If browser access is unavailable, state which behaviors remain unverified and provide reproducible steps instead of claiming visual or accessibility validation.

## Performance

Measure the affected journey with representative data and device/network conditions. Attribute delay to server response, transfer, parsing, rendering, scripting, layout, or third-party work before optimizing. Recheck user-visible metrics and functional behavior after the change.

Compare equivalent conditions before and after; distinguish cold load, warm navigation, and interaction delay. For repeated requests, inspect cache identity and effect ownership before adding rendering optimizations. For large lists, measure actual data volume and interaction requirements before virtualization, then verify focus, search, and accessible reading behavior. Avoid unsupported numeric performance claims from one run.
