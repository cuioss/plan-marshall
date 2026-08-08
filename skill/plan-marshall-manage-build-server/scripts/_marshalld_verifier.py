#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Submit verifier for the marshalld build server (S1 verify-not-resolve, S2 tree).

The verifier is the daemon's trust boundary: it VERIFIES every submit
positionally against the submitting project's REGISTRATION, and never resolves
anything on the client's behalf. A submit is accepted only when ALL of the
following hold; any single deviation returns ``refused(reason=...)`` and the
daemon logs it.

**S1 — positional argv-template check**

1. The command is non-empty.
2. ``command[0]`` (the interpreter) matches the daemon's registered baseline
   interpreter (by basename — ``python3`` / ``python`` / the exact baseline
   path), never an arbitrary client-supplied binary.
3. ``command[1]`` is exactly ``{exec_path}/.plan/execute-script.py`` — the
   executor inside the submitted tree, not an arbitrary script.
4. ``command[2]`` (the executor notation) is in the project's
   ``notation_allowlist``.
5. The remaining args are schema-valid (plain strings, no embedded NULs).

**S2 — exec-path canonicalisation to a live tree**

6. ``exec_path`` canonicalises (symlinks resolved) to the project's registered
   ``canonical_root`` OR to a live linked worktree whose ``git-common-dir``
   resolves to ``canonical_root`` AND which sits under one of the project's
   registered ``worktree_containers``. Anything that escapes the registered tree
   (``..`` traversal, a symlink out, an unregistered worktree) is refused.
7. ``project_path`` — the build child's ``cwd`` (:func:`_marshalld_supervisor.run_job`
   runs the verified command with ``cwd=project_path``) — is independently
   verified against the SAME registration, using the identical containment
   check as ``exec_path`` above. ``exec_path`` and ``project_path`` are two
   separately client-settable job-spec fields (``build_server.py``'s ``submit``
   verb exposes ``--exec-path`` and ``--project-path`` independently); checking
   only ``exec_path`` would let a submitter point the build child's working
   directory at any tree the daemon-owning user can read/write while still
   satisfying the ``exec_path`` check with a legitimately-registered tree — a
   genuine cwd-redirection escape, not mere defense-in-depth, since ``cwd`` is a
   real execution parameter (relative-path resolution, VCS discovery, artifact
   writes) for the build tools the daemon invokes.

The git-common-dir probe is injected via ``common_dir_resolver`` so the verifier
stays a pure function in tests — the daemon passes a git-backed resolver in
production. This module is stdlib-only and has no LLM in the loop.

Usage:
    from _marshalld_verifier import verify_submit, REFUSE_NOT_REGISTERED

    outcome = verify_submit(job_spec, registry, baseline_interpreter='python3')
    if not outcome.accepted:
        respond_refused(outcome.reason)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _build_server_registry import canonicalize_root, find_project_for_root

# Refusal reason codes (stable strings surfaced to the client and the log).
REFUSE_NOT_REGISTERED = 'not_registered'
REFUSE_EMPTY_COMMAND = 'empty_command'
REFUSE_WRONG_INTERPRETER = 'wrong_interpreter'
REFUSE_EXECUTOR_MISMATCH = 'executor_mismatch'
REFUSE_NOTATION_NOT_ALLOWLISTED = 'notation_not_allowlisted'
REFUSE_INVALID_ARGS = 'invalid_args'
REFUSE_EXEC_PATH_ESCAPE = 'exec_path_escape'
REFUSE_WORKTREE_NOT_LIVE = 'worktree_not_live'
REFUSE_PROJECT_PATH_ESCAPE = 'project_path_escape'
REFUSE_PROJECT_PATH_NOT_LIVE = 'project_path_not_live'

_EXECUTOR_SUBPATH = ('.plan', 'execute-script.py')
_DEFAULT_INTERPRETER_NAMES = frozenset({'python3', 'python'})

# A resolver returning the canonical git-common-dir main-checkout root for a
# worktree path, or ``None`` when the path is not inside a git worktree.
CommonDirResolver = Callable[[str], 'str | None']


