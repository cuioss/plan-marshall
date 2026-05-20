#!/usr/bin/env python3
"""Emit a terminal title and/or statusline string that reflects the active
plan-marshall plan and phase, the active slash command (if any), plus a live
status icon.

Hook subprocesses emit ``{"terminalSequence": "<OSC>"}`` JSON on stdout per
the Claude Code 2.1.141+ hook-output contract; Claude Code forwards the
sequence to the controlling terminal. The ``--statusline`` mode writes the
plain title to stdout for Claude Code's statusLine command.

Invoked from Claude Code hooks (SessionStart / UserPromptSubmit / Notification /
PostToolUse(AskUserQuestion) / Stop) and from the Claude Code statusline
command. Never raises to the caller: any failure falls back to `<icon> claude`
and exit 0 so the user's session is never disrupted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

_STATUS_ICONS = {
    'running': '▶',  # ▶
    'waiting': '?',
    'idle': '◯',  # ◯
    'done': '✓',  # ✓
}

_FALLBACK_ICON = _STATUS_ICONS['idle']

_WORKTREE_RE = re.compile(r'.*/\.plan/local/worktrees/(?P<id>[^/]+)(?:/.*)?$')

_COMMAND_TOKEN_RE = re.compile(r'^/([A-Za-z0-9][A-Za-z0-9:_-]*)')
_COMMAND_MAX_LEN = 40

# Upper bound for the explicit --plan-label value used by the finalize-phase
# done emission. Generous headroom above the ~36-char short_description cap so
# legitimate labels always pass while still rejecting pathological input.
_PLAN_LABEL_MAX_LEN = 60

# Upper bound for the plan_id read from the session active-plan cache. Plan
# ids are kebab-case slugs derived from the request title; this cap keeps the
# session-cache fallback from passing pathological values into status-file
# resolution while staying comfortably above any realistic plan-id length.
_ACTIVE_PLAN_ID_MAX_LEN = 120

# Slash-command alias map: verbose tokens collapse to short display labels.
# Applied at read time, so captured state is verbatim but rendering is aliased.
_COMMAND_ALIASES: dict[str, str] = {
    'plan-marshall:plan-marshall': 'pm',
}


# Phase values that signal the plan is no longer active. When
# `_read_plan_meta` returns a phase in this set, `build_title` treats it
# identically to "no phase resolved" and falls through to the
# active-command / `claude` fallback chain.
_TERMINAL_PHASE_VALUES = {'complete', 'archived'}


def _resolve_plan_id(cwd: str) -> str | None:
    # Normalize separators so the forward-slash regex matches both POSIX
    # paths and Windows-style backslash paths surfaced by Claude Code hooks
    # running on Windows. PurePath/Path only treat backslashes as separators
    # when running on Windows itself, so a direct replace is the portable
    # form that works regardless of host OS.
    normalized = cwd.replace('\\', '/')
    match = _WORKTREE_RE.match(normalized)
    if not match or not os.path.isdir(cwd):
        return None
    plan_id = match.group('id')
    # Path-traversal guard: the regex's [^/]+ class accepts '..' and '.',
    # which would let a hostile cwd escape the .plan/local/plans/ tree once
    # joined into a status-file path. Reject explicitly.
    if plan_id in ('..', '.'):
        return None
    return plan_id


def _git_common_dir(cwd: str) -> Path | None:
    try:
        result = subprocess.run(
            ['git', '-C', cwd, 'rev-parse', '--path-format=absolute', '--git-common-dir'],
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
        if (candidate / '.plan').is_dir():
            return candidate
    return None


def _resolve_status_file(cwd: str, plan_id: str) -> Path | None:
    common_dir = _git_common_dir(cwd)
    if common_dir is not None:
        candidate = common_dir.parent / '.plan' / 'local' / 'plans' / plan_id / 'status.json'
        if candidate.is_file():
            return candidate
    walk_root = _walk_up_for_plan(Path(cwd))
    if walk_root is None:
        return None
    candidate = walk_root / '.plan' / 'local' / 'plans' / plan_id / 'status.json'
    if not candidate.is_file():
        return None
    return candidate


def _read_plan_meta(status_file: Path) -> tuple[str | None, str | None]:
    """Return ``(current_phase, short_description)`` from status.json.

    Both fields are optional; a missing, empty, or non-string value yields
    ``None`` for that slot. Any parse/read failure yields ``(None, None)`` —
    the title builder treats this identically to "no active plan".
    """
    try:
        data = json.loads(status_file.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None, None
    if not isinstance(data, dict):
        return None, None
    phase = data.get('current_phase')
    short_description = data.get('short_description')
    phase_value = phase if isinstance(phase, str) and phase else None
    short_value = short_description if isinstance(short_description, str) and short_description else None
    return phase_value, short_value


def _active_plan_path(session_id: str) -> Path | None:
    """Return the per-session active-plan cache path.

    Mirrors ``_command_state_path`` shape. Returns ``None`` for empty
    session ids or values containing path separators, ``..`` or ``.`` — the
    cache layout assumes ``session_id`` is a single safe directory segment.
    """
    if not session_id or '/' in session_id or '\\' in session_id or session_id in ('..', '.'):
        return None
    try:
        home = Path.home()
    except (OSError, RuntimeError):
        return None
    return home / '.cache' / 'plan-marshall' / 'sessions' / session_id / 'active-plan'


def _read_active_plan(session_id: str | None) -> str | None:
    """Read the cached active plan_id for ``session_id``.

    Returns ``None`` on missing session id, missing file, I/O error, empty
    content, or when the cached value fails shape validation (oversize,
    contains path separators, or matches the path-traversal sentinels).
    """
    if not session_id:
        return None
    path = _active_plan_path(session_id)
    if path is None or not path.is_file():
        return None
    try:
        raw = path.read_text(encoding='utf-8').strip()
    except (OSError, ValueError):
        return None
    if not raw or len(raw) > _ACTIVE_PLAN_ID_MAX_LEN:
        return None
    if '/' in raw or '\\' in raw or raw in ('..', '.'):
        return None
    return raw


def _command_state_path(session_id: str) -> Path | None:
    if not session_id or '/' in session_id or '\\' in session_id or session_id in ('..', '.'):
        return None
    try:
        home = Path.home()
    except (OSError, RuntimeError):
        return None
    return home / '.cache' / 'plan-marshall' / 'sessions' / session_id / 'active-command'


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
        path.write_text(command, encoding='utf-8')
    except OSError:
        return


def _read_active_command(session_id: str | None) -> str | None:
    if not session_id:
        return None
    path = _command_state_path(session_id)
    if path is None or not path.is_file():
        return None
    try:
        raw = path.read_text(encoding='utf-8').strip()
    except (OSError, ValueError):
        return None
    if not raw or len(raw) > _COMMAND_MAX_LEN:
        return None
    # Collapse known verbose slash-command tokens to their short display aliases.
    # The on-disk state stays verbatim; only the rendered label is aliased.
    return _COMMAND_ALIASES.get(raw, raw)


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
    if 'sessions' in path.parts:
        try:
            path.parent.rmdir()
        except OSError:
            pass


def _sanitize_plan_label(raw: str | None) -> str | None:
    """Validate a caller-supplied ``--plan-label`` value.

    Returns the stripped label when it is non-empty, within
    ``_PLAN_LABEL_MAX_LEN``, and free of control characters. Any failure
    yields ``None`` so the done emission falls back to the ordinary render
    chain rather than producing a malformed title.
    """
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped or len(stripped) > _PLAN_LABEL_MAX_LEN:
        return None
    if any(ord(c) < 32 or ord(c) == 127 for c in stripped):
        return None
    return stripped


def _session_cache_paths(cwd: str) -> tuple[Path, Path] | None:
    try:
        home = Path.home()
    except (OSError, RuntimeError):
        return None
    base = home / '.cache' / 'plan-marshall' / 'sessions'
    cwd_hash = hashlib.sha256(cwd.encode('utf-8')).hexdigest()
    return base / 'by-cwd' / cwd_hash, base / 'current'


def _write_session_cache(session_id: str | None, cwd: str) -> None:
    if not session_id or not cwd:
        return
    paths = _session_cache_paths(cwd)
    if paths is None:
        return
    by_cwd, current = paths
    try:
        by_cwd.parent.mkdir(parents=True, exist_ok=True)
        by_cwd.write_text(session_id, encoding='utf-8')
    except OSError:
        pass
    try:
        current.parent.mkdir(parents=True, exist_ok=True)
        current.write_text(session_id, encoding='utf-8')
    except OSError:
        pass


def _build_title(
    status: str,
    plan_id: str | None,
    phase: str | None,
    active_command: str | None = None,
    short_description: str | None = None,
    plan_label: str | None = None,
) -> str:
    icon = _STATUS_ICONS.get(status, _FALLBACK_ICON)
    # Terminal 'done' emission from phase-6-finalize: the caller supplies the
    # label directly so we can render without any cwd/status.json resolution.
    # By the time this path fires the plan has been archived and the worktree
    # removed, so the normal resolution chain would return the fallback.
    if status == 'done' and plan_label:
        return f'{icon} pm:done:{plan_label}'
    if plan_id and phase:
        # Plan-active: collapse the plan_id prefix to the constant `pm` alias
        # and append the auto-derived short description when available.
        if short_description:
            return f'{icon} pm:{phase}:{short_description}'
        return f'{icon} pm:{phase}'
    if active_command:
        return f'{icon} {active_command}'
    return f'{icon} claude'


def _read_hook_payload() -> dict[str, str | None]:
    empty: dict[str, str | None] = {'cwd': None, 'prompt': None, 'session_id': None}
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
    cwd = payload.get('cwd')
    prompt = payload.get('prompt')
    session_id = payload.get('session_id')
    return {
        'cwd': cwd if isinstance(cwd, str) and cwd else None,
        'prompt': prompt if isinstance(prompt, str) else None,
        'session_id': session_id if isinstance(session_id, str) and session_id else None,
    }


def _emit_terminal_sequence(title: str) -> None:
    """Emit the terminal-title escape sequence via the Claude Code 2.1.141+
    hook output contract.

    Writes a JSON object ``{"terminalSequence": "<seq>"}`` to stdout. Claude
    Code reads the hook subprocess's stdout, parses the JSON, and forwards the
    ``terminalSequence`` value to the controlling terminal. This replaces the
    pre-2.1.139 path that opened ``/dev/tty`` directly (no longer available to
    hook subprocesses).
    """
    payload = {'terminalSequence': f'\033]0;{title}\007'}
    try:
        json.dump(payload, sys.stdout)
        sys.stdout.flush()
    except OSError:
        return


def build_title(
    status: str,
    cwd: str,
    session_id: str | None = None,
    plan_label: str | None = None,
) -> str:
    # Terminal 'done' emission short-circuits resolution when an explicit
    # plan label is supplied — by this point the live plan directory is
    # already archived and the worktree removed.
    if status == 'done' and plan_label:
        return _build_title(status, None, None, None, None, plan_label=plan_label)
    plan_id = _resolve_plan_id(cwd)
    phase: str | None = None
    short_description: str | None = None
    if plan_id:
        status_file = _resolve_status_file(cwd, plan_id)
        if status_file is not None:
            phase, short_description = _read_plan_meta(status_file)
    if plan_id and (not phase or phase in _TERMINAL_PHASE_VALUES):
        plan_id = None
        phase = None
        short_description = None
    # Tier 2: session active-plan cache. Consulted only when the worktree-cwd
    # resolution above failed to yield a (plan_id, phase) pair — e.g., the
    # main orchestration session runs from the repo root whose cwd never
    # matches the worktree regex. The cache is keyed by session_id so
    # concurrent tabs render independent titles. Terminal phases fall
    # through identically to the worktree-cwd path above.
    if not (plan_id and phase) and session_id:
        candidate = _read_active_plan(session_id)
        if candidate:
            status_file = _resolve_status_file(cwd, candidate)
            if status_file and status_file.is_file():
                cand_phase, cand_short = _read_plan_meta(status_file)
                if cand_phase and cand_phase not in _TERMINAL_PHASE_VALUES:
                    plan_id = candidate
                    phase = cand_phase
                    short_description = cand_short
    active_command: str | None = None
    if not (plan_id and phase):
        active_command = _read_active_command(session_id)
    return _build_title(status, plan_id, phase, active_command, short_description)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='Emit plan-marshall terminal title / statusline',
        allow_abbrev=False,
    )
    parser.add_argument('status', choices=sorted(_STATUS_ICONS), help='Live status for the icon')
    parser.add_argument(
        '--statusline',
        action='store_true',
        help=(
            'Print the title to stdout for Claude Code statusline (instead '
            'of the hook-output JSON terminalSequence emission)'
        ),
    )
    parser.add_argument(
        '--plan-label',
        dest='plan_label',
        type=str,
        default=None,
        help=(
            "Explicit plan label for the 'done' status. When provided with "
            "--status done, the title renders as '{icon} pm:done:{label}' "
            'and bypasses cwd/status.json resolution — used by the '
            'phase-6-finalize terminal emission after the plan is archived.'
        ),
    )
    args = parser.parse_args(argv)

    payload = _read_hook_payload()
    cwd = payload['cwd'] or os.getcwd()
    session_id = payload['session_id']

    # Only hook invocations (no --statusline) mutate session state.
    # The statusLine command fires continuously and must be a pure read.
    if not args.statusline and session_id:
        _write_session_cache(session_id, cwd)
        if args.status == 'running' and payload['prompt']:
            token = _extract_command_token(payload['prompt'])
            if token:
                _write_active_command(session_id, token)
        elif args.status == 'idle':
            _clear_active_command(session_id)

    plan_label = _sanitize_plan_label(args.plan_label)
    title = build_title(args.status, cwd, session_id, plan_label=plan_label)

    if args.statusline:
        sys.stdout.write(title)
        sys.stdout.flush()
    else:
        _emit_terminal_sequence(title)
    return 0


if __name__ == '__main__':
    sys.exit(main())
