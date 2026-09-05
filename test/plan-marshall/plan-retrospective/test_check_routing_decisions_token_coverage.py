# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ``execution_log`` token sum states how much of its population it READ.

The sum is already labelled with the phase population it covers. A phase filter
is not the only way it can be partial, though: the writer's token columns are
three-state, so a row whose flag the caller omitted carries the ``unmeasured``
token and contributes nothing. Summing over such rows and publishing the total
alone reconstructs the fabricated figure the token exists to prevent, one level
up from the ledger.

These tests pin the reader's own output: the per-state row counts beside the sum,
the int-parsing floor that keeps every NON-NEGATIVE numeric row summing exactly
as before, the agreement of the int and string arms about what a measured count
is — a negative is unrecognised in both, because it is the one unreadable cell
that would SUBTRACT rather than merely fail to add — the refusal to emit a delta
computed against a floor, and the refusal to emit one over an EMPTY population,
the case the floor guard cannot reach because "every in-population row was
readable" is vacuously true over zero rows.

Every positive assertion has its fully-measured, populated control beside it.
"""


from __future__ import annotations

from _check_routing_decisions_fixtures import _crd

from conftest import load_script_module

#: The population the sum claims to cover — rows outside it are excluded before
#: any state is read, which the out-of-population test below keeps honest.
IN_POPULATION_PHASE = '5-execute'


def _row(step_id: str, total_tokens: object, phase: str = IN_POPULATION_PHASE) -> dict:
    return {'step_id': step_id, 'phase': phase, 'total_tokens': total_tokens}


def _manifest(*rows: dict) -> dict:
    return {'execution_log': list(rows)}


class TestSumCoverageIsPublished:
    """Every sum carries the per-state row counts it was taken over."""

    def test_a_fully_measured_population_reports_no_gap(self):
        """The control: without it, a reader that reported everything unmeasured passes."""
        coverage = _crd.summarize_execution_log_tokens(
            _manifest(_row('a', 40_000), _row('b', 60_000))
        )

        assert coverage['total_tokens'] == 100_000
        assert coverage['rows_in_population'] == 2
        assert coverage['rows_measured'] == 2
        assert coverage['rows_unmeasured'] == 0
        assert coverage['rows_unrecognised'] == 0

    def test_an_unmeasured_row_is_counted_not_summed(self):
        coverage = _crd.summarize_execution_log_tokens(
            _manifest(_row('a', 40_000), _row('b', _crd.UNMEASURED_COLUMN_TOKEN))
        )

        assert coverage['total_tokens'] == 40_000
        assert coverage['rows_measured'] == 1
        assert coverage['rows_unmeasured'] == 1
        assert coverage['rows_unrecognised'] == 0

    def test_a_measured_zero_counts_as_measured(self):
        """⛔ The distinction the whole contract turns on, asserted at this reader."""
        coverage = _crd.summarize_execution_log_tokens(_manifest(_row('a', 0)))

        assert coverage['rows_measured'] == 1
        assert coverage['rows_unmeasured'] == 0

    def test_an_unreadable_cell_is_unrecognised_not_unmeasured(self):
        coverage = _crd.summarize_execution_log_tokens(_manifest(_row('a', '12x')))

        assert coverage['rows_unrecognised'] == 1
        assert coverage['rows_unmeasured'] == 0

    def test_the_state_counts_partition_the_population(self):
        coverage = _crd.summarize_execution_log_tokens(
            _manifest(
                _row('a', 5),
                _row('b', _crd.UNMEASURED_COLUMN_TOKEN),
                _row('c', '12x'),
                _row('d', 7, phase='1-init'),
            )
        )

        assert coverage['rows_in_population'] == 3
        assert (
            coverage['rows_measured']
            + coverage['rows_unmeasured']
            + coverage['rows_unrecognised']
            == coverage['rows_in_population']
        )

    def test_the_int_parsing_floor_still_reads_a_digit_string(self):
        """Historical all-numeric rows parse and sum exactly as before."""
        coverage = _crd.summarize_execution_log_tokens(_manifest(_row('a', '12000')))

        assert coverage['total_tokens'] == 12_000
        assert coverage['rows_measured'] == 1


class TestCostPreviewRefusesADeltaAgainstAFloor:
    """A populations-match delta is emitted only when the sum covered its population."""

    _METADATA = {
        'execution_profile_cost_preview': '50000',
        'execution_profile_cost_preview_population': _crd.EXECUTION_LOG_POPULATION,
    }

    def test_a_fully_measured_sum_still_computes_the_delta(self):
        """The control — the refusal must not fire on a complete measurement."""
        preview = _crd.evaluate_cost_preview(_manifest(_row('a', 60_000)), self._METADATA)

        assert preview['comparison'] == _crd.COMPARISON_COMPUTED
        assert preview['delta_tokens'] == 10_000

    def test_an_unmeasured_row_refuses_the_delta(self):
        preview = _crd.evaluate_cost_preview(
            _manifest(_row('a', 60_000), _row('b', _crd.UNMEASURED_COLUMN_TOKEN)),
            self._METADATA,
        )

        assert preview['comparison'] == _crd.COMPARISON_REFUSED
        assert 'incomplete_measurement' in preview['comparison_reason']
        assert 'delta_tokens' not in preview

    def test_the_preview_publishes_the_coverage_either_way(self):
        preview = _crd.evaluate_cost_preview(
            _manifest(_row('a', 60_000), _row('b', _crd.UNMEASURED_COLUMN_TOKEN)),
            self._METADATA,
        )

        assert preview['execution_log_rows_in_population'] == 2
        assert preview['execution_log_rows_measured'] == 1
        assert preview['execution_log_rows_unmeasured'] == 1
        assert preview['execution_log_rows_unrecognised'] == 0


class TestCostPreviewRefusesOverAnEmptyPopulation:
    """The coverage gate cannot fire over zero rows, so the SIZE gate must.

    ``rows_unmeasured + rows_unrecognised`` is ``0`` over an empty population, so
    "every in-population row was readable" is VACUOUSLY true and the
    ``incomplete_measurement`` refusal above cannot reach this state. The
    fall-through emitted ``delta_tokens = 0 - predicted`` under
    ``COMPARISON_COMPUTED`` — a confident delta against a fabricated zero, fed to
    the ``cost_size_token_table`` recalibration loop.

    Every assertion here has its populated control beside it, because a reader
    that refused unconditionally would satisfy the positive half alone.
    """

    _METADATA = {
        'execution_profile_cost_preview': '50000',
        'execution_profile_cost_preview_population': _crd.EXECUTION_LOG_POPULATION,
    }

    def test_a_manifest_with_no_execution_log_key_refuses(self):
        """The composed-but-unrun manifest — the reported shape."""
        preview = _crd.evaluate_cost_preview({}, self._METADATA)

        assert preview['comparison'] == _crd.COMPARISON_REFUSED
        assert 'empty_population' in preview['comparison_reason']
        assert 'delta_tokens' not in preview
        assert 'delta_pct' not in preview

    def test_an_empty_execution_log_list_refuses(self):
        preview = _crd.evaluate_cost_preview(_manifest(), self._METADATA)

        assert preview['comparison'] == _crd.COMPARISON_REFUSED
        assert 'empty_population' in preview['comparison_reason']

    def test_rows_only_outside_the_population_refuse(self):
        """Rows exist, but none in the population the sum names."""
        preview = _crd.evaluate_cost_preview(
            _manifest(_row('a', 60_000, phase='1-init')), self._METADATA
        )

        assert preview['comparison'] == _crd.COMPARISON_REFUSED
        assert 'empty_population' in preview['comparison_reason']

    def test_the_refusal_publishes_the_population_size_it_keyed_on(self):
        """The zero is legible as an empty population, not as a measured total."""
        preview = _crd.evaluate_cost_preview({}, self._METADATA)

        assert preview['execution_log_rows_in_population'] == 0
        assert preview['execution_log_tokens'] == 0
        assert str(preview['execution_log_rows_in_population']) in preview['comparison_reason']

    def test_one_measured_row_is_enough_to_compute(self):
        """The control — the size gate must not fire on a populated measurement."""
        preview = _crd.evaluate_cost_preview(_manifest(_row('a', 60_000)), self._METADATA)

        assert preview['comparison'] == _crd.COMPARISON_COMPUTED
        assert preview['delta_tokens'] == 10_000

    def test_an_empty_population_still_refuses_before_the_coverage_reason(self):
        """Ordering control: the empty case names its OWN reason, not the floor's.

        Collapsing it into ``incomplete_measurement`` would tell a reader the sum
        could not read some of its rows, when the truth is that there were none.
        """
        preview = _crd.evaluate_cost_preview({}, self._METADATA)

        assert 'incomplete_measurement' not in preview['comparison_reason']

    def test_a_population_mismatch_still_wins_over_an_empty_population(self):
        """The scope gate is the outer one and keeps its own reason."""
        preview = _crd.evaluate_cost_preview(
            {},
            {
                'execution_profile_cost_preview': '50000',
                'execution_profile_cost_preview_population': '6-finalize',
            },
        )

        assert preview['comparison'] == _crd.COMPARISON_REFUSED
        assert 'population_mismatch' in preview['comparison_reason']

    def test_no_prediction_over_an_empty_population_is_still_not_attempted(self):
        """The prediction gate is outermost — an absent prediction is not a refusal."""
        preview = _crd.evaluate_cost_preview({}, {})

        assert preview['comparison'] == _crd.COMPARISON_NOT_ATTEMPTED


class TestAPaddedNumericTokenIsMeasured:
    """Whitespace around a numeric cell must not silently drop its count.

    The reader stripped for the ``unmeasured`` comparison but not for the digit
    test, so `' 12000'` matched neither arm and fell to UNRECOGNISED — an
    under-count wearing the shape of an unreadable cell. That is the
    measured-vs-unmeasured conflation this module exists to REPORT, committed by
    the reporter itself.
    """

    def test_a_padded_numeric_cell_counts_toward_the_sum(self):
        coverage = _crd.summarize_execution_log_tokens(_manifest(_row('a', ' 12000 ')))

        assert coverage['rows_measured'] == 1
        assert coverage['rows_unrecognised'] == 0
        assert coverage['total_tokens'] == 12_000

    def test_a_padded_unmeasured_token_still_reads_as_unmeasured(self):
        """The adjacent arm, pinned so a future edit cannot fix one and break it."""
        padded = f'  {_crd.UNMEASURED_COLUMN_TOKEN}  '

        coverage = _crd.summarize_execution_log_tokens(_manifest(_row('a', padded)))

        assert coverage['rows_unmeasured'] == 1
        assert coverage['rows_measured'] == 0

    def test_a_genuinely_unreadable_cell_is_still_unrecognised(self):
        """The negative control — stripping must not widen what counts as measured."""
        coverage = _crd.summarize_execution_log_tokens(_manifest(_row('a', ' 12x ')))

        assert coverage['rows_unrecognised'] == 1
        assert coverage['rows_measured'] == 0
        assert coverage['total_tokens'] == 0


class TestANonDecimalDigitCellIsUnrecognisedNotAnException:
    """⛔ ``str.isdigit()`` and ``int()`` do not admit the same set.

    ``'²'`` is a digit CHARACTER but not a DECIMAL one: ``str.isdigit()`` returns
    True and ``int()`` then raises ``ValueError``. The reader tested one and
    parsed with the other, so a single corrupt cell took the whole cost preview
    down instead of being counted ``rows_unrecognised`` — the state this reader
    publishes precisely so an unreadable cell is REPORTED rather than fatal. A
    row carrying one reaches here through ``cmd_run``, so the path is live.

    Each case has its readable control beside it, because a predicate that
    rejected every string would satisfy the positive half alone.
    """

    def test_a_superscript_digit_is_unrecognised(self):
        coverage = _crd.summarize_execution_log_tokens(_manifest(_row('a', '²')))

        assert coverage['rows_unrecognised'] == 1
        assert coverage['rows_measured'] == 0
        assert coverage['total_tokens'] == 0

    def test_a_non_ascii_decimal_is_unrecognised(self):
        """``int('٣')`` SUCCEEDS — so this one is a classification call, not a crash.

        A token count nobody wrote in ASCII is an unreadable cell rather than a
        term of the sum; admitting it would put a number the writer never
        produced into a published total.
        """
        coverage = _crd.summarize_execution_log_tokens(_manifest(_row('a', '٣')))

        assert coverage['rows_unrecognised'] == 1
        assert coverage['rows_measured'] == 0

    def test_a_corrupt_cell_does_not_stop_the_rest_of_the_population(self):
        """The consequence: the readable rows still sum, and the gap is published."""
        coverage = _crd.summarize_execution_log_tokens(
            _manifest(_row('a', 40_000), _row('b', '²'))
        )

        assert coverage['total_tokens'] == 40_000
        assert coverage['rows_in_population'] == 2
        assert coverage['rows_measured'] == 1
        assert coverage['rows_unrecognised'] == 1

    def test_an_ascii_digit_string_is_still_measured(self):
        """The control — the ASCII bound must not reject the normal cell."""
        coverage = _crd.summarize_execution_log_tokens(_manifest(_row('a', '12000')))

        assert coverage['rows_measured'] == 1
        assert coverage['total_tokens'] == 12_000


class TestANegativeCountIsUnrecognisedInBothArms:
    """⛔ The two arms must classify the same number the same way.

    ``is_ascii_digits`` refuses the string ``'-1'`` while the int arm tested
    nothing, so ONE value in two encodings landed in two different states — the
    reader disagreeing with itself about what a measured count is.

    A negative is also the only unreadable cell that MOVES the sum. Every other
    one merely fails to add; this one subtracts, pulling the published figure
    below the floor the coverage counts promise it is, and feeding a delta
    computed from invalid evidence into the cost comparison.

    The controls are carried inline — a readable row beside the negative, and
    the ``0`` boundary beside ``-1`` — because a guard that rejected every int
    would satisfy the positive half alone.
    """

    def test_a_negative_int_is_unrecognised(self):
        coverage = _crd.summarize_execution_log_tokens(_manifest(_row('a', -1)))

        assert coverage['rows_unrecognised'] == 1
        assert coverage['rows_measured'] == 0
        assert coverage['total_tokens'] == 0

    def test_a_negative_digit_string_is_unrecognised(self):
        """The adjacent arm, pinned so a future edit cannot move one and not the other."""
        coverage = _crd.summarize_execution_log_tokens(_manifest(_row('a', '-1')))

        assert coverage['rows_unrecognised'] == 1
        assert coverage['rows_measured'] == 0

    def test_a_negative_does_not_subtract_from_a_readable_population(self):
        """The consequence: the readable rows sum intact and the gap is published."""
        coverage = _crd.summarize_execution_log_tokens(
            _manifest(_row('a', 40_000), _row('b', -1))
        )

        assert coverage['total_tokens'] == 40_000
        assert coverage['rows_in_population'] == 2
        assert coverage['rows_measured'] == 1
        assert coverage['rows_unrecognised'] == 1

    def test_zero_and_minus_one_split_at_the_guard_boundary(self):
        """The boundary is ``>= 0``, so a measured ``0`` stays measured beside ``-1``."""
        coverage = _crd.summarize_execution_log_tokens(_manifest(_row('a', 0), _row('b', -1)))

        assert coverage['rows_measured'] == 1
        assert coverage['rows_unrecognised'] == 1
        assert coverage['total_tokens'] == 0


def test_unmeasured_token_matches_writer():
    """The mirrored literal agrees with the manifest writer's own definition.

    This script runs in a different process from ``manage-execution-manifest`` and
    cannot import its private module, so the token is a hand-mirror — the same
    shape ``EXECUTION_LOG_PHASES`` already uses beside it. Without this check the
    two could drift, and every unmeasured row would then be counted as
    unrecognised instead.
    """
    core = load_script_module(
        'plan-marshall',
        'manage-execution-manifest',
        '_manifest_core.py',
        module_name='_mem_core_crd_token_drift',
    )

    assert _crd.UNMEASURED_COLUMN_TOKEN == core.UNMEASURED_COLUMN_TOKEN
