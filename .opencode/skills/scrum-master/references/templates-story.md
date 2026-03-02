## Template: story context (optional)

Use this when you want a “story file” that is richer than an individual task, or when you want to group multiple tasks under a user-story shaped wrapper.

---
Story: `<Epic>.<Story>` — `<title>`
Status: `ready-for-dev`
---

## Story

As a `<role>`,
I want `<action>`,
so that `<benefit>`.

## Acceptance criteria

1. <AC>
2. <AC>

## Task breakdown

- [ ] `<T#>`: <task title> (links: `TASK_<slug>.md`)
- [ ] `<T#>`: <task title> (links: `TASK_<slug>.md`)

## Developer guardrails (must-follow)

- Follow architecture constraints exactly (cite sources).
- Reuse existing code; do not reinvent.
- Do not silence errors.
- Zero legacy tolerance: do not leave legacy code paths behind; plan refactoring explicitly.

## References

- Requirements: <links>
- Architecture: <links>
- Related code: <paths>

