#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
ClaudeRuntime — Claude Code implementation of all 15 platform-runtime operations.

Implements every abstract method from Runtime (runtime_base.py) for the Claude Code
target.  All responses are serialized TOON strings built via the toon_success,
toon_error, and toon_noop helpers from runtime_base.

TOON output is consumed by manage-* skills and by platform_runtime.py (the router).
Follows the tools-script-executor / ref-toon-format compliance contract documented
in SKILL.md.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Bootstrap sys.path so sibling skill libraries resolve without the executor.
# Walk up from this script to the skills/ root, then append each library dir.
for _ancestor in Path(__file__).resolve().parents:
    if _ancestor.name == "skills" and (_ancestor.parent / ".claude-plugin" / "plugin.json").is_file():
        for _lib in (
            "ref-toon-format",
            "manage-terminal-title",
            "tools-file-ops",
            "script-shared",
        ):
            _lib_path = str(_ancestor / _lib / "scripts")
            if _lib_path not in sys.path:
                sys.path.append(_lib_path)
        break

from manage_terminal_title import _compose_body, compose  # noqa: E402,F401
from runtime_base import Runtime, toon_error, toon_noop, toon_success  # noqa: E402,F401
from toon_parser import parse_toon  # noqa: E402

# ---------------------------------------------------------------------------
# Session cache helpers — shared constants
# ---------------------------------------------------------------------------

_PLAN_DIR_NAME = os.environ.get("PLAN_DIR_NAME", ".plan")
_SESSION_CACHE_BASE = Path.home() / ".cache" / "plan-marshall" / "sessions"
_CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"

# Pattern: assistant messages in JSONL with usage data
_USAGE_FIELD_RE = re.compile(
    r"^\s*(total_tokens|input_tokens|output_tokens)\s*:\s*(\d+)",
    re.MULTILINE,
)

# Pattern: canonical UUID format for session identifiers. The session_id
# originates from an external hook payload and is interpolated into file
# paths and glob patterns, so it MUST be validated against this strict
# format before any filesystem use to prevent path traversal and glob
# injection.
_SESSION_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)

# ---------------------------------------------------------------------------
# Transcript engine — Claude-shaped normalized-token computation.
#
# This block is the home of the Claude session-transcript engine, relocated
# from manage-metrics: the ``~/.claude/projects/.../{session_id}.jsonl`` layout,
# the ``{session_id}/subagents/agent-*.jsonl`` discovery, the ``<usage>`` return
# tag, the ``message.usage`` four-field parse, and the Anthropic cache-pricing
# weights. ``manage-metrics`` consumes the normalized numbers this engine emits
# and never parses a transcript itself.
# ---------------------------------------------------------------------------

# Matches an embedded ``<usage>...</usage>`` block in subagent tool-result text.
_USAGE_TAG_RE = re.compile(r"<usage>([\s\S]*?)</usage>", re.MULTILINE)

# Matches the single-figure fields inside a ``<usage>`` tag body. The subagent
# return tag carries a single token figure with no input/output split and no
# cache fields, so these are the only keys it ever contains.
_USAGE_TAG_FIELD_RE = re.compile(
    r"^\s*(total_tokens|subagent_tokens|tool_uses|duration_ms)\s*:\s*(\d+)",
    re.MULTILINE,
)

# Session-id match used by the subagent-transcript discovery (unanchored, to
# match the legacy manage-metrics ``re.fullmatch`` semantics over the same
# canonical UUID shape).
_TRANSCRIPT_SESSION_ID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)

# The four distinct Claude API usage fields. These live only in the raw
# subagent-transcript ``message.usage`` dicts — the subagent ``<usage>`` return
# tag carries a single token figure with no input/output split and no cache
# fields.
_USAGE_FOUR_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
)

# Billing weights (request-stated approximations): a cached read is ~0.1x the
# cost of an input token, and a cache creation write is ~1.25x. The weighted
# total is a billing-cost figure, NOT a work-comparable measure — cache_read
# sums context re-reads across turns.
_BILLING_WEIGHT_CACHE_READ = 0.1
_BILLING_WEIGHT_CACHE_CREATION = 1.25

# Missing-executor guard. While a worktree-backed plan sits mid-phase-5 the
# executor can be absent from the main checkout's cwd. Each executor-invoking
# hook command is wrapped so an absent ``.plan/execute-script.py`` is a silent
# no-op: ``[ -f ... ]`` is false, so the ``python3`` invocation never runs and no
# ``[Errno 2] No such file or directory`` is surfaced as a "hook blocked" error.
# A present executor runs the command normally. The trailing ``|| true`` keeps
# the cosmetic terminal-title hook fail-soft on ANY command error — a
# title-render failure must never block the user's prompt. These wrap the command
# constants at their single source, so every install site inherits the guard.
_EXECUTOR_GUARD_PREFIX = "[ -f .plan/execute-script.py ] && "
_EXECUTOR_GUARD_SUFFIX = " || true"

# Hook command installed by project initial-setup. Captures $CLAUDE_CODE_SESSION_ID
# and stores it via manage-status; the renderer reads this cache to resolve the
# active plan for the current session.
_HOOK_COMMAND = (
    f"{_EXECUTOR_GUARD_PREFIX}"
    "python3 .plan/execute-script.py plan-marshall:platform-runtime:claude_hook"
    f"{_EXECUTOR_GUARD_SUFFIX}"
)

# Render-title hook command installed across all eight render-trigger events
# plus statusLine. Invoked by Claude Code on SessionStart (matcher-less + matcher
# "clear"), UserPromptSubmit, Notification, Stop, PreToolUse:AskUserQuestion,
# PreToolUse:Bash, PostToolUse:AskUserQuestion, and PostToolUse:Bash; the
# statusLine variant appends ``--statusline`` for plain-text emission. The
# PreToolUse:Bash entry surfaces the ⚙ busy icon BEFORE a long-running shell
# command runs, so the title no longer shows the misleading ➤ active arrow
# while the command is in flight. The statusLine variant is
# built explicitly (not by appending to the guarded render command) so
# ``--statusline`` lands on the python3 invocation, not after ``|| true``.
_RENDER_HOOK_COMMAND = (
    f"{_EXECUTOR_GUARD_PREFIX}"
    "python3 .plan/execute-script.py "
    "plan-marshall:platform-runtime:platform_runtime session render-title"
    f"{_EXECUTOR_GUARD_SUFFIX}"
)
_STATUSLINE_COMMAND = (
    f"{_EXECUTOR_GUARD_PREFIX}"
    "python3 .plan/execute-script.py "
    "plan-marshall:platform-runtime:platform_runtime session render-title --statusline"
    f"{_EXECUTOR_GUARD_SUFFIX}"
)

# Conditional PreToolUse enforcement hook command. Installed (opt-in) as a
# matcher-less ``hooks.PreToolUse`` entry, ORTHOGONAL to the terminal-title
# render wiring: it invokes the enforcement leaf that blocks the four hard-rule
# violation families inside a plan-marshall plan context (fail-open everywhere
# else). Keyed on its own command string so its present/MISSING detection is
# independent of the render-entry detection.
_ENFORCEMENT_HOOK_COMMAND = (
    f"{_EXECUTOR_GUARD_PREFIX}"
    "python3 .plan/execute-script.py "
    "plan-marshall:platform-runtime:claude_pretooluse_hook"
    f"{_EXECUTOR_GUARD_SUFFIX}"
)

# Render-trigger hook events that each receive a single matcher-less entry
# invoking the renderer. SessionStart receives BOTH a matcher-less entry AND a
# ``matcher: "clear"`` entry, so it is handled separately below.
_RENDER_TRIGGER_EVENTS: tuple[str, ...] = (
    "UserPromptSubmit",
    "Notification",
    "Stop",
)

