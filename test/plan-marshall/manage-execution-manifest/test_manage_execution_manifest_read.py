#!/usr/bin/env python3
"""Tests for the ``read`` subcommand of manage-execution-manifest.py.

Split from test_manage_execution_manifest.py — tier 2 direct-import tests for
the read path plus the CLI roundtrip for the missing-manifest error case.
"""

import importlib.util
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, run_script

# Script path for subprocess (CLI plumbing) tests.
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py')

# Tier 2 direct imports via importlib (scripts loaded via PYTHONPATH at runtime).
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


_mem = _load_module('_mem_script', 'manage-execution-manifest.py')
cmd_compose = _mem.cmd_compose
cmd_read = _mem.cmd_read
DEFAULT_PHASE_5_STEPS = _mem.DEFAULT_PHASE_5_STEPS
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Quiet down the best-effort decision-log subprocess so tests don't depend on a
# running executor. The handler is wrapped in try/except so failures are
# already silent, but we replace it with a no-op for clarity and speed.
_mem._log_decision = lambda *a, **kw: None  # type: ignore[attr-defined]


# =============================================================================
# Namespace Helpers
# =============================================================================


def _compose_ns(
    plan_id: str = 'test-plan',
    change_type: str = 'feature',
    track: str = 'complex',
    scope_estimate: str = 'multi_module',
    recipe_key: str | None = None,
    affected_files_count: int = 5,
    phase_5_steps: str | None = 'quality-gate,module-tests',
    phase_6_steps: str | None = ','.join(DEFAULT_PHASE_6_STEPS),
    commit_and_push: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track=track,
        scope_estimate=scope_estimate,
        recipe_key=recipe_key,
        affected_files_count=affected_files_count,
        phase_5_steps=phase_5_steps,
        phase_6_steps=phase_6_steps,
        commit_and_push=commit_and_push,
    )


def _read_ns(plan_id: str = 'test-plan') -> Namespace:
    return Namespace(plan_id=plan_id)


# =============================================================================
# read subcommand tests
# =============================================================================


def test_read_returns_full_manifest(plan_context):
    cmd_compose(_compose_ns(plan_id='io-read'))
    result = cmd_read(_read_ns(plan_id='io-read'))
    assert result is not None and result['status'] == 'success'
    assert result['plan_id'] == 'io-read'
    assert 'phase_5' in result
    assert 'phase_6' in result


def test_read_missing_manifest_returns_none_with_toon_error(plan_context, capsys):
    result = cmd_read(_read_ns(plan_id='io-missing'))
    assert result is None
    captured = capsys.readouterr()
    assert 'file_not_found' in captured.out


def test_read_returns_all_manifest_keys(plan_context):
    """read echoes every manifest field the composer wrote."""
    cmd_compose(_compose_ns(plan_id='io-read-fields'))
    result = cmd_read(_read_ns(plan_id='io-read-fields'))
    assert result is not None
    # Mandatory schema keys.
    assert result['manifest_version'] == 1
    assert 'phase_5' in result and 'phase_6' in result
    # phase_5 sub-keys.
    assert 'early_terminate' in result['phase_5']
    assert 'verification_steps' in result['phase_5']
    # phase_6 sub-keys.
    assert 'steps' in result['phase_6']


# =============================================================================
# CLI plumbing (subprocess) tests for read
# =============================================================================


def test_cli_read_missing_manifest_emits_toon_error(plan_context):
    """read without a prior compose emits file_not_found via TOON."""
    result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'cli-no-manifest')
    # Script exits 0 on missing-file errors (TOON contract).
    assert result.returncode == 0
    data = result.toon()
    assert data['status'] == 'error'
    assert data['error'] == 'file_not_found'
