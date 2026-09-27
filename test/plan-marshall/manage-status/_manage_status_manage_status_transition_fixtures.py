#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-status.py transition: delete-plan claim writes, carry-back vocabulary,
and the ``phase-transition`` mailbox check-point the transition payload carries."""

import json
import os
from argparse import Namespace
from pathlib import Path

from _manage_status_transition_fixtures import (
    SCRIPT_PATH,
    _lifecycle,
    cmd_create,
    cmd_delete_plan,
    cmd_transition,
)

from conftest import load_script_module, run_script

#: The channel module, loaded under a name of this module's own — the same
#: collision-proof spelling ``_transition_lessons_query`` below uses — so the
#: load cannot displace a registration another test module holds. Only pure
#: helpers are taken from it (the address composition, the envelope renderer and
#: the state vocabulary), and nothing here monkeypatches it, so a second copy is
#: equivalent to the one the production probe imports.
_inbox = load_script_module(
    'plan-marshall', 'plan-orchestrator', '_orchestrator_inbox.py', '_transition_orchestrator_inbox'
)


# =============================================================================
# Tests: the ``phase-transition`` mailbox check-point on the transition payload
# =============================================================================
#
# A phase transition is one of the two moments a running plan changes hands, so
# it is where a message delivered to that plan's mailbox can first be noticed.
# The block is ADDITIVE and FAIL-OPEN: these tests pin that it reports which
# kind of zero it returned, and that no failure of it can reach the transition.

_MAILBOX_EPIC = 'mailbox-checkpoint-epic'

#: The count keys the block publishes ONLY when a read actually happened. A
#: could-not-look branch omits them rather than zeroing them, so the set is
#: named once here and asserted against on every non-``read`` branch.
_MAILBOX_COUNT_KEYS = ('count', 'live_count', 'invalid_count')


def _orchestrator_source_id(epic_slug: str) -> str:
    """The ``request.md`` provenance pointer phase-1-init records for an orchestrated plan."""
    return f'.plan/orchestrator/{epic_slug}/plans/PLAN-MBX-01-demo.md'


def _seed_plan_with_provenance(plan_context, plan_id: str, source_id: str) -> None:
    """Create a plan at ``1-init`` whose ``request.md`` carries ``source_id``."""
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Mailbox Checkpoint',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'request.md').write_text(
        f'source=orchestrator\nsource_id={source_id}\n\n# Request\n\nDemo request body.\n',
        encoding='utf-8',
    )


def _mailbox_dir(plan_id: str, epic_slug: str = _MAILBOX_EPIC) -> Path:
    """The addressee mailbox, composed by the PRODUCTION address seam.

    Deliberately not hand-joined: the whole point of the check-point is that it
    reads the directory the delivery route writes to, so the fixture resolves
    that path through ``delivery_dir_for_write`` rather than re-deriving a
    second layout the test could agree with while production disagreed.
    """
    # Re-wrapped in ``Path`` because the channel module is loaded dynamically, so
    # its return type is opaque to the type checker — the value itself is already
    # a ``Path`` and the wrap is idempotent.
    return Path(_inbox.delivery_dir_for_write(_inbox.ChannelAddress(epic_slug, plan_id)))


def _deliver(plan_id: str, sender: str = 'sender-plan', epic_slug: str = _MAILBOX_EPIC) -> Path:
    """Write one VALID message into ``plan_id``'s mailbox and return its path."""
    mailbox = _mailbox_dir(plan_id, epic_slug)
    mailbox.mkdir(parents=True, exist_ok=True)
    message = mailbox / f'{sender}-001.md'
    message.write_text(
        _inbox.compose_envelope('plan', sender, epic_slug, 'finding', 'A delivered advisory.'),
        encoding='utf-8',
    )
    return message


def _transition(plan_id: str, completed: str = '1-init') -> dict:
    """Complete an UNGUARDED boundary.

    ``1-init`` is used throughout rather than ``5-execute`` because the
    ``5-execute → 6-finalize`` boundary fires the strict-verify guard and the
    clean-tree post-condition, neither of which has anything to do with the
    mailbox — a seed satisfying them would put handshake and worktree stubs
    between these assertions and the behaviour under test.
    """
    result: dict = cmd_transition(Namespace(plan_id=plan_id, completed=completed))
    return result


def _persisted_status(plan_context, plan_id: str) -> dict:
    """The plan's ``status.json`` as it now stands on disk.

    The returned payload says what the verb REPORTED; this says what it WROTE.
    The "never blocks" claim is about the second, so it is asserted against the
    persisted document rather than against the dict the call handed back.
    """
    data: dict = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
    return data


def _phase_status(status: dict, name: str) -> str:
    """The recorded status of one named phase in a persisted ``status.json``."""
    return str(next(phase['status'] for phase in status['phases'] if phase['name'] == name))
