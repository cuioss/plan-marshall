#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Cross-engine regression coverage for build-timeout truthfulness.

Three end-to-end properties, each asserted for EVERY one of the four build
engine configs so no engine is covered by omission. Each property is the
user-visible complement of a defect this plan fixed, driven through a public
seam rather than re-implementing the resolution logic:

1. **A passing near-learned-value build never reports ``timeout``.** A build
   whose real duration sits just under the persisted learned value must
   resolve to ``status: success`` with a ``timeout_used_seconds`` at least the
   floored bound. (Red when the engine floor is dropped: the bound collapses
   to the tool-agnostic ``MIN_TIMEOUT`` and a slow-but-passing build is killed
   and mis-reported as a timeout.)
2. **An explicit ``--timeout`` binds end-to-end.** Driving the factory
   ``cmd_run`` in-process leg with an explicit ``--timeout`` far above a
   SEEDED persisted value must put the explicit bound on the subprocess.
   (Red before deliverable 1: ``timeout_get`` discarded the caller's bound
   whenever any persisted value existed, and the argparse default made an
   explicit value indistinguishable from an unsupplied flag.)
3. **Each engine carries its floor, and the resolve stamp agrees with the
   run.** ``_lookup_bash_timeout``'s stamp must equal
   ``get_bash_timeout(max(learned, config.min_timeout))`` — the same floored
   value ``execute_direct_base`` measures against — and the derived
   ``execution_tier`` / ``exceeds_bash_ceiling`` verdict must follow that
   floored stamp rather than the raw learned value. (Red before deliverable 2:
   the stamp omitted the floor, under-reporting the bound and mis-tiering an
   orchestrator-tier command as ``per_task``.)

The engine list itself is the coverage guarantee: every case is parameterised
over :data:`_ENGINES`, so adding a fifth engine without a declared floor fails
the parity case rather than passing by omission.

``_build_execute.py`` and ``_cmd_client_build.py`` are the two seams this
module drives; neither is modified here.
"""

from __future__ import annotations

import json
import sys
import tempfile
from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest

from conftest import load_script_module

from _build_execute import execute_direct_base
from _build_shared import DEFAULT_BUILD_TIMEOUT, OUTER_TIMEOUT_BUFFER, get_bash_timeout
from _build_execute_factory import compute_command_key

# Sibling test modules install a ``MagicMock`` under ``sys.modules['run_config']``
# so their engine-config assertions never touch real persisted state. These
# regression cases assert the OPPOSITE — the resolution the production path
# actually performs against a real ``run-configuration.json`` — so the genuine
# module is loaded here under a private name and re-bound per test (see
# ``_isolate_run_config``). Without this, a mocked ``timeout_get`` would return
# a canned value and every "the learned value resolves to X" claim below would
# pass vacuously, depending only on collection order.
_real_run_config = load_script_module(
    'plan-marshall', 'manage-run-config', 'run_config.py', '_real_run_config_for_truthfulness'
)

_arch_build = load_script_module(
    'plan-marshall', 'manage-architecture', '_cmd_client_build.py', '_cmd_client_build'
)
_lookup_bash_timeout = _arch_build._lookup_bash_timeout
_compute_execution_tier_fields = _arch_build._compute_execution_tier_fields
_load_build_config = _arch_build._load_build_config
HARNESS_BASH_CEILING_SECONDS = _arch_build.HARNESS_BASH_CEILING_SECONDS


# ---------------------------------------------------------------------------
# The engine list — the coverage guarantee for all three properties.
#
# ``expected_floor`` is asserted as a LITERAL rather than as an equality
# against ``DEFAULT_BUILD_TIMEOUT``: the Maven / Gradle / npm floor coincides
# with that constant today, so an equality assertion would keep passing
# vacuously if the constant later moved.
# ---------------------------------------------------------------------------

_ENGINES = [
    ('maven', 'build-maven', '_maven_execute.py', 300),
    ('gradle', 'build-gradle', '_gradle_execute.py', 300),
    ('npm', 'build-npm', '_npm_execute.py', 300),
    ('python', 'build-pyproject', '_pyproject_execute.py', 600),
]

_ENGINE_IDS = [row[0] for row in _ENGINES]


def _engine_module(skill: str, script_file: str, module_name: str):
    """Load a build engine's ``_*_execute`` module through the shared loader."""
    return load_script_module('plan-marshall', skill, script_file, module_name)


