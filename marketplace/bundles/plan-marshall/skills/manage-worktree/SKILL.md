---
name: manage-worktree
description: Manage per-plan git worktrees under <project_root>/.claude/worktrees/
user-invocable: false
scope: plan
---

# Manage Worktree Skill

Create, remove, resolve, and list per-plan git worktrees. Worktrees live under `<project_root>/.claude/worktrees/{plan-id}/` — the canonical Claude Code worktree location inside the main git checkout — and are isolated per plan so multiple plans can run in parallel on one repo. Anchoring worktrees inside the main checkout means project-level permission allow-lists and IDE indexing work without per-host customization. All plan-marshall runtime state lives at `<root>/.plan/local/` in the main checkout; each worktree's `.plan` is a symlink back to the main checkout's `.plan`, so tracked config, the executor, and runtime state are shared across every worktree.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Never use `git worktree remove --force` unless the caller has explicitly verified the worktree is clean. Destructive deletion of in-progress work is prohibited.
- After `git worktree add`, always symlink `{worktree}/.plan` to the main checkout's `.plan` directory so documented command invocations (`python3 .plan/execute-script.py …`) resolve to the same executor and runtime state from inside the worktree. The symlink step is idempotent — re-running create over an existing worktree never clobbers real user data.
- The worktree path is computed deterministically from `get_worktree_root()` (which resolves to `<project_root>/.claude/worktrees`) and the plan id; never accept an arbitrary path from the caller.

## Subcommands

| Subcommand | Arguments | Purpose |
|-----------|-----------|---------|
| `path` | `--plan-id` | Return the computed worktree path (without creating anything) |
| `create` | `--plan-id --branch [--base]` | Create worktree + new branch + `.plan` symlink |
| `remove` | `--plan-id [--force]` | Remove worktree (non-force by default) |
| `list` | _(none)_ | Enumerate worktrees under `<root>/.claude/worktrees/` |

## Output

TOON format per the manage-contract. Successful results include `worktree_path`.
