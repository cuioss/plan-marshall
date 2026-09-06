#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Population-derived TOON round-trip and single-implementation guard.

One format, several implementations that disagree, and no test comparing them —
this module is the test that compares them. It answers two questions over a
population it DERIVES from the tree at test time, never from a hand-typed list:

1. **Does every TOON emitter write through the canonical serializer?**
   Two derivations answer this, because either alone would leave a hole. The
   first is every function in ``marketplace/bundles/**/scripts`` whose NAME
   matches the TOON naming probe; an emitter is a member of that population that
   prints to stdout. Every emitter must reach ``serialize_toon`` / ``parse_toon``
   in its OWN body — file-level import presence is the wrong predicate, because a
   module can import the canonical serializer at the top and still hand-roll its
   own emission below it.

   Reaching the canonical name is necessary but not sufficient, for the same
   reason at one scope down: a body can call the serializer on one value and
   still ``print`` a TOON line it composed itself, so the symbol's presence would
   launder the hand-roll. A stdout ``print`` whose argument STARTS with a
   TOON-shaped literal is therefore an offence in its own right, whatever else
   the body calls — and the literal counts whether it is written into the
   ``print`` call or composed into a local one statement earlier, since the two
   emit the same bytes.

   The naming probe alone cannot substantiate a claim over *every* emitter: a
   function's name is precisely the property a new emitter is free to choose, so
   one named without the token would sit outside the population the guard reports
   its clean result over — absence read as coverage. The second derivation is
   therefore name-blind, selecting on BEHAVIOUR (a stdout ``print`` of a literal
   shaped like a TOON scalar line), and the two are cross-checked. What the
   cross-check asserts is that no name-blind emitter BYPASSES the canonical
   serializer while being invisible to the naming probe; a canonically-emitting
   function the probe happens to miss is not a defect, so the guard is over
   escaped offenders rather than over set equality.

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

- Every derivation publishes its size, the number of scripts it PARSED, and the
  set it could not parse. The name-derived population and its emitter subset are
  asserted non-zero — a property test over an empty population passes for the
  wrong reason. The name-blind derivation is asserted differently, because its
  selection IS the defect: an empty result there is the clean tree the plan was
  after, so what must be non-zero is the number of scripts scanned, and the proof
  that the detector fires at all lives in its fixture controls. The unreadable
  set is asserted empty either way, because a scan that quietly skipped a file
  reports the same clean result over a population that no longer covers the tree.
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
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from toon_parser import parse_toon, serialize_toon

from conftest import PROJECT_ROOT

#: The naming probe the emitter census used: ``def [a-z_]*toon[a-z_]*(``.
_TOON_NAME = re.compile(r'^[a-z_]*toon[a-z_]*$', re.IGNORECASE)

#: The canonical reader/writer names. A body that mentions either reaches the
#: single implementation; a body that mentions neither has its own.
_CANONICAL_NAMES = frozenset({'serialize_toon', 'parse_toon'})

#: The TOON scalar-line shape a hand-rolled emitter prints: a bare key, a colon,
#: then end-of-literal or a space. Used by the name-blind derivation, which does
#: not get to assume an emitter announced itself in its own name.
#:
#: Deliberately CASE-SENSITIVE: TOON keys are lower snake_case, whereas human
#: progress narration capitalises ("Target: claude", "Using context: ..."). Case
#: folding here made the probe match narration and report a progress line as an
#: un-canonical emitter — a guard that cries wolf is one its readers learn to
#: ignore, which costs more than the coverage the folding bought.
_TOON_LINE = re.compile(r'^[a-z_][a-z0-9_]*:(?: |$)')

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
    hand_rolls_toon: bool

    @property
    def bypasses_canonical(self) -> bool:
        """Whether this record emits TOON the canonical serializer never wrote.

        ``reaches_canonical`` cannot answer that on its own: it says only that
        ``serialize_toon``/``parse_toon`` appears SOMEWHERE in the body, so a
        function that hand-prints a TOON line and calls the serializer on some
        unrelated value satisfies it while emitting output the canonical writer
        never touched. A stdout ``print`` whose argument STARTS with a TOON-shaped
        literal is a hand-rolled emission whatever else the body calls, which is
        the ``hand_rolls_toon`` disjunct. The second disjunct keeps the weaker
        original signal for an emitter printing TOON in a shape the literal probe
        does not recognise — a bare separator-joined row, say — while referencing
        no canonical name at all.
        """
        return self.prints_to_stdout and (self.hand_rolls_toon or not self.reaches_canonical)


