#!/usr/bin/env python3
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
            "tools-permission-doctor",
            "tools-permission-fix",
            "workflow-permission-web",
            "script-shared",
        ):
            _lib_path = str(_ancestor / _lib / "scripts")
            if _lib_path not in sys.path:
                sys.path.append(_lib_path)
        break

from manage_terminal_title import _compose_body, compose  # type: ignore[import-not-found]  # noqa: E402
from runtime_base import Runtime, toon_error, toon_noop, toon_success  # type: ignore[import-not-found]  # noqa: E402
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

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

# Render-title hook command installed across all seven render-trigger events
# plus statusLine. Invoked by Claude Code on SessionStart (matcher-less + matcher
# "clear"), UserPromptSubmit, Notification, Stop, PreToolUse:AskUserQuestion,
# PostToolUse:AskUserQuestion, and PostToolUse:Bash; the statusLine variant
# appends ``--statusline`` for plain-text emission. The statusLine variant is
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
    - ``hooks.PreToolUse`` — one render entry with ``matcher: "AskUserQuestion"``
      so the ``?`` icon flips BEFORE the prompt is answered.
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
          (``PreToolUse:AskUserQuestion``, ``PostToolUse:AskUserQuestion``,
          ``PostToolUse:Bash``) so each can be reported individually.
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

        # --- PreToolUse with matcher:"AskUserQuestion" (flip "?" before prompt). ---
        pre_tool_use = hooks_block.setdefault("PreToolUse", [])
        if not isinstance(pre_tool_use, list):
            pre_tool_use = []
            hooks_block["PreToolUse"] = pre_tool_use
        if not _has_render_entry(pre_tool_use, matcher="AskUserQuestion"):
            pre_tool_use.append(_render_entry(matcher="AskUserQuestion"))
            installed_events.append("PreToolUse:AskUserQuestion")
        else:
            already_present_events.append("PreToolUse:AskUserQuestion")

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
        return data  # type: ignore[return-value]
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
    """Read the active plan_id from the session cache."""
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
# Permission helpers (thin wrappers over existing scripts)
# ---------------------------------------------------------------------------


def _claude_project_settings_path(project_dir: str | None = None) -> Path:
    """Return the Claude project settings file path to write to."""
    try:
        # Import via the already-bootstrapped sys.path.
        from permission_common import get_project_settings_path_for_write  # type: ignore[import-not-found]

        if project_dir:
            return get_project_settings_path_for_write(Path(project_dir))
        return get_project_settings_path_for_write()
    except ImportError:
        base = Path(project_dir) if project_dir else Path.cwd()
        settings_json = base / ".claude" / "settings.json"
        if settings_json.exists():
            return settings_json
        return base / ".claude" / "settings.local.json"


def _claude_global_settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def _settings_path_for_scope(scope: str) -> Path:
    if scope == "global":
        return _claude_global_settings_path()
    return _claude_project_settings_path()


def _load_settings(path: Path) -> dict[str, Any]:
    try:
        from permission_common import load_settings_path  # type: ignore[import-not-found]

        return load_settings_path(path)
    except ImportError:
        pass
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
    except (OSError, json.JSONDecodeError):
        return {"permissions": {"allow": [], "deny": [], "ask": []}}


def _save_settings(path: Path, settings: dict[str, Any]) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


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
# ClaudeRuntime
# ---------------------------------------------------------------------------


