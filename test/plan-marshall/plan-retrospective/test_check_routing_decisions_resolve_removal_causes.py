# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process behavioral tests for ``check-routing-decisions.py``."""


from __future__ import annotations

import json
from pathlib import Path

import pytest
from _check_routing_decisions_fixtures import (
    _STEPS_WITHOUT_SONAR,
    CEREMONY_ADDED_LINE,
    CEREMONY_DROPPED_LINE,
    DECISION_MATRIX_LINE,
    LANE_RESOLUTION_LINE,
    LANE_RESOLUTION_PREFIXED_LINE,
    LANE_RESOLUTION_SECOND_STEP_LINE,
    PRODUCTION_PATH,
    SIMPLIFY_INACTIVE_LINE,
    UNRESOLVED_ASK_LINE,
    _build_plan,
    _check,
    _crd,
    _diff_file,
    _run_args,
)
from _decision_line_shapes import format_dropped_record


class TestFootprintResolverFallback:
    """When ``--diff-file`` is absent, the mis-prune check recovers the footprint
    through the SHARED resolver — the D4 "one footprint resolution, two consumers".

    A post-merge run has no ``--diff-file`` and no live worktree, so before D4 the
    mis-prune checks SKIPPED for want of a footprint. They now resolve the realized
    footprint (capture → merge-commit → legacy) exactly as the recall check does.
    """

    def _write_refs(self, plan_dir: Path, refs: dict) -> None:
        (plan_dir / 'references.json').write_text(json.dumps(refs), encoding='utf-8')

    def test_diff_file_absent_recovers_footprint_from_capture(self, tmp_path):
        """No diff-file + realized_footprint present → the predicate re-evaluates."""
        plan_dir = _build_plan(
            tmp_path / 'plan', steps=_STEPS_WITHOUT_SONAR, decision_lines=['unrelated line']
        )
        self._write_refs(plan_dir, {'realized_footprint': [PRODUCTION_PATH]})

        result = _crd.cmd_run(_run_args(plan_dir, None))
        assert result['footprint_source'] == 'resolved'
        check = _check(result['mis_prune_checks'], 'mis_prune:sonar-roundtrip')
        assert check is not None
        # no_code_delta is now FALSE (the realized footprint touched production), and
        # the readable log names no removal cause → a substantiated mis-prune.
        assert check['status'] == 'fail'

    def test_diff_file_absent_and_unresolvable_footprint_skips(self, tmp_path):
        """Negative control: nothing resolvable → SKIP, never a fabricated fail."""
        plan_dir = _build_plan(
            tmp_path / 'plan', steps=_STEPS_WITHOUT_SONAR, decision_lines=['unrelated line']
        )
        self._write_refs(plan_dir, {'base_branch': 'main'})

        result = _crd.cmd_run(_run_args(plan_dir, None))
        assert result['footprint_source'] == 'unresolved'
        check = _check(result['mis_prune_checks'], 'mis_prune:sonar-roundtrip')
        assert check is not None
        assert check['status'] == 'skip'
        assert check['removal_cause'] == 'not_evaluated'

    def test_diff_file_present_takes_precedence_over_capture(self, tmp_path):
        """An explicit --diff-file wins over the recorded capture."""
        plan_dir = _build_plan(
            tmp_path / 'plan', steps=_STEPS_WITHOUT_SONAR, decision_lines=['unrelated line']
        )
        # The capture is doc-only (no production) — if it were consulted the predicate
        # would still hold and the check would PASS. The production diff-file must win.
        self._write_refs(plan_dir, {'realized_footprint': ['doc/only.md']})
        diff = _diff_file(tmp_path, [PRODUCTION_PATH])

        result = _crd.cmd_run(_run_args(plan_dir, diff))
        assert result['footprint_source'] == 'diff_file'
        check = _check(result['mis_prune_checks'], 'mis_prune:sonar-roundtrip')
        assert check is not None
        assert check['status'] == 'fail'


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


