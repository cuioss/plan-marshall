# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_orchestrator_store_orchestrator_fixtures import (
    Namespace,
    _create_args,
    _legacy_document,
    _orchestrator_anchor_file,
    _orchestrator_root,
    _row,
    _write_legacy,
    cmd_orchestrator_create,
    cmd_orchestrator_metadata,
    cmd_orchestrator_read,
    cmd_orchestrator_update_field,
    pytest,
)

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

    @pytest.mark.parametrize('force', [False, True], ids=['plain', 'force'])
    def test_should_refuse_legacy_create_and_write_nothing(self, plan_context, force):
        """``--force`` does not bypass the refusal: overwriting a monolithic header
        would drop the queue and the anchor it still carries."""
        root = _orchestrator_root(plan_context, 'legacy-create-epic')
        path = _write_legacy(root, _legacy_document(plans=[_row('PLAN-01', 'first')]))
        before = path.read_bytes()

        result = cmd_orchestrator_create(_create_args('legacy-create-epic', title='Replaced', force=force))

        assert result['status'] == 'error'
        assert result['error'] == 'legacy_layout'
        assert path.read_bytes() == before
        assert not _orchestrator_anchor_file(plan_context, 'legacy-create-epic').exists()

    def test_should_refuse_a_header_carrying_only_the_anchor_key(self, plan_context):
        document = _legacy_document()
        del document['plans']
        _write_legacy(_orchestrator_root(plan_context, 'legacy-anchor-epic'), document)

        result = cmd_orchestrator_read(Namespace(plan_id='legacy-anchor-epic'))

        assert result['error'] == 'legacy_layout'
