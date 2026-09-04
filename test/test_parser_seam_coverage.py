#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tree-wide guard: every marketplace CLI entry point still reaches a parser seam.

:func:`conftest.parse_ns` builds a namespace by running a script's OWN parser, and
raises :class:`conftest.ParserSeamNotFound` when neither of its two seams resolves.
Which scripts are reachable that way is a property of the whole tree that nothing
re-derived, so an entry-point script could land with no reachable seam unnoticed.

Both populations are derived from the tree on every run and compared against a
roster recording a shape verdict per script. :data:`SEAM_EXEMPT` holds the entry
points that deliberately reach no seam, and the set that actually raises is compared
against its ``probe: live`` rows in both directions — non-empty by construction, so
a new unreachable entry point AND a row that has since gained a seam each fail.
:data:`NON_CLI_LIBRARY` holds the modules under a skill's ``scripts/`` tree whose
owning skill ships no entry point at all, compared against the derivation both ways.

The two probe modes are different properties. ``probe: live`` rows are really run,
which is what makes the raising set non-empty and therefore assertable. ``probe:
structural`` rows are the unprobeable ones — each publishes a ``main()`` that reads
stdin and acts on it — so they are never executed and are pinned against BOTH seams
from source; a builder-only pin would leave a hook free to grow a seam-2
``parse_args`` path and stay green forever.

Per ADR-019 a module the probe could not evaluate becomes a distinct ``unmeasured``
outcome rather than counting as seam-reached, and the set equality holds only while
that set is empty — which is asserted, not assumed.
"""

import ast
import contextlib
import io
import sys
from pathlib import Path
from types import ModuleType
from typing import NamedTuple

import pytest

from conftest import (
    MARKETPLACE_ROOT,
    PARSER_BUILDER_NAMES,
    ParserSeamNotFound,
    load_script_module,
    parse_ns,
)

#: A token no parser declares, so a REACHED parser rejects it with ``SystemExit``
#: while an unreachable one raises ``ParserSeamNotFound``. It names no subcommand,
#: so no command handler can run.
PROBE_TOKEN = '--pm-parser-seam-probe-not-a-real-flag'

PROBE_LIVE = 'live'
PROBE_STRUCTURAL = 'structural'

#: Probe outcomes. ``unmeasured`` is the ADR-019 third state and is never folded
#: into ``reached``: a module that could not be evaluated has not been shown to
#: reach anything.
_REACHED = 'reached'
_NO_SEAM = 'no_seam'
_UNMEASURED = 'unmeasured'


class ShapeVerdict(NamedTuple):
    """One recorded verdict: the script's shape, how it is probed, and why."""

    shape: str
    probe: str
    rationale: str


class ProbeResult(NamedTuple):
    """The partition one probe pass produces over the probed population."""

    reached: frozenset[str]
    no_seam: frozenset[str]
    unmeasured: tuple[tuple[str, str], ...]


def is_main_guard(node: ast.stmt) -> bool:
    """Whether *node* is a module-level ``if __name__ == '__main__':`` guard.

    AST-shaped rather than text-matched, because modules in this tree MENTION
    ``__main__`` in a comment or a rule literal without being entry points.
    """
    if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
        return False
    test = node.test
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return False
    sides: set[str] = set()
    for side in (test.left, test.comparators[0]):
        if isinstance(side, ast.Name):
            sides.add(side.id)
        elif isinstance(side, ast.Constant) and isinstance(side.value, str):
            sides.add(side.value)
    return sides == {'__name__', '__main__'}