# The terminal-title icon palette and body-format logic now live in the
# ``manage-terminal-title`` library skill (consumed via ``compose`` above). This
# module is the resolve+read+emit layer only: it reads ``status.json`` and emits
# the OSC/statusLine bytes the composer returns.
#
# The composer is target-neutral — it knows nothing about Claude hook events. The
# Claude-specific event → neutral-process-state mapping lives HERE (the Claude
# runtime), and the resolved neutral state is what gets passed to ``compose``.


def _claude_event_to_process_state(
    hook_event_name: str | None, tool_name: str | None
) -> str | None:
    """Map a Claude hook event (+ optional tool name) to a neutral process state.

    Returns one of the ``manage_terminal_title.PROCESS_STATES`` values, or
    ``None`` when no event was supplied (the composer then applies its active
    default). This is the Claude-target-specific half of the old ``resolve_icon``
    logic, relocated out of the pure composer:

    - ``Stop`` → ``"done"``
    - ``Notification`` → ``"waiting"``
    - ``PreToolUse`` + ``tool_name == "AskUserQuestion"`` → ``"waiting"``
    - ``PreToolUse`` + ``tool_name == "Bash"`` → ``"busy"``
    - ``UserPromptSubmit`` / ``SessionStart`` / ``PostToolUse`` (any tool) and
      any other event → ``"active"``
    - missing event → ``None`` (composer applies the active default)
    """
    if hook_event_name is None:
        return None
    if hook_event_name == "Stop":
        return "done"
    if hook_event_name == "Notification":
        return "waiting"
    if hook_event_name == "PreToolUse" and tool_name == "AskUserQuestion":
        return "waiting"
    if hook_event_name == "PreToolUse" and tool_name == "Bash":
        return "busy"
    return "active"


# The four build-wrapper executor notations that route a long-running
# build/orchestration command through the executor. The ``PreToolUse:Bash``
# render hook anchors its build-command detection on these substrings: the
# canonical ``verify`` / ``coverage`` / ``quality-gate`` / ``module-tests`` verbs
# are passed AS ``--command-args`` to these same wrappers, so a wrapper-notation
# match already covers them without matching a bare verb word.
_BUILD_WRAPPER_NOTATIONS: tuple[str, ...] = (
    "plan-marshall:build-pyproject",
    "plan-marshall:build-maven",
    "plan-marshall:build-gradle",
    "plan-marshall:build-npm",
)


def _command_is_build(command: str | None) -> bool:
    """Return True when *command* routes a long-running build through the executor.

    Detection anchors on the four build-wrapper executor notation substrings in
    :data:`_BUILD_WRAPPER_NOTATIONS`. A match means the Bash call is a build /
    orchestration invocation that should surface the persistent 🔨 ``build-busy``
    terminal-title state for its duration. An empty / ``None`` command, or any
    command that names none of the wrapper notations, returns False (the existing
    ``PreToolUse:Bash`` → ⚙ busy mapping remains the fallback).

    Never matches on a bare verb word alone (e.g. ``echo verify``): the canonical
    ``verify`` / ``coverage`` / ``quality-gate`` / ``module-tests`` verbs are
    passed as ``--command-args`` to the wrappers, so a wrapper-notation match
    already covers them — anchoring on the notation keeps the predicate precise
    and low-false-positive.
    """
    if not command:
        return False
    return any(notation in command for notation in _BUILD_WRAPPER_NOTATIONS)


# Required render-trigger entries inspected by the ``display`` health check, in
# report order. Each tuple is (label, hooks_block_key, matcher). The label is the
# token the menu doc tells the user to read; it matches the ``installed_events``
# naming from ``_install_terminal_title_hooks`` exactly, except SessionStart is
# split into its two matcher variants so a partial install is named per-line.
_DISPLAY_RENDER_ENTRIES: tuple[tuple[str, str, str], ...] = (
    ("SessionStart:matcher-less", "SessionStart", ""),
    ("SessionStart:clear", "SessionStart", "clear"),
    ("UserPromptSubmit", "UserPromptSubmit", ""),
    ("Notification", "Notification", ""),
    ("Stop", "Stop", ""),
    ("PreToolUse:AskUserQuestion", "PreToolUse", "AskUserQuestion"),
    ("PreToolUse:Bash", "PreToolUse", "Bash"),
    ("PostToolUse:AskUserQuestion", "PostToolUse", "AskUserQuestion"),
    ("PostToolUse:Bash", "PostToolUse", "Bash"),
)


def _diagnose_display_entries(settings_data: dict[str, Any]) -> tuple[list[str], bool]:
    """Build the per-entry ``display`` diagnostic lines for *settings_data*.

    Inspects every render-trigger entry in ``_DISPLAY_RENDER_ENTRIES`` plus the
    ``statusLine`` command and ``env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE``. For
    each, appends a line of the form ``"<label>: present"`` or
    ``"<label>: MISSING"`` (the literal token ``MISSING`` is load-bearing — the
    menu doc tells the user to grep for it).

    Returns ``(lines, healthy)`` where ``healthy`` is True iff every required
    entry is present.
    """
    hooks_block = settings_data.get("hooks", {})
    if not isinstance(hooks_block, dict):
        hooks_block = {}

    lines: list[str] = []
    healthy = True

    for label, block_key, matcher in _DISPLAY_RENDER_ENTRIES:
        entries = hooks_block.get(block_key, [])
        present = isinstance(entries, list) and _has_render_entry(entries, matcher=matcher)
        lines.append(f"{label}: {'present' if present else 'MISSING'}")
        if not present:
            healthy = False

    # Enforcement-hook entry — keyed on _ENFORCEMENT_HOOK_COMMAND, NOT the render
    # command, so it has its own present/MISSING label. The opt-in enforcement
    # install is orthogonal to the terminal-title bundle: its absence does NOT
    # mark the display unhealthy (a user may enable terminal-title without it).
    pre_tool_use = hooks_block.get("PreToolUse", [])
    enforcement_present = isinstance(pre_tool_use, list) and _has_enforcement_entry(
        pre_tool_use
    )
    lines.append(
        f"PreToolUse:enforcement: {'present' if enforcement_present else 'MISSING'}"
    )

    statusline = settings_data.get("statusLine")
    statusline_present = isinstance(statusline, dict) and bool(statusline.get("command"))
    lines.append(f"statusLine: {'present' if statusline_present else 'MISSING'}")
    if not statusline_present:
        healthy = False

    env_block = settings_data.get("env", {})
    env_present = (
        isinstance(env_block, dict)
        and env_block.get("CLAUDE_CODE_DISABLE_TERMINAL_TITLE") is not None
    )
    lines.append(
        f"env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE: {'present' if env_present else 'MISSING'}"
    )
    if not env_present:
        healthy = False

    return lines, healthy


