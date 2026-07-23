#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ClaudeRuntime.session_render_title surface (impl module).

The ``ClaudeRuntime`` class — including ``session_render_title`` — now lives in
``_claude_runtime_impl.py`` (co-located with the ``claude_runtime`` entry, which
re-exports it). The ``resolver-matrix-coverage`` plugin-doctor rule derives a
resolver's expected test file from the SOURCE module stem, so the tier-matrix
tests for ``session_render_title`` live here (``test__claude_runtime_impl.py``)
mirroring the source move.

Covers:
  * ``session_render_title(statusline=True)`` plain-text / no-op branches;
  * the parametrized {input-tier x hit/miss/stale} resolver matrix;
  * hook-mode state-aware icon selection driven by the stdin payload; and
  * the conditional ``hookSpecificOutput.sessionTitle`` emit.

All filesystem writes are redirected to tmp_path via monkeypatching so no
real settings files are mutated.
"""
from __future__ import annotations  # noqa: I001

import json
from pathlib import Path
from typing import Any, cast

import pytest

# conftest.py sets up PYTHONPATH so cross-skill imports resolve without manual
# sys.path manipulation. The ``claude_runtime`` entry re-exports ``ClaudeRuntime``
# (now defined in ``_claude_runtime_impl.py``), so this import mechanism is
# unchanged from ``test_claude_runtime.py``.
import session_binding
from claude_runtime import ClaudeRuntime
from toon_parser import parse_toon


# =============================================================================
# Fixture
# =============================================================================


@pytest.fixture()
def rt(tmp_path, monkeypatch):
    """Return a ClaudeRuntime instance with all filesystem roots redirected.

    Monkeypatches the module-level constants that control where marshal.json,
    session cache, and settings files land so no real files are mutated. The
    per-session active-plan cache root lives in ``session_binding`` (the read
    side ``_read_active_plan`` delegates to), so its base is patched there.
    """
    import claude_runtime as _cr

    monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")
    monkeypatch.setattr(_cr, "_CLAUDE_PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
    return ClaudeRuntime()


# =============================================================================
# 4b. session_render_title --statusline mode (status.json source)
# =============================================================================
#
# The renderer now reads title state from status.json (current_phase,
# short_description, title_token) and delegates composition to the
# manage-terminal-title composer. The composed body for current_phase=X +
# short_description=Y is ``pm:X:Y`` (the composer's body format). With no
# title_token, the composed title is ``{icon} pm:X:Y`` (no glyph).


def _write_status_json(
    tmp_path: Path,
    *,
    session_id: str,
    plan_id: str,
    current_phase: str | None = "5-execute",
    short_description: str | None = "my-task",
    title_token: str | None = None,
    archived: bool = False,
    date_prefix: str = "2026-05-29",
) -> None:
    """Materialize the session-cache pointer + a plan ``status.json`` on disk.

    Writes the active-plan pointer for *session_id* → *plan_id*, then a
    ``status.json`` containing the title-state fields. When *archived* is True
    the status.json lands under ``archived-plans/{date_prefix}-{plan_id}/``;
    otherwise under the live ``plans/{plan_id}/`` dir. A ``None`` field is
    omitted from the JSON so the absent-field paths can be exercised.
    """
    cache_dir = tmp_path / "sessions" / session_id
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "active-plan").write_text(plan_id, encoding="utf-8")

    status: dict[str, Any] = {}
    if current_phase is not None:
        status["current_phase"] = current_phase
    if short_description is not None:
        status["short_description"] = short_description
    if title_token is not None:
        status["title_token"] = title_token

    if archived:
        status_dir = (
            tmp_path / ".plan" / "local" / "archived-plans" / f"{date_prefix}-{plan_id}"
        )
    else:
        status_dir = tmp_path / ".plan" / "local" / "plans" / plan_id
    status_dir.mkdir(parents=True, exist_ok=True)
    (status_dir / "status.json").write_text(json.dumps(status), encoding="utf-8")


def _redirect_render_env(tmp_path: Path, monkeypatch, session_id: str) -> None:
    """Redirect the renderer's module constants + env at *session_id*."""
    import claude_runtime as _cr

    monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")
    monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", session_id)
    monkeypatch.chdir(tmp_path)


def _activate_terminal_title(tmp_path: Path) -> None:
    """Write a settings file that makes ``_terminal_title_active()`` report True.

    A configured ``statusLine`` command alone is enough — the predicate reports
    active when EITHER a render-hook entry or a statusLine command is present.
    """
    settings = tmp_path / ".claude" / "settings.local.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(
        json.dumps({"statusLine": {"type": "command", "command": "render"}}),
        encoding="utf-8",
    )


def _patch_dev_tty(monkeypatch, *, openable: bool) -> list[str]:
    """Redirect ``open('/dev/tty', ...)``; return the list of captured writes.

    With ``openable=False`` the open raises ``OSError`` (no controlling
    terminal). With ``openable=True`` it yields an in-memory writer whose
    payload is appended to the returned list. Every other path falls through to
    the real builtin, so ordinary file I/O in the code under test is unaffected.
    """
    import builtins
    import io

    writes: list[str] = []
    real_open = builtins.open

    class _CapturingTty(io.StringIO):
        def close(self) -> None:
            writes.append(self.getvalue())
            super().close()

    def _fake_open(file, *args, **kwargs):
        if file == "/dev/tty":
            if not openable:
                raise OSError(6, "Device not configured")
            return _CapturingTty()
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", _fake_open)
    return writes


def _stub_hook_stdin(monkeypatch, payload: dict[str, Any]) -> None:
    """Feed *payload* to the renderer's hook-mode ``sys.stdin.read()``."""
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))


class TestSessionTeardown:
    """Tests for the activation-gated ``session teardown`` operation.

    Order is load-bearing: the activation signal is read FIRST, so an inactive
    project is never touched — no title escape, no /dev/tty open, no binding
    mutation. When active, the neutral-default reset escape is written and the
    session's own slot is dropped, with ``reset`` and ``unbound`` reported
    independently.
    """

    def test_inactive_feature_touches_nothing(self, rt, tmp_path, monkeypatch):
        """With the feature inactive: no tty write, no unbind, reason feature_inactive."""
        _redirect_render_env(tmp_path, monkeypatch, "sess-teardown-inactive")
        session_binding.bind("sess-teardown-inactive", "some-plan")
        writes = _patch_dev_tty(monkeypatch, openable=True)

        unbind_calls: list[str] = []
        real_unbind = session_binding.unbind
        monkeypatch.setattr(
            session_binding,
            "unbind",
            lambda sid: (unbind_calls.append(sid), real_unbind(sid))[1],
        )

        result = parse_toon(rt.session_teardown())

        assert result["status"] == "success"
        assert result["active"] is False
        assert result["reset"] is False
        assert result["unbound"] is False
        assert result["reason"] == "feature_inactive"
        # Nothing was written and no binding was mutated.
        assert writes == []
        assert unbind_calls == []
        assert session_binding.resolve_plan("sess-teardown-inactive") == "some-plan"

    def test_active_feature_writes_neutral_reset_and_unbinds(self, rt, tmp_path, monkeypatch):
        """With the feature active: the bare OSC-0 reset lands and the slot is dropped."""
        _redirect_render_env(tmp_path, monkeypatch, "sess-teardown-active")
        _activate_terminal_title(tmp_path)
        session_binding.bind("sess-teardown-active", "some-plan")
        writes = _patch_dev_tty(monkeypatch, openable=True)

        result = parse_toon(rt.session_teardown())

        assert result["active"] is True
        assert result["reset"] is True
        assert result["unbound"] is True
        # EXACTLY the neutral-default reset escape — an empty OSC-0 payload,
        # which returns the tab to the terminal's own default title.
        assert writes == ["\x1b]0;\x07"]
        assert session_binding.resolve_plan("sess-teardown-active") is None

    def test_active_without_controlling_tty_still_unbinds(self, rt, tmp_path, monkeypatch):
        """reset and unbound are independent: no tty still drops the binding."""
        _redirect_render_env(tmp_path, monkeypatch, "sess-teardown-notty")
        _activate_terminal_title(tmp_path)
        session_binding.bind("sess-teardown-notty", "some-plan")
        _patch_dev_tty(monkeypatch, openable=False)

        result = parse_toon(rt.session_teardown())

        assert result["active"] is True
        assert result["reset"] is False
        assert result["unbound"] is True
        assert session_binding.resolve_plan("sess-teardown-notty") is None


