#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the manage-execution-manifest pre-filters and finalize selection.

Covers:

- ``pre_push_quality_gate_inactive`` — re-pointed onto the centralized
  build-decision API (``extension_base.should_execute_build``). The pre-filter
  drops ``pre-push-quality-gate`` ONLY on the positive ``not_necessary`` verdict;
  ``build`` and ``unknown`` both KEEP it. The decision logic itself is
  exhaustively covered in ``manage-config/test_build_decision.py``; here we
  assert the consumer-site wiring (verdict → keep/drop).
- ``pre-submission-self-review``'s survival through compose. There is no
  footprint-gated pre-filter for this step: the vacuous
  ``pre_submission_self_review_inactive`` predicate (which structurally never
  fired) has been removed outright, so the step is subtracted only by
  ``commit_push_disabled`` when no push will occur.
- The six-row decision matrix's SUBTRACTION RECORDS: every narrowing row returns
  one ``{step, reason}`` record per candidate it removed, so a row can no longer
  narrow the candidate list silently.
- The absence of any bot-enforcement guard: ``automatic-review`` is governed
  purely by its configured candidacy / ``lane`` — compose never force-adds nor
  re-orders it.
- The task-queue-aware ``early_terminate`` predicate.
"""

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

import extension_base
import pytest

from conftest import PlanContext

# =============================================================================
# Module loading (script has hyphens in filename → load via importlib)
# =============================================================================

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-execution-manifest'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None, f'Failed to load module spec for {filename}'
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_mem = _load_module('_mem_script_decision_rules', 'manage-execution-manifest.py')
cmd_compose = _mem.cmd_compose
read_manifest = _mem.read_manifest
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS
_decide = _mem._decide

# Silence the best-effort decision-log subprocess in tests.
#
# Each assignment below MUST name an emitter that still exists. ``setattr`` on a
# module succeeds for a name that was never defined, so a stale entry here does
# not fail loudly — it silently resurrects a dead attribute and leaves a live
# reference to a removed function in the tree. ``TestNoRemovedSelfReviewSymbols``
# asserts the absence explicitly rather than relying on these patches to fail.
_mem._log_decision = lambda *a, **kw: None
_mem._log_commit_push_omitted = lambda *a, **kw: None
_mem._log_pre_push_quality_gate_omitted = lambda *a, **kw: None
_mem._log_pre_push_quality_gate_kept_unknown = lambda *a, **kw: None
_mem._emit_decision_log = lambda *a, **kw: None

# =============================================================================
# Helpers
# =============================================================================


def _phase_6_with_self_review() -> str:
    """Return the comma-separated default phase-6-finalize steps with pre-submission-self-review added."""
    steps = list(DEFAULT_PHASE_6_STEPS) + ['pre-submission-self-review']
    return ','.join(steps)


def _compose_ns(
    plan_id: str = 'test-plan',
    change_type: str = 'feature',
    track: str = 'complex',
    scope_estimate: str = 'multi_module',
    recipe_key: str | None = None,
    affected_files_count: int = 5,
    phase_5_steps: str | None = 'quality-gate,module-tests',
    phase_6_steps: str | None = None,
    commit_and_push: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track=track,
        scope_estimate=scope_estimate,
        recipe_key=recipe_key,
        affected_files_count=affected_files_count,
        phase_5_steps=phase_5_steps,
        phase_6_steps=phase_6_steps if phase_6_steps is not None else _phase_6_with_self_review(),
        commit_and_push=commit_and_push,
    )


def _seed_marshal(ci_provider: str | None = 'github') -> Path:
    """Write a minimal marshal.json at PLAN_BASE_DIR/marshal.json for the test.

    Pre-push-quality-gate activation derives from ``build.map``
    globs (D7/D8), so the seed carries a build_map entry whose ``**/*.py`` glob
    keeps the gate active against a matching footprint.
    """
    from file_ops import get_marshal_path

    marshal: dict = {
        'plan': {'phase-6-finalize': {}},
        'build': {
            'map': {
                'python': [
                    {'glob': '**/*.py', 'role': 'production', 'build_class': 'compile'},
                ],
            },
        },
    }
    if ci_provider:
        marshal['providers'] = [
            {'skill_name': f'plan-marshall:workflow-integration-{ci_provider}', 'category': 'ci'}
        ]
    marshal_path = get_marshal_path()
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(marshal, indent=2))
    return marshal_path


def _stub_footprint(footprint: list[str] | None) -> None:
    """Stub ``_resolve_footprint`` so the activation pre-filters see the given state.

    The composer derives the live plan footprint on demand via
    ``compute_plan_branch_diff`` rather than reading a seeded
    ``references.modified_files`` ledger. Tests inject the resolver's THREE-state
    return: ``None`` (unresolvable — no evidence), ``[]`` (resolvable and
    genuinely empty), or a non-empty path list. The module-scoped autouse
    ``_restore_footprint_resolver`` fixture restores the original after each test.
    """
    _mem._resolve_footprint = lambda plan_id: None if footprint is None else list(footprint)


# =============================================================================
# Test: pre-submission-self-review survival (the removed vacuous pre-filter)
# =============================================================================


@pytest.fixture(autouse=True)
def _restore_footprint_resolver():
    """Restore ``_resolve_footprint`` after any test that stubbed it.

    ``_stub_footprint`` replaces the module-level resolver in-place; this
    module-scoped autouse fixture snapshots and restores it so a stub installed
    by one test never leaks into the next.
    """
    original = _mem._resolve_footprint
    yield
    _mem._resolve_footprint = original


