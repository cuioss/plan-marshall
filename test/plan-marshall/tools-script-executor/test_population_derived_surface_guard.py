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

This test removes the hand in "hand-built". It derives the surface for EVERY
registered notation (the real population — flagless roots, deep verb trees,
alias groupings, and all), then asserts the validator accepts each notation's
``--help``, ``-h``, and declared-flag invocations. The corpus IS the derived
population, so a surface shape the fixtures never supplied is covered by
construction, and a derivation that drops an attribute fails a test here instead
of shipping.

**Why it catches a derivation strip, not just a validator bug.** The IN-MEMORY
:class:`~argparse_surface.ScriptSurface` is the ground truth for what to
exercise (its verb paths and declared flags), while the SERIALIZED
``surface.to_dict()`` — the exact shape the generator embeds — is what the
validator judges against. The two come from the same derivation but through
different code paths, so a serializer that drops ``children`` or ``flags``
leaves the truth still exercising a verb path or a flag the installed surface no
longer carries, and the validator's refusal of that now-valid call fails the
test.

**Tiering.** This drives a real ``--help`` derivation over the whole registry,
so it is marked ``slow_live`` exactly as
``test_argparse_surface.py::...::test_every_registered_notation_is_confident_or_explicitly_not_derivable``
is — registered in ``pyproject.toml`` (the single marker registry), collected by
default in CI's ``verify`` and deselectable in a fast local loop with
``-m 'not slow_live'``. The corpus is NOT sampled: sampling a population-derived
test is a hand-built fixture with extra steps. The derivation shares the on-disk
help cache (``.plan/temp/plugin-doctor-help-cache/``, same ``content_hash`` key)
with the sibling ``slow_live`` characterization, so whichever runs second reads a
warm cache rather than re-probing.
"""

from pathlib import Path

import argparse_surface as surf
import pytest

# The validator lives in the executor TEMPLATE; load it as a module via the
# established helper (renders the template with an empty SCRIPT_SURFACES, which
# this test overrides with the real derived index below).
from test_execute_script import load_executor_module

from conftest import PROJECT_ROOT

# COUPLED TO pyproject.toml's ``timeout = 300`` pytest-timeout hang detector.
# This is a TRUE TOTAL wall-clock deadline for the whole derivation batch, so it
# is this test's declared runtime ceiling and must stay comfortably BELOW 300 or
# the hang detector fires on a healthy cold run. It mirrors the sibling
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
        pytest.fail(
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
    import ast

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


def _walk_surface(node: surf.ParserNode, chain: list[str]):
    """Yield ``(chain, node)`` for the in-memory node and every descendant.

    ``chain`` is the positional path from the root to ``node`` (empty for the
    root). Walking the IN-MEMORY :class:`~argparse_surface.ParserNode` — not the
    serialized dict — is what makes a ``to_dict`` strip visible: the truth keeps
    exercising a verb path the installed (serialized) surface may have dropped.
    """
    yield chain, node
    for name, child in node.children.items():
        yield from _walk_surface(child, [*chain, name])


@pytest.mark.slow_live
def test_pre_spawn_validator_accepts_help_and_declared_flags_across_the_derived_population():
    """Every registered notation's ``--help``, ``-h``, and declared-flag calls are accepted.

    Population-derived: the corpus is the real derived surface index, not a
    literal list, so it fails the moment the derivation drops an attribute a real
    surface carries (a verb path, a flag) — which four hand-built rounds could
    not do. The enumerated population size is published in the assertion messages
    and on stdout.
    """
    executor = _live_executor()
    notations = _registered_notations(executor)
    assert notations, (
        f'the executor at {executor} registers no notations — the population '
        'this guard grades is empty, so a pass here would certify nothing'
    )

    config = surf.DerivationConfig(total_budget_seconds=_DERIVATION_BUDGET_SECONDS)
    index = surf.build_surface_index(notations, executor, config=config)
    derivable = {n: r for n, r in index.items() if surf.is_derivable(r)}

    # Floor the derivable population so a derivation collapse (a budget too tight,
    # a broken probe) surfaces as a visible number rather than a vacuous green
    # over a shrunken corpus. Matches the sibling characterization's floor.
    assert len(derivable) >= len(notations) // 2, (
        f'fewer than half the registered notations yielded a derivable surface — '
        f'population={len(notations)} derivable={len(derivable)}; the corpus this '
        'guard grades has collapsed'
    )

    validator = load_executor_module()
    # Install the SERIALIZED surfaces — the exact shape the generator embeds —
    # while the loop below walks the IN-MEMORY surfaces for the truth. A
    # serializer that drops an attribute therefore diverges the two, and the
    # validator's refusal of a call the truth built is caught below.
    validator.SCRIPT_SURFACES = {
        notation: {'digest': 'live-population', 'surface': result.to_dict()}
        for notation, result in derivable.items()
    }

    help_checks = 0
    flag_invocation_checks = 0
    refusals: list[tuple[str, list[str], dict]] = []

    for notation, result in derivable.items():
        for chain, node in _walk_surface(result.root, []):
            # argparse fires its help action in BOTH spellings at whatever depth
            # the token appears, so the validator must let each through — even on
            # a flagless leaf carrying required flags, the exact shape that
            # refused ``-h`` live.
            for spelling in ('--help', '-h'):
                argv = [*chain, spelling]
                rejection = validator._validate_invocation(notation, argv)
                help_checks += 1
                if rejection is not None:
                    refusals.append((notation, argv, rejection))

            # A declared-flag invocation: every long flag the node's OWN surface
            # declares, provided together so no required flag is reported missing.
            # A validator that refuses a flag the derived surface carries — or a
            # serializer that dropped the flag so the surface no longer carries it
            # — fails here.
            declared = sorted(node.flags)
            if declared:
                argv = [*chain, *(f'--{flag}' for flag in declared)]
                rejection = validator._validate_invocation(notation, argv)
                flag_invocation_checks += 1
                if rejection is not None:
                    refusals.append((notation, argv, rejection))

    # Publish the enumerated population size and the check counts.
    print(
        f'surface-guard population: registered={len(notations)} '
        f'derivable={len(derivable)} help_checks={help_checks} '
        f'flag_invocation_checks={flag_invocation_checks}'
    )

    assert not refusals, (
        f'the pre-spawn validator refused {len(refusals)} valid invocation(s) built '
        f'from a script\'s OWN derived surface, over a population of {len(derivable)} '
        f'derivable notations. Each refusal is a valid call the executor would reject '
        f'before spawning:\n  '
        + '\n  '.join(f'{notation} {argv} -> {rejection}' for notation, argv, rejection in refusals[:12])
    )
