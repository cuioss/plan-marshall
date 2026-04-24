#!/usr/bin/env python3
"""Emit a terminal title (OSC) and/or statusline string that reflects the
active plan-marshall plan and phase, the active slash command (if any),
plus a live status icon.

Invoked from Claude Code hooks (SessionStart / UserPromptSubmit / Notification /
PostToolUse(AskUserQuestion) / Stop) and from the Claude Code statusline
command. Never raises to the caller: any failure falls back to `<icon> claude`
and exit 0 so the user's session is never disrupted.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

_STATUS_ICONS = {
    "running": "▶",   # ▶
    "waiting": "?",
    "idle": "◯",      # ◯
    "done": "✓",      # ✓
}

_FALLBACK_ICON = _STATUS_ICONS["idle"]

_WORKTREE_RE = re.compile(r".*/\.claude/worktrees/(?P<id>[^/]+)(?:/.*)?$")

_PLAN_SHORT_MAX = 20
_PLAN_SHORT_TAIL = 14

_COMMAND_TOKEN_RE = re.compile(r"^/([A-Za-z0-9][A-Za-z0-9:_-]*)")
_COMMAND_MAX_LEN = 40


def _resolve_plan_id(cwd: str) -> str | None:
    match = _WORKTREE_RE.match(cwd)
    if match:
        return match.group("id")
    env_plan = os.environ.get("PLAN_ID")
    if env_plan:
        return env_plan.strip() or None
    return None


def _git_common_dir(cwd: str) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    common_dir = Path(result.stdout.strip())
    if not common_dir.is_absolute():
        return None
    return common_dir


def _walk_up_for_plan(start: Path) -> Path | None:
    for candidate in [start, *start.parents]:
        if (candidate / ".plan").is_dir():
            return candidate
    return None


def _resolve_status_file(cwd: str, plan_id: str) -> Path | None:
    common_dir = _git_common_dir(cwd)
    if common_dir is not None:
        candidate = common_dir.parent / ".plan" / "local" / "plans" / plan_id / "status.json"
        if candidate.is_file():
            return candidate
    walk_root = _walk_up_for_plan(Path(cwd))
    if walk_root is None:
        return None
    candidate = walk_root / ".plan" / "local" / "plans" / plan_id / "status.json"
    return candidate if candidate.is_file() else None


def _read_phase(status_file: Path) -> str | None:
    try:
        data = json.loads(status_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    phase = data.get("current_phase") if isinstance(data, dict) else None
    if isinstance(phase, str) and phase:
        return phase
    return None


def _plan_short(plan_id: str) -> str:
    if len(plan_id) <= _PLAN_SHORT_MAX:
        return plan_id
    return "…" + plan_id[-_PLAN_SHORT_TAIL:]


def _command_state_path(session_id: str) -> Path | None:
    if not session_id or "/" in session_id or "\\" in session_id or session_id in ("..", "."):
        return None
    try:
        home = Path.home()
    except (OSError, RuntimeError):
        return None
    return home / ".cache" / "plan-marshall" / "sessions" / session_id / "active-command"


def _extract_command_token(prompt: str) -> str | None:
    if not isinstance(prompt, str):
        return None
    match = _COMMAND_TOKEN_RE.match(prompt.lstrip())
    if not match:
        return None
    token = match.group(1)
    if not token or len(token) > _COMMAND_MAX_LEN:
        return None
    return token


def _write_active_command(session_id: str, command: str) -> None:
    path = _command_state_path(session_id)
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(command, encoding="utf-8")
    except OSError:
        return


def _read_active_command(session_id: str | None) -> str | None:
    if not session_id:
        return None
    path = _command_state_path(session_id)
    if path is None or not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except (OSError, ValueError):
        return None
    if not raw or len(raw) > _COMMAND_MAX_LEN:
        return None
    return raw


def _clear_active_command(session_id: str | None) -> None:
    if not session_id:
        return
    path = _command_state_path(session_id)
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return


def _build_title(
    status: str,
    plan_id: str | None,
    phase: str | None,
    active_command: str | None = None,
) -> str:
    icon = _STATUS_ICONS.get(status, _FALLBACK_ICON)
    if plan_id and phase:
        return f"{icon} {_plan_short(plan_id)}:{phase}"
    if active_command:
        return f"{icon} {active_command}"
    return f"{icon} claude"


def _read_hook_payload() -> dict[str, str | None]:
    empty = {"cwd": None, "prompt": None, "session_id": None}
    if sys.stdin is None or sys.stdin.isatty():
        return empty
    try:
        raw = sys.stdin.read()
    except OSError:
        return empty
    if not raw.strip():
        return empty
    try:
        payload = json.loads(raw)
    except ValueError:
        return empty
    if not isinstance(payload, dict):
        return empty
    cwd = payload.get("cwd")
    prompt = payload.get("prompt")
    session_id = payload.get("session_id")
    return {
        "cwd": cwd if isinstance(cwd, str) and cwd else None,
        "prompt": prompt if isinstance(prompt, str) else None,
        "session_id": session_id if isinstance(session_id, str) and session_id else None,
    }


def _emit_osc(title: str) -> None:
    escape = f"\033]0;{title}\007"
    try:
        with open("/dev/tty", "w", encoding="utf-8") as tty:
            tty.write(escape)
            tty.flush()
    except OSError:
        try:
            sys.stdout.write(escape)
            sys.stdout.flush()
        except OSError:
            return


def build_title(status: str, cwd: str, session_id: str | None = None) -> str:
    plan_id = _resolve_plan_id(cwd)
    phase: str | None = None
    if plan_id:
        status_file = _resolve_status_file(cwd, plan_id)
        if status_file is not None:
            phase = _read_phase(status_file)
    if plan_id and not phase:
        plan_id = None
    active_command: str | None = None
    if not (plan_id and phase):
        active_command = _read_active_command(session_id)
    return _build_title(status, plan_id, phase, active_command)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit plan-marshall terminal title / statusline",
        allow_abbrev=False,
    )
    parser.add_argument("status", choices=sorted(_STATUS_ICONS), help="Live status for the icon")
    parser.add_argument(
        "--statusline",
        action="store_true",
        help="Print the title to stdout for Claude Code statusline (instead of OSC to /dev/tty)",
    )
    args = parser.parse_args(argv)

    payload = _read_hook_payload()
    cwd = payload["cwd"] or os.getcwd()
    session_id = payload["session_id"]

    # Only hook invocations (no --statusline) mutate session state.
    # The statusLine command fires continuously and must be a pure read.
    if not args.statusline and session_id:
        if args.status == "running" and payload["prompt"]:
            token = _extract_command_token(payload["prompt"])
            if token:
                _write_active_command(session_id, token)
        elif args.status == "idle":
            _clear_active_command(session_id)

    title = build_title(args.status, cwd, session_id)

    if args.statusline:
        sys.stdout.write(title)
        sys.stdout.flush()
    else:
        _emit_osc(title)
    return 0


if __name__ == "__main__":
    sys.exit(main())