def _merge_display_settings(*sources: dict[str, Any]) -> dict[str, Any]:
    """Merge the display-relevant slices of several Claude settings dicts.

    The ``display`` health-check must reflect entries wherever they legitimately
    live — ``.claude/settings.json`` OR ``.claude/settings.local.json``. The
    install resolver prefers a pre-existing shared ``settings.json``, while the
    enforcement install pins ``settings.local.json``, so a hook entry can sit in
    either file. This mirrors the ``hook`` check, which already treats either
    file as authoritative. Per-event ``hooks`` entry lists are concatenated; the
    first present ``statusLine`` and each first-seen ``env`` key win.
    """
    merged_hooks: dict[str, list[Any]] = {}
    merged_env: dict[str, Any] = {}
    merged_statusline: dict[str, Any] | None = None
    for source in sources:
        if not isinstance(source, dict):
            continue
        hooks = source.get("hooks", {})
        if isinstance(hooks, dict):
            for event, entries in hooks.items():
                if isinstance(entries, list):
                    merged_hooks.setdefault(event, []).extend(entries)
        statusline = source.get("statusLine")
        if (
            merged_statusline is None
            and isinstance(statusline, dict)
            and statusline.get("command")
        ):
            merged_statusline = statusline
        env_block = source.get("env", {})
        if isinstance(env_block, dict):
            for key, value in env_block.items():
                merged_env.setdefault(key, value)
    merged: dict[str, Any] = {"hooks": merged_hooks, "env": merged_env}
    if merged_statusline is not None:
        merged["statusLine"] = merged_statusline
    return merged


def _has_render_entry(entries: list[Any], matcher: str | None = None) -> bool:
    """Return True when *entries* already contains a render-hook entry.

    When *matcher* is None, any entry whose ``hooks[].command`` matches the
    renderer command counts. When *matcher* is a string, the entry's
    ``matcher`` field must equal it as well (used to disambiguate the
    matcher-less and matcher:"clear" SessionStart variants).
    """
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if matcher is not None and entry.get("matcher", "") != matcher:
            continue
        hooks = entry.get("hooks", [])
        if not isinstance(hooks, list):
            continue
        for h in hooks:
            if isinstance(h, dict) and h.get("command") == _RENDER_HOOK_COMMAND:
                return True
    return False


def _has_capture_entry(entries: list[Any]) -> bool:
    """Return True when *entries* already contains the session-capture hook."""
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        hooks = entry.get("hooks", [])
        if not isinstance(hooks, list):
            continue
        for h in hooks:
            if isinstance(h, dict) and h.get("command") == _HOOK_COMMAND:
                return True
    return False


def _has_enforcement_entry(entries: list[Any]) -> bool:
    """Return True when *entries* already contains the PreToolUse enforcement hook.

    Keyed on ``_ENFORCEMENT_HOOK_COMMAND`` (not the render command), so the
    enforcement entry's presence is detected independently of the terminal-title
    render entries that may also live in ``hooks.PreToolUse``.
    """
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        hooks = entry.get("hooks", [])
        if not isinstance(hooks, list):
            continue
        for h in hooks:
            if isinstance(h, dict) and h.get("command") == _ENFORCEMENT_HOOK_COMMAND:
                return True
    return False


def _render_entry(matcher: str = "") -> dict[str, Any]:
    """Build a render-hook entry with the given matcher."""
    return {
        "matcher": matcher,
        "hooks": [
            {
                "type": "command",
                "command": _RENDER_HOOK_COMMAND,
                "timeout": 5000,
            }
        ],
    }


def _capture_entry() -> dict[str, Any]:
    """Build the session-id-capture SessionStart entry."""
    return {
        "matcher": "",
        "hooks": [
            {
                "type": "command",
                "command": _HOOK_COMMAND,
                "timeout": 5000,
            }
        ],
    }


def _enforcement_entry() -> dict[str, Any]:
    """Build the matcher-less PreToolUse enforcement entry."""
    return {
        "matcher": "",
        "hooks": [
            {
                "type": "command",
                "command": _ENFORCEMENT_HOOK_COMMAND,
                "timeout": 5000,
            }
        ],
    }


def _install_enforcement_hook(settings_path: Path) -> dict[str, Any]:
    """Idempotently install ONLY the PreToolUse enforcement entry into *settings_path*.

    Adds the matcher-less enforcement entry to ``hooks.PreToolUse`` without
    touching any existing entry — the terminal-title render matchers
    (``AskUserQuestion`` / ``Bash``) in the same block, and every SessionStart
    capture/render entry, are preserved verbatim. The install is orthogonal to
    the terminal-title bundle: it never installs render wiring.

    Args:
        settings_path: Path to the JSON settings file. Created (with parent
            dirs) when absent.

    Returns:
        Dict with keys:

        - ``io_ok`` (bool): True iff the file was read AND written successfully.
        - ``enforcement_status`` (str): ``installed`` when freshly added,
          ``already_present`` when the entry was already there (no write).

        Returns ``io_ok: False`` with ``enforcement_status: error`` on any I/O
        failure.
    """
    failure: dict[str, Any] = {"io_ok": False, "enforcement_status": "error"}

    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_data = _read_json(settings_path) or {}

        hooks_block = settings_data.setdefault("hooks", {})
        if not isinstance(hooks_block, dict):
            hooks_block = {}
            settings_data["hooks"] = hooks_block

        pre_tool_use = hooks_block.setdefault("PreToolUse", [])
        if not isinstance(pre_tool_use, list):
            pre_tool_use = []
            hooks_block["PreToolUse"] = pre_tool_use

        if _has_enforcement_entry(pre_tool_use):
            return {"io_ok": True, "enforcement_status": "already_present"}

        pre_tool_use.append(_enforcement_entry())
        if not _write_json(settings_path, settings_data):
            return failure

        return {"io_ok": True, "enforcement_status": "installed"}
    except (OSError, ValueError):
        return failure


