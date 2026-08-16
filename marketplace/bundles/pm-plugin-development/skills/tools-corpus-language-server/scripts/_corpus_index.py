#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Resident, read-only view over the marketplace dependency index.

This module is the **consumption** half of the corpus language server: it wraps
the dependency index that ``tools-marketplace-inventory`` already builds and
answers the three coordinate-oriented questions an editor (or an agent acting as
an LSP client) asks — *definition*, *references*, *hover*.

⛔ **The index is consumed, never edited.** Nothing here writes to
``_dep_index`` / ``_dep_detection``; the resolution and provenance-verification
logic below exists precisely so that the index needs no change to serve a
coordinate-oriented surface.

**Why residency is the whole design.** Building the index costs ~1.9 s and is
paid *per process*, while a warm index answers cheaply: ``definition`` and
``hover`` in microseconds, and ``references`` in under 5 ms once the citing
components' file lists are cached (the first call on a heavily-referenced
component pays a one-off directory walk — ~20 ms at 443 inbound edges). A
surface that forks a process per request is therefore a ~2 s-per-request
surface no matter which protocol it speaks, and it never gets to amortise
that walk either. :class:`CorpusIndex` is built once and reused for the life
of the server, which is what makes the substrate interactive at all.

Stdlib only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _dep_detection import Dependency
from _dep_index import build_dependency_index

# A component notation token: ``bundle:skill`` or ``bundle:skill:script``.
# The lookbehind/lookahead keep a cursor inside a longer colon-chain (a URL, a
# Maven coordinate) from resolving to a spurious two-part prefix.
NOTATION_RE = re.compile(r'(?<![\w:-])([\w-]+):([\w-]+)(?::([\w-]+))?(?![\w-])')

# Sub-document suffixes an edge can be cited from. The index attributes such an
# edge to the *owning* skill, so a reference's recorded line number may belong to
# one of these files rather than to the owner's own definition file — which is
# exactly what :func:`resolve_reference_site` has to disambiguate.
SUBDOC_SUFFIXES = ('.md',)


@dataclass(frozen=True)
class Location:
    """A resolved position in the corpus: 0-based line, as LSP counts them."""

    path: Path
    line: int

    def as_dict(self) -> dict[str, Any]:
        return {'path': str(self.path), 'line': self.line}


@dataclass(frozen=True)
class Reference:
    """One inbound edge, with the provenance verdict for its recorded site.

    ``verified`` distinguishes *we re-read the cited line and it carries the
    target* from *the index cited a line we could not confirm*. An unverified
    site is still reported — suppressing it would trade a wrong location for a
    missing one — but it is never presented as exact. What counts as carrying
    the target is per :func:`expected_tokens`, because an edge's surface form is
    not always the notation.
    """

    source_notation: str
    dep_type: str
    location: Location
    verified: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            'source': self.source_notation,
            'type': self.dep_type,
            'path': str(self.location.path),
            'line': self.location.line,
            'verified': self.verified,
        }


def notation_at(line_text: str, character: int) -> str | None:
    """Return the notation token spanning ``character`` in ``line_text``.

    Returns ``None`` when the cursor is not inside a notation. Prefers the
    longest match at the position, so a cursor inside ``a:b:c`` resolves to the
    three-part script notation rather than to its ``a:b`` prefix.
    """
    if character < 0:
        return None
    best: str | None = None
    for match in NOTATION_RE.finditer(line_text):
        if match.start() <= character <= match.end():
            token = match.group(0)
            if best is None or len(token) > len(best):
                best = token
    return best


def expected_tokens(notation: str) -> list[str]:
    """Return the surface forms a citing line may legitimately carry for ``notation``.

    ⚠ An edge's *surface form* is not always the notation. Only ``script`` and
    ``skill`` edges are written as ``bundle:skill[:script]`` in the citing line —
    a ``path`` edge appears as a relative path (``../manage-architecture/...``)
    and an ``import`` edge as a bare module name (``from extension_base import``).
    Verifying against the notation alone therefore marks every ``path`` and
    ``import`` edge unverified regardless of whether its site is correct, which
    makes the flag noise rather than signal.

    So a site is confirmed when the line carries **either** the full notation
    **or** the target's discriminating final segment — the script name for a
    three-part notation, the skill name for a two-part one — which is the form
    every edge kind has in common.
    """
    tokens = [notation]
    tail = notation.rsplit(':', 1)[-1]
    if tail and tail != notation:
        tokens.append(tail)
    return tokens


def _context_line(dep: Dependency) -> int | None:
    """Extract the 1-based line number from a dependency's ``context`` field.

    A non-positional context (``frontmatter:skills``) yields ``None`` — the edge
    is real but has no line to point at.
    """
    context = dep.context
    if not context.startswith('line:'):
        return None
    try:
        return int(context.split(':', 1)[1])
    except ValueError:
        return None


