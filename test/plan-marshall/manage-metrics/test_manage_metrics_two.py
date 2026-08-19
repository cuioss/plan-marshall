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


class TestCacheReadAttributionRoundTrip:
    """The attribution group survives enrich -> metrics.toon -> generate intact.

    Same absent-vs-measured-zero pair as the exploration counters, and for a
    sharper reason: the RESIDUAL rendering as ``0`` is the statement that the split
    was fully explained. Collapsing that into an absent field under a truthiness
    guard would make "fully explained" unreadable from "never computed".
    """

    def test_absent_attribution_fields_are_not_persisted_as_zero_and_render_nothing(
        self, plan_context, monkeypatch
    ):
        """A runtime supplying no attribution leaves the fields absent, not zeroed."""
        plan_dir = plan_context.plan_dir_for('attr-absent')
        manage_metrics.write_metrics('attr-absent', {'plan_id': 'attr-absent'})
        (plan_dir / 'work' / 'metrics.toon').write_text(
            _ENRICH_TWO_PHASE_METRICS.format(plan_id='attr-absent'), encoding='utf-8'
        )
        # A bucket carrying the four-field view — including a real cache_read — but
        # NO attribution group. A defaulted 0 here would assert a split that was
        # never computed over a figure that is demonstrably non-zero.
        _patch_runtime_op(
            monkeypatch,
            status='success',
            per_phase={
                '5-execute': {
                    'input_tokens': 10,
                    'output_tokens': 2,
                    'cache_read_input_tokens': 5000,
                }
            },
            counters={'message_count': 1},
        )

        assert cmd_enrich(ns_enrich('attr-absent', 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))[
            'status'
        ] == 'success'

        five = manage_metrics.read_metrics_raw('attr-absent')['phases']['5-execute']
        assert five['cache_read_input_tokens'] == 5000
        for field in manage_metrics._CACHE_READ_ATTRIBUTION_FIELDS:
            assert field not in five, f'absent attribution field {field} must not be persisted as 0'

        cmd_generate(ns_generate('attr-absent'))
        md = (plan_dir / 'metrics.md').read_text()
        assert '- **Cache read attributed exploration**' not in md
        assert '- **Unattributed cache_read tokens**' not in md

    def test_measured_zeros_persist_and_render_as_zero(self, plan_context, monkeypatch):
        """Supplied zeros are measurements: written and rendered as 0, residual included."""
        plan_dir = plan_context.plan_dir_for('attr-zero')
        manage_metrics.write_metrics('attr-zero', {'plan_id': 'attr-zero'})
        (plan_dir / 'work' / 'metrics.toon').write_text(
            _ENRICH_TWO_PHASE_METRICS.format(plan_id='attr-zero'), encoding='utf-8'
        )
        # A phase that recorded no cache_read at all: every member of the group is
        # a measured zero, residual included.
        _patch_runtime_op(
            monkeypatch,
            status='success',
            per_phase={
                '5-execute': {
                    'input_tokens': 10,
                    'output_tokens': 2,
                    'cache_read_input_tokens': 0,
                    **dict.fromkeys(manage_metrics._CACHE_READ_ATTRIBUTION_FIELDS, 0),
                }
            },
            counters={'message_count': 1},
        )

        assert cmd_enrich(ns_enrich('attr-zero', 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))[
            'status'
        ] == 'success'

        five = manage_metrics.read_metrics_raw('attr-zero')['phases']['5-execute']
        for field in manage_metrics._CACHE_READ_ATTRIBUTION_FIELDS:
            assert five[field] == 0, field

        cmd_generate(ns_generate('attr-zero'))
        md = (plan_dir / 'metrics.md').read_text()
        assert '- **Cache read attributed exploration**: 0' in md
        # The cache_read residual names its DENOMINATOR (cache_read_input_tokens),
        # a different quantity and denominator from the byte residual (plan 030 D1).
        assert (
            '- **Unattributed cache_read tokens**: 0 of 0 cache_read_input_tokens' in md
        )

    def test_split_round_trips_and_still_reconciles_after_persistence(
        self, plan_context, monkeypatch
    ):
        """The exact-reconciliation invariant is readable off the persisted row and the report."""
        plan_dir = plan_context.plan_dir_for('attr-split')
        manage_metrics.write_metrics('attr-split', {'plan_id': 'attr-split'})
        (plan_dir / 'work' / 'metrics.toon').write_text(
            _ENRICH_TWO_PHASE_METRICS.format(plan_id='attr-split'), encoding='utf-8'
        )
        supplied = {
            'cache_read_attributed_exploration': 800,
            'cache_read_attributed_work': 150,
            'cache_read_attributed_execute': 40,
            'cache_read_attributed_orchestration': 0,
            'cache_read_attributed_unclassified': 0,
            'cache_read_unattributed': 10,
        }
        _patch_runtime_op(
            monkeypatch,
            status='success',
            per_phase={
                '5-execute': {
                    'input_tokens': 10,
                    'output_tokens': 2,
                    'cache_read_input_tokens': 1000,
                    **supplied,
                }
            },
            counters={'message_count': 1},
        )

        assert cmd_enrich(ns_enrich('attr-split', 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))[
            'status'
        ] == 'success'

        five = manage_metrics.read_metrics_raw('attr-split')['phases']['5-execute']
        # Every supplied value survives storage byte-for-byte...
        for field, value in supplied.items():
            assert five[field] == value, field
        # ...so the invariant the producer guarantees is still checkable here.
        persisted_sum = sum(
            five[field] for field in manage_metrics._CACHE_READ_ATTRIBUTION_FIELDS
        )
        assert persisted_sum == five['cache_read_input_tokens']

        cmd_generate(ns_generate('attr-split'))
        md = (plan_dir / 'metrics.md').read_text()
        assert '- **Cache read attributed exploration**: 800' in md
        assert '- **Cache read attributed work**: 150' in md
        assert (
            '- **Unattributed cache_read tokens**: 10 of 1,000 cache_read_input_tokens'
            in md
        )