class TestSessionStartClearTeardown:
    """SessionStart:clear is a teardown, not a render.

    The matcher-less SessionStart render hook fires for every source, so the
    renderer itself branches on ``source``: ``"clear"`` performs the teardown and
    writes nothing to stdout, while ``"startup"`` renders normally.
    """

    def test_source_clear_tears_down_and_writes_nothing(
        self, rt, tmp_path, monkeypatch, capsys
    ):
        """A SessionStart payload with source: clear emits no stdout and unbinds."""
        session_id = "sess-clear-teardown"
        _write_status_json(tmp_path, session_id=session_id, plan_id="active-plan")
        _redirect_render_env(tmp_path, monkeypatch, session_id)
        _activate_terminal_title(tmp_path)
        _patch_dev_tty(monkeypatch, openable=True)
        _stub_hook_stdin(monkeypatch, {"hook_event_name": "SessionStart", "source": "clear"})

        capsys.readouterr()
        assert rt.session_render_title() == ""

        assert capsys.readouterr().out == ""
        assert session_binding.resolve_plan(session_id) is None

    def test_source_startup_still_renders(self, rt, tmp_path, monkeypatch, capsys):
        """A SessionStart payload with source: startup renders with sessionTitle intact."""
        session_id = "sess-startup-render"
        _write_status_json(tmp_path, session_id=session_id, plan_id="active-plan")
        _redirect_render_env(tmp_path, monkeypatch, session_id)
        _activate_terminal_title(tmp_path)
        _stub_hook_stdin(monkeypatch, {"hook_event_name": "SessionStart", "source": "startup"})

        capsys.readouterr()
        assert rt.session_render_title() == ""

        envelope = json.loads(capsys.readouterr().out)
        assert "terminalSequence" in envelope
        assert envelope["hookSpecificOutput"]["sessionTitle"] == "pm:5-execute:my-task"
        # The binding survives — a startup render is not a teardown.
        assert session_binding.resolve_plan(session_id) == "active-plan"


class TestSessionPushTitleTokenDelivery:
    """Tests for the observable delivery outcome of session_push_title_token.

    The ``/dev/tty`` write is the FALLBACK delivery channel; off a controlling
    terminal it cannot land. That non-delivery is reported rather than swallowed:
    ``pushed: false`` with ``reason: no_controlling_tty``, and every ``/dev/tty``
    attempt names its channel via ``delivery: dev_tty_fallback``. An absent title
    state is a different outcome entirely and keeps ``reason: no_title_state``.
    """

    def test_unopenable_dev_tty_reports_no_controlling_tty(self, rt, tmp_path, monkeypatch):
        """An unopenable /dev/tty yields pushed: false, reason: no_controlling_tty."""
        plan_id = "push-no-tty"
        _write_status_json(tmp_path, session_id="sess-push-no-tty", plan_id=plan_id)
        _redirect_render_env(tmp_path, monkeypatch, "sess-push-no-tty")
        _patch_dev_tty(monkeypatch, openable=False)

        result = parse_toon(rt.session_push_title_token(plan_id))
        assert result["status"] == "success"
        assert result["pushed"] is False
        assert result["reason"] == "no_controlling_tty"
        assert result["delivery"] == "dev_tty_fallback"

    def test_successful_push_reports_dev_tty_fallback_channel(self, rt, tmp_path, monkeypatch):
        """A landed push yields pushed: true, delivery: dev_tty_fallback, no reason."""
        plan_id = "push-ok"
        _write_status_json(tmp_path, session_id="sess-push-ok", plan_id=plan_id)
        _redirect_render_env(tmp_path, monkeypatch, "sess-push-ok")
        writes = _patch_dev_tty(monkeypatch, openable=True)

        result = parse_toon(rt.session_push_title_token(plan_id))
        assert result["status"] == "success"
        assert result["pushed"] is True
        assert result["delivery"] == "dev_tty_fallback"
        assert "reason" not in result
        # The OSC escape actually reached the (captured) terminal.
        assert writes and writes[0].startswith("\x1b]0;")

    def test_absent_title_state_keeps_no_title_state_reason(self, rt, tmp_path, monkeypatch):
        """A plan with no status.json keeps reason: no_title_state and names no channel.

        The state read fails BEFORE any /dev/tty attempt, so the outcome must not
        be conflated with the delivery-channel failure above.
        """
        _redirect_render_env(tmp_path, monkeypatch, "sess-push-absent")
        _patch_dev_tty(monkeypatch, openable=False)

        result = parse_toon(rt.session_push_title_token("no-such-plan"))
        assert result["status"] == "success"
        assert result["pushed"] is False
        assert result["reason"] == "no_title_state"
        assert "delivery" not in result


