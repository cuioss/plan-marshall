# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_reconcile_fixtures import (
    GHOST,
    REAL_A,
    _reconcile_ns,
    _seed_manifest,
    cmd_reconcile,
)

# =============================================================================
# Fail-closed when live config cannot be read at all
# =============================================================================


class TestUnreadableLiveConfigFailsClosed:
    def test_no_marshal_treats_unloadable_as_broken(self, plan_context):
        """With no live config there is no evidence the step was dropped.

        Absence of evidence is not evidence of absence: without a live
        candidate set the run cannot tell "config dropped it" from "config
        still wants it", so it keeps today's hard fail rather than inventing a
        clean verdict.
        """
        _seed_manifest('rec-nomarshal', [REAL_A, GHOST], candidate_steps=[REAL_A, GHOST])

        result = cmd_reconcile(_reconcile_ns('rec-nomarshal'))
        assert result['status'] == 'error'
        assert result['error'] == 'unreconcilable_step'
        assert result['candidate_source'] == 'unavailable'
