#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``qgate-mechanical-checks`` subcommand of manage-tasks.

Scope: the files-exist check across every operation — read, write-new, write-replace
and delete — and which combination of operation and on-disk presence is a flag
rather than a pass.
"""


from __future__ import annotations

from _manage_tasks_qgate_mechanical_fixtures import _EXISTING_FILE, _MISSING_FILE, _files_exist_failed


def test_qgate_files_exist_read_missing_flags(plan_context):
    """read + missing target → 1 finding (current behaviour preserved)."""
    assert _files_exist_failed(plan_context, 'qgate-read-missing', _MISSING_FILE, 'read') == 1


def test_qgate_files_exist_read_present_passes(plan_context):
    """read + existing target → 0 findings."""
    assert _files_exist_failed(plan_context, 'qgate-read-present', _EXISTING_FILE, 'read') == 0


def test_qgate_files_exist_write_new_missing_passes(plan_context):
    """write-new + missing target → 0 findings (the noise class this plan removes)."""
    assert _files_exist_failed(plan_context, 'qgate-writenew-missing', _MISSING_FILE, 'write-new') == 0


def test_qgate_files_exist_write_new_present_flags(plan_context):
    """write-new + existing target → 1 finding (inverted signal fires)."""
    assert _files_exist_failed(plan_context, 'qgate-writenew-present', _EXISTING_FILE, 'write-new') == 1


def test_qgate_files_exist_write_replace_missing_passes(plan_context):
    """write-replace + missing target → 0 findings."""
    assert _files_exist_failed(plan_context, 'qgate-writerepl-missing', _MISSING_FILE, 'write-replace') == 0


def test_qgate_files_exist_write_replace_present_passes(plan_context):
    """write-replace + existing target → 0 findings."""
    assert _files_exist_failed(plan_context, 'qgate-writerepl-present', _EXISTING_FILE, 'write-replace') == 0


def test_qgate_files_exist_delete_missing_flags(plan_context):
    """delete + missing target → 1 finding (delete-specific message)."""
    assert _files_exist_failed(plan_context, 'qgate-delete-missing', _MISSING_FILE, 'delete') == 1


def test_qgate_files_exist_delete_present_passes(plan_context):
    """delete + existing target → 0 findings."""
    assert _files_exist_failed(plan_context, 'qgate-delete-present', _EXISTING_FILE, 'delete') == 0
