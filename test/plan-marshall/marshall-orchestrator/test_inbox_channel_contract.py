#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Contract tests for the epic inbox channel (deliverables 1 and 2).

Behavioural assertions run end-to-end through the ``orchestrator.py`` CLI entry
point with constructed argv at the subprocess boundary (``run_script``), under
``PLAN_BASE_DIR`` isolation (via ``plan_context``):

- **Well-formed message**: ``scaffold`` -> ``inbox write`` -> ``inbox validate``
  round trip, the header carrying all six fields, and a second write landing at
  ``-002`` without clobbering ``-001``.
- **CLI wiring carries a rejection**: exactly ONE representative rejection class
  (an unknown ``envelope_version`` — the forward-compatibility case) is carried
  end-to-end. The exhaustive seven-class sweep is NOT repeated here; it lives
  once in ``test_inbox_envelope.py``'s in-process unit tests. This module's job
  at the CLI level is to prove the wiring (argv -> handler -> TOON ``error``)
  transports a rejection faithfully, not to re-enumerate the schema.
- **``inbox validate`` resolves the archive**: a queued message reports
  ``location: queued`` with an empty ``archive_path``, a CONSUMED one reports
  ``location: archived`` with the resolved archived path, and ``file_not_found``
  fires only when the message is present at NEITHER path.
- **Drain surface**: ``inbox list`` enumerates the queue in deterministic
  (sender, sequence) order, reports a malformed message with its distinct
  validator error code instead of dropping it, and never looks inside
  ``inbox/archive/``; ``inbox archive`` relocates a consumed message, is
  idempotent on repeat, refuses a path-shaped or empty name, refuses to clobber
  an existing archived copy, and — being a MUTATING verb — refuses an unsafe
  slug, an unscaffolded epic, and an archived-only epic rather than resolving
  through the archived read-fallback the read-side verbs use. The
  ``--as-name`` RECOVERY flow retires a message stranded by a pre-fix sequence
  collision under a non-colliding archived name, and is refused at the argv
  boundary by two distinct rules: ``invalid_message_name`` for a path-shaped
  override and ``as_name_sender_mismatch`` for one that drops the source
  message's sender segment.
- **Archive-aware allocation**: a ``write`` -> ``archive`` -> ``write`` round
  trip lands the second message at ``-002`` rather than re-using the retired
  ``-001``, and that second message archives cleanly.
- **Boundary still holds on every non-inbox path**: after a write, and again
  after a ``list`` + ``archive`` pair, every non-inbox path in a pre-populated
  epic tree is byte-identical, and an unsafe slug is refused.

