#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Observable invariants for the terminal-title feature.

These tests assert what the TERMINAL actually receives, not that a seam fired.
That distinction is the whole point of the file: the tests it replaces asserted
that a delegation was invoked, which stayed green while the bytes never reached
a tab.

Two invariants live here:

- **Terminal-state invariant** — driving a plan through finalize + archive and
  then rendering must put the terminal ``pm:Completed`` marker on the wire. The
  assertion is on the BYTES a fake terminal sink received, never on a call
  count, and it explicitly rejects an active-phase ``pm:{phase}`` body.
- **Total-render invariant** — ``render-title`` produces a defined, NAMED
  outcome for every reachable input, including an unbound session and a missing
  ``status.json``. "Wrote nothing and said nothing" is a defect, not a pass.

The pairing invariant (every state-setting path has a matching clear) lives in
``test/plan-marshall/manage-status/test_title_token_ownership.py``.
"""
from __future__ import annotations  # noqa: I001

import json
from pathlib import Path
from typing import Any, cast

import pytest

# conftest.py sets up PYTHONPATH so cross-skill imports resolve without manual
# sys.path manipulation.
import session_binding
from claude_runtime import ClaudeRuntime
from toon_parser import parse_toon


@pytest.fixture()
def rt(tmp_path, monkeypatch):
    """A ClaudeRuntime with every filesystem root redirected under tmp_path."""
    import claude_runtime as _cr

    monkeypatch.setattr(session_binding, '_SESSION_CACHE_BASE', tmp_path / 'sessions')
    monkeypatch.setattr(_cr, '_CLAUDE_PROJECTS_DIR', tmp_path / 'projects')
    monkeypatch.setattr(_cr, '_PLAN_DIR_NAME', '.plan')
    monkeypatch.chdir(tmp_path)
    return ClaudeRuntime()


def _bind(tmp_path: Path, session_id: str, plan_id: str) -> None:
    """Point *session_id*'s active-plan slot at *plan_id*."""
    cache_dir = tmp_path / 'sessions' / session_id
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / 'active-plan').write_text(plan_id, encoding='utf-8')


def _archived_status(tmp_path: Path, plan_id: str, **fields: Any) -> Path:
    """Write an ARCHIVED status.json for *plan_id*, returning its path.

    Mirrors what ``cmd_archive`` leaves behind: the whole plan directory has
    moved under ``archived-plans/{date}-{plan_id}/``, carrying the terminal
    ``current_phase`` with it.
    """
    status_dir = tmp_path / '.plan' / 'local' / 'archived-plans' / f'2026-05-29-{plan_id}'
    status_dir.mkdir(parents=True, exist_ok=True)
    status_path = status_dir / 'status.json'
    status_path.write_text(json.dumps({'current_phase': 'complete', **fields}), encoding='utf-8')
    return status_path


def _sink_bytes(capsys) -> str:
    """Return the OSC payload the fake terminal sink (stdout) received."""
    out = capsys.readouterr().out
    assert out, 'nothing reached the terminal sink'
    return cast(str, cast(dict[str, Any], json.loads(out))['terminalSequence'])


# =============================================================================
# (a) Terminal-state invariant — the tab RECEIVES the Completed marker
# =============================================================================


class TestTerminalStateInvariant:
    """The archived plan's terminal state reaches the terminal.

    Delivery is asserted on the received bytes. A test that asserted a teardown
    or push seam "fired" would stay green while the terminal saw nothing, which
    is precisely the failure this file exists to make impossible.
    """

    def test_last_bytes_carry_the_terminal_marker(self, rt, tmp_path, monkeypatch, capsys):
        """After archive, the next render puts ``pm:Completed`` on the wire."""
        session_id = 'sess-terminal'
        plan_id = 'finished-plan'
        _archived_status(tmp_path, plan_id, short_description='the-work')
        _bind(tmp_path, session_id, plan_id)
        monkeypatch.setenv('CLAUDE_CODE_SESSION_ID', session_id)
        capsys.readouterr()

        rt.session_render_title(statusline=False)

        delivered = _sink_bytes(capsys)
        assert 'pm:Completed' in delivered
        # The ✅ terminal icon, never a process icon, for a finished plan.
        assert '✅' in delivered
        assert '➤' not in delivered

    def test_delivered_bytes_are_never_an_active_phase_body(self, rt, tmp_path, monkeypatch, capsys):
        """The negative half: no ``pm:{active-phase}`` body may reach the tab.

        Asserting only that ``pm:Completed`` is present would also pass for a
        payload that carried BOTH — e.g. a renderer that appended the terminal
        body to a stale active one. The active-phase body must be absent.
        """
        session_id = 'sess-terminal-neg'
        plan_id = 'finished-plan-neg'
        _archived_status(tmp_path, plan_id, short_description='the-work')
        _bind(tmp_path, session_id, plan_id)
        monkeypatch.setenv('CLAUDE_CODE_SESSION_ID', session_id)
        capsys.readouterr()

        rt.session_render_title(statusline=False)

        delivered = _sink_bytes(capsys)
        for active_phase in ('1-init', '2-refine', '3-outline', '4-plan', '5-execute', '6-finalize'):
            assert f'pm:{active_phase}' not in delivered

    def test_archive_does_not_destroy_the_delivery_route(self, rt, tmp_path, monkeypatch, capsys):
        """The binding survives the archive, so the terminal render can resolve.

        This is the ordering rule stated as an observable: releasing the binding
        at archive time would leave the render with no plan to resolve, and the
        terminal state — already persisted — would never be delivered. Here the
        binding is the ONLY route, so a render that produces the marker proves
        the route survived.
        """
        session_id = 'sess-route'
        plan_id = 'route-plan'
        _archived_status(tmp_path, plan_id)
        _bind(tmp_path, session_id, plan_id)
        monkeypatch.setenv('CLAUDE_CODE_SESSION_ID', session_id)

        assert session_binding.resolve_plan(session_id) == plan_id
        capsys.readouterr()
        rt.session_render_title(statusline=False)
        assert 'pm:Completed' in _sink_bytes(capsys)

    def test_slot_is_gc_exempt_until_delivered_then_collectable(self, rt, tmp_path, monkeypatch, capsys):
        """The GC exemption is STATE-driven, and it lapses on delivery.

        Both halves are asserted in one test because either alone is
        misleading: an always-exempt slot leaks forever, and an always-
        collectable slot destroys the delivery route. The transition point is
        the render itself.
        """
        session_id = 'sess-gc'
        plan_id = 'gc-plan'
        _archived_status(tmp_path, plan_id)
        _bind(tmp_path, session_id, plan_id)
        monkeypatch.setenv('CLAUDE_CODE_SESSION_ID', session_id)

        # Before delivery: the archived slot is exempt (still owed a render).
        assert session_binding._plan_is_live(plan_id) is True

        capsys.readouterr()
        rt.session_render_title(statusline=False)
        assert 'pm:Completed' in _sink_bytes(capsys)

        # After delivery: the obligation is discharged, so the slot may be GC'd.
        assert session_binding._plan_is_live(plan_id) is False