class TestPreSubmissionSelfReviewSurvivesCompose:
    """No footprint gate subtracts this step; only ``commit_push_disabled`` does.

    The ``pre_submission_self_review_inactive`` pre-filter was VACUOUS — it
    structurally returned ``(candidates, False)`` for every input, so no footprint
    state could ever drop the step — and has been removed outright along with its
    unreachable emitter and its always-``False`` compose-result key. These cases
    pin the surviving behaviour across all three footprint states, so a future
    re-introduction of a footprint gate here fails rather than silently dropping a
    review step the operator never opted out of.
    """

    def test_keeps_step_when_footprint_unresolvable(self, plan_context):
        """Early compose (no worktree yet) is no evidence — the step survives."""
        _seed_marshal(ci_provider=None)
        _stub_footprint(None)

        ns = _compose_ns(plan_id='qg-self-review-unresolvable')
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert 'pre-submission-self-review' in result_phase_6_steps(result)

    def test_keeps_step_when_footprint_resolvable_and_empty(self, plan_context):
        """A resolvable-but-empty footprint does not drop the step either."""
        _seed_marshal(ci_provider=None)
        _stub_footprint([])

        ns = _compose_ns(plan_id='qg-self-review-empty')
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert 'pre-submission-self-review' in result_phase_6_steps(result)

    def test_keeps_step_when_footprint_non_empty(self, plan_context):
        _seed_marshal(ci_provider=None)
        _stub_footprint(['marketplace/bundles/x/skills/y/SKILL.md'])

        ns = _compose_ns(plan_id='qg-self-review-active')
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert 'pre-submission-self-review' in result_phase_6_steps(result)

    def test_commit_and_push_false_strips_self_review(self, plan_context):
        """``commit_push_disabled`` is the ONE gate that still removes the step."""
        _seed_marshal(ci_provider=None)
        _stub_footprint(['some/file.py'])

        ns = _compose_ns(plan_id='qg-self-review-no-push', commit_and_push='false')
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        steps = result_phase_6_steps(result)
        assert 'push' not in steps
        assert 'pre-push-quality-gate' not in steps
        assert 'pre-submission-self-review' not in steps

    def test_commit_push_drop_is_reported_per_step(self, plan_context):
        """Every dropped step is named, not just ``push``.

        The former aggregate reporting named only ``push``, so the two push-only
        gates vanished unnamed. Each drop now carries its own ``{step, reason}``
        record with a non-empty reason.

        The candidate CSV is built explicitly to carry all three droppable steps:
        the gate removes the INTERSECTION of its drop set with the candidates, and
        the default candidate list happens to contain only ``push`` — which is
        precisely why an aggregate line looked sufficient for so long.
        """
        _seed_marshal(ci_provider=None)
        _stub_footprint(['some/file.py'])

        candidates = list(DEFAULT_PHASE_6_STEPS)
        for extra in ('pre-push-quality-gate', 'pre-submission-self-review'):
            if extra not in candidates:
                candidates.insert(candidates.index('push'), extra)

        ns = _compose_ns(
            plan_id='qg-self-review-records',
            commit_and_push='false',
            phase_6_steps=','.join(candidates),
        )
        result = cmd_compose(ns)

        assert result is not None
        dropped = result['commit_push_dropped']
        assert {record['step'] for record in dropped} == {
            'push',
            'pre-push-quality-gate',
            'pre-submission-self-review',
        }
        assert all(record['reason'] for record in dropped)

    def test_commit_push_dropped_is_empty_when_pushing(self, plan_context):
        """The complementary direction: nothing is dropped when a push will occur."""
        _seed_marshal(ci_provider=None)
        _stub_footprint(['some/file.py'])

        ns = _compose_ns(plan_id='qg-self-review-pushing', commit_and_push='true')
        result = cmd_compose(ns)

        assert result is not None
        assert result['commit_push_dropped'] == []


class TestNoRemovedSelfReviewSymbols:
    """The clean break left NO reference behind, in production or in test setup.

    Asserted explicitly rather than inferred from a monkeypatch failing, because
    ``setattr`` on a module SUCCEEDS for a name that no longer exists: a stale
    ``_mem._log_pre_submission_self_review_omitted = ...`` line in a test's setup
    would quietly re-create the dead attribute and this suite would never notice.
    """

    def test_removed_symbols_are_absent_from_the_module(self):
        for symbol in (
            '_apply_pre_submission_self_review_inactive',
            '_log_pre_submission_self_review_omitted',
        ):
            assert not hasattr(_mem, symbol), (
                f'{symbol} was removed in the clean break; a surviving attribute means '
                'some test setup re-created it via setattr'
            )

    def test_removed_compose_result_key_is_absent(self, plan_context):
        """The always-``False`` ``pre_submission_self_review_omitted`` key is gone."""
        _seed_marshal(ci_provider=None)
        _stub_footprint(['some/file.py'])

        ns = _compose_ns(plan_id='qg-self-review-nokey')
        result = cmd_compose(ns)

        assert result is not None
        assert 'pre_submission_self_review_omitted' not in result


# =============================================================================
# Test: pre_push_quality_gate_inactive pre-filter (build-decision consumer site)
# =============================================================================


