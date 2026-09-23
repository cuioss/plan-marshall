#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the plan-orchestrator scaffolding script (D7).

Covers the ``scaffold`` / ``queue`` / ``resume-summary`` verbs under
``PLAN_BASE_DIR`` isolation (via ``plan_context``). The ``archive`` verb has
its own module (``test_orchestrator_archive.py``), and the ``inbox`` verb
group's envelope schema and handler surface have theirs
(``test_inbox_envelope.py``):

- ``scaffold``: directory-tree creation (including ``inbox/``) and idempotency.
- ``queue``: read, transition, per-row field-set, and single-row append
  round-trips against a per-concern fixture ledger (seeded through
  ``_ledger_fixtures.write_ledger``), plus the error envelopes (missing header,
  malformed header, unknown plan, unknown field, invalid plan id, duplicate plan
  id, unreadable row file, unpaired flags, mutually-exclusive write forms). Each
  write form is asserted to touch ONE row file and to stamp no shared
  ``updated`` field. The append form discriminates the header three ways —
  absent, present-but-not-a-JSON-object, and a JSON object including the empty
  ``{}`` — and all three arms are asserted together so the guard can be met
  neither by refusing everything nor by admitting everything; a monolithic
  (legacy-layout) ledger is refused with ``legacy_layout`` by every form, with a
  migrated control beside it. It also carries the three-valued spec-presence
  probe, whose ``absent`` and ``unlistable`` verdicts are asserted apart so a
  measured negative is never confused with an unobserved one. The settled status
  vocabulary is pinned as a matched pair — every member of
  ``VALID_STATUS_VOCABULARY`` transitions, and a plausible non-member is still
  refused with nothing written — because the acceptance arm alone would pass for
  a validator that accepted anything.
- ``migrate-layout``: conversion fidelity (every row value, the anchor text, and
  every header value survive), generated-block removal that leaves every
  hand-written byte of ``epic.md`` identical, a written ``queue-view.md`` equal
  to a fresh render, idempotence, a re-run that finishes a tail an interrupted
  run left undone, archived-epic resolution, and the refusals.
- status vocabulary: the construction the settled set rests on — the three
  declaring sets partition ``VALID_STATUS_VOCABULARY`` exactly (summed against
  distinct, so a repeat the ``frozenset`` union absorbs is still seen),
  ``TERMINAL_PLAN_STATUSES`` is the two terminal sets joined, and
  ``LIVE_QUEUE_EXCLUDED_STATUSES`` is asserted to be the SAME OBJECT rather than
  an equal copy. Both count-claim directions are covered over the whole noun
  population: every legal status is a checkable noun, and every noun both
  matches the derived alternation and resolves to a ``_derive_counts`` key.
- doc contract: ALL THREE enumerations SKILL.md mirrors are extracted through one
  shared anchored reader and asserted EQUAL to their declaring constants in both
  directions — the ``--field`` whitelist against ``PLAN_ROW_FIELDS``, which
  ``cmd_queue`` validates against, the ``--status`` vocabulary against
  ``VALID_STATUS_VOCABULARY``, which ``cmd_queue`` validates against, and the
  ``--add-row`` seed fields against ``ADD_ROW_SEED_FIELDS``. Each check asserts its anchored extraction and both
  populations non-empty FIRST, so an equality can never pass over two empty
  sets. The seed fields are additionally asserted in DECLARATION ORDER, because
  that tuple's order is the key order an appended row is written in; the
  whitelist's ``frozenset`` declares no order and none is pinned for it.
- ``resume-summary``: START-HERE block generation derived purely from
  the ledger (resume anchor, phase, running/parked plans, ordered queue),
  including the two questions the terminal statuses answer separately — a
  closed-without-shipping row is excluded from the live queue like a shipped one
  but carries no ``(!) missing: …`` marker, asserted per rendered LINE so the
  pair is a control rather than a whole-block substring test — plus
  the render-time-derived inbox counts — which come from the epic's ``inbox/``
  directory rather than from the anchor's prose, keep the two zeros
  (``present`` / ``missing``) distinct, and sit beside a stale anchor sentence
  that is still rendered verbatim.
- CLI boundary: the three verbs above driven through the ``orchestrator.py``
  entry point with constructed argv at the subprocess boundary
  (``run_script``); the ``inbox`` group's CLI wiring is covered in
  ``test_inbox_channel_contract.py``.
