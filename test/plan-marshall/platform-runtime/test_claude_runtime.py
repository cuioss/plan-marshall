#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for claude_runtime.py — ClaudeRuntime implementation of all 24 operations.

Covers every method defined by the Runtime ABC:
  1.  project_initial_setup       — creates dirs, writes marshal.json, installs hook
  2.  session_capture             — reads $CLAUDE_CODE_SESSION_ID, stores via manage-status
  3.  session_render_title        — resolves session → plan → OSC emit
  4.  session_push_title_token    — live /dev/tty repaint (icon now optional)
  4b. session_bind / resolve-plan / doctor — the relocated last-driven-wins binding
      policy (covered in depth by test__claude_runtime_impl.py)
  5.  permission_configure        — overwrites allow list in settings
  6.  permission_analyze          — audits redundant / suspicious / missing-steps
  7.  permission_fix              — normalize / add / remove / ensure / consolidate
  8.  permission_ensure_wildcards — scans marketplace bundles, adds wildcard perms
  9.  permission_ensure_steps     — ensures project:{skill} step permissions
  10. permission_web_analyze       — audits WebFetch domain permissions
  11. permission_web_apply         — adds / removes WebFetch domain permissions
  12. metrics_capture             — records token consumption
  13. subagent_dispatch           — returns Task: invocation parameters
  14. wait_for                    — bounded poll of a concrete observable
  15. health_check               — verifies platform integration

All filesystem writes are redirected to tmp_path via monkeypatching so no
real settings files are mutated.

Integration test: test_project_initial_setup_fresh_init is a full end-to-end
test that exercises the happy-path of project_initial_setup without mocking.
"""
from __future__ import annotations  # noqa: I001

import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# conftest.py sets up PYTHONPATH so cross-skill imports resolve without manual
# sys.path manipulation.
import claude_runtime
import session_binding
from claude_runtime import (
    _BUILD_WRAPPER_NOTATIONS,
    ClaudeRuntime,
    _command_is_build,
    _ENFORCEMENT_HOOK_COMMAND,
    _HOOK_COMMAND,
    _RENDER_HOOK_COMMAND,
    _STATUSLINE_COMMAND,
)
from toon_parser import parse_toon


# =============================================================================
# Helpers
# =============================================================================


def _make_settings(allow: list[str] | None = None) -> dict[str, Any]:
    """Build a minimal settings dict for tests."""
    return {"permissions": {"allow": list(allow or []), "deny": [], "ask": []}}


def _write_settings(path: Path, allow: list[str] | None = None) -> None:
    """Write a minimal settings.json at *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_make_settings(allow)), encoding="utf-8")


def _make_marshal(target: str = "claude") -> dict[str, Any]:
    return {"runtime": {"target": target}}


