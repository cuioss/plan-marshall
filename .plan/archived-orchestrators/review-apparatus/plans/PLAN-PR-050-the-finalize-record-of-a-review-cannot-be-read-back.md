# PLAN-PR-050: The finalize record says done at a head it never examined, and the review channel it declares is always empty

> ⛔⛔ **SUPERSEDED 2026-09-12 by `PLAN-PR-063` — do NOT emit this spec.** Its queue row is retired
> under the operator's decision to raise the split guard to 12 deliverables and group staged work by
> shared target surface; D1, D2, D2a, D3, D4 and D5 are carried there as D1–D6 and D0 folds into that
> plan's merged D0 gate. ⛔ **This file is NOT dead and is NOT deleted**: it remains the AUTHORITATIVE
> TEXT of every deliverable body, and `PLAN-PR-063` points here rather than retyping it.

epic: review-apparatus
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Drained 2026-09-05 from inbox `-002`, `-007` and `-008` (all `candidate-lesson`), filed by
> `apply-the-cloud-plan-lane-contract-amendments` during its finalize and observed live on PR #1416.

## Objective

Make the finalize phase's own record of a review readable back as what actually happened: the head
the step last examined, whether the step returned findings, and whether verification ran at all.

## Problem

Three defects in the record, not in the work. Each one makes a *later reader* — a retrospective, an
audit, this epic's own analysis — reach a confident wrong conclusion. The theme is the epic's:
**a confident signal hiding a caveat.**

**1. A step that re-fires after its last `mark-step-done` leaves a record naming the wrong head.**
`status.metadata.phase_steps["6-finalize"]["pre-submission-self-review"]` reads
`outcome: done, head_at_completion: d08dc56e…, firing_count: 5,
display_detail: "clean at round 5; content byte-identical after rebase"`. That record is **stale**:
a sixth round ran at 2026-09-05T00:33Z as a delta over `c57a294c` — the commit carrying the
TASK-007/008 remediation of CodeRabbit's two Major findings — returned 2 findings, both fixed in
`30b325984`, and the step was never re-marked.

⛔ **Read literally, the record says the CodeRabbit remediation was never self-reviewed.** The run's
own `finalize-step-review-retrospective` reported exactly that and had to publish a correction.
`mark-step-done` is emitted by the step at the end of a firing, and a re-fire after the orchestrator
has already accepted completion has no obligation to re-mark. Nothing reconciles `head_at_completion`
against the head the step actually last examined, so **a stale record is indistinguishable from a
current one.**

**2. Dispatch boundaries stamp `step_complete` even when the step returned findings.** All 8 rows in
`work/metrics-dispatch-boundaries-6-finalize.toon` carry `termination_cause=step_complete`; **none**
carries `returned_with_findings`. Yet `pre-submission-self-review` returned findings in rounds 1, 2,
3, 4 and 6 — five findings-bearing terminations recorded as clean completions.

