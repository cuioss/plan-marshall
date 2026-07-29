#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""The phase-5 leaf's runnable build slice must be NON-EMPTY.

This module asserts the **user-visible property the plan exists to restore**,
which is deliberately a different verification scope from D1's co-located unit
tests: those assert the arithmetic at each individual seam, this one asserts
that the set of canonicals a phase-5 leaf may run inline is not empty.

The distinction matters because the defect was invisible at every individual
seam. Each seam was locally correct — the floor clamp made the stamp truthful,
the ceiling comparison was right, the tier derivation matched its own
documentation — yet their COMPOSITION produced a leaf that could run nothing at
all. `execution_tier` was keyed on the FLOORED `bash_timeout_seconds`, so
pyproject's over-provisioned 600 s outer floor put every pyprojectx canonical at
`600 + 30 = 630`, past the 600 s harness ceiling, before any measurement was
consulted. Every pyprojectx canonical therefore tiered `orchestrator`, and the
630 the leaf was told to pass on its Bash call was itself un-passable.

Everything below is driven through the REAL production chain —
``_classify_build_executable`` -> ``_lookup_bash_timeout`` ->
``_compute_execution_tier_fields`` -> the composer's
``_stamp_phase_5_step_execution_tier`` — against an isolated run-config sandbox.
No hand-authored resolve-shaped fixture appears anywhere: a hand-built fixture
is exactly what let the four-field contract drift away from its consumer
unnoticed, and it would let this suite keep passing against a broken producer.

Four cases:

(a) A cheap MEASURED pyprojectx canonical stamps ``per_task`` and carries a
    ``bash_timeout_seconds`` at or below ``HARNESS_BASH_CEILING_SECONDS``, so
    the leaf can actually pass it. **This case is RED against pre-fix code**
    (pre-fix it stamped ``orchestrator`` at 630).
(b) An UNMEASURED canonical stamps ``orchestrator`` for EVERY registered
    engine — the fail-closed guard. The engine set is derived by iterating
    ``_arch_build._BUILD_CONFIG_LOCATIONS`` rather than hand-listed, so a fifth
    engine cannot escape the guard by omission.
(c) A genuinely slow MEASURED canonical still stamps ``orchestrator``.
(d) ``bash_timeout_seconds`` remains the floored bound in every case above,
    re-asserting the stamp-truthfulness invariant from this end of the chain.

The runnable slice is asserted as a SET property — at least one canonical
resolves ``per_task`` — rather than by pinning a particular canonical name, so
the case states the restored CAPABILITY instead of today's incidental values.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import run_config

from conftest import load_script_module

from _build_execute_factory import compute_command_key
from _build_shared import DEFAULT_BUILD_TIMEOUT, get_bash_timeout

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-execution-manifest'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None, f'Failed to load module spec for {filename}'
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_mem = _load_module('_mem_runnable_slice', 'manage-execution-manifest.py')
_core = _load_module('_core_runnable_slice', '_manifest_core.py')

_arch_build = load_script_module(
    'plan-marshall',
    'manage-architecture',
    '_cmd_client_build.py',
    '_arch_client_build_runnable_slice',
)

_stamp = _mem._stamp_phase_5_step_execution_tier


@pytest.fixture(autouse=True)
def _clear_arch_resolve_cache():
    """Reset the compose-scoped memos so each case exercises its own stub."""
    _mem._invoke_architecture_resolve_cached.cache_clear()
    _mem._manifest_validation._domain_appended_canonicals.cache_clear()
    yield
    _mem._invoke_architecture_resolve_cached.cache_clear()
    _mem._manifest_validation._domain_appended_canonicals.cache_clear()


# ---------------------------------------------------------------------------
# Canonical executables, in the exact Bucket B shape ``architecture resolve``
# emits. Fed to the production classifier rather than decomposed by hand.
# ---------------------------------------------------------------------------

_PYPROJECT_EXECUTOR = 'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build'


def _pyproject_executable(command_args: str) -> str:
    return f'{_PYPROJECT_EXECUTOR} run --command-args "{command_args}"'


# The real learned durations observed on this repo at the time the defect was
# diagnosed. They are SEEDED into the sandbox below rather than read from the
# live run-configuration.json — a case that read the real store would silently
# change meaning as the project's builds get faster or slower.
_CHEAP_CANONICAL_ARGS = 'compile plan-marshall'
_CHEAP_OBSERVED_SECONDS = 120

_SLOW_CANONICAL_ARGS = 'coverage'
_SLOW_OBSERVED_SECONDS = 1897