class TestPrePushQualityGateInactive:
    """The pre-filter consumes ``extension_base.should_execute_build``'s verdict.

    The build-necessity decision was centralized into
    ``extension_base.should_execute_build`` (Axis-B strip: the four former
    consumer sites no longer each re-derive it). ``_apply_pre_push_quality_gate_inactive``
    is now a thin consumer over the THREE-value verdict vocabulary: it drops
    ``pre-push-quality-gate`` only on the positive ``not_necessary`` answer, and
    KEEPS it on both ``build`` (a real build is needed) and ``unknown`` (no
    evidence either way). The pre-filter imports ``should_execute_build`` from
    ``extension_base`` at call time, so patching it on the ``extension_base``
    module object is what the pre-filter observes. The decision logic itself is
    covered in ``manage-config/test_build_decision.py``; these tests assert only
    the consumer-site wiring.
    """

    def _phase_6_with_pre_push_quality_gate(self) -> str:
        """Default phase-6 steps with ``pre-push-quality-gate`` spliced in.

        ``DEFAULT_PHASE_6_STEPS`` does not carry the gate, so a test that wants
        to exercise the pre-filter must inject it into the candidate set.
        """
        steps = list(DEFAULT_PHASE_6_STEPS)
        steps.insert(steps.index('push'), 'pre-push-quality-gate')
        return ','.join(steps)

    def test_keeps_gate_when_verdict_is_build(self, plan_context, monkeypatch):
        """A ``build`` verdict keeps ``pre-push-quality-gate`` in phase_6.steps."""
        _seed_marshal(ci_provider=None)
        _stub_footprint(['scripts/foo.py'])
        monkeypatch.setattr(
            extension_base,
            'should_execute_build',
            lambda command, plan_id, project_root=None: {
                'decision': 'build',
                'canonical_command': command,
            },
        )

        ns = _compose_ns(
            plan_id='qg-pre-push-build',
            phase_6_steps=self._phase_6_with_pre_push_quality_gate(),
        )
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert result['pre_push_quality_gate_omitted'] is False
        assert 'pre-push-quality-gate' in result_phase_6_steps(result)

    def test_drops_gate_when_verdict_is_not_necessary(self, plan_context, monkeypatch):
        """A ``not_necessary`` verdict drops ``pre-push-quality-gate``."""
        _seed_marshal(ci_provider=None)
        _stub_footprint(['README.md'])
        monkeypatch.setattr(
            extension_base,
            'should_execute_build',
            lambda command, plan_id, project_root=None: {
                'decision': 'not_necessary',
                'reason': 'plan footprint touches no build_map glob',
                'canonical_command': command,
            },
        )

        ns = _compose_ns(
            plan_id='qg-pre-push-not-necessary',
            phase_6_steps=self._phase_6_with_pre_push_quality_gate(),
        )
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert result['pre_push_quality_gate_omitted'] is True
        assert 'pre-push-quality-gate' not in result_phase_6_steps(result)

    def test_keeps_gate_when_verdict_is_unknown(self, plan_context, monkeypatch):
        """An ``unknown`` verdict KEEPS the gate — fail toward inclusion.

        The load-bearing regression for Defect B's consumer site. An unresolvable
        footprint is the normal state at phase-4-plan compose; reading it as a
        positive "nothing to build" answer is what silently dropped a quality gate
        the operator never opted out of. ADR-009 (an unsubstantiated verdict must
        not read as a positive one) and ADR-004 (the composer may not re-derive
        build necessity from any other signal) both require the keep.
        """
        _seed_marshal(ci_provider=None)
        _stub_footprint(None)
        monkeypatch.setattr(
            extension_base,
            'should_execute_build',
            lambda command, plan_id, project_root=None: {
                'decision': 'unknown',
                'reason': 'plan footprint unresolvable — worktree not yet materialised',
                'canonical_command': command,
            },
        )

        ns = _compose_ns(
            plan_id='qg-pre-push-unknown',
            phase_6_steps=self._phase_6_with_pre_push_quality_gate(),
        )
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert result['pre_push_quality_gate_omitted'] is False
        assert result['build_verdict_decision'] == 'unknown'
        assert 'pre-push-quality-gate' in result_phase_6_steps(result)

    def test_unknown_and_not_necessary_diverge_on_the_same_gate(self, plan_context, monkeypatch):
        """Only the verdict differs, and only ``not_necessary`` drops the gate.

        The paired assertion that pins the consumer reads the decision VALUE
        rather than "anything that is not ``build``" — the shape that would
        collapse ``unknown`` back into a drop.
        """
        _seed_marshal(ci_provider=None)
        _stub_footprint(None)

        def _verdict(decision):
            return lambda command, plan_id, project_root=None: {
                'decision': decision,
                'reason': f'{decision} for test',
                'canonical_command': command,
            }

        monkeypatch.setattr(extension_base, 'should_execute_build', _verdict('unknown'))
        kept = cmd_compose(
            _compose_ns(
                plan_id='qg-pre-push-diverge-unknown',
                phase_6_steps=self._phase_6_with_pre_push_quality_gate(),
            )
        )
        monkeypatch.setattr(extension_base, 'should_execute_build', _verdict('not_necessary'))
        dropped = cmd_compose(
            _compose_ns(
                plan_id='qg-pre-push-diverge-not-necessary',
                phase_6_steps=self._phase_6_with_pre_push_quality_gate(),
            )
        )

        assert 'pre-push-quality-gate' in result_phase_6_steps(kept)
        assert 'pre-push-quality-gate' not in result_phase_6_steps(dropped)

    def test_no_op_when_gate_absent_from_candidates(self, plan_context, monkeypatch):
        """The pre-filter is a no-op (and never calls the decision) when the gate
        is already absent from the candidate set — e.g. already stripped by
        ``commit_and_push=false``."""
        _seed_marshal(ci_provider=None)
        _stub_footprint(['scripts/foo.py'])

        def _should_not_be_called(*_a, **_kw):
            raise AssertionError('should_execute_build must not run when the gate is absent')

        monkeypatch.setattr(extension_base, 'should_execute_build', _should_not_be_called)

        # Default candidate set carries no pre-push-quality-gate.
        ns = _compose_ns(plan_id='qg-pre-push-absent')
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert result['pre_push_quality_gate_omitted'] is False
        assert 'pre-push-quality-gate' not in result_phase_6_steps(result)


# =============================================================================
# Test: the six-row matrix reports every subtraction it makes
# =============================================================================


