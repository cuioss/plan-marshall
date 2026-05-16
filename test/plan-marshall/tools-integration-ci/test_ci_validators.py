#!/usr/bin/env python3
"""6-axis canonical-identifier rejection tests for ``ci.py`` (provider-agnostic router).

Tests the user-facing entry point ``ci.py`` even though the actual argparse
declarations live in ``ci_base.py`` (via ``add_plan_id_arg``). Without the
provider scaffolding (marshal.json with a configured CI provider), the
router exits early with ``CI provider not configured`` — to exercise the
validator path we need a marshal.json that declares a github provider so
the router delegates to ``github_ops.main()`` which calls
``parse_args_with_toon_errors``.

The canonical TASK-3 migration target was the ``pr prepare-body`` subcommand,
which uses ``add_plan_id_arg`` (line 627 in ci_base.py). Malformed input
must surface ``status: error / error: invalid_plan_id`` on stdout TOON
with exit code 0.

Re-uses ``test/plan-marshall/_input_validation_fixtures.py`` for the
canonical 6-axis matrix (TASK-2 foundation).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from _input_validation_fixtures import (  # type: ignore[import-not-found]
    HAPPY_VALUES,
    MALFORMED_AXES,
    assert_not_invalid_field,
)

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'tools-integration-ci', 'ci.py')


def _seed_github_marshal(tmp_path: Path) -> Path:
    """Create a minimal marshal.json that resolves to the github provider.

    ci.py walks up from cwd looking for ``.plan/marshal.json``. Tests
    run with ``cwd=tmp_path`` so the file lands at
    ``tmp_path/.plan/marshal.json``.
    """
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    marshal = {
        'providers': [
            {
                'skill_name': 'plan-marshall:workflow-integration-github',
                'category': 'ci',
            },
        ],
    }
    (plan_dir / 'marshal.json').write_text(json.dumps(marshal))
    return plan_dir / 'marshal.json'


# =============================================================================
# --plan-id rejection-path tests for ``pr prepare-body``
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['plan_id'])
def test_pr_prepare_body_plan_id_after_subcommand_rejected_by_guard(axis, bad_value, tmp_path):
    """``pr prepare-body --plan-id X`` is rejected by the positional routing-flag guard.

    Fix A (secondary guard): routing flags that appear after the subcommand
    boundary are a structural error. The guard fires before argparse runs,
    so the subcommand-level --plan-id validator is never reached via this path.
    The guard emits exit 2 + ``routing_flag_after_subcommand`` TOON error.

    Callers must place ``--plan-id`` before the subcommand token for routing
    (e.g., ``ci.py --plan-id X pr prepare-body``) or use ``--project-dir``
    before the subcommand for the explicit-path escape hatch.
    """
    _seed_github_marshal(tmp_path)
    result = run_script(
        SCRIPT_PATH,
        'pr',
        'prepare-body',
        '--plan-id',
        bad_value,
        cwd=tmp_path,
    )
    assert result.returncode == 2, (
        f'Expected exit 2 (routing_flag_after_subcommand guard), got {result.returncode}\n'
        f'stdout={result.stdout!r}\nstderr={result.stderr!r}'
    )
    assert 'routing_flag_after_subcommand' in result.stdout, (
        f'Expected routing_flag_after_subcommand in TOON output, got: {result.stdout!r}'
    )


def test_pr_prepare_body_accepts_canonical_plan_id(tmp_path):
    """Happy-path canonical plan_id MUST NOT trigger invalid_plan_id.

    The script may still fail with another error (provider not
    available, gh CLI missing, etc.) but the failure cause MUST NOT be
    the canonical identifier validator.
    """
    _seed_github_marshal(tmp_path)
    result = run_script(
        SCRIPT_PATH,
        'pr',
        'prepare-body',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        cwd=tmp_path,
    )
    assert_not_invalid_field(result, 'invalid_plan_id')


# =============================================================================
# Top-level --project-dir flag is consumed BEFORE provider delegation,
# so a malformed --plan-id must still surface invalid_plan_id even when
# --project-dir is supplied.
# =============================================================================


def test_pr_prepare_body_with_project_dir_plan_id_after_subcommand_rejected_by_guard(tmp_path):
    """``--project-dir PATH pr prepare-body --plan-id X`` is rejected by the guard.

    Fix A (secondary guard): routing flags that appear after the subcommand
    boundary are rejected even when ``--project-dir`` is provided before
    the subcommand. The ``--plan-id`` in the subcommand's argv triggers
    the guard with ``routing_flag_after_subcommand``.
    """
    _seed_github_marshal(tmp_path)
    result = run_script(
        SCRIPT_PATH,
        '--project-dir',
        str(tmp_path),
        'pr',
        'prepare-body',
        '--plan-id',
        'BAD!ID',
        cwd=tmp_path,
    )
    assert result.returncode == 2, (
        f'Expected exit 2 (routing_flag_after_subcommand guard), got {result.returncode}\n'
        f'stdout={result.stdout!r}\nstderr={result.stderr!r}'
    )
    assert 'routing_flag_after_subcommand' in result.stdout, (
        f'Expected routing_flag_after_subcommand in TOON output, got: {result.stdout!r}'
    )


# =============================================================================
# Two-state routing contract — both --plan-id and --project-dir at router
# =============================================================================
#
# The router-level ``--plan-id`` is consumed by ``extract_routing_args`` for
# worktree resolution. Supplying it together with router-level
# ``--project-dir`` MUST surface mutually_exclusive_args before the
# canonical validator ever runs (the validator only sees
# subcommand-level identifiers).


def test_router_level_plan_id_with_project_dir_yields_mutually_exclusive_error(tmp_path):
    """Router-level --plan-id + --project-dir → mutually_exclusive_args TOON error.

    Both flags appear BEFORE the subcommand token, so the guard does not fire.
    The mutually-exclusive check triggers instead.
    """
    _seed_github_marshal(tmp_path)
    result = run_script(
        SCRIPT_PATH,
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--project-dir',
        str(tmp_path),
        'pr',
        'prepare-body',
        cwd=tmp_path,
    )
    assert result.returncode == 2, f'Expected exit 2 (mutually_exclusive_args), got {result.returncode}'
    assert 'mutually_exclusive_args' in result.stdout, (
        f'Expected mutually_exclusive_args in TOON output, got: {result.stdout!r}'
    )


