envelope_version=1
sender_type=plan
sender_id=lane-router-reads-the-wrong-body
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T10:56:56Z

component=plan-marshall:manage-execution-manifest
category=bug
proposed_title=Compose logs a confident empty-footprint verdict against a footprint that cannot exist yet

# Compose logs a confident empty-footprint verdict against a footprint that cannot exist yet

## Status

**Observed during `lane-router-reads-the-wrong-body`, NOT fixed.** Low blast radius in this run — the step was re-added moments later by a different rule — but the shape is precisely the one this epic tracks, and the recovery was accidental rather than designed.

## The observation

Two consecutive `decision.log` entries, both at `07:03:28Z`, from the same compose run:

```text
(manage-execution-manifest:compose) pre-push-quality-gate omitted — plan footprint is empty — no changed files to build
...
(manage-execution-manifest:compose) ceremony_finalize selection — finalize.qgate=always, added pre-push-quality-gate to phase_6.steps
```

Compose runs in **phase-4-plan**. Phase 5 has not executed. The worktree was not even materialised until `07:12:17Z`, nine minutes later. The plan's footprint at compose time is not empty — it is **not yet populated**, which is a different fact with a different correct handling.

## Why this is the epic's archetype

The log line states a **conclusion about the world** ("no changed files to build") derived from a **structurally-unpopulated input**. It is stated at full confidence, with no hedge, and it drives a real pruning decision. Had `finalize.qgate` been anything other than `always`, this plan would have shipped six changed files — including a Python script and two SKILL.md contract docs — with `pre-push-quality-gate` pruned on the grounds that there was nothing to build.

This is the same fault the plan itself was fixing, one layer up: a sensor reading a not-yet-real input and reporting the reading as a fact. Compare the first-party reproduction logged at `06:01:38Z`, where the scope-estimate heuristic counted a boilerplate citation as the sole target path.

The near-miss is instructive: **the system did not detect the bad verdict; a second, unrelated rule happened to overwrite it.** `ceremony_finalize` re-added the step because `finalize.qgate=always`, not because anything recognised the prune as wrong.

## Proposed action

1. `compose` runs before execution by construction, so a footprint-conditioned prune predicate has no valid input at that point. Either:
   - **(preferred)** make footprint-conditioned prunes *defer* — record the step as conditionally-pruned and re-evaluate at the point the footprint exists — or
   - refuse to evaluate the predicate and keep the step, treating unpopulated as `unknown`, never as `empty`.
2. Whichever path is chosen, the log line must distinguish the two states. `plan footprint is empty` and `plan footprint not yet populated` are different claims and only one of them is true at compose time.
3. Sweep for sibling predicates: any compose-time rule keyed on realized-execution state (footprint, diff, changed-file count, test-file presence) has the same defect by construction. This is a population-derived sweep, not a spot-check — enumerate the predicates, do not sample them.

## Evidence

- `logs/decision.log` 07:03:28Z — both compose entries, adjacent
- `logs/work.log` 07:12:17Z — `Metadata: worktree_path=...` (worktree materialised nine minutes after the verdict)
- `logs/work.log` 08:04:30Z — `Per-deliverable commit: TASK-4 - 6 files` (the real footprint)
- `logs/decision.log` 06:01:38Z — the sibling first-party reproduction at phase-1-init
