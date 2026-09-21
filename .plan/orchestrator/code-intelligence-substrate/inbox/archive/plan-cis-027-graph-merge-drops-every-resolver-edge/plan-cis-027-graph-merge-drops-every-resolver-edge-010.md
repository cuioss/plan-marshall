envelope_version=1
sender_type=plan
sender_id=plan-cis-027-graph-merge-drops-every-resolver-edge
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T15:04:19Z

component=plan-marshall:phase-6-finalize
category=bug
created=2026-08-02
bundle=plan-marshall

# A conditionally-dispatching step needs a conditional roster row

`dispatch-inline-split.md` forces exactly one classification per step. `architecture-refresh`'s
classification is **conditional**, and expressing it as unconditional makes the dispatch audit's
inverse-coverage check unsound in the false-positive direction.

## Context

The roster places `default:architecture-refresh` on the **DISPATCHED** side with this rationale:

> hybrid, classified dispatched: its Tier 0 discover + diff is deterministic inline script work,
> and its Tier 1 re-enrichment fans out under `phase-6-finalize` per affected module — the only
> per-iteration parallel dispatch in the contract. **The dispatching tier governs the
> classification, so the step carries exactly one roster row.**

On this plan the step reached `outcome=done` with **zero** `[DISPATCH]` evidence. The decision log
explains why:

```
[architecture-refresh] Tier 0 — .plan/project-architecture clean after discover, no commit needed
[architecture-refresh] Tier 1 skipped — change_type = bug_fix
```

The dispatching tier is gated on `change_type`. The roster row does not express that gate, so the
audit's inverse-coverage check reads "DISPATCHED step reached terminal outcome, no dispatch
evidence" and emits a `dispatch_coverage_violation`.

## Why this is a real defect and not a one-off

The gate is `change_type = bug_fix`. That is not an edge case — it is one of the most common change
types in this repository. **The check will emit a false positive on every `bug_fix` plan that runs
`architecture-refresh`**, which is every `bug_fix` plan whose posture keeps the step.

A recurring false positive in a hard-rule check is worse than a missing check: the
`dispatch_coverage_violation` category exists to catch the genuine "ran phase-5/6 inline instead of
dispatching" defect, and a category that cries wolf on a routine change type trains readers to
discount it.

## Corroborating signal (why the rest of the audit is trustworthy)

The inline/dispatched partition separated cleanly on every other step, by two independent measures
that agree: every DISPATCHED-roster step that ran emitted a `[DISPATCH]` line **and** recorded
non-zero `total_tokens`/`tool_uses` in the execution log; every INLINE-roster step emitted none
**and** recorded `0/0`. `architecture-refresh` is the sole crossover — it is on the dispatched
roster and recorded `0/0/0`, matching the inline signature exactly. The token attribution
independently confirms no dispatch occurred, so this is a roster-expressiveness gap, not a lost
emission.

## Root cause

The roster's closure invariant ("exactly one classification per step, never both and never
neither") has no vocabulary for a step whose dispatch is conditional. The author correctly noted
the hybrid nature and resolved it by declaring the dispatching tier authoritative — but the
dispatching tier is itself gated, and that second-order condition has nowhere to live.

## Proposed action

1. Add a **`dispatched-when` qualifier** to the roster row naming the gating condition — for
   `architecture-refresh`, `change_type not in {bug_fix}`. The closure invariant is preserved: a
   conditional row is still exactly one row, and
   `test_dispatch_roster_closure.py` continues to assert one-classification-per-step.
2. Teach the dispatch audit's `dispatch_coverage_violation` check to **evaluate the qualifier**
   against the plan's actual `change_type` before flagging a missing `[DISPATCH]`.
3. Keep the count-free discipline the document already enforces — a qualifier is not a count.

## Generalisation

Any roster that partitions steps by a runtime behaviour must be able to express that the behaviour
is conditional. A partition that can only state unconditional membership will misclassify every
member whose behaviour is gated, and the misclassification surfaces as an audit false positive
rather than as a roster error — i.e. it is reported against the wrong component.

## Evidence

- aspect `execution_context_dispatch_audit` — `dispatch_coverage_violation` on `default:architecture-refresh`, `outcome=done`, zero dispatch evidence
- decision.log `d0b69f` — "Tier 0 — `.plan/project-architecture` clean after discover, no commit needed"
- decision.log `531318` — "Tier 1 skipped — change_type = bug_fix"
- `dispatch-inline-split.md` § Dispatched steps — the unconditional `architecture-refresh` row and its "exactly one roster row" rationale
- `execution.toon` `execution_log` — `architecture-refresh,6-finalize,executed,0,0,0` (inline token signature on a dispatched-roster step)
- `status.json` `metadata.change_type: bug_fix`
