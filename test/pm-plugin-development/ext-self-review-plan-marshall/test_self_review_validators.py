#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""6-axis canonical-identifier rejection tests for ``self_review.py``.

Covers the ``--plan-id`` flag declared by the ``surface`` subcommand
(via ``add_plan_id_arg``). The TASK-3 production-code fix wired
``parse_args_with_toon_errors`` into ``self_review.py``'s ``main()`` so
malformed input now produces ``status: error / error: invalid_plan_id``
on stdout TOON (exit 0) instead of argparse's default exit-2 stderr error.

Re-uses ``test/plan-marshall/_pm_input_validation_fixtures.py`` for the
canonical 6-axis matrix (TASK-2 foundation).
"""

from __future__ import annotations

import pytest

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from _pm_input_validation_fixtures import (  # type: ignore[import-not-found]
    HAPPY_VALUES,
    MALFORMED_AXES,
    assert_invalid_field,
    assert_not_invalid_field,
)

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('pm-plugin-development', 'ext-self-review-plan-marshall', 'self_review.py')


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['plan_id'])
def test_surface_rejects_invalid_plan_id(axis, bad_value, tmp_path):
    """Malformed --plan-id for ``surface`` surfaces invalid_plan_id.

    ``--project-dir`` is required for ``surface``; we supply tmp_path
    so argparse's required-arg machinery is satisfied and the failure
    is unambiguously attributed to --plan-id.
    """
    result = run_script(
        SCRIPT_PATH,
        'surface',
        '--plan-id',
        bad_value,
        '--project-dir',
        str(tmp_path),
    )
    assert_invalid_field(result, 'invalid_plan_id')


def test_surface_accepts_canonical_plan_id(tmp_path):
    """Happy-path canonical plan_id MUST NOT trigger invalid_plan_id.

    The script will fail with another error (no git repo, no diff,
    etc.) but the failure cause MUST NOT be the canonical identifier
    validator.
    """
    result = run_script(
        SCRIPT_PATH,
        'surface',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--project-dir',
        str(tmp_path),
    )
    assert_not_invalid_field(result, 'invalid_plan_id')


# =============================================================================
# Two-state ``--plan-id`` / ``--project-dir`` routing contract
# =============================================================================
#
# self_review.py uses a custom routing path: ``--plan-id`` is mandatory
# (drives modified-files lookup) and ``--project-dir`` is optional
# (escape hatch for the worktree path). When ``--project-dir`` is
# omitted, the script auto-resolves the worktree via
# ``resolve_project_dir(plan_id, None, default=None)``. The pre-existing
# tests above cover the validator rejection path; these tests pin the
# routing wiring.


def test_surface_help_declares_both_routing_flags():
    """``surface --help`` must declare both --plan-id and --project-dir."""
    result = run_script(SCRIPT_PATH, 'surface', '--help')
    assert result.success, f'--help failed: {result.stderr}'
    assert '--plan-id' in result.stdout
    assert '--project-dir' in result.stdout


def test_surface_plan_id_optional_project_dir_resolves_via_manage_status(tmp_path, monkeypatch):
    """Without --project-dir, ``surface`` auto-resolves the worktree via manage-status.

    We can't run the full pipeline (it needs a real git checkout) so we
    only verify that argparse accepts ``--plan-id`` alone — the resolver
    failure mode is irrelevant; we just need it to NOT be ``invalid_plan_id``
    or an argparse error.
    """
    result = run_script(
        SCRIPT_PATH,
        'surface',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
    )
    # No argparse error → routing flag pair was accepted.
    assert 'unrecognized arguments' not in result.stderr
    # And the failure (if any) is NOT invalid_plan_id.
    assert_not_invalid_field(result, 'invalid_plan_id')


def test_surface_imports_resolve_project_dir():
    """self_review.py MUST import resolve_project_dir for auto-routing."""
    source = SCRIPT_PATH.read_text(encoding='utf-8')
    assert 'resolve_project_dir' in source, (
        'self_review.py must import resolve_project_dir to enforce '
        'the two-state --plan-id / --project-dir routing contract.'
    )


def test_surface_imports_emit_worktree_error():
    """self_review.py MUST surface the canonical worktree-resolution error payload."""
    source = SCRIPT_PATH.read_text(encoding='utf-8')
    assert 'emit_worktree_error' in source, (
        'self_review.py must call emit_worktree_error so worktree-resolution '
        'failures surface as the canonical TOON error payload.'
    )
