#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``billing-composition`` reconstruction and reconciliation — the billing formula is
re-derived from the metrics store and reconciled against the dispatch-boundary
ledger.
"""

from pathlib import Path

from _audit_fixtures import (
    _EXECUTE_PHASE,
    _billing_row,
    _clean_metrics_body,
    _write_billing_plan,
    audit,
)

# The canonical nine-column dispatch-boundary ledger header
# (`data-format.md` § Per-Dispatch Context-Load Attribution).
_LEDGER_HEADER = (
    'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms,'
    'input_tokens,output_tokens,cache_read_input_tokens,'
    'cache_creation_input_tokens}:'
)

# The four appended context-load columns, in canonical order. Written as a
# literal rather than imported from the reader: the literal IS the contract
# `data-format.md` § Per-Dispatch Context-Load Attribution states, and a test
# that read the names back out of the code under test could not falsify a drift
# in them.
_CONTEXT_LOAD_COLUMNS = (
    'input_tokens',
    'output_tokens',
    'cache_read_input_tokens',
    'cache_creation_input_tokens',
)


def _ledger_body(phase: str, rows: list[tuple[int, ...]]) -> str:
    """Render a dispatch-boundary ledger carrying *rows* in canonical column order."""
    lines = ['plan_id: ledger-plan', f'phase: {phase}', _LEDGER_HEADER]
    for row in rows:
        cells = ','.join(str(cell) for cell in row)
        lines.append(f'2026-05-08T14:23:11Z,clean_exit_queue_empty,{cells}')
    return '\n'.join(lines) + '\n'


class TestBillingCompositionReconstruction:
    """The billing-formula reconstruction and its composition shares."""

    def test_reconstruction_applies_the_documented_weights(self, tmp_path: Path):
        # input + output + round(0.1 * cache_read) + round(1.25 * cache_creation)
        #   = 1000 + 500 + 20000 + 10000 = 31500.
        inputs = _write_billing_plan(
            tmp_path,
            'weights',
            _clean_metrics_body(
                input_tokens=1000,
                output_tokens=500,
                cache_read_input_tokens=200_000,
                cache_creation_input_tokens=8_000,
            ),
        )

        result = audit.cross_billing_composition([inputs])
        row = _billing_row(result, 'weights')

        assert row['billing_total'] == 31_500
        # An unweighted sum would be 209_500 — the assertion distinguishes the
        # weighted reconstruction from a raw four-field total.
        assert row['billing_total'] != 209_500

    def test_composition_shares_are_taken_over_the_reconstruction(self, tmp_path: Path):
        inputs = _write_billing_plan(
            tmp_path,
            'shares',
            _clean_metrics_body(
                input_tokens=1000,
                output_tokens=500,
                cache_read_input_tokens=200_000,
                cache_creation_input_tokens=8_000,
            ),
        )

        result = audit.cross_billing_composition([inputs])
        row = _billing_row(result, 'shares')

        # 20000/31500, 10000/31500, 500/31500.
        assert row['cache_read_share'] == '63.5%'
        assert row['cache_creation_share'] == '31.7%'
        assert row['output_share'] == '1.6%'

    def test_zero_reconstruction_reports_na_rather_than_a_fabricated_share(
        self, tmp_path: Path
    ):
        # A plan whose four-field view is present but all-zero has no denominator;
        # the share is `n/a`, never a 0% that would read as a measured composition.
        inputs = _write_billing_plan(
            tmp_path,
            'zero',
            _clean_metrics_body(
                input_tokens=0,
                output_tokens=0,
                cache_read_input_tokens=0,
                cache_creation_input_tokens=0,
            ),
        )

        result = audit.cross_billing_composition([inputs])
        row = _billing_row(result, 'zero')

        assert row['billing_total'] == 0
        assert row['cache_read_share'] == 'n/a'


class TestBillingCompositionReconciliation:
    """The same-population `max(row, ledger)` dispatch-boundary reconciliation."""

    def test_ledger_recovers_an_under_counted_row_without_summing(
        self, tmp_path: Path
    ):
        # The ledger's two dispatch rows SUM per column (4000/1000/300000/12000)
        # and the phase row is lower on every field, so the reconciled value is the
        # ledger's — recovered, not added.
        ledger = _ledger_body(
            _EXECUTE_PHASE,
            [
                (40_000, 20, 100, 2_000, 500, 150_000, 6_000),
                (44_211, 18, 312_290, 2_000, 500, 150_000, 6_000),
            ],
        )
        inputs = _write_billing_plan(
            tmp_path,
            'reconciled',
            _clean_metrics_body(
                input_tokens=1000,
                output_tokens=500,
                cache_read_input_tokens=200_000,
                cache_creation_input_tokens=8_000,
            ),
            ledgers={_EXECUTE_PHASE: ledger},
        )

        result = audit.cross_billing_composition([inputs])
        row = _billing_row(result, 'reconciled')

        # max(): 4000 + 1000 + round(0.1*300000) + round(1.25*12000)
        #      = 4000 + 1000 + 30000 + 15000 = 50000.
        assert row['billing_total'] == 50_000
        # A SUM of row + ledger would be 81500 — the number this rule exists to
        # avoid, because it double-counts every leaf recorded in both places.
        assert row['billing_total'] != 81_500
        assert row['reconciled_phases'] == _EXECUTE_PHASE
        assert result['reconciled_plans'] == 1

    def test_row_larger_than_ledger_is_left_untouched(self, tmp_path: Path):
        # The healthy case: the enrich four-field walk also covers the parent
        # turns, so the row is already the larger value and max() is a no-op —
        # `reconciled_phases` stays empty rather than naming every phase.
        ledger = _ledger_body(_EXECUTE_PHASE, [(10, 1, 1, 1, 1, 1, 1)])
        inputs = _write_billing_plan(
            tmp_path,
            'healthy',
            _clean_metrics_body(
                input_tokens=1000,
                output_tokens=500,
                cache_read_input_tokens=200_000,
                cache_creation_input_tokens=8_000,
            ),
            ledgers={_EXECUTE_PHASE: ledger},
        )

        result = audit.cross_billing_composition([inputs])
        row = _billing_row(result, 'healthy')

        assert row['billing_total'] == 31_500
        assert row['reconciled_phases'] == ''

    def test_absent_ledger_is_a_clean_no_op(self, tmp_path: Path):
        inputs = _write_billing_plan(
            tmp_path,
            'no-ledger',
            _clean_metrics_body(
                input_tokens=1000,
                output_tokens=500,
                cache_read_input_tokens=200_000,
                cache_creation_input_tokens=8_000,
            ),
        )

        result = audit.cross_billing_composition([inputs])
        row = _billing_row(result, 'no-ledger')

        assert row['billing_total'] == 31_500
        assert row['reconciled_phases'] == ''

    def test_legacy_five_column_row_reports_context_columns_unmeasured(
        self, tmp_path: Path
    ):
        # A ledger written before the four context-load columns existed keeps its
        # columns 1-5 readable; the appended columns are OMITTED from the totals
        # rather than summed as 0, and the whole row is not dropped.
        legacy = (
            'plan_id: legacy\n'
            f'phase: {_EXECUTE_PHASE}\n'
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:\n'
            '2026-05-08T14:23:11Z,clean_exit_queue_empty,999,3,10\n'
        )
        path = tmp_path / 'legacy.toon'
        path.write_text(legacy, encoding='utf-8')

        totals = audit._parse_dispatch_boundary_totals(path)

        assert totals['total_tokens'] == 999
        # ABSENT, not 0 — the legacy ledger measured no context load at all.
        assert 'input_tokens' not in totals
        assert 'cache_read_input_tokens' not in totals

    def test_unmeasured_cells_are_omitted_while_measured_zeros_are_kept(
        self, tmp_path: Path
    ):
        """The three-way cell read, at the ledger reader.

        One row measures zero on `input_tokens` and declines to measure
        `cache_read_input_tokens`. The measured zero must appear in the totals as
        `0` while the unmeasured column stays absent — collapsing the two would
        put a number no dispatch reported into the reconciliation maximum.
        """
        body = (
            'plan_id: mixed\n'
            f'phase: {_EXECUTE_PHASE}\n'
            f'{_LEDGER_HEADER}\n'
            '2026-05-08T14:23:11Z,clean_exit_queue_empty,50,1,2,0,7,unmeasured,not-an-int\n'
        )
        path = tmp_path / 'mixed.toon'
        path.write_text(body, encoding='utf-8')

        totals = audit._parse_dispatch_boundary_totals(path)

        assert totals['total_tokens'] == 50
        # A measured zero IS a measurement and is carried.
        assert totals['input_tokens'] == 0
        assert totals['output_tokens'] == 7
        # Unmeasured and unrecognised both contribute nothing and stay absent.
        assert 'cache_read_input_tokens' not in totals
        assert 'cache_creation_input_tokens' not in totals

    def test_row_below_the_legacy_column_floor_is_skipped(self, tmp_path: Path):
        malformed = (
            'plan_id: broken\n'
            f'phase: {_EXECUTE_PHASE}\n'
            f'{_LEDGER_HEADER}\n'
            '2026-05-08T14:23:11Z,clean_exit_queue_empty,5\n'
            '2026-05-08T14:24:11Z,clean_exit_queue_empty,7,1,2,3,4,5,6\n'
        )
        path = tmp_path / 'broken.toon'
        path.write_text(malformed, encoding='utf-8')

        totals = audit._parse_dispatch_boundary_totals(path)

        # Only the well-formed row contributes; the truncated one is skipped.
        assert totals['total_tokens'] == 7

    def test_absent_ledger_file_yields_no_totals(self, tmp_path: Path):
        assert audit._parse_dispatch_boundary_totals(tmp_path / 'nope.toon') == {}


# =============================================================================
# The provenance gate on a literal `0` (the fourth cell state)
# =============================================================================
#
# The pre-token writer defaulted every omitted context-load column to a literal
# `0`, so "measured zero" and "wrote 0 because it had nothing to measure" are
# byte-identical on disk. This reader dates a row by an IN-band post-token
# FINGERPRINT — an `unmeasured` token, or a nonzero context-load cell — and sums
# a `0` as a measurement only when the row carries one. The gate is the same one
# `plan-retrospective`'s `_parse_dispatch_boundary_file` applies to the same
# bytes; the two definitions of "datable" must not drift.
#
# Source of truth: `manage-metrics/standards/data-format.md` § Per-Dispatch
# Context-Load Attribution → "Provenance of a measured zero".


class TestDispatchBoundaryZeroProvenance:
    """A literal `0` sums as a measurement only in a row a fingerprint dates."""

    def _ledger(self, tmp_path: Path, name: str, rows: list[str]) -> Path:
        lines = [f'plan_id: {name}', f'phase: {_EXECUTE_PHASE}', _LEDGER_HEADER, *rows]
        path = tmp_path / f'{name}.toon'
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        return path

    def test_fingerprint_free_all_zero_ledger_omits_the_context_columns(
        self, tmp_path: Path
    ):
        """The affected case: an undatable `0` is not reported as a measured zero.

        Every row's four context-load cells are a literal `0` and nothing dates
        any of them, so the four fields are OMITTED from the totals — exactly as
        an all-`unmeasured` ledger already yields — rather than present as a
        summed `0` the reader cannot attribute to any dispatch.
        """
        path = self._ledger(
            tmp_path,
            'undatable',
            [
                '2026-05-08T14:23:11Z,clean_exit_queue_empty,100,2,1000,0,0,0,0',
                '2026-05-08T14:24:11Z,clean_exit_queue_empty,200,3,2000,0,0,0,0',
            ],
        )

        totals = audit._parse_dispatch_boundary_totals(path)

        # The legacy five columns are outside the gate and still sum.
        assert totals['total_tokens'] == 300
        for column in _CONTEXT_LOAD_COLUMNS:
            assert column not in totals, column

    def test_nonzero_fingerprint_keeps_sibling_measured_zeros(self, tmp_path: Path):
        """Negative control: a nonzero cell dates the row, so its `0`s still sum.

        The standard's row-3 example `…,9100,0,0,0` is one real measurement and
        three genuine measured zeros. A gate that marked EVERY zero undatable
        would trade this reader's false positive for a false negative, so the
        three zeros must be PRESENT as `0`.
        """
        path = self._ledger(
            tmp_path,
            'nonzero-fingerprint',
            ['2026-05-08T14:23:11Z,clean_exit_queue_empty,100,2,1000,9100,0,0,0'],
        )

        totals = audit._parse_dispatch_boundary_totals(path)

        assert totals['input_tokens'] == 9100
        assert totals['output_tokens'] == 0
        assert totals['cache_read_input_tokens'] == 0
        assert totals['cache_creation_input_tokens'] == 0

    def test_unmeasured_token_fingerprint_keeps_sibling_measured_zeros(
        self, tmp_path: Path
    ):
        """Negative control: the token dates the row without measuring anything.

        Only the current writer emits `unmeasured`, so a row carrying it was
        written by the current writer and its literal `0`s are measured zeros —
        present as `0` — while the token's own column stays absent.
        """
        path = self._ledger(
            tmp_path,
            'token-fingerprint',
            ['2026-05-08T14:23:11Z,budget_yield,100,2,1000,unmeasured,0,0,0'],
        )

        totals = audit._parse_dispatch_boundary_totals(path)

        assert 'input_tokens' not in totals
        assert totals['output_tokens'] == 0
        assert totals['cache_read_input_tokens'] == 0
        assert totals['cache_creation_input_tokens'] == 0

    def test_a_fingerprinted_row_does_not_date_its_neighbour(self, tmp_path: Path):
        """The gate is per ROW, never per file: one dated row dates only itself.

        A file-level fingerprint would let one current-writer row promote every
        other row's undatable `0` to a measurement. Here the fingerprinted row
        contributes its own measurement while the fingerprint-free row's zeros
        contribute nothing — so `output_tokens` carries 7, not 7 summed with a
        zero this reader cannot date.
        """
        path = self._ledger(
            tmp_path,
            'mixed-rows',
            [
                '2026-05-08T14:23:11Z,clean_exit_queue_empty,100,2,1000,0,0,0,0',
                '2026-05-08T14:24:11Z,clean_exit_queue_empty,200,3,2000,unmeasured,7,0,0',
            ],
        )

        totals = audit._parse_dispatch_boundary_totals(path)

        assert totals['total_tokens'] == 300
        assert totals['output_tokens'] == 7
        # Measured on the dated row, so present — and the undated row's `0`s add
        # nothing to them.
        assert totals['cache_read_input_tokens'] == 0
        assert totals['cache_creation_input_tokens'] == 0
        # Never measured on the dated row, and undatable on the other.
        assert 'input_tokens' not in totals

    def test_unrecognised_cell_is_not_a_fingerprint(self, tmp_path: Path):
        """A cell this reader could not parse dates nothing.

        An unrecognised cell is evidence about the reader, not about which writer
        wrote the row, so the row's remaining `0`s stay undatable and the field
        stays absent.
        """
        path = self._ledger(
            tmp_path,
            'unrecognised-not-fingerprint',
            ['2026-05-08T14:23:11Z,clean_exit_queue_empty,100,2,1000,0,not-an-int,0,0'],
        )

        totals = audit._parse_dispatch_boundary_totals(path)

        assert totals['total_tokens'] == 100
        for column in _CONTEXT_LOAD_COLUMNS:
            assert column not in totals, column
