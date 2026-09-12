#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Population pin for the machine-global config-scope audit.

``manage-locks/standards/machine-global-config-scope-audit.md`` dispositions two
populations: the files that move the process cwd away from a config key's
resolution root, and the files that reach the machine-global home-root tier. This
module re-derives both from the tree and asserts each equals the set the audit
dispositions, so a new cwd-moving process or a new consumer of that tier cannot
join either population unnoticed — it fails here until the audit dispositions it.

**The derivation is call-aware, and that is the load-bearing property.** A text
sweep over these names cannot answer the question either shape asks, because a
regex over bytes matches a docstring, a comment and a ``def`` line exactly as it
matches a call. Narrowing to a parenthesised form does not separate those classes;
it only makes a textual figure look like a criterion-bearing one. The audit records
the concrete counter-example: ``script-shared/scripts/build/_machine_config.py``
carries two ``chdir`` occurrences and invokes it zero times, because that prose is
the module docstring describing the hazard the module exists to remove. A textual
criterion would place the module that CLOSES the shape inside the shape. This
derivation therefore parses each candidate with ``ast`` and keeps only occurrences
that are a call's own ``func``, resolving ``import … as`` aliases first — an alias
binds the target to a local name that no longer contains the target substring, so
any classifier matching on the name alone, textual **or** AST, under-counts callers
by exactly the aliased sites.

Every assertion publishes the derived population size. A closure or equality check
over an empty population passes vacuously — it reports agreement while ranging over
nothing — and publishing the size is what makes that failure visible rather than
silent. The scan additionally fails loudly on any file it could not read or parse,
because an unscanned file is a file that might hold a member and was never looked
at: a coverage gap, not an absence.