def _parsed(output: str) -> dict[str, Any]:
    """Parse TOON output and return the result dict."""
    return parse_toon(output)


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

    monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")
    monkeypatch.setattr(_cr, "_CLAUDE_PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
    return ClaudeRuntime()


# =============================================================================
# 3b. _read_active_orchestrator — session → epic slug read delegation
# =============================================================================


class TestReadActiveOrchestrator:
    """Tests for the ``_read_active_orchestrator`` session-cache read helper.

    A thin delegation to ``session_binding.resolve_orchestrator`` — the
    orchestrator-slot counterpart of ``_read_active_plan``. ``session
    render-title`` resolves a session→epic binding through it when no plan is
    bound, so the orchestrator title reaches the PRIMARY hook channel.
    """

    def test_returns_bound_epic_slug(self, tmp_path, monkeypatch):
        """After bind_orchestrator, the helper returns the bound epic slug."""
        monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")
        session_binding.bind_orchestrator("sess-orch-read", "my-epic")
        assert claude_runtime._read_active_orchestrator("sess-orch-read") == "my-epic"

    def test_unbound_session_returns_none(self, tmp_path, monkeypatch):
        """An unbound session resolves to None."""
        monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")
        assert claude_runtime._read_active_orchestrator("sess-orch-none") is None

    def test_malformed_session_id_returns_none(self, tmp_path, monkeypatch):
        """A malformed session id resolves to None without touching disk."""
        monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")
        assert claude_runtime._read_active_orchestrator("../evil") is None

    def test_plan_binding_does_not_leak_into_orchestrator_read(self, tmp_path, monkeypatch):
        """A plan-bound session (no epic) resolves None on the orchestrator read —
        the two kind-disjoint slots do not cross-read."""
        monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")
        session_binding.bind("sess-plan-only", "some-plan")
        assert claude_runtime._read_active_orchestrator("sess-plan-only") is None


# =============================================================================
# 1. project_initial_setup
# =============================================================================


class TestProjectInitialSetup:
    """Tests for ClaudeRuntime.project_initial_setup."""

    def test_unknown_target_returns_error(self, rt, tmp_path):
        """Passing an unknown target returns status=error."""
        result = _parsed(rt.project_initial_setup(str(tmp_path), "unknown_target"))
        assert result["status"] == "error"
        assert result["error"] == "unknown_target"

    def test_creates_plan_temp_directory(self, rt, tmp_path):
        """project_initial_setup creates .plan/temp/ under the project dir."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        output = rt.project_initial_setup(str(project_dir), "claude")
        result = _parsed(output)
        assert result["status"] == "success"
        assert (project_dir / ".plan" / "temp").is_dir()

    def test_writes_marshal_json_with_runtime_target(self, rt, tmp_path):
        """project_initial_setup writes .plan/marshal.json with runtime.target=claude."""
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        rt.project_initial_setup(str(project_dir), "claude")
        marshal = json.loads((project_dir / ".plan" / "marshal.json").read_text())
        assert marshal["runtime"]["target"] == "claude"
        assert marshal["project_dir"] == str(project_dir.resolve())

    def test_response_includes_target_and_marshal_written(self, rt, tmp_path):
        """Success response includes target, project_dir, marshal_written fields."""
        project_dir = tmp_path / "proj2"
        project_dir.mkdir()
        result = _parsed(rt.project_initial_setup(str(project_dir), "claude"))
        assert result["target"] == "claude"
        assert result["marshal_written"] is True

    def test_hook_not_installed_twice(self, rt, tmp_path):
        """Calling project_initial_setup twice does not duplicate the hook entry."""
        project_dir = tmp_path / "proj3"
        project_dir.mkdir()
        rt.project_initial_setup(str(project_dir), "claude")
        rt.project_initial_setup(str(project_dir), "claude")
        settings = json.loads((project_dir / ".claude" / "settings.json").read_text())
        session_starts = settings.get("hooks", {}).get("SessionStart", [])
        hook_count = sum(
            sum(1 for h in entry.get("hooks", []) if h.get("command") == _HOOK_COMMAND)
            for entry in session_starts
            if isinstance(entry, dict)
        )
        assert hook_count == 1

    def test_installs_session_start_hook(self, rt, tmp_path):
        """project_initial_setup writes the SessionStart hook to .claude/settings.json."""
        project_dir = tmp_path / "proj4"
        project_dir.mkdir()
        result = _parsed(rt.project_initial_setup(str(project_dir), "claude"))
        assert result["hook_installed"] is True
        settings_path = project_dir / ".claude" / "settings.json"
        assert settings_path.is_file()
        settings = json.loads(settings_path.read_text())
        session_starts = settings.get("hooks", {}).get("SessionStart", [])
        assert len(session_starts) >= 1


class TestProjectInitialSetupFreshInit:
    """Fresh-init integration test — no mocking, real filesystem operations."""

    def test_fresh_init_creates_all_expected_artifacts(self, tmp_path):
        """Full happy-path: directories, marshal.json, and SessionStart hook all created."""
        project_dir = tmp_path / "integration-project"
        project_dir.mkdir()

        # Run without any monkeypatching — real filesystem operations.
        runtime = ClaudeRuntime()
        output = runtime.project_initial_setup(str(project_dir), "claude")
        result = _parsed(output)

        # Status
        assert result["status"] == "success"
        assert result["target"] == "claude"
        assert result["marshal_written"] is True

        # Directory structure
        assert (project_dir / ".plan").is_dir()
        assert (project_dir / ".plan" / "temp").is_dir()

        # marshal.json content
        marshal_path = project_dir / ".plan" / "marshal.json"
        assert marshal_path.is_file()
        marshal = json.loads(marshal_path.read_text())
        assert marshal["runtime"]["target"] == "claude"
        assert "project_dir" in marshal

        # SessionStart hook in settings.json
        settings_path = project_dir / ".claude" / "settings.json"
        assert settings_path.is_file()
        settings = json.loads(settings_path.read_text())
        session_starts = settings.get("hooks", {}).get("SessionStart", [])
        hook_commands = [
            h.get("command")
            for entry in session_starts
            if isinstance(entry, dict)
            for h in entry.get("hooks", [])
            if isinstance(h, dict)
        ]
        assert _HOOK_COMMAND in hook_commands


# =============================================================================
# 1b. project_install_hook — terminal-title wiring (render hooks + statusLine + env)
# =============================================================================


def _collect_commands(entries: list[dict[str, Any]]) -> list[str]:
    """Return the list of hook commands inside a hooks-event entry list."""
    commands: list = [
        h.get("command")
        for entry in entries
        if isinstance(entry, dict)
        for h in entry.get("hooks", [])
        if isinstance(h, dict)
    ]
    return commands


def _count_command(entries: list[dict[str, Any]], command: str) -> int:
    """Count how many times *command* appears across a hooks-event entry list."""
    return sum(1 for c in _collect_commands(entries) if c == command)


# =============================================================================
# 1c. Missing-executor fail-soft guard (FIX 2)
# =============================================================================


class TestExecutorGuardFailSoft:
    """The executor-invoking hook commands are wrapped in a missing-executor
    guard so an absent ``.plan/execute-script.py`` is a silent no-op (exit 0, no
    output the hook surfaces as a block) while a present executor still runs.

    This is the FIX-2 stopgap: while a worktree-backed plan sits mid-phase-5 the
    main checkout's executor is transiently absent, and an unguarded hook command
    would raise ``[Errno 2] No such file or directory`` on every user prompt.
    """

    def test_command_constants_are_guarded(self):
        """Every executor-invoking command constant carries the guard wrapper."""
        for command in (_RENDER_HOOK_COMMAND, _STATUSLINE_COMMAND, _HOOK_COMMAND):
            assert command.startswith("[ -f .plan/execute-script.py ] && ")
            assert command.endswith(" || true")
            assert "python3 .plan/execute-script.py" in command
        # The statusLine variant passes --statusline to the renderer (BEFORE the
        # trailing || true), never after it.
        assert "render-title --statusline || true" in _STATUSLINE_COMMAND

    def test_absent_executor_exits_zero_silently(self, tmp_path):
        """With no .plan/execute-script.py in cwd, the guarded render command exits
        0 and emits nothing — the [ -f ] test short-circuits before python3 runs."""
        result = subprocess.run(
            _RENDER_HOOK_COMMAND,
            shell=True,
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout == ""
        assert result.stderr == ""

    def test_present_executor_runs_the_command(self, tmp_path):
        """With a .plan/execute-script.py present, the guard's then-branch fires and
        runs the command (a stub executor writes a marker proving it ran)."""
        plan_dir = tmp_path / ".plan"
        plan_dir.mkdir()
        marker = tmp_path / "ran.txt"
        (plan_dir / "execute-script.py").write_text(
            "#!/usr/bin/env python3\n"
            "import pathlib\n"
            f"pathlib.Path({str(marker)!r}).write_text('ran')\n"
        )
        result = subprocess.run(
            _RENDER_HOOK_COMMAND,
            shell=True,
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert marker.is_file()
        assert marker.read_text() == "ran"

    def test_install_writes_guarded_command_and_health_check_matches(self, rt, tmp_path):
        """_install_terminal_title_hooks writes the guarded command form, and
        _has_render_entry still matches it (install + health-check stay consistent
        because both read the same single-sourced constant)."""
        import claude_runtime as _cr

        target = tmp_path / ".claude" / "settings.local.json"
        rt.project_install_hook(str(target))
        settings = json.loads(target.read_text())
        ups = settings["hooks"]["UserPromptSubmit"]
        commands = _collect_commands(ups)
        assert commands  # at least one render entry installed
        assert all(c == _RENDER_HOOK_COMMAND for c in commands)
        assert all(c.startswith("[ -f .plan/execute-script.py ] && ") for c in commands)
        # The health-check matcher recognizes the guarded installed command.
        assert _cr._has_render_entry(ups, matcher="")


class TestInstallTerminalTitleHooks:
    """Tests for ClaudeRuntime.project_install_hook covering the full terminal-title wiring.

    Covers (a) fresh install creates all seven render-trigger hook entries plus
    statusLine plus env entry; (b) re-running is idempotent; (c) existing
    statusLine with a different command yields already_present_other; (d)
    existing env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE with a different value
    yields already_present_other; (e) --overwrite-statusline /
    --overwrite-env-disable flags overwrite; (f) existing claude_hook
    SessionStart entry is preserved.
    """

    # ------------------------------------------------------------------
    # (a) Fresh install wires all seven render-trigger entries + statusLine + env.
    # ------------------------------------------------------------------

    def test_fresh_install_creates_all_render_events(self, rt, tmp_path):
        """Fresh install populates SessionStart (ONE matcher-less entry), UserPromptSubmit,
        Notification, Stop, PreToolUse:AskUserQuestion, PreToolUse:Bash, and a
        matcher-less PostToolUse entry with the renderer command."""
        target = tmp_path / ".claude" / "settings.local.json"
        result = _parsed(rt.project_install_hook(str(target)))
        assert result["status"] == "success"
        assert result["hook_installed"] is True

        settings = json.loads(target.read_text())
        hooks_block = settings["hooks"]

        # SessionStart has BOTH the existing capture entry AND exactly ONE
        # matcher-less render entry. The matcher-less entry already fires for
        # every source (including "clear", which the renderer turns into a
        # session teardown), so no matcher:"clear" variant is installed.
        session_start = hooks_block["SessionStart"]
        assert _count_command(session_start, _RENDER_HOOK_COMMAND) == 1
        matchers_with_render = [
            entry.get("matcher", "")
            for entry in session_start
            if isinstance(entry, dict)
            and any(h.get("command") == _RENDER_HOOK_COMMAND for h in entry.get("hooks", []))
        ]
        assert matchers_with_render == [""]

        # UserPromptSubmit, Notification, Stop — each one matcher-less render entry.
        for event_name in ("UserPromptSubmit", "Notification", "Stop"):
            event_entries = hooks_block[event_name]
            assert _count_command(event_entries, _RENDER_HOOK_COMMAND) == 1
            # The single entry is matcher-less.
            assert event_entries[0].get("matcher", "") == ""

        # PreToolUse: matcher="AskUserQuestion" AND matcher="Bash" render entries.
        pre_tool_use = hooks_block["PreToolUse"]
        assert _count_command(pre_tool_use, _RENDER_HOOK_COMMAND) == 2
        pre_matchers = {
            entry.get("matcher")
            for entry in pre_tool_use
            if isinstance(entry, dict)
            and any(h.get("command") == _RENDER_HOOK_COMMAND for h in entry.get("hooks", []))
        }
        assert pre_matchers == {"AskUserQuestion", "Bash"}

        # PostToolUse: exactly ONE matcher-less render entry (every tool call).
        post_tool_use = hooks_block["PostToolUse"]
        assert _count_command(post_tool_use, _RENDER_HOOK_COMMAND) == 1
        post_matchers = {
            entry.get("matcher", "")
            for entry in post_tool_use
            if isinstance(entry, dict)
            and any(h.get("command") == _RENDER_HOOK_COMMAND for h in entry.get("hooks", []))
        }
        assert post_matchers == {""}

    def test_fresh_install_writes_statusline_command(self, rt, tmp_path):
        """Fresh install writes statusLine = {type: command, command: _STATUSLINE_COMMAND}."""
        target = tmp_path / ".claude" / "settings.local.json"
        result = _parsed(rt.project_install_hook(str(target)))
        assert result["statusLine_status"] == "installed"

        settings = json.loads(target.read_text())
        assert settings["statusLine"]["type"] == "command"
        assert settings["statusLine"]["command"] == _STATUSLINE_COMMAND

    def test_fresh_install_writes_env_disable_entry(self, rt, tmp_path):
        """Fresh install writes env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE = "1"."""
        target = tmp_path / ".claude" / "settings.local.json"
        result = _parsed(rt.project_install_hook(str(target)))
        assert result["env_status"] == "installed"

        settings = json.loads(target.read_text())
        assert settings["env"]["CLAUDE_CODE_DISABLE_TERMINAL_TITLE"] == "1"

    def test_fresh_install_response_lists_installed_events(self, rt, tmp_path):
        """installed_events lists every event freshly wired (SessionStart counted once)."""
        target = tmp_path / ".claude" / "settings.local.json"
        result = _parsed(rt.project_install_hook(str(target)))
        installed = result["installed_events"]
        # SessionStart appears once even though two render entries were added.
        # The tool-scoped entries use matcher-qualified labels.
        assert set(installed) == {
            "SessionStart",
            "UserPromptSubmit",
            "Notification",
            "Stop",
            "PreToolUse:AskUserQuestion",
            "PreToolUse:Bash",
            "PostToolUse",
        }

    # ------------------------------------------------------------------
    # (b) Re-running is idempotent across all hook blocks.
    # ------------------------------------------------------------------

    def test_idempotent_second_run_adds_nothing(self, rt, tmp_path):
        """Re-invoking after a fresh install reports already_present and adds no new entries."""
        target = tmp_path / ".claude" / "settings.local.json"
        rt.project_install_hook(str(target))
        first_settings = json.loads(target.read_text())

        result = _parsed(rt.project_install_hook(str(target)))
        assert result["already_present"] is True
        assert result["installed_events"] == []
        assert result["statusLine_status"] == "already_present"
        assert result["env_status"] == "already_present"

        second_settings = json.loads(target.read_text())
        # File contents are byte-identical: no duplicate entries, no toggles.
        assert first_settings == second_settings

    def test_idempotent_render_commands_not_duplicated(self, rt, tmp_path):
        """Across two installs, each render-hook event still contains exactly one render command
        (SessionStart included — it carries a single matcher-less entry)."""
        target = tmp_path / ".claude" / "settings.local.json"
        rt.project_install_hook(str(target))
        rt.project_install_hook(str(target))

        settings = json.loads(target.read_text())
        hooks_block = settings["hooks"]
        assert _count_command(hooks_block["SessionStart"], _RENDER_HOOK_COMMAND) == 1
        for event_name in ("UserPromptSubmit", "Notification", "Stop"):
            assert _count_command(hooks_block[event_name], _RENDER_HOOK_COMMAND) == 1
        # PreToolUse carries two render entries (AskUserQuestion + Bash).
        assert _count_command(hooks_block["PreToolUse"], _RENDER_HOOK_COMMAND) == 2
        # PostToolUse carries exactly one matcher-less render entry.
        assert _count_command(hooks_block["PostToolUse"], _RENDER_HOOK_COMMAND) == 1

    # ------------------------------------------------------------------
    # (b2) Tool-scoped PreToolUse entries + the broadened PostToolUse entry.
    # ------------------------------------------------------------------

    def test_fresh_install_adds_pre_bash_and_broad_post_entries(self, rt, tmp_path):
        """A fresh install adds the PreToolUse:AskUserQuestion and PreToolUse:Bash
        render entries under matcher-qualified labels, and the matcher-less
        PostToolUse entry under the single ``PostToolUse`` label."""
        target = tmp_path / ".claude" / "settings.local.json"
        result = _parsed(rt.project_install_hook(str(target)))
        assert result["status"] == "success"
        installed = set(result["installed_events"])
        assert "PreToolUse:AskUserQuestion" in installed
        assert "PreToolUse:Bash" in installed
        assert "PostToolUse" in installed
        # The retired matcher-qualified PostToolUse labels are never reported.
        assert "PostToolUse:AskUserQuestion" not in installed
        assert "PostToolUse:Bash" not in installed

        settings = json.loads(target.read_text())
        hooks_block = settings["hooks"]
        # PreToolUse has exactly two render entries (AskUserQuestion + Bash).
        pre = hooks_block["PreToolUse"]
        assert _count_command(pre, _RENDER_HOOK_COMMAND) == 2
        pre_matchers = {
            entry.get("matcher")
            for entry in pre
            if isinstance(entry, dict)
            and any(h.get("command") == _RENDER_HOOK_COMMAND for h in entry.get("hooks", []))
        }
        assert pre_matchers == {"AskUserQuestion", "Bash"}
        # PostToolUse has exactly one matcher-less render entry.
        assert _count_command(hooks_block["PostToolUse"], _RENDER_HOOK_COMMAND) == 1

    def test_pre_bash_and_broad_post_entries_dedup_idempotent(self, rt, tmp_path):
        """Re-invoking after a fresh install reports the PreToolUse:AskUserQuestion,
        PreToolUse:Bash, and PostToolUse render entries as already-present and does
        not duplicate them."""
        target = tmp_path / ".claude" / "settings.local.json"
        rt.project_install_hook(str(target))

        result = _parsed(rt.project_install_hook(str(target)))
        already = set(result["already_present_events"])
        assert "PreToolUse:AskUserQuestion" in already
        assert "PreToolUse:Bash" in already
        assert "PostToolUse" in already
        # Nothing fresh installed on the second run.
        assert result["installed_events"] == []

        settings = json.loads(target.read_text())
        hooks_block = settings["hooks"]
        assert _count_command(hooks_block["PreToolUse"], _RENDER_HOOK_COMMAND) == 2
        assert _count_command(hooks_block["PostToolUse"], _RENDER_HOOK_COMMAND) == 1

    # ------------------------------------------------------------------
    # (b3) Upgrade path — legacy matcher-scoped PostToolUse entries are pruned.
    # ------------------------------------------------------------------

    def _seed_legacy_post_tool_use(self, target: Path) -> None:
        """Write a settings file carrying the two legacy matcher-scoped PostToolUse
        render entries (the pre-broadening wiring this install pass must retire)."""
        target.parent.mkdir(parents=True, exist_ok=True)
        legacy_entry = {
            "matcher": "AskUserQuestion",
            "hooks": [
                {"type": "command", "command": _RENDER_HOOK_COMMAND, "timeout": 5000}
            ],
        }
        legacy_bash_entry = {
            "matcher": "Bash",
            "hooks": [
                {"type": "command", "command": _RENDER_HOOK_COMMAND, "timeout": 5000}
            ],
        }
        target.write_text(
            json.dumps({"hooks": {"PostToolUse": [legacy_entry, legacy_bash_entry]}}),
            encoding="utf-8",
        )

    def test_upgrade_prunes_legacy_matcher_scoped_post_entries(self, rt, tmp_path):
        """Installing over the two legacy matcher-scoped PostToolUse render entries
        removes BOTH and leaves exactly one matcher-less render entry."""
        target = tmp_path / ".claude" / "settings.local.json"
        self._seed_legacy_post_tool_use(target)

        result = _parsed(rt.project_install_hook(str(target)))
        assert result["status"] == "success"
        assert "PostToolUse" in set(result["installed_events"])

        settings = json.loads(target.read_text())
        post = settings["hooks"]["PostToolUse"]
        assert _count_command(post, _RENDER_HOOK_COMMAND) == 1
        post_matchers = [
            entry.get("matcher", "")
            for entry in post
            if isinstance(entry, dict)
            and any(h.get("command") == _RENDER_HOOK_COMMAND for h in entry.get("hooks", []))
        ]
        assert post_matchers == [""]

    def test_prune_preserves_foreign_post_tool_use_entries(self, rt, tmp_path):
        """The prune removes ONLY matcher-scoped render entries — a foreign
        matcher-scoped PostToolUse hook belonging to someone else survives."""
        target = tmp_path / ".claude" / "settings.local.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {
                    "hooks": {
                        "PostToolUse": [
                            {
                                "matcher": "Bash",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": _RENDER_HOOK_COMMAND,
                                        "timeout": 5000,
                                    }
                                ],
                            },
                            {
                                "matcher": "Edit",
                                "hooks": [{"type": "command", "command": "echo foreign"}],
                            },
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )

        rt.project_install_hook(str(target))

        settings = json.loads(target.read_text())
        post = settings["hooks"]["PostToolUse"]
        assert "echo foreign" in _collect_commands(post)
        assert _count_command(post, _RENDER_HOOK_COMMAND) == 1

    def test_prune_leaves_pre_tool_use_and_enforcement_untouched(self, rt, tmp_path):
        """The PostToolUse prune never touches the matcher-scoped PreToolUse render
        entries nor the matcher-less enforcement entry."""
        target = tmp_path / ".claude" / "settings.local.json"
        # Wire terminal-title + enforcement, then seed the legacy PostToolUse pair.
        rt.project_install_hook(str(target))
        rt.project_install_hook(str(target), enforcement=True)
        settings = json.loads(target.read_text())
        pre_before = settings["hooks"]["PreToolUse"]
        settings["hooks"]["PostToolUse"] = [
            {
                "matcher": matcher,
                "hooks": [
                    {"type": "command", "command": _RENDER_HOOK_COMMAND, "timeout": 5000}
                ],
            }
            for matcher in ("AskUserQuestion", "Bash")
        ]
        target.write_text(json.dumps(settings), encoding="utf-8")

        rt.project_install_hook(str(target))

        after = json.loads(target.read_text())
        # PreToolUse block is byte-identical — both render matchers plus enforcement.
        assert after["hooks"]["PreToolUse"] == pre_before
        assert _count_command(after["hooks"]["PreToolUse"], _RENDER_HOOK_COMMAND) == 2
        assert _count_command(after["hooks"]["PreToolUse"], _ENFORCEMENT_HOOK_COMMAND) == 1
        # PostToolUse converged to the single matcher-less entry.
        assert _count_command(after["hooks"]["PostToolUse"], _RENDER_HOOK_COMMAND) == 1

    def test_second_install_after_prune_adds_no_further_post_entry(self, rt, tmp_path):
        """After the upgrade prune, a second install writes no further PostToolUse
        entry — the broadened wiring is idempotent."""
        target = tmp_path / ".claude" / "settings.local.json"
        self._seed_legacy_post_tool_use(target)
        rt.project_install_hook(str(target))
        first = json.loads(target.read_text())

        result = _parsed(rt.project_install_hook(str(target)))
        assert "PostToolUse" in set(result["already_present_events"])
        assert "PostToolUse" not in set(result["installed_events"])

        second = json.loads(target.read_text())
        assert first == second
        assert _count_command(second["hooks"]["PostToolUse"], _RENDER_HOOK_COMMAND) == 1

    # ------------------------------------------------------------------
    # (c) Existing foreign statusLine yields already_present_other (preserved).
    # ------------------------------------------------------------------

    def test_foreign_statusline_returns_already_present_other(self, rt, tmp_path):
        """A pre-existing statusLine whose command differs from ours is preserved and reported
        as already_present_other (no overwrite without the flag)."""
        target = tmp_path / ".claude" / "settings.local.json"
        target.parent.mkdir(parents=True)
        existing = {"statusLine": {"type": "command", "command": "echo hello-world"}}
        target.write_text(json.dumps(existing), encoding="utf-8")

        result = _parsed(rt.project_install_hook(str(target)))
        assert result["statusLine_status"] == "already_present_other"

        settings = json.loads(target.read_text())
        # Foreign value preserved untouched.
        assert settings["statusLine"]["command"] == "echo hello-world"

    # ------------------------------------------------------------------
    # (d) Existing foreign env value yields already_present_other (preserved).
    # ------------------------------------------------------------------

    def test_foreign_env_disable_returns_already_present_other(self, rt, tmp_path):
        """A pre-existing env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE with a non-'1' value is
        preserved and reported as already_present_other."""
        target = tmp_path / ".claude" / "settings.local.json"
        target.parent.mkdir(parents=True)
        existing = {"env": {"CLAUDE_CODE_DISABLE_TERMINAL_TITLE": "0"}}
        target.write_text(json.dumps(existing), encoding="utf-8")

        result = _parsed(rt.project_install_hook(str(target)))
        assert result["env_status"] == "already_present_other"

        settings = json.loads(target.read_text())
        # Foreign value preserved untouched.
        assert settings["env"]["CLAUDE_CODE_DISABLE_TERMINAL_TITLE"] == "0"

    # ------------------------------------------------------------------
    # (e) --overwrite-statusline / --overwrite-env-disable replace foreign values.
    # ------------------------------------------------------------------

    def test_overwrite_statusline_flag_replaces_foreign_command(self, rt, tmp_path):
        """overwrite_statusline=True replaces a foreign statusLine command with ours."""
        target = tmp_path / ".claude" / "settings.local.json"
        target.parent.mkdir(parents=True)
        existing = {"statusLine": {"type": "command", "command": "echo hello-world"}}
        target.write_text(json.dumps(existing), encoding="utf-8")

        result = _parsed(
            rt.project_install_hook(str(target), overwrite_statusline=True)
        )
        assert result["statusLine_status"] == "overwritten"

        settings = json.loads(target.read_text())
        assert settings["statusLine"]["command"] == _STATUSLINE_COMMAND

    def test_overwrite_env_disable_flag_replaces_foreign_value(self, rt, tmp_path):
        """overwrite_env_disable=True replaces a foreign env value with '1'."""
        target = tmp_path / ".claude" / "settings.local.json"
        target.parent.mkdir(parents=True)
        existing = {"env": {"CLAUDE_CODE_DISABLE_TERMINAL_TITLE": "0"}}
        target.write_text(json.dumps(existing), encoding="utf-8")

        result = _parsed(
            rt.project_install_hook(str(target), overwrite_env_disable=True)
        )
        assert result["env_status"] == "overwritten"

        settings = json.loads(target.read_text())
        assert settings["env"]["CLAUDE_CODE_DISABLE_TERMINAL_TITLE"] == "1"

    # ------------------------------------------------------------------
    # (f) Existing claude_hook SessionStart entry is preserved.
    # ------------------------------------------------------------------

    def test_existing_claude_hook_session_start_preserved(self, rt, tmp_path):
        """A pre-existing claude_hook capture entry is preserved when render entries are added."""
        target = tmp_path / ".claude" / "settings.local.json"
        target.parent.mkdir(parents=True)
        existing = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "",
                        "hooks": [{"type": "command", "command": _HOOK_COMMAND, "timeout": 5000}],
                    }
                ]
            }
        }
        target.write_text(json.dumps(existing), encoding="utf-8")

        result = _parsed(rt.project_install_hook(str(target)))
        assert result["status"] == "success"

        settings = json.loads(target.read_text())
        session_start = settings["hooks"]["SessionStart"]
        # Capture entry still present.
        assert _count_command(session_start, _HOOK_COMMAND) == 1
        # The matcher-less render entry was added without disturbing the capture entry.
        assert _count_command(session_start, _RENDER_HOOK_COMMAND) == 1

    def test_preserves_unrelated_existing_hooks_block(self, rt, tmp_path):
        """Existing unrelated hooks (e.g. UserPromptSubmit with a foreign command) are preserved
        alongside the inserted render entry."""
        target = tmp_path / ".claude" / "settings.local.json"
        target.parent.mkdir(parents=True)
        existing = {
            "permissions": {"allow": ["Read(**)"]},
            "hooks": {
                "UserPromptSubmit": [
                    {"matcher": "", "hooks": [{"type": "command", "command": "echo hi"}]}
                ]
            },
        }
        target.write_text(json.dumps(existing), encoding="utf-8")

        result = _parsed(rt.project_install_hook(str(target)))
        assert result["status"] == "success"

        settings = json.loads(target.read_text())
        # Unrelated permission block preserved.
        assert settings["permissions"]["allow"] == ["Read(**)"]
        # Foreign UserPromptSubmit hook preserved.
        ups_commands = _collect_commands(settings["hooks"]["UserPromptSubmit"])
        assert "echo hi" in ups_commands
        # Our render entry added alongside the foreign one.
        assert _RENDER_HOOK_COMMAND in ups_commands

    def test_shared_helper_parity_with_initial_setup(self, rt, tmp_path):
        """project_install_hook produces the same SessionStart wiring as project_initial_setup."""
        # project_initial_setup writes to .claude/settings.json.
        setup_project = tmp_path / "setup-proj"
        setup_project.mkdir()
        rt.project_initial_setup(str(setup_project), "claude")
        setup_settings = json.loads(
            (setup_project / ".claude" / "settings.json").read_text()
        )

        # project_install_hook writes to an arbitrary target file.
        install_target = tmp_path / "install" / "settings.local.json"
        rt.project_install_hook(str(install_target))
        install_settings = json.loads(install_target.read_text())

        # Both code paths produce identical hooks / statusLine / env wiring.
        assert setup_settings["hooks"] == install_settings["hooks"]
        assert setup_settings["statusLine"] == install_settings["statusLine"]
        assert setup_settings["env"] == install_settings["env"]

    # ------------------------------------------------------------------
    # (g) Target argument shape — platform identifier vs absolute path.
    # ------------------------------------------------------------------

    def test_target_claude_resolves_to_project_settings_path(self, rt, tmp_path, monkeypatch):
        """``--target claude`` MUST resolve via _claude_project_settings_path(), NOT be treated as a literal ./claude file path."""
        monkeypatch.chdir(tmp_path)
        # Ensure .claude/settings.json does NOT exist so the helper falls
        # through to .claude/settings.local.json (the preferred-on-absence path).
        result = _parsed(rt.project_install_hook("claude"))
        assert result["status"] == "success"
        # The resolved path lives under .claude/ — never a stray ./claude file.
        resolved = Path(result["settings_path"])
        assert resolved.is_absolute()
        assert resolved.parent.name == ".claude"
        assert resolved.name in ("settings.json", "settings.local.json")
        # No stray ./claude file in cwd.
        assert not (tmp_path / "claude").exists()
        # The actual settings file got the wiring.
        assert resolved.is_file()
        wiring = json.loads(resolved.read_text())
        assert "hooks" in wiring
        assert "UserPromptSubmit" in wiring["hooks"]

    def test_target_relative_path_or_bare_identifier_rejected(self, rt, tmp_path, monkeypatch):
        """Any target value that is neither 'claude' nor an absolute .json path MUST be rejected with unknown_target."""
        monkeypatch.chdir(tmp_path)
        for invalid in ("opencode", "settings.local.json", "./settings.json", "/tmp/no-extension"):
            result = _parsed(rt.project_install_hook(invalid))
            assert result["status"] == "error", f"expected error for target={invalid!r}, got {result}"
            assert result["error"] == "unknown_target", f"target={invalid!r}: {result}"
            # No stray file ever created.
            assert not (tmp_path / invalid).exists()


# =============================================================================
# 1c. project_install_hook --enforcement — orthogonal PreToolUse enforcement entry
# =============================================================================


class TestInstallEnforcementHook:
    """Tests for the orthogonal ``project install-hook --enforcement`` path.

    The enforcement install adds ONLY the matcher-less PreToolUse enforcement
    entry (keyed on ``_ENFORCEMENT_HOOK_COMMAND``); it is idempotent, orthogonal
    to the terminal-title bundle, and never disturbs existing hooks.
    """

    def test_fresh_enforcement_install_adds_entry(self, rt, tmp_path):
        """--enforcement installs the PreToolUse enforcement entry and reports installed."""
        target = tmp_path / ".claude" / "settings.local.json"
        result = _parsed(rt.project_install_hook(str(target), enforcement=True))

        assert result["status"] == "success"
        assert result["enforcement_installed"] is True
        assert result["enforcement_status"] == "installed"
        assert result["already_present"] is False

        wiring = json.loads(target.read_text())
        pre = wiring["hooks"]["PreToolUse"]
        assert _count_command(pre, _ENFORCEMENT_HOOK_COMMAND) == 1

    def test_idempotent_second_enforcement_run_already_present(self, rt, tmp_path):
        """A second --enforcement run reports already_present and adds nothing."""
        target = tmp_path / ".claude" / "settings.local.json"
        rt.project_install_hook(str(target), enforcement=True)
        result = _parsed(rt.project_install_hook(str(target), enforcement=True))

        assert result["enforcement_status"] == "already_present"
        assert result["already_present"] is True

        wiring = json.loads(target.read_text())
        # Still exactly one enforcement entry — no duplication.
        assert _count_command(wiring["hooks"]["PreToolUse"], _ENFORCEMENT_HOOK_COMMAND) == 1

    def test_already_present_does_not_rewrite_file(self, rt, tmp_path):
        """A second --enforcement run on an already-present entry must not rewrite the file.

        Validates the no-write-on-already_present fix: the file's mtime and content
        must be byte-identical after the idempotent second call.
        """
        import os
        target = tmp_path / ".claude" / "settings.local.json"
        rt.project_install_hook(str(target), enforcement=True)

        content_before = target.read_bytes()
        mtime_before = os.stat(target).st_mtime_ns

        result = _parsed(rt.project_install_hook(str(target), enforcement=True))

        assert result["enforcement_status"] == "already_present"
        # File must not have been touched (byte-identical, same mtime).
        assert target.read_bytes() == content_before
        assert os.stat(target).st_mtime_ns == mtime_before

    def test_plain_install_does_not_add_enforcement_entry(self, rt, tmp_path):
        """A plain install-hook (no --enforcement) never installs the enforcement entry."""
        target = tmp_path / ".claude" / "settings.local.json"
        rt.project_install_hook(str(target))

        wiring = json.loads(target.read_text())
        pre = wiring["hooks"].get("PreToolUse", [])
        assert _count_command(pre, _ENFORCEMENT_HOOK_COMMAND) == 0

    def test_enforcement_install_does_not_add_terminal_title_wiring(self, rt, tmp_path):
        """--enforcement installs ONLY the enforcement entry — no render/statusLine/env wiring."""
        target = tmp_path / ".claude" / "settings.local.json"
        rt.project_install_hook(str(target), enforcement=True)

        wiring = json.loads(target.read_text())
        hooks = wiring.get("hooks", {})
        # No render entries anywhere, no statusLine, no env disable.
        for block in hooks.values():
            assert _count_command(block, _RENDER_HOOK_COMMAND) == 0
        assert "statusLine" not in wiring
        assert "CLAUDE_CODE_DISABLE_TERMINAL_TITLE" not in wiring.get("env", {})
        # SessionStart was never created (no capture/render entries added).
        assert "SessionStart" not in hooks

    def test_enforcement_install_preserves_existing_terminal_title_hooks(self, rt, tmp_path):
        """Installing enforcement onto a terminal-title-wired file preserves all render entries."""
        target = tmp_path / ".claude" / "settings.local.json"
        # First fully wire terminal-title.
        rt.project_install_hook(str(target))
        before = json.loads(target.read_text())
        # Then add enforcement orthogonally.
        rt.project_install_hook(str(target), enforcement=True)
        after = json.loads(target.read_text())

        hooks = after["hooks"]
        # Existing render entries intact.
        assert _count_command(hooks["SessionStart"], _RENDER_HOOK_COMMAND) == 1
        assert _count_command(hooks["PreToolUse"], _RENDER_HOOK_COMMAND) == 2
        assert _count_command(hooks["PostToolUse"], _RENDER_HOOK_COMMAND) == 1
        # statusLine + env preserved verbatim.
        assert after["statusLine"] == before["statusLine"]
        assert after["env"] == before["env"]
        # Enforcement entry added alongside the render entries.
        assert _count_command(hooks["PreToolUse"], _ENFORCEMENT_HOOK_COMMAND) == 1

    def test_terminal_title_install_preserves_existing_enforcement_entry(self, rt, tmp_path):
        """Installing terminal-title onto an enforcement-wired file preserves the enforcement entry."""
        target = tmp_path / ".claude" / "settings.local.json"
        # First install enforcement only.
        rt.project_install_hook(str(target), enforcement=True)
        # Then install the terminal-title bundle.
        rt.project_install_hook(str(target))

        wiring = json.loads(target.read_text())
        pre = wiring["hooks"]["PreToolUse"]
        # Enforcement entry survives the terminal-title install.
        assert _count_command(pre, _ENFORCEMENT_HOOK_COMMAND) == 1
        # And the render entries were added.
        assert _count_command(pre, _RENDER_HOOK_COMMAND) == 2

    def test_target_claude_enforcement_pins_settings_local_even_when_settings_json_exists(
        self, rt, tmp_path, monkeypatch
    ):
        """``--target claude --enforcement`` pins settings.local.json even when a
        shared settings.json already exists.

        Regression: the enforcement install used to ride the prefer-settings.json
        resolver, scattering the operator-local opt-in into the shared
        settings.json where the display health-check could not see it.
        """
        monkeypatch.chdir(tmp_path)
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        # A pre-existing shared settings.json — the prefer-settings.json resolver
        # would otherwise target this file.
        settings_json = claude_dir / "settings.json"
        settings_json.write_text(json.dumps({"permissions": {"allow": []}}))
        shared_before = settings_json.read_text()

        result = _parsed(rt.project_install_hook("claude", enforcement=True))

        assert result["status"] == "success"
        assert result["enforcement_installed"] is True
        # The entry landed in settings.local.json, NOT the shared settings.json.
        assert Path(result["settings_path"]).name == "settings.local.json"
        local = json.loads((claude_dir / "settings.local.json").read_text())
        assert _count_command(local["hooks"]["PreToolUse"], _ENFORCEMENT_HOOK_COMMAND) == 1
        # The shared settings.json was NOT touched — byte-identical, not merely
        # "no hooks block" (an in-place rewrite without hooks would be a bug too).
        assert settings_json.read_text() == shared_before
        shared = json.loads(shared_before)
        assert "hooks" not in shared


class TestDisplayEnforcementLabel:
    """Tests for the dedicated ``PreToolUse:enforcement`` display present/MISSING label."""

    def test_display_reports_enforcement_missing_before_install(self, rt, tmp_path, monkeypatch):
        """The display check reports PreToolUse:enforcement MISSING before the install."""
        monkeypatch.chdir(tmp_path)
        result = _parsed(rt.health_check("display"))
        display_result = next(r for r in result["results"] if r["check"] == "display")
        assert "PreToolUse:enforcement: MISSING" in display_result["detail"]

    def test_display_reports_enforcement_present_after_install(self, rt, tmp_path, monkeypatch):
        """The display check reports PreToolUse:enforcement present after the enforcement install."""
        target = tmp_path / ".claude" / "settings.local.json"
        rt.project_install_hook(str(target), enforcement=True)
        monkeypatch.chdir(tmp_path)

        result = _parsed(rt.health_check("display"))
        display_result = next(r for r in result["results"] if r["check"] == "display")
        assert "PreToolUse:enforcement: present" in display_result["detail"]

    def test_enforcement_only_install_keeps_display_unhealthy_for_terminal_title(
        self, rt, tmp_path, monkeypatch
    ):
        """An enforcement-only install does NOT make the terminal-title display healthy.

        The enforcement entry is orthogonal: installing it alone leaves every
        terminal-title render label MISSING, so the display stays unhealthy
        while the enforcement label itself reports present.
        """
        target = tmp_path / ".claude" / "settings.local.json"
        rt.project_install_hook(str(target), enforcement=True)
        monkeypatch.chdir(tmp_path)

        result = _parsed(rt.health_check("display"))
        display_result = next(r for r in result["results"] if r["check"] == "display")
        assert display_result["healthy"] is False
        detail = display_result["detail"]
        assert "PreToolUse:enforcement: present" in detail
        assert "SessionStart:matcher-less: MISSING" in detail

    def test_display_reports_enforcement_present_when_entry_in_settings_json(
        self, rt, tmp_path, monkeypatch
    ):
        """The display check detects the enforcement entry in settings.json too.

        Regression: the display check used to read ONLY settings.local.json, so an
        enforcement entry living in the shared settings.json (where the
        prefer-settings.json resolver could place it) was reported MISSING even
        though it was registered. The check now reads both files, like the
        sibling ``hook`` check.
        """
        target = tmp_path / ".claude" / "settings.json"
        rt.project_install_hook(str(target), enforcement=True)
        monkeypatch.chdir(tmp_path)

        result = _parsed(rt.health_check("display"))
        display_result = next(r for r in result["results"] if r["check"] == "display")
        assert "PreToolUse:enforcement: present" in display_result["detail"]


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


# =============================================================================
# 2. session_capture
# =============================================================================


class TestSessionCapture:
    """Tests for ClaudeRuntime.session_capture."""

    def test_missing_env_var_returns_error(self, rt, monkeypatch):
        """When $CLAUDE_CODE_SESSION_ID is unset, session_capture returns error."""
        monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
        result = _parsed(rt.session_capture("my-plan"))
        assert result["status"] == "error"
        assert result["error"] == "hook_not_configured"

    def test_stores_session_id_when_env_var_set(self, rt, monkeypatch):
        """When env var is set, session_capture stores and returns success."""
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "test-session-abc")
        with patch("claude_runtime._manage_status_store_session", return_value=True):
            result = _parsed(rt.session_capture("my-plan"))
        assert result["status"] == "success"
        assert result["session_id"] == "test-session-abc"
        assert result["plan_id"] == "my-plan"

    def test_stored_flag_reflects_subprocess_outcome(self, rt, monkeypatch):
        """stored field is True when subprocess succeeds, False when it fails."""
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-123")
        with patch("claude_runtime._manage_status_store_session", return_value=False):
            result = _parsed(rt.session_capture("plan-x"))
        assert result["stored"] is False


# =============================================================================
# 3b. composer-import wiring — claude_runtime delegates to manage-terminal-title
# =============================================================================


class TestComposerImportWiring:
    """Assert claude_runtime imports the manage-terminal-title composer and no
    longer owns the icon palette / body format (moved to D12).

    The body-format, glyph-prepend, and ✅ terminal-override assertions live in
    D12's ``test_manage_terminal_title.py`` (pure composer). These tests assert
    only the resolve+read+emit wiring: that ``claude_runtime`` imports
    ``compose`` and that the removed helpers are gone.
    """

    def test_claude_runtime_imports_compose(self):
        """claude_runtime exposes the imported composer (consumed, not reimplemented)."""
        import claude_runtime as _cr

        assert _cr.compose is not None
        # The composer is the manage-terminal-title module's function.
        assert _cr.compose.__module__ == "manage_terminal_title"

    def test_icon_palette_removed_from_claude_runtime(self):
        """The icon palette + _resolve_icon moved to manage-terminal-title (D12)."""
        import claude_runtime as _cr

        assert not hasattr(_cr, "_resolve_icon")
        assert not hasattr(_cr, "_ICON_ACTIVE")
        assert not hasattr(_cr, "_ICON_WAITING")
        assert not hasattr(_cr, "_ICON_DONE")

    def test_title_body_resolver_replaced_by_status_json(self):
        """The title-body.txt archived resolver is replaced by the status.json one."""
        import claude_runtime as _cr

        assert not hasattr(_cr, "_resolve_archived_title_body")
        assert hasattr(_cr, "_resolve_archived_status_json")
        assert hasattr(_cr, "_read_title_state")


# =============================================================================
# 3c3. _command_is_build detection predicate (D5)
# =============================================================================


class TestCommandIsBuild:
    """Unit tests for the ``_command_is_build`` detection predicate.

    Detection anchors on the four build-wrapper executor notation substrings in
    ``_BUILD_WRAPPER_NOTATIONS``. A match means the Bash call routes a
    long-running build / orchestration command through the executor; an empty /
    ``None`` command, a bare canonical verb word, or any command naming none of
    the wrapper notations returns False.
    """

    @pytest.mark.parametrize("notation", list(_BUILD_WRAPPER_NOTATIONS))
    def test_each_wrapper_notation_matches(self, notation):
        """Every build-wrapper notation, embedded in an executor invocation, matches."""
        command = (
            f"python3 .plan/execute-script.py {notation}:run_build run "
            '--command-args "verify plan-marshall"'
        )
        assert _command_is_build(command) is True

    @pytest.mark.parametrize("notation", list(_BUILD_WRAPPER_NOTATIONS))
    def test_notation_substring_anywhere_matches(self, notation):
        """The notation substring matches anywhere in the command string."""
        assert _command_is_build(f"some prefix {notation} trailing args") is True

    @pytest.mark.parametrize("command", [None, ""])
    def test_empty_or_none_command_is_false(self, command):
        """An empty or None command is never a build command."""
        assert _command_is_build(command) is False

    @pytest.mark.parametrize(
        "command",
        [
            "verify",
            "coverage",
            "quality-gate",
            "module-tests",
            "echo verify",
            "ls -la",
            "git commit -m 'verify the build'",
            "python3 some_other_script.py run",
            "cat plan-marshall/README.md",
        ],
    )
    def test_non_build_commands_are_false(self, command):
        """A bare canonical verb word, or any non-wrapper command, never matches.

        The canonical ``verify`` / ``coverage`` / ``quality-gate`` / ``module-tests``
        verbs are only build invocations when passed AS ``--command-args`` to a
        wrapper notation — the bare verb word alone (or a verb appearing in an
        unrelated command like ``git commit -m 'verify ...'``) must NOT match.
        """
        assert _command_is_build(command) is False

    def test_canonical_verb_via_wrapper_matches(self):
        """A canonical verb passed as --command-args to a wrapper matches via the notation."""
        command = (
            "python3 .plan/execute-script.py "
            "plan-marshall:build-pyproject:pyproject_build run "
            '--command-args "quality-gate plan-marshall"'
        )
        assert _command_is_build(command) is True


# =============================================================================
# 3c4. session_render_title build-busy hook assist (D5)
# =============================================================================


class TestSessionRenderTitleBuildBusy:
    """Tests for the D5 build-busy hook assist in ``session_render_title``.

    When a ``PreToolUse:Bash`` hook event carries a build-wrapper command (one of
    ``_BUILD_WRAPPER_NOTATIONS`` as a substring of ``tool_input.command``), the
    renderer forces the persistent ``build-busy`` title-token for this render: the
    composed title paints the 🔨 icon-slot override (beating the ⚙ momentary-busy
    icon the bare ``PreToolUse:Bash`` event would otherwise resolve), AND the
    token is persisted best-effort via ``_manage_status_set_title_token`` so it
    survives to subsequent renders and the agent's D3 clear. A non-build Bash
    command, a missing ``tool_input``, a non-``PreToolUse`` event, or statusLine
    mode is a silent no-op — the existing ⚙ busy mapping remains.
    """

    _ICON_BUILD = "\U0001f528"  # 🔨 build-busy icon-slot override
    _ICON_BUSY = "⚙"  # momentary-busy icon (bare PreToolUse:Bash)
    _ICON_ACTIVE = "➤"  # active icon (PostToolUse / statusLine)

    @staticmethod
    def _arrange(
        tmp_path,
        monkeypatch,
        *,
        session_id="sess-build",
        plan_id="build-plan",
        current_phase="5-execute",
        short_description="build-task",
    ):
        _write_status_json(
            tmp_path,
            session_id=session_id,
            plan_id=plan_id,
            current_phase=current_phase,
            short_description=short_description,
        )
        _redirect_render_env(tmp_path, monkeypatch, session_id)
        return f"pm:{current_phase}:{short_description}"

    @staticmethod
    def _bash_payload(command):
        """Build a PreToolUse:Bash hook payload carrying *command*."""
        return {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
        }

    @pytest.mark.parametrize("notation", list(_BUILD_WRAPPER_NOTATIONS))
    def test_build_command_renders_build_busy_icon(
        self, notation, rt, tmp_path, monkeypatch, capsys
    ):
        """Each build-wrapper notation flips the OSC envelope to the 🔨 build-busy override."""
        from io import StringIO

        body = self._arrange(tmp_path, monkeypatch)
        command = (
            f"python3 .plan/execute-script.py {notation}:run_build run "
            '--command-args "verify plan-marshall"'
        )
        monkeypatch.setattr("sys.stdin", StringIO(json.dumps(self._bash_payload(command))))

        capsys.readouterr()
        with patch("claude_runtime._manage_status_set_title_token", return_value=True):
            returned = rt.session_render_title(statusline=False)
        captured = capsys.readouterr().out

        assert returned == ""
        envelope = json.loads(captured)
        assert envelope["terminalSequence"] == f"\x1b]0;{self._ICON_BUILD} {body}\x07"

    def test_build_command_persists_build_busy_token(
        self, rt, tmp_path, monkeypatch, capsys
    ):
        """A build command persists the token via _manage_status_set_title_token(plan_id, 'build-busy')."""
        from io import StringIO

        self._arrange(tmp_path, monkeypatch, plan_id="persist-plan")
        command = (
            "python3 .plan/execute-script.py "
            "plan-marshall:build-pyproject:pyproject_build run "
            '--command-args "verify plan-marshall"'
        )
        monkeypatch.setattr("sys.stdin", StringIO(json.dumps(self._bash_payload(command))))

        capsys.readouterr()
        with patch(
            "claude_runtime._manage_status_set_title_token", return_value=True
        ) as mock_set:
            rt.session_render_title(statusline=False)

        mock_set.assert_called_once_with("persist-plan", "build-busy")

    @pytest.mark.parametrize(
        "command",
        [
            "echo verify",
            "ls -la",
            "git status",
            "git commit -m 'verify the build'",
            "python3 some_other_script.py run",
        ],
    )
    def test_non_build_command_keeps_busy_icon_and_does_not_persist(
        self, command, rt, tmp_path, monkeypatch, capsys
    ):
        """A non-build Bash command keeps the existing ⚙ busy icon and never persists build-busy."""
        from io import StringIO

        body = self._arrange(tmp_path, monkeypatch)
        monkeypatch.setattr("sys.stdin", StringIO(json.dumps(self._bash_payload(command))))

        capsys.readouterr()
        with patch(
            "claude_runtime._manage_status_set_title_token", return_value=True
        ) as mock_set:
            returned = rt.session_render_title(statusline=False)
        captured = capsys.readouterr().out

        assert returned == ""
        envelope = json.loads(captured)
        assert envelope["terminalSequence"] == f"\x1b]0;{self._ICON_BUSY} {body}\x07"
        mock_set.assert_not_called()

    def test_bash_without_tool_input_keeps_busy_icon(
        self, rt, tmp_path, monkeypatch, capsys
    ):
        """A PreToolUse:Bash event with no tool_input is a silent no-op → ⚙ busy, no persist."""
        from io import StringIO

        body = self._arrange(tmp_path, monkeypatch)
        monkeypatch.setattr(
            "sys.stdin",
            StringIO(json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash"})),
        )

        capsys.readouterr()
        with patch(
            "claude_runtime._manage_status_set_title_token", return_value=True
        ) as mock_set:
            rt.session_render_title(statusline=False)
        captured = capsys.readouterr().out

        envelope = json.loads(captured)
        assert envelope["terminalSequence"] == f"\x1b]0;{self._ICON_BUSY} {body}\x07"
        mock_set.assert_not_called()

    def test_build_command_on_post_tool_use_does_not_trigger_build_busy(
        self, rt, tmp_path, monkeypatch, capsys
    ):
        """A build command on PostToolUse:Bash does NOT trigger build-busy (only PreToolUse:Bash does)."""
        from io import StringIO

        body = self._arrange(tmp_path, monkeypatch)
        command = (
            "python3 .plan/execute-script.py "
            "plan-marshall:build-maven:maven run --targets verify"
        )
        monkeypatch.setattr(
            "sys.stdin",
            StringIO(
                json.dumps(
                    {
                        "hook_event_name": "PostToolUse",
                        "tool_name": "Bash",
                        "tool_input": {"command": command},
                    }
                )
            ),
        )

        capsys.readouterr()
        with patch(
            "claude_runtime._manage_status_set_title_token", return_value=True
        ) as mock_set:
            rt.session_render_title(statusline=False)
        captured = capsys.readouterr().out

        envelope = json.loads(captured)
        # PostToolUse:Bash → ➤ active (existing mapping), never build-busy.
        assert envelope["terminalSequence"] == f"\x1b]0;{self._ICON_ACTIVE} {body}\x07"
        mock_set.assert_not_called()

    def test_statusline_mode_never_triggers_build_busy(
        self, rt, tmp_path, monkeypatch, capsys
    ):
        """statusLine mode never reads stdin, so a build command never flips to 🔨 — active icon stays."""
        from io import StringIO

        body = self._arrange(tmp_path, monkeypatch)
        command = (
            "python3 .plan/execute-script.py "
            "plan-marshall:build-gradle:gradle run --targets verify"
        )
        monkeypatch.setattr("sys.stdin", StringIO(json.dumps(self._bash_payload(command))))

        capsys.readouterr()
        with patch(
            "claude_runtime._manage_status_set_title_token", return_value=True
        ) as mock_set:
            returned = rt.session_render_title(statusline=True)
        captured = capsys.readouterr().out

        assert returned == ""
        assert captured == f"{self._ICON_ACTIVE} {body}"
        mock_set.assert_not_called()


# =============================================================================
# 3d. session_render_title archived-path fallback + ✓ Completed-body pairing (D3)
# =============================================================================


class TestSessionRenderTitleArchivedFallback:
    """Tests for the archived-status.json fallback branch of session_render_title.

    Once a plan is archived, the live ``.plan/local/plans/{plan_id}/`` directory
    is gone — ``cmd_archive`` moved it (status.json included) to
    ``.plan/local/archived-plans/{YYYY-MM-DD}-{plan_id}/``. status.json is the
    SINGLE source of persisted title state, so the reader falls back to the
    archived ``status.json`` when the live one is absent. A terminal phase
    (``complete``/``archived``) composes the ✅ Completed title via the
    manage-terminal-title composer (the ✅ override itself is asserted in D12's
    pure-composer tests); these tests assert the resolve+read+emit wiring.
    """

    @staticmethod
    def _arrange(
        tmp_path,
        monkeypatch,
        *,
        session_id="sess-archived",
        plan_id="archived-plan",
        archived_phase="complete",
        archived_short="consolidate-terminal-docs",
        date_prefix="2026-05-29",
        write_live=False,
        live_phase="5-execute",
        live_short="active-body",
    ):
        """Materialize an archived plan (and optionally a live plan) on disk.

        Always writes the session-cache pointer and the archived ``status.json``.
        When ``write_live`` is True, also writes the live
        ``.plan/local/plans/{plan_id}/status.json`` so the live-path-wins
        precedence can be exercised.
        """
        import claude_runtime as _cr

        cache_dir = tmp_path / "sessions" / session_id
        cache_dir.mkdir(parents=True)
        (cache_dir / "active-plan").write_text(plan_id, encoding="utf-8")

        archived_dir = (
            tmp_path / ".plan" / "local" / "archived-plans" / f"{date_prefix}-{plan_id}"
        )
        archived_dir.mkdir(parents=True)
        archived_status: dict[str, Any] = {}
        if archived_phase:
            archived_status["current_phase"] = archived_phase
        if archived_short is not None:
            archived_status["short_description"] = archived_short
        (archived_dir / "status.json").write_text(json.dumps(archived_status), encoding="utf-8")

        if write_live:
            live_dir = tmp_path / ".plan" / "local" / "plans" / plan_id
            live_dir.mkdir(parents=True)
            (live_dir / "status.json").write_text(
                json.dumps(
                    {"current_phase": live_phase, "short_description": live_short}
                ),
                encoding="utf-8",
            )

        monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")
        monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", session_id)
        monkeypatch.chdir(tmp_path)

    def test_falls_back_to_archived_status_when_live_absent(
        self, rt, tmp_path, monkeypatch, capsys
    ):
        """Live status.json absent → reader globs the archived status.json and composes the Completed title.

        A ``complete`` phase forces the ✅ terminal icon inside the composer
        regardless of the (absent) hook event.
        """
        self._arrange(tmp_path, monkeypatch, archived_short="consolidate-terminal-docs")

        capsys.readouterr()
        returned = rt.session_render_title(statusline=False)
        captured = capsys.readouterr().out

        assert returned == ""
        envelope = json.loads(captured)
        # Terminal phase → ✅ override + Completed body, both owned by the composer.
        assert envelope["terminalSequence"] == "\x1b]0;✅ pm:Completed:consolidate-terminal-docs\x07"

    def test_terminal_icon_overrides_stop_event_from_archived_status(
        self, rt, tmp_path, monkeypatch, capsys
    ):
        """Even a Stop hook payload over an archived terminal status emits the ✅ override.

        The composer's terminal-phase ✅ override wins over the ✓ Stop-event icon
        for a finished plan.
        """
        from io import StringIO

        self._arrange(tmp_path, monkeypatch, archived_short="consolidate-terminal-docs")
        monkeypatch.setattr("sys.stdin", StringIO(json.dumps({"hook_event_name": "Stop"})))

        capsys.readouterr()
        returned = rt.session_render_title(statusline=False)
        captured = capsys.readouterr().out

        assert returned == ""
        envelope = json.loads(captured)
        assert envelope["terminalSequence"] == "\x1b]0;✅ pm:Completed:consolidate-terminal-docs\x07"

    def test_statusline_mode_emits_completed_title_from_archived_status(
        self, rt, tmp_path, monkeypatch, capsys
    ):
        """statusLine mode reads the archived terminal status and emits the composed ✅ Completed title."""
        self._arrange(tmp_path, monkeypatch, archived_short="consolidate-terminal-docs")

        capsys.readouterr()
        returned = rt.session_render_title(statusline=True)
        captured = capsys.readouterr().out

        assert returned == ""
        assert captured == "✅ pm:Completed:consolidate-terminal-docs"

    def test_live_status_wins_over_archived_when_both_present(
        self, rt, tmp_path, monkeypatch, capsys
    ):
        """When both the live and archived status.json exist, the LIVE state is composed.

        The fallback is strictly a live-status-absent branch — a live status.json
        must take precedence so an in-flight re-run of a previously archived
        plan_id never surfaces the stale Completed title.
        """
        self._arrange(
            tmp_path,
            monkeypatch,
            archived_phase="complete",
            archived_short="stale-completed-body",
            write_live=True,
            live_phase="5-execute",
            live_short="active-body",
        )

        capsys.readouterr()
        returned = rt.session_render_title(statusline=False)
        captured = capsys.readouterr().out

        assert returned == ""
        envelope = json.loads(captured)
        assert "pm:5-execute:active-body" in envelope["terminalSequence"]
        assert "Completed" not in captured

    def test_empty_archived_status_writes_nothing(
        self, rt, tmp_path, monkeypatch, capsys
    ):
        """An archived status.json with no current_phase → composer returns None → no-op."""
        self._arrange(tmp_path, monkeypatch, archived_phase="", archived_short=None)

        capsys.readouterr()
        returned = rt.session_render_title(statusline=False)
        captured = capsys.readouterr().out

        assert returned == ""
        assert captured == ""

    def test_no_live_and_no_archived_writes_nothing(
        self, rt, tmp_path, monkeypatch, capsys
    ):
        """Neither live nor archived status.json present → no-op (empty stdout, empty return)."""
        import claude_runtime as _cr

        session_id = "sess-no-status"
        plan_id = "ghost-plan"
        cache_dir = tmp_path / "sessions" / session_id
        cache_dir.mkdir(parents=True)
        (cache_dir / "active-plan").write_text(plan_id, encoding="utf-8")
        # archived-plans/ exists but contains no matching plan dir.
        (tmp_path / ".plan" / "local" / "archived-plans").mkdir(parents=True)

        monkeypatch.setattr(session_binding, "_SESSION_CACHE_BASE", tmp_path / "sessions")
        monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", session_id)
        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        returned = rt.session_render_title(statusline=False)
        captured = capsys.readouterr().out

        assert returned == ""
        assert captured == ""


class TestResolveArchivedStatusJson:
    """Tests for the module-level _resolve_archived_status_json helper.

    Resolves ``.plan/local/archived-plans/{YYYY-MM-DD}-{plan_id}/status.json``
    by globbing ``*-{plan_id}/status.json``. The matched parent name must end
    with the exact ``-{plan_id}`` suffix to defeat a prefix collision between
    similarly named plans.
    """

    def test_resolves_archived_status_for_dated_dir(self, tmp_path, monkeypatch):
        """Returns the archived status.json path under {date}-{plan_id}/."""
        import claude_runtime as _cr

        plan_id = "my-plan"
        archived_dir = tmp_path / ".plan" / "local" / "archived-plans" / f"2026-05-29-{plan_id}"
        archived_dir.mkdir(parents=True)
        status_path = archived_dir / "status.json"
        status_path.write_text(json.dumps({"current_phase": "complete"}), encoding="utf-8")

        monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.chdir(tmp_path)

        resolved = _cr._resolve_archived_status_json(plan_id)
        assert resolved is not None
        assert resolved.resolve() == status_path.resolve()

    def test_returns_none_when_archived_base_absent(self, tmp_path, monkeypatch):
        """No archived-plans/ directory at all → None (not an error)."""
        import claude_runtime as _cr

        monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.chdir(tmp_path)

        assert _cr._resolve_archived_status_json("anything") is None

    def test_does_not_match_unrelated_plan_dir(self, tmp_path, monkeypatch):
        """The ``*-{plan_id}`` glob must not resolve a directory for a different
        plan whose name does not end in the exact ``-{plan_id}`` suffix.

        A request for plan_id 'plan' must NOT resolve an archive named
        ``{date}-superplan`` (which ends in ``superplan``, not ``-plan``)."""
        import claude_runtime as _cr

        other_dir = tmp_path / ".plan" / "local" / "archived-plans" / "2026-05-29-superplan"
        other_dir.mkdir(parents=True)
        (other_dir / "status.json").write_text(json.dumps({"current_phase": "complete"}), encoding="utf-8")

        monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.chdir(tmp_path)

        # Only the unrelated -superplan dir exists → no resolution for 'plan'.
        assert _cr._resolve_archived_status_json("plan") is None

    def test_resolves_exact_plan_when_sibling_prefixed_dir_present(self, tmp_path, monkeypatch):
        """With both a ``{date}-superplan`` archive and a ``{date}-plan`` archive
        present, a request for plan_id 'plan' resolves ONLY the exact ``-plan``
        directory — the sibling whose suffix is ``superplan`` is ignored."""
        import claude_runtime as _cr

        other_dir = tmp_path / ".plan" / "local" / "archived-plans" / "2026-05-29-superplan"
        other_dir.mkdir(parents=True)
        (other_dir / "status.json").write_text(json.dumps({"current_phase": "complete"}), encoding="utf-8")

        exact_dir = tmp_path / ".plan" / "local" / "archived-plans" / "2026-05-30-plan"
        exact_dir.mkdir(parents=True)
        exact_status = exact_dir / "status.json"
        exact_status.write_text(json.dumps({"current_phase": "complete"}), encoding="utf-8")

        monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.chdir(tmp_path)

        resolved = _cr._resolve_archived_status_json("plan")
        assert resolved is not None
        assert resolved.resolve() == exact_status.resolve()


# =============================================================================
# 3e. _read_title_state — status.json reader (live + archived fallback)
# =============================================================================


class TestReadTitleState:
    """Tests for the module-level _read_title_state helper.

    Reads the title-state fields (current_phase, short_description, title_token)
    from the live ``status.json`` first, falling back to the archived one.
    """

    def test_reads_live_status_fields(self, tmp_path, monkeypatch):
        """Returns the {current_phase, short_description, title_token} dict from the live status.json."""
        import claude_runtime as _cr

        plan_id = "live-plan"
        live_dir = tmp_path / ".plan" / "local" / "plans" / plan_id
        live_dir.mkdir(parents=True)
        (live_dir / "status.json").write_text(
            json.dumps(
                {
                    "current_phase": "5-execute",
                    "short_description": "do-work",
                    "title_token": "lock-owned",
                }
            ),
            encoding="utf-8",
        )

        monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.chdir(tmp_path)

        state = _cr._read_title_state(plan_id)
        assert state == {
            "current_phase": "5-execute",
            "short_description": "do-work",
            "title_token": "lock-owned",
        }

    def test_falls_back_to_archived_status(self, tmp_path, monkeypatch):
        """Live status.json absent → reads the archived status.json."""
        import claude_runtime as _cr

        plan_id = "arch-plan"
        archived_dir = tmp_path / ".plan" / "local" / "archived-plans" / f"2026-05-29-{plan_id}"
        archived_dir.mkdir(parents=True)
        (archived_dir / "status.json").write_text(
            json.dumps({"current_phase": "complete", "short_description": "done-task"}),
            encoding="utf-8",
        )

        monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.chdir(tmp_path)

        state = _cr._read_title_state(plan_id)
        assert state == {"current_phase": "complete", "short_description": "done-task"}

    def test_returns_none_when_no_status_anywhere(self, tmp_path, monkeypatch):
        """Neither live nor archived status.json present → None."""
        import claude_runtime as _cr

        monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.chdir(tmp_path)

        assert _cr._read_title_state("ghost") is None

    def test_omits_absent_optional_fields(self, tmp_path, monkeypatch):
        """A status.json with only current_phase yields a dict without the optional keys."""
        import claude_runtime as _cr

        plan_id = "minimal-plan"
        live_dir = tmp_path / ".plan" / "local" / "plans" / plan_id
        live_dir.mkdir(parents=True)
        (live_dir / "status.json").write_text(
            json.dumps({"current_phase": "1-init"}), encoding="utf-8"
        )

        monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.chdir(tmp_path)

        state = _cr._read_title_state(plan_id)
        assert state == {"current_phase": "1-init"}


# =============================================================================
# 3f. session_push_title_token — live /dev/tty push (push-mode)
# =============================================================================


class TestSessionPushTitleToken:
    """Tests for ClaudeRuntime.session_push_title_token.

    Reads the plan's status.json, composes via the manage-terminal-title
    composer with the push icon override, and writes the OSC escape to
    ``/dev/tty``. Best-effort: a silent no-op when state is absent or
    ``/dev/tty`` is not openable; never raises.
    """

    @staticmethod
    def _write_live_status(tmp_path, monkeypatch, plan_id, *, current_phase="5-execute",
                           short_description="push-task", title_token=None):
        import claude_runtime as _cr

        live_dir = tmp_path / ".plan" / "local" / "plans" / plan_id
        live_dir.mkdir(parents=True)
        status: dict[str, Any] = {"current_phase": current_phase}
        if short_description is not None:
            status["short_description"] = short_description
        if title_token is not None:
            status["title_token"] = title_token
        (live_dir / "status.json").write_text(json.dumps(status), encoding="utf-8")

        monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.chdir(tmp_path)

    def test_push_with_tty_writes_osc_escape(self, rt, tmp_path, monkeypatch):
        """When /dev/tty is openable, the composed OSC escape is written and pushed: true is reported."""
        plan_id = "push-plan"
        self._write_live_status(
            tmp_path, monkeypatch, plan_id,
            current_phase="5-execute", short_description="push-task",
            title_token="lock-owned",
        )

        written: list[str] = []

        class _FakeTTY:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *exc):
                return False

            def write(self_inner, text):
                written.append(text)

            def flush(self_inner):
                pass

        real_open = open

        def _fake_open(path, *args, **kwargs):
            if path == "/dev/tty":
                return _FakeTTY()
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", _fake_open)

        result = _parsed(rt.session_push_title_token(plan_id, "⏳"))
        assert result["status"] == "success"
        assert result["pushed"] is True
        # The push icon override + lock-owned glyph (🔒) + body, composed by D12.
        assert written == ["\x1b]0;⏳ \U0001f512 pm:5-execute:push-task\x07"]

    def test_push_without_tty_is_silent_noop(self, rt, tmp_path, monkeypatch):
        """When /dev/tty cannot be opened, the push is a silent no-op (pushed: false) and never raises."""
        plan_id = "push-no-tty"
        self._write_live_status(tmp_path, monkeypatch, plan_id)

        real_open = open

        def _fake_open(path, *args, **kwargs):
            if path == "/dev/tty":
                raise OSError("no controlling terminal")
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", _fake_open)

        result = _parsed(rt.session_push_title_token(plan_id, "⏳"))
        assert result["status"] == "success"
        assert result["pushed"] is False

    def test_push_with_no_status_state_is_noop(self, rt, tmp_path, monkeypatch):
        """No status.json for the plan → pushed: false, /dev/tty never touched."""
        import claude_runtime as _cr

        monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.chdir(tmp_path)

        opened: list[str] = []
        real_open = open

        def _fake_open(path, *args, **kwargs):
            opened.append(str(path))
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", _fake_open)

        result = _parsed(rt.session_push_title_token("ghost-plan", "⏳"))
        assert result["status"] == "success"
        assert result["pushed"] is False
        assert "/dev/tty" not in opened

    def test_push_with_unrenderable_state_is_noop(self, rt, tmp_path, monkeypatch):
        """status.json present but with no current_phase → composer returns None →
        pushed: false, /dev/tty never touched.

        This exercises the second falsy-guard branch in session_push_title_token:
        _read_title_state returns a non-None dict (it carries short_description),
        but compose() returns None because current_phase is absent. The push must
        be a silent no-op without ever opening /dev/tty (distinct from the
        state-is-None branch, where _read_title_state itself returns None).
        """
        import claude_runtime as _cr

        plan_id = "unrenderable-plan"
        # status.json with short_description but NO current_phase. _read_title_state
        # returns {"short_description": ...} (non-None); compose() returns None.
        live_dir = tmp_path / ".plan" / "local" / "plans" / plan_id
        live_dir.mkdir(parents=True)
        (live_dir / "status.json").write_text(
            json.dumps({"short_description": "orphan-no-phase"}), encoding="utf-8"
        )

        monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.chdir(tmp_path)

        opened: list[str] = []
        real_open = open

        def _fake_open(path, *args, **kwargs):
            opened.append(str(path))
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", _fake_open)

        result = _parsed(rt.session_push_title_token(plan_id, "⏳"))
        assert result["status"] == "success"
        assert result["pushed"] is False
        assert "/dev/tty" not in opened

    def test_push_osc_format_correctness(self, rt, tmp_path, monkeypatch):
        """The pushed bytes are exactly ``\\x1b]0;{composed}\\x07`` (no extra framing)."""
        plan_id = "push-fmt"
        self._write_live_status(
            tmp_path, monkeypatch, plan_id,
            current_phase="3-outline", short_description="fmt", title_token=None,
        )

        written: list[str] = []

        class _FakeTTY:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *exc):
                return False

            def write(self_inner, text):
                written.append(text)

            def flush(self_inner):
                pass

        real_open = open

        def _fake_open(path, *args, **kwargs):
            if path == "/dev/tty":
                return _FakeTTY()
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", _fake_open)

        rt.session_push_title_token(plan_id, "🔨")
        assert len(written) == 1
        out = written[0]
        assert out.startswith("\x1b]0;")
        assert out.endswith("\x07")
        # No glyph (no title_token) → ``{icon} {body}`` only.
        assert out == "\x1b]0;🔨 pm:3-outline:fmt\x07"


# =============================================================================
# 5. permission_configure
# =============================================================================


class TestPermissionConfigure:
    """Tests for ClaudeRuntime.permission_configure."""

    def test_invalid_scope_returns_error(self, rt):
        """An invalid scope returns status=error."""
        result = _parsed(rt.permission_configure("invalid", []))
        assert result["status"] == "error"
        assert result["error"] == "invalid_scope"

    def test_writes_permissions_to_project_settings(self, rt, tmp_path, monkeypatch):
        """permission_configure writes the allow list to project settings.json."""
        import claude_runtime as _cr

        settings_path = tmp_path / ".claude" / "settings.json"
        _write_settings(settings_path, [])
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: settings_path)

        perms = ["Read(**)", "Write(.plan/**)"]
        result = _parsed(rt.permission_configure("project", perms))
        assert result["status"] == "success"
        assert result["permissions_written"] == 2

        saved = json.loads(settings_path.read_text())
        assert saved["permissions"]["allow"] == perms

    def test_empty_permissions_clears_allow_list(self, rt, tmp_path, monkeypatch):
        """Passing [] clears the allow list."""
        import claude_runtime as _cr

        settings_path = tmp_path / ".claude" / "settings.json"
        _write_settings(settings_path, ["Read(**)", "Write(**)"])
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: settings_path)

        result = _parsed(rt.permission_configure("project", []))
        assert result["status"] == "success"
        saved = json.loads(settings_path.read_text())
        assert saved["permissions"]["allow"] == []


# =============================================================================
# 6. permission_analyze
# =============================================================================


class TestPermissionAnalyze:
    """Tests for ClaudeRuntime.permission_analyze."""

    def test_invalid_scope_returns_error(self, rt):
        result = _parsed(rt.permission_analyze("invalid", ["redundant"], None))
        assert result["status"] == "error"
        assert result["error"] == "invalid_scope"

    def test_invalid_check_returns_error(self, rt):
        result = _parsed(rt.permission_analyze("project", ["nonexistent"], None))
        assert result["status"] == "error"
        assert result["error"] == "invalid_check"

    def test_missing_steps_without_marshal_returns_error(self, rt):
        """missing-steps check without marshal_path returns error."""
        result = _parsed(rt.permission_analyze("project", ["missing-steps"], None))
        assert result["status"] == "error"
        assert result["error"] == "marshal_not_found"

    def test_redundant_check_detects_duplicates(self, rt, tmp_path, monkeypatch):
        """redundant check reports permissions present in both global and project."""
        import claude_runtime as _cr

        global_settings = tmp_path / "global_settings.json"
        project_settings = tmp_path / "project_settings.json"
        shared_perm = "Read(.plan/**)"
        _write_settings(global_settings, [shared_perm, "Write(**)"])
        _write_settings(project_settings, [shared_perm, "Edit(**)"])

        monkeypatch.setattr(_cr, "_claude_global_settings_path", lambda: global_settings)
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: project_settings)

        result = _parsed(rt.permission_analyze("both", ["redundant"], None))
        assert result["status"] == "success"
        assert result["total_findings"] >= 1
        redundant_findings = [f for f in result["findings"] if f["check"] == "redundant"]
        assert any(shared_perm in f["details"] for f in redundant_findings)

    def test_suspicious_check_detects_broad_bash(self, rt, tmp_path, monkeypatch):
        """suspicious check reports Bash(*) as high-severity."""
        import claude_runtime as _cr

        settings = tmp_path / "settings.json"
        _write_settings(settings, ["Bash(*)", "Read(**)"])
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: settings)

        result = _parsed(rt.permission_analyze("project", ["suspicious"], None))
        assert result["status"] == "success"
        suspicious = [f for f in result["findings"] if f["check"] == "suspicious"]
        assert any(f["severity"] == "high" for f in suspicious)

    def test_all_check_expands_to_three_checks(self, rt, tmp_path, monkeypatch):
        """checks=['all'] runs redundant, suspicious, and missing-steps (requires marshal)."""
        import claude_runtime as _cr

        marshal = tmp_path / "marshal.json"
        marshal.write_text(json.dumps({"plan": {}}), encoding="utf-8")
        settings = tmp_path / "settings.json"
        _write_settings(settings, [])
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: settings)
        monkeypatch.setattr(_cr, "_claude_global_settings_path", lambda: settings)

        result = _parsed(rt.permission_analyze("project", ["all"], str(marshal)))
        assert result["status"] == "success"
        assert sorted(result["checks_run"]) == sorted(["missing-steps", "redundant", "suspicious"])


# =============================================================================
# 7. permission_fix
# =============================================================================


class TestPermissionFix:
    """Tests for ClaudeRuntime.permission_fix."""

    def test_invalid_scope_returns_error(self, rt):
        result = _parsed(rt.permission_fix("invalid", "add", [], False))
        assert result["status"] == "error"
        assert result["error"] == "invalid_scope"

    def test_invalid_operation_returns_error(self, rt):
        result = _parsed(rt.permission_fix("project", "explode", [], False))
        assert result["status"] == "error"
        assert result["error"] == "invalid_operation"

    def test_add_operation_appends_new_permissions(self, rt, tmp_path, monkeypatch):
        """add operation appends new permissions to the allow list."""
        import claude_runtime as _cr

        settings_path = tmp_path / "settings.json"
        _write_settings(settings_path, ["Read(**)"])
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: settings_path)

        result = _parsed(rt.permission_fix("project", "add", ["Write(**)"], False))
        assert result["status"] == "success"
        assert result["changes_applied"] == 1
        saved = json.loads(settings_path.read_text())
        assert "Write(**)" in saved["permissions"]["allow"]

    def test_add_operation_does_not_duplicate(self, rt, tmp_path, monkeypatch):
        """add operation skips already-present permissions."""
        import claude_runtime as _cr

        settings_path = tmp_path / "settings.json"
        _write_settings(settings_path, ["Read(**)"])
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: settings_path)

        result = _parsed(rt.permission_fix("project", "add", ["Read(**)"], False))
        assert result["status"] == "success"
        assert result["changes_applied"] == 0

    def test_remove_operation_removes_permissions(self, rt, tmp_path, monkeypatch):
        """remove operation removes matching permissions from the allow list."""
        import claude_runtime as _cr

        settings_path = tmp_path / "settings.json"
        _write_settings(settings_path, ["Read(**)", "Write(**)"])
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: settings_path)

        result = _parsed(rt.permission_fix("project", "remove", ["Write(**)"], False))
        assert result["status"] == "success"
        assert result["changes_applied"] == 1
        saved = json.loads(settings_path.read_text())
        assert "Write(**)" not in saved["permissions"]["allow"]

    def test_normalize_deduplicates_and_adds_defaults(self, rt, tmp_path, monkeypatch):
        """normalize deduplicates and adds missing default permissions."""
        import claude_runtime as _cr

        settings_path = tmp_path / "settings.json"
        _write_settings(settings_path, ["Read(**)", "Read(**)"])  # duplicate
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: settings_path)

        result = _parsed(rt.permission_fix("project", "normalize", [], False))
        assert result["status"] == "success"
        saved = json.loads(settings_path.read_text())
        allow = saved["permissions"]["allow"]
        # No duplicates.
        assert len(allow) == len(set(allow))
        # Default entries added.
        assert "Edit(.plan/**)" in allow

    def test_dry_run_does_not_write_settings(self, rt, tmp_path, monkeypatch):
        """dry_run=True returns proposed_additions but does not mutate the file."""
        import claude_runtime as _cr

        settings_path = tmp_path / "settings.json"
        original = ["Read(**)"]
        _write_settings(settings_path, original)
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: settings_path)

        result = _parsed(rt.permission_fix("project", "add", ["Write(**)"], True))
        assert result["status"] == "success"
        assert result["dry_run"] is True
        assert result["changes_applied"] == 0
        # File unchanged.
        saved = json.loads(settings_path.read_text())
        assert saved["permissions"]["allow"] == original

    def test_ensure_operation_adds_missing(self, rt, tmp_path, monkeypatch):
        """ensure operation adds permissions that are not already present."""
        import claude_runtime as _cr

        settings_path = tmp_path / "settings.json"
        _write_settings(settings_path, [])
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: settings_path)

        result = _parsed(rt.permission_fix("project", "ensure", ["Bash(python3 .plan/execute-script.py *)"], False))
        assert result["status"] == "success"
        saved = json.loads(settings_path.read_text())
        assert "Bash(python3 .plan/execute-script.py *)" in saved["permissions"]["allow"]

    def test_consolidate_replaces_enumerated_with_wildcard(self, rt, tmp_path, monkeypatch):
        """consolidate replaces 3+ same-tool permissions with a wildcard."""
        import claude_runtime as _cr

        settings_path = tmp_path / "settings.json"
        _write_settings(settings_path, ["Read(a)", "Read(b)", "Read(c)"])
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: settings_path)

        result = _parsed(rt.permission_fix("project", "consolidate", [], False))
        assert result["status"] == "success"
        saved = json.loads(settings_path.read_text())
        assert "Read(*)" in saved["permissions"]["allow"]


# =============================================================================
# 8. permission_ensure_wildcards
# =============================================================================


class TestPermissionEnsureWildcards:
    """Tests for ClaudeRuntime.permission_ensure_wildcards."""

    def test_invalid_scope_returns_error(self, rt):
        result = _parsed(rt.permission_ensure_wildcards("invalid", ".", False))
        assert result["status"] == "error"
        assert result["error"] == "invalid_scope"

    def test_scans_bundles_and_adds_wildcards(self, rt, tmp_path, monkeypatch):
        """Bundles with plugin.json get Skill({bundle}:*) and SlashCommand(/{bundle}:*) permissions."""
        import claude_runtime as _cr

        # Create a fake marketplace dir with one bundle.
        marketplace = tmp_path / "marketplace"
        bundle_dir = marketplace / "my-bundle"
        plugin_json = bundle_dir / ".claude-plugin" / "plugin.json"
        plugin_json.parent.mkdir(parents=True)
        plugin_json.write_text("{}", encoding="utf-8")

        settings_path = tmp_path / "settings.json"
        _write_settings(settings_path, [])
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: settings_path)

        result = _parsed(rt.permission_ensure_wildcards("project", str(marketplace), False))
        assert result["status"] == "success"
        assert result["bundles_scanned"] == 1
        saved = json.loads(settings_path.read_text())
        allow = saved["permissions"]["allow"]
        assert "Skill(my-bundle:*)" in allow
        assert "SlashCommand(/my-bundle:*)" in allow

    def test_dry_run_reports_without_writing(self, rt, tmp_path, monkeypatch):
        """dry_run=True returns proposed_additions without mutating settings."""
        import claude_runtime as _cr

        marketplace = tmp_path / "mp"
        bundle_dir = marketplace / "bundle-x"
        pj = bundle_dir / ".claude-plugin" / "plugin.json"
        pj.parent.mkdir(parents=True)
        pj.write_text("{}", encoding="utf-8")

        settings_path = tmp_path / "settings.json"
        _write_settings(settings_path, [])
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: settings_path)

        result = _parsed(rt.permission_ensure_wildcards("project", str(marketplace), True))
        assert result["dry_run"] is True
        assert result["wildcards_added"] == 0
        # File not changed.
        saved = json.loads(settings_path.read_text())
        assert saved["permissions"]["allow"] == []

    def test_already_present_wildcards_not_duplicated(self, rt, tmp_path, monkeypatch):
        """Wildcards already in the allow list are not added again."""
        import claude_runtime as _cr

        marketplace = tmp_path / "mp2"
        bundle_dir = marketplace / "bundle-y"
        pj = bundle_dir / ".claude-plugin" / "plugin.json"
        pj.parent.mkdir(parents=True)
        pj.write_text("{}", encoding="utf-8")

        settings_path = tmp_path / "settings.json"
        _write_settings(settings_path, ["Skill(bundle-y:*)", "SlashCommand(/bundle-y:*)"])
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: settings_path)

        result = _parsed(rt.permission_ensure_wildcards("project", str(marketplace), False))
        assert result["wildcards_already_present"] == 2
        assert result["wildcards_added"] == 0


# =============================================================================
# 9. permission_ensure_steps
# =============================================================================


class TestPermissionEnsureSteps:
    """Tests for ClaudeRuntime.permission_ensure_steps."""

    def test_invalid_scope_returns_error(self, rt, tmp_path):
        result = _parsed(rt.permission_ensure_steps(str(tmp_path / "marshal.json"), "invalid", False))
        assert result["status"] == "error"
        assert result["error"] == "invalid_scope"

    def test_missing_marshal_returns_error(self, rt, tmp_path):
        result = _parsed(rt.permission_ensure_steps(str(tmp_path / "missing.json"), "project", False))
        assert result["status"] == "error"
        assert result["error"] == "marshal_not_found"

    def test_valid_marshal_returns_success(self, rt, tmp_path, monkeypatch):
        """A valid marshal.json (even with no steps) returns success."""
        import claude_runtime as _cr

        marshal = tmp_path / "marshal.json"
        marshal.write_text(json.dumps({"plan": {}}), encoding="utf-8")
        settings_path = tmp_path / "settings.json"
        _write_settings(settings_path, [])
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: settings_path)

        result = _parsed(rt.permission_ensure_steps(str(marshal), "project", False))
        assert result["status"] == "success"
        assert result["marshal"] == str(marshal)


# =============================================================================
# 10. permission_web_analyze
# =============================================================================


class TestPermissionWebAnalyze:
    """Tests for ClaudeRuntime.permission_web_analyze."""

    def test_invalid_scope_returns_error(self, rt):
        result = _parsed(rt.permission_web_analyze("invalid"))
        assert result["status"] == "error"
        assert result["error"] == "invalid_scope"

    def test_global_scope_returns_success(self, rt, tmp_path, monkeypatch):
        """global scope reads global settings and returns domain rows."""
        import claude_runtime as _cr

        settings = tmp_path / "global.json"
        _write_settings(settings, ["WebFetch(github.com)", "WebFetch(example.com)"])
        monkeypatch.setattr(_cr, "_claude_global_settings_path", lambda: settings)

        result = _parsed(rt.permission_web_analyze("global"))
        assert result["status"] == "success"
        assert result["total_domains"] == 2

    def test_both_scope_combines_global_and_project(self, rt, tmp_path, monkeypatch):
        """both scope includes domains from both global and project settings."""
        import claude_runtime as _cr

        global_s = tmp_path / "global.json"
        project_s = tmp_path / "project.json"
        _write_settings(global_s, ["WebFetch(a.com)"])
        _write_settings(project_s, ["WebFetch(b.com)"])
        monkeypatch.setattr(_cr, "_claude_global_settings_path", lambda: global_s)
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: project_s)

        result = _parsed(rt.permission_web_analyze("both"))
        assert result["total_domains"] == 2

    def test_major_domain_categorized_correctly(self, rt, tmp_path, monkeypatch):
        """github.com is categorized as 'major'."""
        import claude_runtime as _cr

        settings = tmp_path / "settings.json"
        _write_settings(settings, ["WebFetch(github.com)"])
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: settings)

        result = _parsed(rt.permission_web_analyze("project"))
        assert result["status"] == "success"
        domains = result["domains"]
        github_entry = next((d for d in domains if d["domain"] == "github.com"), None)
        assert github_entry is not None
        assert github_entry["category"] == "major"


# =============================================================================
# 11. permission_web_apply
# =============================================================================


class TestPermissionWebApply:
    """Tests for ClaudeRuntime.permission_web_apply."""

    def test_invalid_scope_returns_error(self, rt):
        result = _parsed(rt.permission_web_apply("invalid", [], [], False))
        assert result["status"] == "error"
        assert result["error"] == "invalid_scope"

    def test_add_domain_appends_webfetch_permission(self, rt, tmp_path, monkeypatch):
        """Adding a domain appends WebFetch({domain}) to the allow list."""
        import claude_runtime as _cr

        settings_path = tmp_path / "settings.json"
        _write_settings(settings_path, [])
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: settings_path)

        result = _parsed(rt.permission_web_apply("project", ["docs.example.com"], [], False))
        assert result["status"] == "success"
        assert result["domains_added"] == 1
        saved = json.loads(settings_path.read_text())
        assert "WebFetch(docs.example.com)" in saved["permissions"]["allow"]

    def test_remove_domain_removes_webfetch_permission(self, rt, tmp_path, monkeypatch):
        """Removing a domain removes the corresponding WebFetch permission."""
        import claude_runtime as _cr

        settings_path = tmp_path / "settings.json"
        _write_settings(settings_path, ["WebFetch(old.com)", "Read(**)"])
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: settings_path)

        result = _parsed(rt.permission_web_apply("project", [], ["old.com"], False))
        assert result["status"] == "success"
        assert result["domains_removed"] == 1
        saved = json.loads(settings_path.read_text())
        assert "WebFetch(old.com)" not in saved["permissions"]["allow"]

    def test_dry_run_does_not_write(self, rt, tmp_path, monkeypatch):
        """dry_run=True computes counts without mutating the file."""
        import claude_runtime as _cr

        settings_path = tmp_path / "settings.json"
        original_allow = ["WebFetch(old.com)"]
        _write_settings(settings_path, original_allow)
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: settings_path)

        rt.permission_web_apply("project", ["new.com"], [], True)
        saved = json.loads(settings_path.read_text())
        assert saved["permissions"]["allow"] == original_allow


# =============================================================================
# 12. metrics_capture
# =============================================================================


class TestMetricsCapture:
    """Tests for ClaudeRuntime.metrics_capture."""

    def test_manual_total_tokens_stores_and_returns_success(self, rt, tmp_path, monkeypatch):
        """Providing total_tokens manually stores via manage-metrics and returns success."""
        import claude_runtime as _cr

        monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.chdir(tmp_path)
        # Cursor dir must exist.
        cursor_dir = tmp_path / ".plan" / "local" / "plans" / "my-plan" / "work"
        cursor_dir.mkdir(parents=True)

        with patch("claude_runtime._manage_metrics_end_phase", return_value=True):
            result = _parsed(rt.metrics_capture("my-plan", "phase-1-init", 12345))

        assert result["status"] == "success"
        assert result["tokens_captured"] == 12345
        assert result["source"] == "manual"

    def test_no_session_id_returns_noop(self, rt, monkeypatch):
        """When no session_id is stored, metrics_capture returns no-op."""
        with patch("claude_runtime._manage_status_read_session", return_value=None):
            result = _parsed(rt.metrics_capture("plan-x", "phase-2-refine", None))
        assert result["status"] == "no-op"

    def test_no_transcript_returns_noop(self, rt, monkeypatch):
        """When transcript cannot be located, metrics_capture returns no-op."""
        with patch("claude_runtime._manage_status_read_session", return_value="sess-123"):
            with patch("claude_runtime._find_transcript", return_value=None):
                result = _parsed(rt.metrics_capture("plan-y", "phase-3-outline", None))
        assert result["status"] == "no-op"

    def test_cursor_delta_captures_incremental_tokens(self, rt, tmp_path, monkeypatch):
        """Token count is prior_cursor subtracted from transcript total."""
        import claude_runtime as _cr

        monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.chdir(tmp_path)

        # Create a fake JSONL transcript.
        transcript = tmp_path / "transcript.jsonl"
        line1 = json.dumps({"message": {"usage": {"input_tokens": 100, "output_tokens": 50}}})
        line2 = json.dumps({"message": {"usage": {"input_tokens": 80, "output_tokens": 20}}})
        transcript.write_text(f"{line1}\n{line2}\n", encoding="utf-8")

        # Cursor already at 100 from a prior capture.
        cursor_dir = tmp_path / ".plan" / "local" / "plans" / "plan-tok" / "work"
        cursor_dir.mkdir(parents=True)
        (cursor_dir / "metrics-cursor-phase-1-init.toon").write_text(
            "plan_id: plan-tok\nphase: phase-1-init\ntotal_tokens: 100\n"
        )

        with patch("claude_runtime._manage_status_read_session", return_value="sess-tok"):
            with patch("claude_runtime._find_transcript", return_value=transcript):
                with patch("claude_runtime._manage_metrics_end_phase", return_value=True):
                    result = _parsed(rt.metrics_capture("plan-tok", "phase-1-init", None))

        assert result["status"] == "success"
        # Total = 100+50+80+20 = 250; prior cursor = 100; captured = 150.
        assert result["tokens_captured"] == 150


# =============================================================================
# 13. subagent_dispatch
# =============================================================================


class TestSubagentDispatch:
    """Tests for ClaudeRuntime.subagent_dispatch."""

    def test_agent_not_found_returns_error(self, rt):
        """When agent file cannot be located, subagent_dispatch returns error."""
        with patch("claude_runtime._find_agent_file", return_value=None):
            result = _parsed(rt.subagent_dispatch("nonexistent-agent", None, None))
        assert result["status"] == "error"
        assert result["error"] == "prompt_not_found"

    def test_agent_with_unmapped_tool_returns_noop(self, rt, tmp_path):
        """An agent requiring an unmapped tool (e.g. SendMessage) returns no-op."""
        agent_file = tmp_path / "bad-agent.md"
        agent_file.write_text(
            "---\nname: bad-agent\ndescription: uses bad tool\ntools: [SendMessage]\n---\nBody.",
            encoding="utf-8",
        )
        with patch("claude_runtime._find_agent_file", return_value=agent_file):
            result = _parsed(rt.subagent_dispatch("bad-agent", None, None))
        assert result["status"] == "no-op"

    def test_valid_agent_returns_task_invocation(self, rt, tmp_path):
        """A valid agent returns success with platform=claude and invocation.tool=Task."""
        agent_file = tmp_path / "good-agent.md"
        agent_file.write_text(
            "---\nname: good-agent\ndescription: Does something useful\ntools: [Read, Write]\n---\nDo the work.",
            encoding="utf-8",
        )
        with patch("claude_runtime._find_agent_file", return_value=agent_file):
            result = _parsed(rt.subagent_dispatch("good-agent", None, None))
        assert result["status"] == "success"
        assert result["platform"] == "claude"
        assert result["invocation"]["tool"] == "Task"

    def test_context_injected_into_prompt(self, rt, tmp_path):
        """Provided context is merged into the prompt body.

        Note: TOON cannot round-trip multi-line strings in nested objects (the
        serializer emits a quoted string with literal newlines, which the parser
        does not re-join into a single value).  The assertion therefore checks
        the raw TOON output string rather than the parsed dict.
        """
        agent_file = tmp_path / "ctx-agent.md"
        agent_file.write_text(
            "---\nname: ctx-agent\ndescription: context test\ntools: [Read]\n---\nAgent body.",
            encoding="utf-8",
        )
        with patch("claude_runtime._find_agent_file", return_value=agent_file):
            raw_output = rt.subagent_dispatch("ctx-agent", None, {"plan_id": "my-plan"})
        # Check status via parsed TOON (single-line value — round-trips cleanly).
        result = _parsed(raw_output)
        assert result["status"] == "success"
        # Check prompt content in the raw TOON string (multi-line value).
        assert "my-plan" in raw_output

    def test_prompt_file_override_used_when_provided(self, rt, tmp_path):
        """When prompt_file is provided and exists, its content is used as the prompt body.

        The prompt value may contain newlines and therefore does not round-trip
        cleanly through TOON.  The assertion checks the raw TOON output string.
        """
        agent_file = tmp_path / "agent.md"
        agent_file.write_text(
            "---\nname: agent\ndescription: override test\ntools: [Read]\n---\nOriginal.",
            encoding="utf-8",
        )
        override_file = tmp_path / "override.md"
        override_file.write_text("Override body content.", encoding="utf-8")

        with patch("claude_runtime._find_agent_file", return_value=agent_file):
            raw_output = rt.subagent_dispatch("agent", str(override_file), None)
        result = _parsed(raw_output)
        assert result["status"] == "success"
        # Check prompt content in the raw TOON string (multi-line value).
        assert "Override body content." in raw_output

    def test_missing_prompt_file_returns_error(self, rt, tmp_path):
        """A prompt_file path that does not exist returns error."""
        agent_file = tmp_path / "agent2.md"
        agent_file.write_text(
            "---\nname: agent2\ndescription: test\ntools: [Read]\n---\nBody.",
            encoding="utf-8",
        )
        with patch("claude_runtime._find_agent_file", return_value=agent_file):
            result = _parsed(rt.subagent_dispatch("agent2", str(tmp_path / "missing.md"), None))
        assert result["status"] == "error"
        assert result["error"] == "prompt_not_found"


# =============================================================================
# 14. health_check
# =============================================================================


class TestHealthCheck:
    """Tests for ClaudeRuntime.health_check."""

    def test_invalid_check_returns_error(self, rt):
        result = _parsed(rt.health_check("invalid-check"))
        assert result["status"] == "error"
        assert result["error"] == "invalid_check"

    def test_permissions_check_included_in_all(self, rt, tmp_path, monkeypatch):
        """checks='all' includes permissions, display, mcp-diagnostics, and hook."""
        import claude_runtime as _cr

        # Ensure no real settings file is accessed.
        fake_settings = tmp_path / "settings.json"
        _write_settings(fake_settings, [])
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: fake_settings)
        monkeypatch.chdir(tmp_path)

        result = _parsed(rt.health_check("all"))
        assert result["status"] == "success"
        assert "permissions" in result["checks_run"]
        assert "display" in result["checks_run"]
        assert "mcp-diagnostics" in result["checks_run"]
        assert "hook" in result["checks_run"]

    def test_permissions_healthy_when_settings_present(self, rt, tmp_path, monkeypatch):
        """permissions check is healthy when project settings.json exists."""
        import claude_runtime as _cr

        fake_settings = tmp_path / "project_settings.json"
        _write_settings(fake_settings, ["Read(**)"])
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: fake_settings)
        monkeypatch.chdir(tmp_path)

        result = _parsed(rt.health_check("permissions"))
        perm_result = next(r for r in result["results"] if r["check"] == "permissions")
        assert perm_result["healthy"] is True

    # Per-event labels reported by the display check, in order. Mirrors
    # _DISPLAY_RENDER_ENTRIES plus statusLine + env in claude_runtime.
    _DISPLAY_LABELS = (
        "SessionStart:matcher-less",
        "UserPromptSubmit",
        "Notification",
        "Stop",
        "PreToolUse:AskUserQuestion",
        "PreToolUse:Bash",
        "PostToolUse",
        "statusLine",
        "env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE",
    )

    def test_display_healthy_when_fully_wired(self, rt, tmp_path, monkeypatch):
        """display check is healthy when every required terminal-title entry is present.

        A fresh terminal-title project install-hook writes the complete render
        wiring; the display check must then report every terminal-title label as
        ``present`` and ``healthy: true``. The orthogonal enforcement entry is
        NOT installed by the terminal-title path, so it reports MISSING without
        making the display unhealthy.
        """
        target = tmp_path / ".claude" / "settings.local.json"
        rt.project_install_hook(str(target))
        monkeypatch.chdir(tmp_path)

        result = _parsed(rt.health_check("display"))
        display_result = next(r for r in result["results"] if r["check"] == "display")
        assert display_result["healthy"] is True
        detail = display_result["detail"]
        for label in self._DISPLAY_LABELS:
            assert f"{label}: present" in detail
        # The enforcement entry is orthogonal — absent after a terminal-title
        # install — so it is the ONLY MISSING line and the display stays healthy.
        assert "PreToolUse:enforcement: MISSING" in detail

    def test_display_unhealthy_when_render_hook_absent(self, rt, tmp_path, monkeypatch):
        """display check is unhealthy when no render-title hook entry is present.

        An empty settings file (no .claude/settings.local.json) reports every
        required label as MISSING.
        """
        monkeypatch.chdir(tmp_path)
        result = _parsed(rt.health_check("display"))
        display_result = next(r for r in result["results"] if r["check"] == "display")
        assert display_result["healthy"] is False
        detail = display_result["detail"]
        for label in self._DISPLAY_LABELS:
            assert f"{label}: MISSING" in detail

    def test_display_partial_install_names_each_missing_entry(self, rt, tmp_path, monkeypatch):
        """A partial install (only SessionStart wired) reports the missing entries by label.

        Only the SessionStart matcher-less render entry is present; every other
        required label must be reported MISSING and the literal token MISSING
        (the load-bearing grep target the menu doc references) must appear.
        """
        settings_path = tmp_path / ".claude" / "settings.local.json"
        settings_path.parent.mkdir(parents=True)
        settings_data = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "",
                        "hooks": [
                            {"type": "command", "command": _RENDER_HOOK_COMMAND}
                        ],
                    }
                ]
            }
        }
        settings_path.write_text(json.dumps(settings_data), encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        result = _parsed(rt.health_check("display"))
        display_result = next(r for r in result["results"] if r["check"] == "display")
        assert display_result["healthy"] is False
        detail = display_result["detail"]
        # The one wired entry is present.
        assert "SessionStart:matcher-less: present" in detail
        # Every other required entry is named MISSING.
        for label in (
            "UserPromptSubmit",
            "Notification",
            "Stop",
            "PreToolUse:AskUserQuestion",
            "PreToolUse:Bash",
            "PostToolUse",
            "statusLine",
            "env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE",
        ):
            assert f"{label}: MISSING" in detail

    def test_display_detail_contains_missing_token_when_any_entry_absent(
        self, rt, tmp_path, monkeypatch
    ):
        """The literal token MISSING is present whenever any required entry is absent.

        Load-bearing for the menu-terminal-title.md diagnosis guidance, which
        tells the user to grep the detail field for MISSING.
        """
        monkeypatch.chdir(tmp_path)
        result = _parsed(rt.health_check("display"))
        display_result = next(r for r in result["results"] if r["check"] == "display")
        assert "MISSING" in display_result["detail"]

    def test_hook_check_healthy_when_session_start_entry_present(self, rt, tmp_path, monkeypatch):
        """hook check is healthy when .claude/settings.json contains SessionStart hook."""
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_data = {
            "hooks": {
                "SessionStart": [
                    {"matcher": "", "hooks": [{"type": "command", "command": _HOOK_COMMAND}]}
                ]
            }
        }
        settings_path.write_text(json.dumps(settings_data), encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        result = _parsed(rt.health_check("all"))
        hook_result = next((r for r in result["results"] if r["check"] == "hook"), None)
        assert hook_result is not None
        assert hook_result["healthy"] is True

    @staticmethod
    def _write_hook_settings(path: Path) -> None:
        """Write a settings file at *path* containing the SessionStart hook."""
        path.parent.mkdir(parents=True, exist_ok=True)
        settings_data = {
            "hooks": {
                "SessionStart": [
                    {"matcher": "", "hooks": [{"type": "command", "command": _HOOK_COMMAND}]}
                ]
            }
        }
        path.write_text(json.dumps(settings_data), encoding="utf-8")

    def test_hook_check_healthy_when_in_settings_json_only(self, rt, tmp_path, monkeypatch):
        """hook check is healthy when the hook lives only in .claude/settings.json."""
        self._write_hook_settings(tmp_path / ".claude" / "settings.json")
        monkeypatch.chdir(tmp_path)

        result = _parsed(rt.health_check("all"))
        hook_result = next(r for r in result["results"] if r["check"] == "hook")
        assert hook_result["healthy"] is True
        assert "settings.json" in hook_result["detail"]

    def test_hook_check_healthy_when_in_settings_local_json_only(self, rt, tmp_path, monkeypatch):
        """hook check is healthy when the hook lives only in .claude/settings.local.json."""
        self._write_hook_settings(tmp_path / ".claude" / "settings.local.json")
        monkeypatch.chdir(tmp_path)

        result = _parsed(rt.health_check("all"))
        hook_result = next(r for r in result["results"] if r["check"] == "hook")
        assert hook_result["healthy"] is True
        assert "settings.local.json" in hook_result["detail"]

    def test_hook_check_unhealthy_when_in_neither_file(self, rt, tmp_path, monkeypatch):
        """hook check is unhealthy when the hook is absent from both settings files."""
        monkeypatch.chdir(tmp_path)

        result = _parsed(rt.health_check("all"))
        hook_result = next(r for r in result["results"] if r["check"] == "hook")
        assert hook_result["healthy"] is False
        assert "missing" in hook_result["detail"]

    def test_hook_check_healthy_when_in_both_files(self, rt, tmp_path, monkeypatch):
        """hook check is healthy when the hook is present in both settings files."""
        self._write_hook_settings(tmp_path / ".claude" / "settings.json")
        self._write_hook_settings(tmp_path / ".claude" / "settings.local.json")
        monkeypatch.chdir(tmp_path)

        result = _parsed(rt.health_check("all"))
        hook_result = next(r for r in result["results"] if r["check"] == "hook")
        assert hook_result["healthy"] is True
        assert "settings.json" in hook_result["detail"]
        assert "settings.local.json" in hook_result["detail"]

    def test_all_healthy_reflects_individual_results(self, rt, tmp_path, monkeypatch):
        """all_healthy is False when any single check is unhealthy."""
        import claude_runtime as _cr

        # No settings file → permissions check fails.
        fake_settings = tmp_path / "nonexistent_settings.json"
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: fake_settings)
        monkeypatch.chdir(tmp_path)

        result = _parsed(rt.health_check("permissions"))
        assert result["all_healthy"] is False


# =============================================================================
# 4c. _read_title_state three-location search order (main-live -> worktree ->
#     archived) + _resolve_worktree_status_json probe (phase-5/6 freeze fix)
# =============================================================================


def _titlestate_reader_cwd(tmp_path, monkeypatch):
    """Pin the reader's ``_PLAN_DIR_NAME`` at ``.plan`` and chdir into tmp_path
    so the reader's relative ``Path(_PLAN_DIR_NAME)`` resolutions land under the
    temp tree. Returns the ``claude_runtime`` module."""
    import claude_runtime as _cr

    monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
    monkeypatch.chdir(tmp_path)
    return _cr


def _titlestate_write_live(tmp_path, plan_id, status):
    """Write the main-live ``status.json`` for *plan_id*."""
    d = tmp_path / ".plan" / "local" / "plans" / plan_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "status.json").write_text(json.dumps(status), encoding="utf-8")


def _titlestate_write_worktree(tmp_path, plan_id, status):
    """Write the phase-5+ worktree ``status.json`` for *plan_id* at
    ``.plan/local/worktrees/{plan_id}/.plan/local/plans/{plan_id}/status.json``."""
    d = (
        tmp_path
        / ".plan"
        / "local"
        / "worktrees"
        / plan_id
        / ".plan"
        / "local"
        / "plans"
        / plan_id
    )
    d.mkdir(parents=True, exist_ok=True)
    (d / "status.json").write_text(json.dumps(status), encoding="utf-8")


def _titlestate_write_archived(tmp_path, plan_id, status, date_prefix="2026-05-29"):
    """Write the archived ``status.json`` for *plan_id*."""
    d = tmp_path / ".plan" / "local" / "archived-plans" / f"{date_prefix}-{plan_id}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "status.json").write_text(json.dumps(status), encoding="utf-8")


class TestReadTitleStateWorktree:
    """Regression tests for the three-location ``_read_title_state`` search order
    (main-live -> worktree -> archived) and the ``_resolve_worktree_status_json``
    probe added so the title no longer freezes once the plan dir is moved into
    its worktree during phases 5-6 (ADR-002)."""

    def test_live_present_resolves_live(self, tmp_path, monkeypatch):
        """Case 1 — a present main-live status.json resolves live even when
        worktree and archived copies also exist (live wins, unchanged)."""
        cr = _titlestate_reader_cwd(tmp_path, monkeypatch)
        _titlestate_write_live(
            tmp_path, "wt-plan", {"current_phase": "3-outline", "short_description": "live"}
        )
        _titlestate_write_worktree(
            tmp_path, "wt-plan", {"current_phase": "5-execute", "short_description": "wt"}
        )
        _titlestate_write_archived(
            tmp_path, "wt-plan", {"current_phase": "6-finalize", "short_description": "arch"}
        )

        state = cr._read_title_state("wt-plan")

        assert state == {"current_phase": "3-outline", "short_description": "live"}

    def test_live_absent_worktree_present_resolves_worktree(self, tmp_path, monkeypatch):
        """Case 2 — with the main-live path absent, the worktree status.json
        resolves (the phase-5/6 freeze scenario), taking precedence over the
        archived copy."""
        cr = _titlestate_reader_cwd(tmp_path, monkeypatch)
        _titlestate_write_worktree(
            tmp_path, "wt-plan", {"current_phase": "5-execute", "short_description": "wt"}
        )
        _titlestate_write_archived(
            tmp_path, "wt-plan", {"current_phase": "6-finalize", "short_description": "arch"}
        )

        state = cr._read_title_state("wt-plan")

        assert state == {"current_phase": "5-execute", "short_description": "wt"}

    def test_live_and_worktree_absent_archived_present_resolves_archived(
        self, tmp_path, monkeypatch
    ):
        """Case 3 — with both live and worktree absent, the archived fallback is
        preserved unchanged."""
        cr = _titlestate_reader_cwd(tmp_path, monkeypatch)
        _titlestate_write_archived(
            tmp_path, "wt-plan", {"current_phase": "6-finalize", "short_description": "arch"}
        )

        state = cr._read_title_state("wt-plan")

        assert state == {"current_phase": "6-finalize", "short_description": "arch"}

    def test_none_present_returns_none(self, tmp_path, monkeypatch):
        """Case 4 — no status.json in any of the three locations returns None."""
        cr = _titlestate_reader_cwd(tmp_path, monkeypatch)

        assert cr._read_title_state("wt-plan") is None

    def test_resolve_worktree_status_json_present_returns_path(self, tmp_path, monkeypatch):
        """Focused probe — a present worktree status.json resolves to its path."""
        cr = _titlestate_reader_cwd(tmp_path, monkeypatch)
        _titlestate_write_worktree(tmp_path, "wt-plan", {"current_phase": "5-execute"})

        resolved = cr._resolve_worktree_status_json("wt-plan")

        assert resolved is not None
        expected = (
            tmp_path
            / ".plan"
            / "local"
            / "worktrees"
            / "wt-plan"
            / ".plan"
            / "local"
            / "plans"
            / "wt-plan"
            / "status.json"
        )
        assert resolved.resolve() == expected.resolve()

    def test_resolve_worktree_status_json_absent_returns_none(self, tmp_path, monkeypatch):
        """Focused probe — an absent worktree status.json resolves to None."""
        cr = _titlestate_reader_cwd(tmp_path, monkeypatch)

        assert cr._resolve_worktree_status_json("wt-plan") is None


# =============================================================================
# session_reload_directive — Claude resolves /reload-plugins + monitor caveat
# =============================================================================


def test_session_reload_directive_resolves_reload_plugins():
    """Claude resolves the /reload-plugins directive (a pure resolver — no
    filesystem), so a plain ClaudeRuntime instance suffices."""
    result = parse_toon(ClaudeRuntime().session_reload_directive())
    assert result["status"] == "success"
    assert result["operation"] == "session reload-directive"
    assert result["directive"] == "/reload-plugins"


def test_session_reload_directive_carries_monitor_caveat():
    """The success payload carries the monitor caveat verbatim — plan-marshall
    registers no monitors, so /reload-plugins picks up the regenerated set live."""
    result = parse_toon(ClaudeRuntime().session_reload_directive())
    caveat = result["caveat"]
    assert "monitors require a full session restart" in caveat
    assert "plan-marshall registers no monitors" in caveat
    assert "/reload-plugins picks up the regenerated executor / agent set live" in caveat


# =============================================================================
# wait_for — bounded poll over a concrete observable
#
# The op is deliberately narrowed to a CONCRETE observable kind rather than an
# opaque condition descriptor. These tests pin the two fail-closed rules the
# contract names: silence is not success (every failure signature maps to its
# own negative outcome) and a bound is not a verdict (exhaustion yields a
# non-terminal ``pending``, never an implicit pass).
# =============================================================================


def _fake_clock(*values: float):
    """Return a deterministic ``time.monotonic`` stand-in.

    Successive calls yield *values* in order; the final value is repeated for
    any further call, so a test states only as many ticks as it cares about.
    """
    seq = list(values)

    def _clock() -> float:
        return seq.pop(0) if len(seq) > 1 else seq[0]

    return _clock


class _PollRecorder:
    """Stand-in for ``claude_runtime.build_job_poll`` recording its call args."""

    def __init__(self, *payloads: dict[str, Any]) -> None:
        self._payloads = list(payloads)
        self.calls: list[tuple[str, int]] = []

    def __call__(self, reference: str, bound_seconds: int) -> dict[str, Any]:
        self.calls.append((reference, bound_seconds))
        if len(self._payloads) > 1:
            return self._payloads.pop(0)
        return self._payloads[0]


def _wait_for(
    poll: _PollRecorder,
    *,
    observable: str = "build-job",
    reference: str = "job-42",
    bound_seconds: int = 10,
    clock=None,
    channel_reason: str | None = None,
) -> dict[str, Any]:
    """Run ``wait_for`` with the observable channel fully stubbed out."""
    clock = clock or _fake_clock(0.0, 0.0, 2.0)
    with (
        patch("claude_runtime.build_job_verify_channel", lambda: channel_reason),
        patch("claude_runtime.build_job_poll", poll),
        patch("time.monotonic", clock),
    ):
        return parse_toon(ClaudeRuntime().wait_for(observable, reference, bound_seconds))


class TestWaitForVocabulary:
    """The observable kind set and the normalized outcome vocabulary."""

    def test_observable_kinds_are_a_closed_single_element_set(self):
        """Exactly one observable kind ships — the marshalld build job."""
        assert claude_runtime.WAIT_OBSERVABLES == (claude_runtime.OBSERVABLE_BUILD_JOB,)
        assert claude_runtime.OBSERVABLE_BUILD_JOB == "build-job"

    def test_terminal_outcomes_exclude_pending(self):
        """``pending`` is deliberately absent — a bound is not a verdict."""
        assert claude_runtime.OUTCOME_PENDING not in claude_runtime.TERMINAL_OUTCOMES

    def test_terminal_outcomes_are_the_four_documented_values(self):
        """The terminal set is exactly succeeded / failed / timed_out / killed."""
        assert claude_runtime.TERMINAL_OUTCOMES == frozenset(
            {"succeeded", "failed", "timed_out", "killed"}
        )

    def test_every_failure_signature_maps_to_its_own_negative_outcome(self):
        """Silence is not success: each daemon failure status has a distinct
        negative outcome, so a failure can never read as continued waiting."""
        mapping = claude_runtime._BUILD_JOB_STATUS_TO_OUTCOME
        assert mapping["failure"] == "failed"
        assert mapping["timeout"] == "timed_out"
        assert mapping["killed"] == "killed"
        assert mapping["success"] == "succeeded"

    def test_killed_does_not_fold_into_failed(self):
        """An externally reaped job keeps its own outcome — it is not a flaky
        build and must not be blind-retried."""
        mapping = claude_runtime._BUILD_JOB_STATUS_TO_OUTCOME
        assert mapping["killed"] != mapping["failure"]

    def test_non_terminal_statuses_are_disjoint_from_the_outcome_map(self):
        """No wire status is both "keep waiting" and a terminal verdict."""
        assert not (
            claude_runtime._BUILD_JOB_NON_TERMINAL_STATUSES
            & set(claude_runtime._BUILD_JOB_STATUS_TO_OUTCOME)
        )


class TestWaitForGuards:
    """Input and channel guards — each returns a distinct error, never a pass."""

    def test_unknown_observable_kind_is_rejected(self):
        """An unrecognised kind errors rather than being silently awaited."""
        poll = _PollRecorder({"status": "success"})
        result = _wait_for(poll, observable="ci-run")

        assert result["status"] == "error"
        assert result["error"] == "unsupported_observable"
        assert "build-job" in result["message"]
        assert poll.calls == []

    def test_opaque_condition_descriptor_is_rejected_as_a_kind(self):
        """A free-form condition string is not an observable kind — a subprocess
        cannot evaluate an arbitrary predicate, so it is refused up front."""
        poll = _PollRecorder({"status": "success"})
        result = _wait_for(poll, observable="until the deploy looks healthy")

        assert result["error"] == "unsupported_observable"
        assert poll.calls == []

    @pytest.mark.parametrize("bound", [0, -1, -3600])
    def test_non_positive_bound_is_rejected(self, bound: int):
        """A bound must be a positive number of seconds."""
        poll = _PollRecorder({"status": "success"})
        result = _wait_for(poll, bound_seconds=bound)

        assert result["status"] == "error"
        assert result["error"] == "invalid_bound"
        assert poll.calls == []

    def test_observable_kind_is_validated_before_the_bound(self):
        """With both inputs invalid, the kind rejection wins — the caller is told
        the observable is not inspectable at all before bound arithmetic."""
        poll = _PollRecorder({"status": "success"})
        result = _wait_for(poll, observable="ci-run", bound_seconds=0)

        assert result["error"] == "unsupported_observable"

    @pytest.mark.parametrize(
        "reason", ["shared_build_layer_unavailable", "socket_absent", "version_mismatch"]
    )
    def test_unverifiable_channel_errors_without_polling(self, reason: str):
        """An unreachable inspection channel is an explicit error — never a pass
        and never an implicit pending."""
        poll = _PollRecorder({"status": "success"})
        result = _wait_for(poll, channel_reason=reason)

        assert result["status"] == "error"
        assert result["error"] == "observable_unreachable"
        assert reason in result["message"]
        assert "no outcome is implied" in result["message"]
        assert poll.calls == []


class TestWaitForOutcomes:
    """Normalized outcomes returned for each daemon wire status."""

    @pytest.mark.parametrize(
        ("wire_status", "outcome"),
        [
            ("success", "succeeded"),
            ("failure", "failed"),
            ("timeout", "timed_out"),
            ("killed", "killed"),
        ],
    )
    def test_terminal_status_maps_to_its_outcome(self, wire_status: str, outcome: str):
        """Each terminal wire status normalizes to its outcome, flagged terminal."""
        poll = _PollRecorder({"status": wire_status})
        result = _wait_for(poll)

        assert result["status"] == "success"
        assert result["operation"] == "wait for"
        assert result["outcome"] == outcome
        assert result["terminal"] is True

    def test_success_payload_echoes_the_intent_and_the_bounds(self):
        """The payload carries the kind, the reference, and both bound figures —
        and nothing observable-shaped."""
        poll = _PollRecorder({"status": "success"})
        result = _wait_for(poll, reference="job-99", bound_seconds=10)

        assert result["observable"] == "build-job"
        assert result["reference"] == "job-99"
        assert result["bound_seconds"] == 10
        assert result["elapsed_seconds"] == 2

    def test_no_daemon_shaped_field_crosses_the_boundary(self):
        """Daemon-internal keys are not leaked into the normalized payload."""
        poll = _PollRecorder(
            {"status": "failure", "log_file": "/tmp/x.log", "errors": [], "exit_code": 1}
        )
        result = _wait_for(poll)

        for leaked in ("log_file", "errors", "exit_code"):
            assert leaked not in result

    def test_unknown_reference_is_reported_as_such(self):
        """A ``not_found`` job is an error naming the reference, not a verdict."""
        poll = _PollRecorder({"status": "not_found"})
        result = _wait_for(poll, reference="job-nope")

        assert result["status"] == "error"
        assert result["error"] == "unknown_reference"
        assert "job-nope" in result["message"]

    def test_channel_lost_mid_wait_is_an_error(self):
        """A channel that drops after verification errors rather than passing."""
        poll = _PollRecorder({"status": "unreachable", "reason": "connection reset"})
        result = _wait_for(poll)

        assert result["status"] == "error"
        assert result["error"] == "observable_unreachable"
        assert "connection reset" in result["message"]

    def test_out_of_vocabulary_status_refuses_to_infer(self):
        """An undocumented status is an explicit error — no outcome is guessed."""
        poll = _PollRecorder({"status": "quantum-superposition"})
        result = _wait_for(poll)

        assert result["status"] == "error"
        assert result["error"] == "unexpected_observable_status"
        assert "quantum-superposition" in result["message"]

    @pytest.mark.parametrize("non_terminal", ["queued", "running"])
    def test_bound_exhaustion_yields_non_terminal_pending(self, non_terminal: str):
        """A bound is not a verdict: exhausting it returns pending / terminal
        false, an explicit unknown the caller must act on."""
        poll = _PollRecorder({"status": non_terminal})
        result = _wait_for(poll, clock=_fake_clock(0.0, 0.0, 11.0), bound_seconds=10)

        assert result["status"] == "success"
        assert result["outcome"] == "pending"
        assert result["terminal"] is False
        assert result["bound_seconds"] == 10
        assert result["elapsed_seconds"] == 11

    def test_non_terminal_status_is_re_polled_until_terminal(self):
        """A live job is re-polled; the first terminal status ends the wait."""
        poll = _PollRecorder(
            {"status": "queued"}, {"status": "running"}, {"status": "success"}
        )
        result = _wait_for(poll, clock=_fake_clock(0.0, 0.0, 1.0, 2.0, 3.0))

        assert result["outcome"] == "succeeded"
        assert len(poll.calls) == 3


class TestWaitForPollBound:
    """The per-poll long-poll bound handed to the daemon."""

    def test_poll_bound_is_capped_at_the_daemon_ceiling(self):
        """A caller bound larger than the ceiling is clamped per poll."""
        poll = _PollRecorder({"status": "success"})
        _wait_for(poll, bound_seconds=100_000)

        assert poll.calls[0][1] == claude_runtime._BUILD_JOB_POLL_BOUND_SECONDS

    def test_poll_bound_follows_the_caller_bound_when_smaller(self):
        """Below the ceiling the caller's bound is used verbatim."""
        poll = _PollRecorder({"status": "success"})
        _wait_for(poll, bound_seconds=10)

        assert poll.calls[0][1] == 10

    def test_poll_bound_floors_at_one_second(self):
        """A sub-second remainder still issues a one-second poll rather than a
        zero-second one that would return instantly and spin."""
        poll = _PollRecorder({"status": "success"})
        _wait_for(poll, bound_seconds=10, clock=_fake_clock(0.0, 9.5, 9.6))

        assert poll.calls[0][1] == 1

    def test_reference_is_forwarded_to_the_poll_verbatim(self):
        """The caller's reference reaches the daemon unmodified."""
        poll = _PollRecorder({"status": "success"})
        _wait_for(poll, reference="job-abc-123")

        assert poll.calls[0][0] == "job-abc-123"


