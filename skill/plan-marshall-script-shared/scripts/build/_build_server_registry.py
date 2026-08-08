#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Machine-global marshalld project registry (read/write + audit).

The registry is the operator-interactivity wall for the build server: a project
is served by ``marshalld`` only when it has been REGISTERED, and registration is
the enable signal (there is no config knob and nothing git-tracked). This module
is the single reader/writer of the machine-global ``registry.json`` under
``~/.plan-marshall/marshalld/`` — the daemon's verifier (S1/S2) reads it to
decide whether to accept a submit, and the ``manage-build-server`` control skill
writes it on ``register`` / ``unregister``.

It is a pure deterministic helper that extends the ``script-shared`` build
library exactly as :mod:`_build_result` / :mod:`_build_queue_slot` do. State
lives under the machine-global ``home_root()`` tier (NOT a repo's ``.plan/`` and
NOT the per-repo main-anchored exception set): the directory is created ``0o700``
via :func:`marketplace_paths.ensure_home_root`, and every registration change
appends an audit line to an append-only log so the registration history is
reconstructable.

Registry layout (``registry.json``)::

    {
      "version": 1,
      "projects": {
        "<canonical_root>": {
          "canonical_root": "<canonical_root>",
          "worktree_containers": ["<dir>", ...],
          "notation_allowlist": ["<bundle:skill:script>", ...],
          "registered_at": "<iso>",
          "updated_at": "<iso>"
        }
      }
    }

Projects are keyed by their canonical (symlink-resolved, absolute) root, so the
verifier can look a submit's tree up positionally.

Usage:
    from _build_server_registry import (
        read_registry, write_registry, get_project, find_project_for_root,
        register_project, unregister_project, canonicalize_root,
        registry_path, registry_dir, audit_path, ProjectRecord,
    )
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from file_ops import atomic_write_file, now_utc_iso, read_json
from marketplace_paths import ensure_home_root, home_root

# =============================================================================
# Constants and path resolution
# =============================================================================

REGISTRY_VERSION = 1
"""Schema version stamped into a freshly-written registry."""

_REGISTRY_SUBDIR = 'marshalld'
_REGISTRY_FILENAME = 'registry.json'
_AUDIT_FILENAME = 'registry-audit.log'

_DIR_MODE = 0o700
"""State-directory mode — owner-only (machine-global state is not world-listable)."""

_FILE_MODE = 0o600
"""Registry / audit file mode — owner read/write only."""

ACTION_REGISTER = 'register'
ACTION_UNREGISTER = 'unregister'


def registry_dir() -> Path:
    """Return the marshalld state directory under the machine-global home root."""
    return home_root() / _REGISTRY_SUBDIR


def registry_path() -> Path:
    """Return the path to the machine-global ``registry.json``."""
    return registry_dir() / _REGISTRY_FILENAME


def audit_path() -> Path:
    """Return the path to the append-only registration audit log."""
    return registry_dir() / _AUDIT_FILENAME


def ensure_registry_dir() -> Path:
    """Create the marshalld state directory ``0o700`` and return it.

    Routes the home-root creation through :func:`ensure_home_root` (which
    creates ``~/.plan-marshall`` ``0o700`` and repairs a wider mode), then
    creates the ``marshalld`` subdirectory ``0o700``. Both steps are idempotent
    and repair an existing directory whose mode is wider than ``0o700``.

    Returns:
        The resolved marshalld state directory path.
    """
    ensure_home_root()
    directory = registry_dir()
    directory.mkdir(mode=_DIR_MODE, parents=True, exist_ok=True)
    if (directory.stat().st_mode & 0o777) != _DIR_MODE:
        os.chmod(directory, _DIR_MODE)
    return directory


# =============================================================================
# Project record
# =============================================================================


