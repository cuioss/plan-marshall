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
from typing import Any

import pytest

# conftest.py sets up PYTHONPATH so cross-skill imports resolve without manual
# sys.path manipulation. The ``claude_runtime`` entry re-exports ``ClaudeRuntime``
# (now defined in ``_claude_runtime_impl.py``), so this import mechanism is
# unchanged from ``test_claude_runtime.py``.
from claude_runtime import ClaudeRuntime


# =============================================================================
# Fixture
# =============================================================================


@pytest.fixture()
def rt(tmp_path, monkeypatch):
    """Return a ClaudeRuntime instance with all filesystem roots redirected.

    Monkeypatches the module-level constants that control where marshal.json,
    session cache, and settings files land so no real files are mutated.
    """
    import claude_runtime as _cr

    monkeypatch.setattr(_cr, "_SESSION_CACHE_BASE", tmp_path / "sessions")
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

    monkeypatch.setattr(_cr, "_SESSION_CACHE_BASE", tmp_path / "sessions")
    monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", session_id)
    monkeypatch.chdir(tmp_path)


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
        import claude_runtime as _cr

        monkeypatch.setattr(_cr, "_SESSION_CACHE_BASE", tmp_path / "sessions")
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

        monkeypatch.setattr(_cr, "_SESSION_CACHE_BASE", tmp_path / "sessions")
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
        import claude_runtime as _cr

        monkeypatch.setattr(_cr, "_SESSION_CACHE_BASE", tmp_path / "sessions")
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

        monkeypatch.setattr(_cr, "_SESSION_CACHE_BASE", tmp_path / "sessions")
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

    monkeypatch.setattr(_cr, "_SESSION_CACHE_BASE", tmp_path / "sessions")
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
        ids=[c["id"] for c in _RENDER_MATRIX],
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

        monkeypatch.setattr(_cr, "_SESSION_CACHE_BASE", tmp_path / "sessions")
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

    @pytest.mark.parametrize("source", ["clear", "compact"])
    def test_session_start_clear_or_compact_omits_session_title(
        self, source, rt, tmp_path, monkeypatch, capsys
    ):
        """(c) SessionStart with source clear/compact emits ONLY terminalSequence."""
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
