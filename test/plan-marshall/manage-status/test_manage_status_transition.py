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


def test_delete_plan_destination_claim_does_not_rely_on_an_exists_probe(plan_context, monkeypatch):
    """The incumbent survives even when an ``exists()`` probe reports absence.

    ``destination.exists()`` and the move were a TOCTOU pair: a destination
    created between the two was silently overwritten and the incumbent lesson
    lost. Lying about ``exists()`` simulates exactly that window — the claim
    must be a no-replace create, so the collision is caught by the claim itself
    and reported as the ordinary ``destination_exists`` skip.
    """
    lessons_dir = plan_context.fixture_dir / 'lessons-learned'
    lessons_dir.mkdir(parents=True, exist_ok=True)
    incumbent = lessons_dir / '2025-08-08-008.md'
    incumbent.write_text('id=2025-08-08-008\n\n# Incumbent\n\nCorpus copy.\n')

    plan_dir = plan_context.plan_dir_for('toctou-carry-back')
    (plan_dir / 'lesson-2025-08-08-008.md').write_text(
        'id=2025-08-08-008\ncomponent=foo\ncategory=bug\ncreated=2025-08-08\n\n# Carried\n\nPlan copy.\n'
    )

    original_exists = Path.exists

    def lying_exists(self, *args, **kwargs):
        # Scoped to the one destination path, matched on name rather than
        # equality so a symlinked fixture root (macOS /tmp) still hits.
        if self.name == incumbent.name and self.parent.name == lessons_dir.name:
            return False
        return original_exists(self, *args, **kwargs)

    monkeypatch.setattr(Path, 'exists', lying_exists)

    result = cmd_delete_plan(Namespace(plan_id='toctou-carry-back', no_restore_lessons=False))

    assert result['status'] == 'error'
    assert result['error'] == 'lesson_carry_back_incomplete'
    assert result['skipped_lessons'] == [{'lesson_id': '2025-08-08-008', 'reason': 'destination_exists'}]
    assert result['restored_lesson_ids'] == []

    monkeypatch.undo()
    assert 'Corpus copy.' in incumbent.read_text(), (
        'The incumbent corpus lesson was overwritten — the destination claim '
        'is still gated on a separate exists() probe instead of a no-replace '
        'create, so a destination appearing inside the window is clobbered.'
    )
    # The veto held: the plan directory still holds its only copy.
    assert plan_dir.exists()
    assert (plan_dir / 'lesson-2025-08-08-008.md').exists()


def test_delete_plan_writes_through_the_claim_instead_of_reopening_by_path(plan_context, monkeypatch):
    """The claimed destination is written THROUGH its fd, never reopened by path.

    ``O_EXCL`` buys an atomic collision test, and closing the claim fd to hand
    the PATH back to a copy helper gives that guarantee straight back: the
    reopen is a SECOND name lookup, so an entry substituted under the name in
    between is what gets written — and a ``'wb'`` open follows a symlink,
    truncating whatever it points at. The claim then protects the collision test
    and not the write it exists to make safe.

    The substitution is made deterministic rather than raced: closing a
    descriptor that IS the claimed destination replaces that destination with a
    symlink to an external victim. Only an implementation that closes the claim
    and then addresses the destination by NAME can reach that swap; one that
    writes through the descriptor addresses the claimed inode, which no later
    substitution of the name can redirect.
    """
    victim = plan_context.fixture_dir / 'victim-outside-the-corpus.md'
    victim.write_text('# Victim\n\nAn unrelated file the carry-back has no claim on.\n')

    lessons_dir = plan_context.fixture_dir / 'lessons-learned'
    lessons_dir.mkdir(parents=True, exist_ok=True)
    destination = lessons_dir / '2025-09-09-009.md'

    plan_dir = plan_context.plan_dir_for('claim-writethrough')
    (plan_dir / 'request.md').write_text('# Request')
    (plan_dir / 'lesson-2025-09-09-009.md').write_text(
        'id=2025-09-09-009\ncomponent=foo\ncategory=bug\ncreated=2025-09-09\n\n# Carried\n\nPlan copy.\n'
    )

    real_close = os.close

    def swapping_close(fd):
        # Scoped to a descriptor open on the claimed destination itself, so the
        # swap is reachable only by an implementation that closes the claim
        # before writing. Every unrelated close falls through untouched.
        try:
            claimed = not destination.is_symlink() and os.fstat(fd).st_ino == destination.stat().st_ino
        except OSError:
            claimed = False
        if claimed:
            destination.unlink()
            destination.symlink_to(victim)
        return real_close(fd)

    monkeypatch.setattr(os, 'close', swapping_close)

    result = cmd_delete_plan(Namespace(plan_id='claim-writethrough', no_restore_lessons=False))

    monkeypatch.undo()

    assert result['status'] == 'success'
    assert result['lesson_carry_back_action'] == 'restored'
    assert result['restored_lesson_ids'] == ['2025-09-09-009']

    assert '# Victim' in victim.read_text(), (
        'The carry-back reopened the claimed destination by path, followed a '
        'symlink substituted under that name, and truncated an unrelated file — '
        'the copy must be written through the claim descriptor, which names the '
        'claimed inode and cannot be redirected.'
    )
    # The lesson landed on the claimed inode, not through a substituted name.
    assert not destination.is_symlink()
    assert '# Carried' in destination.read_text()
    assert not plan_dir.exists()


