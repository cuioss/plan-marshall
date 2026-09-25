# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_orchestrator_store_orchestrator_fixtures import (
    Namespace,
    _create_args,
    _read_header,
    _seed_ledger,
    cmd_orchestrator_create,
    cmd_orchestrator_metadata,
)

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
