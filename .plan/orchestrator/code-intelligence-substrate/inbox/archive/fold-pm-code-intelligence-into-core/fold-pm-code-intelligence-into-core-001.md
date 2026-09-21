envelope_version=1
sender_type=plan
sender_id=fold-pm-code-intelligence-into-core
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-25T21:12:47Z

# Persist the realized footprint before branch-cleanup removes the worktree

## Context

This plan's post-merge retrospective could not resolve the plan footprint from any tier. `check-artifact-consistency` reported both `affected_files_recall` and `affected_files_exact_match` as `inconclusive` with the message "no live worktree diff, no realized-footprint capture, no merge-commit, no modified_files key". The same absence disabled the `ARTIFACT_COVERAGE` floor in `analyze-logs` and left the routing aspect without a footprint to re-evaluate prune predicates against. The retrospective recovered the footprint by hand from the squash-merge commit — 25 paths — and only then could grade coverage.

## Root cause

`branch-cleanup` removes the worktree, and the worktree diff is the only tier that is reliably populated during the run. Nothing persists the realized footprint before that removal, so every check that needs a diff loses its evidence at exactly the moment the plan finishes — which is when the retrospective runs.

## Proposed action

Have `branch-cleanup` capture the realized footprint (`{base}...HEAD` name-only) into the plan directory before `git worktree remove`, so the shared resolver's realized-footprint-capture tier has a file to read. This is the cheapest of the three candidate fixes because the data is in hand at that instant and needs no reconstruction.

## Evidence

- aspect: artifact_consistency — 2 of 6 checks `inconclusive`; `footprint_resolved: false` with `declared: 22`
- aspect: logging_gap_analysis — `ARTIFACT_COVERAGE_UNMEASURABLE` warning: "This is an unmeasured check, not a clean one"
- aspect: routing_decisions — the aspect only produced measured verdicts once `--diff-file` was supplied by hand
- realized footprint recovered manually: 25 paths from squash-merge `9aaf22d8f`
