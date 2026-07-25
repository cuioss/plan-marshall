# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process behavioral tests for ``check-routing-decisions.py``.

The aspect's headline defect was inferring a removal *cause* from a removal
*fact*: any prunable step absent from ``phase_6.steps`` was treated as proof its
``no_code_delta`` predicate had fired, so a step dropped by the posture cutoff
(or by any of the three other recorded non-predicate mechanisms) was reported as
a mis-prune whenever the realized footprint touched production code.

These tests pin the corrected contract: the recorded decision log is consulted
FIRST, and ``log_readable`` is the sole discriminator between a substantiated
``fail`` and an honest ``inconclusive``.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest
from toon_parser import serialize_toon

from conftest import load_script_module

_crd = load_script_module(
    'plan-marshall', 'plan-retrospective', 'check-routing-decisions.py', 'crd_behavior_mod'
)


# The four recorded non-predicate removal mechanisms, copied verbatim from
# manage-execution-manifest/standards/decision-rules.md. Keeping the literals
# here (rather than importing the script's regexes) is what makes these tests a
# real contract check against the emitter rather than a tautology over the
# script's own patterns.
LANE_RESOLUTION_LINE = (
    "[2026-04-17T10:00:00Z] [INFO] [aaaaaa] "
    "(plan-marshall:manage-execution-manifest:compose) lane_resolution — "
    "execution_profile=minimal, dropped ['sonar-roundtrip', 'plan-retrospective'] "
    'from phase_6.steps (tier above posture cutoff)'
)
LANE_RESOLUTION_PREFIXED_LINE = (
    "[2026-04-17T10:00:00Z] [INFO] [aaaaaa] "
    "(plan-marshall:manage-execution-manifest:compose) lane_resolution — "
    "execution_profile=minimal, dropped ['default:sonar-roundtrip'] "
    'from phase_6.steps (tier above posture cutoff)'
)
UNRESOLVED_ASK_LINE = (
    '[2026-04-17T10:00:00Z] [INFO] [bbbbbb] '
    '(plan-marshall:manage-execution-manifest:compose) unresolved_ask_provider_drop — '
    'dropped default:sonar-roundtrip from phase_6.steps '
    '(unresolved lane:ask, provider absent)'
)
SIMPLIFY_INACTIVE_LINE = (
    '[2026-04-17T10:00:00Z] [INFO] [cccccc] '
    '(plan-marshall:manage-execution-manifest:compose) finalize-step-simplify omitted — '
    'change_type=analysis affected_files_count=0'
)
CEREMONY_DROPPED_LINE = (
    '[2026-04-17T10:00:00Z] [INFO] [dddddd] '
    '(plan-marshall:manage-execution-manifest:compose) ceremony_finalize selection — '
    'finalize.simplify=never, dropped finalize-step-simplify from phase_6.steps'
)
CEREMONY_ADDED_LINE = (
    '[2026-04-17T10:00:00Z] [INFO] [eeeeee] '
    '(plan-marshall:manage-execution-manifest:compose) ceremony_finalize selection — '
    'finalize.simplify=always, added finalize-step-simplify to phase_6.steps'
)

# A production path — non-bookkeeping, non-doc, non-test — so
# ``footprint_has_production`` is True and the predicate would be FALSE.
PRODUCTION_PATH = 'marketplace/bundles/plan-marshall/skills/demo/scripts/demo.py'


def _manifest_toon(steps: list[str]) -> str:
    """Render a minimal ``execution.toon`` carrying only ``phase_6.steps``.

    Serialized with the same ``serialize_toon`` the manifest writer uses, so the
    fixture round-trips through the production ``parse_toon`` reader exactly as a
    real manifest does.
    """
    return serialize_toon({'plan_id': 'demo', 'phase_6': {'steps': steps}}) + '\n'


def _build_plan(
    plan_dir: Path,
    *,
    steps: list[str],
    decision_lines: list[str] | None = None,
    write_decision_log: bool = True,
    metadata: dict | None = None,
) -> Path:
    """Materialize a plan directory the aspect can read.

    ``write_decision_log=False`` omits ``logs/decision.log`` entirely, which is
    the ``log_readable == False`` input state.
    """
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'execution.toon').write_text(_manifest_toon(steps), encoding='utf-8')
    (plan_dir / 'status.json').write_text(
        json.dumps({'metadata': metadata if metadata is not None else {}}), encoding='utf-8'
    )
    if write_decision_log:
        logs = plan_dir / 'logs'
        logs.mkdir(exist_ok=True)
        (logs / 'decision.log').write_text('\n'.join(decision_lines or []) + '\n', encoding='utf-8')
    return plan_dir


