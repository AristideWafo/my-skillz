# Frontend testing and performance

Read this reference when choosing validation depth or addressing a measured frontend bottleneck.

## Test by risk

- Use unit tests for deterministic transformations and local state transitions.
- Use component or integration tests for rendering, interaction, accessibility roles, and boundary behavior.
- Use browser tests for critical journeys, routing, storage, real network behavior, and regressions that depend on layout or browser APIs.
- Prefer assertions on user-visible behavior over implementation details and fragile snapshots.

For a defect, reproduce the failure before fixing it when practical and add the narrowest test that would have caught it.

## Browser evidence

Inspect console errors, failed requests, focus order, keyboard operation, responsive layout, and relevant accessibility output. Use screenshots for visual comparison only when they have a stable source of truth and review process.

## Performance

Measure the affected journey with representative data and device/network conditions. Attribute delay to server response, transfer, parsing, rendering, scripting, layout, or third-party work before optimizing. Recheck user-visible metrics and functional behavior after the change.
