# Interface quality

Read this reference when implementing interactive UI, forms, navigation, or responsive layouts.

## Interaction and accessibility

- Start with semantic elements, associated labels, useful headings, visible focus, and predictable tab order.
- Use ARIA to express semantics that native elements cannot provide, not to recreate built-in controls unnecessarily.
- Keep destructive, irreversible, and privileged actions visually distinct and confirm them in proportion to their consequence.
- Announce asynchronous status changes when a screen-reader user would otherwise miss them. Move focus only when the interaction establishes a clear new context.
- Support keyboard, pointer, zoom, text resize, reduced motion, and sufficient contrast at the level required by the product and applicable standard.

## Forms and errors

- Preserve user input after recoverable failures.
- Put field-specific errors near the field and provide a useful summary when several errors need attention.
- Do not rely on color alone. Explain how to recover without exposing internal details.
- Prevent duplicate submission where it causes harm, but do not disable recovery or retry indefinitely.

## Responsive behavior

Choose breakpoints from content pressure and existing project tokens rather than device names. Test narrow, intermediate, and wide layouts, plus unusually long labels, translated text, empty content, and dense realistic data when relevant.
