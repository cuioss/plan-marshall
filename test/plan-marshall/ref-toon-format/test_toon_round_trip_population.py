#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Population-derived TOON round-trip and single-implementation guard.

One format, several implementations that disagree, and no test comparing them —
this module is the test that compares them. It answers two questions over a
population it DERIVES from the tree at test time, never from a hand-typed list:

1. **Does every TOON emitter write through the canonical serializer?**
   The population is every function in ``marketplace/bundles/**/scripts`` whose
   name matches the TOON naming probe. An emitter is a member of that population
   that prints to stdout. Every emitter must reach ``serialize_toon`` /
   ``parse_toon`` in its OWN body — file-level import presence is the wrong
   predicate, because a module can import the canonical serializer at the top and
   still hand-roll its own emission below it.

2. **Does the canonical pair round-trip the values that break a hand-rolled one?**
   ``serialize_toon`` → ``parse_toon`` must return the payload it was given for
   ``None``, for a list, and for strings carrying a tab, a comma and a colon —
   exactly the values every retired lookalike wrote bare into a separator-joined
   row.

The round trip is asserted over the CANONICAL PAIR rather than by calling each
enumerated emitter: the emitters take unrelated arguments and there is no generic
way to drive them. What makes that substitution sound is question 1 — once every
emitter is shown to route through the canonical serializer, a property of that
serializer IS a property of every emitter's output.

Three controls keep the two answers from being vacuous:

- The derived population size is published and asserted non-zero, as is the
  emitter subset — a property test over an empty population passes for the wrong
  reason.
- A fixture emitter that prints TOON WITHOUT the canonical serializer must be
  flagged, and a fixture module that swallows a failing ``toon_parser`` import
  behind a substitute must be flagged too. Both prove the clean tree result is a
  measurement rather than a detector that flags nothing.
- An emitter newly added to the tree must be picked up by the derivation, so the
  population cannot silently stop growing.

No ``__init__.py`` is added here: ``ref-toon-format`` is a dashed directory and a
dashed segment is an invalid package name under mypy's ``explicit_package_bases``.
No ``conftest.py`` either — helpers live in this module.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from toon_parser import parse_toon, serialize_toon

from conftest import PROJECT_ROOT

#: The naming probe the emitter census used: ``def [a-z_]*toon[a-z_]*(``.
_TOON_NAME = re.compile(r'^[a-z_]*toon[a-z_]*$', re.IGNORECASE)

#: The canonical reader/writer names. A body that mentions either reaches the
#: single implementation; a body that mentions neither has its own.
_CANONICAL_NAMES = frozenset({'serialize_toon', 'parse_toon'})

#: Where marketplace scripts live, relative to the repo root.
_SCRIPTS_GLOB = 'marketplace/bundles/*/skills/*/scripts/**/*.py'


@dataclass(frozen=True)
class EmitterRecord:
    """One member of the derived population."""

    path: str
    function: str
    line: int
    prints_to_stdout: bool
    reaches_canonical: bool


def _referenced_names(node: ast.AST) -> set[str]:
    """Every bare name and attribute name appearing anywhere under ``node``."""
    found: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            found.add(child.id)
        elif isinstance(child, ast.Attribute):
            found.add(child.attr)
    return found


def _prints_to_stdout(node: ast.AST) -> bool:
    """Whether the function body prints to stdout.

    A ``print(..., file=sys.stderr)`` is a diagnostic, not TOON emission, so it
    does not make its function an emitter. Without this discrimination the
    check-table row BUILDERS in the CI providers — which return dicts and warn on
    stderr — would be demanded to serialize output they never write.
    """
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if not (isinstance(child.func, ast.Name) and child.func.id == 'print'):
            continue
        if any(keyword.arg == 'file' for keyword in child.keywords):
            continue
        return True
    return False


def derive_toon_population(root: Path) -> list[EmitterRecord]:
    """Enumerate the TOON-named functions across the marketplace script tree.

    Derived by walking the tree, so a component added tomorrow is in the
    population without anyone remembering to list it here.
    """
    records: list[EmitterRecord] = []
    for path in sorted(root.glob(_SCRIPTS_GLOB)):
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        except (OSError, SyntaxError):  # pragma: no cover - a broken file is a build failure
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not _TOON_NAME.match(node.name):
                continue
            records.append(
                EmitterRecord(
                    path=str(path.relative_to(root)),
                    function=node.name,
                    line=node.lineno,
                    prints_to_stdout=_prints_to_stdout(node),
                    reaches_canonical=bool(_referenced_names(node) & _CANONICAL_NAMES),
                )
            )
    return records


