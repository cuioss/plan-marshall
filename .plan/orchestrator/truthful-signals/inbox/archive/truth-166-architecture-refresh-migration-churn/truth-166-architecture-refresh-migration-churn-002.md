envelope_version=1
sender_type=plan
sender_id=truth-166-architecture-refresh-migration-churn
epic=truthful-signals
kind=candidate-lesson
created=2026-09-17T02:29:10Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
rank=2
source_plan=truth-166-architecture-refresh-migration-churn

# Route check-manifest-consistency through the shared footprint resolver, not a base_ref diff

## Context

`plan-marshall:plan-retrospective` is step 17 of the 23-step finalize manifest;
`default:branch-cleanup` — which merges the PR — is step 13. The retrospective therefore
runs AFTER the plan has landed, by manifest construction, on every plan that reaches it.

A `base_ref` diff is structurally empty at that point, because the plan's changes are
already IN `origin/main`. On this run, `check-manifest-consistency --base-ref origin/main`
reported `files_total: 0`, `files_kept: 0`, with `diff_available: true` and
`oracle_available: true`, and its `branch_cleanup_changes` rule FAILED with:

    phase_6.steps includes branch-cleanup but the observed diff is empty — the
    footprint resolved to no changed path at all, so no implementation file changed

for a plan that changed 22 declared files and shipped a 26-path footprint.

## Root cause

The aspect derives its footprint from a git base_ref instead of the shared footprint
resolver, and an empty-but-available diff is then read as positive evidence of no change.
Two sibling aspects in the SAME run got it right: `check-routing-decisions` and
`check-outline-vs-shipped` both report `footprint_source: resolved`, the latter counting
26 footprint paths. So the run contains a 0-vs-26 disagreement in which the wrong aspect
is the one self-reporting its diff as `available`.

The skill's own canonical block makes the wrong path the default. It instructs supplying
`--base-ref` whenever `--diff-file` is absent, and records that omitting BOTH yields
`base: unknown` with every diff-fed rule reporting `indeterminate`. Following the
documented instruction produces the confident false verdict; ignoring it produces the
honest one.

## Proposed action

Resolve the footprint through the shared resolver, exactly as the two sibling aspects in
the same skill already do. Failing that, gate the diff-fed rules on whether the plan's PR
has already merged and report `indeterminate` when it has. Either way, an empty `base_ref`
diff must never assert that no implementation file changed, and the canonical block's
"supply `--base-ref`" advice should stop recommending the path that fails here.

## Evidence

- aspect: manifest_decisions — `diff: base: origin/main, files_total: 0,
  diff_available: true`; `checks: branch_cleanup_changes,fail`.
- aspect: outline_vs_shipped — `footprint_source: resolved`,
  `footprint_path_count: 26`, `comparison: measured`.
- aspect: routing_decisions — `footprint_source: resolved`.
- manifest: `phase_6.steps` places `plan-marshall:plan-retrospective` after
  `branch-cleanup`, so the post-merge ordering is guaranteed, not incidental.

## Generalizes

A footprint derived from a git base_ref is only valid relative to the moment it is taken.
A step that runs after its own merge has no base_ref that can see its work, so any
base_ref-derived verdict there is false by construction — and publishing
`diff_available: true` beside it tells a consumer the measurement was sound.
