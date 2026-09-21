envelope_version=1
sender_type=plan
sender_id=derive-the-partition-and-the-budget-attribution
epic=test-quality
kind=candidate-lesson
created=2026-08-25T09:06:14Z

component=plan-marshall:plan-marshall
category=bug
confidence=medium
source_plan=derive-the-partition-and-the-budget-attribution

# A session restart mid-finalize silently reset cwd off the worktree, breaking every manage-* call

## Context

A session restart part-way through 6-finalize silently moved the orchestrator's working
directory from the plan's worktree back to the main checkout. Nothing announced the move.

The first symptom was that every `manage-*` call began returning `plan_not_found` — for a
plan that existed, in a phase that was running, from an orchestrator that had been
operating on it successfully minutes earlier. Multiple dispatched agents hit the identical
wall independently before the cause was identified and the cwd re-pinned.

`plan_not_found` is an accurate answer to the question the script was asked. It is a
badly misleading answer to the question the caller was asking, because the caller had no
reason to suspect its own cwd had changed underneath it.

## Root cause

Under the cwd-pinned model (ADR-002) a plan's directory MOVES into its worktree at phase-5
entry, so plan-scoped store resolution is keyed on the working directory. The pin is
session state: it is established once and held, and nothing re-establishes it when the
session is replaced.

A restart therefore produces a state that is internally consistent and externally wrong —
the resolver correctly reports that the main checkout holds no such plan, while the plan
sits in the worktree the process is no longer standing in.

## Proposed action

The cheapest durable fix is diagnostic rather than structural: when a plan-scoped verb
resolves no plan directory, check whether the plan is resolvable from its recorded
`worktree_path` before answering. If it is, say so — `plan_not_found (resolvable from the
plan worktree; cwd is the main checkout)` names the actual condition and the remedy in one
line. `manage-status list` already scans both locations and tags each plan `current` /
`worktree`, so the information needed is on hand.

Structurally, a phase-5+ resume that re-pins cwd from `status.metadata.worktree_path`
before its first plan-scoped call would prevent the state arising at all. That is the
better fix; the diagnostic is the one that pays off even when the re-pin is missed.

## Evidence

- observed: session restart mid-6-finalize; cwd reverted from the plan worktree to the main checkout
- every subsequent `manage-*` call returned `plan_not_found` until the cwd was re-pinned by hand
- multiple dispatched agents hit the same condition independently, none of them diagnosing it
- ADR-002 — the move-based, cwd-pinned model that makes cwd the resolution anchor
