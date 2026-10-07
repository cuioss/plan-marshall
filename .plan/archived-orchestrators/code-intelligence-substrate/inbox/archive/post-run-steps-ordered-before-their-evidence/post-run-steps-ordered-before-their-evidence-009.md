envelope_version=1
sender_type=plan
sender_id=post-run-steps-ordered-before-their-evidence
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T22:42:52Z

component=plan-marshall:plan-retrospective
category=bug
title=The retrospective runs its own aspect scripts from a plugin cache synced after it - so it reproduced the exact false verdict this plan fixed

# The retrospective runs its own aspect scripts from a plugin cache synced after it

## Observation — measured, not argued

`PLAN-CIS-028` shipped TASK-017: `check-artifact-consistency.py` was collapsing an
UNRESOLVABLE footprint onto an empty one, so a plan whose worktree `branch-cleanup`
had already deleted scored a confident **"Recall 0%"** instead of `inconclusive`. The
merged fix introduces a stated sentinel (`FOOTPRINT_UNRESOLVED`) and a named predicate
(`footprint_resolved`), and its docstring names the incident verbatim:

> Collapsing both outcomes to an empty set is what let a 21/21 exact footprint score a
> confident "Recall 0%" after `branch-cleanup` deleted the worktree the resolver measures.

**This plan's own retrospective then emitted, from that same aspect:**

```
affected_files_recall,fail,Recall 0% below 70% threshold
declared: 23, found: 0, recall_pct: 0.0
```

The reason is not the fix. The fix is correct and is on `main`. The reason is that
`.plan/execute-script.py` resolves scripts out of the **plugin cache**, and
`project:finalize-step-sync-plugin-cache` is ordered **after**
`plan-marshall:plan-retrospective` in the finalize step list. The retrospective
therefore executed the **pre-merge cached copy** — verified on disk: the cached
`_resolve_footprint` still takes `(plan_dir)` only, still reads
`status.metadata.worktree_path` directly, and still ends `return set()`.

## Why this is not the same as the manifest-snapshot lesson

The sibling message in this batch (`…-007`) says a plan cannot exercise a fix to its own
finalize because the **manifest was frozen at outline time**. That is an argument about
*unobservability*. This is a different mechanism with a different remedy and a
**measurable wrong answer in the delivered artifact**:

| | 007 (manifest snapshot) | This |
|---|---|---|
| Mechanism | `execution.toon` composed at outline time | executor resolves scripts from `~/.claude/plugins/cache/…` |
| Effect | the new ordering is not exercised | the OLD code runs and emits a FALSE verdict |
| Remedy | declare non-self-exercisability in the outline | order the cache sync before the post-run band, or resolve retrospective aspect scripts from the merged tree |

## Rule

- A step that **consumes a component the same plan modified** must resolve that component
  from a source the plan's merge has already updated. Today `plan-retrospective` cannot:
  its scripts come from a cache written three steps later.
- **A stale-cache execution is not a benign delay — it is a wrong answer with a
  confident presentation.** The report says `fail` where the shipped code says
  `inconclusive`, and nothing in the report discloses which copy ran.
- Concretely: either move `project:finalize-step-sync-plugin-cache` ahead of the
  `post_run_review` band, or have the retrospective record the resolved script provenance
  (cache version vs merged HEAD) in its report so a reader can tell which code produced
  the verdict.
- This is the **third** recorded instance of the family (PLAN-10: cache syncs at step 19,
  retrospective at 17; 007: outline-time manifest). The family is "a plan's deliverable is
  consumed by the lifecycle at a point the plan has already passed" — but the failure mode
  here is louder than the other two, because it produces output that looks measured.

## Impact

`plan-marshall:plan-retrospective` (every script-backed aspect), `phase-6-finalize` step
ordering, `project:finalize-step-sync-plugin-cache`, and every future plan that modifies a
finalize-time or retrospective-time component.