def derive_populations(root: Path) -> tuple[frozenset[str], frozenset[str]]:
    """Derive ``(entry_points, non_cli_modules)`` from the script tree under *root*.

    One walk yields both, because the non-CLI class is the entry-point class's
    complement at SKILL granularity, so the two cannot disagree about which skills
    publish a CLI. Members are labelled ``bundle:skill:script`` — the label
    :func:`conftest.parse_ns` reports a script under — so a failure names the call
    that reproduces it. A module that does not parse is deliberately not skipped: it
    might be an entry point and was never classified, so the ``SyntaxError``
    propagates instead of shrinking the population silently.
    """
    modules: list[tuple[str, str]] = []
    entry: set[str] = set()
    for path in sorted(root.glob('*/skills/*/scripts/**/*.py')):
        if '__pycache__' in path.parts:
            continue
        parts = path.relative_to(root).parts
        skill_key = f'{parts[0]}:{parts[2]}'
        label = f'{skill_key}:{"/".join(parts[4:])}'
        modules.append((skill_key, label))
        if any(is_main_guard(node) for node in ast.parse(path.read_text(encoding='utf-8')).body):
            entry.add(label)

    with_cli = {skill_key for skill_key, label in modules if label in entry}
    return frozenset(entry), frozenset(label for skill_key, label in modules if skill_key not in with_cli)


ENTRY_POINTS, NON_CLI_MODULES = derive_populations(MARKETPLACE_ROOT)

#: Entry points that deliberately reach no parser seam, one row per script.
SEAM_EXEMPT: dict[str, ShapeVerdict] = {
    'plan-marshall:platform-runtime:platform_runtime.py': ShapeVerdict(
        'dispatch router',
        PROBE_LIVE,
        'main() resolves an operation and dispatches before reaching any parse_args, so only a handler parser is '
        'interceptable; its pre-dispatch config read and sys.path insert are idempotent and already paid by '
        'test_shared_harness.py::test_a_router_script_fails_loudly_rather_than_yielding_a_guess.',
    ),
    'plan-marshall:manage-logging:plan_logging.py': ShapeVerdict(
        'import-only library',
        PROBE_LIVE,
        'it publishes no callable main(), so parse_ns reaches its raise without executing any script logic.',
    ),
    'plan-marshall:platform-runtime:claude_hook.py': ShapeVerdict(
        'stdin-driven hook',
        PROBE_STRUCTURAL,
        'main() reads a hook payload from stdin and acts on it, so there is no argv contract to probe.',
    ),
    'plan-marshall:platform-runtime:claude_pretooluse_capture.py': ShapeVerdict(
        'stdin-driven hook',
        PROBE_STRUCTURAL,
        'main() reads a PreToolUse payload from stdin and records it, so there is no argv contract to probe.',
    ),
    'plan-marshall:platform-runtime:claude_pretooluse_hook.py': ShapeVerdict(
        'stdin-driven hook',
        PROBE_STRUCTURAL,
        'main() reads a PreToolUse payload from stdin and renders a gate verdict, so there is no argv contract.',
    ),
}

#: Modules whose owning skill ships no entry point at all. The keys are asserted
#: against the guard's own derived population both ways, so this is a verdict record
#: rather than a hand-kept list.
NON_CLI_LIBRARY: dict[str, str] = {
    'plan-marshall:manage-terminal-title:manage_terminal_title.py':
        'terminal-title rendering library called by the runtime hooks; its skill publishes no CLI.',
    'plan-marshall:ref-toon-format:toon_parser.py':
        'TOON parse/serialize library imported across every bundle; its skill publishes no CLI.',
    'plan-marshall:tools-input-validation:input_validation.py':
        'shared argument- and identifier-validation helpers; its skill publishes no CLI.',
    'plan-marshall:tools-input-validation:schema_validation.py':
        'shared schema-validation helpers; its skill publishes no CLI.',
    'pm-documents:plan-marshall-plugin:doc_references.py':
        'documentation-reference helpers for the bundle extension; its skill publishes no CLI.',
}

LIVE_PROBED = frozenset(label for label, row in SEAM_EXEMPT.items() if row.probe == PROBE_LIVE)
STRUCTURALLY_PINNED = frozenset(label for label, row in SEAM_EXEMPT.items() if row.probe == PROBE_STRUCTURAL)

#: Published on EVERY run — passing included — by the root conftest's
#: ``pytest_report_header``, which reads this pair rather than re-deriving anything.
#: Both derived sizes are carried, so a silent shrink in EITHER sweep shows up on a
#: green run. Derived by the tree walk alone, so the header hook does no probing.
GUARD_POPULATION_LABEL = f'parser-seam entry points (+{len(NON_CLI_MODULES)} non-CLI library modules)'
GUARD_POPULATION_SIZE = len(ENTRY_POINTS)


