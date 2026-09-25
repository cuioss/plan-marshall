# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_decision_rules_fixtures import (
    _compose_ns,
    _mem,
    _restore_footprint_resolver,
    _seed_marshal,
    _stub_footprint,
    cmd_compose,
)


class TestRetiredDropReviewEscapeHatch:
    """The superseded ``drop_review_on_scope_gate`` special case is gone.

    Declared-lane immunity generalizes the carve-out it hard-coded, so the knob,
    its reader, and its override drop-set are removed outright (clean break, no
    shim) rather than left beside the general rule.
    """

    def test_retired_symbols_do_not_survive(self):
        for symbol in ('_read_drop_review_on_scope_gate', '_SCOPE_GATED_OVERRIDE_DROP'):
            assert not hasattr(_mem, symbol), (
                f'{symbol} must be deleted with the drop_review_on_scope_gate escape hatch'
            )

    def test_compose_result_no_longer_reports_the_knob(self, plan_context):
        _seed_marshal(ci_provider='github')
        _stub_footprint(['some/file.py'])

        result = cmd_compose(_compose_ns(plan_id='sg-no-knob'))

        assert result is not None
        assert result['status'] == 'success'
        assert 'drop_review_on_scope_gate' not in result
