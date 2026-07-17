#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the orchestrator terminal-title integration (D13).

Covers:
- Pure composition: a ``kind: orchestrator`` state composes the
  ``Orchestrator-{SlugName}`` body (slug from the state's ``slug`` field).
- Plan-state composition stays byte-identical to before (regression).
- Icon/glyph precedence is unchanged on the orchestrator branch
  (process icon, ``build-busy`` 🔨 icon-slot override, lock glyphs,
  ``icon_override``).
- The platform-runtime ``session push-title-token --store orchestrator
  --slug {slug}`` seam resolves the epic's ``status.json`` via
  ``get_store_dir('orchestrator', slug)`` under ``PLAN_BASE_DIR`` isolation,
  and the title-disabled / state-absent path stays the existing no-op.
"""

import json

import claude_runtime
import platform_runtime
from manage_terminal_title import compose


def _write_orchestrator_status(tmp_path, slug: str, extra: dict | None = None) -> None:
    """Write a minimal kind=orchestrator status.json under the sandboxed store."""
    epic_dir = tmp_path / 'orchestrator' / slug
    epic_dir.mkdir(parents=True, exist_ok=True)
    status: dict = {
        'kind': 'orchestrator',
        'title': 'Test Epic',
        'phase': 'orchestrating',
        'workstreams': [],
        'plans': [],
        'resume_anchor': '',
        'metadata': {},
    }
    if extra:
        status.update(extra)
    (epic_dir / 'status.json').write_text(json.dumps(status, indent=2), encoding='utf-8')


# =============================================================================
# Pure composition — orchestrator body
# =============================================================================


class TestOrchestratorBody:
    def test_should_compose_orchestrator_body_from_slug(self):
        composed = compose({'kind': 'orchestrator', 'slug': 'token-optimization'}, None)

        assert composed == '➤ Orchestrator-token-optimization'

    def test_should_apply_process_icon_on_orchestrator_body(self):
        composed = compose({'kind': 'orchestrator', 'slug': 'my-epic'}, 'waiting')

        assert composed == '? Orchestrator-my-epic'

    def test_should_return_none_for_missing_slug(self):
        assert compose({'kind': 'orchestrator'}, None) is None

    def test_should_return_none_for_empty_slug(self):
        assert compose({'kind': 'orchestrator', 'slug': ''}, None) is None

    def test_should_return_none_for_whitespace_slug(self):
        assert compose({'kind': 'orchestrator', 'slug': '   '}, None) is None

    def test_should_strip_slug_whitespace(self):
        composed = compose({'kind': 'orchestrator', 'slug': '  my-epic  '}, None)

        assert composed == '➤ Orchestrator-my-epic'


# =============================================================================
# Plan-state composition regression — byte-identical to before
# =============================================================================


class TestPlanStateRegression:
    def test_should_compose_active_phase_with_short_description(self):
        state = {'current_phase': '5-execute', 'short_description': 'demo'}

        assert compose(state, 'active') == '➤ pm:5-execute:demo'

    def test_should_compose_active_phase_without_short_description(self):
        assert compose({'current_phase': '5-execute'}, 'active') == '➤ pm:5-execute'

    def test_should_compose_completed_body_with_terminal_override(self):
        state = {'current_phase': 'complete', 'short_description': 'demo'}

        assert compose(state, 'active') == '✅ pm:Completed:demo'

    def test_should_return_none_for_missing_current_phase_without_kind(self):
        assert compose({'short_description': 'demo'}, 'active') is None

    def test_should_prepend_lock_glyph_for_active_plan(self):
        state = {'current_phase': '5-execute', 'title_token': 'lock-owned'}

        assert compose(state, 'active') == '➤ 🔒 pm:5-execute'

    def test_should_force_build_icon_for_build_busy_plan(self):
        state = {'current_phase': '5-execute', 'title_token': 'build-busy'}

        assert compose(state, 'active') == '🔨 pm:5-execute'


# =============================================================================
# Icon/glyph precedence on the orchestrator branch
# =============================================================================


class TestOrchestratorIconGlyphPrecedence:
    def test_should_force_build_icon_for_build_busy_orchestrator(self):
        state = {'kind': 'orchestrator', 'slug': 'my-epic', 'title_token': 'build-busy'}

        assert compose(state, 'active') == '🔨 Orchestrator-my-epic'

    def test_should_prepend_lock_waiting_glyph_on_orchestrator_body(self):
        state = {'kind': 'orchestrator', 'slug': 'my-epic', 'title_token': 'lock-waiting'}

        assert compose(state, None) == '➤ ⏳ Orchestrator-my-epic'

    def test_should_honour_icon_override_on_orchestrator_body(self):
        state = {'kind': 'orchestrator', 'slug': 'my-epic'}

        assert compose(state, None, icon_override='🔒') == '🔒 Orchestrator-my-epic'

    def test_should_let_build_busy_win_over_icon_override(self):
        state = {'kind': 'orchestrator', 'slug': 'my-epic', 'title_token': 'build-busy'}

        assert compose(state, None, icon_override='🔒') == '🔨 Orchestrator-my-epic'


# =============================================================================
# Platform-runtime seam — orchestrator state read (PLAN_BASE_DIR isolation)
# =============================================================================


class TestOrchestratorStateRead:
    def test_should_read_state_from_orchestrator_store(self, monkeypatch, tmp_path):
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        _write_orchestrator_status(tmp_path, 'my-epic')

        state = claude_runtime._read_orchestrator_title_state('my-epic')

        assert state == {'kind': 'orchestrator', 'slug': 'my-epic'}

    def test_should_carry_title_token_through(self, monkeypatch, tmp_path):
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        _write_orchestrator_status(tmp_path, 'my-epic', extra={'title_token': 'build-busy'})

        state = claude_runtime._read_orchestrator_title_state('my-epic')

        assert state is not None
        assert compose(state, 'active') == '🔨 Orchestrator-my-epic'

    def test_should_return_none_when_status_absent(self, monkeypatch, tmp_path):
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

        assert claude_runtime._read_orchestrator_title_state('missing-epic') is None

    def test_should_return_none_for_empty_slug(self, monkeypatch, tmp_path):
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

        assert claude_runtime._read_orchestrator_title_state('') is None


class TestPushTitleTokenSeam:
    """The state-absent path stays the existing no-op (title-disabled parity)."""

    def test_should_noop_when_orchestrator_state_absent(self, monkeypatch, tmp_path):
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        runtime = claude_runtime.ClaudeRuntime()

        result = runtime.session_push_title_token(
            '', None, store='orchestrator', slug='missing-epic'
        )

        assert 'status: success' in result
        assert 'pushed: false' in result
        assert 'no_title_state' in result
        assert 'slug: missing-epic' in result

    def test_should_noop_when_plan_state_absent_via_default_store(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        monkeypatch.chdir(tmp_path)
        runtime = claude_runtime.ClaudeRuntime()

        result = runtime.session_push_title_token('no-such-plan')

        assert 'status: success' in result
        assert 'pushed: false' in result
        assert 'plan_id: no-such-plan' in result


class TestPushTitleTokenCliBoundary:
    """Router-level --store / --slug validation on session push-title-token."""

    def test_should_reject_orchestrator_store_without_slug(self):
        runtime = claude_runtime.ClaudeRuntime()

        result = platform_runtime._dispatch(
            runtime, 'session push-title-token', ['--store', 'orchestrator']
        )

        assert 'status: error' in result
        assert 'invalid_argument' in result
        assert '--slug' in result

    def test_should_reject_plans_store_without_plan_id(self):
        runtime = claude_runtime.ClaudeRuntime()

        result = platform_runtime._dispatch(runtime, 'session push-title-token', [])

        assert 'status: error' in result
        assert 'invalid_argument' in result
        assert '--plan-id' in result

    def test_should_route_orchestrator_store_through_state_read(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        runtime = claude_runtime.ClaudeRuntime()

        result = platform_runtime._dispatch(
            runtime,
            'session push-title-token',
            ['--store', 'orchestrator', '--slug', 'missing-epic'],
        )

        assert 'status: success' in result
        assert 'pushed: false' in result
        assert 'no_title_state' in result
