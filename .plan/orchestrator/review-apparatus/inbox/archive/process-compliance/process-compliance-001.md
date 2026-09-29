envelope_version=1
sender_type=orchestrator
sender_id=process-compliance
epic=review-apparatus
kind=finding
created=2026-09-28T11:42:08Z

# Ledger regression: #1641 reverted this epic's state — restore from `88fcfc9ef`

**Sender:** `process-compliance` orchestrator, 2026-09-28. **Action required:** verify, then restore.

## What happened

PR #1641 (`945e59287`, "chore(orchestrator): land cross-epic ledger sync") was squash-merged onto main
**after** #1643 (`88fcfc9ef`), from a branch cut before #1643. Its body states it *held back* 20 deletions
"with no verifiable successor" — but the squash **deleted exactly those 20 files**, and additionally
reverted the PM-MCP-supersession edits #1643 had landed (spec banners, `epic.md` decision entries, anchor
blocks, queue statuses). Nobody flagged it at merge.

## What it changed in `.plan/orchestrator/review-apparatus/` (56 paths)

| Change | Path | Lines |
|---|---|---|
| `M` | `epic.md` | +4 / -36 |
| `D` | `findings/2026-09-26-pm-mcp-carry-over.md` | +0 / -150 |
| `R` | `inbox/ledger-decomposition-and-row-vocabulary-001.md` | +? / -? |
| `M` | `plans/PLAN-PR-002-org-empty-review-guard-too-broad.md` | +2 / -47 |
| `M` | `plans/PLAN-PR-039-the-workflow-assembles-the-charter.md` | +0 / -3 |
| `M` | `plans/PLAN-PR-068-the-response-path-and-what-it-drops.md` | +0 / -6 |
| `M` | `plans/PLAN-PR-069-refusal-recognition-and-the-rate-window.md` | +0 / -6 |
| `M` | `plans/PLAN-PR-070-participation-and-what-the-gate-may-credit.md` | +0 / -6 |
| `M` | `plans/PLAN-PR-071-reviewed-at-all-and-the-numbers.md` | +0 / -6 |
| `M` | `plans/PLAN-PR-072-the-findings-store-and-its-dispositions.md` | +0 / -6 |
| `M` | `plans/PLAN-PR-073-the-landing-record-and-the-pr-body.md` | +0 / -6 |
| `M` | `plans/PLAN-PR-074-the-merge-gate-and-the-finalize-dispatcher.md` | +0 / -6 |
| `M` | `plans/PLAN-PR-075-the-telemetry-channels-of-finalize.md` | +0 / -6 |
| `M` | `plans/PLAN-PR-076-the-retrospective-and-what-it-can-establish.md` | +0 / -6 |
| `M` | `plans/PLAN-PR-077-the-gate-before-the-wait-region.md` | +0 / -6 |
| `M` | `queue-view.md` | +79 / -73 |
| `M` | `queue/PLAN-PR-002.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-026.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-029.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-030.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-031.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-035.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-037.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-039.json` | +2 / -2 |
| `M` | `queue/PLAN-PR-040.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-043.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-045.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-047.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-048.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-049.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-050.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-051.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-052.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-053.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-054.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-055.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-056.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-057.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-058.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-059.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-060.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-061.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-062.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-063.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-064.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-068.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-069.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-070.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-071.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-072.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-073.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-074.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-075.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-076.json` | +1 / -1 |
| `M` | `queue/PLAN-PR-077.json` | +1 / -1 |
| `M` | `resume_anchor.md` | +0 / -31 |

(`D` = deleted, `M` = modified, `R` = renamed/moved. Deletion-only `M` rows are typically a stripped banner
or a removed decision / anchor block.)

## How to verify and restore

- See the damage: `git diff 945e59287^ 945e59287 -- .plan/orchestrator/review-apparatus/`
- Restore source: `88fcfc9ef` (the last commit carrying the full state). Only restore paths whose content has
  NOT been legitimately changed on main since — compare `git diff 88fcfc9ef origin/main -- <path>` against the
  #1641 diff first; a later drain or directive in this epic may have superseded part of it.
- ⚠ `queue/*.json` status regressions are not visible as deletion-only rows; diff them explicitly.

The `process-compliance` epic restored its own tree the same way (operator decision: each epic restores its own).
