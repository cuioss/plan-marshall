---
name: finalize-step-sync-plugin-cache
description: Finalize-phase wrapper that syncs marketplace bundles to the Claude plugin cache by delegating to the sync-plugin-cache skill
user-invocable: false
allowed-tools: Skill
---

# Finalize Step: sync-plugin-cache

## Purpose

Keep `~/.claude/plugins/cache/plan-marshall/` in sync with the merged state of `marketplace/bundles/` after a plan finalizes. Without this step, Claude Code plugins silently load stale bundle code after a finalize completes, producing behavior that diverges from the freshly merged source tree until the cache is manually re-synced.

## Interface Contract

Invoked by `plan-marshall:phase-6-finalize` for projects that include `project:finalize-step-sync-plugin-cache` in their `phase-6-finalize.steps` list.

Accepts the standard finalize-step arguments:

- `--plan-id` — plan identifier (ignored; rsync is stateless)
- `--iteration` — finalize iteration counter (ignored; rsync is idempotent)

Both arguments are accepted for discovery-contract compliance but have no effect on execution. The underlying rsync operation is fully idempotent and can be re-run safely.

## Workflow

Load and run the underlying sync skill:

```
Skill: project:sync-plugin-cache
```

The `project:` prefix matches the notation used by phase-6-finalize when dispatching project-local skills (see `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` line 88), and is consistent with how this wrapper itself is referenced as `project:finalize-step-sync-plugin-cache` in `phase-6-finalize.steps`.

That skill performs parallel rsync of every bundle under `marketplace/bundles/` into `~/.claude/plugins/cache/plan-marshall/` with `--delete` semantics.

## Error Handling

rsync failures are **non-fatal**. Log the failure and continue — finalize must not block on a cache mismatch, because the cache can always be re-synced manually via the `/sync-plugin-cache` command after the plan is merged.

## Related

- [.claude/skills/sync-plugin-cache/SKILL.md](../sync-plugin-cache/SKILL.md) — underlying rsync implementation
- [marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md) — finalize phase that invokes this wrapper
