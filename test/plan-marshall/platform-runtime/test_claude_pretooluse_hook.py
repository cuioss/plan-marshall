#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for claude_pretooluse_hook.py — the conditional PreToolUse enforcement leaf.

The leaf is a stdin->stdout hook script, so it is exercised both via subprocess (a
fresh interpreter, exactly as Claude Code would invoke it — proving the whole
fail-open + deny-envelope contract end to end) and via direct import of its pure
``evaluate`` function (proving each R1–R5 matcher and the gate-delegation behaviour
without subprocess overhead).

The shared ``pretooluse_gate`` module is imported directly (sibling-import
scaffolding) so the tests can build realistic in-context fixtures from the gate's
own field-name constants and prove the hook delegates parse/accessors/gate to the
shared module rather than carrying its own field-name copies.

Coverage:
  - Gate fail-open when neither signal fires (emit nothing, exit 0).
  - Signal-1-only enforcement (sub-agent identity carries the execution-context
    marker) and Signal-2-only enforcement (worktree cwd).
  - Each of R1–R5 producing a ``permissionDecision: deny`` with the expected
    redirect-reason substring when the gate is satisfied.
  - Each rule NOT firing on a benign in-context call.
  - Malformed / empty stdin -> no output, exit 0; never raises.
  - Absent Signal-1 field -> falls back to Signal 2 alone.
  - The hook delegates parse/accessors/gate to the shared module (matchers only).
"""

from __future__ import annotations

import json
import sys

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path(
    "plan-marshall", "platform-runtime", "claude_pretooluse_hook.py"
)
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import pretooluse_gate as gate  # noqa: E402
import claude_pretooluse_hook as hook  # noqa: E402


# =============================================================================
# Helpers
# =============================================================================

#: A realistic bundle-qualified sub-agent identity that carries the
#: execution-context marker (Signal 1), as confirmed against real payloads.
_SUB_AGENT_IDENTITY = "plan-marshall:execution-context-level-4"


def _worktree_cwd() -> str:
    """A cwd resolving under the plan-worktree path segment (Signal 2)."""
    return f"/Users/dev/project/{gate.WORKTREE_PATH_SEGMENT}/my-plan"


def _signal1_payload(tool_name: str, tool_input: dict) -> dict:
    """Payload satisfying the gate via Signal 1 only (sub-agent identity)."""
    return {
        gate.SUB_AGENT_IDENTITY_FIELD: _SUB_AGENT_IDENTITY,
        "tool_name": tool_name,
        "tool_input": tool_input,
    }


def _signal2_payload(tool_name: str, tool_input: dict) -> dict:
    """Payload satisfying the gate via Signal 2 only (worktree cwd)."""
    return {
        gate.CWD_FIELD: _worktree_cwd(),
        "tool_name": tool_name,
        "tool_input": tool_input,
    }


def _bash(command: str) -> dict:
    return {"command": command}


def _run(payload_json: str):
    """Run the enforcement leaf via subprocess with the given stdin JSON."""
    return run_script(SCRIPT_PATH, input_data=payload_json)


def _decision(stdout: str) -> dict:
    """Parse the deny envelope's hookSpecificOutput from leaf stdout."""
    return json.loads(stdout)["hookSpecificOutput"]


# =============================================================================
# Gate fail-open — neither signal fires
# =============================================================================


def test_emits_nothing_when_neither_signal_fires() -> None:
    payload = {"tool_name": "Bash", "tool_input": _bash("cat foo"), "cwd": "/tmp"}
    result = _run(json.dumps(payload))

    assert result.returncode == 0
    assert result.stdout == ""


def test_evaluate_none_when_gate_unsatisfied_even_on_violation() -> None:
    # A clear R2 violation but no signal -> fail OPEN, no deny.
    payload = {"tool_name": "Bash", "tool_input": _bash("grep x file")}
    assert hook.evaluate(payload) is None


# =============================================================================
# Signal-1-only and Signal-2-only enforcement
# =============================================================================


def test_signal1_only_enforces() -> None:
    payload = _signal1_payload("Bash", _bash("cat foo"))
    result = _run(json.dumps(payload))

    assert result.returncode == 0
    assert _decision(result.stdout)["permissionDecision"] == "deny"


def test_signal2_only_enforces() -> None:
    payload = _signal2_payload("Bash", _bash("cat foo"))
    assert hook.evaluate(payload) == hook._R2_REASON


def test_absent_signal1_falls_back_to_signal2() -> None:
    # No sub-agent identity field at all; Signal 2 alone satisfies the gate.
    payload = {
        "cwd": _worktree_cwd(),
        "tool_name": "Bash",
        "tool_input": _bash("ls -la"),
    }
    assert hook.evaluate(payload) == hook._R2_REASON


# =============================================================================
# R1 — shell-construct compound
# =============================================================================


def test_r1_denies_and_chain() -> None:
    assert hook.evaluate(_signal1_payload("Bash", _bash("a && b"))) == hook._R1_REASON


def test_r1_denies_semicolon() -> None:
    assert hook.evaluate(_signal2_payload("Bash", _bash("a; b"))) == hook._R1_REASON


def test_r1_denies_background() -> None:
    assert hook.evaluate(_signal2_payload("Bash", _bash("server &"))) == hook._R1_REASON


def test_r1_denies_newline() -> None:
    assert hook.evaluate(_signal2_payload("Bash", _bash("a\nb"))) == hook._R1_REASON


def test_r1_denies_command_substitution() -> None:
    assert (
        hook.evaluate(_signal2_payload("Bash", _bash("echo $(date)")))
        == hook._R1_REASON
    )


def test_r1_denies_for_loop() -> None:
    assert (
        hook.evaluate(_signal2_payload("Bash", _bash("for f in *; do echo $f; done")))
        == hook._R1_REASON
    )


