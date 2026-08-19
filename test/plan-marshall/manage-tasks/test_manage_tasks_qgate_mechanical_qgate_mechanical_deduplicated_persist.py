#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``qgate-mechanical-checks`` subcommand of manage-tasks.

The subcommand runs the deterministic Q-Gate checks over the tasks and parent
deliverables of a plan, emitting one finding per failure under ``--source
qgate`` so the existing phase-4-plan aggregate consumes them without
modification. The check names this file asserts against are enumerated once, in
:data:`_ALL_CHECKS`, and read from the result rather than restated per test.

The CLOSURE checks (``declared_set_closure``,
``declared_scope_reconciliation``) have their own suite in
``test_qgate_closure.py``; here they are exercised only as members of the full
result — a fixture in this file must be a well-formed plan except for the one
fault the test injects.
"""


from __future__ import annotations

from _manage_tasks_qgate_mechanical_fixtures import (
    _load_module,
    _ns,
    _seed_one_coverage_failure,
    cmd_qgate_mechanical,
)


def test_qgate_mechanical_deduplicated_persist_stays_benign(plan_context):
    """A ``deduplicated`` outcome is benign — it must not collapse onto a rejection.

    The second emit run re-detects the same failure, so the primitive dedups it.
    The record is still in the store, so no persist failure is reported.
    """
    _seed_one_coverage_failure(plan_context, 'qgate-persist-dedup')

    first = cmd_qgate_mechanical(_ns('qgate-persist-dedup', no_emit=False))
    assert first['findings_emitted'] == 1
    assert first['qgate_persist_failed'] is False

    second = cmd_qgate_mechanical(_ns('qgate-persist-dedup', no_emit=False))

    assert second['qgate_persist_failed'] is False
    assert second['qgate_persist_failures'] == []
    # ``findings_emitted`` counts appends, and a dedup appends nothing — but that
    # zero means "already in the store", never "rejected".
    assert second['findings_emitted'] == 0


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