def _production_fields(executable: str) -> dict[str, Any]:
    """Run the full production producer chain for a resolved executable."""
    classified = _arch_build._classify_build_executable(executable)
    assert classified is not None, 'production classifier rejected a real resolved executable'
    tool_name, command_args = classified
    lookup = _arch_build._lookup_bash_timeout(tool_name, command_args, '.')
    assert lookup is not None, 'production timeout lookup returned nothing'
    stamp, measured = lookup
    fields: dict[str, Any] = _arch_build._compute_execution_tier_fields(stamp, measured)
    return fields


def _seed(command_args: str, observed_seconds: int) -> None:
    """Persist an observed duration through the PRODUCTION writer.

    The autouse ``_plan_base_dir_sandbox`` fixture redirects the run-config
    store into a per-test tmp sandbox, so this never touches the real learned
    durations and an unseeded key genuinely reads as unmeasured.
    """
    config = _arch_build._load_build_config('python')
    assert config is not None, 'production build config did not load'
    run_config.timeout_set(compute_command_key(config, command_args), observed_seconds)


def _expected_floored_stamp(tool_name: str, command_args: str) -> int:
    """Recompute the floored bound from the production primitives.

    Deliberately re-derived from ``timeout_get`` + the engine's declared
    ``min_timeout`` rather than hard-coded, so case (d) pins the ARITHMETIC and
    not a snapshot of today's numbers.
    """
    config = _arch_build._load_build_config(tool_name)
    assert config is not None
    command_key = compute_command_key(config, command_args)
    inner = max(run_config.timeout_get(command_key, DEFAULT_BUILD_TIMEOUT), config.min_timeout)
    return get_bash_timeout(inner)


def _stamp_through_composer(monkeypatch, plan_id: str, step_id: str, fields: dict[str, Any]) -> str:
    """Drive the composer's stamping pass with a production-derived resolve TOON.

    The TOON is serialized from the fields the production producers emitted, so
    the composer consumes exactly the envelope ``architecture resolve`` would
    have handed it — the subprocess is stubbed, the CONTRACT is not.
    """
    toon: str = _core.serialize_toon({'status': 'success', **fields})
    monkeypatch.setattr(_mem, '_resolve_executor', lambda: Path('/dev/null'))
    monkeypatch.setattr(
        _mem.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=0, stdout=toon)
    )
    records = _stamp(plan_id, [step_id])
    assert records[0]['step_id'] == step_id
    tier: str = records[0]['tier']
    return tier


# ---------------------------------------------------------------------------
# Case (a) — THE restored capability: a cheap measured canonical is runnable
#            inside a phase-5 leaf.
# ---------------------------------------------------------------------------


def test_cheap_measured_canonical_is_runnable_in_a_phase_5_leaf(monkeypatch):
    """A cheap MEASURED pyprojectx canonical stamps per_task AND is passable.

    Both halves are load-bearing and neither implies the other:

    * ``per_task`` is what admits the step into the leaf's runnable slice.
    * ``bash_timeout_seconds <= HARNESS_BASH_CEILING_SECONDS`` is what makes the
      instruction the leaf receives FOLLOWABLE. The pre-fix code got this wrong
      in a way a tier-only assertion would have missed: it told the leaf to pass
      630 s on a call the host caps at 600 s.

    RED against pre-fix code: with ``PYTEST_OUTER_FLOOR_SECONDS = 600`` the
    stamp was 630 and the tier ``orchestrator``, so both assertions failed.
    """
    _seed(_CHEAP_CANONICAL_ARGS, _CHEAP_OBSERVED_SECONDS)
    fields = _production_fields(_pyproject_executable(_CHEAP_CANONICAL_ARGS))

    assert fields['execution_tier'] == 'per_task', (
        'a cheap measured canonical must be runnable inside a phase-5 leaf, got '
        f'{fields["execution_tier"]} at stamp={fields["bash_timeout_seconds"]}'
    )
    assert fields['bash_timeout_seconds'] <= _arch_build.HARNESS_BASH_CEILING_SECONDS, (
        'the leaf is instructed to pass bash_timeout_seconds on its Bash call, so a '
        'per_task stamp above the harness ceiling is an unfollowable instruction'
    )
    assert fields['exceeds_bash_ceiling'] is False

    # ...and the verdict survives the composer's stamping pass unchanged.
    tier = _stamp_through_composer(monkeypatch, 'runnable-slice-cheap', 'verify:compile', fields)
    assert tier == 'per_task'


