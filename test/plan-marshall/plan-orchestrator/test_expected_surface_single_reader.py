#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The single-reader guard for the ``## Expected Surface`` grammar.

Two properties, both of which the disjointness gate's soundness rests on.

**One reader.** Exactly one production module in the marketplace parses the
``## Expected Surface`` heading, and it is ``plan-marshall:script-shared``'s
``epic_spec_parser``. Two readers of that section is the defect this guard
exists to keep closed: the gate previously consumed a weaker parse that resolved
named files only, so a spec declaring a directory, a recursive glob, an
exclusion, or a bullet-relative entry contributed ZERO paths and passed the gate
as colliding with nothing — a plan the gate cannot see is a plan it cannot
serialize.

**One resolution.** The two plan-marshall consumers of that reader — the Ordered
Queue's Surface cell (``_row_surface``) and ``corpus cross-check``'s collision
input (``_spec_record``) — resolve the IDENTICAL surface for the same spec,
because they call the same function. A guard on the carrier set alone would not
catch two consumers that both import the single reader and then disagree about
what to do with it.

The carrier set is POPULATION-DERIVED: the marketplace Python surface is
enumerated at test time and never listed by hand, and its size is published in
the failure message, so a pass over an empty population is impossible.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT, PROJECT_ROOT, load_script_module

#: The single reader under test, addressed by three module-level string
#: constants so the loader call stays statically resolvable to
#: ``test_conftest_loader_contract``'s walker — never the star-unpacked tuple
#: form, which that walker cannot read and which would silently widen its blind
#: spot. ``register=False``: only the returned module is needed here, and the
#: stem is imported plainly by the partition suites.
_BUNDLE = 'plan-marshall'
_SKILL = 'script-shared'
_SCRIPT = 'epic_spec_parser.py'

spec_parser = load_script_module(_BUNDLE, _SKILL, _SCRIPT, register=False)

#: The orchestrator, the module whose retired parse this guard replaced. Loaded
#: under an explicit collision-proof name for the same reason its sibling suite
#: does: the stem is imported plainly elsewhere in the tree.
_ORCH_BUNDLE = 'plan-marshall'
_ORCH_SKILL = 'plan-orchestrator'
_ORCH_SCRIPT = 'orchestrator.py'
_ORCH_MODULE_NAME = 'orchestrator_single_reader_guard'

_orch = load_script_module(
    _ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, module_name=_ORCH_MODULE_NAME
)

#: The filename the sole reader must be, and nothing else.
SOLE_READER = 'epic_spec_parser.py'

#: The heading whose parse is being guarded.
HEADING_TEXT = 'Expected Surface'


# =============================================================================
# One reader — the population-derived carrier set
# =============================================================================


def _marketplace_modules() -> list[Path]:
    """Every production Python module under the marketplace, derived at test time."""
    return sorted(MARKETPLACE_ROOT.rglob('*.py'))


def _compiles_the_heading(module: Path) -> bool:
    """Whether ``module`` COMPILES a pattern for the Expected-Surface heading.

    The signature is a ``re.compile`` call whose pattern literal names the
    heading — which is what PARSING it looks like in code, and what distinguishes
    a reader from the several modules that merely MENTION the section in prose.
    A bare phrase match would flag every docstring that names the section and
    make the guard assert something it does not mean.

    A residual heading regex left behind in a module that no longer reads the
    section is a carrier under this signature, which is the point: the grammar
    leaving a module and its reader leaving it are the same event.
    """
    try:
        tree = ast.parse(module.read_text(encoding='utf-8', errors='ignore'), filename=str(module))
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, 'id', None)
        if name != 'compile':
            continue
        for argument in node.args:
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                if HEADING_TEXT in argument.value:
                    return True
    return False


def test_the_enumerated_population_is_non_empty_and_reaches_both_bundles():
    """Guards every assertion below against a vacuous pass.

    Without this, a walk that resolved nothing would make the carrier-set
    assertion trivially true — which is the failure mode a guard over a
    hand-listed set has by construction and this one must not acquire.
    """
    modules = _marketplace_modules()

    assert modules, f'no Python modules enumerated under {MARKETPLACE_ROOT}'
    names = {module.name for module in modules}
    assert SOLE_READER in names, (
        f'the sole reader is absent from the {len(modules)}-module population — '
        'the walk is not reaching the module under test'
    )
    assert 'orchestrator.py' in names, (
        f'the retired parse\'s former home is absent from the {len(modules)}-module '
        'population, so its residual-carrier case is unreachable'
    )
    bundles = {path.relative_to(MARKETPLACE_ROOT).parts[0] for path in modules}
    assert {'plan-marshall', 'pm-plugin-development'} <= bundles, (
        f'the walk reached only {sorted(bundles)}; both consuming bundles must be in '
        'the population or a duplicate in the unreached one is invisible'
    )


def test_the_sole_reader_is_detected_by_the_signature():
    """Positive control for the signature itself.

    The carrier-set assertion below is an equality against a one-element set, so
    a signature that matched NOTHING would fail it loudly — but a signature that
    matched nothing for the wrong reason would be indistinguishable from a
    corpus with no duplicate. Pinning the true positive separately keeps the two
    apart.
    """
    reader = [m for m in _marketplace_modules() if m.name == SOLE_READER]
    assert len(reader) == 1, f'expected exactly one {SOLE_READER}, found {len(reader)}'

    assert _compiles_the_heading(reader[0])