"""

import argparse
import copy
import json
import re
from collections.abc import Collection
from pathlib import Path
from typing import Any

import pytest
from _ledger_fixtures import read_rows, write_ledger, write_legacy_status

from conftest import get_script_path, load_script_module, parse_ns, run_script

#: The orchestrator script's address, as module-level string constants so every
#: ``parse_ns`` call below stays statically resolvable.
_ORCH_BUNDLE = 'plan-marshall'
_ORCH_SKILL = 'plan-orchestrator'
_ORCH_SCRIPT = 'orchestrator.py'

SCRIPT_PATH = get_script_path(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT)

#: The skill doc that publishes the CLI contract, resolved from the script path
#: so the two can never point at different installations
#: (``.../{skill}/scripts/orchestrator.py`` -> ``.../{skill}/SKILL.md``).
SKILL_MD_PATH = Path(SCRIPT_PATH).parent.parent / 'SKILL.md'

#: The fixed anchors SKILL.md publishes its two mirrored enumerations behind.
#: The doc keeps each list on its own line specifically so these are LINE lookups
#: rather than prose scans; if an anchor is ever reworded the extractor returns
#: nothing, which the non-vacuity assertions below turn into a failure instead of
#: a silent pass.
FIELD_WHITELIST_ANCHOR = '`--field` whitelist (mirrors `PLAN_ROW_FIELDS`):'
ADD_ROW_SEED_FIELDS_ANCHOR = '`--add-row` seed fields (mirrors `ADD_ROW_SEED_FIELDS`):'
STATUS_VOCABULARY_ANCHOR = '`--status` vocabulary (mirrors `VALID_STATUS_VOCABULARY`):'

#: Every backticked token, used to lift the whitelist entries off the anchored
#: line.
_BACKTICKED_RE = re.compile(r'`([^`]+)`')

_orch = load_script_module(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, 'orchestrator_script')

cmd_scaffold = _orch.cmd_scaffold
cmd_queue = _orch.cmd_queue
cmd_inbox_list = _orch.cmd_inbox_list
cmd_resume_summary = _orch.cmd_resume_summary
cmd_regenerate_view = _orch.cmd_regenerate_view
cmd_migrate_layout = _orch.cmd_migrate_layout
render_queue_view = _orch.render_queue_view
EPIC_SUBDIRS = _orch.EPIC_SUBDIRS
PLAN_ROW_FIELDS = _orch.PLAN_ROW_FIELDS
ADD_ROW_SEED_FIELDS = _orch.ADD_ROW_SEED_FIELDS
VALID_STATUS_VOCABULARY = _orch.VALID_STATUS_VOCABULARY
LIVE_PLAN_STATUSES = _orch.LIVE_PLAN_STATUSES
SHIPPED_PLAN_STATUSES = _orch.SHIPPED_PLAN_STATUSES
CLOSED_UNSHIPPED_PLAN_STATUSES = _orch.CLOSED_UNSHIPPED_PLAN_STATUSES
TERMINAL_PLAN_STATUSES = _orch.TERMINAL_PLAN_STATUSES
LIVE_QUEUE_EXCLUDED_STATUSES = _orch.LIVE_QUEUE_EXCLUDED_STATUSES
COUNT_CLAIM_NOUNS = _orch.COUNT_CLAIM_NOUNS

#: The declaring-set roster the module's own construction check reports over —
#: taken from the source rather than re-listed here, so the controls below range
#: over whatever set the production partition is actually built from.
DECLARED_STATUS_SETS = _orch._DECLARED_STATUS_SETS

#: The count-claim machinery is reached through its private names deliberately:
#: the KeyError this module pins is raised INSIDE ``_count_divergences`` at
#: ``derived[key]``, so the join it would fail on — noun to alternation to
#: derivation key — is what has to be exercised, not the rendered payload the
#: detector's own test module already drives.
_derive_counts = _orch._derive_counts
_claim_key = _orch._claim_key
_COUNT_CLAIM_RE = _orch._COUNT_CLAIM_RE

FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'

#: The slug every hoisted base below is parsed with. Each test overrides it
#: through :func:`_variant`, so the value is a placeholder rather than a fixture.
_BASE_SLUG = 'base-epic'


# =============================================================================
# Parser-derived argument namespaces
# =============================================================================
#
# One hoisted namespace per verb, built by the orchestrator's OWN parser so each
# carries every default the production CLI applies rather than only the fields a
# test author remembered. ``parse_ns`` re-executes the script module on every
# call, so these live at module scope and each test derives its own slug through
# :func:`_variant` instead of parsing again. ``register=False`` throughout: only
# the namespace is wanted, and publishing ``orchestrator`` in ``sys.modules``
# would displace the explicitly-named registration above.


def _variant(base: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    """Derive a namespace from a hoisted parser-derived base.

    The base supplies every parser default; ``overrides`` names only the fields
    this call differs in. A shallow copy is enough because a namespace's values
    are the parser's own scalars, and the base must stay unmutated for the other
    callers sharing it.
    """
    derived = copy.copy(base)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


_SCAFFOLD_ARGS = parse_ns(
    _ORCH_BUNDLE,
    _ORCH_SKILL,
    _ORCH_SCRIPT,
    'scaffold',
    '--slug',
    _BASE_SLUG,
    register=False,
)

_QUEUE_ARGS = parse_ns(
    _ORCH_BUNDLE,
    _ORCH_SKILL,
    _ORCH_SCRIPT,
    'queue',
    '--slug',
    _BASE_SLUG,
    register=False,
)

_RESUME_SUMMARY_ARGS = parse_ns(
    _ORCH_BUNDLE,
    _ORCH_SKILL,
    _ORCH_SCRIPT,
    'resume-summary',
    '--slug',
    _BASE_SLUG,
    register=False,
)

_INBOX_LIST_ARGS = parse_ns(
    _ORCH_BUNDLE,
    _ORCH_SKILL,
    _ORCH_SCRIPT,
    'inbox',
    'list',
    '--slug',
    _BASE_SLUG,
    register=False,
)

_REGENERATE_VIEW_ARGS = parse_ns(
    _ORCH_BUNDLE,
    _ORCH_SKILL,
    _ORCH_SCRIPT,
    'regenerate-view',
    '--slug',
    _BASE_SLUG,
    register=False,
)

_MIGRATE_ARGS = parse_ns(
    _ORCH_BUNDLE,
    _ORCH_SKILL,
    _ORCH_SCRIPT,
    'migrate-layout',
    '--slug',
    _BASE_SLUG,
    register=False,
)


def _epic_dir(plan_context, slug: str) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / slug


def _queue_args(
    slug: str,
    transition: str | None = None,
    status: str | None = None,
    set_row: str | None = None,
    field: str | None = None,
    value: str | None = None,
    add_row: str | None = None,
    slug_value: str | None = None,
    workstream: str | None = None,
) -> argparse.Namespace:
    """Derive a complete ``queue`` namespace so every flag attribute is present."""
    return _variant(
        _QUEUE_ARGS,
        slug=slug,
        transition=transition,
        status=status,
        set_row=set_row,
        field=field,
        value=value,
        add_row=add_row,
        slug_value=slug_value,
        workstream=workstream,
    )


def _make_plan(
    plan_id: str,
    status: str = 'staged',
    workstream: str = 'WS-01',
    plan_marshall_plan_id: str = '',
    pr: str = '',
    landing: str = '',
) -> dict:
    return {
        'id': plan_id,
        'slug': plan_id.lower(),
        'workstream': workstream,
        'status': status,
        'plan_marshall_plan_id': plan_marshall_plan_id,
        'pr': pr,
        'landing': landing,
    }


def _fixture_doc(
    plans: list[dict] | None = None,
    phase: str = 'orchestrating',
    resume_anchor: str = 'await PR #912 CI, then analyze landing',
) -> dict[str, Any]:
    """A legacy-SHAPED fixture dict — the shape the assembled view hands back."""
    return {
        'kind': 'orchestrator',
        'title': 'Fixture Epic',
        'phase': phase,
        'workstreams': ['WS-01'],
        'plans': plans if plans is not None else [],
        'resume_anchor': resume_anchor,
        'metadata': {},
        'created': FIXED_TIMESTAMP,
        'updated': FIXED_TIMESTAMP,
    }


def _write_status(
    plan_context,
    slug: str,
    plans: list[dict] | None = None,
    phase: str = 'orchestrating',
    resume_anchor: str = 'await PR #912 CI, then analyze landing',
) -> Path:
    """Seed a per-concern kind=orchestrator ledger into the isolated store; return the epic root.

    The fixture dict is materialised through the production conversion
    (:func:`_ledger_fixtures.write_ledger`): the header lands in ``status.json``,
    the anchor in ``resume_anchor.md``, and each row in ``queue/{PLAN-ID}.json``
    with a ``seq`` taken from its position.
    """
    root = _epic_dir(plan_context, slug)
    write_ledger(root, _fixture_doc(plans, phase, resume_anchor))
    return root


def _rows(root: Path) -> list[dict]:
    """The queue rows at ``root`` through the production reader, ``seq`` included."""
    return read_rows(root)


def _rows_without_seq(root: Path) -> list[dict]:
    """The queue rows with ``seq`` dropped, for comparison against :func:`_make_plan` rows."""
    return [{key: value for key, value in row.items() if key != 'seq'} for row in read_rows(root)]


def _header(root: Path) -> dict:
    return dict(json.loads((root / 'status.json').read_text(encoding='utf-8')))


def _snapshot(root: Path) -> dict[str, bytes]:
    """Every file under ``root`` keyed by its relative path, as bytes — a write detector."""
    return {str(path.relative_to(root)): path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}


def _seed_inbox(plan_context, slug: str, queued: int = 0, archived: int = 0, extra_names: tuple = ()) -> Path:
    """Create the epic's ``inbox/`` with ``queued`` live and ``archived`` retired messages.

    Names follow the channel's ``{sender}-{NNN}.md`` grammar so the derivation
    counts them; ``extra_names`` seeds off-shape files that MUST NOT be counted.
    """
    inbox = _epic_dir(plan_context, slug) / 'inbox'
    inbox.mkdir(parents=True, exist_ok=True)
    for index in range(1, queued + 1):
        (inbox / f'sender-{index:03d}.md').write_text('queued', encoding='utf-8')
    if archived or extra_names:
        archive = inbox / 'archive'
        archive.mkdir(exist_ok=True)
        for index in range(1, archived + 1):
            (archive / f'retired-{index:03d}.md').write_text('gone', encoding='utf-8')
        for name in extra_names:
            (archive / name).write_text('off shape', encoding='utf-8')
    return inbox


# =============================================================================
# scaffold
# =============================================================================


class TestScaffold:
    def test_should_create_epic_directory_tree(self, plan_context):
        result = cmd_scaffold(_variant(_SCAFFOLD_ARGS, slug='fresh-epic'))

        assert result['status'] == 'success'
        assert result['operation'] == 'scaffold'
        assert result['already_existed'] is False
        root = _epic_dir(plan_context, 'fresh-epic')
        assert result['root'] == str(root)
        assert root.is_dir()
        for sub in ('workstreams', 'plans', 'landings', 'logs', 'inbox'):
            assert (root / sub).is_dir()

    def test_should_report_all_layout_subdirs(self, plan_context):
        result = cmd_scaffold(_variant(_SCAFFOLD_ARGS, slug='layout-epic'))

        assert sorted(result['directories']) == sorted(EPIC_SUBDIRS)
        assert set(EPIC_SUBDIRS) == {'workstreams', 'plans', 'landings', 'logs', 'inbox'}

    def test_should_be_idempotent_on_rerun(self, plan_context):
        cmd_scaffold(_variant(_SCAFFOLD_ARGS, slug='rerun-epic'))
        marker = _epic_dir(plan_context, 'rerun-epic') / 'plans' / 'PLAN-01-keep.md'
        marker.write_text('kept', encoding='utf-8')

        result = cmd_scaffold(_variant(_SCAFFOLD_ARGS, slug='rerun-epic'))

        assert result['status'] == 'success'
        assert result['already_existed'] is True
        assert marker.read_text(encoding='utf-8') == 'kept'

    def test_should_not_create_status_json(self, plan_context):
        cmd_scaffold(_variant(_SCAFFOLD_ARGS, slug='no-status-epic'))

        assert not (_epic_dir(plan_context, 'no-status-epic') / 'status.json').exists()

    def test_should_reject_invalid_slug(self, plan_context):
        result = cmd_scaffold(_variant(_SCAFFOLD_ARGS, slug='../evil'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'
        assert not (plan_context.fixture_dir / 'evil').exists()

    def test_should_reject_empty_slug(self, plan_context):
        result = cmd_scaffold(_variant(_SCAFFOLD_ARGS, slug=''))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'


# =============================================================================
# queue — read
# =============================================================================


class TestQueueRead:
    def test_should_return_phase_anchor_and_plans(self, plan_context):
        plans = [_make_plan('PLAN-01'), _make_plan('PLAN-02', status='running')]
        _write_status(plan_context, 'read-epic', plans=plans)

        result = cmd_queue(_queue_args('read-epic'))

        assert result['status'] == 'success'
        assert result['operation'] == 'queue'
        assert result['phase'] == 'orchestrating'
        assert result['resume_anchor'] == 'await PR #912 CI, then analyze landing'
        assert result['plans'] == [{**plan, 'seq': index} for index, plan in enumerate(plans, start=1)]
        assert result['unreadable_row_count'] == 0

    def test_should_order_rows_by_seq_then_id(self, plan_context):
        root = _write_status(plan_context, 'order-epic', plans=[_make_plan('PLAN-02'), _make_plan('PLAN-01')])

        result = cmd_queue(_queue_args('order-epic'))

        # Staging order (seq) wins over the id's own sort order.
        assert [row['id'] for row in result['plans']] == ['PLAN-02', 'PLAN-01']
        assert [row['seq'] for row in _rows(root)] == [1, 2]

    def test_should_name_an_unreadable_row_rather_than_drop_it_silently(self, plan_context):
        root = _write_status(plan_context, 'unread-epic', plans=[_make_plan('PLAN-01'), _make_plan('PLAN-02')])
        (root / 'queue' / 'PLAN-02.json').write_text('<<<<<<< ours\n{}\n', encoding='utf-8')

        result = cmd_queue(_queue_args('unread-epic'))

        assert result['status'] == 'success'
        assert [row['id'] for row in result['plans']] == ['PLAN-01']
        assert result['unreadable_row_count'] == 1
        assert result['unreadable_rows'] == ['PLAN-02.json']

    def test_should_error_when_status_json_missing(self, plan_context):
        cmd_scaffold(_variant(_SCAFFOLD_ARGS, slug='bare-epic'))

        result = cmd_queue(_queue_args('bare-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'

    def test_should_reject_invalid_slug(self, plan_context):
        result = cmd_queue(_queue_args('../evil'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'


# =============================================================================
# queue — transition
# =============================================================================


class TestQueueTransition:
    def test_should_round_trip_status_transition(self, plan_context):
        root = _write_status(plan_context, 'flow-epic', plans=[_make_plan('PLAN-01'), _make_plan('PLAN-02')])

        result = cmd_queue(_queue_args('flow-epic', transition='PLAN-01', status='running'))

        assert result['status'] == 'success'
        assert result['operation'] == 'queue-transition'
        assert result['plan'] == 'PLAN-01'
        assert result['previous_status'] == 'staged'
        assert result['new_status'] == 'running'
        on_disk = _rows(root)
        assert on_disk[0]['status'] == 'running'
        assert on_disk[1]['status'] == 'staged'

    def test_should_write_only_the_transitioned_row_file(self, plan_context):
        # One-row-file operation: the header, the anchor and every sibling row
        # file are byte-identical afterwards, and no shared ``updated`` stamp is
        # written anywhere — that stamp was the collision line the per-concern
        # layout removes.
        root = _write_status(plan_context, 'stamp-epic', plans=[_make_plan('PLAN-01'), _make_plan('PLAN-02')])
        before = _snapshot(root)

        cmd_queue(_queue_args('stamp-epic', transition='PLAN-01', status='parked'))

        after = _snapshot(root)
        changed = sorted(name for name in after if after[name] != before.get(name))
        assert changed == [str(Path('queue') / 'PLAN-01.json')]
        assert 'updated' not in _header(root)

    def test_should_read_back_transitioned_state(self, plan_context):
        _write_status(plan_context, 'roundtrip-epic', plans=[_make_plan('PLAN-01')])
        cmd_queue(_queue_args('roundtrip-epic', transition='PLAN-01', status='landed'))

        result = cmd_queue(_queue_args('roundtrip-epic'))

        assert result['plans'][0]['status'] == 'landed'

    def test_should_error_for_unknown_plan_id(self, plan_context):
        _write_status(plan_context, 'miss-epic', plans=[_make_plan('PLAN-01')])

        result = cmd_queue(_queue_args('miss-epic', transition='PLAN-99', status='running'))

        assert result['status'] == 'error'
        assert result['error'] == 'plan_not_found'
        assert result['available_plans'] == ['PLAN-01']

    def test_should_require_status_with_transition(self, plan_context):
        _write_status(plan_context, 'pair-epic', plans=[_make_plan('PLAN-01')])

        result = cmd_queue(_queue_args('pair-epic', transition='PLAN-01'))

        assert result['status'] == 'error'
        assert result['error'] == 'wrong_parameters'

    def test_should_require_transition_with_status(self, plan_context):
        _write_status(plan_context, 'pair2-epic', plans=[_make_plan('PLAN-01')])

        result = cmd_queue(_queue_args('pair2-epic', status='running'))

        assert result['status'] == 'error'
        assert result['error'] == 'wrong_parameters'

    def test_should_error_when_status_json_missing(self, plan_context):
        result = cmd_queue(_queue_args('absent-epic', transition='PLAN-01', status='running'))

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'


class TestQueueTransitionStatusVocabulary:
    """Every vocabulary member transitions, and a non-member is still refused.

    The matched pair the settled vocabulary needs. The positive arm alone would
    pass for a validator that accepted anything at all, and the negative arm
    alone would pass for one that had never been widened; only the two together
    say that the set grew AND stayed closed.

    The positive arm's cases are DERIVED from ``VALID_STATUS_VOCABULARY`` rather
    than listed, so a member added to the constant is exercised here without an
    edit — and the population is asserted non-empty first, because a
    parametrization over an emptied constant would collect no cases and report
    green over nothing.
    """

    def test_the_parametrized_vocabulary_population_is_not_empty(self):
        assert VALID_STATUS_VOCABULARY, (
            'VALID_STATUS_VOCABULARY is empty (population 0), so the '
            'parametrized acceptance arm below would generate no cases at all '
            'and pass by collecting nothing'
        )

    @pytest.mark.parametrize('status', sorted(VALID_STATUS_VOCABULARY))
    def test_should_accept_every_vocabulary_member(self, plan_context, status):
        slug = f'vocab-{status}-epic'
        root = _write_status(plan_context, slug, plans=[_make_plan('PLAN-01', status='launched')])

        result = cmd_queue(_queue_args(slug, transition='PLAN-01', status=status))

        assert result['status'] == 'success'
        assert result['new_status'] == status
        assert _rows(root)[0]['status'] == status

    def test_should_refuse_a_non_member_leaving_the_row_untouched(self, plan_context):
        # ``abandoned`` is plausible and deliberately outside the settled set:
        # widening the vocabulary to cover the ledger's real end states must not
        # have widened it to any end state someone can name.
        root = _write_status(plan_context, 'vocab-reject-epic', plans=[_make_plan('PLAN-01')])

        result = cmd_queue(_queue_args('vocab-reject-epic', transition='PLAN-01', status='abandoned'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_field'
        assert _rows(root)[0]['status'] == 'staged'


# =============================================================================
# queue — set-row
# =============================================================================


class TestQueueSetRow:
    def test_should_set_named_row_field_and_leave_siblings_untouched(self, plan_context):
        siblings = [_make_plan('PLAN-02'), _make_plan('PLAN-03', status='running')]
        root = _write_status(plan_context, 'set-epic', plans=[_make_plan('PLAN-01'), *siblings])

        result = cmd_queue(_queue_args('set-epic', set_row='PLAN-01', field='pr', value='#1001'))

        assert result['status'] == 'success'
        assert result['operation'] == 'queue-set-row'
        assert result['plan'] == 'PLAN-01'
        assert result['field'] == 'pr'
        assert result['previous_value'] == ''
        assert result['new_value'] == '#1001'
        on_disk = _rows_without_seq(root)
        assert on_disk[0]['pr'] == '#1001'
        assert on_disk[1:] == siblings

    def test_should_round_trip_every_whitelisted_field(self, plan_context):
        _write_status(plan_context, 'fields-epic', plans=[_make_plan('PLAN-01')])
        values = {
            'plan_marshall_plan_id': 'epic-plan-1',
            'pr': '#1002',
            'landing': 'PLAN-01.md',
        }
        assert set(values) == set(PLAN_ROW_FIELDS)

        for field, value in values.items():
            cmd_queue(_queue_args('fields-epic', set_row='PLAN-01', field=field, value=value))

        row = cmd_queue(_queue_args('fields-epic'))['plans'][0]
        for field, value in values.items():
            assert row[field] == value

    def test_should_report_previous_value_on_overwrite(self, plan_context):
        _write_status(plan_context, 'overwrite-epic', plans=[_make_plan('PLAN-01', pr='#900')])

        result = cmd_queue(_queue_args('overwrite-epic', set_row='PLAN-01', field='pr', value='#901'))

        assert result['previous_value'] == '#900'
        assert result['new_value'] == '#901'

    def test_should_leave_the_header_byte_identical_on_set_row(self, plan_context):
        root = _write_status(plan_context, 'set-stamp-epic', plans=[_make_plan('PLAN-01')])
        header_before = (root / 'status.json').read_bytes()

        cmd_queue(_queue_args('set-stamp-epic', set_row='PLAN-01', field='landing', value='x.md'))

        assert (root / 'status.json').read_bytes() == header_before
        assert _rows(root)[0]['landing'] == 'x.md'

    def test_should_refuse_an_unreadable_row_file_rather_than_overwrite_it(self, plan_context):
        root = _write_status(plan_context, 'set-unread-epic', plans=[_make_plan('PLAN-01')])
        row_file = root / 'queue' / 'PLAN-01.json'
        conflicted = '<<<<<<< ours\n{"id": "PLAN-01"}\n=======\n{"id": "PLAN-01"}\n>>>>>>> theirs\n'
        row_file.write_text(conflicted, encoding='utf-8')

        result = cmd_queue(_queue_args('set-unread-epic', set_row='PLAN-01', field='pr', value='#1'))

        assert result['status'] == 'error'
        assert result['error'] == 'row_unreadable'
        assert row_file.read_text(encoding='utf-8') == conflicted

    def test_should_error_for_unknown_plan_id(self, plan_context):
        _write_status(plan_context, 'set-miss-epic', plans=[_make_plan('PLAN-01')])

        result = cmd_queue(_queue_args('set-miss-epic', set_row='PLAN-99', field='pr', value='#1'))

        assert result['status'] == 'error'
        assert result['error'] == 'plan_not_found'
        assert result['available_plans'] == ['PLAN-01']

    def test_should_error_for_unknown_field(self, plan_context):
        root = _write_status(plan_context, 'set-field-epic', plans=[_make_plan('PLAN-01')])

        result = cmd_queue(_queue_args('set-field-epic', set_row='PLAN-01', field='status', value='shipped'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_field'
        assert 'landing' in result['message']
        assert _rows(root)[0]['status'] == 'staged'

    def test_should_require_field_and_value_with_set_row(self, plan_context):
        _write_status(plan_context, 'set-pair-epic', plans=[_make_plan('PLAN-01')])

        result = cmd_queue(_queue_args('set-pair-epic', set_row='PLAN-01'))

        assert result['status'] == 'error'
        assert result['error'] == 'wrong_parameters'

    def test_should_require_set_row_with_field(self, plan_context):
        _write_status(plan_context, 'set-pair2-epic', plans=[_make_plan('PLAN-01')])

        result = cmd_queue(_queue_args('set-pair2-epic', field='pr', value='#1'))

        assert result['status'] == 'error'
        assert result['error'] == 'wrong_parameters'

    def test_should_reject_set_row_combined_with_transition(self, plan_context):
        _write_status(plan_context, 'set-excl-epic', plans=[_make_plan('PLAN-01')])

        result = cmd_queue(
            _queue_args(
                'set-excl-epic',
                transition='PLAN-01',
                status='shipped',
                set_row='PLAN-01',
                field='pr',
                value='#1',
            )
        )

        assert result['status'] == 'error'
        assert result['error'] == 'wrong_parameters'

    def test_should_error_when_status_json_missing(self, plan_context):
        result = cmd_queue(_queue_args('set-absent-epic', set_row='PLAN-01', field='pr', value='#1'))

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'


# =============================================================================
# the status vocabulary — construction, and the consumers derived from it
# =============================================================================


def _partition_surplus(*declaring_sets: Collection[str]) -> int:
    """How many members the declaring sets carry beyond the distinct union.

    The partition rule itself, lifted out so it can be applied to SYNTHETIC
    declaring sets. The assertion below claims the rule sees two different
    shapes — a value repeated inside one declaring set, and a value shared
    between two — and a claim of that kind is only worth what its controls
    prove, so the rule is exercised against both shapes rather than described.
    """
    declared = [status for members in declaring_sets for status in members]
    return len(declared) - len({*declared})


class TestStatusVocabularyConstruction:
    """The vocabulary is DERIVED from three declaring sets, and they partition it.

    The derivation is what makes a status added later reach every consumer or
    none. Two properties carry it and neither is self-evident from reading the
    constants: the three declaring sets must partition the vocabulary exactly
    (the ``frozenset`` union absorbs a repeat silently, so a summed-versus-
    distinct comparison is the only thing that sees one), and the live-queue
    exclusion must remain the SAME OBJECT as the terminal set rather than an
    equal copy that a later edit could move independently.

    ⛔ **The both-shapes claim rests on the declarations being SEQUENCES**, and
    that dependency is pinned rather than assumed. A declaring set written as a
    ``frozenset`` would discard its own repeat before the expansion ever saw it,
    narrowing the check to cross-set overlap alone while the message went on
    claiming both — the overclaiming-guard shape. The type control below fails
    the moment a declaration stops preserving a repeat, so the message cannot
    outlive the mechanism behind it.
    """

    def test_the_declaring_sets_partition_the_vocabulary_exactly(self):
        declared = [*LIVE_PLAN_STATUSES, *SHIPPED_PLAN_STATUSES, *CLOSED_UNSHIPPED_PLAN_STATUSES]

        assert set(declared) == set(VALID_STATUS_VOCABULARY), (
            f'the declaring sets resolve to {sorted(set(declared))} but the vocabulary is '
            f'{sorted(VALID_STATUS_VOCABULARY)}'
        )
        assert len(declared) == len(VALID_STATUS_VOCABULARY), (
            f'the declaring sets carry {len(declared)} member(s) but only '
            f'{len(VALID_STATUS_VOCABULARY)} are distinct: a status is repeated within one '
            'set or shared between two, which the frozenset union would absorb silently'
        )

    def test_every_declaring_set_preserves_a_repeat_rather_than_absorbing_it(self):
        """The property the intra-set half of the message depends on.

        The roster comes from the production constant, so a fourth declaring set
        added later is checked here without editing this test.
        """
        assert DECLARED_STATUS_SETS, 'the declaring-set roster is empty — this control checks nothing'

        set_like = {
            name: type(members).__name__
            for name, members in DECLARED_STATUS_SETS.items()
            if not isinstance(members, (tuple, list))
        }
        assert not set_like, (
            f'{set_like} do not preserve a repeated member, so the partition check above sees '
            'cross-set overlap ONLY — its message claims a shape the mechanism no longer has'
        )

    @pytest.mark.parametrize(
        ('declaring_sets', 'expected_surplus'),
        (
            ((('staged', 'running'), ('shipped',)), 0),
            ((('staged', 'running', 'staged'), ('shipped',)), 1),
            ((('staged', 'running'), ('running', 'shipped')), 1),
        ),
        ids=['a-clean-partition', 'a-repeat-within-one-set', 'a-value-shared-between-two-sets'],
    )
    def test_the_partition_rule_sees_both_shapes_its_message_names(self, declaring_sets, expected_surplus):
        """Both claimed shapes, against a clean partition that must stay silent.

        The clean row is the matched control: without it a rule that reported a
        surplus for everything would satisfy both positive rows.
        """
        assert _partition_surplus(*declaring_sets) == expected_surplus

    def test_the_rule_is_the_one_the_real_partition_check_applies(self):
        """The controls above are only load-bearing if this IS that comparison.

        Asserted as an equality between the helper and the live expression over
        the real declaring sets, so a helper that drifted from the production
        rule fails here rather than certifying a rule nothing uses.
        """
        declared = [*LIVE_PLAN_STATUSES, *SHIPPED_PLAN_STATUSES, *CLOSED_UNSHIPPED_PLAN_STATUSES]

        assert _partition_surplus(*DECLARED_STATUS_SETS.values()) == len(declared) - len(VALID_STATUS_VOCABULARY)
        assert _partition_surplus(*DECLARED_STATUS_SETS.values()) == 0, (
            'the shipped declaring sets already carry a surplus — the partition is broken'
        )

    def test_terminal_is_the_two_terminal_sets_joined_in_order(self):
        assert TERMINAL_PLAN_STATUSES == (*SHIPPED_PLAN_STATUSES, *CLOSED_UNSHIPPED_PLAN_STATUSES)

    def test_live_queue_exclusion_is_the_terminal_set_itself(self):
        # IDENTITY, not equality. An equal copy satisfies ``==`` on the day it is
        # written and drifts the moment one of the two is edited; sharing one
        # object is what makes the two names unable to disagree at all.
        assert LIVE_QUEUE_EXCLUDED_STATUSES is TERMINAL_PLAN_STATUSES

    def test_no_live_status_is_excluded_from_the_live_queue(self):
        overlap = sorted(set(LIVE_PLAN_STATUSES) & set(LIVE_QUEUE_EXCLUDED_STATUSES))

        assert not overlap, (
            f'{overlap} is both a LIVE status and excluded from the live queue, so a row at '
            'that status would be unfinished and invisible at the same time'
        )


class TestCountClaimNounsCoverTheSettledVocabulary:
    """Every legal status is a checkable count claim, and every noun has a key.

    The module's own comment records the two failure directions this pins. A
    status legal in the vocabulary but absent from ``COUNT_CLAIM_NOUNS`` yields
    NO divergence check for it — a claim about it passes unexamined, which is
    the silent half. A noun the alternation matches but ``_derive_counts``
    builds no key for raises ``KeyError`` at ``derived[key]`` — the loud half.
    Both are checked over the whole noun population rather than over a sample,
    and the population is asserted non-empty first so an emptied constant
    collects no cases and fails instead of passing.
    """

    def test_the_noun_population_is_not_empty(self):
        assert COUNT_CLAIM_NOUNS, (
            'COUNT_CLAIM_NOUNS is empty (population 0), so the parametrized arms below would '
            'generate no cases at all and pass by collecting nothing'
        )

    def test_every_legal_status_is_a_count_claim_noun(self):
        unchecked = sorted(set(VALID_STATUS_VOCABULARY) - set(COUNT_CLAIM_NOUNS))

        assert not unchecked, (
            f'{unchecked} is a legal status with no count-claim noun, so a rendered block '
            'claiming a number of them is never compared against its derivation'
        )

    def test_the_whole_population_nouns_ride_alongside_the_per_status_ones(self):
        # ``rows``/``plans`` count the whole queue rather than a status tally, so
        # they are NOT derivable from the vocabulary and would be lost by a
        # derivation that replaced the tuple instead of extending it.
        assert {'rows', 'plans'} <= set(COUNT_CLAIM_NOUNS)

    @pytest.mark.parametrize('noun', COUNT_CLAIM_NOUNS)
    def test_every_noun_resolves_to_a_derivation_key(self, noun):
        derived = _derive_counts({'plans': []})

        assert _claim_key(noun) in derived, (
            f'{noun!r} is a count-claim noun whose derivation key {_claim_key(noun)!r} is '
            f'absent from {sorted(derived)}; _count_divergences would raise KeyError on it'
        )

    @pytest.mark.parametrize('noun', COUNT_CLAIM_NOUNS)
    def test_every_noun_is_matched_by_the_derived_alternation(self, noun):
        # The other direction: a noun in the tuple that the DERIVED alternation
        # does not match contributes no check either, and does so without
        # raising — the non-vacuity guard on the derivation itself.
        match = _COUNT_CLAIM_RE.search(f'the block claims 3 {noun} today')

        assert match is not None, f'the derived alternation matches no claim written with {noun!r}'
        assert _claim_key(match.group('noun')) == _claim_key(noun)


# =============================================================================
# queue — documented enumerations vs. their declaring sources
# =============================================================================


def _documented_entries(anchor: str) -> tuple[list[str], int]:
    """Extract the backticked entries SKILL.md publishes behind ``anchor``.

    The single reader behind both anchored-fragment checks below, so the two
    fragments are pinned by one mechanism rather than by two parallel ones.

    Returns the parsed entries IN DOCUMENT ORDER — the order matters to the seed
    fields, whose tuple order is load-bearing — AND the number of anchored lines
    the lookup matched, so a caller can tell an anchor that matched nothing apart
    from an anchored line that legitimately listed nothing. Collapsing those two
    into a bare empty result is what would let a reworded doc pass this file
    silently.
    """
    lines = [line for line in SKILL_MD_PATH.read_text(encoding='utf-8').splitlines() if line.startswith(anchor)]
    if len(lines) != 1:
        return [], len(lines)
    return _BACKTICKED_RE.findall(lines[0][len(anchor) :]), 1


def _assert_extraction_is_not_vacuous(
    anchor: str, documented: list[str], anchor_matches: int, declared: Collection[str]
) -> None:
    """Fail unless BOTH populations are non-empty and the anchor matched once.

    Two empty sets compare EQUAL, so every set-equality assertion below is only
    meaningful while both populations are non-zero. Asserting that precondition
    separately — and naming both populations — is what stops a reworded anchor
    and an emptied constant from agreeing on nothing.
    """
    assert anchor_matches == 1, (
        f'expected exactly ONE line in {SKILL_MD_PATH} starting with '
        f'{anchor!r}, matched {anchor_matches} — the extractor found no '
        'anchored enumeration to compare'
    )
    assert documented, (
        f'the line anchored by {anchor!r} in {SKILL_MD_PATH} yielded no '
        'backticked entries (population 0), so a set-equality check against it '
        'would compare an empty set'
    )
    assert declared, (
        f'the constant mirrored by {anchor!r} is empty (population 0), so a '
        'set-equality check against it would compare an empty set'
    )


def _assert_sets_agree(anchor: str, documented: list[str], declared: Collection[str]) -> None:
    """Fail unless the documented entries and the declared constant agree, both ways."""
    documented_set = set(documented)
    declared_set = set(declared)

    assert documented_set == declared_set, (
        f'the enumeration anchored by {anchor!r} {sorted(documented_set)} '
        f'(population {len(documented_set)}) disagrees with its declaring '
        f'constant {sorted(declared_set)} (population {len(declared_set)}): '
        f'documented-only={sorted(documented_set - declared_set)}, '
        f'declared-only={sorted(declared_set - documented_set)}'
    )


class TestDocumentedFieldWhitelistMatchesDeclaration:
    """SKILL.md's ``--field`` whitelist equals ``PLAN_ROW_FIELDS``, both ways.

    The doc states CLOSURE over an enumeration declared in ``orchestrator.py``
    and validated there by ``cmd_queue``. Re-checking the claim against its
    declaring source on every run is what the standing "never assert closure
    over an enumeration without re-checking it" rule prescribes, in preference
    to a hand-maintained second copy.

    ``PLAN_ROW_FIELDS`` is a ``frozenset``, so it declares MEMBERSHIP and no
    order; the doc line's order is therefore presentational and is not pinned.
    """

    def test_the_whitelist_and_its_declaration_are_both_non_empty(self):
        documented, anchor_matches = _documented_entries(FIELD_WHITELIST_ANCHOR)

        _assert_extraction_is_not_vacuous(FIELD_WHITELIST_ANCHOR, documented, anchor_matches, PLAN_ROW_FIELDS)

    def test_documented_whitelist_equals_plan_row_fields(self):
        documented, _ = _documented_entries(FIELD_WHITELIST_ANCHOR)

        _assert_sets_agree(FIELD_WHITELIST_ANCHOR, documented, PLAN_ROW_FIELDS)


class TestDocumentedStatusVocabularyMatchesDeclaration:
    """SKILL.md's ``--status`` vocabulary equals ``VALID_STATUS_VOCABULARY``, both ways.

    The third mirrored enumeration in the same document, pinned by the same
    mechanism as the ``--field`` whitelist above rather than by a second parallel
    one. ``VALID_STATUS_VOCABULARY`` is a ``frozenset`` validated by ``cmd_queue``
    with the ``invalid_field`` error, so it declares MEMBERSHIP and no order;
    the doc line's order is therefore presentational and is not pinned.
    """

    def test_the_vocabulary_and_its_declaration_are_both_non_empty(self):
        documented, anchor_matches = _documented_entries(STATUS_VOCABULARY_ANCHOR)

        _assert_extraction_is_not_vacuous(STATUS_VOCABULARY_ANCHOR, documented, anchor_matches, VALID_STATUS_VOCABULARY)

    def test_documented_vocabulary_equals_valid_status_vocabulary(self):
        documented, _ = _documented_entries(STATUS_VOCABULARY_ANCHOR)

        _assert_sets_agree(STATUS_VOCABULARY_ANCHOR, documented, VALID_STATUS_VOCABULARY)


class TestDocumentedSeedFieldsMatchDeclaration:
    """SKILL.md's ``--add-row`` seed fields equal ``ADD_ROW_SEED_FIELDS``.

    The second mirrored enumeration in the same document, pinned by the same
    mechanism as the ``--field`` whitelist above rather than by a second parallel
    one.

    ORDER IS PINNED HERE, and that is the deliberate difference from the
    whitelist class. ``ADD_ROW_SEED_FIELDS`` is an ORDERED tuple whose order is
    load-bearing — it is the key order an appended row is written in — so the
    documented line is asserted as a SEQUENCE as well as a set. The set check is
    kept alongside it because it is the one that names WHICH members diverged in
    each direction; the sequence check adds the claim the set check cannot make.
    """

    def test_the_seed_fields_and_their_declaration_are_both_non_empty(self):
        documented, anchor_matches = _documented_entries(ADD_ROW_SEED_FIELDS_ANCHOR)

        _assert_extraction_is_not_vacuous(ADD_ROW_SEED_FIELDS_ANCHOR, documented, anchor_matches, ADD_ROW_SEED_FIELDS)

    def test_documented_seed_fields_equal_add_row_seed_fields(self):
        documented, _ = _documented_entries(ADD_ROW_SEED_FIELDS_ANCHOR)

        _assert_sets_agree(ADD_ROW_SEED_FIELDS_ANCHOR, documented, ADD_ROW_SEED_FIELDS)

    def test_documented_seed_fields_are_in_declaration_order(self):
        documented, _ = _documented_entries(ADD_ROW_SEED_FIELDS_ANCHOR)

        assert documented == list(ADD_ROW_SEED_FIELDS), (
            f'the documented seed-field order {documented} disagrees with '
            f'ADD_ROW_SEED_FIELDS {list(ADD_ROW_SEED_FIELDS)}; that tuple order '
            'is the key order an appended row is written in, so the doc line '
            'states a sequence and not merely a membership'
        )


# =============================================================================
# queue — add-row
# =============================================================================


def _add_row_args(slug: str, plan_id: str = 'PLAN-07', **overrides: Any) -> argparse.Namespace:
    """A complete ``--add-row`` namespace, with the required triple supplied.

    ``overrides`` names only what a case differs in, so a test asserting the
    INCOMPLETE-triple rejection passes ``slug_value=None`` explicitly rather than
    relying on a default that would make the omission invisible.
    """
    return _queue_args(
        slug,
        add_row=overrides.pop('add_row', plan_id),
        slug_value=overrides.pop('slug_value', plan_id.lower()),
        workstream=overrides.pop('workstream', 'WS-01'),
        **overrides,
    )


def _write_spec(plan_context, slug: str, name: str) -> Path:
    """Stage one spec file under the epic's ``plans/`` directory."""
    plans = _epic_dir(plan_context, slug) / 'plans'
    plans.mkdir(parents=True, exist_ok=True)
    path = plans / name
    path.write_text('# spec', encoding='utf-8')
    return path


