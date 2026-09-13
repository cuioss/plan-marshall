# Test Scaffolding Patterns

Canonical patterns for test files in this repository whose collection is non-trivial. Each pattern is a documented composition that fresh agents should not have to rediscover.

## Pattern: importing underscore-prefixed sibling modules

### Problem

Tests under `test/plan-marshall/.../` need to drive helpers shipped as underscore-prefixed sibling modules (`_handshake_commands.py`, `_handshake_store.py`, `_git_helpers.py`, `_invariants.py`, `_plan_parsing.py`, …) that live next to the script under test in `marketplace/bundles/.../scripts/`. Three Python/ruff facts collide when scaffolding such a test:

1. The underscore-prefixed scripts are **not** installable packages and **not** on `PYTHONPATH` by default. A bare `import _handshake_commands` at module top fails with `ModuleNotFoundError`.
2. Inserting `sys.path` mutation before the import is the only working approach — but ruff `I001` (isort) flags the resulting import block as unsorted, because there is no sort order that legally puts a `sys.path.insert(...)` call before an `import _foo` statement.
3. ruff `E402` (module-level import not at top of file) also fires because the import necessarily lives after the `sys.path.insert` mutation.

Three independent ruff/import facts means three independent rediscovery rounds per fresh agent. The canonical resolution is to suppress both ruff codes **at the file level** and use the `sys.path.insert(0, ...)` mutation immediately before the underscore imports.

### Canonical pattern

A **file-level** `# ruff: noqa: I001, E402` directive at the top of the file (line 2, immediately after the shebang) plus a `sys.path.insert(0, str(SCRIPTS_DIR))` call before the underscore-prefixed imports:

```python
#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for {script} internals.

Drive {underscore-helpers} directly by inserting the scripts dir on sys.path.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from conftest import PlanContext, get_script_path  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('{bundle}', '{skill}', '{script}.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _foo as foo  # noqa: E402
import _bar as bar  # noqa: E402
```

### In-tree citation

The canonical example lives in `test/plan-marshall/plan-marshall/test_phase_handshake.py`:

- **Line 2**: `# ruff: noqa: I001, E402` (file-level suppression)
- **Lines 20-24**: `SCRIPT_PATH` / `SCRIPTS_DIR` / `sys.path.insert` setup
- **Lines 26-29**: underscore-prefixed imports with per-line `# noqa: E402` reinforcement

When scaffolding a new test file that follows this pattern, copy the prologue from `test_phase_handshake.py` verbatim and substitute the `{bundle}`, `{skill}`, and `{script}` segments via `get_script_path(...)`.

### Why each piece is required

- **File-level `# ruff: noqa: I001, E402`** — line-level suppression on each import is verbose, drifts as imports change, and is inconsistent with the project's preferred convention. The file-level form is one line near the top and stays correct as the import block evolves.
- **`sys.path.insert(0, str(SCRIPTS_DIR))`** — the only mechanism to make underscore-prefixed siblings importable without packaging changes. Inserting at index `0` ensures the local helpers shadow any installed package of the same name.
- **The `if str(SCRIPTS_DIR) not in sys.path:` guard** — keeps `sys.path` deterministic when the test file is collected more than once (e.g., by pytest plugins that re-import).
- **Per-line `# noqa: E402` on each underscore import** — belt-and-braces: the file-level directive already suppresses E402, but per-line annotations keep IDE static analysers quiet and make the intent visible to readers who skip the file header.

### Anti-patterns to avoid

- **Top-of-file `import _foo`** — fails because the module is not on the import path.
- **`sys.path.insert(...)` followed by an unannotated `import _foo`** — passes Python but fails ruff `I001` and `E402`.
- **Per-line `# noqa: I001, E402`** without the file-level header — partial pass; inconsistent with project convention; drift-prone as imports change.
- **Adding the underscore module to `pyproject.toml` as an installable package** — defeats the purpose of underscore-prefixed siblings (they are deliberately script-local helpers, not public packages).

### When this pattern does NOT apply

Plain test files that import only stdlib modules and packages declared in `pyproject.toml` do not need this prologue. Reach for it only when the test must import a sibling helper from a script directory that is not on `PYTHONPATH`.