class TestDecideSubtractionRecords:
    """Every narrowing row returns one ``{step, reason}`` record per removal.

    Five of the six matrix rows narrow a candidate list, and every one of them
    used to do it SILENTLY — the row returned only the body and its rule name, so
    a step the matrix removed left no trace an operator could read. The third
    return value closes that: the matrix's DECISIONS are unchanged, only their
    observability is.

    Each case therefore asserts the record set against the actual difference
    between the candidates it passed in and the steps that came out, rather than
    against a hand-written expected list. Deriving the expectation from the
    row's own output is what keeps these from degenerating into a restatement of
    the implementation — a row that stopped narrowing, or narrowed more, fails.
    """

    _PHASE_5 = ['quality-gate', 'module-tests', 'coverage']
    _PHASE_6 = ['push', 'ci-wait', 'lessons-capture', 'adr-propose', 'archive-plan', 'create-pr']

    def _decide_with(self, **overrides):
        kwargs = {
            'change_type': 'feature',
            'track': 'complex',
            'scope_estimate': 'multi_module',
            'recipe_key': None,
            'affected_files_count': 5,
            'phase_5_candidates': list(self._PHASE_5),
            'phase_6_candidates': list(self._PHASE_6),
        }
        kwargs.update(overrides)
        return _decide(**kwargs)

    @staticmethod
    def _assert_records_match_the_removals(body, dropped, phase_5_in, phase_6_in):
        """Assert the record set is exactly what the row actually removed.

        Derived from the row's own kept lists, so the assertion cannot drift into
        a copy of the implementation's hardcoded reason sets.
        """
        removed = [s for s in phase_5_in if s not in body['phase_5']['verification_steps']]
        removed += [s for s in phase_6_in if s not in body['phase_6']['steps']]
        assert [record['step'] for record in dropped] == removed
        assert all(record['reason'] for record in dropped), 'every record needs a non-empty reason'

    def test_early_terminate_analysis_records_every_drop(self):
        """Rule 1 empties phase-5 outright and narrows phase-6 to the analysis minimum."""
        body, rule, dropped = self._decide_with(change_type='analysis', affected_files_count=0)

        assert rule == 'early_terminate_analysis'
        self._assert_records_match_the_removals(body, dropped, self._PHASE_5, self._PHASE_6)
        # Every phase-5 candidate is removed, so each must be individually named.
        assert {r['step'] for r in dropped} >= set(self._PHASE_5)

    def test_recipe_row_records_every_drop(self):
        """Rule 2 narrows phase-5 to the core verify roles and drops legacy ci-wait."""
        body, rule, dropped = self._decide_with(recipe_key='recipe-surgical-fix')

        assert rule == 'recipe'
        self._assert_records_match_the_removals(body, dropped, self._PHASE_5, self._PHASE_6)
        assert 'ci-wait' in {r['step'] for r in dropped}

    def test_tests_only_row_records_every_drop(self):
        """Rule 4 narrows phase-5 to the module-tests role and leaves phase-6 whole."""
        body, rule, dropped = self._decide_with(change_type='verification', affected_files_count=3)

        assert rule == 'tests_only'
        self._assert_records_match_the_removals(body, dropped, self._PHASE_5, self._PHASE_6)
        assert body['phase_6']['steps'] == self._PHASE_6

    def test_surgical_bug_fix_row_records_every_drop(self):
        """Rule 5 narrows both phases, and the reason names the firing rule."""
        body, rule, dropped = self._decide_with(
            change_type='bug_fix', scope_estimate='surgical'
        )

        assert rule == 'surgical_bug_fix'
        self._assert_records_match_the_removals(body, dropped, self._PHASE_5, self._PHASE_6)
        assert all('surgical_bug_fix' in record['reason'] for record in dropped)

    def test_verification_no_files_row_records_every_drop(self):
        """Rule 6 narrows phase-6 to the analysis minimum and keeps phase-5 whole."""
        body, rule, dropped = self._decide_with(
            change_type='verification', affected_files_count=0
        )

        assert rule == 'verification_no_files'
        self._assert_records_match_the_removals(body, dropped, self._PHASE_5, self._PHASE_6)
        assert body['phase_5']['verification_steps'] == self._PHASE_5

    def test_default_row_narrows_nothing_and_records_nothing(self):
        """Rule 7 is the safe baseline: no subtraction, so no records.

        The negative case matters as much as the positives — a helper that
        emitted a record per candidate regardless of removal would pass every
        test above and fail only here.
        """
        body, rule, dropped = self._decide_with()

        assert rule == 'default'
        assert dropped == []
        assert body['phase_5']['verification_steps'] == self._PHASE_5
        assert body['phase_6']['steps'] == self._PHASE_6

    def test_records_are_surfaced_on_the_compose_result(self, plan_context):
        """The records reach the compose result, not just ``_decide``'s return.

        The end-to-end half: a record list that never left the matrix would leave
        the drop just as invisible to an operator as before.
        """
        _seed_marshal(ci_provider=None)
        _stub_footprint(['some/file.py'])

        ns = _compose_ns(
            plan_id='qg-decide-records',
            change_type='bug_fix',
            scope_estimate='surgical',
            phase_5_steps='quality-gate,module-tests,coverage',
        )
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        records = result['decision_matrix_dropped']
        assert records, 'a narrowing row must surface its records on the compose result'
        assert all(record['step'] and record['reason'] for record in records)


# =============================================================================
# Test: no bot-enforcement guard — automatic-review governed by candidacy/lane
# =============================================================================


class TestNoBotEnforcementGuard:
    """The bot-enforcement guard (and its placement-validator twin) are removed.

    ``automatic-review`` is governed purely by its configured candidacy / ``lane``
    — compose never force-adds it back on GitHub/GitLab plans and never emits a
    ``bot_enforcement_violation`` error. Its presence tracks the candidate list and
    the lane resolution exactly.
    """

    def test_no_bot_enforcement_symbols_survive(self):
        """No bot-enforcement guard / placement-validator symbol remains on the module."""
        for symbol in (
            '_apply_bot_enforcement_guard',
            '_bot_enforcement_insert_index',
            '_validate_automatic_review_placement',
            '_log_bot_enforcement_guard_fired',
            '_log_bot_enforcement_guard_remediated',
            '_log_bot_enforcement_placement_violation',
        ):
            assert not hasattr(_mem, symbol), f'{symbol} must be deleted with the bot-enforcement guard'

    def test_github_plan_does_not_force_add_dropped_automatic_review(self, plan_context):
        _seed_marshal(ci_provider='github')
        _stub_footprint(['some/file.py'])

        # Candidate set EXCLUDES automatic-review; with no guard it stays absent.
        phase_6 = ','.join(s for s in DEFAULT_PHASE_6_STEPS if s != 'automatic-review')
        ns = _compose_ns(plan_id='qg-bot-github', phase_6_steps=phase_6)
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert result.get('error') != 'bot_enforcement_violation'
        assert 'automatic-review' not in result_phase_6_steps(result)

    def test_gitlab_plan_does_not_force_add_dropped_automatic_review(self, plan_context):
        _seed_marshal(ci_provider='gitlab')
        _stub_footprint(['some/file.py'])

        phase_6 = ','.join(s for s in DEFAULT_PHASE_6_STEPS if s != 'automatic-review')
        ns = _compose_ns(plan_id='qg-bot-gitlab', phase_6_steps=phase_6)
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert result.get('error') != 'bot_enforcement_violation'
        assert 'automatic-review' not in result_phase_6_steps(result)

    def test_present_when_in_candidates(self, plan_context):
        _seed_marshal(ci_provider='github')
        _stub_footprint(['some/file.py'])

        # multi_module feature keeps automatic-review (present in default candidates).
        ns = _compose_ns(plan_id='qg-bot-present')
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert 'automatic-review' in result_phase_6_steps(result)

    def test_absent_for_non_ci_plan_stays_absent(self, plan_context):
        _seed_marshal(ci_provider=None)
        _stub_footprint(['some/file.py'])

        phase_6 = ','.join(s for s in DEFAULT_PHASE_6_STEPS if s != 'automatic-review')
        ns = _compose_ns(plan_id='qg-bot-other', phase_6_steps=phase_6)
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert 'automatic-review' not in result_phase_6_steps(result)


# =============================================================================
# Helpers — read manifest after a successful compose
# =============================================================================


def result_phase_6_steps(result: dict) -> list[str]:
    """Read the persisted manifest after a successful compose and return phase_6.steps."""
    plan_id = result['plan_id']
    manifest = read_manifest(plan_id)
    assert manifest is not None
    return list(manifest.get('phase_6', {}).get('steps', []))


