---
name: finalize-step-sync-plugin-cache
description: Synchronize the Claude plugin cache from target/claude/ via the consolidated sync engine
order: 14
---

# Finalize Step — Sync Plugin Cache (project-local)

Project-local executor for `project:finalize-step-sync-plugin-cache`.
Invokes the consolidated `sync.py` engine in the project-local
`.claude/skills/sync-plugin-cache/` skill to mirror `target/claude/`
into the host plugin cache.

This step is **project-local** rather than a `default:` built-in for
the same reason as `project:finalize-step-deploy-target`: the cache-
sync only makes sense for this repo (the plan-marshall meta-project).
Consumer projects have nothing to publish, so they don't get this step
seeded into their `marshal.json` defaults.

## Ordering

The canonical Phase 6 ordering surrounding this step is:

```
default:commit-push (10) →
project:finalize-step-deploy-target (12) →
project:finalize-step-sync-plugin-cache (14) →
default:create-pr (20)
```

`order: 14` places this step immediately after
`project:finalize-step-deploy-target` (so the cache mirrors the
just-generated `target/claude/` content) and before
`default:create-pr` (so the fresh cache is in place when downstream
agent-dispatched steps run).

## Inputs

- `{plan_id}` — required. Used to resolve the worktree path and for logging.

## cwd contract — why this step takes `--from-worktree` explicitly

The Claude Code Bash sandbox does NOT `cd` into the worktree before
invoking finalize steps. `sync.py`'s default source-root resolver
falls back to `Path.cwd() / 'target' / 'claude'` (see `sync.py`
`_resolve_source_root`), so without an explicit override it reads the
**main checkout's** `target/claude/` — which the preceding
`finalize-step-deploy-target` step did NOT write to (deploy-target
writes to the worktree's `target/claude/`). The staleness guard does
not catch the mismatch either: it compares cwd-derived source and
cwd-derived marketplace roots, so a consistent-but-stale main checkout
passes the guard cleanly.

The net effect of omitting the override is a `status: success` /
`synced_count: 10` return with the cache reflecting the previous
contents of main, not the in-flight worktree changes. This step
therefore resolves `{worktree_path}` explicitly and forwards it via
`--from-worktree`.

## Execution

Inline-only — this step does NOT delegate to a Task agent. The sync
engine is a fast Python script with deterministic output.

### 1. Resolve worktree path

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  get-worktree-path --plan-id {plan_id}
```

Parse `worktree_path` from the TOON output. When `metadata.use_worktree==false`
the script returns the main checkout absolute path, so `{worktree_path}`
is always set after this call.

### 2. Invoke the consolidated sync engine

```bash
python3 "{worktree_path}/.claude/skills/sync-plugin-cache/scripts/sync.py" \
  --from-worktree "{worktree_path}"
```

Quote both placeholders so the invocation survives a `{worktree_path}`
that contains spaces (rare on CI runners, common in developer-machine
checkouts under `Documents/` or similar).

`--from-worktree` overrides the cwd-based source resolver and binds
the sync to the worktree's `target/claude/` tree.

The script returns a TOON document with `status` (`success` |
`partial` | `error`), `synced_count`, `failed_count`,
`summary_message`, and a `synced[N]{bundle,version,status}` table.

### 3. Parse the result

| Field | Meaning |
|-------|---------|
| `status: success` | All bundles synced; record `outcome=done` and use `synced_count` for the display detail |
| `status: partial` | Some bundles failed; record `outcome=failed` and surface `summary_message` in `display_detail` |
| `status: error` | Hard failure (no bundles synced); record `outcome=failed` and surface `summary_message` |

### 4. Capture HEAD and mark step complete

This step is a member of `CONDITIONAL_HEAD_DEPENDENT_STEPS` (see
`marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`
§ Conditional HEAD-dependent steps). The dispatcher re-fires this step on
loop-back IFF `references.modified_files` (at the prior `done` mark)
intersects `marketplace/bundles/**` AND the live worktree HEAD has
advanced past the persisted `head_at_completion`. To make that
comparison meaningful, capture HEAD before `mark-step-done`:

```bash
git -C {worktree_path} rev-parse HEAD
```

Then forward the captured SHA to `mark-step-done` via
`--head-at-completion`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step project:finalize-step-sync-plugin-cache \
  --outcome {done|failed} --head-at-completion {sha} \
  --display-detail "{display_detail}"
```

On `status: success`, `{display_detail}` is `"{synced_count} bundles synced"`.
On `status: partial` or `status: error`, surface the engine's
`summary_message` field verbatim in `--display-detail` so the renderer
shows the underlying failure for triage.

## Related

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` § Conditional HEAD-dependent steps — defines `CONDITIONAL_HEAD_DEPENDENT_STEPS` membership and the `modified_files ∩ marketplace/bundles/**` re-fire predicate this step obeys.
