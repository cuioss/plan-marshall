# PLAN-PR-057: A bot that COULD NOT review, and the refusal that should have said so

epic: review-apparatus
workstream: WS-01

> ⛔⛔ **SUPERSEDED 2026-09-18 — RETIRED AT THE COMPONENT RE-CUT. Do not emit this spec.**
>
> Its deliverables were carried, verbatim and as pointer rows, into: PLAN-PR-070 (D0/D1/D2/D3 — classification in both directions), PLAN-PR-069 (D5/D8/D9 — transport-failure classification and the executable remedy), PLAN-PR-074 (D7 — ci_timeout partitions build checks from review bots), PLAN-PR-076 (D11 — findings follow a split PR), PLAN-PR-067 (D10 — the waiter sees an in-place edit).
>
> **Why**: the nine theme specs were cut by SUBJECT, and every subject crossed the same components —
> `_findings_core.py` was declared by 7 of 9, `automatic-review/SKILL.md` by 6, `github_pr.py` by 5 — so
> no two could ever run concurrently and five plans would each have re-derived the same file. The re-cut
> is by component; no file is declared by two live plans.
>
> ⭐ **This file is NOT deleted**: it remains the authoritative pointer chain between a successor's
> `Carried from` column and the retired source spec holding each deliverable body, and it holds the
> claim labels the successors deliberately do not restate.

> Composed spec — **absorbs `PLAN-PR-048` and `PLAN-PR-052` whole**, under the operator's 2026-09-12
> decision to raise the split guard to **12 deliverables** and group staged work by shared target
> surface.
>
> ⛔ **Every deliverable body below lives in its SOURCE spec and is NOT restated here.** The sources
> are retired from the queue but remain the authoritative text. Follow the pointer; do not retype.

## Objective

Close the loop between a refusal and the score it produces: make the refusal say WHICH refusal it is
and survive being read later, and stop the five paths that let a bot which could not review be scored
as one that reviewed and found nothing.

## Why these were grouped

Derived from `corpus surfaces`: the two sources share **six** declared paths — `bot_registry.py`,
`review_completeness.py`, `bot-participation-contract.md`, `coderabbit.md`, `sourcery.md`,
`github_pr.py` — and `PLAN-PR-052`'s own sequencing note already named `PLAN-PR-048` D3 its **closest
neighbour**, asking for a re-check of D1/D3 against whatever PR-048 shipped first. That re-check is
what a merge removes: one plan cannot ship half of a classification and then re-derive the other half
against itself.

⛔ **Ingestion classifies; scoring consumes.** `PLAN-PR-048` D3 classifies a rate-limit notice as a
transport failure; `PLAN-PR-052` D1 discriminates WHICH condition it is. Shipped apart, the second
re-opens the first's records.

## Deliverables

**D0 — GATE, mutates nothing.** The merged re-grounding gate, carrying `PLAN-PR-052` D0 verbatim in
scope: re-ground all four refusal findings at HEAD, and for `PLAN-PR-052` defect 2 **derive** whether
`refusal_structural` is reachable at the shipped default configuration, publishing the configuration
population walked. Additionally re-ground `PLAN-PR-048`'s five scoring paths. **HALT and report** if
any no longer reproduces. ⛔ An unreachability claim asserted from one configuration is the
vacuous-authority archetype this epic keeps re-finding.

| # | Deliverable | Body lives at |
|---|---|---|
| D1 | Classify a bot's publication correctly **in BOTH directions** — three artifact classes fool a "the bot commented" predicate, a FOURTH (a thread acknowledgement) is credited as a fresh review, and inversely a genuine clean verdict is read as NO participation into an unclearable `participated_stale` | `PLAN-PR-048` §§ D0 + D0a + D0b |
| D2 | A force-done override of `absent` must cite evidence the review HAPPENED | `PLAN-PR-048` § D1 |
| D3 | An unregistered bot kind must fail LOUD, not be force-done past | `PLAN-PR-048` § D1a |
| D4 | A paced wait is an orchestrator-tier primitive | `PLAN-PR-048` § D2 |
| D5 | Rate-limit notices are TRANSPORT FAILURES, classified at ingestion | `PLAN-PR-048` § D3 |
| D6 | Sourcery's refusal shapes are three, each misclassified differently | `PLAN-PR-048` § D3a |
| D7 | A review bot is not a build check, and today it is counted as both | `PLAN-PR-048` § D4 |
| D8 | Classify the refusal by CONDITION, and make the named remedy executable | `PLAN-PR-052` § D1 |
| D9 | Make `refusal_structural` reachable, or delete it | `PLAN-PR-052` § D2 |
| D10 | Capture a refusal body at ingestion, and make the waiter see an in-place edit | `PLAN-PR-052` §§ D3 + 3a |
| D11 | Follow the split — findings and participation records reach the successor PRs | `PLAN-PR-052` § D4 |

D10 merges `PLAN-PR-052`'s D3 and its 3a because they are one subject stated twice — the mutable
refusal as an archival problem and as a live-wait problem. ⛔ The merge is a **numbering** change only:
both bodies stand, and both *Done when* clauses must be satisfied.

Twelve deliverables: at the ceiling. ⛔ **Absorb no thirteenth.**

⚠ **The 2026-09-13 fold was ABSORBED INTO D1 rather than added as a thirteenth row, and that choice is
recorded because it is a scope change, not a formatting one.** `PLAN-PR-048` § D0b (a clean review read
as no participation) is the INVERSE of D0's direction, so D1 now carries both — a classifier that is
wrong in one direction and corrected only there will simply fail in the other. ⛔ D1 is consequently the
heaviest deliverable in this plan: if D0 finds the two directions need separate mechanisms, **split D1
and drop something else**, rather than shipping half a classifier.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_verify.py`
- OBSERVED: `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py`
- OBSERVED: `test/plan-marshall/automatic-review/`
- OBSERVED: `test/plan-marshall/workflow-integration-github/`
- OBSERVED: `test/plan-marshall/phase-6-finalize/`

## Claim Labels

- OBSERVED: this plan's claim set is exactly the union of `PLAN-PR-048` § Claim Labels and
  `PLAN-PR-052` § Claim Labels, carried unchanged with their labels. Confirm/refute at those two
  sections — they are the authoritative record and this plan re-states none of them.
- OBSERVED: `PLAN-PR-052` § Dependencies names `PLAN-PR-048` D3 its closest neighbour and asks for a
  re-check if PR-048 lands first. Confirm/refute at that section.
- HYPOTHESIS: `refusal_structural` is unreachable at the shipped default configuration — confirm/refute
  at `automatic-review/scripts/review_completeness.py` § the escalation-class selection
  (verify-at-outline). ⛔ D0 derives this over the configuration population rather than asserting it.
- ⛔ RETRACTED, do not re-derive: *"closing and reopening a PR pushes the CodeRabbit window."* The
  window is org-scoped; see `PLAN-PR-052` § Problem for the same-instant ETA evidence.

## Dependencies and Sequencing

- ⛔ **Overlaps `PLAN-PR-056`, `PLAN-PR-058` and `PLAN-PR-059`** on the `automatic-review` and
  `github_pr` families — sequence, never pair.
- ⭐ **Internal order: D0 → D5/D6/D8 (ingestion classification) → D1/D2/D3/D7 (scoring) → D9/D10/D11.**
  Scoring reads the verdicts ingestion produces, so ingestion lands first.
- Supersedes: `PLAN-PR-048`, `PLAN-PR-052`.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-057-a-bot-that-could-not-review-and-the-refusal-that-says-so.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