# =============================================================================
# Test: task-queue-aware early_terminate predicate (lesson 2026-05-24-17-001)
# =============================================================================


def _seed_task_file(plan_id: str, task_number: int, status: str) -> None:
    """Write a minimal TASK-{NNN}.json with the given status under the plan's tasks/ dir.

    Used to exercise the composer's task-queue read: Rule 1's
    ``early_terminate`` predicate now ANDs the existing
    ``affected_files_count==0`` condition with "no pending or in-progress task
    on disk". A test that seeds at least one pending task forces the
    short-circuit to fall through to Rule 7 (default).
    """
    from file_ops import get_plan_dir

    tasks_dir = get_plan_dir(plan_id) / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        'number': task_number,
        'title': f'stub task {task_number}',
        'status': status,
        'steps': [],
    }
    (tasks_dir / f'TASK-{task_number:03d}.json').write_text(json.dumps(payload, indent=2))


class TestEarlyTerminateTaskQueueGuard:
    """Rule 1 (early_terminate_analysis) now requires the task queue to be empty.

    Lesson ``2026-05-24-17-001``: an analysis-only plan that produces zero
    affected files but still queues at least one deliverable task must NOT
    short-circuit phase-5 before TASK-001 runs. The composer reads
    ``tasks/TASK-*.json`` directly and ANDs the existing
    ``affected_files_count==0`` condition with "no pending or in-progress
    task". Genuine no-op plans (no task files on disk) preserve the prior
    early-terminate behaviour.
    """

    def test_early_terminate_when_task_queue_empty(self):
        """Case (i): analysis + affected_files=0 + task_queue empty → early_terminate=True."""
        with PlanContext('et-queue-empty'):
            # No tasks/TASK-*.json seeded — queue is empty.
            ns = _compose_ns(
                plan_id='et-queue-empty',
                change_type='analysis',
                scope_estimate='none',
                affected_files_count=0,
            )
            result = cmd_compose(ns)
            assert result is not None
            assert result['rule_fired'] == 'early_terminate_analysis'
            assert result['phase_5']['early_terminate'] is True

    def test_falls_through_to_default_when_task_queue_non_empty(self):
        """Case (ii): analysis + affected_files=0 + task_queue pending → Rule 7 default."""
        with PlanContext('et-queue-pending'):
            _seed_task_file('et-queue-pending', task_number=1, status='pending')
            ns = _compose_ns(
                plan_id='et-queue-pending',
                change_type='analysis',
                scope_estimate='none',
                affected_files_count=0,
            )
            result = cmd_compose(ns)
            assert result is not None
            assert result['rule_fired'] == 'default'
            assert result['phase_5']['early_terminate'] is False

    def test_rule_label_preserved_for_genuine_early_terminate(self):
        """Case (iii): the ``early_terminate_analysis`` rule label still appears for case (i)."""
        with PlanContext('et-queue-label'):
            ns = _compose_ns(
                plan_id='et-queue-label',
                change_type='analysis',
                scope_estimate='none',
                affected_files_count=0,
            )
            result = cmd_compose(ns)
            assert result is not None
            assert result['rule_fired'] == 'early_terminate_analysis'

    def test_falls_through_when_task_queue_in_progress(self):
        """An in_progress task also blocks the short-circuit (symmetric to pending)."""
        with PlanContext('et-queue-inprogress'):
            _seed_task_file('et-queue-inprogress', task_number=1, status='in_progress')
            ns = _compose_ns(
                plan_id='et-queue-inprogress',
                change_type='analysis',
                scope_estimate='none',
                affected_files_count=0,
            )
            result = cmd_compose(ns)
            assert result is not None
            assert result['rule_fired'] == 'default'
            assert result['phase_5']['early_terminate'] is False

    def test_done_tasks_do_not_block_short_circuit(self):
        """A queue containing ONLY done tasks does NOT block early_terminate."""
        with PlanContext('et-queue-done'):
            _seed_task_file('et-queue-done', task_number=1, status='done')
            ns = _compose_ns(
                plan_id='et-queue-done',
                change_type='analysis',
                scope_estimate='none',
                affected_files_count=0,
            )
            result = cmd_compose(ns)
            assert result is not None
            assert result['rule_fired'] == 'early_terminate_analysis'
            assert result['phase_5']['early_terminate'] is True


# =============================================================================
# Test: security_class_inactive pre-filter (direct helper unit coverage)
#
# ``_apply_security_class_inactive`` is NOT the peer of
# ``_apply_simplify_inactive`` — it shares no helper and no gate. It drops a
# security-class step (the caller-derived population) from the phase-6 candidate
# list ONLY when ``affected_files_count == 0`` AND ``live_footprint_count == 0``.
# There is no ``change_type`` leg, so the gate fails toward INCLUSION: an unknown
# or misleading change shape keeps the security sweep. These tests exercise the
# helper directly (no compose round-trip) so the gate's truth table, the
# population contract, and the no-op-when-absent contract are pinned at the unit
# boundary. See standards/decision-rules.md § Pre-Filter: security_class_inactive.
# =============================================================================


_apply_security_class_inactive = _mem._apply_security_class_inactive

_SECURITY_CLASS = frozenset({'finalize-step-security-audit'})


