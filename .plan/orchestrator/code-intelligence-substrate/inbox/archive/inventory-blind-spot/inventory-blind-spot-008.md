envelope_version=1
sender_type=plan
sender_id=inventory-blind-spot
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T16:36:44Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall
source_plan=inventory-blind-spot

# Artifact-consistency reported 0% footprint recall because branch-cleanup had already deleted the worktree

## Observation — this run

`check-artifact-consistency` emitted, with no hedge:

```
affected_files_recall,fail,Recall 0% below 70% threshold
details.affected_files_recall: declared: 10, found: 0, recall_pct: 0.0
  missing[10]: <every one of the 10 declared files>
```

The true recall is **10/10 = 100%**. Deriving the footprint from the recorded SHAs directly:

```
git diff --name-only ef80c1c8...69f22701
```

returns exactly the 10 declared files, in order, with no omissions and no extras.

The aspect derives its footprint live from the plan's worktree. `branch-cleanup` is manifest step **16**; `plan-marshall:plan-retrospective` is step **17**. By the time the aspect runs, `.plan/local/worktrees/inventory-blind-spot` no longer exists, so the derivation returns the empty set — and the aspect reports the empty set as a *measured* 0%.

## Root cause

An absent input is being reported as a measured value of zero. The aspect has no way to distinguish "the worktree says nothing changed" from "there is no worktree to ask", and the SKILL's own coverage contract says this comparison is graded **to the floor** — so an unavailable input produces the worst possible grade with full confidence.

The documented fallback (`references.modified_files`) is described as being for "archived plans created before the ledger was removed", so it does not engage for a live plan whose worktree simply no longer exists.

## Solution

1. Make the derivation distinguish absent-input from empty-result: when the worktree path is gone, the check MUST report `skip` with an explicit `worktree_removed` reason, never `fail` with `recall 0%`.
2. Better: persist the resolved footprint at branch-cleanup time (the last moment it is cheaply knowable) into plan state, and have the aspect read that recorded fact. See the companion candidate-lesson on footprint persistence.
3. As a fallback, derive from `main_sha`...`head_at_completion` — both are already in `status.metadata` / `phase_steps` and both survive worktree removal.

## Generalisation

This is the **stale-cache-as-evidence** archetype in its purest form: a confident numeric answer computed over a data source that no longer exists. A 0% on a *floor-graded* dial is the maximum-severity output, so this failure mode does not degrade quietly — it produces the loudest possible wrong answer, in the component whose whole job is to detect wrong answers.

Pairs with the finalize-ordering lesson: both are the retrospective being positioned after the state it needs to observe has already been torn down.

## Impact

Every plan that runs the full finalize manifest with `branch-cleanup` before `plan-retrospective` — i.e. the default ordering — gets a false 0%-recall finding. The signal is currently worthless and actively misleading.
