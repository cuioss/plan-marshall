# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process behavioral tests for ``check-routing-decisions.py``."""


from __future__ import annotations

import pytest
from _check_routing_decisions_fixtures import (
    _STEPS_WITH_BOTH,
    _STEPS_WITHOUT_SIMPLIFY,
    _STEPS_WITHOUT_SONAR,
    CEREMONY_ADDED_LINE,
    CEREMONY_DROPPED_LINE,
    DECISION_MATRIX_LINE,
    LANE_RESOLUTION_LINE,
    LANE_RESOLUTION_PREFIXED_LINE,
    PRODUCTION_PATH,
    SIMPLIFY_INACTIVE_LINE,
    UNRESOLVED_ASK_LINE,
    _build_plan,
    _check,
    _crd,
    _diff_file,
    _run_args,
)

from conftest import load_script_module


class TestLoadDecisionLogLines:
    """The widened loader reports readability explicitly.

    A missing log and a readable-but-empty log both yield no lines, but only the
    latter is evidence that no removal cause was recorded — collapsing both to
    ``[]`` is the ambiguity the ``log_readable`` flag resolves.
    """

    def test_missing_log_is_not_readable(self, tmp_path):
        lines, readable = _crd.load_decision_log_lines(tmp_path)
        assert lines == []
        assert readable is False

    def test_present_log_is_readable(self, tmp_path):
        logs = tmp_path / 'logs'
        logs.mkdir()
        (logs / 'decision.log').write_text(LANE_RESOLUTION_LINE + '\n', encoding='utf-8')
        lines, readable = _crd.load_decision_log_lines(tmp_path)
        assert lines == [LANE_RESOLUTION_LINE]
        assert readable is True

    def test_empty_but_present_log_is_readable(self, tmp_path):
        logs = tmp_path / 'logs'
        logs.mkdir()
        (logs / 'decision.log').write_text('', encoding='utf-8')
        lines, readable = _crd.load_decision_log_lines(tmp_path)
        assert lines == []
        assert readable is True

    def test_unreadable_log_is_not_readable(self, tmp_path):
        # A directory named decision.log passes .exists() but raises
        # IsADirectoryError (an OSError) on read_text — portable OSError
        # injection needing no permission bits.
        logs = tmp_path / 'logs'
        logs.mkdir()
        (logs / 'decision.log').mkdir()
        lines, readable = _crd.load_decision_log_lines(tmp_path)
        assert lines == []
        assert readable is False


class TestLoadDiffFiles:
    """An ABSENT ``--diff-file`` and a SUPPLIED-but-unresolvable one are different.

    The absent case yields an empty list so the caller can recover the footprint
    through the shared whole-chain resolver. A supplied path that resolves to
    nothing RAISES: reporting it as an empty diff gave a could-not-look the same
    token as a nothing-to-look-at, and that token degrades to a benign-reading
    ``skip`` in every downstream summary.
    """

    def test_absent_argument_yields_the_omitted_sentinel(self, tmp_path):
        """OMITTED returns ``None``, distinct from a supplied-and-empty ``[]``."""
        assert _crd.load_diff_files(None, tmp_path) is None

    def test_empty_string_argument_is_supplied_input_not_omission(self, tmp_path):
        """``--diff-file ""`` is supplied, so it takes the supplied path and raises.

        A truthiness test would send it down the omitted path, which is the same
        could-not-look-versus-nothing-to-look-at conflation the raise exists to
        prevent, arriving by a different door.
        """
        with pytest.raises(ValueError, match='names no path'):
            _crd.load_diff_files('', tmp_path)
        with pytest.raises(ValueError, match='names no path'):
            _crd.load_diff_files('   ', tmp_path)

    def test_supplied_file_naming_nothing_is_a_resolved_empty_footprint(self, tmp_path):
        """An existing but EMPTY diff file resolves to ``[]``, never to ``None``."""
        path = tmp_path / 'empty.txt'
        path.write_text('', encoding='utf-8')
        assert _crd.load_diff_files(str(path), tmp_path) == []

    def test_missing_file_raises_rather_than_reporting_an_empty_diff(self, tmp_path):
        with pytest.raises(ValueError, match='Diff file does not exist'):
            _crd.load_diff_files(str(tmp_path / 'nope.txt'), tmp_path)

    def test_unreadable_file_raises(self, tmp_path):
        target = tmp_path / 'diff.txt'
        target.mkdir()
        with pytest.raises(ValueError, match='could not be read'):
            _crd.load_diff_files(str(target), tmp_path)

    def test_blank_lines_dropped(self, tmp_path):
        path = tmp_path / 'diff.txt'
        path.write_text('a.py\n\n  b.py  \n', encoding='utf-8')
        assert _crd.load_diff_files(str(path), tmp_path) == ['a.py', 'b.py']

    def test_relative_argument_resolves_against_the_plan_directory(self, tmp_path):
        """The documented ``--diff-file work/footprint.txt`` form, resolved."""
        work = tmp_path / 'work'
        work.mkdir()
        (work / 'footprint.txt').write_text('a.py\n', encoding='utf-8')
        assert _crd.load_diff_files('work/footprint.txt', tmp_path) == ['a.py']

    def test_relative_argument_falls_back_to_cwd(self, tmp_path, monkeypatch):
        """A cwd-relative argument that predates the plan-relative form still works."""
        (tmp_path / 'cwd-diff.txt').write_text('b.py\n', encoding='utf-8')
        monkeypatch.chdir(tmp_path)
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        assert _crd.load_diff_files('cwd-diff.txt', plan_dir) == ['b.py']


