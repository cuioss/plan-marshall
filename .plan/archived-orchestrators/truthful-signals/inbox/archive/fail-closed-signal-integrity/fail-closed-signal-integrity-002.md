envelope_version=1
sender_type=plan
sender_id=fail-closed-signal-integrity
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T21:09:29Z

component=plan-marshall:manage-lessons
category=bug
bundle=plan-marshall

# manage-lessons restore-from-plan fails open when the plan dir is worktree-resident

`restore-from-plan` returns `status: success` with `no_lesson_file` when the plan directory
it resolved is worktree-resident rather than main-anchored. "I could not determine whether a
relocated lesson exists" is collapsed into the benign verdict "there is no lesson to
restore" — the caller cannot tell the two apart, and a carried lesson is silently left
stranded inside the plan directory.

This is the *inverse* of the verb used to retire lessons, and it is the plan's own target
defect reproduced inside the machinery the plan used to do its work. `convert-to-plan` moves
a lesson OUT of the active corpus; `restore-from-plan` is the only path back IN. A fail-open
on that path is a silent corpus loss, not a no-op.

Observed live during this run: the plan's own directory resolved to
`.../worktrees/{plan_id}/.plan/local/plans/{plan_id}/`, and `restore-from-plan` reported the
benign verdict against it.

## Impact

D5 lesson retirement for `PLAN-TRUTH-010` is UNFINISHED as a direct consequence:
classification of all carried lessons is complete and logged, but *application* is blocked
because the retirement path cannot be trusted to report whether it acted. 8 lessons were
carried through this plan; 2 of the spec's 10 were already absent from the corpus.

## Solution

Make the verb distinguish the three states it currently collapses into two:

- `restored` — a relocated `lesson-*.md` was found and moved back.
- `no_lesson_file` — the plan directory was resolved AND scanned, and held no relocated
  lesson (a real, observed zero).
- a distinct non-benign outcome for "the plan directory could not be resolved to the
  main-anchored store" — the could-not-look case, which must NOT share a representation
  with the looked-and-found-nothing case.

This is the same discriminator shape `orchestrator inbox list` already carries
(`epic_not_found` vs `inbox_state: missing` vs `inbox_state: present, count: 0`) — reuse
that precedent rather than inventing a new one.