def test_carry_back_vocabulary_agrees_with_restore_from_plan(plan_context):
    """The relationship is a STRICT superset by exactly one value.

    ``CARRY_BACK_ACTIONS`` is now DERIVED as
    ``RESTORE_ACTIONS | {'not_attempted'}``, so "the shared four agree" holds by
    construction and asserting it here would be vacuous. What the construction
    does NOT guarantee is that the union is strict: were ``not_attempted`` ever
    added upstream to ``RESTORE_ACTIONS``, the union would silently become a
    no-op and the two surfaces would claim the false identity the docstring
    explicitly warns against. The strictness and the exact-by-one cardinality
    are what this test pins — they also catch a regression to re-listed
    literals that drop or gain a member.
    """
    lessons_query = load_script_module(
        'plan-marshall', 'manage-lessons', '_lessons_query.py', '_transition_lessons_query'
    )

    # The one thing the union cannot enforce about itself: that it adds a value.
    assert 'not_attempted' not in lessons_query.RESTORE_ACTIONS, (
        'not_attempted leaked into RESTORE_ACTIONS, collapsing the union into a '
        'no-op and making the two vocabularies equal — the identity claim the '
        'CARRY_BACK_ACTIONS docstring exists to deny.'
    )
    assert len(_lifecycle.CARRY_BACK_ACTIONS) == len(lessons_query.RESTORE_ACTIONS) + 1
    assert _lifecycle.CARRY_BACK_ACTIONS > lessons_query.RESTORE_ACTIONS

    # ``restored`` is the value the two used to define incompatibly.
    assert 'restored' in _lifecycle.CARRY_BACK_ACTIONS
    assert 'restore_incomplete' in _lifecycle.CARRY_BACK_ACTIONS


def test_unresolvable_store_over_an_empty_plan_dir_is_still_the_benign_zero(plan_context, monkeypatch):
    """Store-unresolved does NOT force ``plan_dir_unresolved`` unconditionally.

    The mirror of the carried-lesson case above. The directory WAS scanned and
    held no ``lesson-*.md``, so nothing needed to land and ``no_lesson_file`` is
    the honest action even though the corpus was never reached. The
    could-not-look half is carried by ``lesson_store_resolution: unresolved``.

    Pins the precedence the ``CARRY_BACK_ACTIONS`` docstring states: the two
    fields answer different questions — ``action`` says what the scan found,
    ``store_resolution`` says whether the corpus was reachable — and a consumer
    reading either alone gets a wrong answer on this branch.
    """
    import _lessons_io

    monkeypatch.setattr(
        _lessons_io,
        'resolve_lesson_store',
        lambda subpath=_lessons_io.DIR_LESSONS: _lessons_io.LessonStore(
            None, 'unresolved', 'cannot resolve the main-anchored store (test stub)'
        ),
    )

    plan_dir = plan_context.plan_dir_for('unresolved-store-empty-plan')
    (plan_dir / 'request.md').write_text('# Request')

    result = cmd_delete_plan(Namespace(plan_id='unresolved-store-empty-plan', no_restore_lessons=False))

    # No lesson was at risk, so the veto does not fire and the delete proceeds.
    assert result['status'] == 'success'
    assert result['action'] == 'deleted'
    assert result['lesson_carry_back_action'] == 'no_lesson_file'
    assert result['lesson_carry_back_action'] != 'plan_dir_unresolved'
    # The could-not-look fact still rides the payload on the other field.
    assert result['lesson_store_resolution'] == 'unresolved'
    assert result['lessons_dir'] == ''
    assert result['skipped_lessons'] == []
    assert not plan_dir.exists()


