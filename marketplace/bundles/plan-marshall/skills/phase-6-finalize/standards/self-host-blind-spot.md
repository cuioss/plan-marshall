---
name: default:self-host-blind-spot
description: Self-host blind spot invariant — plugin cache vs worktree mismatch at phase-6 dispatch time
order: 5
---

# Self-Host Blind Spot Invariant

This standards document codifies the **self-host blind spot**: the structural mismatch that arises when plan-marshall's own `phase-6-finalize` workflow dispatches agents that resolve content through the installed plugin cache while the plan is running in an isolated worktree on a feature branch — before those worktree changes have been deployed to the cache.

Plans that modify the `plan-marshall` bundle itself are the only callers exposed to this class of failure. Consumer projects of plan-marshall never trip the invariant because their worktree edits do not target the dispatcher's own resolution roots.

## The Invariant

> **A plan that modifies plan-marshall itself cannot use its own modified skills, workflows, or manifest-shape changes at phase-6 dispatch time unless (a) the plugin cache is synced from the worktree AND (b) the Claude Code session is restarted.**

Both halves are load-bearing. Synchronising the cache without restarting the session leaves the in-process skill registry pinned to the pre-sync snapshot. Restarting the session without first syncing leaves the cache pinned to the previous commit on `main`. The invariant fails closed only when both conditions hold.

## The Three Failure Surfaces

The invariant manifests at three distinct resolution boundaries inside `phase-6-finalize`. Naming them explicitly is the point of this document — diagnosing a self-host failure requires identifying which surface tripped, because the remediation is different for each.

### 1. Skill resolution against the installed cache

When the dispatcher loads a skill via `Skill:` directive (e.g., `Skill: plan-marshall:phase-6-finalize`), the host platform resolves the skill body from `~/.claude/plugins/cache/plan-marshall/skills/phase-6-finalize/SKILL.md`, not from the worktree's `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`. A worktree edit to a skill body is invisible to every `Skill:` load until `/sync-plugin-cache` runs.

### 2. Workflow-notation resolution against the installed cache

When the dispatcher emits `workflow: plan-marshall:plan-marshall/workflow/verification-feedback.md` in a `Task:` prompt body, the dispatched `execution-context-{level}` agent resolves the notation against the installed cache — same root as surface (1), same blind spot. A worktree edit to a `workflow/*.md` file is invisible to every dispatched workflow until the cache is synced. The cache-as-resolution-root contract is the authoritative source for this surface; see [`../../extension-api/standards/ext-point-execution-context-workflow.md`](../../extension-api/standards/ext-point-execution-context-workflow.md) § Workflow-Resolution Root.

### 3. Execution-manifest content baked at write time

The per-plan execution manifest at `.plan/local/plans/{plan_id}/execution.toon` is composed once (at plan-4 time, with phase-5 amendments) by reading the **then-current** plugin cache. The manifest's `phase_5.verification_steps` and `phase_6.steps` lists are snapshots; subsequent worktree edits to step ordering, step activation, or default profiles do NOT re-flow into an already-written manifest. Phase-6 readers see the pre-change manifest shape even after a successful cache sync, until the plan is re-planned or the manifest is recomposed. See [`../../manage-execution-manifest/SKILL.md`](../../manage-execution-manifest/SKILL.md) § Manifest-on-Write Semantics for the authoritative read/write semantics statement.

## Why the Remediation Is Both Halves

The three surfaces collapse into the two-part remediation in the invariant above:

- `/sync-plugin-cache` (or `finalize-step-sync-plugin-cache`) addresses surfaces (1) and (2) at the filesystem layer — the cache directory now matches the worktree.
- A Claude Code session restart addresses surfaces (1) and (2) at the runtime layer — the host platform re-reads the cache on next launch instead of serving its in-process snapshot.
- Surface (3) is NOT addressed by either step alone: a manifest written against the pre-change shape stays written. Plans that need the new manifest shape must be re-planned (or have the manifest explicitly recomposed) AFTER the cache sync and session restart. The session-restart fence in [`../SKILL.md`](../SKILL.md) § Session-Restart Fence formalises the halt point.

## Scope

This invariant applies **only** to plans whose `references.modified_files` includes paths under `marketplace/bundles/plan-marshall/`. Plans that touch sibling bundles (`pm-dev-java`, `pm-documents`, etc.) trip a narrower variant — the cache sync still matters for in-session re-dispatch of those bundles' skills, but `phase-6-finalize`'s own dispatcher is unaffected because the modified files are not on its hot path.

## Cross-References

- [`../SKILL.md`](../SKILL.md) § Session-Restart Fence — the mandatory halt-and-restart gate placed after `finalize-step-sync-plugin-cache` in the finalize workflow.
- [`../../extension-api/standards/ext-point-execution-context-workflow.md`](../../extension-api/standards/ext-point-execution-context-workflow.md) § Workflow-Resolution Root — the cache-as-resolution-root contract for surface (2).
- [`../../manage-execution-manifest/SKILL.md`](../../manage-execution-manifest/SKILL.md) § Manifest-on-Write Semantics — the baked-at-write / not-re-resolved-at-read semantics for surface (3).
