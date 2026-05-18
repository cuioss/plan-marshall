---
name: finalize-step-self-host-fence
description: Halt the finalize dispatcher when the running plan modifies plan-marshall itself, requiring a session restart before downstream agent-dispatched steps
order: 15
---

# Finalize Step — Self-Host Fence (project-local)

Project-local executor for `project:finalize-step-self-host-fence`. Halts the
phase-6-finalize dispatcher when the in-flight plan modifies the
`plan-marshall` bundle itself, demanding a Claude Code session restart
before any subsequent agent-dispatched finalize step runs.

This step is **project-local** rather than a `default:` built-in because
only meta-projects that author the `plan-marshall` bundle can trip the
self-host blind spot. Consumer projects of plan-marshall never modify the
bundle's own files, so they never need the fence — and would only see noise
if the step were seeded into their `marshal.json` defaults. The placement
parallels `project:finalize-step-sync-plugin-cache` (project-local for the
same "meta-project only" reason).

## Ordering

The canonical Phase 6 ordering surrounding this step is:

```
default:commit-push (10) →
project:finalize-step-deploy-target (12) →
project:finalize-step-sync-plugin-cache (14) →
project:finalize-step-self-host-fence (15) →
default:create-pr (20)
```

`order: 15` places this step immediately after
`project:finalize-step-sync-plugin-cache` (so the cache is freshly synced
from `target/claude/` before the fence evaluates its predicate) and before
`default:create-pr` (so any downstream agent-dispatched step is halted
behind the fence until the session restart completes).

## Inputs

- `{plan_id}` — required. Used to read `references.modified_files`, log the
  halt event, and emit the resumable-re-entry signal.

## Predicate

The fence fires iff **both** of the following hold:

1. `references.modified_files` intersects
   `marketplace/bundles/plan-marshall/`. Plans that touch sibling bundles
   only (`pm-dev-java`, `pm-documents`, etc.) do not trigger the fence —
   those bundles' modified skills become visible to the next session
   naturally, and the running finalize dispatch is unaffected because its
   own hot path is unchanged.
2. **Cache-freshness guard**: the in-process Claude Code session is the
   same one that produced the modifications — i.e. the prior dispatcher
   state for this step is either absent (first dispatch in this plan) or
   `outcome=failed` from a fence trigger that has not yet been cleared by
   a session restart. The dispatcher distinguishes these two cases via the
   `manifest.phase_6.steps[project:finalize-step-self-host-fence]` record:

   - **No record** → first dispatch in this plan. The session that called
     `phase-5-execute` is the one whose in-process skill registry holds
     the pre-change skill bodies; the fence MUST fire so the user
     restarts before any downstream agent loads stale skills.
   - **`outcome=failed`** → retry-once after the prescribed session
     restart. The session is fresh by construction (the `[BLOCKED]` halt
     prevented in-session continuation), so the in-process skill registry
     was rebuilt from the synced cache during session boot. The
     cache-freshness guard is satisfied; the fence records `outcome=done`
     and the dispatcher advances. See § Resumable re-entry semantics
     below.
   - **`outcome=done`** → unreachable inside the predicate (the
     dispatcher's `done → skip` rule short-circuits before the predicate
     evaluates).

The two-clause predicate is the source of truth for the apparent
inconsistency between this section and § Resumable re-entry: the fence
re-evaluates on every dispatch, but clause (2) flips between sessions
even though clause (1) does not. `modified_files` alone is not enough —
without the cache-freshness guard the dispatcher would loop on the fence
forever, because the modified-files set is plan-scoped and survives
session restarts unchanged.

## Halt protocol

**This fence is normative, not advisory.** When the predicate matches,
the dispatcher MUST halt immediately and refuse to dispatch any subsequent
agent-loaded step in the same Claude Code session.

The fence is the single structural guard against the self-host blind
spot — see [`standards/self-host-blind-spot.md`](standards/self-host-blind-spot.md)
for the invariant and its three failure surfaces. The two-part
remediation (cache sync + session restart) cannot be collapsed into the
sync step alone: synchronising the cache does NOT refresh the host
platform's in-process skill registry, so any agent dispatched in the same
session continues to load the pre-sync skill bodies and workflow
notations from its registry snapshot.

### 1. Log the fence trigger

Emit the canonical `[BLOCKED]` work-log line naming the modified
plan-marshall paths from `references.modified_files`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING \
  --message "[BLOCKED] (project:finalize-step-self-host-fence) plan-marshall self-modification detected — modified_files: {paths}. Session restart required before subsequent finalize steps."
```

### 2. Emit the canonical halt instruction

Surface the verbatim halt instruction to the user as the step's
`display_detail` and in chat output:

> `"plan-marshall self-modification detected — session restart required before subsequent finalize steps. Re-enter /plan-marshall action=finalize plan={plan_id} in a fresh Claude Code session."`

### 3. Mark the step blocked and return

Record the step outcome as `failed` (so the dispatcher's resumable-re-entry
semantics treat the fence as a retry candidate on next session entry, not a
completed step) with the canonical display detail:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step project:finalize-step-self-host-fence \
  --outcome failed \
  --display-detail "session-restart fence triggered"
```

Return the structured payload:

```toon
status: blocked
display_detail: "session-restart fence triggered"
plan_id: {plan_id}
modified_files[N]:
  - marketplace/bundles/plan-marshall/skills/.../...
  - ...
```

Do NOT advance the manifest pointer. Do NOT mark the next step `failed`.

## Why the fence is mandatory, not advisory

Surfaces (1) and (2) in the blind-spot invariant — skill resolution and
workflow-notation resolution — both bind to the in-process registry. An
advisory "consider restarting" note that left the dispatcher free to
continue would let the dispatched `create-pr`, `automated-review`, or
`lessons-capture` agent execute against stale skill bodies, producing a
PR description / review comment / lesson record that reflects the
pre-change shape of the very code the plan just shipped.

The fence MUST NOT be skippable by a `--force` flag or a per-plan opt-out;
the only escape is the prescribed session restart.

## Resumable re-entry semantics

The fresh Claude Code session re-enters `/plan-marshall action=finalize`
and the dispatcher walks `manifest.phase_6.steps` from the start. Steps
recorded `outcome=done` in the prior session are skipped (including
`project:finalize-step-sync-plugin-cache`). The fence step itself was
recorded `outcome=failed`, so the dispatcher retries it once — and on the
re-entry the predicate no longer trips the halt path: clause (2) of the
predicate (the cache-freshness guard documented in § Predicate above) is
satisfied because the fresh session's in-process skill registry was
rebuilt from the synced cache during session boot. Clause (1) still
matches (`modified_files` is plan-scoped and unchanged across sessions),
but the two-clause AND requires both — so the fence records
`outcome=done` and the dispatcher continues into `default:create-pr`.

The detailed resumable-re-entry contract — including the
`done → skip` / `failed → retry-once` / `no-record → fresh run` rules —
is documented in the dispatcher itself; see
`marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`
§ Step 3 (Execute Step Pipeline).

## Related

- [`standards/self-host-blind-spot.md`](standards/self-host-blind-spot.md) —
  the invariant and its three failure surfaces.
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`
  § Step 3 — the dispatcher loop and resumable-re-entry semantics this
  step participates in.
- `.claude/skills/finalize-step-sync-plugin-cache/SKILL.md` — the
  immediately-preceding step in the canonical ordering, which addresses
  the filesystem half of the two-part remediation (cache sync).
