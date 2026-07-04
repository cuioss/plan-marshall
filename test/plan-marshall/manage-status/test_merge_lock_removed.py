#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression guard for the removed ``manage-status merge-lock`` status-marker surface.

The layer-#2 merge-lock status-marker scan was removed from ``manage-status`` (its
implementation ``_cmd_merge_lock.py`` and the original behavioural contract
``test_merge_lock.py`` were both deleted). The cross-plan filesystem merge lock now
lives exclusively in ``manage-locks/merge_lock.py`` — ``manage-status`` no longer owns
any merge-lock subcommand.

These tests lock in that removal: the CLI must reject ``merge-lock`` (and its former
acquire/release/check sub-verbs) as an unknown subcommand so the surface cannot be
silently reintroduced.
"""

from __future__ import annotations

import pytest

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')


@pytest.mark.parametrize('args', [
    ('merge-lock',),
    ('merge-lock', '--plan-id', 'plan-a'),
    ('merge-lock', 'acquire', '--plan-id', 'plan-a'),
    ('merge-lock', 'release', '--plan-id', 'plan-a'),
    ('merge-lock', 'check', '--plan-id', 'plan-a'),
])
def test_merge_lock_subcommand_rejected(args):
    """``manage-status merge-lock ...`` is no longer a valid subcommand.

    argparse rejects an unregistered subcommand with exit code 2 and an
    ``invalid choice`` usage error on stderr.
    """
    result = run_script(SCRIPT_PATH, *args)
    assert result.returncode == 2
    assert 'invalid choice' in result.stderr
    assert 'merge-lock' in result.stderr