@dataclass
class VerifyOutcome:
    """Result of verifying one submit.

    Attributes:
        accepted: ``True`` when the submit passed every S1/S2 check.
        reason: The refusal reason code (one of the ``REFUSE_*`` constants);
            empty when accepted.
        record: The matched project record on acceptance; ``None`` otherwise.
    """

    accepted: bool
    reason: str = ''
    record: dict[str, Any] | None = None

    @classmethod
    def accept(cls, record: dict[str, Any]) -> VerifyOutcome:
        """Return an accepting outcome carrying the matched project record."""
        return cls(accepted=True, reason='', record=record)

    @classmethod
    def refuse(cls, reason: str) -> VerifyOutcome:
        """Return a refusing outcome carrying the reason code."""
        return cls(accepted=False, reason=reason, record=None)


def _interpreter_ok(interpreter: str, baseline_interpreter: str | None) -> bool:
    """Return whether ``interpreter`` matches the registered baseline."""
    name = Path(interpreter).name
    if baseline_interpreter:
        return interpreter == baseline_interpreter or name == Path(baseline_interpreter).name
    return name in _DEFAULT_INTERPRETER_NAMES


def _args_schema_valid(args: list[str]) -> bool:
    """Return whether every remaining arg is a plain, NUL-free string."""
    return all(isinstance(arg, str) and '\x00' not in arg for arg in args)


def _path_within_registration(
    path: str,
    record: dict[str, Any],
    common_dir_resolver: CommonDirResolver | None,
    *,
    escape_reason: str,
    not_live_reason: str,
) -> str:
    """Classify a path against a project's registration (S2, generic).

    Shared containment check used for BOTH ``exec_path`` (where the executor
    script lives) and ``project_path`` (the build child's ``cwd``) — each field
    is checked against the SAME registered tree, with a distinct pair of
    ``REFUSE_*`` reasons so a refusal names which field escaped.

    Returns an empty string when the path is accepted, or the caller-supplied
    ``escape_reason`` / ``not_live_reason`` when it escapes the registered tree.
    """
    canonical = Path(canonicalize_root(path))
    registered_root = record.get('canonical_root', '')
    if registered_root and canonical == Path(registered_root):
        return ''

    # Not the registered root itself — allow only a live linked worktree whose
    # git-common-dir resolves to the registered root AND which sits under a
    # registered container.
    containers = [Path(canonicalize_root(c)) for c in record.get('worktree_containers', []) or []]
    under_container = any(
        canonical == container or container in canonical.parents
        for container in containers
    )
    if not under_container:
        return escape_reason

    if common_dir_resolver is None:
        # No liveness probe available — a worktree cannot be proven live.
        return not_live_reason
    resolved_root = common_dir_resolver(str(canonical))
    if not resolved_root:
        return not_live_reason
    if Path(canonicalize_root(resolved_root)) != Path(registered_root):
        return not_live_reason
    return ''


def _exec_path_within_registration(
    exec_path: str,
    record: dict[str, Any],
    common_dir_resolver: CommonDirResolver | None,
) -> str:
    """Classify an exec-path against a project's registration (S2)."""
    return _path_within_registration(
        exec_path,
        record,
        common_dir_resolver,
        escape_reason=REFUSE_EXEC_PATH_ESCAPE,
        not_live_reason=REFUSE_WORKTREE_NOT_LIVE,
    )


def _project_path_within_registration(
    project_path: str,
    record: dict[str, Any],
    common_dir_resolver: CommonDirResolver | None,
) -> str:
    """Classify the build child's cwd against a project's registration (S2).

    Applies the IDENTICAL containment check as :func:`_exec_path_within_registration`
    to ``project_path`` — the field :func:`_marshalld_supervisor.run_job` uses
    verbatim as the subprocess ``cwd``. Without this check ``project_path`` is a
    client-settable field that never touches the verifier, letting a submitter
    redirect the build child's working directory to any tree the daemon-owning
    user can access while ``exec_path`` alone still satisfies S1/S2.
    """
    return _path_within_registration(
        project_path,
        record,
        common_dir_resolver,
        escape_reason=REFUSE_PROJECT_PATH_ESCAPE,
        not_live_reason=REFUSE_PROJECT_PATH_NOT_LIVE,
    )


