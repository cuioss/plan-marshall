envelope_version=1
sender_type=plan
sender_id=plan-footprint-is-unknowable-to-its-own-graders
epic=truthful-signals
kind=candidate-lesson
created=2026-08-27T14:44:09Z

component=plan-marshall:plan-retrospective
category=improvement
confidence=high
source_plan=plan-footprint-is-unknowable-to-its-own-graders
source_pr=1359

# Return the answering tier from resolve_footprint so a grader can name its evidence

## Context

`_footprint_resolver.RESOLVING_TIERS` declares five tiers in precedence order, and `resolve_footprint` walks them. It returns a `set[str] | None` — the footprint, or the unresolvable sentinel. **It does not return which tier produced the answer.**

Every consumer therefore reports only a binary: `footprint_resolved: true` (`check-artifact-consistency`) or `footprint_source: resolved` (`check-routing-decisions`, `check-outline-vs-shipped`). None can say *how* it knows.

This plan exists because every prior post-merge retrospective on this repository graded blind. Establishing that the remedy worked — and by which tier — was the single most valuable measurement this retrospective could make, and it was not obtainable from any script output.

## Root cause

The tier is computed and then discarded at the return boundary. The chain is a private implementation detail of a function whose whole value to a grader is *which evidence it found*.

## Proposed action

Return `(footprint, answering_tier)` where `answering_tier` is a member of `RESOLVING_TIERS` or the unresolved sentinel, and have every member of `FOOTPRINT_CONSUMING_ASPECTS` publish `footprint_tier` beside its existing `footprint_source`. The tier name is already the authoritative vocabulary, so no new enum is needed.

## Evidence

- Establishing the tier for this plan required five manual, judgement-free steps: `git worktree list` (to prove tier 1 could not fire), `manage-references get --field realized_footprint`, `manage-references get --field merge_commit_sha`, a read of `_footprint_resolver.py`, and a `git diff --name-only {sha}^1 {sha}` cross-check.
- The answer was **tier 2 (`realized_capture`)** — not the newly-added tier 4 (`pr_landing`), which remains unexercised on this plan because `branch-cleanup` wrote the capture before removing the worktree.
- Tier 3 (`merge_commit`) independently reproduces tier 2 exactly: 33 paths, symmetric difference 0. That cross-check upgraded the verdict from *resolved* to *demonstrably exact* — and nothing in the pipeline performs it.
- aspect: llm_to_script_opportunities — filed as the highest-value scripting candidate of this run.