class TestBuildJobVerifyChannel:
    """Fail-closed verification of the build-job inspection channel."""

    def test_missing_shared_build_layer_is_named(self):
        """An un-importable shared build layer is reported, not swallowed."""
        with patch("claude_runtime._build_job_modules", lambda: None):
            assert claude_runtime.build_job_verify_channel() == "shared_build_layer_unavailable"

    def test_absent_socket_is_named(self, tmp_path):
        """A registry with no socket file yields ``socket_absent``."""
        with (
            patch("claude_runtime._build_job_modules", lambda: (object(), object())),
            patch("claude_runtime._build_job_socket_path", lambda: tmp_path / "socket"),
        ):
            assert claude_runtime.build_job_verify_channel() == "socket_absent"

    def test_unanswered_ping_is_named(self, tmp_path):
        """A present socket that does not answer yields ``unreachable``."""
        sock = tmp_path / "socket"
        sock.write_text("", encoding="utf-8")
        with (
            patch("claude_runtime._build_job_modules", lambda: (object(), object())),
            patch("claude_runtime._build_job_socket_path", lambda: sock),
            patch("claude_runtime._build_job_call", lambda request, timeout: None),
        ):
            assert claude_runtime.build_job_verify_channel() == "unreachable"

    def test_non_ok_handshake_is_named(self, tmp_path):
        """A daemon answering with a non-ok status yields ``handshake_failed``."""
        sock = tmp_path / "socket"
        sock.write_text("", encoding="utf-8")
        with (
            patch("claude_runtime._build_job_modules", lambda: (object(), object())),
            patch("claude_runtime._build_job_socket_path", lambda: sock),
            patch(
                "claude_runtime._build_job_call",
                lambda request, timeout: {"status": "refused"},
            ),
        ):
            assert claude_runtime.build_job_verify_channel() == "handshake_failed"

    def test_protocol_version_mismatch_is_named(self, tmp_path):
        """A daemon speaking another protocol version is not trusted."""
        protocol = type("P", (), {"PROTOCOL_VERSION": "1"})
        sock = tmp_path / "socket"
        sock.write_text("", encoding="utf-8")
        with (
            patch("claude_runtime._build_job_modules", lambda: (protocol, object())),
            patch("claude_runtime._build_job_socket_path", lambda: sock),
            patch(
                "claude_runtime._build_job_call",
                lambda request, timeout: {"status": "ok", "version": "99"},
            ),
        ):
            assert claude_runtime.build_job_verify_channel() == "version_mismatch"

    def test_verified_channel_returns_none(self, tmp_path):
        """A reachable daemon on the matching version verifies clean."""
        protocol = type("P", (), {"PROTOCOL_VERSION": "1"})
        sock = tmp_path / "socket"
        sock.write_text("", encoding="utf-8")
        with (
            patch("claude_runtime._build_job_modules", lambda: (protocol, object())),
            patch("claude_runtime._build_job_socket_path", lambda: sock),
            patch(
                "claude_runtime._build_job_call",
                lambda request, timeout: {"status": "ok", "version": "1"},
            ),
        ):
            assert claude_runtime.build_job_verify_channel() is None