def _engine_config(tool_name: str):
    """Return the engine's live ``ExecuteConfig`` via the architecture loader.

    Using ``_load_build_config`` — the loader the resolve stamp itself uses —
    rather than importing each engine module keeps property 3's parity claim
    honest: the config under assertion is the one the stamp actually reads.
    """
    config = _load_build_config(tool_name)
    assert config is not None, f'{tool_name} build config failed to load'
    return config


def _isolate_run_config(tmp_path, monkeypatch, entries: dict[str, int]) -> None:
    """Point run-configuration.json at ``tmp_path`` with the given persisted values.

    ``entries`` maps a canonical command key to its persisted
    ``timeout_seconds``. An empty mapping models an UNMEASURED command (the
    file exists but carries no entry), so ``timeout_get`` echoes the caller's
    default.
    """
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setenv('PLAN_DIR_NAME', '.plan')
    import file_ops

    monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
    # Re-bind BOTH consumers to the genuine module: ``_build_execute`` bound
    # ``timeout_get`` at import time, while ``_lookup_bash_timeout`` imports it
    # lazily from ``sys.modules`` on every call.
    monkeypatch.setitem(sys.modules, 'run_config', _real_run_config)
    monkeypatch.setattr('_build_execute.timeout_get', _real_run_config.timeout_get)
    config = {
        'version': 1,
        'commands': {key: {'timeout_seconds': value} for key, value in entries.items()},
    }
    (tmp_path / 'run-configuration.json').write_text(json.dumps(config))


def _build_command_fn(wrapper, args, log_file):
    """Predictable command construction for the direct-seam property."""
    return [wrapper, *args.split()], f'{wrapper} {args}'


# ---------------------------------------------------------------------------
# Structural guard — the engine list must stay in sync with the loader's own
# registry, so a newly-added engine cannot be silently omitted from all three
# properties below.
# ---------------------------------------------------------------------------


def test_engine_list_covers_every_registered_build_tool():
    """Every tool the architecture loader knows about MUST appear in _ENGINES."""
    registered = set(_arch_build._BUILD_CONFIG_LOCATIONS)
    covered = {row[0] for row in _ENGINES}
    assert covered == registered, (
        f'Engine coverage drifted — registered={sorted(registered)}, '
        f'covered={sorted(covered)}. A build engine added without a row here '
        'would escape all three truthfulness properties.'
    )


@pytest.mark.parametrize(('tool_name', 'skill', 'script_file', 'expected_floor'), _ENGINES, ids=_ENGINE_IDS)
def test_every_engine_declares_its_floor_explicitly(tool_name, skill, script_file, expected_floor):
    """No engine may inherit the dataclass ``MIN_TIMEOUT`` default silently."""
    config = _engine_config(tool_name)
    assert config.min_timeout == expected_floor, (
        f'{tool_name} must declare min_timeout={expected_floor}, got '
        f'{config.min_timeout}'
    )


# ---------------------------------------------------------------------------
# Property 1 — a passing near-learned-value build never reports ``timeout``.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(('tool_name', 'skill', 'script_file', 'expected_floor'), _ENGINES, ids=_ENGINE_IDS)
def test_passing_near_learned_value_build_reports_success_not_timeout(
    tool_name, skill, script_file, expected_floor
):
    """A build finishing just under the learned value resolves to success.

    The bound the subprocess is measured against must be at least the floored
    value — never the bare learned value and never the tool-agnostic floor.
    """
    config = _engine_config(tool_name)
    learned = 400
    expected_bound = max(learned, config.min_timeout)

    with tempfile.TemporaryDirectory() as tmpdir:
        with (
            patch('_build_execute.create_log_file', return_value='/tmp/regression.log'),
            patch('_build_execute.timeout_get', return_value=learned),
            patch('_build_execute.timeout_set'),
            patch('_build_execute.subprocess.run', return_value=MagicMock(returncode=0)),
            patch('builtins.open', MagicMock()),
        ):
            result = execute_direct_base(
                args='verify',
                command_key=f'{tool_name}:verify',
                default_timeout=config.default_timeout,
                project_dir=tmpdir,
                tool_name=config.tool_name,
                build_command_fn=_build_command_fn,
                wrapper=config.system_fallback,
                capture_strategy=config.capture_strategy,
                min_timeout=config.min_timeout,
            )

    assert result['status'] == 'success', (
        f'{tool_name}: a build finishing under its bound must not report '
        f'{result["status"]!r}'
    )
    assert result['timeout_used_seconds'] == expected_bound, (
        f'{tool_name}: the consumed bound must be max(learned={learned}, '
        f'floor={config.min_timeout}) = {expected_bound}, got '
        f'{result["timeout_used_seconds"]}'
    )
    assert result['timeout_used_seconds'] >= config.min_timeout


