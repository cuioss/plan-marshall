# PLAN-PR-061: "Reviewed at all", and every number computed from it

epic: review-apparatus
workstream: WS-03

> ⛔⛔ **SUPERSEDED 2026-09-18 — RETIRED AT THE COMPONENT RE-CUT. Do not emit this spec.**
>
> Its deliverables were carried, verbatim and as pointer rows, into: PLAN-PR-071 (D0/D1/D3/D4/D5/D6/D8 — the handoff and its numbers), PLAN-PR-070 (D11/D13 — publish-shape reconciliation and one config reader), PLAN-PR-069 (D9 — the refusal mode), PLAN-PR-067 (D10 — the actionable-count classifier), PLAN-PR-076 (D2 — the retrospective grade); D7 moved to ORCHESTRATOR HOUSEKEEPING (operator-decision record, no diff).
>
> **Why**: the nine theme specs were cut by SUBJECT, and every subject crossed the same components —
> `_findings_core.py` was declared by 7 of 9, `automatic-review/SKILL.md` by 6, `github_pr.py` by 5 — so
> no two could ever run concurrently and five plans would each have re-derived the same file. The re-cut
> is by component; no file is declared by two live plans.
>
> ⭐ **This file is NOT deleted**: it remains the authoritative pointer chain between a successor's
> `Carried from` column and the retired source spec holding each deliverable body, and it holds the
> claim labels the successors deliberately do not restate.

> Composed spec — **absorbs `PLAN-PR-026` and `PLAN-PR-047` whole**, under the operator's 2026-09-12
> decision to raise the split guard to **12 deliverables** and group staged work by shared target
> surface.
>
> ⛔ **Every deliverable body below lives in its SOURCE spec and is NOT restated here.** The sources
> are retired from the queue but remain the authoritative text. Follow the pointer; do not retype.

## Objective

Separate *nobody reviewed* from *reviewed and found nothing* on every surface that claims to
distinguish them — and then make the counting stages that consume that distinction compute from inputs
somebody actually persisted.

## Why these were grouped

Derived from `corpus surfaces`: both declare `review_completeness.py`, the review-retrospective script
and SKILL, `bot_registry.py` and both test trees. The subject link is a **producer/consumer pair**:
`PLAN-PR-026` D1 builds the reviewed-at-all handoff, and `PLAN-PR-047` D0 is *"persist the
reviewed-at-all classification where a post-merge step can read it"* — the same fact, one step later.
⛔ Two plans writing one handoff from both ends is how two producers come to disagree, which is the
defect class this epic keeps finding. D1 below therefore carries BOTH bodies.

## Deliverables

**D0 — GATE, mutates nothing.** `PLAN-PR-026` D0 verbatim in scope: derive the handoff's populations
and its persistence channel, or HALT. The derivation now also has to satisfy `PLAN-PR-047` D0's
post-merge reader, because the persisted classification is the same artifact.

| # | Deliverable | Body lives at |
|---|---|---|
| D1 | Build the reviewed-at-all handoff, producer to consumer — **and persist it where a post-merge step can read it** | `PLAN-PR-026` § D1 **+** `PLAN-PR-047` § D0 |
| D2 | Make the `comparison` grade compute over the populations it names | `PLAN-PR-026` § D2 |
| D3 | Stop rendering an empty required population as a positive result | `PLAN-PR-026` § D3 |
| D4 | The same collapse at the QUORUM layer, not just the per-bot layer | `PLAN-PR-026` § D3a |
| D5 | Bound and de-glyph every operator-facing string these surfaces render | `PLAN-PR-026` § D4 |
| D6 | Replace guards that cannot fail with guards derived from behaviour | `PLAN-PR-026` § D5 |
| D7 | Record three open decisions instead of taking them | `PLAN-PR-026` § D6 |
| D8 | Model the reviewed tree per ROUND, not once per PR | `PLAN-PR-047` § D1 |
| D9 | Give a stored refusal its MODE — the two modes have different remedies | `PLAN-PR-047` § D2 |
| D10 | Exclude a RECOGNISED refusal from `actionable_count` | `PLAN-PR-047` § D3 |
| D11 | Reconcile declared `publish_shape` against the observed one, and REPORT the divergence | `PLAN-PR-047` § D4 |

D1 merges two bodies for the reason stated above; both *Done when* clauses must be satisfied. ⛔ The
merge is a numbering change, not a scope reduction.

⛔ **D7 is operator-gated** — it records decisions rather than taking them, so it ends in an
`AskUserQuestion` and cannot run in a dispatched leaf.

