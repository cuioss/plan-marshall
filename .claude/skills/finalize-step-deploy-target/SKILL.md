---
lane:
  class: derived-state
  cost_size: XS
name: finalize-step-deploy-target
description: Generate every harness target tree (claude, opencode, antigravity) via the multi-target generator
mode: script-executor
order: 81
mutates_source: false
default_on: false
presets: []
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Finalize Step — Deploy Target (project-local)

Project-local executor for `project:finalize-step-deploy-target`.
Always invokes the multi-target generator once per harness to emit the
three target trees the sync step consumes: `target/claude/`,
`target/opencode/` and `target/antigravity/`. The generator itself
handles the no-op case (for the `claude` target, the equality engine
short-circuits the per-bundle write when output already matches
sources), so this step has **no skip detector**: it always runs, each
generator call always reports an outcome, and this executor records the
step outcome from those reports.

The emitted Claude tree contains both per-bundle artifacts
(`target/claude/{bundle}/`, including each bundle's regenerated
`.claude-plugin/plugin.json` with variant-aware `agents:` entries and
an empty `skills:` array so the runtime's default folder scan owns
skill discovery without double-loading) and a top-level
`target/claude/.claude-plugin/marketplace.json` that lets Claude Code
register `target/claude/` itself as a marketplace. The Claude target's
equality engine validates both before returning success. The OpenCode
tree (`skill/`, `agent/`, `command/`) and the Antigravity tree
(`skills/`, `agents/`, `commands/`) carry the layouts the sync step
deploys into those harnesses.

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
the three target trees here means every harness install the sync step
writes is derived from the same authoritative merged source tree the
dispatcher just wrote to.

## Ordering

The canonical Phase 6 ordering surrounding this step is:

```text
default:branch-cleanup (70) →
project:finalize-step-deploy-target (81) →
project:finalize-step-sync-plugin-cache (85)
```

`order: 81` places this step immediately after `default:branch-cleanup`
and before `project:finalize-step-sync-plugin-cache`. The generator must
run on the post-merge main checkout so the sync that follows mirrors the
just-regenerated `target/` content into every harness install. On-main
executor regeneration is performed by
`project:finalize-step-sync-plugin-cache` (order 85) after the sync, in
both worktree and no-worktree finalize flows — `integrate_into_main`
(invoked during the move-back, before `branch-cleanup`) performs the
plan-dir move-back only and does NOT regenerate the executor. The
executor is per-tree derived state (generated, not file-moved) per
ADR-002.

## Inputs

- `{plan_id}` — required. Used for logging.

## Execution

Inline-only — this step does NOT delegate to a Task agent. The
generator is a fast, deterministic Python script.

### 1. Invoke the generator once per harness

Three separate calls, one per target. Run all three even when an earlier
one fails, so every harness that can be regenerated is, and the failure
is reported per target:

```bash
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "generate-claude"
```

```bash
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "generate-opencode"
```

```bash
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "generate-antigravity"
```

Each call runs the matching `./pw generate-{target}` alias through the
build executor. The executor form is required, not a style choice: the
enforcement hook denies a direct `./pw` call inside a plan context, and
the wrapper itself is still what runs the generator (`uv` lives only in
the project-local `.pyprojectx/` tree). Each `generate-{target}` alias in
`pyproject.toml` carries its own `--target {target} --output
target/{target}` arguments.

### 2. Read the result

Each call returns a TOON document. Read its `status` field — the
executor exits `0` even when the build failed, so the process exit code
carries no verdict:

| TOON `status` | Meaning |
|---------------|---------|
| `success` | Generation of `{target}` completed |
| `error` | Generation of `{target}` failed; the generator's `error: …` line is in the build log the TOON's `log_file` names |

The step outcome combines the three calls:

| TOON status | Outcome |
|-------------|---------|
| all three `success` | `outcome=done` |
| any call not `success` | `outcome=failed`, surfacing the failing target's `error: …` line |

The generator's own output (`{target}: produced {N} entries`, the
stamping summary, any `warning: …`) lands in that build log, not on the
call's stdout.

### 3. Mark step complete

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step project:finalize-step-deploy-target \
  --outcome {done|failed} \
  --display-detail "{display_detail}"
```

When all three calls report `status: success`, `{display_detail}` is
`"claude, opencode, antigravity regenerated in target/"`. When any call
reports anything else, set `--outcome failed` and surface the failing
target's `error: …` line from its build log verbatim in
`--display-detail` so the renderer shows the underlying failure; when
more than one target failed, name each failed target ahead of its line.

## Why "always run" instead of a skip detector

The equality-check engine inside the Claude target already
short-circuits per-bundle when the generated output equals the
committed plugin.json (no write, no diff). Asking the dispatcher to
second-guess this is duplicate logic that drifts. Even when the diff
is empty for marketplace sources, a target tree may be stale or absent
on disk (e.g. user ran `target/` cleanup manually). Always running
guarantees the on-disk `target/claude/`, `target/opencode/` and
`target/antigravity/` state matches sources before the sync step
consumes it. The generator's idempotence is the contract that makes
"always run" free.