# ---------------------------------------------------------------------------
# Property 2 — an explicit ``--timeout`` binds end-to-end through cmd_run.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(('tool_name', 'skill', 'script_file', 'expected_floor'), _ENGINES, ids=_ENGINE_IDS)
def test_explicit_timeout_binds_end_to_end_through_cmd_run(
    tool_name, skill, script_file, expected_floor, tmp_path, monkeypatch
):
    """An explicit ``--timeout`` above a SEEDED persisted value reaches the subprocess.

    Driven through the factory ``cmd_run`` in-process leg with a REAL
    ``run-configuration.json`` carrying a learned value for the very key the
    invocation resolves to — the exact shape that discarded the caller's bound
    before deliverable 1.
    """
    module = _engine_module(skill, script_file, f'_{tool_name}_truthfulness_execute')
    config = module._CONFIG
    command_args = 'verify'
    command_key = compute_command_key(config, command_args)
    explicit = 1800

    # Persisted 240 resolves to 240 * 1.25 = 300 on the learned path — far
    # below the explicit request, so a discarded override is unmistakable.
    _isolate_run_config(tmp_path, monkeypatch, {command_key: 240})

    args = Namespace(
        command_args=command_args,
        project_dir=str(tmp_path),
        timeout=explicit,
        execution_mode='in_process',
        format='toon',
        mode='actionable',
        plan_id=None,
    )

    with (
        patch('_build_execute.create_log_file', return_value=str(tmp_path / 'build.log')),
        patch('_build_execute.timeout_set'),
        patch('_build_execute.subprocess.run', return_value=MagicMock(returncode=0)) as mock_run,
    ):
        module.cmd_run(args)

    assert mock_run.call_args is not None, f'{tool_name}: the in-process leg never ran'
    assert mock_run.call_args[1]['timeout'] == explicit, (
        f'{tool_name}: the explicit --timeout {explicit} must bind end-to-end; '
        f'the subprocess was bounded by {mock_run.call_args[1]["timeout"]} '
        'instead — a learned value discarded the caller\'s override'
    )


@pytest.mark.parametrize(('tool_name', 'skill', 'script_file', 'expected_floor'), _ENGINES, ids=_ENGINE_IDS)
def test_below_floor_explicit_timeout_still_resolves_up_to_the_engine_floor(
    tool_name, skill, script_file, expected_floor, tmp_path, monkeypatch
):
    """The override wins over the learned value but never waives the floor.

    An explicit request below the engine's declared floor resolves UP to the
    floor — the floor protects against under-specification.
    """
    module = _engine_module(skill, script_file, f'_{tool_name}_truthfulness_execute')
    config = module._CONFIG
    command_args = 'verify'
    command_key = compute_command_key(config, command_args)

    _isolate_run_config(tmp_path, monkeypatch, {command_key: 240})

    args = Namespace(
        command_args=command_args,
        project_dir=str(tmp_path),
        timeout=120,
        execution_mode='in_process',
        format='toon',
        mode='actionable',
        plan_id=None,
    )

    with (
        patch('_build_execute.create_log_file', return_value=str(tmp_path / 'build.log')),
        patch('_build_execute.timeout_set'),
        patch('_build_execute.subprocess.run', return_value=MagicMock(returncode=0)) as mock_run,
    ):
        module.cmd_run(args)

    assert mock_run.call_args[1]['timeout'] == config.min_timeout, (
        f'{tool_name}: an explicit --timeout 120 below the declared floor '
        f'{config.min_timeout} must resolve UP to the floor, got '
        f'{mock_run.call_args[1]["timeout"]}'
    )