class TestQueueAddRow:
    def test_should_append_onto_an_empty_queue(self, plan_context):
        root = _write_status(plan_context, 'add-empty-epic', plans=[])

        result = cmd_queue(_add_row_args('add-empty-epic'))

        assert result['status'] == 'success'
        assert result['operation'] == 'queue-add-row'
        assert result['plan'] == 'PLAN-07'
        assert _rows_without_seq(root) == [_make_plan('PLAN-07')]
        assert (root / 'queue' / 'PLAN-07.json').is_file()

    def test_should_append_onto_a_populated_queue_leaving_siblings_untouched(self, plan_context):
        existing = [_make_plan('PLAN-01', status='running'), _make_plan('PLAN-02')]
        root = _write_status(plan_context, 'add-populated-epic', plans=copy.deepcopy(existing))
        before = _snapshot(root)

        cmd_queue(_add_row_args('add-populated-epic'))

        on_disk = _rows_without_seq(root)
        assert on_disk[:2] == existing
        assert on_disk[2] == _make_plan('PLAN-07')
        # Staging created ONE new file and rewrote none.
        after = _snapshot(root)
        assert sorted(set(after) - set(before)) == [str(Path('queue') / 'PLAN-07.json')]
        assert all(after[name] == before[name] for name in before)

    def test_should_seed_the_row_with_empty_result_fields(self, plan_context):
        _write_status(plan_context, 'add-shape-epic', plans=[])

        result = cmd_queue(_add_row_args('add-shape-epic'))

        # The seeded row is exactly the fixture shape: three identity fields, a
        # status, the three PLAN_ROW_FIELDS empty — a staged row has landed
        # nothing yet — and the allocated ``seq``.
        assert result['row'] == {**_make_plan('PLAN-07'), 'seq': 1}
        assert list(result['row']) == list(ADD_ROW_SEED_FIELDS)
        assert all(result['row'][field] == '' for field in PLAN_ROW_FIELDS)

    def test_should_allocate_seq_as_the_local_maximum_plus_one(self, plan_context):
        root = _write_status(plan_context, 'add-seq-epic', plans=[_make_plan('PLAN-01'), _make_plan('PLAN-02')])

        result = cmd_queue(_add_row_args('add-seq-epic'))

        assert result['row']['seq'] == 3
        assert [(row['id'], row['seq']) for row in _rows(root)] == [('PLAN-01', 1), ('PLAN-02', 2), ('PLAN-07', 3)]

    def test_should_default_the_seed_status_to_staged(self, plan_context):
        _write_status(plan_context, 'add-default-status-epic', plans=[])

        result = cmd_queue(_add_row_args('add-default-status-epic', status=None))

        assert result['row']['status'] == 'staged'

    def test_should_honour_a_supplied_seed_status(self, plan_context):
        root = _write_status(plan_context, 'add-status-epic', plans=[])

        result = cmd_queue(_add_row_args('add-status-epic', status='running'))

        assert result['row']['status'] == 'running'
        assert _rows(root)[0]['status'] == 'running'

    def test_should_reject_a_duplicate_plan_id_leaving_the_queue_unchanged(self, plan_context):
        existing = [_make_plan('PLAN-07', status='shipped', pr='#900')]
        root = _write_status(plan_context, 'add-dup-epic', plans=copy.deepcopy(existing))
        before = _snapshot(root)

        result = cmd_queue(_add_row_args('add-dup-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'duplicate_plan_id'
        assert result['existing_status'] == 'shipped'
        # Refused by the atomic create: every file is byte-identical.
        assert _snapshot(root) == before

    def test_should_reject_a_duplicate_slug_leaving_the_queue_unchanged(self, plan_context):
        queued = _make_plan('PLAN-01')
        queued['slug'] = 'shared-slug'
        root = _write_status(plan_context, 'add-dup-slug-epic', plans=[queued])
        before = _snapshot(root)

        result = cmd_queue(_add_row_args('add-dup-slug-epic', add_row='PLAN-07', slug_value='shared-slug'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_field'
        assert result['existing_plan'] == 'PLAN-01'
        assert _snapshot(root) == before

    def test_should_reject_a_slug_equal_to_the_epic_slug_without_writing(self, plan_context):
        root = _write_status(plan_context, 'add-epic-slug-epic', plans=[])

        result = cmd_queue(_add_row_args('add-epic-slug-epic', add_row='PLAN-07', slug_value='add-epic-slug-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_field'
        assert _rows(root) == []

    def test_should_leave_non_canonical_header_bytes_untouched_on_every_append(self, plan_context):
        # Staging writes a row file and never the header, so a non-canonical
        # header survives a refusal AND an admission byte-for-byte.
        root = _write_status(plan_context, 'add-epic-slug-raw-epic', plans=[])
        header_path = root / 'status.json'
        raw = header_path.read_text(encoding='utf-8')
        non_canonical = json.dumps(json.loads(raw), separators=(',', ':'))
        assert non_canonical != raw
        header_path.write_text(non_canonical, encoding='utf-8')

        refused = cmd_queue(
            _add_row_args('add-epic-slug-raw-epic', add_row='PLAN-07', slug_value='add-epic-slug-raw-epic')
        )
        admitted = cmd_queue(_add_row_args('add-epic-slug-raw-epic', add_row='PLAN-08', slug_value='beta-slug'))

        assert refused['error'] == 'invalid_field'
        assert admitted['status'] == 'success'
        assert header_path.read_text(encoding='utf-8') == non_canonical
        assert [row['slug'] for row in _rows(root)] == ['beta-slug']

    def test_should_admit_distinct_slugs_cleanly(self, plan_context):
        queued = _make_plan('PLAN-01')
        queued['slug'] = 'alpha-slug'
        root = _write_status(plan_context, 'add-distinct-slug-epic', plans=[queued])

        result = cmd_queue(_add_row_args('add-distinct-slug-epic', add_row='PLAN-07', slug_value='beta-slug'))

        assert result['status'] == 'success'
        assert result['operation'] == 'queue-add-row'
        assert [row['slug'] for row in _rows(root)] == ['alpha-slug', 'beta-slug']

    def test_should_never_stamp_a_shared_updated_field(self, plan_context):
        root = _write_status(plan_context, 'add-stamp-epic', plans=[_make_plan('PLAN-07')])

        rejected = cmd_queue(_add_row_args('add-stamp-epic'))
        accepted = cmd_queue(_add_row_args('add-stamp-epic', plan_id='PLAN-08'))

        assert rejected['status'] == 'error'
        assert accepted['status'] == 'success'
        assert 'updated' not in _header(root)
        assert all('updated' not in row for row in _rows(root))


class TestQueueAddRowRejections:
    def test_should_reject_a_lowercase_plan_id_without_writing(self, plan_context):
        root = _write_status(plan_context, 'add-lower-epic', plans=[])

        result = cmd_queue(_add_row_args('add-lower-epic', add_row='plan-07'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_plan_id'
        assert _rows(root) == []

    def test_should_reject_a_path_shaped_plan_id_without_writing(self, plan_context):
        root = _write_status(plan_context, 'add-path-epic', plans=[])

        result = cmd_queue(_add_row_args('add-path-epic', add_row='PLAN-07/evil'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_plan_id'
        assert _rows(root) == []
        assert not (root / 'queue').exists()

    def test_should_reject_a_traversing_plan_id_without_writing(self, plan_context):
        root = _write_status(plan_context, 'add-traverse-epic', plans=[])

        result = cmd_queue(_add_row_args('add-traverse-epic', add_row='../PLAN-07'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_plan_id'
        assert _rows(root) == []

    def test_should_reject_a_trailing_newline_plan_id_without_writing(self, plan_context):
        """A trailing newline must not slip past the tail anchor.

        Python's ``$`` matches immediately before a trailing newline, so an
        ``^…$`` anchoring accepts ``PLAN-07\\n``. That newline would ride into
        ``row['id']``, and because the duplicate check compares ids by exact
        string it would never collide with a clean ``PLAN-07`` already queued —
        appending the same logical plan twice and evading the
        ``duplicate_plan_id`` guard. The tail anchor is ``\\Z`` for this reason.
        """
        root = _write_status(plan_context, 'add-newline-epic', plans=[])

        result = cmd_queue(_add_row_args('add-newline-epic', add_row='PLAN-07\n'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_plan_id'
        assert _rows(root) == []

    def test_should_reject_a_newline_duplicate_of_an_already_queued_row(self, plan_context):
        """The newline variant must not append alongside its clean twin.

        This is the consequence the anchor fix exists to prevent, asserted at
        the level that matters: with a clean ``PLAN-07`` already queued, the
        newline-bearing spelling must be refused rather than appended as a
        second row for the same logical plan.
        """
        root = _write_status(
            plan_context,
            'add-newline-dup-epic',
            plans=[{'id': 'PLAN-07', 'slug': 'clean', 'workstream': 'WS-01', 'status': 'staged'}],
        )

        result = cmd_queue(_add_row_args('add-newline-dup-epic', add_row='PLAN-07\n'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_plan_id'
        assert len(_rows(root)) == 1

    def test_should_require_slug_value_with_add_row(self, plan_context):
        _write_status(plan_context, 'add-nosl-epic', plans=[])

        result = cmd_queue(_add_row_args('add-nosl-epic', slug_value=None))

        assert result['status'] == 'error'
        assert result['error'] == 'wrong_parameters'

    def test_should_require_workstream_with_add_row(self, plan_context):
        _write_status(plan_context, 'add-nows-epic', plans=[])

        result = cmd_queue(_add_row_args('add-nows-epic', workstream=None))

        assert result['status'] == 'error'
        assert result['error'] == 'wrong_parameters'

    def test_should_require_add_row_with_its_companions(self, plan_context):
        _write_status(plan_context, 'add-companion-epic', plans=[])

        result = cmd_queue(_queue_args('add-companion-epic', slug_value='plan-07', workstream='WS-01'))

        assert result['status'] == 'error'
        assert result['error'] == 'wrong_parameters'

    def test_should_reject_add_row_combined_with_transition(self, plan_context):
        _write_status(plan_context, 'add-excl-tr-epic', plans=[_make_plan('PLAN-01')])

        result = cmd_queue(_add_row_args('add-excl-tr-epic', transition='PLAN-01', status='running'))

        assert result['status'] == 'error'
        assert result['error'] == 'wrong_parameters'

    def test_should_reject_add_row_combined_with_set_row(self, plan_context):
        _write_status(plan_context, 'add-excl-sr-epic', plans=[_make_plan('PLAN-01')])

        result = cmd_queue(_add_row_args('add-excl-sr-epic', set_row='PLAN-01', field='pr', value='#1'))

        assert result['status'] == 'error'
        assert result['error'] == 'wrong_parameters'

    def test_should_reject_all_three_write_forms_together(self, plan_context):
        _write_status(plan_context, 'add-excl-all-epic', plans=[_make_plan('PLAN-01')])

        result = cmd_queue(
            _add_row_args(
                'add-excl-all-epic',
                transition='PLAN-01',
                status='running',
                set_row='PLAN-01',
                field='pr',
                value='#1',
            )
        )

        assert result['status'] == 'error'
        assert result['error'] == 'wrong_parameters'

    def test_should_reject_status_with_neither_transition_nor_add_row(self, plan_context):
        # ``--status`` is shared between two forms, so it no longer marks the
        # transition form on its own. It must still be rejected when it dangles:
        # the restructured three-way guard has to keep the case the old
        # two-way pairing predicate expressed.
        root = _write_status(plan_context, 'add-dangle-epic', plans=[_make_plan('PLAN-01')])

        result = cmd_queue(_queue_args('add-dangle-epic', status='running'))

        assert result['status'] == 'error'
        assert result['error'] == 'wrong_parameters'
        assert _rows(root)[0]['status'] == 'staged'


def _write_raw_status(plan_context, slug: str, body: str) -> Path:
    """Write ``body`` VERBATIM as the epic's status.json.

    The malformed-document arms need bytes the JSON encoder would never emit —
    an unterminated object, a top-level array, a bare scalar — so they bypass
    :func:`_write_status` and its dict-shaped fixture entirely.
    """
    path = _epic_dir(plan_context, slug) / 'status.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding='utf-8')
    return path


class TestQueueAddRowStatusDocumentGuard:
    """The opening guard discriminates the header ``status.json``, not one-way.

    A truthiness test on the PARSED document reports four different on-disk
    states as ``file_not_found``; a bare file-presence test collapses the same
    states the other way. The three arms below are asserted TOGETHER because
    each is satisfiable alone by a guard that is wrong in the other direction:
    refusing everything satisfies (a) and (c) while breaking every first append
    at (b), and presence-only satisfies (a) and (b) while letting (c) through to
    a row write under a header nothing can read. The fourth arm — a header still
    in the monolithic layout — is :class:`TestQueueLegacyLayoutRefusal`.
    """

    def test_should_report_file_not_found_when_status_json_is_absent(self, plan_context):
        cmd_scaffold(_variant(_SCAFFOLD_ARGS, slug='doc-absent-epic'))
        root = _epic_dir(plan_context, 'doc-absent-epic')

        result = cmd_queue(_add_row_args('doc-absent-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'
        # Nothing was conjured: no header and no row file beside no header.
        assert not (root / 'status.json').exists()
        assert not (root / 'queue').exists()

    def test_should_seed_the_queue_when_the_document_is_an_empty_object(self, plan_context):
        """An empty ``{}`` header is a valid object, so the first append lands.

        This is the arm a parsed-document truthiness guard fails: ``{}`` is
        falsy, so a present, well-formed, merely bare ledger was reported as a
        file that does not exist and the legitimate first-append seed path was
        blocked.
        """
        _write_raw_status(plan_context, 'doc-empty-epic', '{}')

        result = cmd_queue(_add_row_args('doc-empty-epic'))

        assert result['status'] == 'success'
        assert _rows_without_seq(_epic_dir(plan_context, 'doc-empty-epic')) == [_make_plan('PLAN-07')]

    @pytest.mark.parametrize(
        ('slug', 'body', 'observed_type'),
        [
            ('doc-unparseable-epic', '{"kind": "orchestrator",', 'unparseable'),
            ('doc-array-epic', '["PLAN-01"]', 'list'),
            ('doc-string-epic', '"PLAN-01"', 'str'),
            ('doc-null-epic', 'null', 'NoneType'),
        ],
        ids=['unparseable', 'array', 'string', 'null'],
    )
    def test_should_refuse_a_present_non_object_document_without_writing(self, plan_context, slug, body, observed_type):
        """A present-but-unusable header is refused, never reported absent."""
        status_path = _write_raw_status(plan_context, slug, body)

        result = cmd_queue(_add_row_args(slug))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_status_document'
        assert result['observed_type'] == observed_type
        # Byte-identical on disk, and no row file beside the unusable header.
        assert status_path.read_text(encoding='utf-8') == body
        assert not (status_path.parent / 'queue').exists()


#: A monolithic-layout document — the retired shape every queue verb refuses.
_LEGACY_DOC = _fixture_doc([_make_plan('PLAN-01', status='running')])


def _legacy_epic(plan_context, slug: str) -> Path:
    """Write the retired monolithic ``status.json`` for ``slug``; return the epic root."""
    root = _epic_dir(plan_context, slug)
    write_legacy_status(root, _LEGACY_DOC)
    return root


class TestQueueLegacyLayoutRefusal:
    """Every queue form refuses a monolithic-layout ledger with ``legacy_layout``.

    There is no read-fallback: a legacy ``status.json`` is never read as an
    empty ledger and never written into, and the refusal names
    ``migrate-layout`` as the one remedy. Each arm asserts the tree is
    byte-identical afterwards and that no ``queue/`` directory was created.
    The per-concern control shows the same forms succeed on a migrated ledger,
    so the refusal is about the layout rather than about the verbs.
    """

    @pytest.mark.parametrize(
        'form',
        [
            {},
            {'transition': 'PLAN-01', 'status': 'parked'},
            {'set_row': 'PLAN-01', 'field': 'pr', 'value': '#1'},
            {'add_row': 'PLAN-07', 'slug_value': 'plan-07', 'workstream': 'WS-01'},
        ],
        ids=['read', 'transition', 'set-row', 'add-row'],
    )
    def test_every_form_refuses_a_legacy_ledger_without_writing(self, plan_context, form):
        root = _legacy_epic(plan_context, 'legacy-queue-epic')
        before = _snapshot(root)

        result = cmd_queue(_queue_args('legacy-queue-epic', **form))

        assert result['status'] == 'error'
        assert result['error'] == 'legacy_layout'
        assert 'migrate-layout' in result['remedy']
        assert _snapshot(root) == before
        assert not (root / 'queue').exists()

    def test_resume_summary_refuses_a_legacy_ledger(self, plan_context):
        _legacy_epic(plan_context, 'legacy-summary-epic')

        result = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='legacy-summary-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'legacy_layout'

    def test_regenerate_view_refuses_a_legacy_ledger_without_writing(self, plan_context):
        root = _legacy_epic(plan_context, 'legacy-view-epic')
        before = _snapshot(root)

        result = cmd_regenerate_view(_variant(_REGENERATE_VIEW_ARGS, slug='legacy-view-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'legacy_layout'
        assert _snapshot(root) == before
        assert not (root / 'queue-view.md').exists()

    def test_the_same_forms_succeed_once_the_ledger_is_migrated(self, plan_context):
        root = _legacy_epic(plan_context, 'legacy-control-epic')

        migrated = cmd_migrate_layout(_variant(_MIGRATE_ARGS, slug='legacy-control-epic'))
        transition = cmd_queue(_queue_args('legacy-control-epic', transition='PLAN-01', status='parked'))

        assert migrated['status'] == 'success'
        assert transition['status'] == 'success'
        assert _rows(root)[0]['status'] == 'parked'


class TestQueueAddRowSpecPresence:
    def test_should_report_present_when_the_spec_is_staged(self, plan_context):
        _write_status(plan_context, 'spec-present-epic', plans=[])
        _write_spec(plan_context, 'spec-present-epic', 'PLAN-07-add-row.md')

        result = cmd_queue(_add_row_args('spec-present-epic'))

        assert result['spec_presence'] == 'present'
        assert result['spec'] == 'PLAN-07-add-row.md'
        assert result['spec_absent_warning'] == ''
        assert result['spec_probe_error'] == ''

    def test_should_report_absent_when_the_plans_dir_holds_no_matching_spec(self, plan_context):
        _write_status(plan_context, 'spec-absent-epic', plans=[])
        _write_spec(plan_context, 'spec-absent-epic', 'PLAN-99-other.md')

        result = cmd_queue(_add_row_args('spec-absent-epic'))

        assert result['spec_presence'] == 'absent'
        assert result['spec'] == ''
        # A MEASURED negative: the warning names the directory that was listed.
        assert 'spec-absent-epic' in result['spec_absent_warning']
        assert result['spec_probe_error'] == ''

    def test_should_report_absent_when_the_plans_dir_does_not_exist(self, plan_context):
        _write_status(plan_context, 'spec-nodir-epic', plans=[])

        result = cmd_queue(_add_row_args('spec-nodir-epic'))

        assert result['spec_presence'] == 'absent'
        assert 'does not exist' in result['spec_absent_warning']

    def test_should_report_unlistable_and_never_fold_it_into_absent(self, plan_context):
        # A ``plans`` path that is a FILE makes ``iterdir`` raise
        # NotADirectoryError — a deterministic, privilege-independent way to
        # reach the branch a chmod-based probe cannot reach when tests run as
        # root. Nothing was observed, so the verdict must NOT read as ``absent``.
        _write_status(plan_context, 'spec-unlistable-epic', plans=[])
        (_epic_dir(plan_context, 'spec-unlistable-epic') / 'plans').write_text('not a directory', encoding='utf-8')

        result = cmd_queue(_add_row_args('spec-unlistable-epic'))

        assert result['spec_presence'] == 'unlistable'
        assert result['spec_probe_error'] != ''
        assert result['spec_absent_warning'] == ''

    def test_should_still_append_the_row_when_the_spec_is_absent(self, plan_context):
        # The probe REPORTS; it never gates the append. A plan is routinely
        # queued before its spec is written.
        root = _write_status(plan_context, 'spec-nogate-epic', plans=[])

        result = cmd_queue(_add_row_args('spec-nogate-epic'))

        assert result['status'] == 'success'
        assert result['spec_presence'] == 'absent'
        assert _rows_without_seq(root) == [_make_plan('PLAN-07')]


# =============================================================================
# resume-summary
# =============================================================================


class TestResumeSummary:
    def test_should_render_anchor_phase_and_groups_from_status_json(self, plan_context):
        plans = [
            _make_plan('PLAN-01', status='landed', pr='#901', landing='PLAN-01.md'),
            _make_plan('PLAN-02', status='running', plan_marshall_plan_id='epic-plan-2'),
            _make_plan('PLAN-03', status='parked'),
            _make_plan('PLAN-04', workstream='WS-02'),
            _make_plan('PLAN-05'),
        ]
        _write_status(plan_context, 'summary-epic', plans=plans)

        result = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='summary-epic'))

        assert result['status'] == 'success'
        assert result['operation'] == 'resume-summary'
        summary = result['summary']
        assert '**Resume anchor**: await PR #912 CI, then analyze landing' in summary
        assert '**Phase**: orchestrating' in summary
        assert '**Running**:' in summary
        assert 'PLAN-02 (WS-01) — plan=epic-plan-2' in summary
        assert '**Parked**:' in summary
        assert 'PLAN-03 (WS-01)' in summary
        assert '1. PLAN-04 (WS-02)' in summary
        assert '2. PLAN-05 (WS-01)' in summary
        assert 'PLAN-01 (WS-01)' in summary
        assert 'status: landed' in summary
        assert 'PR #901' in summary

    def test_should_also_emit_the_ordered_queue_block_live_rows_only(self, plan_context):
        # resume-summary is the lightweight render path for BOTH derivable blocks.
        # The Ordered Queue block carries only the LIVE queue: a landed/shipped row
        # belongs in its landing record, not here.
        plans = [
            _make_plan('PLAN-01', status='landed', pr='#901', landing='PLAN-01.md'),
            _make_plan('PLAN-02', status='running'),
            _make_plan('PLAN-03', status='staged', workstream='WS-02'),
        ]
        _write_status(plan_context, 'oq-epic', plans=plans)

        result = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='oq-epic'))

        queue = result['ordered_queue']
        assert '| # | Plan | Workstream | Status | Surface (expected) |' in queue
        assert '| 1 | PLAN-02 | WS-01 | running |' in queue
        assert '| 2 | PLAN-03 | WS-02 | staged |' in queue
        # The terminal row is excluded from the live queue.
        assert 'PLAN-01' not in queue

    def test_should_mark_terminal_row_missing_both_links(self, plan_context):
        _write_status(plan_context, 'gap-both-epic', plans=[_make_plan('PLAN-01', status='shipped')])

        result = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='gap-both-epic'))

        assert '(!) missing: pr, landing' in result['summary']

    def test_should_mark_terminal_row_missing_only_pr(self, plan_context):
        _write_status(
            plan_context,
            'gap-pr-epic',
            plans=[_make_plan('PLAN-01', status='shipped', landing='PLAN-01.md')],
        )

        result = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='gap-pr-epic'))

        assert '(!) missing: pr' in result['summary']
        assert '(!) missing: pr, landing' not in result['summary']

    def test_should_mark_landed_row_the_same_as_shipped(self, plan_context):
        _write_status(
            plan_context,
            'gap-landed-epic',
            plans=[_make_plan('PLAN-01', status='landed', pr='#901')],
        )

        result = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='gap-landed-epic'))

        assert '(!) missing: landing' in result['summary']

    def test_should_not_mark_fully_stamped_terminal_row(self, plan_context):
        _write_status(
            plan_context,
            'gap-none-epic',
            plans=[_make_plan('PLAN-01', status='shipped', pr='#901', landing='PLAN-01.md')],
        )

        result = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='gap-none-epic'))

        assert '(!) missing' not in result['summary']

    def test_should_not_mark_non_terminal_row_with_empty_links(self, plan_context):
        _write_status(
            plan_context,
            'gap-inflight-epic',
            plans=[_make_plan('PLAN-01', status='staged'), _make_plan('PLAN-02', status='running')],
        )

        result = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='gap-inflight-epic'))

        assert '(!) missing' not in result['summary']

    def test_should_render_empty_queue_marker(self, plan_context):
        _write_status(plan_context, 'empty-epic', plans=[])

        result = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='empty-epic'))

        assert '**Queue** (staged, in order):' in result['summary']
        assert '- (empty)' in result['summary']

    def test_should_render_placeholder_for_unset_anchor(self, plan_context):
        _write_status(plan_context, 'anchorless-epic', resume_anchor='')

        result = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='anchorless-epic'))

        assert '**Resume anchor**: (not set)' in result['summary']

    def test_should_error_when_status_json_missing(self, plan_context):
        result = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='absent-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'

    def test_should_reject_invalid_slug(self, plan_context):
        result = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='../evil'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'


# =============================================================================
# resume-summary — the gap marker is a SHIPPED signal, not a terminal one
# =============================================================================


#: The completeness marker a shipped row missing BOTH result links renders.
_GAP_MARKER = '(!) missing: pr, landing'


def _summary_line_for(summary: str, plan_id: str) -> str:
    """The one rendered START-HERE line naming ``plan_id``.

    Asserting per LINE rather than over the whole block is what makes the pair
    below a matched control: both rows render into one summary, so a
    whole-block substring test could be satisfied by the marker belonging to
    either of them and would prove nothing about which row carried it.
    """
    lines = [line for line in summary.split('\n') if plan_id in line]

    assert len(lines) == 1, f'expected exactly ONE rendered line naming {plan_id}, found {len(lines)}: {lines}'
    return lines[0]


class TestResumeSummaryGapMarkerIsAShippedSignal:
    """The completeness marker fires on SHIPPED, never on terminal-at-large.

    A row that closed WITHOUT shipping is finished, so it is excluded from the
    live queue exactly as a shipped row is — but it never had a PR or a landing
    record to point at, so marking it incomplete would report a gap that cannot
    exist. The two questions are answered by two different sets, and each test
    below is a matched pair over ONE rendering differing in exactly one
    variable: the second row's status.
    """

    def test_the_two_terminal_populations_are_non_empty_and_disjoint(self):
        assert SHIPPED_PLAN_STATUSES, 'SHIPPED_PLAN_STATUSES is empty (population 0)'
        assert CLOSED_UNSHIPPED_PLAN_STATUSES, (
            'CLOSED_UNSHIPPED_PLAN_STATUSES is empty (population 0), so the '
            'parametrized arms below would generate no cases at all'
        )
        overlap = set(SHIPPED_PLAN_STATUSES) & set(CLOSED_UNSHIPPED_PLAN_STATUSES)
        assert not overlap, (
            f'the shipped and closed-unshipped terminal sets share {sorted(overlap)}; '
            'a status in both would make every pair below compare a row with itself'
        )

    @pytest.mark.parametrize('closed_status', CLOSED_UNSHIPPED_PLAN_STATUSES)
    def test_should_mark_the_shipped_row_and_not_its_closed_unshipped_twin(self, plan_context, closed_status):
        slug = f'gap-unshipped-{closed_status}-epic'
        _write_status(
            plan_context,
            slug,
            plans=[_make_plan('PLAN-01', status='shipped'), _make_plan('PLAN-02', status=closed_status)],
        )

        summary = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug=slug))['summary']

        assert _GAP_MARKER in _summary_line_for(summary, 'PLAN-01')
        assert _GAP_MARKER not in _summary_line_for(summary, 'PLAN-02')

    @pytest.mark.parametrize('closed_status', CLOSED_UNSHIPPED_PLAN_STATUSES)
    def test_should_leave_a_closed_unshipped_row_out_of_the_live_queue(self, plan_context, closed_status):
        # The staged row is the positive control: without it a table that
        # rendered nothing at all would satisfy the exclusion assertion.
        slug = f'oq-unshipped-{closed_status}-epic'
        _write_status(
            plan_context,
            slug,
            plans=[_make_plan('PLAN-01', status=closed_status), _make_plan('PLAN-02', status='staged')],
        )

        queue = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug=slug))['ordered_queue']

        assert 'PLAN-02' in queue
        assert 'PLAN-01' not in queue