def _source_of(label: str) -> ast.Module:
    """Parse a roster member's source without importing it.

    ``path`` is annotated because ``conftest`` is an untyped import, so
    ``MARKETPLACE_ROOT`` arrives as ``Any`` and every path derived from it would too.
    """
    bundle, skill, script = label.split(':', 2)
    path: Path = MARKETPLACE_ROOT / bundle / 'skills' / skill / 'scripts' / script
    return ast.parse(path.read_text(encoding='utf-8'), filename=str(path))


#: How a module body binds a name, as reported in the seam-1 failure message. The
#: remedy differs by route: a builder DEFINED here means the row is simply wrong,
#: while an IMPORTED one may mean the hook re-exports a builder owned elsewhere.
_BOUND_DEFINED = 'defined here'
_BOUND_IMPORTED = 'imported'


def _module_bindings(module: ast.Module) -> dict[str, str]:
    """Every name the module BODY binds, mapped to the route that binds it.

    Approximates the ``getattr(module, name, None)`` lookup that
    :func:`conftest._parser_from_builder` performs, without importing anything.
    Imports are bindings too — a module-level ``from helper import build_parser``
    publishes that attribute exactly as a ``def`` does — so a collector reading only
    definitions would report an imported builder as absent and leave a row pinned as
    unprobeable while its seam 1 is reachable. Only module-level nodes are walked,
    because a binding inside a function body is not a module attribute.
    """
    bound: dict[str, str] = {}
    for node in module.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            bound[node.name] = _BOUND_DEFINED
        elif isinstance(node, ast.Assign):
            bound.update((t.id, _BOUND_DEFINED) for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            bound[node.target.id] = _BOUND_DEFINED
        elif isinstance(node, ast.ImportFrom):
            bound.update((alias.asname or alias.name, _BOUND_IMPORTED) for alias in node.names)
        elif isinstance(node, ast.Import):
            # ``import pkg.mod`` binds ``pkg``; only an ``as`` clause binds the tail.
            bound.update(
                (alias.asname or alias.name.split('.', 1)[0], _BOUND_IMPORTED) for alias in node.names
            )
    return bound


def _published_builders(module: ast.Module) -> list[str]:
    """The :data:`conftest.PARSER_BUILDER_NAMES` members *module* binds, route included."""
    bound = _module_bindings(module)
    return sorted(f'{name} ({bound[name]})' for name in PARSER_BUILDER_NAMES if name in bound)


def _classify(bundle: str, skill: str, script: str, *, register: bool) -> tuple[str, str]:
    """Run one ``parse_ns`` probe and classify how it ended.

    Output is discarded because every probed CLI writes its own usage error, and a
    hundred of those would bury the failing assertion's message. ``Exception`` is
    caught so a module that cannot be evaluated becomes the ``unmeasured`` third
    state instead of aborting the sweep — producing that classification IS this
    function's job. Any other ``BaseException`` still propagates.
    """
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            parse_ns(bundle, skill, script, PROBE_TOKEN, register=register)
    except SystemExit:
        return _REACHED, ''
    except ParserSeamNotFound as exc:
        return _NO_SEAM, str(exc)
    # A broad catch is deliberate here: an unexpected exception is classified as
    # unmeasured and reported with its type and message, never swallowed.
    except Exception as exc:
        return _UNMEASURED, f'{type(exc).__name__}: {exc}'
    return _REACHED, ''


def probe_entry_point(label: str) -> tuple[str, str]:
    """Classify one entry point's seam reachability as ``(outcome, detail)``.

    Probed unregistered first, which ``parse_ns`` documents as correct when only the
    namespace is wanted, so the probe cannot displace a copy another test module
    imports plainly. A module whose own body resolves its name through
    ``sys.modules`` — a ``dataclass(slots=True)`` field-type lookup is the shape
    here — cannot execute unregistered, and would otherwise read as ``unmeasured``
    for a reason belonging to the probe rather than the script. It is retried
    registered with the displaced entry restored afterwards, so no-displacement
    still holds and ``unmeasured`` stays reserved for a genuinely unprobeable module.
    """
    bundle, skill, script = label.split(':', 2)
    outcome, detail = _classify(bundle, skill, script, register=False)
    if outcome != _UNMEASURED:
        return outcome, detail

    name = script.rsplit('/', 1)[-1].removesuffix('.py')
    saved: ModuleType | None = sys.modules.get(name)
    try:
        return _classify(bundle, skill, script, register=True)
    finally:
        if saved is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = saved


@pytest.fixture(scope='module')
def probe() -> ProbeResult:
    """Probe every derived entry point except the structurally pinned rows.

    Module-scoped because the sweep re-executes each script module, so probing per
    assertion would repeat the whole tree once per test.
    """
    reached: set[str] = set()
    no_seam: set[str] = set()
    unmeasured: list[tuple[str, str]] = []
    for label in sorted(ENTRY_POINTS - STRUCTURALLY_PINNED):
        outcome, detail = probe_entry_point(label)
        if outcome == _REACHED:
            reached.add(label)
        elif outcome == _NO_SEAM:
            no_seam.add(label)
        else:
            unmeasured.append((label, detail))
    return ProbeResult(frozenset(reached), frozenset(no_seam), tuple(unmeasured))


def test_both_populations_are_derived_and_non_empty():
    """The walk finds entry points across several bundles, and library modules too.

    Every assertion below quantifies over these sets, so a walk that stopped finding
    scripts would satisfy all of them vacuously. Bundle spread is checked instead of
    a count, which would move whenever a script is added.
    """
    assert ENTRY_POINTS, f'No entry point derived under {MARKETPLACE_ROOT}; every seam check below is vacuous'
    bundles = {label.split(':', 1)[0] for label in ENTRY_POINTS}
    assert len(bundles) > 1, (
        f'All {len(ENTRY_POINTS)} derived entry points come from {sorted(bundles)}, so the walk no longer '
        'reaches the whole marketplace tree.'
    )
    assert NON_CLI_MODULES, 'No non-CLI module derived, so the NON_CLI_LIBRARY comparison covers nothing'
    overlap = sorted(NON_CLI_MODULES & ENTRY_POINTS)
    assert overlap == [], f'Derived as BOTH entry point and non-CLI: {overlap}; the classes are complements'


def test_the_exempt_roster_is_well_formed():
    """Every row names a derived entry point and declares a known probe mode.

    A row for a renamed script never appears on either side of the set comparison
    below, and a row with an unknown mode falls out of both the probed population
    and the structural pins — so either is checked by nothing at all.
    """
    stale = sorted(set(SEAM_EXEMPT) - ENTRY_POINTS)
    assert stale == [], (
        f'{len(stale)} SEAM_EXEMPT row(s) name no derived entry point: {stale}. The script was renamed or '
        'removed, or it no longer carries a __main__ guard.'
    )
    unknown = sorted(label for label, row in SEAM_EXEMPT.items() if row.probe not in (PROBE_LIVE, PROBE_STRUCTURAL))
    assert unknown == [], f'SEAM_EXEMPT row(s) declare an unknown probe mode: {unknown}'
    assert LIVE_PROBED, 'No row is live-probed, so the raising set below is empty and its equality is vacuous'


def test_no_entry_point_is_left_unmeasured(probe):
    """The probe evaluated every script it swept.

    Checked before the set equality is trusted, per ADR-019: a module that could not
    be evaluated has not been shown to reach a seam, so a clean equality over a
    population containing one is a verdict about a subject nobody examined.
    """
    assert probe.unmeasured == (), (
        f'{len(probe.unmeasured)} entry point(s) could not be probed, so the seam verdict covers less than '
        f'the derived population: {[f"{label} ({why})" for label, why in probe.unmeasured]}'
    )


def test_the_raising_set_is_exactly_the_live_probed_exempt_rows(probe):
    """Precisely the recorded ``probe: live`` scripts fail to reach a seam.

    Both directions are real failures while the raising set is non-empty: an entry
    point that raises with no row lost its CLI surface unnoticed, and a row that
    stopped raising is a verdict that has silently gone out of date.
    """
    assert probe.no_seam == LIVE_PROBED, (
        f'Raising with no SEAM_EXEMPT row: {sorted(probe.no_seam - LIVE_PROBED)}; live-probed rows that '
        f'reached a seam after all: {sorted(LIVE_PROBED - probe.no_seam)}. Probed '
        f'{len(probe.reached) + len(probe.no_seam)} of {len(ENTRY_POINTS)} derived entry points.'
    )


def test_every_probed_script_landed_in_exactly_one_outcome(probe):
    """The probed population is the derivation less the structural rows.

    Without this, a script dropped between derivation and probe would leave the
    equality above passing over a smaller set than the guard claims to cover.
    """
    assert probe.reached | probe.no_seam == ENTRY_POINTS - STRUCTURALLY_PINNED
    assert not (probe.reached & probe.no_seam)


@pytest.mark.parametrize('label', sorted(STRUCTURALLY_PINNED))
def test_a_structurally_pinned_row_publishes_no_parser_builder(label):
    """Seam 1, pinned from source: the module binds no builder name, by any route.

    Read from source because these scripts are never executed — importing one to
    inspect its attributes is the cost this probe mode exists to avoid. The
    approximation covers imports as well as definitions, because the runtime
    predicate it stands in for is an attribute lookup, and an import binds a module
    attribute just as a ``def`` does.
    """
    published = _published_builders(_source_of(label))
    assert published == [], (
        f'{label} is recorded as unprobeable but publishes {published}, which parse_ns resolves as seam 1. '
        'It has a reachable seam and no longer belongs in SEAM_EXEMPT. A builder defined here means the row '
        'is simply wrong; an imported one may mean the hook re-exports a builder owned by another module.'
    )


@pytest.mark.parametrize('label', sorted(STRUCTURALLY_PINNED))
def test_a_structurally_pinned_row_has_no_parse_args_call_site(label):
    """Seam 2, pinned from source: the module never calls ``parse_args``.

    This is the half a builder-only pin misses — a hook that grew a parse call in
    its ``main()`` becomes interceptable while still publishing no builder. Matched
    as an ATTRIBUTE access, because the patched seam is the method on the parser
    object; a bare imported function of the same name is not that seam.
    """
    lines = sorted(
        node.lineno
        for node in ast.walk(_source_of(label))
        if isinstance(node, ast.Attribute) and node.attr == 'parse_args'
    )
    assert lines == [], (
        f'{label} is recorded as unprobeable but calls parse_args at line(s) {lines}, which parse_ns '
        'intercepts as seam 2. It has a reachable seam and no longer belongs in SEAM_EXEMPT.'
    )


def test_the_non_cli_roster_matches_the_derived_population():
    """``NON_CLI_LIBRARY``'s keys are exactly the derived non-CLI modules.

    Both directions carry work: a new skill shipping only libraries fails until it
    carries a verdict, and a row whose skill now publishes an entry point fails
    until it is removed.
    """
    assert set(NON_CLI_LIBRARY) == NON_CLI_MODULES, (
        f'Derived with no NON_CLI_LIBRARY row: {sorted(NON_CLI_MODULES - set(NON_CLI_LIBRARY))}; rows whose '
        f'skill now publishes an entry point: {sorted(set(NON_CLI_LIBRARY) - NON_CLI_MODULES)}.'
    )


@pytest.mark.parametrize('label', sorted(NON_CLI_LIBRARY))
def test_a_non_cli_row_publishes_neither_builder_nor_main(label):
    """A recorded library module exposes no CLI surface.

    Growing a builder or a ``main()`` without an entry-point guard would make that
    verdict false while the roster still asserted it, leaving the module reachable
    as a CLI that no entry-point sweep covers.
    """
    bundle, skill, script = label.split(':', 2)
    module = load_script_module(bundle, skill, script, register=False)

    published = [name for name in PARSER_BUILDER_NAMES if callable(getattr(module, name, None))]
    assert published == [], f'{label} is recorded as a non-CLI library but publishes {published}'
    assert not callable(getattr(module, 'main', None)), (
        f'{label} is recorded as a non-CLI library but publishes a callable main(), which parse_ns would '
        'reach as seam 2 while no entry-point guard makes it a CLI.'
    )


#: Detector controls. The mention-only cases are what a text match gets wrong, and
#: both are present in this tree: a module documents being loaded as ``__main__`` in
#: a comment, and a rule analyzer carries the name as a string literal it detects.
_GUARD_SOURCES = [
    ("if __name__ == '__main__':\n    pass\n", True, 'canonical-guard'),
    ("if '__main__' == __name__:\n    pass\n", True, 'reversed-operands'),
    ('# run directly it loads as ``__main__``\nG = \'if __name__ == "__main__":\'\n', False, 'mention-only'),
    ("if GUARD == '__main__':\n    pass\n", False, 'compares-another-name'),
]


@pytest.mark.parametrize(
    ('source', 'expected'),
    [(source, expected) for source, expected, _ in _GUARD_SOURCES],
    ids=[name for _, _, name in _GUARD_SOURCES],
)
def test_guard_detector_classifies_each_shape(source, expected):
    """The detector fires on a real guard and on nothing that merely resembles one."""
    assert any(is_main_guard(node) for node in ast.parse(source).body) is expected


#: Seam-1 collector controls, one binding route each. The import rows are what a
#: definition-only collector misses, and they are matched by negative rows so the
#: pin is shown to distinguish a published builder from a module that binds none.
_BUILDER_SOURCES = [
    ('def build_parser():\n    pass\n', ['build_parser (defined here)'], 'defined'),
    ('_build_parser = None\n', ['_build_parser (defined here)'], 'assigned'),
    ('from helper import build_parser\n', ['build_parser (imported)'], 'imported-from'),
    ('import build_parser\n', ['build_parser (imported)'], 'imported-plain'),
    ('from helper import make as _build_arg_parser\n', ['_build_arg_parser (imported)'], 'imported-aliased'),
    ('import argparse\nVALUE = 1\n', [], 'binds-no-builder'),
    ('def _hook():\n    from helper import build_parser\n', [], 'function-local-import'),
]


@pytest.mark.parametrize(
    ('source', 'expected'),
    [(source, expected) for source, expected, _ in _BUILDER_SOURCES],
    ids=[name for _, _, name in _BUILDER_SOURCES],
)
def test_seam_one_collector_reports_a_builder_by_every_binding_route(source, expected):
    """The pin fails for an import-bound builder and passes for a module binding none.

    ``parse_ns`` resolves seam 1 with ``getattr`` plus ``callable``, which cannot tell
    where the attribute came from, so a structural row that ignored imports would go
    green over a hook that re-exported a builder — the same silently-out-of-date
    verdict the row exists to catch.
    """
    assert _published_builders(ast.parse(source)) == expected


def test_derivation_reports_empty_populations_for_a_tree_with_no_scripts(tmp_path):
    """A mis-rooted walk derives nothing, which is what the population test catches."""
    assert derive_populations(tmp_path) == (frozenset(), frozenset())


def test_derivation_splits_a_synthetic_tree_by_skill(tmp_path):
    """The non-CLI class is the complement at SKILL level, not at module level.

    A library BESIDE an entry point is not in the class, while one in a skill with no
    entry point is. Both live in one synthetic tree, so a derivation keyed on the
    module fails here rather than quietly reclassifying every private helper.
    """
    cli_skill = tmp_path / 'b' / 'skills' / 'has-cli' / 'scripts'
    lib_skill = tmp_path / 'b' / 'skills' / 'no-cli' / 'scripts'
    cli_skill.mkdir(parents=True)
    lib_skill.mkdir(parents=True)
    (cli_skill / 'tool.py').write_text("if __name__ == '__main__':\n    pass\n", encoding='utf-8')
    (cli_skill / '_helper.py').write_text('VALUE = 1\n', encoding='utf-8')
    (lib_skill / 'library.py').write_text('VALUE = 1\n', encoding='utf-8')

    entry, non_cli = derive_populations(tmp_path)

    assert entry == frozenset({'b:has-cli:tool.py'})
    assert non_cli == frozenset({'b:no-cli:library.py'})
