#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for claude_pretooluse_hook.py — the conditional PreToolUse enforcement leaf.

The leaf is a stdin->stdout hook script, so it is exercised both via subprocess (a
fresh interpreter, exactly as Claude Code would invoke it — proving the whole
fail-open + deny-envelope contract end to end) and via direct import of its pure
``evaluate`` function (proving each R1-R4 matcher and the gate-delegation behaviour
without subprocess overhead).

The shared ``pretooluse_gate`` module is imported directly (sibling-import
scaffolding) so the tests can build realistic in-context fixtures from the gate's
own field-name constants and prove the hook delegates parse/accessors/gate to the
shared module rather than carrying its own field-name copies.

Coverage:
  - Gate fail-open when neither signal fires (emit nothing, exit 0).
  - Signal-1-only enforcement (sub-agent identity carries the execution-context
    marker) and Signal-2-only enforcement (worktree cwd).
  - Each of R1-R4 producing a ``permissionDecision: deny`` with the expected
    redirect-reason substring when the gate is satisfied.
  - Each rule NOT firing on a benign in-context call.
  - Malformed / empty stdin -> no output, exit 0; never raises.
  - Absent Signal-1 field -> falls back to Signal 2 alone.
  - The hook delegates parse/accessors/gate to the shared module (matchers only).
