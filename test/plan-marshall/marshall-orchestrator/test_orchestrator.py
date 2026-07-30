#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the marshall-orchestrator scaffolding script (D7).

Covers the ``scaffold`` / ``queue`` / ``resume-summary`` verbs under
``PLAN_BASE_DIR`` isolation (via ``plan_context``). The ``archive`` verb has
its own module (``test_orchestrator_archive.py``), and the ``inbox`` verb
group's envelope schema and handler surface have theirs
(``test_inbox_envelope.py``):

- ``scaffold``: directory-tree creation (including ``inbox/``) and idempotency.
- ``queue``: read, transition, and per-row field-set round-trips against a
  fixture status.json, plus the error envelopes (missing status, unknown
  plan, unknown field, unpaired flags, mutually-exclusive write forms).
- ``resume-summary``: START-HERE block generation derived purely from
  status.json (resume anchor, phase, running/parked plans, ordered queue), plus
  the render-time-derived inbox counts — which come from the epic's ``inbox/``
  directory rather than from the anchor's prose, keep the two zeros
  (``present`` / ``missing``) distinct, and sit beside a stale anchor sentence
  that is still rendered verbatim.
- CLI boundary: the three verbs above driven through the ``orchestrator.py``
  entry point with constructed argv at the subprocess boundary
  (``run_script``); the ``inbox`` group's CLI wiring is covered in
  ``test_inbox_channel_contract.py``.
