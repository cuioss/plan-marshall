---
name: script-shared
description: Shared Python modules consumed by other plan-marshall scripts via PYTHONPATH
user-invocable: false
mode: knowledge
---

# Script Shared

Shared Python modules consumed by other plan-marshall scripts via PYTHONPATH.

This skill has no user-facing workflow. It provides build utilities, extension framework helpers, workflow helpers, and query modules that are imported by executable scripts in other skills.

## Directory Layout

```text
scripts/
  marketplace_paths.py    # Path/root resolution constants and helpers; defines NO_PLAN_SENTINEL
  resolve_project_dir.py  # The --plan-id / --project-dir argv routing layer
  build/        # Build system utilities (_build_*.py, _coverage_parse.py)
  extension/    # Extension framework (extension_base.py, extension_discovery.py, ...)
  workflow/     # Workflow helpers (triage_helpers.py)
  query/        # Query utilities (query-config.py, query-architecture.py)
```

## Import Resolution

The executor's PYTHONPATH generation scans immediate subdirectories of each `scripts/` directory, so modules in `scripts/build/` and `scripts/extension/` are importable by any script in the marketplace without path manipulation.

`marketplace_paths.find_marketplace_path()` and `get_base_path()` accept an optional `marketplace_root` override and resolve in this order: explicit parameter → `PM_MARKETPLACE_ROOT` env var → script-relative `Path(__file__).parents[6]` walk → cwd-based discovery. Use the override (or the env var) to pin marketplace lookups to a specific worktree or test fixture instead of relying on cwd.

See `workflow-integration-git/standards/worktree-handling.md` for the worktree-specific application of this rule (path convention and the `--plan-id` / `--project-dir` binding contract for callers that need to bind to a specific working tree).

## `resolve_project_dir` — the argv routing layer, not a resolver

`resolve_project_dir.py` implements the `--plan-id` / `--project-dir` contract that every Bucket B (worktree-scoped) script shares, so consumer scripts have one implementation instead of one copy each. Its role is narrow and worth stating precisely, because it used to be wider:

- It is the **argv/flag layer**: it enforces mutual exclusion (`MutuallyExclusiveArgsError`), decides which of the two flags was supplied, and returns an absolute working-tree path string.
- It is **not** an independent worktree resolver. The worktree face is delegated to `file_ops.resolve_plan_context`, which owns the single `manage-status get-worktree-path` invocation in the codebase. `resolve_project_dir` calls it with `ensure=False` — resolving a working tree is a routing lookup and must not materialize or existence-check the plan — and returns `.worktree_path`.
- `--project-dir` is still returned verbatim (made absolute), and the no-flag case falls back to `file_ops.cwd_checkout_root()`.
- `WorktreeResolutionError` is **re-exported from `file_ops`**, not defined here; it is raised by the resolver, and callers surface its message verbatim.

Because the resolution goes through `resolve_plan_context`, `--plan-id NO_PLAN` is an accepted routing value on every Bucket B consumer and binds to the main checkout — a plan-less caller never resolves to a worktree. `NO_PLAN_SENTINEL` is **defined** in `marketplace_paths.py`, this bundle's pure-stdlib foundation, so that `file_ops` can import it on the bootstrap path where `tools-input-validation` is not on `sys.path`; `input_validation` re-exports it. See [`tools-file-ops/SKILL.md`](../tools-file-ops/SKILL.md) § "Plan-Context Resolution" for the resolver contract and [`tools-input-validation/SKILL.md`](../tools-input-validation/SKILL.md) § "The `NO_PLAN` sentinel (plan_id carve-out)" for the validator carve-out.
