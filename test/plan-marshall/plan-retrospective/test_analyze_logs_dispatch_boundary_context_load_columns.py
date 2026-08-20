# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``analyze-logs.py``.

Scope: reading the four context-load columns off a dispatch-boundary row, holding
absent, unmeasured, unrecognised and measured-zero apart across both the legacy
five-column and the widened nine-column shapes.
"""


from __future__ import annotations

from pathlib import Path

from _analyze_logs_fixtures import _analyze_logs

# =============================================================================
# Per-dispatch context-load columns in the dispatch-boundary reader
# =============================================================================
#
# The dispatch-boundary row carries nine columns (legacy five + input_tokens,
# output_tokens, cache_read_input_tokens, cache_creation_input_tokens appended at
# the END). ``_parse_dispatch_boundary_file`` uses a ``len(parts) >= 5`` floor so
# a legacy five-column row still parses.
#
# The four context-load columns read FOUR ways, never two:
#   * an integer            → MEASURED (with the zero gate below). The key
#                             carries the int.
#   * the `unmeasured` token, or a column a short row does not have
#                           → UNMEASURED. The key is OMITTED and the column is
#                             named in the row's `unmeasured_columns`.
#   * anything else         → UNRECOGNISED. The key is omitted too, and the
#                             column is named in `unrecognised_columns` — a
#                             different fact from unmeasured.
#   * a literal 0 the reader cannot date → INDETERMINATE. "Measured zero" and
#                             the pre-token writer's "wrote 0 because it had
#                             nothing" are byte-identical, so a `0` is measured
#                             only when the row carries a post-token FINGERPRINT
#                             (an `unmeasured` token or a nonzero context-load
#                             cell); otherwise the key is OMITTED and the column
#                             is named in `indeterminate_columns`.
#
# The canonical column order/count/unmeasured representation are owned by
# manage-metrics ``standards/data-format.md`` (Per-Dispatch Context-Load
# Attribution section); this reader consumes that contract.


class TestDispatchBoundaryContextLoadColumns:
    """``_parse_dispatch_boundary_file`` ingests the four context-load columns."""

    _CTX_HEADER = (
        'timestamp,termination_cause,total_tokens,tool_uses,duration_ms,'
        'input_tokens,output_tokens,cache_read_input_tokens,cache_creation_input_tokens'
    )
    _LEGACY_HEADER = 'timestamp,termination_cause,total_tokens,tool_uses,duration_ms'

    def _write_boundary(self, plan_dir: Path, phase: str, header_cols: str, rows: list[str]) -> Path:
        """Write a metrics-dispatch-boundaries-{phase}.toon artifact and return its path."""
        work = plan_dir / 'work'
        work.mkdir(parents=True, exist_ok=True)
        lines = [f'plan_id: {plan_dir.name}', f'phase: {phase}', f'rows[]{{{header_cols}}}:']
        lines.extend(rows)
        path = work / f'metrics-dispatch-boundaries-{phase}.toon'
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        return path

    def test_nine_column_row_surfaces_four_context_load_values(self, tmp_path):
        """A widened nine-column row exposes the four context-load values and
        leaves the legacy five columns unchanged."""
        plan_dir = tmp_path / 'plans' / 'ctx-nine'
        plan_dir.mkdir(parents=True)
        path = self._write_boundary(
            plan_dir,
            '5-execute',
            self._CTX_HEADER,
            ['2026-05-08T14:00:00Z,clean_exit_queue_empty,84211,38,412390,38000,4000,210000,12000'],
        )

        result = _analyze_logs._parse_dispatch_boundary_file(path)

        assert result['present'] is True
        assert len(result['rows']) == 1
        row = result['rows'][0]
        # Legacy five columns parse unchanged.
        assert row['timestamp'] == '2026-05-08T14:00:00Z'
        assert row['termination_cause'] == 'clean_exit_queue_empty'
        assert row['total_tokens'] == 84211
        assert row['tool_uses'] == 38
        assert row['duration_ms'] == 412390
        # The four appended context-load columns surface, and the row declares
        # that nothing on it was unmeasured or unrecognised.
        assert row['input_tokens'] == 38000
        assert row['output_tokens'] == 4000
        assert row['cache_read_input_tokens'] == 210000
        assert row['cache_creation_input_tokens'] == 12000
        assert row['unmeasured_columns'] == []
        assert row['unrecognised_columns'] == []

    def test_all_zero_no_fingerprint_row_reads_indeterminate(self, tmp_path):
        """The affected case (D0/D2): an all-zero row with NO post-token
        fingerprint cannot be dated, so its four `0`s read as INDETERMINATE.

        This is the pre-token writer's row shape: it defaulted every omitted
        context-load column to a literal `0`, so `…,0,0,0,0` is byte-identical to
        a genuine all-four-measured-zero row and cannot be dated. The honest
        reading is neither measured (a false positive) nor unmeasured (asserting
        a statement the writer never made) — it is the fourth state.

        RED against pre-fix code, which read every literal `0` as a measured
        zero (`input_tokens == 0`, `unmeasured_columns == []`, and no
        `indeterminate_columns` key at all).
        """
        plan_dir = tmp_path / 'plans' / 'ctx-all-zero'
        plan_dir.mkdir(parents=True)
        path = self._write_boundary(
            plan_dir,
            '5-execute',
            self._CTX_HEADER,
            ['2026-05-08T14:00:00Z,clean_exit_queue_empty,100,2,1000,0,0,0,0'],
        )

        result = _analyze_logs._parse_dispatch_boundary_file(path)

        row = result['rows'][0]
        # An indeterminate `0` is NOT carried as a measured value.
        for column in (
            'input_tokens',
            'output_tokens',
            'cache_read_input_tokens',
            'cache_creation_input_tokens',
        ):
            assert column not in row, column
        assert row['indeterminate_columns'] == [
            'input_tokens',
            'output_tokens',
            'cache_read_input_tokens',
            'cache_creation_input_tokens',
        ]
        # Not folded into either neighbour — the writer made no statement, and
        # the reader parsed the cells fine.
        assert row['unmeasured_columns'] == []
        assert row['unrecognised_columns'] == []

    def test_nonzero_fingerprint_keeps_measured_zeros_measured(self, tmp_path):
        """Negative control (D4, direction 1): a genuine post-token measured zero
        must STILL read as measured.

        A nonzero context-load cell dates the row to the current writer
        ("nothing to measure" never yields a nonzero), so the row's other `0`s
        are genuine measured zeros — the standards row-3 example `…,9100,0,0,0`.
        A fix that marked EVERY zero indeterminate would fail here, trading the
        false positive for a false negative.

        RED against pre-fix code, which emitted no `indeterminate_columns` key.
        """
        plan_dir = tmp_path / 'plans' / 'ctx-nonzero-fingerprint'
        plan_dir.mkdir(parents=True)
        path = self._write_boundary(
            plan_dir,
            '5-execute',
            self._CTX_HEADER,
            ['2026-05-08T14:00:00Z,clean_exit_queue_empty,100,2,1000,9100,0,0,0'],
        )

        result = _analyze_logs._parse_dispatch_boundary_file(path)

        row = result['rows'][0]
        assert row['input_tokens'] == 9100
        # The three measured zeros survive as measured zeros — the nonzero dated
        # the whole row.
        assert row['output_tokens'] == 0
        assert row['cache_read_input_tokens'] == 0
        assert row['cache_creation_input_tokens'] == 0
        assert row['unmeasured_columns'] == []
        assert row['unrecognised_columns'] == []
        # Present and EMPTY — never collapsed to absent (D4, direction 2).
        assert 'indeterminate_columns' in row
        assert row['indeterminate_columns'] == []

    def test_unmeasured_token_fingerprint_keeps_measured_zeros_measured(self, tmp_path):
        """Negative control (D4, direction 1): the `unmeasured` token also dates
        the row, so its sibling `0`s stay measured.

        Only the current writer emits the token, so a row carrying it was
        written by the current writer and its literal `0`s are measured — even
        though the row's other column was deliberately not measured.

        RED against pre-fix code, which emitted no `indeterminate_columns` key.
        """
        plan_dir = tmp_path / 'plans' / 'ctx-token-fingerprint'
        plan_dir.mkdir(parents=True)
        path = self._write_boundary(
            plan_dir,
            '5-execute',
            self._CTX_HEADER,
            ['2026-05-08T14:00:00Z,budget_yield,100,2,1000,unmeasured,0,0,0'],
        )

        result = _analyze_logs._parse_dispatch_boundary_file(path)

        row = result['rows'][0]
        assert 'input_tokens' not in row
        assert row['output_tokens'] == 0
        assert row['cache_read_input_tokens'] == 0
        assert row['cache_creation_input_tokens'] == 0
        assert row['unmeasured_columns'] == ['input_tokens']
        assert row['unrecognised_columns'] == []
        assert row['indeterminate_columns'] == []

    def test_indeterminate_columns_present_empty_on_legacy_row(self, tmp_path):
        """The opposite collapse (D4, direction 2): a row with NO indeterminate
        columns still emits `indeterminate_columns` as a PRESENT, empty list —
        never collapsed to absent.

        A legacy five-column row has no context-load cells at all, so it has
        nothing indeterminate; the key must still be present-and-empty so a
        consumer can tell "measured no indeterminate columns" from "this reader
        predates the fourth state".

        RED against pre-fix code, which had no `indeterminate_columns` key.
        """
        plan_dir = tmp_path / 'plans' / 'ctx-legacy-empty'
        plan_dir.mkdir(parents=True)
        path = self._write_boundary(
            plan_dir,
            '5-execute',
            self._LEGACY_HEADER,
            ['2026-05-08T14:00:00Z,unknown,100,2,1000'],
        )

        result = _analyze_logs._parse_dispatch_boundary_file(path)

        row = result['rows'][0]
        assert 'indeterminate_columns' in row
        assert row['indeterminate_columns'] == []
        # A legacy row's four columns are UNMEASURED, not indeterminate: absence
        # of the column is a different fact from an undatable literal zero.
        assert row['unmeasured_columns'] == [
            'input_tokens',
            'output_tokens',
            'cache_read_input_tokens',
            'cache_creation_input_tokens',
        ]

    def test_indeterminate_zero_coexists_with_unrecognised_cell(self, tmp_path):
        """A fingerprint-free row mixing `0`s with a corrupt cell splits cleanly:
        the `0`s are indeterminate, the corrupt cell is unrecognised.

        An unrecognised cell is NOT a fingerprint — the reader could not parse
        it, so it dates nothing — so the row's undatable `0`s stay indeterminate
        rather than being promoted to measured.
        """
        plan_dir = tmp_path / 'plans' / 'ctx-indeterminate-plus-unrecognised'
        plan_dir.mkdir(parents=True)
        path = self._write_boundary(
            plan_dir,
            '5-execute',
            self._CTX_HEADER,
            ['2026-05-08T14:00:00Z,clean_exit_queue_empty,100,2,1000,0,not-an-int,0,0'],
        )

        result = _analyze_logs._parse_dispatch_boundary_file(path)

        row = result['rows'][0]
        for column in (
            'input_tokens',
            'output_tokens',
            'cache_read_input_tokens',
            'cache_creation_input_tokens',
        ):
            assert column not in row, column
        assert row['indeterminate_columns'] == [
            'input_tokens',
            'cache_read_input_tokens',
            'cache_creation_input_tokens',
        ]
        assert row['unrecognised_columns'] == ['output_tokens']
        assert row['unmeasured_columns'] == []

    def test_unmeasured_token_reads_as_absent_not_zero(self, tmp_path):
        """The `unmeasured` literal omits the key and names the column.

        This is the distinction the token exists for: contrast with
        ``test_nonzero_fingerprint_keeps_measured_zeros_measured`` above, whose
        row carries genuinely measured `0` cells and yields `input_tokens == 0`.
        Collapsing the two would make "the caller measured nothing"
        indistinguishable from "the dispatch loaded nothing".
        """
        plan_dir = tmp_path / 'plans' / 'ctx-unmeasured'
        plan_dir.mkdir(parents=True)
        path = self._write_boundary(
            plan_dir,
            '5-execute',
            self._CTX_HEADER,
            [
                '2026-05-08T14:00:00Z,budget_yield,100,2,1000,'
                'unmeasured,unmeasured,unmeasured,unmeasured'
            ],
        )

        result = _analyze_logs._parse_dispatch_boundary_file(path)

        row = result['rows'][0]
        # Legacy five still parse.
        assert row['total_tokens'] == 100
        for column in (
            'input_tokens',
            'output_tokens',
            'cache_read_input_tokens',
            'cache_creation_input_tokens',
        ):
            assert column not in row, column
        assert row['unmeasured_columns'] == [
            'input_tokens',
            'output_tokens',
            'cache_read_input_tokens',
            'cache_creation_input_tokens',
        ]
        assert row['unrecognised_columns'] == []

    def test_per_column_mix_of_measured_and_unmeasured(self, tmp_path):
        """Measured, unmeasured and unrecognised are decided per COLUMN.

        One measured cell does not make its neighbours measured, and one
        unmeasured cell does not discard the measured ones beside it.

        These three verdicts are per-column because none of them depends on the
        rest of the row. The reader's FOURTH verdict — ``indeterminate``, for a
        literal ``0`` on a row carrying no post-token fingerprint — is decided
        per ROW, since the bytes for a measured zero and an undated one are
        identical and only the whole row can date them. This row carries a
        nonzero cell, so its zeros are measured; the per-row half is covered by
        the provenance tests.
        """
        plan_dir = tmp_path / 'plans' / 'ctx-column-mix'
        plan_dir.mkdir(parents=True)
        path = self._write_boundary(
            plan_dir,
            '5-execute',
            self._CTX_HEADER,
            ['2026-05-08T14:00:00Z,clean_exit_queue_empty,100,2,1000,50,unmeasured,0,unmeasured'],
        )

        result = _analyze_logs._parse_dispatch_boundary_file(path)

        row = result['rows'][0]
        assert row['input_tokens'] == 50
        assert row['cache_read_input_tokens'] == 0
        assert 'output_tokens' not in row
        assert 'cache_creation_input_tokens' not in row
        assert row['unmeasured_columns'] == ['output_tokens', 'cache_creation_input_tokens']
        assert row['unrecognised_columns'] == []

    def test_legacy_five_column_row_reads_context_load_as_unmeasured(self, tmp_path):
        """A legacy five-column row still parses; its four context-load columns
        read as UNMEASURED — absent, never a measured 0.

        A row written before the columns existed recorded no context-load
        measurement at all, so `0` would assert a measurement it never took. The
        `len(parts) >= 5` legacy floor is preserved: the row is kept, not dropped.
        """
        plan_dir = tmp_path / 'plans' / 'ctx-legacy'
        plan_dir.mkdir(parents=True)
        path = self._write_boundary(
            plan_dir,
            '5-execute',
            self._LEGACY_HEADER,
            ['2026-05-08T14:00:00Z,voluntary_checkpoint,100,2,1000'],
        )

        result = _analyze_logs._parse_dispatch_boundary_file(path)

        assert result['present'] is True
        assert len(result['rows']) == 1
        row = result['rows'][0]
        # Legacy five columns unchanged.
        assert row['termination_cause'] == 'voluntary_checkpoint'
        assert row['total_tokens'] == 100
        assert row['tool_uses'] == 2
        assert row['duration_ms'] == 1000
        # The four context-load columns are ABSENT, and named as unmeasured.
        for column in (
            'input_tokens',
            'output_tokens',
            'cache_read_input_tokens',
            'cache_creation_input_tokens',
        ):
            assert column not in row, column
        assert row['unmeasured_columns'] == [
            'input_tokens',
            'output_tokens',
            'cache_read_input_tokens',
            'cache_creation_input_tokens',
        ]
        assert row['unrecognised_columns'] == []

    def test_mixed_legacy_and_widened_rows_each_parse(self, tmp_path):
        """A file mixing a legacy five-column row and a widened nine-column row
        parses both — neither is dropped by the floor guard."""
        plan_dir = tmp_path / 'plans' / 'ctx-mixed'
        plan_dir.mkdir(parents=True)
        path = self._write_boundary(
            plan_dir,
            '5-execute',
            self._CTX_HEADER,
            [
                # Legacy five-column row (written before the columns existed).
                '2026-05-08T14:00:00Z,voluntary_checkpoint,100,2,1000',
                # Widened nine-column row.
                '2026-05-08T14:01:00Z,clean_exit_queue_empty,200,4,2000,50,10,3000,90',
            ],
        )

        result = _analyze_logs._parse_dispatch_boundary_file(path)

        assert len(result['rows']) == 2
        legacy_row, widened_row = result['rows']
        # Legacy row → context columns absent, reported unmeasured.
        assert legacy_row['total_tokens'] == 100
        assert 'input_tokens' not in legacy_row
        assert 'cache_creation_input_tokens' not in legacy_row
        assert len(legacy_row['unmeasured_columns']) == 4
        # Widened row → context columns surface.
        assert widened_row['total_tokens'] == 200
        assert widened_row['input_tokens'] == 50
        assert widened_row['output_tokens'] == 10
        assert widened_row['cache_read_input_tokens'] == 3000
        assert widened_row['cache_creation_input_tokens'] == 90
        assert widened_row['unmeasured_columns'] == []

    def test_malformed_appended_field_reads_as_unrecognised(self, tmp_path):
        """A non-numeric, non-token appended field reads as UNRECOGNISED.

        Distinct from unmeasured: the writer made a statement this reader failed
        to parse, rather than deliberately declining to measure. The whole row is
        still kept and the legacy five still parse.
        """
        plan_dir = tmp_path / 'plans' / 'ctx-malformed'
        plan_dir.mkdir(parents=True)
        path = self._write_boundary(
            plan_dir,
            '5-execute',
            self._CTX_HEADER,
            ['2026-05-08T14:00:00Z,error,1,2,3,xx,yy,zz,ww'],
        )

        result = _analyze_logs._parse_dispatch_boundary_file(path)

        assert len(result['rows']) == 1
        row = result['rows'][0]
        # Legacy five columns still parse.
        assert row['termination_cause'] == 'error'
        assert row['total_tokens'] == 1
        assert row['tool_uses'] == 2
        assert row['duration_ms'] == 3
        # All four are unrecognised — and NOT folded into unmeasured.
        for column in (
            'input_tokens',
            'output_tokens',
            'cache_read_input_tokens',
            'cache_creation_input_tokens',
        ):
            assert column not in row, column
        assert row['unrecognised_columns'] == [
            'input_tokens',
            'output_tokens',
            'cache_read_input_tokens',
            'cache_creation_input_tokens',
        ]
        assert row['unmeasured_columns'] == []

    def test_unmeasured_and_unrecognised_are_reported_separately(self, tmp_path):
        """One row can carry both, and they land in different lists.

        The failure this rules out is a reader that lumps every non-integer cell
        into one bucket — which would make a corrupt cell read as a deliberate
        abstention.
        """
        plan_dir = tmp_path / 'plans' / 'ctx-both'
        plan_dir.mkdir(parents=True)
        path = self._write_boundary(
            plan_dir,
            '5-execute',
            self._CTX_HEADER,
            ['2026-05-08T14:00:00Z,error,1,2,3,unmeasured,yy,7,unmeasured'],
        )

        result = _analyze_logs._parse_dispatch_boundary_file(path)

        row = result['rows'][0]
        assert row['cache_read_input_tokens'] == 7
        assert row['unmeasured_columns'] == ['input_tokens', 'cache_creation_input_tokens']
        assert row['unrecognised_columns'] == ['output_tokens']

    def test_truncated_appended_fields_read_as_unmeasured(self, tmp_path):
        """A row with only some appended cells reports the missing ones unmeasured.

        The present cells are still MEASURED — the old all-or-nothing except
        block discarded them along with the missing ones.
        """
        plan_dir = tmp_path / 'plans' / 'ctx-truncated'
        plan_dir.mkdir(parents=True)
        path = self._write_boundary(
            plan_dir,
            '5-execute',
            self._CTX_HEADER,
            # Seven columns: legacy five + input_tokens + output_tokens only.
            ['2026-05-08T14:00:00Z,clean_exit_queue_empty,100,2,1000,7,8'],
        )

        result = _analyze_logs._parse_dispatch_boundary_file(path)

        assert len(result['rows']) == 1
        row = result['rows'][0]
        # Legacy five parse, and the two cells the row DOES carry are measured.
        assert row['total_tokens'] == 100
        assert row['input_tokens'] == 7
        assert row['output_tokens'] == 8
        # Only the two the row lacks read as unmeasured.
        assert 'cache_read_input_tokens' not in row
        assert 'cache_creation_input_tokens' not in row
        assert row['unmeasured_columns'] == [
            'cache_read_input_tokens',
            'cache_creation_input_tokens',
        ]
        assert row['unrecognised_columns'] == []

    def test_read_per_phase_carries_context_load_columns(self, tmp_path):
        """``read_dispatch_boundaries_per_phase`` surfaces the four context-load
        keys end-to-end via the glob reader."""
        plan_dir = tmp_path / 'plans' / 'ctx-per-phase'
        path = self._write_boundary(
            plan_dir,
            '5-execute',
            self._CTX_HEADER,
            ['2026-05-08T14:00:00Z,clean_exit_queue_empty,200,4,2000,50,10,3000,90'],
        )
        assert path.exists()

        result = _analyze_logs.read_dispatch_boundaries_per_phase(plan_dir)

        assert set(result.keys()) == {'5-execute'}
        row = result['5-execute']['rows'][0]
        assert row['input_tokens'] == 50
        assert row['output_tokens'] == 10
        assert row['cache_read_input_tokens'] == 3000
        assert row['cache_creation_input_tokens'] == 90
        # The two disclosure lists survive the glob reader unchanged.
        assert row['unmeasured_columns'] == []
        assert row['unrecognised_columns'] == []
