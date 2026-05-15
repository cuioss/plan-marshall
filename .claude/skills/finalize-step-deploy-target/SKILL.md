---
name: finalize-step-deploy-target
description: Generate Claude Code target output via the multi-target generator
order: 12
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

## Ordering

The canonical Phase 6 ordering surrounding this step is:

```
default:commit-push (10) →
project:finalize-step-deploy-target (12) →
project:finalize-step-sync-plugin-cache (14) →
default:create-pr (20)
```

`order: 12` places this step immediately before
`project:finalize-step-sync-plugin-cache` and before
`default:create-pr`. The generator must run before the cache sync (so
the cache has fresh `target/claude/` content) and before the PR is
created (so the diff visible to reviewers includes the target output
that downstream steps pick up).

## Inputs

- `{plan_id}` — required. Used to resolve the worktree path and for logging.

## cwd contract — why this step takes explicit absolute paths

The Claude Code Bash sandbox does NOT `cd` into the worktree before
invoking finalize steps. Every Bash call runs from the main checkout's
cwd. Relying on `Path.cwd()` inside the generator (or any cwd-relative
path in this SKILL) would therefore generate into the main checkout's
`target/claude/`, not the worktree's — silently leaving the worktree
unchanged and propagating stale content to the downstream
`finalize-step-sync-plugin-cache` step.

To avoid that failure mode, this step resolves `{worktree_path}`
explicitly and passes absolute paths to both the script and its
`--output` flag. Do NOT shorten the invocation to the cwd-relative form
`python3 marketplace/targets/generate.py --target claude --output target/claude`
— that variant only works when the caller cd's into the worktree first,
which finalize steps do not.

## Execution

Inline-only — this step does NOT delegate to a Task agent. The
generator is a fast, deterministic Python script.

### 1. Resolve worktree path

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  get-worktree-path --plan-id {plan_id}
```

Parse `worktree_path` from the TOON output. When `metadata.use_worktree==false`
the script returns the main checkout absolute path, so `{worktree_path}`
is always set after this call.

### 2. Invoke the generator

```bash
python3 "{worktree_path}/marketplace/targets/generate.py" \
  --target claude --output "{worktree_path}/target/claude"
```

Quote both placeholders so the invocation survives a `{worktree_path}`
that contains spaces (rare on CI runners, common in developer-machine
checkouts under `Documents/` or similar).

The script returns a TOON document on stdout describing the run.
Capture exit code and stdout.

### 3. Parse the result

| Field | Meaning |
|-------|---------|
| `status: success` | Generation completed; record `outcome=done` and use `emitted_count` for the display detail |
| `status: error` | Generation failed; record `outcome=failed` and surface the `error` field in `display_detail` |

### 4. Mark step complete

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step project:finalize-step-deploy-target \
  --outcome {done|failed} --display-detail "{N} files emitted to target/claude/"
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
the cache sync and PR steps consume it. The generator's idempotence is
the contract that makes "always run" free.
