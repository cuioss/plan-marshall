#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ``input-integrity`` emitted block — its columns, severity, and corpus
completeness summary.
"""

from pathlib import Path

from _audit_fixtures import (
    _write_ii_plan,
    audit,
)


class TestInputIntegrityEmitBlock:
    """``emit_input_integrity_block`` renders the corpus ``data_confidence``
    summary, the per-plan rows with the uniform D1 ``severity`` column, and the
    check is wired into the registries (in ``CHECK_NAMES``, NOT ``CROSS_PLAN``)."""

    def test_check_registered_in_check_names_only(self):
        # dispatchable but deliberately per-plan
        assert 'input-integrity' in audit.CHECK_NAMES
        assert 'input-integrity' not in audit.CROSS_PLAN_CHECKS

    def test_block_header_and_corpus_confidence_summary(self, tmp_path: Path):
        # three plans: fully-recorded, partial, blind
        rows = [
            audit.check_input_integrity(_write_ii_plan(tmp_path, 'p-fr')),
            audit.check_input_integrity(
                _write_ii_plan(tmp_path, 'p-partial', has_references=False)
            ),
            audit.check_input_integrity(
                _write_ii_plan(
                    tmp_path, 'p-blind',
                    phase_tokens={'5-execute': 0, '6-finalize': 5_000},
                )
            ),
        ]

        block = audit.emit_input_integrity_block(rows)

        # header + the three-bucket data_confidence tally
        assert 'check: input-integrity' in block
        assert 'status: success' in block
        assert 'plans_scanned: 3' in block
        assert 'data_confidence_fully_recorded: 1' in block
        assert 'data_confidence_partial: 1' in block
        assert 'data_confidence_blind: 1' in block

    def test_block_lists_blind_plan_ids(self, tmp_path: Path):
        # two blind plans (zero-token 5-execute) + one healthy
        rows = [
            audit.check_input_integrity(_write_ii_plan(tmp_path, 'healthy')),
            audit.check_input_integrity(
                _write_ii_plan(
                    tmp_path, 'blind-b',
                    phase_tokens={'5-execute': 0, '6-finalize': 5_000},
                )
            ),
            audit.check_input_integrity(
                _write_ii_plan(
                    tmp_path, 'blind-a',
                    phase_tokens={'5-execute': 0, '6-finalize': 5_000},
                )
            ),
        ]

        block = audit.emit_input_integrity_block(rows)

        # blind plan ids are sorted, semicolon-joined, healthy excluded
        assert 'blind_plan_ids: blind-a;blind-b' in block

    def test_block_header_declares_severity_column(self, tmp_path: Path):
        # one plan
        rows = [audit.check_input_integrity(_write_ii_plan(tmp_path, 'one'))]

        block = audit.emit_input_integrity_block(rows)

        # the rows[] header carries the full column set ending in severity, with
        # the marker-schema column between data_confidence and severity
        assert (
            'rows[1]{plan_id,has_execution,has_metrics,has_references,'
            'has_tasks,has_findings,has_script_log,metrics_blind,'
            'incomplete_lifecycle,missing_dispatch_markers,data_confidence,'
            'metrics_marker_schema,severity}:'
        ) in block

    def test_row_renders_the_marker_schema_cell(self, tmp_path: Path):
        """The emitted row carries the schema, so the floor's REASON is visible.

        Two plans differing only in marker schema render different cells — the
        block does not merely declare the column in its header.
        """
        rows = [
            audit.check_input_integrity(_write_ii_plan(tmp_path, 'sch-current')),
            audit.check_input_integrity(
                _write_ii_plan(tmp_path, 'sch-old', marker_schema='old-schema')
            ),
            audit.check_input_integrity(
                _write_ii_plan(tmp_path, 'sch-pre', marker_schema='pre-#812')
            ),
        ]

        block = audit.emit_input_integrity_block(rows)
        cells = {
            ln.strip().split(',')[0]: ln.strip().split(',')
            for ln in block.splitlines()
            if ln.strip().startswith('sch-')
        }
        assert cells['sch-current'][-2] == audit.METRICS_SCHEMA_CURRENT
        assert cells['sch-old'][-2] == audit.METRICS_SCHEMA_OLD
        assert cells['sch-pre'][-2] == audit.METRICS_SCHEMA_PRE_812

    def test_genuine_row_renders_genuine_severity_cell(self, tmp_path: Path):
        # a blind plan (zero-token 5-execute) is a genuine defect
        rows = [
            audit.check_input_integrity(
                _write_ii_plan(
                    tmp_path, 'g',
                    phase_tokens={'5-execute': 0, '6-finalize': 5_000},
                )
            )
        ]

        block = audit.emit_input_integrity_block(rows)
        row_line = next(
            ln.strip()
            for ln in block.splitlines()
            if ln.strip().startswith('g,')
        )

        # the flagged row ends on the genuine cell + count reflects it
        assert row_line.endswith(',genuine')
        assert 'genuine_signal_count: 1' in block

    def test_clean_row_renders_informational_severity_cell(self, tmp_path: Path):
        # a fully-recorded plan has no flag => informational
        rows = [audit.check_input_integrity(_write_ii_plan(tmp_path, 'i'))]

        block = audit.emit_input_integrity_block(rows)
        row_line = next(
            ln.strip()
            for ln in block.splitlines()
            if ln.strip().startswith('i,')
        )

        # clean row stamps informational, genuine count is zero
        assert row_line.endswith(',informational')
        assert 'genuine_signal_count: 0' in block

    def test_empty_corpus_yields_zero_counts(self):
        # no plans scanned
        block = audit.emit_input_integrity_block([])

        # all-zero buckets, empty blind list, zero genuine
        assert 'plans_scanned: 0' in block
        assert 'data_confidence_fully_recorded: 0' in block
        assert 'data_confidence_partial: 0' in block
        assert 'data_confidence_blind: 0' in block
        assert 'genuine_signal_count: 0' in block
