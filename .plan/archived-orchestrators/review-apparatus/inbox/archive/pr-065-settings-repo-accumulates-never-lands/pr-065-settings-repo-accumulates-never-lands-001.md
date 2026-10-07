envelope_version=1
sender_type=plan
sender_id=pr-065-settings-repo-accumulates-never-lands
epic=review-apparatus
kind=candidate-lesson
created=2026-09-14T19:07:18Z

component=plan-marshall:manage-references
category=bug
confidence=high
source_plan=pr-065-settings-repo-accumulates-never-lands

# Resolve the foreign-checkout half of a two-repository plan's footprint

## Context

PLAN-PR-065 declared a surface spanning two repositories: this one, and the foreign
checkout `cuioss/pr-agent-settings`. Seven of its fifteen declared modification-intent
paths were absolute paths into `/Users/oliver/git/pr-agent-settings/` — the validation
workflow, `.pr_agent.toml`, `README.adoc`, and the four new `doc/` files.

Every footprint-derived retrospective aspect erased that half. `check-artifact-consistency`
reported `affected_files_recall` at 53.3% and returned `fail` on a plan that took all ten
deliverables to `done`. `check-outline-vs-shipped` resolved a 13-path footprint, none of
them foreign. The plan spec had anticipated exactly this: it declared the foreign half as
`FOREIGN` rather than as a resolvable path, on the reasoning that the disjointness gate
cannot compare it at all and that saying so is what stops the gate's silence reading as a
checked negative (ADR-019).

## Root cause

The shared footprint resolver derives from this repository's git state through every tier
in `RESOLVING_TIERS`. A path in another checkout cannot appear in any of them, so a
declared foreign path is indistinguishable from a declared path the plan never touched —
and the recall metric grades the declaration style rather than the execution.

## Proposed action

Give the resolver, or the aspects that consume it, a way to partition declared paths into
in-checkout and out-of-checkout sets before computing recall, and report the out-of-checkout
set as `unmeasurable` rather than folding it into the miss count. The spec-level `FOREIGN`
annotation already exists as a vocabulary; the measurement surface does not read it. Until
it does, any two-repository plan will fail its own coverage check while delivering
completely — a false negative in the direction that matters, because a genuine 53% recall
and a fully-delivered two-repo plan are currently the same reading.

## Evidence

- aspect: artifact-consistency — `affected_files_recall,fail,Recall 53% below 70% threshold`; all 7 `missing[]` entries are `/Users/oliver/git/pr-agent-settings/...`
- aspect: outline-vs-shipped — `footprint_path_count: 13`, every member local
- aspect: request-result-alignment — all ten deliverables `fulfilled`, no gap
- source: `request.md` § Expected Surface — "FOREIGN (`cuioss/pr-agent-settings`, verify-at-outline — no path in this checkout resolves it)"