def test_the_leafs_runnable_slice_is_non_empty(monkeypatch):
    """At least ONE canonical resolves per_task — asserted as a SET property.

    Stated as "the slice is non-empty" rather than "``compile`` is per_task" on
    purpose: the plan exists to restore a CAPABILITY, and pinning one canonical
    name would let the capability regress the moment that particular canonical's
    learned duration moved, while a differently-named cheap canonical still
    carried it. The set formulation fails only when the slice is genuinely
    empty — which is precisely the defect.
    """
    _seed(_CHEAP_CANONICAL_ARGS, _CHEAP_OBSERVED_SECONDS)
    _seed(_SLOW_CANONICAL_ARGS, _SLOW_OBSERVED_SECONDS)

    tiers = {
        args: _production_fields(_pyproject_executable(args))['execution_tier']
        for args in (_CHEAP_CANONICAL_ARGS, _SLOW_CANONICAL_ARGS)
    }
    runnable = {args for args, tier in tiers.items() if tier == 'per_task'}

    assert runnable, (
        'the phase-5 leaf runnable slice is EMPTY — every measured canonical '
        f'resolved orchestrator: {tiers}'
    )


# ---------------------------------------------------------------------------
# Case (b) — the fail-closed guard, population-derived over the engine registry.
# ---------------------------------------------------------------------------


def test_unmeasured_canonical_fails_closed_for_every_registered_engine():
    """An UNMEASURED canonical stamps orchestrator on every engine the loader knows.

    The engine set is derived by iterating ``_BUILD_CONFIG_LOCATIONS`` — the
    loader's own registry — and the notation is looked up from
    ``_BUILD_NOTATIONS``, so a fifth engine added tomorrow is covered
    automatically instead of escaping this guard by not being hand-listed.

    Nothing is seeded here: the sandbox is empty, so every key genuinely reads
    as unmeasured through the production lookup rather than via a stubbed flag.
    """
    notation_by_tool = {tool: notation for notation, tool in _arch_build._BUILD_NOTATIONS.items()}
    registered = sorted(_arch_build._BUILD_CONFIG_LOCATIONS)
    assert registered, 'the engine registry must not be empty'

    tiers = {}
    for tool_name in registered:
        notation = notation_by_tool.get(tool_name)
        assert notation is not None, (
            f'{tool_name} is registered in _BUILD_CONFIG_LOCATIONS but has no '
            'entry in _BUILD_NOTATIONS — the two registries have drifted'
        )
        executable = f'python3 .plan/execute-script.py {notation} run --command-args "verify"'
        fields = _production_fields(executable)
        tiers[tool_name] = fields['execution_tier']

    assert tiers == dict.fromkeys(registered, 'orchestrator'), (
        f'an unmeasured canonical must fail closed on EVERY engine: {tiers}'
    )


# ---------------------------------------------------------------------------
# Case (c) — a genuinely slow measured canonical still hands off.
# ---------------------------------------------------------------------------


def test_slow_measured_canonical_still_stamps_orchestrator(monkeypatch):
    """The fix must not make a genuinely long build runnable in-leaf.

    The complement of case (a), and the reason the floor correction alone would
    have been unsafe: lowering the floor must widen the runnable slice only for
    builds that genuinely fit. A canonical measured at ~1897 s is far past the
    ceiling on its own learned value, with the floor entirely inert.
    """
    _seed(_SLOW_CANONICAL_ARGS, _SLOW_OBSERVED_SECONDS)
    fields = _production_fields(_pyproject_executable(_SLOW_CANONICAL_ARGS))

    assert fields['bash_timeout_seconds'] > _arch_build.HARNESS_BASH_CEILING_SECONDS
    assert fields['exceeds_bash_ceiling'] is True
    assert fields['execution_tier'] == 'orchestrator'

    tier = _stamp_through_composer(monkeypatch, 'runnable-slice-slow', 'verify:coverage', fields)
    assert tier == 'orchestrator'


# ---------------------------------------------------------------------------
# Case (d) — the stamp is still the floored bound, from this end of the chain.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('command_args', 'observed_seconds'),
    [
        (_CHEAP_CANONICAL_ARGS, _CHEAP_OBSERVED_SECONDS),
        (_SLOW_CANONICAL_ARGS, _SLOW_OBSERVED_SECONDS),
        (_CHEAP_CANONICAL_ARGS, None),
    ],
    ids=['cheap-measured', 'slow-measured', 'unmeasured'],
)
def test_bash_timeout_seconds_is_the_floored_bound_in_every_case(command_args, observed_seconds):
    """``bash_timeout_seconds`` stays ``get_bash_timeout(max(learned, floor))`` throughout.

    Re-asserts the stamp-truthfulness invariant from the composition end rather
    than at the lookup seam. Keeping it here is what stops a future change from
    "fixing" the runnable slice by shrinking the stamp below what the run
    actually measures against — the tier moved off the floor, but the STAMP is
    still the floored bound, and the two must not be conflated again.

    The unmeasured row is included deliberately: the fail-closed rule changes
    that row's TIER, and this case pins that it leaves its STAMP alone.
    """
    if observed_seconds is not None:
        _seed(command_args, observed_seconds)

    fields = _production_fields(_pyproject_executable(command_args))

    assert fields['bash_timeout_seconds'] == _expected_floored_stamp('python', command_args)
