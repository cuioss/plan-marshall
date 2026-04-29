#!/usr/bin/env python3
"""6-axis identifier-validation rejection-path tests for ``manage-memory.py``.

In-scope flags from TASK-1: ``--session-id`` (save command, optional).
"""

from __future__ import annotations

import pytest
from _input_validation_fixtures import (  # type: ignore[import-not-found]
    MALFORMED_AXES,
    assert_invalid_field,
)

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-memories', 'manage-memory.py')


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['session_id'])
def test_save_rejects_invalid_session_id(axis, bad_value):
    """``manage-memory save --session-id <bad> ...`` → invalid_session_id TOON.

    The only valid ``--category`` value today is ``context``; the other
    required flags (``--identifier``, ``--content``) provide minimal
    placeholders so argparse reaches the ``--session-id`` validator.
    """
    result = run_script(
        SCRIPT_PATH,
        'save',
        '--category',
        'context',
        '--identifier',
        'foo',
        '--content',
        '{}',
        '--session-id',
        bad_value,
    )
    assert_invalid_field(result, 'invalid_session_id')