def _defines_substitute_serializer(tree: ast.AST) -> bool:
    """Whether the module defines a TOON-named function of its own making."""
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _TOON_NAME.match(node.name):
            continue
        if not (_referenced_names(node) & _CANONICAL_NAMES):
            return True
    return False


def swallows_canonical_import(source: str) -> bool:
    """Whether the module swallows a failing ``toon_parser`` import into a substitute.

    This is the lookalike-substitution shape: the canonical import is guarded by
    ``except ImportError``, the handler does NOT re-raise, and the module carries
    its own TOON writer to route around the loss with. Detected by that shape
    rather than by one flag name — a single flag name resolves to a single file
    and cannot establish a population.

    **The substitute is the discriminator, not the swallow.** A health check that
    probes whether ``toon_parser`` imports and records the boolean also swallows
    the error, and installs nothing in its place; flagging it would report a
    diagnostic as a second implementation.
    """
    tree = ast.parse(source)
    if not _defines_substitute_serializer(tree):
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        imports_canonical = any(
            isinstance(stmt, ast.ImportFrom) and stmt.module == 'toon_parser'
            for stmt in ast.walk(node)
        )
        if not imports_canonical:
            continue
        for handler in node.handlers:
            names = _referenced_names(handler.type) if handler.type is not None else set()
            if 'ImportError' not in names:
                continue
            if not any(isinstance(stmt, ast.Raise) for stmt in ast.walk(handler)):
                return True
    return False


# =============================================================================
# The derived population — published, and asserted non-empty before it is used
# =============================================================================


def test_population_is_derived_and_non_empty(capsys):
    """Publish the derived size; a property over an empty population proves nothing."""
    population = derive_toon_population(PROJECT_ROOT)
    emitters = [record for record in population if record.prints_to_stdout]

    with capsys.disabled():
        print(
            f'\nderived TOON population: {len(population)} function(s), '
            f'{len(emitters)} of which emit to stdout'
        )

    assert population, 'the derivation found no TOON-named functions at all'
    assert emitters, 'the derivation found no emitters — the guard below would be vacuous'


def test_every_emitter_reaches_the_canonical_serializer():
    """No emitter writes TOON of its own.

    The failure message names each offender, because the remedy is per-function.
    """
    offenders = [
        f'{record.path}:{record.line} {record.function}'
        for record in derive_toon_population(PROJECT_ROOT)
        if record.prints_to_stdout and not record.reaches_canonical
    ]

    assert not offenders, (
        'these functions emit TOON without reaching the canonical serializer: '
        + ', '.join(offenders)
    )


def test_no_module_swallows_a_failing_canonical_import():
    """A missing serializer must propagate, not hand over to a substitute."""
    offenders = [
        str(path.relative_to(PROJECT_ROOT))
        for path in sorted(PROJECT_ROOT.glob(_SCRIPTS_GLOB))
        if swallows_canonical_import(path.read_text(encoding='utf-8'))
    ]

    assert not offenders, (
        'these modules swallow a failing toon_parser import and fall back to their '
        'own serialization: ' + ', '.join(offenders)
    )


# =============================================================================
# Round trip over the canonical pair — the values a hand-rolled writer lost
# =============================================================================


def test_canonical_pair_round_trips_the_hostile_payload():
    """None, a list, and separator-carrying strings survive write -> read."""
    payload = {
        'nothing': None,
        'names': ['alpha', 'beta'],
        'separator_laden': 'weird\tid,with:separators',
        'rows': [
            {'id': 'a\tb,c:d', 'label': 'plain'},
            {'id': 'plain', 'label': 'x,y'},
        ],
    }

    recovered = parse_toon(serialize_toon(payload))

    assert recovered['nothing'] is None
    assert recovered['names'] == ['alpha', 'beta']
    assert recovered['separator_laden'] == 'weird\tid,with:separators'
    assert recovered['rows'] == payload['rows']


