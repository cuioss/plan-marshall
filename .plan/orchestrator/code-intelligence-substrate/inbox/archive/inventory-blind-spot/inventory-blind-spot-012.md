envelope_version=1
sender_type=plan
sender_id=inventory-blind-spot
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T16:38:21Z

component=plan-marshall:manage-solution-outline
category=anti-pattern
bundle=plan-marshall
source_plan=inventory-blind-spot

# 12 argparse rejections in one plan, 4 of them guessing one script's surface

## Observation — this run

`script-failure-analysis` classified 12 non-zero-exit script calls, 10 unique. The distribution is not uniform — one script absorbs a third of them:

| script | rejections | invented shapes |
|--------|-----------:|-----------------|
| `manage-solution-outline` | 4 | `deliverables` (verb-paraphrase of `list-deliverables`), `--deliverable 1` (should be `--deliverable-number`), missing required `--deliverable-number`, plus one worktree-resolution error |
| `manage-findings` | 2 | `--resolution-detail` (should be `--detail`), one qgate-add shape error |
| `manage-architecture` | 2 | `--module plan-marshall` at top level, `--field skills_by_profile` |
| `automatic-review:review_completeness` | 2 | same rejection twice, 16 minutes apart |
| `manage-logging` | 1 | `read --level ERROR` |
| `phase_handshake` | 1 | exit-1 internal error (drift, not argparse) |

Each rejection is a wasted round trip inside a dispatched envelope, and each was recoverable only by re-reading the script's `--help`.

## Root cause

Two distinct causes, worth separating:

1. **Verb-paraphrase and flag-paraphrase** (`deliverables` for `list-deliverables`, `--deliverable` for `--deliverable-number`, `--resolution-detail` for `--detail`). These are the documented recurrence signatures in `agent-behavior-rules.md` — the invented name reads naturally in workflow prose but is not in the argparse `choices`. `manage-solution-outline` is disproportionately affected because its verb set contains both `read` and `list-deliverables` and `get-deliverable`, so the "obvious" short name is wrong three different ways.

2. **The same rejection repeated after 16 minutes** (`review_completeness check`, 15:22:09 and 15:38:46, byte-identical stderr). A loop-back re-fired the identical malformed call rather than correcting it — a blind retry of a known-failing invocation.

## Solution

- For (1): `manage-solution-outline` is the highest-value target for an argument-naming pass — either add argparse aliases for the natural short forms (`deliverables` -> `list-deliverables`, `--deliverable` -> `--deliverable-number`) the way `manage-lessons read` / `manage-tasks get` / `manage-status get` already do, or make the workflow docs that call it xref its `## Canonical invocations` block instead of restating the command.
- For (2): a loop-back that re-fires a step MUST NOT replay a call that failed with `exit_code: 2` on the previous iteration — argparse rejection is deterministic, so the retry cannot succeed.

## Generalisation

**An argparse rejection repeated verbatim across a retry boundary is never flaky.** Exit code 2 from argparse is a pure function of the argv; re-running it is guaranteed to fail identically. This is the provenance-before-retry principle applied at its cheapest possible instance — the ground truth is one `--help` call away.

## Impact

`manage-solution-outline` (4 of 10 unique failures, concentrated in phase-3-outline and phase-4-plan workflows), `automatic-review` loop-back path.
