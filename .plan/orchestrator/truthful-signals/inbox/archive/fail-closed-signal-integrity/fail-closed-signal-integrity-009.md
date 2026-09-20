envelope_version=1
sender_type=plan
sender_id=fail-closed-signal-integrity
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T22:05:51Z

component=plan-marshall:manage-lessons
category=bug
bundle=plan-marshall

# `list-stalled` reports zero while carried lessons sit trapped in a plan directory

The corpus-wide trapped-lesson detector is vacuous for exactly the plans that trap lessons.

Verified first-party at retrospective time, all three facts together:

- `manage-lessons get --lesson-id 2026-07-22-16-003` returns `error: not_found` — the lesson is
  **not in the corpus**.
- All 8 `lesson-*.md` files are still sitting in `.plan/local/plans/fail-closed-signal-integrity/`
  — the lessons are **in the plan directory**.
- `manage-lessons list-stalled` returns `stalled_count: 0` — the detector says **nothing is
  stalled**.

## Root cause

`list-stalled` (and `plan-retrospective` Step 5.5, which shares the signal) keys the
stalled-lesson condition off `status.metadata.plan_source` matching the lesson-id pattern
`YYYY-MM-DD-HH-NNN`. That field identifies a plan *created from* a lesson. A plan that instead
**carries** lessons via `convert-to-plan` — which is what every orchestrator-staged plan with a
`Lessons Carried` block does — has `plan_source` unset and `source: description`. The detector's
population is a strict subset of the population that can exhibit the condition.

## Why this is DISTINCT from inbox message 002

Message 002 is the **restore** path: `cmd_restore_from_plan` resolves `plan_parent` main-anchored,
finds a worktree-resident plan dir missing, and reports "nothing to restore". This is the
**detection** path: nothing ever asks whether a restore is owed, because the plan does not look
like a lesson-sourced plan.

The two fail open independently and stack. Fixing 002 alone still leaves the condition invisible
until a human counts `lesson-*.md` files by hand — which is how it was found here.

## Impact

8 lessons are currently absent from the active corpus and resident in a plan directory that
`archive-plan` is about to move. Nothing in the system reports this. Two of the eight
(`2026-06-21-21-001`, `2026-07-22-12-003`) carry residue the housekeeping pass explicitly
classified as **not** covered by the promoted standard and therefore load-bearing.

## Solution

Derive the population from the observable, not from a declaration:

1. `list-stalled` should scan every plan directory for `lesson-*.md` files and report any plan
   holding one, independent of `plan_source`. Presence of the file IS the condition.
2. Cross-check the other direction too: a `lesson-*.md` in a plan dir whose id is ALSO present in
   `.plan/local/lessons-learned/` is a different (duplicated) fault than one that is absent from
   the corpus. Report both, distinctly.
3. `plan-retrospective` Step 5.5's trigger should consume the same widened signal rather than
   re-deriving `plan_source`.

⚠ **Operator action owed now, independent of the fix:** the 8 lessons in
`.plan/local/plans/fail-closed-signal-integrity/` need restoring to the corpus before the plan is
archived. The retrospective did not perform the restore — a corpus mutation is the orchestrator's
to make, and a dispatched leaf cannot fire the confirming `AskUserQuestion`.
