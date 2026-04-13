---
name: manage-worktree
description: Manage per-plan git worktrees under ~/.plan-marshall/{project}/worktrees/
user-invocable: false
scope: plan
---

# Manage Worktree Skill

Create, remove, resolve, and list per-plan git worktrees. Worktrees live under `~/.plan-marshall/{project}/worktrees/{plan-id}/` and are isolated per plan so multiple plans can run in parallel on one repo.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Never use `git worktree remove --force` unless the caller has explicitly verified the worktree is clean. Destructive deletion of in-progress work is prohibited.
- Always drop the executor shim (`.plan/execute-script.py`) into the new worktree so documented command invocations work identically from inside it.
- The worktree path is computed deterministically from `get_base_dir()` and the plan id; never accept an arbitrary path from the caller.

## Subcommands

| Subcommand | Arguments | Purpose |
|-----------|-----------|---------|
| `path` | `--plan-id` | Return the computed worktree path (without creating anything) |
| `create` | `--plan-id --branch [--base]` | Create worktree + new branch + shim |
| `remove` | `--plan-id [--force]` | Remove worktree (non-force by default) |
| `list` | _(none)_ | Enumerate worktrees under the global dir |

## Output

TOON format per the manage-contract. Successful results include `worktree_path`.