# =============================================================================
# resume-summary — inbox counts derived at render time, beside the narrative
# =============================================================================


class TestResumeSummaryDerivedInbox:
    """The counts come from the filesystem, never from the anchor's prose.

    The defect this pins: the START-HERE block carried only the operator's
    ``resume_anchor`` sentence, so a narrative "inbox drained 8/8" outranked a
    queue that still held messages. The derived line now sits beside the anchor
    and is authoritative over it.
    """

    def test_should_render_the_derived_inbox_line_from_the_filesystem(self, plan_context):
        _write_status(plan_context, 'inbox-count-epic')
        _seed_inbox(plan_context, 'inbox-count-epic', queued=2, archived=3)

        result = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='inbox-count-epic'))

        assert '**Inbox (derived)**: 2 queued, 3 archived' in result['summary']

    def test_should_surface_the_counts_as_top_level_payload_fields(self, plan_context):
        # A caller reconciles against ``inbox list`` without parsing markdown.
        _write_status(plan_context, 'inbox-fields-epic')
        _seed_inbox(plan_context, 'inbox-fields-epic', queued=1, archived=4)

        result = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='inbox-fields-epic'))

        assert result['inbox_queued'] == 1
        assert result['inbox_archived'] == 4
        assert result['inbox_state'] == 'present'

    def test_should_render_an_empty_queue_as_a_present_zero(self, plan_context):
        # Looked, found nothing — distinct from the absent-directory case below.
        _write_status(plan_context, 'inbox-empty-epic')
        _seed_inbox(plan_context, 'inbox-empty-epic')

        result = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='inbox-empty-epic'))

        assert '**Inbox (derived)**: 0 queued, 0 archived' in result['summary']
        assert result['inbox_state'] == 'present'

    def test_should_render_an_absent_inbox_explicitly_not_as_zero_queued(self, plan_context):
        # Could not look. Rendering "0 queued" here would be the same collapse
        # ``inbox list`` refuses to make.
        _write_status(plan_context, 'inbox-absent-epic')
        assert not (_epic_dir(plan_context, 'inbox-absent-epic') / 'inbox').exists()

        result = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='inbox-absent-epic'))

        assert '**Inbox (derived)**: no inbox directory' in result['summary']
        assert '0 queued' not in result['summary']
        assert result['inbox_state'] == 'missing'
        assert result['inbox_queued'] == 0

    def test_should_not_answer_the_two_zeros_with_equal_summaries(self, plan_context):
        # The two zeros agree on every count yet MUST NOT render identically.
        _write_status(plan_context, 'zero-looked-epic')
        _seed_inbox(plan_context, 'zero-looked-epic')
        _write_status(plan_context, 'zero-blind-epic')

        looked = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='zero-looked-epic'))
        could_not_look = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='zero-blind-epic'))

        assert looked['inbox_queued'] == could_not_look['inbox_queued'] == 0
        assert looked['inbox_archived'] == could_not_look['inbox_archived'] == 0
        assert looked['summary'] != could_not_look['summary']
        assert looked['inbox_state'] != could_not_look['inbox_state']

    def test_should_keep_a_stale_anchor_verbatim_beside_the_derived_truth(self, plan_context):
        # The whole point of the deliverable: the operator's prose is NEVER
        # silently rewritten, and the live count sits visibly next to it so the
        # contradiction is readable instead of hidden.
        _write_status(
            plan_context,
            'stale-anchor-epic',
            resume_anchor='inbox drained 8/8 — nothing queued',
        )
        _seed_inbox(plan_context, 'stale-anchor-epic', queued=3)

        result = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='stale-anchor-epic'))

        summary = result['summary']
        assert '**Resume anchor**: inbox drained 8/8 — nothing queued' in summary
        assert '**Inbox (derived)**: 3 queued, 0 archived' in summary
        assert result['inbox_queued'] == 3

    def test_should_render_the_derived_line_separately_from_the_anchor_line(self, plan_context):
        # Separate LINES, so neither can be mistaken for the other's authority.
        _write_status(plan_context, 'separate-lines-epic')
        _seed_inbox(plan_context, 'separate-lines-epic', queued=1)

        lines = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='separate-lines-epic'))['summary']

        anchor_line = next(line for line in lines.split('\n') if line.startswith('**Resume anchor**'))
        assert 'Inbox (derived)' not in anchor_line

    def test_should_agree_with_inbox_list_for_the_same_epic(self, plan_context):
        # Cross-verb reconciliation: the two surfaces are derived from the SAME
        # directory through the same filename grammar, so a caller comparing
        # them can never be told two different stories about one queue. Anchored
        # against a stale narrative so the disagreement is with the PROSE only.
        _write_status(
            plan_context,
            'cross-verb-epic',
            resume_anchor='inbox drained 8/8 — nothing queued',
        )
        _seed_inbox(plan_context, 'cross-verb-epic', queued=4, archived=2)

        summary = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='cross-verb-epic'))
        listed = cmd_inbox_list(_variant(_INBOX_LIST_ARGS, slug='cross-verb-epic'))

        assert summary['inbox_queued'] == listed['count'] == 4
        assert summary['inbox_state'] == listed['inbox_state'] == 'present'

    def test_should_agree_with_inbox_list_on_the_absent_inbox_state(self, plan_context):
        # The agreement holds on the *could not look* zero too — both verbs draw
        # ``inbox_state`` from the same closed present/missing vocabulary.
        cmd_scaffold(_variant(_SCAFFOLD_ARGS, slug='cross-verb-absent-epic'))
        _write_status(plan_context, 'cross-verb-absent-epic')
        (_epic_dir(plan_context, 'cross-verb-absent-epic') / 'inbox').rmdir()

        summary = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='cross-verb-absent-epic'))
        listed = cmd_inbox_list(_variant(_INBOX_LIST_ARGS, slug='cross-verb-absent-epic'))

        assert summary['inbox_state'] == listed['inbox_state'] == 'missing'
        assert summary['inbox_queued'] == listed['count'] == 0

    def test_should_only_count_files_matching_the_channel_filename_grammar(self, plan_context):
        # The archived tally uses the SAME shape filter the channel allocates
        # with, so an unrelated file dropped into archive/ never inflates it.
        _write_status(plan_context, 'shape-filter-epic')
        _seed_inbox(
            plan_context,
            'shape-filter-epic',
            archived=2,
            extra_names=('README.md', 'notes.txt', 'sender-nn.md'),
        )

        result = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='shape-filter-epic'))

        assert result['inbox_archived'] == 2


