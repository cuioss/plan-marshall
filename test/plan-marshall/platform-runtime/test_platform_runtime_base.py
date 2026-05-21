#!/usr/bin/env python3
"""Tests for runtime_base.py — Runtime ABC and TOON helpers."""

import pytest  # noqa: I001

# conftest.py sets up PYTHONPATH so imports resolve without manual sys.path work.
from runtime_base import Runtime, toon_error, toon_noop, toon_success  # type: ignore[import-not-found]
from toon_parser import parse_toon  # type: ignore[import-not-found]


# =============================================================================
# Test: TOON helper — toon_success
# =============================================================================


def test_toon_success_minimal():
    """toon_success without result dict returns status and operation."""
    output = toon_success("session capture")
    result = parse_toon(output)
    assert result["status"] == "success"
    assert result["operation"] == "session capture"


def test_toon_success_with_result():
    """toon_success merges result fields into the response."""
    output = toon_success("health-check", {"passed": True, "checks_run": 3})
    result = parse_toon(output)
    assert result["status"] == "success"
    assert result["operation"] == "health-check"
    assert result["passed"] is True
    assert result["checks_run"] == 3


def test_toon_success_result_none_ignored():
    """toon_success with result=None behaves identically to no result."""
    output_none = toon_success("project initial-setup", None)
    output_default = toon_success("project initial-setup")
    assert parse_toon(output_none) == parse_toon(output_default)


def test_toon_success_round_trip():
    """toon_success output parses back to a dict with the expected fields."""
    output = toon_success("permission configure", {"scope": "project", "count": 5})
    result = parse_toon(output)
    assert result["status"] == "success"
    assert result["scope"] == "project"
    assert result["count"] == 5


# =============================================================================
# Test: TOON helper — toon_error
# =============================================================================


def test_toon_error_fields():
    """toon_error populates status, operation, error, and message."""
    output = toon_error("session capture", "hook_not_configured", "SessionStart hook missing")
    result = parse_toon(output)
    assert result["status"] == "error"
    assert result["operation"] == "session capture"
    assert result["error"] == "hook_not_configured"
    assert "hook" in result["message"].lower()


def test_toon_error_round_trip():
    """toon_error output round-trips through parse_toon without data loss."""
    code = "marshal_not_found"
    msg = ".plan/marshal.json missing"
    output = toon_error("subagent dispatch", code, msg)
    result = parse_toon(output)
    assert result["error"] == code
    assert result["message"] == msg


def test_toon_error_distinct_from_noop():
    """toon_error must not include reason/alternative keys."""
    output = toon_error("permission analyze", "invalid_check", "unknown check name")
    result = parse_toon(output)
    assert "reason" not in result
    assert "alternative" not in result


# =============================================================================
# Test: TOON helper — toon_noop
# =============================================================================


def test_toon_noop_fields():
    """toon_noop populates status, operation, reason, and alternative."""
    output = toon_noop(
        "session configure-display",
        "OpenCode has no plugin-driven status-line hook",
        "Use OpenCode's built-in TUI status surface",
    )
    result = parse_toon(output)
    assert result["status"] == "no-op"
    assert result["operation"] == "session configure-display"
    assert "OpenCode" in result["reason"]
    assert "TUI" in result["alternative"]


def test_toon_noop_round_trip():
    """toon_noop output round-trips through parse_toon."""
    reason = "automatic token capture requires a platform-provided session id"
    alternative = "pass --total-tokens manually"
    output = toon_noop("metrics capture", reason, alternative)
    result = parse_toon(output)
    assert result["reason"] == reason
    assert result["alternative"] == alternative


def test_toon_noop_distinct_from_error():
    """toon_noop must not include error/message keys."""
    output = toon_noop("session render-title", "no hook", "use TUI")
    result = parse_toon(output)
    assert "error" not in result
    assert "message" not in result


# =============================================================================
# Test: Runtime ABC — abstract enforcement
# =============================================================================


def _make_partial_runtime(**overrides):
    """Create a concrete subclass with only the provided overrides.

    Any method not overridden remains abstract, so instantiation must fail.
    """
    methods = {
        "project_initial_setup",
        "project_install_hook",
        "session_capture",
        "session_configure_display",
        "session_render_title",
        "permission_configure",
        "permission_analyze",
        "permission_fix",
        "permission_ensure_wildcards",
        "permission_ensure_steps",
        "permission_web_analyze",
        "permission_web_apply",
        "metrics_capture",
        "subagent_dispatch",
        "health_check",
    }
    stubs = {m: lambda self, *a, **kw: "" for m in methods}
    stubs.update(overrides)
    return type("PartialRuntime", (Runtime,), stubs)


