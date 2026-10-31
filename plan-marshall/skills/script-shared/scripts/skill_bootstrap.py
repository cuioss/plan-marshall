#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ONE plan-marshall entry-script bootstrap: resolve sibling skill libraries.

A marketplace script that imports a shared library must put that library's
``scripts/`` directory on ``sys.path`` itself, because it may run before the
executor has set ``PYTHONPATH`` (the wizard's generate/bootstrap steps, a recovery
command, a script run straight from a deployed tree). That resolution used to be
copied into every carrier, with the flat ``{bundle}-{lib}`` fallback re-spelled
each time — five copies, two of which disagreed about the layout.

This module is the single home for the LIBRARY resolution. It reuses the
deployed-shape helpers the tree already owns (:func:`marketplace_bundles.
resolve_sibling_skill_path`, backed by :mod:`deployed_layout`), so the naming rule
for a flat skill directory is written once and a carrier never re-derives it.

The one thing this module cannot do is find itself: it lives in
``script-shared/scripts``, which is exactly what the bootstrap is looking for. So
each carrier opens with the same short, stdlib-only ANCHOR (see
:data:`ANCHOR_MARKER`) — it locates ``script-shared/scripts`` by probing the
nested and the flat sibling shapes, then calls :func:`bootstrap_skill_libraries`
for the rest. The anchor is deliberately tiny and byte-identical everywhere, and
``test_skill_bootstrap_guard`` asserts that: a carrier that grows its own
fallback, or a new carrier that copies the old loop, reds the guard.

A library that cannot be found is reported by NAME and by the paths that were
probed (:class:`BootstrapLibraryNotFound`), never as a bare
``ModuleNotFoundError`` from the first ``import`` that follows.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from deployed_layout import read_flat_skill_identity
from marketplace_bundles import (
    describe_sibling_skill_shapes,
    resolve_sibling_skill_path,
    resolve_skills_root,
)

#: The bundle every skill this bootstrap resolves belongs to. Only the FLAT
#: sibling leg needs it (the nested leg is found by directory name), and it is
#: overridden by the identity a flat skill directory records whenever that
#: identity re-joins to the directory name.
DEFAULT_BUNDLE = 'plan-marshall'

#: Line every carrier's stdlib-only anchor opens with. The guard test locates the
#: anchor by this marker and asserts the block is identical in every carrier.
ANCHOR_MARKER = '# --- plan-marshall skill bootstrap: one shared anchor'


class BootstrapLibraryNotFound(RuntimeError):
    """A library this script needs is in NEITHER deployed shape.

    Carries the library name and the shared shape description — the nested path
    and, on a flat tree, the ``{bundle}-{lib}`` candidate — so the reader sees an
    install-layout answer instead of an import traceback naming only the module
    that happened to import first.
    """

    def __init__(self, library: str, shapes: str) -> None:
        self.library = library
        self.shapes = shapes
        super().__init__(
            f'plan-marshall bootstrap: library directory {library!r} not found.\n'
            f'  probed (either deployed shape):\n{shapes}'
        )


def _bundle_name(script_file: Path, skills_root: Path) -> str:
    """Return the bundle the running script's own skill directory records.

    A flat deployment names every skill ``{bundle}-{skill}``, and the emitted
    ``SKILL.md`` records that identity (``deployed_layout.read_flat_skill_identity``).
    Reading it is what keeps this module from hard-coding a bundle for the flat
    leg, and it falls back to :data:`DEFAULT_BUNDLE` for a nested tree, where the
    flat leg is never probed at all.
    """
    identity = read_flat_skill_identity(script_file.parent.parent)
    if identity is not None:
        return identity[0]
    return DEFAULT_BUNDLE


def _front_load(path: Path) -> None:
    """Put ``path`` first on ``sys.path``, moving an existing entry to the front.

    Unconditional on purpose: a plain "insert only when absent" guard leaves the
    script's own directory behind an inherited ``PYTHONPATH`` entry pointing at an
    older deployed copy, which then shadows the imports this bootstrap exists to
    make resolve. Removing first makes the local copy win regardless of inherited
    priority.
    """
    entry = str(path)
    if entry in sys.path:
        sys.path.remove(entry)
    sys.path.insert(0, entry)


def bootstrap_skill_libraries(
    script_file: Path,
    libraries: Sequence[str],
    bundle: str | None = None,
    extra_subdirs: Sequence[tuple[str, str]] = (),
) -> tuple[Path, ...]:
    """Resolve every named library's ``scripts`` dir and front-load it on ``sys.path``.

    Args:
        script_file: The calling script (``Path(__file__)``).
        libraries: Sibling skill names, e.g. ``('script-shared',)`` — the library
            directory, never the flat ``{bundle}-`` spelling.
        bundle: Bundle the siblings belong to. Defaults to the identity the
            running skill directory records, else :data:`DEFAULT_BUNDLE`.
        extra_subdirs: ``(library, subdir)`` pairs to add from a resolved library
            — for a library that organises its modules into sub-directories
            (``script-shared/scripts/build``). The sub-directory is joined onto
            the path this function already resolved, so the layout is still
            decided in one place.

    Returns:
        The resolved ``scripts`` directories, in the order given.

    Raises:
        BootstrapLibraryNotFound: the first library present in neither deployed
            shape, naming it and the paths probed.
    """
    script = Path(script_file).resolve()
    skills_root = resolve_skills_root(script)
    bundle_name = bundle or _bundle_name(script, skills_root)
    by_library: dict[str, Path] = {}
    for library in libraries:
        relative_path = f'skills/{library}/scripts'
        path = resolve_sibling_skill_path(script, bundle_name, relative_path)
        if not path.is_dir():
            raise BootstrapLibraryNotFound(
                library,
                describe_sibling_skill_shapes(script, bundle_name, relative_path),
            )
        _front_load(path)
        by_library[library] = path
    for library, subdir in extra_subdirs:
        parent = by_library.get(library)
        if parent is None:
            continue
        candidate = parent / subdir
        if candidate.is_dir():
            _front_load(candidate)
    return tuple(by_library[library] for library in libraries)