class TestSessionRenderTitleStatusline:
    """Tests for ClaudeRuntime.session_render_title(statusline=True).

    Covers plain-text emission of the composer output on the success branch (no
    JSON envelope) and the no-op branches (missing session-id / no active plan /
    missing status.json) which must still write nothing on stdout in statusline
    mode.
    """

    def test_statusline_emits_plain_text_on_success(self, rt, tmp_path, monkeypatch, capsys):
        """In statusline mode, success branch writes plain ``{composed}`` — no JSON envelope, no OSC, no TOON tail."""
        session_id = "sess-statusline-ok"
        plan_id = "active-plan"
        _write_status_json(
            tmp_path, session_id=session_id, plan_id=plan_id,
            current_phase="5-execute", short_description="my-task",
        )
        _redirect_render_env(tmp_path, monkeypatch, session_id)

        capsys.readouterr()  # discard prior capture
        # Function MUST return empty string in statusline mode so the caller's
        # print(result) does not append a TOON envelope after the title.
        returned = rt.session_render_title(statusline=True)
        assert returned == ""

        captured = capsys.readouterr().out
        # Plain text — composer output (active icon, no glyph) — no JSON
        # envelope, no OSC escape sequence, no TOON.
        assert captured == "➤ pm:5-execute:my-task"
        assert "terminalSequence" not in captured
        assert "\x1b]0;" not in captured
        assert "status:" not in captured

    def test_default_mode_emits_only_json_envelope(self, rt, tmp_path, monkeypatch, capsys):
        """Hook mode (statusline=False) success: stdout contains ONLY the JSON envelope — no TOON tail, function returns ""."""
        session_id = "sess-envelope-mode"
        plan_id = "active-plan"
        _write_status_json(
            tmp_path, session_id=session_id, plan_id=plan_id,
            current_phase="1-init", short_description="foo",
        )
        _redirect_render_env(tmp_path, monkeypatch, session_id)

        capsys.readouterr()
        # Function MUST return empty string so the wrapper main() does not
        # append a TOON tail to the JSON envelope. Mixed-content stdout breaks
        # Claude Code's host parser (see hook-authoring-guide.md).
        returned = rt.session_render_title(statusline=False)
        assert returned == ""

        captured = capsys.readouterr().out
        # Stdout MUST be parseable as a single JSON object with no trailing bytes.
        payload = json.loads(captured)
        assert payload["terminalSequence"] == "\x1b]0;➤ pm:1-init:foo\x07"
        # No TOON success/noop row glued to the envelope.
        assert "status:" not in captured

    def test_title_token_glyph_prepended_in_composed_title(self, rt, tmp_path, monkeypatch, capsys):
        """A status.json title_token renders its glyph between the icon and body via the composer."""
        session_id = "sess-glyph"
        plan_id = "glyph-plan"
        _write_status_json(
            tmp_path, session_id=session_id, plan_id=plan_id,
            current_phase="5-execute", short_description="locked-task",
            title_token="lock-owned",
        )
        _redirect_render_env(tmp_path, monkeypatch, session_id)

        capsys.readouterr()
        returned = rt.session_render_title(statusline=True)
        assert returned == ""
        captured = capsys.readouterr().out
        # 🔒 is the lock-owned glyph (owned by the D12 composer).
        assert captured == "➤ \U0001f512 pm:5-execute:locked-task"

    def test_statusline_missing_session_id_writes_nothing(self, rt, monkeypatch, capsys):
        """statusline noop: missing $CLAUDE_CODE_SESSION_ID — nothing written to stdout, empty return."""
        monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
        capsys.readouterr()
        # statusline noop returns empty string (NOT a TOON noop) so the
        # caller's print(result) does not paint a noop envelope into the
        # statusLine slot.
        assert rt.session_render_title(statusline=True) == ""
        assert capsys.readouterr().out == ""

    def test_statusline_no_active_plan_writes_nothing(self, rt, tmp_path, monkeypatch, capsys):
        """statusline noop: session has no registered plan — nothing written to stdout, empty return."""
        monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-without-plan")
        capsys.readouterr()
        assert rt.session_render_title(statusline=True) == ""
        assert capsys.readouterr().out == ""

    def test_statusline_missing_status_json_writes_nothing(self, rt, tmp_path, monkeypatch, capsys):
        """statusline noop: session resolves to plan but status.json is missing — empty return."""
        import claude_runtime as _cr

        session_id = "sess-no-status"
        plan_id = "plan-no-status"
        cache_dir = tmp_path / "sessions" / session_id
        cache_dir.mkdir(parents=True)
        (cache_dir / "active-plan").write_text(plan_id, encoding="utf-8")

        monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")
        monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", session_id)
        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        assert rt.session_render_title(statusline=True) == ""
        assert capsys.readouterr().out == ""

    def test_hook_mode_missing_session_id_writes_nothing(self, rt, monkeypatch, capsys):
        """Hook mode noop (missing session id): empty stdout, empty return — host-parser contract requires absolute silence."""
        monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
        capsys.readouterr()
        assert rt.session_render_title(statusline=False) == ""
        assert capsys.readouterr().out == ""

    def test_hook_mode_no_active_plan_writes_nothing(self, rt, tmp_path, monkeypatch, capsys):
        """Hook mode noop (no plan mapping): empty stdout, empty return."""
        monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-no-plan-mapping")
        capsys.readouterr()
        assert rt.session_render_title(statusline=False) == ""
        assert capsys.readouterr().out == ""

    def test_hook_mode_missing_status_json_writes_nothing(self, rt, tmp_path, monkeypatch, capsys):
        """Hook mode noop (status.json missing): empty stdout, empty return."""
        import claude_runtime as _cr

        session_id = "sess-no-status-json"
        plan_id = "plan-no-status"
        cache_dir = tmp_path / "sessions" / session_id
        cache_dir.mkdir(parents=True)
        (cache_dir / "active-plan").write_text(plan_id, encoding="utf-8")

        monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")
        monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", session_id)
        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        assert rt.session_render_title(statusline=False) == ""
        assert capsys.readouterr().out == ""

    def test_hook_mode_empty_current_phase_writes_nothing(self, rt, tmp_path, monkeypatch, capsys):
        """status.json without current_phase → composer returns None → no-op (empty stdout)."""
        session_id = "sess-no-phase"
        plan_id = "plan-no-phase"
        _write_status_json(
            tmp_path, session_id=session_id, plan_id=plan_id,
            current_phase=None, short_description="orphan",
        )
        _redirect_render_env(tmp_path, monkeypatch, session_id)

        capsys.readouterr()
        assert rt.session_render_title(statusline=False) == ""
        assert capsys.readouterr().out == ""


# =============================================================================
# 3. session_render_title
# =============================================================================


# ---------------------------------------------------------------------------
# session_render_title matrix scaffolding (status.json source)
# ---------------------------------------------------------------------------
#
# The renderer resolves a terminal title across three input tiers, each of
# which may yield one of three outcomes (hit / miss / stale). The matrix below
# encodes every {tier × outcome} cell exactly once. The renderer now reads the
# title state from ``status.json`` (current_phase / short_description /
# title_token) and delegates composition to the manage-terminal-title composer,
# so each ``hit`` cell asserts the composer output ``pm:{phase}:{short}``.
#
# Input-tier definitions (in resolver order):
#   1. plan_id-only       — $CLAUDE_CODE_SESSION_ID is present in the env.
#                           hit   = valid session-id string is exported.
#                           miss  = env var is unset entirely.
#                           stale = env var is present but the empty string.
#   2. title-from-status  — Session cache resolves to a plan via the
#                           ``$_SESSION_CACHE_BASE/{session}/active-plan`` file.
#                           hit   = pointer file exists with a plan id.
#                           miss  = pointer file is absent.
#                           stale = pointer file exists but is empty.
#   3. status-from-plan   — Plan dir resolves to a ``status.json`` carrying a
#                           non-empty ``current_phase``.
#                           hit   = status.json exists with current_phase.
#                           miss  = status.json is absent.
#                           stale = status.json exists but has no current_phase
#                                   (composer returns None → no-op).
#
# Production-dominant cell (named below):  TIER ``status-from-plan`` × HIT.
# That is the cell exercised on every hook fire during normal plan execution —
# main session at repo root, populated session cache, status.json with a live
# phase. Documented inline so future editors see it before running tests.
#
# Cross-tab isolation cells:  The two ``status-from-plan`` × ``hit`` rows
# (``status-from-plan-hit-session-A`` and ``status-from-plan-hit-session-B``)
# exercise two distinct session ids each pointing at distinct plan dirs. Each
# cell asserts the OSC envelope embeds the partner session's composed body,
# proving per-session state isolation.

# Matrix cell schema:
#   id            — pytest parametrize id (kebab-case)
#   tier          — one of {plan_id-only, title-from-status, status-from-plan}
#   outcome       — one of {hit, miss, stale}
#   session_id    — env value to export (None ⇒ delenv)
#   plan_id       — active-plan pointer content (None ⇒ no file written;
#                   "" ⇒ empty pointer)
#   current_phase — status.json current_phase (None ⇒ no status.json written;
#                   "" ⇒ status.json present but current_phase empty/absent)
#   short_desc    — status.json short_description
#   expected_body — composed body asserted in the OSC payload (None for no-op)
#   emits_stdout  — True iff stdout receives the JSON envelope


