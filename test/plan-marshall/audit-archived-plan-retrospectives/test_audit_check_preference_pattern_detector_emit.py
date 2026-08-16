#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ``preference-pattern-detector`` emitted block — its columns and severity.
"""

from _audit_fixtures import audit


class TestEmitPreferencePatternBlock:
    """``emit_preference_pattern_block`` renders the documented TOON columns and
    the severity column; every surfaced row is genuine."""

    def test_block_header_and_columns(self):
        result = {
            'threshold': 3,
            'candidate_count': 1,
            'rows': [
                {
                    'module': 'python',
                    'finding_class': 'unused import',
                    'disposition': 'suppressed',
                    'occurrence_count': 4,
                    'plan_ids': ['p0', 'p1', 'p2', 'p3'],
                }
            ],
        }

        block = audit.emit_preference_pattern_block(result)

        # exactly one check block with the documented header lines and columns
        assert block.count('check: preference-pattern-detector') == 1
        assert 'status: success' in block
        assert 'threshold: 3' in block
        assert 'candidate_count: 1' in block
        assert 'genuine_signal_count: 1' in block
        assert (
            'rows[1]{module,finding_class,disposition,occurrence_count,plan_ids,severity}:'
            in block
        )

    def test_surfaced_row_is_genuine(self):
        result = {
            'threshold': 3,
            'candidate_count': 1,
            'rows': [
                {
                    'module': 'python',
                    'finding_class': 'magic number',
                    'disposition': 'accepted',
                    'occurrence_count': 3,
                    'plan_ids': ['p0', 'p1', 'p2'],
                }
            ],
        }

        block = audit.emit_preference_pattern_block(result)
        row_line = next(
            ln.strip()
            for ln in block.splitlines()
            if ln.strip().startswith('python,magic number,accepted,')
        )

        # plan_ids are ;-joined and the row ends in the genuine severity cell
        assert 'p0;p1;p2' in row_line
        assert row_line.endswith(',genuine')

    def test_empty_rows_yields_zero_genuine(self):
        result = {'threshold': 3, 'candidate_count': 0, 'rows': []}

        block = audit.emit_preference_pattern_block(result)

        assert 'candidate_count: 0' in block
        assert 'genuine_signal_count: 0' in block
        assert 'rows[0]{module,finding_class,disposition,occurrence_count,plan_ids,severity}:' in block

    def test_block_reports_unattributed_excluded_count(self):
        # D2 — the count of unattributed (default-bucket) recurrences the detector
        # declined to promote is surfaced so the decision is visible, not silent.
        result = {
            'threshold': 3,
            'candidate_count': 0,
            'unattributed_excluded_count': 2,
            'rows': [],
        }

        block = audit.emit_preference_pattern_block(result)

        assert 'unattributed_excluded_count: 2' in block
