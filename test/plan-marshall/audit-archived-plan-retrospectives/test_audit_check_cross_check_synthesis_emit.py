#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``cross-check-synthesis`` genuine-signal predicate and emitted block.
"""

from _audit_fixtures import audit


class TestCrossCheckSynthesisGenuinePredicate:
    """``_syn_genuine`` maps a fired coupling to a genuine (actionable) signal."""

    def test_fired_row_is_genuine(self):
        # fired => genuine
        assert audit._syn_genuine({'fired': True}) is True

    def test_unfired_row_is_informational(self):
        # not fired => informational
        assert audit._syn_genuine({'fired': False}) is False


class TestCrossCheckSynthesisEmitBlock:
    """``emit_cross_check_synthesis_block`` renders the header counts, the D1
    severity column, and is wired into both the CHECK_NAMES and CROSS_PLAN
    registries (runs LAST)."""

    def test_check_registered_as_cross_plan(self):
        # dispatchable AND cross-plan
        assert 'cross-check-synthesis' in audit.CHECK_NAMES
        assert 'cross-check-synthesis' in audit.CROSS_PLAN_CHECKS

    def test_synthesis_runs_last_in_check_names(self):
        # synthesis must be the final dispatch entry so
        # every upstream result is retained before it reads them
        assert audit.CHECK_NAMES[-1] == 'cross-check-synthesis'

    def test_block_header_and_severity_column(self):
        # one fired coupling (a) over an otherwise-empty corpus
        all_results = {
            'token-efficiency-trend': {'regression': ''},
            'input-integrity': [
                {'plan_id': 'p-blind', 'data_confidence': 'blind'},
            ],
        }
        result = audit.cross_check_synthesis(all_results)

        block = audit.emit_cross_check_synthesis_block(result)

        # header counts + the rows[] column set ends in severity
        assert 'check: cross-check-synthesis' in block
        assert 'status: success' in block
        assert 'couplings_evaluated: 10' in block
        assert 'couplings_fired: 1' in block
        assert 'genuine_signal_count: 1' in block
        assert 'rows[10]{coupling,fired,caveat,detail,severity}:' in block

    def test_fired_coupling_renders_genuine_cell(self):
        # coupling (a) fires
        all_results = {
            'token-efficiency-trend': {'regression': ''},
            'input-integrity': [
                {'plan_id': 'p-blind', 'data_confidence': 'blind'},
            ],
        }
        result = audit.cross_check_synthesis(all_results)

        block = audit.emit_cross_check_synthesis_block(result)
        row_line = next(
            ln.strip()
            for ln in block.splitlines()
            if ln.strip().startswith('trend_empty_untrustworthy,')
        )

        # fired row carries true + a trailing genuine severity cell
        assert row_line.startswith('trend_empty_untrustworthy,true,')
        assert row_line.endswith(',genuine')

    def test_unfired_coupling_renders_informational_cell(self):
        # empty corpus: no coupling fires
        result = audit.cross_check_synthesis({})

        block = audit.emit_cross_check_synthesis_block(result)
        row_line = next(
            ln.strip()
            for ln in block.splitlines()
            if ln.strip().startswith('trend_empty_untrustworthy,')
        )

        # unfired row carries false + a trailing informational cell
        assert row_line.startswith('trend_empty_untrustworthy,false,')
        assert row_line.endswith(',informational')
        assert 'couplings_fired: 0' in block
        assert 'genuine_signal_count: 0' in block

    def test_empty_results_evaluate_all_couplings(self):
        # no upstream results at all (best-effort degradation)
        result = audit.cross_check_synthesis({})
        block = audit.emit_cross_check_synthesis_block(result)

        # every coupling still evaluated, none fired
        assert result['couplings_evaluated'] == 10
        assert result['couplings_fired'] == 0
        assert 'couplings_evaluated: 10' in block