_RENDER_MATRIX = [
    # ─── Tier 1: plan_id-only ────────────────────────────────────────────
    {
        "id": "plan_id-only-hit",
        "tier": "plan_id-only",
        "outcome": "hit",
        "session_id": "sess-tier1-hit",
        "plan_id": "tier1-hit-plan",
        "current_phase": "5-execute",
        "short_desc": "t1-hit",
        "expected_body": "pm:5-execute:t1-hit",
        "emits_stdout": True,
    },
    {
        "id": "plan_id-only-miss",
        "tier": "plan_id-only",
        "outcome": "miss",
        "session_id": None,  # env unset
        "plan_id": None,
        "current_phase": None,
        "short_desc": None,
        "expected_body": None,
        "emits_stdout": False,
    },
    {
        "id": "plan_id-only-stale",
        "tier": "plan_id-only",
        "outcome": "stale",
        "session_id": "",  # env present but empty
        "plan_id": None,
        "current_phase": None,
        "short_desc": None,
        "expected_body": None,
        "emits_stdout": False,
    },
    # ─── Tier 2: title-from-status ───────────────────────────────────────
    {
        "id": "title-from-status-hit",
        "tier": "title-from-status",
        "outcome": "hit",
        "session_id": "sess-tier2-hit",
        "plan_id": "tier2-hit-plan",
        "current_phase": "3-outline",
        "short_desc": "t2-hit",
        "expected_body": "pm:3-outline:t2-hit",
        "emits_stdout": True,
    },
    {
        "id": "title-from-status-miss",
        "tier": "title-from-status",
        "outcome": "miss",
        "session_id": "sess-tier2-miss",
        "plan_id": None,  # no active-plan pointer
        "current_phase": None,
        "short_desc": None,
        "expected_body": None,
        "emits_stdout": False,
    },
    {
        "id": "title-from-status-stale",
        "tier": "title-from-status",
        "outcome": "stale",
        "session_id": "sess-tier2-stale",
        "plan_id": "",  # empty pointer file
        "current_phase": None,
        "short_desc": None,
        "expected_body": None,
        "emits_stdout": False,
    },
    # ─── Tier 3: status-from-plan ────────────────────────────────────────
    # PRODUCTION-DOMINANT CELL — main session at repo root + worktree active +
    # populated session cache + status.json with a live phase + UserPromptSubmit
    # trigger. This is the cell that fires on every hook during normal plan
    # execution. Do NOT remove or rename without auditing every other test that
    # references this naming.
    {
        "id": "status-from-plan-hit-session-A",  # PRODUCTION-DOMINANT (session A)
        "tier": "status-from-plan",
        "outcome": "hit",
        "session_id": "sess-tab-A",
        "plan_id": "plan-tab-A",
        "current_phase": "5-execute",
        "short_desc": "session-A-task",
        "expected_body": "pm:5-execute:session-A-task",
        "emits_stdout": True,
    },
    {
        "id": "status-from-plan-hit-session-B",  # cross-tab isolation partner
        "tier": "status-from-plan",
        "outcome": "hit",
        "session_id": "sess-tab-B",
        "plan_id": "plan-tab-B",
        "current_phase": "3-outline",
        "short_desc": "session-B-task",
        "expected_body": "pm:3-outline:session-B-task",
        "emits_stdout": True,
    },
    {
        "id": "status-from-plan-miss",
        "tier": "status-from-plan",
        "outcome": "miss",
        "session_id": "sess-tier3-miss",
        "plan_id": "tier3-miss-plan",
        "current_phase": None,  # no status.json
        "short_desc": None,
        "expected_body": None,
        "emits_stdout": False,
    },
    {
        "id": "status-from-plan-stale",
        "tier": "status-from-plan",
        "outcome": "stale",
        "session_id": "sess-tier3-stale",
        "plan_id": "tier3-stale-plan",
        "current_phase": "",  # status.json present but no current_phase
        "short_desc": "orphan",
        "expected_body": None,
        "emits_stdout": False,
    },
]


def _arrange_render_cell(
    cell: dict[str, Any], tmp_path: Path, monkeypatch
) -> None:
    """Materialize the on-disk + env state for one matrix cell.

    Writes the session cache pointer + plan ``status.json`` according to the
    cell's ``plan_id`` / ``current_phase`` / ``short_desc`` values, then
    redirects module-level constants and exports ``$CLAUDE_CODE_SESSION_ID``.
    """
    import claude_runtime as _cr

    monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")
    monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
    monkeypatch.chdir(tmp_path)

    session_id = cell["session_id"]
    if session_id is None:
        monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    else:
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", session_id)

    # Skip on-disk arrangement when the env var is unusable.
    if not session_id:
        return

    plan_pointer = cell["plan_id"]
    if plan_pointer is not None:
        cache_dir = tmp_path / "sessions" / session_id
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "active-plan").write_text(plan_pointer, encoding="utf-8")

    current_phase = cell["current_phase"]
    # Only materialize status.json when we have a non-empty plan pointer to
    # anchor the path. ``current_phase is None`` means "no status.json"; an
    # empty-string current_phase means "status.json present but unrenderable".
    if current_phase is not None and plan_pointer:
        plan_dir = tmp_path / ".plan" / "local" / "plans" / plan_pointer
        plan_dir.mkdir(parents=True, exist_ok=True)
        status: dict[str, Any] = {}
        if current_phase:
            status["current_phase"] = current_phase
        if cell["short_desc"] is not None:
            status["short_description"] = cell["short_desc"]
        (plan_dir / "status.json").write_text(json.dumps(status), encoding="utf-8")


