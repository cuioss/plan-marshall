envelope_version=1
sender_type=plan
sender_id=unchecked-finding-persist-loses-the-finding
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T17:25:28Z

component=plan-marshall:phase-6-finalize
category=improvement
bundle=plan-marshall
created=2026-07-28

# finalize-step-simplify can introduce new untested production code with no test-coverage gate

## Context

This plan's `finalize-step-simplify` sweep introduced a new shared helper,
`add_qgate_finding_checked`, in `_findings_core.py` — consolidating the repeated
bind-and-test-against-`QGATE_PERSIST_OK` pattern across the `github_pr.py` / `gitlab_pr.py`
producer-mismatch emitters. This is new production code, not a pure simplification of existing
code, and it shipped with zero direct test coverage — only exercised transitively through its
two callers. CodeRabbit's review caught the gap (a review_body nitpick) and it had to be closed
by an added TASK-8 fix task after the PR was already open, rather than being caught by any
in-plan gate before push.

## Root cause

`finalize-step-simplify` is scoped as a "collapse accidental complexity" sweep and, per its own
standards doc, is not paired with the same "new code needs a direct test" obligation that
`phase-4-plan`/`phase-5-execute` task planning enforces for planned deliverables — because the
sweep's edits are, by design, supposed to be behavior-preserving refactors of EXISTING code, not
new abstractions. When the sweep does introduce a genuinely new helper (as opposed to
inlining/deleting), no gate currently checks that the new surface got its own test.

## Proposed action

Add a check to `finalize-step-simplify` (or `pre-submission-self-review`, which already runs
right before it in the settle band) that flags any NEW top-level function/symbol the sweep's diff
introduces which has no corresponding new or updated test reference, so this class of gap is
caught before push rather than by an external reviewer after the PR opens.

## Evidence

- CodeRabbit review_body finding 9842c8 on PR #1038 (nitpick) — "no direct test exists for
  add_qgate_finding_checked itself"
- TASK-008 (this plan) — added post-PR to close the gap; review-retrospective.md quotes this as
  "the only item with real depth" across all 3 reviewers this cycle
- request-result-alignment (this retrospective) — scope_creep finding names this helper as one
  of the 6 files touched beyond the outline's declared affected_files