class TestBuildJobPoll:
    """The single bounded long-poll issued against the daemon."""

    def test_request_carries_the_wait_op_job_id_and_bound(self):
        """The wire request is the daemon's ``wait`` op for this job and bound."""
        captured: dict[str, Any] = {}

        def _call(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return {"status": "success"}

        with patch("claude_runtime._build_job_call", _call):
            claude_runtime.build_job_poll("job-7", 42)

        assert captured["request"] == {"op": "wait", "job_id": "job-7", "bound": 42}

    def test_read_timeout_exceeds_the_long_poll_bound(self):
        """The socket read window outlasts the server-side hold, so a daemon that
        answers exactly at the bound is not misread as unreachable."""
        captured: dict[str, Any] = {}

        def _call(request, timeout):
            captured["timeout"] = timeout
            return {"status": "success"}

        with patch("claude_runtime._build_job_call", _call):
            claude_runtime.build_job_poll("job-7", 42)

        assert captured["timeout"] > 42

    def test_unreachable_channel_yields_the_synthetic_payload(self):
        """A failed call surfaces as an explicit unreachable status — never as a
        terminal daemon status and never as an exception."""
        with patch("claude_runtime._build_job_call", lambda request, timeout: None):
            payload = claude_runtime.build_job_poll("job-7", 42)

        assert payload["status"] == claude_runtime._BUILD_JOB_UNREACHABLE_STATUS
        assert payload["reason"] == "unreachable"

    def test_daemon_payload_passes_through_unmodified(self):
        """A real daemon response is returned as-is for the caller to normalize."""
        payload = {"status": "failure", "duration_seconds": 12}
        with patch("claude_runtime._build_job_call", lambda request, timeout: payload):
            assert claude_runtime.build_job_poll("job-7", 42) == payload
