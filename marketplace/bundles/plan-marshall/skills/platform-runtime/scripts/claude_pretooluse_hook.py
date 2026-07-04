#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Conditional PreToolUse enforcement leaf for Claude Code.

Registered (opt-in) as a matcher-less ``hooks.PreToolUse`` entry. It blocks four
mechanically-checkable hard-rule violation families, but ONLY when the call
originates inside a plan-marshall plan context. Outside that context — and on
every error path — it emits nothing and exits 0, so a hook bug can never block
the user (fail OPEN).

ALL payload parsing, field access, and the context-gate predicate are delegated
to the shared ``pretooluse_gate`` module — this leaf adds NO field-name knowledge
of its own. The only logic it owns is the R1-R4 rule matchers and the
``permissionDecision: deny`` envelope layered on top:

- **R1 shell-construct compound** — a Bash command containing ``&&``, ``;``,
  ``&``, a newline, a ``for``/``while`` loop, ``$(...)`` command substitution, or
  a leading ``VAR=val cmd`` inline env-var assignment.
- **R2 Bash file-ops** — a Bash command whose program is ``cat`` / ``grep`` /
  ``head`` / ``tail`` / ``find`` / ``ls``.
- **R3 generated-executor edit** — an Edit/Write whose path is the generated
  ``.plan/execute-script.py``.
- **R4 hard-coded build** — a Bash command invoking ``./pw`` or a bare ``mvn`` /
  ``npm`` / ``gradle``.

Control flow:

1. Parse stdin via ``gate.parse`` (empty/malformed → emit nothing, exit 0).
2. Apply ``gate.context_gate(payload)`` (``Signal1 OR Signal2``) — false → emit
   nothing, exit 0 (fail OPEN).
3. Run the matchers against ``gate.tool_name(payload)`` /
   ``gate.tool_input(payload)``; on the FIRST match, emit the deny envelope with
   a one-line redirect reason. No match → emit nothing, exit 0.

The whole leaf is best-effort/no-raise: any internal error degrades to a silent
no-op (emit nothing, exit 0).

Usage (invoked by Claude Code's PreToolUse hook mechanism, not directly):
    echo '{"tool_name": "Bash", "tool_input": {"command": "cat x"},
           "cwd": "/repo/.plan/local/worktrees/p"}' \\
        | python3 claude_pretooluse_hook.py
