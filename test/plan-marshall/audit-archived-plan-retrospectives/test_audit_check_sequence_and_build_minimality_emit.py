#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ``sequence-and-build-minimality`` emitted block — its columns and severity.
"""

from pathlib import Path

from _audit_fixtures import (
    _sbm_index,
    _write_sbm_plan,
    audit,
)


class TestSequenceBuildMinimalityEmitBlock:
    """``emit_sequence_build_minimality_block`` renders the cross-plan block with
    the D1 severity column, the genuine-signal count, and is wired into the check
    registries."""

    def test_check_registered_in_registries(self):
        # dispatchable and cross-plan scoped
        assert 'sequence-and-build-minimality' in audit.CHECK_NAMES
        assert 'sequence-and-build-minimality' in audit.CROSS_PLAN_CHECKS

    def test_genuine_predicate_fires_only_with_flags(self):
        # a row with >=1 flag is genuine, an empty-flag
        # row is informational (the D1 severity predicate).
        assert audit._sbm_genuine({'flags': ['build_churn(1<10m)']}) is True
        assert audit._sbm_genuine({'flags': []}) is False

    def test_block_carries_thresholds_and_corpus_totals(self, tmp_path: Path):
        # one plan with a single minimal build
        inputs = _write_sbm_plan(
            tmp_path, 'emit-thresholds',
            ledger_builds=[{'dur': 30.0}],
            modified_files=['scripts/audit.py'],
        )
        result = audit.cross_sequence_build_minimality([inputs], _sbm_index(tmp_path))

        block = audit.emit_sequence_build_minimality_block(result)

        # header, the duration-band thresholds, and corpus aggregates
        assert 'check: sequence-and-build-minimality' in block
        assert 'status: success' in block
        assert 'build_minimal_seconds: 120' in block
        assert 'build_heavy_seconds: 400' in block
        assert 'build_clustering_minutes: 10' in block
        assert 'corpus_builds: 1' in block
        assert 'corpus_build_minimal: 1' in block

    def test_flagged_row_renders_genuine_severity_cell(self, tmp_path: Path):
        # a heavy build raises non_minimal_build, the only flag, so the
        # per-plan row must stamp the genuine severity cell.
        inputs = _write_sbm_plan(
            tmp_path, 'emit-genuine',
            ledger_builds=[{'dur': 600.0}],
            modified_files=['scripts/audit.py'],
        )
        result = audit.cross_sequence_build_minimality([inputs], _sbm_index(tmp_path))

        block = audit.emit_sequence_build_minimality_block(result)
        row_line = next(
            ln.strip()
            for ln in block.splitlines()
            if ln.strip().startswith('emit-genuine,')
        )

        # the flagged row ends on the genuine cell, and the count reflects it
        assert row_line.endswith(',genuine')
        assert 'genuine_signal_count: 1' in block

    def test_clean_row_renders_informational_severity_cell(self, tmp_path: Path):
        # a minimal-only plan with no redundancy primitive: informational
        inputs = _write_sbm_plan(
            tmp_path, 'emit-clean',
            ledger_builds=[{'dur': 30.0}],
            modified_files=['scripts/audit.py'],
        )
        result = audit.cross_sequence_build_minimality([inputs], _sbm_index(tmp_path))

        block = audit.emit_sequence_build_minimality_block(result)
        row_line = next(
            ln.strip()
            for ln in block.splitlines()
            if ln.strip().startswith('emit-clean,')
        )

        # the clean row stamps informational and the genuine count is zero
        assert row_line.endswith(',informational')
        assert 'genuine_signal_count: 0' in block

    def test_rows_sorted_descending_by_total_build_seconds(self, tmp_path: Path):
        # two plans; the heavier total must sort first
        light = _write_sbm_plan(
            tmp_path, 'sort-light',
            ledger_builds=[{'dur': 30.0}],
            modified_files=['scripts/audit.py'],
        )
        heavy = _write_sbm_plan(
            tmp_path, 'sort-heavy',
            ledger_builds=[{'dur': 600.0}],
            modified_files=['scripts/audit.py'],
        )
        result = audit.cross_sequence_build_minimality([light, heavy], _sbm_index(tmp_path))

        # rows ordered by descending total_build_seconds
        assert [r['plan_id'] for r in result['rows']] == ['sort-heavy', 'sort-light']

    def test_empty_corpus_yields_zero_aggregates_no_rows(self):
        # no plans in the corpus
        result = audit.cross_sequence_build_minimality([], {})
        block = audit.emit_sequence_build_minimality_block(result)

        # all-zero aggregates, no rows, zero genuine signals
        assert result['plans_in_corpus'] == 0
        assert result['rows'] == []
        assert 'plans_in_corpus: 0' in block
        assert 'genuine_signal_count: 0' in block
