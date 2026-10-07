envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T20:45:56Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=plan-truth-148
source_aspects=manifest_decisions,outline_vs_shipped,artifact_consistency

# check-manifest-consistency emits a false fail from an empty post-merge diff

## Context

Running `check-manifest-consistency run --base-ref origin/main` after the plan's PR had already merged
produced `diff.files_total: 0` and this verdict:

```
branch_cleanup_changes,fail,"phase_6.steps includes branch-cleanup but the observed diff is
empty - the footprint resolved to no changed path at all, so no implementation file changed"
```

The footprint was not empty. The shared resolver recovered 27 paths, and those 27 match the landed
commit `db0ae6346` path for path. Re-running the identical check with `--diff-file` carrying those
27 paths flipped the same rule to `pass` with 26 kept files after 1 bookkeeping filter.

## Root cause

The script trusts whatever `--base-ref` resolves to and never asks whether the oracle it just built
can see anything. Post-merge, `HEAD == origin/main`, so the diff is degenerate — and a degenerate
oracle is indistinguishable, at the rule's input, from a plan that genuinely changed nothing. Two
sibling scripts in the same skill already avoid this: `check-routing-decisions` and
`check-outline-vs-shipped` both fall back to the shared footprint resolver when no `--diff-file` is
supplied. This one does not.

The result is a could-not-look converted into a confident violation — the exact archetype the
retrospective exists to detect, committed by the retrospective's own machinery. It matters more here
than elsewhere because the retrospective is the last measurement surface in the lifecycle: a false
`fail` it emits has nothing downstream to correct it.

## Proposed action

1. When neither `--diff-file` nor a usable `--base-ref` diff is available, resolve the footprint
   through the shared resolver, exactly as the two sibling scripts do.
2. Independently of (1): never emit `fail` from an empty oracle. An empty diff with `oracle_available:
   true` is `indeterminate`, not a violation. The distinction between "resolved empty footprint" and
   "oracle saw nothing" is already drawn in the skill's own canonical-invocations prose for
   `--diff-file`; the `--base-ref` path does not honour it.

## Evidence

- aspect: manifest_decisions — first run, `--base-ref origin/main`: `files_total: 0`,
  `branch_cleanup_changes,fail`, `summary.failed: 1`
- aspect: manifest_decisions — second run, `--diff-file`: `files_total: 27`, `files_kept: 26`,
  `branch_cleanup_changes,pass`, `summary.failed: 0`
- aspect: outline_vs_shipped — `footprint_source: resolved`, `footprint_path_count: 27`
- corroboration — `git show --name-only db0ae6346` returns exactly those 27 paths