class TestResolveRemovalCauses:
    """The pure cause resolver covers every recorded mechanism."""

    def test_lane_resolution_drop_is_recorded_against_its_gate(self):
        """The posture-cutoff drop the reader could previously never see."""
        causes = _crd.resolve_removal_causes(
            [LANE_RESOLUTION_LINE, LANE_RESOLUTION_SECOND_STEP_LINE]
        )
        assert causes['sonar-roundtrip'] == 'lane_resolution'
        assert causes['plan-retrospective'] == 'lane_resolution'

    def test_decision_matrix_drop_is_recorded(self):
        """The matrix rows that narrow phase_6 to the analysis minimum.

        Unrecognised before the shared shape was adopted, so a plan under
        ``early_terminate_analysis`` or ``verification_no_files`` had both
        prunable steps re-evaluated against a footprint that never removed them.
        """
        causes = _crd.resolve_removal_causes([DECISION_MATRIX_LINE])
        assert causes == {'sonar-roundtrip': 'decision_matrix'}

    def test_prefixed_step_key_normalizes_to_bare(self):
        causes = _crd.resolve_removal_causes([LANE_RESOLUTION_PREFIXED_LINE])
        assert causes == {'sonar-roundtrip': 'lane_resolution'}

    def test_archived_legacy_aggregate_line_still_resolves_its_cause(self):
        """An ARCHIVED log written under the retired aggregate emitter.

        This shape is transcribed literally on purpose: no live emitter produces
        it any more, so there is no writer to render it from. Archived decision
        logs are immutable history, and dropping the pattern would leave every
        pre-change archive resolving NO cause for its posture-cutoff drops —
        falling through to predicate re-evaluation and producing exactly the false
        `mis_prune` this check exists to end.
        """
        legacy = (
            '[2026-04-17T10:00:00Z] [INFO] [aaaaaa] '
            '(plan-marshall:manage-execution-manifest:compose) lane_resolution — '
            "execution_profile=minimal, dropped ['sonar-roundtrip', 'plan-retrospective'] "
            'from phase_6.steps (tier above posture cutoff)'
        )
        causes = _crd.resolve_removal_causes([legacy])

        assert causes['sonar-roundtrip'] == 'posture_cutoff_legacy_aggregate'
        assert causes['plan-retrospective'] == 'posture_cutoff_legacy_aggregate'

    def test_the_legacy_pattern_is_the_only_route_to_the_list_repr_branch(self):
        """Pins the COUPLING, not the splitter.

        The predecessor of this test asserted `_parse_step_tokens("['a','b']")`
        directly, which passes whether or not any pattern can ever hand it a list
        repr — it pinned neither reachability nor uniqueness while claiming both.

        These assertions fail if the legacy pattern is removed (the branch becomes
        dead) and if some other pattern starts capturing a list repr (the
        uniqueness claim becomes false).
        """
        legacy_capture = "['sonar-roundtrip', 'plan-retrospective']"

        # Reachability: exactly one pattern can produce a list-repr capture.
        producers = [
            cause
            for cause, pattern in _crd._REMOVAL_CAUSE_PATTERNS
            if pattern.search(
                '(plan-marshall:manage-execution-manifest:compose) lane_resolution — '
                f'execution_profile=minimal, dropped {legacy_capture} '
                'from phase_6.steps (tier above posture cutoff)'
            )
        ]
        assert producers == ['posture_cutoff_legacy_aggregate']

        # Uniqueness: the shared shape cannot capture one (its capture is `\\S+`).
        assert not _crd._DROPPED_RECORD_RE.search(
            '[STATUS] lane_resolution — dropped '
            f'{legacy_capture} from phase_6.steps: a reason'
        )

    def test_unknown_future_gate_in_the_shared_shape_is_still_a_cause(self):
        """Gate-agnostic by construction — a new composer gate needs no edit here.

        This is the property that replaces the hand-written enumeration: the
        reader's coverage follows the shape, not a list.
        """
        line = '[2026-04-17T10:00:03Z] [INFO] [gggggg] ' + format_dropped_record(
            'some_future_gate', 'sonar-roundtrip', 'a reason', target=' from phase_6.steps'
        )
        assert _crd.resolve_removal_causes([line]) == {'sonar-roundtrip': 'some_future_gate'}

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