"""

import json
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'marshall-orchestrator', 'orchestrator.py')

_orch = load_script_module(
    'plan-marshall', 'marshall-orchestrator', 'orchestrator.py', 'orchestrator_script'
)

cmd_scaffold = _orch.cmd_scaffold
cmd_queue = _orch.cmd_queue
cmd_inbox_list = _orch.cmd_inbox_list
cmd_resume_summary = _orch.cmd_resume_summary
EPIC_SUBDIRS = _orch.EPIC_SUBDIRS
PLAN_ROW_FIELDS = _orch.PLAN_ROW_FIELDS

FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'


def _epic_dir(plan_context, slug: str) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / slug


def _queue_args(
    slug: str,
    transition: str | None = None,
    status: str | None = None,
    set_row: str | None = None,
    field: str | None = None,
    value: str | None = None,
) -> Namespace:
    """Build a complete ``queue`` Namespace so every flag attribute is present."""
    return Namespace(
        slug=slug,
        transition=transition,
        status=status,
        set_row=set_row,
        field=field,
        value=value,
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


def _write_status(
    plan_context,
    slug: str,
    plans: list | None = None,
    phase: str = 'orchestrating',
    resume_anchor: str = 'await PR #912 CI, then analyze landing',
) -> Path:
    """Write a kind=orchestrator fixture status.json into the isolated store."""
    doc = {
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
    path = _epic_dir(plan_context, slug) / 'status.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding='utf-8')
    return path


def _read_status_file(path: Path) -> dict:
    return dict(json.loads(path.read_text(encoding='utf-8')))


def _seed_inbox(
    plan_context, slug: str, queued: int = 0, archived: int = 0, extra_names: tuple = ()
) -> Path:
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
        result = cmd_scaffold(Namespace(slug='fresh-epic'))

        assert result['status'] == 'success'
        assert result['operation'] == 'scaffold'
        assert result['already_existed'] is False
        root = _epic_dir(plan_context, 'fresh-epic')
        assert result['root'] == str(root)
        assert root.is_dir()
        for sub in ('workstreams', 'plans', 'landings', 'logs', 'inbox'):
            assert (root / sub).is_dir()

    def test_should_report_all_layout_subdirs(self, plan_context):
        result = cmd_scaffold(Namespace(slug='layout-epic'))

        assert sorted(result['directories']) == sorted(EPIC_SUBDIRS)
        assert set(EPIC_SUBDIRS) == {'workstreams', 'plans', 'landings', 'logs', 'inbox'}

    def test_should_be_idempotent_on_rerun(self, plan_context):
        cmd_scaffold(Namespace(slug='rerun-epic'))
        marker = _epic_dir(plan_context, 'rerun-epic') / 'plans' / 'PLAN-01-keep.md'
        marker.write_text('kept', encoding='utf-8')

        result = cmd_scaffold(Namespace(slug='rerun-epic'))

        assert result['status'] == 'success'
        assert result['already_existed'] is True
        assert marker.read_text(encoding='utf-8') == 'kept'

    def test_should_not_create_status_json(self, plan_context):
        cmd_scaffold(Namespace(slug='no-status-epic'))

        assert not (_epic_dir(plan_context, 'no-status-epic') / 'status.json').exists()

    def test_should_reject_invalid_slug(self, plan_context):
        result = cmd_scaffold(Namespace(slug='../evil'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'
        assert not (plan_context.fixture_dir / 'evil').exists()

    def test_should_reject_empty_slug(self, plan_context):
        result = cmd_scaffold(Namespace(slug=''))

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
        assert result['plans'] == plans

    def test_should_error_when_status_json_missing(self, plan_context):
        cmd_scaffold(Namespace(slug='bare-epic'))

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
        status_path = _write_status(
            plan_context, 'flow-epic', plans=[_make_plan('PLAN-01'), _make_plan('PLAN-02')]
        )

        result = cmd_queue(_queue_args('flow-epic', transition='PLAN-01', status='running'))

        assert result['status'] == 'success'
        assert result['operation'] == 'queue-transition'
        assert result['plan'] == 'PLAN-01'
        assert result['previous_status'] == 'staged'
        assert result['new_status'] == 'running'
        on_disk = _read_status_file(status_path)
        assert on_disk['plans'][0]['status'] == 'running'
        assert on_disk['plans'][1]['status'] == 'staged'

    def test_should_stamp_updated_on_transition(self, plan_context):
        status_path = _write_status(plan_context, 'stamp-epic', plans=[_make_plan('PLAN-01')])

        cmd_queue(_queue_args('stamp-epic', transition='PLAN-01', status='parked'))

        assert _read_status_file(status_path)['updated'] != FIXED_TIMESTAMP

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


# =============================================================================
# queue — set-row
# =============================================================================


class TestQueueSetRow:
    def test_should_set_named_row_field_and_leave_siblings_untouched(self, plan_context):
        siblings = [_make_plan('PLAN-02'), _make_plan('PLAN-03', status='running')]
        status_path = _write_status(
            plan_context, 'set-epic', plans=[_make_plan('PLAN-01'), *siblings]
        )

        result = cmd_queue(
            _queue_args('set-epic', set_row='PLAN-01', field='pr', value='#1001')
        )

        assert result['status'] == 'success'
        assert result['operation'] == 'queue-set-row'
        assert result['plan'] == 'PLAN-01'
        assert result['field'] == 'pr'
        assert result['previous_value'] == ''
        assert result['new_value'] == '#1001'
        on_disk = _read_status_file(status_path)
        assert on_disk['plans'][0]['pr'] == '#1001'
        assert on_disk['plans'][1:] == siblings

    def test_should_round_trip_every_whitelisted_field(self, plan_context):
        _write_status(plan_context, 'fields-epic', plans=[_make_plan('PLAN-01')])
        values = {
            'plan_marshall_plan_id': 'epic-plan-1',
            'pr': '#1002',
            'landing': 'PLAN-01.md',
        }
        assert set(values) == set(PLAN_ROW_FIELDS)

        for field, value in values.items():
            cmd_queue(
                _queue_args('fields-epic', set_row='PLAN-01', field=field, value=value)
            )

        row = cmd_queue(_queue_args('fields-epic'))['plans'][0]
        for field, value in values.items():
            assert row[field] == value

    def test_should_report_previous_value_on_overwrite(self, plan_context):
        _write_status(
            plan_context, 'overwrite-epic', plans=[_make_plan('PLAN-01', pr='#900')]
        )

        result = cmd_queue(
            _queue_args('overwrite-epic', set_row='PLAN-01', field='pr', value='#901')
        )

        assert result['previous_value'] == '#900'
        assert result['new_value'] == '#901'

    def test_should_stamp_updated_on_set_row(self, plan_context):
        status_path = _write_status(
            plan_context, 'set-stamp-epic', plans=[_make_plan('PLAN-01')]
        )

        cmd_queue(
            _queue_args('set-stamp-epic', set_row='PLAN-01', field='landing', value='x.md')
        )

        assert _read_status_file(status_path)['updated'] != FIXED_TIMESTAMP

    def test_should_error_for_unknown_plan_id(self, plan_context):
        _write_status(plan_context, 'set-miss-epic', plans=[_make_plan('PLAN-01')])

        result = cmd_queue(
            _queue_args('set-miss-epic', set_row='PLAN-99', field='pr', value='#1')
        )

        assert result['status'] == 'error'
        assert result['error'] == 'plan_not_found'
        assert result['available_plans'] == ['PLAN-01']

    def test_should_error_for_unknown_field(self, plan_context):
        status_path = _write_status(
            plan_context, 'set-field-epic', plans=[_make_plan('PLAN-01')]
        )

        result = cmd_queue(
            _queue_args('set-field-epic', set_row='PLAN-01', field='status', value='shipped')
        )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_field'
        assert 'landing' in result['message']
        assert _read_status_file(status_path)['plans'][0]['status'] == 'staged'

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
        result = cmd_queue(
            _queue_args('set-absent-epic', set_row='PLAN-01', field='pr', value='#1')
        )

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'


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

        result = cmd_resume_summary(Namespace(slug='summary-epic'))

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

    def test_should_mark_terminal_row_missing_both_links(self, plan_context):
        _write_status(
            plan_context, 'gap-both-epic', plans=[_make_plan('PLAN-01', status='shipped')]
        )

        result = cmd_resume_summary(Namespace(slug='gap-both-epic'))

        assert '(!) missing: pr, landing' in result['summary']

    def test_should_mark_terminal_row_missing_only_pr(self, plan_context):
        _write_status(
            plan_context,
            'gap-pr-epic',
            plans=[_make_plan('PLAN-01', status='shipped', landing='PLAN-01.md')],
        )

        result = cmd_resume_summary(Namespace(slug='gap-pr-epic'))

        assert '(!) missing: pr' in result['summary']
        assert '(!) missing: pr, landing' not in result['summary']

    def test_should_mark_landed_row_the_same_as_shipped(self, plan_context):
        _write_status(
            plan_context,
            'gap-landed-epic',
            plans=[_make_plan('PLAN-01', status='landed', pr='#901')],
        )

        result = cmd_resume_summary(Namespace(slug='gap-landed-epic'))

        assert '(!) missing: landing' in result['summary']

    def test_should_not_mark_fully_stamped_terminal_row(self, plan_context):
        _write_status(
            plan_context,
            'gap-none-epic',
            plans=[
                _make_plan('PLAN-01', status='shipped', pr='#901', landing='PLAN-01.md')
            ],
        )

        result = cmd_resume_summary(Namespace(slug='gap-none-epic'))

        assert '(!) missing' not in result['summary']

    def test_should_not_mark_non_terminal_row_with_empty_links(self, plan_context):
        _write_status(
            plan_context,
            'gap-inflight-epic',
            plans=[_make_plan('PLAN-01', status='staged'), _make_plan('PLAN-02', status='running')],
        )

        result = cmd_resume_summary(Namespace(slug='gap-inflight-epic'))

        assert '(!) missing' not in result['summary']

    def test_should_render_empty_queue_marker(self, plan_context):
        _write_status(plan_context, 'empty-epic', plans=[])

        result = cmd_resume_summary(Namespace(slug='empty-epic'))

        assert '**Queue** (staged, in order):' in result['summary']
        assert '- (empty)' in result['summary']

    def test_should_render_placeholder_for_unset_anchor(self, plan_context):
        _write_status(plan_context, 'anchorless-epic', resume_anchor='')

        result = cmd_resume_summary(Namespace(slug='anchorless-epic'))

        assert '**Resume anchor**: (not set)' in result['summary']

    def test_should_error_when_status_json_missing(self, plan_context):
        result = cmd_resume_summary(Namespace(slug='absent-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'

    def test_should_reject_invalid_slug(self, plan_context):
        result = cmd_resume_summary(Namespace(slug='../evil'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'


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

    def test_should_render_the_derived_inbox_line_from_the_filesystem(
        self, plan_context
    ):
        _write_status(plan_context, 'inbox-count-epic')
        _seed_inbox(plan_context, 'inbox-count-epic', queued=2, archived=3)

        result = cmd_resume_summary(Namespace(slug='inbox-count-epic'))

        assert '**Inbox (derived)**: 2 queued, 3 archived' in result['summary']

    def test_should_surface_the_counts_as_top_level_payload_fields(self, plan_context):
        # A caller reconciles against ``inbox list`` without parsing markdown.
        _write_status(plan_context, 'inbox-fields-epic')
        _seed_inbox(plan_context, 'inbox-fields-epic', queued=1, archived=4)

        result = cmd_resume_summary(Namespace(slug='inbox-fields-epic'))

        assert result['inbox_queued'] == 1
        assert result['inbox_archived'] == 4
        assert result['inbox_state'] == 'present'

    def test_should_render_an_empty_queue_as_a_present_zero(self, plan_context):
        # Looked, found nothing — distinct from the absent-directory case below.
        _write_status(plan_context, 'inbox-empty-epic')
        _seed_inbox(plan_context, 'inbox-empty-epic')

        result = cmd_resume_summary(Namespace(slug='inbox-empty-epic'))

        assert '**Inbox (derived)**: 0 queued, 0 archived' in result['summary']
        assert result['inbox_state'] == 'present'

    def test_should_render_an_absent_inbox_explicitly_not_as_zero_queued(
        self, plan_context
    ):
        # Could not look. Rendering "0 queued" here would be the same collapse
        # deliverable 2 removed from ``inbox list``.
        _write_status(plan_context, 'inbox-absent-epic')
        assert not (_epic_dir(plan_context, 'inbox-absent-epic') / 'inbox').exists()

        result = cmd_resume_summary(Namespace(slug='inbox-absent-epic'))

        assert '**Inbox (derived)**: no inbox directory' in result['summary']
        assert '0 queued' not in result['summary']
        assert result['inbox_state'] == 'missing'
        assert result['inbox_queued'] == 0

    def test_should_not_answer_the_two_zeros_with_equal_summaries(self, plan_context):
        # The two zeros agree on every count yet MUST NOT render identically.
        _write_status(plan_context, 'zero-looked-epic')
        _seed_inbox(plan_context, 'zero-looked-epic')
        _write_status(plan_context, 'zero-blind-epic')

        looked = cmd_resume_summary(Namespace(slug='zero-looked-epic'))
        could_not_look = cmd_resume_summary(Namespace(slug='zero-blind-epic'))

        assert looked['inbox_queued'] == could_not_look['inbox_queued'] == 0
        assert looked['inbox_archived'] == could_not_look['inbox_archived'] == 0
        assert looked['summary'] != could_not_look['summary']
        assert looked['inbox_state'] != could_not_look['inbox_state']

    def test_should_keep_a_stale_anchor_verbatim_beside_the_derived_truth(
        self, plan_context
    ):
        # The whole point of the deliverable: the operator's prose is NEVER
        # silently rewritten, and the live count sits visibly next to it so the
        # contradiction is readable instead of hidden.
        _write_status(
            plan_context,
            'stale-anchor-epic',
            resume_anchor='inbox drained 8/8 — nothing queued',
        )
        _seed_inbox(plan_context, 'stale-anchor-epic', queued=3)

        result = cmd_resume_summary(Namespace(slug='stale-anchor-epic'))

        summary = result['summary']
        assert '**Resume anchor**: inbox drained 8/8 — nothing queued' in summary
        assert '**Inbox (derived)**: 3 queued, 0 archived' in summary
        assert result['inbox_queued'] == 3

    def test_should_render_the_derived_line_separately_from_the_anchor_line(
        self, plan_context
    ):
        # Separate LINES, so neither can be mistaken for the other's authority.
        _write_status(plan_context, 'separate-lines-epic')
        _seed_inbox(plan_context, 'separate-lines-epic', queued=1)

        lines = cmd_resume_summary(Namespace(slug='separate-lines-epic'))['summary']

        anchor_line = next(
            line for line in lines.split('\n') if line.startswith('**Resume anchor**')
        )
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

        summary = cmd_resume_summary(Namespace(slug='cross-verb-epic'))
        listed = cmd_inbox_list(Namespace(slug='cross-verb-epic'))

        assert summary['inbox_queued'] == listed['count'] == 4
        assert summary['inbox_state'] == listed['inbox_state'] == 'present'

    def test_should_agree_with_inbox_list_on_the_absent_inbox_state(self, plan_context):
        # The agreement holds on the *could not look* zero too — both verbs draw
        # ``inbox_state`` from the same closed present/missing vocabulary.
        cmd_scaffold(Namespace(slug='cross-verb-absent-epic'))
        _write_status(plan_context, 'cross-verb-absent-epic')
        (_epic_dir(plan_context, 'cross-verb-absent-epic') / 'inbox').rmdir()

        summary = cmd_resume_summary(Namespace(slug='cross-verb-absent-epic'))
        listed = cmd_inbox_list(Namespace(slug='cross-verb-absent-epic'))

        assert summary['inbox_state'] == listed['inbox_state'] == 'missing'
        assert summary['inbox_queued'] == listed['count'] == 0

    def test_should_only_count_files_matching_the_channel_filename_grammar(
        self, plan_context
    ):
        # The archived tally uses the SAME shape filter the channel allocates
        # with, so an unrelated file dropped into archive/ never inflates it.
        _write_status(plan_context, 'shape-filter-epic')
        _seed_inbox(
            plan_context,
            'shape-filter-epic',
            archived=2,
            extra_names=('README.md', 'notes.txt', 'sender-nn.md'),
        )

        result = cmd_resume_summary(Namespace(slug='shape-filter-epic'))

        assert result['inbox_archived'] == 2


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