# ---------------------------------------------------------------------------
# Property 3 — the resolve stamp agrees with the run, and the derived tier
# follows the FLOORED value.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(('tool_name', 'skill', 'script_file', 'expected_floor'), _ENGINES, ids=_ENGINE_IDS)
def test_resolve_stamp_equals_the_floored_bound_the_run_measures_against(
    tool_name, skill, script_file, expected_floor, tmp_path, monkeypatch
):
    """Parity: the stamp and the run are computed from ONE floored value.

    Defect C was exactly this divergence — the stamp omitted the
    ``config.min_timeout`` clamp that ``execute_direct_base`` enforces.
    """
    config = _engine_config(tool_name)
    command_args = 'verify'
    command_key = compute_command_key(config, command_args)
    # Persisted 400 resolves to 400 * 1.25 = 500 on the learned path.
    persisted, learned = 400, 500
    floored = max(learned, config.min_timeout)

    _isolate_run_config(tmp_path, monkeypatch, {command_key: persisted})

    stamp = _lookup_bash_timeout(tool_name, command_args, str(tmp_path))

    assert stamp == get_bash_timeout(floored), (
        f'{tool_name}: the stamp must be get_bash_timeout(max(learned={learned}, '
        f'floor={config.min_timeout})) = {get_bash_timeout(floored)}, got {stamp}'
    )

    # ...and the SAME floored value is what the run measures against.
    with tempfile.TemporaryDirectory() as tmpdir:
        with (
            patch('_build_execute.create_log_file', return_value='/tmp/regression.log'),
            patch('_build_execute.timeout_get', return_value=learned),
            patch('_build_execute.timeout_set'),
            patch('_build_execute.subprocess.run', return_value=MagicMock(returncode=0)),
            patch('builtins.open', MagicMock()),
        ):
            result = execute_direct_base(
                args=command_args,
                command_key=command_key,
                default_timeout=config.default_timeout,
                project_dir=tmpdir,
                tool_name=config.tool_name,
                build_command_fn=_build_command_fn,
                wrapper=config.system_fallback,
                capture_strategy=config.capture_strategy,
                min_timeout=config.min_timeout,
            )

    assert result['timeout_used_seconds'] == floored
    assert stamp == result['timeout_used_seconds'] + OUTER_TIMEOUT_BUFFER, (
        f'{tool_name}: the stamp must equal the run bound plus the outer '
        'buffer — a stamp below what the run consumes is defect C'
    )


@pytest.mark.parametrize(('tool_name', 'skill', 'script_file', 'expected_floor'), _ENGINES, ids=_ENGINE_IDS)
def test_unmeasured_tier_verdict_follows_the_floored_stamp(
    tool_name, skill, script_file, expected_floor, tmp_path, monkeypatch
):
    """The derived tier is computed from the floored stamp — Decision 1b.

    With NO learned value, the floor alone decides: pyproject's 600s floor
    puts every pyproject build over the harness ceiling
    (``orchestrator``), while the three 300s engines stay under it
    (``per_task``). The expected verdict is DERIVED from the engine's declared
    floor here, so the case cannot pass vacuously for an engine whose floor
    changes.
    """
    config = _engine_config(tool_name)
    command_args = 'verify'

    # Empty entries → unmeasured → timeout_get echoes DEFAULT_BUILD_TIMEOUT.
    _isolate_run_config(tmp_path, monkeypatch, {})

    stamp = _lookup_bash_timeout(tool_name, command_args, str(tmp_path))
    expected_stamp = get_bash_timeout(max(DEFAULT_BUILD_TIMEOUT, config.min_timeout))
    assert stamp == expected_stamp

    fields = _compute_execution_tier_fields(stamp)
    expected_exceeds = expected_stamp > HARNESS_BASH_CEILING_SECONDS
    assert fields['exceeds_bash_ceiling'] is expected_exceeds
    assert fields['execution_tier'] == ('orchestrator' if expected_exceeds else 'per_task')


def test_decision_1b_split_is_observable_across_the_engine_list(tmp_path, monkeypatch):
    """The engine list itself proves Decision 1b's accepted blast radius.

    Unmeasured, pyproject resolves ``orchestrator`` and the three 300s engines
    resolve ``per_task``. Asserting the SPLIT (not just each engine in
    isolation) is what makes the case fail if every engine collapsed to one
    tier — the shape a dropped floor or a dropped clamp would produce.
    """
    _isolate_run_config(tmp_path, monkeypatch, {})

    tiers = {}
    for tool_name, _skill, _script, _floor in _ENGINES:
        stamp = _lookup_bash_timeout(tool_name, 'verify', str(tmp_path))
        assert stamp is not None
        tiers[tool_name] = _compute_execution_tier_fields(stamp)['execution_tier']

    assert tiers == {
        'maven': 'per_task',
        'gradle': 'per_task',
        'npm': 'per_task',
        'python': 'orchestrator',
    }, f'Decision 1b tier split drifted: {tiers}'