def test_cli_transition_not_found_exits_zero(plan_context):
    """Regression: transition with missing status.json exits 0 with TOON error output."""
    result = run_script(SCRIPT_PATH, 'transition', '--plan-id', 'nonexistent', '--completed', '1-init')
    assert result.success, f'Should exit 0, got: {result.stderr}'
    assert 'status: error' in result.stdout
    assert 'file_not_found' in result.stdout


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
    return f'.plan/local/orchestrator/{epic_slug}/plans/PLAN-MBX-01-demo.md'


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


def test_probe_vocabulary_separates_reaching_the_read_from_what_it_saw():
    """``MAILBOX_PROBE_DID_NOT_READ`` is derived, non-empty, and excludes ``read``.

    The set is computed by subtraction from ``MAILBOX_PROBES`` so a member added
    to the vocabulary cannot silently default into the looked-and-found-nothing
    reading. A subtraction that produced the empty set would make every
    could-not-look assertion downstream vacuously true, so its non-emptiness is
    pinned here rather than assumed — and the population it was derived from is
    named, so the guard cannot pass over an empty vocabulary either.
    """
    assert len(_lifecycle.MAILBOX_PROBES) == 3
    assert set(_lifecycle.MAILBOX_PROBES) == {
        _lifecycle.MAILBOX_PROBE_READ,
        _lifecycle.MAILBOX_PROBE_NOT_ORCHESTRATED,
        _lifecycle.MAILBOX_PROBE_UNRESOLVED,
    }
    assert _lifecycle.MAILBOX_PROBE_DID_NOT_READ
    assert _lifecycle.MAILBOX_PROBE_READ not in _lifecycle.MAILBOX_PROBE_DID_NOT_READ
    assert _lifecycle.MAILBOX_PROBE_DID_NOT_READ == frozenset(_lifecycle.MAILBOX_PROBES) - {
        _lifecycle.MAILBOX_PROBE_READ
    }


def test_transition_reports_a_message_delivered_to_the_plans_mailbox(plan_context):
    """The positive control: a delivered message is visible at the hand-over.

    Without this arm every could-not-look assertion below would be satisfied by
    a check-point that never reports mail at all.
    """
    plan_id = 'mailbox-delivered'
    _seed_plan_with_provenance(plan_context, plan_id, _orchestrator_source_id(_MAILBOX_EPIC))
    _deliver(plan_id)

    result = _transition(plan_id)

    assert result['status'] == 'success'
    assert result['next_phase'] == '2-refine'
    mailbox = result['mailbox']
    assert mailbox['checkpoint'] == _lifecycle.MAILBOX_CHECKPOINT_KEY
    assert mailbox['probe'] == _lifecycle.MAILBOX_PROBE_READ
    assert mailbox['epic'] == _MAILBOX_EPIC
    assert mailbox['state'] == _inbox.MAILBOX_STATE_PRESENT
    assert mailbox['count'] == 1
    assert mailbox['live_count'] == 1
    assert mailbox['invalid_count'] == 0


