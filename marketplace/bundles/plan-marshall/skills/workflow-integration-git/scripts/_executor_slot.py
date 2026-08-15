# SPDX-License-Identifier: FSL-1.1-ALv2
"""The worktree executor slot: where it lives, and whether one actually landed.

Two facts that every executor-producing path in this skill needs, single-sourced
here because they are shared across module boundaries rather than private to one
verb. (The ``_cmd_*.py`` verb modules deliberately duplicate their own private
helpers to stay independent — that convention governs helpers used by ONE
module, not a definition two entrypoints must agree on.)

Both consumers produce the same artifact at different moments:

- ``prepare_execute`` generates a NEW worktree's executor at phase-5 move-in.
- ``git-workflow``'s ``worktree-rebase-to`` REgenerates it when a finalize
  rebase changed the bundle script set.

They must agree on the path (or one writes where the other does not look) and on
what counts as success (or one reports a refreshed executor the other cannot
find). Sharing the definitions is what makes that agreement structural instead
of a comment asking two files to stay in sync.
"""

from __future__ import annotations

from pathlib import Path

from marketplace_paths import PLAN_DIR_NAME


def worktree_executor_path(worktree_path: Path) -> Path:
    """Return the executor slot inside ``worktree_path``.

    The executor is per-tree DERIVED state (ADR-002): main keeps its own copy,
    and each worktree gets one at this path. Never a moved slot, never a symlink.
    """
    return worktree_path / PLAN_DIR_NAME / 'execute-script.py'


def executor_landed(executor_path: Path) -> bool:
    """Return True when ``executor_path`` exists on disk AND is non-empty.

    The on-disk post-assertion that keeps a generation's SUCCESS verdict tied to
    reality rather than to its exit code. ``generate_executor.py`` can exit 0
    having written nothing — the plugin-cache-install case, where the tree has no
    vendored ``marketplace/bundles`` so marketplace anchoring lands nowhere — and
    a caller that trusted ``returncode == 0`` would report an executor that does
    not exist.

    A symlink is rejected outright: the executor is generated per-tree, so a
    symlink at that path means some earlier layout is still in place rather than
    a real generation having landed.
    """
    try:
        return (
            executor_path.is_file()
            and not executor_path.is_symlink()
            and executor_path.stat().st_size > 0
        )
    except OSError:
        return False
