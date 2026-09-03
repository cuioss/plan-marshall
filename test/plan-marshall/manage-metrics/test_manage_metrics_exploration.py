#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py CLI script.

Scope: the exploration buckets, counters and subsource fields — that each matches
the platform-runtime contract, that an absent counter is not persisted as zero while
a measured zero is, and that the source reaches no transcript-engine symbol.
"""


from pathlib import Path

from _manage_metrics_fixtures import (
    ns_enrich,
    ns_generate,
)
from _manage_metrics_module_fixtures import (
    _ENRICH_TWO_PHASE_METRICS,
    _UNSEEDED_PLAN_IDS,
    SCRIPT_PATH,
    _contract_counter_keys,
    _contract_subsource_keys,
    _patch_runtime_op,
    _seed_guarded_plan_dirs,
    cmd_enrich,
    cmd_generate,
    manage_metrics,
)


class TestManageMetricsHasNoTranscriptCode:
    """Regression: the Claude-transcript engine no longer lives in manage-metrics.

    The transcript engine (transcript discovery, message.usage parse, <usage> tag,
    strict-UUID, cache-pricing weights) was relocated to claude_runtime. These
    assertions guard against a re-introduction.
    """

    def test_no_transcript_engine_symbols(self):
        """The removed transcript-engine helpers/constants are absent from the module."""
        for symbol in (
            'USAGE_TAG_RE',
            'USAGE_FIELD_RE',
            'SESSION_ID_RE',
            'USAGE_FOUR_FIELDS',
            'BILLING_WEIGHT_CACHE_READ',
            'BILLING_WEIGHT_CACHE_CREATION',
            '_sum_subagent_transcript',
            '_billing_weighted_total',
            '_attribute_subagent_usage',
            '_add_usage_four_fields',
            '_window_for_timestamp',
            '_extract_text_payload',
            '_resolve_subagent_transcripts',
        ):
            assert not hasattr(manage_metrics, symbol), f'{symbol} should have been relocated'

    def test_source_has_no_claude_transcript_path_or_parse(self):
        """The manage-metrics source no longer hard-codes the Claude transcript layout.

        The ``.claude/projects`` path derivation and the transcript JSONL parse are
        the transcript engine — both relocated to claude_runtime. (The ``<usage>``
        return-tag continues to be consumed by the accumulate-agent-usage storage
        path, so its string still legitimately appears; the assertion targets only
        the transcript-engine markers.)
        """
        source = Path(SCRIPT_PATH).read_text(encoding='utf-8')
        assert '.claude/projects' not in source
        # The strict-UUID transcript guard and cache-pricing weights are gone.
        assert 'SESSION_ID_RE' not in source
        assert 'BILLING_WEIGHT' not in source


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


def test_exploration_buckets_match_platform_runtime_contract():
    """``_EXPLORATION_BUCKETS`` matches the bucket set the runtime contract declares.

    Contract-level drift guard for the cross-process hand-mirror: the bucket names
    are recovered from the contract's ``*_tool_calls`` keys, so adding a bucket to
    the producer without extending ``_EXPLORATION_BUCKETS`` fails loudly here.
    """
    contract_buckets = {
        key[: -len('_tool_calls')]
        for key in _contract_counter_keys()
        if key.endswith('_tool_calls')
    }

    assert contract_buckets, 'contract declares no *_tool_calls counter keys'
    assert set(manage_metrics._EXPLORATION_BUCKETS) == contract_buckets
    # The mirror must also stay duplicate-free — a repeated name would silently
    # double a bucket's counter fields below.
    assert len(manage_metrics._EXPLORATION_BUCKETS) == len(contract_buckets)


def test_exploration_counter_fields_match_platform_runtime_contract():
    """``_EXPLORATION_COUNTER_FIELDS`` equals the contract's counter key set exactly.

    The derived ``{bucket}_{measure}`` product must reproduce the contract's ten
    published counter keys — no extra field manage-metrics would persist but the
    producer never emits, and no missing field the producer emits but the report
    would drop.
    """
    assert set(manage_metrics._EXPLORATION_COUNTER_FIELDS) == _contract_counter_keys()


def test_exploration_subsource_fields_match_platform_runtime_contract():
    """``_EXPLORATION_SUBSOURCE_FIELDS`` equals the contract's sub-source key set exactly.

    Same cross-process hand-mirror guard as the two drift tests above: a
    sub-source added on the producer side without extending the mirror would
    silently under-persist and under-render, and fails loudly here instead.
    """
    contract_keys = _contract_subsource_keys()

    assert contract_keys, 'contract declares no exploration sub-source keys'
    assert set(manage_metrics._EXPLORATION_SUBSOURCE_FIELDS) == contract_keys
    # The mirror stays duplicate-free — a repeated name would double a field.
    assert len(manage_metrics._EXPLORATION_SUBSOURCE_FIELDS) == len(contract_keys)
