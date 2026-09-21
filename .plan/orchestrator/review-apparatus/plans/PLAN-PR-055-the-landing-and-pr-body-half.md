# PLAN-PR-055: The landing and PR-body half — `540b`, the second half of PLAN-PR-028's mandatory split

> ⛔⛔ **SUPERSEDED 2026-09-12 by `PLAN-PR-064` — do NOT emit this spec.** ⭐ **The split this file
> implements is RETIRED because its stated cause is gone**: `PLAN-PR-028` was cut into `540a` / `540b`
> only because ten deliverables broke the ~6 guard, and the operator raised that guard to 12. The whole
> of `PLAN-PR-028` is restored as one plan, carrying this half's D1/D2/D3 and D6 `080` items. ⛔ **This
> file is NOT dead and is NOT deleted**: it records why the split existed and what it scoped. The
> authoritative deliverable text was always `PLAN-PR-028`'s, and `PLAN-PR-064` points there.

epic: review-apparatus
workstream: WS-04

> ⛔⛔ **SPLIT SPEC. This is `540b` of the mandatory `540a` / `540b` split recorded in
> `PLAN-PR-028-a-landing-message-that-cannot-outrun-its-merge.md` § "MANDATORY SPLIT".** Performed by
> the 2026-09-08 `cleanup` pass (A5, redistribution).
>
> ⛔ **The deliverable BODIES are NOT retyped here.** `PLAN-PR-028` stays on disk as the audit record
> and remains the authoritative text for every deliverable this spec carries. The implementing plan
> **READS them from that file** — a deterministic file read, never a reconstruction from this summary.
>
> `PLAN-PR-028` itself is now **superseded by `PLAN-PR-054` and this spec**, and is never emitted whole.

## Objective

Make a landing message assert only what it positively read, and make the PR body's as-of line and the
reader-failure distinction honest.

## Deliverables carried

| From `PLAN-PR-028` | Subject |
|---|---|
| **D1** | the landing's claim, its headline forms, the Branch F re-entry sentence, the `failed_outcome_strategy` citation, and the terminal-branch mapping table |
| **D2** | landing uniqueness, value-level completeness, the SHA key, the payload contract and the per-plan invariant |
| **D3** | the reader-failure distinction, the PR body's as-of line, and the retrospective artifact's as-of line |
| **D6's `080` items** | the coverage figure's host/foreign split, for the `080` half only |

⛔ **D0 is STRUCK** in the source spec, so this half inherits **NO halt gate** — its count derivations
are stated as facts in `PLAN-PR-028` § Re-Grounding. **Read that section; do not re-derive it.**

⚠⚠ **This half's surface is the one #1338 and #1344 BOTH moved**, so `PLAN-PR-028` requires it to
**re-derive every line reference at outline.** ⭐ And that window has since widened enormously: the
2026-09-08 cleanup measured **1005 paths moved** between `cc5ea40a1` and HEAD `b64db6671`, of which
**56 intersect this spec's declared surface** — the largest intersection of any staged spec in the
corpus. Treat every line reference in the source text as stale until re-derived.

**D0 (this spec) — GATE, mutates nothing.** Re-derive each line reference `PLAN-PR-028`'s D1/D2/D3
bodies cite, anchoring on **symbols, never line numbers**. **HALT and report** if a cited symbol no
longer resolves. ⭐ This pass found the `head_sha_verified` coordinates stale in *two* independent
records while the mechanism held — the same failure mode this gate exists to catch.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pr_intent_section.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/`
- OBSERVED: `.claude/skills/finalize-step-review-retrospective/SKILL.md`
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_pr_intent_section.py`
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_dispatch_roster_closure.py`
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_landing_completeness.py`
- OBSERVED: `test/plan-marshall/plan-orchestrator/`

⛔ **Epic-tree record, NOT repository source — read input only**, reaching no PR diff:
`../cloud-runs/080-landing-message-carries-the-outcome-post-merge/report-01.md`.

## Claim Labels

- OBSERVED: the split is recorded as **settled, not proposed**, in `PLAN-PR-028` § "MANDATORY SPLIT".
- OBSERVED: `PLAN-PR-028` records this half's surface as **moved by both #1338 and #1344**, requiring
  a line-reference re-derivation at outline.
- OBSERVED (2026-09-08 cleanup, first-party): **56 of this spec's 26 declared entries' paths moved**
  in the `cc5ea40a1..b64db6671` window of 1005 paths — the corpus's largest intersection.
- OBSERVED: `PLAN-PR-028`'s D0 is struck, so this half carries no halt gate from it.
- ⭐⭐ **CORROBORATED IN THE INTERVAL — this spec's subject reproduced FOUR times while it sat staged.**
  `landings/PLAN-PR-032.md` (the `pr` fact named an unmerged PR), `landings/PLAN-PR-036.md` (a single
  `pr` key could not express a two-PR split landing), `landings/PLAN-PR-025B.md` (a recovery replaced
  its own PR and no step re-recorded it), and this epic's `create-pr` producer-gap Open Defect. ⛔ **Do
  not treat D1/D2 as unverified: the landing-fact defects are observed, repeatedly, on this epic's own
  plans.**
- HYPOTHESIS: the terminal-branch mapping table D1 specifies still matches the registered step set —
  confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`
  § the registered-step roster (verify-at-outline).

## Dependencies and Sequencing

- ⛔⛔ **`PLAN-PR-054` (`540a`) MUST LAND FIRST.** `PLAN-PR-028`'s own sequencing note: D1's mapping
  table wants the derived terminal-branch set D4/D5 will already have read. **This spec is NOT
  emittable until `PLAN-PR-054` lands.**
- ⛔ **Overlaps `PLAN-PR-050`** on `phase-6-finalize/SKILL.md` and `dispatch-inline-split.md`, and
  **`PLAN-PR-051`** on `branch-cleanup.md` — **sequence, never pair.**
- ⛔ Overlaps `PLAN-PR-054` on `phase-6-finalize` docs and `manage-metrics/`; the sequencing above
  already forbids pairing them.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-055-the-landing-and-pr-body-half.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
