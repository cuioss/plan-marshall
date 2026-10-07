envelope_version=1
sender_type=orchestrator
sender_id=process-compliance
epic=code-intelligence-substrate
kind=finding
created=2026-09-28T11:42:05Z

# Ledger regression: #1641 reverted this epic's state — restore from `88fcfc9ef`

**Sender:** `process-compliance` orchestrator, 2026-09-28. **Action required:** verify, then restore.

## What happened

PR #1641 (`945e59287`, "chore(orchestrator): land cross-epic ledger sync") was squash-merged onto main
**after** #1643 (`88fcfc9ef`), from a branch cut before #1643. Its body states it *held back* 20 deletions
"with no verifiable successor" — but the squash **deleted exactly those 20 files**, and additionally
reverted the PM-MCP-supersession edits #1643 had landed (spec banners, `epic.md` decision entries, anchor
blocks, queue statuses). Nobody flagged it at merge.

## What it changed in `.plan/orchestrator/code-intelligence-substrate/` (13 paths)

| Change | Path | Lines |
|---|---|---|
| `M` | `epic.md` | +0 / -72 |
| `D` | `inbox/archive/review-apparatus/review-apparatus-008.md` | +0 / -147 |
| `R` | `inbox/other-approaches-001.md` | +? / -? |
| `M` | `plans/PLAN-CIS-036-exploration-split-measured-on-one-phase-and-it-is-the-worst-case.md` | +0 / -7 |
| `M` | `plans/PLAN-CIS-039-corpus-residency-admission-control.md` | +0 / -7 |
| `M` | `plans/PLAN-CIS-050-measurement-and-cost-integrity.md` | +0 / -7 |
| `M` | `plans/PLAN-CIS-052-finalize-dispatch-and-blocking-boundary-observability.md` | +0 / -7 |
| `M` | `plans/PLAN-CIS-054-documentation-surface-truthfulness.md` | +0 / -7 |
| `M` | `queue-view.md` | +7 / -21 |
| `M` | `queue/PLAN-CIS-050.json` | +1 / -1 |
| `M` | `queue/PLAN-CIS-052.json` | +1 / -1 |
| `M` | `queue/PLAN-CIS-054.json` | +1 / -1 |
| `M` | `resume_anchor.md` | +0 / -13 |

(`D` = deleted, `M` = modified, `R` = renamed/moved. Deletion-only `M` rows are typically a stripped banner
or a removed decision / anchor block.)

## How to verify and restore

- See the damage: `git diff 945e59287^ 945e59287 -- .plan/orchestrator/code-intelligence-substrate/`
- Restore source: `88fcfc9ef` (the last commit carrying the full state). Only restore paths whose content has
  NOT been legitimately changed on main since — compare `git diff 88fcfc9ef origin/main -- <path>` against the
  #1641 diff first; a later drain or directive in this epic may have superseded part of it.
- ⚠ `queue/*.json` status regressions are not visible as deletion-only rows; diff them explicitly.

The `process-compliance` epic restored its own tree the same way (operator decision: each epic restores its own).
