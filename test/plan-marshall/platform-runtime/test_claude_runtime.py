#!/usr/bin/env python3
"""Tests for claude_runtime.py — ClaudeRuntime implementation of all 14 operations.

Covers every method defined by the Runtime ABC:
  1.  project_initial_setup       — creates dirs, writes marshal.json, installs hook
  2.  session_capture             — reads $CLAUDE_CODE_SESSION_ID, stores via manage-status
  3.  session_configure_display   — writes / removes claude_pre_prompt.js
  4.  session_render_title        — resolves session → plan → OSC emit
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
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# conftest.py sets up PYTHONPATH so cross-skill imports resolve without manual
# sys.path manipulation.
from claude_runtime import ClaudeRuntime, _HOOK_COMMAND  # type: ignore[import-not-found]
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
# 3. session_configure_display
# =============================================================================


class TestSessionConfigureDisplay:
    """Tests for ClaudeRuntime.session_configure_display."""

    def test_invalid_type_returns_error(self, rt):
        """An unknown display_type returns status=error."""
        result = _parsed(rt.session_configure_display("invalid-type", "unicode"))
        assert result["status"] == "error"
        assert result["error"] == "invalid_type"

    def test_invalid_style_returns_error(self, rt):
        """An unknown style returns status=error."""
        result = _parsed(rt.session_configure_display("terminal-title", "bold"))
        assert result["status"] == "error"
        assert result["error"] == "invalid_style"

    def test_none_type_removes_hook_file(self, rt, tmp_path, monkeypatch):
        """display_type='none' removes the hook file when it exists."""
        hook_file = tmp_path / ".claude" / "claude_pre_prompt.js"
        hook_file.parent.mkdir(parents=True, exist_ok=True)
        hook_file.write_text("existing content", encoding="utf-8")
        # Run from tmp_path so relative paths resolve there.
        monkeypatch.chdir(tmp_path)
        result = _parsed(rt.session_configure_display("none", "unicode"))
        assert result["status"] == "success"
        assert result["written"] is False
        assert not hook_file.exists()

    def test_terminal_title_writes_hook_file(self, rt, tmp_path, monkeypatch):
        """terminal-title type writes claude_pre_prompt.js."""
        monkeypatch.chdir(tmp_path)
        result = _parsed(rt.session_configure_display("terminal-title", "unicode"))
        assert result["status"] == "success"
        assert result["written"] is True
        hook_file = tmp_path / ".claude" / "claude_pre_prompt.js"
        assert hook_file.is_file()
        content = hook_file.read_text(encoding="utf-8")
        assert "render-title" in content

    def test_status_line_type_writes_hook_file(self, rt, tmp_path, monkeypatch):
        """status-line type is valid and writes the hook file."""
        monkeypatch.chdir(tmp_path)
        result = _parsed(rt.session_configure_display("status-line", "ascii"))
        assert result["status"] == "success"

    def test_response_includes_hook_file_path(self, rt, tmp_path, monkeypatch):
        """Response includes hook_file, type, and style fields."""
        monkeypatch.chdir(tmp_path)
        result = _parsed(rt.session_configure_display("terminal-title", "ascii"))
        assert "hook_file" in result
        assert result["type"] == "terminal-title"
        assert result["style"] == "ascii"


# =============================================================================
# 4. session_render_title
# =============================================================================


class TestSessionRenderTitle:
    """Tests for ClaudeRuntime.session_render_title."""

    def test_missing_session_id_env_returns_noop(self, rt, monkeypatch):
        """When $CLAUDE_CODE_SESSION_ID is unset, render_title returns no-op."""
        monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
        result = _parsed(rt.session_render_title())
        assert result["status"] == "no-op"

    def test_no_active_plan_returns_noop(self, rt, tmp_path, monkeypatch):
        """When session has no registered plan, render_title returns no-op."""
        import claude_runtime as _cr

        monkeypatch.setattr(_cr, "_SESSION_CACHE_BASE", tmp_path / "sessions")
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-without-plan")
        result = _parsed(rt.session_render_title())
        assert result["status"] == "no-op"

    def test_no_title_body_file_returns_noop(self, rt, tmp_path, monkeypatch):
        """When title-body.txt does not exist, render_title returns no-op."""
        import claude_runtime as _cr

        session_id = "sess-with-plan"
        plan_id = "my-plan"
        cache_dir = tmp_path / "sessions" / session_id
        cache_dir.mkdir(parents=True)
        (cache_dir / "active-plan").write_text(plan_id, encoding="utf-8")

        monkeypatch.setattr(_cr, "_SESSION_CACHE_BASE", tmp_path / "sessions")
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", session_id)
        monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.chdir(tmp_path)

        result = _parsed(rt.session_render_title())
        assert result["status"] == "no-op"

    def test_emits_osc_sequence_on_success(self, rt, tmp_path, monkeypatch):
        """When session → plan → title-body chain resolves, render_title emits OSC and returns success."""
        import claude_runtime as _cr

        session_id = "sess-full"
        plan_id = "active-plan"
        title_body = "phase-5-execute | my-task"

        # Set up session cache.
        cache_dir = tmp_path / "sessions" / session_id
        cache_dir.mkdir(parents=True)
        (cache_dir / "active-plan").write_text(plan_id, encoding="utf-8")

        # Set up title-body.txt in .plan/local/plans/{plan_id}/.
        plan_titles_dir = tmp_path / ".plan" / "local" / "plans" / plan_id
        plan_titles_dir.mkdir(parents=True)
        (plan_titles_dir / "title-body.txt").write_text(title_body, encoding="utf-8")

        monkeypatch.setattr(_cr, "_SESSION_CACHE_BASE", tmp_path / "sessions")
        monkeypatch.setattr(_cr, "_PLAN_DIR_NAME", ".plan")
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", session_id)
        monkeypatch.chdir(tmp_path)

        result = _parsed(rt.session_render_title())
        assert result["status"] == "success"
        assert result["plan_id"] == plan_id
        assert result["title_body"] == title_body


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

    def test_display_healthy_when_hook_file_present(self, rt, tmp_path, monkeypatch):
        """display check is healthy when .claude/claude_pre_prompt.js exists."""
        hook_file = tmp_path / ".claude" / "claude_pre_prompt.js"
        hook_file.parent.mkdir(parents=True)
        hook_file.write_text("// hook", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        result = _parsed(rt.health_check("display"))
        display_result = next(r for r in result["results"] if r["check"] == "display")
        assert display_result["healthy"] is True

    def test_display_unhealthy_when_hook_file_absent(self, rt, tmp_path, monkeypatch):
        """display check is unhealthy when claude_pre_prompt.js does not exist."""
        monkeypatch.chdir(tmp_path)
        result = _parsed(rt.health_check("display"))
        display_result = next(r for r in result["results"] if r["check"] == "display")
        assert display_result["healthy"] is False

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

    def test_all_healthy_reflects_individual_results(self, rt, tmp_path, monkeypatch):
        """all_healthy is False when any single check is unhealthy."""
        import claude_runtime as _cr

        # No settings file → permissions check fails.
        fake_settings = tmp_path / "nonexistent_settings.json"
        monkeypatch.setattr(_cr, "_claude_project_settings_path", lambda *_: fake_settings)
        monkeypatch.chdir(tmp_path)

        result = _parsed(rt.health_check("permissions"))
        assert result["all_healthy"] is False
