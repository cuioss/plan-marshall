envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:04Z

component=plan-marshall:automatic-review
category=improvement
title=Review-bot rounds do not converge: each fix batch produces a fresh comment wave
source_lesson=2026-11-18-13-001
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-18

# Review-bot rounds do not converge: each fix batch produces a fresh comment wave

# Candidate lesson: review-bot rounds did not converge, each fix batch produced a fresh comment wave

- Source signal: automatic-review, plan git-core-import, PR 25 (inbox git-core-import-001).

## What happened

The review loop needed four triage rounds on PR 25: 23, 27, 1 and 1 actionable findings. The third iteration reached the 3/3 loop-back cap and a fourth had to be granted explicitly. The second round was larger than the first: the bots re-reviewed the fix commits and raised new comments on code the fix batch had just touched, not only on lines they had flagged before. The clusters were credential and PII leakage in results, remote-policy enforcement on every transport path including redirects, lease semantics and test portability.

## Why it matters

Each round costs a full cycle of simplify, pre-push gate, push, CI, automatic-review and Sonar, plus bot-quota waits. A loop that ends only when the bots run dry is unbounded by design, so the loop-back cap becomes the real stopping rule and lifting it takes an operator decision.

## Candidate rule

- Before the first push of a large security-sensitive change, run a local review pass with the lenses the bots use.
- When fixing a batch, sweep the same cluster across every sibling call site, not only the flagged line.
- Surface "new-comment rate per round" so a non-converging loop is visible before the cap is hit; consider budgeting the cap per PR size.

## Recurrence - 2026-11-22 (plan-12-forms-kinds-schema-layout, PR 54)

The CodeRabbit loop ran 8 rounds on one small module (schema validation in `git-forms`), and the operator had to raise the loop-back ceiling twice. Unlike PR 25, the rounds were not different clusters: every round found one more corner case of the same family, reference handling in a copy of JSON Schema validation (what a reference resolves to, where it is looked up, how it nests). Each fix closed the reported case only, so the next round reported the neighbouring case.

Added rule: when a review finding names a member of a family (here: reference resolution), stop patching the single case. Enumerate the whole family from the standard (every reference keyword, scope and resolution step the specification defines), fix or explicitly exclude each member in one commit, and add a test per member. Doing this on the second round of a family would have saved the remaining rounds.
