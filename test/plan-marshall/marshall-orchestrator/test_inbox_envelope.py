#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the inbox envelope module backing ``orchestrator.py inbox``.

This module is the SINGLE home of the exhaustive validator sweep: all seven
rejection classes are exercised in-process against hand-built messages here,
and the CLI-level contract test carries exactly one representative class
end-to-end rather than re-enumerating the schema.

Covers, under ``PLAN_BASE_DIR`` isolation (via ``plan_context``):

- ``compose_envelope`` / ``validate_envelope``: header round-trip and every
  validator error code, in the fixed check order.
- ``next_sequence`` / ``allocate_message_path``: per-sender allocation,
  zero-padding, and the ``O_EXCL`` concurrent-claim retry.
- ``classify_source_id``: positive, negative, and traversal cases.
- ``cmd_inbox_write`` / ``cmd_inbox_validate`` / ``cmd_inbox_detect``: the
  handler surface, including every refusal class.
"""

from argparse import Namespace
from pathlib import Path

from conftest import load_script_module

_inbox = load_script_module(
    'plan-marshall', 'marshall-orchestrator', '_orchestrator_inbox.py', 'orchestrator_inbox'
)
_orch = load_script_module(
    'plan-marshall', 'marshall-orchestrator', 'orchestrator.py', 'orchestrator_script'
)

ENVELOPE_VERSION = _inbox.ENVELOPE_VERSION
HEADER_FIELDS = _inbox.HEADER_FIELDS
KINDS = _inbox.KINDS
SENDER_TYPES = _inbox.SENDER_TYPES
allocate_message_path = _inbox.allocate_message_path
classify_source_id = _inbox.classify_source_id
cmd_inbox_detect = _inbox.cmd_inbox_detect
cmd_inbox_validate = _inbox.cmd_inbox_validate
cmd_inbox_write = _inbox.cmd_inbox_write
compose_envelope = _inbox.compose_envelope
next_sequence = _inbox.next_sequence
validate_envelope = _inbox.validate_envelope

cmd_scaffold = _orch.cmd_scaffold

EPIC = 'demo-epic'
SENDER = 'demo-plan'


def _epic_dir(plan_context, slug: str = EPIC) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / slug


def _inbox_dir(plan_context, slug: str = EPIC) -> Path:
    return _epic_dir(plan_context, slug) / 'inbox'


def _header_text(**overrides: str) -> str:
    """Hand-build a message header block, overriding named fields."""
    values = {
        'envelope_version': str(ENVELOPE_VERSION),
        'sender_type': 'plan',
        'sender_id': SENDER,
        'epic': EPIC,
        'kind': 'landing',
        'created': '2020-01-01T00:00:00Z',
    }
    values.update(overrides)
    return '\n'.join(f'{key}={values[key]}' for key in HEADER_FIELDS if key in values)


def _message(body: str = 'payload prose', **overrides: str) -> str:
    return f'{_header_text(**overrides)}\n\n{body}\n'


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


def _payload(tmp_path: Path, body: str = 'the landing narrative') -> str:
    path = tmp_path / 'inbox-payload.md'
    path.write_text(body, encoding='utf-8')
    return str(path)


# =============================================================================
# compose_envelope / validate_envelope — round trip
# =============================================================================


class TestEnvelopeRoundTrip:
    def test_should_carry_every_header_field(self):
        text = compose_envelope('plan', SENDER, EPIC, 'landing', 'body prose')

        ok, error_code, header = validate_envelope(text)

        assert ok is True
        assert error_code is None
        assert set(header) == set(HEADER_FIELDS)

    def test_should_preserve_the_composed_values(self):
        text = compose_envelope('orchestrator', 'other-epic', EPIC, 'finding', 'body')

        _, _, header = validate_envelope(text)

        assert header['envelope_version'] == str(ENVELOPE_VERSION)
        assert header['sender_type'] == 'orchestrator'
        assert header['sender_id'] == 'other-epic'
        assert header['epic'] == EPIC
        assert header['kind'] == 'finding'

    def test_should_separate_header_and_body_with_one_blank_line(self):
        text = compose_envelope('plan', SENDER, EPIC, 'landing', '## Heading\n\nprose')

        assert text.split('\n\n', 1)[1].startswith('## Heading')

    def test_should_accept_every_declared_kind(self):
        for kind in sorted(KINDS):
            ok, _, _ = validate_envelope(
                compose_envelope('plan', SENDER, EPIC, kind, 'body')
            )
            assert ok is True, kind

    def test_should_accept_every_declared_sender_type(self):
        for sender_type in sorted(SENDER_TYPES):
            ok, _, _ = validate_envelope(
                compose_envelope(sender_type, SENDER, EPIC, 'landing', 'body')
            )
            assert ok is True, sender_type

    def test_should_accept_matching_epic_and_filename_context(self):
        text = compose_envelope('plan', SENDER, EPIC, 'landing', 'body')

        ok, error_code, _ = validate_envelope(
            text, expected_epic=EPIC, filename=f'{SENDER}-001.md'
        )

        assert (ok, error_code) == (True, None)


# =============================================================================
# validate_envelope — the exhaustive seven-class rejection sweep
# =============================================================================


class TestEnvelopeRejections:
    def test_should_reject_missing_header_field(self):
        text = f'{_header_text(kind="")}\n\nbody'

        ok, error_code, _ = validate_envelope(text)

        assert (ok, error_code) == (False, 'missing_header_field')

    def test_should_reject_absent_header_line(self):
        header = '\n'.join(
            line for line in _header_text().split('\n') if not line.startswith('epic=')
        )

        ok, error_code, _ = validate_envelope(f'{header}\n\nbody')

        assert (ok, error_code) == (False, 'missing_header_field')

    def test_should_reject_unknown_envelope_version(self):
        ok, error_code, _ = validate_envelope(
            _message(envelope_version=str(ENVELOPE_VERSION + 1))
        )

        assert (ok, error_code) == (False, 'unknown_envelope_version')

    def test_should_reject_non_numeric_envelope_version(self):
        ok, error_code, _ = validate_envelope(_message(envelope_version='latest'))

        assert (ok, error_code) == (False, 'unknown_envelope_version')

    def test_should_reject_invalid_sender_type(self):
        ok, error_code, _ = validate_envelope(_message(sender_type='robot'))

        assert (ok, error_code) == (False, 'invalid_sender_type')

    def test_should_reject_invalid_kind(self):
        ok, error_code, _ = validate_envelope(_message(kind='gossip'))

        assert (ok, error_code) == (False, 'invalid_kind')

    def test_should_reject_empty_payload(self):
        ok, error_code, _ = validate_envelope(f'{_header_text()}\n\n   \n')

        assert (ok, error_code) == (False, 'empty_payload')

    def test_should_reject_message_with_no_body_at_all(self):
        ok, error_code, _ = validate_envelope(_header_text())

        assert (ok, error_code) == (False, 'empty_payload')

    def test_should_reject_epic_mismatch(self):
        ok, error_code, _ = validate_envelope(_message(), expected_epic='other-epic')

        assert (ok, error_code) == (False, 'epic_mismatch')

    def test_should_reject_filename_sender_mismatch(self):
        ok, error_code, _ = validate_envelope(_message(), filename='someone-else-001.md')

        assert (ok, error_code) == (False, 'filename_sender_mismatch')

    def test_should_reject_filename_outside_the_message_shape(self):
        ok, error_code, _ = validate_envelope(_message(), filename='notes.md')

        assert (ok, error_code) == (False, 'filename_sender_mismatch')

    def test_should_return_a_distinct_code_for_each_rejection_class(self):
        codes = {
            validate_envelope(
                _message(body=body, **overrides),
                expected_epic=expected_epic,
                filename=filename,
            )[1]
            for body, overrides, expected_epic, filename in (
                ('body', {'kind': ''}, None, None),
                ('body', {'envelope_version': '99'}, None, None),
                ('body', {'sender_type': 'robot'}, None, None),
                ('body', {'kind': 'gossip'}, None, None),
                ('   ', {}, None, None),
                ('body', {}, 'other-epic', None),
                ('body', {}, None, 'someone-else-001.md'),
            )
        }

        assert codes == {
            'missing_header_field',
            'unknown_envelope_version',
            'invalid_sender_type',
            'invalid_kind',
            'empty_payload',
            'epic_mismatch',
            'filename_sender_mismatch',
        }


# =============================================================================
# next_sequence / allocate_message_path
# =============================================================================


class TestSequenceAllocation:
    def test_should_start_at_one_for_an_absent_inbox(self, tmp_path):
        assert next_sequence(tmp_path / 'missing', SENDER) == 1

    def test_should_advance_past_the_highest_existing_message(self, tmp_path):
        (tmp_path / f'{SENDER}-001.md').write_text('x', encoding='utf-8')
        (tmp_path / f'{SENDER}-004.md').write_text('x', encoding='utf-8')

        assert next_sequence(tmp_path, SENDER) == 5

    def test_should_count_only_the_named_senders_messages(self, tmp_path):
        (tmp_path / 'other-plan-009.md').write_text('x', encoding='utf-8')

        assert next_sequence(tmp_path, SENDER) == 1

    def test_should_ignore_files_outside_the_message_shape(self, tmp_path):
        (tmp_path / f'{SENDER}-notes.md').write_text('x', encoding='utf-8')

        assert next_sequence(tmp_path, SENDER) == 1

    def test_should_split_a_sender_id_that_ends_in_digits(self, tmp_path):
        (tmp_path / 'plan-001-002.md').write_text('x', encoding='utf-8')

        assert next_sequence(tmp_path, 'plan-001') == 3

    def test_should_write_a_zero_padded_first_message(self, tmp_path):
        path = allocate_message_path(tmp_path / 'inbox', SENDER, 'content\n')

        assert path.name == f'{SENDER}-001.md'
        assert path.read_text(encoding='utf-8') == 'content\n'

    def test_should_not_clobber_an_earlier_message(self, tmp_path):
        first = allocate_message_path(tmp_path, SENDER, 'first\n')
        second = allocate_message_path(tmp_path, SENDER, 'second\n')

        assert (first.name, second.name) == (f'{SENDER}-001.md', f'{SENDER}-002.md')
        assert first.read_text(encoding='utf-8') == 'first\n'

    def test_should_retry_the_next_sequence_when_the_claim_collides(
        self, tmp_path, monkeypatch
    ):
        # Simulate the check-then-act window: the scan proposes a sequence that
        # a concurrent writer has already claimed between scan and create.
        (tmp_path / f'{SENDER}-001.md').write_text('concurrent\n', encoding='utf-8')
        monkeypatch.setattr(_inbox, 'next_sequence', lambda inbox_dir, sender_id: 1)

        path = allocate_message_path(tmp_path, SENDER, 'mine\n')

        assert path.name == f'{SENDER}-002.md'
        assert (tmp_path / f'{SENDER}-001.md').read_text(encoding='utf-8') == 'concurrent\n'


# =============================================================================
# classify_source_id
# =============================================================================


class TestClassifySourceId:
    def test_should_classify_an_orchestrator_plan_spec_pointer(self):
        pointer = '.plan/local/orchestrator/truthful-signals/plans/PLAN-55-inbox.md'

        assert classify_source_id(pointer) == (True, 'truthful-signals', pointer)

    def test_should_classify_a_bare_numbered_spec(self):
        pointer = '.plan/local/orchestrator/my-epic/plans/PLAN-7.md'

        assert classify_source_id(pointer) == (True, 'my-epic', pointer)

    def test_should_tolerate_surrounding_whitespace(self):
        pointer = '.plan/local/orchestrator/my-epic/plans/PLAN-7.md'

        assert classify_source_id(f'  {pointer}\n') == (True, 'my-epic', pointer)

    def test_should_reject_a_prose_description(self):
        assert classify_source_id('a request typed by the operator') == (False, None, None)

    def test_should_reject_an_unrelated_path(self):
        assert classify_source_id('doc/developer/build.adoc') == (False, None, None)

    def test_should_reject_an_empty_source_id(self):
        assert classify_source_id('') == (False, None, None)

    def test_should_reject_a_traversal_bearing_pointer(self):
        pointer = '.plan/local/orchestrator/../../etc/plans/PLAN-1.md'

        assert classify_source_id(pointer) == (False, None, None)

    def test_should_reject_an_unsafe_slug(self):
        pointer = '.plan/local/orchestrator/..evil/plans/PLAN-1.md'

        assert classify_source_id(pointer) == (False, None, None)

    def test_should_reject_a_non_plan_file_in_the_plans_dir(self):
        pointer = '.plan/local/orchestrator/my-epic/plans/README.md'

        assert classify_source_id(pointer) == (False, None, None)


# =============================================================================
# cmd_inbox_write
# =============================================================================


class TestInboxWrite:
    def test_should_write_a_validating_message(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))

        result = cmd_inbox_write(_write_args(payload_file=_payload(tmp_path)))

        assert result['status'] == 'success'
        assert result['operation'] == 'inbox-write'
        assert result['message'] == f'{SENDER}-001.md'
        path = _inbox_dir(plan_context) / f'{SENDER}-001.md'
        assert path.is_file()
        ok, error_code, _ = validate_envelope(
            path.read_text(encoding='utf-8'), expected_epic=EPIC, filename=path.name
        )
        assert (ok, error_code) == (True, None)

    def test_should_stamp_the_supplied_sender_and_epic_in_the_header(
        self, plan_context, tmp_path
    ):
        cmd_scaffold(Namespace(slug=EPIC))
        cmd_inbox_write(
            _write_args(kind='candidate-lesson', payload_file=_payload(tmp_path))
        )

        text = (_inbox_dir(plan_context) / f'{SENDER}-001.md').read_text(encoding='utf-8')

        _, _, header = validate_envelope(text)
        assert header['sender_id'] == SENDER
        assert header['epic'] == EPIC
        assert header['kind'] == 'candidate-lesson'

    def test_should_append_a_second_message_without_clobbering(
        self, plan_context, tmp_path
    ):
        cmd_scaffold(Namespace(slug=EPIC))
        cmd_inbox_write(_write_args(payload_file=_payload(tmp_path, 'first body')))

        result = cmd_inbox_write(
            _write_args(payload_file=_payload(tmp_path, 'second body'))
        )

        assert result['message'] == f'{SENDER}-002.md'
        first = (_inbox_dir(plan_context) / f'{SENDER}-001.md').read_text(encoding='utf-8')
        assert 'first body' in first

    def test_should_carry_the_payload_body_verbatim(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))
        body = '## What landed\n\n- one thing\n- another thing'
        cmd_inbox_write(_write_args(payload_file=_payload(tmp_path, body)))

        text = (_inbox_dir(plan_context) / f'{SENDER}-001.md').read_text(encoding='utf-8')

        assert text.endswith(f'{body}\n')

    def test_should_reject_an_unsafe_slug(self, plan_context, tmp_path):
        result = cmd_inbox_write(
            _write_args(slug='../evil', payload_file=_payload(tmp_path))
        )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'

    def test_should_reject_an_unsafe_sender_id(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))

        result = cmd_inbox_write(
            _write_args(sender_id='../escape', payload_file=_payload(tmp_path))
        )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_sender_id'

    def test_should_reject_an_unknown_sender_type(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))

        result = cmd_inbox_write(
            _write_args(sender_type='robot', payload_file=_payload(tmp_path))
        )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_sender_type'

    def test_should_reject_an_unknown_kind(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))

        result = cmd_inbox_write(
            _write_args(kind='gossip', payload_file=_payload(tmp_path))
        )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_kind'

    def test_should_reject_an_absent_epic_tree(self, plan_context, tmp_path):
        result = cmd_inbox_write(
            _write_args(slug='never-scaffolded', payload_file=_payload(tmp_path))
        )

        assert result['status'] == 'error'
        assert result['error'] == 'epic_not_found'

    def test_should_reject_a_missing_payload_file(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))

        result = cmd_inbox_write(
            _write_args(payload_file=str(tmp_path / 'absent.md'))
        )

        assert result['status'] == 'error'
        assert result['error'] == 'payload_not_found'

    def test_should_reject_an_empty_payload_file(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))

        result = cmd_inbox_write(_write_args(payload_file=_payload(tmp_path, '   \n')))

        assert result['status'] == 'error'
        assert result['error'] == 'empty_payload'

    def test_should_leave_every_non_inbox_path_untouched(self, plan_context, tmp_path):
        cmd_scaffold(Namespace(slug=EPIC))
        status_path = _epic_dir(plan_context) / 'status.json'
        status_path.write_text('{"kind": "orchestrator"}', encoding='utf-8')

        cmd_inbox_write(_write_args(payload_file=_payload(tmp_path)))

        assert status_path.read_text(encoding='utf-8') == '{"kind": "orchestrator"}'
        assert sorted(p.name for p in _epic_dir(plan_context).iterdir()) == sorted(
            ['workstreams', 'plans', 'landings', 'logs', 'inbox', 'status.json']
        )


# =============================================================================
# cmd_inbox_validate
# =============================================================================


class TestInboxValidate:
    def test_should_accept_a_message_written_by_the_write_verb(
        self, plan_context, tmp_path
    ):
        cmd_scaffold(Namespace(slug=EPIC))
        written = cmd_inbox_write(_write_args(payload_file=_payload(tmp_path)))

        result = cmd_inbox_validate(Namespace(slug=EPIC, message=written['message']))

        assert result['status'] == 'success'
        assert result['operation'] == 'inbox-validate'
        assert result['sender_id'] == SENDER
        assert result['kind'] == 'landing'

    def test_should_surface_the_validator_error_code(self, plan_context):
        cmd_scaffold(Namespace(slug=EPIC))
        path = _inbox_dir(plan_context) / f'{SENDER}-001.md'
        path.write_text(_message(envelope_version='99'), encoding='utf-8')

        result = cmd_inbox_validate(Namespace(slug=EPIC, message=path.name))

        assert result['status'] == 'error'
        assert result['error'] == 'unknown_envelope_version'

    def test_should_reject_a_message_name_carrying_a_path(self, plan_context):
        cmd_scaffold(Namespace(slug=EPIC))

        result = cmd_inbox_validate(
            Namespace(slug=EPIC, message='../status.json')
        )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_message_name'

    def test_should_report_a_missing_message(self, plan_context):
        cmd_scaffold(Namespace(slug=EPIC))

        result = cmd_inbox_validate(Namespace(slug=EPIC, message='absent-001.md'))

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'

    def test_should_reject_an_unsafe_slug(self, plan_context):
        result = cmd_inbox_validate(Namespace(slug='../evil', message='x-001.md'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'


# =============================================================================
# cmd_inbox_detect
# =============================================================================


class TestInboxDetect:
    def test_should_report_the_epic_for_an_orchestrated_pointer(self):
        pointer = '.plan/local/orchestrator/my-epic/plans/PLAN-3-thing.md'

        result = cmd_inbox_detect(Namespace(source_id=pointer))

        assert result['status'] == 'success'
        assert result['orchestrated'] is True
        assert result['epic'] == 'my-epic'
        assert result['plan_spec'] == pointer

    def test_should_report_not_orchestrated_for_a_plain_description(self):
        result = cmd_inbox_detect(Namespace(source_id='fix the flaky test'))

        assert result['orchestrated'] is False
        assert result['epic'] == ''
        assert result['plan_spec'] == ''
