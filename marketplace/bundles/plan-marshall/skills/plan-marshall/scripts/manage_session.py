#!/usr/bin/env python3
"""Resolve the active Claude Code session_id and transcript path from disk.

The terminal-title hook (`set_terminal_title.py`) writes the session_id into
`~/.cache/plan-marshall/sessions/{by-cwd/{sha256(cwd)},current}` on every
UserPromptSubmit. This script reads those caches back so main-context skill
calls can obtain the id without reaching for an environment variable.

The `transcript-path` subcommand resolves the absolute path of the Claude
Code session transcript JSONL on disk. Claude Code stores transcripts under
`~/.claude/projects/{cwd-slug}/{session_id}.jsonl`, where `cwd-slug` is the
absolute project cwd with each `/` replaced by `-` (path-slug — distinct
from the SHA256 scheme used for plan-marshall's own cache).

Usage:
    manage_session.py current
    manage_session.py transcript-path --session-id {session_id}
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from file_ops import output_toon, output_toon_error, safe_main  # type: ignore[import-not-found]

_SESSION_ID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _cache_base() -> Path | None:
    try:
        home = Path.home()
    except (OSError, RuntimeError):
        return None
    return home / ".cache" / "plan-marshall" / "sessions"


def _resolve_cwd() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return str(Path.cwd())
    if result.returncode != 0:
        return str(Path.cwd())
    root = result.stdout.strip()
    return root or str(Path.cwd())


def _read_text(path: Path) -> str | None:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except (OSError, ValueError):
        return None
    return raw or None


def cmd_current(_args: argparse.Namespace) -> int:
    base = _cache_base()
    if base is None:
        output_toon_error("session_id_unavailable", "Home directory not resolvable")
        return 0

    cwd = _resolve_cwd()
    cwd_hash = hashlib.sha256(cwd.encode("utf-8")).hexdigest()

    by_cwd = base / "by-cwd" / cwd_hash
    session_id = _read_text(by_cwd)

    if session_id is None:
        current = base / "current"
        session_id = _read_text(current)

    if session_id is None:
        output_toon_error("session_id_unavailable", "No session_id cached for this cwd or singleton")
        return 0

    output_toon({"status": "success", "session_id": session_id})
    return 0


def _projects_root() -> Path | None:
    try:
        home = Path.home()
    except (OSError, RuntimeError):
        return None
    return home / ".claude" / "projects"


def _cwd_to_slug(cwd: str) -> str:
    return cwd.replace("/", "-")


def cmd_transcript_path(args: argparse.Namespace) -> int:
    session_id = args.session_id
    if not _SESSION_ID_RE.match(session_id):
        output_toon_error("invalid_session_id", "session_id must be a UUID (8-4-4-4-12 hex)")
        return 0

    projects = _projects_root()
    if projects is None:
        output_toon_error("transcript_not_found", "Home directory not resolvable")
        return 0

    cwd = _resolve_cwd()
    cwd_slug = _cwd_to_slug(cwd)

    direct = projects / cwd_slug / f"{session_id}.jsonl"
    if direct.is_file():
        output_toon({"status": "success", "transcript_path": str(direct)})
        return 0

    if projects.is_dir():
        for match in projects.glob(f"*/{session_id}.jsonl"):
            if match.is_file():
                output_toon({"status": "success", "transcript_path": str(match)})
                return 0

    output_toon_error("transcript_not_found", f"No transcript JSONL found for session_id {session_id}")
    return 0


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve the active Claude Code session_id from the hook cache",
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("current", help="Return the current session_id", allow_abbrev=False)

    transcript_parser = subparsers.add_parser(
        "transcript-path",
        help="Resolve the absolute path of a session transcript JSONL",
        allow_abbrev=False,
    )
    transcript_parser.add_argument(
        "--session-id",
        required=True,
        help="Claude Code session id whose transcript should be resolved",
    )

    args = parser.parse_args()
    if args.command == "current":
        return cmd_current(args)
    if args.command == "transcript-path":
        return cmd_transcript_path(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
