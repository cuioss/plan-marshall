#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for platform_runtime.py — router dispatch logic.

Covers:
  - _build_operation: operation token parsing from argv
  - _read_marshal: marshal.json lookup (project_dir path and cwd-walk)
  - _resolve_target: runtime.target extraction from marshal data
  - _make_runtime: registry lookup and unknown target handling
  - _parse_json_list / _parse_context: JSON helpers
  - _dispatch: correct routing and argparse for all 21 operations
  - main: full integration — no args, missing marshal, unknown target, dispatch
"""
from __future__ import annotations  # noqa: I001

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# conftest.py sets up PYTHONPATH so cross-skill imports resolve without
# manual sys.path manipulation.
from platform_runtime import (
    _build_operation,
    _dispatch,
    _make_runtime,
    _parse_context,
    _parse_json_list,
    _read_marshal,
    _resolve_target,
    main,
)
from runtime_base import toon_success
from toon_parser import parse_toon


# =============================================================================
# Helpers
# =============================================================================


def _parsed(output: str) -> dict[str, Any]:
    """Parse TOON output and return the result dict."""
    return parse_toon(output)


def _make_marshal_file(directory: Path, target: str = "claude") -> Path:
    """Write a minimal .plan/marshal.json and return its path."""
    plan_dir = directory / ".plan"
    plan_dir.mkdir(parents=True, exist_ok=True)
    marshal_path = plan_dir / "marshal.json"
    marshal_path.write_text(json.dumps({"runtime": {"target": target}}), encoding="utf-8")
    return marshal_path


def _mock_runtime() -> MagicMock:
    """Return a MagicMock that returns valid TOON for every Runtime method."""
    rt = MagicMock()
    rt.project_initial_setup.return_value = toon_success("project initial-setup")
    rt.project_install_hook.return_value = toon_success("project install-hook")
    rt.session_capture.return_value = toon_success("session capture")
    rt.session_render_title.return_value = toon_success("session render-title")
    rt.session_push_title_token.return_value = toon_success("session push-title-token")
    rt.session_bind.return_value = toon_success("session bind")
    rt.session_resolve_plan.return_value = toon_success("session resolve-plan")
    rt.session_doctor.return_value = toon_success("session doctor")
    rt.permission_configure.return_value = toon_success("permission configure")
    rt.permission_analyze.return_value = toon_success("permission analyze")
    rt.permission_fix.return_value = toon_success("permission fix")
    rt.permission_ensure_wildcards.return_value = toon_success("permission ensure-wildcards")
    rt.permission_ensure_steps.return_value = toon_success("permission ensure-steps")
    rt.permission_web_analyze.return_value = toon_success("permission web-analyze")
    rt.permission_web_apply.return_value = toon_success("permission web-apply")
    rt.metrics_capture.return_value = toon_success("metrics capture")
    rt.subagent_dispatch.return_value = toon_success("subagent dispatch")
    rt.health_check.return_value = toon_success("health-check")
    return rt


# =============================================================================
# Test: _build_operation
# =============================================================================


class TestBuildOperation:
    """Tests for the argv-to-operation parser."""

    def test_empty_argv_returns_empty_operation(self):
        """Empty argv produces an empty operation string and no remaining args."""
        op, remaining = _build_operation([])
        assert op == ""
        assert remaining == []

    def test_health_check_is_single_token(self):
        """health-check is recognized as a single-token operation."""
        op, remaining = _build_operation(["health-check", "--checks", "all"])
        assert op == "health-check"
        assert remaining == ["--checks", "all"]

    def test_two_token_operation_project_initial_setup(self):
        """project initial-setup produces the two-word operation string."""
        op, remaining = _build_operation(["project", "initial-setup", "--project-dir", "."])
        assert op == "project initial-setup"
        assert remaining == ["--project-dir", "."]

    def test_two_token_operation_session_capture(self):
        """session capture operation is parsed correctly."""
        op, remaining = _build_operation(["session", "capture", "--plan-id", "my-plan"])
        assert op == "session capture"
        assert remaining == ["--plan-id", "my-plan"]

    def test_two_token_operation_permission_web_apply(self):
        """permission web-apply operation is parsed correctly."""
        op, remaining = _build_operation(
            ["permission", "web-apply", "--scope", "project", "--dry-run"]
        )
        assert op == "permission web-apply"
        assert remaining == ["--scope", "project", "--dry-run"]

    def test_two_token_operation_metrics_capture(self):
        """metrics capture operation is parsed correctly."""
        op, remaining = _build_operation(["metrics", "capture", "--plan-id", "p1", "--phase", "p1"])
        assert op == "metrics capture"
        assert remaining == ["--plan-id", "p1", "--phase", "p1"]

    def test_two_token_operation_subagent_dispatch(self):
        """subagent dispatch operation is parsed correctly."""
        op, remaining = _build_operation(["subagent", "dispatch", "--agent", "my-agent"])
        assert op == "subagent dispatch"
        assert remaining == ["--agent", "my-agent"]

    def test_single_unknown_token_returns_token_as_operation(self):
        """A single unrecognized token is returned as the operation with no remaining."""
        op, remaining = _build_operation(["unknown-op"])
        assert op == "unknown-op"
        assert remaining == []

    def test_all_standard_groups_produce_two_part_operations(self):
        """All documented operation groups produce two-part identifiers."""
        groups = [
            ("session", "render-title"),
            ("session", "push-title-token"),
            ("session", "bind"),
            ("session", "resolve-plan"),
            ("session", "doctor"),
            ("permission", "configure"),
            ("permission", "analyze"),
            ("permission", "fix"),
            ("permission", "ensure-wildcards"),
            ("permission", "ensure-steps"),
            ("permission", "web-analyze"),
        ]
        for group, subcommand in groups:
            op, _ = _build_operation([group, subcommand])
            assert op == f"{group} {subcommand}", f"Failed for {group} {subcommand}"


# =============================================================================
# Test: _read_marshal
# =============================================================================


class TestReadMarshal:
    """Tests for the marshal.json loader."""

    def test_reads_marshal_from_explicit_project_dir(self, tmp_path):
        """_read_marshal returns parsed dict when project_dir contains .plan/marshal.json."""
        _make_marshal_file(tmp_path, "claude")
        result = _read_marshal(str(tmp_path))
        assert result is not None
        assert result["runtime"]["target"] == "claude"

    def test_returns_none_when_project_dir_has_no_marshal(self, tmp_path):
        """_read_marshal returns None when marshal.json is absent in project_dir."""
        result = _read_marshal(str(tmp_path))
        assert result is None

    def test_returns_none_for_malformed_json_in_project_dir(self, tmp_path):
        """_read_marshal returns None when marshal.json contains malformed JSON."""
        plan_dir = tmp_path / ".plan"
        plan_dir.mkdir()
        (plan_dir / "marshal.json").write_text("{ not valid json }", encoding="utf-8")
        result = _read_marshal(str(tmp_path))
        assert result is None

    def test_returns_none_when_marshal_is_not_dict(self, tmp_path):
        """_read_marshal returns None when marshal.json root is not a JSON object."""
        plan_dir = tmp_path / ".plan"
        plan_dir.mkdir()
        (plan_dir / "marshal.json").write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        result = _read_marshal(str(tmp_path))
        assert result is None

    def test_cwd_walk_finds_marshal_in_parent(self, tmp_path, monkeypatch):
        """Without project_dir, _read_marshal walks up from cwd to find marshal.json."""
        _make_marshal_file(tmp_path, "opencode")
        # Change cwd to a sub-directory so the walk must climb.
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        monkeypatch.chdir(nested)
        result = _read_marshal(None)
        assert result is not None
        assert result["runtime"]["target"] == "opencode"

    def test_cwd_walk_returns_none_when_no_marshal_found(self, tmp_path, monkeypatch):
        """_read_marshal returns None when marshal.json is absent in the entire ancestry."""
        monkeypatch.chdir(tmp_path)
        result = _read_marshal(None)
        assert result is None


# =============================================================================
# Test: _resolve_target
# =============================================================================


class TestResolveTarget:
    """Tests for target extraction from marshal data."""

    def test_extracts_target_from_valid_marshal(self):
        """_resolve_target returns the target string from runtime.target."""
        data = {"runtime": {"target": "claude"}}
        assert _resolve_target(data) == "claude"

    def test_returns_none_when_runtime_key_missing(self):
        """_resolve_target returns None when 'runtime' key is absent."""
        assert _resolve_target({}) is None

    def test_returns_none_when_runtime_is_not_dict(self):
        """_resolve_target returns None when 'runtime' value is not a dict."""
        assert _resolve_target({"runtime": "claude"}) is None

    def test_returns_none_when_target_key_missing(self):
        """_resolve_target returns None when 'target' key is absent in runtime."""
        assert _resolve_target({"runtime": {}}) is None

    def test_returns_none_when_target_is_empty_string(self):
        """_resolve_target returns None when target is an empty string."""
        assert _resolve_target({"runtime": {"target": ""}}) is None

    def test_returns_string_for_non_string_target(self):
        """_resolve_target coerces non-string target to str."""
        result = _resolve_target({"runtime": {"target": 42}})
        assert result == "42"

    def test_opencode_target(self):
        """_resolve_target correctly extracts the 'opencode' target."""
        assert _resolve_target({"runtime": {"target": "opencode"}}) == "opencode"


# =============================================================================
# Test: _make_runtime
# =============================================================================


class TestMakeRuntime:
    """Tests for the registry lookup."""

    def test_claude_target_returns_claude_runtime(self):
        """_make_runtime('claude') returns a ClaudeRuntime instance."""
        from claude_runtime import ClaudeRuntime

        runtime = _make_runtime("claude")
        assert runtime is not None
        assert isinstance(runtime, ClaudeRuntime)

    def test_opencode_target_returns_opencode_runtime(self):
        """_make_runtime('opencode') returns an OpenCodeRuntime instance."""
        from opencode_runtime import OpenCodeRuntime

        runtime = _make_runtime("opencode")
        assert runtime is not None
        assert isinstance(runtime, OpenCodeRuntime)

    def test_unknown_target_returns_none(self):
        """_make_runtime returns None for unrecognized target strings."""
        assert _make_runtime("unknown") is None
        assert _make_runtime("") is None
        assert _make_runtime("CLAUDE") is None  # case-sensitive


# =============================================================================
# Test: _parse_json_list
# =============================================================================


class TestParseJsonList:
    """Tests for the JSON-array argument helper."""

    def test_parses_empty_array(self):
        """_parse_json_list parses an empty JSON array."""
        assert _parse_json_list("[]") == []

    def test_parses_string_array(self):
        """_parse_json_list parses a JSON array of strings."""
        result = _parse_json_list('["Read(**)", "Write(.plan/**)"]')
        assert result == ["Read(**)", "Write(.plan/**)"]

    def test_coerces_non_strings_to_str(self):
        """_parse_json_list coerces non-string elements to str."""
        result = _parse_json_list("[1, 2, 3]")
        assert result == ["1", "2", "3"]

    def test_raises_on_non_array_json(self):
        """_parse_json_list raises ValueError for a non-array JSON value."""
        with pytest.raises(ValueError, match="expected JSON array"):
            _parse_json_list('{"key": "value"}')

    def test_raises_on_invalid_json(self):
        """_parse_json_list raises json.JSONDecodeError for malformed input."""
        import json as _json

        with pytest.raises(_json.JSONDecodeError):
            _parse_json_list("not json")


# =============================================================================
# Test: _parse_context
# =============================================================================


class TestParseContext:
    """Tests for the JSON-object argument helper."""

    def test_parses_valid_object(self):
        """_parse_context returns a dict for a valid JSON object."""
        result = _parse_context('{"key": "value", "count": 3}')
        assert result == {"key": "value", "count": 3}

    def test_raises_on_non_object_json(self):
        """_parse_context raises ValueError for a JSON array."""
        with pytest.raises(ValueError, match="expected JSON object"):
            _parse_context("[1, 2, 3]")

    def test_raises_on_invalid_json(self):
        """_parse_context raises json.JSONDecodeError for malformed input."""
        import json as _json

        with pytest.raises(_json.JSONDecodeError):
            _parse_context("not json")


# =============================================================================
# Test: _dispatch — all 21 operations
# =============================================================================


class TestDispatch:
    """Tests that _dispatch correctly routes each operation to the right runtime method."""

    @pytest.fixture()
    def rt(self):
        """Mock runtime with TOON success stubs."""
        return _mock_runtime()

    # ---- project initial-setup ------------------------------------------------

    def test_dispatch_project_initial_setup(self, rt):
        """project initial-setup passes project_dir and target to runtime."""
        _dispatch(rt, "project initial-setup", ["--project-dir", "/tmp/proj", "--target", "claude"])
        rt.project_initial_setup.assert_called_once_with("/tmp/proj", "claude")

    def test_dispatch_project_initial_setup_defaults(self, rt):
        """project initial-setup uses '.' and 'claude' as defaults."""
        _dispatch(rt, "project initial-setup", [])
        rt.project_initial_setup.assert_called_once_with(".", "claude")

    # ---- project install-hook -------------------------------------------------

    def test_dispatch_project_install_hook(self, rt):
        """project install-hook forwards --target and overwrite flags to runtime.project_install_hook."""
        _dispatch(rt, "project install-hook", ["--target", ".claude/settings.local.json"])
        rt.project_install_hook.assert_called_once_with(
            ".claude/settings.local.json",
            overwrite_statusline=False,
            overwrite_env_disable=False,
            enforcement=False,
        )

    def test_dispatch_project_install_hook_with_overwrite_flags(self, rt):
        """project install-hook forwards both overwrite flags when supplied."""
        _dispatch(
            rt,
            "project install-hook",
            [
                "--target",
                ".claude/settings.local.json",
                "--overwrite-statusline",
                "--overwrite-env-disable",
            ],
        )
        rt.project_install_hook.assert_called_once_with(
            ".claude/settings.local.json",
            overwrite_statusline=True,
            overwrite_env_disable=True,
            enforcement=False,
        )

    def test_dispatch_project_install_hook_with_enforcement_flag(self, rt):
        """project install-hook forwards enforcement=True when --enforcement is supplied."""
        _dispatch(
            rt,
            "project install-hook",
            ["--target", ".claude/settings.local.json", "--enforcement"],
        )
        rt.project_install_hook.assert_called_once_with(
            ".claude/settings.local.json",
            overwrite_statusline=False,
            overwrite_env_disable=False,
            enforcement=True,
        )

    def test_dispatch_project_install_hook_missing_target_rejected(self, rt):
        """project install-hook without --target is rejected by argparse (SystemExit)."""
        with pytest.raises(SystemExit):
            _dispatch(rt, "project install-hook", [])
        rt.project_install_hook.assert_not_called()

    # ---- session capture ------------------------------------------------------

    def test_dispatch_session_capture(self, rt):
        """session capture forwards --plan-id to runtime."""
        _dispatch(rt, "session capture", ["--plan-id", "my-plan"])
        rt.session_capture.assert_called_once_with("my-plan")

    # ---- session render-title -------------------------------------------------

    def test_dispatch_session_render_title(self, rt):
        """session render-title defaults to statusline=False."""
        _dispatch(rt, "session render-title", [])
        rt.session_render_title.assert_called_once_with(statusline=False)

    def test_dispatch_session_render_title_with_statusline(self, rt):
        """session render-title --statusline forwards statusline=True."""
        _dispatch(rt, "session render-title", ["--statusline"])
        rt.session_render_title.assert_called_once_with(statusline=True)

    # ---- session push-title-token --------------------------------------------

    def test_dispatch_session_push_title_token(self, rt):
        """session push-title-token forwards --plan-id and --icon to runtime."""
        _dispatch(
            rt,
            "session push-title-token",
            ["--plan-id", "my-plan", "--icon", "⏳"],
        )
        rt.session_push_title_token.assert_called_once_with("my-plan", "⏳", store="plans", slug=None)

    def test_dispatch_session_push_title_token_icon_optional(self, rt):
        """session push-title-token without --icon forwards icon=None (plain repaint)."""
        _dispatch(rt, "session push-title-token", ["--plan-id", "my-plan"])
        rt.session_push_title_token.assert_called_once_with("my-plan", None, store="plans", slug=None)

    # ---- session bind ---------------------------------------------------------

    def test_dispatch_session_bind(self, rt):
        """session bind forwards --plan-id and --session-id to runtime."""
        _dispatch(
            rt,
            "session bind",
            ["--plan-id", "my-plan", "--session-id", "sess-1"],
        )
        rt.session_bind.assert_called_once_with("my-plan", "sess-1")

    def test_dispatch_session_bind_session_id_optional(self, rt):
        """session bind without --session-id forwards session_id=None (env fallback)."""
        _dispatch(rt, "session bind", ["--plan-id", "my-plan"])
        rt.session_bind.assert_called_once_with("my-plan", None)

    def test_dispatch_session_bind_missing_plan_id_rejected(self, rt):
        """session bind without --plan-id is rejected by argparse (SystemExit)."""
        with pytest.raises(SystemExit):
            _dispatch(rt, "session bind", [])
        rt.session_bind.assert_not_called()

    # ---- session resolve-plan -------------------------------------------------

    def test_dispatch_session_resolve_plan(self, rt):
        """session resolve-plan forwards --session-id to runtime."""
        _dispatch(rt, "session resolve-plan", ["--session-id", "sess-1"])
        rt.session_resolve_plan.assert_called_once_with("sess-1")

    def test_dispatch_session_resolve_plan_session_id_optional(self, rt):
        """session resolve-plan without --session-id forwards session_id=None."""
        _dispatch(rt, "session resolve-plan", [])
        rt.session_resolve_plan.assert_called_once_with(None)

    # ---- session doctor -------------------------------------------------------

    def test_dispatch_session_doctor(self, rt):
        """session doctor without --fix forwards fix=False."""
        _dispatch(rt, "session doctor", [])
        rt.session_doctor.assert_called_once_with(False)

    def test_dispatch_session_doctor_fix(self, rt):
        """session doctor --fix forwards fix=True."""
        _dispatch(rt, "session doctor", ["--fix"])
        rt.session_doctor.assert_called_once_with(True)

    # ---- permission configure -------------------------------------------------

    def test_dispatch_permission_configure(self, rt):
        """permission configure forwards --scope and --permissions to runtime."""
        _dispatch(
            rt,
            "permission configure",
            ["--scope", "project", "--permissions", "Read(**)", "Write(.plan/**)"],
        )
        rt.permission_configure.assert_called_once_with("project", ["Read(**)", "Write(.plan/**)"])

    # ---- permission analyze ---------------------------------------------------

    def test_dispatch_permission_analyze(self, rt):
        """permission analyze forwards scope, checks list, and marshal path to runtime."""
        _dispatch(
            rt,
            "permission analyze",
            ["--scope", "both", "--checks", "redundant,missing-steps", "--marshal", "/tmp/m.json"],
        )
        rt.permission_analyze.assert_called_once_with(
            "both", ["redundant", "missing-steps"], "/tmp/m.json"
        )

    def test_dispatch_permission_analyze_no_marshal(self, rt):
        """permission analyze without --marshal passes None as marshal_path."""
        _dispatch(rt, "permission analyze", ["--scope", "global", "--checks", "all"])
        rt.permission_analyze.assert_called_once_with("global", ["all"], None)

    # ---- permission fix -------------------------------------------------------

    def test_dispatch_permission_fix_normalize(self, rt):
        """permission fix normalize forwards scope, operation, empty permissions, dry_run=False."""
        _dispatch(
            rt,
            "permission fix",
            ["--scope", "project", "--operation", "normalize"],
        )
        rt.permission_fix.assert_called_once_with("project", "normalize", [], False)

    def test_dispatch_permission_fix_add_dry_run(self, rt):
        """permission fix add with --dry-run forwards permissions and dry_run=True."""
        _dispatch(
            rt,
            "permission fix",
            ["--scope", "global", "--operation", "add", "--permissions", "Read(**)", "--dry-run"],
        )
        rt.permission_fix.assert_called_once_with("global", "add", ["Read(**)"], True)

    # ---- permission ensure-wildcards ------------------------------------------

    def test_dispatch_permission_ensure_wildcards(self, rt):
        """permission ensure-wildcards forwards scope, marketplace_dir, dry_run to runtime."""
        _dispatch(
            rt,
            "permission ensure-wildcards",
            ["--scope", "project", "--marketplace-dir", "mktplace/", "--dry-run"],
        )
        rt.permission_ensure_wildcards.assert_called_once_with("project", "mktplace/", True)

    def test_dispatch_permission_ensure_wildcards_defaults(self, rt):
        """permission ensure-wildcards uses 'marketplace/' as default marketplace-dir."""
        _dispatch(rt, "permission ensure-wildcards", ["--scope", "global"])
        rt.permission_ensure_wildcards.assert_called_once_with("global", "marketplace/", False)

    # ---- permission ensure-steps ----------------------------------------------

    def test_dispatch_permission_ensure_steps(self, rt):
        """permission ensure-steps forwards marshal path, scope, and dry_run to runtime."""
        _dispatch(
            rt,
            "permission ensure-steps",
            ["--marshal", ".plan/marshal.json", "--scope", "project"],
        )
        rt.permission_ensure_steps.assert_called_once_with(".plan/marshal.json", "project", False)

    # ---- permission web-analyze -----------------------------------------------

    def test_dispatch_permission_web_analyze(self, rt):
        """permission web-analyze forwards scope to runtime."""
        _dispatch(rt, "permission web-analyze", ["--scope", "both"])
        rt.permission_web_analyze.assert_called_once_with("both")

    # ---- permission web-apply -------------------------------------------------

    def test_dispatch_permission_web_apply_defaults(self, rt):
        """permission web-apply with only --scope uses empty add/remove lists."""
        _dispatch(rt, "permission web-apply", ["--scope", "project"])
        rt.permission_web_apply.assert_called_once_with("project", [], [], False)

    def test_dispatch_permission_web_apply_with_lists(self, rt):
        """permission web-apply parses --add and --remove JSON arrays."""
        _dispatch(
            rt,
            "permission web-apply",
            [
                "--scope", "global",
                "--add", '["example.com"]',
                "--remove", '["old.com"]',
            ],
        )
        rt.permission_web_apply.assert_called_once_with("global", ["example.com"], ["old.com"], False)

    def test_dispatch_permission_web_apply_invalid_add_returns_error(self, rt):
        """permission web-apply with non-array --add returns TOON error instead of raising."""
        result = _dispatch(
            rt,
            "permission web-apply",
            ["--scope", "project", "--add", '{"bad": "input"}'],
        )
        parsed = _parsed(result)
        assert parsed["status"] == "error"
        assert "invalid_argument" in parsed.get("error", "")
        rt.permission_web_apply.assert_not_called()

    # ---- metrics capture ------------------------------------------------------

    def test_dispatch_metrics_capture(self, rt):
        """metrics capture forwards plan_id, phase, and total_tokens to runtime."""
        _dispatch(
            rt,
            "metrics capture",
            ["--plan-id", "my-plan", "--phase", "phase-1-init", "--total-tokens", "5000"],
        )
        rt.metrics_capture.assert_called_once_with("my-plan", "phase-1-init", 5000)

    def test_dispatch_metrics_capture_no_tokens(self, rt):
        """metrics capture without --total-tokens passes None."""
        _dispatch(rt, "metrics capture", ["--plan-id", "p", "--phase", "ph"])
        rt.metrics_capture.assert_called_once_with("p", "ph", None)

    # ---- subagent dispatch ----------------------------------------------------

    def test_dispatch_subagent_dispatch_minimal(self, rt):
        """subagent dispatch with only --agent passes None for prompt_file and context."""
        _dispatch(rt, "subagent dispatch", ["--agent", "execution-context"])
        rt.subagent_dispatch.assert_called_once_with("execution-context", None, None)

    def test_dispatch_subagent_dispatch_with_context(self, rt):
        """subagent dispatch parses --context JSON object."""
        _dispatch(
            rt,
            "subagent dispatch",
            ["--agent", "my-agent", "--context", '{"plan_id": "p1"}'],
        )
        rt.subagent_dispatch.assert_called_once_with("my-agent", None, {"plan_id": "p1"})

    def test_dispatch_subagent_dispatch_invalid_context_returns_error(self, rt):
        """subagent dispatch with non-object --context returns TOON error."""
        result = _dispatch(
            rt,
            "subagent dispatch",
            ["--agent", "my-agent", "--context", "[1, 2]"],
        )
        parsed = _parsed(result)
        assert parsed["status"] == "error"
        assert "invalid_argument" in parsed.get("error", "")
        rt.subagent_dispatch.assert_not_called()

    def test_dispatch_subagent_dispatch_with_prompt_file(self, rt):
        """subagent dispatch forwards --prompt-file to runtime."""
        _dispatch(
            rt,
            "subagent dispatch",
            ["--agent", "my-agent", "--prompt-file", "/tmp/prompt.md"],
        )
        rt.subagent_dispatch.assert_called_once_with("my-agent", "/tmp/prompt.md", None)

    # ---- health-check ---------------------------------------------------------

    def test_dispatch_health_check(self, rt):
        """health-check forwards --checks to runtime."""
        _dispatch(rt, "health-check", ["--checks", "all"])
        rt.health_check.assert_called_once_with("all")

    def test_dispatch_health_check_specific_checks(self, rt):
        """health-check forwards specific comma-separated checks to runtime."""
        _dispatch(rt, "health-check", ["--checks", "permissions,display"])
        rt.health_check.assert_called_once_with("permissions,display")

    # ---- unknown operation ----------------------------------------------------

    def test_dispatch_unknown_operation_returns_toon_error(self, rt):
        """An unrecognized operation returns a TOON error without calling the runtime."""
        result = _dispatch(rt, "not-a-real-operation", [])
        parsed = _parsed(result)
        assert parsed["status"] == "error"
        assert "unknown_operation" in parsed.get("error", "")
        # No runtime methods should have been called.
        rt.project_initial_setup.assert_not_called()
        rt.session_capture.assert_not_called()


# =============================================================================
# Test: main — full integration
# =============================================================================


class TestMain:
    """Integration tests for the main() entry point."""

    def test_main_no_args_returns_1(self, capsys):
        """main() with no arguments prints usage to stderr and returns exit code 1."""
        code = main([])
        assert code == 1
        captured = capsys.readouterr()
        assert "usage" in captured.err.lower() or "platform_runtime" in captured.err.lower()

    def test_main_missing_marshal_returns_0_with_toon_error(self, tmp_path, monkeypatch, capsys):
        """main() with non-project-initial-setup op and no marshal prints TOON error, exit 0."""
        # Change cwd to a directory with no marshal.json anywhere in its ancestry.
        monkeypatch.chdir(tmp_path)
        code = main(["session", "capture", "--plan-id", "p1"])
        assert code == 0
        captured = capsys.readouterr()
        parsed = _parsed(captured.out)
        assert parsed["status"] == "error"
        assert parsed["error"] == "marshal_not_found"

    def test_main_unknown_target_in_marshal_returns_0_with_toon_error(
        self, tmp_path, monkeypatch, capsys
    ):
        """main() with an unknown runtime.target in marshal prints TOON error, exit 0."""
        monkeypatch.chdir(tmp_path)
        _make_marshal_file(tmp_path, "unsupported-runtime")
        code = main(["session", "capture", "--plan-id", "p1"])
        assert code == 0
        captured = capsys.readouterr()
        parsed = _parsed(captured.out)
        assert parsed["status"] == "error"
        assert parsed["error"] == "unknown_target"

    def test_main_dispatches_to_runtime_and_prints_toon(self, tmp_path, monkeypatch, capsys):
        """main() with a valid marshal dispatches correctly and prints TOON to stdout."""
        monkeypatch.chdir(tmp_path)
        _make_marshal_file(tmp_path, "claude")
        with patch("platform_runtime._make_runtime") as mock_make:
            rt = _mock_runtime()
            mock_make.return_value = rt
            code = main(["session", "render-title"])
        assert code == 0
        captured = capsys.readouterr()
        parsed = _parsed(captured.out)
        assert parsed["status"] == "success"
        rt.session_render_title.assert_called_once()

    def test_main_project_initial_setup_without_marshal_uses_target_arg(
        self, tmp_path, monkeypatch, capsys
    ):
        """project initial-setup can run before marshal.json exists; uses --target arg."""
        monkeypatch.chdir(tmp_path)
        with patch("platform_runtime._make_runtime") as mock_make:
            rt = _mock_runtime()
            mock_make.return_value = rt
            code = main(
                ["project", "initial-setup", "--project-dir", str(tmp_path), "--target", "opencode"]
            )
        assert code == 0
        mock_make.assert_called_once_with("opencode")

    def test_main_marshal_with_missing_target_defaults_to_claude(
        self, tmp_path, monkeypatch, capsys
    ):
        """When marshal.json exists but lacks runtime.target, router defaults to 'claude'."""
        monkeypatch.chdir(tmp_path)
        plan_dir = tmp_path / ".plan"
        plan_dir.mkdir()
        (plan_dir / "marshal.json").write_text(json.dumps({"runtime": {}}), encoding="utf-8")
        with patch("platform_runtime._make_runtime") as mock_make:
            rt = _mock_runtime()
            mock_make.return_value = rt
            code = main(["health-check", "--checks", "all"])
        assert code == 0
        mock_make.assert_called_once_with("claude")

    def test_main_uses_plan_dir_name_env_var(self, tmp_path, monkeypatch, capsys):
        """main() respects PLAN_DIR_NAME env var when locating marshal.json."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PLAN_DIR_NAME", ".custom-plan")
        import platform_runtime as _pr

        monkeypatch.setattr(_pr, "_PLAN_DIR_NAME", ".custom-plan")
        custom_plan = tmp_path / ".custom-plan"
        custom_plan.mkdir()
        (custom_plan / "marshal.json").write_text(
            json.dumps({"runtime": {"target": "claude"}}), encoding="utf-8"
        )
        with patch("platform_runtime._make_runtime") as mock_make:
            rt = _mock_runtime()
            mock_make.return_value = rt
            code = main(["health-check", "--checks", "all"])
        assert code == 0
        mock_make.assert_called_once_with("claude")