def test_r1_denies_while_loop() -> None:
    assert (
        hook.evaluate(_signal2_payload("Bash", _bash("while true; do echo x; done")))
        == hook._R1_REASON
    )


def test_r1_denies_leading_env_assignment() -> None:
    assert (
        hook.evaluate(_signal2_payload("Bash", _bash("FOO=bar python3 x.py")))
        == hook._R1_REASON
    )


def test_r1_not_fired_on_plain_command() -> None:
    # A single command with no shell construct does not trip R1 (and is not a
    # file-op / provider / build, so no rule fires).
    assert hook.evaluate(_signal2_payload("Bash", _bash("python3 script.py"))) is None


# =============================================================================
# R2 — Bash file-ops
# =============================================================================


def test_r2_denies_each_file_op() -> None:
    for prog in ("cat", "grep", "head", "tail", "find", "ls"):
        payload = _signal2_payload("Bash", _bash(f"{prog} something"))
        assert hook.evaluate(payload) == hook._R2_REASON


def test_r2_not_fired_on_substring_program() -> None:
    # A program whose name merely contains a file-op substring is not a file-op.
    assert hook.evaluate(_signal2_payload("Bash", _bash("category --help"))) is None


# =============================================================================
# R3 — direct gh / glab
# =============================================================================


def test_r3_denies_gh() -> None:
    assert (
        hook.evaluate(_signal2_payload("Bash", _bash("gh pr create"))) == hook._R3_REASON
    )


def test_r3_denies_glab() -> None:
    assert (
        hook.evaluate(_signal2_payload("Bash", _bash("glab mr list")))
        == hook._R3_REASON
    )


def test_r3_not_fired_on_other_command() -> None:
    assert hook.evaluate(_signal2_payload("Bash", _bash("github-cli --help"))) is None


# =============================================================================
# R4 — generated-executor edit
# =============================================================================


def test_r4_denies_edit_of_generated_executor() -> None:
    payload = {
        gate.CWD_FIELD: _worktree_cwd(),
        "tool_name": "Edit",
        "tool_input": {"file_path": ".plan/execute-script.py"},
    }
    assert hook.evaluate(payload) == hook._R4_REASON


def test_r4_denies_write_with_absolute_path() -> None:
    payload = {
        gate.CWD_FIELD: _worktree_cwd(),
        "tool_name": "Write",
        "tool_input": {"file_path": "/Users/dev/project/.plan/execute-script.py"},
    }
    assert hook.evaluate(payload) == hook._R4_REASON


def test_r4_not_fired_on_other_path() -> None:
    payload = {
        gate.CWD_FIELD: _worktree_cwd(),
        "tool_name": "Edit",
        "tool_input": {"file_path": "marketplace/bundles/plan-marshall/foo.py"},
    }
    assert hook.evaluate(payload) is None


# =============================================================================
# R5 — hard-coded build
# =============================================================================


def test_r5_denies_pw() -> None:
    assert (
        hook.evaluate(_signal2_payload("Bash", _bash("./pw verify"))) == hook._R5_REASON
    )


def test_r5_denies_bare_build_programs() -> None:
    for prog in ("mvn", "npm", "gradle"):
        payload = _signal2_payload("Bash", _bash(f"{prog} build"))
        assert hook.evaluate(payload) == hook._R5_REASON


def test_r5_not_fired_on_resolved_build() -> None:
    # The architecture-resolved executor call is a plain python3 invocation and
    # trips no rule.
    cmd = "python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run"
    assert hook.evaluate(_signal2_payload("Bash", _bash(cmd))) is None


# =============================================================================
# Deny envelope shape (subprocess, end-to-end)
# =============================================================================


def test_deny_envelope_shape() -> None:
    payload = _signal2_payload("Bash", _bash("cat foo"))
    result = _run(json.dumps(payload))

    assert result.returncode == 0
    decision = _decision(result.stdout)
    assert decision["hookEventName"] == "PreToolUse"
    assert decision["permissionDecision"] == "deny"
    assert isinstance(decision["permissionDecisionReason"], str)
    assert decision["permissionDecisionReason"]


# =============================================================================
# Never blocks on malformed / empty stdin
# =============================================================================


def test_exits_zero_and_silent_on_empty_stdin() -> None:
    result = _run("")
    assert result.returncode == 0
    assert result.stdout == ""


def test_exits_zero_and_silent_on_malformed_stdin() -> None:
    result = _run("not json {{{")
    assert result.returncode == 0
    assert result.stdout == ""


def test_evaluate_never_raises_on_non_dict_payload() -> None:
    # gate.parse returns {} for non-object input, but defensively prove evaluate
    # tolerates a {} payload (gate unsatisfied -> None).
    assert hook.evaluate({}) is None


# =============================================================================
# Delegation to the shared gate (matchers only — no field-name copies)
# =============================================================================


def test_gate_decision_matches_shared_module() -> None:
    # A payload the shared gate rules out-of-context must NOT enforce, even with
    # an otherwise-matching violation -> proves the hook calls context_gate.
    payload = {"tool_name": "Bash", "tool_input": _bash("cat foo"), "cwd": "/tmp"}
    assert gate.context_gate(payload) is False
    assert hook.evaluate(payload) is None


def test_marker_value_satisfies_signal1() -> None:
    # The bundle-qualified identity carries the gate's execution-context marker.
    assert gate.EXECUTION_CONTEXT_MARKER in _SUB_AGENT_IDENTITY
    payload = _signal1_payload("Read", {"file_path": "x"})
    # Read is a benign non-matching tool: gate satisfied, but no rule fires.
    assert hook.evaluate(payload) is None
