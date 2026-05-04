---
name: script-shared
description: Shared Python modules consumed by other plan-marshall scripts via PYTHONPATH
user-invocable: false
---

# Script Shared

Shared Python modules consumed by other plan-marshall scripts via PYTHONPATH.

This skill has no user-facing workflow. It provides build utilities, extension framework helpers, workflow helpers, and query modules that are imported by executable scripts in other skills.

## Directory Layout

```
scripts/
  build/        # Build system utilities (_build_*.py, _coverage_parse.py, _markers_search.py)
  extension/    # Extension framework (extension_base.py, extension_discovery.py, ...)
  workflow/     # Workflow helpers (triage_helpers.py)
  query/        # Query utilities (query-config.py, query-architecture.py)
```

## Import Resolution

The executor's PYTHONPATH generation scans immediate subdirectories of each `scripts/` directory, so modules in `scripts/build/` and `scripts/extension/` are importable by any script in the marketplace without path manipulation.

`marketplace_paths.find_marketplace_path()` and `get_base_path()` accept an optional `marketplace_root` override and resolve in this order: explicit parameter → `PM_MARKETPLACE_ROOT` env var → script-relative `Path(__file__).parents[6]` walk → cwd-based discovery. Use the override (or the env var) to pin marketplace lookups to a specific worktree or test fixture instead of relying on cwd.