# =============================================================================
# (c) Total-render invariant — every reachable input yields a NAMED outcome
# =============================================================================


class TestRenderIsTotal:
    """``render-title`` is TOTAL: every reachable input has a named outcome.

    Totality is the property that makes the observability trustworthy. A render
    path that silently produced nothing would be indistinguishable from a
    healthy one, so "no outcome reported" is asserted to be impossible rather
    than merely unlikely.
    """

    @staticmethod
    def _outcome(capsys) -> str:
        err = capsys.readouterr().err
        assert err.strip(), 'a reachable render input produced NO named outcome'
        return cast(str, cast(dict[str, Any], parse_toon(err))['outcome'])

    def test_unbound_session_yields_a_named_outcome(self, rt, tmp_path, monkeypatch, capsys):
        """A session bound to nothing is a reachable input, not an edge case."""
        monkeypatch.setenv('CLAUDE_CODE_SESSION_ID', 'sess-nothing-bound')
        capsys.readouterr()

        rt.session_render_title(statusline=False)

        assert self._outcome(capsys) == 'no_binding'

    def test_missing_status_json_yields_a_named_outcome(self, rt, tmp_path, monkeypatch, capsys):
        """A binding whose plan directory is gone is likewise reachable."""
        _bind(tmp_path, 'sess-ghost-plan', 'vanished-plan')
        monkeypatch.setenv('CLAUDE_CODE_SESSION_ID', 'sess-ghost-plan')
        capsys.readouterr()

        rt.session_render_title(statusline=False)

        assert self._outcome(capsys) == 'no_title_state'

    def test_no_session_id_yields_a_named_outcome(self, rt, monkeypatch, capsys):
        """The hook firing without a session id is reachable on every platform."""
        monkeypatch.delenv('CLAUDE_CODE_SESSION_ID', raising=False)
        capsys.readouterr()

        rt.session_render_title(statusline=False)

        assert self._outcome(capsys) == 'no_session_id'

    @pytest.mark.parametrize('statusline', [False, True])
    def test_every_reachable_input_class_is_total(self, rt, tmp_path, monkeypatch, capsys, statusline):
        """Sweep the reachable input classes on BOTH channels.

        Parametrizing over ``statusline`` is load-bearing: the two channels have
        separate emit paths, and an outcome gap on one would be invisible to a
        hook-only sweep.
        """
        # 1. No session id.
        monkeypatch.delenv('CLAUDE_CODE_SESSION_ID', raising=False)
        capsys.readouterr()
        rt.session_render_title(statusline=statusline)
        assert self._outcome(capsys)

        # 2. Session id, nothing bound.
        monkeypatch.setenv('CLAUDE_CODE_SESSION_ID', 'sess-total-unbound')
        capsys.readouterr()
        rt.session_render_title(statusline=statusline)
        assert self._outcome(capsys)

        # 3. Bound, but the plan is gone.
        _bind(tmp_path, 'sess-total-ghost', 'no-such')
        monkeypatch.setenv('CLAUDE_CODE_SESSION_ID', 'sess-total-ghost')
        capsys.readouterr()
        rt.session_render_title(statusline=statusline)
        assert self._outcome(capsys)

        # 4. Bound, plan present but unrenderable (no current_phase).
        live = tmp_path / '.plan' / 'local' / 'plans' / 'phaseless'
        live.mkdir(parents=True, exist_ok=True)
        (live / 'status.json').write_text(json.dumps({'short_description': 'x'}), encoding='utf-8')
        _bind(tmp_path, 'sess-total-phaseless', 'phaseless')
        monkeypatch.setenv('CLAUDE_CODE_SESSION_ID', 'sess-total-phaseless')
        capsys.readouterr()
        rt.session_render_title(statusline=statusline)
        assert self._outcome(capsys)

        # 5. Bound and fully renderable — the success path is named too.
        live_ok = tmp_path / '.plan' / 'local' / 'plans' / 'renderable'
        live_ok.mkdir(parents=True, exist_ok=True)
        (live_ok / 'status.json').write_text(
            json.dumps({'current_phase': '5-execute', 'short_description': 'work'}),
            encoding='utf-8',
        )
        _bind(tmp_path, 'sess-total-ok', 'renderable')
        monkeypatch.setenv('CLAUDE_CODE_SESSION_ID', 'sess-total-ok')
        capsys.readouterr()
        rt.session_render_title(statusline=statusline)
        assert self._outcome(capsys)
