#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``track-selection-accuracy`` — the actual planning track is compared against the
counterfactual the live planning-lane router would have chosen.
"""

from pathlib import Path
from typing import Any

from _audit_fixtures import audit

from conftest import PROJECT_ROOT

_CONCRETE_REQUEST = (
    '# Request\n\n## Clarified Request\n\n'
    'Update `marketplace/bundles/plan-marshall/skills/x/scripts/x.py` to fix it.\n'
)


def _write_track_plan(
    repo_root: Path,
    plan_id: str,
    *,
    planning_lane: str | None,
    track: str | None,
    scope_estimate: str = 'surgical',
    change_type: str = 'bug_fix',
    plan_source: str = 'lesson',
    request_body: str = _CONCRETE_REQUEST,
    write_request: bool = True,
) -> Any:
    """Materialise one synthetic plan and return its parsed ``PlanInputs``.

    Builds a plan directory under ``{repo_root}/.plan/temp`` carrying the inputs
    the track-selection-accuracy check reads: ``references.json`` (track,
    scope_estimate), ``status.json`` (metadata.planning_lane, change_type,
    plan_source), and an optional ``request.md`` for the S5 re-derivation. The
    plan is parsed through the real ``collect_inputs`` so the field wiring is
    exercised end-to-end.
    """
    import json as _json

    plan_dir = repo_root / '.plan' / 'temp' / 'track-corpus' / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)

    refs: dict[str, Any] = {'scope_estimate': scope_estimate}
    if track is not None:
        refs['track'] = track
    (plan_dir / 'references.json').write_text(_json.dumps(refs), encoding='utf-8')

    metadata: dict[str, Any] = {'change_type': change_type, 'plan_source': plan_source}
    if planning_lane is not None:
        metadata['planning_lane'] = planning_lane
    (plan_dir / 'status.json').write_text(
        _json.dumps({'metadata': metadata}), encoding='utf-8'
    )

    if write_request:
        (plan_dir / 'request.md').write_text(request_body, encoding='utf-8')

    return audit.collect_inputs(plan_dir)


_NON_BREAKING_COMPAT = 'deprecation'


class TestTrackSelectionAccuracy:
    """`check_track_selection_accuracy` replays the live router and emits an
    OVER-TRACKED / UNDER-TRACKED / correct verdict per plan."""

    def test_collect_inputs_populates_planning_lane_and_track(self, tmp_path: Path):
        inputs = _write_track_plan(
            tmp_path, 'plan-fields', planning_lane='deep', track='complex'
        )

        assert inputs.planning_lane == 'deep'
        assert inputs.track == 'complex'

    def test_correct_when_actual_deep_matches_counterfactual_deep(self, tmp_path: Path):
        # Ran deep/complex; a multi_module scope (S2) scores the counterfactual deep.
        inputs = _write_track_plan(
            tmp_path, 'plan-correct',
            planning_lane='deep', track='complex', scope_estimate='multi_module',
        )
        routing = audit._load_routing_logic(PROJECT_ROOT)
        assert routing is not None, 'live routing module must import'

        row = audit.check_track_selection_accuracy(inputs, routing, _NON_BREAKING_COMPAT)

        assert row['counterfactual_lane'] == 'deep'
        assert row['verdict'] == 'correct'

    def test_over_tracked_when_actual_deep_but_counterfactual_light(self, tmp_path: Path):
        # Ran deep/complex but every signal is light → OVER-TRACKED.
        inputs = _write_track_plan(
            tmp_path, 'plan-over',
            planning_lane='deep', track='complex', scope_estimate='surgical',
        )
        routing = audit._load_routing_logic(PROJECT_ROOT)

        row = audit.check_track_selection_accuracy(inputs, routing, _NON_BREAKING_COMPAT)

        assert row['counterfactual_lane'] == 'light'
        assert row['verdict'] == 'OVER-TRACKED'

    def test_under_tracked_when_actual_light_but_counterfactual_deep(self, tmp_path: Path):
        # Ran light/simple but a multi_module scope (S2) scores deep → UNDER-TRACKED.
        inputs = _write_track_plan(
            tmp_path, 'plan-under',
            planning_lane='light', track='simple', scope_estimate='multi_module',
        )
        routing = audit._load_routing_logic(PROJECT_ROOT)

        row = audit.check_track_selection_accuracy(inputs, routing, _NON_BREAKING_COMPAT)

        assert row['counterfactual_lane'] == 'deep'
        assert row['verdict'] == 'UNDER-TRACKED'

    def test_correct_when_actual_light_matches_counterfactual_light(self, tmp_path: Path):
        # Ran light/simple and every signal is light → correct.
        inputs = _write_track_plan(
            tmp_path, 'plan-light-correct',
            planning_lane='light', track='simple', scope_estimate='surgical',
        )
        routing = audit._load_routing_logic(PROJECT_ROOT)

        row = audit.check_track_selection_accuracy(inputs, routing, _NON_BREAKING_COMPAT)

        assert row['counterfactual_lane'] == 'light'
        assert row['verdict'] == 'correct'

    def test_not_recorded_when_no_lane_or_track(self, tmp_path: Path):
        # A plan that never recorded a planning lane/track → not_recorded.
        inputs = _write_track_plan(
            tmp_path, 'plan-missing', planning_lane=None, track=None,
        )
        routing = audit._load_routing_logic(PROJECT_ROOT)

        row = audit.check_track_selection_accuracy(inputs, routing, _NON_BREAKING_COMPAT)

        assert row['verdict'] == 'not_recorded'
        assert row['actual_lane'] == ''
        assert row['actual_track'] == ''

    def test_no_routing_logic_when_router_unavailable(self, tmp_path: Path):
        # When the routing module cannot be imported the check degrades gracefully.
        inputs = _write_track_plan(
            tmp_path, 'plan-noroute', planning_lane='deep', track='complex',
        )

        row = audit.check_track_selection_accuracy(inputs, None, _NON_BREAKING_COMPAT)

        assert row['verdict'] == 'no_routing_logic'

    def test_track_derived_from_lane_when_track_absent(self, tmp_path: Path):
        # references.json carries no `track`; the actual track is derived from the
        # recorded lane (deep ⇒ complex).
        inputs = _write_track_plan(
            tmp_path, 'plan-derive',
            planning_lane='deep', track=None, scope_estimate='multi_module',
        )
        routing = audit._load_routing_logic(PROJECT_ROOT)

        row = audit.check_track_selection_accuracy(inputs, routing, _NON_BREAKING_COMPAT)

        assert row['actual_track'] == 'complex'
        assert row['verdict'] == 'correct'

    def test_breaking_compatibility_carved_out_for_narrow_concrete_plan(self, tmp_path: Path):
        # S4 (breaking compatibility) is SUPPRESSED under the narrow-and-concrete
        # carve-out: a surgical, concretely-specified plan is positively bounded,
        # so breaking compatibility alone no longer scores the counterfactual
        # deep. A plan that ran light is therefore correct, not UNDER-TRACKED.
        inputs = _write_track_plan(
            tmp_path, 'plan-s4',
            planning_lane='light', track='simple', scope_estimate='surgical',
        )
        routing = audit._load_routing_logic(PROJECT_ROOT)

        row = audit.check_track_selection_accuracy(inputs, routing, 'breaking')

        assert row['counterfactual_lane'] == 'light'
        assert row['verdict'] == 'correct'

    def test_breaking_compatibility_scores_counterfactual_deep_for_broad_plan(self, tmp_path: Path):
        # Outside the narrow-and-concrete carve-out, S4 (breaking compatibility)
        # still contributes to a deep counterfactual: a broad-scope plan that ran
        # light is UNDER-TRACKED (S2 + S4 both score deep).
        inputs = _write_track_plan(
            tmp_path, 'plan-s4-broad',
            planning_lane='light', track='simple', scope_estimate='multi_module',
        )
        routing = audit._load_routing_logic(PROJECT_ROOT)

        row = audit.check_track_selection_accuracy(inputs, routing, 'breaking')

        assert row['counterfactual_lane'] == 'deep'
        assert row['verdict'] == 'UNDER-TRACKED'

    def test_not_recorded_when_request_md_absent(self, tmp_path: Path):
        # A plan with a recorded lane but NO request.md must short-circuit to
        # not_recorded (reason missing_request_md) rather than fabricating a vague
        # S5 signal. Without the short-circuit this light/surgical plan would feed
        # request_concrete=False, fire S5, score the counterfactual deep, and
        # manufacture a false UNDER-TRACKED verdict.
        inputs = _write_track_plan(
            tmp_path, 'plan-no-request',
            planning_lane='light', track='simple', scope_estimate='surgical',
            write_request=False,
        )
        routing = audit._load_routing_logic(PROJECT_ROOT)
        assert routing is not None, 'live routing module must import'

        row = audit.check_track_selection_accuracy(inputs, routing, _NON_BREAKING_COMPAT)

        assert row['verdict'] == 'not_recorded'
        assert row['reason'] == 'missing_request_md'
        assert row['counterfactual_lane'] == ''
        # The recorded lane/track are still surfaced for context.
        assert row['actual_lane'] == 'light'
        assert row['actual_track'] == 'simple'

    def test_unreadable_request_md_treated_as_unknown_not_vague(
        self, tmp_path: Path, monkeypatch
    ):
        # An OSError reading an existing request.md must be treated as unknown (no
        # S5 deep-bias), NOT as a vague request. A light/surgical plan therefore
        # stays correct rather than being pushed to a false UNDER-TRACKED.
        inputs = _write_track_plan(
            tmp_path, 'plan-unreadable',
            planning_lane='light', track='simple', scope_estimate='surgical',
        )
        routing = audit._load_routing_logic(PROJECT_ROOT)
        assert routing is not None, 'live routing module must import'

        original_read_text = Path.read_text

        def _raise_on_request(self, *args, **kwargs):
            if self.name == 'request.md':
                raise OSError('simulated unreadable file')
            return original_read_text(self, *args, **kwargs)

        monkeypatch.setattr(Path, 'read_text', _raise_on_request)

        row = audit.check_track_selection_accuracy(inputs, routing, _NON_BREAKING_COMPAT)

        # request_concrete=True suppresses S5, so the counterfactual stays light and
        # the verdict is correct — no fabricated UNDER-TRACKED.
        assert row['counterfactual_lane'] == 'light'
        assert row['verdict'] == 'correct'

    def test_track_selection_accuracy_registered_in_check_names(self):
        # The check is registered and runnable via --check, and is per-plan (NOT
        # a cross-plan check).
        assert 'track-selection-accuracy' in audit.CHECK_NAMES
        assert 'track-selection-accuracy' not in audit.CROSS_PLAN_CHECKS

    def test_run_checks_emits_track_selection_accuracy_block(self, tmp_path: Path):
        # End-to-end dispatch: run_checks selects the check and emits its TOON
        # block. repo_root is tmp_path so the persisted report and routing import
        # resolve against the isolated tree (routing is unavailable there, so the
        # row degrades to `no_routing_logic`) and the live .plan tree is untouched.
        inputs = _write_track_plan(
            tmp_path, 'plan-e2e',
            planning_lane='deep', track='complex', scope_estimate='surgical',
        )

        output = audit.run_checks([inputs], ['track-selection-accuracy'], tmp_path)

        # The block header is emitted and carries the per-plan row.
        assert 'track-selection-accuracy' in output
        assert 'plan-e2e' in output