def test_an_empty_mailbox_and_an_absent_one_are_different_zeros(plan_context):
    """``count: 0`` alone does not discriminate — the state is what does.

    Both arms report zero messages. Only one of them looked.
    """
    looked_id = 'mailbox-looked-empty'
    _seed_plan_with_provenance(plan_context, looked_id, _orchestrator_source_id(_MAILBOX_EPIC))
    _mailbox_dir(looked_id).mkdir(parents=True, exist_ok=True)
    looked = _transition(looked_id)['mailbox']

    # Same epic tree (materialized by the arm above), no mailbox for this plan.
    absent_id = 'mailbox-never-addressed'
    _seed_plan_with_provenance(plan_context, absent_id, _orchestrator_source_id(_MAILBOX_EPIC))
    absent = _transition(absent_id)['mailbox']

    assert looked['probe'] == absent['probe'] == _lifecycle.MAILBOX_PROBE_READ
    assert looked['count'] == absent['count'] == 0
    assert looked['state'] == _inbox.MAILBOX_STATE_PRESENT
    assert absent['state'] == _inbox.MAILBOX_STATE_NO_MAILBOX
    assert looked['state'] not in _inbox.MAILBOX_COULD_NOT_LOOK_STATES
    assert absent['state'] in _inbox.MAILBOX_COULD_NOT_LOOK_STATES


def test_an_unreadable_mailbox_degrades_the_block_and_never_the_transition(plan_context):
    """A mailbox that cannot be listed still lets the phase advance.

    The failure is produced the way production would meet it — the addressee
    path is a FILE where a directory belongs — rather than by stubbing the
    reader, so the fail-open claim is exercised through the real read path.
    """
    plan_id = 'mailbox-unreadable'
    _seed_plan_with_provenance(plan_context, plan_id, _orchestrator_source_id(_MAILBOX_EPIC))
    mailbox = _mailbox_dir(plan_id)
    mailbox.parent.mkdir(parents=True, exist_ok=True)
    mailbox.write_text('not a directory\n', encoding='utf-8')

    result = _transition(plan_id)

    assert result['status'] == 'success'
    assert result['completed_phase'] == '1-init'
    assert result['mailbox']['probe'] == _lifecycle.MAILBOX_PROBE_READ
    assert result['mailbox']['state'] == _inbox.MAILBOX_STATE_UNREADABLE
    assert result['mailbox']['count'] == 0


def test_a_plan_with_no_epic_reports_not_orchestrated_and_publishes_no_counts(plan_context):
    """A non-orchestrated plan has no mailbox — a measured fact, not a zero.

    The omission of the count keys is the assertion that matters: a `0` here
    would be byte-identical to a mailbox that was listed and held nothing.
    """
    plan_id = 'mailbox-free-form'
    _seed_plan_with_provenance(plan_context, plan_id, 'a free-form description, not a pointer')

    mailbox = _transition(plan_id)['mailbox']

    assert mailbox['probe'] == _lifecycle.MAILBOX_PROBE_NOT_ORCHESTRATED
    assert mailbox['probe'] in _lifecycle.MAILBOX_PROBE_DID_NOT_READ
    assert 'not_orchestrator_pointer' in mailbox['reason']
    for key in _MAILBOX_COUNT_KEYS:
        assert key not in mailbox, f'{key} was published by a probe that never read a mailbox'
    assert 'state' not in mailbox


def test_an_unreadable_request_md_reports_unresolved_and_publishes_no_counts(plan_context):
    """Provenance that cannot be read establishes nothing about the mailbox."""
    plan_id = 'mailbox-no-request'
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Mailbox Checkpoint',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    # No request.md is written at all — the plan carries no readable provenance.

    result = _transition(plan_id)

    assert result['status'] == 'success'
    mailbox = result['mailbox']
    assert mailbox['probe'] == _lifecycle.MAILBOX_PROBE_UNRESOLVED
    assert 'request.md' in mailbox['reason']
    for key in _MAILBOX_COUNT_KEYS:
        assert key not in mailbox


