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
3. **Each engine carries its floor, the resolve stamp agrees with the run, and
   the tier follows the MEASUREMENT.** ``_lookup_bash_timeout``'s stamp must
   equal ``get_bash_timeout(max(learned, config.min_timeout))`` — the same
   floored value ``execute_direct_base`` measures against. ``exceeds_bash_ceiling``
   follows that floored stamp, but ``execution_tier`` does NOT: it is
   ``per_task`` only for a MEASURED command whose stamp stays within the
   ceiling, and ``orchestrator`` otherwise, so an unmeasured command fails
   closed uniformly across all four engines. (Red before deliverable 2: the
   stamp omitted the floor, under-reporting the bound. Red before this plan:
   the tier was derived from the floor, so an over-provisioned floor emptied
   the runnable slice and an unmeasured slow command could be run in-leaf on
   its very first run.)

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

#: The plan these timeout regressions attribute their builds to. ``plan_id`` is
#: mandatory on ``execute_direct_base``; ``create_log_file`` is patched out in
#: every case below, so the value only has to be a valid attribution.
_PLAN_ID = 'timeout-truthfulness-test-plan'

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
    ('python', 'build-pyproject', '_pyproject_execute.py', 330),
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


@pytest.mark.parametrize(('tool_name', 'skill', 'script_file', 'expected_floor'), _ENGINES, ids=_ENGINE_IDS)
def test_every_engine_floor_leaves_the_buffered_stamp_passable(
    tool_name, skill, script_file, expected_floor
):
    """A declared floor must never push the stamped bound past the Bash ceiling.

    The floor is bounded on BOTH sides. The lower half (floor > the engine's
    inner backstop) is asserted at each engine's own declaration; this is the
    upper half, and it is the one that had no guard: ``bash_timeout_seconds``
    is the number a leaf is instructed to pass on its Bash call, so a floor
    above ``ceiling - OUTER_TIMEOUT_BUFFER`` yields an instruction the host
    platform cannot honour and forces every one of that engine's canonicals to
    the orchestrator tier before any measurement is consulted. Parameterised
    over the engine list so a fifth engine cannot escape by omission.
    """
    config = _engine_config(tool_name)
    buffered = get_bash_timeout(config.min_timeout)
    assert buffered <= HARNESS_BASH_CEILING_SECONDS, (
        f'{tool_name}: min_timeout={config.min_timeout} + '
        f'OUTER_TIMEOUT_BUFFER={OUTER_TIMEOUT_BUFFER} = {buffered} exceeds the '
        f'harness Bash ceiling {HARNESS_BASH_CEILING_SECONDS}; the stamped bound '
        'would be un-passable and the engine could never resolve per_task'
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
                plan_id=_PLAN_ID,
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

    stamp, measured = _lookup_bash_timeout(tool_name, command_args, str(tmp_path))
    assert measured is True, f'{tool_name}: a seeded persisted value must read as measured'

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
                plan_id=_PLAN_ID,
                capture_strategy=config.capture_strategy,
                min_timeout=config.min_timeout,
            )

    assert result['timeout_used_seconds'] == floored
    assert stamp == result['timeout_used_seconds'] + OUTER_TIMEOUT_BUFFER, (
        f'{tool_name}: the stamp must equal the run bound plus the outer '
        'buffer — a stamp below what the run consumes is defect C'
    )