class TestSecurityClassInactivePreFilter:
    """Direct unit coverage of the ``security_class_inactive`` pre-filter helper."""

    @pytest.mark.parametrize(
        'affected_files_count,live_footprint_count,expect_present,expect_dropped_count',
        [
            # Either change-surface signal being non-empty keeps the step.
            (5, 3, True, 0),
            (5, 0, True, 0),
            (0, 3, True, 0),
            (1, 0, True, 0),
            (0, 1, True, 0),
            # Only the genuine no-change-surface case drops it.
            (0, 0, False, 1),
        ],
    )
    def test_gate_truth_table(
        self,
        affected_files_count,
        live_footprint_count,
        expect_present,
        expect_dropped_count,
    ):
        candidates = ['finalize-step-security-audit', 'push', 'archive-plan']
        kept, dropped = _apply_security_class_inactive(
            candidates, _SECURITY_CLASS, affected_files_count, live_footprint_count
        )
        assert len(dropped) == expect_dropped_count
        assert ('finalize-step-security-audit' in kept) is expect_present
        # Non-target candidates are never disturbed.
        assert 'push' in kept
        assert 'archive-plan' in kept

    @pytest.mark.parametrize('change_type', ['analysis', 'verification', 'feature', 'bug_fix'])
    def test_change_type_is_not_an_input_at_all(self, change_type):
        # The helper's signature carries no change_type parameter — the regression
        # this gate exists to prevent is a security sweep dropped on a semantic
        # outline-time label. Passing a change-shape-bearing candidate set with a
        # non-zero surface must keep the step whatever the plan's change_type is,
        # which the absent parameter makes structurally true.
        assert 'change_type' not in _apply_security_class_inactive.__code__.co_varnames
        kept, dropped = _apply_security_class_inactive(
            ['finalize-step-security-audit'], _SECURITY_CLASS, 4, 0
        )
        assert kept == ['finalize-step-security-audit']
        assert dropped == []

    def test_drop_record_names_step_and_reason(self):
        kept, dropped = _apply_security_class_inactive(
            ['finalize-step-security-audit', 'push'], _SECURITY_CLASS, 0, 0
        )
        assert kept == ['push']
        assert dropped == [
            {
                'step': 'finalize-step-security-audit',
                'reason': 'no declared affected files and empty live footprint',
            }
        ]

    def test_population_is_caller_derived_not_a_step_id_literal(self):
        # A second security-class member is dropped by the same call, and a
        # non-member sharing no persona is not — proving the helper reads the
        # supplied population rather than a hardcoded id.
        population = frozenset({'finalize-step-security-audit', 'finalize-step-other-security'})
        candidates = [
            'finalize-step-security-audit',
            'finalize-step-other-security',
            'finalize-step-simplify',
        ]
        kept, dropped = _apply_security_class_inactive(candidates, population, 0, 0)
        assert kept == ['finalize-step-simplify']
        assert {record['step'] for record in dropped} == population

    def test_no_op_when_no_security_class_step_in_candidates(self):
        # No population member is present → nothing to drop even in the
        # zero-change-surface case.
        candidates = ['push', 'archive-plan']
        kept, dropped = _apply_security_class_inactive(candidates, _SECURITY_CLASS, 0, 0)
        assert dropped == []
        assert kept == candidates

    def test_returns_new_list_on_drop_not_mutating_input(self):
        # The drop branch must not mutate the caller's candidate list in place.
        candidates = ['finalize-step-security-audit', 'push']
        kept, dropped = _apply_security_class_inactive(candidates, _SECURITY_CLASS, 0, 0)
        assert len(dropped) == 1
        assert 'finalize-step-security-audit' not in kept
        # Input list is untouched.
        assert candidates == ['finalize-step-security-audit', 'push']


# =============================================================================
# Test: unresolved_ask_provider_drop pre-filter (D6, direct helper coverage)
#
# ``_apply_unresolved_ask_provider_drop`` drops an UNRESOLVED ``lane:ask`` infra
# element (automatic-review / sonar-roundtrip) from the phase-6 candidate list
# when its provider is absent. The seed lane for both elements is ``ask``; a
# steward answer overwrites the override to off/standard/full, so an effective tier
# still equal to ``ask`` at compose is the unresolved case. These tests exercise
# the pure helper directly (no compose round-trip) so the full truth table and
# the no-op contracts are pinned at the unit boundary. See
# standards/decision-rules.md § Pre-Filter: unresolved_ask_provider_drop.
# =============================================================================


_apply_unresolved_ask_provider_drop = _mem._apply_unresolved_ask_provider_drop
_read_sonar_provider = _mem._read_sonar_provider


def _override_map(ar_lane: str | None = None, sr_lane: str | None = None) -> dict[str, dict]:
    """Build a marshal-style phase-6 step map with per-element lane overrides.

    Keys mirror the seeded marshal shape: ``plan-marshall:automatic-review`` and
    ``default:sonar-roundtrip`` (the D1 seed keys). Only elements with a non-None
    lane are included.
    """
    m: dict[str, dict] = {}
    if ar_lane is not None:
        m['plan-marshall:automatic-review'] = {'lane': ar_lane}
    if sr_lane is not None:
        m['default:sonar-roundtrip'] = {'lane': sr_lane}
    return m


class TestUnresolvedAskProviderDropPreFilter:
    """Direct unit coverage of the D6 unresolved-ask provider-drop pre-filter."""

    @pytest.mark.parametrize(
        'ar_lane,ci_provider,expect_present',
        [
            ('ask', None, False),      # unresolved ask + no CI provider → DROP
            ('ask', 'github', True),   # unresolved ask + CI provider → keep
            ('ask', 'gitlab', True),   # provider identity is irrelevant — any non-None keeps
            ('auto', None, True),      # resolved auto (steward answered) → keep even w/o provider
            ('full', None, True),      # resolved full → keep even w/o provider
            ('off', None, True),       # off is resolved; the later lane pass drops it, not this one
        ],
    )
    def test_automatic_review_truth_table(self, ar_lane, ci_provider, expect_present):
        candidates = ['plan-marshall:automatic-review', 'push', 'archive-plan']
        kept, dropped = _apply_unresolved_ask_provider_drop(
            candidates, _override_map(ar_lane=ar_lane), ci_provider, None
        )
        assert ('plan-marshall:automatic-review' in kept) is expect_present
        assert ('plan-marshall:automatic-review' in dropped) is (not expect_present)
        # Non-infra candidates are never disturbed.
        assert 'push' in kept and 'archive-plan' in kept

    @pytest.mark.parametrize(
        'sr_lane,sonar_provider,expect_present',
        [
            ('ask', None, False),      # unresolved ask + no Sonar provider → DROP
            ('ask', 'sonar', True),    # unresolved ask + Sonar provider → keep
            ('auto', None, True),      # resolved auto → keep even w/o provider
            ('full', None, True),      # resolved full → keep even w/o provider
            ('off', None, True),       # off is resolved; dropped later by the lane pass, not here
        ],
    )
    def test_sonar_roundtrip_truth_table(self, sr_lane, sonar_provider, expect_present):
        # The candidate list is boundary-normalized in compose (``default:`` is
        # stripped), so the helper is given the bare ``sonar-roundtrip`` form.
        candidates = ['sonar-roundtrip', 'push']
        kept, dropped = _apply_unresolved_ask_provider_drop(
            candidates, _override_map(sr_lane=sr_lane), None, sonar_provider
        )
        assert ('sonar-roundtrip' in kept) is expect_present
        assert ('sonar-roundtrip' in dropped) is (not expect_present)
        assert 'push' in kept

    def test_both_unresolved_no_providers_drop_both(self):
        candidates = ['plan-marshall:automatic-review', 'sonar-roundtrip', 'push']
        kept, dropped = _apply_unresolved_ask_provider_drop(
            candidates, _override_map(ar_lane='ask', sr_lane='ask'), None, None
        )
        assert kept == ['push']
        assert set(dropped) == {'plan-marshall:automatic-review', 'sonar-roundtrip'}

    def test_provider_isolation_ci_present_sonar_absent(self):
        # A configured CI provider keeps automatic-review; an absent Sonar
        # provider still drops an unresolved sonar-roundtrip. The two elements
        # are keyed to distinct providers.
        candidates = ['plan-marshall:automatic-review', 'sonar-roundtrip']
        kept, dropped = _apply_unresolved_ask_provider_drop(
            candidates, _override_map(ar_lane='ask', sr_lane='ask'), 'github', None
        )
        assert kept == ['plan-marshall:automatic-review']
        assert dropped == ['sonar-roundtrip']

    def test_no_override_keeps_infra_elements(self):
        # No marshal override at all (e.g. CSV-fallback, marshal_map None/empty):
        # the effective tier is undeterminable, not ``ask``, so nothing is dropped
        # (conservative keep).
        candidates = ['plan-marshall:automatic-review', 'sonar-roundtrip']
        for override_map in ({}, None):
            kept, dropped = _apply_unresolved_ask_provider_drop(candidates, override_map, None, None)
            assert dropped == []
            assert kept == candidates

    def test_non_infra_elements_pass_through_untouched(self):
        candidates = ['push', 'archive-plan', 'finalize-step-simplify']
        kept, dropped = _apply_unresolved_ask_provider_drop(
            candidates, _override_map(ar_lane='ask'), None, None
        )
        assert kept == candidates
        assert dropped == []

    def test_does_not_mutate_input_list(self):
        candidates = ['plan-marshall:automatic-review', 'push']
        _apply_unresolved_ask_provider_drop(
            candidates, _override_map(ar_lane='ask'), None, None
        )
        assert candidates == ['plan-marshall:automatic-review', 'push']


