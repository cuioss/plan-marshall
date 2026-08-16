#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``exploration-share`` flagging and emission — corpus-relative flags over a
degenerate corpus and the emitted block's shape.
"""

from pathlib import Path

from _audit_fixtures import (
    _counters,
    _plan_with_counters,
    _shares_plan,
    audit,
)


class TestExplorationShareDegenerateCorpus:
    """Each flag is a corpus-relative OUTLIER detector, so it stays suppressed
    unless the share distribution has a genuine high tail. A collapsed band
    (`p75 == median == max`) would otherwise flag every plan."""

    def test_single_plan_corpus_flags_nobody(self, tmp_path: Path):
        # one plan IS the distribution: max == median, so no spread, no flags.
        inputs = _shares_plan(
            tmp_path, 'solo',
            exploration_calls=9, other_calls=1,
            exploration_bytes=900, other_bytes=100,
        )

        result = audit.cross_exploration_share([inputs])

        thr = result['thresholds']
        assert thr['byte_share_has_spread'] == 0.0
        assert thr['turn_share_has_spread'] == 0.0
        assert result['rows'][0]['flags'] == []

    def test_uniform_corpus_flags_nobody(self, tmp_path: Path):
        # every plan explores alike: max == median on both distributions.
        inputs = [
            _shares_plan(
                tmp_path, name,
                exploration_calls=8, other_calls=2,
                exploration_bytes=800, other_bytes=200,
            )
            for name in ('u1', 'u2', 'u3')
        ]

        result = audit.cross_exploration_share(inputs)

        assert all(r['flags'] == [] for r in result['rows']), result['rows']
        assert result['thresholds']['byte_share_has_spread'] == 0.0


class TestExplorationShareFlags:
    """With a real high tail present, the corpus-relative flags fire — each
    annotating the plan's value AND the floating cut-point."""

    def test_byte_heavy_fires_on_the_high_tail(self, tmp_path: Path):
        inputs = [
            _shares_plan(
                tmp_path, 'hi',
                exploration_calls=9, other_calls=1,
                exploration_bytes=900, other_bytes=100,
            ),
            _shares_plan(
                tmp_path, 'mid',
                exploration_calls=5, other_calls=5,
                exploration_bytes=500, other_bytes=500,
            ),
            _shares_plan(
                tmp_path, 'lo',
                exploration_calls=1, other_calls=9,
                exploration_bytes=100, other_bytes=900,
            ),
        ]

        result = audit.cross_exploration_share(inputs)

        by = {r['plan_id']: r for r in result['rows']}
        assert any(f.startswith('exploration_byte_heavy') for f in by['hi']['flags'])
        assert by['lo']['flags'] == []
        # rows are sorted by byte share, descending — the headline number.
        assert [r['plan_id'] for r in result['rows']] == ['hi', 'mid', 'lo']

    def test_many_cheap_probes_fires_on_high_turn_low_byte(self, tmp_path: Path):
        # `probe` spends an unusual share of its DECISIONS on lookup while those
        # lookups return almost no context — the groping-around signature.
        inputs = [
            _shares_plan(
                tmp_path, 'probe',
                exploration_calls=9, other_calls=1,
                exploration_bytes=10, other_bytes=990,
            ),
            _shares_plan(
                tmp_path, 'balanced',
                exploration_calls=5, other_calls=5,
                exploration_bytes=500, other_bytes=500,
            ),
            _shares_plan(
                tmp_path, 'bulk',
                exploration_calls=1, other_calls=9,
                exploration_bytes=900, other_bytes=100,
            ),
        ]

        result = audit.cross_exploration_share(inputs)

        by = {r['plan_id']: r for r in result['rows']}
        assert any(f.startswith('many_cheap_probes') for f in by['probe']['flags'])
        # `balanced` is turn-heavy too, but its byte share is NOT below the corpus
        # median, so the cheap-probe signature does not fire for it.
        assert not any(f.startswith('many_cheap_probes') for f in by['balanced']['flags'])
        # `bulk` is byte-heavy (0.9 byte share — the corpus high tail), so it
        # legitimately carries `exploration_byte_heavy`; that orthogonal flag is
        # covered by test_byte_heavy_fires_on_the_high_tail. Assert only the
        # subject of THIS test: the cheap-probe signature does not fire for it.
        assert not any(f.startswith('many_cheap_probes') for f in by['bulk']['flags'])

    def test_unclassified_tools_flag_is_spread_independent(self, tmp_path: Path):
        # A tool name outside the classifier's domain is a maintenance signal, not
        # an outlier — it fires even in a degenerate single-plan corpus.
        inputs = _shares_plan(
            tmp_path, 'unknown-tool',
            exploration_calls=1, other_calls=1,
            exploration_bytes=10, other_bytes=10,
            unclassified_calls=2, unclassified_bytes=20,
        )

        result = audit.cross_exploration_share([inputs])

        assert result['rows'][0]['flags'] == ['unclassified_tools(n=2)']


class TestEmitExplorationShareBlock:
    """The emitted block leads with the exclusion read-out and the derived
    cut-points, and carries the uniform severity column."""

    def test_block_renders_header_columns_and_severity(self, tmp_path: Path):
        inputs = [
            _shares_plan(
                tmp_path, 'hi',
                exploration_calls=9, other_calls=1,
                exploration_bytes=900, other_bytes=100,
            ),
            _shares_plan(
                tmp_path, 'lo',
                exploration_calls=1, other_calls=9,
                exploration_bytes=100, other_bytes=900,
            ),
            _plan_with_counters(tmp_path, 'unmeasured', {'5-execute': {}}),
        ]
        result = audit.cross_exploration_share(inputs)

        block = audit.emit_exploration_share_block(result)

        assert 'check: exploration-share' in block
        assert 'status: success' in block
        assert 'plans_in_corpus: 2' in block
        # the excluded plan is NAMED rather than silently absent or zeroed
        assert 'plans_excluded_no_counters: 1' in block
        assert 'excluded_plan_ids: unmeasured' in block
        assert 'genuine_signal_count: 1' in block
        assert (
            'rows[2]{plan_id,change_type,phases,exploration_calls,denom_calls,'
            'turn_share,exploration_bytes,denom_bytes,byte_share,unclassified,'
            'flags,severity}:' in block
        )
        genuine_row = next(
            ln.strip() for ln in block.splitlines() if ln.strip().startswith('hi,')
        )
        assert genuine_row.endswith(',genuine')

    def test_undefined_share_renders_as_not_available(self, tmp_path: Path):
        # a measured zero has no defined share; it renders `n/a`, never `0.0%`
        inputs = _plan_with_counters(tmp_path, 'zeroed', {'5-execute': _counters(0, 0)})
        result = audit.cross_exploration_share([inputs])

        block = audit.emit_exploration_share_block(result)

        row = next(ln.strip() for ln in block.splitlines() if ln.strip().startswith('zeroed,'))
        assert ',n/a,' in row

    def test_empty_corpus_emits_zeroed_block(self):
        result = audit.cross_exploration_share([])

        block = audit.emit_exploration_share_block(result)

        assert 'plans_in_corpus: 0' in block
        assert 'genuine_signal_count: 0' in block
