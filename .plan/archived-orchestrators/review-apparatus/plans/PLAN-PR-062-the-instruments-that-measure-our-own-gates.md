# PLAN-PR-062: The instruments that measure our own gates, and the loop that cannot account for itself

epic: review-apparatus
workstream: WS-03

> ⛔⛔ **SUPERSEDED 2026-09-18 — RETIRED AT THE COMPONENT RE-CUT. Do not emit this spec.**
>
> Its deliverables were carried, verbatim and as pointer rows, into: PLAN-PR-071 (D1/D2/D3 — the gate-measurement half), PLAN-PR-074 (D7 + the D4 review_commitments amendment — the dispatcher and the commitment population); D5/D8/D9 and the D0 count-prose arm ROUTED OUT to truthful-signals (self-review instrument, fails the PR test); D4 bullets G5/G8/G9/G12 ROUTED OUT to truthful-signals (pyprojectx build gate); D6 moved to ORCHESTRATOR HOUSEKEEPING.
>
> **Why**: the nine theme specs were cut by SUBJECT, and every subject crossed the same components —
> `_findings_core.py` was declared by 7 of 9, `automatic-review/SKILL.md` by 6, `github_pr.py` by 5 — so
> no two could ever run concurrently and five plans would each have re-derived the same file. The re-cut
> is by component; no file is declared by two live plans.
>
> ⭐ **This file is NOT deleted**: it remains the authoritative pointer chain between a successor's
> `Carried from` column and the retired source spec holding each deliverable body, and it holds the
> claim labels the successors deliberately do not restate.

> Composed spec — **absorbs `PLAN-PR-030` and `PLAN-PR-049` whole**, under the operator's 2026-09-12
> decision to raise the split guard to **12 deliverables** and group staged work by shared target
> surface.
>
> ⛔ **Every deliverable body below lives in its SOURCE spec and is NOT restated here.** The sources
> are retired from the queue but remain the authoritative text. Follow the pointer; do not retype.

## Objective

Make the instruments that measure our own gates report only what they measured, and make the
self-review loop able to account for every finding it produced and to terminate on something other
than exhaustion.

## Why these were grouped

Derived from `corpus surfaces`: both declare the `ext-self-review-plan-marshall` detector and pattern
modules, its SKILL, `pre-submission-self-review.md`, `pre-push-quality-gate.md` and the shared
self-review test. ⛔ They are the **same instrument from two sides**: `PLAN-PR-030` fixes what the
self-review measurement CLAIMS about itself, `PLAN-PR-049` fixes whether its findings SURVIVE the round
that produced them. A measurement whose findings are lost cannot be made honest by re-wording its
report.

## Deliverables

**D0 — GATE, mutates nothing.** The merged gate. From `PLAN-PR-030` D0: derive three populations from
the tree, or HALT — every later deliverable reads them. From `PLAN-PR-049` D0: re-ground all three
claims at HEAD before any edit. **HALT and report** on either failure.

| # | Deliverable | Body lives at |
|---|---|---|
| D1 | Anchor the delta's coverage denominator so a roster shrink cannot restore a share | `PLAN-PR-030` § D1 |
| D2 | Make the escape set's population explicit, matched to its denominator | `PLAN-PR-030` § D2 |
| D3 | Make the delta's published claims about itself true | `PLAN-PR-030` § D3 |
| D4 | Every gate verdict distinguishes checked, degraded, not-reached, never-performed | `PLAN-PR-030` § D4 |
| D5 | Measure the count-prose detector's three reach axes, and fix the instances outside them | `PLAN-PR-030` § D5 |
| D6 | Record the open measurement-semantics proposals, and correct two restating records | `PLAN-PR-030` § D6 |
| D7 | Make finding persistence a post-condition of the round, not a step inside it | `PLAN-PR-049` § D1 |
| D8 | Give the review chain a bounded terminus | `PLAN-PR-049` § D2 |
| D9 | Add a finished-edit detector for partial de-duplication | `PLAN-PR-049` § D3 |

⛔ **D6 is operator-gated** — it records proposals rather than deciding them, so it ends in an
`AskUserQuestion` and cannot run in a dispatched leaf.

**D4 amendment 2026-09-18 — the commitment population is WRONG, not merely empty (lessons
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

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py`
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_patterns.py`
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_gate_delta.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/sonar-roundtrip.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py`
- OBSERVED: `.claude/skills/finalize-step-plugin-doctor/SKILL.md`
- OBSERVED: `.claude/skills/finalize-step-review-retrospective/SKILL.md`
- OBSERVED: `build.py`
- OBSERVED: `test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review.py`
- OBSERVED: `test/plan-marshall/automatic-review/test_review_gate_delta.py`
- OBSERVED: `test/plan-marshall/automatic-review/test_counting_rule_parity.py`
- OBSERVED: `test/plan-marshall/automatic-review/test_bot_participation_contract.py`
- OBSERVED: `test/plan-marshall/build-pyproject/test_gate_coverage.py`
- OBSERVED: `test/plan-marshall/manage-findings/`

## Claim Labels

- OBSERVED: this plan's claim set is exactly the union of `PLAN-PR-030` § Claim Labels and
  `PLAN-PR-049` § Claim Labels, carried unchanged with their labels. Confirm/refute at those two
  sections — they are the authoritative record and this plan re-states none of them.
- OBSERVED: the two sources declare the same self-review detector, pattern module, SKILL and test —
  the instrument is one artifact read from two sides. Confirm/refute at `corpus surfaces` over the
  retired source rows.
- HYPOTHESIS: `PLAN-PR-030`'s three derived populations and `PLAN-PR-049`'s three re-grounded claims
  are independent, so one gate can carry both — confirm/refute at D0 (verify-at-outline). If D0 finds
  them entangled, it reports the entanglement rather than proceeding on either.

## Dependencies and Sequencing

- ⛔ **Overlaps `PLAN-PR-061`** on `automatic-review` and the retrospective, and `PLAN-PR-063` on the
  finalize step records — sequence, never pair.
- ⭐ **Internal order: D0 → D7 (persist the findings) → D1–D5 (make the measurement honest) → D8/D9 →
  D6.** Persistence first: a measurement fixed over findings that still evaporate cannot be pinned.
- Supersedes: `PLAN-PR-030`, `PLAN-PR-049`.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-062-the-instruments-that-measure-our-own-gates.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
