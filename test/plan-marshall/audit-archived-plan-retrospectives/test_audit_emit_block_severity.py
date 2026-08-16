#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The uniform severity column and ``genuine_signal_count`` across the ``emit_*``
blocks — table, recurring, and trend blocks each carry the same severity
vocabulary and count only genuine signals.
"""

from _audit_fixtures import audit


class TestSeveritySummary:
    """``_severity_summary`` stamps a uniform ``severity`` cell on every row and
    returns the genuine-signal count — the generalization of the manifest-only
    severity pattern to every ``emit_*_block``."""

    def test_stamps_severity_and_counts_genuine(self):
        # predicate fires on rows whose ``flag`` is truthy
        rows = [{'flag': 'x'}, {'flag': ''}, {'flag': 'y'}]

        stamped, count = audit._severity_summary(rows, lambda r: bool(r['flag']))

        assert count == 2
        assert stamped[0]['severity'] == 'genuine'
        assert stamped[1]['severity'] == 'informational'
        assert stamped[2]['severity'] == 'genuine'

    def test_all_informational_when_predicate_never_fires(self):
        rows = [{'v': 1}, {'v': 2}]

        stamped, count = audit._severity_summary(rows, lambda _r: False)

        assert count == 0
        assert all(r['severity'] == 'informational' for r in stamped)

    def test_empty_rows_yields_zero_count(self):
        stamped, count = audit._severity_summary([], lambda _r: True)

        assert stamped == []
        assert count == 0


class TestEmitTableBlockSeverity:
    """Every ``emit_table_block`` carries the uniform ``severity`` final column
    and the ``genuine_signal_count`` summary line."""

    def test_severity_column_appended_and_count_line_present(self):
        # two rows, one genuine (mismatch populated)
        rows = [
            {'plan_id': 'p1', 'mismatch': 'declared=surgical actual=99'},
            {'plan_id': 'p2', 'mismatch': ''},
        ]

        block = audit.emit_table_block(
            'scope-estimate-accuracy',
            ['plan_id', 'mismatch'],
            rows,
            lambda r: bool(r['mismatch']),
        )

        # header carries the appended severity column + count line
        assert 'rows[2]{plan_id,mismatch,severity}:' in block
        assert 'genuine_signal_count: 1' in block
        assert 'check: scope-estimate-accuracy' in block
        assert 'plans_scanned: 2' in block

    def test_genuine_and_informational_rows_emit_correct_severity_cell(self):
        rows = [
            {'plan_id': 'g', 'outlier': 'over_decomposed (ratio=5.00)'},
            {'plan_id': 'i', 'outlier': ''},
        ]

        block = audit.emit_table_block(
            'task-count-efficiency',
            ['plan_id', 'outlier'],
            rows,
            lambda r: bool(r['outlier']),
        )
        lines = [ln.strip() for ln in block.splitlines()]

        # the row cells end in genuine / informational respectively
        genuine_row = next(ln for ln in lines if ln.startswith('g,'))
        info_row = next(ln for ln in lines if ln.startswith('i,'))
        assert genuine_row.endswith(',genuine')
        assert info_row.endswith(',informational')


class TestEmitRecurringBlockSeverity:
    """Every systemic recurring pattern cleared the N-occurrence threshold, so
    every row is by definition a genuine signal."""

    def test_all_systemic_rows_are_genuine(self):
        result = {
            'threshold': 3,
            'systemic_count': 2,
            'rows': [
                {
                    'signature': 'sig-a',
                    'occurrence_count': 4,
                    'plan_ids': ['p1', 'p2'],
                    'candidate': 'novel',
                },
                {
                    'signature': 'sig-b',
                    'occurrence_count': 3,
                    'plan_ids': ['p3'],
                    'candidate': 'covered_by:lesson-x',
                },
            ],
        }

        block = audit.emit_recurring_block(result)

        # both rows genuine; the count + threshold lines present
        assert 'genuine_signal_count: 2' in block
        assert 'threshold: 3' in block
        assert (
            'rows[2]{signature,occurrence_count,plan_ids,candidate,severity}:'
            in block
        )

    def test_empty_systemic_rows_yields_zero_genuine(self):
        result = {'threshold': 3, 'systemic_count': 0, 'rows': []}

        block = audit.emit_recurring_block(result)

        assert 'genuine_signal_count: 0' in block
        assert 'systemic_count: 0' in block


class TestEmitTrendBlockSeverity:
    """A trend row is genuine only when a sustained regression fired for the
    whole series; without regression the per-plan rows are informational."""

    def test_regression_marks_all_rows_genuine(self):
        # a populated regression string flags the whole series
        result = {
            'plans_in_series': 2,
            'regression': 'tokens/phase rose 100 -> 200 (+100%)',
            'rows': [
                {'plan_id': 'p1', 'phases': 1, 'total_tokens': 100, 'tokens_per_phase': 100},
                {'plan_id': 'p2', 'phases': 1, 'total_tokens': 200, 'tokens_per_phase': 200},
            ],
        }

        block = audit.emit_trend_block(result)

        # both supporting rows genuine when regression fired
        assert 'genuine_signal_count: 2' in block

    def test_no_regression_marks_all_rows_informational(self):
        # empty regression string
        result = {
            'plans_in_series': 2,
            'regression': '',
            'rows': [
                {'plan_id': 'p1', 'phases': 1, 'total_tokens': 100, 'tokens_per_phase': 100},
                {'plan_id': 'p2', 'phases': 1, 'total_tokens': 110, 'tokens_per_phase': 110},
            ],
        }

        block = audit.emit_trend_block(result)

        assert 'genuine_signal_count: 0' in block
        assert (
            'rows[2]{plan_id,phases,total_tokens,tokens_per_phase,severity}:'
            in block
        )
