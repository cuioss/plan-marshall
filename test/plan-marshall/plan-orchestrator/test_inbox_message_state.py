#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the inbox message-state vocabulary and the foldered archive.

Covers the deliverables of the "a filed message cannot be corrected" plan, each
exercised in-process against the ``_orchestrator_inbox`` handlers under
``PLAN_BASE_DIR`` isolation (via ``plan_context``):

- **amend** (D1): the sanctioned in-place body correction — it preserves
  ``created``, stamps ``amended``, and bumps a monotonic ``revision``, so a
  corrected message is distinguishable from a virgin one **from its envelope
  alone**.
- **supersede** (the replaced half): a retired message flips to
  ``lifecycle=superseded`` and records ``superseded_by``; it stays resolvable
  through ``validate`` while it stops presenting as live in ``list``.
- **validate** (D2): the revision-monotonicity and lifecycle invariants are
  enforced — a claimed amendment with no advanced revision is rejected.
- **close-stream + drain** (D3): a sender marks its stream ended with one
  ``lifecycle=stream-end`` marker, and ``list``'s ``live_count`` /
  ``closed_senders`` let the drain tell an empty queue from a finished one.
- **foldered archive** (D4): the archive is per-sender
  (``inbox/archive/{sender}/``); ``next_sequence`` sees a foldered archived twin
  so no retired sequence is re-opened (the D5(e) control), ``migrate-archive``
  folds a flat archive and reports the count moved per sender, and a sender
  unsafe as a directory name is refused rather than allowed to traverse.
