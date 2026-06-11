---
name: default:pre-push-quality-gate
description: Run quality-gate per affected bundle as the last gate before commit-push
order: 5
---

# Pre-Push Quality Gate

Pure executor for the `pre-push-quality-gate` finalize step. Runs `quality-gate` once per unique bundle derived from the plan's live footprint (the `compute-footprint` query against the worktree), immediately before `default:commit-push` (`order: 10`). This is the deterministic last-line guard against type/lint regressions reaching remote CI — converting soft "consider quality-gate" guidance into a hard precondition for push.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

This document carries NO step-activation logic. Activation is controlled by the manifest composer in `manage-execution-manifest/scripts/manage-execution-manifest.py` via the `pre_push_quality_gate_inactive` pre-filter (see `manage-execution-manifest/standards/decision-rules.md`). When the dispatcher runs this step the executor always runs to completion: a clean run records `outcome=done`; a failed bundle invocation records `outcome=failed` and halts the phase. The `commit_strategy == none` case is also filtered at composition time (the `commit_strategy_none` pre-filter strips both `commit-push` AND `pre-push-quality-gate`), so this step is never dispatched without a downstream push.

## Inputs

- `git working-tree state` — the live footprint, computed on demand from the worktree by the `manage-references compute-footprint` query (below): the union of the three-dot diff (`git diff --name-only {base_ref}...HEAD`) and the porcelain working-tree state (`git status --porcelain`). There is no persisted ledger; the footprint is always derived live from the worktree, which is the single source of truth.
- `build.map` globs — the fnmatch globs collected from every `{glob, role, build_class}` entry in `build.map`. The manifest composer already gated activation on whether the footprint matches any of these globs; the executor re-reads them to scope which live-and-intended entries should contribute to bundle derivation (defense-in-depth — only entries that match a registered build_map glob feed bundle derivation).
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). The `quality-gate` build invocation below MUST identify the worktree via `--plan-id {plan_id}` (which auto-resolves through `manage-status get-worktree-path`) — **not** the `--project-dir {worktree_path}` escape hatch. This is a hard requirement, not a stylistic preference: the freshness-relevant build-log line that `pyproject_build run` emits must land in the **plan-scoped** execution-log tier (`.plan/local/plans/{plan_id}/logs/script-execution.log`), because the immediately-following `default:commit-push` (`order: 10`) step runs the `pre-commit-verify-freshness` gate, which reads exactly that plan-scoped log to confirm the worktree was verified after its last source mutation. The `--project-dir` escape hatch routes the executor's two-tier audit-log entry to the **global** tier instead, where the freshness gate cannot see it — producing a false-negative `stale`/`undecidable` verdict and a refused push even though the gate just ran. The two flags are mutually exclusive (Bucket B two-state contract); for this freshness-relevant call site, `--plan-id` is the only correct choice. See `manage-tasks/SKILL.md` § "Pre-Commit Verify Freshness" for the gate that consumes the plan-scoped log line.

## Execution

### Read the live footprint

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references \
  compute-footprint --plan-id {plan_id} --worktree-path {worktree_path}
```

Extract the `files` array from the TOON output. This is the live footprint derived from the worktree — the union of the three-dot `{base_ref}...HEAD` diff and the porcelain working-tree state — so it already reflects only what is actually modified now. A file that was touched then reverted does not appear, so it forces no redundant `quality-gate` run against a bundle with no actual changes.

### Read the build_map globs

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  build-map read --audit-plan-id {plan_id}
```

Extract `build_map` (the domain-keyed `{glob, role, build_class}` map) from the TOON output and collect the set of `glob` values across every domain entry. The manifest composer guarantees the footprint matches at least one of these globs when this step is dispatched, but the executor reads them again for defense-in-depth.

### Derive unique bundle set

For each entry `path` in `files`:

1. Skip the entry if it matches none of the build_map globs (using `fnmatch.fnmatch`).
2. If the entry begins with `marketplace/bundles/`, take path segment 2 as the bundle (e.g., `marketplace/bundles/plan-marshall/skills/.../foo.py` → `plan-marshall`).
3. Otherwise, if the entry begins with `test/`, take path segment 1 as the bundle (e.g., `test/plan-marshall/.../test_foo.py` → `plan-marshall`).
4. Otherwise, the entry contributes no bundle (drop silently).

Collect the resulting bundle names into a sorted, de-duplicated list `bundles`. Let `N = len(bundles)`.

### Run quality-gate per bundle

For each `bundle` in `bundles` (in sorted order):

```bash
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build \
  run --command-args "quality-gate {bundle}" --plan-id {plan_id}
```

Inspect the TOON output. On `status: error`, halt: stop iterating, record the failing bundle, and proceed to **Mark Step Complete (Failure)** below. The underlying `pyproject_build` TOON output already carries `errors[N]{file,line,message,category}` — surface the offending file/line via the standard finalize TOON.

If every bundle succeeds (`status: success` for all `N` invocations), proceed to **Mark Step Complete (Success)**.

## Mark Step Complete

Record the outcome on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

**Branch A — all bundles green**:

Immediately before invoking `mark-step-done`, resolve the worktree HEAD SHA so the dispatcher can detect a stale completion record after a downstream loop-back commit advances HEAD:

```bash
git -C {worktree_path} rev-parse HEAD
```

The `{worktree_path}` value is the path resolved by `phase-6-finalize` Step 0 (Resolve Worktree and Main Checkout Paths). Do NOT re-resolve it from any other cwd or shell context — the canonical resolution lives in Step 0 and propagates into every standards document loaded by the finalize pipeline. Capture the stdout as `{sha}` (a 40-character hex SHA) and forward it via `--head-at-completion`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step pre-push-quality-gate --outcome done \
  --display-detail "quality-gate green for {N} bundle(s)" \
  --head-at-completion {sha}
```

The persisted `head_at_completion` field is consumed by phase-6-finalize Step 3's resumable re-entry check: when the worktree HEAD has advanced past `{sha}` (typically because `automated-review` or `sonar-roundtrip` opened a loop-back fix-task that produced a new commit), the dispatcher re-fires this gate against the newer HEAD instead of skipping it.

**Branch B — at least one bundle failed**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step pre-push-quality-gate --outcome failed \
  --display-detail "quality-gate failed for {bundle}"
```

The failure branch does not need `--head-at-completion`: the dispatcher unconditionally retries `failed` records on re-entry regardless of HEAD, so the SHA carries no decision value here. The dispatcher's existing failure handling halts the phase on `outcome=failed` and surfaces the offending file/line through the finalize TOON, matching the contract used by the other gating steps.