@dataclass(frozen=True)
class Derivation:
    """What a derivation found, over how much, and what it could not read.

    All three travel together because a hit count alone cannot say whether it is
    a result or an accident. ``scanned`` is the denominator — the number of
    scripts actually parsed — and ``unreadable`` is the coverage gap, so a size
    read off a population that silently shrank is distinguishable from one read
    off a complete walk. Every caller holding ``records`` holds both.

    The distinction matters most for a derivation whose selection IS the defect
    (``derive_name_blind_emitters``): its ``records`` are legitimately empty on a
    clean tree, so emptiness there is the goal rather than a vacuity signal, and
    ``scanned`` is what has to be non-zero for the result to mean anything.
    """

    records: list[EmitterRecord]
    unreadable: list[str]
    scanned: int


def _referenced_names(node: ast.AST) -> set[str]:
    """Every bare name and attribute name appearing anywhere under ``node``."""
    found: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            found.add(child.id)
        elif isinstance(child, ast.Attribute):
            found.add(child.attr)
    return found


def _is_provably_not_stdout(node: ast.expr) -> bool:
    """Whether a ``print(..., file=X)`` target provably writes somewhere else.

    Only ``sys.stderr`` — or a bare ``stderr`` imported from it — qualifies.
    ``file=sys.stdout`` and ``file=None`` BOTH write to stdout, so excluding
    every ``file=`` keyword put an emitter using either outside both derived
    populations. An unrecognised target is treated as stdout rather than dropped:
    a population predicate that fails open is one a future emitter evades by
    naming its stream, which is the hole this derivation exists to close.
    """
    if isinstance(node, ast.Attribute):
        return node.attr == 'stderr'
    if isinstance(node, ast.Name):
        return node.id == 'stderr'
    return False


def _stdout_print_calls(node: ast.AST) -> Iterator[ast.Call]:
    """Every ``print(...)`` call in the body that writes to stdout.

    A ``print(..., file=sys.stderr)`` is a diagnostic, not TOON emission, so it
    does not make its function an emitter. Without this discrimination the
    check-table row BUILDERS in the CI providers — which return dicts and warn on
    stderr — would be demanded to serialize output they never write. The
    discrimination is over the TARGET, never over the mere presence of a ``file=``
    keyword: see ``_is_provably_not_stdout``.
    """
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if not (isinstance(child.func, ast.Name) and child.func.id == 'print'):
            continue
        if any(
            keyword.arg == 'file' and _is_provably_not_stdout(keyword.value)
            for keyword in child.keywords
        ):
            continue
        yield child


def _prints_to_stdout(node: ast.AST) -> bool:
    """Whether the function body prints to stdout."""
    return next(_stdout_print_calls(node), None) is not None


