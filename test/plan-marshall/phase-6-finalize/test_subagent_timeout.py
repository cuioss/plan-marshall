#!/usr/bin/env python3
"""
Regression tests for the phase-6-finalize per-agent timeout wrapper contract.

Each agent-suitable finalize step (sonar-roundtrip, automated-review,
knowledge-capture, lessons-capture) runs under a per-agent timeout enforced
by the SKILL.md Step 3 dispatch loop. When the wrapper expires, the
dispatcher MUST:

  1. Log an ERROR entry.
  2. Mark the step outcome=failed (NOT done) with a timeout display_detail.
  3. Continue with the next manifest step (no abort, no re-throw).

These tests pin the timeout contract:

  * The four budgeted steps and their budgets are documented in SKILL.md.
  * automated-review.md and sonar-roundtrip.md document the timeout contract
    (15-minute budget, graceful degradation).
  * A simulated hung agent yields outcome=failed and the dispatcher continues.
  * lessons-capture (5-minute budget) is unconditional whenever it is in the
    manifest — even after a prior timeout failure.
"""

import importlib.util
from argparse import Namespace

import pytest

from conftest import MARKETPLACE_ROOT, PlanContext

# ---------------------------------------------------------------------------
# Manifest module (Tier 2 direct import via importlib because of the hyphen)
# ---------------------------------------------------------------------------

_MANIFEST_SCRIPT = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'manage-execution-manifest'
    / 'scripts'
    / 'manage-execution-manifest.py'
)
_spec = importlib.util.spec_from_file_location('mem_for_timeout', str(_MANIFEST_SCRIPT))
assert _spec is not None
_mem = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mem)

cmd_compose = _mem.cmd_compose
read_manifest = _mem.read_manifest
DEFAULT_PHASE_5_STEPS = _mem.DEFAULT_PHASE_5_STEPS
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

_mem._log_decision = lambda *a, **kw: None  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Standards-doc paths for narrative-contract assertions
# ---------------------------------------------------------------------------

_PHASE_6_SKILL_MD = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'SKILL.md'
_AUTOMATED_REVIEW_MD = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'standards' / 'automated-review.md'
)
_SONAR_ROUNDTRIP_MD = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'standards' / 'sonar-roundtrip.md'
)
_LESSONS_CAPTURE_MD = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'standards' / 'lessons-capture.md'
)


def _compose_ns(plan_id: str) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type='feature',
        track='complex',
        scope_estimate='multi_module',
        recipe_key=None,
        affected_files_count=5,
        phase_5_steps=','.join(DEFAULT_PHASE_5_STEPS),
        phase_6_steps=','.join(DEFAULT_PHASE_6_STEPS),
        commit_strategy=None,
    )


# ---------------------------------------------------------------------------
# Per-agent budget table (mirrors SKILL.md Step 3).
# ---------------------------------------------------------------------------

PER_AGENT_BUDGET_SECONDS = {
    'sonar-roundtrip': 900,
    'automated-review': 900,
    'lessons-capture': 300,
}


# ---------------------------------------------------------------------------
# Dispatcher simulator with timeout wrapper.
# ---------------------------------------------------------------------------


def _simulate_dispatch_with_timeout(
    manifest: dict,
    agent_durations_seconds: dict[str, int],
    initial_state: dict[str, dict] | None = None,
) -> tuple[list[str], dict[str, dict]]:
    """Simulate the SKILL.md Step 3 dispatch loop with timeout wrapper.

    Args:
        manifest: parsed execution manifest.
        agent_durations_seconds: per-step "time the agent took". When the
            value exceeds the per-agent budget, the wrapper records
            outcome=failed and the dispatcher continues with the next step.
        initial_state: prior phase_steps records (resumable re-entry).

    Returns:
        (dispatched_step_ids, final_phase_steps_state)
    """
    state = dict(initial_state or {})
    dispatched: list[str] = []

    for step_id in manifest['phase_6']['steps']:
        prior = state.get(step_id, {}).get('outcome')
        if prior == 'done':
            continue  # resumable skip
        # Dispatch (failed records get retried).
        dispatched.append(step_id)
        budget = PER_AGENT_BUDGET_SECONDS.get(step_id)
        duration = agent_durations_seconds.get(step_id, 0)
        if budget is not None and duration > budget:
            state[step_id] = {
                'outcome': 'failed',
                'display_detail': f'timed out after {budget}s',
            }
        else:
            state[step_id] = {
                'outcome': 'done',
                'display_detail': 'simulated done',
            }
    return dispatched, state