The doc-contract assertions pin all three describe-side surfaces of the ledger
write-boundary carve-out, plus the two describe-side surfaces of the
``inbox validate`` resolution contract (``SKILL.md`` § ``### inbox validate``
and ``standards/inbox-envelope.md`` § Drain semantics / Validator error codes),
in the same style as the existing ``test_step_termination_contract.py`` /
``test_dispatch_roster_closure.py`` doc-contract tests.
"""

from __future__ import annotations

from pathlib import Path

from conftest import MARKETPLACE_ROOT, get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'marshall-orchestrator', 'orchestrator.py')

_PLAN_MARSHALL = MARKETPLACE_ROOT / 'plan-marshall' / 'skills'
_ORCHESTRATION_MODEL = (
    _PLAN_MARSHALL / 'persona-marshall-orchestrator' / 'standards' / 'orchestration-model.md'
)
_PLAN_SPEC_TEMPLATE = (
    _PLAN_MARSHALL / 'marshall-orchestrator' / 'templates' / 'plan-spec.md'
)
_ORCHESTRATOR_SKILL = _PLAN_MARSHALL / 'marshall-orchestrator' / 'SKILL.md'
_INBOX_ENVELOPE = (
    _PLAN_MARSHALL / 'marshall-orchestrator' / 'standards' / 'inbox-envelope.md'
)

EPIC = 'contract-epic'
SENDER = 'contract-plan'
#: A second sender, so the (sender, sequence) ordering is observable. Sorts
#: AFTER ``SENDER`` ('c' < 'o'), which is what the order assertion pins.
OTHER_SENDER = 'other-plan'

#: An epic whose active tree is relocated to ``archived-orchestrators/`` mid-test,
#: so the mutating-verb resolver is observed against an archived-only epic.
ARCHIVED_EPIC = 'archived-epic'

#: The five ledger paths that stay forbidden to a plan after the carve-out.
FORBIDDEN_PATHS = ('status.json', 'epic.md', 'workstreams', 'plans', 'landings')


def _env(plan_context) -> dict[str, str]:
    return {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}


def _epic_dir(plan_context, slug: str = EPIC) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / slug


def _archived_epic_dir(plan_context, slug: str) -> Path:
    return Path(plan_context.fixture_dir) / 'archived-orchestrators' / slug


def _payload(tmp_path: Path, body: str = 'the landing narrative', name: str = 'p.md') -> str:
    path = tmp_path / name
    path.write_text(body, encoding='utf-8')
    return str(path)


def _scaffold(plan_context, slug: str = EPIC):
    return run_script(SCRIPT_PATH, 'scaffold', '--slug', slug, env_overrides=_env(plan_context))


def _write(
    plan_context,
    payload_file: str,
    slug: str = EPIC,
    kind: str = 'landing',
    sender: str = SENDER,
):
    return run_script(
        SCRIPT_PATH,
        'inbox',
        'write',
        '--slug',
        slug,
        '--sender-type',
        'plan',
        '--sender-id',
        sender,
        '--kind',
        kind,
        '--payload-file',
        payload_file,
        env_overrides=_env(plan_context),
    )


def _list(plan_context, slug: str = EPIC):
    return run_script(
        SCRIPT_PATH,
        'inbox',
        'list',
        '--slug',
        slug,
        env_overrides=_env(plan_context),
    )


def _archive(plan_context, message: str, slug: str = EPIC, as_name: str | None = None):
    """Run ``inbox archive``, appending ``--as-name`` only when one is supplied.

    The flag is omitted rather than passed as an empty value on the default
    path, so the default-destination behaviour is exercised through the same
    argv shape a caller that never heard of the override produces.
    """
    argv = ['inbox', 'archive', '--slug', slug, '--message', message]
    if as_name is not None:
        argv += ['--as-name', as_name]
    return run_script(SCRIPT_PATH, *argv, env_overrides=_env(plan_context))


def _malformed(sender: str = OTHER_SENDER) -> str:
    """A message whose only defect is an unsupported ``envelope_version``."""
    return (
        'envelope_version=99\n'
        'sender_type=plan\n'
        f'sender_id={sender}\n'
        f'epic={EPIC}\n'
        'kind=landing\n'
        'created=2020-01-01T00:00:00Z\n'
        '\n'
        'payload prose\n'
    )


def _validate(plan_context, message: str, slug: str = EPIC):
    return run_script(
        SCRIPT_PATH,
        'inbox',
        'validate',
        '--slug',
        slug,
        '--message',
        message,
        env_overrides=_env(plan_context),
    )


def _section(text: str, heading: str) -> str:
    """Return the text between ``heading`` and the next same-level heading."""
    lines = text.splitlines()
    level = heading.split(' ', 1)[0]
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == heading)
    except StopIteration:
        raise AssertionError(f'Heading not found: {heading!r}') from None
    collected: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith(f'{level} '):
            break
        collected.append(line)
    return '\n'.join(collected)


def _line(section: str, prefix: str) -> str:
    """Return the first section line whose stripped form starts with ``prefix``.

    Stripping before the prefix test matters: a bullet or table row nested under
    a list item is indented to the item's continuation column, and a matcher
    anchored at column zero would silently find nothing there — passing only by
    the accident that the source happens to be unindented today.
    """
    stripped = (line.strip() for line in section.splitlines())
    match = next((line for line in stripped if line.startswith(prefix)), None)
    assert match is not None, f'no line starting with {prefix!r} in the section'
    return match


# =============================================================================
# Well-formed message: round trip through the CLI
# =============================================================================


class TestWellFormedMessage:
    def test_should_round_trip_write_then_validate(self, plan_context, tmp_path):
        _scaffold(plan_context)

        written = _write(plan_context, _payload(tmp_path))
        validated = _validate(plan_context, f'{SENDER}-001.md')

        assert written.returncode == 0
        assert 'status: success' in written.stdout
        assert f'message: {SENDER}-001.md' in written.stdout
        assert validated.returncode == 0
        assert 'status: success' in validated.stdout
        assert 'operation: inbox-validate' in validated.stdout

    def test_should_create_the_message_under_inbox(self, plan_context, tmp_path):
        _scaffold(plan_context)

        _write(plan_context, _payload(tmp_path))

        assert (_epic_dir(plan_context) / 'inbox' / f'{SENDER}-001.md').is_file()

    def test_should_carry_all_six_header_fields(self, plan_context, tmp_path):
        _scaffold(plan_context)
        _write(plan_context, _payload(tmp_path))

        text = (_epic_dir(plan_context) / 'inbox' / f'{SENDER}-001.md').read_text(
            encoding='utf-8'
        )

        for field in (
            'envelope_version=1',
            'sender_type=plan',
            f'sender_id={SENDER}',
            f'epic={EPIC}',
            'kind=landing',
        ):
            assert field in text, field
        assert 'created=' in text

    def test_should_land_a_second_write_at_002_without_clobbering(
        self, plan_context, tmp_path
    ):
        _scaffold(plan_context)
        _write(plan_context, _payload(tmp_path, 'first body', 'a.md'))

        second = _write(plan_context, _payload(tmp_path, 'second body', 'b.md'))

        assert f'message: {SENDER}-002.md' in second.stdout
        first_text = (_epic_dir(plan_context) / 'inbox' / f'{SENDER}-001.md').read_text(
            encoding='utf-8'
        )
        assert 'first body' in first_text
        assert 'second body' not in first_text

    def test_should_scaffold_the_inbox_directory(self, plan_context):
        _scaffold(plan_context)

        assert (_epic_dir(plan_context) / 'inbox').is_dir()


# =============================================================================
# CLI wiring carries ONE representative rejection end-to-end
# =============================================================================


class TestCliCarriesRejection:
    def test_should_reject_an_unknown_envelope_version_through_the_cli(
        self, plan_context
    ):
        _scaffold(plan_context)
        (_epic_dir(plan_context) / 'inbox' / f'{SENDER}-001.md').write_text(
            _malformed(SENDER), encoding='utf-8'
        )

        result = _validate(plan_context, f'{SENDER}-001.md')

        assert result.returncode == 0
        assert 'status: error' in result.stdout
        assert 'error: unknown_envelope_version' in result.stdout

    def test_should_refuse_an_empty_message_name(self, plan_context):
        _scaffold(plan_context)

        result = _validate(plan_context, '')

        assert result.returncode == 0
        assert 'error: invalid_message_name' in result.stdout


# =============================================================================
# inbox validate resolves the archive: consumed vs missing, through real argv
# =============================================================================


class TestInboxValidateResolution:
    def test_should_report_the_queued_location_for_a_live_message(
        self, plan_context, tmp_path
    ):
        _scaffold(plan_context)
        _write(plan_context, _payload(tmp_path))

        parsed = _validate(plan_context, f'{SENDER}-001.md').toon()

        assert parsed['status'] == 'success'
        assert parsed['location'] == 'queued'
        assert parsed['archive_path'] == ''

    def test_should_resolve_a_consumed_message_out_of_the_archive(
        self, plan_context, tmp_path
    ):
        # The end-to-end proof that a DRAINED message no longer answers
        # file_not_found: archival is the consume marker, and this is its
        # read-side counterpart surviving the subprocess boundary.
        _scaffold(plan_context)
        _write(plan_context, _payload(tmp_path))
        _archive(plan_context, f'{SENDER}-001.md')
        inbox = _epic_dir(plan_context) / 'inbox'
        assert not (inbox / f'{SENDER}-001.md').exists()

        parsed = _validate(plan_context, f'{SENDER}-001.md').toon()

        assert parsed['status'] == 'success'
        assert parsed['location'] == 'archived'
        assert parsed['archive_path'] == str(inbox / 'archive' / f'{SENDER}-001.md')

    def test_should_report_file_not_found_only_when_present_at_neither_path(
        self, plan_context
    ):
        _scaffold(plan_context)
        inbox = _epic_dir(plan_context) / 'inbox'
        assert not (inbox / f'{SENDER}-404.md').exists()
        assert not (inbox / 'archive' / f'{SENDER}-404.md').exists()

        result = _validate(plan_context, f'{SENDER}-404.md')

        assert 'error: file_not_found' in result.stdout


# =============================================================================
# Drain surface: inbox list
# =============================================================================


class TestInboxList:
    def test_should_return_messages_in_sender_then_sequence_order(
        self, plan_context, tmp_path
    ):
        _scaffold(plan_context)
        _write(plan_context, _payload(tmp_path, 'first', 'a.md'), kind='landing')
        _write(plan_context, _payload(tmp_path, 'second', 'b.md'), kind='finding')
        _write(
            plan_context,
            _payload(tmp_path, 'third', 'c.md'),
            kind='candidate-lesson',
            sender=OTHER_SENDER,
        )

        result = _list(plan_context)

        assert result.returncode == 0
        rows = result.toon()['messages']
        assert [row['name'] for row in rows] == [
            f'{SENDER}-001.md',
            f'{SENDER}-002.md',
            f'{OTHER_SENDER}-001.md',
        ]
        assert [row['sender_id'] for row in rows] == [SENDER, SENDER, OTHER_SENDER]
        assert [row['kind'] for row in rows] == ['landing', 'finding', 'candidate-lesson']
        assert all(row['valid'] is True for row in rows)
        assert all(row['created'] for row in rows)

    def test_should_report_a_malformed_message_alongside_the_valid_ones(
        self, plan_context, tmp_path
    ):
        _scaffold(plan_context)
        _write(plan_context, _payload(tmp_path))
        (_epic_dir(plan_context) / 'inbox' / f'{OTHER_SENDER}-001.md').write_text(
            _malformed(), encoding='utf-8'
        )

        parsed = _list(plan_context).toon()

        rows = {row['name']: row for row in parsed['messages']}
        assert parsed['count'] == 2
        assert parsed['invalid_count'] == 1
        assert rows[f'{SENDER}-001.md']['valid'] is True
        assert rows[f'{SENDER}-001.md']['error'] == ''
        assert rows[f'{OTHER_SENDER}-001.md']['valid'] is False
        assert rows[f'{OTHER_SENDER}-001.md']['error'] == 'unknown_envelope_version'

    def test_should_not_enumerate_anything_under_the_archive_subdirectory(
        self, plan_context, tmp_path
    ):
        _scaffold(plan_context)
        _write(plan_context, _payload(tmp_path))
        archive_dir = _epic_dir(plan_context) / 'inbox' / 'archive'
        archive_dir.mkdir()
        (archive_dir / f'{OTHER_SENDER}-001.md').write_text('retired\n', encoding='utf-8')

        parsed = _list(plan_context).toon()

        assert [row['name'] for row in parsed['messages']] == [f'{SENDER}-001.md']
        assert parsed['count'] == 1

    def test_should_report_an_unreadable_message_and_still_return_the_rest(
        self, plan_context, tmp_path
    ):
        _scaffold(plan_context)
        _write(plan_context, _payload(tmp_path, 'first', 'a.md'), kind='landing')
        (_epic_dir(plan_context) / 'inbox' / f'{OTHER_SENDER}-001.md').write_bytes(
            b'\xff\xfe not valid utf-8 \xff'
        )
        _write(
            plan_context,
            _payload(tmp_path, 'third', 'c.md'),
            kind='candidate-lesson',
            sender=OTHER_SENDER,
        )

        parsed = _list(plan_context).toon()

        rows = {row['name']: row for row in parsed['messages']}
        assert parsed['count'] == 3
        assert parsed['invalid_count'] == 1
        bad = rows[f'{OTHER_SENDER}-001.md']
        assert bad['valid'] is False
        assert bad['error'] == 'unreadable'
        assert rows[f'{SENDER}-001.md']['valid'] is True
        assert rows[f'{SENDER}-001.md']['error'] == ''
        assert rows[f'{OTHER_SENDER}-002.md']['valid'] is True
        assert rows[f'{OTHER_SENDER}-002.md']['error'] == ''

    def test_should_refuse_an_unscaffolded_epic(self, plan_context):
        result = _list(plan_context, slug='never-scaffolded')

        assert 'error: epic_not_found' in result.stdout

    def test_should_refuse_an_unsafe_slug(self, plan_context):
        result = _list(plan_context, slug='../evil')

        assert 'error: invalid_slug' in result.stdout


# =============================================================================
# Drain surface: inbox archive
# =============================================================================


class TestInboxArchive:
    def test_should_relocate_the_message_and_drop_it_from_the_next_list(
        self, plan_context, tmp_path
    ):
        _scaffold(plan_context)
        _write(plan_context, _payload(tmp_path, 'first', 'a.md'))
        _write(plan_context, _payload(tmp_path, 'second', 'b.md'))

        archived = _archive(plan_context, f'{SENDER}-001.md')

        assert 'status: success' in archived.stdout
        assert 'already_archived: false' in archived.stdout
        inbox = _epic_dir(plan_context) / 'inbox'
        assert not (inbox / f'{SENDER}-001.md').exists()
        assert (inbox / 'archive' / f'{SENDER}-001.md').read_text(
            encoding='utf-8'
        ).endswith('first\n')
        remaining = _list(plan_context).toon()['messages']
        assert [row['name'] for row in remaining] == [f'{SENDER}-002.md']

    def test_should_be_idempotent_on_a_second_archive(self, plan_context, tmp_path):
        _scaffold(plan_context)
        _write(plan_context, _payload(tmp_path))
        _archive(plan_context, f'{SENDER}-001.md')

        second = _archive(plan_context, f'{SENDER}-001.md')

        assert 'status: success' in second.stdout
        assert 'already_archived: true' in second.stdout

    def test_should_refuse_a_path_shaped_message_name(self, plan_context, tmp_path):
        _scaffold(plan_context)
        _write(plan_context, _payload(tmp_path))

        result = _archive(plan_context, f'../{SENDER}-001.md')

        assert 'error: invalid_message_name' in result.stdout
        assert (_epic_dir(plan_context) / 'inbox' / f'{SENDER}-001.md').is_file()

    def test_should_refuse_to_clobber_an_existing_archived_copy(
        self, plan_context, tmp_path
    ):
        _scaffold(plan_context)
        _write(plan_context, _payload(tmp_path, 'original body', 'a.md'))
        _archive(plan_context, f'{SENDER}-001.md')
        inbox = _epic_dir(plan_context) / 'inbox'
        (inbox / f'{SENDER}-001.md').write_text('a resurrected body\n', encoding='utf-8')

        result = _archive(plan_context, f'{SENDER}-001.md')

        assert 'error: archive_conflict' in result.stdout
        assert 'original body' in (inbox / 'archive' / f'{SENDER}-001.md').read_text(
            encoding='utf-8'
        )

    def test_should_report_a_message_present_at_neither_path(self, plan_context):
        _scaffold(plan_context)

        result = _archive(plan_context, f'{SENDER}-404.md')

        assert 'error: file_not_found' in result.stdout

    def test_should_refuse_an_empty_message_name(self, plan_context, tmp_path):
        _scaffold(plan_context)
        _write(plan_context, _payload(tmp_path))

        result = _archive(plan_context, '')

        assert 'error: invalid_message_name' in result.stdout
        assert (_epic_dir(plan_context) / 'inbox' / f'{SENDER}-001.md').is_file()

    def test_should_refuse_an_unsafe_slug(self, plan_context):
        result = _archive(plan_context, f'{SENDER}-001.md', slug='../evil')

        assert 'error: invalid_slug' in result.stdout

    def test_should_refuse_an_unscaffolded_epic(self, plan_context):
        result = _archive(plan_context, f'{SENDER}-001.md', slug='never-scaffolded')

        assert 'error: epic_not_found' in result.stdout

    def test_should_refuse_to_mutate_an_archived_only_epic(self, plan_context, tmp_path):
        _scaffold(plan_context, ARCHIVED_EPIC)
        _write(plan_context, _payload(tmp_path, 'archived body'), slug=ARCHIVED_EPIC)
        archived = _archived_epic_dir(plan_context, ARCHIVED_EPIC)
        archived.parent.mkdir(parents=True, exist_ok=True)
        _epic_dir(plan_context, ARCHIVED_EPIC).rename(archived)

        result = _archive(plan_context, f'{SENDER}-001.md', slug=ARCHIVED_EPIC)

        assert 'error: epic_not_found' in result.stdout
        assert (archived / 'inbox' / f'{SENDER}-001.md').is_file()
        assert not (archived / 'inbox' / 'archive').exists()


# =============================================================================
# Archive-aware allocation and the --as-name recovery, through real argv
# =============================================================================


class TestArchiveAwareAllocationCli:
    def test_should_allocate_above_the_archive_after_a_drain(self, plan_context, tmp_path):
        """(i) write -> archive -> write lands at -002, not back at -001.

        The end-to-end proof that the widened proposal survives the subprocess
        boundary: before the fix the second write re-used ``-001`` and its
        archival was then refused forever.
        """
        _scaffold(plan_context)
        _write(plan_context, _payload(tmp_path, 'first body', 'a.md'))
        _archive(plan_context, f'{SENDER}-001.md')

        second = _write(plan_context, _payload(tmp_path, 'second body', 'b.md'))

        assert f'message: {SENDER}-002.md' in second.stdout
        inbox = _epic_dir(plan_context) / 'inbox'
        assert (inbox / f'{SENDER}-002.md').is_file()
        assert (inbox / 'archive' / f'{SENDER}-001.md').is_file()

    def test_should_archive_the_second_write_without_a_conflict(
        self, plan_context, tmp_path
    ):
        _scaffold(plan_context)
        _write(plan_context, _payload(tmp_path, 'first body', 'a.md'))
        _archive(plan_context, f'{SENDER}-001.md')
        _write(plan_context, _payload(tmp_path, 'second body', 'b.md'))

        result = _archive(plan_context, f'{SENDER}-002.md')

        assert 'status: success' in result.stdout
        assert 'already_archived: false' in result.stdout


class TestInboxArchiveAsNameCli:
    def _strand(self, plan_context, tmp_path) -> Path:
        """Hand-construct the pre-fix stranded state through the CLI surface."""
        _scaffold(plan_context)
        _write(plan_context, _payload(tmp_path, 'stranded body', 'a.md'))
        archive_dir = _epic_dir(plan_context) / 'inbox' / 'archive'
        archive_dir.mkdir(parents=True, exist_ok=True)
        (archive_dir / f'{SENDER}-001.md').write_text(
            'the earlier audit record\n', encoding='utf-8'
        )
        return archive_dir

    def test_should_strand_the_message_without_the_override(self, plan_context, tmp_path):
        # Non-vacuity anchor for the recovery cases below: the default
        # destination genuinely IS refused in this state.
        self._strand(plan_context, tmp_path)

        result = _archive(plan_context, f'{SENDER}-001.md')

        assert 'error: archive_conflict' in result.stdout

    def test_should_recover_a_stranded_message_under_a_sender_preserving_name(
        self, plan_context, tmp_path
    ):
        """(ii) The recovery round trip, through constructed argv."""
        archive_dir = self._strand(plan_context, tmp_path)
        recovery_name = f'{SENDER}-001.dup1.md'

        result = _archive(plan_context, f'{SENDER}-001.md', as_name=recovery_name)

        assert 'status: success' in result.stdout
        assert result.toon()['archived_to'] == str(archive_dir / recovery_name)
        assert (archive_dir / recovery_name).read_text(encoding='utf-8').endswith(
            'stranded body\n'
        )
        assert (archive_dir / f'{SENDER}-001.md').read_text(
            encoding='utf-8'
        ) == 'the earlier audit record\n'
        assert not (_epic_dir(plan_context) / 'inbox' / f'{SENDER}-001.md').exists()

    def test_should_refuse_a_path_shaped_override(self, plan_context, tmp_path):
        """(iii) The retained bare-filename guard survives the CLI boundary."""
        archive_dir = self._strand(plan_context, tmp_path)

        result = _archive(
            plan_context, f'{SENDER}-001.md', as_name=f'../{SENDER}-001.dup1.md'
        )

        assert 'error: invalid_message_name' in result.stdout
        assert (_epic_dir(plan_context) / 'inbox' / f'{SENDER}-001.md').is_file()
        assert sorted(p.name for p in archive_dir.iterdir()) == [f'{SENDER}-001.md']

    def test_should_refuse_a_sender_dropping_override(self, plan_context, tmp_path):
        """(iv) The sender constraint is a DISTINCT code at the argv boundary."""
        archive_dir = self._strand(plan_context, tmp_path)

        result = _archive(plan_context, f'{SENDER}-001.md', as_name='other-001.md')

        assert 'error: as_name_sender_mismatch' in result.stdout
        assert sorted(p.name for p in archive_dir.iterdir()) == [f'{SENDER}-001.md']
        remaining = _list(plan_context).toon()['messages']
        assert [row['name'] for row in remaining] == [f'{SENDER}-001.md']


# =============================================================================
# The write boundary holds on every non-inbox path
# =============================================================================


class TestWriteBoundary:
    def test_should_leave_every_non_inbox_path_byte_identical(
        self, plan_context, tmp_path
    ):
        _scaffold(plan_context)
        root = _epic_dir(plan_context)
        seeded = {
            'status.json': '{"kind": "orchestrator"}',
            'epic.md': '# Epic\n',
            'workstreams/WS-01-a.md': 'charter\n',
            'plans/PLAN-01-a.md': 'spec\n',
            'landings/PLAN-01.md': 'landing\n',
        }
        for rel, content in seeded.items():
            (root / rel).write_text(content, encoding='utf-8')

        _write(plan_context, _payload(tmp_path))

        for rel, content in seeded.items():
            assert (root / rel).read_text(encoding='utf-8') == content, rel

    def test_should_leave_every_non_inbox_path_byte_identical_after_a_drain(
        self, plan_context, tmp_path
    ):
        _scaffold(plan_context)
        root = _epic_dir(plan_context)
        seeded = {
            'status.json': '{"kind": "orchestrator"}',
            'epic.md': '# Epic\n',
            'workstreams/WS-01-a.md': 'charter\n',
            'plans/PLAN-01-a.md': 'spec\n',
            'landings/PLAN-01.md': 'landing\n',
        }
        for rel, content in seeded.items():
            (root / rel).write_text(content, encoding='utf-8')
        _write(plan_context, _payload(tmp_path))

        _list(plan_context)
        _archive(plan_context, f'{SENDER}-001.md')

        for rel, content in seeded.items():
            assert (root / rel).read_text(encoding='utf-8') == content, rel

    def test_should_refuse_an_unsafe_slug(self, plan_context, tmp_path):
        result = _write(plan_context, _payload(tmp_path), slug='../evil')

        assert result.returncode == 0
        assert 'error: invalid_slug' in result.stdout
        assert not (Path(plan_context.fixture_dir) / 'evil').exists()

    def test_should_refuse_an_unknown_kind(self, plan_context, tmp_path):
        _scaffold(plan_context)

        result = _write(plan_context, _payload(tmp_path), kind='gossip')

        assert 'error: invalid_kind' in result.stdout

    def test_should_expose_no_output_path_argument(self, plan_context):
        result = run_script(SCRIPT_PATH, 'inbox', 'write', '--help', env_overrides={})

        for forbidden_flag in ('--path', '--output', '--target', '--file '):
            assert forbidden_flag not in result.stdout, forbidden_flag


# =============================================================================
# Doc contract — all three describe-side surfaces
# =============================================================================


class TestDocContract:
    def test_ledger_write_boundary_still_names_all_five_forbidden_paths(self):
        section = _section(
            _ORCHESTRATION_MODEL.read_text(encoding='utf-8'), '## Ledger Write-Boundary'
        )

        for forbidden in FORBIDDEN_PATHS:
            assert forbidden in section, forbidden

    def test_ledger_write_boundary_names_inbox_as_the_sole_exception(self):
        section = _section(
            _ORCHESTRATION_MODEL.read_text(encoding='utf-8'), '## Ledger Write-Boundary'
        )

        assert 'The one sanctioned exception' in section
        assert 'inbox/{sender}-{seq}' in section

    def test_ledger_write_boundary_carries_all_three_qualifiers(self):
        section = _section(
            _ORCHESTRATION_MODEL.read_text(encoding='utf-8'), '## Ledger Write-Boundary'
        )

        for qualifier in ('Append-only', 'Own-file-only', 'One-way'):
            assert qualifier in section, qualifier

    def test_ledger_write_boundary_points_at_the_envelope_standard(self):
        section = _section(
            _ORCHESTRATION_MODEL.read_text(encoding='utf-8'), '## Ledger Write-Boundary'
        )

        assert 'inbox-envelope.md' in section
        assert 'orchestrator inbox write' in section

    def test_directory_layout_includes_inbox(self):
        section = _section(
            _ORCHESTRATION_MODEL.read_text(encoding='utf-8'), '## Directory Layout'
        )

        assert 'inbox/' in section

    def test_dispatch_rule_s2_names_the_leaf_class_it_governs(self):
        section = _section(
            _ORCHESTRATION_MODEL.read_text(encoding='utf-8'), '## Dispatch Decision Rule'
        )
        s2 = _line(section, '- **S2')

        assert 'dispatched by an orchestrator verb' in s2
        assert 'Ledger Write-Boundary' in s2

    def test_dispatch_rule_s2_no_longer_states_the_unqualified_absolute(self):
        section = _section(
            _ORCHESTRATION_MODEL.read_text(encoding='utf-8'), '## Dispatch Decision Rule'
        )
        s2 = _line(section, '- **S2')

        assert 'No dispatched leaf writes inside' not in s2

    def test_plan_spec_template_drops_the_superseded_absolute(self):
        text = _PLAN_SPEC_TEMPLATE.read_text(encoding='utf-8')

        assert 'through its PR alone' not in text
        assert 'other than its own' in _section(text, '## Write-Boundary')

    def test_plan_spec_template_names_both_report_channels(self):
        section = _section(
            _PLAN_SPEC_TEMPLATE.read_text(encoding='utf-8'), '## Write-Boundary'
        )

        assert 'its PR and its inbox message' in section
        assert 'Ledger Write-Boundary' in section

    def test_inbox_validate_documents_both_success_branches(self):
        section = _section(
            _ORCHESTRATOR_SKILL.read_text(encoding='utf-8'), '### inbox validate'
        )

        for token in ('location: queued', 'location: archived', 'archive_path'):
            assert token in section, token

    def test_inbox_validate_documents_the_narrowed_file_not_found(self):
        section = _section(
            _ORCHESTRATOR_SKILL.read_text(encoding='utf-8'), '### inbox validate'
        )

        assert 'file_not_found' in section
        assert 'inbox/archive/' in section

    def test_inbox_validate_still_lists_every_retained_rejection_code(self):
        # The archive-probe change narrows file_not_found; it must not quietly
        # drop any envelope-validation code from the documented surface.
        section = _section(
            _ORCHESTRATOR_SKILL.read_text(encoding='utf-8'), '### inbox validate'
        )

        for code in (
            'missing_header_field',
            'unknown_envelope_version',
            'invalid_sender_type',
            'invalid_kind',
            'empty_payload',
            'epic_mismatch',
            'filename_sender_mismatch',
            'invalid_message_name',
        ):
            assert code in section, code

    def test_drain_semantics_records_the_read_side_of_the_consume_marker(self):
        section = _section(_INBOX_ENVELOPE.read_text(encoding='utf-8'), '## Drain semantics')

        assert 'Archival is the consume marker' in section
        assert 'inbox validate` resolves the archive' in section

    def test_validator_error_code_table_is_not_read_as_exhaustive(self):
        section = _section(
            _INBOX_ENVELOPE.read_text(encoding='utf-8'), '## Validator error codes'
        )

        assert 'resolution' in section
        assert 'location' in section