@dataclass
class ProjectRecord:
    """A single registered project's record.

    Attributes:
        canonical_root: The project's canonical (symlink-resolved, absolute)
            root — the registry key.
        worktree_containers: Directories under which linked worktrees of this
            project may live; a submit from a live worktree whose git-common-dir
            resolves to ``canonical_root`` is accepted when the worktree sits
            under one of these.
        notation_allowlist: The executor notations this project may submit.
        registered_at: ISO-8601 timestamp of first registration.
        updated_at: ISO-8601 timestamp of the last registration change.
    """

    canonical_root: str
    worktree_containers: list[str] = field(default_factory=list)
    notation_allowlist: list[str] = field(default_factory=list)
    registered_at: str = ''
    updated_at: str = ''

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serialisable form of this record."""
        return {
            'canonical_root': self.canonical_root,
            'worktree_containers': list(self.worktree_containers),
            'notation_allowlist': list(self.notation_allowlist),
            'registered_at': self.registered_at,
            'updated_at': self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectRecord:
        """Reconstruct a record from a stored registry entry.

        Args:
            data: A stored project-record dict.

        Returns:
            The reconstructed record. Missing list fields default to empty
            lists; missing timestamps default to empty strings.
        """
        return cls(
            canonical_root=str(data.get('canonical_root', '')),
            worktree_containers=list(data.get('worktree_containers', []) or []),
            notation_allowlist=list(data.get('notation_allowlist', []) or []),
            registered_at=str(data.get('registered_at', '')),
            updated_at=str(data.get('updated_at', '')),
        )


# =============================================================================
# Path canonicalisation
# =============================================================================


def canonicalize_root(root: str | Path) -> str:
    """Canonicalise a project root to an absolute, symlink-resolved string.

    The registry key is always the canonical form so that a submit's tree —
    which the verifier likewise canonicalises — matches regardless of the
    symlink path a caller used.

    Args:
        root: A project root path (relative or absolute, possibly via symlinks).

    Returns:
        The absolute, symlink-resolved path as a string.
    """
    return str(Path(root).resolve())


# =============================================================================
# Registry read / write
# =============================================================================


def _empty_registry() -> dict[str, Any]:
    """Return a fresh, empty registry structure."""
    return {'version': REGISTRY_VERSION, 'projects': {}}


def read_registry() -> dict[str, Any]:
    """Read the machine-global registry, degrading to empty on any failure.

    A missing file, an unreadable file, or an unparseable / wrong-shaped
    payload all degrade deterministically to an empty registry — the verifier
    then treats every submit as unregistered rather than crashing. The returned
    structure is always shape-normalised: ``version`` present and ``projects`` a
    dict.

    Returns:
        The registry dict (``{'version': int, 'projects': {...}}``).
    """
    data = read_json(registry_path(), default=_empty_registry())
    if not isinstance(data, dict):
        return _empty_registry()
    projects = data.get('projects')
    if not isinstance(projects, dict):
        projects = {}
    version = data.get('version')
    if not isinstance(version, int):
        version = REGISTRY_VERSION
    return {'version': version, 'projects': projects}


def write_registry(registry: dict[str, Any]) -> None:
    """Atomically persist the registry ``0o600`` under a ``0o700`` state dir.

    Args:
        registry: The registry structure to write.
    """
    ensure_registry_dir()
    path = registry_path()
    atomic_write_file(path, json.dumps(registry, indent=2))
    if (path.stat().st_mode & 0o777) != _FILE_MODE:
        os.chmod(path, _FILE_MODE)


# =============================================================================
# Project lookup
# =============================================================================


def get_project(registry: dict[str, Any], canonical_root: str) -> dict[str, Any] | None:
    """Return the stored record for ``canonical_root``, or ``None``.

    Args:
        registry: A registry structure from :func:`read_registry`.
        canonical_root: The canonical root key to look up.

    Returns:
        The project-record dict, or ``None`` when the project is not registered.
    """
    record = registry.get('projects', {}).get(canonical_root)
    return record if isinstance(record, dict) else None


def find_project_for_root(
    registry: dict[str, Any], candidate_root: str
) -> dict[str, Any] | None:
    """Find the record whose canonical root or a container covers ``candidate_root``.

    Matches when ``candidate_root`` equals a project's ``canonical_root`` OR
    sits at/under one of its ``worktree_containers``. Both sides are compared as
    resolved absolute paths, so a symlinked or relative candidate still matches.
    This is the coarse registry-level lookup; the verifier layers the S2
    git-common-dir worktree-liveness check on top.

    Args:
        registry: A registry structure from :func:`read_registry`.
        candidate_root: A submit's tree root (canonical or not).

    Returns:
        The matching project-record dict, or ``None`` when no project covers the
        candidate.
    """
    resolved = Path(canonicalize_root(candidate_root))
    for record in registry.get('projects', {}).values():
        if not isinstance(record, dict):
            continue
        canonical = record.get('canonical_root', '')
        if canonical and Path(canonical) == resolved:
            return record
        for container in record.get('worktree_containers', []) or []:
            container_path = Path(canonicalize_root(container))
            if resolved == container_path or container_path in resolved.parents:
                return record
    return None


# =============================================================================
# Registration mutations (each appends an audit line)
# =============================================================================


def register_project(
    root: str | Path,
    worktree_containers: list[str] | None = None,
    notation_allowlist: list[str] | None = None,
) -> dict[str, Any]:
    """Register (or update) a project and append an audit line.

    Upserts the project keyed by its canonical root: a first registration
    stamps ``registered_at``; a re-registration preserves the original
    ``registered_at`` and refreshes ``updated_at`` and the container/allowlist
    fields. The registry is persisted and one audit line is appended.

    Args:
        root: The project root to register (canonicalised internally).
        worktree_containers: Directories linked worktrees may live under.
        notation_allowlist: Executor notations this project may submit.

    Returns:
        The stored project-record dict.
    """
    canonical = canonicalize_root(root)
    now = now_utc_iso()
    registry = read_registry()
    existing = get_project(registry, canonical)
    registered_at = existing.get('registered_at', now) if existing else now

    record = ProjectRecord(
        canonical_root=canonical,
        worktree_containers=list(worktree_containers or []),
        notation_allowlist=list(notation_allowlist or []),
        registered_at=registered_at,
        updated_at=now,
    ).to_dict()

    registry.setdefault('projects', {})[canonical] = record
    write_registry(registry)
    _append_audit(
        ACTION_REGISTER,
        canonical,
        worktree_containers=record['worktree_containers'],
        notation_allowlist=record['notation_allowlist'],
        timestamp=now,
    )
    return record


def unregister_project(root: str | Path) -> bool:
    """Unregister a project and append an audit line when it was present.

    Args:
        root: The project root to unregister (canonicalised internally).

    Returns:
        ``True`` when a record was removed, ``False`` when the project was not
        registered (no audit line is appended in the ``False`` case).
    """
    canonical = canonicalize_root(root)
    registry = read_registry()
    projects = registry.get('projects', {})
    if canonical not in projects:
        return False
    del projects[canonical]
    write_registry(registry)
    _append_audit(ACTION_UNREGISTER, canonical, timestamp=now_utc_iso())
    return True


def _append_audit(action: str, canonical_root: str, **detail: Any) -> None:
    """Append one JSON-lines audit entry to the append-only registration log.

    The audit log is append-only by contract — every registration change adds
    exactly one line and no line is ever rewritten — so the registration history
    stays reconstructable. The line is a compact JSON object carrying the
    action, the affected root, and any extra detail (containers / allowlist /
    timestamp).

    Args:
        action: :data:`ACTION_REGISTER` or :data:`ACTION_UNREGISTER`.
        canonical_root: The affected project's canonical root.
        **detail: Extra fields to record on the audit line.
    """
    ensure_registry_dir()
    entry: dict[str, Any] = {
        'timestamp': detail.pop('timestamp', now_utc_iso()),
        'action': action,
        'canonical_root': canonical_root,
    }
    entry.update(detail)
    path = audit_path()
    created = not path.exists()
    with open(path, 'a', encoding='utf-8') as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + '\n')
    if created and (path.stat().st_mode & 0o777) != _FILE_MODE:
        os.chmod(path, _FILE_MODE)