class TestSessionRenderTitle:
    """Matrix-parametrized tests for ClaudeRuntime.session_render_title.

    Single parametrized class covering every {input-tier × hit/miss/stale}
    cell of the status.json-driven hook chain. See ``_RENDER_MATRIX`` above for
    the cell definitions and the production-dominant / cross-tab-isolation
    annotations.

    The three input tiers are:
      - plan_id-only        — $CLAUDE_CODE_SESSION_ID present in env
      - title-from-status   — active-plan pointer resolves a plan
      - status-from-plan    — status.json carries a non-empty current_phase

    Each tier yields one of three outcomes: hit, miss, stale. Each ``hit`` cell
    asserts the OSC payload carries the composer output ``{icon} {expected_body}``.
    """

    @pytest.mark.parametrize(
        "cell",
        _RENDER_MATRIX,
        ids=[cast(dict, c)["id"] for c in _RENDER_MATRIX],
    )
    def test_resolver_matrix(self, cell, rt, tmp_path, monkeypatch, capsys):
        """Every {tier × outcome} cell asserts the function returns "" and stdout matches the hook contract.

        Hook mode contract: stdout carries exactly the JSON envelope on
        success, exactly nothing on every noop. The function ALWAYS returns
        the empty string so the wrapper main() does not append a TOON tail.
        """
        _arrange_render_cell(cell, tmp_path, monkeypatch)
        capsys.readouterr()  # discard prior captures

        returned = rt.session_render_title()
        captured = capsys.readouterr().out

        # Function always returns "" — TOON observability has been removed
        # from the hook channel because the host parser drops mixed-content
        # stdout (see hook-authoring-guide.md).
        assert returned == "", (
            f"cell {cell['id']!r}: expected empty return, got {returned!r}"
        )

        if cell["emits_stdout"]:
            # Success branch emits the JSON envelope; assert the OSC payload
            # carries the composer output (active icon, no glyph) for this cell.
            payload = json.loads(captured)
            expected_osc = f"\x1b]0;➤ {cell['expected_body']}\x07"
            assert payload["terminalSequence"] == expected_osc, (
                f"cell {cell['id']!r}: OSC payload mismatch"
            )
            # No TOON success row glued to the envelope.
            assert "status:" not in captured, (
                f"cell {cell['id']!r}: TOON tail leaked into stdout: {captured!r}"
            )
        else:
            # No-op branches must write nothing to stdout.
            assert captured == "", (
                f"cell {cell['id']!r}: expected no stdout, got {captured!r}"
            )

    def test_cross_tab_isolation_session_A_does_not_leak_into_session_B(
        self, rt, tmp_path, monkeypatch, capsys
    ):
        """The two production-dominant cells (session A and session B) must
        resolve to distinct composed bodies — proving per-session state
        isolation across the resolver chain.

        Both sessions are arranged simultaneously; the renderer is invoked
        once per session and each invocation MUST observe only its own
        session's status.json.
        """
        import claude_runtime as _cr

        cell_a = next(c for c in _RENDER_MATRIX if c["id"] == "status-from-plan-hit-session-A")
        cell_b = next(c for c in _RENDER_MATRIX if c["id"] == "status-from-plan-hit-session-B")

        monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")
        monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.chdir(tmp_path)

        # Materialize BOTH sessions' on-disk state side by side.
        for cell in (cell_a, cell_b):
            cache_dir = tmp_path / "sessions" / cell["session_id"]
            cache_dir.mkdir(parents=True)
            (cache_dir / "active-plan").write_text(cell["plan_id"], encoding="utf-8")
            plan_dir = tmp_path / ".plan" / "local" / "plans" / cell["plan_id"]
            plan_dir.mkdir(parents=True)
            (plan_dir / "status.json").write_text(
                json.dumps(
                    {
                        "current_phase": cell["current_phase"],
                        "short_description": cell["short_desc"],
                    }
                ),
                encoding="utf-8",
            )

        # Session A invocation — must see session A's composed body only.
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", cell_a["session_id"])
        capsys.readouterr()
        returned_a = rt.session_render_title()
        captured_a = capsys.readouterr().out
        assert returned_a == ""
        payload_a = json.loads(captured_a)
        assert cell_a["expected_body"] in payload_a["terminalSequence"]
        assert cell_b["expected_body"] not in captured_a

        # Session B invocation — must see session B's composed body only.
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", cell_b["session_id"])
        capsys.readouterr()
        returned_b = rt.session_render_title()
        captured_b = capsys.readouterr().out
        assert returned_b == ""
        payload_b = json.loads(captured_b)
        assert cell_b["expected_body"] in payload_b["terminalSequence"]
        assert cell_a["expected_body"] not in captured_b


# =============================================================================
# 3c. session_render_title hook-mode state-aware icon (D1, stdin-driven)
# =============================================================================


class TestSessionRenderTitleStateAwareIcon:
    """Tests for hook-mode session_render_title icon selection driven by stdin payload.

    Hook mode reads the JSON payload Claude Code writes to stdin, parses
    ``hook_event_name`` + ``tool_name``, and resolves the icon via the canonical
    palette. The parse is best-effort: missing / empty / malformed stdin defaults
    to ``➤`` and never raises.
    """

    @staticmethod
    def _arrange(tmp_path, monkeypatch, *, session_id="sess-icon", plan_id="icon-plan",
                 current_phase="5-execute", short_description="icon-task"):
        _write_status_json(
            tmp_path, session_id=session_id, plan_id=plan_id,
            current_phase=current_phase, short_description=short_description,
        )
        _redirect_render_env(tmp_path, monkeypatch, session_id)
        # The composed body the renderer emits for this fixture.
        return f"pm:{current_phase}:{short_description}"

    @pytest.mark.parametrize(
        ("payload", "expected_icon"),
        [
            ({"hook_event_name": "UserPromptSubmit"}, "➤"),
            ({"hook_event_name": "Notification"}, "?"),
            ({"hook_event_name": "PreToolUse", "tool_name": "AskUserQuestion"}, "?"),
            ({"hook_event_name": "PreToolUse", "tool_name": "Bash"}, "⚙"),
            ({"hook_event_name": "PostToolUse", "tool_name": "AskUserQuestion"}, "➤"),
            ({"hook_event_name": "PostToolUse", "tool_name": "Bash"}, "➤"),
            ({"hook_event_name": "Stop"}, "✓"),
            ({"hook_event_name": "SessionStart"}, "➤"),
        ],
    )
    def test_hook_mode_icon_from_stdin_payload(
        self, payload, expected_icon, rt, tmp_path, monkeypatch, capsys
    ):
        """The OSC envelope embeds the icon the composer resolves from the stdin hook event."""
        from io import StringIO

        body = self._arrange(tmp_path, monkeypatch)
        monkeypatch.setattr("sys.stdin", StringIO(json.dumps(payload)))

        capsys.readouterr()
        returned = rt.session_render_title(statusline=False)
        captured = capsys.readouterr().out

        assert returned == ""
        envelope = json.loads(captured)
        assert envelope["terminalSequence"] == f"\x1b]0;{expected_icon} {body}\x07"

    @pytest.mark.parametrize("stdin_text", ["", "   ", "not-json{", "[1, 2, 3]"])
    def test_hook_mode_defensive_default_on_bad_stdin(
        self, stdin_text, rt, tmp_path, monkeypatch, capsys
    ):
        """Empty / whitespace / malformed / non-dict stdin defaults to ➤ and never raises."""
        from io import StringIO

        body = self._arrange(tmp_path, monkeypatch)
        monkeypatch.setattr("sys.stdin", StringIO(stdin_text))

        capsys.readouterr()
        returned = rt.session_render_title(statusline=False)
        captured = capsys.readouterr().out

        assert returned == ""
        envelope = json.loads(captured)
        assert envelope["terminalSequence"] == f"\x1b]0;➤ {body}\x07"

    def test_statusline_mode_keeps_active_icon_without_reading_stdin(
        self, rt, tmp_path, monkeypatch, capsys
    ):
        """statusLine mode never consults stdin — it always emits the active icon."""
        from io import StringIO

        body = self._arrange(tmp_path, monkeypatch)
        # Even with a Stop payload on stdin, statusLine mode keeps ➤.
        monkeypatch.setattr("sys.stdin", StringIO(json.dumps({"hook_event_name": "Stop"})))

        capsys.readouterr()
        returned = rt.session_render_title(statusline=True)
        captured = capsys.readouterr().out

        assert returned == ""
        assert captured == f"➤ {body}"


# =============================================================================
# 3c2. session_render_title hook-mode conditional sessionTitle emit
# =============================================================================


