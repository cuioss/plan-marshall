envelope_version=1
sender_type=plan
sender_id=inbox-sequence-reuse-collides-with-the-archive
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T15:12:23Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall

# Artifact-consistency reports 0% recall because branch-cleanup already deleted the worktree

`check-artifact-consistency` derives the plan footprint **live from the plan's
worktree** (`{base}...HEAD` union porcelain). On this plan it reported:

```
affected_files_recall,fail,Recall 0% below 70% threshold
declared: 8
found: 0
missing[8]: <all eight declared files>
```

The declared set was in fact **exactly right**: merged commit `89fd4d1f6`
(PR #1034) touched precisely those 8 files — 100% recall, zero scope creep. The
0% is entirely an artefact of *when* the aspect ran.

## Root cause — an ordering guarantee, not a race

In `phase-6-finalize`, `default:branch-cleanup` (order 70) removes the worktree.
`plan-marshall:plan-retrospective` sorts **after** it. So on every plan with
`use_worktree=true`, the retrospective's footprint derivation is guaranteed to
find no worktree. This is not intermittent — it is structural, and it will report
`recall 0%` and `fail` on every such plan.

The failure is loud in the wrong direction: a reader sees an error-shaped
`affected_files_recall FAIL` with all eight declared files listed as "missing"
and reasonably concludes the plan under-delivered. The measurement instrument
broke, and it reported the breakage as a finding about the plan.

## Corrective action

Snapshot the resolved footprint into the plan directory **while the worktree
still exists** — the natural point is the `default:push` barrier or `create-pr`,
both of which already have the settled HEAD — and have
`check-artifact-consistency`, `check-routing-decisions`, and
`check-manifest-consistency` read that snapshot. Add a fallback chain for older
plans (snapshot, else merged-PR commit, else `references.modified_files`), and
make the aspect emit a distinguishable `status: unmeasurable` rather than
`recall 0% / fail` when no footprint source resolves. An unmeasured quantity must
not be reported as a measured zero.

## Evidence

- aspect: artifact_consistency — `recall_pct: 0.0`, `found: 0`, `declared: 8`
- ground truth: `git show --name-only 89fd4d1f6` returns exactly the 8 declared
  files
- the same gap forced this retrospective to hand-write `work/footprint.txt` from
  the merged commit so aspects 12 and 13 could run at all
