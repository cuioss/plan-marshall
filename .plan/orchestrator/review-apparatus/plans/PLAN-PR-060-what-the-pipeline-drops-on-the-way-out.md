# PLAN-PR-060: What the pipeline drops on the way OUT, and the record that says it did not

epic: review-apparatus
workstream: WS-03

> ⛔⛔ **SUPERSEDED 2026-09-18 — RETIRED AT THE COMPONENT RE-CUT. Do not emit this spec.**
>
> Its deliverables were carried, verbatim and as pointer rows, into: PLAN-PR-068 (D0/D1/D3/D4 — the response path), PLAN-PR-073 (D10 — a posted disposition re-checked against what landed); D2 DELETED as a duplicate of PLAN-PR-059 D2 item 3; D5/D6/D7/D9 and D8 cold reads moved to ORCHESTRATOR HOUSEKEEPING (no repository diff).
>
> **Why**: the nine theme specs were cut by SUBJECT, and every subject crossed the same components —
> `_findings_core.py` was declared by 7 of 9, `automatic-review/SKILL.md` by 6, `github_pr.py` by 5 — so
> no two could ever run concurrently and five plans would each have re-derived the same file. The re-cut
> is by component; no file is declared by two live plans.
>
> ⭐ **This file is NOT deleted**: it remains the authoritative pointer chain between a successor's
> `Carried from` column and the retired source spec holding each deliverable body, and it holds the
> claim labels the successors deliberately do not restate.

> Composed spec — **absorbs `PLAN-PR-035` and `PLAN-PR-031` whole**, under the operator's 2026-09-12
> decision to raise the split guard to **12 deliverables** and group staged work by shared target
> surface.
>
> ⛔ **Every deliverable body below lives in its SOURCE spec and is NOT restated here.** The sources
> are retired from the queue but remain the authoritative text. Follow the pointer; do not retype.

## Objective

Make an unanswered review finding observable, and make the epic's own record of what it answered
resolve against the tree. One plan, because the second is the first's audit surface: `PLAN-PR-031` D6
is the claim that *a posted disposition is a promise nothing re-checks against what landed*, and
`PLAN-PR-035` is the measurement of the promises that were never posted at all.

## Why these were grouped

Derived from `corpus surfaces`: both declare `github_pr.py`, `_findings_core.py` and
`test_github_pr.py`. The subject link is `PLAN-PR-031` D6 ↔ `PLAN-PR-035` D1 — one records what we
said, the other establishes whether we said it. ⛔ Shipped apart, the run-report corrections of
`PLAN-PR-031` would be written against a transmit verb whose honest/unhonest counts `PLAN-PR-035` is
about to change, so the corrected record would need correcting again.

## Deliverables

**D0 — GATE, mutates nothing.** The merged attribution-and-derivation gate, carrying BOTH populations.
From `PLAN-PR-035` D0: attribute each of the thirteen unanswered findings to a mechanism or record it
unattributable, published as a table with its population (13 of 43, four named PRs); **HALT if fewer
than nine attribute.** From `PLAN-PR-031` D0: derive the report corpus and confirm every defect still
reproduces. ⛔ `PLAN-PR-035` § Dependencies: **D0 must ATTRIBUTE BY AUTHOR before reporting any ratio**
— some of the 43 may be our own comments, which would make numerator and denominator both wrong.

| # | Deliverable | Body lives at |
|---|---|---|
| D1 | Make "unanswered" a first-class outcome of the transmit verb | `PLAN-PR-035` § D1 |
| D2 | Stop discarding the marker's error return | `PLAN-PR-035` § D2 |
| D3 | Close the mechanism D0 implicates | `PLAN-PR-035` § D3 |
| D4 | Pin the measurement | `PLAN-PR-035` § D4 |
| D5 | Correct the false claims about symbols, PRs and states | `PLAN-PR-031` § D1 |
| D6 | Re-derive every disputed figure, and label the real measurements | `PLAN-PR-031` § D2 |
| D7 | Finalize plan 060's report, and correct what it asserts | `PLAN-PR-031` § D3 |
| D8 | Discharge the owed obligations, or give each a git-tracked handle | `PLAN-PR-031` § D4 |
| D9 | Re-anchor the `cloud-plan-lane` proposals and put them to the operator | `PLAN-PR-031` § D5 |
| D10 | A posted disposition is a promise, and nothing re-checks it | `PLAN-PR-031` § D6 |

⛔ **D9 is operator-gated by construction** — it ends in an `AskUserQuestion`, and a dispatched leaf
cannot reach the operator. Route it to main context or the plan stalls holding a decision it cannot
take.

