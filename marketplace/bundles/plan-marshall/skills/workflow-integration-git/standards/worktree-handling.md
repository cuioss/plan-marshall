# Worktree Handling

Single canonical reference for the worktree mechanism used by plan-marshall: why it exists, where worktrees live, how they propagate through agent dispatch, the git invocation rule that applies inside them, the never-edit-main-checkout invariant, the cleanup ordering, and the `--plan-id` two-state contract that replaces per-call path forwarding.

This document is the source of truth. Sibling skills and standards reference it rather than duplicating the narrative. The per-call-site rule (e.g., "use `git -C` here", "pass `--plan-id` to the build wrapper there") stays at the call site; the worktree-specific application of that rule lives here.

## Why Worktrees

Plans run in **isolated git worktrees** for three independent reasons:

1. **Isolation** — uncommitted edits, generated files, and partial test runs stay confined to the plan's own working tree. A failed or aborted plan never pollutes the main checkout's index, working tree, or branch state.
2. **Parallelism** — multiple plans can execute simultaneously without contending for the main checkout's HEAD. Each worktree has its own branch and index; the only shared state is the `.git/` repository (commits, refs, objects) and the `.plan/` metadata directory (resolved via `git rev-parse --git-common-dir`).
3. **No main-checkout pollution** — the main checkout remains the user's primary working environment. The agent never edits, builds, or tests inside the main checkout while a plan is in flight.

A plan opts into worktree mode at `phase-1-init` via `branch_strategy: feature` (the default for new plans). Plans that target the main checkout directly (e.g., docs-only patches with `branch_strategy: main`) skip worktree allocation and run against the main checkout — every rule below that mentions `{worktree_path}` substitutes `{main_checkout}` for those plans.

## Path Convention (Platform-Neutral)

Worktrees live at the platform-neutral location:

```
<project_root>/.plan/local/worktrees/{plan-id}/
```

Rationale:

- `.plan/` is the canonical plan-state root that is already excluded from version control by every plan-marshall project's `.gitignore`. Placing worktrees under `.plan/local/worktrees/` inherits the same gitignore coverage without a separate carve-out.
- `local/` signals "host-local, do not transport" — the directory is a per-host scratch space, never published, never archived.
- `{plan-id}/` is the plan identifier (e.g., `lesson-2026-05-07-11-001`), one directory per active plan.

The path is computed by the worktree-handling layer; callers never construct it from string concatenation. Resolve it via:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status get-worktree-path \
  --plan-id {plan_id}
