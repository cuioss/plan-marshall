#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script.

Covers: start-phase, end-phase, generate, enrich, accumulate-agent-usage subcommands.

Tier 2 (direct import) tests for cmd_* functions, with 2 subprocess
tests retained for CLI plumbing verification.
"""


import pytest
from _manage_metrics_fixtures import (
    ns_enrich,
    ns_generate,
)
from _manage_metrics_module_fixtures import (
    _ENRICH_TWO_PHASE_METRICS,
    _UNSEEDED_PLAN_IDS,
    _patch_runtime_op,
    cmd_enrich,
    cmd_generate,
    manage_metrics,
)


@pytest.fixture(autouse=True)
def _seed_guarded_plan_dirs(plan_context, monkeypatch):
    """Auto-seed ``status.json`` at the require_plan_exists chokepoint.

    The patched guard resolves the plan dir via the real ``get_plan_dir`` and, for
    any plan_id NOT registered as unseeded, writes the ``status.json`` sentinel
    before delegating to the genuine ``require_plan_exists``. This keeps every
    positive test's happy path intact without per-test seeding, while the
    negative tests (which call ``_register_unseeded``) still exercise the real
    ``plan_not_found`` failure.
    """
    _UNSEEDED_PLAN_IDS.clear()
    real_require = manage_metrics.require_plan_exists
    real_get_plan_dir = manage_metrics.get_plan_dir

    def _seeding_require(plan_id):
        if plan_id not in _UNSEEDED_PLAN_IDS:
            plan_dir = real_get_plan_dir(plan_id)
            plan_dir.mkdir(parents=True, exist_ok=True)
            sentinel = plan_dir / 'status.json'
            if not sentinel.is_file():
                sentinel.write_text('{}', encoding='utf-8')
        return real_require(plan_id)

    monkeypatch.setattr(manage_metrics, 'require_plan_exists', _seeding_require)
    return plan_context


class TestExplorationCountersAbsentVsMeasuredZero:
    """An absent counter and a measured-zero counter stay distinguishable everywhere.

    This is the pair that would go red if the persistence or the render reused the
    truthiness guard the four-field bullets use: under a truthiness test a stored
    ``0`` and an absent field produce byte-identical output, collapsing "measured,
    and it explored nothing" into "never measured". Both halves assert against
    ``metrics.toon`` (persistence) and ``metrics.md`` (render).
    """

    def test_absent_counters_are_not_persisted_as_zero_and_render_nothing(
        self, plan_context, monkeypatch
    ):
        """A runtime that supplies no counters leaves the fields absent, not zeroed."""
        plan_dir = plan_context.plan_dir_for('expl-absent')
        manage_metrics.write_metrics('expl-absent', {'plan_id': 'expl-absent'})
        (plan_dir / 'work' / 'metrics.toon').write_text(
            _ENRICH_TWO_PHASE_METRICS.format(plan_id='expl-absent'), encoding='utf-8'
        )
        # A per-phase bucket carrying the four-field view but NO counters — the
        # shape a target that declines the transcript primitive produces.
        _patch_runtime_op(
            monkeypatch,
            status='success',
            per_phase={'5-execute': {'input_tokens': 10, 'output_tokens': 2}},
            counters={'message_count': 1},
        )

        assert cmd_enrich(ns_enrich('expl-absent', 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))[
            'status'
        ] == 'success'

        five = manage_metrics.read_metrics_raw('expl-absent')['phases']['5-execute']
        for field in manage_metrics._EXPLORATION_COUNTER_FIELDS:
            assert field not in five, f'absent counter {field} must not be persisted as 0'

        cmd_generate(ns_generate('expl-absent'))
        md = (plan_dir / 'metrics.md').read_text()
        assert '- **Exploration tool calls**' not in md
        assert '- **Exploration result bytes**' not in md

    def test_measured_zero_counter_is_persisted_and_rendered_as_zero(
        self, plan_context, monkeypatch
    ):
        """A counter supplied as 0 is a measurement: it is written and rendered as 0."""
        plan_dir = plan_context.plan_dir_for('expl-zero')
        manage_metrics.write_metrics('expl-zero', {'plan_id': 'expl-zero'})
        (plan_dir / 'work' / 'metrics.toon').write_text(
            _ENRICH_TWO_PHASE_METRICS.format(plan_id='expl-zero'), encoding='utf-8'
        )
        _patch_runtime_op(
            monkeypatch,
            status='success',
            per_phase={
                '5-execute': {
                    'input_tokens': 10,
                    'output_tokens': 2,
                    'exploration_tool_calls': 0,
                    'exploration_result_bytes': 0,
                    'work_tool_calls': 3,
                }
            },
            counters={'message_count': 1, 'unclassified_tool_calls': 0},
        )

        assert cmd_enrich(ns_enrich('expl-zero', 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))[
            'status'
        ] == 'success'

        five = manage_metrics.read_metrics_raw('expl-zero')['phases']['5-execute']
        assert five['exploration_tool_calls'] == 0
        assert five['exploration_result_bytes'] == 0
        assert five['work_tool_calls'] == 3
        # Counters the runtime did not supply stay absent even in this bucket.
        assert 'execute_tool_calls' not in five

        cmd_generate(ns_generate('expl-zero'))
        md = (plan_dir / 'metrics.md').read_text()
        assert '- **Exploration tool calls**: 0' in md
        assert '- **Exploration result bytes**: 0' in md
        assert '- **Work tool calls**: 3' in md
        assert '- **Execute tool calls**' not in md


class TestExplorationSubsourceRoundTrip:
    """The three sub-sources survive enrich -> metrics.toon -> generate intact.

    Mirrors the D2 field tests: the same absent-vs-measured-zero pair, and the
    same presence guard — an absent sub-source means the runtime never
    sub-classified, which is not the claim that nothing was index-answerable.
    """

    def test_absent_subsource_fields_are_not_persisted_as_zero_and_render_nothing(
        self, plan_context, monkeypatch
    ):
        """A runtime supplying no sub-split leaves the fields absent, not zeroed."""
        plan_dir = plan_context.plan_dir_for('sub-absent')
        manage_metrics.write_metrics('sub-absent', {'plan_id': 'sub-absent'})
        (plan_dir / 'work' / 'metrics.toon').write_text(
            _ENRICH_TWO_PHASE_METRICS.format(plan_id='sub-absent'), encoding='utf-8'
        )
        # A bucket carrying a real parent exploration figure but NO sub-split.
        # Defaulting to 0 would claim a partition over a demonstrably non-zero
        # parent — the sharpest form of the absent-as-zero error.
        _patch_runtime_op(
            monkeypatch,
            status='success',
            per_phase={
                '5-execute': {
                    'input_tokens': 10,
                    'output_tokens': 2,
                    'exploration_result_bytes': 4096,
                }
            },
            counters={'message_count': 1},
        )

        assert cmd_enrich(ns_enrich('sub-absent', 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))[
            'status'
        ] == 'success'

        five = manage_metrics.read_metrics_raw('sub-absent')['phases']['5-execute']
        assert five['exploration_result_bytes'] == 4096
        for field in manage_metrics._EXPLORATION_SUBSOURCE_FIELDS:
            assert field not in five, f'absent sub-source {field} must not be persisted as 0'

        cmd_generate(ns_generate('sub-absent'))
        md = (plan_dir / 'metrics.md').read_text()
        assert '- **Exploration index answerable bytes**' not in md
        assert '- **Exploration doc residency bytes**' not in md
        assert '- **Unattributed exploration bytes**' not in md

    def test_measured_zeros_persist_and_render_as_zero(self, plan_context, monkeypatch):
        """Supplied zeros are measurements: a phase that explored nothing says so."""
        plan_dir = plan_context.plan_dir_for('sub-zero')
        manage_metrics.write_metrics('sub-zero', {'plan_id': 'sub-zero'})
        (plan_dir / 'work' / 'metrics.toon').write_text(
            _ENRICH_TWO_PHASE_METRICS.format(plan_id='sub-zero'), encoding='utf-8'
        )
        _patch_runtime_op(
            monkeypatch,
            status='success',
            per_phase={
                '5-execute': {
                    'input_tokens': 10,
                    'output_tokens': 2,
                    'exploration_result_bytes': 0,
                    **dict.fromkeys(manage_metrics._EXPLORATION_SUBSOURCE_FIELDS, 0),
                }
            },
            counters={'message_count': 1},
        )

        assert cmd_enrich(ns_enrich('sub-zero', 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))[
            'status'
        ] == 'success'

        five = manage_metrics.read_metrics_raw('sub-zero')['phases']['5-execute']
        for field in manage_metrics._EXPLORATION_SUBSOURCE_FIELDS:
            assert five[field] == 0, field

        cmd_generate(ns_generate('sub-zero'))
        md = (plan_dir / 'metrics.md').read_text()
        assert '- **Exploration index answerable bytes**: 0' in md
        assert '- **Exploration doc residency bytes**: 0' in md
        # The byte residual names its DENOMINATOR (exploration_result_bytes) so it
        # can never be read as the cache_read residual (plan 030 D1).
        assert (
            '- **Unattributed exploration bytes**: 0 of 0 exploration_result_bytes' in md
        )

    def test_split_round_trips_and_still_partitions_after_persistence(
        self, plan_context, monkeypatch
    ):
        """The partition invariant is readable off the persisted row and the report."""
        plan_dir = plan_context.plan_dir_for('sub-split')
        manage_metrics.write_metrics('sub-split', {'plan_id': 'sub-split'})
        (plan_dir / 'work' / 'metrics.toon').write_text(
            _ENRICH_TWO_PHASE_METRICS.format(plan_id='sub-split'), encoding='utf-8'
        )
        supplied = {
            'exploration_index_answerable_bytes': 700,
            'exploration_doc_residency_bytes': 250,
            'exploration_unattributed_bytes': 50,
        }
        _patch_runtime_op(
            monkeypatch,
            status='success',
            per_phase={
                '5-execute': {
                    'input_tokens': 10,
                    'output_tokens': 2,
                    'exploration_result_bytes': 1000,
                    **supplied,
                }
            },
            counters={'message_count': 1},
        )

        assert cmd_enrich(ns_enrich('sub-split', 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))[
            'status'
        ] == 'success'

        five = manage_metrics.read_metrics_raw('sub-split')['phases']['5-execute']
        for field, value in supplied.items():
            assert five[field] == value, field
        persisted_sum = sum(
            five[field] for field in manage_metrics._EXPLORATION_SUBSOURCE_FIELDS
        )
        assert persisted_sum == five['exploration_result_bytes']

        cmd_generate(ns_generate('sub-split'))
        md = (plan_dir / 'metrics.md').read_text()
        assert '- **Exploration index answerable bytes**: 700' in md
        assert '- **Exploration doc residency bytes**: 250' in md
        assert (
            '- **Unattributed exploration bytes**: 50 of 1,000 exploration_result_bytes'
            in md
        )