class CorpusIndex:
    """A built-once, queried-many view over the marketplace dependency index."""

    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path
        self.index = build_dependency_index(base_path)
        self._line_cache: dict[Path, list[str]] = {}
        self._candidate_cache: dict[Path, list[Path]] = {}

    # -- component lookup ---------------------------------------------------

    def knows(self, notation: str) -> bool:
        """Whether ``notation`` names a component the index discovered."""
        return notation in self.index.components

    def definition(self, notation: str) -> Location | None:
        """Resolve a notation to the file that defines it.

        Line 0 is deliberate: a component's definition is its *file*, and the
        index records no intra-file position for a component's own declaration.
        Pointing at line 0 is honest about that; inventing a line would not be.
        """
        component = self.index.components.get(notation)
        if component is None:
            return None
        return Location(path=component.file_path, line=0)

    def hover(self, notation: str) -> dict[str, Any] | None:
        """Return the hover payload for ``notation``: description + frontmatter."""
        component = self.index.components.get(notation)
        if component is None:
            return None
        frontmatter = component.frontmatter or {}
        return {
            'notation': notation,
            'kind': component.component_id.component_type,
            'path': str(component.file_path),
            'description': frontmatter.get('description'),
            'frontmatter': {k: v for k, v in frontmatter.items() if k != 'description'},
            'inbound_edges': len(self.index.get_reverse_deps(notation)),
            'outbound_edges': len(self.index.get_forward_deps(notation)),
        }

    # -- references ---------------------------------------------------------

    def references(self, notation: str) -> list[Reference]:
        """Return every inbound edge to ``notation``, each with a verified site.

        ⚠ Completeness is bounded by what the index sees. An edge the detectors
        do not recognise is absent here, so an empty result means *the index
        found no inbound edge*, never *the corpus contains none*. The server
        surfaces that distinction rather than implying completeness.
        """
        out: list[Reference] = []
        for dep in self.index.get_reverse_deps(notation):
            source_notation = dep.source.to_notation()
            location, verified = self.resolve_reference_site(dep, notation)
            if location is None:
                continue
            out.append(
                Reference(
                    source_notation=source_notation,
                    dep_type=dep.dep_type.value,
                    location=location,
                    verified=verified,
                )
            )
        return out

    def resolve_reference_site(self, dep: Dependency, notation: str) -> tuple[Location | None, bool]:
        """Resolve where an edge is actually cited, and whether that is confirmed.

        The index attributes a sub-document edge to the **owning skill**, so the
        recorded line number may belong to a sibling document rather than to the
        owner's own definition file. Re-reading the cited line is what tells the
        two apart; without it, a reference would point confidently at the wrong
        file. Candidate files are searched owner-first, then its sub-documents.
        """
        owner = self.index.components.get(dep.source.to_notation())
        if owner is None:
            return None, False

        line_no = _context_line(dep)
        if line_no is None:
            # A non-positional edge (frontmatter) still points at a real file.
            return Location(path=owner.file_path, line=0), False

        zero_based = line_no - 1
        tokens = expected_tokens(notation)
        for candidate in self._candidate_files(owner.file_path):
            lines = self._lines(candidate)
            if 0 <= zero_based < len(lines) and any(token in lines[zero_based] for token in tokens):
                return Location(path=candidate, line=zero_based), True

        # Cited, but unconfirmable — reported against the owner, flagged as such.
        return Location(path=owner.file_path, line=zero_based), False

    def _candidate_files(self, owner_file: Path) -> list[Path]:
        """The owner's own file first, then the sub-documents it may cite from.

        ⚠ **Cached per owner, because this is called once per reverse edge.** The
        directory walk is the dominant cost of :meth:`references` — a component
        with 443 inbound edges walked the same skill directory 443 times, which
        made a "warm index" answer take ~125 ms and, worse, made it take the same
        ~125 ms on every repeat call. Residency is the whole justification for
        this surface, so a per-edge filesystem walk that never warms up defeats
        the design rather than merely slowing it.
        """
        cached = self._candidate_cache.get(owner_file)
        if cached is not None:
            return cached
        candidates = [owner_file]
        skill_dir = owner_file.parent
        if skill_dir.is_dir():
            for sub in sorted(skill_dir.rglob('*')):
                if sub.is_file() and sub.suffix in SUBDOC_SUFFIXES and sub != owner_file:
                    candidates.append(sub)
        self._candidate_cache[owner_file] = candidates
        return candidates

    def _lines(self, path: Path) -> list[str]:
        """Read and cache a file's lines; unreadable files cache as empty."""
        cached = self._line_cache.get(path)
        if cached is not None:
            return cached
        try:
            lines = path.read_text(encoding='utf-8').split('\n')
        except (OSError, UnicodeDecodeError):
            lines = []
        self._line_cache[path] = lines
        return lines

    # -- reporting ----------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Coverage figures a consumer needs to read an empty answer correctly."""
        forward = sum(len(v) for v in self.index.forward_deps.values())
        return {
            'components': len(self.index.components),
            'forward_edges': forward,
            'base_path': str(self.base_path),
        }