def _install_terminal_title_hooks(
    settings_path: Path,
    overwrite_statusline: bool = False,
    overwrite_env_disable: bool = False,
) -> dict[str, Any]:
    """Install the full terminal-title hook wiring into *settings_path*.

    Installs (each block dedup-idempotent on the canonical command string):

    - ``hooks.SessionStart`` — the existing ``claude_hook`` session-capture
      entry (preserved when present, inserted when absent) **and** two render
      entries (matcher-less + ``matcher: "clear"``).
    - ``hooks.UserPromptSubmit``, ``hooks.Notification``, ``hooks.Stop`` —
      single matcher-less render entries each.
    - ``hooks.PreToolUse`` — two render entries: one with
      ``matcher: "AskUserQuestion"`` so the ``?`` icon flips BEFORE the prompt is
      answered, and one with ``matcher: "Bash"`` so the ⚙ busy icon flips BEFORE
      a long-running shell command runs.
    - ``hooks.PostToolUse`` — two render entries: one with
      ``matcher: "AskUserQuestion"`` and one with ``matcher: "Bash"`` (the
      latter refreshes the title immediately after each shell call).
    - ``statusLine`` — ``{"type": "command", "command": _STATUSLINE_COMMAND}``.
      Preserves a foreign existing value unless ``overwrite_statusline`` is True.
    - ``env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE`` — set to ``"1"``. Preserves a
      foreign existing value unless ``overwrite_env_disable`` is True.

    Args:
        settings_path: Path to the JSON settings file to install into. Created
            (with parent dirs) when absent.
        overwrite_statusline: When True, overwrite an existing ``statusLine``
            whose command differs from ours. When False, the foreign value is
            preserved and reported via ``statusLine_status: already_present_other``.
        overwrite_env_disable: Same semantics for
            ``env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE``.

    Returns:
        Dict with keys:

        - ``io_ok`` (bool): True iff the file was read AND written successfully.
        - ``installed_events`` (list[str]): event labels whose render entry was
          freshly added on this call. SessionStart appears at most once even
          though it gets two render entries. The tool-scoped PreToolUse and
          PostToolUse entries use matcher-qualified labels
          (``PreToolUse:AskUserQuestion``, ``PreToolUse:Bash``,
          ``PostToolUse:AskUserQuestion``, ``PostToolUse:Bash``) so each can be
          reported individually.
        - ``already_present_events`` (list[str]): event labels where our render
          entry was already present (no write).
        - ``statusLine_status`` (str): one of ``installed``, ``already_present``,
          ``already_present_other``, ``overwritten``.
        - ``env_status`` (str): same enum for the env entry.

        Returns ``io_ok: False`` (with the per-event lists empty and the
        statuses set to ``error``) on any I/O failure.
    """
    failure: dict[str, Any] = {
        "io_ok": False,
        "installed_events": [],
        "already_present_events": [],
        "statusLine_status": "error",
        "env_status": "error",
    }

    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_data = _read_json(settings_path) or {}

        hooks_block = settings_data.setdefault("hooks", {})
        if not isinstance(hooks_block, dict):
            hooks_block = {}
            settings_data["hooks"] = hooks_block

        installed_events: list[str] = []
        already_present_events: list[str] = []

        # --- SessionStart: capture entry + two render entries. ---
        session_start = hooks_block.setdefault("SessionStart", [])
        if not isinstance(session_start, list):
            session_start = []
            hooks_block["SessionStart"] = session_start

        # Capture entry: preserve when already present, insert when absent.
        # This is the existing claude_hook session-id-capture entry; it must
        # coexist with the new render entries.
        if not _has_capture_entry(session_start):
            session_start.append(_capture_entry())

        session_start_changed = False
        if not _has_render_entry(session_start, matcher=""):
            session_start.append(_render_entry(matcher=""))
            session_start_changed = True
        if not _has_render_entry(session_start, matcher="clear"):
            session_start.append(_render_entry(matcher="clear"))
            session_start_changed = True

        if session_start_changed:
            installed_events.append("SessionStart")
        else:
            already_present_events.append("SessionStart")

        # --- Single matcher-less render-trigger events. ---
        for event_name in _RENDER_TRIGGER_EVENTS:
            event_entries = hooks_block.setdefault(event_name, [])
            if not isinstance(event_entries, list):
                event_entries = []
                hooks_block[event_name] = event_entries
            if not _has_render_entry(event_entries, matcher=""):
                event_entries.append(_render_entry(matcher=""))
                installed_events.append(event_name)
            else:
                already_present_events.append(event_name)

        # --- PreToolUse with matcher:"AskUserQuestion" and matcher:"Bash". ---
        # AskUserQuestion flips the "?" icon before the prompt is answered; Bash
        # flips the ⚙ busy icon before a long-running shell command runs.
        pre_tool_use = hooks_block.setdefault("PreToolUse", [])
        if not isinstance(pre_tool_use, list):
            pre_tool_use = []
            hooks_block["PreToolUse"] = pre_tool_use
        if not _has_render_entry(pre_tool_use, matcher="AskUserQuestion"):
            pre_tool_use.append(_render_entry(matcher="AskUserQuestion"))
            installed_events.append("PreToolUse:AskUserQuestion")
        else:
            already_present_events.append("PreToolUse:AskUserQuestion")
        if not _has_render_entry(pre_tool_use, matcher="Bash"):
            pre_tool_use.append(_render_entry(matcher="Bash"))
            installed_events.append("PreToolUse:Bash")
        else:
            already_present_events.append("PreToolUse:Bash")

        # --- PostToolUse with matcher:"AskUserQuestion" and matcher:"Bash". ---
        post_tool_use = hooks_block.setdefault("PostToolUse", [])
        if not isinstance(post_tool_use, list):
            post_tool_use = []
            hooks_block["PostToolUse"] = post_tool_use
        if not _has_render_entry(post_tool_use, matcher="AskUserQuestion"):
            post_tool_use.append(_render_entry(matcher="AskUserQuestion"))
            installed_events.append("PostToolUse:AskUserQuestion")
        else:
            already_present_events.append("PostToolUse:AskUserQuestion")
        if not _has_render_entry(post_tool_use, matcher="Bash"):
            post_tool_use.append(_render_entry(matcher="Bash"))
            installed_events.append("PostToolUse:Bash")
        else:
            already_present_events.append("PostToolUse:Bash")

        # --- statusLine: command entry with overwrite-on-request semantics. ---
        statusline_block: dict[str, Any] = {
            "type": "command",
            "command": _STATUSLINE_COMMAND,
        }
        existing_statusline = settings_data.get("statusLine")
        if existing_statusline is None:
            settings_data["statusLine"] = statusline_block
            statusline_status = "installed"
        elif (
            isinstance(existing_statusline, dict)
            and existing_statusline.get("command") == _STATUSLINE_COMMAND
        ):
            statusline_status = "already_present"
        elif overwrite_statusline:
            settings_data["statusLine"] = statusline_block
            statusline_status = "overwritten"
        else:
            statusline_status = "already_present_other"

        # --- env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE: "1" with overwrite-on-request. ---
        env_block = settings_data.setdefault("env", {})
        if not isinstance(env_block, dict):
            env_block = {}
            settings_data["env"] = env_block
        existing_env = env_block.get("CLAUDE_CODE_DISABLE_TERMINAL_TITLE")
        if existing_env is None:
            env_block["CLAUDE_CODE_DISABLE_TERMINAL_TITLE"] = "1"
            env_status = "installed"
        elif existing_env == "1":
            env_status = "already_present"
        elif overwrite_env_disable:
            env_block["CLAUDE_CODE_DISABLE_TERMINAL_TITLE"] = "1"
            env_status = "overwritten"
        else:
            env_status = "already_present_other"

        write_ok = _write_json(settings_path, settings_data)
        if not write_ok:
            return failure

        return {
            "io_ok": True,
            "installed_events": installed_events,
            "already_present_events": already_present_events,
            "statusLine_status": statusline_status,
            "env_status": env_status,
        }
    except (OSError, ValueError):
        return failure


def _project_dir_path(project_dir: str) -> Path:
    return Path(project_dir).resolve()


def _marshal_json_path(project_dir: str) -> Path:
    return _project_dir_path(project_dir) / _PLAN_DIR_NAME / "marshal.json"


def _claude_settings_path(project_dir: str) -> Path:
    return _project_dir_path(project_dir) / ".claude" / "settings.json"


def _plan_dir(project_dir: str) -> Path:
    return _project_dir_path(project_dir) / _PLAN_DIR_NAME


def _local_plans_dir(project_dir: str) -> Path:
    return _plan_dir(project_dir) / "local" / "plans"


def _read_json(path: Path) -> dict[str, Any] | None:
    """Read a JSON file, returning None on failure."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        return data
    except (OSError, json.JSONDecodeError):
        return None


def _write_json(path: Path, data: dict[str, Any]) -> bool:
    """Write a JSON file atomically via a temp file, returning True on success."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(path)
        return True
    except OSError:
        return False


def _cwd_to_slug(cwd: str) -> str:
    """Convert an absolute cwd path to a Claude-style project slug (slashes → dashes)."""
    return cwd.replace("/", "-")


def _find_transcript(session_id: str) -> Path | None:
    """Locate the JSONL transcript for a Claude Code session.

    ``session_id`` originates from an external hook payload and is
    interpolated into filesystem paths and glob patterns below.  It is
    validated against the canonical UUID format first; any value that does
    not match is rejected to prevent path traversal and glob injection.
    """
    if not _SESSION_ID_RE.match(session_id):
        return None
    if not _CLAUDE_PROJECTS_DIR.is_dir():
        return None
    # Try the canonical cwd-slug path first.
    cwd = _resolve_cwd()
    slug = _cwd_to_slug(cwd)
    direct = _CLAUDE_PROJECTS_DIR / slug / f"{session_id}.jsonl"
    if direct.is_file():
        return direct
    # Fall back: scan all project dirs.
    for candidate in _CLAUDE_PROJECTS_DIR.glob(f"*/{session_id}.jsonl"):
        if candidate.is_file():
            return candidate
    return None