"""

from __future__ import annotations

import json
import sys

from conftest import get_script_path, run_script

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
    output: dict = json.loads(stdout)["hookSpecificOutput"]
    return output


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
    # file-op or hard-coded build, so no rule fires).
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


# -----------------------------------------------------------------------------
# R2 — the `git grep` arm
#
# `git grep` reads file bodies exactly as bare `grep` does, so it joins the
# EXISTING R2 family. The positive controls below all place the subcommand
# somewhere other than tokens[1], which is precisely what a naive
# `tokens[1] == "grep"` check walks past — testing only `git grep foo` would pass
# against that vacuous guard. The negative controls are what make the boundary
# real: a suite carrying only positives would equally pass against an
# implementation that blocks every `git` invocation.
# -----------------------------------------------------------------------------


def test_r2_denies_git_grep_forms() -> None:
    """Every global-option shape still resolves the subcommand to `grep`."""
    for command in (
        "git grep foo",
        "git -C . grep foo",
        "git --no-pager grep foo",
        "/usr/bin/git grep foo",
    ):
        payload = _signal2_payload("Bash", _bash(command))
        assert hook.evaluate(payload) == hook._R2_REASON, command


def test_r2_denies_git_grep_past_value_taking_options() -> None:
    """A value-taking global option consumes its value, not the subcommand slot."""
    for command in (
        "git -c core.pager=cat grep foo",
        "git --git-dir=/repo/.git grep foo",
        "git --work-tree /repo grep foo",
        "git --literal-pathspecs grep foo",
    ):
        payload = _signal2_payload("Bash", _bash(command))
        assert hook.evaluate(payload) == hook._R2_REASON, command


def test_r2_denies_git_grep_past_attached_and_unlisted_options() -> None:
    """Option SHAPES the walker never names must not become the subcommand.

    The regression these pin: when the walk recognised only a named allowlist of
    option spellings, each command below returned its own option token as the
    subcommand (``"-c."``, ``"-p"``, ``"--bare"``), so the ``== "grep"`` test
    missed and ``git grep`` was let through. Every form here is valid ``git``,
    and none of them appears in ``_R2_GIT_VALUE_OPTIONS`` — which is exactly why
    a suite drawn only from that tuple could not detect the gap.
    """
    for command in (
        "git -C. grep foo",  # attached short value
        "git -cvar=val grep foo",  # attached short value, inline config pair
        "git -p grep foo",  # unlisted short flag (--paginate)
        "git --bare grep foo",  # unlisted long flag
        "git --no-optional-locks grep foo",  # unlisted long flag
        "git -C. -p --bare grep foo",  # several stacked together
    ):
        payload = _signal2_payload("Bash", _bash(command))
        assert hook.evaluate(payload) == hook._R2_REASON, command


def test_r2_git_option_skip_is_structural_not_an_allowlist() -> None:
    """No named-option tuple may be the sole thing standing between git and grep.

    Guards the property directly rather than sampling spellings: an option shape
    invented here (one that cannot be in any allowlist) must still resolve to the
    real subcommand. A future edit that narrows the walk back to a membership
    test fails this even if it re-adds every spelling the suite above names.
    """
    assert hook._git_subcommand("git --a-flag-nobody-listed grep foo") == "grep"
    assert hook._git_subcommand("git -Zqx grep foo") == "grep"


def test_r2_not_fired_on_non_grep_git_subcommands_behind_the_same_options() -> None:
    """The matched negative control for the attached/unlisted positives above.

    Skipping every dash-token structurally must not swallow the subcommand slot:
    the SAME option shapes in front of a non-grep subcommand still resolve to
    that subcommand and stay allowed. Without this, an implementation that simply
    blocked every ``git`` call would satisfy the positive controls.
    """
    for command in (
        "git -C. status",
        "git -p log --oneline",
        "git --bare rev-parse HEAD",
        "git -cvar=val diff --name-only",
    ):
        payload = _signal2_payload("Bash", _bash(command))
        assert hook.evaluate(payload) is None, command


def test_r2_detached_value_option_does_not_mistake_its_value_for_grep() -> None:
    """A detached value token is consumed, never read as the subcommand.

    ``-C grep`` names a DIRECTORY called ``grep``; the subcommand is ``status``.
    This is the trap the structural dash-skip alone would not catch, and it is
    why the detached value options still need naming.
    """
    assert hook._git_subcommand("git -C grep status") == "status"
    assert hook.evaluate(_signal2_payload("Bash", _bash("git -C grep status"))) is None


def test_r2_denies_git_grep_behind_a_quoted_detached_value() -> None:
    """A quoted value containing a space must not tear the skip arithmetic.

    ``git -C "repo dir" grep x`` is a real ``git grep`` file-op. Under a
    whitespace split the quoted value becomes two tokens, so the ``-C`` skip
    lands mid-value and the subcommand resolves to ``dir"`` — R2 misses the
    file-op entirely. Shell-lexical splitting keeps the value one token. Both
    quote styles are covered because either spelling is valid shell.
    """
    for command in (
        'git -C "repo dir" grep needle',
        "git -C 'repo dir' grep needle",
    ):
        assert hook._git_subcommand(command) == "grep", command
        payload = _signal2_payload("Bash", _bash(command))
        assert hook.evaluate(payload) == hook._R2_REASON, command


def test_r2_quoted_detached_value_still_allows_non_grep_subcommand() -> None:
    """The negative control for the quoted-value fix — matched pair.

    The same quoted-path shape with a benign subcommand must stay allowed, so
    the fix is proven to resolve the subcommand rather than to blanket-deny any
    command carrying a quoted token.
    """
    command = 'git -C "repo dir" status'
    assert hook._git_subcommand(command) == "status"
    assert hook.evaluate(_signal2_payload("Bash", _bash(command))) is None


def test_git_subcommand_falls_back_to_whitespace_split_on_bad_quoting() -> None:
    """Malformed quoting degrades to the whitespace split, never to a bypass.

    An unbalanced quote makes ``shlex`` raise. Returning ``""`` there would turn
    a lexer error into a silent R2 bypass, so the fallback preserves the
    pre-existing whitespace-split detection instead.
    """
    assert hook._git_subcommand('git -C "unbalanced grep needle') == "grep"


def test_r2_not_fired_on_non_grep_git_subcommands() -> None:
    """Ordinary git usage must keep working — these are not file-ops."""
    for command in (
        "git status",
        "git log --oneline -5",
        "git diff --name-only HEAD",
        "git rev-parse HEAD",
    ):
        payload = _signal2_payload("Bash", _bash(command))
        assert hook.evaluate(payload) is None, command


def test_r2_not_fired_on_git_log_grep_option() -> None:
    """`git log --grep=fix` is a COMMIT-MESSAGE search, and stays allowed.

    The trap a sloppy substring check breaks: the string ``grep`` appears in the
    command, but it is an option to ``log``, not the subcommand, and searching
    commit messages is not a file-content operation. This is the single most
    discriminating negative control in the arm.
    """
    payload = _signal2_payload("Bash", _bash("git log --grep=fix"))
    assert hook.evaluate(payload) is None


def test_r2_not_fired_on_bare_git() -> None:
    """A `git` call with no subcommand resolves to no subcommand, so it passes."""
    assert hook.evaluate(_signal2_payload("Bash", _bash("git"))) is None


def test_r2_reason_names_the_sanctioned_content_search_replacement() -> None:
    """The redirect must name the replacement, not just refuse the call.

    Blocking `git grep` is only legitimate because a sanctioned content-search
    path exists; the reason string is where the caller learns it.
    """
    assert "architecture search --content" in hook._R2_REASON


# =============================================================================
# R3 — generated-executor edit
# =============================================================================


def test_r3_denies_edit_of_generated_executor() -> None:
    payload = {
        gate.CWD_FIELD: _worktree_cwd(),
        "tool_name": "Edit",
        "tool_input": {"file_path": ".plan/execute-script.py"},
    }
    assert hook.evaluate(payload) == hook._R3_REASON


def test_r3_denies_write_with_absolute_path() -> None:
    payload = {
        gate.CWD_FIELD: _worktree_cwd(),
        "tool_name": "Write",
        "tool_input": {"file_path": "/Users/dev/project/.plan/execute-script.py"},
    }
    assert hook.evaluate(payload) == hook._R3_REASON


def test_r3_not_fired_on_other_path() -> None:
    payload = {
        gate.CWD_FIELD: _worktree_cwd(),
        "tool_name": "Edit",
        "tool_input": {"file_path": "marketplace/bundles/plan-marshall/foo.py"},
    }
    assert hook.evaluate(payload) is None


# =============================================================================
# R4 — hard-coded build
# =============================================================================


def test_r4_denies_pw() -> None:
    assert (
        hook.evaluate(_signal2_payload("Bash", _bash("./pw verify"))) == hook._R4_REASON
    )


def test_r4_denies_bare_build_programs() -> None:
    for prog in ("mvn", "npm", "gradle"):
        payload = _signal2_payload("Bash", _bash(f"{prog} build"))
        assert hook.evaluate(payload) == hook._R4_REASON


def test_r4_not_fired_on_resolved_build() -> None:
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


# =============================================================================
# _program_name — path-prefix normalization
# =============================================================================


def test_program_name_strips_absolute_path_prefix() -> None:
    assert hook._program_name("/usr/bin/cat") == "cat"


def test_program_name_strips_bin_path_prefix() -> None:
    assert hook._program_name("/bin/grep") == "grep"


def test_program_name_preserves_bare_name() -> None:
    assert hook._program_name("cat") == "cat"


def test_program_name_preserves_pw_literal() -> None:
    # ./pw is matched as a literal in R4; _program_name must not strip it.
    assert hook._program_name("./pw") == "./pw"


def test_program_name_returns_empty_on_empty_command() -> None:
    assert hook._program_name("") == ""


# =============================================================================
# R2/R4 — path-prefixed bypass prevention
# =============================================================================


def test_r2_denies_path_prefixed_cat() -> None:
    # /usr/bin/cat must trip R2 the same as bare cat.
    assert hook.evaluate(_signal2_payload("Bash", _bash("/usr/bin/cat file.txt"))) == hook._R2_REASON


def test_r2_denies_path_prefixed_grep() -> None:
    assert hook.evaluate(_signal2_payload("Bash", _bash("/bin/grep pattern file"))) == hook._R2_REASON


def test_r4_denies_path_prefixed_mvn() -> None:
    # /usr/local/bin/mvn must trip R4 the same as bare mvn.
    assert hook.evaluate(_signal2_payload("Bash", _bash("/usr/local/bin/mvn verify"))) == hook._R4_REASON


def test_r4_denies_path_prefixed_npm() -> None:
    assert hook.evaluate(_signal2_payload("Bash", _bash("/usr/bin/npm install"))) == hook._R4_REASON
