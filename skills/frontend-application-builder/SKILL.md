---
name: frontend-application-builder
description: Implement or debug browser interfaces, forms, navigation, accessibility, and asynchronous UI behavior within the existing framework and design system. Use for concrete frontend work rather than server-side behavior or standalone architecture exploration.
---

# Frontend Application Builder

Deliver a usable interface that fits the existing product and remains understandable under loading, failure, empty, and success conditions.

## Workflow

1. Inspect the framework, package manager, routing, state and data-fetching patterns, design system, browser support, tests, and nearby components before choosing an implementation.
2. Establish the user goal, affected journey, data contract, visual source of truth, responsive targets, accessibility needs, and acceptance criteria from available evidence. Ask only for material unknowns.
3. Reuse coherent components, tokens, layouts, and interaction patterns. Introduce a new abstraction only when repeated behavior or a real boundary justifies it.
4. Implement the smallest complete user-facing slice, including relevant loading, empty, error, disabled, optimistic, and success states.
5. Validate behavior at representative viewport sizes and input methods. Run project-native type, lint, unit, component, and end-to-end checks in proportion to the change.

For an interaction change, identify the trigger, pending state, success, rejection, and recovery path. For a bug, reproduce the user-visible failure before altering component boundaries. Apply only the states the journey actually needs; do not add speculative UI or dependencies.

## Decision rules

- Preserve the chosen framework and design system unless the task explicitly includes migration or a demonstrated defect requires change.
- Prefer semantic HTML and native browser behavior before adding custom interaction code.
- Keep server state, durable client state, URL state, and ephemeral component state distinct. Do not add a global store for local state.
- Treat the API schema as a contract. Do not silently invent fields, permissions, or error semantics; surface unresolved contract changes to the backend owner.
- Preserve deep links, keyboard navigation, focus behavior, browser history, and form data when the user journey depends on them.
- Optimize measured bottlenecks. Avoid memoization, code splitting, virtualization, or dependency additions without a plausible benefit and validation path.
- Never place secrets or privileged authorization decisions in browser code. Treat client-side checks as user experience, not a security boundary.
- Associate asynchronous results with the current resource, query, and user context. Cancellation alone does not prevent every stale completion from updating the screen.
- Treat optimistic updates and retries as product semantics: preserve newer edits, reconcile uncertain outcomes, and avoid claiming success before the contract supports it.

## Read references selectively

- Interaction, accessibility, forms, and responsive behavior: [references/interface-quality.md](references/interface-quality.md)
- Testing, browser validation, and performance: [references/testing-and-performance.md](references/testing-and-performance.md)
- Fetch races, optimistic mutations, caches, and interrupted journeys: [references/async-state-and-contracts.md](references/async-state-and-contracts.md)

## Validation and done

The change is done when the intended journey works with representative data, failure and empty states are deliberate, keyboard and focus behavior are usable, responsive layouts remain coherent, client/server contracts agree, relevant tests pass, and no avoidable console, network, accessibility, or hydration errors remain.

Report what was validated in a real browser and what was only checked statically.

For a boundary change, report the API assumptions and whether they were checked against real schemas or representative fixtures. A visually correct mock is not evidence that authorization, persistence, or production data compatibility works.
