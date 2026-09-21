envelope_version=1
sender_type=plan
sender_id=pr-065-settings-repo-accumulates-never-lands
epic=review-apparatus
kind=candidate-lesson
created=2026-09-14T19:07:29Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=pr-065-settings-repo-accumulates-never-lands

# check-manifest-consistency reports a false empty diff when run post-merge on main

## Context

`plan-marshall:plan-retrospective` runs at `order: 995` — after `branch-cleanup` (order 70)
has removed the plan's worktree and landed the PR. On this run the retrospective executed
in the main checkout against a plan whose branch had already merged as `6c87e12ab`.

`check-manifest-consistency run --base-ref origin/main` then resolved `files_total: 0`,
`files_kept: 0`, with `diff_available: true` and `oracle_available: true` — a confident,
fully-populated empty measurement. It fired `branch_cleanup_changes,fail`:
*"phase_6.steps includes branch-cleanup but the observed diff is empty — the footprint
resolved to no changed path at all, so no implementation file changed"* — against a plan
with a 13-path realized footprint that had just merged to main.

## Root cause

Post-merge, `origin/main..HEAD` is empty by construction: the branch's commits ARE main's
commits. The script treats that empty range as a resolved-empty footprint (a genuine
measurement) rather than as an unresolvable one, so its diff-fed rules pass judgement over
no evidence. The script's own canonical-invocation note anticipates the unresolvable case —
it documents `base: unknown` plus `indeterminate` for every diff-fed rule — but a merged
base ref does not reach that path.

`check-outline-vs-shipped`, on the same run and the same checkout, resolved the full
13-path footprint through the shared resolver. The capability to see this plan's footprint
post-merge exists; this script does not use it.

## Proposed action

Either (a) route `check-manifest-consistency`'s footprint acquisition through the shared
resolver that `check-outline-vs-shipped` already uses, or (b) have it detect that the head
is an ancestor of the base ref and report `base: merged` with every diff-fed rule
`indeterminate` — never a clean or failing verdict over an empty range. Option (b) is the
smaller change and matches the script's existing no-verdict-over-no-evidence discipline.

## Evidence

- aspect: manifest-decisions — `checks: branch_cleanup_changes,fail`; `diff: base: origin/main, files_total: 0, diff_available: true`
- aspect: outline-vs-shipped — `footprint_source: resolved`, `footprint_path_count: 13`, same run, same checkout
- orchestrator dispatch note: retrospective ran post-merge on the main checkout, `merge_commit_sha 6c87e12abf44eac2c78dd655dc03ac0efef51922`
