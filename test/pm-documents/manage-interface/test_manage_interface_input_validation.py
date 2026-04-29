#!/usr/bin/env python3
"""6-axis identifier-validation rejection-path tests for ``manage-interface.py``.

In-scope flags from TASK-5: ``--field`` (the ``update`` subcommand).

The 6 axes mirror the canonical fixture set established by TASK-2:

    * empty, path-separator, glob-meta, traversal, overlong (rejection)
    * happy-path (passes validator)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from _input_validation_fixtures import (  # type: ignore[import-not-found]  # noqa: E402
    HAPPY_VALUES,
    MALFORMED_AXES,
    assert_invalid_field,
    assert_not_invalid_field,
)

from conftest import get_script_path, run_script  # type: ignore[import-not-found]  # noqa: E402

SCRIPT_PATH = get_script_path('pm-documents', 'manage-interface', 'manage-interface.py')


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['field'])
def test_update_rejects_invalid_field(axis, bad_value):
    """``manage-interface update --field <bad>`` → ``invalid_field`` TOON."""
    result = run_script(
        SCRIPT_PATH,
        'update',
        '--number', '1',
        '--field', bad_value,
        '--value', 'irrelevant',
    )
    assert_invalid_field(result, 'invalid_field')


def test_update_accepts_canonical_field():
    """Canonical ``--field`` value passes the validator.

    The script may still error on missing interface file or other
    downstream concerns, but it MUST NOT emit ``invalid_field``.
    """
    result = run_script(
        SCRIPT_PATH,
        'update',
        '--number', '1',
        '--field', HAPPY_VALUES['field'],
        '--value', 'irrelevant',
    )
    assert_not_invalid_field(result, 'invalid_field')