def _leading_literal_text(node: ast.AST) -> str | None:
    """The literal text a printed expression begins with, if it begins with one.

    An f-string is handled by taking its leading literal segment, because that is
    where a hand-rolled emitter puts the key: ``print(f'status: {value}')``.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr) and node.values:
        head = node.values[0]
        if isinstance(head, ast.Constant) and isinstance(head.value, str):
            return head.value
    return None


def _local_literal_assignments(node: ast.AST) -> dict[str, list[str]]:
    """Map each name the body assigns a literal to onto the text(s) it was given.

    A hand-rolled emitter does not have to compose its line inside the ``print``
    call: ``line = f'status: {value}'`` followed by ``print(line)`` produces the
    same output through an ``ast.Name`` the literal probe cannot read. Resolving
    that one hop is what keeps the indirect form visible.

    Every literal ever assigned to a name is kept, not just the last, because the
    order two assignments execute in is not something this walk can decide. The
    fail-closed reading is the right one here: a name that EVER holds a TOON line
    is one whose ``print`` may emit it, and a predicate that guessed the other way
    would hand an emitter a trivial way to hide behind a re-assignment.

    Scope is deliberately one hop and no further — only ``name = <literal>``. This
    is not a dataflow engine, and widening it into one would buy coverage the two
    findings that motivated it never asked for.
    """
    assigned: dict[str, list[str]] = {}
    for child in ast.walk(node):
        if not isinstance(child, ast.Assign):
            continue
        text = _leading_literal_text(child.value)
        if text is None:
            continue
        for target in child.targets:
            if isinstance(target, ast.Name):
                assigned.setdefault(target.id, []).append(text)
    return assigned


def _printed_literal_texts(node: ast.expr, assigned: dict[str, list[str]]) -> list[str]:
    """The literal text(s) a printed argument can begin with.

    A direct literal contributes itself. A bare name contributes whatever literals
    the body assigned to it — and a name the body never assigned a literal to
    contributes NOTHING, which is what keeps this from degenerating into "any
    printed variable is a hand-roll".
    """
    text = _leading_literal_text(node)
    if text is not None:
        return [text]
    if isinstance(node, ast.Name):
        return assigned.get(node.id, [])
    return []


def _prints_toon_shaped_line(node: ast.AST) -> bool:
    """Whether the function prints a literal shaped like a TOON scalar line.

    The literal may be written into the ``print`` call or assigned to a local name
    first; both emit the same bytes, so both count. See
    ``_local_literal_assignments`` for the bound on that resolution.
    """
    assigned = _local_literal_assignments(node)
    for call in _stdout_print_calls(node):
        for arg in call.args:
            if any(_TOON_LINE.match(text) for text in _printed_literal_texts(arg, assigned)):
                return True
    return False


#: The two derivations below differ ONLY in which functions they select — by NAME
#: versus by BEHAVIOUR. That difference is the whole point of the cross-check, so
#: it is what stays per-derivation; the traversal, the parse-failure skip and the
#: record construction they shared are collapsed into ``_derive_emitters``.
_Selector = Callable[[ast.FunctionDef | ast.AsyncFunctionDef], bool]


def _derive_emitters(root: Path, selects: _Selector) -> Derivation:
    """Record every function in the marketplace script tree that ``selects`` accepts.

    A file that cannot be read or parsed is recorded in ``Derivation.unreadable``
    rather than dropped in silence: skipping it would shrink the population every
    downstream assertion reports its clean result over, without the result saying
    so.
    """
    records: list[EmitterRecord] = []
    unreadable: list[str] = []
    scanned = 0
    for path in sorted(root.glob(_SCRIPTS_GLOB)):
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        except (OSError, SyntaxError) as error:
            unreadable.append(f'{path.relative_to(root)}: {type(error).__name__}: {error}')
            continue
        scanned += 1
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not selects(node):
                continue
            records.append(
                EmitterRecord(
                    path=str(path.relative_to(root)),
                    function=node.name,
                    line=node.lineno,
                    prints_to_stdout=_prints_to_stdout(node),
                    reaches_canonical=bool(_referenced_names(node) & _CANONICAL_NAMES),
                    hand_rolls_toon=_prints_toon_shaped_line(node),
                )
            )
    return Derivation(records=records, unreadable=unreadable, scanned=scanned)


def derive_toon_population(root: Path) -> Derivation:
    """Enumerate the TOON-named functions across the marketplace script tree.

    Derived by walking the tree, so a component added tomorrow is in the
    population without anyone remembering to list it here.
    """
    return _derive_emitters(root, lambda node: bool(_TOON_NAME.match(node.name)))


def derive_name_blind_emitters(root: Path) -> Derivation:
    """Enumerate emitters by BEHAVIOUR rather than by name.

    ``derive_toon_population`` selects on the function NAME, which is the one
    property a newly-added emitter is entirely free to choose — so on its own it
    cannot substantiate the module docstring's claim over *every* emitter. This
    derivation selects on what a function actually prints: a literal shaped like
    a TOON scalar line, written to stdout. An emitter named without the probe's
    token is therefore still in a population, and the cross-check below is what
    turns the docstring's completeness claim into a derived result.
    """
    return _derive_emitters(root, _prints_toon_shaped_line)


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


#: Handler types broad enough to swallow a failing ``toon_parser`` import.
#: ``ImportError`` inherits from ``Exception``, which inherits from
#: ``BaseException``, so each of these genuinely catches the failure — and they
#: are the BROADEST handlers a module could route around the serializer with,
#: which is to say the ones the guard most needs to see rather than the ones it
#: can afford to miss. A bare ``except:`` is broader still and is recognised by
#: ``_catches_import_failure`` directly, since it names no type at all.
_IMPORT_CATCHING_HANDLERS = frozenset({'ImportError', 'Exception', 'BaseException'})


def _catches_import_failure(handler: ast.ExceptHandler) -> bool:
    """Whether this handler catches a failing canonical import.

    Recognising only a handler that NAMES ``ImportError`` read the narrowest form
    of the scenario as the whole of it: a bare ``except:`` names nothing and an
    ``except Exception:`` names a supertype, yet both swallow the same failure.
    """
    if handler.type is None:
        return True
    return bool(_referenced_names(handler.type) & _IMPORT_CATCHING_HANDLERS)


def swallows_canonical_import(source: str) -> bool:
    """Whether the module swallows a failing ``toon_parser`` import into a substitute.

    This is the lookalike-substitution shape: the canonical import is guarded by
    a handler broad enough to catch its failure (see ``_catches_import_failure``),
    the handler does NOT re-raise, and the module carries its own TOON writer to
    route around the loss with. Detected by that shape rather than by one flag
    name — a single flag name resolves to a single file and cannot establish a
    population.

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
            if not _catches_import_failure(handler):
                continue
            if not any(isinstance(stmt, ast.Raise) for stmt in ast.walk(handler)):
                return True
    return False


# =============================================================================
# The derived population — published, and asserted non-empty before it is used
# =============================================================================


