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
emitters cannot drift apart with two subtly-different copies of it. That
promise was made once and then broken in the way it was written to
prevent: each emitter grew its OWN inline ``is_within(output_dir,
marketplace_dir)`` overlap refusal, and because the two copies were
identical they drifted TOGETHER — both covering only the direction where
the OUTPUT lies inside the SOURCE, and neither covering the reverse.
:func:`refuse_tree_overlap` is that check hoisted here, symmetric, so the
call sites hold no copy to drift.
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


def trees_overlap(first: Path, second: Path) -> bool:
    """Return True when either tree contains the other, or they are the same tree.

    :func:`is_within` answers a DIRECTED question — "is ``path`` under
    ``root``?" — and a destructive emit needs the undirected one. Two trees
    are safe to treat as source and destination only when they are
    genuinely disjoint: an output inside the source lets the wipe eat
    source, and a source inside the output lets the prune sweep eat the
    source wholesale, because every entry it walks is contained in the
    output by construction and so passes :func:`safe_rmtree` trivially.
    """
    return is_within(first, second) or is_within(second, first)


def refuse_tree_overlap(output_dir: Path, source_dir: Path) -> None:
    """Raise ``ValueError`` unless ``output_dir`` and ``source_dir`` are disjoint.

    The single overlap refusal both target emitters call before they create
    or delete anything. It refuses BOTH directions:

    * ``output_dir`` inside ``source_dir`` — the per-bundle wipe would
      target real source; and
    * ``source_dir`` inside ``output_dir`` — the removed-bundle prune sweep
      walks every child of ``output_dir``, so the source tree is just
      another child to delete, and :func:`safe_rmtree` cannot object
      because that child IS contained in ``output_dir``.

    The second direction is not hypothetical: it is reached on exactly the
    path the first direction was added for. When ``source_dir`` names a
    level whose children carry no ``.claude-plugin/plugin.json``, no bundle
    is discovered, every per-bundle guard is skipped for want of a bundle,
    and the prune sweep runs against an empty "keep" set.
    """
    if not trees_overlap(output_dir, source_dir):
        return
    raise ValueError(
        f'Refusing to emit into {output_dir.resolve()}: it overlaps the source tree '
        f'{source_dir.resolve()} — the output directory must be a distinct build '
        'location, disjoint from the marketplace source; neither tree may contain '
        'the other'
    )


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


__all__ = ['is_within', 'refuse_tree_overlap', 'safe_rmtree', 'trees_overlap']