# =============================================================================
# migrate-layout
# =============================================================================

#: The hand-written narrative a monolithic ``epic.md`` carries AROUND its two
#: generated blocks. Both annotation zones are included, because the migration
#: must leave every one of these bytes where it was.
_EPIC_HEAD = (
    '# Epic: Migration Fixture\n'
    '\n'
    'slug: migrate-epic\n'
    '\n'
    '## Vision\n'
    '\n'
    'A hand-written vision paragraph.\n'
    '\n'
    '## START HERE\n'
    '\n'
)
_EPIC_SUMMARY_BLOCK = (
    '<!-- GENERATED BLOCK — never hand-write or hand-edit this section.\n'
    '     Paste the returned `summary` block verbatim between the markers. -->\n'
    '\n'
    '<!-- BEGIN GENERATED: resume-summary -->\n'
    '**Resume anchor**: a stale pasted anchor\n'
    '<!-- END GENERATED: resume-summary -->\n'
    '\n'
)
_EPIC_MIDDLE = (
    '### Annotations\n'
    '\n'
    '<!-- ANNOTATION ZONE — hand-written. -->\n'
    '\n'
    '- PLAN-01 — waits on the CI fix\n'
    '\n'
    '## Ordered Queue\n'
    '\n'
)
_EPIC_QUEUE_BLOCK = (
    '<!-- GENERATED BLOCK — never hand-write or hand-edit the table between the markers. -->\n'
    '\n'
    '<!-- BEGIN GENERATED: ordered-queue -->\n'
    '| # | Plan | Workstream | Status | Surface (expected) |\n'
    '|---|------|------------|--------|--------------------|\n'
    '| 1 | PLAN-99 | WS-09 | staged | stale |\n'
    '<!-- END GENERATED: ordered-queue -->\n'
    '\n'
)
_EPIC_TAIL = (
    '### Queue annotations\n'
    '\n'
    '<!-- ANNOTATION ZONE — hand-written queue notes. -->\n'
    '\n'
    '- PLAN-02 — disjoint from PLAN-01\n'
    '\n'
    '## Decisions\n'
    '\n'
    '- a recorded decision\n'
)