def test_population_is_derived_and_non_empty(capsys):
    """Publish the derived size; a property over an empty population proves nothing.

    The unreadable set is published and asserted empty alongside the sizes. A
    scan that skipped a file it could not parse would report the same clean
    result over a smaller population, and nothing in that result would say so.
    """
    derivation = derive_toon_population(PROJECT_ROOT)
    emitters = [record for record in derivation.records if record.prints_to_stdout]

    with capsys.disabled():
        print(
            f'\nderived TOON population: {len(derivation.records)} function(s) '
            f'over {derivation.scanned} script(s), '
            f'{len(emitters)} of which emit to stdout; '
            f'{len(derivation.unreadable)} script(s) unreadable'
        )

    assert derivation.records, 'the derivation found no TOON-named functions at all'
    assert emitters, 'the derivation found no emitters — the guard below would be vacuous'
    assert not derivation.unreadable, (
        'these scripts could not be parsed, so the population above is smaller '
        'than the tree it claims to cover: ' + ', '.join(derivation.unreadable)
    )


def test_every_emitter_reaches_the_canonical_serializer():
    """No emitter writes TOON of its own.

    The failure message names each offender, because the remedy is per-function.
    """
    offenders = [
        f'{record.path}:{record.line} {record.function}'
        for record in derive_toon_population(PROJECT_ROOT).records
        if record.bypasses_canonical
    ]

    assert not offenders, (
        'these functions emit TOON without reaching the canonical serializer: '
        + ', '.join(offenders)
    )


