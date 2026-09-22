# PLAN-PR-074: The merge gate, the foreign gate, and the dispatcher that records them

epic: review-apparatus
workstream: WS-04

> **Component-cut spec, authored 2026-09-18.** This plan owns ONE component: `phase-6-finalize` — the pre-merge barrier, `foreign_pr_gate.py`, `review_commitments.py`, `ci_verify.py`, and the dispatch boundary.
> ⛔ **Every deliverable body below lives in its ORIGINAL source spec and is NOT restated here** — the
> `Carried from` column names the theme spec this deliverable was cut out of, and that spec's own
> pointer names the retired spec holding the body. Follow the chain; do not retype.
>
> The theme specs `PLAN-PR-056` … `PLAN-PR-064` were retired on 2026-09-18 because their surfaces
> overlapped almost totally — `_findings_core.py` was declared by 7 of 9 — so no two could ever run
> concurrently. The cut is by component, so **no file is declared by two live plans**.

## Objective

Make every finalize gate clear only against a population it can prove it classified, and make the dispatcher record what a step actually returned.

## Deliverables

| # | Deliverable | Body lives at | Carried from |
|---|---|---|---|
| D0 | The foreign-PR gate clears only against a population it can prove was classified | `PLAN-PR-028` § D4 | `PLAN-PR-064` D4 |
| D1 | The gate is proven where it bites, and its off-normal paths keep its contract's shape | `PLAN-PR-028` § D5 | `PLAN-PR-064` D5 |
| D2 | Make the post-merge catch a pre-merge one | `PLAN-PR-053` § D4 | `PLAN-PR-058` D5 |
| D3 | A documented empty-string default the executor makes unreachable | `PLAN-PR-051` § D1a | `PLAN-PR-058` D9 |
| D4 | A review bot is not a build check, and today it is counted as both | `PLAN-PR-048` § D4 | `PLAN-PR-057` D7 |
| D5 | Stamp `returned_with_findings` at the finalize dispatch boundary | `PLAN-PR-050` § D2 | `PLAN-PR-063` D2 |
| D6 | Make finding persistence a post-condition of the round, not a step inside it | `PLAN-PR-049` § D1 | `PLAN-PR-062` D7 |
| D7 | Retire the duplicate retrospective step record | `PLAN-PR-050` § D4 | `PLAN-PR-063` D5 |
| D8 | The post-run dirty-path guard must attribute by AUTHORSHIP | `PLAN-PR-050` § D5 | `PLAN-PR-063` D6 |


**D9 — A triage decision needs a representation the pipeline can protect (lesson `2026-09-04-08-015`,
absorbed 2026-09-18).** A remedy whose whole artifact is a sentence in a document is deleted by a later,
entirely correct accuracy pass, and nothing notices that a decision was voided: Q-Gate `c4e309` removed
the sentence step 1 had added, and CodeRabbit `1002a8` then reopened the same finding. *Done when:* a
triage disposition whose remedy is documentary records a commitment naming the file, the claim and the
finding it discharges, and a later edit that removes the claim surfaces the commitment rather than
silently voiding it. ⭐ In-epic by provenance — carried out of this epic's own inbox
(`review-packs-become-published-artifacts-014.md`).

**D8 amendment 2026-09-18 (lesson `2026-09-05-07-001`).** The `rejected` bucket does two jobs —
**administrative** rejection (out of scope, duplicate, not-for-this-PR) and a **refuted premise** (the
reviewer was wrong) — so `false_positives_count` over-reported by 4 and under-reported by 3 on one run,
in opposite directions at once, which no scaling can correct. D8's disclosure of a contradicting record
does not reach this axis (`grep -rn "administrative" plans/ epic.md findings/` → 0). ⇒ D8 additionally
separates the two at triage time, or excludes administrative dispositions from the metric's
denominator and says so.

Thirteen deliverables. The 12 ceiling is a guideline (operator ruling 2026-09-15); D13 is the same
disposition record the other twelve read and write. ⛔ **Absorb no fourteenth.**

*(Carried verbatim from `PLAN-PR-063` D13 at the 2026-09-18 component re-cut.)*

**D10 amendment 2026-09-18 — the commitment population is WRONG, not merely empty (lessons
`2026-09-08-20-002` and `2026-09-05-07-007`, absorbed from the global corpus).** D4 currently makes a
`clear` over zero commitments legible (`not-reached` rather than `clear`). That is necessary and it is
not sufficient, because two separate causes keep the population empty:

1. **Wrong population.** `review_commitments.py:402` derives the whole commitment set from
   `query_findings(plan_id, finding_type='pr-comment')`, so without `--include-qgate` **every qgate
   self-review commitment is outside it by construction** — five ids were named on the observing run
   (`bea8e3`, `20d5ae`, `9e2c7e`, `1599c0`, `767d58`).
2. **Wrong order.** `cmd_reconcile`'s sole caller is `default:finalize-step-simplify` at order **9**,
   while the producers of `pr-comment` findings run at `default:push` (11), `default:create-pr` (20) and
   `automatic-review` (~40). The population is therefore empty at that order **for every plan, forever**
   — a scheduling defect a rendering rule cannot reach.

*Done when:* the reconcile reads a population that includes qgate commitments, runs at an order where
its producers have run, and reports the population it used with its size. ⛔ Fixing only the rendering
leaves a guard that is honest about a verdict it should never have been in a position to give.

