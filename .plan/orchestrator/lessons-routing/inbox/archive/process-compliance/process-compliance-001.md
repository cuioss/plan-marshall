envelope_version=1
sender_type=orchestrator
sender_id=process-compliance
epic=lessons-routing
kind=finding
created=2026-09-28T11:42:06Z

# Ledger regression: #1641 reverted this epic's state — restore from `88fcfc9ef`

**Sender:** `process-compliance` orchestrator, 2026-09-28. **Action required:** verify, then restore.

## What happened

PR #1641 (`945e59287`, "chore(orchestrator): land cross-epic ledger sync") was squash-merged onto main
**after** #1643 (`88fcfc9ef`), from a branch cut before #1643. Its body states it *held back* 20 deletions
"with no verifiable successor" — but the squash **deleted exactly those 20 files**, and additionally
reverted the PM-MCP-supersession edits #1643 had landed (spec banners, `epic.md` decision entries, anchor
blocks, queue statuses). Nobody flagged it at merge.

## What it changed in `.plan/orchestrator/lessons-routing/` (12 paths)

| Change | Path | Lines |
|---|---|---|
| `D` | `inbox/archive/review-apparatus/review-apparatus-001.md` | +0 / -147 |
| `M` | `plans/PLAN-LR-01-derive-the-corpus-and-the-audience-axis.md` | +0 / -6 |
| `M` | `plans/PLAN-LR-02-the-ownership-predicate-answers-the-wrong-question.md` | +0 / -6 |
| `M` | `plans/PLAN-LR-03-an-upstream-finding-becomes-an-issue.md` | +0 / -6 |
| `M` | `plans/PLAN-LR-04-route-the-corpus-that-is-already-stranded.md` | +0 / -6 |
| `M` | `plans/PLAN-LR-05-a-lesson-does-not-record-what-was-running-when-it-was-observed.md` | +0 / -6 |
| `M` | `queue-view.md` | +10 / -12 |
| `M` | `queue/PLAN-LR-01.json` | +1 / -1 |
| `M` | `queue/PLAN-LR-02.json` | +1 / -1 |
| `M` | `queue/PLAN-LR-03.json` | +1 / -1 |
| `M` | `queue/PLAN-LR-04.json` | +1 / -1 |
| `M` | `queue/PLAN-LR-05.json` | +1 / -1 |

(`D` = deleted, `M` = modified, `R` = renamed/moved. Deletion-only `M` rows are typically a stripped banner
or a removed decision / anchor block.)

## How to verify and restore

- See the damage: `git diff 945e59287^ 945e59287 -- .plan/orchestrator/lessons-routing/`
- Restore source: `88fcfc9ef` (the last commit carrying the full state). Only restore paths whose content has
  NOT been legitimately changed on main since — compare `git diff 88fcfc9ef origin/main -- <path>` against the
  #1641 diff first; a later drain or directive in this epic may have superseded part of it.
- ⚠ `queue/*.json` status regressions are not visible as deletion-only rows; diff them explicitly.

The `process-compliance` epic restored its own tree the same way (operator decision: each epic restores its own).
