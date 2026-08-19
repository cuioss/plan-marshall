#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-status.py read + phase verbs + worktree-path resolution.

Split from test_manage_status.py: covers cmd_read, cmd_set_phase,
cmd_update_phase, cmd_progress, cmd_get_worktree_path (incl.
pre-materialization edge cases), and CLI plumbing/regression entry points.
"""








from conftest import get_script_path, load_script_module

# Script path for CLI plumbing tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')


_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_status_cmd_lifecycle')


_query = load_script_module('plan-marshall', 'manage-status', '_status_query.py', '_status_cmd_query')


cmd_create = _lifecycle.cmd_create


cmd_get_worktree_path = _query.cmd_get_worktree_path


cmd_progress = _query.cmd_progress


cmd_read = _query.cmd_read


cmd_set_phase = _query.cmd_set_phase


cmd_update_phase = _query.cmd_update_phase