"""

from argparse import Namespace
from pathlib import Path

from conftest import load_script_module

_inbox = load_script_module(
    'plan-marshall', 'plan-orchestrator', '_orchestrator_inbox.py', 'orchestrator_inbox'
)
_orch = load_script_module(
    'plan-marshall', 'plan-orchestrator', 'orchestrator.py', 'orchestrator_script'
)

LIFECYCLE_LIVE = _inbox.LIFECYCLE_LIVE
LIFECYCLE_SUPERSEDED = _inbox.LIFECYCLE_SUPERSEDED
LIFECYCLE_STREAM_END = _inbox.LIFECYCLE_STREAM_END
LIFECYCLES = _inbox.LIFECYCLES
STREAM_END_KIND = _inbox.STREAM_END_KIND
cmd_inbox_amend = _inbox.cmd_inbox_amend
cmd_inbox_archive = _inbox.cmd_inbox_archive
cmd_inbox_close_stream = _inbox.cmd_inbox_close_stream
cmd_inbox_list = _inbox.cmd_inbox_list
cmd_inbox_migrate_archive = _inbox.cmd_inbox_migrate_archive
cmd_inbox_supersede = _inbox.cmd_inbox_supersede
cmd_inbox_validate = _inbox.cmd_inbox_validate
cmd_inbox_write = _inbox.cmd_inbox_write
next_sequence = _inbox.next_sequence
validate_envelope = _inbox.validate_envelope

cmd_scaffold = _orch.cmd_scaffold

EPIC = 'demo-epic'
SENDER = 'demo-plan'
OTHER = 'other-plan'


def _epic_dir(plan_context, slug: str = EPIC) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / slug


def _inbox_dir(plan_context, slug: str = EPIC) -> Path:
    return _epic_dir(plan_context, slug) / 'inbox'


def _payload(tmp_path: Path, body: str = 'the original body', name: str = 'p.md') -> str:
    path = tmp_path / name
    path.write_text(body, encoding='utf-8')
    return str(path)


def _write_args(
    slug: str = EPIC,
    sender_type: str = 'plan',
    sender_id: str = SENDER,
    kind: str = 'landing',
    payload_file: str = '',
) -> Namespace:
    return Namespace(
        slug=slug,
        sender_type=sender_type,
        sender_id=sender_id,
        kind=kind,
        payload_file=payload_file,
    )


def _amend_args(message: str, payload_file: str, slug: str = EPIC) -> Namespace:
    return Namespace(slug=slug, message=message, payload_file=payload_file)


def _supersede_args(message: str, by: str, slug: str = EPIC) -> Namespace:
    return Namespace(slug=slug, message=message, by=by)


def _close_stream_args(
    sender_id: str = SENDER,
    slug: str = EPIC,
    sender_type: str = 'plan',
    reason: str | None = None,
) -> Namespace:
    return Namespace(slug=slug, sender_type=sender_type, sender_id=sender_id, reason=reason)


def _write_message(plan_context, tmp_path, body: str = 'the original body', name: str = 'p.md'):
    """Scaffold-safe write returning the message name."""
    return cmd_inbox_write(_write_args(payload_file=_payload(tmp_path, body, name)))['message']


def _read(plan_context, message: str) -> str:
    return (_inbox_dir(plan_context) / message).read_text(encoding='utf-8')


# =============================================================================
# amend — the sanctioned in-place body correction (D1, D5a, D5b)
# =============================================================================


class TestInboxAmend:
    def test_should_replace_the_body_in_place(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))
        message = _write_message(plan_context, tmp_path, 'first version', 'a.md')

        result = cmd_inbox_amend(
            _amend_args(message, _payload(tmp_path, 'corrected version', 'b.md'))
        )

        assert result['status'] == 'success'
        assert result['operation'] == 'inbox-amend'
        text = _read(plan_context, message)
        assert 'corrected version' in text
        assert 'first version' not in text

    def test_should_stamp_amended_and_bump_revision(self, plan_context, tmp_path):
        # (D5a) An amended message is distinguishable from a virgin one.
        cmd_scaffold(Namespace(slug=EPIC))
        message = _write_message(plan_context, tmp_path, 'v1', 'a.md')

        result = cmd_inbox_amend(_amend_args(message, _payload(tmp_path, 'v2', 'b.md')))

        assert result['revision'] == 1
        assert result['amended']
        text = _read(plan_context, message)
        assert 'revision=1' in text
        assert 'amended=' in text

    def test_amended_message_is_distinguishable_from_a_virgin_one_from_the_envelope(
        self, plan_context, tmp_path
    ):
        # (D5a) The load-bearing claim, checked from the ENVELOPE alone: the
        # amended message's header carries fields the virgin one's does not, so
        # no body diff against a kept copy is needed to see the mutation.
        cmd_scaffold(Namespace(slug=EPIC))
        virgin = _write_message(plan_context, tmp_path, 'untouched', 'a.md')
        amended = _write_message(plan_context, tmp_path, 'to correct', 'b.md')
        cmd_inbox_amend(_amend_args(amended, _payload(tmp_path, 'corrected', 'c.md')))

        virgin_header = _read(plan_context, virgin).split('\n\n', 1)[0]
        amended_header = _read(plan_context, amended).split('\n\n', 1)[0]

        assert 'amended=' not in virgin_header
        assert 'revision=' not in virgin_header
        assert 'amended=' in amended_header
        assert 'revision=1' in amended_header
        assert virgin_header != amended_header

    def test_should_preserve_created_across_an_amend(self, plan_context, tmp_path):
        # (D5b) ``created`` survives an amend — it keeps naming the message's
        # first filing rather than being restamped to the correction instant. A
        # distinctive PAST timestamp is planted so a naive amend that restamps to
        # "now" is caught regardless of the clock's one-second granularity (a
        # restamp landing in the same second as the write would otherwise slip
        # past a same-instant comparison).
        cmd_scaffold(Namespace(slug=EPIC))
        planted = _inbox_dir(plan_context) / f'{SENDER}-001.md'
        planted.write_text(_state_message(), encoding='utf-8')
        assert 'created=2020-01-01T00:00:00Z' in planted.read_text(encoding='utf-8')

        cmd_inbox_amend(_amend_args(planted.name, _payload(tmp_path, 'corrected', 'b.md')))

        _, error_code, after = validate_envelope(_read(plan_context, planted.name))
        assert error_code is None
        assert after['created'] == '2020-01-01T00:00:00Z'

    def test_should_bump_revision_monotonically_across_two_amends(
        self, plan_context, tmp_path
    ):
        cmd_scaffold(Namespace(slug=EPIC))
        message = _write_message(plan_context, tmp_path, 'v1', 'a.md')

        first = cmd_inbox_amend(_amend_args(message, _payload(tmp_path, 'v2', 'b.md')))
        second = cmd_inbox_amend(_amend_args(message, _payload(tmp_path, 'v3', 'c.md')))

        assert first['revision'] == 1
        assert second['revision'] == 2
        assert 'revision=2' in _read(plan_context, message)

    def test_amended_message_still_validates_green(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))
        message = _write_message(plan_context, tmp_path, 'v1', 'a.md')
        cmd_inbox_amend(_amend_args(message, _payload(tmp_path, 'v2', 'b.md')))

        result = cmd_inbox_validate(Namespace(slug=EPIC, message=message))

        assert result['status'] == 'success'
        assert result['revision'] == '1'
        assert result['lifecycle'] == LIFECYCLE_LIVE

    def test_should_reject_an_unsafe_slug(self, plan_context, tmp_path):
        result = cmd_inbox_amend(
            _amend_args('x-001.md', _payload(tmp_path), slug='../evil')
        )

        assert result['error'] == 'invalid_slug'

    def test_should_reject_a_path_shaped_message(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))

        result = cmd_inbox_amend(_amend_args('../status.json', _payload(tmp_path)))

        assert result['error'] == 'invalid_message_name'

    def test_should_reject_a_missing_payload(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))
        message = _write_message(plan_context, tmp_path, 'v1', 'a.md')

        result = cmd_inbox_amend(_amend_args(message, str(tmp_path / 'absent.md')))

        assert result['error'] == 'payload_not_found'

    def test_should_reject_a_missing_message(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))

        result = cmd_inbox_amend(_amend_args('absent-001.md', _payload(tmp_path)))

        assert result['error'] == 'file_not_found'

    def test_should_refuse_to_amend_a_consumed_message(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))
        message = _write_message(plan_context, tmp_path, 'v1', 'a.md')
        cmd_inbox_archive(Namespace(slug=EPIC, message=message, as_name=None))

        result = cmd_inbox_amend(_amend_args(message, _payload(tmp_path, 'v2', 'b.md')))

        assert result['error'] == 'not_live'

    def test_should_refuse_to_amend_a_superseded_message(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))
        first = _write_message(plan_context, tmp_path, 'v1', 'a.md')
        second = _write_message(plan_context, tmp_path, 'successor', 'b.md')
        cmd_inbox_supersede(_supersede_args(first, second))

        result = cmd_inbox_amend(_amend_args(first, _payload(tmp_path, 'v2', 'c.md')))

        assert result['error'] == 'not_amendable'


# =============================================================================
# supersede — the replaced half (D5c)
# =============================================================================


class TestInboxSupersede:
    def test_should_flip_lifecycle_and_record_successor(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))
        first = _write_message(plan_context, tmp_path, 'wrong body', 'a.md')
        second = _write_message(plan_context, tmp_path, 'the successor', 'b.md')

        result = cmd_inbox_supersede(_supersede_args(first, second))

        assert result['status'] == 'success'
        assert result['lifecycle'] == LIFECYCLE_SUPERSEDED
        assert result['superseded_by'] == second
        text = _read(plan_context, first)
        assert f'lifecycle={LIFECYCLE_SUPERSEDED}' in text
        assert f'superseded_by={second}' in text

    def test_superseded_message_stops_appearing_as_live_but_stays_resolvable(
        self, plan_context, tmp_path
    ):
        # (D5c) The retired message drops out of the live set yet still resolves.
        cmd_scaffold(Namespace(slug=EPIC))
        first = _write_message(plan_context, tmp_path, 'wrong body', 'a.md')
        second = _write_message(plan_context, tmp_path, 'the successor', 'b.md')
        cmd_inbox_supersede(_supersede_args(first, second))

        listing = cmd_inbox_list(Namespace(slug=EPIC))
        rows = {row['name']: row for row in listing['messages']}
        resolved = cmd_inbox_validate(Namespace(slug=EPIC, message=first))

        # Stops presenting as live: flagged superseded and out of live_count.
        assert rows[first]['lifecycle'] == LIFECYCLE_SUPERSEDED
        assert listing['live_count'] == 1  # only the successor is live
        assert rows[second]['lifecycle'] == LIFECYCLE_LIVE
        # Stays resolvable: validate still finds and accepts it.
        assert resolved['status'] == 'success'
        assert resolved['lifecycle'] == LIFECYCLE_SUPERSEDED
        assert resolved['superseded_by'] == second

    def test_should_preserve_the_body_byte_for_byte(self, plan_context, tmp_path):
        # The inbox is append-only for content: supersede records state in the
        # envelope and never rewrites the body into a redirect stub.
        cmd_scaffold(Namespace(slug=EPIC))
        first = _write_message(plan_context, tmp_path, 'the original narrative', 'a.md')
        second = _write_message(plan_context, tmp_path, 'the successor', 'b.md')
        body_before = _read(plan_context, first).split('\n\n', 1)[1]

        cmd_inbox_supersede(_supersede_args(first, second))

        assert _read(plan_context, first).split('\n\n', 1)[1] == body_before

    def test_should_refuse_a_self_supersede(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))
        message = _write_message(plan_context, tmp_path, 'v1', 'a.md')

        result = cmd_inbox_supersede(_supersede_args(message, message))

        assert result['error'] == 'self_supersede'

    def test_should_refuse_a_missing_successor(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))
        message = _write_message(plan_context, tmp_path, 'v1', 'a.md')

        result = cmd_inbox_supersede(_supersede_args(message, 'absent-001.md'))

        assert result['error'] == 'successor_not_found'

    def test_should_refuse_a_path_shaped_successor(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))
        message = _write_message(plan_context, tmp_path, 'v1', 'a.md')

        result = cmd_inbox_supersede(_supersede_args(message, '../evil-001.md'))

        assert result['error'] == 'invalid_successor_name'

    def test_should_refuse_to_supersede_a_stream_end_marker(self, plan_context, tmp_path):
        # A terminal control marker cannot be retired-by-successor: flipping it to
        # superseded would drop the sender from closed_senders and re-open the
        # stream. The successor must still exist so the refusal is the marker
        # guard firing, not successor_not_found.
        cmd_scaffold(Namespace(slug=EPIC))
        marker = cmd_inbox_close_stream(_close_stream_args())['message']
        successor = _write_message(plan_context, tmp_path, 'successor', 'b.md')

        result = cmd_inbox_supersede(_supersede_args(marker, successor))

        assert result['error'] == 'not_supersedable'
        # The marker still closes the stream — the guard preserved the signal.
        assert cmd_inbox_list(Namespace(slug=EPIC))['closed_senders'] == [SENDER]


# =============================================================================
# validate — the revision-monotonicity and lifecycle invariants (D2, D5d)
# =============================================================================


def _state_message(**state: str) -> str:
    """Hand-build a valid base message plus the supplied state header lines."""
    base = [
        'envelope_version=1',
        'sender_type=plan',
        f'sender_id={SENDER}',
        f'epic={EPIC}',
        'kind=landing',
        'created=2020-01-01T00:00:00Z',
    ]
    base.extend(f'{key}={value}' for key, value in state.items())
    return '\n'.join(base) + '\n\npayload prose\n'


class TestStateFieldValidation:
    def test_should_reject_amended_without_a_revision_bump(self):
        # (D5d) Monotonicity: a claimed amendment with no advanced revision.
        ok, error_code, _ = validate_envelope(
            _state_message(amended='2020-02-02T00:00:00Z')
        )

        assert (ok, error_code) == (False, 'revision_not_monotonic')

    def test_should_reject_a_revision_bump_without_an_amended_stamp(self):
        ok, error_code, _ = validate_envelope(_state_message(revision='2'))

        assert (ok, error_code) == (False, 'revision_not_monotonic')

    def test_should_accept_a_consistent_amended_revision_pair(self):
        ok, error_code, _ = validate_envelope(
            _state_message(revision='1', amended='2020-02-02T00:00:00Z')
        )

        assert (ok, error_code) == (True, None)

    def test_should_reject_a_non_integer_revision(self):
        ok, error_code, _ = validate_envelope(_state_message(revision='latest'))

        assert (ok, error_code) == (False, 'invalid_revision')

    def test_should_reject_a_lifecycle_outside_the_vocabulary(self):
        ok, error_code, _ = validate_envelope(_state_message(lifecycle='retired'))

        assert (ok, error_code) == (False, 'invalid_lifecycle')

    def test_should_reject_superseded_without_a_pointer(self):
        ok, error_code, _ = validate_envelope(
            _state_message(lifecycle=LIFECYCLE_SUPERSEDED)
        )

        assert (ok, error_code) == (False, 'invalid_supersede_state')

    def test_should_reject_a_pointer_without_the_superseded_lifecycle(self):
        ok, error_code, _ = validate_envelope(_state_message(superseded_by='x-002.md'))

        assert (ok, error_code) == (False, 'invalid_supersede_state')

    def test_should_only_report_lifecycles_from_the_module_vocabulary(self):
        # Two-sided: every declared lifecycle is reachable through a real
        # message, and none reports one outside the module's own frozenset.
        live = validate_envelope(_state_message())[2].get('lifecycle', LIFECYCLE_LIVE)
        superseded = validate_envelope(
            _state_message(lifecycle=LIFECYCLE_SUPERSEDED, superseded_by='x-002.md')
        )[2]['lifecycle']
        stream_end = validate_envelope(
            _state_message(lifecycle=LIFECYCLE_STREAM_END)
        )[2]['lifecycle']

        assert {live, superseded, stream_end} == LIFECYCLES


# =============================================================================
# close-stream + drain — stream termination (D3)
# =============================================================================


class TestCloseStreamAndDrain:
    def test_should_file_a_stream_end_marker(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))

        result = cmd_inbox_close_stream(_close_stream_args())

        assert result['status'] == 'success'
        assert result['lifecycle'] == LIFECYCLE_STREAM_END
        text = _read(plan_context, result['message'])
        assert f'lifecycle={LIFECYCLE_STREAM_END}' in text
        assert f'kind={STREAM_END_KIND}' in text

    def test_stream_end_marker_validates_green(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))
        marker = cmd_inbox_close_stream(_close_stream_args())['message']

        result = cmd_inbox_validate(Namespace(slug=EPIC, message=marker))

        assert result['status'] == 'success'
        assert result['lifecycle'] == LIFECYCLE_STREAM_END

    def test_close_stream_allocates_a_fresh_sequence(self, plan_context, tmp_path):
        # The marker claims a sequence like any message, so a later write for the
        # same sender never re-uses the marker's number.
        cmd_scaffold(Namespace(slug=EPIC))
        _write_message(plan_context, tmp_path, 'v1', 'a.md')
        marker = cmd_inbox_close_stream(_close_stream_args())['message']

        assert marker == f'{SENDER}-002.md'

    def test_drain_tells_an_empty_queue_from_a_finished_one(self, plan_context, tmp_path):
        # (D3) The drain distinguishes empty (live_count 0, no closed sender)
        # from finished (live_count 0, the sender has closed its stream).
        cmd_scaffold(Namespace(slug=EPIC))
        empty = cmd_inbox_list(Namespace(slug=EPIC))
        assert empty['live_count'] == 0
        assert empty['closed_senders'] == []

        cmd_inbox_close_stream(_close_stream_args())
        finished = cmd_inbox_list(Namespace(slug=EPIC))

        assert finished['live_count'] == 0
        assert finished['closed_senders'] == [SENDER]

    def test_live_count_excludes_the_stream_end_marker(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))
        _write_message(plan_context, tmp_path, 'live work', 'a.md')
        cmd_inbox_close_stream(_close_stream_args())

        listing = cmd_inbox_list(Namespace(slug=EPIC))

        assert listing['count'] == 2  # the payload message and the marker
        assert listing['live_count'] == 1  # only the payload message is live
        assert listing['closed_senders'] == [SENDER]

    def test_should_reject_an_unsafe_sender_id(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))

        result = cmd_inbox_close_stream(_close_stream_args(sender_id='../escape'))

        assert result['error'] == 'invalid_sender_id'


# =============================================================================
# list surfaces the state (D2)
# =============================================================================


class TestListSurfacesState:
    def test_row_carries_lifecycle_and_revision(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))
        virgin = _write_message(plan_context, tmp_path, 'v1', 'a.md')
        amended = _write_message(plan_context, tmp_path, 'to fix', 'b.md')
        cmd_inbox_amend(_amend_args(amended, _payload(tmp_path, 'fixed', 'c.md')))

        rows = {row['name']: row for row in cmd_inbox_list(Namespace(slug=EPIC))['messages']}

        # A virgin row and a revised row are visibly different in the listing.
        assert rows[virgin]['revision'] == '0'
        assert rows[virgin]['lifecycle'] == LIFECYCLE_LIVE
        assert rows[amended]['revision'] == '1'
        assert rows[virgin] != rows[amended]


# =============================================================================
# foldered archive — D4 and the D5(e) control
# =============================================================================


class TestFolderedArchive:
    def test_next_sequence_advances_past_a_foldered_archived_message(self, tmp_path):
        # (D5e) THE control. The sender's only prior message is archived in a
        # per-sender SUBDIRECTORY. A naive flat-only scan proposes 001 and hands
        # back a number whose foldered twin already exists — silent reuse. The
        # foldered scan sees it and proposes 002.
        sender_archive = tmp_path / 'archive' / SENDER
        sender_archive.mkdir(parents=True)
        (sender_archive / f'{SENDER}-001.md').write_text('retired\n', encoding='utf-8')

        assert next_sequence(tmp_path, SENDER) == 2

    def test_next_sequence_takes_the_max_across_flat_and_foldered_twins(self, tmp_path):
        # A partly-migrated archive holds a flat twin AND a foldered one; the max
        # spans both so no sequence is re-opened mid-migration.
        archive = tmp_path / 'archive'
        (archive / SENDER).mkdir(parents=True)
        (archive / f'{SENDER}-004.md').write_text('flat\n', encoding='utf-8')
        (archive / SENDER / f'{SENDER}-007.md').write_text('foldered\n', encoding='utf-8')

        assert next_sequence(tmp_path, SENDER) == 8

    def test_archive_writes_into_a_per_sender_subdirectory(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))
        message = _write_message(plan_context, tmp_path, 'body', 'a.md')

        result = cmd_inbox_archive(Namespace(slug=EPIC, message=message, as_name=None))

        assert result['archived_to'].endswith(f'archive/{SENDER}/{message}')
        assert (_inbox_dir(plan_context) / 'archive' / SENDER / message).is_file()

    def test_archive_refuses_a_sender_unsafe_as_a_directory_name(
        self, plan_context, tmp_path
    ):
        # (D4 safety) A ``..``-shaped sender segment is a valid FILENAME
        # component but would traverse out of the archive as a DIRECTORY. It is
        # refused fail-closed rather than folded into ``archive/../``.
        cmd_scaffold(Namespace(slug=EPIC))
        inbox = _inbox_dir(plan_context)
        planted = inbox / '..-001.md'
        planted.write_text('hand-planted\n', encoding='utf-8')

        result = cmd_inbox_archive(Namespace(slug=EPIC, message=planted.name, as_name=None))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_message_name'
        # The refusal left the source in place — nothing traversed out of the
        # archive, and no sibling of inbox/ was written.
        assert planted.is_file()
        assert not (inbox.parent / '..-001.md').exists()

    def test_migrate_archive_folds_flat_and_reports_per_sender_counts(
        self, plan_context, tmp_path
    ):
        cmd_scaffold(Namespace(slug=EPIC))
        archive = _inbox_dir(plan_context) / 'archive'
        archive.mkdir(parents=True, exist_ok=True)
        for name in (f'{SENDER}-001.md', f'{SENDER}-002.md', f'{OTHER}-001.md'):
            (archive / name).write_text('flat\n', encoding='utf-8')

        result = cmd_inbox_migrate_archive(Namespace(slug=EPIC))

        assert result['status'] == 'success'
        assert result['moved_total'] == 3
        assert result['moved_by_sender'] == {SENDER: 2, OTHER: 1}
        # The flat files are gone; the foldered twins exist.
        assert not (archive / f'{SENDER}-001.md').exists()
        assert (archive / SENDER / f'{SENDER}-001.md').is_file()
        assert (archive / SENDER / f'{SENDER}-002.md').is_file()
        assert (archive / OTHER / f'{OTHER}-001.md').is_file()

    def test_migrate_archive_is_idempotent(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))
        archive = _inbox_dir(plan_context) / 'archive'
        archive.mkdir(parents=True, exist_ok=True)
        (archive / f'{SENDER}-001.md').write_text('flat\n', encoding='utf-8')
        cmd_inbox_migrate_archive(Namespace(slug=EPIC))

        second = cmd_inbox_migrate_archive(Namespace(slug=EPIC))

        assert second['moved_total'] == 0

    def test_migrate_archive_skips_a_sender_unsafe_as_a_directory(
        self, plan_context, tmp_path
    ):
        cmd_scaffold(Namespace(slug=EPIC))
        archive = _inbox_dir(plan_context) / 'archive'
        archive.mkdir(parents=True, exist_ok=True)
        (archive / '..-001.md').write_text('unsafe\n', encoding='utf-8')

        result = cmd_inbox_migrate_archive(Namespace(slug=EPIC))

        assert result['moved_total'] == 0
        assert any(row['reason'] == 'unsafe_sender' for row in result['skipped'])
        # The unsafe file was left in place, not folded into a traversing path.
        assert (archive / '..-001.md').is_file()

    def test_write_then_drain_then_write_folds_and_never_reuses_a_sequence(
        self, plan_context, tmp_path
    ):
        # The full cycle end-to-end: a drained sender's next write lands above
        # the foldered archived twin, and archives cleanly under the sender dir.
        cmd_scaffold(Namespace(slug=EPIC))
        first = _write_message(plan_context, tmp_path, 'first', 'a.md')
        cmd_inbox_archive(Namespace(slug=EPIC, message=first, as_name=None))

        second = _write_message(plan_context, tmp_path, 'second', 'b.md')
        archived = cmd_inbox_archive(Namespace(slug=EPIC, message=second, as_name=None))

        assert second == f'{SENDER}-002.md'
        assert archived['status'] == 'success'
        sender_archive = _inbox_dir(plan_context) / 'archive' / SENDER
        assert sorted(p.name for p in sender_archive.iterdir()) == [
            f'{SENDER}-001.md',
            f'{SENDER}-002.md',
        ]
