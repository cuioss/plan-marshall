# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_validate_loadable_fixtures import _TOKEN_CONSUMING_FINALIZE_STEPS, _mem


class TestRecordMetricsOrderAfterTokenConsumingSteps:
    def test_record_metrics_order_exceeds_every_token_consuming_step(self):
        """record-metrics order strictly trails every token-consuming step.

        Fails if record-metrics' frontmatter `order` is reverted at or below
        any token-consuming finalize step — the regression this plan guards.
        """
        record_metrics_order = _mem._resolve_step_order('default:record-metrics')
        assert record_metrics_order is not None

        for step in _TOKEN_CONSUMING_FINALIZE_STEPS:
            step_order = _mem._resolve_step_order(step)
            assert step_order is not None, f'token-consuming step {step!r} has no resolvable frontmatter order'
            assert record_metrics_order > step_order, (
                f'record-metrics order ({record_metrics_order}) must be strictly '
                f'greater than {step!r} order ({step_order}) — record-metrics must '
                f'run after every token-consuming finalize step so end-phase folds '
                f'their token spend into the closed 6-finalize phase row'
            )
