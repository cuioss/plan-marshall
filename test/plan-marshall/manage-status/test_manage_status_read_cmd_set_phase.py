#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-status.py read + phase verbs + worktree-path resolution."""


from argparse import Namespace
from pathlib import Path

from _manage_status_read_fixtures import SCRIPT_PATH, _query, cmd_create, cmd_set_phase

# =============================================================================
# Tests: get alias for read (subprocess / CLI plumbing)
# =============================================================================

def test_script_source_uses_canonical_local_plans_path():
    """The script source references .plan/local/plans, not the legacy form.

    Regression guard for the path-consolidation sweep: the module docstring's
    storage line and the ``list-orphans`` help text must spell the plan
    location as ``.plan/local/plans/`` — the legacy bare ``.plan/plans/`` form
    is incorrect since runtime state moved under ``.plan/local``.
    """
    import re

    source = Path(SCRIPT_PATH).read_text(encoding='utf-8')
    assert '.plan/local/plans/' in source
    legacy = re.findall(r'(?<!local/)\.plan/plans/', source)
    assert legacy == [], f'Legacy .plan/plans/ strings remain: {legacy}'


# =============================================================================
# Regression Tests: cmd_set_phase fires the persisted-title-state-write drive seam
# =============================================================================
#
# cmd_set_phase is a current_phase writer, so it fires the shared _surface_drive
# seam (bind + repaint) AFTER write_status. An invalid-phase error returns before
# write_status, so the seam must NOT fire on that path.


def test_cmd_set_phase_fires_drive_seam_after_write(plan_context, monkeypatch):
    """cmd_set_phase fires _surface_drive exactly once (with the plan_id) after the write."""
    cmd_create(
        Namespace(
            plan_id='setphase-drive',
            title='Set Phase Drive',
            phases='1-init,2-refine,3-outline',
            force=False,
        )
    )
    calls = []
    monkeypatch.setattr(_query, '_surface_drive', lambda pid: calls.append(pid))

    result = cmd_set_phase(Namespace(plan_id='setphase-drive', phase='3-outline'))

    assert result['status'] == 'success'
    assert calls == ['setphase-drive'], (
        f'cmd_set_phase must fire the drive seam once with the plan_id, got {calls!r}.'
    )


def test_cmd_set_phase_invalid_does_not_fire_drive_seam(plan_context, monkeypatch):
    """An invalid-phase error returns before write_status — the seam must NOT fire."""
    cmd_create(
        Namespace(plan_id='setphase-invalid-drive', title='Invalid', phases='1-init,2-refine', force=False)
    )
    calls = []
    monkeypatch.setattr(_query, '_surface_drive', lambda pid: calls.append(pid))

    result = cmd_set_phase(Namespace(plan_id='setphase-invalid-drive', phase='nonexistent'))

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_phase'
    assert calls == [], (
        f'The drive seam must not fire when set-phase is rejected before '
        f'write_status, got {calls!r}.'
    )
