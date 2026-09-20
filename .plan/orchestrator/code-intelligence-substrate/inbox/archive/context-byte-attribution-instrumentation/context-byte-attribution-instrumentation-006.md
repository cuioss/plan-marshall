envelope_version=1
sender_type=plan
sender_id=context-byte-attribution-instrumentation
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-03T16:42:37Z

# Resolve the plan footprint from the merge commit after branch-cleanup

component: plan-marshall:plan-retrospective
category: improvement
confidence: high
source_plan: context-byte-attribution-instrumentation
source_pr: 1086

## Context

`check-artifact-consistency` is the deterministic item-coverage half of the thoroughness dial — it
compares declared in-scope files (`affected_files`) against the plan's actual footprint. On this run
it returned **inconclusive** on both of its coverage checks:

> "Plan footprint could not be resolved (no live worktree diff and no modified_files key) — recall is
> unmeasurable, not 0%"

The footprint resolver has exactly two sources: a live worktree diff, and the legacy
`references.modified_files` key. Neither survives the post-merge band — `branch-cleanup` removes the
worktree, and `modified_files` was retired.

## Root cause

The retrospective is ordered **after** `branch-cleanup` in the finalize manifest (step 17 of 22,
versus branch-cleanup at 13). By the time it runs, its primary evidence source has been deleted by an
earlier step of the same phase. The resolver was never given a source that outlives the worktree.

The verdict was not genuinely ambiguous — it was merely unreachable. Recovering the footprint from
the merged squash commit takes one command:

```
git show --name-only --pretty=format: 9b689d65
```

That yields 12 files, against 12 declared in `references.affected_files`, as an **exact set match**:
recall 100%, exact_match true. The plan had perfect declared-vs-achieved coverage and the report
could not say so.

## Proposed action

Add a third fallback to the footprint resolver, tried when no live worktree and no `modified_files`
exist: read the merge/squash SHA that `branch-cleanup` already records and derive the footprint from
that commit. This restores the coverage verdict for every plan whose retrospective runs post-merge —
which, given the manifest ordering, is *every orchestrated plan*.

Worth noting the contrast with the standing `affected_files` under-recording defect (19-vs-37): here
`affected_files` was exactly right. The instrument, not the data, was the limitation.

## Evidence

- aspect: artifact_consistency — 2 of 6 checks `inconclusive`, both with `footprint_resolved: false`
- Recovered footprint (12 paths) vs `references.affected_files` (12 paths): exact set match, zero outline-only, zero references-only
- The same absence forced `check-manifest-consistency` and `check-routing-decisions` to be re-run manually with a hand-reconstructed `--diff-file`