def verify_submit(
    job_spec: Any,
    registry: dict[str, Any],
    *,
    baseline_interpreter: str | None = None,
    common_dir_resolver: CommonDirResolver | None = None,
) -> VerifyOutcome:
    """Verify one submit positionally against the registry (S1/S2).

    Args:
        job_spec: A :class:`_build_server_protocol.JobSpec` (or any object with
            ``command`` / ``exec_path`` / ``project_path`` attributes).
        registry: The registry structure from
            :func:`_build_server_registry.read_registry`.
        baseline_interpreter: The daemon's registered baseline interpreter; when
            ``None`` the default ``python3`` / ``python`` basenames are accepted.
        common_dir_resolver: Callable resolving a worktree path to its
            git-common-dir main-checkout root (or ``None``); required to accept a
            submit from a linked worktree.

    Returns:
        A :class:`VerifyOutcome` — accepting with the matched record, or refusing
        with a ``REFUSE_*`` reason.
    """
    command: list[str] = list(getattr(job_spec, 'command', []) or [])
    exec_path: str = getattr(job_spec, 'exec_path', '') or ''
    project_path: str = getattr(job_spec, 'project_path', '') or ''

    # S2 registry lookup first — an unregistered tree is refused outright.
    record = find_project_for_root(registry, exec_path)
    if record is None:
        return VerifyOutcome.refuse(REFUSE_NOT_REGISTERED)

    # S1.1 — non-empty command.
    if len(command) < 3:
        return VerifyOutcome.refuse(REFUSE_EMPTY_COMMAND)

    # S1.2 — interpreter matches the registered baseline.
    if not _interpreter_ok(command[0], baseline_interpreter):
        return VerifyOutcome.refuse(REFUSE_WRONG_INTERPRETER)

    # S1.3 — argv[1] is exactly {exec_path}/.plan/execute-script.py.
    expected_executor = Path(exec_path).joinpath(*_EXECUTOR_SUBPATH)
    if Path(command[1]) != expected_executor:
        return VerifyOutcome.refuse(REFUSE_EXECUTOR_MISMATCH)

    # S1.4 — notation is allowlisted.
    if command[2] not in (record.get('notation_allowlist', []) or []):
        return VerifyOutcome.refuse(REFUSE_NOTATION_NOT_ALLOWLISTED)

    # S1.5 — remaining args schema-valid.
    if not _args_schema_valid(command[3:]):
        return VerifyOutcome.refuse(REFUSE_INVALID_ARGS)

    # S2 — exec-path canonicalises into the registered tree (or a live worktree).
    escape_reason = _exec_path_within_registration(exec_path, record, common_dir_resolver)
    if escape_reason:
        return VerifyOutcome.refuse(escape_reason)

    # S2 — project_path (the build child's cwd) is independently verified: an
    # empty value is refused outright (never let an empty string canonicalise to
    # the daemon process's own unrelated cwd); otherwise it must canonicalise
    # into the SAME registered tree as exec_path, using the identical
    # containment check — never an unrelated/arbitrary directory the client
    # happened to name.
    if not project_path:
        return VerifyOutcome.refuse(REFUSE_PROJECT_PATH_ESCAPE)
    project_escape_reason = _project_path_within_registration(project_path, record, common_dir_resolver)
    if project_escape_reason:
        return VerifyOutcome.refuse(project_escape_reason)

    return VerifyOutcome.accept(record)


def git_common_dir_resolver(worktree_path: str) -> str | None:
    """Production ``common_dir_resolver``: resolve a worktree's main-checkout root.

    Runs ``git -C {worktree_path} rev-parse --git-common-dir`` and returns the
    parent of the resolved common dir (the main checkout root), or ``None`` when
    the path is not inside a git worktree.

    Args:
        worktree_path: A candidate worktree path.

    Returns:
        The main-checkout root path, or ``None`` when unresolvable.
    """
    import subprocess

    try:
        result = subprocess.run(
            ['git', '-C', worktree_path, 'rev-parse', '--git-common-dir'],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None
    common_dir = result.stdout.strip()
    if not common_dir:
        return None
    common_path = Path(common_dir)
    if not common_path.is_absolute():
        common_path = (Path(worktree_path) / common_path).resolve()
    return str(common_path.parent)