class TestLaneResolutionView:
    """Widening the loader must not change what the report-facing fields count."""

    def test_view_keeps_only_lane_resolution_lines(self):
        view = _crd.lane_resolution_view(
            [LANE_RESOLUTION_LINE, UNRESOLVED_ASK_LINE, SIMPLIFY_INACTIVE_LINE, CEREMONY_DROPPED_LINE]
        )
        assert view == [LANE_RESOLUTION_LINE]


class TestMisPruneRecordedCauses:
    """Each recorded mechanism yields ``skip`` plus its own ``removal_cause``.

    Every case below supplies a production footprint — the exact input that
    reported a false ``fail`` before the fix.
    """

    @pytest.mark.parametrize(
        ('line', 'steps', 'step', 'expected_cause'),
        [
            (LANE_RESOLUTION_LINE, _STEPS_WITHOUT_SONAR, 'sonar-roundtrip', 'lane_resolution'),
            (
                LANE_RESOLUTION_PREFIXED_LINE,
                _STEPS_WITHOUT_SONAR,
                'sonar-roundtrip',
                'lane_resolution',
            ),
            (DECISION_MATRIX_LINE, _STEPS_WITHOUT_SONAR, 'sonar-roundtrip', 'decision_matrix'),
            (
                UNRESOLVED_ASK_LINE,
                _STEPS_WITHOUT_SONAR,
                'sonar-roundtrip',
                'unresolved_ask_provider_drop',
            ),
            (
                SIMPLIFY_INACTIVE_LINE,
                _STEPS_WITHOUT_SIMPLIFY,
                'finalize-step-simplify',
                'simplify_inactive',
            ),
            (
                CEREMONY_DROPPED_LINE,
                _STEPS_WITHOUT_SIMPLIFY,
                'finalize-step-simplify',
                'ceremony_finalize_never',
            ),
        ],
    )
    def test_recorded_cause_skips_instead_of_failing(
        self, tmp_path, line, steps, step, expected_cause
    ):
        plan_dir = _build_plan(tmp_path / 'plan', steps=steps, decision_lines=[line])
        result = _crd.cmd_run(_run_args(plan_dir, _diff_file(tmp_path, [PRODUCTION_PATH])))

        row = _check(result['mis_prune_checks'], f'mis_prune:{step}')
        assert row is not None
        assert row['status'] == 'skip'
        assert row['removal_cause'] == expected_cause
        assert 'prune predicate not evaluated' in row['detail']
        assert result['summary']['failed'] == 0

    def test_added_direction_does_not_suppress_a_genuine_mis_prune(self, tmp_path):
        """A ``ceremony_finalize selection ... added`` line is not a removal cause."""
        plan_dir = _build_plan(
            tmp_path / 'plan', steps=_STEPS_WITHOUT_SIMPLIFY, decision_lines=[CEREMONY_ADDED_LINE]
        )
        result = _crd.cmd_run(_run_args(plan_dir, _diff_file(tmp_path, [PRODUCTION_PATH])))

        row = _check(result['mis_prune_checks'], 'mis_prune:finalize-step-simplify')
        assert row['status'] == 'fail'
        assert row['removal_cause'] == 'predicate_evaluated'