def test_the_name_probe_misses_no_uncanonical_emitter(capsys):
    """The name-derived population is measured against a name-blind one.

    Without this the module's completeness claim would rest on the naming probe
    alone, and an emitter named without its token would be outside the population
    the guard above reports a clean result over — absence read as coverage. Here
    the two derivations are compared, so the claim is derived rather than
    asserted. Only an offender is a failure, and probe VISIBILITY is what clears
    one here: a hand-rolled emitter the naming probe does see is not escaping —
    the guard above already covers it — so the assertion is over the ESCAPED
    OFFENDERS, not over set equality.

    ``reaches_canonical`` is deliberately NOT a clearing clause. Selection here
    is the hand-roll itself (a stdout print of a TOON-shaped literal), and a
    body that hand-prints one line and serializes another still emitted output
    the canonical writer never wrote.

    Because selection is the defect, this derivation is a DETECTOR and an empty
    result over a clean tree is the goal, not a vacuity signal — asserting the
    population non-empty would demand the tree keep a hand-rolled emitter alive
    for the guard to point at. What must be non-zero for the result to mean
    anything is the DENOMINATOR: the number of scripts the walk actually parsed.
    That the detector fires at all is proved by its fixture controls below, over
    a synthetic tree, where it does not depend on the state of this one.
    """
    named = {
        (record.path, record.function)
        for record in derive_toon_population(PROJECT_ROOT).records
    }
    behavioural = derive_name_blind_emitters(PROJECT_ROOT)
    escaped = [
        f'{record.path}:{record.line} {record.function}'
        for record in behavioural.records
        if (record.path, record.function) not in named
    ]

    with capsys.disabled():
        print(
            f'\nname-blind emitter population: {len(behavioural.records)} function(s) '
            f'over {behavioural.scanned} script(s); '
            f'{len(escaped)} of them escape the naming probe uncanonically; '
            f'{len(behavioural.unreadable)} script(s) unreadable'
        )

    assert behavioural.scanned, (
        'the name-blind derivation parsed no scripts at all — the cross-check would be vacuous'
    )
    assert not behavioural.unreadable, (
        'these scripts could not be parsed, so the cross-check covers less of the '
        'tree than it claims: ' + ', '.join(behavioural.unreadable)
    )
    assert not escaped, (
        'these functions print TOON-shaped output without reaching the canonical '
        'serializer AND are invisible to the naming probe: ' + ', '.join(escaped)
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

_PARTIAL_HAND_ROLL = '''
from toon_parser import serialize_toon


def emit_toon(payload):
    """Hand-prints one TOON line, then serializes the rest — still a hand-roll."""
    print(f'status: {payload["status"]}')
    print(serialize_toon(payload))
'''

#: The same hand-roll, composed one statement earlier. Reading only the direct
#: arguments of the ``print`` call saw an ``ast.Name`` here and nothing else.
_ASSIGNED_LINE_HAND_ROLL = '''
def emit_toon(payload):
    """Composes the TOON line into a local, then prints the local."""
    line = f'status: {payload["status"]}'
    print(line)
'''

#: The same again, with the name re-assigned. Which assignment reaches the
#: ``print`` is not something a walk can decide, so the fail-closed reading — any
#: literal the name ever holds counts — is the one that does not hand an emitter a
#: one-line way to hide.
_REASSIGNED_LINE_HAND_ROLL = '''
def emit_toon(payload):
    """Assigns twice; one of the two is a TOON line."""
    line = 'starting'
    line = f'status: {payload["status"]}'
    print(line)
'''

#: Matched negative: a local carrying a literal that is NOT TOON-shaped. The
#: resolution reads the assigned text and judges it, rather than treating the
#: indirection itself as the offence.
_ASSIGNED_NON_TOON_LINE = '''
def emit_toon(payload):
    """Prints a local holding ordinary narration."""
    line = f'processing {payload["name"]}'
    print(line)
'''

#: Matched negative: a printed name the body never assigns a literal to. Nothing
#: is known about it, and "not known" must not read as "hand-rolled" — otherwise
#: the resolution would flag every function that prints a variable.
_PRINTS_AN_UNASSIGNED_NAME = '''
from toon_parser import serialize_toon


def emit_toon(payload):
    """Prints a parameter and the canonical serializer's output."""
    print(payload)
    print(serialize_toon(payload))
'''

#: A file the AST parser cannot read. Its ``def`` is deliberately unterminated so
#: the failure is a ``SyntaxError`` rather than anything importable.
_UNPARSEABLE_SCRIPT = '''
def emit_toon(payload:
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

#: The swallowing shape behind a BARE handler. It names no exception type at all,
#: which is the broadest catch Python has, so the narrow ``ImportError``-by-name
#: reading skipped it while it swallowed exactly the failure the guard is about.
_BARE_EXCEPT_SWALLOWING_MODULE = '''
try:
    from toon_parser import serialize_toon

    HAS_TOON_PARSER = True
except:  # noqa: E722
    HAS_TOON_PARSER = False


def serialize_toon_simple(data):
    return '\\n'.join(f'{k}: {v}' for k, v in data.items())
'''

#: The swallowing shape behind ``except Exception:``. ``ImportError`` is a
#: subclass, so this catches the failed import as surely as naming it would.
_BROAD_EXCEPT_SWALLOWING_MODULE = '''
try:
    from toon_parser import serialize_toon

    HAS_TOON_PARSER = True
except Exception:
    HAS_TOON_PARSER = False


def serialize_toon_simple(data):
    return '\\n'.join(f'{k}: {v}' for k, v in data.items())
'''

#: The probing module's sibling under the widened handler set: it catches the
#: broadest thing there is and still installs no substitute. This is the fixture
#: that keeps the widening from quietly turning every health check into a
#: lookalike — the substitute remains the discriminator, not the swallow.
_BROAD_EXCEPT_PROBING_MODULE = '''
def cmd_self_test():
    """Records whether the canonical serializer imports; substitutes nothing."""
    try:
        from toon_parser import serialize_toon  # noqa: F401

        return ('import_toon_parser', True)
    except Exception:
        return ('import_toon_parser', False)
'''

#: A module that DOES carry a substitute writer, but whose guarded import catches
#: something that cannot be the import failing. The widening added supertypes of
#: ``ImportError``, not every handler, and this fixture is what says so.
_UNRELATED_HANDLER_MODULE = '''
try:
    from toon_parser import serialize_toon

    HAS_TOON_PARSER = True
except ValueError:
    HAS_TOON_PARSER = False


def serialize_toon_simple(data):
    return '\\n'.join(f'{k}: {v}' for k, v in data.items())
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
        record for record in derive_toon_population(tmp_path).records if record.bypasses_canonical
    ]

    assert [record.function for record in flagged] == ['emit_toon']


def test_detector_flags_a_hand_roll_that_also_calls_the_serializer(tmp_path):
    """A serializer call elsewhere in the body does not launder a hand-printed line.

    This is the hole ``reaches_canonical`` left open on its own: the symbol is
    present, so the weaker predicate cleared the function while it still printed
    a TOON line the canonical writer never produced.
    """
    _synthetic_script(
        tmp_path, 'fixture-bundle', 'fixture-skill', 'partial.py', _PARTIAL_HAND_ROLL
    )

    population = derive_toon_population(tmp_path).records

    assert [record.function for record in population] == ['emit_toon']
    assert population[0].reaches_canonical is True
    assert population[0].bypasses_canonical is True


def test_detector_clears_an_emitter_that_uses_the_serializer(tmp_path):
    """Matched positive for the control above: a canonical emitter is not flagged."""
    _synthetic_script(tmp_path, 'fixture-bundle', 'fixture-skill', 'canonical.py', _CANONICAL_EMITTER)

    population = derive_toon_population(tmp_path).records

    assert [record.function for record in population] == ['emit_toon']
    assert population[0].reaches_canonical is True
    assert population[0].bypasses_canonical is False


