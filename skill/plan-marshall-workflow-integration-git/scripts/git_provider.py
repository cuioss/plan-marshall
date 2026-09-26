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

#: Budget applied to a git call whose caller names none. See :func:`run_git` for
#: what it is and is not: a floor for calls whose cost does not scale with a
#: tree, never a fitted budget for one that walks a worktree. It is also read by
#: ``git-workflow.py::_derive_removal_timeout`` as the LOWER bound of the derived
#: worktree-removal budget, so a small tree keeps exactly this budget and the
#: derivation can only ever lengthen it.
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
    ``capture_output=True``, ``text=True``, and
    :data:`_DEFAULT_TIMEOUT_SECONDS` when the caller names no budget of its own.

    **That default is a FLOOR for SHORT-RUNNING git calls, not a budget that
    fits every invocation.** It suits the calls whose cost does not scale with
    the size of any tree — ``rev-parse``, ``merge-base``, ``branch -D``,
    ``ls-remote``, a ref lookup — for which 60 seconds is already far more than
    the call can legitimately need, so the timeout only ever fires on something
    genuinely wedged. It is NOT a defensible budget for a call whose cost scales
    with the tree it walks: ``git worktree remove`` unlinks every entry under
    the worktree, so on a GB-scale tree the default expires on a perfectly
    healthy removal. A caller in that position derives its own budget from the
    tree it observes and passes it as ``timeout`` — see
    ``git-workflow.py::_derive_removal_timeout``. Raising the default instead
    would not fix that class of caller; it would only move the size at which the
    constant is wrong again.

    On expiry the helper returns ``124`` with the timeout described in
    ``stderr``, and ``127`` when ``git`` is not on ``PATH``. Both are sentinels
    the helper synthesizes, not exit codes git produced — a caller that must
    distinguish "the budget expired, so git rendered no verdict" from "git ran
    and reported a failure" branches on ``124`` before its generic non-zero
    branch.

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