def _resolve_cwd() -> str:
    """Return the git repository root, falling back to os.getcwd()."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return os.getcwd()


def _read_active_plan(session_id: str) -> str | None:
    """Read the active plan_id from the session cache.

    ``session_id`` originates from an external hook payload
    (``$CLAUDE_CODE_SESSION_ID``) and is interpolated into the cache path below,
    so reject empty values and any path-traversal token (a separator or ``..``)
    before use — a crafted value must not escape the session-cache root.
    """
    if not session_id or "/" in session_id or "\\" in session_id or ".." in session_id:
        return None
    active_plan_path = _SESSION_CACHE_BASE / session_id / "active-plan"
    try:
        raw = active_plan_path.read_text(encoding="utf-8").strip()
        return raw or None
    except OSError:
        return None


def _resolve_archived_status_json(plan_id: str) -> Path | None:
    """Resolve the archived ``status.json`` for a plan, or ``None``.

    Once a plan is archived, the live ``.plan/local/plans/{plan_id}/`` directory
    is gone — ``cmd_archive`` moved it to
    ``.plan/local/archived-plans/{YYYY-MM-DD}-{plan_id}/``. ``status.json`` is the
    SINGLE source of persisted title state, so the archived state lives at
    ``archived-plans/{YYYY-MM-DD}-{plan_id}/status.json``.

    Globs ``archived-plans/*-{plan_id}/status.json`` (the ``*`` matches the
    ``YYYY-MM-DD`` date prefix) and returns the first regular file found, or
    ``None`` when no archived state exists. The returned path's parent name must
    end with the exact ``-{plan_id}`` suffix to avoid a prefix collision between
    similarly named plans.
    """
    archived_base = Path(_PLAN_DIR_NAME) / "local" / "archived-plans"
    if not archived_base.is_dir():
        return None
    suffix = f"-{plan_id}"
    try:
        for candidate in sorted(archived_base.glob(f"*-{plan_id}/status.json"), reverse=True):
            if candidate.is_file() and candidate.parent.name.endswith(suffix):
                return candidate
    except OSError:
        return None
    return None


def _read_title_state(plan_id: str) -> dict[str, Any] | None:
    """Read the title state for *plan_id* from ``status.json``, or ``None``.

    Reads the live plan dir's ``status.json``
    (``<_PLAN_DIR_NAME>/local/plans/{plan_id}/status.json``) first; on absence,
    falls back to the archived ``status.json`` resolved via
    :func:`_resolve_archived_status_json`.

    Returns a ``{current_phase, short_description, title_token}`` state dict (the
    inputs :func:`manage_terminal_title.compose` consumes), reading
    ``current_phase`` from the top-level field and ``short_description`` /
    ``title_token`` from wherever they live in the status structure. Returns
    ``None`` when neither the live nor the archived file is present or readable.

    ``current_phase`` is sourced from the status ``current_phase`` field;
    ``short_description`` and ``title_token`` are best-effort (a status.json
    lacking them yields a state dict with those keys absent, which the composer
    handles).
    """
    live_path = Path(_PLAN_DIR_NAME) / "local" / "plans" / plan_id / "status.json"
    if live_path.is_file():
        status_path: Path | None = live_path
    else:
        status_path = _resolve_archived_status_json(plan_id)
    if status_path is None:
        return None

    status_data = _read_json(status_path)
    if status_data is None:
        return None

    state: dict[str, Any] = {}
    current_phase = status_data.get("current_phase")
    if isinstance(current_phase, str):
        state["current_phase"] = current_phase
    short_description = status_data.get("short_description")
    if isinstance(short_description, str):
        state["short_description"] = short_description
    title_token = status_data.get("title_token")
    if isinstance(title_token, str):
        state["title_token"] = title_token
    return state


def _manage_status_store_session(plan_id: str, session_id: str) -> bool:
    """Store session_id in plan status.json via manage-status metadata --set.

    Returns True when the subprocess exits 0.
    """
    try:
        result = subprocess.run(
            [
                sys.executable,
                ".plan/execute-script.py",
                "plan-marshall:manage-status:manage-status",
                "metadata",
                "--plan-id",
                plan_id,
                "--set",
                "--field",
                "session_id",
                "--value",
                session_id,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _manage_status_read_session(plan_id: str) -> str | None:
    """Read session_id from plan status.json via manage-status metadata --get."""
    try:
        result = subprocess.run(
            [
                sys.executable,
                ".plan/execute-script.py",
                "plan-marshall:manage-status:manage-status",
                "metadata",
                "--plan-id",
                plan_id,
                "--get",
                "--field",
                "session_id",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        parsed = parse_toon(result.stdout)
        value = parsed.get("value")
        return str(value) if value else None
    except (OSError, subprocess.SubprocessError):
        return None


def _manage_status_set_title_token(plan_id: str, state: str) -> bool:
    """Best-effort ``manage-status title-token set --state {state}``.

    Persists *state* into the plan's ``status.json`` so the ``build-busy``
    title-token set by the ``PreToolUse:Bash`` render hook survives to subsequent
    renders and is available for the agent's D3 clear. Best-effort: returns False
    on any failure and never raises — a persist failure must never break the
    render hook. The bare STATE NAME is passed; the render path never hard-codes a
    glyph. The timeout stays inside the render hook's own budget.
    """
    try:
        result = subprocess.run(
            [
                sys.executable,
                ".plan/execute-script.py",
                "plan-marshall:manage-status:manage-status",
                "title-token",
                "set",
                "--plan-id",
                plan_id,
                "--state",
                state,
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _manage_metrics_end_phase(plan_id: str, phase: str, total_tokens: int) -> bool:
    """Store total_tokens via manage-metrics end-phase."""
    try:
        result = subprocess.run(
            [
                sys.executable,
                ".plan/execute-script.py",
                "plan-marshall:manage-metrics:manage-metrics",
                "end-phase",
                "--plan-id",
                plan_id,
                "--phase",
                phase,
                "--total-tokens",
                str(total_tokens),
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


# ---------------------------------------------------------------------------
# Token capture helpers
# ---------------------------------------------------------------------------


def _read_token_cursor(plan_id: str, phase: str) -> int:
    """Read the previously-recorded token count for a plan+phase.

    Returns 0 when no prior capture exists.  Cursor is stored at
    ``.plan/local/plans/{plan_id}/work/metrics-cursor-{phase}.toon``.
    """
    cursor_file = (
        Path(_PLAN_DIR_NAME)
        / "local"
        / "plans"
        / plan_id
        / "work"
        / f"metrics-cursor-{phase}.toon"
    )
    try:
        for line in cursor_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("total_tokens:"):
                _, _, raw = stripped.partition(":")
                return int(raw.strip())
    except (OSError, ValueError):
        pass
    return 0


def _write_token_cursor(plan_id: str, phase: str, total: int) -> None:
    """Persist the running token total for a plan+phase cursor."""
    cursor_file = (
        Path(_PLAN_DIR_NAME)
        / "local"
        / "plans"
        / plan_id
        / "work"
        / f"metrics-cursor-{phase}.toon"
    )
    try:
        cursor_file.parent.mkdir(parents=True, exist_ok=True)
        cursor_file.write_text(f"plan_id: {plan_id}\nphase: {phase}\ntotal_tokens: {total}\n", encoding="utf-8")
    except OSError:
        pass


def _sum_tokens_from_jsonl(transcript_path: Path) -> int:
    """Sum input_tokens + output_tokens from all assistant messages in a JSONL transcript."""
    total = 0
    try:
        with open(transcript_path, encoding="utf-8") as fh:
            for raw_line in fh:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    entry = json.loads(raw_line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if not isinstance(entry, dict):
                    continue
                msg = entry.get("message", {})
                if not isinstance(msg, dict):
                    continue
                usage = msg.get("usage", {})
                if not isinstance(usage, dict):
                    continue
                # Sum whichever fields are present.
                input_tok = usage.get("input_tokens", 0) or 0
                output_tok = usage.get("output_tokens", 0) or 0
                total_tok = usage.get("total_tokens", 0) or 0
                if total_tok:
                    total += total_tok
                elif input_tok or output_tok:
                    total += input_tok + output_tok
    except OSError:
        pass
    return total


# ---------------------------------------------------------------------------
# Transcript engine — per-phase normalized-token computation helpers.
# ---------------------------------------------------------------------------


def _resolve_subagent_transcripts(
    session_id: str,
    parent_transcript_path: Path | None = None,
) -> list[Path]:
    """Return absolute paths of subagent transcript JSONLs for the parent session.

    Subagent transcripts live under
    ``{project_dir}/{parent_session_id}/subagents/agent-*.jsonl``.

    Discovery is anchored to the resolved parent transcript location when
    ``parent_transcript_path`` is supplied: the subagents directory is derived as
    ``parent_transcript_path.parent / session_id / 'subagents'``. This pins
    discovery to the actual project-dir the parent transcript was found under, so
    the worktree-vs-main-checkout cwd no longer changes the answer. When
    ``parent_transcript_path`` is ``None`` the legacy ``_resolve_cwd()``-slug path
    is used as a fallback. Returns ``[]`` when the directory is absent or empty.

    The session-id UUID format guard is preserved on both paths.
    """
    if not re.fullmatch(_TRANSCRIPT_SESSION_ID_RE, session_id):
        return []

    if parent_transcript_path is not None:
        subagents_dir = parent_transcript_path.parent / session_id / "subagents"
    else:
        try:
            home = Path.home()
        except (OSError, RuntimeError):
            return []
        projects = home / ".claude" / "projects"
        cwd_slug = _resolve_cwd().replace("/", "-")
        subagents_dir = projects / cwd_slug / session_id / "subagents"

    try:
        if not subagents_dir.is_dir():
            return []
        return sorted(p for p in subagents_dir.glob("agent-*.jsonl") if p.is_file())
    except OSError:
        return []


def _add_usage_four_fields(usage: dict[str, Any], bucket: dict[str, int]) -> None:
    """Accumulate the four ``message.usage`` fields from *usage* into *bucket*."""
    for field in _USAGE_FOUR_FIELDS:
        raw = usage.get(field)
        if isinstance(raw, bool):
            continue
        if isinstance(raw, int):
            bucket[field] = bucket.get(field, 0) + raw


def _sum_subagent_transcript(path: Path) -> tuple[dict[str, int], str | None]:
    """Sum the four ``message.usage`` fields across one subagent transcript JSONL.

    Returns ``(four_field_bucket, first_timestamp_iso)``. ``first_timestamp_iso``
    is ``None`` when no line carried a timestamp.
    """
    bucket: dict[str, int] = dict.fromkeys(_USAGE_FOUR_FIELDS, 0)
    first_timestamp: str | None = None
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except (json.JSONDecodeError, AttributeError):
                    continue
                if not isinstance(entry, dict):
                    continue
                if first_timestamp is None:
                    ts = entry.get("timestamp")
                    if isinstance(ts, str) and ts:
                        first_timestamp = ts
                msg = entry.get("message", {})
                usage = msg.get("usage", {}) if isinstance(msg, dict) else {}
                if isinstance(usage, dict) and usage:
                    _add_usage_four_fields(usage, bucket)
    except OSError:
        return dict.fromkeys(_USAGE_FOUR_FIELDS, 0), None
    return bucket, first_timestamp


def _window_for_timestamp(
    timestamp_iso: str | None,
    windows: list[tuple[str, datetime, datetime]],
) -> str | None:
    """Return the phase name whose window contains *timestamp_iso*, else None.

    Boundary ties resolve to the newer phase via latest-window-wins (reversed
    iteration).
    """
    if not timestamp_iso:
        return None
    try:
        ts = datetime.fromisoformat(timestamp_iso.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    for phase_name, start_dt, end_dt in reversed(windows):
        if start_dt <= ts <= end_dt:
            return phase_name
    return None


def _attribute_subagent_usage(
    timestamp_iso: str | None,
    windows: list[tuple[str, datetime, datetime]],
    body: str,
    per_phase: dict[str, dict[str, int]],
) -> bool:
    """Parse a ``<usage>`` body and add its totals to the matching phase row.

    Returns True when the totals were attributed, False when no phase window
    contained the timestamp.
    """
    matching_phase = _window_for_timestamp(timestamp_iso, windows)
    if matching_phase is None:
        return False

    fields = {m.group(1): int(m.group(2)) for m in _USAGE_TAG_FIELD_RE.finditer(body)}
    bucket = per_phase.setdefault(
        matching_phase,
        {"total_tokens": 0, "tool_uses": 0, "duration_ms": 0, "samples": 0},
    )
    # The harness sometimes emits the sub-agent token figure under the
    # ``subagent_tokens`` key instead of the canonical ``total_tokens``; accept
    # either so the token bucket is never silently dropped to zero.
    bucket["total_tokens"] += fields.get("total_tokens", fields.get("subagent_tokens", 0))
    bucket["tool_uses"] += fields.get("tool_uses", 0)
    bucket["duration_ms"] += fields.get("duration_ms", 0)
    bucket["samples"] += 1
    return True


def _billing_weighted_total(four_fields: dict[str, int]) -> int:
    """Compute the billing-weighted token total from the four-field usage view.

    ``input + output + round(0.1 * cache_read) + round(1.25 * cache_creation)``.
    A billing-cost figure, NOT a work-comparable measure.
    """
    return (
        four_fields.get("input_tokens", 0)
        + four_fields.get("output_tokens", 0)
        + round(four_fields.get("cache_read_input_tokens", 0) * _BILLING_WEIGHT_CACHE_READ)
        + round(four_fields.get("cache_creation_input_tokens", 0) * _BILLING_WEIGHT_CACHE_CREATION)
    )


def _extract_text_payload(content: object) -> str:
    """Best-effort flattening of a tool_result content payload to a single string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    chunks.append(text)
        return "\n".join(chunks)
    return ""


def _find_enrich_transcript(session_id: str) -> Path | None:
    """Locate the parent JSONL transcript for *session_id* under ~/.claude/projects.

    Mirrors the legacy manage-metrics ``cmd_enrich`` discovery: scan project-dir
    subtrees whose name contains the session id, then fall back to the direct
    ``{session_id}.jsonl`` file pattern. Returns ``None`` when no transcript is
    found.
    """
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return None

    try:
        for session_dir in projects_dir.rglob("*"):
            if session_dir.is_dir() and session_id in session_dir.name:
                for jsonl_file in session_dir.glob("*.jsonl"):
                    return jsonl_file

        for project_dir in projects_dir.iterdir():
            if project_dir.is_dir():
                candidate = project_dir / f"{session_id}.jsonl"
                if candidate.exists():
                    return candidate
    except OSError:
        return None
    return None


def _parse_windows(windows: list[tuple[str, str, str]]) -> list[tuple[str, datetime, datetime]]:
    """Parse ``(phase, start_iso, end_iso)`` tuples into datetime windows.

    Entries whose start/end are unparseable are dropped (mirroring the legacy
    ``_phase_window_lookup`` filter).
    """
    parsed: list[tuple[str, datetime, datetime]] = []
    for entry in windows:
        if len(entry) != 3:
            continue
        phase_name, start_str, end_str = entry
        try:
            start_dt = datetime.fromisoformat(str(start_str))
            end_dt = datetime.fromisoformat(str(end_str))
        except (ValueError, TypeError):
            continue
        parsed.append((phase_name, start_dt, end_dt))
    return parsed


def _compute_normalized_tokens(
    session_id: str,
    windows: list[tuple[str, str, str]],
) -> tuple[dict[str, dict[str, int]], dict[str, int]] | None:
    """Walk the Claude session transcript and compute per-phase normalized tokens.

    Returns ``(per_phase, counters)`` where ``per_phase`` maps each attributed
    phase to a normalized bucket carrying the four ``message.usage`` fields, the
    billing-weighted total, and the subagent ``<usage>`` attribution
    (``subagent_total_tokens`` / ``subagent_tool_uses`` / ``subagent_duration_ms``
    / ``subagent_samples``). ``counters`` carries the attribution counters.

    Returns ``None`` when no parent transcript can be located (the caller maps
    this to a ``transcript_not_found`` no-op).
    """
    transcript_path = _find_enrich_transcript(session_id)
    if transcript_path is None:
        return None

    parsed_windows = _parse_windows(windows)

    message_count = 0
    per_phase_subagent: dict[str, dict[str, int]] = {}
    subagent_calls_attributed = 0
    per_phase_four_fields: dict[str, dict[str, int]] = {}

    def _four_field_bucket(phase_name: str) -> dict[str, int]:
        return per_phase_four_fields.setdefault(phase_name, dict.fromkeys(_USAGE_FOUR_FIELDS, 0))

    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except (json.JSONDecodeError, AttributeError):
                    continue

                msg = entry.get("message", {}) if isinstance(entry, dict) else {}
                usage = msg.get("usage", {}) if isinstance(msg, dict) else {}
                if isinstance(usage, dict) and usage:
                    if usage.get("total_tokens") or usage.get("input_tokens") or usage.get("output_tokens"):
                        message_count += 1
                        if parsed_windows:
                            timestamp = entry.get("timestamp") if isinstance(entry, dict) else None
                            if isinstance(timestamp, str):
                                parent_phase = _window_for_timestamp(timestamp, parsed_windows)
                                if parent_phase is not None:
                                    _add_usage_four_fields(usage, _four_field_bucket(parent_phase))

                if not parsed_windows:
                    continue
                content = msg.get("content") if isinstance(msg, dict) else None
                payloads: list[str] = []
                if isinstance(content, list):
                    for item in content:
                        if not isinstance(item, dict):
                            continue
                        if item.get("type") == "tool_result":
                            payloads.append(_extract_text_payload(item.get("content")))
                        elif item.get("type") == "text":
                            text = item.get("text")
                            if isinstance(text, str):
                                payloads.append(text)
                elif isinstance(content, str):
                    payloads.append(content)

                timestamp = entry.get("timestamp") if isinstance(entry, dict) else None
                for payload in payloads:
                    if not payload or "<usage>" not in payload:
                        continue
                    for tag_match in _USAGE_TAG_RE.finditer(payload):
                        if _attribute_subagent_usage(
                            timestamp, parsed_windows, tag_match.group(1), per_phase_subagent
                        ):
                            subagent_calls_attributed += 1
    except OSError:
        return None

    subagent_transcripts_walked = 0
    if parsed_windows:
        for sub_path in _resolve_subagent_transcripts(session_id, transcript_path):
            subagent_transcripts_walked += 1
            sub_fields, sub_ts = _sum_subagent_transcript(sub_path)
            sub_phase = _window_for_timestamp(sub_ts, parsed_windows)
            if sub_phase is None:
                continue
            bucket = _four_field_bucket(sub_phase)
            for field in _USAGE_FOUR_FIELDS:
                bucket[field] += sub_fields.get(field, 0)

    # Compose the per-phase normalized result. Each phase carries the four-field
    # view, the billing-weighted total, and the subagent <usage> attribution.
    per_phase: dict[str, dict[str, int]] = {}
    phase_names = set(per_phase_four_fields) | set(per_phase_subagent)
    for phase_name in phase_names:
        four = per_phase_four_fields.get(phase_name, dict.fromkeys(_USAGE_FOUR_FIELDS, 0))
        sub = per_phase_subagent.get(phase_name)
        phase_bucket: dict[str, int] = {
            "input": four.get("input_tokens", 0),
            "output": four.get("output_tokens", 0),
            "cache_read": four.get("cache_read_input_tokens", 0),
            "cache_creation": four.get("cache_creation_input_tokens", 0),
            "input_tokens": four.get("input_tokens", 0),
            "output_tokens": four.get("output_tokens", 0),
            "cache_read_input_tokens": four.get("cache_read_input_tokens", 0),
            "cache_creation_input_tokens": four.get("cache_creation_input_tokens", 0),
            "billing_weighted_total": _billing_weighted_total(four),
            "subagent_total_tokens": 0,
            "subagent_tool_uses": 0,
            "subagent_duration_ms": 0,
            "subagent_samples": 0,
        }
        phase_bucket["total"] = (
            four.get("input_tokens", 0)
            + four.get("output_tokens", 0)
            + four.get("cache_read_input_tokens", 0)
            + four.get("cache_creation_input_tokens", 0)
        )
        if sub is not None:
            phase_bucket["subagent_total_tokens"] = sub["total_tokens"]
            phase_bucket["subagent_tool_uses"] = sub["tool_uses"]
            phase_bucket["subagent_duration_ms"] = sub["duration_ms"]
            phase_bucket["subagent_samples"] = sub["samples"]
        per_phase[phase_name] = phase_bucket

    counters = {
        "message_count": message_count,
        "subagent_phases_attributed": len(per_phase_subagent),
        "subagent_calls_attributed": subagent_calls_attributed,
        "subagent_transcripts_walked": subagent_transcripts_walked,
        "four_field_phases_attributed": len(per_phase_four_fields),
    }
    return per_phase, counters


# ---------------------------------------------------------------------------
# Permission helpers (thin wrappers over existing scripts)
# ---------------------------------------------------------------------------


def _claude_project_settings_path(project_dir: str | None = None) -> Path:
    """Return the Claude project settings file path to write to.

    Prefers ``.claude/settings.json`` when it already exists; otherwise targets
    ``.claude/settings.local.json``. This is the single home for Claude project
    settings-path resolution — the ``tools-permission-*`` scripts delegate here
    rather than owning the path-resolution logic themselves.
    """
    base = Path(project_dir) if project_dir else Path.cwd()
    settings_json = base / ".claude" / "settings.json"
    if settings_json.exists():
        return settings_json
    return base / ".claude" / "settings.local.json"


def _claude_local_settings_path(project_dir: str | None = None) -> Path:
    """Return the operator-local Claude settings file path (always settings.local.json).

    The PreToolUse enforcement hook is an operator-local opt-in, so its
    registration pins here rather than delegating to
    ``_claude_project_settings_path()`` — which prefers a pre-existing shared
    ``settings.json`` and would therefore scatter the enforcement entry into the
    shared file. Pinning keeps the enforcement entry in the single file the
    documented install contract (``pretooluse-enforcement.md``) names, regardless
    of whether a shared ``settings.json`` already exists.
    """
    base = Path(project_dir) if project_dir else Path.cwd()
    return base / ".claude" / "settings.local.json"


def _claude_global_settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def _settings_path_for_scope(scope: str) -> Path:
    if scope == "global":
        return _claude_global_settings_path()
    return _claude_project_settings_path()


def _load_settings(path: Path) -> dict[str, Any]:
    """Load Claude settings JSON, returning a defaulted skeleton when absent.

    This is the single home for Claude settings load logic; the
    ``tools-permission-*`` scripts delegate here. A missing file yields the
    empty-permissions skeleton; malformed JSON yields the same skeleton with an
    ``error`` key so callers can surface the parse failure.
    """
    if not path.exists():
        return {"permissions": {"allow": [], "deny": [], "ask": []}}
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        if "permissions" not in data:
            data["permissions"] = {}
        for key in ("allow", "deny", "ask"):
            if key not in data["permissions"]:
                data["permissions"][key] = []
        return data
    except json.JSONDecodeError as exc:
        return {"error": f"Invalid JSON: {exc}", "permissions": {"allow": [], "deny": [], "ask": []}}
    except OSError:
        return {"permissions": {"allow": [], "deny": [], "ask": []}}


def _save_settings(path: Path, settings: dict[str, Any]) -> bool:
    """Write Claude settings JSON. Single home for the save logic."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


def _skill_permission_covered(skill: str, allow_list: list[str]) -> str | None:
    """Return the allow-rule covering *skill*, or ``None``.

    Matches an exact ``Skill({skill})`` rule or a covering ``Skill({skill}:*)``
    wildcard. This is the single home for the skill-coverage check — relocated
    from ``permission_doctor`` so the runtime owns it with no back-import.
    """
    exact = f"Skill({skill})"
    wildcard = f"Skill({skill}:*)"
    for rule in allow_list:
        if rule == exact or rule == wildcard:
            return rule
    return None


# Phases in marshal.json that may carry ``project:{skill}`` step references.
_PROJECT_STEP_PHASES = ("phase-5-execute", "phase-6-finalize")


def _load_marshal_config(path: str) -> tuple[dict[str, Any], str | None]:
    """Load marshal.json, returning ``(config, error)``.

    Relocated from ``permission_doctor`` so the runtime owns marshal parsing for
    the missing-steps / ensure-steps permission ops without a back-import.
    """
    marshal_path = Path(path)
    if not marshal_path.exists():
        return {}, f"marshal.json not found: {path}"
    try:
        data = json.loads(marshal_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}, f"Invalid marshal.json (expected object) in {path}"
        return data, None
    except json.JSONDecodeError as exc:
        return {}, f"Invalid JSON in {path}: {exc}"
    except OSError as exc:
        return {}, f"Could not read {path}: {exc}"


def _extract_project_steps(marshal_config: dict[str, Any]) -> list[dict[str, str]]:
    """Enumerate ``project:{skill}`` step references from marshal.json.

    Scans the phases in ``_PROJECT_STEP_PHASES`` under ``plan.{phase}.steps`` and
    returns one ``{skill, step, phase}`` dict per ``project:``-prefixed entry.
    Relocated from ``permission_doctor`` (single home in the runtime).
    """
    plan = marshal_config.get("plan", {})
    if not isinstance(plan, dict):
        return []
    project_steps: list[dict[str, str]] = []
    for phase in _PROJECT_STEP_PHASES:
        phase_config = plan.get(phase, {})
        if not isinstance(phase_config, dict):
            continue
        steps = phase_config.get("steps", [])
        if not isinstance(steps, list):
            continue
        for step in steps:
            if isinstance(step, str) and step.startswith("project:"):
                skill = step[len("project:") :]
                project_steps.append({"skill": skill, "step": step, "phase": phase})
    return project_steps


# ---------------------------------------------------------------------------
# Subagent dispatch helper
# ---------------------------------------------------------------------------


def _find_agent_file(agent_name: str) -> Path | None:
    """Locate an agent markdown under the marketplace tree."""
    # Look under the plugin cache and source tree in sequence.
    search_roots: list[Path] = []
    cache_base = Path.home() / ".claude" / "plugins" / "cache" / "plan-marshall"
    if cache_base.exists():
        search_roots.append(cache_base)
    # Script-relative walk to find marketplace.
    for ancestor in Path(__file__).resolve().parents:
        candidate = ancestor / "marketplace" / "bundles"
        if candidate.is_dir():
            search_roots.append(candidate)
            break
        candidate2 = ancestor / "bundles"
        if candidate2.is_dir():
            search_roots.append(candidate2)
            break

    for root in search_roots:
        for match in root.glob(f"*/agents/{agent_name}.md"):
            if match.is_file():
                return match
    return None


