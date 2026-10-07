envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-09T07:59:30Z

component=plan-marshall:manage-lessons
category=bug

# consult returns outline_not_found for a phase-5+ plan whose directory has moved into its worktree: main-anchored store, no --project-dir override

⛔ **RELOCATED FROM THE WRONG STORE — this is a MOVE, not a new report.** It was filed as lesson
`2026-09-08-11-001` in **Token-Sheriff's** lessons store, whose repo does not own the `plan-marshall` bundle.
It is written here first and removed there second (integrate-then-remove), so exactly one copy
exists at every point and none exists in two places.

Origin: Token-Sheriff epic `lessons-handling-26-09-04-01`. Original id `2026-09-08-11-001`, created 2026-09-08, lifecycle `active` at the time of the move.
⚠ Nine such lessons accumulated because a plan overrode the `wrong_store` guard rather than
routing the lesson to the repo that owns the bundle — the mechanism is reported separately as
`lessons-handling-26-09-04-01-032`. Body reproduced verbatim below.

---

## Context

Observed in TokenSheriff plan `refresh-2a-coverage-priorities`, 2026-09-08, during a phase-3-outline
revision that was **looped back from phase-5**. By that point the plan directory had already been
moved into its worktree by `prepare_execute` (the ADR-002 move-based model), so the outline was
running with cwd pinned to
`.plan/local/worktrees/refresh-2a-coverage-priorities/`.

`manage-lessons consult` returned `outline_not_found`. The lessons store is **main-anchored**, so the
verb resolves the store against the main checkout — but it then looks for the plan's
`solution_outline.md` relative to that same main-anchored root, where the plan directory no longer
exists. There is no `--project-dir` (or equivalent) override to tell it the outline lives in the
worktree.

## Impact

The prospective-lessons consult is silently unavailable to any outline pass that runs after the
phase-5 move-in. That is not a rare shape: it is every loop-back revision — the exact passes most
likely to benefit from prior lessons, because they exist precisely because something went wrong.

The failure is also **shaped to invite a false record**. The natural recovery is to log
`surfaced_count: 0` and move on, which reads downstream as \"the corpus was consulted and matched
nothing\" when in truth the corpus was never read. In this run the outline agent avoided that: it read
the corpus by hand and dispositioned the three active lessons manually rather than record a zero the
verb never produced. That is the right call and should not have been necessary.

## Directive

Give `consult` a way to locate a worktree-resident outline — either an explicit `--project-dir`
override mirroring the Bucket B build/CI script convention, or the same `locate-plan-checkout`
resolution the orchestrator entry paths already use to re-anchor.

Until then, a `consult` that returns `outline_not_found` must **never** be recorded as
`surfaced_count: 0`. Report the store as unresolved and read the corpus directly, per ADR-009: an
unreadable store is an explicit unknown, not a clean zero.
