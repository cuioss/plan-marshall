# Self-Host Blind Spot Invariant

This standards document codifies the **self-host blind spot**: the structural mismatch that arises when plan-marshall's own `phase-6-finalize` workflow dispatches agents that resolve content through the installed plugin cache while the plan is running in an isolated worktree on a feature branch — before those worktree changes have been deployed to the cache.

Plans that modify the `plan-marshall` bundle itself are the only callers exposed to this class of failure. Consumer projects of plan-marshall never trip the invariant because their worktree edits do not target the dispatcher's own resolution roots.

## The Invariant

> **A plan that modifies `plan-marshall` itself cannot use its own modified skills, workflows, or manifest-shape changes at `phase-6` dispatch time unless (a) the plugin cache is synced from the worktree AND (b) the Claude Code session is restarted.**

Both halves are load-bearing. Synchronising the cache without restarting the session leaves the in-process skill registry pinned to the pre-sync snapshot. Restarting the session without first syncing leaves the cache pinned to the previous commit on `main`. The invariant fails closed only when both conditions hold.

## The Three Failure Surfaces

The invariant manifests at three distinct resolution boundaries inside `phase-6-finalize`. Naming them explicitly is the point of this document — diagnosing a self-host failure requires identifying which surface tripped, because the remediation is different for each.

### 1. Skill resolution against the installed cache

When the dispatcher loads a skill via `Skill:` directive (e.g., `Skill: plan-marshall:phase-6-finalize`), the host platform resolves the skill body from `~/.claude/plugins/cache/plan-marshall/skills/phase-6-finalize/SKILL.md`, not from the worktree's `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`. A worktree edit to a skill body is invisible to every `Skill:` load until `/sync-plugin-cache` runs.

### 2. Workflow-notation resolution against the installed cache

When the dispatcher emits `workflow: plan-marshall:plan-marshall/workflow/verification-feedback.md` in a `Task:` prompt body, the dispatched `execution-context-{level}` agent resolves the notation against the installed cache — same root as surface (1), same blind spot. A worktree edit to a `workflow/*.md` file is invisible to every dispatched workflow until the cache is synced. The cache-as-resolution-root contract is the authoritative source for this surface; see [`marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-execution-context-workflow.md`](../../../../marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-execution-context-workflow.md) § Workflow-Resolution Root.

### 3. Execution-manifest content baked at write time

The per-plan execution manifest at `.plan/local/plans/{plan_id}/execution.toon` is composed once (at `phase-4-plan` time, with `phase-5` amendments) by reading the **then-current** plugin cache. The manifest's `phase_5.verification_steps` and `phase_6.steps` lists are snapshots; subsequent worktree edits to step ordering, step activation, or default profiles do NOT re-flow into an already-written manifest. `Phase-6` readers see the pre-change manifest shape even after a successful cache sync, until the plan is re-planned or the manifest is recomposed. See `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/SKILL.md` § Manifest-on-Write Semantics for the authoritative read/write semantics statement.

## Why the Remediation Is Both Halves

The three surfaces collapse into the two-part remediation in the invariant above:

- `/sync-plugin-cache` (or `finalize-step-sync-plugin-cache`) addresses surfaces (1) and (2) at the filesystem layer — the cache directory now matches the worktree.
- A Claude Code session restart addresses surfaces (1) and (2) at the runtime layer — the host platform re-reads the cache on next launch instead of serving its in-process snapshot.
- Surface (3) is NOT addressed by either step alone: a manifest written against the pre-change shape stays written. Plans that need the new manifest shape must be re-planned (or have the manifest explicitly recomposed) AFTER the cache sync and session restart. The session-restart fence in [`../SKILL.md`](../SKILL.md) § Halt protocol formalises the halt point.

## Scope

This invariant applies **only** to plans whose `references.modified_files` includes paths under `marketplace/bundles/plan-marshall/`. Plans that touch sibling bundles (`pm-dev-java`, `pm-documents`, etc.) trip a narrower variant — the cache sync still matters for in-session re-dispatch of those bundles' skills, but `phase-6-finalize`'s own dispatcher is unaffected because the modified files are not on its hot path.

## Predicate Authoring Contract for Session-Restart Gates

This section codifies the structural contract that any session-restart-gating finalize step MUST satisfy. It exists because the failure mode — an infinite-halt loop on dispatcher re-entry — is not obvious from the gate's first dispatch and was only discovered empirically during PR #415 review (captured as lesson [`2026-05-18-23-001`](#cross-references)). Authors of new session-restart-gating steps should consult this contract before shipping a predicate; the canonical worked example is [`../SKILL.md`](../SKILL.md) § Predicate.

### Two required clauses

A session-restart-gating predicate MUST combine **both** of the following clauses joined by logical AND:

