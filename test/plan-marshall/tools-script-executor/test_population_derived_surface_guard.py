#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Population-derived surface guard.

The pre-spawn validator embedded in the generated executor rejects an invalid
invocation against a DERIVED argparse surface. Four defects in that validator
shipped past a green synthetic suite — every one a valid call refused (``--help``
refused on a flagless surface, ``-h`` refused, a leading top-level flag
desyncing the walk) — and every one was caught only by running the validator
LIVE against the real derived surfaces. The suite missed them for one structural
reason: every hand-built fixture is written to be representative, and therefore
POPULATED, so the whole class *"the validator mishandles a surface where an
attribute is ABSENT"* is invisible — the absent-attribute surface is one nobody
would hand-write.

This module removes the hand in "hand-built". It derives the surface for EVERY
registered notation (the real population — flagless roots, deep verb trees,
alias groupings, and all) and drives the validator against it. The corpus IS the
derived population, so a surface shape the fixtures never supplied is covered by
construction.

Two checks, two populations, deliberately separate
--------------------------------------------------
The two invocation classes this module drives are NOT the same kind of check,
and reporting them as one number said they were:

* **The help short-circuit** (``--help`` / ``-h`` at every verb depth) is a
  REGRESSION NET, not a derivation check. ``_validate_invocation`` calls
  ``_mentions_help(script_args)`` and returns ``None`` before it reads a single
  node attribute, so no derivation defect can make one of these calls fail.
  What CAN make them fail is the removal of that short-circuit — which is
  exactly the defect that shipped twice (``-h`` refused; ``--help`` refused on a
  flagless surface carrying required flags). The net is kept for that, and named
  for that.
* **The declared-flag invocations** are the derivation check: each is built from
  a node's OWN in-memory flag set and judged against the SERIALIZED surface, so
  a serializer that drops an attribute diverges the two and the validator's
  refusal of a now-valid call is the failure.

Each class is its own test with its own count, so a collapse in one is not
hidden by the volume of the other.

**Recorded proposal, deliberately NOT taken here.** The alternative remedy is to
route the help spellings through a surface-consulting path so that the majority
of the corpus grades the derivation rather than the short-circuit. It is not
taken in this change for a reason that has to be settled before it can land: the
short-circuit exists because argparse fires its help action at whatever depth the
token appears, so a surface-consulting help path would have to model that, and
any place it models it imperfectly is a VALID call refused — the one outcome the
validator's fail-open design rules out. Landing it therefore needs a triage pass
over whatever fail-open behaviour it surfaces first. Choosing between the two
mid-run is what this note exists to prevent.

**Why a serializer strip is visible at all.** The IN-MEMORY
:class:`~argparse_surface.ScriptSurface` is the ground truth for what to exercise
(its verb paths and declared flags), while the SERIALIZED ``surface.to_dict()``
— the exact shape the generator embeds — is what the validator judges against.
The two come from the same derivation but through different code paths.

Which attribute strips this module can see, and which it cannot
---------------------------------------------------------------
:class:`~argparse_surface.ParserNode` serializes SEVEN attributes. This module
reddens on TWO of them. The claim used to be that "a derivation that drops an
attribute fails a test here"; it is narrowed to what the checks can actually
observe, and the five it cannot are listed with the reason each is invisible —
so nobody reads this guard as covering a strip it never grades.

Reddens:

* ``children`` — the walk stops descending, the leaf's flags never join the
  accept-set, and the declared-flag invocation is refused ``unknown_flag``.
* ``flags`` — the node's own flags are absent from the accept-set, and the same
  invocation is refused ``unknown_flag``.

Does NOT redden, and why:

* ``required_flags`` — its only effect is to ADD a ``missing_required_flag``
  rejection. Dropping it can only make the validator more permissive, and this
  module fails on refusals, never on acceptances.
* ``flag_arity`` — consulted only to decide how many argv tokens a flag binds.
  Every invocation built here is all-flags, so the next token is always
  ``-``-prefixed or absent and ``_consume_flag_value`` returns a confident ``0``
  without reaching the arity map at all.
