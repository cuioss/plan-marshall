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
    assert_invalid_field,
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
def test_pr_prepare_body_rejects_invalid_plan_id(axis, bad_value, tmp_path):
    """Malformed --plan-id for ``pr prepare-body`` surfaces invalid_plan_id.

    The router (ci.py) consumes ``--project-dir`` first, then delegates to
    ``github_ops.main()`` which runs ``parse_args_with_toon_errors``.
    The validator failure is emitted on stdout as TOON (exit 0).
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
    assert_invalid_field(result, 'invalid_plan_id')


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


def test_pr_prepare_body_with_project_dir_still_validates_plan_id(tmp_path):
    """Top-level ``--project-dir`` does not bypass the canonical validator.

    The router strips ``--project-dir`` before delegating, so the
    downstream parser still sees ``--plan-id`` and runs validation.
    """
    _seed_github_marshal(tmp_path)
    result = run_script(
        SCRIPT_PATH,
        '--project-dir',
        str(tmp_path),
        'pr',
        'prepare-body',
        '--plan-id',
        'BAD!ID',  # invalid format
        cwd=tmp_path,
    )
    assert_invalid_field(result, 'invalid_plan_id')