def test_a_probe_that_raises_is_contained_and_named(plan_context, monkeypatch):
    """An unanticipated probe failure degrades the block, never the transition.

    The blanket containment is what "inherits the fail-open contract in full"
    means at this site, and it is only worth having if the contained failure is
    still NAMED — a swallowed exception would be indistinguishable from a plan
    that simply has no mailbox.
    """
    plan_id = 'mailbox-probe-explodes'
    _seed_plan_with_provenance(plan_context, plan_id, _orchestrator_source_id(_MAILBOX_EPIC))

    def _exploding(_plan_id):
        raise RuntimeError('the reader blew up')

    monkeypatch.setattr(_lifecycle, '_resolve_mailbox_checkpoint', _exploding)

    result = _transition(plan_id)

    assert result['status'] == 'success'
    assert result['next_phase'] == '2-refine'
    mailbox = result['mailbox']
    assert mailbox['checkpoint'] == _lifecycle.MAILBOX_CHECKPOINT_KEY
    assert mailbox['probe'] == _lifecycle.MAILBOX_PROBE_UNRESOLVED
    assert 'RuntimeError' in mailbox['reason']
    assert 'the reader blew up' in mailbox['reason']


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


def test_neither_arm_of_the_matched_pair_blocks_the_phase_write(plan_context):
    """The matched pair, anchored on PERSISTED state rather than on the return.

    One arm's mailbox is readable and carries a message; the other's cannot be
    listed at all. Both must advance the plan, and the assertion is made against
    ``status.json`` rather than against the returned dict — a check-point that
    returned ``status: success`` while skipping ``write_status`` would satisfy a
    return-only assertion and still have blocked the transition.

    The two arms are asserted side by side rather than in separate tests so the
    degraded arm's success is anchored: they are shown to differ in exactly the
    mailbox state, which is what makes this a matched pair instead of two calls
    that happen to agree.
    """
    readable_id = 'mailbox-pair-readable'
    _seed_plan_with_provenance(plan_context, readable_id, _orchestrator_source_id(_MAILBOX_EPIC))
    _deliver(readable_id)

    degraded_id = 'mailbox-pair-degraded'
    _seed_plan_with_provenance(plan_context, degraded_id, _orchestrator_source_id(_MAILBOX_EPIC))
    degraded_mailbox = _mailbox_dir(degraded_id)
    degraded_mailbox.parent.mkdir(parents=True, exist_ok=True)
    degraded_mailbox.write_text('a file where the mailbox directory belongs\n', encoding='utf-8')

    readable = _transition(readable_id)
    degraded = _transition(degraded_id)

    for plan_id, result in ((readable_id, readable), (degraded_id, degraded)):
        assert result['status'] == 'success', f'{plan_id} did not report a successful transition'
        persisted = _persisted_status(plan_context, plan_id)
        assert persisted['current_phase'] == '2-refine', (
            f'{plan_id} reported success but status.json was not advanced — the '
            'check-point blocked the phase write it is forbidden to gate.'
        )
        assert _phase_status(persisted, '1-init') == 'done'
        assert _phase_status(persisted, '2-refine') == 'in_progress'

    # Both arms reached the read; they differ in what the read could see.
    assert readable['mailbox']['probe'] == degraded['mailbox']['probe'] == _lifecycle.MAILBOX_PROBE_READ
    assert readable['mailbox']['state'] == _inbox.MAILBOX_STATE_PRESENT
    assert degraded['mailbox']['state'] == _inbox.MAILBOX_STATE_UNREADABLE
    assert readable['mailbox']['live_count'] == 1
    assert degraded['mailbox']['live_count'] == 0


def test_a_refused_transition_carries_no_mailbox_block(plan_context):
    """The check-point rides a hand-over; a refusal is not one.

    Publishing a mailbox block on a payload whose phase never advanced would
    claim a check-point at a moment the plan did not change hands.
    """
    plan_id = 'mailbox-refused'
    _seed_plan_with_provenance(plan_context, plan_id, _orchestrator_source_id(_MAILBOX_EPIC))
    _deliver(plan_id)

    result = cmd_transition(Namespace(plan_id=plan_id, completed='9-nonexistent'))

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_phase'
    assert 'mailbox' not in result


def test_collect_modified_files_helper_is_removed():
    """The ``_collect_modified_files`` producer no longer exists.

    The footprint ledger was deleted in favour of the on-demand
    compute-footprint verb; the seeding helper must be gone so no code
    path can re-introduce a persisted modified_files write at transition.
    """
    assert not hasattr(_lifecycle, '_collect_modified_files'), (
        '_collect_modified_files must be deleted — the 5-execute transition '
        'no longer seeds references.modified_files (footprint is derived '
        'on-demand via manage-references compute-footprint).'
    )