# ===========================================================================
# Per-agent budget contract
# ===========================================================================


class TestBudgetContract:
    @pytest.fixture(scope='class')
    def skill_md_text(self) -> str:
        return _PHASE_6_SKILL_MD.read_text(encoding='utf-8')

    def test_sonar_roundtrip_15min_budget_documented(self, skill_md_text: str):
        assert 'sonar-roundtrip' in skill_md_text
        assert '15 min' in skill_md_text or '900' in skill_md_text, (
            'SKILL.md must document the 15-min (900s) budget for sonar-roundtrip'
        )

    def test_automated_review_15min_budget_documented(self, skill_md_text: str):
        assert 'automated-review' in skill_md_text
        assert '15 min' in skill_md_text or '900' in skill_md_text

    def test_lessons_capture_5min_budget_documented(self, skill_md_text: str):
        assert 'lessons-capture' in skill_md_text
        assert '5 min' in skill_md_text or '300' in skill_md_text

    def test_timeout_failed_outcome_and_continuation_documented(
        self,
        skill_md_text: str,
    ):
        """SKILL.md must explicitly say: on timeout -> mark failed + continue."""
        text_lower = skill_md_text.lower()
        assert 'timeout' in text_lower or 'timed out' in text_lower
        assert 'failed' in text_lower
        assert 'continue' in text_lower, 'Timeout contract must document continuation (no abort)'


# ===========================================================================
# Standards-doc timeout contract
# ===========================================================================


class TestStandardsTimeoutContract:
    def test_automated_review_doc_documents_timeout_contract(self):
        text = _AUTOMATED_REVIEW_MD.read_text(encoding='utf-8')
        text_lower = text.lower()
        assert 'timeout' in text_lower
        assert '15 min' in text or '900' in text
        assert 'graceful' in text_lower or 'degrad' in text_lower
        assert 'failed' in text_lower
        assert 'continu' in text_lower

    def test_sonar_roundtrip_doc_documents_timeout_contract(self):
        text = _SONAR_ROUNDTRIP_MD.read_text(encoding='utf-8')
        text_lower = text.lower()
        assert 'timeout' in text_lower
        assert '15 min' in text or '900' in text
        assert 'graceful' in text_lower or 'degrad' in text_lower
        assert 'failed' in text_lower
        assert 'continu' in text_lower

    def test_lessons_capture_doc_documents_5min_budget(self):
        text = _LESSONS_CAPTURE_MD.read_text(encoding='utf-8')
        assert '5 min' in text or '300' in text


# ===========================================================================
# Hung-agent simulation
# ===========================================================================


