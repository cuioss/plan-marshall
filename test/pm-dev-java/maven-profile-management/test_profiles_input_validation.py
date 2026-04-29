#!/usr/bin/env python3
"""6-axis identifier-validation rejection-path tests for ``profiles.py``.

In-scope flags from TASK-5: ``--module`` (the ``list`` subcommand). The
``--profile-id`` flag is OUT OF SCOPE per TASK-5 notes — it is not yet
backed by a canonical validator from ``input_validation.py``.

The 6 axes mirror the canonical fixture set established by TASK-2:

    * empty, path-separator, glob-meta, traversal, overlong (rejection)
    * happy-path (passes validator)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# The sibling _fixtures.py lives next to this file. Make it importable
# without requiring conftest plumbing.
sys.path.insert(0, str(Path(__file__).parent))

from _input_validation_fixtures import (  # type: ignore[import-not-found]  # noqa: E402
    HAPPY_VALUES,
    MALFORMED_AXES,
    assert_invalid_field,
    assert_not_invalid_field,
)

from conftest import get_script_path, run_script  # type: ignore[import-not-found]  # noqa: E402

SCRIPT_PATH = get_script_path('pm-dev-java', 'manage-maven-profiles', 'profiles.py')


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['module'])
def test_list_rejects_invalid_module(axis, bad_value):
    """``profiles list --module <bad>`` → ``invalid_module`` TOON."""
    result = run_script(SCRIPT_PATH, 'list', '--module', bad_value)
    assert_invalid_field(result, 'invalid_module')


def test_list_accepts_canonical_module():
    """Canonical ``--module`` value passes the validator.

    The script may still return another error (e.g. derived-data not
    found), but it MUST NOT emit ``invalid_module``.
    """
    result = run_script(SCRIPT_PATH, 'list', '--module', HAPPY_VALUES['module'])
    assert_not_invalid_field(result, 'invalid_module')
