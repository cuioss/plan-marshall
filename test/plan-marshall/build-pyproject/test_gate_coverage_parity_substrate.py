#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""One `parity_population` cell, re-checked against the substrate it describes.

``parity_population`` is a **recorded** literal, not a derivation: each cell's
``verdict`` and ``note`` was established by reading both sides by hand, and
nothing recomputes them. Its sibling test asserts the population is non-empty,
which is a real guard against an empty table reading as perfect parity — but it
is a guard over a hand-written tuple, so it stays green while every note in that
tuple drifts away from the code it claims to describe.

This module closes one instance of that gap. The ``spdx-paths`` cell names the
exact path list the whole-tree quality gate hands to the SPDX checker, and
``build.py`` constructs that list in code — so the note IS checkable, and is
checked here. If the gate's SPDX scope changes and the note does not, the build
fails instead of quietly misdescribing itself.

**One cell, deliberately.** Making the whole population genuinely derived would
be new machinery for an artifact with no production consumer; that was weighed
and not taken. What this module buys is that "recorded" no longer means
"unchecked in every direction" — the cell whose note is most mechanically
verifiable is bound to its source. The remaining cells stay recorded-only, and
that asymmetry is stated rather than papered over.
"""

from __future__ import annotations

import re
from pathlib import Path

from _gate_coverage import parity_population

#: Repository root, from this module's own position (``test/{bundle}/{skill}/``).
_REPO_ROOT = Path(__file__).parents[3]

#: The build driver whose whole-tree SPDX scope the cell describes.
_BUILD_PY = _REPO_ROOT / 'build.py'

#: The cell under test.
_CELL_DIMENSION = 'spdx-paths'


def _cell(dimension: str):
    """Resolve one recorded parity cell by dimension name."""
    for cell in parity_population():
        if cell.dimension == dimension:
            return cell
    raise AssertionError(
        f'parity_population() carries no {dimension!r} cell, so this substrate '
        f'check has nothing to verify. Present dimensions: '
        f'{[c.dimension for c in parity_population()]}'
    )


def _whole_tree_spdx_path_expressions() -> list[str]:
    """The path expressions ``build.py`` feeds the SPDX checker on a whole-tree run.

    Read from the source text rather than by importing and calling
    ``cmd_quality_gate``: that function runs the real ruff/mypy/pytest tooling as
    a side effect of reaching the SPDX block, so calling it here would turn a
    string check into a full build. The two assignments it is read from are
    adjacent and literal.
    """
    source = _BUILD_PY.read_text(encoding='utf-8')

    # `paths` is assigned on BOTH branches of cmd_quality_gate — the module-scoped
    # one (`[bundle_path]`) comes first in the source. Select by content: the
    # whole-tree branch is the assignment naming the directory constants. Matching
    # the first assignment instead reads the module-scoped list and compares the
    # note against the wrong scope entirely.
    candidates = [
        match
        for match in re.finditer(r'^\s*paths = \[(.+?)\]\s*$', source, re.MULTILINE)
        if 'BUNDLES_DIR' in match.group(1)
    ]
    assert len(candidates) == 1, (
        f'Expected exactly one whole-tree `paths = [...]` assignment naming '
        f'BUNDLES_DIR in build.py; found {len(candidates)}. Re-read cmd_quality_gate '
        f'and re-anchor the extraction — a wrong anchor here compares the parity '
        f'note against the module-scoped list, which is a different scope.'
    )
    whole_tree = candidates[0]

    extra = re.search(
        r'^\s*spdx_paths \+= \[(.+?)\]\s*$', source, re.MULTILINE
    )
    assert extra, (
        'build.py no longer widens `spdx_paths` with a literal list on the '
        'whole-tree branch. Re-read cmd_quality_gate and re-anchor the extraction.'
    )

    return [
        token.strip()
        for group in (whole_tree.group(1), extra.group(1))
        for token in group.split(',')
        if token.strip()
    ]


def _note_tokens(note: str) -> list[str]:
    """The bracketed path list a parity note names, split into bare tokens."""
    bracketed = re.search(r'\[(.+?)\]', note)
    assert bracketed, (
        f'The {_CELL_DIMENSION!r} note carries no bracketed path list, so there is '
        f'nothing to compare against build.py: {note!r}'
    )
    return [token.strip() for token in bracketed.group(1).split(',') if token.strip()]


def test_the_cell_under_test_is_present_and_parseable():
    """Anti-vacuity: both sides of the comparison must resolve to something."""
    cell = _cell(_CELL_DIMENSION)

    assert _note_tokens(cell.note), 'the recorded note names no paths'
    assert _whole_tree_spdx_path_expressions(), 'build.py yielded no SPDX path expressions'


def test_spdx_paths_note_matches_the_gate_it_describes():
    """The recorded note names exactly the whole-tree SPDX scope build.py builds.

    ``build.py`` composes the whole-tree list from four directory constants plus
    the literal ``'build.py'``. The note names them in prose shorthand, so the
    comparison is by STEM — the last path segment of each constant's value — not
    by the constant's identifier: a note reading ``BUNDLES_DIR`` would describe
    the code rather than the scope, which is not what a parity table is for.
    """
    cell = _cell(_CELL_DIMENSION)

    constant_stems = {
        'BUNDLES_DIR': 'bundles',
        'TEST_DIR': 'test',
        'CLAUDE_DIR': '.claude',
        'TARGETS_DIR': 'targets',
    }
    actual = set()
    for expression in _whole_tree_spdx_path_expressions():
        name = re.search(r'\b([A-Z_]+_DIR)\b', expression)
        if name:
            stem = constant_stems.get(name.group(1))
            assert stem is not None, (
                f'build.py feeds the SPDX checker an unrecognised path constant '
                f'{name.group(1)!r}. Add its stem here and to the parity note, or '
                f'this check silently stops covering it.'
            )
            actual.add(stem)
            continue
        literal = re.search(r"""['"](.+?)['"]""", expression)
        assert literal, f'unparseable SPDX path expression in build.py: {expression!r}'
        actual.add(literal.group(1))

    recorded = set(_note_tokens(cell.note))

    assert recorded == actual, (
        f'The recorded {_CELL_DIMENSION!r} parity note claims the whole-tree SPDX '
        f'scope is {sorted(recorded)}, but build.py hands the checker '
        f'{sorted(actual)}. A recorded note that has drifted from the gate it '
        f'describes is exactly the confident-but-untrue signal this population is '
        f'supposed to make legible — correct the note, or correct the gate.'
    )