def test_a_module_that_only_mentions_the_heading_is_not_a_carrier(tmp_path):
    """Matched negative control: prose about the section is not a parse of it.

    Several modules legitimately NAME ``## Expected Surface`` in a docstring —
    including the orchestrator, which documents that it deliberately no longer
    carries the grammar. A signature that flagged them would report a
    single-reader violation on every doc edit and would have to be weakened,
    which is how this class of guard dies.
    """
    prose = tmp_path / 'mentions_only.py'
    prose.write_text(
        '"""A module documenting the ``## Expected Surface`` section it does not parse."""\n'
        'import re\n'
        "HEADING = 'Expected Surface'\n"
        "OTHER = re.compile(r'^ {0,3}##[ \\t]+Claim Labels[ \\t]*$')\n",
        encoding='utf-8',
    )

    assert not _compiles_the_heading(prose)


def test_exactly_one_module_parses_the_expected_surface_heading():
    """The guard. Fails the moment a second reader of the grammar appears.

    Population-derived: the marketplace Python surface is enumerated at test
    time, never listed by hand — a hard-coded list would pass vacuously against
    exactly the duplicate this guard exists to catch — and the population size
    rides the failure message so the assertion can never be read as green over
    an unexamined tree.
    """
    modules = _marketplace_modules()
    carriers = [module for module in modules if _compiles_the_heading(module)]

    assert [module.name for module in carriers] == [SOLE_READER], (
        f'the "## {HEADING_TEXT}" grammar has {len(carriers)} carrier(s) across a '
        f'population of {len(modules)} enumerated marketplace modules, expected '
        f'exactly [{SOLE_READER!r}]: '
        f'{[str(module.relative_to(MARKETPLACE_ROOT)) for module in carriers]}. '
        'A second reader is the defect this guard exists to keep closed; a residual '
        'heading regex in a module that no longer reads the section is one too.'
    )


def test_the_sole_reader_lives_in_the_shared_home():
    """The reader's HOME is part of the contract, not an incidental location.

    It sits in ``script-shared`` because both consuming bundles read the section;
    moving it back inside either one re-creates the import direction that made a
    second copy the easy option.
    """
    carriers = [module for module in _marketplace_modules() if _compiles_the_heading(module)]
    assert len(carriers) == 1, f'{len(carriers)} carriers, expected 1'

    relative = carriers[0].relative_to(MARKETPLACE_ROOT)

    assert relative.parts[:4] == ('plan-marshall', 'skills', 'script-shared', 'scripts'), (
        f'the sole reader lives at {relative}, not in plan-marshall:script-shared'
    )


# =============================================================================
# One resolution — the two consumers agree
# =============================================================================


#: A surface declaring the two shapes the retired reader could not resolve, so
#: agreement is asserted over a NON-EMPTY set that the old parse would have read
#: as empty at both call sites.
_SURFACE_BODY = (
    '# PLAN-01: Fixture\n'
    '\n'
    '## Expected Surface\n'
    '\n'
    '- Adds `test/plan-marshall/plan-orchestrator/`\n'
    '- Adds `marketplace/bundles/plan-marshall/skills/script-shared/**`\n'
)


@pytest.fixture
def spec(tmp_path: Path) -> Path:
    path = tmp_path / 'PLAN-01-alpha.md'
    path.write_text(_SURFACE_BODY, encoding='utf-8')
    return path


def test_the_two_consumers_resolve_the_identical_surface(spec: Path):
    """The Ordered Queue cell and the collision input agree, by construction.

    They agree because they call the same function — this pins that they still
    do. The assertion is over a non-empty set: two consumers that both resolved
    NOTHING would agree vacuously, which is precisely the state the old reader
    left them in.
    """
    rendered = _orch._row_surface(spec, PROJECT_ROOT)
    record = _orch._spec_record('fixture-epic', spec, PROJECT_ROOT)

    from_cell = set(rendered.split(_orch._SURFACE_JOIN))

    assert record['paths'], 'the fixture resolved no surface — the agreement would be vacuous'
    assert len(record['paths']) == 2, (
        f'2 entries declared, {len(record["paths"])} resolved — the fixture is the '
        'directory-plus-recursive-glob pair the retired reader resolved to nothing'
    )
    assert from_cell == record['paths']


def test_the_two_consumers_agree_on_a_spec_that_declares_nothing_resolvable(tmp_path: Path):
    """Matched negative control: they agree on the EMPTY case too, and say so.

    The cell renders the derivation class rather than a blank, and the record
    carries an empty path set — the two agree, and the cell still states WHICH
    zero it is instead of collapsing to a marker that reads as "collides with
    nothing".
    """
    path = tmp_path / 'PLAN-02-beta.md'
    path.write_text(
        '# PLAN-02: Fixture\n\n## Expected Surface\n\nProse only; no entry resolves.\n',
        encoding='utf-8',
    )

    rendered = _orch._row_surface(path, PROJECT_ROOT)
    record = _orch._spec_record('fixture-epic', path, PROJECT_ROOT)

    assert record['paths'] == set()
    assert rendered == f'({spec_parser.CLASS_PROSE})'
    assert record['derivation_status'] == spec_parser.CLASS_PROSE


def test_a_spec_with_no_section_renders_its_own_state_at_the_cell(tmp_path: Path):
    """The third state stays distinguishable at the rendering consumer.

    ``(spec missing)``, ``(spec unreadable)`` and a spec that declares no section
    are three different facts; the cell names each rather than collapsing them.
    """
    path = tmp_path / 'PLAN-03-gamma.md'
    path.write_text('# PLAN-03: Fixture\n\n## Objective\n\nNo surface section.\n', encoding='utf-8')

    rendered = _orch._row_surface(path, PROJECT_ROOT)

    assert rendered == '(no expected surface section)'
    assert _orch._row_surface(None, PROJECT_ROOT) == '(spec missing)'
