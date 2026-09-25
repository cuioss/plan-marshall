# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_reconcile_fixtures import (
    GHOST,
    REAL_A,
    _reconcile_ns,
    _seed_manifest,
    _write_marshal,
    cmd_reconcile,
    read_manifest,
)

# =============================================================================
# The fail-loud direction — live config still wants a step whose doc is gone
# =============================================================================


class TestBrokenStepStillFailsLoud:
    def test_unloadable_step_still_in_live_config_is_an_error(self, plan_context):
        """The ORIGINAL motivating failure keeps its hard fail.

        The plan deleted the standards doc but did NOT sweep marshal.json, so
        live config still schedules a step that cannot run. Reconciling that
        away would silently drop work the project still asks for.
        """
        _write_marshal(plan_context.fixture_dir, [REAL_A, GHOST])
        _seed_manifest('rec-broken', [REAL_A, GHOST], candidate_steps=[REAL_A, GHOST])

        result = cmd_reconcile(_reconcile_ns('rec-broken'))
        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'unreconcilable_step'
        assert result['broken'] == [GHOST]

    def test_broken_step_message_is_the_canonical_actionable_phrasing(self, plan_context):
        _write_marshal(plan_context.fixture_dir, [GHOST])
        _seed_manifest('rec-broken-msg', [GHOST], candidate_steps=[GHOST])

        result = cmd_reconcile(_reconcile_ns('rec-broken-msg'))
        assert 'missing standards file' in result['message']
        assert 'deleted the file without sweeping' in result['message']

    def test_broken_step_is_not_applied(self, plan_context):
        _write_marshal(plan_context.fixture_dir, [REAL_A, GHOST])
        _seed_manifest('rec-broken-apply', [REAL_A, GHOST], candidate_steps=[REAL_A, GHOST])

        cmd_reconcile(_reconcile_ns('rec-broken-apply', apply=True))
        assert GHOST in read_manifest('rec-broken-apply')['phase_6']['steps'], 'a failing reconcile must write nothing'
