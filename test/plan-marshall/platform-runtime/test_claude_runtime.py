#!/usr/bin/env python3
"""Tests for claude_runtime.py — ClaudeRuntime implementation of all 15 operations.

Covers every method defined by the Runtime ABC:
  1.  project_initial_setup       — creates dirs, writes marshal.json, installs hook
  2.  session_capture             — reads $CLAUDE_CODE_SESSION_ID, stores via manage-status
  3.  session_render_title        — resolves session → plan → OSC emit
  5.  permission_configure        — overwrites allow list in settings
  6.  permission_analyze          — audits redundant / suspicious / missing-steps
  7.  permission_fix              — normalize / add / remove / ensure / consolidate
  8.  permission_ensure_wildcards — scans marketplace bundles, adds wildcard perms
  9.  permission_ensure_steps     — ensures project:{skill} step permissions
  10. permission_web_analyze       — audits WebFetch domain permissions
  11. permission_web_apply         — adds / removes WebFetch domain permissions
  12. metrics_capture             — records token consumption
  13. subagent_dispatch           — returns Task: invocation parameters
  14. health_check               — verifies platform integration

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
from claude_runtime import (  # type: ignore[import-not-found]
    ClaudeRuntime,
    _HOOK_COMMAND,
    _RENDER_HOOK_COMMAND,
    _STATUSLINE_COMMAND,
)
from toon_parser import parse_toon  # type: ignore[import-not-found]


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

    monkeypatch.setattr(_cr, "_SESSION_CACHE_BASE", tmp_path / "sessions")
    monkeypatch.setattr(_cr, "_CLAUDE_PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
    return ClaudeRuntime()


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
    return [
        h.get("command")
        for entry in entries
        if isinstance(entry, dict)
        for h in entry.get("hooks", [])
        if isinstance(h, dict)
    ]


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
        """Fresh install populates SessionStart (matcher-less + clear), UserPromptSubmit,
        Notification, Stop, PreToolUse:AskUserQuestion, PostToolUse:AskUserQuestion, and
        PostToolUse:Bash with the renderer command."""
        target = tmp_path / ".claude" / "settings.local.json"
        result = _parsed(rt.project_install_hook(str(target)))
        assert result["status"] == "success"
        assert result["hook_installed"] is True

        settings = json.loads(target.read_text())
        hooks_block = settings["hooks"]

        # SessionStart has BOTH the existing capture entry AND two render entries
        # (matcher-less + matcher:"clear").
        session_start = hooks_block["SessionStart"]
        # Render command appears exactly twice (one per matcher variant).
        assert _count_command(session_start, _RENDER_HOOK_COMMAND) == 2
        # And one matcher-less render entry, one matcher:"clear" render entry.
        matchers_with_render = [
            entry.get("matcher", "")
            for entry in session_start
            if isinstance(entry, dict)
            and any(h.get("command") == _RENDER_HOOK_COMMAND for h in entry.get("hooks", []))
        ]
        assert "" in matchers_with_render
        assert "clear" in matchers_with_render

        # UserPromptSubmit, Notification, Stop — each one matcher-less render entry.
        for event_name in ("UserPromptSubmit", "Notification", "Stop"):
            event_entries = hooks_block[event_name]
            assert _count_command(event_entries, _RENDER_HOOK_COMMAND) == 1
            # The single entry is matcher-less.
            assert event_entries[0].get("matcher", "") == ""

        # PreToolUse: matcher="AskUserQuestion" + render command.
        pre_tool_use = hooks_block["PreToolUse"]
        assert _count_command(pre_tool_use, _RENDER_HOOK_COMMAND) == 1
        pre_ask_entries = [
            entry
            for entry in pre_tool_use
            if isinstance(entry, dict) and entry.get("matcher") == "AskUserQuestion"
        ]
        assert len(pre_ask_entries) == 1

        # PostToolUse: matcher="AskUserQuestion" AND matcher="Bash" render entries.
        post_tool_use = hooks_block["PostToolUse"]
        assert _count_command(post_tool_use, _RENDER_HOOK_COMMAND) == 2
        post_matchers = {
            entry.get("matcher")
            for entry in post_tool_use
            if isinstance(entry, dict)
            and any(h.get("command") == _RENDER_HOOK_COMMAND for h in entry.get("hooks", []))
        }
        assert post_matchers == {"AskUserQuestion", "Bash"}

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
            "PostToolUse:AskUserQuestion",
            "PostToolUse:Bash",
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
        (SessionStart still has exactly two — matcher-less + clear)."""
        target = tmp_path / ".claude" / "settings.local.json"
        rt.project_install_hook(str(target))
        rt.project_install_hook(str(target))

        settings = json.loads(target.read_text())
        hooks_block = settings["hooks"]
        assert _count_command(hooks_block["SessionStart"], _RENDER_HOOK_COMMAND) == 2
        for event_name in ("UserPromptSubmit", "Notification", "Stop", "PreToolUse"):
            assert _count_command(hooks_block[event_name], _RENDER_HOOK_COMMAND) == 1
        # PostToolUse carries two render entries (AskUserQuestion + Bash).
        assert _count_command(hooks_block["PostToolUse"], _RENDER_HOOK_COMMAND) == 2

    # ------------------------------------------------------------------
    # (b2) New D1 entries: PreToolUse:AskUserQuestion + PostToolUse:Bash.
    # ------------------------------------------------------------------

    def test_fresh_install_adds_pre_and_post_bash_entries(self, rt, tmp_path):
        """A fresh install adds the PreToolUse:AskUserQuestion and PostToolUse:Bash render
        entries and reports them with matcher-qualified labels in installed_events."""
        target = tmp_path / ".claude" / "settings.local.json"
        result = _parsed(rt.project_install_hook(str(target)))
        assert result["status"] == "success"
        installed = set(result["installed_events"])
        assert "PreToolUse:AskUserQuestion" in installed
        assert "PostToolUse:AskUserQuestion" in installed
        assert "PostToolUse:Bash" in installed

        settings = json.loads(target.read_text())
        hooks_block = settings["hooks"]
        # PreToolUse has exactly one AskUserQuestion render entry.
        pre = hooks_block["PreToolUse"]
        assert _count_command(pre, _RENDER_HOOK_COMMAND) == 1
        assert pre[0].get("matcher") == "AskUserQuestion"
        # PostToolUse has exactly two render entries (AskUserQuestion + Bash).
        assert _count_command(hooks_block["PostToolUse"], _RENDER_HOOK_COMMAND) == 2

    def test_pre_and_post_bash_entries_dedup_idempotent(self, rt, tmp_path):
        """Re-invoking after a fresh install reports the PreToolUse:AskUserQuestion,
        PostToolUse:AskUserQuestion, and PostToolUse:Bash render entries as already-present
        and does not duplicate them."""
        target = tmp_path / ".claude" / "settings.local.json"
        rt.project_install_hook(str(target))

        result = _parsed(rt.project_install_hook(str(target)))
        already = set(result["already_present_events"])
        assert "PreToolUse:AskUserQuestion" in already
        assert "PostToolUse:AskUserQuestion" in already
        assert "PostToolUse:Bash" in already
        # Nothing fresh installed on the second run.
        assert result["installed_events"] == []

        settings = json.loads(target.read_text())
        hooks_block = settings["hooks"]
        assert _count_command(hooks_block["PreToolUse"], _RENDER_HOOK_COMMAND) == 1
        assert _count_command(hooks_block["PostToolUse"], _RENDER_HOOK_COMMAND) == 2

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
        # Render entries (matcher-less + clear) added without disturbing the capture entry.
        assert _count_command(session_start, _RENDER_HOOK_COMMAND) == 2

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

        monkeypatch.setattr(_cr, "_SESSION_CACHE_BASE", tmp_path / "sessions")
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

        monkeypatch.setattr(_cr, "_SESSION_CACHE_BASE", tmp_path / "sessions")
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
        "SessionStart:clear",
        "UserPromptSubmit",
        "Notification",
        "Stop",
        "PreToolUse:AskUserQuestion",
        "PostToolUse:AskUserQuestion",
        "PostToolUse:Bash",
        "statusLine",
        "env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE",
    )

    def test_display_healthy_when_fully_wired(self, rt, tmp_path, monkeypatch):
        """display check is healthy when every required entry is present.

        A fresh project install-hook writes the complete wiring; the display
        check must then report every label as ``present`` and ``healthy: true``.
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
        assert "MISSING" not in detail

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
            "SessionStart:clear",
            "UserPromptSubmit",
            "Notification",
            "Stop",
            "PreToolUse:AskUserQuestion",
            "PostToolUse:AskUserQuestion",
            "PostToolUse:Bash",
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
