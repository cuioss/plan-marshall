#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for pretooluse_gate.py — the shared PreToolUse gate module.

pretooluse_gate is a pure-function library shipped as a sibling module of the
platform-runtime scripts. It is imported directly (not run as a subprocess), so
the scripts dir is inserted on sys.path before the import per the canonical
sibling-import scaffolding pattern.

Coverage:
  - parse() returns {} on empty / malformed / non-object input and never raises.
  - Each accessor (sub_agent_identity, cwd, tool_name, tool_input) returns the
    field value when present and a safe default when absent.
  - context_gate() is true on a Signal-1-only payload, true on a Signal-2-only
    payload, true when both fire, and false (fail-open) when neither fires.
  - An absent Signal-1 field falls back to Signal 2 alone.
"""

from __future__ import annotations

import os
import sys

from conftest import get_script_path  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path("plan-marshall", "platform-runtime", "pretooluse_gate.py")
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import pretooluse_gate as gate  # noqa: E402


# =============================================================================
# Helpers
# =============================================================================


def _worktree_cwd() -> str:
    """A cwd resolving under the plan-worktree path segment (Signal 2)."""
    return os.path.join(
        "/Users/dev/project",
        gate.WORKTREE_PATH_SEGMENT,
        "my-plan",
    )


def _signal1_payload() -> dict:
    """Payload where only Signal 1 fires (execution-context sub-agent identity).

    Uses the real bundle-qualified ``agent_type`` value observed in live
    PreToolUse payloads (D2 capture) — NOT a bare ``execution-context-*``.
    """
    return {gate.SUB_AGENT_IDENTITY_FIELD: "plan-marshall:execution-context-level-3"}


def _signal2_payload() -> dict:
    """Payload where only Signal 2 fires (cwd under a plan worktree)."""
    return {gate.CWD_FIELD: _worktree_cwd()}


# =============================================================================
# parse()
# =============================================================================


def test_parse_returns_dict_on_well_formed_object() -> None:
    assert gate.parse('{"tool_name": "Bash"}') == {"tool_name": "Bash"}


def test_parse_returns_empty_on_empty_string() -> None:
    assert gate.parse("") == {}


def test_parse_returns_empty_on_whitespace_only() -> None:
    assert gate.parse("   \n\t ") == {}


def test_parse_returns_empty_on_malformed_json() -> None:
    assert gate.parse("{not valid json") == {}


def test_parse_returns_empty_on_non_object_json() -> None:
    # Valid JSON but not an object — list and scalar both degrade to {}.
    assert gate.parse("[1, 2, 3]") == {}
    assert gate.parse('"a string"') == {}
    assert gate.parse("42") == {}


def test_parse_returns_empty_on_non_string_input() -> None:
    # Defensive: a non-str argument must not raise.
    assert gate.parse(None) == {}  # type: ignore[arg-type]
    assert gate.parse(123) == {}  # type: ignore[arg-type]


def test_parse_never_raises_on_arbitrary_input() -> None:
    for raw in ["", "null", "{", "}{", "\x00", '{"a":}', "[", "true"]:
        # Must not raise; result is always a dict.
        assert isinstance(gate.parse(raw), dict)


# =============================================================================
# sub_agent_identity()
# =============================================================================


def test_sub_agent_identity_reads_primary_field() -> None:
    payload = {gate.SUB_AGENT_IDENTITY_FIELD: "execution-context-level-1"}
    assert gate.sub_agent_identity(payload) == "execution-context-level-1"


def test_sub_agent_identity_reads_fallback_field() -> None:
    fallback = gate.SUB_AGENT_IDENTITY_FALLBACK_FIELDS[0]
    payload = {fallback: "execution-context-level-2"}
    assert gate.sub_agent_identity(payload) == "execution-context-level-2"


def test_sub_agent_identity_returns_none_when_absent() -> None:
    assert gate.sub_agent_identity({"unrelated": "x"}) is None


def test_sub_agent_identity_returns_none_on_empty_string_value() -> None:
    assert gate.sub_agent_identity({gate.SUB_AGENT_IDENTITY_FIELD: ""}) is None


def test_sub_agent_identity_returns_none_on_non_dict() -> None:
    assert gate.sub_agent_identity(None) is None  # type: ignore[arg-type]
    assert gate.sub_agent_identity("not a dict") is None  # type: ignore[arg-type]


# =============================================================================
# cwd()
# =============================================================================


def test_cwd_reads_field() -> None:
    payload = {gate.CWD_FIELD: "/Users/dev/project"}
    assert gate.cwd(payload) == "/Users/dev/project"


def test_cwd_returns_none_when_absent() -> None:
    assert gate.cwd({"unrelated": "x"}) is None


def test_cwd_returns_none_on_empty_string() -> None:
    assert gate.cwd({gate.CWD_FIELD: ""}) is None


def test_cwd_returns_none_on_non_dict() -> None:
    assert gate.cwd(None) is None  # type: ignore[arg-type]


# =============================================================================
# tool_name()
# =============================================================================


def test_tool_name_reads_field() -> None:
    assert gate.tool_name({gate.TOOL_NAME_FIELD: "Bash"}) == "Bash"


def test_tool_name_returns_none_when_absent() -> None:
    assert gate.tool_name({"unrelated": "x"}) is None


def test_tool_name_returns_none_on_non_dict() -> None:
    assert gate.tool_name(None) is None  # type: ignore[arg-type]


# =============================================================================
# tool_input()
# =============================================================================


def test_tool_input_reads_dict() -> None:
    payload = {gate.TOOL_INPUT_FIELD: {"command": "ls -la"}}
    assert gate.tool_input(payload) == {"command": "ls -la"}


def test_tool_input_returns_empty_dict_when_absent() -> None:
    assert gate.tool_input({"unrelated": "x"}) == {}


def test_tool_input_returns_empty_dict_on_non_dict_value() -> None:
    # A non-dict tool_input value degrades to {} so callers can index safely.
    assert gate.tool_input({gate.TOOL_INPUT_FIELD: "a string"}) == {}
    assert gate.tool_input({gate.TOOL_INPUT_FIELD: None}) == {}


def test_tool_input_returns_empty_dict_on_non_dict_payload() -> None:
    assert gate.tool_input(None) == {}  # type: ignore[arg-type]


# =============================================================================
# context_gate() — Signal1 OR Signal2, fail-open
# =============================================================================


def test_context_gate_true_on_signal1_only() -> None:
    assert gate.context_gate(_signal1_payload()) is True


def test_context_gate_true_on_signal2_only() -> None:
    assert gate.context_gate(_signal2_payload()) is True


def test_context_gate_true_when_both_signals_fire() -> None:
    payload = {**_signal1_payload(), **_signal2_payload()}
    assert gate.context_gate(payload) is True


def test_context_gate_false_when_neither_signal_fires() -> None:
    # Fail-open: a benign main-checkout call is never gated.
    payload = {
        gate.SUB_AGENT_IDENTITY_FIELD: "some-other-agent",
        gate.CWD_FIELD: "/Users/dev/project",
    }
    assert gate.context_gate(payload) is False


def test_context_gate_false_on_empty_payload() -> None:
    assert gate.context_gate({}) is False


def test_context_gate_false_on_non_dict() -> None:
    assert gate.context_gate(None) is False  # type: ignore[arg-type]


def test_context_gate_absent_signal1_falls_back_to_signal2() -> None:
    # No Signal-1 identity field at all — Signal 2 alone must satisfy the gate.
    payload = {gate.CWD_FIELD: _worktree_cwd()}
    assert gate.sub_agent_identity(payload) is None
    assert gate.context_gate(payload) is True


def test_context_gate_signal1_requires_execution_context_marker() -> None:
    # A sub-agent identity that does not carry the :execution-context marker does
    # not fire Signal 1 (e.g. a non-execution-context agent type).
    payload = {gate.SUB_AGENT_IDENTITY_FIELD: "phase-5-execute"}
    assert gate.context_gate(payload) is False


def test_context_gate_true_on_real_bundle_qualified_subagent_identity() -> None:
    # Regression (D2 capture): the real agent_type value in live PreToolUse
    # payloads is bundle-qualified, e.g. "plan-marshall:execution-context-level-4".
    # An earlier startswith("execution-context") prefix match silently failed to
    # gate EVERY real sub-agent call whose cwd was not a worktree. Signal 1 MUST
    # fire on the bundle-qualified value.
    payload = {gate.SUB_AGENT_IDENTITY_FIELD: "plan-marshall:execution-context-level-4"}
    assert gate.context_gate(payload) is True


def test_context_gate_true_on_reader_subagent_identity() -> None:
    # The reader variant is also a plan-marshall sub-agent and carries the marker.
    payload = {
        gate.SUB_AGENT_IDENTITY_FIELD: "plan-marshall:execution-context-reader-level-2"
    }
    assert gate.context_gate(payload) is True


# =============================================================================
# Signal 2 — path-boundary precision (regression: substring false-positive)
# =============================================================================


def test_signal2_not_triggered_by_partial_segment_match() -> None:
    # A path that merely contains the WORKTREE_PATH_SEGMENT as a substring but
    # not as a proper directory boundary must NOT trigger Signal 2.
    # E.g. if WORKTREE_PATH_SEGMENT is "worktrees", then a path like
    # "/tmp/fake-worktrees-extra/plans" must not match.
    partial_path = f"/tmp/fake-{gate.WORKTREE_PATH_SEGMENT}-extra/plans"
    payload = {gate.CWD_FIELD: partial_path}
    assert gate.context_gate(payload) is False


def test_signal2_triggered_on_proper_directory_boundary() -> None:
    # A cwd that resolves exactly under the segment as a directory component
    # must trigger Signal 2.
    proper_path = f"/Users/dev/project/{gate.WORKTREE_PATH_SEGMENT}/my-plan/subdir"
    payload = {gate.CWD_FIELD: proper_path}
    assert gate.context_gate(payload) is True


def test_signal2_triggered_on_trailing_segment_match() -> None:
    # A cwd that ends exactly at the segment boundary (no sub-path) also matches.
    trailing_path = f"/Users/dev/project/{gate.WORKTREE_PATH_SEGMENT}"
    payload = {gate.CWD_FIELD: trailing_path}
    assert gate.context_gate(payload) is True


# =============================================================================
# No rule-matcher logic present (enforcement stays in D3)
# =============================================================================


def test_module_exposes_no_rule_matchers() -> None:
    # The shared gate owns parse + accessors + context_gate only; the R1-R5 rule
    # matchers are enforcement-only and must not leak into this module.
    public_names = {name for name in dir(gate) if not name.startswith("_")}
    forbidden = {"match_rules", "rule_matchers", "deny", "permission_decision"}
    assert forbidden.isdisjoint(public_names)
