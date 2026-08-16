#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``architecture-lookup-ratio`` — information-lookup calls are separated from
build-lookup calls and the ratio is threshold-gated.
"""

from pathlib import Path

from _audit_fixtures import (
    _ARCH,
    _sbm_call,
    _write_sbm_plan,
    audit,
)


class TestArchitectureLookupRatio:
    """architecture-lookup-ratio: per-plan information-lookup vs build-lookup ratio
    over `logs/script-execution.log`, with a corpus-derived build_dominated_lookup
    flag (build_lookups >= median AND ratio <= p25, degenerate-corpus guarded)."""

    def test_classifies_info_build_and_discovery(self, tmp_path: Path):
        # 2 info (find, which-module) + 4 build (resolve x3 + derive-verification)
        # + 1 discovery (enrich, excluded from the ratio)
        inputs = _write_sbm_plan(
            tmp_path, 'p-mix',
            sel_lines=[
                _sbm_call('2026-06-01T10:00:00', _ARCH, 'find'),
                _sbm_call('2026-06-01T10:00:01', _ARCH, 'which-module'),
                _sbm_call('2026-06-01T10:00:02', _ARCH, 'resolve'),
                _sbm_call('2026-06-01T10:00:03', _ARCH, 'resolve'),
                _sbm_call('2026-06-01T10:00:04', _ARCH, 'resolve'),
                _sbm_call('2026-06-01T10:00:05', _ARCH, 'derive-verification'),
                _sbm_call('2026-06-01T10:00:06', _ARCH, 'enrich'),
            ],
        )

        row = audit._architecture_lookup_ratio_plan(inputs)

        assert row['info_lookups'] == 2
        assert row['build_lookups'] == 4
        assert row['discovery_calls'] == 1
        assert row['total_arch'] == 7
        assert row['ratio'] == 0.5

    def test_ratio_is_none_when_no_build_lookup(self, tmp_path: Path):
        # only information lookups -> ratio undefined (n/a), never build-dominated
        inputs = _write_sbm_plan(
            tmp_path, 'p-info-only',
            sel_lines=[
                _sbm_call('2026-06-01T10:00:00', _ARCH, 'find'),
                _sbm_call('2026-06-01T10:00:01', _ARCH, 'files'),
            ],
        )

        row = audit._architecture_lookup_ratio_plan(inputs)

        assert row['build_lookups'] == 0
        assert row['ratio'] is None

    def test_build_dominated_flag_fires_on_low_ratio_high_build(self, tmp_path: Path):
        # a build-heavy low-ratio plan vs two balanced higher-ratio plans
        lo = _write_sbm_plan(
            tmp_path, 'p-build-heavy',
            sel_lines=[
                _sbm_call(f'2026-06-01T10:00:{i:02d}', _ARCH, 'resolve')
                for i in range(20)
            ] + [_sbm_call('2026-06-01T10:01:00', _ARCH, 'find')],  # 1/20 = 0.05
        )
        hi1 = _write_sbm_plan(
            tmp_path, 'p-balanced-1',
            sel_lines=[
                _sbm_call('2026-06-01T10:00:00', _ARCH, 'resolve'),
                _sbm_call('2026-06-01T10:00:01', _ARCH, 'resolve'),
                _sbm_call('2026-06-01T10:00:02', _ARCH, 'find'),
                _sbm_call('2026-06-01T10:00:03', _ARCH, 'which-module'),
            ],  # 2/2 = 1.0
        )
        hi2 = _write_sbm_plan(
            tmp_path, 'p-balanced-2',
            sel_lines=[
                _sbm_call('2026-06-01T10:00:00', _ARCH, 'resolve'),
                _sbm_call('2026-06-01T10:00:01', _ARCH, 'find'),
                _sbm_call('2026-06-01T10:00:02', _ARCH, 'find'),
            ],  # 2/1 = 2.0
        )

        result = audit.cross_architecture_lookup_ratio([lo, hi1, hi2])
        by = {r['plan_id']: r for r in result['rows']}

        assert any(f.startswith('build_dominated_lookup') for f in by['p-build-heavy']['flags'])
        assert by['p-balanced-1']['flags'] == []
        assert by['p-balanced-2']['flags'] == []
        assert sum(1 for r in result['rows'] if r['flags']) == 1
        assert result['corpus_info_lookups'] == 5
        assert result['corpus_build_lookups'] == 23

    def test_degenerate_corpus_guard_flags_nobody(self, tmp_path: Path):
        # a uniform corpus (every plan 1 info / 2 build = 0.5) has no low tail, so
        # the spread guard suppresses the flag for all
        plans = [
            _write_sbm_plan(
                tmp_path, f'p-uniform-{i}',
                sel_lines=[
                    _sbm_call('2026-06-01T10:00:00', _ARCH, 'resolve'),
                    _sbm_call('2026-06-01T10:00:01', _ARCH, 'resolve'),
                    _sbm_call('2026-06-01T10:00:02', _ARCH, 'find'),
                ],
            )
            for i in range(3)
        ]

        result = audit.cross_architecture_lookup_ratio(plans)

        assert all(r['flags'] == [] for r in result['rows'])
        assert sum(1 for r in result['rows'] if r['flags']) == 0

    def test_in_check_registry_and_emits_block(self, tmp_path: Path):
        assert 'architecture-lookup-ratio' in audit.CHECK_NAMES
        inputs = _write_sbm_plan(
            tmp_path, 'p-x',
            sel_lines=[_sbm_call('2026-06-01T10:00:00', _ARCH, 'resolve')],
        )

        block = audit.emit_architecture_lookup_ratio_block(
            audit.cross_architecture_lookup_ratio([inputs])
        )

        assert 'check: architecture-lookup-ratio' in block
        assert 'corpus_info_lookups: 0' in block
        assert 'corpus_build_lookups: 1' in block
        assert 'genuine_signal_count: 0' in block

    def test_discovery_breakdown_per_verb(self, tmp_path: Path):
        # discovery (setup-time) calls are broken out per verb: discover / enrich /
        # crawl / other. `derived` is not info/build/discover/enrich/crawl -> other.
        inputs = _write_sbm_plan(
            tmp_path, 'p-disc',
            sel_lines=[
                _sbm_call('2026-06-01T10:00:00', _ARCH, 'discover'),
                _sbm_call('2026-06-01T10:00:01', _ARCH, 'enrich'),
                _sbm_call('2026-06-01T10:00:02', _ARCH, 'enrich'),
                _sbm_call('2026-06-01T10:00:03', _ARCH, 'crawl_module_derived'),
                _sbm_call('2026-06-01T10:00:04', _ARCH, 'crawl-module-derived'),
                _sbm_call('2026-06-01T10:00:05', _ARCH, 'derived'),
            ],
        )

        row = audit._architecture_lookup_ratio_plan(inputs)

        assert row['discovery'] == {'discover': 1, 'enrich': 2, 'crawl': 2, 'other': 1}
        assert row['discovery_calls'] == 6
        assert row['info_lookups'] == 0
        assert row['build_lookups'] == 0

        result = audit.cross_architecture_lookup_ratio([inputs])
        assert result['corpus_discovery'] == {
            'discover': 1, 'enrich': 2, 'crawl': 2, 'other': 1
        }

        block = audit.emit_architecture_lookup_ratio_block(result)
        assert 'corpus_discovery: discover=1;enrich=2;crawl=2;other=1' in block
        # the per-row discovery_breakdown column carries the same split
        assert 'discover=1;enrich=2;crawl=2;other=1' in block
