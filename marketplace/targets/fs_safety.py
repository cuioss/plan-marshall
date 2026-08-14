# SPDX-License-Identifier: FSL-1.1-ALv2
"""Filesystem-safety primitives shared across build targets.

A build target's emitter clears stale output before rewriting it. That
clear is a ``shutil.rmtree`` — a destructive operation whose target must
be proven contained before it runs, never assumed safe because the
*intended* destination happens to be a gitignored build directory. A
mistyped ``output_dir`` pointing at real source turns the same wipe into
data loss, and "the intended path is regenerable" is a statement about
the intended path, not a guard against the mistyped one.

This module is the single home for the containment check so the two
emitters cannot drift apart with two subtly-different copies of it.
"""

from __future__ import annotations

import shutil
from pathlib import Path


def is_within(path: Path, root: Path) -> bool:
    """Return True when ``path`` resolves to ``root`` or a descendant of it.

    Both operands are resolved first, so symlinks and ``..`` segments
    cannot smuggle a path out of ``root`` while still passing a naive
    string-prefix test.
    """
    resolved = path.resolve()
    resolved_root = root.resolve()
    return resolved == resolved_root or str(resolved).startswith(str(resolved_root) + '/')


def safe_rmtree(path: Path, output_dir: Path) -> None:
    """Remove ``path`` only when it is contained within ``output_dir``.

    Refuses (raises ``ValueError``) rather than deleting when ``path`` is
    not ``output_dir`` itself or a descendant of it. This is the
    containment invariant every destructive wipe in a target emitter must
    pass before it runs.
    """
    if not is_within(path, output_dir):
        resolved = path.resolve()
        resolved_output = output_dir.resolve()
        raise ValueError(f'Refusing to delete {resolved}: not within output directory {resolved_output}')
    shutil.rmtree(path)


__all__ = ['is_within', 'safe_rmtree']
