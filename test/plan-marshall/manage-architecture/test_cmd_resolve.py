#!/usr/bin/env python3
"""Tests for ``cmd_resolve`` augmentation with bash-timeout / execution-tier fields.

Pins the contract documented in ``_cmd_client`` § "Build-executable
classification": when the resolved ``executable`` is a Bucket B build
notation (``plan-marshall:build-{maven,gradle,npm,pyproject_build}``),
``cmd_resolve`` augments today's TOON shape with four additional fields
(``bash_timeout_seconds``, ``exceeds_bash_ceiling``, ``execution_tier``,
``hint``). Non-build executables (Bucket A ``manage-*`` notations, raw
shell invocations) keep today's shape verbatim.

The five parametrised cases below cover the public surface:

* Bucket B with short persisted duration -> ``per_task`` tier.
* Bucket B with persisted duration above 600s -> ``orchestrator`` tier.
* Bucket B with no persisted measurement -> ``per_task`` tier with the
  ``DEFAULT_BUILD_TIMEOUT``-derived bash timeout.
* Bucket A ``manage-*`` notation -> legacy TOON (no augmentation).
* Pinned hint strings match exactly so an LLM can recognise them.
"""

import importlib.util
import sys
import tempfile
from argparse import Namespace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from _arch_fixtures import seed_project as _seed_project  # noqa: E402

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-architecture'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_architecture_core = _load_module('_architecture_core', '_architecture_core.py')
_cmd_client = _load_module('_cmd_client', '_cmd_client.py')

cmd_resolve = _cmd_client.cmd_resolve


# Canonical Bucket B executable shape ``cmd_resolve`` returns for a pyproject
# ``verify`` command scoped to the ``plan-marshall`` bundle module. The
# ``command_args`` string after ``--command-args`` is the literal value that
# ``default_command_key_fn`` normalises to the persisted key
# ``python:verify_plan_marshall``.
_PYPROJECT_VERIFY_EXECUTABLE = (
    'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
    'run --command-args "verify plan-marshall"'
)

# Bucket A manage-* notation — passes classification's filter and the four
# augmentation fields MUST be absent from the resolve TOON.
_BUCKET_A_MANAGE_EXECUTABLE = (
    'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read'
)


def _seed_single_module(tmpdir: str, command: str, executable: str) -> None:
    """Seed a single ``root`` module exposing ``command`` with ``executable``."""
    modules = {
        'root': {
            'name': 'root',
            'build_systems': ['pyproject'],
            'paths': {'module': '.'},
            'commands': {command: executable},
        }
    }
    _seed_project(tmpdir, modules)


def _set_persisted_timeout(plan_dir: Path, command_key: str, duration_seconds: int) -> None:
    """Write a persisted timeout under ``plan_dir/run-configuration.json``.

    The file path mirrors what ``get_run_config_path`` returns when
    ``PLAN_BASE_DIR`` is set to ``plan_dir``.
    """
    import json

    config_path = plan_dir / 'run-configuration.json'
    config = {
        'version': 1,
        'commands': {command_key: {'timeout_seconds': duration_seconds}},
    }
    config_path.write_text(json.dumps(config, indent=2))


@pytest.fixture
def isolated_run_config(monkeypatch, tmp_path):
    """Redirect ``run-configuration.json`` lookup to an isolated tmp dir.

    Routes both the env var (consumed by ``file_ops.get_base_dir``) and the
    module-level ``_config_core.RUN_CONFIG_PATH`` so the in-process
    ``timeout_get`` lookup reads from ``tmp_path`` instead of the real
    repo-local ``.plan/local/run-configuration.json``.
    """
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    import _config_core  # type: ignore[import-not-found]

    monkeypatch.setattr(_config_core, 'PLAN_BASE_DIR', plan_dir)
    monkeypatch.setattr(_config_core, 'RUN_CONFIG_PATH', plan_dir / 'run-configuration.json')

    return plan_dir


# =============================================================================
# Case (a): Bucket B notation, short duration -> per_task tier
# =============================================================================


def test_cmd_resolve_bucket_b_short_duration_returns_per_task(isolated_run_config):
    """Bucket B + persisted timeout below 600s ceiling -> per_task tier.

    persisted=400 -> inner=max(120, int(400*1.25))=500 -> bash=500+30=530.
    530 <= 600 so execution_tier=per_task and the hint pins the value as
    ``Bash timeout=530000ms``.
    """
    _set_persisted_timeout(isolated_run_config, 'python:verify_plan_marshall', 400)

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_single_module(tmpdir, 'verify', _PYPROJECT_VERIFY_EXECUTABLE)

        args = Namespace(project_dir=tmpdir, resolve_command='verify', module=None)
        result = cmd_resolve(args)

    assert result['status'] == 'success'
    assert result['executable'] == _PYPROJECT_VERIFY_EXECUTABLE
    assert result['bash_timeout_seconds'] == 530
    assert result['exceeds_bash_ceiling'] is False
    assert result['execution_tier'] == 'per_task'
    assert result['hint'] == 'Bash timeout=530000ms'


