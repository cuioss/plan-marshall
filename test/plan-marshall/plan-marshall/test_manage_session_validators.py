#!/usr/bin/env python3
"""6-axis canonical-identifier rejection tests for ``manage_session.py``.

Covers the ``--session-id`` flag exposed via ``transcript-path`` (the only
in-scope identifier flag declared by this script). Mirrors the canonical
6-axis matrix established by TASK-2 and re-uses
``test/plan-marshall/_input_validation_fixtures.py``.

Each malformed axis MUST produce ``status: error / error: invalid_session_id``
on stdout (TOON contract); the canonical happy-path value MUST NOT trigger
the validator (the script may still fail with ``transcript_not_found``
because the cache is empty in tests, but it MUST NOT report
``invalid_session_id``).
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

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-marshall', 'manage_session.py')


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['session_id'])
def test_transcript_path_rejects_invalid_session_id(axis, bad_value, tmp_path):
    """Each malformed axis MUST surface ``invalid_session_id`` on stdout TOON.

    The script uses ``parse_args_with_toon_errors`` so the validator
    failure is translated to ``status: error / error: invalid_session_id``
    on stdout with exit code 0 (instead of argparse's default exit-2
    stderr error).
    """
    result = run_script(
        SCRIPT_PATH,
        'transcript-path',
        '--session-id',
        bad_value,
        env_overrides={'HOME': str(tmp_path)},
    )
    assert_invalid_field(result, 'invalid_session_id')


def test_transcript_path_accepts_canonical_session_id(tmp_path):
    """Happy-path canonical session id MUST NOT trigger the validator.

    The script may still fail with ``transcript_not_found`` (the cache is
    empty in this test), but it MUST NOT report ``invalid_session_id``.
    """
    result = run_script(
        SCRIPT_PATH,
        'transcript-path',
        '--session-id',
        HAPPY_VALUES['session_id'],
        env_overrides={'HOME': str(tmp_path)},
    )
    assert_not_invalid_field(result, 'invalid_session_id')
