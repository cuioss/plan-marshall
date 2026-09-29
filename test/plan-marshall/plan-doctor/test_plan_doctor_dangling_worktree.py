#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The plan-doctor ``dangling-worktree`` rule, including the reserved ledger tree.

A direct child of the worktree root with no ``plans/{name}/`` directory is
dangling — except the reserved shared orchestrator ledger worktree, which has no
plan directory by design and is never reported.

That exclusion is keyed on the reserved name through
``is_orchestrator_worktree_dir``, and it must hold on its own: the plan-id
validator happens to reject the reserved name's leading underscore, so a test
that left the validator in place would pass against a rule with no reserved-tree
skip at all. The in-process cases therefore patch the validator to accept every
name, and carry a non-reserved underscore entry as the control that shows the
patch took effect — that entry IS reported once the validator admits it.

The CLI cases run ``scan --all --no-emit`` through ``run_script``; the
validator-independence cases call the scanner in-process, because a patch in this
process cannot reach a subprocess.
"""

from __future__ import annotations

import pytest
from _doctor_fixtures import make_healthy_plan, make_worktree_dir, seed_lesson_inventory
from marketplace_paths import ORCHESTRATOR_WORKTREE_KEY

from conftest import get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-doctor', 'plan_doctor.py')

plan_doctor = load_script_module('plan-marshall', 'plan-doctor', 'plan_doctor.py', register=False)

_LIVE_PLAN = 'live-plan-with-wt'
_DANGLING_PLAN = 'dangling-wt-no-plan'
#: A non-reserved name the plan-id validator rejects for the same reason it
#: rejects the reserved key — the leading underscore.
_UNDERSCORE_SCRATCH = '_scratch'


def _dangling_ids_from_cli() -> set[str]:
    result = run_script(SCRIPT_PATH, 'scan', '--all', '--no-emit')
    payload = result.toon()
    raw = payload.get('findings', []) or []
    findings = [raw] if isinstance(raw, dict) else list(raw)
    return {finding['plan_id'] for finding in findings if finding.get('reason') == 'dangling_worktree'}


@pytest.fixture
def worktree_store(plan_context):
    """A store holding a live plan with its worktree and one dangling worktree."""
    seed_lesson_inventory(plan_context.fixture_dir)
    make_healthy_plan(plan_context.fixture_dir / 'plans' / _LIVE_PLAN)
    make_worktree_dir(plan_context.fixture_dir, _LIVE_PLAN)
    make_worktree_dir(plan_context.fixture_dir, _DANGLING_PLAN)
    return plan_context.fixture_dir


def test_worktree_without_plan_dir_is_dangling_and_live_one_is_not(worktree_store):
    dangling = _dangling_ids_from_cli()

    assert _DANGLING_PLAN in dangling
    assert _LIVE_PLAN not in dangling


def test_reserved_ledger_worktree_is_never_reported_dangling(worktree_store):
    make_worktree_dir(worktree_store, ORCHESTRATOR_WORKTREE_KEY)
    assert not (worktree_store / 'plans' / ORCHESTRATOR_WORKTREE_KEY).exists()

    dangling = _dangling_ids_from_cli()

    assert ORCHESTRATOR_WORKTREE_KEY not in dangling
    assert _DANGLING_PLAN in dangling


def test_reserved_skip_holds_when_the_validator_accepts_every_name(worktree_store, monkeypatch):
    make_worktree_dir(worktree_store, ORCHESTRATOR_WORKTREE_KEY)
    make_worktree_dir(worktree_store, _UNDERSCORE_SCRATCH)
    monkeypatch.setattr(plan_doctor, 'is_valid_plan_id', lambda _name: True)

    dangling = {finding['plan_id'] for finding in plan_doctor._scan_dangling_worktrees()}

    assert ORCHESTRATOR_WORKTREE_KEY not in dangling
    assert dangling == {_DANGLING_PLAN, _UNDERSCORE_SCRATCH}


def test_underscore_control_is_filtered_only_by_the_validator(worktree_store):
    make_worktree_dir(worktree_store, _UNDERSCORE_SCRATCH)

    dangling = {finding['plan_id'] for finding in plan_doctor._scan_dangling_worktrees()}

    assert dangling == {_DANGLING_PLAN}
