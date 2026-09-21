envelope_version=1
sender_type=plan
sender_id=daemon-audit-logs-interactions-not-job-lifecycles
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T16:19:20Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall

# check-artifact-consistency reports 0% recall when the footprint SOURCE is gone, not "unmeasurable"

## What was observed

Run as a finalize step after `branch-cleanup` (i.e. after the merge and after the worktree
was removed), `check-artifact-consistency` emitted:

```
affected_files_recall,fail,Recall 0% below 70% threshold
details.affected_files_recall: declared: 9, found: 0, recall_pct: 0.0
  missing[9]: <every single declared file>
```

Recomputed here against the merged commit `741a1c99d`, the plan touched 8 of its 9
declared files (+913/-54). **True recall is 88.9%** — comfortably above the threshold. The
one unmatched file (`_marshalld_journal.py`) was correctly not touched: deliverable D1
chose emission-at-terminalization over a read-time journal join, which removed the reason
to modify that module.

The aspect found 0 files because its footprint source — the plan's worktree — no longer
existed, not because the plan missed its files.

## Why it matters to this epic

The aspect is the retrospective's own *declared-vs-achieved coverage* check, and it
reported a **0% coverage number that is not a measurement**. Zero-because-unmeasured is
rendered identically to zero-because-failed, and the severity attached (`fail`, warning
finding, all 9 files listed as `missing`) reads as an unambiguous plan defect.

An audit tool that manufactures a false coverage failure is worse than one that abstains:
it puts a wrong number into the report that every downstream consumer treats as a fact.
This is the same shape as the epic's other findings, turned on the auditor.

The ordering makes this systematic rather than incidental: `plan-marshall:plan-retrospective`
sits AFTER `branch-cleanup` in the standard phase-6 step order, so on any plan that runs
the retrospective as a finalize step with `use_worktree=true`, the worktree is *always*
already gone. This does not misfire occasionally — it misfires every time.

## Proposed action

Two changes, both small:

1. **Add a merged-commit fallback footprint source.** The plan's PR number is already on
   disk at `status.metadata.phase_steps["6-finalize"]["create-pr"].display_detail`, and
   the merge commit is reachable from it. `git show --name-only` against that commit gives
   the realized footprint after the worktree is gone.
2. **Make the no-source case explicit.** When no footprint source resolves, the check MUST
   emit `status: skipped` with reason `footprint_source_unavailable` and `recall_pct: null`
   — never `0.0`. A missing measurement is not a measurement of zero.

A regression test should assert that a plan directory with no worktree and no
`references.modified_files` yields `skipped`, not `fail`.

## Evidence

- `work/fragment-artifact-consistency.toon` (this run) — `recall_pct: 0.0`, 9 missing
- `git show --stat 741a1c99d` — 8 files, +913/-54
- `standards/dispatch-inline-split.md` + `execution.toon` `phase_6.steps` — retrospective
  runs after `branch-cleanup`
- `status.metadata.use_worktree = true`