**D13 — One reader for the reviewer-classification config (lesson `2026-09-05-07-009`, absorbed
2026-09-18).** Two readers of `required_bots` / `optional_bots` take **opposite dispositions on the same
unregistered token**: the shared contract refuses with `unregistered_kind`, while the second reader
folds the token into three participation-ratio denominators with no row of its own — so a typo'd bot
name blocks in one place and silently inflates a ratio in the other. The concrete instance closed in-run
(#1416 TASK-007, finding `e4aea1`); the structural half never did. *Done when:* the classification config
is read through ONE shared surface whose refusals every consumer inherits, and a test proves an
unregistered token reaches the same disposition on both paths. ⚠ Sits beside `epic.md`'s standing
`bot_kind`-rename-with-no-propagation entry — the same config, the same absence of a shared reader.

Thirteen deliverables. ⚠ The 12 ceiling is a **guideline, not a hard limit** (operator ruling 2026-09-15):
up to ~14 is acceptable when the aspects fit together — so a thirteenth is admissible only if it belongs
to the reviewed-at-all handoff this plan builds, never as a convenient home for an unrelated finding.

**Evidence amendment 2026-09-15** (from
[`findings/2026-09-15-pr-agent-vs-coderabbit-vs-sourcery.md`](../findings/2026-09-15-pr-agent-vs-coderabbit-vs-sourcery.md);
sizes D0's populations and supplies D1/D3/D4 negative controls — adds no deliverable, because every item
feeds an existing one):

- ⭐ **The collapsed state is the MAJORITY case, now at n = 156.** 152 of 156 pr-agent guides (97.4%) are
  the canned "No major issues / No security concerns" table; paired recall against CodeRabbit is 4 of
  123. A canned guide and a real clean review remain indistinguishable to every consumer D1 feeds.
- ⛔ **21 PRs had no baseline reviewer at all, 6 of them merged** (`plan-marshall` `#1380`, `#1406`,
  `#1407`, `#1438`; `API-Sheriff` `#288`, `#300`) — their only posted review is a canned guide. These are
  the D3/D4 fixtures: an empty required population rendered as positive.
- **Three distinct "nobody reviewed" shapes D1's handoff must keep apart from "reviewed clean":**
  - *never triggered* — `cui-http#185`: zero `pull_request`-event runs across every workflow for the
    opening window; the first runs follow a force-push `pr-agent.yml` does not subscribe to;
  - *re-review failed silently* — `plan-marshall#1479`: the `/review` re-review failed at step "Generate
    Review Token" and never recovered, so the guide shows only the opening commit;
  - *run stuck* — pr-agent run `34748813129` (issue_comment, `#1477`) `queued` since
    2026-09-13T09:01:19Z.
- **D9 (refusal MODE) has a measured split:** CodeRabbit refused-only on 22 PRs — 20 rate (expires), 2
  size (`#1407`, `#1432`, never expires); Sourcery quota on 103 PRs, size on 34, and a review on only 40
  of 181.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_gate_delta.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`
- OBSERVED: `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py`
- OBSERVED: `.claude/skills/finalize-step-review-retrospective/SKILL.md`
- OBSERVED: `test/plan-marshall/automatic-review/`
- OBSERVED: `test/plan-marshall/finalize-step-review-retrospective/`

## Claim Labels

- OBSERVED: this plan's claim set is exactly the union of `PLAN-PR-026` § Claim Labels and
  `PLAN-PR-047` § Claim Labels, carried unchanged with their labels. Confirm/refute at those two
  sections — they are the authoritative record and this plan re-states none of them.
- OBSERVED: `PLAN-PR-026` D1 and `PLAN-PR-047` D0 name the same artifact from the producing and the
  consuming side. Confirm/refute by reading both bodies — this is why D1 carries the pair.
- OBSERVED: the clean-barrier work-log line states a zero over ONE finding type without its
  population, rendered by the clean path D4 rewrites. Confirm/refute at
  `phase-6-finalize/standards/branch-cleanup.md` § the pre-merge barrier's clean message. Re-read
  first-party at `356973d80` during the 2026-09-11 inbox drain.
- HYPOTHESIS: one persistence channel serves both the in-run consumer and the post-merge reader —
  confirm/refute at D0 (verify-at-outline). If they need different channels, D1 splits rather than
  shipping a channel only one side can read.
- OBSERVED (corpus pass 2026-09-15, not re-read first-party): 152 of 156 pr-agent guides in the window
  are the canned table, and 21 PRs had no baseline reviewer (6 merged). Confirm/refute at D0 by
  re-deriving over the named PRs.
- OBSERVED (corpus pass 2026-09-15, not re-read first-party): `cui-http#185` was never triggered,
  `plan-marshall#1479`'s re-review failed at "Generate Review Token", and run `34748813129` has sat
  `queued` since 2026-09-13. Confirm/refute at each run's Actions record (query runs UNFILTERED by
  branch — `review-practice.md` § 1).

## Dependencies and Sequencing

- ⛔ **Overlaps `PLAN-PR-056`, `PLAN-PR-057`, `PLAN-PR-058` and `PLAN-PR-062`** on
  `review_completeness.py` and the retrospective — sequence, never pair.
- ⭐ **Internal order: D0 → D1 (the handoff) → D2/D3/D4 (what reads it) → D8–D11 (what counts it) →
  D5/D6/D7.**
- Supersedes: `PLAN-PR-026`, `PLAN-PR-047`.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-061-reviewed-at-all-and-the-numbers-computed-from-it.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