class _ConcreteRuntime(Runtime):
    """Minimal concrete subclass that implements all 15 abstract methods."""

    def project_initial_setup(self, project_dir: str, target: str) -> str:
        return toon_success("project initial-setup")

    def project_install_hook(self, target: str) -> str:
        return toon_success("project install-hook")

    def session_capture(self, plan_id: str) -> str:
        return toon_success("session capture")

    def session_configure_display(self, display_type: str, style: str) -> str:
        return toon_success("session configure-display")

    def session_render_title(self) -> str:
        return toon_success("session render-title")

    def permission_configure(self, scope: str, permissions: list) -> str:
        return toon_success("permission configure")

    def permission_analyze(self, scope: str, checks: list, marshal_path) -> str:
        return toon_success("permission analyze")

    def permission_fix(self, scope: str, operation: str, permissions: list, dry_run: bool) -> str:
        return toon_success("permission fix")

    def permission_ensure_wildcards(self, scope: str, marketplace_dir: str, dry_run: bool) -> str:
        return toon_success("permission ensure-wildcards")

    def permission_ensure_steps(self, marshal_path: str, scope: str, dry_run: bool) -> str:
        return toon_success("permission ensure-steps")

    def permission_web_analyze(self, scope: str) -> str:
        return toon_success("permission web-analyze")

    def permission_web_apply(self, scope: str, add: list, remove: list, dry_run: bool) -> str:
        return toon_success("permission web-apply")

    def metrics_capture(self, plan_id: str, phase: str, total_tokens) -> str:
        return toon_success("metrics capture")

    def subagent_dispatch(self, agent: str, prompt_file, context) -> str:
        return toon_success("subagent dispatch")

    def health_check(self, checks: str) -> str:
        return toon_success("health-check")


ALL_ABSTRACT_METHODS = [
    "project_initial_setup",
    "project_install_hook",
    "session_capture",
    "session_configure_display",
    "session_render_title",
    "permission_configure",
    "permission_analyze",
    "permission_fix",
    "permission_ensure_wildcards",
    "permission_ensure_steps",
    "permission_web_analyze",
    "permission_web_apply",
    "metrics_capture",
    "subagent_dispatch",
    "health_check",
]


def test_runtime_has_15_abstract_methods():
    """Runtime ABC exposes exactly 15 abstract methods."""
    abstract_methods = getattr(Runtime, "__abstractmethods__", frozenset())
    assert len(abstract_methods) == 15, (
        f"Expected 15 abstract methods, found {len(abstract_methods)}: {sorted(abstract_methods)}"
    )


def test_all_expected_methods_are_abstract():
    """Each of the 15 documented operations is abstract on Runtime."""
    abstract_methods = getattr(Runtime, "__abstractmethods__", frozenset())
    for method in ALL_ABSTRACT_METHODS:
        assert method in abstract_methods, (
            f"Expected {method!r} to be abstract on Runtime"
        )


def test_runtime_cannot_be_instantiated_directly():
    """Runtime ABC cannot be instantiated directly."""
    with pytest.raises(TypeError):
        Runtime()  # type: ignore[abstract]


@pytest.mark.parametrize("missing_method", ALL_ABSTRACT_METHODS)
def test_subclass_missing_one_method_raises(missing_method: str):
    """A subclass omitting any single abstract method cannot be instantiated."""
    # Build a complete set of stubs, then remove the one under test.
    stubs = {m: lambda self, *a, **kw: "" for m in ALL_ABSTRACT_METHODS}
    del stubs[missing_method]
    PartialRuntime = type("PartialRuntime", (Runtime,), stubs)
    with pytest.raises(TypeError, match="abstract"):
        PartialRuntime()


def test_concrete_subclass_can_be_instantiated():
    """A subclass implementing all 15 methods can be instantiated without error."""
    runtime = _ConcreteRuntime()
    assert isinstance(runtime, Runtime)


# =============================================================================
# Test: concrete subclass return values use TOON helpers
# =============================================================================


def test_concrete_returns_valid_toon_for_each_method():
    """Every _ConcreteRuntime method returns parseable TOON with status=success."""
    runtime = _ConcreteRuntime()

    outputs = [
        runtime.project_initial_setup(".", "claude"),
        runtime.project_install_hook(".claude/settings.local.json"),
        runtime.session_capture("my-plan"),
        runtime.session_configure_display("terminal-title", "unicode"),
        runtime.session_render_title(),
        runtime.permission_configure("project", ["Read(**)"]),
        runtime.permission_analyze("both", ["all"], None),
        runtime.permission_fix("project", "normalize", [], False),
        runtime.permission_ensure_wildcards("project", "marketplace/", False),
        runtime.permission_ensure_steps(".plan/marshal.json", "project", False),
        runtime.permission_web_analyze("global"),
        runtime.permission_web_apply("project", ["example.com"], [], False),
        runtime.metrics_capture("my-plan", "phase-1-init", None),
        runtime.subagent_dispatch("execution-context", None, None),
        runtime.health_check("all"),
    ]

    assert len(outputs) == 15, "Expected output for each of the 15 methods"
    for output in outputs:
        result = parse_toon(output)
        assert result.get("status") == "success", (
            f"Expected status=success, got {result.get('status')!r} in: {output!r}"
        )