The shapes, the sweeps, the per-member evidence and the dispositions are NOT copied
here — the audit standard is the single home for that enforcement-critical content.
"""

from __future__ import annotations

import ast
import re
from functools import lru_cache
from pathlib import Path

from _dispatch_roster import section_lines

from conftest import MARKETPLACE_ROOT

#: The audit standard whose disposition tables the derived populations are checked against.
_AUDIT_STANDARD = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'manage-locks'
    / 'standards'
    / 'machine-global-config-scope-audit.md'
)

#: The two stage-2 classification sections, each holding a table with a ``Call sites`` column.
_SHAPE_A_HEADING = '### Shape A — stage 2, classification (AST, call-aware)'
_SHAPE_B_HEADING = '### Shape B — stage 2, classification (AST, call-aware)'

#: Shape A's target: a process moving its own cwd. ``os.chdir`` is the only form.
_CHDIR_TARGETS = frozenset({'chdir'})

#: Shape B's targets. ``ensure_home_root`` is the creating variant of ``home_root``;
#: both reach the machine-global tier, so both count as a call into it.
_HOME_ROOT_TARGETS = frozenset({'home_root', 'ensure_home_root'})

#: Candidate scope, relative to ``marketplace/bundles``. A superset of both
#: populations by construction: every call site lives in a skill's ``scripts/`` tree.
_CANDIDATE_GLOB = '*/skills/*/scripts/**/*.py'

#: Implausibility floor for the candidate scan. Guards a broken glob, which would
#: otherwise shrink the population silently and let every equality check below pass.
_MIN_CANDIDATES = 300

#: Matches the code-spanned path in a disposition table's first cell.
_PATH_CELL = re.compile(r'`([^`]+\.py)`')

#: Matches the leading integer of a ``Call sites`` / ``Occurrences`` cell, which may
#: carry a parenthetical gloss after the number (``1 (`double_fork`)``).
_LEADING_INT = re.compile(r'(\d+)')

#: Negative-control anchor: the single file the audit places in BOTH shapes. Its
#: presence in both derived sets is what makes the overlap a derived figure rather
#: than a claim, and it is the site whose cwd move and whose tier access are the
#: same process.
_BOTH_SHAPES_ANCHOR = 'manage-build-server/scripts/marshalld.py'


def _skill_relative(path: Path) -> str:
    """Return the ``{skill}/scripts/…`` form of a candidate path.

    The audit's tables are skill-relative while the scan yields bundle-relative
    paths, so both sides are normalised into one space and the assertions below
    can compare SETS for equality rather than matching on path suffixes.
    """
    # parts == (bundle, 'skills', skill, 'scripts', …) by construction of the glob.
    return '/'.join(path.parts[2:])


def _called_names(tree: ast.AST, targets: frozenset[str]) -> bool:
    """Return whether the module invokes any name in ``targets``.

    Resolves ``import … as`` aliases to their target BEFORE counting, then keeps
    only occurrences that are a call's own ``func`` — so a definition, an import
    binding, a bare non-call reference and textual residue in comments, docstrings
    and string literals are all excluded.
    """
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in targets:
                    aliases[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    aliases[alias.asname] = alias.name.rsplit('.', 1)[-1]

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute):
            name = func.attr
        elif isinstance(func, ast.Name):
            name = func.id
        else:
            continue
        if name in targets or aliases.get(name) in targets:
            return True
    return False


@lru_cache(maxsize=1)
def _derive_populations() -> tuple[int, tuple[str, ...], tuple[str, ...]]:
    """Return ``(files_scanned, chdir_callers, home_root_callers)``.

    Walks the real candidate tree once and classifies every file with ``ast``.
    Both member tuples are sorted skill-relative paths, so the populations are
    deterministic. Memoised because several tests consume them and the scan reads
    several hundred files; the returns are TUPLES rather than lists precisely
    because they are now shared, so one test cannot mutate another's population.
    """
    scanned = 0
    chdir_callers: set[str] = set()
    home_root_callers: set[str] = set()

    for path in sorted(MARKETPLACE_ROOT.glob(_CANDIDATE_GLOB)):
        scanned += 1
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'))
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            # An unreadable or unparseable candidate is a file that might hold a
            # member and was never classified. Fail loudly rather than silently
            # shrinking the population it belongs to.
            raise AssertionError(f'Could not scan candidate script {path}: {type(exc).__name__}: {exc}') from None

        relative = _skill_relative(path.relative_to(MARKETPLACE_ROOT))
        if _called_names(tree, _CHDIR_TARGETS):
            chdir_callers.add(relative)
        if _called_names(tree, _HOME_ROOT_TARGETS):
            home_root_callers.add(relative)

    return scanned, tuple(sorted(chdir_callers)), tuple(sorted(home_root_callers))


def _table_rows(heading: str, count_column: str) -> list[tuple[str, int]]:
    """Return ``(skill_relative_path, count)`` for one disposition table.

    A stage-2 section holds more than one table — the classification table and, for
    shape B, the mention-only exclusions — so the table is selected by the column
    its header declares rather than by position. Reading the header is also what
    keeps a renamed column a loud failure instead of an empty result.
    """
    lines = section_lines(_AUDIT_STANDARD.read_text(encoding='utf-8'), heading, stop_prefixes=('### ', '## '))

    rows: list[tuple[str, int]] = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith('|'):
            if in_table:
                break
            continue
        cells = [cell.strip() for cell in stripped.strip('|').split('|')]
        if not in_table:
            if count_column in cells:
                in_table = True
            continue
        if set(''.join(cells)) <= set('-: '):
            continue  # the header separator row
        path_match = _PATH_CELL.search(cells[0])
        count_match = _LEADING_INT.search(cells[1])
        assert path_match, f'No code-spanned path in the first cell of row {cells!r} under {heading!r}'
        assert count_match, f'No leading integer in the {count_column!r} cell of row {cells!r} under {heading!r}'
        rows.append((path_match.group(1), int(count_match.group(1))))
    return rows


def _dispositioned_callers(heading: str) -> set[str]:
    """Return the paths a classification table dispositions as having >= 1 call site."""
    return {path for path, count in _table_rows(heading, 'Call sites') if count >= 1}


def test_audit_standard_exists():
    """The audit standard the populations are checked against must exist."""
    assert _AUDIT_STANDARD.is_file(), f'Missing audit standard: {_AUDIT_STANDARD}'


def test_candidate_scan_is_plausibly_complete():
    """The scan reached a plausible candidate population, and publishes its size.

    Every equality check below ranges over what this scan found. A broken glob
    yields an empty or tiny candidate set, both derived populations come back
    empty, and each equality check then agrees with an audit table it never
    actually tested. The floor is what turns that into a failure.
    """
    scanned, chdir_callers, home_root_callers = _derive_populations()
    assert scanned >= _MIN_CANDIDATES, (
        f'Candidate scan examined {scanned} file(s) under '
        f'{MARKETPLACE_ROOT}/{_CANDIDATE_GLOB}, below the plausibility floor of '
        f'{_MIN_CANDIDATES} — the glob is broken, so the derived populations '
        f'({len(chdir_callers)} cwd-moving, {len(home_root_callers)} tier-reaching) '
        f'cannot be trusted and every equality check below would pass vacuously.'
    )


def test_both_derived_populations_are_non_empty():
    """Neither derived population is empty, and both sizes are published.

    An empty population is not a clean result here: both shapes provably have
    members, so an empty derivation means the classifier stopped working, not that
    the tree stopped carrying them.
    """
    scanned, chdir_callers, home_root_callers = _derive_populations()
    assert chdir_callers, (
        f'Derived cwd-moving population is EMPTY over {scanned} scanned candidate(s) — '
        f'the ast classifier matched no `chdir` call, so the shape A equality check '
        f'would pass vacuously.'
    )
    assert home_root_callers, (
        f'Derived home-root-tier population is EMPTY over {scanned} scanned candidate(s) — '
        f'the ast classifier matched no `home_root`/`ensure_home_root` call, so the '
        f'shape B equality check would pass vacuously.'
    )


def test_shape_a_derived_callers_equal_the_audit_population():
    """The derived cwd-moving set equals the set shape A's table dispositions."""
    scanned, chdir_callers, _home = _derive_populations()
    derived = set(chdir_callers)
    dispositioned = _dispositioned_callers(_SHAPE_A_HEADING)

    assert dispositioned, (
        f'Shape A table under {_SHAPE_A_HEADING!r} dispositions no file with >= 1 call '
        f'site, so the equality check has nothing to range over — against a derived '
        f'population of {len(derived)}: {sorted(derived)}'
    )
    assert derived == dispositioned, (
        f'Shape A population disagrees with the audit. Derived {len(derived)} '
        f'cwd-moving file(s) from {scanned} candidate(s); the audit dispositions '
        f'{len(dispositioned)}.\n'
        f'  Derived but NOT dispositioned (new members — disposition them in the audit): '
        f'{sorted(derived - dispositioned)}\n'
        f'  Dispositioned but NOT derived (the call site is gone — retire the row): '
        f'{sorted(dispositioned - derived)}'
    )