`returned_with_findings` exists precisely to mark a *productive* non-completion, and the logging-gap
contract excludes it from the agent-initiated-re-dispatch >50 % threshold for that reason ("a high
`returned_with_findings` share means the review dispatches were doing their job"). Because the
finalize dispatcher never stamps it, **the exclusion has nothing to exclude**. The consequence is not
cosmetic: `error_total_tokens` vs `retryable_total_tokens` vs productive-loop-back spend are the three
cost classes the retrospective separates, and one of the three is invisible on every finalize run.

**3. Zero `[VERIFY]` work-log entries on a plan that ran verification at least six times.** The
plan's `logs/work.log` carries 412 entries — `STATUS` 56, `STEP` 41, `DISPATCH` 26, `SKILL` 16,
`ARTIFACT` 13, and `VERIFY` **zero**. The same plan ran `pre-push-quality-gate` 5×, a whole-tree
`verify` after the rebase (24244 tests green at `30b325984`), `module-tests pm-plugin-development`
(3141 tests green) during execute, and whole-tree `plugin-doctor`.

`[VERIFY] (plan-marshall:{skill}) …` is a **declared expected pattern** in the logging-gap contract,
but no verification-bearing step emits it. Any consumer reading the tagged channel — including the
retrospective's own `expected_vs_actual` table — concludes no verification ran. ⛔ **A declared
category with a guaranteed zero is the worst of both**: it reports a gap no producer was ever going
to fill.

## Deliverables

**D0 — GATE, mutates nothing.** Re-ground all three claims at HEAD and record, per claim, the file
and symbol that settles it. For D3, settle the fork **before** implementing: is `VERIFY` a pattern
whose producer is missing, or a pattern that should be retired? Both are legitimate; shipping neither
is not.

**D1 — Make a step record self-validating about its head.** Either (a) require every re-fire of a
`mutates_source`-adjacent finalize step to re-mark with the new head and an incremented
`firing_count`, **enforced by the dispatcher rather than by the step**; or (b) make
`head_at_completion` self-validating — when the recorded head is an ancestor of current HEAD **and**
the step's declared surface changed in between, the record reports `stale` rather than `done`.
⛔ Whichever arm is chosen, a reader must not be able to mistake a stale verdict for a current one.

**D2 — Stamp `returned_with_findings` at the finalize dispatch boundary.** When a step's return
payload carries a non-empty findings list, the finalize dispatcher stamps `returned_with_findings`
and reserves `step_complete` for a clean return. This is a one-branch change at the
`record-dispatch-boundary` call site, not a new mechanism.

**D2a — THREE channels go dark over `6-finalize`, and a green completeness flag does not cover it.**
⭐⭐ **Folded from `arm-the-refusal-recovery-that-has-never-run-005.md` on 2026-09-07.** On that run
`6-finalize` — the phase that did the most work — produced **no accumulator file, no dispatch-boundary
file, and `check-dispatch-audit` classified 16/16 finalize steps `no_evidence`.**

⛔⛔ **`total_tokens` was therefore a FLOOR while `any_phase_missing_end_time=false`.** That flag
attests to phase **end-times** and to nothing else; it does **not** attest to accumulator coverage.
⭐ This ledger read it the stronger way once, in `landings/PLAN-PR-042.md`, and that reading is
corrected there — recorded here so the same inference is not made again.

*Done when:* a phase whose accumulator or dispatch-boundary channel produced nothing says so in the
record, and any published token total states whether it is settled or a floor — **derived from channel
coverage, never from the end-time flag.**

**D3 — Resolve the `VERIFY` channel one way.** Either emit `[VERIFY]` at each verification boundary
(the gate steps, the phase-5 verification sweep, `plugin-doctor`), or retire `VERIFY` from the
expected-pattern contract. Whichever is chosen, the expected-pattern set and its producers agree
afterwards, and a test pins that agreement.

**D4 — Retire the duplicate retrospective step record.** `phase_steps["6-finalize"]` carries BOTH
`plan-marshall:plan-retrospective` (recorded by the step) and a bare `plan-retrospective` (recorded
by the orchestrator). Both say `done` with different `display_detail`. The manifest step id is the
prefixed form; the bare one inflates any count over `phase_steps` and defeats a
`len(phase_steps) == len(manifest.steps)` handshake. Remove the orchestrator-side duplicate write.

**D5 — The post-run dirty-path guard must attribute by AUTHORSHIP, and its contract must agree with
its own filing.** ⭐ **Folded from inbox `required-reviewer-returns-empty-list-010.md` on 2026-09-05**,
observed live on PR #1410. Two defects in one guard:

- ⛔ **It attributes by observation, not authorship.** It reported `uv.lock` dirty against **5
  consecutive post-merge steps, none of which wrote it.** The file was already dirty at that run's
  `5-execute` handshake capture; the real cause is dependabot **#1417** raising the ruff specifier
  without refreshing the lock, so every local build re-resolves and dirties the tree. A guard that
  names the step that *ran* rather than the step that *wrote* files N identical findings for one cause.
- ⛔ **Its contract is wrong about itself.** It calls its finding **"non-blocking"**, but the
  `qgate add` call it prescribes files under the **actionable** qgate type — **which blocked the
  archive** until the finding was resolved by hand. This is doc-contract-divergence inside a guard
  whose whole job is to report accurately.

*Done when:* a dirty path is attributed to the step that last wrote it (or reported as
**pre-existing** with the handshake capture that proves it, exactly as that run recorded finding
`5ac74f` once with provenance rather than five times); and the guard's stated blocking class and the
qgate type it actually files under are the same fact, pinned by a test.

⚠ Note the shape: the guard reports **truthfully about the file and falsely about the cause**, which
is this plan's whole theme one level down.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/standards/status-lifecycle.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-logging/standards/log-format.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/`
- OBSERVED: `test/plan-marshall/manage-status/`
- OBSERVED: `test/plan-marshall/manage-logging/`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/post-run-review.md` — D5: the dirty-path guard's own contract, where "non-blocking" is stated
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` — D5: the qgate type the guard actually files under
- OBSERVED: `test/plan-marshall/manage-findings/`

## Claim Labels

- OBSERVED: The `pre-submission-self-review` step record names head `d08dc56e…` with
  `firing_count: 5` while a sixth round ran over `c57a294c` and fixed 2 findings in `30b325984`.
- OBSERVED: All 8 dispatch-boundary rows carry `termination_cause=step_complete`; none carries
  `returned_with_findings`, against 5 findings-bearing rounds.
- OBSERVED: `work.log` tag distribution carries no `VERIFY` row across 412 entries.
- OBSERVED: `phase_steps["6-finalize"]` carries both the prefixed and the bare retrospective step id.
- HYPOTHESIS: `returned_with_findings` is a declared termination cause the finalize dispatcher never
  writes — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md`
  § the `record-dispatch-boundary` call site (verify-at-outline).
- HYPOTHESIS: `[VERIFY]` is declared in the logging-gap expected-pattern set with no emitter anywhere
  in the tree — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/manage-logging/standards/log-format.md`
  § the expected-pattern table (verify-at-outline). ⛔ The **absence** claim is the higher-risk half
  and is verified as such: an unverified absence would have D3 build an emitter beside an existing one.

## Dependencies and Sequencing

- Depends on: none.
- Adjacent to: `PLAN-PR-049` (self-review loop accounting). Disjoint surface; may pair.
- **Overlaps with `PLAN-PR-031`** (`bot-participation-contract.md` is NOT in this surface, but both
  plans write finalize-phase record contracts) — **sequence, never pair** if PR-031's surface widens.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-050-the-finalize-record-of-a-review-cannot-be-read-back.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
