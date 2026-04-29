# Sync Worktree With Main

Full procedure for the `phase-5-execute` Step 3 "Sync Worktree With Main" action. The SKILL.md inlines the step flow; this document is the authoritative reference for git invocations, fast-path semantics, the conflict contract, and the main-checkout fallback.

**Scope note**: The `rebase_on_execute_start` opt-out documented below is a **user-facing config switch** for the sync step itself — it is **not** part of the manifest-driven verification-step selection (which lives in `phase_5.verification_steps` from `manage-execution-manifest`). Sync is a worktree-hygiene action that always runs unless the user explicitly opted out via config; whether it fires has nothing to do with the manifest's verification-step decisions.

## Purpose

Between `phase-1-init` and `phase-5-execute` the user may spend significant time in refine/outline/plan while `origin/{base_branch}` moves forward. Syncing at the start of execute keeps coding on a current base rather than discovering drift at `phase-6-finalize` (after the entire execute phase has already run). `phase-6-finalize`'s `pr update-branch` remains as a second-line safety net for long-running execute runs or plans where the sync step was skipped.

## Inputs

| Source | Field | Purpose |
|--------|-------|---------|
| `marshal.json` (via `manage-config plan phase-5-execute get`) | `rebase_on_execute_start` | Opt-out switch (default `true`). When `false`, the whole step is skipped. |
| `marshal.json` (via `manage-config plan phase-5-execute get`) | `rebase_strategy` | `merge` (default) or `rebase`. Controls the sync operation. |
| `references.json` (via `manage-files read`) | `base_branch` | The branch to fetch and sync against. Set at `phase-1-init` Step 6. |
| `references.json` (via `manage-files read`) | `worktree_path` | Target of every `git -C` invocation. Absent when the plan runs against the main checkout. |

## Strategy Semantics

| Strategy | Command | Behavior | PR safety |
|----------|---------|----------|-----------|
| `merge` (default) | `git -C {worktree_path} merge --no-edit origin/{base_branch}` | Adds a merge commit bringing in base changes. No history rewrite. Matches `phase-6-finalize`'s `pr update-branch` semantics. | PR-safe — no force-push required. |
| `rebase` | `git -C {worktree_path} rebase origin/{base_branch}` | Replays feature-branch commits on top of the updated base. Rewrites history. | Requires `git push --force-with-lease` if the PR is already open. |

## Procedure

### 1. Read config

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get --field rebase_on_execute_start --audit-plan-id {plan_id}

python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get --field rebase_strategy --audit-plan-id {plan_id}
```

If `rebase_on_execute_start` is `false`, skip the remainder of this procedure and emit:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (plan-marshall:phase-5-execute) Sync skipped: rebase_on_execute_start=false"
```

### 2. Resolve worktree path and base branch

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files read \
  --plan-id {plan_id} --file references.json
```

Parse the returned JSON and extract `base_branch` and `worktree_path`.

**Main-checkout fallback**: when `worktree_path` is absent (plan runs against the main checkout rather than an isolated worktree), substitute `.` for `{worktree_path}` in every git command below. All other semantics — fetch, fast-path SHA check, strategy application, and conflict contract — are identical. The `cd && git` compound form is STILL forbidden in main-checkout mode; always use `git -C .`.

### 3. Fetch origin

```bash
git -C {worktree_path} fetch origin {base_branch}
```

If the fetch itself fails (e.g., network or auth error), abort fail-loud per the conflict contract below (the origin reference is unavailable, so no sync decision can be made safely).

### 4. Fast-path SHA check

```bash
git -C {worktree_path} merge-base --is-ancestor origin/{base_branch} HEAD
```

Exit code `0` → `origin/{base_branch}` is already an ancestor of `HEAD`; the feature branch contains the base tip and no sync operation is needed. Log and exit this step:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (plan-marshall:phase-5-execute) Sync skipped: already up to date with origin/{base_branch}"
```

Exit code `1` → base has moved forward; continue to strategy application.

### 5. Apply strategy

First, record the current HEAD so the success path (section 7) can compute the incorporated commit range:

```bash
git -C {worktree_path} rev-parse HEAD
```

Record the output as `{previous_HEAD}`. Then apply the chosen strategy:

**`merge`**:

```bash
git -C {worktree_path} merge --no-edit origin/{base_branch}
```

**`rebase`**:

```bash
git -C {worktree_path} rebase origin/{base_branch}
```

### 6. Conflict contract (fail-loud)

If the strategy command exits non-zero:

1. **Do NOT auto-resolve** — no `git mergetool`, no heuristic merging, no retries.
2. **Do NOT continue** into the execute loop. Abort the phase before Step 4 runs.
3. **Leave conflict markers in place**. The user will see them in the worktree and resolve manually.
4. **Surface the failure** to `work.log` at ERROR level, including `{worktree_path}`, the strategy used, and the list of conflicted files:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level ERROR \
     --message "[ERROR] (plan-marshall:phase-5-execute) Sync conflict at {worktree_path} — strategy={strategy}, conflicted files: {files}. Phase aborted; resolve manually and re-run."
   ```

5. Conflicted files come from `git -C {worktree_path} diff --name-only --diff-filter=U`.

**Rationale for fail-loud**: Auto-resolving a base-drift conflict risks silently discarding either the feature work or the base update. The user is the only party with enough context to decide which side wins for each hunk. Fail-loud also matches `phase-6-finalize`'s `pr update-branch` behavior when GitHub reports merge conflicts.

### 7. Success path — record incorporated commits

On a successful merge or rebase, compute the short-SHA range of commits that were pulled in from base, using the `{previous_HEAD}` captured at the start of section 5:

```bash
git -C {worktree_path} rev-list --abbrev-commit --reverse {previous_HEAD}..HEAD
```

Record the output as `{short_sha_range}`. Log to `decision.log`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-5-execute) Synced worktree with origin/{base_branch} via {strategy} — commits {short_sha_range}"
```

Proceed to Step 4 (Log Phase Start and Surface Active Worktree).

## Interaction With `phase-6-finalize`

`phase-6-finalize`'s `branch-cleanup.md` step invokes `tools-integration-ci:ci pr update-branch` when GitHub reports `merge_state == behind`. That is a *remote* merge-from-base via the CI provider API, intended to catch drift that accumulated *during* the execute phase (long-running plans, late base pushes).

With `rebase_on_execute_start=true`, the phase-5 sync is the primary defense and `pr update-branch` becomes a second-line safety net. When `rebase_on_execute_start=false`, `pr update-branch` remains the only sync point. The two steps are complementary, not redundant.

## Related

- `phase-5-execute/SKILL.md` — Step 3 inlines this procedure.
- `phase-1-init/SKILL.md` — Step 6 creates the worktree and records `base_branch` and `worktree_path` in `references.json`.
- `phase-6-finalize/standards/branch-cleanup.md` — Documents the `pr update-branch` safety-net role.
- `plan-marshall:tools-integration-ci` — Provides the `pr update-branch` subcommand used at phase-6.
