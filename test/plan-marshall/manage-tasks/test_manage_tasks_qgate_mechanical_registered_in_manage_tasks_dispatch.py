#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``qgate-mechanical-checks`` subcommand of manage-tasks."""


from __future__ import annotations

from _manage_tasks_qgate_mechanical_fixtures import _load_module, cmd_qgate_mechanical

# =============================================================================
# Dispatch via manage-tasks.py registry
# =============================================================================


def test_qgate_mechanical_registered_in_manage_tasks_dispatch():
    """The subcommand is wired in ``COMMANDS`` so the dispatcher routes to it."""
    manage_tasks = _load_module('_manage_tasks_dispatch_check', 'manage-tasks.py')
    assert 'qgate-mechanical-checks' in manage_tasks.COMMANDS
    assert manage_tasks.COMMANDS['qgate-mechanical-checks'] is cmd_qgate_mechanical or callable(
        manage_tasks.COMMANDS['qgate-mechanical-checks']
    )