class ClaudeRuntime(Runtime):
    """Claude Code implementation of all 15 platform-runtime operations."""

    # ------------------------------------------------------------------
    # Project lifecycle
    # ------------------------------------------------------------------

    def project_initial_setup(self, project_dir: str, target: str) -> str:
        """One-time project setup for the Claude Code target."""
        if target != "claude":
            return toon_error(
                "project initial-setup",
                "unknown_target",
                f"Target {target!r} is not in the registry; valid targets are: claude, opencode",
            )

        pd = _project_dir_path(project_dir)
        plan_dir = pd / _PLAN_DIR_NAME
        temp_dir = plan_dir / "temp"
        marshal_path = plan_dir / "marshal.json"
        settings_path = pd / ".claude" / "settings.json"

        # Create directory structure.
        try:
            temp_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return toon_error(
                "project initial-setup",
                "io_error",
                f"Failed to create .plan/temp/: {exc}",
            )

        # Write marshal.json with runtime.target.
        marshal_data: dict[str, Any] = {
            "runtime": {"target": "claude"},
            "project_dir": str(pd),
        }
        if not _write_json(marshal_path, marshal_data):
            return toon_error(
                "project initial-setup",
                "io_error",
                f"Failed to write marshal.json at {marshal_path}",
            )

        # Install the full terminal-title hook wiring into .claude/settings.json.
        install_result = _install_terminal_title_hooks(settings_path)
        hook_installed = install_result["io_ok"]

        return toon_success(
            "project initial-setup",
            {
                "target": "claude",
                "project_dir": str(pd),
                "marshal_written": True,
                "hook_installed": hook_installed,
            },
        )

    def project_install_hook(
        self,
        target: str,
        overwrite_statusline: bool = False,
        overwrite_env_disable: bool = False,
    ) -> str:
        """Install the full terminal-title hook wiring into the named settings file.

        Installs the SessionStart capture entry, seven render-trigger hook
        entries, the ``statusLine`` command, and
        ``env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE``. Each block is idempotent.

        The ``target`` argument is one of two shapes:

        - ``"claude"`` — the platform identifier. Resolves to the project's
          Claude Code settings file via ``_claude_project_settings_path()``
          (``.claude/settings.json`` when present, else ``.claude/settings.local.json``).
          This is the canonical invocation from the marshall-steward menu.
        - An absolute path ending in ``.json`` — explicit settings file path.
          Used by tests and recovery flows that need to target a specific file.

        Any other value (relative path, unknown identifier) is rejected with
        ``unknown_target`` rather than silently creating a stray file.

        The two ``overwrite_*`` flags govern conflict resolution when an
        existing ``statusLine`` or env value differs from ours:

        - ``overwrite_statusline=False`` (default): preserve the foreign value
          and report ``statusLine_status: already_present_other`` so the
          marshall-steward menu can surface an AskUserQuestion.
        - ``overwrite_statusline=True``: overwrite with our command and report
          ``statusLine_status: overwritten``.

        ``overwrite_env_disable`` carries identical semantics for the env entry.
        """
        if target == "claude":
            settings_path = _claude_project_settings_path()
        else:
            candidate = Path(target)
            if candidate.is_absolute() and candidate.suffix == ".json":
                settings_path = candidate
            else:
                return toon_error(
                    "project install-hook",
                    "unknown_target",
                    f"target {target!r} must be the platform identifier 'claude' "
                    f"or an absolute path to a .json settings file",
                )

        install_result = _install_terminal_title_hooks(
            settings_path,
            overwrite_statusline=overwrite_statusline,
            overwrite_env_disable=overwrite_env_disable,
        )
        if not install_result["io_ok"]:
            return toon_error(
                "project install-hook",
                "io_error",
                f"Failed to install terminal-title hooks into {settings_path}",
            )

        installed_events = install_result["installed_events"]
        already_present_events = install_result["already_present_events"]
        # Top-level convenience signal: True iff nothing fresh was installed
        # AND no overwrite-other signal needs the caller's attention.
        all_already_present = (
            not installed_events
            and install_result["statusLine_status"]
            in ("already_present", "already_present_other")
            and install_result["env_status"]
            in ("already_present", "already_present_other")
        )

        return toon_success(
            "project install-hook",
            {
                "target": target,
                "settings_path": str(settings_path),
                "hook_installed": True,
                "already_present": all_already_present,
                "installed_events": installed_events,
                "already_present_events": already_present_events,
                "statusLine_status": install_result["statusLine_status"],
                "env_status": install_result["env_status"],
            },
        )

    # ------------------------------------------------------------------
    # Session operations
    # ------------------------------------------------------------------

    def session_capture(self, plan_id: str) -> str:
        """Read $CLAUDE_CODE_SESSION_ID and store via manage-status."""
        session_id = os.environ.get("CLAUDE_CODE_SESSION_ID")
        if not session_id:
            return toon_error(
                "session capture",
                "hook_not_configured",
                "$CLAUDE_CODE_SESSION_ID is unset; run marshall-steward to install the SessionStart hook",
            )

        stored = _manage_status_store_session(plan_id, session_id)
        return toon_success(
            "session capture",
            {
                "plan_id": plan_id,
                "session_id": session_id,
                "stored": stored,
            },
        )

    def session_render_title(self, statusline: bool = False) -> str:
        """Resolve session → plan, read ``status.json``, compose, and emit.

        Both invocation modes share one stdout contract: stdout carries the
        exact bytes Claude Code's host parser consumes, and **nothing else**.
        Mixed payloads — JSON envelope plus a TOON success/noop row glued to
        it, or TOON noop instead of empty output — violate the contract and
        are dropped by the host parser (see ``hook-authoring-guide.md`` §
        "Hook output contract").

        Hook mode (``statusline=False``):
          - Success: write the JSON envelope to stdout, return "".
          - Noop: write nothing to stdout, return "".
        statusLine mode (``statusline=True``):
          - Success: write plain ``{composed}`` to stdout, return "".
          - Noop: write nothing to stdout, return "".

        The title state (``current_phase``, ``short_description``,
        ``title_token``) is read from ``status.json`` — the SINGLE source of
        persisted title state — and the body-format + glyph vocabulary + icon
        palette live in the ``manage-terminal-title`` composer
        (:func:`manage_terminal_title.compose`), consumed via import. This
        module is the resolve+read+emit layer only; it owns neither the icon
        palette nor the body format. The ✅ terminal-icon override for
        ``complete``/``archived`` phases is applied inside ``compose``.

        Hook-mode envelope (Step 5) carries two reader channels in one JSON
        object. ``terminalSequence`` (the OSC-0 escape) is emitted for every
        event. ``hookSpecificOutput.sessionTitle`` — the web/desktop
        session-title channel, equivalent to ``/rename`` and UI-only — is
        emitted ONLY for the two events Claude Code supports it on:

          - ``UserPromptSubmit``; and
          - ``SessionStart`` when ``source ∈ {"startup", "resume"}`` (the
            ``"clear"`` and ``"compact"`` sources do NOT support it).

        For every other event the envelope stays exactly ``{"terminalSequence":
        osc_seq}`` and never carries a stray ``sessionTitle``. The
        ``sessionTitle`` body is the bare ``pm:{phase}[:{short}]`` body (via
        :func:`manage_terminal_title._compose_body`) WITHOUT the icon glyph,
        because the web title channel is static per-prompt text and cannot carry
        the live status icon. A missing or malformed ``hook_event_name`` /
        ``source`` omits ``sessionTitle`` and still emits ``terminalSequence``
        (best-effort/no-raise contract).

        Every return is the empty string so the wrapper ``main()`` (which
        skips ``print()`` on empty results) cannot append a TOON tail.
        """

        # Step 1: Read $CLAUDE_CODE_SESSION_ID.
        session_id = os.environ.get("CLAUDE_CODE_SESSION_ID")
        if not session_id:
            return ""

        # Step 2: Resolve session_id → plan_id via session cache.
        plan_id = _read_active_plan(session_id)
        if not plan_id:
            return ""

        # Step 3: Resolve plan_id → title state via status.json (live first,
        # archived status.json glob fallback). status.json is the SINGLE source
        # of persisted title state — title-body.txt is no longer read anywhere.
        state = _read_title_state(plan_id)
        if state is None:
            return ""

        # Step 4: Parse the hook event (hook mode only) and compose the title.
        #
        # statusLine mode receives no hook stdin payload, so it composes with
        # event=None (the composer applies the active icon for non-terminal
        # phases and the ✅ override for terminal ones). Hook mode reads the
        # JSON payload Claude Code writes to stdin and passes the event +
        # tool_name to the composer. The parse is best-effort: missing, empty,
        # or malformed stdin yields event=None and never raises.
        #
        # The parsed ``hook_event_name`` and ``source`` are also retained for
        # Step 5's conditional ``sessionTitle`` emit. Both default to None so a
        # missing/malformed payload omits ``sessionTitle`` and still emits
        # ``terminalSequence``.
        hook_event_name: str | None = None
        source: str | None = None
        tool_name: str | None = None
        if not statusline:
            try:
                raw_payload = sys.stdin.read() if not sys.stdin.isatty() else ""
                payload = json.loads(raw_payload) if raw_payload.strip() else {}
                if isinstance(payload, dict):
                    hook_event_name = payload.get("hook_event_name")
                    source = payload.get("source")
                    tool_name = payload.get("tool_name")
            except (OSError, ValueError):
                hook_event_name = None
                source = None
                tool_name = None

        composed = compose(state, hook_event_name, tool_name=tool_name)
        if not composed:
            return ""

        # Step 5: Emit the title. Both modes write to stdout and return "".
        if statusline:
            try:
                sys.stdout.write(composed)
                sys.stdout.flush()
            except OSError:
                pass
            return ""

        try:
            osc_seq = f"\x1b]0;{composed}\x07"
            envelope: dict[str, Any] = {"terminalSequence": osc_seq}
            # Conditional web/desktop session-title channel: emit
            # ``hookSpecificOutput.sessionTitle`` (icon-free body) ONLY for the
            # two events Claude Code supports it on — UserPromptSubmit, and
            # SessionStart with source in {startup, resume}. All other events
            # keep the envelope as ``{"terminalSequence": osc_seq}``.
            emit_session_title = hook_event_name == "UserPromptSubmit" or (
                hook_event_name == "SessionStart" and source in ("startup", "resume")
            )
            if emit_session_title:
                bare_body = _compose_body(state)
                if bare_body:
                    envelope["hookSpecificOutput"] = {
                        "hookEventName": hook_event_name,
                        "sessionTitle": bare_body,
                    }
            sys.stdout.write(json.dumps(envelope))
            sys.stdout.flush()
        except OSError:
            pass
        return ""

    def session_push_title_token(self, plan_id: str, icon: str) -> str:
        """Push a live terminal title for *plan_id* directly to ``/dev/tty``.

        Reads the plan's title state from ``status.json`` via
        :func:`_read_title_state`, composes the ``'{icon} {glyph} {body}'``
        string via :func:`manage_terminal_title.compose` (with *icon* as the
        push-mode icon override and ``event=None``), and writes the OSC escape
        (``\\x1b]0;{composed}\\x07``) directly to ``/dev/tty``.

        Best-effort: a silent no-op (``pushed: false``) when the state is
        absent / unrenderable or when ``/dev/tty`` is not openable (CI,
        background, no controlling terminal). Never raises.

        Returns a success TOON noting whether the push reached a TTY.
        """
        state = _read_title_state(plan_id)
        if state is None:
            return toon_success(
                "session push-title-token",
                {"plan_id": plan_id, "pushed": False, "reason": "no_title_state"},
            )

        composed = compose(state, None, icon_override=icon)
        if not composed:
            return toon_success(
                "session push-title-token",
                {"plan_id": plan_id, "pushed": False, "reason": "no_title_state"},
            )

        pushed = False
        try:
            with open("/dev/tty", "w", encoding="utf-8") as tty:
                tty.write(f"\x1b]0;{composed}\x07")
                tty.flush()
            pushed = True
        except OSError:
            pushed = False

        return toon_success(
            "session push-title-token",
            {"plan_id": plan_id, "pushed": pushed},
        )

    # ------------------------------------------------------------------
    # Permission operations
    # ------------------------------------------------------------------

    def permission_configure(self, scope: str, permissions: list[str]) -> str:
        """Write a raw permission list to the Claude Code settings."""
        if scope not in ("project", "global"):
            return toon_error(
                "permission configure",
                "invalid_scope",
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )

        settings_path = _settings_path_for_scope(scope)
        settings = _load_settings(settings_path)
        settings["permissions"]["allow"] = list(permissions)

        if not _save_settings(settings_path, settings):
            return toon_error(
                "permission configure",
                "io_error",
                f"Failed to write settings to {settings_path}",
            )

        return toon_success(
            "permission configure",
            {
                "scope": scope,
                "permissions_written": len(permissions),
                "target_file": str(settings_path),
            },
        )

    def permission_analyze(
        self, scope: str, checks: list[str], marshal_path: str | None
    ) -> str:
        """Read-only audit of permission configuration."""
        valid_scopes = ("global", "project", "both")
        if scope not in valid_scopes:
            return toon_error(
                "permission analyze",
                "invalid_scope",
                f"--scope must be 'global', 'project', or 'both'; got {scope!r}",
            )

        valid_checks = {"redundant", "suspicious", "missing-steps", "all"}
        for check in checks:
            if check not in valid_checks:
                return toon_error(
                    "permission analyze",
                    "invalid_check",
                    f"Unknown check {check!r}; valid checks are: redundant, suspicious, missing-steps, all",
                )

        # Expand 'all'.
        expanded = {"redundant", "suspicious", "missing-steps"} if "all" in checks else set(checks)

        if "missing-steps" in expanded and not marshal_path:
            return toon_error(
                "permission analyze",
                "marshal_not_found",
                "--marshal is required when 'missing-steps' check is included",
            )

        findings: list[dict[str, str]] = []
        checks_run = sorted(expanded)

        # Load settings files.
        global_path = _claude_global_settings_path()
        project_path = _claude_project_settings_path()
        global_settings = _load_settings(global_path) if scope in ("global", "both") else {}
        project_settings = _load_settings(project_path) if scope in ("project", "both") else {}

        global_allow: list[str] = global_settings.get("permissions", {}).get("allow", [])
        project_allow: list[str] = project_settings.get("permissions", {}).get("allow", [])

        # Redundant check: entries present in both global and project.
        if "redundant" in expanded:
            global_set = set(global_allow)
            project_set = set(project_allow)
            for perm in global_set & project_set:
                findings.append(
                    {
                        "check": "redundant",
                        "severity": "info",
                        "details": f"{perm} present in both global and project settings",
                    }
                )

        # Suspicious check: detect security anti-patterns.
        if "suspicious" in expanded:
            suspicious_patterns = [
                (r"Write\(/tmp/", "medium", "Write(/tmp/**) is a broad write permission; consider scoping to a specific path"),
                (r"Bash\(sudo:", "high", "Bash(sudo:*) grants unrestricted sudo; remove or restrict the pattern"),
                (r"Bash\(\*\)", "high", "Bash(*) allows any bash command; this is dangerously broad"),
                (r"Write\(/\*\*\)", "high", "Write(/**) grants write access to the entire filesystem"),
                (r"Read\(/\*\*\)", "medium", "Read(/**) grants read access to the entire filesystem"),
            ]
            all_allow = list(global_allow) + list(project_allow) if scope == "both" else (
                global_allow if scope == "global" else project_allow
            )
            for perm in all_allow:
                for pattern, severity, details in suspicious_patterns:
                    if re.search(pattern, perm):
                        findings.append({"check": "suspicious", "severity": severity, "details": details})

        # Missing-steps check: find project:{skill} steps without matching permission.
        if "missing-steps" in expanded and marshal_path:
            try:
                from permission_doctor import (  # type: ignore[import-not-found]  # noqa: I001
                    extract_project_steps,
                    load_marshal_config,
                    skill_permission_covered,
                )

                marshal_data, marshal_err = load_marshal_config(marshal_path)
                if not marshal_err and marshal_data:
                    steps = extract_project_steps(marshal_data)
                    target_allow = project_allow if scope == "project" else list(set(global_allow + project_allow))
                    for step_entry in steps:
                        skill_name = step_entry.get("skill", "")
                        if skill_name and not skill_permission_covered(skill_name, target_allow):
                            findings.append(
                                {
                                    "check": "missing-steps",
                                    "severity": "high",
                                    "details": f"project:{skill_name} has no matching skill permission",
                                }
                            )
            except ImportError:
                pass

        summary: dict[str, int] = {"high": 0, "medium": 0, "info": 0}
        for f in findings:
            sev = f.get("severity", "info")
            if sev in summary:
                summary[sev] += 1

        return toon_success(
            "permission analyze",
            {
                "scope": scope,
                "checks_run": checks_run,
                "total_findings": len(findings),
                "findings": findings,
                "summary": summary,
            },
        )

    def permission_fix(
        self,
        scope: str,
        operation: str,
        permissions: list[str],
        dry_run: bool,
    ) -> str:
        """Apply hygienic fixes to permission configuration."""
        if scope not in ("project", "global"):
            return toon_error(
                "permission fix",
                "invalid_scope",
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )

        valid_ops = ("normalize", "add", "remove", "ensure", "consolidate")
        if operation not in valid_ops:
            return toon_error(
                "permission fix",
                "invalid_operation",
                f"--operation must be one of {valid_ops}; got {operation!r}",
            )

        settings_path = _settings_path_for_scope(scope)
        settings = _load_settings(settings_path)
        allow: list[str] = settings["permissions"]["allow"]

        changes_applied = 0
        proposed_additions: list[str] = []

        if operation == "normalize":
            original = list(allow)
            # Remove duplicates and sort.
            deduped = list(dict.fromkeys(allow))
            sorted_allow = sorted(deduped)
            # Add defaults if missing.
            defaults = [
                "Edit(.plan/**)",
                "Write(.plan/**)",
                "Read(~/.claude/plugins/cache/**)",
                "Bash(python3 .plan/execute-script.py *)",
            ]
            for d in defaults:
                if d not in sorted_allow:
                    sorted_allow.append(d)
            sorted_allow = sorted(sorted_allow)
            changes_applied = len([p for p in sorted_allow if p not in original]) + (
                len(original) - len(deduped)
            )
            if not dry_run:
                settings["permissions"]["allow"] = sorted_allow
                _save_settings(settings_path, settings)

        elif operation == "add":
            for perm in permissions:
                if perm not in allow:
                    if not dry_run:
                        allow.append(perm)
                        changes_applied += 1
                    else:
                        proposed_additions.append(perm)
            if not dry_run:
                settings["permissions"]["allow"] = allow
                _save_settings(settings_path, settings)

        elif operation == "remove":
            original_len = len(allow)
            allow = [p for p in allow if p not in permissions]
            changes_applied = original_len - len(allow)
            if not dry_run:
                settings["permissions"]["allow"] = allow
                _save_settings(settings_path, settings)

        elif operation == "ensure":
            for perm in permissions:
                if perm not in allow:
                    if not dry_run:
                        allow.append(perm)
                        changes_applied += 1
                    else:
                        proposed_additions.append(perm)
            if not dry_run:
                settings["permissions"]["allow"] = allow
                _save_settings(settings_path, settings)

        elif operation == "consolidate":
            # Group permissions by tool type and base pattern; merge enumerated into wildcards.
            pattern = re.compile(r"^(\w+)\((.+)\)$")
            groups: dict[str, list[str]] = {}
            for perm in allow:
                m = pattern.match(perm)
                if m:
                    tool_type = m.group(1)
                    groups.setdefault(tool_type, []).append(perm)

            new_allow = list(allow)
            for tool_type, perms in groups.items():
                if len(perms) >= 3:
                    # Replace enumerated entries with a wildcard.
                    wildcard = f"{tool_type}(*)"
                    if wildcard not in new_allow:
                        for p in perms:
                            try:
                                new_allow.remove(p)
                                changes_applied += 1
                            except ValueError:
                                pass
                        new_allow.append(wildcard)

            if not dry_run:
                settings["permissions"]["allow"] = new_allow
                _save_settings(settings_path, settings)

        result: dict[str, Any] = {
            "scope": scope,
            "fix_operation": operation,
            "dry_run": dry_run,
            "target_file": str(settings_path),
            "changes_applied": 0 if dry_run else changes_applied,
        }
        if dry_run and proposed_additions:
            result["proposed_additions"] = proposed_additions

        return toon_success("permission fix", result)

    def permission_ensure_wildcards(
        self, scope: str, marketplace_dir: str, dry_run: bool
    ) -> str:
        """Ensure marketplace bundle wildcard permissions exist."""
        if scope not in ("project", "global"):
            return toon_error(
                "permission ensure-wildcards",
                "invalid_scope",
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )

        settings_path = _settings_path_for_scope(scope)
        settings = _load_settings(settings_path)
        allow: list[str] = settings["permissions"]["allow"]

        # Discover bundles from the marketplace directory.
        mp_path = Path(marketplace_dir)
        bundles_scanned = 0
        wildcards_added = 0
        wildcards_already_present = 0
        proposed_additions: list[str] = []

        if mp_path.is_dir():
            for bundle_dir in sorted(mp_path.iterdir()):
                if not bundle_dir.is_dir():
                    continue
                plugin_json = bundle_dir / ".claude-plugin" / "plugin.json"
                if not plugin_json.is_file():
                    continue
                bundles_scanned += 1
                bundle_name = bundle_dir.name
                skill_wildcard = f"Skill({bundle_name}:*)"
                cmd_wildcard = f"SlashCommand(/{bundle_name}:*)"
                for wildcard in (skill_wildcard, cmd_wildcard):
                    if wildcard in allow:
                        wildcards_already_present += 1
                    else:
                        if dry_run:
                            proposed_additions.append(wildcard)
                        else:
                            allow.append(wildcard)
                            wildcards_added += 1

        if not dry_run:
            settings["permissions"]["allow"] = allow
            _save_settings(settings_path, settings)

        result: dict[str, Any] = {
            "scope": scope,
            "marketplace_dir": marketplace_dir,
            "dry_run": dry_run,
            "bundles_scanned": bundles_scanned,
            "wildcards_added": 0 if dry_run else wildcards_added,
            "wildcards_already_present": wildcards_already_present,
            "target_file": str(settings_path),
        }
        if dry_run and proposed_additions:
            result["proposed_additions"] = proposed_additions

        return toon_success("permission ensure-wildcards", result)

    def permission_ensure_steps(
        self, marshal_path: str, scope: str, dry_run: bool
    ) -> str:
        """Ensure permissions exist for all project:{skill} steps."""
        if scope not in ("project", "global"):
            return toon_error(
                "permission ensure-steps",
                "invalid_scope",
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )

        mp = Path(marshal_path)
        if not mp.is_file():
            return toon_error(
                "permission ensure-steps",
                "marshal_not_found",
                f"{marshal_path} not found; run 'project initial-setup' first",
            )

        steps: list[dict[str, Any]] = []
        try:
            from permission_doctor import (  # type: ignore[import-not-found]  # noqa: I001
                extract_project_steps,
                load_marshal_config,
                skill_permission_covered,
            )

            marshal_data, marshal_err = load_marshal_config(marshal_path)
            if not marshal_err and marshal_data:
                steps = extract_project_steps(marshal_data)

            settings_path = _settings_path_for_scope(scope)
            settings = _load_settings(settings_path)
            allow: list[str] = settings["permissions"]["allow"]

            steps_scanned = len(steps)
            permissions_added = 0
            permissions_already_present = 0
            proposed_additions: list[str] = []

            for step_entry in steps:
                skill_name = step_entry.get("skill", "")
                if not skill_name:
                    continue
                skill_perm = f"Skill({skill_name})"
                if skill_permission_covered(skill_name, allow):
                    permissions_already_present += 1
                else:
                    if dry_run:
                        proposed_additions.append(skill_perm)
                    else:
                        allow.append(skill_perm)
                        permissions_added += 1

            if not dry_run:
                settings["permissions"]["allow"] = allow
                _save_settings(settings_path, settings)

        except ImportError:
            settings_path = _settings_path_for_scope(scope)
            settings = _load_settings(settings_path)
            allow = settings["permissions"]["allow"]
            steps_scanned = 0
            permissions_added = 0
            permissions_already_present = 0
            proposed_additions = []

        result: dict[str, Any] = {
            "marshal": marshal_path,
            "scope": scope,
            "dry_run": dry_run,
            "steps_scanned": steps_scanned,
            "permissions_added": 0 if dry_run else permissions_added,
            "permissions_already_present": permissions_already_present,
            "target_file": str(settings_path),
        }
        if dry_run and proposed_additions:
            result["proposed_additions"] = proposed_additions

        return toon_success("permission ensure-steps", result)

    def permission_web_analyze(self, scope: str) -> str:
        """Read-only analysis of WebFetch domain permissions."""
        valid_scopes = ("global", "project", "both")
        if scope not in valid_scopes:
            return toon_error(
                "permission web-analyze",
                "invalid_scope",
                f"--scope must be 'global', 'project', or 'both'; got {scope!r}",
            )

        _WF_RE = re.compile(r"^WebFetch\((.+)\)$")

        def _extract_webfetch_domains(allow: list[str]) -> list[str]:
            domains = []
            for perm in allow:
                m = _WF_RE.match(perm)
                if m:
                    domains.append(m.group(1))
            return domains

        global_allow: list[str] = []
        project_allow: list[str] = []

        if scope in ("global", "both"):
            gs = _load_settings(_claude_global_settings_path())
            global_allow = gs.get("permissions", {}).get("allow", [])

        if scope in ("project", "both"):
            ps = _load_settings(_claude_project_settings_path())
            project_allow = ps.get("permissions", {}).get("allow", [])

        global_domains = _extract_webfetch_domains(global_allow)
        project_domains = _extract_webfetch_domains(project_allow)

        # Categorize domains.
        _MAJOR_PATTERNS = re.compile(
            r"(github\.com|stackoverflow\.com|docs\.python\.org|docs\.oracle\.com|"
            r"developer\.mozilla\.org|npmjs\.com|pypi\.org|mvnrepository\.com|"
            r"api\.github\.com|raw\.githubusercontent\.com)"
        )
        _SUSPICIOUS_PATTERNS = re.compile(r"(\.xyz$|\.tk$|\.pw$|pastebin\.com|bit\.ly)")

        seen: set[str] = set()
        domain_rows: list[dict[str, Any]] = []

        for domain in global_domains:
            is_dup = domain in seen
            seen.add(domain)
            category = "major" if _MAJOR_PATTERNS.search(domain) else (
                "suspicious" if _SUSPICIOUS_PATTERNS.search(domain) else "unknown"
            )
            domain_rows.append(
                {"domain": domain, "category": category, "scope": "global", "duplicate": is_dup}
            )

        for domain in project_domains:
            is_dup = domain in seen
            seen.add(domain)
            category = "major" if _MAJOR_PATTERNS.search(domain) else (
                "suspicious" if _SUSPICIOUS_PATTERNS.search(domain) else "unknown"
            )
            domain_rows.append(
                {"domain": domain, "category": category, "scope": "project", "duplicate": is_dup}
            )

        return toon_success(
            "permission web-analyze",
            {
                "scope": scope,
                "total_domains": len(domain_rows),
                "domains": domain_rows,
            },
        )

    def permission_web_apply(
        self,
        scope: str,
        add: list[str],
        remove: list[str],
        dry_run: bool,
    ) -> str:
        """Add or remove WebFetch domain permissions."""
        if scope not in ("project", "global"):
            return toon_error(
                "permission web-apply",
                "invalid_scope",
                f"--scope must be 'project' or 'global'; got {scope!r}",
            )

        settings_path = _settings_path_for_scope(scope)
        settings = _load_settings(settings_path)
        allow: list[str] = settings["permissions"]["allow"]

        _WF_RE = re.compile(r"^WebFetch\((.+)\)$")

        # Build current domain set.
        current_domains = {m.group(1) for p in allow if (m := _WF_RE.match(p))}

        domains_added = 0
        domains_removed = 0

        if not dry_run:
            for domain in add:
                perm = f"WebFetch({domain})"
                if perm not in allow:
                    allow.append(perm)
                    domains_added += 1

            remove_set = {f"WebFetch({d})" for d in remove}
            original_len = len(allow)
            allow = [p for p in allow if p not in remove_set]
            domains_removed = original_len - len(allow)

            settings["permissions"]["allow"] = allow
            _save_settings(settings_path, settings)
        else:
            domains_added = sum(1 for d in add if d not in current_domains)
            domains_removed = 0
            for d in remove:
                for p in allow:
                    m = _WF_RE.match(p)
                    if m and m.group(1) == d:
                        domains_removed += 1
                        break

        return toon_success(
            "permission web-apply",
            {
                "scope": scope,
                "dry_run": dry_run,
                "domains_added": domains_added,
                "domains_removed": domains_removed,
                "target_file": str(settings_path),
            },
        )

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def metrics_capture(
        self, plan_id: str, phase: str, total_tokens: int | None
    ) -> str:
        """Record token consumption for a planning phase on Claude."""
        if total_tokens is not None:
            # Manual override: store directly.
            _write_token_cursor(plan_id, phase, total_tokens)
            _manage_metrics_end_phase(plan_id, phase, total_tokens)
            return toon_success(
                "metrics capture",
                {
                    "plan_id": plan_id,
                    "phase": phase,
                    "tokens_captured": total_tokens,
                    "cursor_updated": True,
                    "source": "manual",
                },
            )

        # Automatic: read session_id from plan metadata, open JSONL, sum tokens.
        session_id = _manage_status_read_session(plan_id)
        if not session_id:
            return toon_noop(
                "metrics capture",
                "Session ID found but transcript/DB query returned no usage data for this phase",
                "Pass --total-tokens manually",
            )

        transcript = _find_transcript(session_id)
        if not transcript:
            return toon_noop(
                "metrics capture",
                "Session ID found but transcript/DB query returned no usage data for this phase",
                "Pass --total-tokens manually",
            )

        # Sum ALL tokens in transcript, subtract cursor (tokens from prior captures).
        transcript_total = _sum_tokens_from_jsonl(transcript)
        prior_cursor = _read_token_cursor(plan_id, phase)
        captured = max(0, transcript_total - prior_cursor)

        if captured == 0:
            return toon_noop(
                "metrics capture",
                "Session ID found but transcript/DB query returned no usage data for this phase",
                "Pass --total-tokens manually",
            )

        new_cursor = transcript_total
        _write_token_cursor(plan_id, phase, new_cursor)
        _manage_metrics_end_phase(plan_id, phase, captured)

        return toon_success(
            "metrics capture",
            {
                "plan_id": plan_id,
                "phase": phase,
                "session_id": session_id,
                "tokens_captured": captured,
                "cursor_updated": True,
            },
        )

    # ------------------------------------------------------------------
    # Subagent dispatch
    # ------------------------------------------------------------------

    def subagent_dispatch(
        self,
        agent: str,
        prompt_file: str | None,
        context: dict[str, Any] | None,
    ) -> str:
        """Return Claude Code Task: invocation parameters for a subagent."""
        # Locate the agent markdown file.
        agent_path = _find_agent_file(agent)
        if agent_path is None:
            return toon_error(
                "subagent dispatch",
                "prompt_not_found",
                f"Agent {agent!r} not found in marketplace tree",
            )

        # If a prompt_file override is provided, validate it exists.
        if prompt_file:
            pf = Path(prompt_file)
            if not pf.is_file():
                return toon_error(
                    "subagent dispatch",
                    "prompt_not_found",
                    f"prompt file not found: {prompt_file}",
                )
            try:
                prompt_body = pf.read_text(encoding="utf-8")
            except OSError:
                return toon_error(
                    "subagent dispatch",
                    "prompt_not_found",
                    f"prompt file not found: {prompt_file}",
                )
        else:
            try:
                prompt_body = agent_path.read_text(encoding="utf-8")
            except OSError:
                return toon_error(
                    "subagent dispatch",
                    "prompt_not_found",
                    f"Agent {agent!r} not found in marketplace tree",
                )

        # Parse frontmatter.
        fm = _parse_agent_frontmatter(agent_path)
        agent_description = fm.get("description", "")
        tools = fm.get("tools", [])

        # Check for unmapped tools.
        unmapped = [t for t in tools if t in _UNMAPPED_TOOLS]
        if unmapped:
            return toon_noop(
                "subagent dispatch",
                f"Agent {agent!r} requires unmapped tools: {', '.join(unmapped)}",
                "Remove unsupported tools from agent frontmatter or inline the agent logic",
            )

        # Merge context into prompt body.
        if context:
            context_block = "\n".join(f"{k}: {v}" for k, v in context.items())
            prompt_body = f"## Context\n\n{context_block}\n\n{prompt_body}"

        task_description = _short_description_from_agent(agent_description)

        return toon_success(
            "subagent dispatch",
            {
                "platform": "claude",
                "invocation": {
                    "tool": "Task",
                    "description": task_description,
                    "prompt": prompt_body,
                    "subagent_type": agent,
                },
            },
        )

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def health_check(self, checks: str) -> str:
        """Verify Claude Code platform integration."""
        valid_checks = {"all", "permissions", "display", "mcp-diagnostics"}
        check_set_input: set[str] = {c.strip() for c in checks.split(",") if c.strip()}
        for c in check_set_input:
            if c not in valid_checks:
                return toon_error(
                    "health-check",
                    "invalid_check",
                    f"Unknown check {c!r}; valid checks are: all, permissions, display, mcp-diagnostics",
                )

        if "all" in check_set_input:
            checks_to_run = {"permissions", "display", "mcp-diagnostics", "hook"}
        else:
            checks_to_run = check_set_input | {"hook"}

        results: list[dict[str, Any]] = []
        all_healthy = True

        if "permissions" in checks_to_run:
            project_settings = _claude_project_settings_path()
            healthy = project_settings.is_file()
            detail = (
                f"settings.local.json present; allow array has "
                f"{len(_load_settings(project_settings).get('permissions', {}).get('allow', []))} entries"
                if healthy
                else "settings.local.json not found; run permission configure"
            )
            results.append({"check": "permissions", "healthy": healthy, "detail": detail})
            if not healthy:
                all_healthy = False

        if "display" in checks_to_run:
            settings_local = Path(".claude") / "settings.local.json"
            sd = _read_json(settings_local) or {}
            lines, healthy = _diagnose_display_entries(sd)
            if healthy:
                detail = "; ".join(lines)
            else:
                detail = (
                    "; ".join(lines)
                    + "; run marshall-steward or project install-hook to install "
                    "any MISSING entry"
                )
            results.append({"check": "display", "healthy": healthy, "detail": detail})
            if not healthy:
                all_healthy = False

        if "mcp-diagnostics" in checks_to_run:
            # Attempt TCP connection to the JetBrains MCP server port.
            import socket

            mcp_host = "127.0.0.1"
            mcp_port = 64342
            try:
                with socket.create_connection((mcp_host, mcp_port), timeout=2):
                    healthy = True
                    detail = f"MCP server reachable at {mcp_host}:{mcp_port}"
            except (OSError, ConnectionRefusedError):
                healthy = False
                detail = f"MCP server not reachable at {mcp_host}:{mcp_port}; start JetBrains IDE with MCP plugin"
            results.append({"check": "mcp-diagnostics", "healthy": healthy, "detail": detail})
            if not healthy:
                all_healthy = False

        if "hook" in checks_to_run:
            def _hook_in_settings_file(path: Path) -> bool:
                """Return True when the SessionStart hook command is found in *path*."""
                if not path.is_file():
                    return False
                sd = _read_json(path) or {}
                session_starts = sd.get("hooks", {}).get("SessionStart", [])
                for entry in session_starts:
                    if isinstance(entry, dict):
                        for h in entry.get("hooks", []):
                            if isinstance(h, dict) and h.get("command") == _HOOK_COMMAND:
                                return True
                return False

            settings_json = Path(".claude") / "settings.json"
            settings_local = Path(".claude") / "settings.local.json"
            in_settings_json = _hook_in_settings_file(settings_json)
            in_settings_local = _hook_in_settings_file(settings_local)
            healthy = in_settings_json or in_settings_local

            if in_settings_json and in_settings_local:
                detail = "SessionStart hook entry present in .claude/settings.json and .claude/settings.local.json"
            elif in_settings_json:
                detail = "SessionStart hook entry present in .claude/settings.json"
            elif in_settings_local:
                detail = "SessionStart hook entry present in .claude/settings.local.json"
            else:
                detail = (
                    "SessionStart hook entry missing from both .claude/settings.json and "
                    ".claude/settings.local.json; run marshall-steward to install"
                )

            results.append({"check": "hook", "healthy": healthy, "detail": detail})
            if not healthy:
                all_healthy = False

        return toon_success(
            "health-check",
            {
                "checks_run": [r["check"] for r in results],
                "all_healthy": all_healthy,
                "results": results,
            },
        )
