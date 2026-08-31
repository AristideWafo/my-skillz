# Agent routing

Use specialized agents when a task has independent workstreams, needs isolated context, or benefits from an independent review. Handle small, tightly coupled changes directly.

- `solution-architect`: read-only cross-boundary design before implementation when contracts or non-functional requirements are unresolved.
- `frontend-implementer`: browser-facing implementation using `frontend-application-builder`.
- `backend-implementer`: server-side implementation using `backend-service-builder`.
- `platform-release-engineer`: delivery and operations work routed through the relevant existing DevOps skill.
- `software-reviewer`: read-only review after material changes.

Do not assign multiple agents overlapping ownership of the same files. Define the interface between parallel frontend and backend work first. The primary agent remains responsible for reconciling results, running integrated validation, and reporting anything not verified.