def _parse_agent_frontmatter(agent_path: Path) -> dict[str, Any]:
    """Extract YAML-like frontmatter from an agent markdown file.

    Returns a dict with at minimum 'name', 'description', and 'tools' keys.
    Tools are returned as a list of strings.
    """
    result: dict[str, Any] = {"name": "", "description": "", "tools": []}
    try:
        content = agent_path.read_text(encoding="utf-8")
    except OSError:
        return result

    if not content.startswith("---"):
        return result

    end = content.find("---", 3)
    if end == -1:
        return result

    frontmatter = content[3:end].strip()
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()
        if key == "tools":
            # May be inline: tools: [Read, Write] or listed below as - items.
            if value.startswith("["):
                try:
                    parsed = json.loads(value)
                    result["tools"] = [str(t) for t in parsed]
                except (json.JSONDecodeError, ValueError):
                    # Try stripping brackets and splitting by comma.
                    inner = value.strip("[]")
                    result["tools"] = [t.strip().strip('"\'') for t in inner.split(",") if t.strip()]
            elif value:
                result["tools"] = [value]
        elif key in ("name", "description"):
            result[key] = value

    # Handle tools as a YAML list (- item per line) if not yet found inline.
    if not result["tools"]:
        in_tools = False
        for line in frontmatter.splitlines():
            stripped = line.strip()
            if stripped.startswith("tools:"):
                in_tools = True
                inline = stripped[6:].strip()
                if inline:
                    in_tools = False
            elif in_tools:
                if stripped.startswith("- "):
                    result["tools"].append(stripped[2:].strip())
                else:
                    in_tools = False

    return result