class TestHungAgentSimulation:
    def test_hung_sonar_marks_failed_and_continues(self):
        """A simulated hung sonar-roundtrip (16 min > 15 min budget) yields
        outcome=failed and the dispatcher continues with subsequent steps."""
        with PlanContext(plan_id='p6-timeout-sonar'):
            cmd_compose(_compose_ns('p6-timeout-sonar'))
            manifest = read_manifest('p6-timeout-sonar')
            assert manifest is not None

            durations = {
                'sonar-roundtrip': 901,  # one second over the 900s budget
            }
            dispatched, final_state = _simulate_dispatch_with_timeout(
                manifest,
                durations,
            )

            assert 'sonar-roundtrip' in dispatched
            assert final_state['sonar-roundtrip']['outcome'] == 'failed'
            assert 'timed out' in final_state['sonar-roundtrip']['display_detail']

            # Subsequent steps STILL fire — no abort.
            steps = manifest['phase_6']['steps']
            sonar_idx = steps.index('sonar-roundtrip')
            for later in steps[sonar_idx + 1 :]:
                assert later in dispatched, f'{later} must still dispatch after sonar timeout (continuation)'

    def test_hung_automated_review_marks_failed_and_continues(self):
        with PlanContext(plan_id='p6-timeout-review'):
            cmd_compose(_compose_ns('p6-timeout-review'))
            manifest = read_manifest('p6-timeout-review')
            assert manifest is not None

            durations = {'automated-review': 1500}
            dispatched, final_state = _simulate_dispatch_with_timeout(
                manifest,
                durations,
            )

            assert final_state['automated-review']['outcome'] == 'failed'
            steps = manifest['phase_6']['steps']
            ar_idx = steps.index('automated-review')
            # All later steps still fire.
            for later in steps[ar_idx + 1 :]:
                assert later in dispatched

    def test_hung_lessons_capture_marks_failed_and_continues(self):
        """A simulated hung lessons-capture (6 min > 5 min budget) yields
        outcome=failed; the pipeline never aborts on advisory-step timeout."""
        with PlanContext(plan_id='p6-timeout-lessons'):
            cmd_compose(_compose_ns('p6-timeout-lessons'))
            manifest = read_manifest('p6-timeout-lessons')
            assert manifest is not None

            durations = {'lessons-capture': 360}  # > 300s budget
            dispatched, final_state = _simulate_dispatch_with_timeout(
                manifest,
                durations,
            )

            assert final_state['lessons-capture']['outcome'] == 'failed'
            steps = manifest['phase_6']['steps']
            lc_idx = steps.index('lessons-capture')
            for later in steps[lc_idx + 1 :]:
                assert later in dispatched

    def test_within_budget_marks_done(self):
        """An agent that completes inside the budget marks done."""
        with PlanContext(plan_id='p6-within-budget'):
            cmd_compose(_compose_ns('p6-within-budget'))
            manifest = read_manifest('p6-within-budget')
            assert manifest is not None

            durations = {
                'sonar-roundtrip': 100,
                'automated-review': 200,
                'lessons-capture': 30,
            }
            _, final_state = _simulate_dispatch_with_timeout(
                manifest,
                durations,
            )
            # Every step that ran finished done.
            for _step_id, record in final_state.items():
                assert record['outcome'] == 'done'


# ===========================================================================
# Resumable retry of timed-out steps
# ===========================================================================


class TestTimeoutRetryOnReentry:
    def test_failed_timeout_step_retried_on_next_entry(self):
        """A step left at outcome=failed by a timeout MUST be retried on the
        next Phase 6 entry (one fresh attempt per invocation)."""
        with PlanContext(plan_id='p6-retry-after-timeout'):
            cmd_compose(_compose_ns('p6-retry-after-timeout'))
            manifest = read_manifest('p6-retry-after-timeout')
            assert manifest is not None

            # First entry: sonar-roundtrip times out.
            first_dispatch, first_state = _simulate_dispatch_with_timeout(
                manifest,
                {'sonar-roundtrip': 901},
            )
            assert first_state['sonar-roundtrip']['outcome'] == 'failed'

            # Second entry: sonar runs fast this time.
            second_dispatch, second_state = _simulate_dispatch_with_timeout(
                manifest,
                {'sonar-roundtrip': 60},
                initial_state=first_state,
            )

            # The previously-done steps must be SKIPPED on the second entry.
            # The previously-failed sonar step must be RETRIED.
            assert 'sonar-roundtrip' in second_dispatch
            for step_id, record in first_state.items():
                if record['outcome'] == 'done':
                    assert step_id not in second_dispatch, f'done-marked {step_id} must not re-dispatch on re-entry'
            # And on the retry it succeeds.
            assert second_state['sonar-roundtrip']['outcome'] == 'done'


# ===========================================================================
# Lessons-capture unconditionality even when prior steps timed out
# ===========================================================================


class TestLessonsCaptureUnconditional:
    def test_lessons_capture_fires_even_when_sonar_timed_out(self):
        """A sonar timeout must NOT prevent lessons-capture from dispatching
        on the same Phase 6 invocation — lessons-capture is unconditional
        whenever it appears in the manifest."""
        with PlanContext(plan_id='p6-lessons-after-sonar-timeout'):
            cmd_compose(_compose_ns('p6-lessons-after-sonar-timeout'))
            manifest = read_manifest('p6-lessons-after-sonar-timeout')
            assert manifest is not None
            assert 'lessons-capture' in manifest['phase_6']['steps']

            dispatched, final_state = _simulate_dispatch_with_timeout(
                manifest,
                {'sonar-roundtrip': 901},
            )

            assert 'lessons-capture' in dispatched, 'lessons-capture must dispatch even after a sonar timeout'
            assert final_state['sonar-roundtrip']['outcome'] == 'failed'
