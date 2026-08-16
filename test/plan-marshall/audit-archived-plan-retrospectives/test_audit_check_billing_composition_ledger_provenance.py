#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``billing-composition`` ledger reader — the provenance gate on a literal `0`.

The four per-dispatch context-load columns of a dispatch-boundary ledger read
FOUR ways, and the fourth is decided per ROW rather than per cell: a literal `0`
is a measurement only when the row carries a post-token fingerprint that dates it
to the current writer. These pin that gate; the reconstruction and reconciliation
behaviour around it lives in
``test_audit_check_billing_composition_reconstruction.py``.
"""

from pathlib import Path

from _audit_fixtures import _EXECUTE_PHASE, audit

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
