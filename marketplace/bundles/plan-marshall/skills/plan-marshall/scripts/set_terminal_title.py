#!/usr/bin/env python3
"""Emit a terminal title (OSC) and/or statusline string that reflects the
active plan-marshall plan and phase plus a live status icon.

Invoked from Claude Code hooks (SessionStart / UserPromptSubmit / Notification /
Stop) and from the Claude Code statusline command. Never raises to the caller:
any failure falls back to `<icon> claude` and exit 0 so the user's session is
never disrupted.
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
    "running": "\u25b6",   # ▶
    "waiting": "?",
    "idle": "\u25ef",      # ◯
    "done": "\u2713",      # ✓
}

_FALLBACK_ICON = _STATUS_ICONS["idle"]

_WORKTREE_RE = re.compile(r".*/\.claude/worktrees/(?P<id>[^/]+)(?:/.*)?$")

_PLAN_SHORT_MAX = 20
_PLAN_SHORT_TAIL = 14


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
        repo_root = common_dir.parent
        candidate = repo_root / ".plan" / "local" / "plans" / plan_id / "status.json"
        if candidate.is_file():
            return candidate
    repo_root = _walk_up_for_plan(Path(cwd))
    if repo_root is None:
        return None
    candidate = repo_root / ".plan" / "local" / "plans" / plan_id / "status.json"
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
    return "\u2026" + plan_id[-_PLAN_SHORT_TAIL:]


def _build_title(status: str, plan_id: str | None, phase: str | None) -> str:
    icon = _STATUS_ICONS.get(status, _FALLBACK_ICON)
    if plan_id and phase:
        return f"{icon} {_plan_short(plan_id)}:{phase}"
    return f"{icon} claude"


def _read_cwd_from_stdin() -> str | None:
    if sys.stdin is None or sys.stdin.isatty():
        return None
    try:
        raw = sys.stdin.read()
    except OSError:
        return None
    if not raw.strip():
        return None
    try:
        payload = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    cwd = payload.get("cwd")
    return cwd if isinstance(cwd, str) and cwd else None


def _emit_osc(title: str) -> None:
    escape = f"\033]0;{title}\007"
    try:
        with open("/dev/tty", "w", encoding="utf-8") as tty:
            tty.write(escape)
            tty.flush()
    except OSError:
        return


def build_title(status: str, cwd: str) -> str:
    plan_id = _resolve_plan_id(cwd)
    phase: str | None = None
    if plan_id:
        status_file = _resolve_status_file(cwd, plan_id)
        if status_file is not None:
            phase = _read_phase(status_file)
    if plan_id and not phase:
        plan_id = None
    return _build_title(status, plan_id, phase)


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

    cwd = _read_cwd_from_stdin() or os.getcwd()
    title = build_title(args.status, cwd)

    if args.statusline:
        sys.stdout.write(title)
        sys.stdout.flush()
    else:
        _emit_osc(title)
    return 0


if __name__ == "__main__":
    sys.exit(main())
