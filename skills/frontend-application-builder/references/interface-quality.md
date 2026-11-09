# Interface quality

Read this reference when implementing interactive UI, forms, navigation, or responsive layouts.

## Interaction and accessibility

- Start with semantic elements, associated labels, useful headings, visible focus, and predictable tab order.
- Use ARIA to express semantics that native elements cannot provide, not to recreate built-in controls unnecessarily.
- Keep destructive, irreversible, and privileged actions visually distinct and confirm them in proportion to their consequence.
- Announce asynchronous status changes when a screen-reader user would otherwise miss them. Move focus only when the interaction establishes a clear new context.
- Support keyboard, pointer, zoom, text resize, reduced motion, and sufficient contrast at the level required by the product and applicable standard.

For a dialog, verify the initial focus target, keyboard containment where appropriate, dismissal behavior, and return focus. If the opener was removed, choose a logical surviving destination. Avoid treating every popup as a modal: choose the existing interaction pattern that matches the user's task.

For custom composite controls such as tabs, menus, or listboxes, inspect the applicable established keyboard pattern and existing component behavior before adding handlers. A click handler plus `tabindex` is not proof of keyboard equivalence. Use native controls where their behavior meets the requirement.

Keep status announcements useful and bounded. Announce a completed search or save when needed; do not announce every keystroke, rerender, or background polling cycle. Visual loading indicators need an understandable accessible state without repeatedly stealing focus.

## Forms and errors

- Preserve user input after recoverable failures.
- Put field-specific errors near the field and provide a useful summary when several errors need attention.
- Do not rely on color alone. Explain how to recover without exposing internal details.
- Prevent duplicate submission where it causes harm, but do not disable recovery or retry indefinitely.

Define when validation appears: avoid showing a field as invalid before the user has had a reasonable chance to complete it. Connect labels, hints, and errors programmatically; preserve the user's cursor and draft when server validation returns. On submit failure, bring the relevant error into view or focus using the established form pattern. For long or multi-step forms, ensure the user can locate errors outside the current section.

Use input types and autocomplete hints that match the data and supported platform behavior. Test values that look numeric but are identifiers, and date/time inputs where locale or timezone changes meaning. Client validation improves feedback; the server remains responsible for accepted data and authorization.

## Responsive behavior

Choose breakpoints from content pressure and existing project tokens rather than device names. Test narrow, intermediate, and wide layouts, plus unusually long labels, translated text, empty content, and dense realistic data when relevant.

Check that sticky controls, overlays, and virtual keyboards do not obscure the focused element or the action needed to recover. Preserve reading and focus order when rearranging layouts. For data tables, choose overflow, column priority, or an alternative presentation based on the user's comparison task rather than hiding essential fields to fit a screenshot.
