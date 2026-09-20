envelope_version=1
sender_type=plan
sender_id=compose-time-subtractions-drop-steps
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T12:42:41Z

## Proposed lesson metadata

- `component`: `plan-marshall:plan-retrospective`
- `category`: `bug`
- `title`: The coverage check reports a measurement absence as a FAIL once branch-cleanup has removed the worktree

## Observation

This retrospective ran after `branch-cleanup` had merged PR #1066 and removed the
plan's worktree — the ordering the finalize step list itself prescribes
(`branch-cleanup` at position 19, `plan-marshall:plan-retrospective` at 20).

`check-artifact-consistency` derives the realized footprint **live from the
plan's worktree** (`{base}...HEAD` ∪ porcelain). With the worktree gone it
resolved nothing, and emitted:

```
affected_files_recall,fail,Recall 0% below 70% threshold
details.affected_files_recall: declared: 39, found: 0, recall_pct: 0.0
```

`found: 0` is not a coverage result. It is the absence of a measurement, rendered
as the worst possible coverage result. A reader — or an audit sweep over archived
retrospectives — sees a hard `fail` on the declared-vs-achieved coverage check
and has no way to tell it apart from a plan that genuinely touched none of its
declared files.

The plan's actual recall, computed against the merge commit, is **38/39**
(the one miss is declared `intent: read`, so it is correct).

## The fix already exists one file away

`check-routing-decisions.py`, in the same skill, faces the identical problem and
handles it correctly:

```python
have_footprint = bool(footprint)
...
if not have_footprint:
    checks.append({... 'status': 'skip', 'detail': 'no realized footprint'})
```

It distinguishes "measured, and the answer is empty" from "could not measure",
and it emits `skip`, not `fail`. That is exactly the three-state discipline the
audited plan itself shipped into `_resolve_plan_footprint` (`None` = unresolvable,
`[]` = resolvable-and-empty).

## The compounding effect

With aspect 1 producing a vacuous `fail` and aspect 12 (`manifest-decisions`)
passing while skipping 3 of its 5 checks as not-applicable, **the plan's
declared-vs-achieved coverage was never actually graded on this run**. The
retrospective reports a coverage verdict; no coverage verdict was computed.

## Rule

A retrospective aspect that cannot obtain its input must emit `skipped` with the
reason, never a threshold verdict computed over a substituted empty set. Zero
observations is not zero coverage.

## Owed work

1. `check-artifact-consistency` gains the `have_footprint` discriminator, and
   reports `affected_files_recall` as `skip` with reason `footprint_unresolvable`
   when the worktree is gone.
2. Fall back to the merged commit's name-only diff before giving up — after
   `branch-cleanup` the footprint IS still derivable, from `{merge_sha}^..{merge_sha}`.
   That would have produced the real 38/39.
3. Honour the `intent` field: a file declared `intent: read` must not count
   against recall, and a file declared `intent: read` that WAS modified is a
   scope-declaration violation worth its own finding. This run had exactly one of
   those (`test_security_class_gate_regression.py`) and nothing caught it.