class TestMisPruneVerdictDiscriminators:
    """``log_readable`` is the sole discriminator between fail and inconclusive."""

    def test_readable_log_naming_no_cause_still_fails(self, tmp_path):
        """The fix narrows the false positive without disabling the check."""
        plan_dir = _build_plan(
            tmp_path / 'plan', steps=_STEPS_WITHOUT_SONAR, decision_lines=['unrelated decision']
        )
        result = _crd.cmd_run(_run_args(plan_dir, _diff_file(tmp_path, [PRODUCTION_PATH])))

        row = _check(result['mis_prune_checks'], 'mis_prune:sonar-roundtrip')
        assert row['status'] == 'fail'
        assert row['removal_cause'] == 'predicate_evaluated'
        assert result['summary']['failed'] == 1

    def test_missing_decision_log_is_inconclusive(self, tmp_path):
        plan_dir = _build_plan(
            tmp_path / 'plan', steps=_STEPS_WITHOUT_SONAR, write_decision_log=False
        )
        result = _crd.cmd_run(_run_args(plan_dir, _diff_file(tmp_path, [PRODUCTION_PATH])))

        row = _check(result['mis_prune_checks'], 'mis_prune:sonar-roundtrip')
        assert row['status'] == 'inconclusive'
        assert row['removal_cause'] == 'unestablishable'
        assert 'unestablishable' in row['detail']
        # An inconclusive row contributes to none of the summary counters.
        assert result['summary']['failed'] == 0
        assert result['summary']['skipped'] == 0

    def test_unreadable_decision_log_is_inconclusive(self, tmp_path):
        plan_dir = _build_plan(
            tmp_path / 'plan', steps=_STEPS_WITHOUT_SONAR, write_decision_log=False
        )
        logs = plan_dir / 'logs'
        logs.mkdir(exist_ok=True)
        (logs / 'decision.log').mkdir()

        result = _crd.cmd_run(_run_args(plan_dir, _diff_file(tmp_path, [PRODUCTION_PATH])))

        row = _check(result['mis_prune_checks'], 'mis_prune:sonar-roundtrip')
        assert row['status'] == 'inconclusive'
        assert row['removal_cause'] == 'unestablishable'

    def test_absent_step_without_footprint_skips(self, tmp_path):
        plan_dir = _build_plan(
            tmp_path / 'plan', steps=_STEPS_WITHOUT_SONAR, decision_lines=['unrelated decision']
        )
        result = _crd.cmd_run(_run_args(plan_dir, None))

        row = _check(result['mis_prune_checks'], 'mis_prune:sonar-roundtrip')
        assert row['status'] == 'skip'
        assert row['detail'] == 'footprint unresolvable'
        assert row['removal_cause'] == 'not_evaluated'

    def test_present_step_passes(self, tmp_path):
        plan_dir = _build_plan(
            tmp_path / 'plan', steps=_STEPS_WITH_BOTH, decision_lines=['unrelated decision']
        )
        result = _crd.cmd_run(_run_args(plan_dir, _diff_file(tmp_path, [PRODUCTION_PATH])))

        for step in ('sonar-roundtrip', 'finalize-step-simplify'):
            row = _check(result['mis_prune_checks'], f'mis_prune:{step}')
            assert row['status'] == 'pass'
            assert row['detail'] == 'step ran'
            assert row['removal_cause'] == 'not_removed'

    def test_docs_only_footprint_leaves_predicate_holding(self, tmp_path):
        plan_dir = _build_plan(
            tmp_path / 'plan', steps=_STEPS_WITHOUT_SONAR, decision_lines=['unrelated decision']
        )
        result = _crd.cmd_run(_run_args(plan_dir, _diff_file(tmp_path, ['doc/readme.md'])))

        row = _check(result['mis_prune_checks'], 'mis_prune:sonar-roundtrip')
        assert row['status'] == 'pass'
        assert row['detail'] == 'predicate still holds'
        assert row['removal_cause'] == 'predicate_evaluated'

    def test_every_row_carries_a_removal_cause(self, tmp_path):
        plan_dir = _build_plan(
            tmp_path / 'plan', steps=_STEPS_WITHOUT_SONAR, decision_lines=[SIMPLIFY_INACTIVE_LINE]
        )
        result = _crd.cmd_run(_run_args(plan_dir, _diff_file(tmp_path, [PRODUCTION_PATH])))

        assert len(result['mis_prune_checks']) == len(_crd._PRUNABLE_PREDICATES)
        assert all(row.get('removal_cause') for row in result['mis_prune_checks'])


