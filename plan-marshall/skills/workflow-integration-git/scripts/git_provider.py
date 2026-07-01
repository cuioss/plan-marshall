# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Provider extension and shared low-level helpers for Git integration.

Extension point: plan-marshall:extension-api/standards/ext-point-provider

Declares provider requirements for the workflow-integration-git skill.
Git uses system-level authentication (git CLI configured via global
git config or OS credential helpers), not HTTP headers managed by
plan-marshall.

Discovered by discover-and-persist and persisted to marshal.json.

In addition to the provider declaration, this module exposes the
``run_git`` helper that ``git_workflow`` subcommands share for any
direct ``git`` invocation. Centralizing the helper here avoids
duplicating subprocess wiring across worktree CRUD verbs and the
existing ``analyze-diff`` / artifact-scan paths.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_DEFAULT_TIMEOUT_SECONDS = 60


def run_git(
    args: list[str],
    *,
    cwd: str | Path | None = None,
    timeout: int = _DEFAULT_TIMEOUT_SECONDS,
) -> tuple[int, str, str]:
    """Run ``git <args>`` and return ``(returncode, stdout, stderr)`` (stripped).

    Centralized so ``git_workflow`` subcommands share a single subprocess
    contract: ``check=False`` (callers decide what an error means),
    ``capture_output=True``, ``text=True``, and a default 60s timeout
    that matches the absorbed worktree helper.

    Callers MUST pass a fully-formed argument list (e.g.
    ``['-C', repo, 'worktree', 'add', ...]``) — the helper does not
    second-guess the argv. ``cwd`` is a convenience for callers that
    cannot prepend ``-C``; prefer ``-C`` for repo-rooted commands.
    """
    cwd_str = str(cwd) if cwd is not None else None
    try:
        result = subprocess.run(
            ['git', *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd_str,
        )
    except FileNotFoundError:
        return 127, '', 'git executable not found on PATH'
    except subprocess.TimeoutExpired:
        return 124, '', f'git timed out after {timeout} seconds'
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def get_provider_declarations():
    """Return provider declarations for Git integration."""
    return [
        {
            'skill_name': 'plan-marshall:workflow-integration-git',
            'category': 'version-control',
            'display_name': 'Git CLI',
            'description': 'Git version control via git CLI — commit, push, branch operations',
            'verify_command': 'git config user.name',
        },
    ]