def test_detector_flags_a_hand_roll_composed_into_a_local(tmp_path):
    """Control: composing the line one statement earlier is still a hand-roll.

    The literal probe read only the direct arguments of the ``print`` call, so an
    ``ast.Name`` produced no text and the hand-roll went unseen — which let
    ``bypasses_canonical`` fall back to ``not reaches_canonical``, the exact
    laundering the ``hand_rolls_toon`` disjunct exists to stop.
    """
    _synthetic_script(
        tmp_path, 'fixture-bundle', 'fixture-skill', 'assigned.py', _ASSIGNED_LINE_HAND_ROLL
    )

    population = derive_toon_population(tmp_path).records

    assert [record.function for record in population] == ['emit_toon']
    assert population[0].hand_rolls_toon is True
    assert population[0].bypasses_canonical is True


def test_detector_flags_a_local_that_ever_holds_a_toon_line(tmp_path):
    """A re-assignment does not clear the name: the fail-closed reading wins."""
    _synthetic_script(
        tmp_path, 'fixture-bundle', 'fixture-skill', 'reassigned.py', _REASSIGNED_LINE_HAND_ROLL
    )

    population = derive_toon_population(tmp_path).records

    assert [record.function for record in population] == ['emit_toon']
    assert population[0].hand_rolls_toon is True


def test_detector_clears_a_local_that_is_not_toon_shaped(tmp_path):
    """Matched negative: the assigned TEXT is judged, not the indirection."""
    _synthetic_script(
        tmp_path, 'fixture-bundle', 'fixture-skill', 'narration.py', _ASSIGNED_NON_TOON_LINE
    )

    population = derive_toon_population(tmp_path).records

    assert [record.function for record in population] == ['emit_toon']
    assert population[0].hand_rolls_toon is False


def test_detector_clears_a_printed_name_it_knows_nothing_about(tmp_path):
    """Matched negative: an unresolved name contributes no text, so it flags nothing.

    Without this the resolution could degenerate into "any printed variable is a
    hand-roll", which would flag every canonical emitter that prints a value.
    """
    _synthetic_script(
        tmp_path, 'fixture-bundle', 'fixture-skill', 'unassigned.py', _PRINTS_AN_UNASSIGNED_NAME
    )

    population = derive_toon_population(tmp_path).records

    assert [record.function for record in population] == ['emit_toon']
    assert population[0].hand_rolls_toon is False
    assert population[0].bypasses_canonical is False


def test_derivation_publishes_a_script_it_cannot_parse(tmp_path):
    """Control for the coverage claim: an unparseable file is reported, not skipped.

    Without this the population would shrink by one and every assertion over it
    would keep reporting a clean result — over a tree it no longer covered.
    """
    _synthetic_script(tmp_path, 'fixture-bundle', 'fixture-skill', 'broken.py', _UNPARSEABLE_SCRIPT)
    _synthetic_script(tmp_path, 'fixture-bundle', 'fixture-skill', 'canonical.py', _CANONICAL_EMITTER)

    derivation = derive_toon_population(tmp_path)

    assert [record.function for record in derivation.records] == ['emit_toon']
    assert derivation.scanned == 1, 'the broken file must be excluded from the denominator'
    assert len(derivation.unreadable) == 1
    assert derivation.unreadable[0].startswith(
        'marketplace/bundles/fixture-bundle/skills/fixture-skill/scripts/broken.py: SyntaxError'
    )


def test_derivation_reports_nothing_unreadable_for_a_parseable_tree(tmp_path):
    """Matched positive: the unreadable set is a measurement, not a constant."""
    _synthetic_script(tmp_path, 'fixture-bundle', 'fixture-skill', 'canonical.py', _CANONICAL_EMITTER)

    derivation = derive_toon_population(tmp_path)

    assert derivation.unreadable == []
    assert derivation.scanned == 1


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


def test_detector_flags_a_swallow_behind_a_bare_handler():
    """A bare ``except:`` names nothing and catches everything, this failure included.

    Recognising only a handler that NAMED ``ImportError`` read the narrowest form
    of the scenario as the whole of it, and let the broadest form through.
    """
    assert swallows_canonical_import(_BARE_EXCEPT_SWALLOWING_MODULE) is True


def test_detector_flags_a_swallow_behind_a_broad_handler():
    """``except Exception:`` catches ``ImportError`` by inheritance, so it swallows too."""
    assert swallows_canonical_import(_BROAD_EXCEPT_SWALLOWING_MODULE) is True


def test_detector_clears_a_broad_handler_that_installs_no_substitute():
    """Matched negative for the widening: the substitute is still the discriminator.

    This is the ``_PROBING_MODULE`` control's sibling under the widened handler
    set. Without it the widening could start reporting every health check that
    catches broadly as a second implementation, and the guard's clean result would
    stop meaning anything.
    """
    assert swallows_canonical_import(_BROAD_EXCEPT_PROBING_MODULE) is False