class TestSessionRenderTitleSessionTitleEmit:
    """Tests for the conditional ``hookSpecificOutput.sessionTitle`` emit.

    Hook mode augments the JSON envelope with a web/desktop session-title
    channel (equivalent to ``/rename``, UI-only) ONLY for the two events Claude
    Code supports it on:

      - ``UserPromptSubmit``; and
      - ``SessionStart`` with ``source ∈ {startup, resume}`` (the ``clear`` and
        ``compact`` sources do NOT support it).

    For every other event the envelope stays exactly ``{"terminalSequence":
    ...}``. The ``sessionTitle`` value is the bare ``title_body`` WITHOUT the
    icon glyph. ``terminalSequence`` is byte-for-byte identical regardless. A
    missing / malformed ``hook_event_name`` / ``source`` omits ``sessionTitle``
    and still emits ``terminalSequence`` (best-effort/no-raise contract).
    """

    @staticmethod
    def _arrange(tmp_path, monkeypatch, *, session_id="sess-title", plan_id="title-plan",
                 current_phase="5-execute", short_description="title-task"):
        _write_status_json(
            tmp_path, session_id=session_id, plan_id=plan_id,
            current_phase=current_phase, short_description=short_description,
        )
        _redirect_render_env(tmp_path, monkeypatch, session_id)
        # The composed (bare) body the sessionTitle channel carries.
        return f"pm:{current_phase}:{short_description}"

    def test_user_prompt_submit_emits_session_title(
        self, rt, tmp_path, monkeypatch, capsys
    ):
        """(a) UserPromptSubmit emits both terminalSequence and the icon-free sessionTitle."""
        from io import StringIO

        title_body = self._arrange(tmp_path, monkeypatch)
        monkeypatch.setattr(
            "sys.stdin", StringIO(json.dumps({"hook_event_name": "UserPromptSubmit"}))
        )

        capsys.readouterr()
        returned = rt.session_render_title(statusline=False)
        captured = capsys.readouterr().out

        assert returned == ""
        envelope = json.loads(captured)
        # terminalSequence carries the live icon, unchanged.
        assert envelope["terminalSequence"] == f"\x1b]0;➤ {title_body}\x07"
        # sessionTitle is the bare body — NO icon glyph.
        assert envelope["hookSpecificOutput"]["sessionTitle"] == title_body
        assert "➤" not in envelope["hookSpecificOutput"]["sessionTitle"]
        assert envelope["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"

    @pytest.mark.parametrize("source", ["startup", "resume"])
    def test_session_start_startup_or_resume_emits_session_title(
        self, source, rt, tmp_path, monkeypatch, capsys
    ):
        """(b) SessionStart with source startup/resume emits sessionTitle."""
        from io import StringIO

        title_body = self._arrange(tmp_path, monkeypatch)
        monkeypatch.setattr(
            "sys.stdin",
            StringIO(json.dumps({"hook_event_name": "SessionStart", "source": source})),
        )

        capsys.readouterr()
        returned = rt.session_render_title(statusline=False)
        captured = capsys.readouterr().out

        assert returned == ""
        envelope = json.loads(captured)
        assert envelope["terminalSequence"] == f"\x1b]0;➤ {title_body}\x07"
        assert envelope["hookSpecificOutput"]["sessionTitle"] == title_body
        assert envelope["hookSpecificOutput"]["hookEventName"] == "SessionStart"

    def test_session_start_compact_omits_session_title(
        self, rt, tmp_path, monkeypatch, capsys
    ):
        """(c) SessionStart with source compact emits ONLY terminalSequence.

        ``clear`` is deliberately NOT covered here: that source is a session
        teardown, not a render, and emits nothing at all — see
        ``TestSessionStartClearTeardown``.
        """
        from io import StringIO

        title_body = self._arrange(tmp_path, monkeypatch)
        monkeypatch.setattr(
            "sys.stdin",
            StringIO(json.dumps({"hook_event_name": "SessionStart", "source": "compact"})),
        )

        capsys.readouterr()
        returned = rt.session_render_title(statusline=False)
        captured = capsys.readouterr().out

        assert returned == ""
        envelope = json.loads(captured)
        assert envelope["terminalSequence"] == f"\x1b]0;➤ {title_body}\x07"
        assert "hookSpecificOutput" not in envelope

    @pytest.mark.parametrize(
        "payload",
        [
            {"hook_event_name": "Notification"},
            {"hook_event_name": "Stop"},
            {"hook_event_name": "PostToolUse", "tool_name": "Bash"},
            {"hook_event_name": "SessionStart"},  # SessionStart with NO source
        ],
    )
    def test_non_supporting_events_omit_session_title(
        self, payload, rt, tmp_path, monkeypatch, capsys
    ):
        """(d) Non-supporting events (and SessionStart without a source) emit ONLY terminalSequence."""
        from io import StringIO

        self._arrange(tmp_path, monkeypatch)
        monkeypatch.setattr("sys.stdin", StringIO(json.dumps(payload)))

        capsys.readouterr()
        returned = rt.session_render_title(statusline=False)
        captured = capsys.readouterr().out

        assert returned == ""
        envelope = json.loads(captured)
        # terminalSequence still present (with the event's icon).
        assert "terminalSequence" in envelope
        # No stray sessionTitle.
        assert "hookSpecificOutput" not in envelope

    @pytest.mark.parametrize("stdin_text", ["", "   ", "not-json{", "[1, 2, 3]"])
    def test_malformed_stdin_omits_session_title_but_still_emits_terminal_sequence(
        self, stdin_text, rt, tmp_path, monkeypatch, capsys
    ):
        """Best-effort/no-raise: bad stdin omits sessionTitle and still emits terminalSequence."""
        from io import StringIO

        title_body = self._arrange(tmp_path, monkeypatch)
        monkeypatch.setattr("sys.stdin", StringIO(stdin_text))

        capsys.readouterr()
        returned = rt.session_render_title(statusline=False)
        captured = capsys.readouterr().out

        assert returned == ""
        envelope = json.loads(captured)
        assert envelope["terminalSequence"] == f"\x1b]0;➤ {title_body}\x07"
        assert "hookSpecificOutput" not in envelope

    def test_statusline_mode_never_emits_session_title(
        self, rt, tmp_path, monkeypatch, capsys
    ):
        """(e) statusLine mode is unchanged — plain text, no JSON, no sessionTitle channel."""
        from io import StringIO

        title_body = self._arrange(tmp_path, monkeypatch)
        # Even a UserPromptSubmit payload on stdin yields plain text in statusLine mode.
        monkeypatch.setattr(
            "sys.stdin", StringIO(json.dumps({"hook_event_name": "UserPromptSubmit"}))
        )

        capsys.readouterr()
        returned = rt.session_render_title(statusline=True)
        captured = capsys.readouterr().out

        assert returned == ""
        assert captured == f"➤ {title_body}"
        assert "sessionTitle" not in captured
        assert "{" not in captured  # no JSON envelope

    def test_empty_title_body_emits_nothing(self, rt, tmp_path, monkeypatch, capsys):
        """(f) Empty/unrenderable state is a no-op even for a supporting event — nothing on stdout."""
        from io import StringIO

        # status.json present but with no current_phase → composer returns None.
        _write_status_json(
            tmp_path,
            session_id="sess-empty-title",
            plan_id="empty-title-plan",
            current_phase=None,
            short_description=None,
        )
        _redirect_render_env(tmp_path, monkeypatch, "sess-empty-title")
        monkeypatch.setattr(
            "sys.stdin", StringIO(json.dumps({"hook_event_name": "UserPromptSubmit"}))
        )

        capsys.readouterr()
        returned = rt.session_render_title(statusline=False)
        captured = capsys.readouterr().out

        assert returned == ""
        assert captured == ""


# =============================================================================
# session_bind / session_resolve_plan / session_doctor
# =============================================================================


class TestSessionBindResolveDoctor:
    """Tests for the relocated session-binding verbs on ClaudeRuntime.

    ``session bind`` writes the caller's slot last-driven-wins; ``session
    resolve-plan`` reads it back; ``session doctor`` scans for conflicts, GCs
    stale slots, and reports/prunes orphan directories. All delegate to the pure
    ``session_binding`` policy, so the cache root is redirected via
    ``session_binding._SESSION_CACHE_BASE``.
    """

    def test_bind_writes_slot_from_env_session(self, rt, tmp_path, monkeypatch):
        """session bind resolves session id from $CLAUDE_CODE_SESSION_ID and writes the slot."""
        from toon_parser import parse_toon

        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-bind-env")
        parsed = parse_toon(rt.session_bind("plan-1"))
        assert parsed["status"] == "success"
        assert parsed["bound"] is True
        assert session_binding.resolve_plan("sess-bind-env") == "plan-1"

    def test_bind_uses_explicit_session_id_over_env(self, rt, tmp_path, monkeypatch):
        """An explicit session_id argument takes precedence over the env var."""
        from toon_parser import parse_toon

        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-env")
        parsed = parse_toon(rt.session_bind("plan-2", "sess-explicit"))
        assert parsed["bound"] is True
        assert session_binding.resolve_plan("sess-explicit") == "plan-2"
        assert session_binding.resolve_plan("sess-env") is None

    def test_bind_last_driven_wins(self, rt, tmp_path, monkeypatch):
        """A second bind to a different plan overwrites — never protects the prior binding."""
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-ldw")
        rt.session_bind("plan-old")
        rt.session_bind("plan-new")
        assert session_binding.resolve_plan("sess-ldw") == "plan-new"

    def test_bind_no_session_id_reports_unbound(self, rt, monkeypatch):
        """Without a session id, bind reports bound=False with a reason and writes nothing."""
        from toon_parser import parse_toon

        monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
        parsed = parse_toon(rt.session_bind("plan-1"))
        assert parsed["bound"] is False
        assert parsed["reason"] == "no_session_id"

    def test_resolve_plan_returns_bound(self, rt, tmp_path, monkeypatch):
        """session resolve-plan returns the plan bound to the session."""
        from toon_parser import parse_toon

        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-resolve")
        rt.session_bind("plan-r")
        parsed = parse_toon(rt.session_resolve_plan())
        assert parsed["resolved"] is True
        assert parsed["plan_id"] == "plan-r"

    def test_resolve_plan_unbound_returns_empty(self, rt, monkeypatch):
        """An unbound session resolves to an empty plan id."""
        from toon_parser import parse_toon

        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-unbound")
        parsed = parse_toon(rt.session_resolve_plan())
        assert parsed["resolved"] is False
        assert parsed["plan_id"] == ""

    def test_doctor_reports_conflict(self, rt, tmp_path, monkeypatch):
        """session doctor reports a two-sessions-one-plan conflict."""
        from toon_parser import parse_toon

        monkeypatch.setattr(session_binding, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".plan" / "local" / "plans" / "shared-plan").mkdir(parents=True)
        session_binding.bind("sess-d-a", "shared-plan")
        session_binding.bind("sess-d-b", "shared-plan")
        parsed = parse_toon(rt.session_doctor())
        assert parsed["conflict_count"] == 1
        assert "shared-plan=" in parsed["conflicts"][0]

    def test_doctor_fix_gcs_stale_slot(self, rt, tmp_path, monkeypatch):
        """session doctor --fix removes a stale slot whose plan is archived/deleted."""
        from toon_parser import parse_toon

        monkeypatch.setattr(session_binding, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".plan" / "local" / "plans" / "live-plan").mkdir(parents=True)
        session_binding.bind("sess-live", "live-plan")
        session_binding.bind("sess-gone", "gone-plan")
        parsed = parse_toon(rt.session_doctor(fix=True))
        assert parsed["gc_removed"] == 1
        assert session_binding.resolve_plan("sess-gone") is None
        assert session_binding.resolve_plan("sess-live") == "live-plan"

    def test_doctor_renders_orphan_rows_on_a_plain_scan(self, rt, tmp_path, monkeypatch):
        """An orphan directory surfaces as a bare session-id row with a zero removal count."""
        monkeypatch.setattr(session_binding, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.chdir(tmp_path)
        (tmp_path / "sessions" / "sess-orphan").mkdir(parents=True)

        parsed = parse_toon(rt.session_doctor())

        assert parsed["orphan_count"] == 1
        assert parsed["orphans"] == ["sess-orphan"]
        assert parsed["orphans_removed"] == 0
        # A plain scan reports without mutating.
        assert (tmp_path / "sessions" / "sess-orphan").is_dir()

    def test_doctor_fix_prunes_orphan_directory(self, rt, tmp_path, monkeypatch):
        """session doctor --fix prunes the orphan directory and counts it separately."""
        monkeypatch.setattr(session_binding, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".plan" / "local" / "plans" / "live-plan").mkdir(parents=True)
        session_binding.bind("sess-live", "live-plan")
        (tmp_path / "sessions" / "sess-orphan").mkdir(parents=True)

        parsed = parse_toon(rt.session_doctor(fix=True))

        assert parsed["orphans"] == ["sess-orphan"]
        assert parsed["orphans_removed"] == 1
        assert parsed["gc_removed"] == 0  # orphans are not stale slots
        assert not (tmp_path / "sessions" / "sess-orphan").exists()
        assert session_binding.resolve_plan("sess-live") == "live-plan"


# =============================================================================
# session_push_title_token — optional icon
# =============================================================================


class TestSessionPushTitleTokenOptionalIcon:
    """Tests that session_push_title_token accepts an optional icon.

    With an explicit icon the glyph is passed to the composer as an override;
    with no icon the composer receives ``icon_override=None`` (a plain repaint
    with the default active icon).
    """

    def _arrange(self, tmp_path, monkeypatch, plan_id="push-plan"):
        _write_status_json(
            tmp_path, session_id="sess-push", plan_id=plan_id,
            current_phase="5-execute", short_description="push-task",
        )
        monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")
        monkeypatch.chdir(tmp_path)

    def test_icon_override_passed_to_composer(self, rt, tmp_path, monkeypatch):
        """An explicit --icon is forwarded to the composer as icon_override."""
        import _claude_runtime_impl

        self._arrange(tmp_path, monkeypatch)
        captured: dict[str, Any] = {}

        def fake_compose(state, process_state, icon_override=None):
            captured["icon_override"] = icon_override
            return "TITLE"

        monkeypatch.setattr(_claude_runtime_impl, "compose", fake_compose)
        rt.session_push_title_token("push-plan", "⏳")
        assert captured["icon_override"] == "⏳"

    def test_no_icon_passes_none_to_composer(self, rt, tmp_path, monkeypatch):
        """Omitting --icon forwards icon_override=None (plain repaint)."""
        import _claude_runtime_impl

        self._arrange(tmp_path, monkeypatch)
        captured: dict[str, Any] = {}

        def fake_compose(state, process_state, icon_override=None):
            captured["icon_override"] = icon_override
            return "TITLE"

        monkeypatch.setattr(_claude_runtime_impl, "compose", fake_compose)
        rt.session_push_title_token("push-plan")
        assert captured["icon_override"] is None

    def test_no_title_state_reports_not_pushed(self, rt, tmp_path, monkeypatch):
        """Missing state is a best-effort no-op (pushed=False), with or without an icon."""
        from toon_parser import parse_toon

        monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")
        monkeypatch.chdir(tmp_path)
        parsed = parse_toon(rt.session_push_title_token("no-such-plan"))
        assert parsed["pushed"] is False


# =============================================================================
# D3: session_render_title orchestrator fallback (PRIMARY hook channel)
# =============================================================================


class TestSessionRenderTitleOrchestratorFallback:
    """D3: with no plan bound, session_render_title falls back to the ORCHESTRATOR
    epic binding so the orchestrator title reaches the PRIMARY hook channel
    (stdout) — which needs no controlling tty. The plan-bound render path is
    unchanged (D5(c)): the orchestrator fallback is reached only when the plan
    slot is empty.
    """

    def test_epic_bound_no_tty_renders_orchestrator_terminal_sequence(
        self, rt, tmp_path, monkeypatch, capsys
    ):
        """An epic-bound session with NO plan renders a non-empty orchestrator
        terminalSequence from the hook path (stdout) — no /dev/tty involved."""
        import claude_runtime as _cr

        session_id = "sess-orch-render"
        slug = "my-epic"
        _redirect_render_env(tmp_path, monkeypatch, session_id)
        # Bind the session to the EPIC (orchestrator slot), not a plan.
        session_binding.bind_orchestrator(session_id, slug)
        # Isolate the render-fallback wiring from orchestrator-store resolution
        # (the state read is exercised elsewhere): prove the slug resolved from
        # the session binding flows into compose + emit.
        monkeypatch.setattr(
            _cr,
            "_read_orchestrator_title_state",
            lambda s: {"kind": "orchestrator", "slug": s} if s == slug else None,
        )

        capsys.readouterr()
        returned = rt.session_render_title(statusline=False)
        captured = capsys.readouterr().out

        assert returned == ""
        envelope = json.loads(captured)
        # PRIMARY hook channel: a non-empty orchestrator terminalSequence.
        assert envelope["terminalSequence"] == "\x1b]0;➤ Orchestrator-my-epic\x07"

    def test_no_plan_and_no_epic_binding_renders_nothing(
        self, rt, tmp_path, monkeypatch, capsys
    ):
        """With neither a plan nor an epic bound, render is a no-op (empty stdout)."""
        session_id = "sess-neither"
        _redirect_render_env(tmp_path, monkeypatch, session_id)

        capsys.readouterr()
        assert rt.session_render_title(statusline=False) == ""
        assert capsys.readouterr().out == ""

    def test_plan_binding_takes_precedence_over_epic(
        self, rt, tmp_path, monkeypatch, capsys
    ):
        """A plan binding wins: the plan-bound render path is unchanged (D5(c)) —
        the orchestrator fallback is never consulted when a plan is bound."""
        import claude_runtime as _cr

        session_id = "sess-plan-wins"
        _write_status_json(
            tmp_path, session_id=session_id, plan_id="the-plan",
            current_phase="5-execute", short_description="plan-task",
        )
        _redirect_render_env(tmp_path, monkeypatch, session_id)
        # Tripwire: if the orchestrator fallback is wrongly consulted it records
        # the call; the plan-bound path must never reach it.
        orch_calls: list[str] = []
        monkeypatch.setattr(
            _cr,
            "_read_orchestrator_title_state",
            lambda s: (orch_calls.append(s), {"kind": "orchestrator", "slug": s})[1],
        )

        capsys.readouterr()
        returned = rt.session_render_title(statusline=False)
        captured = capsys.readouterr().out

        assert returned == ""
        envelope = json.loads(captured)
        assert envelope["terminalSequence"] == "\x1b]0;➤ pm:5-execute:plan-task\x07"
        assert orch_calls == []


# =============================================================================
# D3: session_push_title_token store="orchestrator" (bind + feature_inactive)
# =============================================================================


class TestSessionPushTitleTokenOrchestrator:
    """D3: the orchestrator-store push establishes the session→epic binding as a
    best-effort side effect (so the PRIMARY hook channel takes over on the next
    render) and distinguishes a configured-OFF feature (feature_inactive) from the
    permanently-inert /dev/tty fallback (no_controlling_tty).
    """

    @staticmethod
    def _stub_orch_state(monkeypatch):
        import claude_runtime as _cr

        monkeypatch.setattr(
            _cr,
            "_read_orchestrator_title_state",
            lambda s: {"kind": "orchestrator", "slug": s},
        )

    def test_orchestrator_push_binds_the_epic(self, rt, tmp_path, monkeypatch):
        """The orchestrator push establishes the session→epic binding so the
        PRIMARY hook channel resolves the epic on the next render."""
        monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-orch-push")
        monkeypatch.chdir(tmp_path)
        _activate_terminal_title(tmp_path)
        self._stub_orch_state(monkeypatch)
        _patch_dev_tty(monkeypatch, openable=True)

        rt.session_push_title_token("", store="orchestrator", slug="my-epic")

        assert session_binding.resolve_orchestrator("sess-orch-push") == "my-epic"

    def test_orchestrator_push_reports_feature_inactive_when_off(self, rt, tmp_path, monkeypatch):
        """With the terminal-title feature configured OFF, the orchestrator push
        returns pushed: false / reason: feature_inactive — the gate fires BEFORE
        the /dev/tty attempt, distinct from the no_controlling_tty fallback."""
        from toon_parser import parse_toon

        monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-orch-inactive")
        monkeypatch.chdir(tmp_path)
        # NO _activate_terminal_title → _terminal_title_active() is False.
        self._stub_orch_state(monkeypatch)
        # /dev/tty is openable, but the feature gate fires first.
        _patch_dev_tty(monkeypatch, openable=True)

        result = parse_toon(rt.session_push_title_token("", store="orchestrator", slug="my-epic"))

        assert result["pushed"] is False
        assert result["reason"] == "feature_inactive"

    def test_orchestrator_push_reports_no_controlling_tty_when_active_but_no_tty(
        self, rt, tmp_path, monkeypatch
    ):
        """With the feature ACTIVE but no controlling terminal, the orchestrator
        push clears the feature gate and reports no_controlling_tty."""
        from toon_parser import parse_toon

        monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-orch-notty")
        monkeypatch.chdir(tmp_path)
        _activate_terminal_title(tmp_path)
        self._stub_orch_state(monkeypatch)
        _patch_dev_tty(monkeypatch, openable=False)

        result = parse_toon(rt.session_push_title_token("", store="orchestrator", slug="my-epic"))

        assert result["pushed"] is False
        assert result["reason"] == "no_controlling_tty"
        assert result["delivery"] == "dev_tty_fallback"

    def test_orchestrator_push_binds_even_when_feature_inactive(self, rt, tmp_path, monkeypatch):
        """The epic binding is established BEFORE the feature gate, so it lands
        even when the push itself reports feature_inactive — the PRIMARY channel
        can then deliver once the feature is turned on."""
        monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-orch-bind-inactive")
        monkeypatch.chdir(tmp_path)
        self._stub_orch_state(monkeypatch)
        _patch_dev_tty(monkeypatch, openable=True)

        rt.session_push_title_token("", store="orchestrator", slug="my-epic")

        assert session_binding.resolve_orchestrator("sess-orch-bind-inactive") == "my-epic"
