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
- ``next_sequence`` / ``allocate_message_path``: per-sender allocation across
  BOTH the live queue and ``inbox/archive/`` (so a drained sender never re-uses
  a retired number), zero-padding, and the ``O_EXCL`` concurrent-claim retry
  that stays scoped to ``inbox/``.
- ``classify_source_id``: the exhaustive grammar and ``detection``-vocabulary
  sweep — one accepting case per settled id form, the over-acceptance and
  slug-bound guards, and one case per ``detection`` token, compared against the
  module's own token frozenset.
- ``resolve_message_path``: the archive-probe order and its closed
  ``MESSAGE_LOCATIONS`` vocabulary, compared against the module's own frozenset.
- ``cmd_inbox_write`` / ``cmd_inbox_validate`` / ``cmd_inbox_detect``: the
  handler surface, including every refusal class. ``cmd_inbox_validate``'s two
  success branches (``location: queued`` / ``location: archived``) are covered
  here together with their success-payload field symmetry and the narrowed
  ``file_not_found`` (present at NEITHER path).
- ``cmd_inbox_list``'s three separately-representable zeros — ``epic_not_found``,
  ``inbox_state: missing`` (could not look), and ``inbox_state: present`` with
  ``count: 0`` (looked, found nothing) — plus the closed ``INBOX_STATES``
  vocabulary compared against the module's own frozenset, and the
  concurrent-drain race in which ``inbox/`` is removed after the enumeration
  read it (``count`` and ``inbox_state`` must report the SAME observation).
- ``cmd_inbox_archive``'s atomic destination claim, driven through a
  deterministically-opened check-to-claim window, plus the sender-constrained
  ``--as-name`` recovery override for a message stranded by a pre-fix sequence
  collision. These live here rather than in the CLI contract module because
  forcing the interleaving requires an in-process seam; a real concurrent race
  reproduces the same states only sporadically and would make the assertion
  flaky.

Three groups here are tabular and are driven as one parametrize each, with the
``ids`` list carrying the prose the per-case test names held: the validator's
rejection classes, and the accepting and rejecting halves of the
``classify_source_id`` grammar. The two grammar halves stay SEPARATE tables
because they are each other's matched controls.

Three further groups were read and judged NOT to be families:

- ``test_should_return_a_distinct_code_for_each_rejection_class`` and
  ``test_should_only_report_tokens_from_the_module_vocabulary`` are
  population-derived: each compares an observed SET against the module's own
  declaration. Their subject is the set, not a row, so there is no table to make.
- ``TestInboxWrite``'s seven refusals share an assertion shape but not a setup:
  two of them (unsafe slug, absent epic tree) deliberately skip ``cmd_scaffold``,
  and three differ in whether the payload file is materialised, absent, or blank.
  The varying element is the per-case SETUP rather than a value, so a table would
  carry callables instead of data and would bury the scaffold-or-not distinction
  the two non-scaffolded cases exist to make.
- ``TestInboxListState``'s three zeros (``present`` with ``count: 0``,
  ``missing``, and ``epic_not_found``) exist precisely to be non-interchangeable,
  and ``test_should_not_answer_the_two_zeros_with_equal_payloads`` is the matched
  control over that pair. Collapsing them would assert the sameness the group
  exists to refute.
