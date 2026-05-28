#!/usr/bin/env python3
"""
SessionStart hook for Claude Code — captures session_id into CLAUDE_ENV_FILE.

Called by Claude Code as a SessionStart hook. Reads the JSON payload from stdin,
extracts session_id, and writes CLAUDE_CODE_SESSION_ID={session_id} to the
$CLAUDE_ENV_FILE file so subsequent tool invocations in the same session can
read the session id from the environment.

Side-effects:
    1. CLAUDE_ENV_FILE append (CLAUDE_CODE_SESSION_ID={session_id}\\n) — the
       primary contract; failures here surface as exit code 2.
    2. Best-effort active-plan cache write at
       ``~/.cache/plan-marshall/sessions/{session_id}/active-plan`` (or
       ``$XDG_CACHE_HOME/plan-marshall/sessions/{session_id}/active-plan`` when
       ``XDG_CACHE_HOME`` is set). The plan id is resolved via a
       most-recently-modified non-terminal heuristic so that a fresh
       Claude Code session can show the correct terminal title before any
       plan-marshall command runs. Every failure inside this branch is
       swallowed silently — the hook NEVER fails because of the heuristic.

Exit codes:
    0 — success (env var written, or hook explicitly chose not to act)
    1 — malformed stdin (not JSON, or session_id field missing)
    2 — runtime error (CLAUDE_ENV_FILE not set, or write failure)

Usage (invoked by Claude Code hook mechanism, not directly):
    echo '{"session_id": "abc123"}' | python3 claude_hook.py

Emits nothing to stdout on success. Error details go to stderr so Claude Code
can surface them without interfering with the hook's env-var delivery channel.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

_TERMINAL_PHASES = frozenset({"complete", "archived"})


def _find_repo_root(start: Path) -> Path | None:
    """Walk up from ``start`` looking for a ``.plan/local/plans`` directory.

    Returns the directory containing ``.plan/local/plans`` or ``None`` when no
    such ancestor exists. We only inspect the filesystem — no subprocess
    fallback — so the heuristic stays cheap and side-effect-free.
    """
    current = start.resolve()
    while True:
        candidate = current / ".plan" / "local" / "plans"
        if candidate.is_dir():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def _resolve_active_plan() -> str | None:
    """Return the best-guess active plan id, or ``None`` when undecidable.

    Heuristic (priority order):
      1. Locate the repository root by walking up from ``Path.cwd()`` until a
         ``.plan/local/plans/`` directory is found. Return ``None`` when no
         plan directory exists in any ancestor.
      2. Enumerate ``.plan/local/plans/*/status.json``.
      3. For each, parse JSON; skip when ``current_phase ∈ {complete,
         archived}``.
      4. Verify ``<plan_dir>/title-body.txt`` exists and is non-empty; skip
         otherwise.
      5. Among surviving candidates, pick the one with the latest
         ``status.json`` mtime; tie-break on ``status.json``'s ``created``
         timestamp (newest wins).
      6. Return the plan id (the plan directory's basename).

    Any per-plan parsing/IO failure skips that plan rather than aborting the
    resolution; this function never raises.
    """
    repo_root = _find_repo_root(Path.cwd())
    if repo_root is None:
        return None

    plans_dir = repo_root / ".plan" / "local" / "plans"
    try:
        plan_dirs = [p for p in plans_dir.iterdir() if p.is_dir()]
    except OSError:
        return None

    candidates: list[tuple[float, str, str]] = []
    for plan_dir in plan_dirs:
        status_path = plan_dir / "status.json"
        if not status_path.is_file():
            continue

        try:
            with open(status_path, encoding="utf-8") as fh:
                status = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(status, dict):
            continue

        # Phase filter: current_phase may live at the top level or nested
        # under "plan" depending on plan vintage. Accept either.
        current_phase = status.get("current_phase")
        if current_phase is None:
            plan_block = status.get("plan")
            if isinstance(plan_block, dict):
                current_phase = plan_block.get("current_phase")
        if isinstance(current_phase, str) and current_phase in _TERMINAL_PHASES:
            continue

        title_body = plan_dir / "title-body.txt"
        try:
            if not title_body.is_file():
                continue
            if title_body.stat().st_size == 0:
                continue
        except OSError:
            continue

        try:
            mtime = status_path.stat().st_mtime
        except OSError:
            continue

        created = ""
        raw_created = status.get("created")
        if isinstance(raw_created, str):
            created = raw_created
        else:
            plan_block = status.get("plan")
            if isinstance(plan_block, dict):
                pc = plan_block.get("created")
                if isinstance(pc, str):
                    created = pc

        candidates.append((mtime, created, plan_dir.name))

    if not candidates:
        return None

    # Stable sort (three passes, reverse priority order):
    # 1. Sort by plan name ascending (final deterministic fallback)
    candidates.sort(key=lambda t: t[2])
    # 2. Sort by created timestamp descending (newer wins, empty values rank last)
    candidates.sort(key=lambda t: t[1], reverse=True)
    # 3. Sort by mtime descending (newest wins)
    candidates.sort(key=lambda t: t[0], reverse=True)
    return candidates[0][2]


def _resolve_cache_dir() -> Path:
    """Resolve the plan-marshall sessions cache directory.

    Honors ``$XDG_CACHE_HOME``; falls back to ``$HOME/.cache``.
    """
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        base = Path(xdg)
    else:
        home = os.environ.get("HOME") or os.path.expanduser("~")
        base = Path(home) / ".cache"
    return base / "plan-marshall" / "sessions"


def _write_active_plan_mapping(session_id: str) -> None:
    """Best-effort write of the resolved active plan id to the session cache.

    Side-effect summary: creates
    ``{cache_dir}/plan-marshall/sessions/{session_id}/active-plan`` containing
    a single line with the plan id. If anything goes wrong (no candidate
    plans, permission errors, malformed status files, etc.) this function
    returns silently. The hook MUST NOT fail because of this side-effect.
    """
    try:
        plan_id = _resolve_active_plan()
        if not plan_id:
            return

        session_dir = _resolve_cache_dir() / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        target = session_dir / "active-plan"

        # Atomic write: temp file in the same dir + os.replace.
        fd, tmp_name = tempfile.mkstemp(prefix=".active-plan-", dir=str(session_dir))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(plan_id)
            os.replace(tmp_name, target)
        finally:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
    except Exception:  # noqa: BLE001 — best-effort by contract.
        return


def main() -> int:
    """Read stdin JSON, extract session_id, write to CLAUDE_ENV_FILE."""
    # Read and parse stdin
    raw = sys.stdin.read()
    if not raw.strip():
        print("claude_hook: stdin is empty — no session payload received", file=sys.stderr)
        return 1

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"claude_hook: malformed JSON on stdin: {exc}", file=sys.stderr)
        return 1

    if not isinstance(payload, dict):
        print(
            f"claude_hook: expected JSON object, got {type(payload).__name__}",
            file=sys.stderr,
        )
        return 1

    session_id = payload.get("session_id")
    if not session_id:
        print(
            "claude_hook: 'session_id' field missing or empty in hook payload",
            file=sys.stderr,
        )
        return 1

    if not isinstance(session_id, str):
        print(
            f"claude_hook: 'session_id' must be a string, got {type(session_id).__name__}",
            file=sys.stderr,
        )
        return 1

    # Write to CLAUDE_ENV_FILE so the session id propagates into the environment
    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if not env_file:
        print(
            "claude_hook: CLAUDE_ENV_FILE is not set — cannot write session id",
            file=sys.stderr,
        )
        return 2

    try:
        with open(env_file, "a", encoding="utf-8") as fh:
            fh.write(f"CLAUDE_CODE_SESSION_ID={session_id}\n")
    except OSError as exc:
        print(f"claude_hook: failed to write to CLAUDE_ENV_FILE ({env_file}): {exc}", file=sys.stderr)
        return 2

    # Best-effort: resolve and write the active-plan cache mapping so a fresh
    # session shows the correct terminal title before any plan-marshall
    # command runs. Failures here are swallowed by contract.
    _write_active_plan_mapping(session_id)

    return 0


if __name__ == "__main__":
    sys.exit(main())
