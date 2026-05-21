---
name: finalize-step-deploy-target
description: Generate Claude Code target output via the multi-target generator
order: 80
---

# Finalize Step — Deploy Target (project-local)

Project-local executor for `project:finalize-step-deploy-target`.
Always invokes the multi-target generator to emit the Claude Code
output tree at `target/claude/`. The generator itself handles the
no-op case (when output already matches sources, the equality engine
inside the `claude` target short-circuits the per-bundle write), so
this step has **no skip detector**: it always runs, the generator
always returns a status, and this executor records the outcome from
that status.

The emitted tree contains both per-bundle artifacts
(`target/claude/{bundle}/`, including each bundle's regenerated
`.claude-plugin/plugin.json` with variant-aware `agents:` entries and
an empty `skills:` array so the runtime's default folder scan owns
skill discovery without double-loading) and a top-level
`target/claude/.claude-plugin/marketplace.json` that lets Claude Code
register `target/claude/` itself as a marketplace. The Claude target's
equality engine validates both before returning success, so a successful
finalize step proves the full deliverable is consistent.

This step is **project-local** (under `.claude/skills/`) rather than a
`default:` built-in because the generator pipeline only makes sense for
this repo (the plan-marshall meta-project): consumer projects that
install plan-marshall as a plugin do not have a `marketplace/bundles/`
tree to generate from. The generator entry point
(`marketplace/targets/generate.py`) is also meta-project-only — it sits
at the repo root, outside `marketplace/bundles/`, so it never ships to
consumers via plugin install.

This step runs on the main checkout post-merge, after
`default:branch-cleanup` has removed the plan's worktree. Regenerating
`target/claude/` here means the next session boot re-derives a clean
host plugin cache from the same authoritative merged source tree the
dispatcher just wrote to.

## Ordering

The canonical Phase 6 ordering surrounding this step is:

```
default:branch-cleanup (70) →
project:finalize-step-deploy-target (80) →
project:finalize-step-sync-plugin-cache (85) →
project:finalize-step-regenerate-executor (90)
```

`order: 80` places this step immediately after `default:branch-cleanup`
and before `project:finalize-step-sync-plugin-cache`. The generator must
run on the post-merge main checkout so the cache sync that follows mirrors
the just-regenerated `target/claude/` content. `project:finalize-step-regenerate-executor`
runs last (order 90) so it scans a cache already refreshed by the
sync step.

## Inputs

- `{plan_id}` — required. Used for logging.

## Execution

Inline-only — this step does NOT delegate to a Task agent. The
generator is a fast, deterministic Python script.

### 1. Invoke the generator

```bash
python3 marketplace/targets/generate.py --target claude --output target/claude
```

The script returns a TOON document on stdout describing the run.
Capture exit code and stdout.

### 2. Parse the result

| Field | Meaning |
|-------|---------|
| `status: success` | Generation completed; record `outcome=done` and use `emitted_count` for the display detail |
| `status: error` | Generation failed; record `outcome=failed` and surface the `error` field in `display_detail` |

### 3. Mark step complete

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step project:finalize-step-deploy-target \
  --outcome {done|failed} \
  --display-detail "{N} files emitted to target/claude/"
```

On `status: success`, `{N}` is the integer from `emitted_count` and the
`display_detail` reads `"{N} files emitted to target/claude/"`. On
`status: error`, set `--outcome failed` and surface the generator's
`error` field verbatim in `--display-detail` so the renderer shows the
underlying failure.

## Why "always run" instead of a skip detector

The equality-check engine inside the Claude target already
short-circuits per-bundle when the generated output equals the
committed plugin.json (no write, no diff). Asking the dispatcher to
second-guess this is duplicate logic that drifts. Even when the diff
is empty for marketplace sources, the generator's output may be stale
on disk (e.g. user ran `target/` cleanup manually). Always running
guarantees the on-disk `target/claude/` state matches sources before
the cache sync step consumes it. The generator's idempotence is
the contract that makes "always run" free.
