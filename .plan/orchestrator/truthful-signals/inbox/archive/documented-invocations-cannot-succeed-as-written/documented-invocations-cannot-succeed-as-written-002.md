envelope_version=1
sender_type=plan
sender_id=documented-invocations-cannot-succeed-as-written
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T18:49:39Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=documented-invocations-cannot-succeed-as-written
source_pr=1386

# check-manifest-consistency reports a post-merge empty diff as a measured empty footprint

## Context

`plan-retrospective` runs at `order: 995`, after `branch-cleanup` has merged the
PR. Invoked as its own SKILL.md prescribes — `--base-ref` supplied because
`--diff-file` is absent — `check-manifest-consistency` computed the diff against
`origin/main`, which by then already contained the plan's own squash-merge commit
`71279cc0`. It reported:

```
diff:
  base: origin/main
  files_total: 0
  oracle_available: true
  diff_available: true
```

and its `branch_cleanup_changes` rule returned `fail` with the message *"phase_6.steps
includes branch-cleanup but the observed diff is empty — the footprint resolved to no
changed path at all, so no implementation file changed"*.

The plan changed 28 files. `git merge-base --is-ancestor 71279cc0 origin/main`
exits 0.

## Root cause

The script treats "git returned no paths" as a measured empty footprint whenever
a `--base-ref` was supplied, with no test for whether the base already contains
the work being diffed. Its own SKILL.md documents the honest fallback for the
adjacent case — an absent `--base-ref` records `base: unknown` and reports every
diff-fed rule `indeterminate` — so the vocabulary for "I could not measure this"
already exists; the post-merge case simply never routes into it.

## Proposed action

Add an ancestry probe: when the plan's merge commit (or HEAD at
`branch-cleanup`) is an ancestor of `--base-ref`, the diff is structurally empty,
and every diff-fed rule MUST report `indeterminate` rather than pass or fail.
One `git merge-base --is-ancestor` call. Alternatively, resolve the footprint
through the shared resolver the sibling aspects already use.

## Evidence

- aspect: manifest_decisions — `checks.branch_cleanup_changes: fail`, "no
  implementation file changed", over `diff.files_total: 0`
- aspect: outline_vs_shipped — same run, same plan:
  `footprint_source: resolved`, `footprint_path_count: 33`
- aspect: artifact_consistency — same run: `declared: 24, found: 24,
  recall_pct: 100.0, footprint_resolved: true`
- corroboration: `git merge-base --is-ancestor 71279cc0 origin/main` exits 0
