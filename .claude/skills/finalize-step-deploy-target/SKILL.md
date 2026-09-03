---
lane:
  class: derived-state
  cost_size: XS
name: finalize-step-deploy-target
description: Generate Claude Code target output via the multi-target generator
mode: script-executor
order: 81
mutates_source: false
default_on: false
presets: []
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Finalize Step — Deploy Target (project-local)

Project-local executor for `project:finalize-step-deploy-target`.
Always invokes the multi-target generator to emit the Claude Code
output tree at `target/claude/`. The generator itself handles the
no-op case (when output already matches sources, the equality engine
inside the `claude` target short-circuits the per-bundle write), so
this step has **no skip detector**: it always runs, the generator
always exits with an outcome code, and this executor records the
outcome from that exit code.

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
project:finalize-step-deploy-target (81) →
project:finalize-step-sync-plugin-cache (85)
```

`order: 81` places this step immediately after `default:branch-cleanup`
and before `project:finalize-step-sync-plugin-cache`. The generator must
run on the post-merge main checkout so the cache sync that follows mirrors
the just-regenerated `target/claude/` content. On-main executor regeneration
is performed by `project:finalize-step-sync-plugin-cache` (order 85) after the
cache sync, in both worktree and no-worktree finalize flows —
`integrate_into_main` (invoked during the move-back, before `branch-cleanup`)
performs the plan-dir move-back only and does NOT regenerate the executor. The
executor is per-tree derived state (generated, not file-moved) per ADR-002.

## Inputs

- `{plan_id}` — required. Used for logging.

## Execution

Inline-only — this step does NOT delegate to a Task agent. The
generator is a fast, deterministic Python script.

### 1. Invoke the generator

```bash
./pw generate-claude
```

Always go through the wrapper: `uv` is installed only into the
project-local `.pyprojectx/` tree and is not on `PATH`, so a bare
`uv run …` exits 127 outside it, and a bare `python3
marketplace/targets/generate.py` fails with `ModuleNotFoundError: No
module named 'yaml'` because PyYAML resolves into the uv-managed venv.
The `generate-claude` alias in `pyproject.toml` carries the
`--target claude --output target/claude` arguments.

Capture the exit code, stdout AND stderr. The generator reports its
outcome through the **exit code**, writes a human-readable per-target
summary to **stdout**, and writes every diagnostic to **stderr**. It
emits no machine-readable envelope, so there is nothing on stdout to
parse structurally.

### 2. Read the result

| Signal | Stream | Meaning |
|--------|--------|---------|
| exit code `0` | process status | Generation completed; record `outcome=done` |
| exit code `2` | process status | Generation failed; record `outcome=failed` |
| `claude: produced {N} entries` | stdout | `{N}` is the entry count for the display detail |
| `claude: stamped version {V} into {M} bundle plugin.json; emitted dist-manifest.json` | stdout | The post-generation stamping summary |
| `error: {text}` | stderr | The failure text to surface on `outcome=failed` |
| `warning: {text}` | stderr | A tolerated degradation (an unresolvable fingerprint in a partial marketplace checkout); does NOT change the outcome |

The exit code is the ONLY outcome signal — a run that failed for one
target still prints that target's earlier stdout lines, so a `produced`
line is not evidence of success on its own.

### 3. Mark step complete

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step project:finalize-step-deploy-target \
  --outcome {done|failed} \
  --display-detail "{N} files emitted to target/claude/"
```

On exit code `0`, `{N}` is the integer read from the `claude: produced
{N} entries` line and the `display_detail` reads `"{N} files emitted to
target/claude/"`. On exit code `2`, set `--outcome failed` and surface
the generator's `error: …` stderr line verbatim in `--display-detail` so
the renderer shows the underlying failure.

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
