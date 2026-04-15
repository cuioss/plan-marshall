# cwd Policy for the Script Executor

## Purpose

`.plan/execute-script.py` is a **pass-through proxy**: it forwards `argv` to the target script and never alters the caller's current working directory. All cwd control is therefore **explicit at the call site**. This document defines how scripts in the marketplace should treat cwd so that operations behave correctly whether they run from the main checkout or from a git worktree under `.claude/worktrees/{plan_id}/`.

The underlying problem is well-known in agent tooling: LLM harnesses (aider, claude-code, SWE-agent, etc.) share a process-wide cwd, which changes silently between tool calls. A script that relies on implicit cwd will appear to work when run from the repo root and silently target the wrong tree when run from a worktree — corrupting state or testing stale code. See the upstream discussions in the aider and claude-code issue trackers for concrete regressions caused by ambient cwd assumptions.

## Three Buckets

Every script in the marketplace falls into exactly one of three buckets. The bucket determines how the script must resolve paths.

### Bucket A — Plan Metadata (cwd-agnostic)

Scripts that read or write plan state under `.plan/` must resolve the plan directory via the shared helper, which uses `git rev-parse --git-common-dir`. This produces the same absolute path from every worktree attached to the repository, so plan metadata is shared across worktrees without duplication.

**Mechanism**: `script_shared.marketplace_paths.get_plan_dir()` in `plan-marshall:script-shared`. Internally:

```
git rev-parse --path-format=absolute --git-common-dir
```

returns the main `.git` directory regardless of which worktree is active; the helper anchors `.plan/` next to it. This is an existing invariant — new scripts inherit the behaviour by calling `get_plan_dir()` rather than constructing paths from `Path.cwd()` or `__file__`.

**Rule**: never read `Path.cwd()` to locate `.plan/`. Always call `get_plan_dir()`.

**Examples**: `manage-files`, `manage-tasks`, `manage-config`, `manage-findings`, `manage-logging`, `manage-memories`, `manage-lessons`, `manage-architecture`, `manage-providers`, `manage-run-config`, `manage-plan-documents`, `manage-references`.

### Bucket B — Worktree-Scoped Operations (explicit path)

Scripts that act on a working tree (building, testing, linting, staging, committing, CI interactions) must accept the target tree as an explicit parameter and never infer it from cwd. There are two concrete mechanisms:

- **Raw git**: invoke with `git -C {worktree_path} <cmd>` so the command applies to the intended worktree regardless of the executor's cwd.
- **Build / CI / Sonar / analysis scripts**: accept a `--project-dir {worktree_path}` (or equivalent) argument and resolve all project paths relative to it. The caller — typically a phase agent running inside a plan — passes the worktree path surfaced by `phase-5-execute` in its `[STATUS] Active worktree: ...` work-log line.

**Rule**: wherever a script touches non-`.plan/` repository content, the caller specifies the tree explicitly. Scripts that silently use `os.getcwd()` to locate source files are non-compliant.

**Examples**: `build-maven`, `build-gradle`, `build-npm`, `build-python`, `tools-integration-ci`, `workflow-integration-git`, `workflow-integration-sonar`, `workflow-pr-doctor`.

### Bucket C — Meta-Tools (always main checkout)

A small set of tools operate on the marketplace itself rather than on plan state or a worktree. These must always run against the **main checkout**, never against a worktree, because:

- They read/write source-of-truth bundle files under `marketplace/bundles/`.
- A worktree's copy of bundle sources may be stale or mid-edit; operating on it would produce incorrect inventories, broken executors, or out-of-sync caches.
- The plugin cache (`~/.claude/plugins/cache/plan-marshall/`) is a singleton on the host — regenerating it from a worktree would silently swap cache contents for every project on the machine.

**Rule**: meta-tools require the caller to run them from the main checkout and must refuse to operate against a worktree path. They should not accept a `--project-dir` pointing into `.claude/worktrees/`.

**Examples**: `plugin-create`, `plugin-doctor`, `plugin-maintain`, `plugin-architecture`, `plugin-script-architecture`, `tools-marketplace-inventory`, `marshall-steward`, `generate_executor` (and anything else that regenerates `.plan/execute-script.py` or the plugin cache).

## Mechanism Matrix

| Bucket | Category | Examples | Mechanism |
|--------|----------|----------|-----------|
| A | Plan metadata | `manage-*` scripts, logging, findings, memories | `get_plan_dir()` → `git rev-parse --git-common-dir` |
| B | Worktree-scoped git | Commit, status, diff, checkout | `git -C {worktree_path} <cmd>` |
| B | Build / test / lint | `build-maven`, `build-python`, `build-npm`, `build-gradle` | `--project-dir {worktree_path}` |
| B | CI / Sonar / PR tooling | `tools-integration-ci`, `workflow-integration-sonar`, `workflow-pr-doctor` | `--project-dir {worktree_path}` (or equivalent) |
| C | Marketplace meta-tools | `plugin-doctor`, `tools-marketplace-inventory`, `marshall-steward`, `generate_executor` | Always main checkout; reject worktree paths |

## Rationale

- **Worktree isolation**: a plan running in `.claude/worktrees/{plan_id}/` must be able to edit, build, and test without touching the main checkout or any sibling worktree.
- **Shared plan state**: plan metadata under `.plan/` intentionally lives next to the main `.git` directory so every worktree sees the same plans, tasks, and logs. `git rev-parse --git-common-dir` is the documented git interface for locating that directory from any linked worktree (see `git-worktree(1)` and `git-rev-parse(1)`).
- **Agent cwd is unreliable**: the claude-code harness resets cwd between tool invocations; aider and SWE-agent have reported similar regressions where implicit cwd caused silent edits to the wrong tree. Making cwd explicit at every call site eliminates that class of bug.
- **Single source of truth for meta-tools**: the plugin cache and generated executor are host-global resources. Regenerating them from anywhere other than the main checkout risks propagating stale or partial content into every project on the machine.

## Assertion

`script_shared.marketplace_paths.get_plan_dir()` MUST use `git rev-parse --git-common-dir` (not `--git-dir`, not `Path.cwd()`, not `__file__`). Any change that regresses this invariant breaks worktree isolation for every Bucket-A script and must be rejected in review.
