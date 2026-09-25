# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_reconcile_fixtures import (
    GHOST,
    REAL_A,
    REAL_B,
    _reconcile_ns,
    _seed_manifest,
    _write_marshal,
    cmd_reconcile,
)

# =============================================================================
# Key canonicalization across the frozen/live boundary
# =============================================================================


class TestPrefixedFrozenIdsCompareCanonically:
    def test_prefixed_frozen_step_is_not_dropped_when_live_lists_it_bare(self, plan_context):
        """A hand-edited manifest may carry `default:`-prefixed ids.

        SKILL.md explicitly sanctions editing execution.toon directly, so the
        frozen list can hold a prefixed id while the live candidate set is
        boundary-normalized. Comparing raw would read the prefixed id as absent
        from live config and drop a step live config still schedules.
        """
        _write_marshal(plan_context.fixture_dir, [REAL_A, GHOST])
        _seed_manifest('rec-prefixed', [REAL_A, f'default:{GHOST}'], candidate_steps=[REAL_A, GHOST])

        result = cmd_reconcile(_reconcile_ns('rec-prefixed'))
        assert result['status'] == 'error', (
            'live config still lists the step, so a prefixed frozen id must be '
            'BROKEN (fail loud), never silently dropped as stale'
        )
        assert result['error'] == 'unreconcilable_step'

    def test_prefixed_frozen_step_is_not_backfilled_as_a_duplicate(self, plan_context):
        """A prefixed frozen id must not read as "absent from the manifest"."""
        _write_marshal(plan_context.fixture_dir, [REAL_A, REAL_B])
        _seed_manifest('rec-dup', [REAL_A, f'default:{REAL_B}'], candidate_steps=[REAL_A])

        result = cmd_reconcile(_reconcile_ns('rec-dup', apply=True))
        assert result['backfill'] == [], (
            f'{REAL_B} is already in the manifest under a prefixed id; backfilling it would duplicate the step'
        )