⛔ **Standing amendment, unchanged by the merge**: once `PLAN-PR-032` landed (it has, #1416), D9's
items 1–3 are DROPPED before this plan is emitted. Check them off at emit, not at outline.

Eleven deliverables, under the ceiling.

**Evidence amendment 2026-09-15** (from
[`findings/2026-09-15-pr-agent-vs-coderabbit-vs-sourcery.md`](../findings/2026-09-15-pr-agent-vs-coderabbit-vs-sourcery.md);
widens D0's population, adds no deliverable):

- ⭐ **The unanswered population is now measured at a far larger n than D0's 13 of 43.** Over the
  plan-marshall window 2026-08-30 → 2026-09-15, **97 of 493** finding units carry no posted answer (per
  `review-practice.md` § 2 — the posted reply, not ledger state). D0 attributes these, not only the
  thirteen. The split to attribute:
  - 55 CodeRabbit + 3 Sourcery threads resolved by the bot's own "✅ Addressed in …" marker, with no
    answer from us;
  - 3 threads resolved with no marker and no reply (`#1458` CodeRabbit `3969226297`; pr-agent `#1372`
    `3893066633`, `#1393` `3927008629`);
  - ⛔ **11 unresolved AND unanswered — 6 on merged PRs**: `#1433` `3947649192`; `#1468` `3992367351`;
    `#1484` `4000267866`, `4000267870`, `4000267874`, `4000267877`; closed: `#1431` `3945309329`, `#1440`
    `3949759158`/`3949759166`/`3949759189`, `#1481` `3997885650`;
  - **every** Sourcery review body (7) and **every** substantive pr-agent guide (3: `#1372`, `#1376`,
    `#1393`) went unanswered — whole finding KINDS the response path does not reach;
  - 16 units on `#1440`, `#1452`, `#1456`, `#1483` were answered only by a free-form PR-level note, not a
    per-finding reply.
- ⚠ The 6 unanswered-and-unresolved findings on merged PRs are ALSO owed post-merge revisits; D8
  (discharge the owed obligations) carries them unless they are answered before this plan runs.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-pr-doctor/standards/automated-review-lifecycle.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md`
- OBSERVED: `.claude/skills/cloud-plan-lane/SKILL.md`
- OBSERVED: `marketplace/bundles/`
- OBSERVED: `.plan/`
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_pr.py`
- OBSERVED: `test/plan-marshall/automatic-review/test_structural_refusal.py`

## Claim Labels

- OBSERVED: this plan's claim set is exactly the union of `PLAN-PR-035` § Claim Labels and
  `PLAN-PR-031` § Claim Labels, carried unchanged with their labels and their stamped verdicts.
  Confirm/refute at those two sections — they are the authoritative record and this plan re-states none
  of them.
- OBSERVED: `PLAN-PR-035` § Dependencies records that its 13-of-43 denominator is SUSPECT until D0
  attributes by author. Confirm/refute at that section.
- HYPOTHESIS: the thirteen are attributable from the stored corpus without re-fetching the PRs —
  confirm/refute at D0 (verify-at-outline). If the corpus was pruned, the PRs remain readable through
  the CI abstraction's read side.
- Verify-first clause, carried from `PLAN-PR-035`: the thirteen were observed on 2026-08-13.
  **Re-check whether any has since been answered** before reporting it unanswered.
- OBSERVED (corpus pass 2026-09-15, not re-read first-party): 97 of 493 plan-marshall finding units in
  the window 2026-08-30T20:16:39Z → 2026-09-15T09:50:16Z carry no posted answer, 11 of them unresolved.
  Confirm/refute at D0 by re-reading the posted replies on the named PRs — and re-check each for a
  late answer before reporting it.

## Dependencies and Sequencing

- ⛔ **Depends on `PLAN-PR-059`** — that plan owns the producer pre-filters and the `070 G1`
  resolve-failure path. D0's attribution runs against a fixed mechanism, and D3 is scoped to what
  remains.
- ⛔ **Overlaps `PLAN-PR-056`, `PLAN-PR-057`, `PLAN-PR-058` and `PLAN-PR-059`** on the `github_pr`
  family — sequence, never pair.
- ⭐ **Internal order: D0 → D1/D2/D3/D4 (the transmit verb) → D5–D8 (the record) → D9/D10.** The record
  is corrected last, against what the verb ends up reporting.
- Supersedes: `PLAN-PR-035`, `PLAN-PR-031`.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-060-what-the-pipeline-drops-on-the-way-out.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