@pytest.mark.parametrize(('tool_name', 'skill', 'script_file', 'expected_floor'), _ENGINES, ids=_ENGINE_IDS)
def test_unmeasured_stamp_is_floored_and_the_tier_fails_closed(
    tool_name, skill, script_file, expected_floor, tmp_path, monkeypatch
):
    """Unmeasured: the stamp is still floored, but the tier fails closed.

    Two separable claims, and keeping both is the point. The STAMP half still
    pins the floor arithmetic — with no learned value, ``timeout_get`` echoes
    ``DEFAULT_BUILD_TIMEOUT`` and the engine's own floor raises it. The TIER
    half no longer follows that stamp: an unmeasured command is
    ``orchestrator`` for EVERY engine regardless of where the stamp lands
    relative to the ceiling, so no slow first run is ever made runnable
    in-leaf before it has been observed.

    ``measured=False`` is passed EXPLICITLY. ``_compute_execution_tier_fields``
    declares the parameter with no default precisely so this case cannot keep
    asserting the old floor-driven path by omission.
    """
    config = _engine_config(tool_name)
    command_args = 'verify'

    # Empty entries → unmeasured → timeout_get echoes DEFAULT_BUILD_TIMEOUT.
    _isolate_run_config(tmp_path, monkeypatch, {})

    stamp, measured = _lookup_bash_timeout(tool_name, command_args, str(tmp_path))
    expected_stamp = get_bash_timeout(max(DEFAULT_BUILD_TIMEOUT, config.min_timeout))
    assert stamp == expected_stamp
    assert measured is False, f'{tool_name}: an absent persisted entry must read as unmeasured'

    fields = _compute_execution_tier_fields(stamp, False)
    # exceeds_bash_ceiling keeps its LITERAL ceiling meaning...
    expected_exceeds = expected_stamp > HARNESS_BASH_CEILING_SECONDS
    assert fields['exceeds_bash_ceiling'] is expected_exceeds
    # ...while the tier decouples from it on exactly this branch.
    assert fields['execution_tier'] == 'orchestrator', (
        f'{tool_name}: an unmeasured command must fail closed to orchestrator '
        f'even at stamp={expected_stamp} (exceeds={expected_exceeds})'
    )


def test_unmeasured_fails_closed_uniformly_across_the_engine_list(tmp_path, monkeypatch):
    """Unmeasured collapses to ONE tier for every registered engine.

    This is the accepted blast radius of the fail-closed rule: it deliberately
    changes first-run Maven / Gradle / npm behaviour from ``per_task`` to
    ``orchestrator``. Asserting the whole dict — derived by iterating
    :data:`_ENGINES` rather than hand-listing four names — is what makes a
    fifth engine unable to escape the guard by omission.

    The companion case below is the necessary other half: with the unmeasured
    path no longer producing ``per_task``, something must still keep that
    verdict reachable, or the tier axis would have collapsed for real.
    """
    _isolate_run_config(tmp_path, monkeypatch, {})

    tiers = {}
    for tool_name, _skill, _script, _floor in _ENGINES:
        lookup = _lookup_bash_timeout(tool_name, 'verify', str(tmp_path))
        assert lookup is not None
        stamp, measured = lookup
        assert measured is False
        tiers[tool_name] = _compute_execution_tier_fields(stamp, measured)['execution_tier']

    assert tiers == dict.fromkeys(_ENGINE_IDS, 'orchestrator'), (
        f'Unmeasured fail-closed drifted — every engine must be orchestrator: {tiers}'
    )


def test_measured_low_value_makes_the_per_task_verdict_reachable(tmp_path, monkeypatch):
    """A cheap MEASURED command resolves ``per_task`` on every engine.

    The split now emerges from the MEASUREMENT rather than from the engine
    floors. Seeding a low persisted value per engine — low enough that the
    floor binds and the buffered bound stays under the ceiling — must yield
    ``per_task`` everywhere; seeding a value whose buffered bound crosses the
    ceiling must yield ``orchestrator`` everywhere. Without this case the
    ``per_task`` verdict would be under no coverage at all once the unmeasured
    path stopped producing it.
    """
    cheap_key_seed, expensive_seed = 60, 4000

    for tool_name, _skill, _script, _floor in _ENGINES:
        config = _engine_config(tool_name)
        command_key = compute_command_key(config, 'verify')

        _isolate_run_config(tmp_path, monkeypatch, {command_key: cheap_key_seed})
        stamp, measured = _lookup_bash_timeout(tool_name, 'verify', str(tmp_path))
        assert measured is True
        assert stamp <= HARNESS_BASH_CEILING_SECONDS, (
            f'{tool_name}: a cheap measured command must stay within the ceiling'
        )
        cheap = _compute_execution_tier_fields(stamp, measured)
        assert cheap['execution_tier'] == 'per_task', (
            f'{tool_name}: a cheap MEASURED command must be runnable in-leaf, got '
            f'{cheap["execution_tier"]} at stamp={stamp}'
        )

        _isolate_run_config(tmp_path, monkeypatch, {command_key: expensive_seed})
        stamp, measured = _lookup_bash_timeout(tool_name, 'verify', str(tmp_path))
        assert measured is True
        expensive = _compute_execution_tier_fields(stamp, measured)
        assert expensive['exceeds_bash_ceiling'] is True
        assert expensive['execution_tier'] == 'orchestrator', (
            f'{tool_name}: a measured command past the ceiling must hand off, got '
            f'{expensive["execution_tier"]} at stamp={stamp}'
        )
