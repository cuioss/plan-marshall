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


# ---------------------------------------------------------------------------
# The population's LABEL stays honest (D5)
# ---------------------------------------------------------------------------
#
# `_gate_coverage.py` contradicted itself at the point a skimming reader looks
# first. Its section banner called the parity population "the derived comparison
# set", while the docstring immediately beneath said the cells are a recorded
# literal, that nothing recomputes them, and that calling a hand-written table
# derived invites a reader to trust stale cells. The banner is what a reader sees
# on the way past; the refutation is four lines further in.
#
# The label is prose, so nothing was going to fail when it drifted — which is why
# it drifted. This control is what stops it drifting back.
#
# It is deliberately NOT a blanket ban on the word: `structural_limits` IS
# computed from the dimensions a run actually recorded, and must stay describable
# as derived. A guard that scrubbed every mention would break the one place the
# word is earned, so the positive half below asserts that place survives.

_GATE_COVERAGE_SOURCE = (
    _REPO_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'script-shared'
    / 'scripts'
    / 'build'
    / '_gate_coverage.py'
)

_DERIVED_RE = re.compile(r'deriv', re.IGNORECASE)
_PARITY_RE = re.compile(r'parity', re.IGNORECASE)

#: Forms that mention derivation in order to DENY it. The module refutes the
#: derived reading on purpose and at length, so a guard without this exemption
#: would flag the refutation itself and force the honest sentences out.
_REFUTATION_RE = re.compile(
    r'not\s+(?:a\s+)?deriv|rather\s+than\s+(?:a\s+)?deriv|"derived"',
    re.IGNORECASE,
)


def _parity_derived_claims() -> tuple[list[str], int, int]:
    """Lines claiming the parity population is derived, plus what was scanned.

    Returns ``(offending_lines, parity_lines_scanned, derived_mentions_scanned)``.
    The two scan counts are returned so a zero-offender result states WHICH zero
    it is: a scan that examined the module and found no stale claim, or a scan
    that matched nothing at all because the file moved or the pattern broke.
    """
    lines = _GATE_COVERAGE_SOURCE.read_text(encoding='utf-8').splitlines()
    offenders: list[str] = []
    parity_lines = 0
    derived_mentions = 0
    for number, line in enumerate(lines, start=1):
        has_parity = bool(_PARITY_RE.search(line))
        mentions = len(_DERIVED_RE.findall(line))
        parity_lines += 1 if has_parity else 0
        derived_mentions += mentions
        if has_parity and mentions and not _REFUTATION_RE.search(line):
            offenders.append(f'{_GATE_COVERAGE_SOURCE.name}:{number}: {line.strip()}')
    return offenders, parity_lines, derived_mentions


def test_no_surviving_text_calls_the_parity_population_derived():
    """NEGATIVE half: no line asserts the parity population is a derivation.

    RED before the relabel — the section banner read
    ``# Parity population — the derived comparison set (D1 / D6)``, the single
    line in the module that both names the population and calls it derived.

    A sentence that mentions derivation in order to deny it ("recorded, not
    derived") is exempt; the module makes that denial deliberately and this guard
    must not push it out.
    """
    offenders, parity_lines, derived_mentions = _parity_derived_claims()

    # Published on a clean run, so a green states the size of what it scanned.
    print(
        f'parity label scan: parity_lines={parity_lines} '
        f'derived_mentions={derived_mentions} offending_lines={len(offenders)}'
    )

    # Anti-vacuity: a scan matching neither term examined nothing, and its empty
    # offender list would be a "could not look" zero wearing a pass.
    assert parity_lines > 0, (
        f'scanned {_GATE_COVERAGE_SOURCE} and matched no line mentioning "parity"; '
        f'the module moved or was restructured, so this guard examined nothing'
    )
    assert derived_mentions > 0, (
        f'scanned {_GATE_COVERAGE_SOURCE} and matched no mention of derivation at '
        f'all — including the ones that are legitimate — so the guard is not '
        f'reading the file it thinks it is'
    )

    assert not offenders, (
        'These lines name the parity population and call it derived, contradicting '
        'the docstring beneath them, which states the cells are a recorded literal '
        'that nothing recomputes. A hand-written table advertised as derived invites '
        'a reader to trust cells that go stale silently:\n  ' + '\n  '.join(offenders)
    )


def test_the_genuinely_derived_neighbour_is_still_described_as_derived():
    """POSITIVE half: the one place the word IS earned survives.

    ``structural_limits`` is computed from the dimensions a run actually recorded,
    so describing it as derived is accurate. Green before the relabel and green
    after — only the parity banner changes verdict. Without this half, deleting
    every occurrence of the word would satisfy the negative control while
    destroying a true statement, and the pair would not be matched at all.
    """
    text = _GATE_COVERAGE_SOURCE.read_text(encoding='utf-8')

    earned = [
        line.strip()
        for line in text.splitlines()
        if _DERIVED_RE.search(line)
        and not _PARITY_RE.search(line)
        and not _REFUTATION_RE.search(line)
    ]

    assert earned, (
        'No surviving line in _gate_coverage.py describes anything as derived. The '
        'relabel was meant to correct ONE stale claim about the parity population, '
        'not to remove the accurate description of structural_limits, which really '
        'is computed from the dimensions a run recorded. An over-broad edit that '
        'scrubbed the word everywhere would pass the negative control and land a '
        'false statement in its place.'
    )
