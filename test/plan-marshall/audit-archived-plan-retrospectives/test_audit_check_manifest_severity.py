#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Manifest block summary precision — genuine signals are counted and informational
rows are excluded from the genuine-signal total.
"""

from _audit_fixtures import audit


class TestManifestSeverityPrecision:
    def test_genuine_signal_count_counts_only_genuine_rows(self):
        # one drift row, one populated name_drift, two informational
        rows = [
            {'verdict': 'drift', 'name_drift': None},
            {'verdict': 'ok', 'name_drift': 'unresolvable role: foo'},
            {'verdict': 'incomplete', 'name_drift': None},
            {'verdict': 'unloggable', 'name_drift': None},
            {'verdict': 'ok', 'name_drift': None},
        ]
        full_rows = [
            {
                'plan_id': f'p{i}',
                'reason': '',
                'expected_rule': None,
                'actual_rule': None,
                'change_type': None,
                'scope': None,
                'recipe': None,
                'affected': 0,
                'modified': 0,
                **r,
            }
            for i, r in enumerate(rows)
        ]

        block = audit.emit_manifest_block(full_rows)

        # drift + populated name_drift = 2 genuine; informational excluded
        assert 'genuine_signal_count: 2' in block
        assert 'name_drift_count: 1' in block

    def test_severity_classifier_marks_informational_rows(self):
        assert (
            audit._manifest_genuine({'verdict': 'drift', 'name_drift': None})
            is True
        )
        assert (
            audit._manifest_genuine({'verdict': 'ok', 'name_drift': 'x'})
            is True
        )
        assert (
            audit._manifest_genuine({'verdict': 'incomplete', 'name_drift': None})
            is False
        )
        assert (
            audit._manifest_genuine({'verdict': 'ok', 'name_drift': None})
            is False
        )