# =============================================================================
# Case (b): Bucket B notation, long duration -> orchestrator tier
# =============================================================================


def test_cmd_resolve_bucket_b_long_duration_returns_orchestrator(isolated_run_config):
    """Bucket B + persisted timeout > 600s ceiling -> orchestrator tier.

    persisted=800 -> inner=max(120, int(800*1.25))=1000 -> bash=1000+30=1030.
    1030 > 600 so exceeds_bash_ceiling=True, execution_tier=orchestrator,
    hint pins the ceiling overflow phrase.
    """
    _set_persisted_timeout(isolated_run_config, 'python:verify_plan_marshall', 800)

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_single_module(tmpdir, 'verify', _PYPROJECT_VERIFY_EXECUTABLE)

        args = Namespace(project_dir=tmpdir, resolve_command='verify', module=None)
        result = cmd_resolve(args)

    assert result['status'] == 'success'
    assert result['bash_timeout_seconds'] == 1030
    assert result['exceeds_bash_ceiling'] is True
    assert result['execution_tier'] == 'orchestrator'
    assert result['hint'] == 'Exceeds Bash ceiling; orchestrator-tier only'


# =============================================================================
# Case (c): Bucket B notation, no persisted measurement -> DEFAULT_BUILD_TIMEOUT
# =============================================================================


def test_cmd_resolve_bucket_b_no_measurement_uses_default(isolated_run_config):
    """Bucket B without persisted measurement -> per_task with default-derived timeout.

    No timeout_set call -> timeout_get falls back to DEFAULT_BUILD_TIMEOUT=300.
    inner=max(120, 300)=300 -> bash=300+30=330. 330 <= 600 so per_task.
    """
    # No call to _set_persisted_timeout. Empty run-config -> default path.
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_single_module(tmpdir, 'verify', _PYPROJECT_VERIFY_EXECUTABLE)

        args = Namespace(project_dir=tmpdir, resolve_command='verify', module=None)
        result = cmd_resolve(args)

    assert result['status'] == 'success'
    assert result['bash_timeout_seconds'] == 330
    assert result['exceeds_bash_ceiling'] is False
    assert result['execution_tier'] == 'per_task'
    assert result['hint'] == 'Bash timeout=330000ms'


# =============================================================================
# Case (d): Bucket A manage-* notation -> legacy TOON (no augmentation)
# =============================================================================


def test_cmd_resolve_bucket_a_manage_notation_returns_legacy_toon(isolated_run_config):
    """Bucket A ``manage-*`` notation does NOT receive the four new fields.

    Classification returns ``None`` for non-build executables, so
    ``cmd_resolve`` falls through without invoking the augmentation helper.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_single_module(tmpdir, 'status', _BUCKET_A_MANAGE_EXECUTABLE)

        args = Namespace(project_dir=tmpdir, resolve_command='status', module=None)
        result = cmd_resolve(args)

    assert result['status'] == 'success'
    assert result['executable'] == _BUCKET_A_MANAGE_EXECUTABLE
    # Legacy TOON shape: none of the four augmentation fields are present.
    assert 'bash_timeout_seconds' not in result
    assert 'exceeds_bash_ceiling' not in result
    assert 'execution_tier' not in result
    assert 'hint' not in result


# =============================================================================
# Case (e): Pinned hint strings match exactly
# =============================================================================


@pytest.mark.parametrize(
    ('persisted_seconds', 'expected_bash_timeout', 'expected_hint'),
    [
        # per_task variants — hint pins the millisecond value.
        (200, 280, 'Bash timeout=280000ms'),  # inner=max(120, 250)=250 -> 280
        (400, 530, 'Bash timeout=530000ms'),  # inner=max(120, 500)=500 -> 530
        # orchestrator variant — hint is the fixed overflow phrase.
        (800, 1030, 'Exceeds Bash ceiling; orchestrator-tier only'),
        (5000, 6280, 'Exceeds Bash ceiling; orchestrator-tier only'),
    ],
)
def test_cmd_resolve_hint_pins_recognition_token(
    isolated_run_config, persisted_seconds, expected_bash_timeout, expected_hint
):
    """Hint string is a pinned recognition token, NOT human prose.

    Asserts exact-match equality on the hint string for both tiers, so a
    future refactor that re-words either template (e.g., adds a period,
    changes capitalisation) trips this guard.
    """
    _set_persisted_timeout(
        isolated_run_config, 'python:verify_plan_marshall', persisted_seconds
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_single_module(tmpdir, 'verify', _PYPROJECT_VERIFY_EXECUTABLE)

        args = Namespace(project_dir=tmpdir, resolve_command='verify', module=None)
        result = cmd_resolve(args)

    assert result['bash_timeout_seconds'] == expected_bash_timeout
    assert result['hint'] == expected_hint