def test_detector_clears_a_substitute_behind_an_unrelated_handler():
    """Matched negative: the handler set grew to ``ImportError``'s supertypes, not to all.

    The module carries a substitute writer, so only the handler type clears it. A
    widening that had dropped the type check altogether would flag this.
    """
    assert swallows_canonical_import(_UNRELATED_HANDLER_MODULE) is False


_UNNAMED_UNCANONICAL_EMITTER = '''
def write_summary(payload):
    """Prints TOON by hand under a name the naming probe cannot see."""
    print(f'status: {payload["status"]}')
'''

#: The partial hand-roll, under a name the probe cannot see. It reaches the
#: canonical serializer AND hand-prints a TOON line, which is precisely the
#: combination the old ``reaches_canonical`` clause cleared; it must now escape.
_UNNAMED_PARTIAL_HAND_ROLL = '''
from toon_parser import serialize_toon


def write_summary(payload):
    """Hand-prints a TOON line under an unprobed name, then serializes the rest."""
    print(f'status: {payload["status"]}')
    print(serialize_toon(payload))
'''

#: The indirect hand-roll under a name the probe cannot see. This is the second
#: consequence of reading only direct ``print`` arguments: the same predicate is
#: ``derive_name_blind_emitters``'s SELECTOR, so an emitter missed by both the
#: naming probe and the literal probe landed in neither population.
_UNNAMED_ASSIGNED_LINE_HAND_ROLL = '''
def write_summary(payload):
    """Composes a TOON line into a local under an unprobed name, then prints it."""
    line = f'status: {payload["status"]}'
    print(line)
'''

#: Matched negative for the selector widening: an unprobed name printing a local
#: that is not TOON-shaped stays out of the name-blind population entirely.
_UNNAMED_ASSIGNED_NON_TOON_LINE = '''
def write_summary(payload):
    """Prints a local holding ordinary narration, under an unprobed name."""
    line = f'processing {payload["name"]}'
    print(line)
'''

#: The matched positive for the cross-check. Selection is the hand-roll itself,
#: so a cleared member cannot be one that hand-rolls "acceptably" — the only
#: honest clearing route left is probe VISIBILITY, which is what this fixture
#: exercises: it enters the name-blind population and is then cleared because the
#: naming probe already sees it, so the primary guard owns it.
_PROBED_HAND_ROLLED_EMITTER = '''
def emit_toon(payload):
    """Hand-prints TOON under a name the naming probe DOES see."""
    print(f'status: {payload["status"]}')
'''

_STDERR_DIAGNOSTIC = '''
import sys


def write_summary(payload):
    """Writes a TOON-shaped diagnostic to stderr — not emission."""
    print(f'status: {payload["status"]}', file=sys.stderr)
'''

_EXPLICIT_STDOUT_EMITTER = '''
import sys


def write_summary(payload):
    """Names its stream explicitly — file=sys.stdout is still stdout."""
    print(f'status: {payload["status"]}', file=sys.stdout)
'''

_NONE_FILE_EMITTER = '''
def write_summary(payload):
    """file=None is the default stream, which is stdout."""
    print(f'status: {payload["status"]}', file=None)
'''


def test_name_blind_derivation_flags_an_emitter_the_naming_probe_misses(tmp_path):
    """Control: the cross-check above is a measurement, not a detector that never fires."""
    _synthetic_script(
        tmp_path, 'fixture-bundle', 'fixture-skill', 'unnamed.py', _UNNAMED_UNCANONICAL_EMITTER
    )

    named = {(record.path, record.function) for record in derive_toon_population(tmp_path).records}
    escaped = [
        record.function
        for record in derive_name_blind_emitters(tmp_path).records
        if (record.path, record.function) not in named
    ]

    assert named == set(), 'the naming probe is expected to miss this function entirely'
    assert escaped == ['write_summary']


def test_name_blind_derivation_flags_an_unprobed_partial_hand_roll(tmp_path):
    """A serializer call in the body no longer clears an unprobed hand-roll.

    This fixture held the opposite role while ``reaches_canonical`` was a
    clearing clause; it is now a negative control, because the line it prints by
    hand is output the canonical writer never produced.
    """
    _synthetic_script(
        tmp_path, 'fixture-bundle', 'fixture-skill', 'unnamed_partial.py', _UNNAMED_PARTIAL_HAND_ROLL
    )

    named = {(record.path, record.function) for record in derive_toon_population(tmp_path).records}
    behavioural = derive_name_blind_emitters(tmp_path).records
    escaped = [
        record.function
        for record in behavioural
        if (record.path, record.function) not in named
    ]

    assert named == set(), 'the naming probe is expected to miss this function entirely'
    assert [record.reaches_canonical for record in behavioural] == [True]
    assert escaped == ['write_summary']


