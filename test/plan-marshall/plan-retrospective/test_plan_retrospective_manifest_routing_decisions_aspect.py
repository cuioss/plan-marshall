# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the routing-decisions aspect of ``check-routing-decisions.py``."""


from __future__ import annotations

import pytest
from _plan_retrospective_manifest_fixtures import (
    _manifest_with_steps_and_log,
    _mis_prune,
    _run_routing,
    _setup_plan_with_manifest,
    _write_diff,
    _write_status_metadata,
)


class TestRoutingDecisionsAspect:
    """Deterministic predicate re-evaluation + the LLM-judgement boundary."""

    def test_no_manifest_emits_skipped_fragment(self, tmp_path, monkeypatch):
        plan_id, plan_dir = _setup_plan_with_manifest(
            tmp_path, monkeypatch, manifest_body='', plan_id='routing-legacy'
        )
        (plan_dir / 'execution.toon').unlink()

        result = _run_routing(plan_id)

        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'skipped'
        assert data['manifest_present'] is False

    def test_mis_prune_flagged_when_sonar_skipped_but_diff_touched_production(self, tmp_path, monkeypatch):
        """sonar-roundtrip absent + a production diff → its no_code_delta predicate is now false."""
        plan_id, plan_dir = _setup_plan_with_manifest(
            tmp_path,
            monkeypatch,
            manifest_body=_manifest_with_steps_and_log(['push', 'create-pr'], []),
            plan_id='routing-misprune',
        )
        _write_status_metadata(plan_dir, {'execution_profile': 'standard', 'planning_lane': 'light'})
        diff = _write_diff(tmp_path, ['marketplace/bundles/plan-marshall/skills/x/scripts/x.py'])

        result = _run_routing(plan_id, '--diff-file', str(diff))

        assert result.success, result.stderr
        data = result.toon()
        assert data['posture'] == 'standard'
        sonar = _mis_prune(data['mis_prune_checks'], 'sonar-roundtrip')
        assert sonar is not None
        assert sonar['status'] == 'fail'
        assert 'production' in sonar['detail']

    def test_no_mis_prune_when_diff_is_docs_only(self, tmp_path, monkeypatch):
        """sonar-roundtrip absent but a docs-only diff → the no_code_delta predicate still holds."""
        plan_id, plan_dir = _setup_plan_with_manifest(
            tmp_path,
            monkeypatch,
            manifest_body=_manifest_with_steps_and_log(['push', 'create-pr'], []),
            plan_id='routing-docs',
        )
        _write_status_metadata(plan_dir, {'execution_profile': 'minimal'})
        diff = _write_diff(tmp_path, ['doc/user/configuration.adoc', 'README.md'])

        result = _run_routing(plan_id, '--diff-file', str(diff))

        data = result.toon()
        sonar = _mis_prune(data['mis_prune_checks'], 'sonar-roundtrip')
        assert sonar is not None
        assert sonar['status'] == 'pass'

    def test_mis_prune_skipped_when_footprint_unresolvable(self, tmp_path, monkeypatch):
        """No --diff-file AND an unresolvable footprint → skip (no false positive).

        With D4 the mis-prune check recovers the footprint through the shared
        resolver when ``--diff-file`` is absent (the recall check and this check
        recover together); only a genuinely UNRESOLVABLE footprint still skips. Here
        there is no diff-file, no live worktree, no realized-footprint capture, and
        no legacy key — so the resolver returns UNRESOLVED and the check skips
        rather than fabricating a verdict.
        """
        import json as _json

        plan_id, plan_dir = _setup_plan_with_manifest(
            tmp_path,
            monkeypatch,
            manifest_body=_manifest_with_steps_and_log(['push', 'create-pr'], []),
            plan_id='routing-nofoot',
        )
        _write_status_metadata(plan_dir, {'execution_profile': 'standard'})
        # Strip the happy-fixture's footprint keys so nothing resolves: the shared
        # resolver's legacy tier would otherwise correctly recover modified_files.
        (plan_dir / 'references.json').write_text(_json.dumps({'domains': []}), encoding='utf-8')

        result = _run_routing(plan_id)

        data = result.toon()
        assert data['footprint_source'] == 'unresolved'
        sonar = _mis_prune(data['mis_prune_checks'], 'sonar-roundtrip')
        assert sonar is not None
        assert sonar['status'] == 'skip'

    def test_step_that_ran_is_pass(self, tmp_path, monkeypatch):
        """sonar-roundtrip present in phase_6.steps → the step ran (pass)."""
        plan_id, plan_dir = _setup_plan_with_manifest(
            tmp_path,
            monkeypatch,
            manifest_body=_manifest_with_steps_and_log(['push', 'sonar-roundtrip', 'create-pr'], []),
            plan_id='routing-ran',
        )
        _write_status_metadata(plan_dir, {'execution_profile': 'full'})
        diff = _write_diff(tmp_path, ['src/x.py'])

        result = _run_routing(plan_id, '--diff-file', str(diff))

        data = result.toon()
        sonar = _mis_prune(data['mis_prune_checks'], 'sonar-roundtrip')
        assert sonar is not None
        assert sonar['status'] == 'pass'

    _COST_LOG_ROWS = [
        {'step_id': 'push', 'phase': '6-finalize', 'total_tokens': 40000},
        {'step_id': 'create-pr', 'phase': '6-finalize', 'total_tokens': 60000},
    ]

    def _setup_cost_plan(self, tmp_path, monkeypatch, metadata):
        """A plan whose execution_log sums to 100000, with the given status metadata."""
        plan_id, plan_dir = _setup_plan_with_manifest(
            tmp_path,
            monkeypatch,
            manifest_body=_manifest_with_steps_and_log(['push', 'create-pr'], self._COST_LOG_ROWS),
            plan_id='routing-cost',
        )
        _write_status_metadata(plan_dir, metadata)
        return plan_id

    def test_cost_preview_delta_computed_when_populations_match(self, tmp_path, monkeypatch):
        """A prediction declaring the ledger's own population yields a signed delta."""
        plan_id = self._setup_cost_plan(
            tmp_path,
            monkeypatch,
            {
                'execution_profile': 'minimal',
                'execution_profile_cost_preview': 80000,
                'execution_profile_cost_preview_population': '5-execute,6-finalize',
            },
        )

        preview = _run_routing(plan_id).toon()['cost_preview']

        assert preview['comparison'] == 'computed'
        assert preview['execution_log_tokens'] == 100000
        assert preview['execution_log_population'] == '5-execute,6-finalize'
        assert preview['predicted_tokens'] == 80000
        assert preview['delta_tokens'] == 20000
        assert preview['delta_pct'] == 25.0

    def test_cost_preview_refuses_population_mismatched_comparison(self, tmp_path, monkeypatch):
        """A prediction over another population is REFUSED — no delta is emitted.

        The recalibration loop consumes ``delta_pct``. A delta between a
        2-of-6-phase sum and a phase-6-only prediction is a plausible number over
        a quantity nobody measured, so the comparison is withheld rather than
        computed.
        """
        plan_id = self._setup_cost_plan(
            tmp_path,
            monkeypatch,
            {
                'execution_profile': 'minimal',
                'execution_profile_cost_preview': 80000,
                'execution_profile_cost_preview_population': '6-finalize',
            },
        )

        preview = _run_routing(plan_id).toon()['cost_preview']

        assert preview['comparison'] == 'refused'
        assert 'population_mismatch' in preview['comparison_reason']
        assert preview['execution_log_tokens'] == 100000
        assert preview['predicted_population'] == '6-finalize'
        assert 'delta_tokens' not in preview
        assert 'delta_pct' not in preview

    def test_cost_preview_refuses_prediction_with_unstated_population(self, tmp_path, monkeypatch):
        """An unstated prediction population never reads as agreement.

        This is the shape every archived plan carries, since no producer writes
        the population companion. Absence must refuse, not default to a match.
        """
        plan_id = self._setup_cost_plan(
            tmp_path,
            monkeypatch,
            {'execution_profile': 'minimal', 'execution_profile_cost_preview': 80000},
        )

        preview = _run_routing(plan_id).toon()['cost_preview']

        assert preview['comparison'] == 'refused'
        assert preview['predicted_population'] == 'unstated'
        assert 'delta_tokens' not in preview

    def test_cost_preview_not_attempted_without_a_prediction(self, tmp_path, monkeypatch):
        """No recorded prediction is `not_attempted`, distinct from a refusal."""
        plan_id = self._setup_cost_plan(
            tmp_path, monkeypatch, {'execution_profile': 'minimal'}
        )

        preview = _run_routing(plan_id).toon()['cost_preview']

        assert preview['comparison'] == 'not_attempted'
        assert preview['predicted_tokens'] is None
        assert preview['execution_log_tokens'] == 100000
        assert 'delta_tokens' not in preview

    @pytest.mark.parametrize(
        'recorded',
        ['12.5', 'abc', '-100', ''],
        ids=['non-integer', 'non-numeric', 'negative', 'empty'],
    )
    def test_a_recorded_but_unreadable_preview_is_not_reported_as_absent(
        self, tmp_path, monkeypatch, recorded
    ):
        """A present-but-unparseable value is a third state, not an absence.

        Collapsing it into "no cost preview recorded" states something the record
        contradicts — the silent choice this deliverable replaces with a legible
        one, committed by the code that replaces it.
        """
        plan_id = self._setup_cost_plan(
            tmp_path,
            monkeypatch,
            {'execution_profile': 'minimal', 'execution_profile_cost_preview': recorded},
        )

        preview = _run_routing(plan_id).toon()['cost_preview']

        assert preview['comparison'] == 'not_attempted'
        assert 'could not be read' in preview['comparison_reason']
        assert 'no cost preview recorded' not in preview['comparison_reason']

    def test_a_padded_numeric_preview_is_read_rather_than_discarded(self, tmp_path, monkeypatch):
        """Whitespace does not silently demote a real value.

        The population field beside it was already stripped; one function reading
        two fields by two rules is how the unparseable state went unnoticed.
        """
        plan_id = self._setup_cost_plan(
            tmp_path,
            monkeypatch,
            {
                'execution_profile': 'minimal',
                'execution_profile_cost_preview': '  80000  ',
                'execution_profile_cost_preview_population': '5-execute,6-finalize',
            },
        )

        preview = _run_routing(plan_id).toon()['cost_preview']

        assert preview['predicted_tokens'] == 80000
        assert preview['comparison'] == 'computed'

    def test_a_truly_absent_preview_still_says_so(self, tmp_path, monkeypatch):
        """The negative control: absence and unreadability stay distinguishable."""
        plan_id = self._setup_cost_plan(
            tmp_path, monkeypatch, {'execution_profile': 'minimal'}
        )

        preview = _run_routing(plan_id).toon()['cost_preview']

        assert preview['comparison'] == 'not_attempted'
        assert 'no cost preview recorded' in preview['comparison_reason']
        assert 'could not be read' not in preview['comparison_reason']

    def test_cost_preview_never_names_the_sum_actual(self, tmp_path, monkeypatch):
        """The 2-of-6-phase sum is not published under the name `actual_tokens`."""
        plan_id = self._setup_cost_plan(
            tmp_path, monkeypatch, {'execution_profile': 'minimal'}
        )

        preview = _run_routing(plan_id).toon()['cost_preview']

        assert 'actual_tokens' not in preview

    def test_llm_judgement_boundary_no_posture_verdict_in_script(self, tmp_path, monkeypatch):
        """The script marks llm_judgement_required and emits NO posture verdict of its own."""
        plan_id, plan_dir = _setup_plan_with_manifest(
            tmp_path,
            monkeypatch,
            manifest_body=_manifest_with_steps_and_log(['push'], []),
            plan_id='routing-boundary',
        )
        _write_status_metadata(plan_dir, {'execution_profile': 'standard'})

        result = _run_routing(plan_id)

        data = result.toon()
        # The deterministic/LLM boundary: the script flags the judgement is the
        # LLM's and never emits a posture_verdict / OVER-UNDER verdict itself.
        assert data['llm_judgement_required'] is True
        assert 'posture_verdict' not in data