"""

import argparse
import copy
import os
import shutil
from pathlib import Path
from typing import Any

import pytest

from conftest import load_script_module, parse_ns

_inbox = load_script_module(
    'plan-marshall', 'plan-orchestrator', '_orchestrator_inbox.py', 'orchestrator_inbox'
)
_orch = load_script_module(
    'plan-marshall', 'plan-orchestrator', 'orchestrator.py', 'orchestrator_script'
)

DETECTION_TOKENS = _inbox.DETECTION_TOKENS
ENVELOPE_VERSION = _inbox.ENVELOPE_VERSION
HEADER_FIELDS = _inbox.HEADER_FIELDS
INBOX_STATES = _inbox.INBOX_STATES
KINDS = _inbox.KINDS
MESSAGE_LOCATIONS = _inbox.MESSAGE_LOCATIONS
SENDER_TYPES = _inbox.SENDER_TYPES
allocate_message_path = _inbox.allocate_message_path
classify_source_id = _inbox.classify_source_id
cmd_inbox_archive = _inbox.cmd_inbox_archive
cmd_inbox_detect = _inbox.cmd_inbox_detect
cmd_inbox_list = _inbox.cmd_inbox_list
cmd_inbox_validate = _inbox.cmd_inbox_validate
cmd_inbox_write = _inbox.cmd_inbox_write
compose_envelope = _inbox.compose_envelope
next_sequence = _inbox.next_sequence
resolve_message_path = _inbox.resolve_message_path
validate_envelope = _inbox.validate_envelope

cmd_scaffold = _orch.cmd_scaffold

EPIC = 'demo-epic'
SENDER = 'demo-plan'

_ORCH_BUNDLE = 'plan-marshall'
_ORCH_SKILL = 'plan-orchestrator'
_ORCH_SCRIPT = 'orchestrator.py'


def _verb_args(*argv: str) -> argparse.Namespace:
    """The namespace ``orchestrator.py``'s OWN parser yields for ``argv``.

    ``register=False`` so building one never publishes a second ``orchestrator``
    in ``sys.modules`` beside the copy loaded above as ``orchestrator_script``.
    """
    args: argparse.Namespace = parse_ns(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, *argv, register=False)
    return args


def _variant(base: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    """Derive a namespace from a hoisted parser-derived base.

    The base supplies every parser default; ``overrides`` names only the fields
    this call differs in. A shallow copy is enough because the values are the
    parser's own scalars, and the base must stay unmutated for the other callers
    sharing it.
    """
    derived = copy.copy(base)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


#: One parser-derived namespace per orchestrator verb this module drives, hoisted
#: to module scope because ``parse_ns`` re-executes the script module on every
#: call. Each carries the two routing discriminators the two-level CLI produces
#: (``command`` and ``inbox_action``) plus the verb's real flag defaults —
#: ``write``'s ``--target-plan`` and ``archive``'s ``--as-name`` among them —
#: none of which the hand-built namespaces they replace had.
_SCAFFOLD_ARGS = _verb_args('scaffold', '--slug', EPIC)
_WRITE_ARGS = _verb_args(
    'inbox', 'write',
    '--slug', EPIC, '--sender-type', 'plan', '--sender-id', SENDER,
    '--kind', 'landing', '--payload-file', 'placeholder',
)
_VALIDATE_ARGS = _verb_args('inbox', 'validate', '--slug', EPIC, '--message', 'placeholder-001.md')
_LIST_ARGS = _verb_args('inbox', 'list', '--slug', EPIC)
_ARCHIVE_ARGS = _verb_args('inbox', 'archive', '--slug', EPIC, '--message', 'placeholder-001.md')
_DETECT_ARGS = _verb_args('inbox', 'detect', '--source-id', 'placeholder')


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
) -> argparse.Namespace:
    return _variant(
        _WRITE_ARGS,
        slug=slug,
        sender_type=sender_type,
        sender_id=sender_id,
        kind=kind,
        payload_file=payload_file,
    )


def _archive_args(message: str, as_name: str | None = None, slug: str = EPIC) -> argparse.Namespace:
    """Build the ``inbox archive`` argument namespace, override included."""
    return _variant(_ARCHIVE_ARGS, slug=slug, message=message, as_name=as_name)


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


def _header_without(field: str) -> str:
    """The standard header block with ``field``'s line deleted outright.

    Distinct from ``_header_text(field='')``, which keeps the line and blanks its
    value — the two reach ``missing_header_field`` by different routes, which is
    why both are rows in the sweep below.
    """
    return '\n'.join(
        line for line in _header_text().split('\n') if not line.startswith(f'{field}=')
    )


#: The exhaustive rejection sweep, as one table: ``(text, expected_epic, filename,
#: expected_code)``. Every row is a message the validator must refuse, and the
#: ``ids`` list below carries the prose each row's own test name held.
_REJECTION_CASES: tuple[tuple[str, str | None, str | None, str], ...] = (
    (f'{_header_text(kind="")}\n\nbody', None, None, 'missing_header_field'),
    (f'{_header_without("epic")}\n\nbody', None, None, 'missing_header_field'),
    (_message(envelope_version=str(ENVELOPE_VERSION + 1)), None, None, 'unknown_envelope_version'),
    (_message(envelope_version='latest'), None, None, 'unknown_envelope_version'),
    (_message(sender_type='robot'), None, None, 'invalid_sender_type'),
    (_message(kind='gossip'), None, None, 'invalid_kind'),
    (f'{_header_text()}\n\n   \n', None, None, 'empty_payload'),
    (_header_text(), None, None, 'empty_payload'),
    (_message(), 'other-epic', None, 'epic_mismatch'),
    (_message(), None, 'someone-else-001.md', 'filename_sender_mismatch'),
    (_message(), None, 'notes.md', 'filename_sender_mismatch'),
)

_REJECTION_IDS = [
    'missing header field',
    'absent header line',
    'unknown envelope version',
    'non-numeric envelope version',
    'invalid sender type',
    'invalid kind',
    'empty payload',
    'message with no body at all',
    'epic mismatch',
    'filename sender mismatch',
    'filename outside the message shape',
]


class TestEnvelopeRejections:
    @pytest.mark.parametrize(
        ('text', 'expected_epic', 'filename', 'expected_code'),
        _REJECTION_CASES,
        ids=_REJECTION_IDS,
    )
    def test_should_reject(self, text, expected_epic, filename, expected_code):
        ok, error_code, _ = validate_envelope(
            text, expected_epic=expected_epic, filename=filename
        )

        assert (ok, error_code) == (False, expected_code)

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


#: The pointer form ``test_should_tolerate_surrounding_whitespace`` wraps — named
#: once so the padded input and the un-padded expected id cannot drift apart.
_BARE_NUMBERED_POINTER = '.plan/local/orchestrator/my-epic/plans/PLAN-7.md'

#: The ACCEPTING grammar sweep, as one table: ``(source_id, expected_epic,
#: expected_id)``. Every row is a settled pointer form the classifier must accept.
_ACCEPTED_SOURCE_IDS = (
    (
        '.plan/local/orchestrator/truthful-signals/plans/PLAN-55-inbox.md',
        'truthful-signals',
        '.plan/local/orchestrator/truthful-signals/plans/PLAN-55-inbox.md',
    ),
    (_BARE_NUMBERED_POINTER, 'my-epic', _BARE_NUMBERED_POINTER),
    (f'  {_BARE_NUMBERED_POINTER}\n', 'my-epic', _BARE_NUMBERED_POINTER),
    (
        '.plan/local/orchestrator/my-epic/plans/PLAN-03-content-search-seam.md',
        'my-epic',
        '.plan/local/orchestrator/my-epic/plans/PLAN-03-content-search-seam.md',
    ),
    (
        '.plan/local/orchestrator/my-epic/plans/PLAN-CIS-01-content-search-seam.md',
        'my-epic',
        '.plan/local/orchestrator/my-epic/plans/PLAN-CIS-01-content-search-seam.md',
    ),
    (
        '.plan/local/orchestrator/my-epic/plans/CIS-01-content-search-seam.md',
        'my-epic',
        '.plan/local/orchestrator/my-epic/plans/CIS-01-content-search-seam.md',
    ),
)

_ACCEPTED_SOURCE_ID_IDS = [
    'orchestrator plan spec pointer',
    'bare numbered spec',
    'surrounding whitespace tolerated',
    'plan-prefixed numbered form',
    'plan-prefixed slug-scoped form',
    'bare slug-scoped form',
]

#: The REJECTING grammar sweep, as one table: ``(source_id, expected_detection)``.
#: Kept a separate table from the accepting one on purpose — the accept and reject
#: halves are the matched controls for each other, and collapsing them into one
#: parametrize would erase that pairing.
_REJECTED_SOURCE_IDS = (
    ('a request typed by the operator', 'not_orchestrator_pointer'),
    ('doc/developer/build.adoc', 'not_orchestrator_pointer'),
    ('', 'not_orchestrator_pointer'),
    ('.plan/local/orchestrator/../../etc/plans/PLAN-1.md', 'not_orchestrator_pointer'),
    ('.plan/local/orchestrator/..evil/plans/PLAN-1.md', 'unsafe_slug'),
    # Orchestrator-SHAPED, id segment unrecognised — the case whose
    # reclassification was previously silent.
    ('.plan/local/orchestrator/my-epic/plans/README.md', 'unrecognised_id'),
    # Over-acceptance guard: an optional-slug-group regex would accept a bare
    # ``01-foo.md`` that is neither PLAN-prefixed nor slug-prefixed.
    ('.plan/local/orchestrator/my-epic/plans/01-foo.md', 'unrecognised_id'),
    ('.plan/local/orchestrator/my-epic/plans/cis-01-foo.md', 'unrecognised_id'),
    # Bound guard: the slug token caps at eight characters, so a nine-character
    # token is outside the widened grammar.
    ('.plan/local/orchestrator/my-epic/plans/ABCDEFGHI-01-foo.md', 'unrecognised_id'),
)

_REJECTED_SOURCE_ID_IDS = [
    'prose description',
    'unrelated path',
    'empty source id',
    'traversal-bearing pointer',
    'unsafe slug',
    'non-plan file in the plans dir',
    'id segment carrying no form prefix',
    'lowercase slug token',
    'over-long slug token',
]


class TestClassifySourceId:
    @pytest.mark.parametrize(
        ('source_id', 'expected_epic', 'expected_id'),
        _ACCEPTED_SOURCE_IDS,
        ids=_ACCEPTED_SOURCE_ID_IDS,
    )
    def test_should_classify(self, source_id, expected_epic, expected_id):
        assert classify_source_id(source_id) == (
            True,
            expected_epic,
            expected_id,
            'orchestrated',
        )

    @pytest.mark.parametrize(
        ('source_id', 'expected_detection'),
        _REJECTED_SOURCE_IDS,
        ids=_REJECTED_SOURCE_ID_IDS,
    )
    def test_should_reject(self, source_id, expected_detection):
        assert classify_source_id(source_id) == (False, None, None, expected_detection)

    def test_should_only_report_tokens_from_the_module_vocabulary(self):
        # Population-derived: the observed tokens are compared against the
        # module's own frozenset rather than a re-listed literal set, so the
        # assertion tracks the vocabulary instead of drifting from it. The
        # equality is two-sided — every declared token is reachable, and no
        # case reports a token outside the declared set.
        cases = (
            '.plan/local/orchestrator/my-epic/plans/PLAN-7.md',
            '.plan/local/orchestrator/..evil/plans/PLAN-1.md',
            '.plan/local/orchestrator/my-epic/plans/README.md',
            'a request typed by the operator',
        )

        observed = {classify_source_id(case).detection for case in cases}

        assert observed == DETECTION_TOKENS


# =============================================================================
# cmd_inbox_write
# =============================================================================


class TestInboxWrite:
    def test_should_write_a_validating_message(self, plan_context, tmp_path):
        cmd_scaffold(_SCAFFOLD_ARGS)

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
        cmd_scaffold(_SCAFFOLD_ARGS)
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
        cmd_scaffold(_SCAFFOLD_ARGS)
        cmd_inbox_write(_write_args(payload_file=_payload(tmp_path, 'first body')))

        result = cmd_inbox_write(
            _write_args(payload_file=_payload(tmp_path, 'second body'))
        )

        assert result['message'] == f'{SENDER}-002.md'
        first = (_inbox_dir(plan_context) / f'{SENDER}-001.md').read_text(encoding='utf-8')
        assert 'first body' in first

    def test_should_carry_the_payload_body_verbatim(self, plan_context, tmp_path):
        cmd_scaffold(_SCAFFOLD_ARGS)
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
        cmd_scaffold(_SCAFFOLD_ARGS)

        result = cmd_inbox_write(
            _write_args(sender_id='../escape', payload_file=_payload(tmp_path))
        )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_sender_id'

    def test_should_reject_an_unknown_sender_type(self, plan_context, tmp_path):
        cmd_scaffold(_SCAFFOLD_ARGS)

        result = cmd_inbox_write(
            _write_args(sender_type='robot', payload_file=_payload(tmp_path))
        )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_sender_type'

    def test_should_reject_an_unknown_kind(self, plan_context, tmp_path):
        cmd_scaffold(_SCAFFOLD_ARGS)

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
        cmd_scaffold(_SCAFFOLD_ARGS)

        result = cmd_inbox_write(
            _write_args(payload_file=str(tmp_path / 'absent.md'))
        )

        assert result['status'] == 'error'
        assert result['error'] == 'payload_not_found'

    def test_should_reject_an_empty_payload_file(self, plan_context, tmp_path):
        cmd_scaffold(_SCAFFOLD_ARGS)

        result = cmd_inbox_write(_write_args(payload_file=_payload(tmp_path, '   \n')))

        assert result['status'] == 'error'
        assert result['error'] == 'empty_payload'

    def test_should_leave_every_non_inbox_path_untouched(self, plan_context, tmp_path):
        cmd_scaffold(_SCAFFOLD_ARGS)
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
        cmd_scaffold(_SCAFFOLD_ARGS)
        written = cmd_inbox_write(_write_args(payload_file=_payload(tmp_path)))

        result = cmd_inbox_validate(_variant(_VALIDATE_ARGS, message=written['message']))

        assert result['status'] == 'success'
        assert result['operation'] == 'inbox-validate'
        assert result['sender_id'] == SENDER
        assert result['kind'] == 'landing'

    def test_should_surface_the_validator_error_code(self, plan_context):
        cmd_scaffold(_SCAFFOLD_ARGS)
        path = _inbox_dir(plan_context) / f'{SENDER}-001.md'
        path.write_text(_message(envelope_version='99'), encoding='utf-8')

        result = cmd_inbox_validate(_variant(_VALIDATE_ARGS, message=path.name))

        assert result['status'] == 'error'
        assert result['error'] == 'unknown_envelope_version'

    def test_should_reject_a_message_name_carrying_a_path(self, plan_context):
        cmd_scaffold(_SCAFFOLD_ARGS)

        result = cmd_inbox_validate(
            _variant(_VALIDATE_ARGS, message='../status.json')
        )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_message_name'

    def test_should_report_a_missing_message(self, plan_context):
        # ``file_not_found`` stays reachable, and now means present at NEITHER
        # inbox/ nor inbox/archive/ — the assertion pins both absences so the
        # narrowed meaning cannot be read as "the archive probe swallowed it".
        cmd_scaffold(_SCAFFOLD_ARGS)
        inbox = _inbox_dir(plan_context)
        assert not (inbox / 'absent-001.md').exists()
        assert not (inbox / 'archive' / 'absent-001.md').exists()

        result = cmd_inbox_validate(_variant(_VALIDATE_ARGS, message='absent-001.md'))

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'

    def test_should_reject_an_unsafe_slug(self, plan_context):
        # The traversal slug is injected onto the derived namespace rather than
        # parsed: ``--slug`` carries a validating ``type=``, so the CLI rejects
        # ``../evil`` before the handler ever sees it. The handler's own guard is
        # defence in depth, and injecting the value is what still reaches it.
        result = cmd_inbox_validate(_variant(_VALIDATE_ARGS, slug='../evil', message='x-001.md'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'

    def test_should_report_the_queued_location_for_a_live_message(
        self, plan_context, tmp_path
    ):
        cmd_scaffold(_SCAFFOLD_ARGS)
        written = cmd_inbox_write(_write_args(payload_file=_payload(tmp_path)))

        result = cmd_inbox_validate(_variant(_VALIDATE_ARGS, message=written['message']))

        assert result['status'] == 'success'
        assert result['location'] == 'queued'
        assert result['archive_path'] == ''

    def test_should_resolve_a_consumed_message_out_of_the_archive(
        self, plan_context, tmp_path
    ):
        # The defect this fixes: a drained message was indistinguishable from a
        # never-written one, because both answered ``file_not_found``.
        cmd_scaffold(_SCAFFOLD_ARGS)
        written = cmd_inbox_write(_write_args(payload_file=_payload(tmp_path)))
        cmd_inbox_archive(_archive_args(written['message']))
        assert not (_inbox_dir(plan_context) / written['message']).exists()

        result = cmd_inbox_validate(_variant(_VALIDATE_ARGS, message=written['message']))

        assert result['status'] == 'success'
        assert result['location'] == 'archived'
        assert result['archive_path'].endswith(f'archive/{SENDER}/{written["message"]}')

    def test_should_report_the_same_header_fields_for_both_success_branches(
        self, plan_context, tmp_path
    ):
        # Success-payload field symmetry: the archived branch is not a reduced
        # payload — it carries every field the queued branch carries, so a
        # consumer never has to special-case where the message was found.
        cmd_scaffold(_SCAFFOLD_ARGS)
        written = cmd_inbox_write(_write_args(payload_file=_payload(tmp_path)))
        queued = cmd_inbox_validate(_variant(_VALIDATE_ARGS, message=written['message']))
        cmd_inbox_archive(_archive_args(written['message']))

        archived = cmd_inbox_validate(_variant(_VALIDATE_ARGS, message=written['message']))

        # The header fields the success payload surfaces; ``epic`` rides the
        # payload as ``slug``, so the reported set is HEADER_FIELDS minus it.
        reported = tuple(field for field in HEADER_FIELDS if field != 'epic')

        assert set(archived) == set(queued)
        assert {key: archived[key] for key in reported} == {
            key: queued[key] for key in reported
        }

    def test_should_validate_an_archived_message_through_the_same_seam(
        self, plan_context
    ):
        # An archived message is not trusted on account of being archived: the
        # identical rejection codes still fire against it.
        cmd_scaffold(_SCAFFOLD_ARGS)
        archive = _inbox_dir(plan_context) / 'archive'
        archive.mkdir(parents=True, exist_ok=True)
        (archive / f'{SENDER}-001.md').write_text(
            _message(envelope_version='99'), encoding='utf-8'
        )

        result = cmd_inbox_validate(_variant(_VALIDATE_ARGS, message=f'{SENDER}-001.md'))

        assert result['status'] == 'error'
        assert result['error'] == 'unknown_envelope_version'

    def test_should_prefer_the_live_queue_over_the_archive(self, plan_context):
        # Probe ORDER: with the name present at both paths, the live queue wins.
        cmd_scaffold(_SCAFFOLD_ARGS)
        inbox = _inbox_dir(plan_context)
        (inbox / f'{SENDER}-001.md').write_text(_message(kind='landing'), encoding='utf-8')
        archive = inbox / 'archive'
        archive.mkdir(parents=True, exist_ok=True)
        (archive / f'{SENDER}-001.md').write_text(
            _message(kind='finding'), encoding='utf-8'
        )

        result = cmd_inbox_validate(_variant(_VALIDATE_ARGS, message=f'{SENDER}-001.md'))

        assert result['location'] == 'queued'
        assert result['kind'] == 'landing'


# =============================================================================
# cmd_inbox_list — which kind of zero a ``count: 0`` is
# =============================================================================


class TestInboxListState:
    """The three separately-representable zeros of the enumeration seam.

    The defect this pins: a ``count: 0`` meaning *could not look* (the epic has
    no ``inbox/`` directory) was indistinguishable from a ``count: 0`` meaning
    *looked, found nothing*. Both now carry a distinct ``inbox_state``, and the
    pre-existing ``epic_not_found`` error branch remains the third zero.
    """

    def test_should_report_present_state_and_the_scanned_directory(
        self, plan_context, tmp_path
    ):
        cmd_scaffold(_SCAFFOLD_ARGS)
        cmd_inbox_write(_write_args(payload_file=_payload(tmp_path)))

        result = cmd_inbox_list(_LIST_ARGS)

        assert result['status'] == 'success'
        assert result['inbox_state'] == 'present'
        assert result['count'] == 1
        assert result['inbox_dir'] == str(_inbox_dir(plan_context))

    def test_should_report_present_state_for_a_genuinely_empty_queue(
        self, plan_context
    ):
        # Zero #3: it looked at a real directory and found nothing.
        cmd_scaffold(_SCAFFOLD_ARGS)
        assert _inbox_dir(plan_context).is_dir()

        result = cmd_inbox_list(_LIST_ARGS)

        assert result['status'] == 'success'
        assert result['count'] == 0
        assert result['inbox_state'] == 'present'

    def test_should_report_missing_state_when_the_inbox_directory_is_absent(
        self, plan_context
    ):
        # Zero #2: the epic tree is there but the enumeration could not look.
        cmd_scaffold(_SCAFFOLD_ARGS)
        _inbox_dir(plan_context).rmdir()

        result = cmd_inbox_list(_LIST_ARGS)

        assert result['count'] == 0
        assert result['inbox_state'] == 'missing'
        # The scanned path is reported even when it does not exist, so the
        # payload always names WHERE the enumeration looked (or would have).
        assert result['inbox_dir'] == str(_inbox_dir(plan_context))

    def test_should_not_answer_the_two_zeros_with_equal_payloads(self, plan_context):
        # The invariant the whole deliverable exists for: a zero meaning "could
        # not look" and a zero meaning "looked, found nothing" agree on `count`
        # and on `status`, so they MUST differ somewhere in the payload — the
        # discriminator is what makes them separately representable.
        cmd_scaffold(_SCAFFOLD_ARGS)
        looked = cmd_inbox_list(_LIST_ARGS)
        _inbox_dir(plan_context).rmdir()

        could_not_look = cmd_inbox_list(_LIST_ARGS)

        assert looked['count'] == could_not_look['count'] == 0
        assert looked['status'] == could_not_look['status'] == 'success'
        assert looked != could_not_look
        assert looked['inbox_dir'] == could_not_look['inbox_dir']

    def test_should_stay_non_faulting_when_the_inbox_directory_is_absent(
        self, plan_context
    ):
        # The discriminator rides the PAYLOAD, never the status — an absent
        # inbox/ must not abort a drain.
        cmd_scaffold(_SCAFFOLD_ARGS)
        _inbox_dir(plan_context).rmdir()

        result = cmd_inbox_list(_LIST_ARGS)

        assert result['status'] == 'success'
        assert 'error' not in result

    def test_should_keep_epic_not_found_as_the_third_zero(self, plan_context):
        # Zero #1: no epic tree at all, retained unchanged as an error branch.
        result = cmd_inbox_list(_variant(_LIST_ARGS, slug='never-scaffolded'))

        assert result['status'] == 'error'
        assert result['error'] == 'epic_not_found'
        assert 'inbox_state' not in result

    def test_should_only_report_states_from_the_module_vocabulary(self, plan_context):
        # Population-derived and two-sided: every declared state is reachable
        # and no case reports one outside the module's own frozenset.
        cmd_scaffold(_SCAFFOLD_ARGS)
        present = cmd_inbox_list(_LIST_ARGS)['inbox_state']
        _inbox_dir(plan_context).rmdir()
        absent = cmd_inbox_list(_LIST_ARGS)['inbox_state']

        assert {present, absent} == INBOX_STATES


class TestInboxListStateUnderConcurrentDrain:
    """``inbox_state`` and ``count`` report ONE observation, not two.

    The defect this pins: ``inbox_state`` was re-derived from a second
    ``is_dir()`` call at return time, AFTER the enumeration loop had already
    run. Under the concurrent writer/drain scenario this module documents, a
    drain that removes ``inbox/`` between the two observations produced a
    self-contradictory payload — ``count`` greater than zero (the scan DID
    look and DID find messages) alongside ``inbox_state: missing`` (asserting
    it could not look). Capturing the discriminator once, before the loop,
    makes the two fields consistent by construction.
    """

    def test_should_not_pair_a_non_zero_count_with_the_missing_state(
        self, plan_context, tmp_path, monkeypatch
    ):
        cmd_scaffold(_SCAFFOLD_ARGS)
        cmd_inbox_write(_write_args(payload_file=_payload(tmp_path)))
        inbox = _inbox_dir(plan_context)
        real_list_messages = _inbox.list_messages

        def draining_list_messages(directory):
            # The deterministic seam for "a concurrent drain retired the queue
            # and removed inbox/ after our enumeration read it": the removal
            # fires when the generator is exhausted, so every message is still
            # read successfully and only the return-time observation changes.
            yield from real_list_messages(directory)
            shutil.rmtree(inbox)

        monkeypatch.setattr(_inbox, 'list_messages', draining_list_messages)

        result = cmd_inbox_list(_LIST_ARGS)

        assert not inbox.exists(), (
            'the seam did not fire — the assertion below would pass vacuously '
            'against an inbox/ that was never removed'
        )
        assert result['count'] == 1
        assert result['inbox_state'] == 'present'


# =============================================================================
# resolve_message_path — the single home of the archive-probe order
# =============================================================================


class TestResolveMessagePath:
    def test_should_resolve_a_queued_message(self, tmp_path):
        (tmp_path / f'{SENDER}-001.md').write_text('x', encoding='utf-8')

        path, location = resolve_message_path(tmp_path, f'{SENDER}-001.md')

        assert location == 'queued'
        assert path == tmp_path / f'{SENDER}-001.md'

    def test_should_resolve_an_archived_message(self, tmp_path):
        archive = tmp_path / 'archive'
        archive.mkdir()
        (archive / f'{SENDER}-001.md').write_text('x', encoding='utf-8')

        path, location = resolve_message_path(tmp_path, f'{SENDER}-001.md')

        assert location == 'archived'
        assert path == archive / f'{SENDER}-001.md'

    def test_should_report_missing_when_present_at_neither_path(self, tmp_path):
        path, location = resolve_message_path(tmp_path, f'{SENDER}-001.md')

        assert location == 'missing'
        # The live-queue candidate is returned so the caller's not-found message
        # keeps naming the path a reader would look at first.
        assert path == tmp_path / f'{SENDER}-001.md'

    def test_should_tolerate_an_absent_inbox_directory(self, tmp_path):
        _path, location = resolve_message_path(tmp_path / 'never-made', 'x-001.md')

        assert location == 'missing'

    def test_should_only_report_locations_from_the_module_vocabulary(self, tmp_path):
        # Population-derived: compared against the module's own frozenset rather
        # than a re-listed literal set, and two-sided — every declared location
        # is reachable and no case reports one outside the declared set.
        (tmp_path / 'queued-001.md').write_text('x', encoding='utf-8')
        archive = tmp_path / 'archive'
        archive.mkdir()
        (archive / 'retired-001.md').write_text('x', encoding='utf-8')

        observed = {
            resolve_message_path(tmp_path, name)[1]
            for name in ('queued-001.md', 'retired-001.md', 'absent-001.md')
        }

        assert observed == MESSAGE_LOCATIONS


# =============================================================================
# cmd_inbox_archive — the atomic destination claim under a forced race
# =============================================================================


def _open_race_window(monkeypatch, trigger_dir: Path, side_effect) -> None:
    """Fire ``side_effect`` ONCE inside the archive verb's check-to-claim window.

    ``cmd_inbox_archive`` creates the destination's per-sender archive
    subdirectory (``inbox/archive/{sender}/``) immediately before it claims the
    foldered destination, so wrapping :meth:`pathlib.Path.mkdir` and firing when
    that subdirectory appears is the deterministic seam for "a concurrent drain
    acted after our presence checks and before our own move" — the exact
    interleaving a real race produces only sporadically. The fire is one-shot:
    ``mkdir(parents=True)`` touches ``trigger_dir`` more than once (the nested
    parent-creation recursion and the outer call), and a side effect that
    re-linked or re-wrote the destination on the second touch would raise inside
    the seam rather than exercising the verb.
    """
    original = Path.mkdir
    fired = {'done': False}

    def mkdir(self, *args, **kwargs):
        original(self, *args, **kwargs)
        if self == trigger_dir and not fired['done']:
            fired['done'] = True
            side_effect()

    monkeypatch.setattr(Path, 'mkdir', mkdir)


class TestInboxArchiveRace:
    def _seed(self, plan_context, tmp_path) -> tuple[Path, Path, Path]:
        cmd_scaffold(_SCAFFOLD_ARGS)
        cmd_inbox_write(_write_args(payload_file=_payload(tmp_path, 'my body')))
        inbox = _inbox_dir(plan_context)
        archive_dir = inbox / 'archive'
        # The destination is foldered per sender, so the seam fires on the
        # sender subdirectory (``dest.parent``), created immediately before the
        # claim.
        dest = archive_dir / SENDER / f'{SENDER}-001.md'
        return inbox / f'{SENDER}-001.md', archive_dir, dest

    def test_should_refuse_a_destination_that_appears_inside_the_window(
        self, plan_context, tmp_path, monkeypatch
    ):
        source, _archive_dir, dest = self._seed(plan_context, tmp_path)
        _open_race_window(
            monkeypatch,
            dest.parent,
            lambda: dest.write_text('the winner audit record\n', encoding='utf-8'),
        )

        result = cmd_inbox_archive(_variant(_ARCHIVE_ARGS, message=source.name))

        assert result['status'] == 'error'
        assert result['error'] == 'archive_conflict'
        assert dest.read_text(encoding='utf-8') == 'the winner audit record\n'
        # A refused claim retires nothing: the un-archived message must survive
        # so a later drain can still consume it.
        assert source.is_file()

    def test_should_report_already_archived_when_dest_is_the_same_inode_as_source(
        self, plan_context, tmp_path, monkeypatch
    ):
        source, _archive_dir, dest = self._seed(plan_context, tmp_path)
        # The winner has claimed the destination but has NOT yet unlinked its
        # source, so both paths are one inode. Source presence is therefore
        # true here while ``dest`` is the winner's own in-flight artifact — not
        # a distinct competing audit record — so this must resolve to
        # idempotent success, not ``archive_conflict``.
        _open_race_window(monkeypatch, dest.parent, lambda: os.link(source, dest))

        result = cmd_inbox_archive(_variant(_ARCHIVE_ARGS, message=source.name))

        assert result['status'] == 'success'
        assert result['already_archived'] is True
        assert dest.is_file()
        # The winner still owns the source unlink; the loser must not have
        # retired it on the winner's behalf.
        assert source.is_file()

    def test_should_reject_a_message_naming_a_directory(self, plan_context, tmp_path):
        # ``archive`` is a bare filename, so it clears ``_is_bare_filename`` and
        # reaches ``os.link`` — where it names the archive DIRECTORY. os.link
        # refuses a directory source with a plain OSError that neither narrow
        # handler catches, so this must return a structured refusal rather than
        # letting the OSError escape.
        self._seed(plan_context, tmp_path)

        result = cmd_inbox_archive(_variant(_ARCHIVE_ARGS, message='archive'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_message_name'
        assert result['message_name'] == 'archive'

    def test_should_report_already_archived_when_the_race_is_lost(
        self, plan_context, tmp_path, monkeypatch
    ):
        source, _archive_dir, dest = self._seed(plan_context, tmp_path)

        def concurrent_winner() -> None:
            os.link(source, dest)
            source.unlink()

        _open_race_window(monkeypatch, dest.parent, concurrent_winner)

        result = cmd_inbox_archive(_variant(_ARCHIVE_ARGS, message=source.name))

        assert result['status'] == 'success'
        assert result['already_archived'] is True
        assert dest.is_file()
        assert not source.exists()

    def test_should_report_file_not_found_when_the_source_vanishes_in_the_window(
        self, plan_context, tmp_path, monkeypatch
    ):
        source, _archive_dir, dest = self._seed(plan_context, tmp_path)
        _open_race_window(monkeypatch, dest.parent, source.unlink)

        result = cmd_inbox_archive(_variant(_ARCHIVE_ARGS, message=source.name))

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'


# =============================================================================
# Archive-aware sequence allocation — the collision the fix removes
# =============================================================================


class TestArchiveAwareAllocation:
    def test_should_advance_past_an_archived_message(self, tmp_path):
        # (a) The sender's only message has been retired to archive/. A
        # live-only scan proposes 001 and hands back a number whose archived
        # twin already exists.
        archive = tmp_path / 'archive'
        archive.mkdir()
        (archive / f'{SENDER}-001.md').write_text('x', encoding='utf-8')

        assert next_sequence(tmp_path, SENDER) == 2

    def test_should_take_the_max_across_the_live_queue_and_the_archive(self, tmp_path):
        (tmp_path / f'{SENDER}-002.md').write_text('x', encoding='utf-8')
        archive = tmp_path / 'archive'
        archive.mkdir()
        (archive / f'{SENDER}-007.md').write_text('x', encoding='utf-8')

        assert next_sequence(tmp_path, SENDER) == 8

    def test_should_consult_the_archive_when_the_live_inbox_is_absent(self, tmp_path):
        inbox = tmp_path / 'inbox'
        archive = inbox / 'archive'
        archive.mkdir(parents=True)
        (archive / f'{SENDER}-003.md').write_text('x', encoding='utf-8')

        assert next_sequence(inbox, SENDER) == 4

    def test_should_count_only_the_named_senders_archived_messages(self, tmp_path):
        archive = tmp_path / 'archive'
        archive.mkdir()
        (archive / 'other-plan-009.md').write_text('x', encoding='utf-8')

        assert next_sequence(tmp_path, SENDER) == 1

    def test_should_allocate_unchanged_for_a_sender_with_no_archive(self, tmp_path):
        # (c) Regression pin that the fix is ADDITIVE: a sender whose messages
        # have never been drained allocates exactly as it did before.
        (tmp_path / f'{SENDER}-001.md').write_text('x', encoding='utf-8')
        (tmp_path / f'{SENDER}-002.md').write_text('x', encoding='utf-8')

        assert next_sequence(tmp_path, SENDER) == 3

    def test_should_tolerate_a_missing_archive_directory(self, tmp_path):
        # (d) archive/ is created on first use, so it is routinely absent.
        (tmp_path / f'{SENDER}-004.md').write_text('x', encoding='utf-8')

        assert next_sequence(tmp_path, SENDER) == 5

    def test_should_claim_only_inside_the_live_inbox(self, tmp_path):
        # The proposal widens; the O_EXCL claim does not. The archive is never
        # a claim target.
        inbox = tmp_path / 'inbox'
        archive = inbox / 'archive'
        archive.mkdir(parents=True)
        (archive / f'{SENDER}-001.md').write_text('retired\n', encoding='utf-8')

        path = allocate_message_path(inbox, SENDER, 'fresh\n')

        assert path == inbox / f'{SENDER}-002.md'
        assert sorted(p.name for p in archive.iterdir()) == [f'{SENDER}-001.md']

    def test_should_archive_cleanly_after_a_drained_sender_writes_again(
        self, plan_context, tmp_path
    ):
        # (b) The full write -> drain -> write -> drain cycle: the second write
        # lands at -002 and its archival succeeds instead of colliding with the
        # retired -001 record.
        cmd_scaffold(_SCAFFOLD_ARGS)
        first = cmd_inbox_write(_write_args(payload_file=_payload(tmp_path, 'first')))
        cmd_inbox_archive(_archive_args(first['message']))

        second = cmd_inbox_write(_write_args(payload_file=_payload(tmp_path, 'second')))
        result = cmd_inbox_archive(_archive_args(second['message']))

        assert second['message'] == f'{SENDER}-002.md'
        assert result['status'] == 'success'
        assert result['already_archived'] is False
        # Both retired messages are foldered under archive/{sender}/.
        sender_archive = _inbox_dir(plan_context) / 'archive' / SENDER
        assert sorted(p.name for p in sender_archive.iterdir()) == [
            f'{SENDER}-001.md',
            f'{SENDER}-002.md',
        ]


# =============================================================================
# cmd_inbox_archive — refusal / idempotence pins that must survive the fix
# =============================================================================


class TestInboxArchiveClaimPins:
    def _seed(self, plan_context, tmp_path) -> tuple[Path, Path]:
        cmd_scaffold(_SCAFFOLD_ARGS)
        cmd_inbox_write(_write_args(payload_file=_payload(tmp_path, 'my body')))
        inbox = _inbox_dir(plan_context)
        source = inbox / f'{SENDER}-001.md'
        # The claim target is foldered per sender.
        dest = inbox / 'archive' / SENDER / f'{SENDER}-001.md'
        return source, dest

    def test_should_refuse_a_distinct_archived_record(self, plan_context, tmp_path):
        # (e) A genuinely DISTINCT destination inode — the stranded-message
        # state a pre-fix collision produces — is still refused fail-closed,
        # and the refusal leaves the source in place.
        source, dest = self._seed(plan_context, tmp_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text('the earlier audit record\n', encoding='utf-8')

        result = cmd_inbox_archive(_archive_args(source.name))

        assert result['status'] == 'error'
        assert result['error'] == 'archive_conflict'
        assert source.is_file()
        assert dest.read_text(encoding='utf-8') == 'the earlier audit record\n'

    def test_should_report_already_archived_for_the_same_inode(
        self, plan_context, tmp_path
    ):
        # (f) The same-inode window: a concurrent winner has linked but not yet
        # unlinked. Inode identity, not source presence, is the discriminator.
        source, dest = self._seed(plan_context, tmp_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.link(source, dest)

        result = cmd_inbox_archive(_archive_args(source.name))

        assert result['status'] == 'success'
        assert result['already_archived'] is True
        assert source.is_file()


# =============================================================================
# cmd_inbox_archive --as-name — the sender-constrained recovery override
# =============================================================================


class TestInboxArchiveAsName:
    def _strand(self, plan_context, tmp_path) -> tuple[Path, Path]:
        """Reproduce the stranded state: source + a distinct FOLDERED twin.

        Under per-sender foldering the default destination is
        ``archive/{sender}/{name}``, so the distinct twin that makes the default
        archive collide must sit at that foldered path — a flat twin would no
        longer conflict. The returned directory is the sender's archive
        subdirectory, where both the twin and any sender-preserving recovery
        name land.
        """
        cmd_scaffold(_SCAFFOLD_ARGS)
        cmd_inbox_write(_write_args(payload_file=_payload(tmp_path, 'stranded body')))
        inbox = _inbox_dir(plan_context)
        source = inbox / f'{SENDER}-001.md'
        sender_archive = inbox / 'archive' / SENDER
        sender_archive.mkdir(parents=True, exist_ok=True)
        (sender_archive / source.name).write_text(
            'the earlier audit record\n', encoding='utf-8'
        )
        return source, sender_archive

    def test_should_accept_an_override_that_preserves_the_sender(
        self, plan_context, tmp_path
    ):
        # (g) Positive arm. The accepted name is asserted to be the
        # sender-matching one, so the constraint cannot pass vacuously via a
        # rule that accepts everything.
        source, archive = self._strand(plan_context, tmp_path)
        recovery_name = f'{SENDER}-001.dup1.md'
        assert recovery_name.startswith(f'{SENDER}-')

        result = cmd_inbox_archive(_archive_args(source.name, as_name=recovery_name))

        assert result['status'] == 'success'
        assert result['already_archived'] is False
        assert result['archived_to'].endswith(recovery_name)
        assert not source.exists()
        assert (archive / recovery_name).read_text(encoding='utf-8').endswith(
            'stranded body\n'
        )
        # The pre-existing audit record was never clobbered.
        assert (archive / source.name).read_text(
            encoding='utf-8'
        ) == 'the earlier audit record\n'

    def test_should_refuse_an_override_that_drops_the_sender(
        self, plan_context, tmp_path
    ):
        # (h) Negative arm, distinct code.
        source, archive = self._strand(plan_context, tmp_path)

        result = cmd_inbox_archive(_archive_args(source.name, as_name='other-001.md'))

        assert result['status'] == 'error'
        assert result['error'] == 'as_name_sender_mismatch'
        assert source.is_file()
        assert sorted(p.name for p in archive.iterdir()) == [source.name]

    def test_should_refuse_a_path_shaped_override(self, plan_context, tmp_path):
        # The retained bare-filename guard is LIVE and distinct from the sender
        # rule — neither validation shadows the other.
        source, archive = self._strand(plan_context, tmp_path)

        result = cmd_inbox_archive(
            _archive_args(source.name, as_name=f'../{SENDER}-001.md')
        )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_message_name'
        assert source.is_file()
        assert sorted(p.name for p in archive.iterdir()) == [source.name]

    def test_should_refuse_an_override_when_no_sender_is_derivable(
        self, plan_context, tmp_path
    ):
        cmd_scaffold(_SCAFFOLD_ARGS)
        inbox = _inbox_dir(plan_context)
        off_shape = inbox / 'notes.md'
        off_shape.write_text('not a message\n', encoding='utf-8')

        result = cmd_inbox_archive(
            _archive_args(off_shape.name, as_name=f'{SENDER}-001.md')
        )

        assert result['status'] == 'error'
        assert result['error'] == 'as_name_sender_mismatch'
        assert off_shape.is_file()

    def test_should_leave_the_default_destination_path_unchanged(
        self, plan_context, tmp_path
    ):
        cmd_scaffold(_SCAFFOLD_ARGS)
        written = cmd_inbox_write(_write_args(payload_file=_payload(tmp_path)))

        result = cmd_inbox_archive(_archive_args(written['message'], as_name=None))

        assert result['status'] == 'success'
        # A default-destination archive folds under archive/{sender}/.
        assert result['archived_to'].endswith(f'archive/{SENDER}/{written["message"]}')


# =============================================================================
# cmd_inbox_detect
# =============================================================================


class TestInboxDetect:
    def test_should_report_the_epic_for_an_orchestrated_pointer(self):
        pointer = '.plan/local/orchestrator/my-epic/plans/PLAN-3-thing.md'

        result = cmd_inbox_detect(_variant(_DETECT_ARGS, source_id=pointer))

        assert result['status'] == 'success'
        assert result['orchestrated'] is True
        assert result['epic'] == 'my-epic'
        assert result['plan_spec'] == pointer
        assert result['detection'] == 'orchestrated'

    def test_should_report_not_orchestrated_for_a_plain_description(self):
        result = cmd_inbox_detect(_variant(_DETECT_ARGS, source_id='fix the flaky test'))

        assert result['orchestrated'] is False
        assert result['epic'] == ''
        assert result['plan_spec'] == ''
        assert result['detection'] == 'not_orchestrator_pointer'

    def test_should_surface_an_unrecognised_id_for_an_orchestrator_shaped_pointer(self):
        # The reclassification the WARNING at the single call site reports: the
        # verdict is still orchestrated=false, but it is now distinguishable
        # from a plain non-pointer.
        pointer = '.plan/local/orchestrator/my-epic/plans/PLAN-CIS-alpha.md'

        result = cmd_inbox_detect(_variant(_DETECT_ARGS, source_id=pointer))

        assert result['orchestrated'] is False
        assert result['epic'] == ''
        assert result['plan_spec'] == ''
        assert result['detection'] == 'unrecognised_id'
