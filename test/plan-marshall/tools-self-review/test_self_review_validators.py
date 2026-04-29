#!/usr/bin/env python3
"""6-axis canonical-identifier rejection tests for ``self_review.py``.

Covers the ``--plan-id`` flag declared by the ``surface`` subcommand
(via ``add_plan_id_arg``). The TASK-3 production-code fix wired
``parse_args_with_toon_errors`` into ``self_review.py``'s ``main()`` so
malformed input now produces ``status: error / error: invalid_plan_id``
on stdout TOON (exit 0) instead of argparse's default exit-2 stderr error.

Re-uses ``test/plan-marshall/_input_validation_fixtures.py`` for the
canonical 6-axis matrix (TASK-2 foundation).
"""

from __future__ import annotations

import pytest

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from _input_validation_fixtures import (  # type: ignore[import-not-found]
    HAPPY_VALUES,
    MALFORMED_AXES,
    assert_invalid_field,
    assert_not_invalid_field,
)

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'tools-self-review', 'self_review.py')


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