```

The script returns the absolute path when `metadata.use_worktree == true` and an empty string when the plan runs against the main checkout.

## Dispatch Protocol (Subagent Header Propagation)

When the plan runs in an isolated worktree, every subagent dispatch — `Task:`, `Skill:` invocations that accept free-form prompts, and `phase-agent` delegations — MUST embed the **Worktree Header** as the first lines of the dispatch prompt:

```
WORKTREE: --plan-id {plan_id}
All Edit/Write/Read tool calls MUST resolve against the worktree allocated for this plan.
Raw git/mvn/npm commands MUST operate against that worktree (use the tool's native cwd flag).
.plan/execute-script.py invocations that touch a working tree MUST pass --plan-id {plan_id};
manage-* scripts (Bucket A) remain cwd-agnostic and MUST NOT receive --plan-id.
NEVER edit the main checkout.
```

Two requirements coexist:

- **Prompt embedding** — the header propagates the constraint through free-form delegation so child agents inherit the worktree binding even when they call further subagents.
- **Parameter passing** — the structured input contract of the dispatched skill (e.g., `execute-task`, `phase-agent`) takes `plan_id` as an explicit parameter; the embedded header does not replace the parameter, it reinforces it.

The path-free `--plan-id` form is the **preferred contract** for Bucket-B scripts (build wrappers, CI integration, sonar). It replaces earlier path-leaking forms (`--worktree-path <abs>`) so the worktree absolute path no longer leaks into model context. The dispatched script resolves the path internally via `manage-status get-worktree-path`. The `--project-dir <abs>` flag remains as an **explicit override / escape hatch** for the rare case where a caller already holds an absolute path (e.g., post-worktree-removal cleanup, fixture-driven test invocations). `--plan-id` and `--project-dir` are mutually exclusive at every call site; passing both is a hard error.

Child agents MUST echo the same header verbatim into any further dispatches they issue.

## The `git -C {path}` Rule (Worktree Application)

The universal "no `cd <path> && <tool>`" prohibition is established in [`dev-general-practices/standards/tool-usage-patterns.md`](../../dev-general-practices/standards/tool-usage-patterns.md) — that document defines the rule for every tool with a native cwd flag.

**Worktree-specific application**: when a plan runs in an isolated worktree, every git command that targets the plan's working tree MUST use the form:

```bash
git -C {worktree_path} <subcommand>
```

`{worktree_path}` is the value returned by `manage-status get-worktree-path --plan-id {plan_id}`. Never derive it from `pwd`, never substitute `cd {worktree_path} && git ...`, never rely on the agent's process cwd.

When a plan runs against the main checkout (no worktree allocated), substitute the main checkout absolute path for `{worktree_path}` — the structural rule is unchanged, only the target tree differs.

The same `<tool> -C / -f / --prefix / --directory / --rootdir` discipline applies to every tool that operates on a working tree (mvn, npm, uv, pytest, ruff). See the native-cwd-flag table in `tool-usage-patterns.md` for the complete mapping.

## Never-Edit-Main-Checkout Invariant

While a plan is in flight in an isolated worktree, the agent MUST NOT:

- Edit any file under the main checkout via Edit/Write/Read tool calls.
- Run raw build, test, or lint commands against the main checkout.
- Stage or commit changes from the main checkout's working tree.

Every Edit/Write/Read tool call MUST resolve its target against `{worktree_path}`. Editing the main checkout while a plan runs in a worktree:

- Pollutes the main checkout's uncommitted state with content the plan never committed.
- Bypasses worktree isolation, defeating the whole point of running in a worktree.
- Lets tests silently load stale source via PYTHONPATH — the test runner sees the main checkout's PYTHONPATH entries and reports green while the worktree's edits go entirely unexercised.

This invariant is enforced structurally by the `--plan-id` auto-routing on Bucket B scripts (build / CI / Sonar): when `--plan-id` is supplied, the script resolves the worktree path internally and binds every subprocess to it; the main checkout is not reachable from the script's process tree.

## Cleanup Ordering: Worktree First, Then Branch

When a plan completes and the feature branch is ready for deletion, the operations MUST happen in this order:

1. **Remove the worktree.** `git worktree remove` refuses to operate on a worktree that is the cwd of any shell, and the local branch cannot be deleted while still checked out in a worktree. Any uncommitted state in the worktree at this point is a fail-loud condition — never pass `--force` to salvage; the user may still want to recover the work.
2. **Switch the main checkout to the base branch.** `git -C {main_checkout} checkout {base_branch}`.
3. **Pull the merge commit on the base branch.** `git -C {main_checkout} pull`.
4. **Delete the local feature branch.** `git -C {main_checkout} branch -d {head_branch}`.

After step 1, every git call MUST switch from `git -C {worktree_path}` to `git -C {main_checkout}` because `{worktree_path}` no longer exists on disk. Build / CI / Sonar invocations that previously took `--plan-id` MUST omit it after step 1 (the plan still has metadata, but no worktree to bind to).

On any plan abort or failure path, do NOT auto-remove the worktree — leave it in place so the user can inspect, salvage, or replay. Worktree removal happens only on successful cleanup.

## The `--plan-id` Two-State Contract

Build wrappers (`build-maven`, `build-python`, `build-npm`, `build-gradle`), CI scripts (`tools-integration-ci`), the Sonar wrapper (`workflow-integration-sonar`), and any other Bucket B script that touches a working tree accept `--plan-id` as their working-tree binding flag.

The flag has exactly two states with no in-between:

| `--plan-id` | Resolution | Effective working tree |
|-------------|-----------|------------------------|
| **Present** (`--plan-id X`) | Script calls `manage-status get-worktree-path --plan-id X` internally, binds subprocesses to the resolved path. | The worktree at `<project_root>/.plan/local/worktrees/X/`. |
| **Absent** | Script binds subprocesses to the main checkout (the project root resolved via `git rev-parse --show-toplevel`). | The main checkout. |

The contract is **bivalent**: a script either has a `--plan-id` (and binds to the worktree) or it does not (and binds to the main checkout). There is no "no `--plan-id` but still target the worktree" mode and no "explicit path override" — the path-leaking `--project-dir` and `--worktree-path` flags are removed so callers cannot accidentally bind to a stale path.

When a script invoked with `--plan-id X` resolves an empty path (i.e., the plan exists but `metadata.use_worktree == false`), the script falls back to the main checkout — the plan opted out of worktree mode at init time, and the caller's `--plan-id` becomes a no-op for path resolution.

Bucket A `manage-*` scripts MUST NOT accept `--plan-id` for cwd binding — they resolve `.plan/` via `git rev-parse --git-common-dir` regardless of the active worktree. (Many `manage-*` scripts already accept `--plan-id` as a *plan-identifier* argument that selects which plan's metadata to read or write — that usage is unrelated to the cwd contract here.) See [`tools-script-executor/standards/cwd-policy.md`](../../tools-script-executor/standards/cwd-policy.md) for the authoritative Bucket A / Bucket B / Bucket C split.

## The `worktree-rebase-to` Verb

`git_workflow worktree-rebase-to --plan-id X --base BRANCH` rebases the worktree's branch onto `--base` after detecting which of eight documented worktree states applies. The verb is intentionally narrow — it does not stash, force, or salvage; the caller is responsible for setting the worktree to a rebaseable state before invoking it.

### Resolution

`--plan-id X` resolves the worktree path via `manage-status get-worktree-path`. Every git invocation issued by the verb uses `git -C {worktree_path} <subcommand>` per the rule above; the main checkout is never modified.

### The 8-State Matrix

| State | Detection | Status | Action |
|-------|-----------|--------|--------|
| `clean` | branch and base point at same commit (ahead/behind both 0) | `success` | no-op, returns `action: noop` |
| `dirty` | `git status --porcelain` reports any modified, staged, or untracked entries | `error` | rejects with `dirty_worktree`; caller MUST stash, commit, or discard |
| `ahead` | branch has commits not on base; base has none branch lacks (or both diverge) | `success` | rebases commits onto base via `git rebase {base}`; returns `action: rebased` |
| `behind` | base has commits branch lacks; branch has none base lacks | `success` | rebases to incorporate base commits via `git rebase {base}`; returns `action: rebased` |
| `conflict` | rebase produces conflicts (`.git/rebase-merge` or `.git/rebase-apply` exists after non-zero exit) | `conflict` | leaves rebase in progress with conflict markers; caller resolves and runs `git rebase --continue` or `git rebase --abort` |
| `detached` | `git symbolic-ref --short HEAD` returns non-zero (no checked-out branch) | `error` | rejects with `detached_head`; caller MUST check out a branch first |
| `missing-base` | `git rev-parse --verify {base}^{commit}` returns non-zero | `error` | rejects with `missing_base`; caller MUST fetch or correct the base ref |
| `missing-target` | resolved worktree path is not a directory on disk | `error` | rejects with `missing_target`; caller MUST recreate the worktree (e.g., `worktree-create`) |

The first six states are detected by inspection before any rebase runs; `conflict` is determined by the rebase attempt itself. `clean` is a no-op; `ahead` and `behind` both attempt the rebase (the detected state is preserved in the response so callers can distinguish what was relocated).

### Output Contract

```
status: success | error | conflict
plan_id: {echo}
worktree_path: {resolved}
base: {echo}
state: clean | dirty | ahead | behind | conflict | detached | missing-base | missing-target
head_branch: {when detected}
ahead: {commits ahead of base, when detected}
behind: {commits behind base, when detected}
action: noop | rebased   # success only
conflicts[N]: [paths]    # conflict only
error: {error_code}      # error or conflict only
message: {human-readable summary}
```

### Conflict Handling

The default behavior on conflict is **leave-in-place**: the rebase remains in progress and the working tree carries conflict markers. This lets the caller inspect the conflicts (the paths are enumerated in `conflicts[]` via `git diff --name-only --diff-filter=U`) and choose between manual resolution (`git rebase --continue`) and abandonment (`git rebase --abort`). The verb never auto-aborts because the caller — typically a higher-level workflow — owns the decision.

Per the never-edit-main-checkout invariant above, `worktree-rebase-to` operates exclusively against `{worktree_path}`; the main checkout's HEAD, index, and working tree are untouched even when the rebase fails.

## Related

- [`dev-general-practices/standards/tool-usage-patterns.md`](../../dev-general-practices/standards/tool-usage-patterns.md) — universal "no `cd && <tool>`" rule, native cwd flags for every tool.
- [`tools-script-executor/standards/cwd-policy.md`](../../tools-script-executor/standards/cwd-policy.md) — Bucket A/B/C policy for marketplace scripts.
- [`phase-5-execute/SKILL.md`](../../phase-5-execute/SKILL.md) — Dispatch Protocol section anchors the Worktree Header at the orchestration layer.
- [`execute-task/SKILL.md`](../../execute-task/SKILL.md) — execute-task input contract surfaces `plan_id` so the skill can resolve the worktree internally.
- [`tools-integration-ci/SKILL.md`](../../tools-integration-ci/SKILL.md) — CI leaf subcommands accept `--plan-id` for worktree-aware invocation.
- [`phase-6-finalize/standards/branch-cleanup.md`](../../phase-6-finalize/standards/branch-cleanup.md) — applies the cleanup ordering during finalize.
