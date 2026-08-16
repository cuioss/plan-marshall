#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``sequence-and-build-minimality`` classification — call classification, phase
bucketing, build-class assignment, and verb mining from the global log.
"""

from pathlib import Path

from _audit_fixtures import (
    _ARCH,
    _BUILD,
    _sbm_call,
    _sbm_dispatch,
    _sbm_index,
    _write_sbm_plan,
    audit,
)


class TestSequenceBuildMinimalityClassify:
    """``_sbm_classify_build`` buckets a build's wall-clock duration against the
    centralized minimal/heavy bands (120s / 400s)."""

    def test_zero_duration_is_unknown(self):
        # an unrecorded (0.0s) build is ``unknown``
        assert audit._sbm_classify_build(0.0) == 'unknown'

    def test_negative_duration_is_unknown(self):
        # defensive: <= 0 collapses to ``unknown``
        assert audit._sbm_classify_build(-5.0) == 'unknown'

    def test_below_minimal_band_is_minimal(self):
        # strictly under build_minimal_seconds
        assert audit._sbm_classify_build(119.9) == 'minimal'

    def test_at_minimal_ceiling_is_scoped(self):
        # exactly build_minimal_seconds tips into scoped
        minimal = float(audit.THRESHOLDS['build_minimal_seconds'])
        assert audit._sbm_classify_build(minimal) == 'scoped'

    def test_between_bands_is_scoped(self):
        # 120..400 is a scoped run
        assert audit._sbm_classify_build(250.0) == 'scoped'

    def test_at_heavy_ceiling_is_heavy(self):
        # exactly build_heavy_seconds is heavy (NOT scoped)
        heavy = float(audit.THRESHOLDS['build_heavy_seconds'])
        assert audit._sbm_classify_build(heavy) == 'heavy'

    def test_above_heavy_band_is_heavy(self):
        # well over the heavy ceiling
        assert audit._sbm_classify_build(900.0) == 'heavy'


class TestSequenceBuildMinimalityPhaseBucketing:
    """``_sequence_build_minimality_plan`` attributes each ``script-execution.log``
    call to the phase whose ``[DISPATCH] role=phase-N`` marker most recently
    preceded it on the ``work.log`` timeline."""

    def test_calls_before_first_dispatch_bucket_to_one_init(self, tmp_path: Path):
        # a single call before any dispatch marker
        inputs = _write_sbm_plan(
            tmp_path, 'phase-default',
            sel_lines=[_sbm_call('2026-06-01T10:00:00', _BUILD, 'run', 30.0)],
            work_lines=[_sbm_dispatch('2026-06-01T11:00:00', 'phase-5-execute')],
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        # the call predates the dispatch, so it falls in the default
        # ``1-init`` bucket (role normalized: ``phase-`` stripped).
        assert '1-init:1' in row['phase_graph']

    def test_call_after_dispatch_buckets_to_normalized_role(self, tmp_path: Path):
        # a call after a phase-5-execute dispatch marker + a ledger build in-phase
        inputs = _write_sbm_plan(
            tmp_path, 'phase-exec',
            sel_lines=[_sbm_call('2026-06-01T12:00:00', _BUILD, 'run', 30.0)],
            work_lines=[_sbm_dispatch('2026-06-01T11:00:00', 'phase-5-execute')],
            ledger_builds=[{'dur': 30.0, 'ts': '2026-06-01T12:00:00Z'}],
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        # the call is attributed to ``5-execute`` and the ledger build tags b=1
        assert '5-execute:1(b=1)' in row['phase_graph']

    def test_arch_call_annotates_phase_with_arch_count(self, tmp_path: Path):
        # an architecture call after a dispatch contributes the ``a=`` tag
        inputs = _write_sbm_plan(
            tmp_path, 'phase-arch',
            sel_lines=[_sbm_call('2026-06-01T12:00:00', _ARCH, 'resolve', 0.5)],
            work_lines=[_sbm_dispatch('2026-06-01T11:00:00', 'phase-4-plan')],
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        # the architecture call lands in 4-plan with an ``a=1`` annotation
        assert '4-plan:1(a=1)' in row['phase_graph']
        assert row['arch_calls'] == 1


class TestSequenceBuildMinimalityBuildClass:
    """The per-plan row counts builds by duration band and reports the corpus
    build-second aggregates."""

    def test_three_bands_counted_independently(self, tmp_path: Path):
        # one minimal (<120), one scoped (120..400), one heavy (>400) ledger build
        inputs = _write_sbm_plan(
            tmp_path, 'three-bands',
            ledger_builds=[
                {'dur': 30.0, 'ts': '2026-06-01T10:00:00Z'},
                {'dur': 250.0, 'ts': '2026-06-01T11:00:00Z'},
                {'dur': 500.0, 'ts': '2026-06-01T12:00:00Z'},
            ],
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        # each band counted once; aggregates reflect the heaviest + total
        assert row['builds'] == 3
        assert row['build_minimal'] == 1
        assert row['build_scoped'] == 1
        assert row['build_heavy'] == 1
        assert row['max_build_seconds'] == 500
        assert row['total_build_seconds'] == 780

    def test_non_build_calls_are_not_classified_as_builds(self, tmp_path: Path):
        # an architecture call and a manage-* call, neither a build
        inputs = _write_sbm_plan(
            tmp_path, 'no-builds',
            sel_lines=[
                _sbm_call('2026-06-01T10:00:00', _ARCH, 'resolve', 0.5),
                _sbm_call('2026-06-01T10:01:00', 'pm:manage-tasks:manage-tasks', 'read'),
            ],
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        # two calls recorded, zero builds
        assert row['calls'] == 2
        assert row['builds'] == 0
        assert row['build_minimal'] == 0


class TestSequenceBuildMinimalityVerbMining:
    """Build-verb mining over ``work.log`` distinguishes scoped vs all-modules
    ``module-tests`` runs and counts the other build verbs."""

    def test_scoped_vs_all_module_tests(self, tmp_path: Path):
        # one scoped (known module) and one all-modules (no arg) run
        inputs = _write_sbm_plan(
            tmp_path, 'verb-mt',
            work_lines=[
                'ran module-tests plan-marshall and it passed',
                'then ran module-tests across the whole tree',
            ],
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        # scoped counted once (smt), all-modules counted once (amt)
        assert 'smt=1' in row['verbs']
        assert 'amt=1' in row['verbs']

    def test_unknown_module_arg_counts_as_all(self, tmp_path: Path):
        # a module-tests arg that is NOT a known buildable module
        inputs = _write_sbm_plan(
            tmp_path, 'verb-unknown',
            work_lines=['ran module-tests not-a-real-module here'],
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        # an unrecognised arg falls into the all-modules bucket
        assert 'smt=0' in row['verbs']
        assert 'amt=1' in row['verbs']

    def test_other_build_verbs_counted(self, tmp_path: Path):
        # one each of quality-gate, verify, coverage, compile
        inputs = _write_sbm_plan(
            tmp_path, 'verb-others',
            work_lines=[
                'invoked quality-gate plan-marshall',
                'invoked verify plan-marshall',
                'invoked coverage plan-marshall',
                'invoked compile plan-marshall',
            ],
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        # each verb tallied in its own slot
        assert 'qg=1' in row['verbs']
        assert 'vf=1' in row['verbs']
        assert 'cov=1' in row['verbs']
        assert 'cmp=1' in row['verbs']
