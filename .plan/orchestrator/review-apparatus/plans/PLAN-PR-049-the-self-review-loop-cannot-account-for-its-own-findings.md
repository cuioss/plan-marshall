# PLAN-PR-049: The self-review loop cannot account for its own findings, and its last commit ships unreviewed

> ⛔⛔ **SUPERSEDED 2026-09-12 by `PLAN-PR-062` — do NOT emit this spec.** Its queue row is retired
> under the operator's decision to raise the split guard to 12 deliverables and group staged work by
> shared target surface; D1–D3 are carried there as D7–D9 and D0 folds into that plan's merged D0
> gate. ⛔ **This file is NOT dead and is NOT deleted**: it remains the AUTHORITATIVE TEXT of every
> deliverable body, and `PLAN-PR-062` points here rather than retyping it.

epic: review-apparatus
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Drained 2026-09-05 from inbox `-001`, `-003` and `-014` (all `candidate-lesson`), filed by
> `apply-the-cloud-plan-lane-contract-amendments` during its finalize and observed live on PR #1416.
> Every claim below is the sender's own first-party observation of its own run; the
> corroboration column in `landings/PLAN-PR-032.md` records what this orchestrator re-derived.

## Objective

Make the self-review loop able to account for every finding it produced, and give the loop a
bounded terminus so no commit ships reviewed by nothing.

## Problem

Three defects, one loop. Each was observed on a single plan's finalize, and each is structural
rather than incidental to that run.

**1. A round can return findings and never persist them, so the store under-counts.**
`pre-submission-self-review` fired six times. Rounds **4 and 6 each returned 2 findings that were
never written** to `artifacts/findings/qgate-6-finalize.jsonl`. The store holds 5 findings, all
`resolution=fixed`; the true rounds-1-to-6 defect count is **9**. Both unpersisted rounds were
fixed on the merits (round 4: `SKILL.md:2242` contract_drift, `SKILL.md:1366` stale_count_prose;
round 6: `SKILL.md:1376` contract_drift, `SKILL.md:1378` same_document_contradiction), and in both
cases the fix agent **correctly refused** to file-then-resolve substitute records rather than
inventing `hash_id`s to close — so the loss leaves **no trace inside the store**.

⛔ **Two distinct causes, one symptom, and only one of them is already filed.** Rounds 1–4 ran
outside contract because the dispatcher omitted the required `candidates` prompt-body field; that
half has a filed root cause (lesson `2026-09-02-18-001`). Round 6 hit the same non-persistence
**after** the dispatch shape had changed, so the persistence gap is **separately live** and is not
closed by fixing the candidates-field omission. A plan that fixes only the first half will report
success against a defect that is still there.

**2. The last remediation commit in a finalize chain ships reviewed by nothing but `verify`.**
Commit `30b325984` (16 insertions / 17 deletions — the over-claim deletions that fixed round 6's own
two findings) had no bot review and no self-review round. It merged in #1416 as part of
`5f810002571fc98f86479527be96c46391d630d3`. The run's decision was reasoned and recorded, so this is
not a lapse in judgement — the *shape* is structural: whatever the last remediation commit is, it
ships unreviewed. The review chain is unbounded by construction (a review produces findings; fixing
them produces a commit; that commit would want reviewing), and at roughly one CodeRabbit review per
hour under contention the regress has no natural terminus. The run resolved it by stopping, which is
the only currently-available move.

⭐ **The hazard is demonstrated, not hypothetical**: round 6 found **2 real defects inside the
CodeRabbit remediation** — exactly the class a terminal pass would catch.

**3. A detector that de-duplicated two of three cells in one table row passed five rounds over the
third.** The PR's whole purpose in that region was de-duplication — replacing inline value
enumerations with cross-references. In the report template's reviewer-participation table row it did
exactly that for the **Class** and **Verdict** columns, and left the **`Reopens?`** column still
enumerating `yes` / `no` / `unknown`, which Step 7 defines. **CodeRabbit** caught it (finding
`ebea56`, `.claude/skills/cloud-plan-lane/SKILL.md:2242`, Minor; remediated in-run by TASK-008).
Five self-review rounds did not. A partial de-duplication is invisible to a detector that asks
"is this value enumerated?" per site rather than "did this edit finish the row it started".

## Deliverables

**D0 — GATE, mutates nothing.** Re-ground all three claims against HEAD before any edit. For D1,
confirm that round-6-shaped non-persistence is still reachable *after* the candidates-field fix —
if it is not, HALT and report, because the whole of D1 rests on that being separately live. Name,
per claim, the file and symbol that settles it.

**D1 — Make finding persistence a post-condition of the round, not a step inside it.** When a round
returns a non-empty findings list, the **dispatcher** verifies the qgate store gained a matching
record per finding before accepting the round's return, and fails the step otherwise. A round that
reports N findings and persists fewer than N is a contract violation the **caller** can detect
without trusting the leaf. ⛔ Do not implement this as a guard inside the round — that is the layer
that already failed twice.

**D2 — Give the review chain a bounded terminus.** After the final remediation commit, run **one**
mandatory self-review pass scoped strictly to the residual delta since the last reviewed head, with
no further chaining permitted regardless of what it finds — findings from that terminal pass are
**filed, not fixed-and-re-reviewed**. This closes the unreviewed sliver at the cost of exactly one
bounded pass and makes the terminal state explicit rather than a judgement made under time pressure.

**D3 — Add a finished-edit detector for partial de-duplication.** A detector that, for a structural
edit applied to a multi-cell row or a multi-entry list, reports the entries the edit did **not**
reach. Population-derived: it publishes the row/list size it evaluated, so a zero is a measured zero.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py`
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py`
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_patterns.py`
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md`
- OBSERVED: `test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review.py`
- OBSERVED: `test/plan-marshall/manage-findings/`

## Claim Labels

- OBSERVED: Rounds 4 and 6 each returned 2 unpersisted findings; the store holds 5 where the true
  count is 9 — first-party from the sender's own run.
- OBSERVED: Commit `30b325984` merged in #1416 with no bot review and no self-review round.
- OBSERVED: CodeRabbit finding `ebea56` names the un-de-duplicated `Reopens?` column at
  `cloud-plan-lane/SKILL.md:2242`; remediated in-run by TASK-008.
- HYPOTHESIS: The round-6 non-persistence is a **separately live** defect not closed by the
  candidates-field fix — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md`
  § the round's finding-persistence step (verify-at-outline). **D0 HALTS on refutation.**
- HYPOTHESIS: No detector in `_self_review_detectors.py` reports an unfinished structural edit —
  confirm/refute at
  `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py`
  § its detector registry (verify-at-outline).

## Dependencies and Sequencing

- Depends on: none.
- **Overlaps with `PLAN-PR-030`** (`_self_review_patterns.py`, `ext-self-review-plan-marshall/SKILL.md`,
  `pre-submission-self-review.md`, `pre-push-quality-gate.md`) — **sequence, never pair**. PR-030 owns
  *what the instruments report*; this plan owns *whether the loop accounts for its own output*.
- Adjacent to: `PLAN-PR-050` (finalize review-telemetry records). Disjoint surface; may pair.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-049-the-self-review-loop-cannot-account-for-its-own-findings.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
