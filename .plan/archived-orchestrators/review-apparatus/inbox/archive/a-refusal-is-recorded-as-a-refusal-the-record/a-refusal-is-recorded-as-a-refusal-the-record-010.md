envelope_version=1
sender_type=plan
sender_id=a-refusal-is-recorded-as-a-refusal-the-record
epic=review-apparatus
kind=candidate-lesson
created=2026-08-31T08:19:03Z

component=plan-marshall:workflow-integration-github
category=anti-pattern
title=The refusal_pattern_drift guard fired a live false positive on its own PR, and its tests were written against the over-broad predicate

# The refusal_pattern_drift guard fired a live false positive on its own PR, and its tests were written against the over-broad predicate

## Context

`github_pr.py:1457` emitted `refusal_pattern_drift` when `len(_layers) == 1` — that is, whenever exactly one recognition layer matched a refusal notice. The diagnostic's purpose is narrow: report the case where the **structural** recognizer matched and the **registry** did not, because that is what says a registered vendor wording has drifted.

The predicate is symmetric; the condition it is meant to detect is not. A **registry-only** match is not drift — it is the designed correct state for a whole class of refusals. Sourcery's size refusal (`larger than the review limit of`) is invisible to the structural arm by construction, so Sourcery's declared `refusal_patterns` make every size refusal registry-only **forever**.

## This is corroborated, not inferred

The guard fired a live false positive **in this PR's own finalize run**, emitting:

```text
refusal_pattern_drift[1]: sourcery,registry_refusal_patterns
```

for a refusal the registry layer read correctly. Three places in the shipped source already said so before the fix: the guard's own comment (`github_pr.py:1443-1448`) names the load-bearing case as a body only the structural arm reads; `refusal_layers`' docstring states the observable in one direction only; and `_is_refusal_notice`'s docstring documents the registry arm as load-bearing *precisely because* Sourcery's size refusal is invisible to the structural arm.

## Two things worth carrying forward

**1. The guard's predicate was never checked against the scenario the guard exists for.** A bidirectional test (`len(...) == 1`) was written for a unidirectional condition (`structural ∧ ¬registry`). The correct form is the one CodeRabbit proposed and the plan applied:

```python
if REFUSAL_LAYER_STRUCTURAL in _layers and REFUSAL_LAYER_REGISTRY not in _layers:
```

**2. The existing tests pinned the defect.** The detector's tests were written against the over-broad predicate, so they passed on the false-positive behaviour and would have failed on the correct one. The fix therefore carried a *mandatory* test reconciliation plus a matched negative control (a registry-only refusal must yield an empty drift list). A guard whose tests were authored from its implementation rather than from its purpose cannot report that its purpose is unmet.

**3. Our own gates did not catch it, an external reviewer did.** The false positive was emitted in the run's own logs and passed through unremarked; the finding entered via CodeRabbit inline comment `86d508` on PR #1368 and was remediated by TASK-014. A guard emitting a diagnostic about the very subject area the PR is changing is a signal our self-review pass had every opportunity to read and did not.

## Proposed action

1. When a guard's diagnostic fires **during the run that is changing that guard's subject area**, treat the emission as a first-class self-review candidate — the run has produced live evidence about its own change.
2. Add the guard-predicate-vs-scenario check to the self-review candidate classes: for every emitted diagnostic, state the scenario in one sentence and confirm the predicate is not broader than it.
3. When a fix changes a predicate, require the accompanying test delta to include a matched negative control over the case the old predicate wrongly admitted — otherwise the pinned-defect tests are simply re-pinned to the new shape.

## Evidence

- finding: `86d508` — CodeRabbit inline on `workflow-integration-github/scripts/github_pr.py:1457`, reviewed_commit_sha `0cba190e`, resolution `fixed` via TASK-014
- live emission: `refusal_pattern_drift[1]: sourcery,registry_refusal_patterns` in this PR's own finalize run, for a correctly-read registry-only refusal
- source: `github_pr.py:1443-1448` (guard comment), `refusal_layers` docstring, `_is_refusal_notice` docstring — three pre-existing statements of the one-directional observable
- structural permanence: `sourcery`'s declared `refusal_patterns` make every size refusal registry-only, so the false positive is guaranteed rather than incidental
