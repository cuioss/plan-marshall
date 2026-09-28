envelope_version=1
sender_type=orchestrator
sender_id=process-compliance
epic=post-run-quality
kind=finding
created=2026-09-28T11:42:07Z

# Ledger regression: #1641 reverted this epic's state — restore from `88fcfc9ef`

**Sender:** `process-compliance` orchestrator, 2026-09-28. **Action required:** verify, then restore.

## What happened

PR #1641 (`945e59287`, "chore(orchestrator): land cross-epic ledger sync") was squash-merged onto main
**after** #1643 (`88fcfc9ef`), from a branch cut before #1643. Its body states it *held back* 20 deletions
"with no verifiable successor" — but the squash **deleted exactly those 20 files**, and additionally
reverted the PM-MCP-supersession edits #1643 had landed (spec banners, `epic.md` decision entries, anchor
blocks, queue statuses). Nobody flagged it at merge.

## What it changed in `.plan/orchestrator/post-run-quality/` (27 paths)

| Change | Path | Lines |
|---|---|---|
| `M` | `epic.md` | +14 / -27 |
| `D` | `inbox/archive/review-apparatus/review-apparatus-001.md` | +0 / -147 |
| `R` | `inbox/lessons-routing-001.md` | +? / -? |
| `R` | `inbox/lessons-routing-002.md` | +? / -? |
| `M` | `plans/PLAN-PRQ-01-retrospective-quality-chain-and-assessments-graded-at-report-time.md` | +0 / -6 |
| `M` | `plans/PLAN-PRQ-03-the-census-does-not-census-itself-and-a-re-check-persists-nothing.md` | +0 / -6 |
| `M` | `plans/PLAN-PRQ-04-an-obligation-that-outlives-its-plan-has-no-owner.md` | +0 / -6 |
| `M` | `plans/PLAN-PRQ-05-lessons-corpus-provenance-and-quality.md` | +0 / -6 |
| `M` | `plans/PLAN-PRQ-07-cross-repo-telemetry-archive-and-analyze.md` | +0 / -6 |
| `M` | `plans/PLAN-PRQ-08-two-dispatch-ledgers-disagree-and-terminal-spend-is-classified-as-waste.md` | +0 / -6 |
| `M` | `plans/PLAN-PRQ-09-retrospective-instruments-that-cannot-fire-and-recall-denominators-that-count-the-wrong-population.md` | +0 / -6 |
| `M` | `plans/PLAN-PRQ-10-finalize-refire-convergence-and-self-review-coverage-honesty.md` | +0 / -6 |
| `M` | `plans/PLAN-PRQ-11-spend-and-diagnostic-aspects-count-the-wrong-population-too.md` | +0 / -6 |
| `M` | `plans/PLAN-PRQ-12-the-reducer-never-marks-its-own-output-for-block-scalar-emission.md` | +0 / -6 |
| `M` | `queue-view.md` | +21 / -27 |
| `M` | `queue/PLAN-PRQ-01.json` | +1 / -1 |
| `M` | `queue/PLAN-PRQ-03.json` | +1 / -1 |
| `M` | `queue/PLAN-PRQ-04.json` | +1 / -1 |
| `M` | `queue/PLAN-PRQ-05.json` | +1 / -1 |
| `M` | `queue/PLAN-PRQ-07.json` | +1 / -1 |
| `M` | `queue/PLAN-PRQ-08.json` | +1 / -1 |
| `M` | `queue/PLAN-PRQ-09.json` | +1 / -1 |
| `M` | `queue/PLAN-PRQ-10.json` | +1 / -1 |
| `M` | `queue/PLAN-PRQ-11.json` | +1 / -1 |
| `M` | `queue/PLAN-PRQ-12.json` | +1 / -1 |
| `M` | `resume_anchor.md` | +0 / -4 |
| `D` | `settled.md` | +0 / -20 |

(`D` = deleted, `M` = modified, `R` = renamed/moved. Deletion-only `M` rows are typically a stripped banner
or a removed decision / anchor block.)

## How to verify and restore

- See the damage: `git diff 945e59287^ 945e59287 -- .plan/orchestrator/post-run-quality/`
- Restore source: `88fcfc9ef` (the last commit carrying the full state). Only restore paths whose content has
  NOT been legitimately changed on main since — compare `git diff 88fcfc9ef origin/main -- <path>` against the
  #1641 diff first; a later drain or directive in this epic may have superseded part of it.
- ⚠ `queue/*.json` status regressions are not visible as deletion-only rows; diff them explicitly.

The `process-compliance` epic restored its own tree the same way (operator decision: each epic restores its own).