**D5 amendment 2026-09-18 (lessons `2026-08-27-16-006`, `2026-09-04-08-013`).** D5 measures the
**count-prose** detector's three reach axes; two absorbed lessons show the axis set is narrower than the
defect class. (a) Four of five observed escapes are NOT count-prose — a closed-set literal sitting
beside the named symbol that defines the same set (`a1ebb0` flag forms, `986369` guard roster, `bc1344`
`error_cause`/`landing_state`, `df7702` `overall_status`), and none of the surfacer's 20 `_detect_*`
functions is that class. (b) The discipline reaches the METRIC and not the NARRATIVE in the same
artifact: `5835d8`'s `cohort_size` was derived over 79 strings in 23 files while the prose beside it was
asserted. ⇒ D5 reports the reach axes it measured AND the population it could not reach, and the
cheaper structural remedy — reject historical narrative in a test docstring outright, removing the site
where the class keeps landing — is evaluated rather than assumed unavailable.

**D8 amendment 2026-09-18 (lesson `2026-09-05-16-001`).** D8 bounds the review chain; it does not
report what the chain did to itself. **14 of 51 findings (27%) across 19 firings carried an explicit
self-seeded marker**, forming five chains in which one round's correction authored the next round's
finding — one running four consecutive rounds, and one OSCILLATING (deleted in one round, restored in
the next, terminating neither time). ⇒ D8 additionally reports the self-seeded share as a field, and
names the terminating move: **replace a drifted restatement with a POINTER at its source, never with a
corrected restatement**.

**D0 amendment 2026-09-18 (lesson `2026-09-15-06-002`, surface only).** D1–D5 all edit
`_self_review_detectors.py` / `_self_review_patterns.py`, and six separately-diagnosed vacuity modes
have been observed in exactly those modules: positional indexing over named members; an
affirmative-verb allowlist incomplete by construction; **the fix for that one self-defeating a round
later** (widening to bare `write` auto-satisfied the condition, since `write` is itself a forbidden
target); an unanchored pattern satisfied by unrelated prose; a matched control transcribing a SUBSET of
the live constant; and a non-vacuity guard firing only on TOTAL emptiness, never on a shrunk
population. ⇒ D0 sweeps the modules for these six modes BEFORE D1–D5 edit them. ⚠ The instances are
closed (#1494); the authoring discipline is what carries — and `PLAN-PR-030` D4's own warning that this
epic *"has repeatedly introduced a vacuous guard inside the fix for one"* is mode 3 realized. ⛔ The
LESSON itself is owned by `truthful-signals` (its `source_epic`), transferred there rather than
absorbed; only this surface-level obligation is ours.

Ten deliverables, under the ceiling. D0's three populations are known to be the widest derivation in
this cluster; the headroom is for what it returns.

*(Carried verbatim from `PLAN-PR-062` D4-amend at the 2026-09-18 component re-cut.)*

11 deliverables — within the guideline (12 nominal, ~14 when the aspects fit together, operator ruling 2026-09-15). ⛔ **Absorb nothing from another component**: the re-cut exists so this plan's surface stays disjoint.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_verify.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-merge-barrier.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/post-run-review.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py`
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_foreign_pr_gate_cli.py`
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_foreign_pr_gate_gate.py`
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_review_commitments_commitments.py`
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_review_commitments_reporting.py`

## Claim Labels

- OBSERVED (2026-09-18): every deliverable in this plan was carried verbatim from the theme spec named
  in its `Carried from` column, which carries the claim labels for its own deliverables. Confirm/refute
  by reading that spec's `## Claim Labels` section — this plan re-states none of them.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: Structural carried-verbatim claim, verified by reading this spec at HEAD: nine pointer deliverables plus five inline amendments, each marked as an absorbed lesson with its provenance rather than a restated body.
- OBSERVED (2026-09-18, orchestrator `corpus surfaces` + per-deliverable mapping): this plan's declared
  surface is disjoint from every other live plan's in this epic. Confirm/refute with
  `orchestrator corpus cross-check --slug review-apparatus`.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: DISJOINTNESS HOLDS, derived by membership over all fourteen declared paths against every other staged spec - the phase-6-finalize split against PLAN-PR-073 (landing surface), PLAN-PR-077 (push/create-pr) and PLAN-PR-075 (telemetry) is clean, no shared path. Surface MOVED though: phase-6-finalize/SKILL.md (+14), review_commitments.py, branch-cleanup.md (+19), four test modules all changed in this window. Light method: not re-audited line by line; the D10 amendment cited review_commitments.py:402 must be re-anchored on its symbol.


## Dependencies and Sequencing

- ⛔⛔ **D5 and D6 are ONE call site** (`record-dispatch-boundary` / `termination_cause`): D5 makes the
  dispatcher stamp what a step returned, D6 makes it verify a matching record per returned finding.
  Shipped apart, the second rewrites the branch the first just added. D5 strictly first.
- ⛔ **D0/D1 run AFTER the launched `PLAN-PR-033`**, whose operator decisions bound what they may
  implement — a constraint carried from the source spec, not added here.
- ⭐ D6 carries the `review_commitments` amendment absorbed 2026-09-18: the commitment population is
  WRONG (qgate findings excluded by construction) and read at the wrong ORDER (9, before every
  producer). Fixing only the rendering leaves a guard honest about a verdict it should never have given.
- ⚠ D9's surface is UNSTATED in its source; its nearest mechanism is `review_commitments.py`, which
  this plan owns. Settle it at outline — do not assign it by assumption.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-074-the-merge-gate-and-the-finalize-dispatcher.md"
```

## Write-Boundary

The plan implementing this spec writes to its own repository source only. It creates and edits NO file
under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