def test_shape_b_derived_callers_equal_the_audit_population():
    """The derived home-root-tier set equals the set shape B's table dispositions."""
    scanned, _chdir, home_root_callers = _derive_populations()
    derived = set(home_root_callers)
    dispositioned = _dispositioned_callers(_SHAPE_B_HEADING)

    assert dispositioned, (
        f'Shape B table under {_SHAPE_B_HEADING!r} dispositions no file with >= 1 call '
        f'site, so the equality check has nothing to range over — against a derived '
        f'population of {len(derived)}: {sorted(derived)}'
    )
    assert derived == dispositioned, (
        f'Shape B population disagrees with the audit. Derived {len(derived)} '
        f'tier-reaching file(s) from {scanned} candidate(s); the audit dispositions '
        f'{len(dispositioned)}.\n'
        f'  Derived but NOT dispositioned (new members — disposition them in the audit): '
        f'{sorted(derived - dispositioned)}\n'
        f'  Dispositioned but NOT derived (the call site is gone — retire the row): '
        f'{sorted(dispositioned - derived)}'
    )


def test_text_only_candidates_are_not_derived_as_callers():
    """A candidate the audit records with zero call sites is absent from THAT shape's set.

    These are the rows that decide the method: a file whose occurrences of that
    shape's target are all prose. If the classifier ever reports one as a caller it
    has regressed to a textual criterion, and the audit's own counter-example is the
    first casualty.

    **The check is per-shape, and that is not a detail.** Exclusion is a property of
    a file AND a shape, never of a file alone:
    ``script-shared/scripts/build/_machine_config.py`` is text-only for ``chdir``
    (its two occurrences are the module docstring naming the hazard it removes) while
    being a genuine ``home_root`` caller. Pooling the two shapes would compare it
    against the union of both derived sets, find it there on shape B's evidence, and
    report shape A's counter-example as a leak — flagging correct behaviour as a
    regression.
    """
    scanned, chdir_callers, home_root_callers = _derive_populations()

    per_shape = (
        (_SHAPE_A_HEADING, set(chdir_callers), 'cwd-moving'),
        (_SHAPE_B_HEADING, set(home_root_callers), 'tier-reaching'),
    )

    checked = 0
    for heading, derived, label in per_shape:
        excluded = {path for path, count in _table_rows(heading, 'Call sites') if count == 0}
        if heading == _SHAPE_B_HEADING:
            excluded |= {path for path, _count in _table_rows(heading, 'Occurrences')}
        checked += len(excluded)

        leaked = sorted(excluded & derived)
        assert not leaked, (
            f'{len(leaked)} of {len(excluded)} candidate(s) the audit excludes as '
            f'prose-only under {heading!r} are in the derived {label} population of '
            f'{len(derived)}: {leaked}. Either the file gained a real call site '
            f'(disposition it as a member) or the classifier has regressed to '
            f'matching text.'
        )

    assert checked, (
        f'The audit records no zero-call or mention-only candidate in either shape, so '
        f'this check ranged over nothing — derived {len(chdir_callers)} cwd-moving and '
        f'{len(home_root_callers)} tier-reaching file(s) over {scanned} candidate(s).'
    )


def test_the_overlap_member_is_derived_in_both_shapes():
    """``marshalld.py`` is derived into BOTH populations — the overlap anchor.

    The audit's key-level finding is that this is not a population of one, and the
    file-level overlap is the structural half of it: one process both moves its cwd
    and reaches the machine-global tier. Deriving the overlap rather than asserting
    it is what keeps that figure honest.
    """
    scanned, chdir_callers, home_root_callers = _derive_populations()
    overlap = set(chdir_callers) & set(home_root_callers)

    assert _BOTH_SHAPES_ANCHOR in overlap, (
        f'Overlap anchor {_BOTH_SHAPES_ANCHOR!r} is absent from the derived overlap of '
        f'{len(overlap)} file(s): {sorted(overlap)}. Derived {len(chdir_callers)} '
        f'cwd-moving and {len(home_root_callers)} tier-reaching file(s) over {scanned} '
        f"candidate(s) — the two shapes no longer meet, so the audit's overlap figure "
        f'is no longer derived from the tree.'
    )