class TestReportFacingFieldsUnchanged:
    """Widening the loader must not change the lane-only report fields."""

    def test_lane_fields_count_only_lane_resolution_entries(self, tmp_path):
        plan_dir = _build_plan(
            tmp_path / 'plan',
            steps=_STEPS_WITH_BOTH,
            decision_lines=[
                LANE_RESOLUTION_LINE,
                UNRESOLVED_ASK_LINE,
                SIMPLIFY_INACTIVE_LINE,
                CEREMONY_DROPPED_LINE,
            ],
        )
        result = _crd.cmd_run(_run_args(plan_dir, None))

        assert result['recompose_divergence']['lane_resolution_log_entries'] == 1
        assert result['recorded_lane_decisions'] == [LANE_RESOLUTION_LINE]


class TestManifestAbsent:
    def test_missing_manifest_returns_skipped(self, tmp_path):
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        result = _crd.cmd_run(_run_args(plan_dir, None))
        assert result['status'] == 'skipped'
        assert result['manifest_present'] is False
        assert result['checks'] == []


class TestExecutionLogPopulation:
    """The mirrored ledger population is held to its writer, not to prose."""

    def test_execution_log_population_matches_writer(self):
        """``EXECUTION_LOG_PHASES`` mirrors the writer's own accepted-phase set.

        ``check-routing-decisions`` runs in a different process from
        ``manage-execution-manifest`` and cannot import its private module at
        runtime, so the population it publishes is a hand-mirror. This test is
        what keeps the mirror honest: it imports the writer's constant and fails
        loudly when a phase is added or removed on either side. Without it, a
        widened writer would leave the reader publishing a population label that
        under-states what the ledger now holds — the exact mislabel the
        population field exists to prevent.
        """
        core = load_script_module(
            'plan-marshall', 'manage-execution-manifest', '_manifest_core.py', 'mc_population_drift'
        )

        assert tuple(_crd.EXECUTION_LOG_PHASES) == tuple(core.VALID_RECORD_PHASES)
        assert _crd.EXECUTION_LOG_POPULATION == ','.join(core.VALID_RECORD_PHASES)

    def test_execution_log_population_is_not_the_whole_plan(self):
        """The published population is a PROPER subset of the canonical phases.

        The defect this plan closes is a partial sum presented as an actual. If
        the ledger ever did span every phase, the population label would be
        redundant and the refusal gate dead code — so the asymmetry is pinned
        rather than assumed.
        """
        constants = load_script_module(
            'plan-marshall', 'tools-file-ops', 'constants.py', 'constants_population_drift'
        )

        ledger = set(_crd.EXECUTION_LOG_PHASES)
        canonical = set(constants.PHASES)
        assert ledger < canonical
        assert canonical - ledger


class TestExecutionLogSumMatchesItsPublishedPopulation:
    """The sum covers exactly the phases its label names."""

    def test_a_row_outside_the_population_is_not_summed(self):
        """An out-of-population row cannot inflate a figure labelled otherwise.

        The writer refuses such rows today, so this is unreachable from it — but
        an archived manifest predating that gate, or a hand-edited one, would
        otherwise be summed under a label naming phases it did not measure. The
        label is a property of the sum, not a promise about a writer in another
        process.
        """
        manifest = {
            'execution_log': [
                {'step_id': 'a', 'phase': '1-init', 'total_tokens': 9_000_000},
                {'step_id': 'b', 'phase': '3-outline', 'total_tokens': 1_000_000},
                {'step_id': 'c', 'phase': '5-execute', 'total_tokens': 1_000},
                {'step_id': 'd', 'phase': '6-finalize', 'total_tokens': 2_000},
            ]
        }

        assert _crd.sum_execution_log_tokens(manifest) == 3_000

    def test_every_in_population_row_is_still_summed(self):
        """The negative control: the filter excludes, it does not under-count."""
        manifest = {
            'execution_log': [
                {'step_id': 'a', 'phase': '5-execute', 'total_tokens': 40_000},
                {'step_id': 'b', 'phase': '6-finalize', 'total_tokens': 60_000},
            ]
        }

        assert _crd.sum_execution_log_tokens(manifest) == 100_000