def test_the_cell_still_claims_parity():
    """The note is only meaningful while the cell claims the two sides are equal.

    Were the verdict downgraded, the note would be describing a difference rather
    than a shared scope, and asserting set equality against build.py would be the
    wrong check — it would fail for the right reason but with a misleading message.
    """
    assert _cell(_CELL_DIMENSION).verdict == 'equal', (
        f'The {_CELL_DIMENSION!r} cell no longer claims parity, so the set-equality '
        f'assertion above no longer matches what the cell asserts. Re-read the cell '
        f'and re-scope this check.'
    )


# ---------------------------------------------------------------------------
# Population COMPLETENESS — every reported coverage dimension has a parity cell
# ---------------------------------------------------------------------------
#
# Raised by automated review: `parity_population` is hand-maintained, so a
# non-empty check plus one bound cell still permits an OMITTED dimension -- the
# gate could report parity while a whole verification dimension went uncompared.
#
# Binding every cell's `note` to its substrate is not tractable (three cells are
# property claims, not path lists). Binding the population's MEMBERSHIP is, and
# it closes the specific hole named: a dimension the gate reports must have at
# least one parity cell speaking to it. Adding a `record_checked` arm to
# `cmd_verify` without a parity cell now fails here rather than silently
# shrinking the table's reach.

#: The dimension label each `boundary.record_checked(...)` call in build.py emits,
#: reduced to its stable leading token. Derived from the source, never transcribed.
_RECORD_CHECKED_RE = re.compile(r'record_checked\(\s*f?[\'"]([^\'"{\[]+)')

#: Maps a gate coverage dimension to the parity-cell names that speak to it.
#: Several dimensions warrant more than one cell (ruff has both a rule-set and a
#: path-scope cell), so this is one-to-many by construction.
_DIMENSION_TO_CELLS = {
    'mypy(production)': {'mypy-production'},
    'mypy(test)': {'mypy-test'},
    'ruff': {'ruff-rules', 'ruff-paths'},
    'SPDX headers': {'spdx-paths'},
    'plugin-doctor': {'plugin-doctor'},
    'module-tests': {'pytest-scope'},
}


def _recorded_dimensions() -> set[str]:
    """The coverage dimensions `cmd_verify`'s arms record, read from build.py.

    The f-string arm at the mypy helper records `{dimension}`, whose two concrete
    values are passed at its call sites; those are picked up separately so the
    set is complete rather than carrying an unexpanded placeholder.
    """
    source = _BUILD_PY.read_text(encoding='utf-8')
    dims = {m.strip() for m in _RECORD_CHECKED_RE.findall(source) if m.strip()}
    dims |= set(re.findall(r"dimension=['\"]([^'\"]+)['\"]", source))
    return dims


def test_the_dimension_extraction_is_not_vacuous():
    """Anti-vacuity: an extraction that found nothing would make the check below pass."""
    dims = _recorded_dimensions()
    assert len(dims) >= 5, (
        f'expected the gate to record at least five coverage dimensions, extracted {sorted(dims)} — '
        f'the regex has probably drifted from build.py, which would make the completeness '
        f'assertion below vacuous'
    )


def test_every_recorded_coverage_dimension_has_a_parity_cell():
    """No dimension the gate reports is missing from the parity population.

    This is the assertion the finding asked for. Without it, `parity_population`
    can omit a dimension entirely and every existing check still passes: the
    non-empty test sees eight other cells, and the per-cell substrate test only
    looks at the cell it names.
    """
    cell_names = {cell.dimension for cell in parity_population()}
    dims = _recorded_dimensions()

    uncovered = []
    for dim in sorted(dims):
        expected = _DIMENSION_TO_CELLS.get(dim)
        if expected is None:
            uncovered.append(f'{dim!r}: no parity cell mapped for this dimension at all')
        elif not (expected & cell_names):
            uncovered.append(f'{dim!r}: expected one of {sorted(expected)}, present cells {sorted(cell_names)}')

    assert not uncovered, (
        'The gate records coverage dimensions that the parity population does not speak to, so a '
        'parity verdict would be reported over an incomplete comparison:\n  ' + '\n  '.join(uncovered)
    )


def test_the_mapping_names_only_cells_that_exist():
    """The map is bound in both directions — a renamed cell fails here.

    Without this the map could name a cell that was deleted or renamed, and the
    completeness check above would report a dimension uncovered for the wrong
    reason (or, if the dimension also vanished, silently stop checking it).
    """
    cell_names = {cell.dimension for cell in parity_population()}
    mapped = {name for names in _DIMENSION_TO_CELLS.values() for name in names}

    missing = mapped - cell_names
    assert not missing, (
        f'the dimension→cell map names cells absent from parity_population(): {sorted(missing)}'
    )
