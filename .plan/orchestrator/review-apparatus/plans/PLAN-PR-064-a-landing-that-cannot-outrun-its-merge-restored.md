# PLAN-PR-064: A landing message that cannot outrun its merge — restored whole

epic: review-apparatus
workstream: WS-04

> ⛔⛔ **SUPERSEDED 2026-09-18 — RETIRED AT THE COMPONENT RE-CUT. Do not emit this spec.**
>
> Its deliverables were carried, verbatim and as pointer rows, into: PLAN-PR-073 (D0/D1/D2/D3/D8 — the landing record and the PR body), PLAN-PR-074 (D4/D5 — the foreign gate), PLAN-PR-075 (D6 code half — the manage-metrics host/foreign split); D6 proposals moved to ORCHESTRATOR HOUSEKEEPING.
>
> **Why**: the nine theme specs were cut by SUBJECT, and every subject crossed the same components —
> `_findings_core.py` was declared by 7 of 9, `automatic-review/SKILL.md` by 6, `github_pr.py` by 5 — so
> no two could ever run concurrently and five plans would each have re-derived the same file. The re-cut
> is by component; no file is declared by two live plans.
>
> ⭐ **This file is NOT deleted**: it remains the authoritative pointer chain between a successor's
> `Carried from` column and the retired source spec holding each deliverable body, and it holds the
> claim labels the successors deliberately do not restate.

> Composed spec — **restores `PLAN-PR-028` as ONE plan and supersedes its two halves,
> `PLAN-PR-054` and `PLAN-PR-055`**, under the operator's 2026-09-12 decision to raise the split guard
> to **12 deliverables**.
>
> ⭐ **The split is retired because its stated cause is gone.** `PLAN-PR-028` was cut into `540a` /
> `540b` for exactly one reason — ten deliverables broke the ~6 guard. At twelve they fit, and the two
> halves shared a gate, a re-grounding obligation and the same finalize surface.
>
> ⛔ **Every deliverable body below lives in `PLAN-PR-028` and is NOT restated here** — that file was
> already the authoritative text of both halves, which pointed at it rather than retyping it. This spec
> points at the same place.

## Objective

Make finalize assert at completion only what it positively read: no landing for a run that did not
merge, and a foreign-PR gate that clears only on evidence.

## Why the halves are re-merged

- **One gate, split in two.** `PLAN-PR-054` D0 and `PLAN-PR-055` D0 are the same re-grounding pass over
  the same spec, each re-deriving the half of `PLAN-PR-028`'s symbol set its own deliverables named. One
  plan needs one gate.
- **One surface.** Both declare `manage-metrics/` and the `phase-6-finalize` tree; the landing half and
  the gate half meet at `emit-landing` and the archive step.
- **The ordering constraint survives the merge unchanged** — see § Dependencies.

## Deliverables

**D0 — GATE, mutates nothing.** Read `PLAN-PR-028` §§ Re-Grounding, Deliverables and Expected Surface,
and confirm each named SYMBOL still resolves at HEAD. ⛔ **Anchor on symbols, never on line numbers** —
the halves' own gates already found relayed line references that had moved while the mechanism held.
**HALT and report** if a named symbol has moved.

⛔ **`PLAN-PR-028` D0 is STRUCK** — do not run it, do not re-litigate it. The roster below starts at its
D1.

| # | Deliverable | Body lives at |
|---|---|---|
| D1 | The landing's claim is gated on a substantiated merge | `PLAN-PR-028` § D1 |
| D2 | The landing's facts are validated at the value level, carry their commit, exist once per run | `PLAN-PR-028` § D2 |
| D3 | The PR body and the retrospective name the tree they describe; a reader failure is not an answer | `PLAN-PR-028` § D3 |
| D4 | The foreign-PR gate clears only against a population it can prove was classified | `PLAN-PR-028` § D4 |
| D5 | The gate is proven where it bites, and its off-normal paths keep its contract's shape | `PLAN-PR-028` § D5 |
| D6 | Record the open lifecycle choices as proposals, and give the foreign column a consumer | `PLAN-PR-028` § D6 |