def test_a_value_that_needs_no_quoting_round_trips_unquoted():
    """Matched negative: the quoting is applied where needed, not everywhere."""
    written = serialize_toon({'plain': 'jacoco'})

    assert written == 'plain: jacoco'
    assert parse_toon(written) == {'plain': 'jacoco'}


# =============================================================================
# Matched negative controls — the detectors flag what they claim to detect
# =============================================================================


_UNCANONICAL_EMITTER = '''
def emit_toon(payload):
    """Prints TOON by hand — exactly what the guard exists to catch."""
    print(f'status: {payload["status"]}')
    for row in payload['rows']:
        print(f'  {row["a"]},{row["b"]}')
'''

_CANONICAL_EMITTER = '''
from toon_parser import serialize_toon


def emit_toon(payload):
    """Prints TOON through the canonical serializer."""
    print(serialize_toon(payload))
'''

_SWALLOWING_MODULE = '''
try:
    from toon_parser import serialize_toon

    HAS_TOON_PARSER = True
except ImportError:
    HAS_TOON_PARSER = False


def serialize_toon_simple(data):
    return '\\n'.join(f'{k}: {v}' for k, v in data.items())
'''

_PROPAGATING_MODULE = '''
from toon_parser import serialize_toon


def emit(data):
    return serialize_toon(data)
'''

_PROBING_MODULE = '''
def cmd_self_test():
    """Records whether the canonical serializer imports; substitutes nothing."""
    try:
        from toon_parser import serialize_toon  # noqa: F401

        return ('import_toon_parser', True)
    except ImportError:
        return ('import_toon_parser', False)
'''


def _synthetic_script(root: Path, bundle: str, skill: str, name: str, source: str) -> Path:
    """Write a script into a synthetic tree shaped like the real script glob."""
    path = root / 'marketplace' / 'bundles' / bundle / 'skills' / skill / 'scripts' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding='utf-8')
    return path


def test_detector_flags_an_emitter_that_bypasses_the_serializer(tmp_path):
    """Control: the clean result above is a measurement, not a detector that never fires."""
    _synthetic_script(tmp_path, 'fixture-bundle', 'fixture-skill', 'hand_rolled.py', _UNCANONICAL_EMITTER)

    flagged = [
        record
        for record in derive_toon_population(tmp_path)
        if record.prints_to_stdout and not record.reaches_canonical
    ]

    assert [record.function for record in flagged] == ['emit_toon']


def test_detector_clears_an_emitter_that_uses_the_serializer(tmp_path):
    """Matched positive for the control above: a canonical emitter is not flagged."""
    _synthetic_script(tmp_path, 'fixture-bundle', 'fixture-skill', 'canonical.py', _CANONICAL_EMITTER)

    population = derive_toon_population(tmp_path)

    assert [record.function for record in population] == ['emit_toon']
    assert population[0].reaches_canonical is True


def test_detector_flags_a_swallowed_canonical_import():
    """Control for the propagation guard: the lookalike shape IS detected."""
    assert swallows_canonical_import(_SWALLOWING_MODULE) is True


def test_detector_clears_an_unguarded_canonical_import():
    """Matched positive: an import that may fail loudly is not flagged."""
    assert swallows_canonical_import(_PROPAGATING_MODULE) is False


def test_detector_clears_a_health_check_that_only_probes_the_import():
    """The substitute is the discriminator, not the swallow.

    A self-test that catches the ImportError to REPORT it installs no second
    implementation. Without this control the guard would read every health check
    in the tree as a lookalike and its clean result would mean nothing.
    """
    assert swallows_canonical_import(_PROBING_MODULE) is False


def test_an_added_emitter_is_picked_up_by_the_derivation(tmp_path):
    """Regression guard: the population grows when the tree does."""
    _synthetic_script(tmp_path, 'fixture-bundle', 'fixture-skill', 'first.py', _CANONICAL_EMITTER)
    before = derive_toon_population(tmp_path)

    _synthetic_script(tmp_path, 'fixture-bundle', 'other-skill', 'second.py', _CANONICAL_EMITTER)
    after = derive_toon_population(tmp_path)

    assert len(before) == 1
    assert len(after) == 2
    assert {record.path for record in after} - {record.path for record in before} == {
        'marketplace/bundles/fixture-bundle/skills/other-skill/scripts/second.py'
    }
