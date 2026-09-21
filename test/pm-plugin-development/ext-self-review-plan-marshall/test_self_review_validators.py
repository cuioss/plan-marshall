#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""6-axis canonical-identifier rejection tests for ``self_review.py``.

Covers the ``--plan-id`` flag declared by the ``surface`` subcommand
(via ``add_plan_id_arg``). The production code wires
``parse_args_with_toon_errors`` into ``self_review.py``'s ``main()`` so
malformed input now produces ``status: error / error: invalid_plan_id``
on stdout TOON (exit 0) instead of argparse's default exit-2 stderr error.

Re-uses ``test/_shared/_input_validation_fixtures.py`` for the
canonical 6-axis matrix.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from _input_validation_fixtures import (
    HAPPY_VALUES,
    MALFORMED_AXES,
    assert_not_invalid_field,
    assert_plan_id_axis_rejected,
)

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('pm-plugin-development', 'ext-self-review-plan-marshall', 'self_review.py')

# ⛔ Vacuity guard — the axis populations are imported, so an emptied one collects
# zero cases at the parametrize sites below and still reports green.
assert MALFORMED_AXES['plan_id'], 'MALFORMED_AXES["plan_id"] is empty'


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['plan_id'])
def test_surface_rejects_invalid_plan_id(axis, bad_value, tmp_path):
    """Malformed --plan-id for ``surface`` surfaces invalid_plan_id.

    ``--project-dir`` is required for ``surface``; we supply tmp_path
    so argparse's required-arg machinery is satisfied and the failure
    is unambiguously attributed to --plan-id.
    """
    assert_plan_id_axis_rejected(SCRIPT_PATH, 'surface', bad_value, extra_args=('--project-dir', str(tmp_path)))


@pytest.fixture
def isolated_repo(tmp_path: Path) -> Path:
    """A standalone git repository to hand ``surface`` as ``--project-dir``.

    ``surface`` shells out as ``git -C {project_dir} ...``, and git resolves a
    repository by walking UPWARD from that directory until it finds a ``.git``.
    A bare ``tmp_path`` therefore does not isolate anything: the suite's
    basetemp root lives at ``.plan/temp/pytest-basetemp`` INSIDE this checkout,
    so the walk reaches the enclosing plan-marshall worktree and the command
    computes that repository's entire ``{base}...HEAD`` diff — thousands of
    files it neither controls nor asserts on, and whose cost grows without
    bound as the real branch grows.

    Initialising a repository AT ``tmp_path`` terminates the walk there, so the
    invocation is answered by this fixture rather than by whatever the
    surrounding checkout happens to contain. ``main`` is unborn in a fresh
    ``init``, so ``surface`` still fails for a reason that is not the
    identifier validator — which is exactly what the caller asserts.

    ``git`` is guaranteed present: the root conftest's ``pytest_sessionstart``
    fails the run when it is missing.
    """
    subprocess.run(
        ['git', '-C', str(tmp_path), 'init', '--initial-branch=main'],
        capture_output=True,
        text=True,
        check=True,
    )
    return tmp_path


def test_surface_accepts_canonical_plan_id(isolated_repo):
    """Happy-path canonical plan_id MUST NOT trigger invalid_plan_id.

    The script will fail with another error (base branch unresolvable in the
    isolated fixture repo) but the failure cause MUST NOT be the canonical
    identifier validator.
    """
    result = run_script(
        SCRIPT_PATH,
        'surface',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--project-dir',
        str(isolated_repo),
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