⛔ **`PLAN-PR-028` § "What is STRUCK" and § "What is CORRECTED" bind unchanged.** Implement the
corrected form, never the original, and do not re-open the struck items. ⛔ The SUPERSEDED block in that
file's header names the retired `540a`/`540b` split, not this plan — read this spec's provenance above
as its replacement.

⛔ **D6 is operator-gated** — it records proposals rather than deciding them, so it ends in an
`AskUserQuestion` and cannot run in a dispatched leaf.

**D8 — `pr merge-queue` reports an ATTEMPT as an OBSERVATION (lesson `2026-09-06-16-001`, absorbed
2026-09-18).** `_github_pr.py:2332-2339` returns `'enqueued': True` with `enqueue_corroboration` set
from the branch rule being active — never from a post-condition read of the PR itself. `isInMergeQueue`
and `mergeQueueEntry` occur in ZERO files across the `tools-integration-ci` and
`workflow-integration-github` script surfaces, so nothing in the tree can currently observe queue
membership. ⚠ `PLAN-PR-009` (#1087) fixed `cmd_pr_merge` and left this verb's corroboration untouched,
by its own landing record. *Done when:* `enqueued: true` is returned only on a read of the PR's own
queue state, and an unobservable state reports `indeterminate` rather than `true`. ⭐ The repo-level
GraphQL `mergeQueue.entries` read is the known-good membership query; `mergeStateStatus` reads `CLEAN`
while genuinely queued and is NOT a substitute.

**D3 amendment 2026-09-18 (lesson `2026-09-04-17-001`).** `pr_intent_section.py` is already on this
spec's Expected Surface for its `OSError`/exit-code collapse; the absorbed lesson adds a second defect
on the same file — the renderer **clips the PR Intent section at a byte offset**, and three properties
compose into a trap: the author is forbidden to size the draft, the renderer appends rather than
replaces, and `ci pr view` does not return the body, so the only repair is a full `ci pr edit` rewrite.
D3 additionally reports an overflow instead of truncating mid-sentence.

Nine deliverables, under the ceiling.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pr_intent_section.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/leaf-command-reference.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md`
- OBSERVED: `.claude/skills/finalize-step-review-retrospective/SKILL.md`
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_foreign_pr_gate.py`
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_pr_intent_section.py`
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_dispatch_roster_closure.py`
- OBSERVED: `test/plan-marshall/manage-solution-outline/test_survey_scope_declaration.py`
- OBSERVED: `test/plan-marshall/plan-orchestrator/`

## Claim Labels

- OBSERVED: this plan's claim set is `PLAN-PR-028` § Claim Labels together with the two halves' own
  sections, carried unchanged with their labels. Confirm/refute at those sections — they are the
  authoritative record and this plan re-states none of them.
- OBSERVED: the `540a`/`540b` split's stated cause was the ~6-deliverable guard, recorded in
  `PLAN-PR-028` § "MANDATORY SPLIT". Confirm/refute at that section — the cause is what the operator's
  12-deliverable decision removes.
- HYPOTHESIS: `PLAN-PR-028`'s symbol set still resolves at HEAD — confirm/refute at D0
  (verify-at-outline). ⛔ Both retired halves recorded a wide move window over this surface; a symbol
  that has moved re-scopes the deliverable that names it rather than being re-pointed by hand.

## Dependencies and Sequencing

- ⛔⛔ **Runs AFTER the launched `PLAN-PR-033`** — they collide on `foreign_pr_gate.py`, and PR-033's
  operator decisions BOUND what D4 and D5 may implement. This ordering is by decision, not by accident;
  it is inherited from the retired `PLAN-PR-054` and is unchanged by the re-merge.
- ⛔ **Overlaps `PLAN-PR-061` and `PLAN-PR-063`** on `branch-cleanup.md` and the retrospective —
  sequence, never pair.
- ⭐ **Internal order: D0 → D1/D2/D3 (the landing) → D4/D5 (the gate) → D6.**
- Supersedes: `PLAN-PR-054`, `PLAN-PR-055`. Restores: `PLAN-PR-028` (whose row stays retired — this
  spec is its queue-visible successor).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-064-a-landing-that-cannot-outrun-its-merge-restored.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