# =============================================================================
# Test: scope_gated_finalize declared-lane immunity (direct helper coverage)
#
# The implicit scope gate must never silently override an explicit per-element
# ``lane`` declaration. The rule is load-bearing because the pre-filter runs at
# the candidate-narrowing stage — before ceremony selection and before lane
# resolution — and the ceremony ``always`` re-add path covers only the four
# ceremony gates. For any other step (canonically
# ``plan-marshall:plan-retrospective``) a drop here makes the declared lane
# structurally UNREACHABLE, not merely outvoted. See standards/decision-rules.md
# § Pre-Filter: scope_gated_finalize.
# =============================================================================


_apply_scope_gated_finalize = _mem._apply_scope_gated_finalize
_has_declared_lane_override = _mem._has_declared_lane_override

_RETROSPECTIVE = 'plan-marshall:plan-retrospective'


def _lane_map(step_id: str, lane: str) -> dict[str, dict]:
    """Build a marshal-style phase-6 step map declaring one element's lane."""
    return {step_id: {'lane': lane}}


class TestHasDeclaredLaneOverride:
    """The predicate backing declared-lane immunity."""

    @pytest.mark.parametrize(
        'lane,expected',
        [
            ('minimal', True),
            ('full', True),
            ('off', True),
            ('ask', True),
            # ``auto`` is the DEFER value — it declares no override intent, so
            # the implicit machinery keeps its say.
            ('auto', False),
        ],
    )
    def test_non_auto_override_counts_as_declared(self, lane, expected):
        assert _has_declared_lane_override(_RETROSPECTIVE, _lane_map(_RETROSPECTIVE, lane)) is expected

    def test_absent_override_is_not_declared(self):
        assert _has_declared_lane_override(_RETROSPECTIVE, {}) is False

    def test_absent_marshal_map_is_not_declared(self):
        # CSV-fallback compose path — no declaration can exist, so nothing is immune.
        assert _has_declared_lane_override(_RETROSPECTIVE, None) is False

    def test_invalid_override_value_is_not_declared(self):
        # ``_lane_override_for`` only returns a value from the closed override
        # vocabulary, so a junk value reads as no declaration at all.
        assert _has_declared_lane_override(_RETROSPECTIVE, _lane_map(_RETROSPECTIVE, 'bogus')) is False

    def test_declaration_matches_across_default_prefix(self):
        # Marshal keys preserve prefixes while candidates are bare-normalized;
        # the lookup strips ``default:`` from the KEY before comparing.
        assert _has_declared_lane_override(
            'pre-submission-self-review',
            _lane_map('default:pre-submission-self-review', 'minimal'),
        ) is True


class TestScopeGatedFinalizeDeclaredLaneImmunity:
    """``_apply_scope_gated_finalize`` honours an explicit lane declaration."""

    def test_single_module_drops_retrospective_without_declaration(self):
        candidates = [_RETROSPECTIVE, 'push', 'archive-plan']
        kept, dropped, immune = _apply_scope_gated_finalize(candidates, 'single_module', None)
        assert _RETROSPECTIVE not in kept
        assert dropped == [_RETROSPECTIVE]
        assert immune == []
        assert kept == ['push', 'archive-plan']

    def test_single_module_keeps_retrospective_with_declared_lane(self):
        # The regression: an operator's ``lane: minimal`` on plan-retrospective
        # must survive a single_module compose. Before declared-lane immunity the
        # step was dropped here and — having no ceremony re-add path — its
        # declared lane was never reachable.
        candidates = [_RETROSPECTIVE, 'push']
        kept, dropped, immune = _apply_scope_gated_finalize(
            candidates, 'single_module', _lane_map(_RETROSPECTIVE, 'minimal')
        )
        assert _RETROSPECTIVE in kept
        assert dropped == []
        assert immune == [_RETROSPECTIVE]

    def test_surgical_keeps_every_declared_step_and_drops_the_rest(self):
        candidates = [_RETROSPECTIVE, 'pre-submission-self-review', 'project:finalize-step-plugin-doctor', 'push']
        kept, dropped, immune = _apply_scope_gated_finalize(
            candidates, 'surgical', _lane_map('pre-submission-self-review', 'minimal')
        )
        assert 'pre-submission-self-review' in kept
        assert immune == ['pre-submission-self-review']
        assert set(dropped) == {_RETROSPECTIVE, 'project:finalize-step-plugin-doctor'}
        assert 'push' in kept

    def test_auto_declaration_does_not_confer_immunity(self):
        # ``auto`` is the defer value, so the implicit gate still drops.
        candidates = [_RETROSPECTIVE, 'push']
        kept, dropped, immune = _apply_scope_gated_finalize(
            candidates, 'single_module', _lane_map(_RETROSPECTIVE, 'standard')
        )
        assert _RETROSPECTIVE not in kept
        assert dropped == [_RETROSPECTIVE]
        assert immune == []

    @pytest.mark.parametrize('scope_estimate', ['none', 'multi_module', 'broad'])
    def test_non_scope_gated_estimates_never_subtract(self, scope_estimate):
        candidates = [_RETROSPECTIVE, 'push']
        kept, dropped, immune = _apply_scope_gated_finalize(candidates, scope_estimate, None)
        assert kept == candidates
        assert dropped == []
        assert immune == []

    def test_immune_step_keeps_its_list_position(self):
        candidates = ['push', _RETROSPECTIVE, 'archive-plan']
        kept, _dropped, _immune = _apply_scope_gated_finalize(
            candidates, 'single_module', _lane_map(_RETROSPECTIVE, 'full')
        )
        assert kept == ['push', _RETROSPECTIVE, 'archive-plan']

    def test_does_not_mutate_input_list(self):
        candidates = [_RETROSPECTIVE, 'push']
        _apply_scope_gated_finalize(candidates, 'single_module', None)
        assert candidates == [_RETROSPECTIVE, 'push']