def _short_description_from_agent(description: str) -> str:
    """Derive a ≤5-word Task description from an agent description string."""
    words = description.strip().split()
    if len(words) <= 5:
        return description.strip()
    return " ".join(words[:5])


# TOOLS that are mapped on both Claude and OpenCode (not unmapped).
_MAPPED_TOOLS: frozenset[str] = frozenset(
    {
        "Read",
        "Write",
        "Edit",
        "Bash",
        "Glob",
        "Grep",
        "Task",
        "Skill",
        "WebFetch",
        "WebSearch",
        "TodoRead",
        "TodoWrite",
        "NotebookRead",
        "NotebookEdit",
        "AskUserQuestion",
    }
)

# Tools that have no platform equivalent — cause no-op for subagent dispatch.
_UNMAPPED_TOOLS: frozenset[str] = frozenset({"SendMessage", "TaskCreate"})



# ---------------------------------------------------------------------------
# ClaudeRuntime — the operation implementations live in the co-located
# _claude_runtime_impl submodule. This bottom re-export runs after every
# module-level helper, constant, and monkeypatchable name above is defined, so
# the submodule's ``import claude_runtime`` returns this fully-populated module
# rather than triggering a circular re-load. The submodule only ACCESSES entry
# names at call time (``claude_runtime.<name>``), so importing it here — while
# this module is partially initialized but with all helpers present — is
# load-order safe. When this file is executed directly (loaded as ``__main__``)
# the setdefault aliases the live module under its real name first, so the
# submodule's ``import claude_runtime`` resolves to it instead of re-loading.
# ---------------------------------------------------------------------------

sys.modules.setdefault("claude_runtime", sys.modules[__name__])

from _claude_runtime_impl import ClaudeRuntime  # noqa: E402,F401
