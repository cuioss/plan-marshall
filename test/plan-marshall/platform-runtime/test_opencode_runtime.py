#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for opencode_runtime.py — OpenCode implementation of all 18 operations.

Asserts the no-op contract for session/display operations that OpenCode does not
support, the honest no-op contract for the permission operations (OpenCode has no
validated permission backend), the success/no-op paths for metrics operations, and
error paths for invalid arguments across all 18 operations defined in the Runtime
ABC.
"""

import json  # noqa: I001
import pathlib

import pytest

# conftest.py sets up PYTHONPATH so imports resolve without manual sys.path work.
from opencode_runtime import OpenCodeRuntime
from toon_parser import parse_toon


# =============================================================================
# Shared fixture
# =============================================================================


@pytest.fixture()
def runtime() -> OpenCodeRuntime:
    """Return a fresh OpenCodeRuntime instance."""
    return OpenCodeRuntime()


# =============================================================================
# Helper
# =============================================================================


def _parse(toon_str: str) -> dict:
    """Parse a TOON string and assert it is non-empty."""
    result = parse_toon(toon_str)
    assert isinstance(result, dict), f"parse_toon returned non-dict: {toon_str!r}"
    return result


# =============================================================================
# 1. project_initial_setup
# =============================================================================


def test_project_initial_setup_creates_plan_dir(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """project_initial_setup creates .plan/ and .plan/temp/ under project_dir."""
    result = _parse(runtime.project_initial_setup(str(tmp_path), "opencode"))
    assert result["status"] == "success"
    assert result["operation"] == "project initial-setup"
    assert result["target"] == "opencode"
    assert result["marshal_written"] is True
    assert result["hook_installed"] is False
    assert (tmp_path / ".plan").is_dir()
    assert (tmp_path / ".plan" / "temp").is_dir()


def test_project_initial_setup_writes_marshal_json(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """project_initial_setup writes runtime.target into marshal.json."""
    runtime.project_initial_setup(str(tmp_path), "opencode")
    marshal_path = tmp_path / ".plan" / "marshal.json"
    assert marshal_path.exists()
    data = json.loads(marshal_path.read_text(encoding="utf-8"))
    assert data["runtime"]["target"] == "opencode"


def test_project_initial_setup_preserves_existing_marshal_fields(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path
) -> None:
    """project_initial_setup merges into an existing marshal.json without discarding other fields."""
    plan_dir = tmp_path / ".plan"
    plan_dir.mkdir()
    marshal_path = plan_dir / "marshal.json"
    marshal_path.write_text(json.dumps({"existing_key": "existing_value"}), encoding="utf-8")

    runtime.project_initial_setup(str(tmp_path), "opencode")

    data = json.loads(marshal_path.read_text(encoding="utf-8"))
    assert data["existing_key"] == "existing_value"
    assert data["runtime"]["target"] == "opencode"


def test_project_initial_setup_hook_skip_reason_present(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path
) -> None:
    """project_initial_setup reports hook_skip_reason explaining no SessionStart hook."""
    result = _parse(runtime.project_initial_setup(str(tmp_path), "opencode"))
    assert "hook_skip_reason" in result
    assert "OpenCode" in result["hook_skip_reason"]


def test_project_initial_setup_invalid_dir_returns_error(runtime: OpenCodeRuntime) -> None:
    """project_initial_setup returns error when project_dir is not writable."""
    result = _parse(runtime.project_initial_setup("/nonexistent/path/that/cannot/be/created", "opencode"))
    assert result["status"] == "error"
    assert result["error"] == "io_error"


# =============================================================================
# 1b. project_install_hook — always no-op
# =============================================================================


def test_project_install_hook_is_noop(runtime: OpenCodeRuntime) -> None:
    """project_install_hook returns no-op because OpenCode has no SessionStart hook."""
    result = _parse(runtime.project_install_hook(".claude/settings.local.json"))
    assert result["status"] == "no-op"
    assert result["operation"] == "project install-hook"
    assert "reason" in result
    assert "alternative" in result


# =============================================================================
# 2. session_capture — always no-op
# =============================================================================


def test_session_capture_is_noop(runtime: OpenCodeRuntime) -> None:
    """session_capture returns no-op because OpenCode does not expose a session id."""
    result = _parse(runtime.session_capture("my-plan"))
    assert result["status"] == "no-op"
    assert result["operation"] == "session capture"


def test_session_capture_noop_has_reason_and_alternative(runtime: OpenCodeRuntime) -> None:
    """session_capture no-op includes reason and alternative fields."""
    result = _parse(runtime.session_capture("my-plan"))
    assert "reason" in result
    assert "alternative" in result
    assert "OpenCode" in result["reason"]


# =============================================================================
# 4. session_render_title — always no-op
# =============================================================================


def test_session_render_title_is_noop(runtime: OpenCodeRuntime) -> None:
    """session_render_title returns no-op because OpenCode has no plugin-driven hook."""
    result = _parse(runtime.session_render_title())
    assert result["status"] == "no-op"
    assert result["operation"] == "session render-title"


def test_session_render_title_noop_fields(runtime: OpenCodeRuntime) -> None:
    """session_render_title no-op includes reason and alternative."""
    result = _parse(runtime.session_render_title())
    assert "reason" in result
    assert "alternative" in result


# =============================================================================
# 4b. session_push_title_token — always no-op
# =============================================================================


def test_session_push_title_token_is_noop(runtime: OpenCodeRuntime) -> None:
    """session_push_title_token returns no-op because OpenCode has no push channel."""
    result = _parse(runtime.session_push_title_token("my-plan", "⏳"))
    assert result["status"] == "no-op"
    assert result["operation"] == "session push-title-token"


def test_session_push_title_token_noop_fields(runtime: OpenCodeRuntime) -> None:
    """session_push_title_token no-op includes reason and alternative."""
    result = _parse(runtime.session_push_title_token("my-plan", "⏳"))
    assert "reason" in result
    assert "alternative" in result


# =============================================================================
# Permission operations — all honest no-op (no validated OpenCode backend)
#
# OpenCode has no validated permission backend and the Claude permission grammar
# does not map onto OpenCode's settings format, so every permission op returns an
# honest ``no-op`` with reason + alternative rather than a fabricated success.
# Scope / operation validation still runs first, so invalid inputs return
# ``error`` before the no-op path.
# =============================================================================


def _assert_permission_noop(result: dict) -> None:
    """Assert *result* is an honest no-op with reason + alternative naming OpenCode."""
    assert result["status"] == "no-op"
    assert "reason" in result
    assert "alternative" in result
    assert "OpenCode" in result["reason"]
    # An honest no-op never claims a write happened.
    assert "permissions_written" not in result
    assert "changes_applied" not in result
    assert "domains_added" not in result
    assert "domains_removed" not in result


# 5. permission_configure


def test_permission_configure_is_noop(runtime: OpenCodeRuntime) -> None:
    """permission_configure returns an honest no-op (no fake permissions_written count)."""
    result = _parse(runtime.permission_configure("project", ["Read(**)", "Write(**)"]))
    assert result["operation"] == "permission configure"
    _assert_permission_noop(result)


def test_permission_configure_global_scope_is_noop(runtime: OpenCodeRuntime) -> None:
    """permission_configure with global scope is also an honest no-op."""
    result = _parse(runtime.permission_configure("global", ["Read(**)"]))
    _assert_permission_noop(result)


def test_permission_configure_invalid_scope_returns_error(runtime: OpenCodeRuntime) -> None:
    """permission_configure with invalid scope returns error before the no-op path."""
    result = _parse(runtime.permission_configure("workspace", ["Read(**)"]))
    assert result["status"] == "error"
    assert result["error"] == "invalid_scope"


# 6. permission_analyze


def test_permission_analyze_is_noop(runtime: OpenCodeRuntime) -> None:
    """permission_analyze returns an honest no-op (no Claude-grammar audit on OpenCode)."""
    result = _parse(runtime.permission_analyze("both", ["all"], None))
    assert result["operation"] == "permission analyze"
    _assert_permission_noop(result)


def test_permission_analyze_invalid_scope_returns_error(runtime: OpenCodeRuntime) -> None:
    """permission_analyze with invalid scope returns error before the no-op path."""
    result = _parse(runtime.permission_analyze("workspace", ["all"], None))
    assert result["status"] == "error"
    assert result["error"] == "invalid_scope"


def test_permission_analyze_invalid_check_returns_error(runtime: OpenCodeRuntime) -> None:
    """permission_analyze with an unknown check name returns error before the no-op path."""
    result = _parse(runtime.permission_analyze("global", ["nonexistent-check"], None))
    assert result["status"] == "error"
    assert result["error"] == "invalid_check"


# 7. permission_fix


def test_permission_fix_is_noop(runtime: OpenCodeRuntime) -> None:
    """permission_fix returns an honest no-op (no fake changes_applied count)."""
    perms = ["Read(**)", "Write(.plan/**)"]
    result = _parse(runtime.permission_fix("project", "add", perms, False))
    assert result["operation"] == "permission fix"
    _assert_permission_noop(result)


def test_permission_fix_all_valid_operations_are_noop(runtime: OpenCodeRuntime) -> None:
    """permission_fix accepts all documented operation names and returns no-op for each."""
    for op in ("normalize", "add", "remove", "ensure", "consolidate"):
        result = _parse(runtime.permission_fix("global", op, [], False))
        assert result["status"] == "no-op", f"Expected no-op for operation {op!r}"


def test_permission_fix_invalid_scope_returns_error(runtime: OpenCodeRuntime) -> None:
    """permission_fix with invalid scope returns error before the no-op path."""
    result = _parse(runtime.permission_fix("unknown", "normalize", [], False))
    assert result["status"] == "error"
    assert result["error"] == "invalid_scope"


def test_permission_fix_invalid_operation_returns_error(runtime: OpenCodeRuntime) -> None:
    """permission_fix with unknown operation name returns error before the no-op path."""
    result = _parse(runtime.permission_fix("project", "delete-all", [], False))
    assert result["status"] == "error"
    assert result["error"] == "invalid_operation"


# 8. permission_ensure_wildcards


def test_permission_ensure_wildcards_is_noop(runtime: OpenCodeRuntime) -> None:
    """permission_ensure_wildcards returns an honest no-op (no fake wildcards_added count)."""
    result = _parse(runtime.permission_ensure_wildcards("project", "marketplace/", False))
    assert result["operation"] == "permission ensure-wildcards"
    _assert_permission_noop(result)
    assert "wildcards_added" not in result


def test_permission_ensure_wildcards_invalid_scope_returns_error(runtime: OpenCodeRuntime) -> None:
    """permission_ensure_wildcards with invalid scope returns error before the no-op path."""
    result = _parse(runtime.permission_ensure_wildcards("workspace", "marketplace/", False))
    assert result["status"] == "error"
    assert result["error"] == "invalid_scope"


# 9. permission_ensure_steps


def test_permission_ensure_steps_is_noop(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path
) -> None:
    """permission_ensure_steps returns an honest no-op when marshal.json exists."""
    marshal_path = tmp_path / "marshal.json"
    marshal_path.write_text(json.dumps({"runtime": {"target": "opencode"}}), encoding="utf-8")

    result = _parse(runtime.permission_ensure_steps(str(marshal_path), "project", False))
    assert result["operation"] == "permission ensure-steps"
    _assert_permission_noop(result)
    assert "permissions_added" not in result


def test_permission_ensure_steps_missing_marshal_returns_error(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path
) -> None:
    """permission_ensure_steps returns error when marshal.json does not exist."""
    missing_path = str(tmp_path / "nonexistent" / "marshal.json")
    result = _parse(runtime.permission_ensure_steps(missing_path, "project", False))
    assert result["status"] == "error"
    assert result["error"] == "marshal_not_found"


def test_permission_ensure_steps_invalid_scope_returns_error(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path
) -> None:
    """permission_ensure_steps with invalid scope returns error before the no-op path."""
    marshal_path = tmp_path / "marshal.json"
    marshal_path.write_text("{}", encoding="utf-8")

    result = _parse(runtime.permission_ensure_steps(str(marshal_path), "workspace", False))
    assert result["status"] == "error"
    assert result["error"] == "invalid_scope"


# 10. permission_web_analyze


def test_permission_web_analyze_is_noop(runtime: OpenCodeRuntime) -> None:
    """permission_web_analyze returns an honest no-op (no Claude WebFetch audit on OpenCode)."""
    result = _parse(runtime.permission_web_analyze("global"))
    assert result["operation"] == "permission web-analyze"
    _assert_permission_noop(result)


def test_permission_web_analyze_invalid_scope_returns_error(runtime: OpenCodeRuntime) -> None:
    """permission_web_analyze with invalid scope returns error before the no-op path."""
    result = _parse(runtime.permission_web_analyze("local"))
    assert result["status"] == "error"
    assert result["error"] == "invalid_scope"


# 11. permission_web_apply


def test_permission_web_apply_is_noop(runtime: OpenCodeRuntime) -> None:
    """permission_web_apply returns an honest no-op (no fake domains_added/removed count)."""
    domains = ["example.com", "api.github.com"]
    result = _parse(runtime.permission_web_apply("project", add=domains, remove=[], dry_run=False))
    assert result["operation"] == "permission web-apply"
    _assert_permission_noop(result)


def test_permission_web_apply_invalid_scope_returns_error(runtime: OpenCodeRuntime) -> None:
    """permission_web_apply with invalid scope returns error before the no-op path."""
    result = _parse(runtime.permission_web_apply("workspace", add=[], remove=[], dry_run=False))
    assert result["status"] == "error"
    assert result["error"] == "invalid_scope"


# =============================================================================
# 12. metrics_capture
# =============================================================================


def test_metrics_capture_with_total_tokens_succeeds(runtime: OpenCodeRuntime) -> None:
    """metrics_capture with total_tokens provided succeeds and stores the count."""
    result = _parse(runtime.metrics_capture("my-plan", "phase-1-init", total_tokens=42000))
    assert result["status"] == "success"
    assert result["operation"] == "metrics capture"
    assert result["plan_id"] == "my-plan"
    assert result["phase"] == "phase-1-init"
    assert result["tokens_captured"] == 42000
    assert result["source"] == "manual"


def test_metrics_capture_without_tokens_is_noop(runtime: OpenCodeRuntime) -> None:
    """metrics_capture without total_tokens is no-op (no session transcript on OpenCode)."""
    result = _parse(runtime.metrics_capture("my-plan", "phase-2-refine", total_tokens=None))
    assert result["status"] == "no-op"
    assert result["operation"] == "metrics capture"
    assert "OpenCode" in result["reason"]
    assert "alternative" in result


def test_metrics_capture_zero_tokens_succeeds(runtime: OpenCodeRuntime) -> None:
    """metrics_capture with total_tokens=0 is a valid success (zero tokens is a count)."""
    result = _parse(runtime.metrics_capture("my-plan", "phase-3-outline", total_tokens=0))
    assert result["status"] == "success"
    assert result["tokens_captured"] == 0


# =============================================================================
# 13. subagent_dispatch
# =============================================================================


def test_subagent_dispatch_without_prompt_file(runtime: OpenCodeRuntime) -> None:
    """subagent_dispatch without prompt_file succeeds and uses 'task' as OpenCode tool."""
    result = _parse(runtime.subagent_dispatch("execution-context-level-3", None, None))
    assert result["status"] == "success"
    assert result["operation"] == "subagent dispatch"
    assert result["invocation"]["tool"] == "task"
    assert result["platform"] == "opencode"


def test_subagent_dispatch_with_prompt_file(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path
) -> None:
    """subagent_dispatch with an existing prompt_file reads and uses its content."""
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("Execute the plan for {plan_id}", encoding="utf-8")

    result = _parse(
        runtime.subagent_dispatch(
            "execution-context-level-3",
            str(prompt_file),
            {"plan_id": "my-plan"},
        )
    )
    assert result["status"] == "success"
    assert "my-plan" in result["invocation"]["prompt"]


def test_subagent_dispatch_context_substitution(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path
) -> None:
    """subagent_dispatch substitutes context keys into prompt template."""
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("Plan: {plan_id}, Task: {task_number}", encoding="utf-8")

    result = _parse(
        runtime.subagent_dispatch(
            "execution-context-level-3",
            str(prompt_file),
            {"plan_id": "my-plan", "task_number": "7"},
        )
    )
    assert result["status"] == "success"
    assert "my-plan" in result["invocation"]["prompt"]
    assert "7" in result["invocation"]["prompt"]


def test_subagent_dispatch_missing_prompt_file_returns_error(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path
) -> None:
    """subagent_dispatch with a non-existent prompt_file returns error."""
    missing = str(tmp_path / "nonexistent_prompt.md")
    result = _parse(runtime.subagent_dispatch("execution-context-level-3", missing, None))
    assert result["status"] == "error"
    assert result["error"] == "prompt_not_found"


# =============================================================================
# 14. health_check
# =============================================================================


def test_health_check_display_always_unhealthy(runtime: OpenCodeRuntime) -> None:
    """health_check display check always reports unhealthy on OpenCode (no hook)."""
    result = _parse(runtime.health_check("display"))
    assert result["status"] == "success"
    assert result["all_healthy"] is False
    display_result = next(r for r in result["results"] if r["check"] == "display")
    assert display_result["healthy"] is False


def test_health_check_hook_always_unhealthy(runtime: OpenCodeRuntime) -> None:
    """health_check hook check always reports unhealthy (no SessionStart hook on OpenCode)."""
    result = _parse(runtime.health_check("hook"))
    assert result["status"] == "success"
    hook_result = next(r for r in result["results"] if r["check"] == "hook")
    assert hook_result["healthy"] is False


def test_health_check_all_includes_four_checks(runtime: OpenCodeRuntime) -> None:
    """health_check with 'all' runs permissions, display, mcp-diagnostics, and hook."""
    result = _parse(runtime.health_check("all"))
    assert result["status"] == "success"
    checks_run = result["checks_run"]
    assert "permissions" in checks_run
    assert "display" in checks_run
    assert "mcp-diagnostics" in checks_run
    assert "hook" in checks_run
    assert len(result["results"]) == 4


def test_health_check_permissions_check_present(runtime: OpenCodeRuntime) -> None:
    """health_check permissions check returns a result dict with healthy and detail."""
    result = _parse(runtime.health_check("permissions"))
    assert result["status"] == "success"
    perm_result = next(r for r in result["results"] if r["check"] == "permissions")
    assert "healthy" in perm_result
    assert "detail" in perm_result


def test_health_check_comma_separated_checks(runtime: OpenCodeRuntime) -> None:
    """health_check accepts comma-separated check names and processes each."""
    result = _parse(runtime.health_check("display,hook"))
    assert result["status"] == "success"
    checks_run = result["checks_run"]
    assert "display" in checks_run
    assert "hook" in checks_run
    assert len(result["results"]) == 2


def test_health_check_all_healthy_false_when_display_or_hook(runtime: OpenCodeRuntime) -> None:
    """health_check all_healthy is False whenever display or hook is included."""
    result = _parse(runtime.health_check("display"))
    assert result["all_healthy"] is False

    result2 = _parse(runtime.health_check("hook"))
    assert result2["all_healthy"] is False
