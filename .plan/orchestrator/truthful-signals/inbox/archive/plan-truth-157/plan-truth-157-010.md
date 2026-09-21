envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:00:20Z

component=plan-marshall:phase-3-outline
category=anti-pattern
bundle=plan-marshall

# An exclusion rationale is per-deliverable — re-test it against every deliverable that touches the same coupling

Deliverable 1 settled `cleanup.md`'s exclusion from the mutation scope on the
ground that the file xrefs the shared Dispatch Decision Rule rather than
restating the three tests. That rationale was verified correct for deliverable 2,
whose refined wording reaches `cleanup.md` with no edit needed.

It did not cover deliverable 3. `cleanup.md` binds its own dispatchable half to
`analyze.md` Step 2 verbatim — the same envelope, the same effort surface, the
same `corroborations[N]{claim,verdict,evidence}` return shape. Deliverable 3
widened exactly that Step 2 dispatch with three new drafting returns, so the
verbatim-reuse claim then pointed at a widened shape `cleanup.md` must NOT adopt:
it drains no inbox and writes no landing report.

The exclusion was stated against the RULE change and was silent on the REUSE
coupling — the precise shape deliverable 1 was explicitly required to avoid.

Source record: Q-Gate finding `7b6268`, phase `3-outline`, resolution
`taken_into_account`.

## Solution

When a deliverable excludes a file on a stated rationale, re-test that rationale
against every OTHER deliverable in the plan that touches the same coupling, and
record per-deliverable which of them the exclusion covers. A rationale that holds
for one deliverable is not an exclusion for the plan.

The cited condition is no longer present at HEAD: `cleanup.md` now reuses
`analyze.md` Step 2's corroboration dispatch specifically, naming the
corroborations return shape, while the widened drafting returns are analyze-only
and unreferenced there.

## Impact

Applies to any outline whose deliverable 1 is a scope-settling gate over files
later deliverables also reach. The failure is invisible at the exclusion site,
because the rationale reads as complete.
