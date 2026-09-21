> ⛔ **MERGED OUT 2026-09-18 (cleanup A5) — this spec is RETIRED and must not be launched.**
> Its substance now lives in **PLAN-TRUTH-153** as D11: tests, fixtures and detectors that cannot fail — a deferred defect in a pin test is that spec's subject.
> The deliverables were carried, not summarised, and this spec's own gate collapsed into the
> receiving spec's D0 rather than being duplicated. This file stays on disk unchanged below the
> line — a superseded spec is never deleted. Its queue row is `parked`, because
> `queue --transition` cannot write `superseded` (see PLAN-TRUTH-143 D9).

# PLAN-TRUTH-163: Two dispatch-workflow-pin test defects deferred at PLAN-TRUTH-157's loop-back ceiling

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-09-15 from PLAN-TRUTH-157's own landing message (`inbox/plan-truth-157-032.md` § Residue, PR
#1494). `pre-submission-self-review` had exhausted all 5 admitted loop-back iterations when CodeRabbit
filed these two findings in its final triage; both were resolved `taken_into_account` rather than fixed,
because no loop-back budget remained to act on them — an outcome the run itself did not choose.

## Objective

**Two live, confirmed defects in `test_orchestrator_dispatch_workflow_pin.py`, named by CodeRabbit on PR
#1494 and left unfixed for want of loop-back budget, not because either was disputed:**

1. **`00d610` — whole-document dispatch-index entry counting.** The test counts dispatch-index entries
   over the whole document rather than scoping the count to the population the assertion is actually
   about, which is the exact shape this epic's own "derive completeness, never assert it" archetype names
   — a count taken over the wrong population reads as measured when it is not.
2. **`9a819a` — a clause-scoped negation gap in the write-grant detector.** Closely related to (but not
   identical to) an already-fixed sibling defect this same plan closed in Q-Gate finding `5a3725`
   (`inbox/plan-truth-157-021.md`, fixed in commit `04f12a22b`): `_NEGATION_RE` applied at sentence scope
   rather than clause scope, so a genuine write-grant sharing a sentence with any negation word
   (not/never/no/none/nothing/cannot/without/outside) is silently dropped. `9a819a` is CodeRabbit's
   finding of a further instance or variant of this same class that the `5a3725` fix did not close.

## Deliverables

Two deliverables.

**D0 — GATE: re-read both findings against `test_orchestrator_dispatch_workflow_pin.py` at HEAD, and
determine whether `9a819a` is closed by the already-landed `5a3725` fix (commit `04f12a22b`) or is a
genuinely separate instance.** Do not assume either way — the two are in the same file and the same
detector class, and D0's job is to settle whether one fix covers both or two fixes are owed.

**D1 — Fix whichever of the two findings D0 confirms still needs a fix, with a matched control per fix**,
per this epic's own standing rule: a guard fixed in one direction needs a control proving the fix,
scoped to the exact population/clause the finding named — not a synthetic fixture.

## Claim Labels

- OBSERVED: CodeRabbit filed `00d610` and `9a819a` against PR #1494's `test_orchestrator_dispatch_workflow_pin.py`,
  both resolved `taken_into_account` at the loop-back ceiling (source: `plan-truth-157-032.md` § Residue).
  - verdict: unverifiable | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: plan-truth-157-032.md is already archived (consumed by this session's own drain fork); the CodeRabbit finding ids and their taken_into_account resolution were not re-read from the archive at cleanup time, though PR #1494 itself is independently confirmed merged
- OBSERVED: a related negation-scope defect (`5a3725`, same broad detector class) was found and fixed in
  the same plan's run, in commit `04f12a22b` (source: `plan-truth-157-021.md`).
  - verdict: corroborated | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: commit 04f12a22b exists on main, titled 'fix(self-review): address round-3 full-scope confirmation findings', consistent with the source finding's description. The target test file test/plan-marshall/plan-orchestrator/test_orchestrator_dispatch_workflow_pin.py exists at exactly the hypothesized path -- confirming the Expected Surface HYPOTHESIS entry too
- ⚠ HYPOTHESIS: `9a819a` is a distinct instance from `5a3725`, not already closed by the same fix. ⛔ Not
  independently verified at staging — the landing message names both by finding id only, without quoting
  the CodeRabbit comment bodies. D0 owns settling this (verify-at-outline).
  - verdict: unverifiable | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: Whether 9a819a is distinct from 5a3725 requires reading the actual CodeRabbit comment bodies, which were not fetched at cleanup time; D0 owns this per the spec's own text
- ⚠ HYPOTHESIS: `00d610`'s "whole-document" scope is the SAME kind of scope error the epic's
  derive-completeness archetype already names elsewhere in this test file's sibling tests. ⛔ Not
  cross-checked against the file at staging (verify-at-outline).
  - verdict: unverifiable | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: Not cross-checked against the test file's sibling tests at cleanup time; D0 owns this per the spec's own text

## Expected Surface

- OBSERVED: `test/plan-marshall/plan-orchestrator/test_orchestrator_dispatch_workflow_pin.py` — both
  findings' target file (D0, D1); path confirmed to exist at cleanup 2026-09-15
- HYPOTHESIS: the write-grant detector script `5a3725`/`9a819a` target (likely under
  `pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/` given the sibling fix's own
  component) (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Distinct from `PLAN-TRUTH-162` (argparse-rejection population) and the guard-authoring lesson promoted
  from this same landing (`2026-09-15-01-002`) — this spec is the CODE fix for the two specific deferred
  findings; the lesson is the process takeaway from the class of mistake.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-163-two-deferred-dispatch-workflow-pin-test-defects-from-plan-truth-157.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