def _migration_fixture(plan_context, slug: str, *, archived: bool = False) -> Path:
    """Write a monolithic ledger plus a marker-bearing ``epic.md``; return the epic root."""
    base = 'archived-orchestrators' if archived else 'orchestrator'
    root = Path(plan_context.fixture_dir) / base / slug
    doc = _fixture_doc(
        [
            {**_make_plan('PLAN-01', status='running', plan_marshall_plan_id='epic-plan-1'), 'note': 'extra field'},
            _make_plan('PLAN-02', status='shipped', pr='#12', landing='PLAN-02.md'),
        ],
        resume_anchor='resume at PLAN-01 CI',
    )
    doc['title_token'] = 'MIG'
    write_legacy_status(root, doc)
    epic = _EPIC_HEAD + _EPIC_SUMMARY_BLOCK + _EPIC_MIDDLE + _EPIC_QUEUE_BLOCK + _EPIC_TAIL
    (root / 'epic.md').write_text(epic, encoding='utf-8')
    return root


class TestMigrateLayout:
    """``migrate-layout`` converts a legacy tree preserving every value."""

    def test_every_row_value_and_the_anchor_survive_the_conversion(self, plan_context):
        root = _migration_fixture(plan_context, 'migrate-epic')

        result = cmd_migrate_layout(_variant(_MIGRATE_ARGS, slug='migrate-epic'))

        assert result['status'] == 'success'
        assert result['already_migrated'] is False
        assert result['rows_migrated'] == 2
        rows = _rows(root)
        assert rows == [
            {
                **_make_plan('PLAN-01', status='running', plan_marshall_plan_id='epic-plan-1'),
                'seq': 1,
                'note': 'extra field',
            },
            {**_make_plan('PLAN-02', status='shipped', pr='#12', landing='PLAN-02.md'), 'seq': 2},
        ]
        assert (root / 'resume_anchor.md').read_text(encoding='utf-8') == 'resume at PLAN-01 CI\n'
        header = _header(root)
        # Every header value survives — including one no field list names —
        # and only the queue, the anchor and the shared stamp leave the header.
        assert header['title_token'] == 'MIG'
        assert header['title'] == 'Fixture Epic'
        assert header['workstreams'] == ['WS-01']
        assert not {'plans', 'resume_anchor', 'updated'} & set(header)

    def test_the_generated_blocks_leave_and_every_hand_written_byte_stays(self, plan_context):
        root = _migration_fixture(plan_context, 'migrate-epic')

        result = cmd_migrate_layout(_variant(_MIGRATE_ARGS, slug='migrate-epic'))

        assert (root / 'epic.md').read_text(encoding='utf-8') == _EPIC_HEAD + _EPIC_MIDDLE + _EPIC_TAIL
        assert result['epic_blocks'] == [
            {'block': 'resume-summary', 'outcome': 'removed'},
            {'block': 'ordered-queue', 'outcome': 'removed'},
        ]

    def test_the_written_view_equals_a_fresh_render(self, plan_context):
        root = _migration_fixture(plan_context, 'migrate-epic')

        result = cmd_migrate_layout(_variant(_MIGRATE_ARGS, slug='migrate-epic'))
        regenerated = cmd_regenerate_view(_variant(_REGENERATE_VIEW_ARGS, slug='migrate-epic'))

        assert result['view_written'] is True
        # A fresh render over the migrated ledger is byte-identical to what the
        # migration wrote, so regenerating writes nothing.
        assert regenerated['written'] is False
        view = (root / 'queue-view.md').read_text(encoding='utf-8')
        assert '| 1 | PLAN-01 | WS-01 | running |' in view
        # The stale pasted row never reaches the view: it is rendered, not copied.
        assert 'PLAN-99' not in view

    def test_a_second_run_reports_already_migrated_and_writes_nothing(self, plan_context):
        root = _migration_fixture(plan_context, 'migrate-epic')
        cmd_migrate_layout(_variant(_MIGRATE_ARGS, slug='migrate-epic'))
        before = _snapshot(root)

        second = cmd_migrate_layout(_variant(_MIGRATE_ARGS, slug='migrate-epic'))

        assert second['status'] == 'success'
        assert second['already_migrated'] is True
        assert second['tail_completed'] is False
        assert _snapshot(root) == before

    def test_a_rerun_after_an_interrupted_tail_finishes_it(self, plan_context):
        """A run interrupted after the header commit leaves per-concern ledger files
        beside an ``epic.md`` still carrying both GENERATED blocks and no view; the
        re-run reports ``already_migrated`` AND strips the blocks and writes the view."""
        root = _migration_fixture(plan_context, 'migrate-epic')
        write_ledger(root, json.loads((root / 'status.json').read_text(encoding='utf-8')))
        assert not (root / 'queue-view.md').exists()

        result = cmd_migrate_layout(_variant(_MIGRATE_ARGS, slug='migrate-epic'))
        regenerated = cmd_regenerate_view(_variant(_REGENERATE_VIEW_ARGS, slug='migrate-epic'))

        assert result['already_migrated'] is True
        assert result['tail_completed'] is True
        assert (root / 'epic.md').read_text(encoding='utf-8') == _EPIC_HEAD + _EPIC_MIDDLE + _EPIC_TAIL
        assert [block['outcome'] for block in result['epic_blocks']] == ['removed', 'removed']
        assert result['view_written'] is True
        assert regenerated['written'] is False

    def test_an_archived_epic_is_resolved_and_converted_in_place(self, plan_context):
        root = _migration_fixture(plan_context, 'migrate-archived-epic', archived=True)

        result = cmd_migrate_layout(_variant(_MIGRATE_ARGS, slug='migrate-archived-epic'))

        assert result['status'] == 'success'
        assert result['archived'] is True
        assert [row['id'] for row in _rows(root)] == ['PLAN-01', 'PLAN-02']
        assert not _epic_dir(plan_context, 'migrate-archived-epic').exists()

    def test_an_unmigratable_row_refuses_the_whole_conversion(self, plan_context):
        root = _epic_dir(plan_context, 'migrate-bad-epic')
        write_legacy_status(root, _fixture_doc([_make_plan('PLAN-01'), {'id': '../evil', 'slug': 'x'}]))
        before = _snapshot(root)

        result = cmd_migrate_layout(_variant(_MIGRATE_ARGS, slug='migrate-bad-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'unmigratable_rows'
        assert result['rejected_rows'][0]['id'] == '../evil'
        assert _snapshot(root) == before

    def test_an_unsafe_slug_and_an_absent_tree_are_refused(self, plan_context):
        unsafe = cmd_migrate_layout(_variant(_MIGRATE_ARGS, slug='../evil'))
        absent = cmd_migrate_layout(_variant(_MIGRATE_ARGS, slug='ghost-epic'))

        assert unsafe['error'] == 'invalid_slug'
        assert absent['error'] == 'not_found'


# =============================================================================
# CLI boundary (constructed argv at the subprocess boundary)
# =============================================================================


class TestCli:
    def test_should_scaffold_through_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}

        result = run_script(SCRIPT_PATH, 'scaffold', '--slug', 'cli-epic', env_overrides=env)

        assert result.returncode == 0
        assert 'status: success' in result.stdout
        assert 'already_existed: false' in result.stdout
        for sub in ('workstreams', 'plans', 'landings', 'logs', 'inbox'):
            assert (_epic_dir(plan_context, 'cli-epic') / sub).is_dir()

    def test_should_transition_and_read_queue_through_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _write_status(plan_context, 'cli-queue-epic', plans=[_make_plan('PLAN-01')])

        transition = run_script(
            SCRIPT_PATH,
            'queue',
            '--slug',
            'cli-queue-epic',
            '--transition',
            'PLAN-01',
            '--status',
            'running',
            env_overrides=env,
        )
        read = run_script(SCRIPT_PATH, 'queue', '--slug', 'cli-queue-epic', env_overrides=env)

        assert transition.returncode == 0
        assert 'previous_status: staged' in transition.stdout
        assert 'new_status: running' in transition.stdout
        assert read.returncode == 0
        assert 'running' in read.stdout

    def test_should_set_row_field_and_read_it_back_through_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _write_status(plan_context, 'cli-setrow-epic', plans=[_make_plan('PLAN-01')])

        set_row = run_script(
            SCRIPT_PATH,
            'queue',
            '--slug',
            'cli-setrow-epic',
            '--set-row',
            'PLAN-01',
            '--field',
            'pr',
            '--value',
            '#1001',
            env_overrides=env,
        )
        read = run_script(SCRIPT_PATH, 'queue', '--slug', 'cli-setrow-epic', env_overrides=env)

        assert set_row.returncode == 0
        assert 'operation: queue-set-row' in set_row.stdout
        assert 'field: pr' in set_row.stdout
        assert '#1001' in set_row.stdout
        assert read.returncode == 0
        assert '#1001' in read.stdout

    def test_should_add_row_and_read_it_back_through_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _write_status(plan_context, 'cli-addrow-epic', plans=[])

        add_row = run_script(
            SCRIPT_PATH,
            'queue',
            '--slug',
            'cli-addrow-epic',
            '--add-row',
            'PLAN-07',
            '--slug-value',
            'plan-07',
            '--workstream',
            'WS-01',
            env_overrides=env,
        )
        read = run_script(SCRIPT_PATH, 'queue', '--slug', 'cli-addrow-epic', env_overrides=env)

        assert add_row.returncode == 0
        assert 'operation: queue-add-row' in add_row.stdout
        assert 'plan: PLAN-07' in add_row.stdout
        assert read.returncode == 0
        assert 'PLAN-07' in read.stdout

    def test_should_generate_resume_summary_through_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _write_status(plan_context, 'cli-summary-epic', plans=[_make_plan('PLAN-01')])

        result = run_script(SCRIPT_PATH, 'resume-summary', '--slug', 'cli-summary-epic', env_overrides=env)

        assert result.returncode == 0
        assert 'status: success' in result.stdout
        assert 'summary:' in result.stdout
        assert 'PLAN-01' in result.stdout

    def test_should_reject_unknown_subcommand(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}

        result = run_script(SCRIPT_PATH, 'launch', '--slug', 'cli-epic', env_overrides=env)

        assert result.returncode == 2
