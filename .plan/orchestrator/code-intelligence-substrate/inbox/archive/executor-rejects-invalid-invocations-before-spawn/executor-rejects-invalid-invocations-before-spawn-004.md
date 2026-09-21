envelope_version=1
sender_type=plan
sender_id=executor-rejects-invalid-invocations-before-spawn
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-09T14:43:13Z

# Recover the plan footprint from the recorded merge SHA when the worktree is gone

component: plan-marshall:plan-retrospective
category: improvement
confidence: high
source_plan: executor-rejects-invalid-invocations-before-spawn
source_pr: 1127

## Context

`check-artifact-consistency` returned `inconclusive` on **both** footprint checks
(`affected_files_recall`, `affected_files_exact_match`) with the message "Plan footprint
could not be resolved (no live worktree diff and no modified_files key)".

That is correct behaviour on the evidence it looked at — and it will happen on **every**
post-merge retrospective, because `plan-retrospective` runs at finalize order 995, after
`branch-cleanup` has removed the worktree by design. The check is structurally unable to
run in its own normal execution position.

Computing the footprint by hand from the recorded squash merge (`415dcf139`) gave the
measurement the check could not:

- declared `affected_files`: 17
- realized footprint: 26
- declared and touched: 15 → **recall 58%**, precision 88%
- 11 files touched but never declared; 2 declared but never touched

## Root cause

The resolver looks for exactly two sources — a live worktree diff, or the retired
`references.modified_files` key — and there is a third that is always available
post-merge: `status.metadata` carries the branch, and `branch-cleanup` records the merge
with its squash SHA in `phase_steps`. A `git show --name-only` against that SHA recovers
the footprint deterministically.

The cost is not bookkeeping. Two of the 11 undeclared files (`rule-catalog.md`,
`doc/adr/001-*.adoc`) were the subject of three review findings, and CodeRabbit's `eae5a0`
caught in ADR-001 the *same* defect the branch had already fixed in `rule-catalog.md` — a
file the plan's own remediation sweep never reached. The check that could not run is the
one that would have predicted that escape.

## Proposed action

Add a third resolution source to the footprint resolver: when no live worktree exists,
read the merge SHA from `status.metadata.phase_steps["6-finalize"]["branch-cleanup"]` (or
the recorded PR merge commit) and derive the footprint from that commit. Keep
`inconclusive` for the case where no source resolves — the current three-valued honesty
is right and should not be traded for a false zero.

## Evidence

- `work/fragment-artifact-consistency.toon` — both checks `inconclusive`, `footprint_resolved: false`, `declared: 17`.
- squash merge `415dcf1397fb6b2eca06e0654801b66d8eaaedbf` on main — 26 files, the realized footprint.
- qgate finding `eae5a0` (CodeRabbit) — the escape in ADR-001 that the under-declared footprint under-scoped.
- The check already refuses to report 0% recall for an unresolvable footprint, which is the correct half of this behaviour and must be preserved.