class TestTwoUnattributedPopulationsAreDistinguishable:
    """Plan 030 D1 (GATE): the two "unattributed" quantities are separately named
    and each carries its own denominator, everywhere either is emitted or rendered.

    ``exploration_unattributed_bytes`` (a byte residual, denominator
    ``exploration_result_bytes``) and ``cache_read_unattributed`` (a cache_read-token
    residual, denominator ``cache_read_input_tokens``) are different quantities with
    different denominators. A consumer holding both must be unable to confuse them —
    asserted on the field NAMES and DENOMINATORS, not on their values.
    """

    def test_emission_carries_two_distinct_keys_with_distinct_denominators(
        self, plan_context, monkeypatch
    ):
        """The persisted record carries both residuals as distinct keys, and their
        denominator fields are distinct — so a consumer reading metrics.toon can
        tell which residual it holds without inspecting values."""
        plan_dir = plan_context.plan_dir_for('d1-emit')
        manage_metrics.write_metrics('d1-emit', {'plan_id': 'd1-emit'})
        (plan_dir / 'work' / 'metrics.toon').write_text(
            _ENRICH_TWO_PHASE_METRICS.format(plan_id='d1-emit'), encoding='utf-8'
        )
        # Deliberately different denominators AND different residual values, so the
        # test cannot pass by the two happening to be equal.
        _patch_runtime_op(
            monkeypatch,
            status='success',
            per_phase={
                '5-execute': {
                    'input_tokens': 10,
                    'output_tokens': 2,
                    'exploration_result_bytes': 4000,
                    'exploration_index_answerable_bytes': 3000,
                    'exploration_doc_residency_bytes': 700,
                    'exploration_unattributed_bytes': 300,
                    'cache_read_input_tokens': 9000,
                    'cache_read_attributed_exploration': 8000,
                    'cache_read_attributed_work': 0,
                    'cache_read_attributed_execute': 0,
                    'cache_read_attributed_orchestration': 0,
                    'cache_read_attributed_unclassified': 0,
                    'cache_read_unattributed': 1000,
                }
            },
            counters={'message_count': 1},
        )

        assert cmd_enrich(ns_enrich('d1-emit', 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))[
            'status'
        ] == 'success'

        five = manage_metrics.read_metrics_raw('d1-emit')['phases']['5-execute']
        # Two distinct keys — neither named merely "unattributed".
        assert 'exploration_unattributed_bytes' in five
        assert 'cache_read_unattributed' in five
        assert 'unattributed' not in five  # no bare-"unattributed" key exists
        # Each residual's DENOMINATOR is a distinct field, also present on the row.
        assert 'exploration_result_bytes' in five
        assert 'cache_read_input_tokens' in five
        assert five['exploration_result_bytes'] != five['cache_read_input_tokens']

    def test_render_names_quantity_and_denominator_for_each_residual(
        self, plan_context, monkeypatch
    ):
        """metrics.md renders each residual with its quantity (bytes vs cache_read
        tokens) AND its denominator, so the two lines are unambiguously different."""
        plan_dir = plan_context.plan_dir_for('d1-render')
        manage_metrics.write_metrics('d1-render', {'plan_id': 'd1-render'})
        (plan_dir / 'work' / 'metrics.toon').write_text(
            _ENRICH_TWO_PHASE_METRICS.format(plan_id='d1-render'), encoding='utf-8'
        )
        _patch_runtime_op(
            monkeypatch,
            status='success',
            per_phase={
                '5-execute': {
                    'input_tokens': 10,
                    'output_tokens': 2,
                    'exploration_result_bytes': 4000,
                    'exploration_index_answerable_bytes': 3000,
                    'exploration_doc_residency_bytes': 700,
                    'exploration_unattributed_bytes': 300,
                    'cache_read_input_tokens': 9000,
                    'cache_read_attributed_exploration': 8000,
                    'cache_read_attributed_work': 0,
                    'cache_read_attributed_execute': 0,
                    'cache_read_attributed_orchestration': 0,
                    'cache_read_attributed_unclassified': 0,
                    'cache_read_unattributed': 1000,
                }
            },
            counters={'message_count': 1},
        )
        cmd_enrich(ns_enrich('d1-render', 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))

        cmd_generate(ns_generate('d1-render'))
        md = (plan_dir / 'metrics.md').read_text()

        # The byte residual: names its quantity (bytes) and its denominator.
        assert (
            '- **Unattributed exploration bytes**: 300 of 4,000 exploration_result_bytes'
            in md
        )
        # The cache_read residual: a DIFFERENT quantity over a DIFFERENT denominator.
        assert (
            '- **Unattributed cache_read tokens**: 1,000 of 9,000 cache_read_input_tokens'
            in md
        )
        # Neither figure is rendered under a bare "unattributed" label: every
        # rendered line carrying the word also carries its denominator ("… of …").
        for line in md.splitlines():
            if 'nattributed' in line and line.lstrip().startswith('- **'):
                assert ' of ' in line, f'unattributed line lacks a denominator: {line!r}'