1. **State-input clause** — the condition that signals the gate is needed (e.g., `references.modified_files` intersects `marketplace/bundles/plan-marshall/` for the self-host fence). This clause answers "is the gate relevant to this plan at all?".
2. **Cache-freshness clause** — the anchor that falsifies after the prescribed session restart (e.g., absent `head_at_completion` OR worktree `HEAD` diverged from the recorded value). This clause answers "has the remediation actually been performed since the gate last fired?".

The loop trap that motivates the contract: a single-input predicate keyed only on plan-state inputs evaluates `true` identically across session restarts because plan-state survives the restart unchanged. Without a freshness signal the same `true` that halted the first run halts every re-entry forever — the gate never releases. The two-clause AND is the structural escape: clause (1) stays `true` across restarts, but clause (2) flips to `false` after the user performs the prescribed remediation, and the AND collapses.

### Canonical freshness anchor

The canonical anchor is `head_at_completion`, persisted on `mark-step-done --outcome done` by the dispatcher's per-step completion metadata. The anchor's lifecycle requirement verbatim: **"survives crash, falsifies on clean re-entry against unchanged worktree."** See [`marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md`](../../../../marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md) for the persistence semantics.

Authors who need a different anchor (e.g., a registry digest, a config-file hash) MUST document why `head_at_completion` is insufficient and confirm the substitute satisfies the same lifecycle requirement.

### Outcome-recording requirement on halt

The dispatcher's `done → skip` resumability rule satisfies clause (2) implicitly for the common case — once a step records `outcome=done`, the dispatcher short-circuits before the predicate evaluates on re-entry. The corollary: session-restart-gating steps MUST record `outcome=failed` (NOT `done`) when the halt fires, otherwise the next session's resumable-re-entry skip path bypasses the predicate entirely without releasing the gate.

The `outcome=failed` recording is the dispatcher-side signal that the step needs a retry-once dispatch on next session entry; clause (2) of the predicate then falsifies on that retry (because the session is fresh by construction), the AND collapses, and the step records `outcome=done` on the retry path.

### Current implementors

The session-restart-gate pattern is implemented today by exactly one step:

- `project:finalize-step-self-host-fence` — gates plan-marshall self-modification plans behind a session restart so the in-process skill registry is rebuilt from the synced cache before downstream agent-dispatched steps run.

Future authors: add yourselves here when you ship a session-restart-gating finalize step, so this list stays an accurate inventory rather than a snapshot.

### Audit result inline

The audit performed for this lesson confirmed that **only** `project:finalize-step-self-host-fence` implements the session-restart-gate pattern today. Two adjacent finalize-set patterns were inspected and ruled out:

- **HEAD-dependent finalize set** (`default:pre-push-quality-gate`, `default:automated-review`, `default:sonar-roundtrip`, `default:commit-push`) — these steps persist `head_at_completion` for **loop-back HEAD-advance detection**, not session-restart gating. The anchor falsifies when HEAD advances mid-finalize (forcing a re-run of HEAD-dependent steps in the same session), not when a session restart occurs. Different predicate shape, different remediation, different invariant.
- **Conditional HEAD-dependent set** (`project:finalize-step-deploy-target`, `project:finalize-step-sync-plugin-cache`) — these steps also persist `head_at_completion` for the same loop-back-detection purpose. They are NOT session-restart gates: their predicates do not halt the dispatcher behind a session-restart requirement; they re-run when HEAD diverges from the cached completion anchor.

Zero other implementors of the session-restart-gate pattern exist in the marketplace at audit time. The list above is the complete inventory.

### Cross-references

- Lesson [`2026-05-18-23-001`](../../../../marketplace/bundles/plan-marshall/skills/manage-lessons/standards/lessons.md) — "Session-restart fence predicates need a cache-freshness guard or they loop", the captured anti-pattern that motivates this contract.
- [`../SKILL.md`](../SKILL.md) § Predicate — the worked two-clause implementation for `project:finalize-step-self-host-fence`, including the resumable-re-entry semantics that the `outcome=failed` recording rule above interacts with.
- [`## The Invariant`](#the-invariant) — the structural mismatch that session-restart gates exist to enforce.
- [`## The Three Failure Surfaces`](#the-three-failure-surfaces) — the three resolution boundaries (skill, workflow-notation, manifest content) that motivate the cache-sync + session-restart two-part remediation.
- [`## Scope`](#scope) — the narrowing rule that restricts session-restart-gate applicability to plans modifying `marketplace/bundles/plan-marshall/`.

## Cross-References

- [`../SKILL.md`](../SKILL.md) § Halt protocol — the mandatory halt-and-restart gate placed after `finalize-step-sync-plugin-cache` in the finalize workflow.
- `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-execution-context-workflow.md` § Workflow-Resolution Root — the cache-as-resolution-root contract for surface (2).
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/SKILL.md` § Manifest-on-Write Semantics — the baked-at-write / not-re-resolved-at-read semantics for surface (3).
