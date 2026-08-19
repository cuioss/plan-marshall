#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``manage status read`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
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
