# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_orchestrator_store_orchestrator_fixtures import (
    _SWEEP_VALUES,
    Namespace,
    _core,
    _create_args,
    _orchestrator_anchor_file,
    _orchestrator_queue_dir,
    _orchestrator_status_file,
    _read_header,
    _row,
    cmd_orchestrator_create,
    cmd_orchestrator_read,
    cmd_orchestrator_update_field,
    json,
)

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
