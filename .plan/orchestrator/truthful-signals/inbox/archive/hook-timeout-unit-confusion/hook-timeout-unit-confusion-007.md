envelope_version=1
sender_type=plan
sender_id=hook-timeout-unit-confusion
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T20:57:34Z

# Coverage aspect is structurally dead for every worktree plan under the current step order

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=hook-timeout-unit-confusion
source_pr=1131

## Context

`check-artifact-consistency` is the declared-vs-achieved coverage comparison — the deterministic
item-coverage half of the thoroughness dial, graded to the floor. On this plan it returned:

```
affected_files_recall,inconclusive,"Plan footprint could not be resolved (no live worktree diff and no modified_files key) — recall is unmeasurable, not 0%"
affected_files_exact_match,inconclusive,"Plan footprint could not be resolved … the comparison substantiates no verdict"
```

The script's honesty here is exemplary — it reports `inconclusive` and states that recall is
*unmeasurable, not 0%*, and it sets `footprint_resolved: false`. The problem is that this is not a
plan-specific accident. It is the guaranteed outcome for every worktree plan under the current
finalize order:

| Order | Step |
|---|---|
| 13 | `default:branch-cleanup` — *"branch + worktree removed"* |
| 17 | `plan-marshall:plan-retrospective` |

The aspect derives the footprint live from the plan's worktree (`{base}...HEAD` ∪ porcelain), falling
back to the legacy `references.modified_files` key only for older archived plans. `modified_files`
was removed with the change ledger. So on any plan with `use_worktree: true` — the default — the
worktree is gone four steps before the aspect runs, and both coverage checks return `inconclusive`
every time.

`project:finalize-step-lessons-housekeeping` hit the same wall from the other side and worked around
it, logging at `15:10:15Z`: *"references.modified_files absent, footprint derived from git diff
main...HEAD"*. So one finalize step already solved this problem locally while the aspect whose whole
purpose is the footprint comparison did not.

Here the footprint was trivially recoverable and the answer would have been a clean pass: the merged
commit `6053382ab` touches exactly the 10 paths `references.affected_files` declares — a perfect
declared-vs-realized match, one of the better coverage results this epic has seen. The retrospective
could not say so.

## Root cause

The footprint resolver depends on a live worktree, and the step that removes the worktree runs
earlier in the same phase. The dependency is on an ephemeral artifact when a durable one (the plan's
commit range on the branch, or the merged commit) carries the same information and outlives the
worktree by design.

## Proposed action

1. Add a git-derived footprint arm ahead of the `inconclusive` return. In order of preference:
   the plan's own commit range (`{base_ref}...{head_sha}` from `status.metadata.worktree_sha` /
   `main_sha`, both of which this plan's `status.json` carries), then the merged PR commit resolved
   from the `create-pr` step record, then the live worktree, then `references.modified_files`.
2. Keep the `inconclusive` branch and its wording — it is correct and should survive as the genuine
   could-not-look state. What must change is how often it is reached.
3. Consider whether `plan-marshall:plan-retrospective` should simply run **before**
   `default:branch-cleanup`. That is the cheaper fix if nothing in the aspect depends on the merge
   having happened; note that the sibling `project:finalize-step-review-retrospective` (order 16) has
   the opposite requirement, so the two may not be movable together.

## Evidence

- `work/fragment-artifact-consistency.toon` — both checks `inconclusive`,
  `details.affected_files_recall.footprint_resolved: false`, `declared: 11`, `deliverables: 2`.
- `execution.toon` `phase_6.steps` — `branch-cleanup` at index 12, `plan-marshall:plan-retrospective`
  at index 16.
- `status.metadata.phase_steps["6-finalize"]["branch-cleanup"].display_detail` — *"PR #1131 merged via
  merge queue, main pulled, branch + worktree removed"*.
- `logs/work.log` `15:10:15Z` — lessons-housekeeping's own git-derived workaround for the same gap.
- `git show --name-only 6053382ab` — 10 paths, set-equal to `references.affected_files`.

## Why this belongs to truthful-signals

A check that can only ever return "unmeasurable" is indistinguishable, in every aggregate that counts
it, from a check that ran. This one is careful enough to say so — `inconclusive`, not `0%` — which is
precisely why it is worth fixing rather than deleting: the honesty is already there, the capability
is what is missing. And it is the coverage half of the thoroughness contract, so its silence removes
the one deterministic input the floor-graded self-report is meant to be graded against.
