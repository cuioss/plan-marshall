#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``sequence-and-build-minimality`` flagging — which build/call sequences raise a
genuine redundancy signal.
"""

from pathlib import Path

from _audit_fixtures import (
    _ARCH,
    _sbm_call,
    _sbm_dispatch,
    _sbm_index,
    _write_sbm_plan,
    audit,
)


class TestSequenceBuildMinimalityFlags:
    """Each redundancy / anti-pattern flag fires on its own primitive and is
    absent on a clean plan."""

    def test_build_churn_flag_on_clustered_builds(self, tmp_path: Path):
        # two ledger builds 5 minutes apart (< 10-minute clustering window)
        inputs = _write_sbm_plan(
            tmp_path, 'flag-churn',
            ledger_builds=[
                {'dur': 30.0, 'ts': '2026-06-01T10:00:00Z'},
                {'dur': 30.0, 'ts': '2026-06-01T10:05:00Z'},
            ],
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        # the second build clusters with the first
        assert row['build_churn'] == 1
        assert any(f.startswith('build_churn(') for f in row['flags'])

    def test_no_churn_when_builds_spaced_beyond_window(self, tmp_path: Path):
        # two ledger builds 20 minutes apart (> 10-minute window)
        inputs = _write_sbm_plan(
            tmp_path, 'flag-nochurn',
            ledger_builds=[
                {'dur': 30.0, 'ts': '2026-06-01T10:00:00Z'},
                {'dur': 30.0, 'ts': '2026-06-01T10:20:00Z'},
            ],
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        # spaced builds do not cluster
        assert row['build_churn'] == 0
        assert not any(f.startswith('build_churn(') for f in row['flags'])

    def test_non_minimal_build_flag_on_heavy_build(self, tmp_path: Path):
        # a single heavy (> 400s) ledger build
        inputs = _write_sbm_plan(
            tmp_path, 'flag-heavy',
            ledger_builds=[{'dur': 600.0}],
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        # the heavy build raises non_minimal_build
        assert row['build_heavy'] == 1
        assert any(f.startswith('non_minimal_build(') for f in row['flags'])

    def test_docs_only_build_flag_when_no_py_touched(self, tmp_path: Path):
        # a ledger build ran but only a markdown file was modified
        inputs = _write_sbm_plan(
            tmp_path, 'flag-docs',
            ledger_builds=[{'dur': 30.0}],
            modified_files=['doc/guide.md'],
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        # docs_only footprint + a build => the docs_only_build flag
        assert row['docs_only'] is True
        assert any(f.startswith('docs_only_build(') for f in row['flags'])

    def test_no_docs_only_flag_when_py_touched(self, tmp_path: Path):
        # a ledger build ran and a .py file was modified
        inputs = _write_sbm_plan(
            tmp_path, 'flag-py',
            ledger_builds=[{'dur': 30.0}],
            modified_files=['scripts/audit.py'],
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        # a .py touch clears docs_only
        assert row['docs_only'] is False
        assert not any(f.startswith('docs_only_build(') for f in row['flags'])

    def test_ci_rerun_flag_on_multiple_ci_run_dirs(self, tmp_path: Path):
        # two CI run directories under artifacts/ci-runs/
        inputs = _write_sbm_plan(tmp_path, 'flag-ci', ci_runs=2)

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        # >1 CI run directory raises ci_rerun
        assert row['ci_runs'] == 2
        assert any(f.startswith('ci_rerun(') for f in row['flags'])

    def test_no_ci_rerun_flag_for_single_run(self, tmp_path: Path):
        # exactly one CI run directory (not a rerun)
        inputs = _write_sbm_plan(tmp_path, 'flag-ci-single', ci_runs=1)

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        # a single CI run is not a rerun signal
        assert row['ci_runs'] == 1
        assert not any(f.startswith('ci_rerun(') for f in row['flags'])

    def test_phase_reentry_flag_when_role_dispatched_twice(self, tmp_path: Path):
        # phase-5-execute dispatched twice on the work.log timeline
        inputs = _write_sbm_plan(
            tmp_path, 'flag-reentry',
            work_lines=[
                _sbm_dispatch('2026-06-01T10:00:00', 'phase-5-execute'),
                _sbm_dispatch('2026-06-01T11:00:00', 'phase-5-execute'),
            ],
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        # the re-dispatched role surfaces in phase_reentry + the flag fires
        assert row['phase_reentry'] == '5-execute'
        assert any(f.startswith('phase_reentry(') for f in row['flags'])

    def test_arch_over_resolution_flag_when_arch_dwarfs_builds(self, tmp_path: Path):
        # 5 architecture calls against a single ledger build (>= 5x ratio)
        sel = [
            _sbm_call(f'2026-06-01T10:0{i}:00', _ARCH, 'resolve', 0.5) for i in range(5)
        ]
        inputs = _write_sbm_plan(
            tmp_path, 'flag-arch',
            sel_lines=sel,
            ledger_builds=[{'dur': 30.0, 'ts': '2026-06-01T10:06:00Z'}],
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        # arch (5) >= 5 * builds (1) raises arch_over_resolution
        assert row['arch_calls'] == 5
        assert row['builds'] == 1
        assert any(f.startswith('arch_over_resolution(') for f in row['flags'])

    def test_consecutive_dup_flag_on_back_to_back_identical_calls(self, tmp_path: Path):
        # two identical (notation, sub) calls back-to-back
        inputs = _write_sbm_plan(
            tmp_path, 'flag-dup',
            sel_lines=[
                _sbm_call('2026-06-01T10:00:00', 'pm:manage-tasks:manage-tasks', 'read'),
                _sbm_call('2026-06-01T10:01:00', 'pm:manage-tasks:manage-tasks', 'read'),
            ],
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        # the second identical call is a consecutive duplicate
        assert row['consecutive_dup'] == 1
        assert any(f.startswith('consecutive_dup(') for f in row['flags'])

    def test_clean_minimal_plan_has_no_flags(self, tmp_path: Path):
        # one minimal ledger build touching a .py file, single CI run, distinct calls
        inputs = _write_sbm_plan(
            tmp_path, 'flag-clean',
            sel_lines=[_sbm_call('2026-06-01T10:00:00', _ARCH, 'resolve', 0.5)],
            modified_files=['scripts/audit.py'],
            ci_runs=1,
            ledger_builds=[{'dur': 30.0, 'ts': '2026-06-01T10:05:00Z'}],
        )

        row = audit._sequence_build_minimality_plan(inputs, _sbm_index(tmp_path))

        # the expected minimal shape carries no redundancy flag
        assert row['flags'] == []
