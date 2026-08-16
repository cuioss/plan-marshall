#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ``metrics_blind`` predicate against the inline-phase carve-out — a matched
positive/negative control pair pinning that an inline phase block is not read as
metrics-blind while a genuinely absent one still is.

``metrics_blind`` reads ``total_tokens`` as the evidence a phase recorded
something. That field is population-discriminated: on a phase that dispatched
nothing, ``manage-metrics enrich`` folds the main-context sum into it and stamps
``total_tokens_population: inline``. The fold is what keeps such a phase off this
flag — the check gets its inline carve-out FROM THE RECORDER and deliberately
carries no inline branch of its own.

These tests pin that coupling from the consumer side, where removing the fold
would surface as a corpus-wide false positive. The negative control keeps the
positive one honest: a phase that genuinely recorded nothing must still flag.
"""

from pathlib import Path
from typing import Any

from _audit_fixtures import (
    _write_metrics_toon,
    audit,
)


def _integrity_inputs(plan_dir: Path) -> Any:
    return audit.PlanInputs(
        plan_id='inline-carveout',
        plan_dir=plan_dir,
        manifest_present=True,
        manifest_phase_5=[],
    )


class TestInlinePhaseIsNotMetricsBlind:
    """A zero-dispatch phase whose cost `enrich` folded in is recorded, not blind."""

    def test_inline_finalize_carrying_the_fold_is_not_flagged(self, tmp_path: Path):
        # 6-finalize ran entirely inline: no dispatched <usage>, so enrich folded
        # the main-context sum into total_tokens and labelled the row `inline`.
        _write_metrics_toon(
            tmp_path,
            {
                '5-execute': {'total_tokens': 42000},
                '6-finalize': {
                    'total_tokens': 6000,
                    'total_tokens_population': 'inline',
                    'inline_main_context_tokens': 6000,
                },
            },
        )

        row = audit.check_input_integrity(_integrity_inputs(tmp_path))

        assert row['metrics_blind'] == ''
        assert row['data_confidence'] != 'blind'

    def test_negative_control_a_genuinely_zero_phase_still_flags(self, tmp_path: Path):
        # Same plan shape, but 6-finalize recorded nothing at all — no fold, no
        # inline attribution. This MUST still flag, or the positive control above
        # would be proving nothing.
        _write_metrics_toon(
            tmp_path,
            {
                '5-execute': {'total_tokens': 42000},
                '6-finalize': {'total_tokens': 0},
            },
        )

        row = audit.check_input_integrity(_integrity_inputs(tmp_path))

        assert '6-finalize' in row['metrics_blind']

    def test_blind_execute_still_wins_the_bucket(self, tmp_path: Path):
        # The load-bearing case is untouched by the carve-out: a zero-token
        # 5-execute with no partiality marker is still `blind`.
        _write_metrics_toon(
            tmp_path,
            {
                '5-execute': {'total_tokens': 0},
                '6-finalize': {
                    'total_tokens': 6000,
                    'total_tokens_population': 'inline',
                },
            },
        )

        row = audit.check_input_integrity(_integrity_inputs(tmp_path))

        assert '5-execute' in row['metrics_blind']
        assert row['data_confidence'] == 'blind'

    def test_population_discriminator_does_not_corrupt_the_parsed_total(
        self, tmp_path: Path
    ):
        # `parse_metrics_toon` whitelists the keys it consumes, so the string-valued
        # discriminator is ignored rather than coerced into a numeric field. This
        # is what makes the new field safe for every audit consumer.
        _write_metrics_toon(
            tmp_path,
            {
                '1-init': {
                    'total_tokens': 25514,
                    'total_tokens_population': 'inline',
                    'inline_main_context_tokens': 25514,
                }
            },
        )

        phases = audit.parse_metrics_toon(tmp_path / 'work' / 'metrics.toon')

        assert [p.phase for p in phases] == ['1-init']
        assert phases[0].total_tokens == 25514
