#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Every documented archived-plans path must carry the segment the archive resolver writes.

``manage-status archive`` moves a finished plan into the directory
``_status_core.get_archive_dir()`` resolves. Prose across the marketplace names
that location by path, and prose drifts: once the runtime state moved under the
plan-local tier (ADR-002), a population of docs and docstrings kept naming the
pre-move layout, so a reader following them looked for archived plans where the
resolver never writes any.

Why the expected segment is DERIVED, not spelled
------------------------------------------------
The expected ``.plan``-relative archive path is computed by running the real
resolver against a fixture plan root and relativizing the result. A literal
copied into this test would be one more hand-maintained restatement of the
resolver — exactly the kind of copy that went stale in the first place. Derived
from the resolver, the test follows the resolver: if the resolver's composition
ever changes, every documented path is re-checked against the new answer.

Why the stale form is never written here
----------------------------------------
The mutation guard builds the stale path at runtime from the resolver's own
parts. Spelling it as a literal would put one occurrence back into the tree
that an inventory-wide zero-count check over the stale form must not find.

Why the population is guarded
-----------------------------
A scanner that silently walks nothing — a wrong root, a pattern that never
matches — passes every per-occurrence assertion vacuously. The population is
therefore asserted non-empty, spanning more than one bundle, and covering both
file kinds the walk reads, and the collector is shown to pick up the stale shape
it exists to reject.
"""

from __future__ import annotations

import re
from pathlib import Path

import _status_core
import file_ops
import pytest

from conftest import MARKETPLACE_ROOT

#: File kinds the walk reads — the prose surfaces (skill docs, standards,
#: references) and the script docstrings that restate paths.
_SCANNED_SUFFIXES: tuple[str, ...] = ('.md', '.py')

#: One path segment inside a documented path: identifier characters, dots,
#: hyphens, and the ``{placeholder}`` braces docs use for variable parts.
_SEGMENT = r'[A-Za-z0-9_.{}\-]+'


def _collector_pattern(anchor: str, leaf: str) -> re.Pattern[str]:
    """Match every path token that starts at the plan-dir anchor and ends at the archive leaf.

    Anchoring on ``{anchor}/`` keeps bare ``{leaf}/`` directory names and
    ``{base}/{leaf}`` forms out of the population: those name the leaf relative
    to an already-resolved base and carry no claim about the layout beneath the
    plan directory. The trailing lookahead stops a longer identifier that merely
    begins with the leaf from being read as the leaf.
    """
    return re.compile(re.escape(anchor) + '/(?:' + _SEGMENT + '/)*?' + re.escape(leaf) + r'(?![A-Za-z0-9_\-])')


@pytest.fixture
def resolved_archive_rel(tmp_path, monkeypatch) -> Path:
    """The archive directory ``manage-status archive`` writes to, relative to its plan root.

    Runs the production resolution branch — no ``set_base_dir`` override, no
    ``PLAN_BASE_DIR`` — from inside a fixture plan root, so the walk-up finds the
    fixture and ``get_archive_dir()`` composes its answer exactly as it does in a
    real checkout.
    """
    monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
    monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
    # The walk-up keys on the plan-local marker directory beneath the plan dir.
    marker = tmp_path / 'fixture-plan-root' / file_ops.PLAN_DIR_NAME / 'local'
    marker.mkdir(parents=True)
    # Resolved so the comparison below holds where the temp root sits behind a symlink.
    plan_root = marker.parent.parent.resolve()
    monkeypatch.chdir(plan_root)

    archive_dir = _status_core.get_archive_dir()

    assert archive_dir.is_relative_to(plan_root), (
        f'the archive resolver answered {archive_dir}, outside the fixture plan root {plan_root}'
    )
    return archive_dir.relative_to(plan_root)


def _carries_resolved_path(token: str, resolved: str) -> bool:
    """The parity predicate: a documented token names the resolver's location."""
    return token.endswith(resolved)


def _collect_population(pattern: re.Pattern[str]) -> list[tuple[Path, str]]:
    """Every ``(file, token)`` pair the collector finds across the whole marketplace."""
    population: list[tuple[Path, str]] = []
    for path in sorted(MARKETPLACE_ROOT.rglob('*')):
        if path.suffix not in _SCANNED_SUFFIXES or not path.is_file():
            continue
        text = path.read_text(encoding='utf-8')
        population.extend((path, match.group(0)) for match in pattern.finditer(text))
    return population


def test_resolver_places_the_archive_under_the_plan_dir(resolved_archive_rel):
    """The derived path is anchored at the plan dir and has a segment between anchor and leaf.

    The mutation guard below deletes that segment; if the resolver ever put the
    leaf directly under the anchor there would be nothing to delete, and the
    guard would silently test nothing.
    """
    parts = resolved_archive_rel.parts
    assert parts[0] == file_ops.PLAN_DIR_NAME
    assert len(parts) >= 3, f'expected anchor/segment/leaf, got {resolved_archive_rel}'


def test_every_documented_archive_path_matches_the_resolver(resolved_archive_rel):
    """Each ``.plan``-anchored archived-plans token across the marketplace carries the resolver's path."""
    anchor, leaf = resolved_archive_rel.parts[0], resolved_archive_rel.parts[-1]
    resolved = resolved_archive_rel.as_posix()
    population = _collect_population(_collector_pattern(anchor, leaf))

    # Anti-vacuity: a walk that found nothing, or only one corner of the tree,
    # would pass the per-token assertion below over an empty or partial set.
    assert population, f'no {anchor}/…/{leaf} token found under {MARKETPLACE_ROOT}'
    bundles = {path.relative_to(MARKETPLACE_ROOT).parts[0] for path, _ in population}
    assert len(bundles) > 1, f'population spans only {sorted(bundles)}; the walk must cover the whole marketplace'
    suffixes = {path.suffix for path, _ in population}
    assert suffixes == set(_SCANNED_SUFFIXES), f'population covers only {sorted(suffixes)} files'

    stale = [
        f'{path.relative_to(MARKETPLACE_ROOT)}: {token}'
        for path, token in population
        if not _carries_resolved_path(token, resolved)
    ]
    assert not stale, (
        f'{len(stale)} of {len(population)} documented archive path(s) do not name the resolver '
        f'location {resolved}:\n' + '\n'.join(stale)
    )


def test_a_token_missing_the_resolved_segment_is_rejected(resolved_archive_rel):
    """Mutation guard: delete the resolver segment from a real occurrence and the predicate must reject it.

    Also asserts the mutated token is still a member of the collector's
    population — otherwise a stale path in the tree would slip past the walk
    instead of failing the parity check.
    """
    parts = resolved_archive_rel.parts
    anchor, leaf = parts[0], parts[-1]
    resolved = resolved_archive_rel.as_posix()
    pattern = _collector_pattern(anchor, leaf)
    population = _collect_population(pattern)
    assert population, 'mutation guard needs at least one real occurrence to mutate'

    _, original = population[0]
    assert _carries_resolved_path(original, resolved), 'control: the unmutated occurrence must pass'

    segment = '/'.join(parts[1:-1])
    mutated = original.replace(f'{anchor}/{segment}/{leaf}', f'{anchor}/{leaf}')

    assert mutated != original, f'mutation removed nothing from {original!r}'
    assert pattern.fullmatch(mutated), f'collector would not pick up the stale form {mutated!r}'
    assert not _carries_resolved_path(mutated, resolved), f'predicate accepted the stale form {mutated!r}'
