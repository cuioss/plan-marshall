envelope_version=1
sender_type=plan
sender_id=implement-plan-165-close-orphan-defects
epic=test-quality
kind=candidate-lesson
created=2026-09-13T11:18:50Z

component=plan-marshall:plan-retrospective
category=improvement

# Give check-manifest-consistency the shared footprint resolver its siblings use

## Context

Three retrospective aspects need the plan's realized footprint. Two of them — `check-routing-decisions` and `check-outline-vs-shipped` — recover it unaided through the shared footprint resolver, and on this plan both independently resolved the correct 4-path footprint with no `--diff-file` supplied (`footprint_source: resolved`, `footprint_path_count: 4`). The third, `check-manifest-consistency`, has no such fallback: its canonical-invocation note instructs the caller to "supply `--base-ref` whenever `--diff-file` is absent — it is how the script obtains a diff at all."

Following that instruction at retrospective time produced a false finding. The retrospective runs at `order: 995`, after `branch-cleanup` has merged the PR, so `origin/main` already contains the plan's own commits and `--base-ref origin/main` yields an empty diff. The script reported `diff.files_total: 0` with `oracle_available: true` and `diff_available: true` — a *resolved empty* footprint, not an indeterminate one — and on that basis failed `branch_cleanup_changes` with `branch_cleanup_without_changes`: "phase_6.steps includes branch-cleanup but the observed diff is empty — the footprint resolved to no changed path at all, so no implementation file changed". Re-running the identical check with the true 4-path footprint turned the same rule green (2 passed, 0 failed, 0 findings).

## Root cause

Two defects compound. First, resolver parity: one of three sibling aspects in the same skill cannot recover a footprint its siblings recover routinely, so it depends on caller-supplied input that the other two do not need. Second, the documented remedy is wrong for this script's actual execution moment — `--base-ref origin/main` is a reasonable instruction in the abstract and a footprint-erasing one after the merge has landed, and nothing in the doc warns of that.

## Proposed action

Give `check-manifest-consistency` the shared footprint resolver as its fallback, so an absent `--diff-file` resolves the footprint the same way its two siblings do instead of depending on a base-ref the caller must choose correctly. Until then, correct the canonical-invocation guidance to state that `origin/main` is not a valid base at retrospective time because the plan's commits are already in it, and that a post-merge caller must supply the realized footprint explicitly.

## Evidence

- aspect: manifest_decisions (first run, `--base-ref origin/main`) — `diff: {base: origin/main, files_total: 0, oracle_available: true, diff_available: true}`; `branch_cleanup_changes,fail`; 1 finding `branch_cleanup_without_changes`
- aspect: manifest_decisions (re-run, `--diff-file work/footprint.txt`) — `diff: {base: file:footprint.txt, files_total: 4, files_kept: 4, production: 2, test: 2}`; `branch_cleanup_changes,pass`; 0 findings
- aspect: routing_decisions — `footprint_source: resolved` with no `--diff-file` supplied
- aspect: outline_vs_shipped — `footprint_source: resolved`, `footprint_path_count: 4`, with no `--diff-file` supplied
- `git show --name-only c89beb88` confirms the true footprint is 4 files
