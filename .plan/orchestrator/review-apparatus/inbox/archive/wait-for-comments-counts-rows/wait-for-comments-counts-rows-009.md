envelope_version=1
sender_type=plan
sender_id=wait-for-comments-counts-rows
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T17:45:06Z

# Derive the retrospective footprint from the merged commit when the worktree is gone

component: plan-marshall:plan-retrospective
category: bug
confidence: high
source_plan: wait-for-comments-counts-rows
source_pr: 1071

## Context

`check-artifact-consistency` (retrospective aspect 1) reported:

```
affected_files_recall,fail,Recall 0% below 70% threshold
  declared: 13
  found: 0
  recall_pct: 0.0
```

The true recall against the merged squash commit `7da89fa95` is **61.5%** (8 of 13 declared files in
a 12-file realized footprint). The 0% is entirely a measurement artifact: the aspect derives the
plan's footprint live from the plan's worktree (`{base}...HEAD` ∪ porcelain), and the worktree had
already been removed.

The removal is not an accident of this run — it is the scheduled order. `branch-cleanup` is
`order: 70` and removes the worktree; `plan-marshall:plan-retrospective` is `order: 995`. In the
default finalize step list the retrospective ALWAYS runs after the worktree is gone, so this
aspect's declared-vs-achieved coverage check is **structurally vacuous on every plan that reaches a
normal finalize** — it can only ever report 0% recall and a `fail`.

A gate that always fails for the same reason stops being read. The coverage contract this aspect is
supposed to implement (the deterministic item-coverage half of the thoroughness dial, graded to the
floor) is therefore not being measured at all.

## Root cause

The footprint derivation has one source (the worktree) and one legacy fallback
(`references.modified_files`, kept only for pre-ledger archived plans). Neither survives the ordering
the step is actually scheduled under. The aspect was presumably validated in a context where the
worktree still existed.

## Proposed action

Add a third derivation source, tried before the legacy fallback:

1. Worktree present → current behaviour.
2. Worktree absent AND the plan recorded a merged PR → derive from that PR's merge/squash commit
   (`git show --pretty=format: --name-only {sha}`), resolving the sha from the recorded `pr_number`
   or `worktree_branch`.
3. Legacy `references.modified_files`.

Additionally: when no source can produce a footprint, the aspect must report
`status: indeterminate` with a named reason — NOT `recall 0%`. A zero is a measurement; an absent
measurement must not be rendered as one. (Same failure shape as the sibling barrier lesson.)

## Evidence

- aspect: artifact_consistency — `affected_files_recall,fail,Recall 0% below 70% threshold`, `found: 0`, all 10 declared paths listed under `missing[]`.
- Realized footprint from `git show --pretty=format: --name-only 7da89fa95` → 12 files, of which 8 are among the 13 declared.
- `references.json` `affected_files` (7 entries) are ALL in the realized footprint — 100% recall on that narrower list, further confirming the 0% is derivation failure and not a real coverage miss.
- Step ordering: `default:branch-cleanup` `order: 70` (removes worktree) precedes `plan-marshall:plan-retrospective` `order: 995` in `manifest.phase_6.steps`.
