---
name: frontend-application-builder
description: Build, extend, or debug production frontend applications and user interfaces while preserving the project's framework, design system, accessibility, and testing conventions. Use for concrete browser-facing implementation; use architecture or backend guidance when the primary work is system design or server behavior.
---

# Frontend Application Builder

Deliver a usable interface that fits the existing product and remains understandable under loading, failure, empty, and success conditions.

## Workflow

1. Inspect the framework, package manager, routing, state and data-fetching patterns, design system, browser support, tests, and nearby components before choosing an implementation.
2. Establish the user goal, affected journey, data contract, visual source of truth, responsive targets, accessibility needs, and acceptance criteria from available evidence. Ask only for material unknowns.
3. Reuse coherent components, tokens, layouts, and interaction patterns. Introduce a new abstraction only when repeated behavior or a real boundary justifies it.
4. Implement the smallest complete user-facing slice, including relevant loading, empty, error, disabled, optimistic, and success states.
5. Validate behavior at representative viewport sizes and input methods. Run project-native type, lint, unit, component, and end-to-end checks in proportion to the change.

## Decision rules

- Preserve the chosen framework and design system unless the task explicitly includes migration or a demonstrated defect requires change.
- Prefer semantic HTML and native browser behavior before adding custom interaction code.
- Keep server state, durable client state, URL state, and ephemeral component state distinct. Do not add a global store for local state.
- Treat the API schema as a contract. Do not silently invent fields, permissions, or error semantics; surface unresolved contract changes to the backend owner.
- Preserve deep links, keyboard navigation, focus behavior, browser history, and form data when the user journey depends on them.
- Optimize measured bottlenecks. Avoid memoization, code splitting, virtualization, or dependency additions without a plausible benefit and validation path.
- Never place secrets or privileged authorization decisions in browser code. Treat client-side checks as user experience, not a security boundary.

## Read references selectively

- Interaction, accessibility, forms, and responsive behavior: [references/interface-quality.md](references/interface-quality.md)
- Testing, browser validation, and performance: [references/testing-and-performance.md](references/testing-and-performance.md)

## Validation and done

The change is done when the intended journey works with representative data, failure and empty states are deliberate, keyboard and focus behavior are usable, responsive layouts remain coherent, client/server contracts agree, relevant tests pass, and no avoidable console, network, accessibility, or hydration errors remain.

Report what was validated in a real browser and what was only checked statically.
