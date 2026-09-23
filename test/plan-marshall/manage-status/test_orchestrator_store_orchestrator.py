#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the manage-status orchestrator store (kind=orchestrator epic ledger).

Its sections, in order:

* Create
* Read
* update-field
* Metadata
* Legacy layout refusal
"""

import json
from argparse import Namespace

from _orchestrator_store_fixtures import (
    _core,
    _create_args,
    _legacy_document,
    _orchestrator_anchor_file,
    _orchestrator_queue_dir,
    _orchestrator_root,
    _orchestrator_status_file,
    _read_header,
    _row,
    _seed_ledger,
    _write_legacy,
    cmd_orchestrator_create,
    cmd_orchestrator_metadata,
    cmd_orchestrator_read,
    cmd_orchestrator_update_field,
)

#: One valid ``--value`` per updatable field, paired with the value the assembled
#: ledger must then carry. Each differs from what ``create`` writes.
_SWEEP_VALUES = {
    'phase': ('closed', 'closed'),
    'resume_anchor': ('run decompose next', 'run decompose next'),
    'workstreams': ('["WS-09"]', ['WS-09']),
}

# =============================================================================
# Create
# =============================================================================


class TestOrchestratorCreate:
    def test_should_create_header_and_empty_anchor(self, plan_context):
        result = cmd_orchestrator_create(_create_args('test-epic'))

        assert result['status'] == 'success'
        assert result['store'] == 'orchestrator'
        header = _read_header(plan_context, 'test-epic')
        assert header['kind'] == 'orchestrator'
        assert header['title'] == 'Test Epic'
        assert header['phase'] == 'init'
        assert header['workstreams'] == []
        assert header['metadata'] == {}
        assert 'created' in header
        # The header carries no queue, no anchor and no shared `updated` stamp.
        assert 'plans' not in header
        assert 'resume_anchor' not in header
        assert 'updated' not in header
        assert _orchestrator_anchor_file(plan_context, 'test-epic').read_text(encoding='utf-8') == '\n'
        assert not _orchestrator_queue_dir(plan_context, 'test-epic').exists()

    def test_should_reject_duplicate_create_without_force(self, plan_context):
        cmd_orchestrator_create(_create_args('dup-epic'))

        result = cmd_orchestrator_create(_create_args('dup-epic', title='Second'))

        assert result['status'] == 'error'
        assert result['error'] == 'already_exists'

    def test_should_overwrite_header_with_force_and_leave_queue_untouched(self, plan_context):
        root = _orchestrator_root(plan_context, 'force-epic')
        _seed_ledger(root, header={'title': 'Original'}, rows=(_row('PLAN-01', 'first'),))
        row_file = _orchestrator_queue_dir(plan_context, 'force-epic') / 'PLAN-01.json'
        row_bytes = row_file.read_bytes()

        result = cmd_orchestrator_create(_create_args('force-epic', title='Replaced', force=True))

        assert result['status'] == 'success'
        assert _read_header(plan_context, 'force-epic')['title'] == 'Replaced'
        assert row_file.read_bytes() == row_bytes


# =============================================================================
# Read
# =============================================================================


class TestOrchestratorRead:
    def test_should_read_created_ledger_as_assembled_document(self, plan_context):
        cmd_orchestrator_create(_create_args('read-epic'))

        result = cmd_orchestrator_read(Namespace(plan_id='read-epic'))

        assert result['status'] == 'success'
        assert result['store'] == 'orchestrator'
        assert result['plan']['kind'] == 'orchestrator'
        assert result['plan']['phase'] == 'init'
        assert result['plan']['plans'] == []
        assert result['plan']['resume_anchor'] == ''
        assert 'unreadable_rows' not in result

    def test_should_assemble_rows_in_seq_order(self, plan_context):
        root = _orchestrator_root(plan_context, 'order-epic')
        _seed_ledger(
            root,
            anchor='next: analyze PLAN-02',
            rows=(_row('PLAN-02', 'second', seq=1), _row('PLAN-01', 'first', seq=2)),
        )

        result = cmd_orchestrator_read(Namespace(plan_id='order-epic'))

        assert [row['id'] for row in result['plan']['plans']] == ['PLAN-02', 'PLAN-01']
        assert result['plan']['resume_anchor'] == 'next: analyze PLAN-02'

    def test_should_report_file_not_found_for_missing_status(self, plan_context):
        result = cmd_orchestrator_read(Namespace(plan_id='absent-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'

    def test_should_report_unreadable_row_instead_of_dropping_it(self, plan_context):
        root = _orchestrator_root(plan_context, 'bad-row-epic')
        _seed_ledger(root, rows=(_row('PLAN-01', 'first'),))
        (_orchestrator_queue_dir(plan_context, 'bad-row-epic') / 'PLAN-02.json').write_text(
            '<<<<<<< HEAD\n', encoding='utf-8'
        )

        result = cmd_orchestrator_read(Namespace(plan_id='bad-row-epic'))

        assert result['status'] == 'success'
        assert [row['id'] for row in result['plan']['plans']] == ['PLAN-01']
        assert [row['file'] for row in result['unreadable_rows']] == ['PLAN-02.json']

    def test_should_report_unreadable_header_distinctly_from_absent(self, plan_context):
        root = _orchestrator_root(plan_context, 'bad-header-epic')
        root.mkdir(parents=True)
        (root / 'status.json').write_text('[1, 2]', encoding='utf-8')

        result = cmd_orchestrator_read(Namespace(plan_id='bad-header-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'header_unreadable'


# =============================================================================
# update-field
# =============================================================================


class TestOrchestratorUpdateField:
    def test_should_update_phase_through_lifecycle(self, plan_context):
        cmd_orchestrator_create(_create_args('phase-epic'))

        for phase in ('orchestrating', 'closed'):
            result = cmd_orchestrator_update_field(Namespace(plan_id='phase-epic', field='phase', value=phase))
            assert result['status'] == 'success'

        header = _read_header(plan_context, 'phase-epic')
        assert header['phase'] == 'closed'
        assert 'updated' not in header

    def test_should_reject_invalid_phase_value(self, plan_context):
        cmd_orchestrator_create(_create_args('bad-phase-epic'))

        result = cmd_orchestrator_update_field(Namespace(plan_id='bad-phase-epic', field='phase', value='running'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_value'

    def test_should_reject_unknown_field(self, plan_context):
        cmd_orchestrator_create(_create_args('bad-field-epic'))

        result = cmd_orchestrator_update_field(Namespace(plan_id='bad-field-epic', field='kind', value='plan'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_field'

    def test_should_write_resume_anchor_to_its_own_file(self, plan_context):
        cmd_orchestrator_create(_create_args('anchor-epic'))
        header_bytes = _orchestrator_status_file(plan_context, 'anchor-epic').read_bytes()

        result = cmd_orchestrator_update_field(
            Namespace(plan_id='anchor-epic', field='resume_anchor', value='await PR #912 CI, then analyze landing')
        )

        assert result['status'] == 'success'
        anchor = _orchestrator_anchor_file(plan_context, 'anchor-epic').read_text(encoding='utf-8')
        assert anchor == 'await PR #912 CI, then analyze landing\n'
        # The anchor write does not touch the header at all.
        assert _orchestrator_status_file(plan_context, 'anchor-epic').read_bytes() == header_bytes

    def test_should_refuse_plans_field_and_write_nothing(self, plan_context):
        """The queue is no longer an update-field target: a whole-array rewrite
        cannot exist over per-row files, so ``plans`` left the updatable set."""
        cmd_orchestrator_create(_create_args('queue-epic'))
        header_bytes = _orchestrator_status_file(plan_context, 'queue-epic').read_bytes()
        plans = [_row('PLAN-01', 'first-plan')]

        result = cmd_orchestrator_update_field(Namespace(plan_id='queue-epic', field='plans', value=json.dumps(plans)))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_field'
        assert _orchestrator_status_file(plan_context, 'queue-epic').read_bytes() == header_bytes
        assert not _orchestrator_queue_dir(plan_context, 'queue-epic').exists()

    def test_should_update_workstreams_list_from_json_array(self, plan_context):
        cmd_orchestrator_create(_create_args('ws-epic'))

        result = cmd_orchestrator_update_field(
            Namespace(plan_id='ws-epic', field='workstreams', value='["WS-01", "WS-02"]')
        )

        assert result['status'] == 'success'
        assert _read_header(plan_context, 'ws-epic')['workstreams'] == ['WS-01', 'WS-02']

    def test_should_reject_non_json_array_for_list_field(self, plan_context):
        cmd_orchestrator_create(_create_args('bad-list-epic'))

        result = cmd_orchestrator_update_field(
            Namespace(plan_id='bad-list-epic', field='workstreams', value='not-json')
        )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_value'

    def test_should_change_every_updatable_field_and_exclude_the_queue(self, plan_context):
        """Every member of ``ORCHESTRATOR_UPDATABLE_FIELDS`` lands its new value in
        the assembled ledger, and ``plans`` is not a member. The sweep's value
        table must equal the membership, so a field joining the set without a
        sweep value fails here instead of going unexercised."""
        assert set(_SWEEP_VALUES) == set(_core.ORCHESTRATOR_UPDATABLE_FIELDS)
        assert 'plans' not in _core.ORCHESTRATOR_UPDATABLE_FIELDS
        cmd_orchestrator_create(_create_args('sweep-epic'))

        for field, (value, _expected) in _SWEEP_VALUES.items():
            result = cmd_orchestrator_update_field(Namespace(plan_id='sweep-epic', field=field, value=value))
            assert result['status'] == 'success', field

        document = cmd_orchestrator_read(Namespace(plan_id='sweep-epic'))['plan']
        assert {field: document[field] for field in _SWEEP_VALUES} == {
            field: expected for field, (_value, expected) in _SWEEP_VALUES.items()
        }


# =============================================================================
# Metadata
# =============================================================================


class TestOrchestratorMetadata:
    def test_should_round_trip_metadata_field(self, plan_context):
        cmd_orchestrator_create(_create_args('meta-epic'))

        set_result = cmd_orchestrator_metadata(
            Namespace(plan_id='meta-epic', set=True, get=False, field='owner', value='operator')
        )
        get_result = cmd_orchestrator_metadata(
            Namespace(plan_id='meta-epic', set=False, get=True, field='owner', value=None)
        )

        assert set_result['status'] == 'success'
        assert get_result['status'] == 'success'
        assert get_result['value'] == 'operator'
        assert _read_header(plan_context, 'meta-epic')['metadata'] == {'owner': 'operator'}

    def test_should_refuse_append_and_write_nothing(self, plan_context):
        """REGRESSION: `--append` is on the SHARED subparser but implemented only
        for the plans store. Ignored here it fell through to the --set branch and
        OVERWROTE, reporting success — reproducing, on the store that never
        implemented it, the exact clobber the flag exists to eliminate.
        """
        cmd_orchestrator_create(_create_args('meta-append-epic'))
        cmd_orchestrator_metadata(
            Namespace(
                plan_id='meta-append-epic', set=True, get=False, append=False, field='session_ids', value='sess-A'
            )
        )

        result = cmd_orchestrator_metadata(
            Namespace(plan_id='meta-append-epic', set=True, get=False, append=True, field='session_ids', value='sess-B')
        )

        assert result['status'] == 'error'
        assert result['error'] == 'append_unsupported_for_store'
        # The earlier value SURVIVES — the refusal wrote nothing.
        get_result = cmd_orchestrator_metadata(
            Namespace(plan_id='meta-append-epic', set=False, get=True, append=False, field='session_ids', value=None)
        )
        assert get_result['value'] == 'sess-A'

    def test_should_report_not_found_for_missing_metadata_field(self, plan_context):
        cmd_orchestrator_create(_create_args('meta-missing-epic'))

        result = cmd_orchestrator_metadata(
            Namespace(plan_id='meta-missing-epic', set=False, get=True, field='absent', value=None)
        )

        assert result['status'] == 'not_found'

    def test_should_require_get_or_set(self, plan_context):
        cmd_orchestrator_create(_create_args('meta-noop-epic'))

        result = cmd_orchestrator_metadata(
            Namespace(plan_id='meta-noop-epic', set=False, get=False, field='x', value=None)
        )

        assert result['status'] == 'error'
        assert result['error'] == 'missing_operation'

    def test_should_reject_combined_get_and_set(self, plan_context):
        cmd_orchestrator_create(_create_args('meta-both-epic'))

        result = cmd_orchestrator_metadata(
            Namespace(plan_id='meta-both-epic', set=True, get=True, field='owner', value='operator')
        )

        assert result['status'] == 'error'
        assert result['error'] == 'wrong_parameters'

    def test_should_reject_combined_get_and_set_without_resurrecting_archived(self, plan_context):
        # Simulate a prior `archive`: the epic lives ONLY in the archived tree
        # (phase closed); no active tree exists. A combined --get --set call must
        # be refused up front — before allow_archived resolution or any write —
        # so the STRICT active-path write branch never resurrects the active dir.
        slug = 'meta-archived-both-epic'
        active_dir = plan_context.fixture_dir / 'orchestrator' / slug
        archived_dir = plan_context.fixture_dir / 'archived-orchestrators' / slug
        _seed_ledger(archived_dir, header={'title': 'Archived Epic', 'phase': 'closed'})

        result = cmd_orchestrator_metadata(Namespace(plan_id=slug, set=True, get=True, field='owner', value='operator'))

        assert result['status'] == 'error'
        assert result['error'] == 'wrong_parameters'
        # The refused call performed no read/write: the active tree stays absent.
        assert not active_dir.exists()

    def test_should_read_archived_metadata_through_read_fallback(self, plan_context):
        slug = 'meta-archived-get-epic'
        archived_dir = plan_context.fixture_dir / 'archived-orchestrators' / slug
        _seed_ledger(archived_dir, header={'phase': 'closed', 'metadata': {'parallelization_scope': '2'}})

        result = cmd_orchestrator_metadata(
            Namespace(plan_id=slug, set=False, get=True, field='parallelization_scope', value=None)
        )

        assert result['status'] == 'success'
        assert result['value'] == '2'


# =============================================================================
# Legacy layout refusal
# =============================================================================


class TestOrchestratorLegacyLayoutRefusal:
    """A monolithic ``status.json`` is refused by every verb with ``legacy_layout``
    naming ``orchestrator migrate-layout``, and nothing is written — there is no
    read-fallback that would read a legacy queue or anchor as empty."""

    def test_should_refuse_legacy_read(self, plan_context):
        _write_legacy(_orchestrator_root(plan_context, 'legacy-read-epic'))

        result = cmd_orchestrator_read(Namespace(plan_id='legacy-read-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'legacy_layout'
        assert 'orchestrator migrate-layout --slug legacy-read-epic' in result['remedy']

    def test_should_refuse_legacy_update_field_and_write_nothing(self, plan_context):
        path = _write_legacy(_orchestrator_root(plan_context, 'legacy-write-epic'))
        before = path.read_bytes()

        for field, value in (('phase', 'closed'), ('resume_anchor', 'new'), ('workstreams', '[]')):
            result = cmd_orchestrator_update_field(Namespace(plan_id='legacy-write-epic', field=field, value=value))
            assert result['status'] == 'error'
            assert result['error'] == 'legacy_layout'

        assert path.read_bytes() == before
        assert not _orchestrator_anchor_file(plan_context, 'legacy-write-epic').exists()

    def test_should_refuse_legacy_metadata_set_and_write_nothing(self, plan_context):
        path = _write_legacy(_orchestrator_root(plan_context, 'legacy-meta-epic'))
        before = path.read_bytes()

        result = cmd_orchestrator_metadata(
            Namespace(plan_id='legacy-meta-epic', set=True, get=False, field='owner', value='operator')
        )

        assert result['status'] == 'error'
        assert result['error'] == 'legacy_layout'
        assert path.read_bytes() == before

    def test_should_refuse_a_header_carrying_only_the_anchor_key(self, plan_context):
        document = _legacy_document()
        del document['plans']
        _write_legacy(_orchestrator_root(plan_context, 'legacy-anchor-epic'), document)

        result = cmd_orchestrator_read(Namespace(plan_id='legacy-anchor-epic'))

        assert result['error'] == 'legacy_layout'