def test_name_blind_derivation_selects_an_indirect_hand_roll(tmp_path):
    """The selector reads composed lines too, so both probes can no longer miss one.

    ``derive_name_blind_emitters`` selects on ``_prints_toon_shaped_line``, so
    every hole in that predicate is a hole in the population as well as in
    ``hand_rolls_toon``. An emitter whose NAME the probe also misses used to land
    in neither.
    """
    _synthetic_script(
        tmp_path,
        'fixture-bundle',
        'fixture-skill',
        'unnamed_assigned.py',
        _UNNAMED_ASSIGNED_LINE_HAND_ROLL,
    )

    named = {(record.path, record.function) for record in derive_toon_population(tmp_path).records}
    escaped = [
        record.function
        for record in derive_name_blind_emitters(tmp_path).records
        if (record.path, record.function) not in named
    ]

    assert named == set(), 'the naming probe is expected to miss this function entirely'
    assert escaped == ['write_summary']


def test_name_blind_derivation_ignores_an_indirect_narration_line(tmp_path):
    """Matched negative: resolving the local did not make every printed local an emitter."""
    _synthetic_script(
        tmp_path,
        'fixture-bundle',
        'fixture-skill',
        'unnamed_narration.py',
        _UNNAMED_ASSIGNED_NON_TOON_LINE,
    )

    assert derive_name_blind_emitters(tmp_path).records == []


def test_name_blind_derivation_clears_an_emitter_the_naming_probe_sees(tmp_path):
    """Matched positive: an unprobed NAME is the defect here, not the hand-roll.

    The strengthened predicate makes selection and hand-rolling the same event,
    so a cleared member cannot be one that hand-rolls acceptably. What this
    cross-check discriminates on is probe VISIBILITY: an emitter the naming probe
    already sees belongs to the guard above, not to the escapee list. The fixture
    therefore ENTERS the name-blind population and is then cleared — asserting
    membership first is what stops the test passing on absence, the way the
    absent-literal case would.
    """
    _synthetic_script(
        tmp_path, 'fixture-bundle', 'fixture-skill', 'probed.py', _PROBED_HAND_ROLLED_EMITTER
    )

    named = {(record.path, record.function) for record in derive_toon_population(tmp_path).records}
    behavioural = derive_name_blind_emitters(tmp_path).records
    escaped = [
        record.function
        for record in behavioural
        if (record.path, record.function) not in named
    ]

    assert [record.function for record in behavioural] == ['emit_toon']
    assert named != set(), 'the naming probe is expected to see this function'
    assert escaped == []


def test_name_blind_derivation_ignores_a_stderr_diagnostic(tmp_path):
    """Matched negative: stderr is diagnostics, so it must not enter the population."""
    _synthetic_script(
        tmp_path, 'fixture-bundle', 'fixture-skill', 'diagnostic.py', _STDERR_DIAGNOSTIC
    )

    assert derive_name_blind_emitters(tmp_path).records == []


def test_name_blind_derivation_selects_an_explicit_stdout_target(tmp_path):
    """``file=sys.stdout`` writes to stdout, so it must not be excluded as a diagnostic.

    Matched positive for the stderr control above: the exclusion is over the
    TARGET, so naming the default stream explicitly cannot buy an emitter its way
    out of the population.
    """
    _synthetic_script(
        tmp_path, 'fixture-bundle', 'fixture-skill', 'explicit.py', _EXPLICIT_STDOUT_EMITTER
    )

    assert [
        record.function for record in derive_name_blind_emitters(tmp_path).records
    ] == ['write_summary']


def test_name_blind_derivation_selects_a_none_file_target(tmp_path):
    """``file=None`` is the default stream, so it must not be excluded either."""
    _synthetic_script(
        tmp_path, 'fixture-bundle', 'fixture-skill', 'none_file.py', _NONE_FILE_EMITTER
    )

    assert [
        record.function for record in derive_name_blind_emitters(tmp_path).records
    ] == ['write_summary']


def test_an_added_emitter_is_picked_up_by_the_derivation(tmp_path):
    """Regression guard: the population grows when the tree does."""
    _synthetic_script(tmp_path, 'fixture-bundle', 'fixture-skill', 'first.py', _CANONICAL_EMITTER)
    before = derive_toon_population(tmp_path).records

    _synthetic_script(tmp_path, 'fixture-bundle', 'other-skill', 'second.py', _CANONICAL_EMITTER)
    after = derive_toon_population(tmp_path).records

    assert len(before) == 1
    assert len(after) == 2
    assert {record.path for record in after} - {record.path for record in before} == {
        'marketplace/bundles/fixture-bundle/skills/other-skill/scripts/second.py'
    }