def _diff_file(tmp_path: Path, paths: list[str], name: str = 'diff.txt') -> str:
    path = tmp_path / name
    path.write_text('\n'.join(paths) + '\n', encoding='utf-8')
    return str(path)


def _run_args(plan_dir: Path, diff_file: str | None) -> Namespace:
    return Namespace(
        command='run',
        plan_id=None,
        archived_plan_path=str(plan_dir),
        mode='archived',
        diff_file=diff_file,
    )


def _check(checks: list[dict], name: str) -> dict | None:
    return next((c for c in checks if c.get('check') == name), None)


# All phase_6 steps EXCEPT sonar-roundtrip — so sonar-roundtrip is the absent
# prunable step under test while finalize-step-simplify stays present.
_STEPS_WITHOUT_SONAR = ['finalize-step-simplify', 'lessons-capture', 'archive-plan']
# All phase_6 steps EXCEPT finalize-step-simplify.
_STEPS_WITHOUT_SIMPLIFY = ['sonar-roundtrip', 'lessons-capture', 'archive-plan']
_STEPS_WITH_BOTH = ['sonar-roundtrip', 'finalize-step-simplify', 'lessons-capture', 'archive-plan']


class TestResolvePlanDir:
    """``resolve_plan_dir`` validates its mode/argument combinations."""

    def test_live_without_plan_id_raises(self):
        with pytest.raises(ValueError, match='--plan-id is required'):
            _crd.resolve_plan_dir('live', None, None)

    def test_archived_without_path_raises(self):
        with pytest.raises(ValueError, match='--archived-plan-path is required'):
            _crd.resolve_plan_dir('archived', None, None)

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError, match='Unknown mode'):
            _crd.resolve_plan_dir('frobnicate', 'p', None)

    def test_archived_returns_supplied_path(self, tmp_path):
        assert _crd.resolve_plan_dir('archived', None, str(tmp_path)) == tmp_path


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


class TestResolveRemovalCauses:
    """The pure cause resolver covers all four recorded mechanisms."""

    def test_posture_cutoff_parses_python_list_repr(self):
        causes = _crd.resolve_removal_causes([LANE_RESOLUTION_LINE])
        assert causes['sonar-roundtrip'] == 'posture_cutoff'
        assert causes['plan-retrospective'] == 'posture_cutoff'

    def test_prefixed_step_key_normalizes_to_bare(self):
        causes = _crd.resolve_removal_causes([LANE_RESOLUTION_PREFIXED_LINE])
        assert causes == {'sonar-roundtrip': 'posture_cutoff'}

    def test_unresolved_ask_provider_drop(self):
        causes = _crd.resolve_removal_causes([UNRESOLVED_ASK_LINE])
        assert causes == {'sonar-roundtrip': 'unresolved_ask_provider_drop'}

    def test_simplify_inactive(self):
        causes = _crd.resolve_removal_causes([SIMPLIFY_INACTIVE_LINE])
        assert causes == {'finalize-step-simplify': 'simplify_inactive'}

    def test_ceremony_finalize_never(self):
        causes = _crd.resolve_removal_causes([CEREMONY_DROPPED_LINE])
        assert causes == {'finalize-step-simplify': 'ceremony_finalize_never'}

    def test_ceremony_added_direction_is_not_a_removal(self):
        """A force-include shares the line shape and MUST NOT read as a cause."""
        assert _crd.resolve_removal_causes([CEREMONY_ADDED_LINE]) == {}

    def test_unrelated_lines_yield_no_causes(self):
        assert _crd.resolve_removal_causes(['some unrelated decision line']) == {}


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
            (LANE_RESOLUTION_LINE, _STEPS_WITHOUT_SONAR, 'sonar-roundtrip', 'posture_cutoff'),
            (
                LANE_RESOLUTION_PREFIXED_LINE,
                _STEPS_WITHOUT_SONAR,
                'sonar-roundtrip',
                'posture_cutoff',
            ),
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
        assert row['detail'] == 'no realized footprint'
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


class TestLoadDiffFiles:
    def test_absent_argument_yields_empty(self):
        assert _crd.load_diff_files(None) == []

    def test_missing_file_yields_empty(self, tmp_path):
        assert _crd.load_diff_files(str(tmp_path / 'nope.txt')) == []

    def test_unreadable_file_yields_empty(self, tmp_path):
        target = tmp_path / 'diff.txt'
        target.mkdir()
        assert _crd.load_diff_files(str(target)) == []

    def test_blank_lines_dropped(self, tmp_path):
        path = tmp_path / 'diff.txt'
        path.write_text('a.py\n\n  b.py  \n', encoding='utf-8')
        assert _crd.load_diff_files(str(path)) == ['a.py', 'b.py']