* ``alias_of`` — read only to PHRASE the corrective on an ``unknown_verb``
  rejection. No invocation built here names an unregistered verb, so that branch
  never runs.
* ``flags_confident`` — read with ``.get('flags_confident', True)``. A dropped
  key therefore reads as ``True``, which turns validation ON where it may have
  been off; the effect is a stricter validator, never a refused-valid-call this
  module can catch.
* ``children_confident`` — same defaulting, same direction: ``.get(...,
  True)`` makes a dropped key read as confident, which resumes verb-path
  validation rather than suppressing it.

Published population
--------------------
The registered-notation count rides the session report header
(``GUARD_POPULATION_LABEL`` / ``GUARD_POPULATION_SIZE`` below, rendered by the
root conftest's ``pytest_report_header``), so a corpus that quietly shrank is
visible on the GREEN run. It replaces a bare ``print``, which published nothing:
this repository's ``addopts`` carry neither ``-s`` nor ``-rA``, so a passing
test's stdout is captured and discarded, and under the ``-n auto`` xdist run the
canonical build performs, even a capture-suspended write is swallowed at the
worker boundary. The header is rendered by the CONTROLLER before collection and
is the one channel a pass surfaces.

⛔ **Stated rather than left implied**: the two per-run check counts do NOT ride
that channel and cannot. They are products of the live derivation the tests
themselves perform, and the header is written before any test runs. Each count
is asserted non-zero by its own test and carried in that test's messages; the
header carries the registered-notation population that BOUNDS both.

**Tiering.** These drive a real ``--help`` derivation over the whole registry, so
they are marked ``slow_live`` exactly as
``test_argparse_surface.py::...::test_every_registered_notation_is_confident_or_explicitly_not_derivable``
is — registered in ``pyproject.toml`` (the single marker registry), collected by
default in CI's ``verify`` and deselectable in a fast local loop with
``-m 'not slow_live'``. The corpus is NOT sampled: sampling a population-derived
test is a hand-built fixture with extra steps. The derivation shares the on-disk
help cache (``.plan/temp/plugin-doctor-help-cache/``, same ``content_hash`` key)
with the sibling ``slow_live`` characterization, so whichever runs second reads a
warm cache rather than re-probing. Both tests here share ONE module-scoped
derivation and are pinned to a single xdist worker so the batch runs once.
"""

import ast
from collections.abc import Iterator
from pathlib import Path

import argparse_surface as surf
import pytest

from conftest import PROJECT_ROOT

# COUPLED TO pyproject.toml's ``timeout = 300`` pytest-timeout hang detector.
# This is a TRUE TOTAL wall-clock deadline for the whole derivation batch, so it
# is this module's declared runtime ceiling and must stay comfortably BELOW 300
# or the hang detector fires on a healthy cold run. It mirrors the sibling
# ``slow_live`` characterization's budget for the same reason.
_DERIVATION_BUDGET_SECONDS = 240.0


def _live_executor() -> Path:
    """Resolve the live ``.plan/execute-script.py`` the root conftest bootstraps.

    Its absence is a real failure rather than a reason to skip: the population
    this guard grades is read from that executor's registry, so with no executor
    there is nothing to grade and a skip would certify nothing.
    """
    executor = surf.resolve_executor(PROJECT_ROOT)
    if executor is None:
        raise AssertionError(
            f'no .plan/execute-script.py under {PROJECT_ROOT} — the root conftest '
            'bootstraps it, so its absence is a real failure rather than a reason '
            'to skip this population-derived guard'
        )
    return executor


def _registered_notations(executor: Path) -> list[str]:
    """Read the notation keys out of the live executor's ``SCRIPTS`` literal.

    Parsed with :mod:`ast` from the generated file rather than imported — the
    executor is a script whose import would run its bootstrap — mirroring
    ``test_argparse_surface.py::_registered_notations``. ``ast.literal_eval``
    rejects a non-literal assignment loudly rather than yielding a partial read,
    so a reformatted registry cannot silently shrink the population.
    """
    source = executor.read_text(encoding='utf-8')
    for node in ast.parse(source).body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == 'SCRIPTS':
                mapping = ast.literal_eval(node.value)
                assert isinstance(mapping, dict), (
                    f'SCRIPTS in {executor} is no longer a dict literal (parsed a '
                    f'{type(mapping).__name__}) — the population this guard grades changed shape'
                )
                return sorted(mapping)
    raise AssertionError(
        f'no module-level SCRIPTS literal in {executor} — the registry this guard '
        'derives its population from is unreadable, so a green run would grade nothing'
    )


#: The registered population, read at IMPORT so the report header can publish it
#: before any test runs. Cheap by construction: an ``ast`` read of one generated
#: file, with no ``--help`` probe and no subprocess.
_REGISTERED_NOTATIONS: list[str] = _registered_notations(_live_executor())

# Non-emptiness asserted at IMPORT — an empty registry would let every sweep
# below iterate nothing and report clean.
assert _REGISTERED_NOTATIONS, (
    'the live executor registers no notation, so the corpus this guard grades is '
    'empty and a pass here would certify nothing'
)

#: Published on EVERY run — passing included — by the root conftest's
#: ``pytest_report_header``. See the module docstring's "Published population"
#: section for why this channel and not a ``print``, and for what it does and
#: does not carry.
GUARD_POPULATION_LABEL = 'pre-spawn validator registered notations'
GUARD_POPULATION_SIZE = len(_REGISTERED_NOTATIONS)


def _walk_surface(node: surf.ParserNode, chain: list[str]) -> Iterator[tuple[list[str], surf.ParserNode]]:
    """Yield ``(chain, node)`` for the in-memory node and every descendant.

    ``chain`` is the positional path from the root to ``node`` (empty for the
    root). Walking the IN-MEMORY :class:`~argparse_surface.ParserNode` — not the
    serialized dict — is what makes a ``to_dict`` strip visible: the truth keeps
    exercising a verb path the installed (serialized) surface may have dropped.
    """
    yield chain, node
    for name, child in node.children.items():
        yield from _walk_surface(child, [*chain, name])


@pytest.fixture(scope='module')
def live_validator():
    """The validator, loaded with the REAL derived surfaces installed.

    Module-scoped so the derivation batch runs once for both tests rather than
    twice. Yields ``(validator_module, derivable)`` — the second is the
    notation -> in-memory surface mapping the tests walk for ground truth.

    The derivable floor is asserted HERE rather than in either test: it is a
    precondition of both, and a collapsed corpus must fail them together rather
    than letting one of them report a clean sweep over a shrunken population.
    """
    # Imported inside the fixture, not at module scope. The root conftest's
    # ``pytest_report_header`` executes this module before collection to read
    # GUARD_POPULATION_SIZE, and at that point pytest has not yet put this
    # test directory on sys.path — so a module-level ``test_execute_script``
    # import would make the header report this publisher UNAVAILABLE on every
    # run.
    from test_execute_script import load_executor_module

    executor = _live_executor()
    config = surf.DerivationConfig(total_budget_seconds=_DERIVATION_BUDGET_SECONDS)
    index = surf.build_surface_index(_REGISTERED_NOTATIONS, executor, config=config)
    derivable = {n: r for n, r in index.items() if surf.is_derivable(r)}

    # Floor the derivable population so a derivation collapse (a budget too tight,
    # a broken probe) surfaces as a visible number rather than a vacuous green
    # over a shrunken corpus. Matches the sibling characterization's floor.
    assert len(derivable) >= len(_REGISTERED_NOTATIONS) // 2, (
        f'fewer than half the registered notations yielded a derivable surface — '
        f'population={len(_REGISTERED_NOTATIONS)} derivable={len(derivable)}; the '
        'corpus this guard grades has collapsed'
    )

    validator = load_executor_module()
    # Install the SERIALIZED surfaces — the exact shape the generator embeds —
    # while the tests walk the IN-MEMORY surfaces for the truth. A serializer
    # that drops an attribute therefore diverges the two, and the validator's
    # refusal of a call the truth built is caught.
    validator.SCRIPT_SURFACES = {
        notation: {'digest': 'live-population', 'surface': result.to_dict()} for notation, result in derivable.items()
    }
    yield validator, derivable


@pytest.mark.slow_live
@pytest.mark.xdist_group(name='live_surface_derivation')
def test_the_help_short_circuit_survives_at_every_verb_depth(live_validator):
    """``--help`` and ``-h`` are accepted at every node of every derived surface.

    A REGRESSION NET over ``_validate_invocation``'s help short-circuit, not a
    derivation check — and named for what it is. The short-circuit runs before
    any node attribute is read, so no serializer strip and no derivation gap can
    reach this assertion; what it catches is the removal or narrowing of the
    short-circuit itself, which shipped twice (``-h`` refused outright; ``--help``
    refused on a flagless leaf carrying required flags). Both spellings are driven
    at every depth because argparse fires its help action wherever the token
    appears.

    Its count is reported separately from the declared-flag sweep's, so the
    volume of these checks cannot make that one look larger than it is.
    """
    validator, derivable = live_validator

    help_checks = 0
    refusals: list[tuple[str, list[str], dict]] = []

    for notation, result in derivable.items():
        for chain, _node in _walk_surface(result.root, []):
            for spelling in ('--help', '-h'):
                argv = [*chain, spelling]
                rejection = validator._validate_invocation(notation, argv)
                help_checks += 1
                if rejection is not None:
                    refusals.append((notation, argv, rejection))

    assert help_checks > 0, (
        f'no help invocation was built at all over {len(derivable)} derivable '
        'notation(s) — the regression net swept nothing'
    )
    assert not refusals, (
        f'the pre-spawn validator refused {len(refusals)} of {help_checks} help '
        f'invocation(s) over {len(derivable)} derivable notation(s). argparse fires '
        f'its help action at whatever depth the token appears, so every one of these '
        f'is a call the executor would reject before spawning:\n  '
        + '\n  '.join(f'{notation} {argv} -> {rejection}' for notation, argv, rejection in refusals[:12])
    )


@pytest.mark.slow_live
@pytest.mark.xdist_group(name='live_surface_derivation')
def test_the_validator_accepts_every_flag_the_derived_surface_declares(live_validator):
    """Each node's OWN declared flags are accepted at that node's verb path.

    This is the derivation check. Every invocation is built from the IN-MEMORY
    node's flag set and judged against the SERIALIZED surface, so a serializer
    that drops ``children`` (the walk stops descending and the leaf's flags never
    join the accept-set) or ``flags`` (the node's flags are absent from it)
    turns a valid call into an ``unknown_flag`` refusal here. The module
    docstring lists the five attributes this cannot see, and why.

    All of a node's long flags are supplied together so no required flag is
    reported missing — a ``missing_required_flag`` rejection would be a defect in
    the invocation, not in the validator.
    """
    validator, derivable = live_validator

    flag_invocation_checks = 0
    refusals: list[tuple[str, list[str], dict]] = []

    for notation, result in derivable.items():
        for chain, node in _walk_surface(result.root, []):
            declared = sorted(node.flags)
            if not declared:
                continue
            argv = [*chain, *(f'--{flag}' for flag in declared)]
            rejection = validator._validate_invocation(notation, argv)
            flag_invocation_checks += 1
            if rejection is not None:
                refusals.append((notation, argv, rejection))

    assert flag_invocation_checks > 0, (
        f'no node across {len(derivable)} derivable notation(s) declared a single '
        'long flag, so this sweep graded nothing — the derivation, not the '
        'validator, is what failed'
    )
    assert not refusals, (
        f'the pre-spawn validator refused {len(refusals)} of {flag_invocation_checks} '
        f"invocation(s) built from a script's OWN derived surface, over a population "
        f'of {len(derivable)} derivable notations (registered: '
        f'{len(_REGISTERED_NOTATIONS)}). Each refusal is a valid call the executor '
        f'would reject before spawning:\n  '
        + '\n  '.join(f'{notation} {argv} -> {rejection}' for notation, argv, rejection in refusals[:12])
    )
