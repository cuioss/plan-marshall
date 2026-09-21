envelope_version=1
sender_type=plan
sender_id=self-review-cannot-see-an-unreachable-guard
epic=truthful-signals
kind=landing
created=2026-07-28T22:04:12Z

## What landed

PR #1042 "feat(self-review): flag unreachable guards, scope the clean verdict" shipped to main from `feature/self-review-cannot-see-an-unreachable-guard` (head `2a0aba2df`). The plan fixed the in-house pre-submission self-review's inability to flag an unreachable guard — the self-review clean verdict is now correctly scoped instead of reporting clean when a guard path cannot fire.

Finalize signals: pre-push quality-gate green (2 bundles + whole-tree), plugin-doctor clean (3 skills gated), pre-submission-self-review itself reported clean (101 candidates examined, no check matched), automatic-review found 5 comment(s), review-retrospective compared 3 reviewers with 8 actionable comments (coderabbit), ci-verify all checks green.

## Residue for the epic to track

The plan's own remediation reproduced the truthful-signals archetype twice more during execution, and a shipped test guard proved conditionally vacuous on terminal width — see the four `candidate-lesson` messages filed alongside this landing for detail. A structural gap in the finalize dispatch loop also surfaced: `pre-submission-self-review` is not in `HEAD_DEPENDENT_STEPS`, so it never re-fired over the loop-back diff that introduced two of those defects — both were instead caught by CodeRabbit and the whole-tree test gate, not by the in-house structural review that exists for exactly this class of check.
