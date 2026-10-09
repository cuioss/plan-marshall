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
from collections.abc import Iterator
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


def refuse_escaping_output_dir(path: Path, output_dir: Path) -> None:
    """Raise ``ValueError`` unless ``path`` is a real location inside ``output_dir``.

    The single check both target emitters call on a per-component output
    directory BEFORE they create it, sweep it, or write into it.
    :func:`refuse_tree_overlap` inspects only the two roots, so it says
    nothing about a nested path such as ``output_dir/skills/{bundle}-{skill}``
    — and ``mkdir(exist_ok=True)`` accepts an existing symlink to a directory
    without complaint. Two shapes are refused:

    * ``path`` is itself a symbolic link, wherever it points — an emitted
      directory is one the emitter created, never a link; and
    * ``path`` resolves outside the resolved ``output_dir`` — a symlinked
      ANCESTOR (``output_dir/skills`` linked elsewhere) carries the sweep and
      the writes out of the tree just as well as a symlinked leaf.

    ``path`` need not exist yet: resolution is non-strict, so the check runs
    ahead of the ``mkdir`` that would otherwise create a directory through a
    symlinked ancestor.
    """
    if path.is_symlink():
        raise ValueError(
            f'Refusing to emit into {path}: it is a symbolic link — an output directory must be a real directory'
        )
    if not is_within(path, output_dir):
        raise ValueError(
            f'Refusing to emit into {path}: it resolves to {path.resolve()}, '
            f'outside output directory {output_dir.resolve()}'
        )


def refuse_symlink(path: Path) -> None:
    """Raise ``ValueError`` when ``path`` is itself a symbolic link, wherever it points.

    The check for a destination the caller must neither follow nor replace —
    a file an operator may have linked elsewhere on purpose. It inspects the
    one path only and says nothing about its ancestors: a caller that walks a
    tree top-down and has already cleared every ancestor needs no more, and
    one that has not uses :func:`refuse_escaping_output_dir` for them. A real
    entry, or a missing one, passes.
    """
    if path.is_symlink():
        raise ValueError(
            f'Refusing to write {path}: it is a symbolic link — a link found at a destination '
            'path is neither followed nor replaced'
        )


def unlink_if_symlink(path: Path) -> None:
    """Remove ``path`` when it is a symbolic link, so a following write creates a real file.

    ``write_text`` and ``shutil.copyfile`` both follow a symlink at the
    destination and rewrite its target. An emitted file is one the emitter
    created, never a link, so a link found at an output path is cleared first;
    its target is left untouched. A real file, or a missing one, is left as is.
    """
    if path.is_symlink():
        path.unlink()


def iter_tree_without_following_links(root: Path) -> Iterator[Path]:
    """Yield every entry under ``root``, never descending into a symlinked directory.

    A symlinked directory is yielded as the link it is and its target is not
    walked. ``Path.rglob`` cannot be used for a destructive sweep: before
    Python 3.13 it follows directory symlinks, so the entries it yields may
    live outside ``root``. Each directory is listed in full before its
    entries are yielded, so a caller may unlink an entry as it receives it.
    """
    for entry in sorted(root.iterdir()):
        descend = entry.is_dir() and not entry.is_symlink()
        yield entry
        if descend:
            yield from iter_tree_without_following_links(entry)


__all__ = [
    'is_within',
    'iter_tree_without_following_links',
    'refuse_escaping_output_dir',
    'refuse_symlink',
    'refuse_tree_overlap',
    'safe_rmtree',
    'trees_overlap',
    'unlink_if_symlink',
]