"""
from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable
from typing import Any

import pretooluse_gate as gate

# =============================================================================
# Rule-matcher constants — enforcement-only knowledge that lives in this leaf.
# (Payload-field knowledge lives in pretooluse_gate; these constants describe
# what counts as a violation, not how to read the payload.)
# =============================================================================

#: Tool name whose ``command`` string the Bash-family matchers (R1/R2/R4)
#: inspect.
_BASH_TOOL = "Bash"

#: Tool names whose ``file_path`` the R3 generated-executor matcher inspects.
_FILE_EDIT_TOOLS = ("Edit", "Write")

#: Generated executor path R3 forbids editing. Matched on the path tail so an
#: absolute or worktree-relative path both trip the rule.
_GENERATED_EXECUTOR_TAIL = ".plan/execute-script.py"

#: R1 — literal shell-construct substrings that mark a compound/marshalled
#: command. A newline is matched separately (see ``_match_r1_shell_construct``).
_R1_SHELL_SUBSTRINGS = ("&&", ";", "&", "$(", "`")

#: R1 — loop-keyword pattern (``for`` / ``while`` as a leading shell keyword).
_R1_LOOP_RE = re.compile(r"(?:^|[;&|]|\bdo\b)\s*(?:for|while)\b")

#: R1 — leading ``VAR=val cmd`` inline env-var assignment (an assignment token
#: followed by whitespace and a command word).
_R1_LEADING_ASSIGNMENT_RE = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*=\S*\s+\S")

#: R2 — Bash file-operation programs that have dedicated Read/Glob/Grep tools.
_R2_FILE_OPS = ("cat", "grep", "head", "tail", "find", "ls")

#: R4 — hard-coded build invocations that must be resolved via the architecture
#: API. ``./pw`` is matched as a literal; ``mvn`` / ``npm`` / ``gradle`` as bare
#: leading programs or path-prefixed executables (e.g. ``/usr/local/bin/mvn``).
_R4_BUILD_PROGRAMS = ("mvn", "npm", "gradle")

#: Per-rule one-line redirect reasons surfaced as ``permissionDecisionReason``.
_R1_REASON = (
    "plan-marshall: one command per Bash call — no '&&', ';', '&', newline, "
    "for/while, $(...), or leading VAR=val; use separate Bash calls or "
    "dedicated tools."
)
_R2_REASON = (
    "plan-marshall: use the Read/Glob/Grep tools, not Bash, for file "
    "operations (cat/grep/head/tail/find/ls)."
)
_R3_REASON = (
    "plan-marshall: never edit the generated .plan/execute-script.py — "
    "regenerate it via /sync-plugin-cache + /marshall-steward."
)
_R4_REASON = (
    "plan-marshall: never hard-code build commands (./pw, mvn, npm, gradle) — "
    "resolve via plan-marshall:manage-architecture:architecture resolve."
)


def _first_word(command: str) -> str:
    """Return the first whitespace-delimited token of *command*, lowercased.

    Best-effort: returns ``""`` when *command* is empty or whitespace-only.
    """
    stripped = command.strip()
    if not stripped:
        return ""
    return stripped.split()[0].lower()


def _program_name(command: str) -> str:
    """Return the normalized executable name from the first command token.

    Strips any leading path component so that ``/bin/cat``, ``/usr/bin/cat``,
    and ``cat`` all resolve to ``"cat"``.  The special ``./pw`` token is
    preserved as-is so the R4 literal check continues to work.
    """
    token = _first_word(command)
    if not token or token == "./pw":
        return token
    # Strip path prefix (e.g. /usr/bin/cat -> cat) but keep bare names intact.
    return token.rsplit("/", 1)[-1]


def _bash_command(tool_name: str | None, tool_input: dict[str, Any]) -> str | None:
    """Return the Bash ``command`` string, or ``None`` for a non-Bash call.

    Returns ``None`` when *tool_name* is not ``Bash`` or the ``command`` value is
    absent / not a non-empty string.
    """
    if tool_name != _BASH_TOOL:
        return None
    value = tool_input.get("command")
    if isinstance(value, str) and value:
        return value
    return None


def _match_r1_shell_construct(
    tool_name: str | None, tool_input: dict[str, Any]
) -> str | None:
    """R1 — Bash command containing a shell-construct compound marker."""
    command = _bash_command(tool_name, tool_input)
    if command is None:
        return None
    if "\n" in command:
        return _R1_REASON
    if any(token in command for token in _R1_SHELL_SUBSTRINGS):
        return _R1_REASON
    if _R1_LOOP_RE.search(command):
        return _R1_REASON
    if _R1_LEADING_ASSIGNMENT_RE.search(command):
        return _R1_REASON
    return None


def _match_r2_file_ops(
    tool_name: str | None, tool_input: dict[str, Any]
) -> str | None:
    """R2 — Bash command whose program is a file-op with a dedicated tool."""
    command = _bash_command(tool_name, tool_input)
    if command is None:
        return None
    if _program_name(command) in _R2_FILE_OPS:
        return _R2_REASON
    return None


def _match_r3_generated_executor(
    tool_name: str | None, tool_input: dict[str, Any]
) -> str | None:
    """R3 — Edit/Write whose target path is the generated executor."""
    if tool_name not in _FILE_EDIT_TOOLS:
        return None
    path = tool_input.get("file_path")
    if not isinstance(path, str) or not path:
        return None
    normalized = path.replace("\\", "/")
    if normalized == _GENERATED_EXECUTOR_TAIL or normalized.endswith(
        "/" + _GENERATED_EXECUTOR_TAIL
    ):
        return _R3_REASON
    return None


def _match_r4_hardcoded_build(
    tool_name: str | None, tool_input: dict[str, Any]
) -> str | None:
    """R4 — Bash command invoking ./pw or a bare mvn/npm/gradle."""
    command = _bash_command(tool_name, tool_input)
    if command is None:
        return None
    first = _first_word(command)
    if first == "./pw" or _program_name(command) in _R4_BUILD_PROGRAMS:
        return _R4_REASON
    return None


#: Ordered rule chain — the first matcher returning a reason wins.
_RULES: tuple[Callable[[str | None, dict[str, Any]], str | None], ...] = (
    _match_r1_shell_construct,
    _match_r2_file_ops,
    _match_r3_generated_executor,
    _match_r4_hardcoded_build,
)


def evaluate(payload: dict[str, Any]) -> str | None:
    """Return the deny reason for the first matched rule, or ``None``.

    Applies the shared context gate first (``Signal1 OR Signal2``); when the gate
    is not satisfied, returns ``None`` (fail OPEN — no enforcement). When the gate
    is satisfied, runs the R1-R4 matchers in order against the shared gate's
    ``tool_name`` / ``tool_input`` accessors and returns the first matching rule's
    redirect reason, or ``None`` when no rule fires.

    Args:
        payload: The parsed PreToolUse payload.

    Returns:
        The ``permissionDecisionReason`` string when a rule denies the call, or
        ``None`` when the gate is unsatisfied or no rule matches.
    """
    if not gate.context_gate(payload):
        return None
    tool_name = gate.tool_name(payload)
    tool_input = gate.tool_input(payload)
    for rule in _RULES:
        reason = rule(tool_name, tool_input)
        if reason is not None:
            return reason
    return None


def _deny_envelope(reason: str) -> dict[str, Any]:
    """Build the Claude Code PreToolUse ``deny`` envelope carrying *reason*."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def main() -> int:
    """Read stdin, deny on a gated rule match, else emit nothing — always exit 0.

    Best-effort/no-raise throughout: any unexpected error degrades to a silent
    no-op so a hook bug can never block a tool call.
    """
    try:
        raw = sys.stdin.read()
        payload = gate.parse(raw)
        reason = evaluate(payload)
        if reason is not None:
            sys.stdout.write(json.dumps(_deny_envelope(reason)))
            sys.stdout.flush()
    except Exception:
        # Whole-leaf fail-open contract: any error path emits nothing and exits 0
        # so the user is never blocked by a hook bug.
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