class TestScopeGatedFinalizeImmunityThroughCompose:
    """End-to-end: the immunity survives a real ``single_module`` compose."""

    def test_declared_lane_keeps_retrospective_in_composed_manifest(self, plan_context):
        from file_ops import get_marshal_path

        marshal = {
            'plan': {
                'phase-6-finalize': {
                    'steps': {
                        'default:push': {},
                        'default:branch-cleanup': {},
                        'plan-marshall:plan-retrospective': {'lane': 'minimal'},
                        'default:archive-plan': {},
                    }
                }
            },
            'build': {'map': {'python': [{'glob': '**/*.py', 'role': 'production', 'build_class': 'compile'}]}},
        }
        marshal_path = get_marshal_path()
        marshal_path.parent.mkdir(parents=True, exist_ok=True)
        marshal_path.write_text(json.dumps(marshal, indent=2))
        _stub_footprint(['some/file.py'])

        result = cmd_compose(_compose_ns(plan_id='sg-immune-compose', scope_estimate='single_module'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['scope_gated_finalize_dropped'] == []
        assert result['scope_gated_finalize_immune'] == [_RETROSPECTIVE]
        assert _RETROSPECTIVE in result_phase_6_steps(result)

    def test_undeclared_retrospective_is_still_dropped_by_compose(self, plan_context):
        from file_ops import get_marshal_path

        marshal = {
            'plan': {
                'phase-6-finalize': {
                    'steps': {
                        'default:push': {},
                        'default:branch-cleanup': {},
                        'plan-marshall:plan-retrospective': {},
                        'default:archive-plan': {},
                    }
                }
            },
            'build': {'map': {'python': [{'glob': '**/*.py', 'role': 'production', 'build_class': 'compile'}]}},
        }
        marshal_path = get_marshal_path()
        marshal_path.parent.mkdir(parents=True, exist_ok=True)
        marshal_path.write_text(json.dumps(marshal, indent=2))
        _stub_footprint(['some/file.py'])

        result = cmd_compose(_compose_ns(plan_id='sg-nodecl-compose', scope_estimate='single_module'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['scope_gated_finalize_dropped'] == [_RETROSPECTIVE]
        assert result['scope_gated_finalize_immune'] == []
        assert _RETROSPECTIVE not in result_phase_6_steps(result)


class TestRetiredDropReviewEscapeHatch:
    """The superseded ``drop_review_on_scope_gate`` special case is gone.

    Declared-lane immunity generalizes the carve-out it hard-coded, so the knob,
    its reader, and its override drop-set are removed outright (clean break, no
    shim) rather than left beside the general rule.
    """

    def test_retired_symbols_do_not_survive(self):
        for symbol in ('_read_drop_review_on_scope_gate', '_SCOPE_GATED_OVERRIDE_DROP'):
            assert not hasattr(_mem, symbol), (
                f'{symbol} must be deleted with the drop_review_on_scope_gate escape hatch'
            )

    def test_compose_result_no_longer_reports_the_knob(self, plan_context):
        _seed_marshal(ci_provider='github')
        _stub_footprint(['some/file.py'])

        result = cmd_compose(_compose_ns(plan_id='sg-no-knob'))

        assert result is not None
        assert result['status'] == 'success'
        assert 'drop_review_on_scope_gate' not in result


class TestReadSonarProvider:
    """``_read_sonar_provider`` resolves the Sonar provider from marshal.json."""

    def _seed_providers(self, providers: list[dict]) -> None:
        from file_ops import get_marshal_path

        marshal = {'plan': {'phase-6-finalize': {}}, 'providers': providers}
        marshal_path = get_marshal_path()
        marshal_path.parent.mkdir(parents=True, exist_ok=True)
        marshal_path.write_text(json.dumps(marshal, indent=2))

    def test_returns_sonar_when_declared(self, plan_context):
        self._seed_providers(
            [{'skill_name': 'plan-marshall:workflow-integration-sonar', 'category': 'sonar'}]
        )
        assert _read_sonar_provider() == 'sonar'

    def test_returns_sonar_regardless_of_category(self, plan_context):
        # The reader keys on skill_name, not category, so a differently-categorized
        # Sonar entry still resolves.
        self._seed_providers(
            [{'skill_name': 'plan-marshall:workflow-integration-sonar', 'category': 'quality'}]
        )
        assert _read_sonar_provider() == 'sonar'

    def test_none_when_no_sonar_provider(self, plan_context):
        self._seed_providers(
            [{'skill_name': 'plan-marshall:workflow-integration-github', 'category': 'ci'}]
        )
        assert _read_sonar_provider() is None

    def test_none_when_providers_absent(self, plan_context):
        from file_ops import get_marshal_path

        marshal_path = get_marshal_path()
        marshal_path.parent.mkdir(parents=True, exist_ok=True)
        marshal_path.write_text(json.dumps({'plan': {'phase-6-finalize': {}}}, indent=2))
        assert _read_sonar_provider() is None
