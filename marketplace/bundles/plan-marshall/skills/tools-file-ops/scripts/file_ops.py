#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Base file operations module for workflow scripts.

Provides atomic file operations, metadata parsing, TOON output helpers,
and base directory configuration for workflow files.

Usage:
    from file_ops import (
        atomic_write_file,
        ensure_directory,
        output_toon,
        output_success,
        output_error,
        parse_markdown_metadata,
        generate_markdown_metadata,
        get_base_dir,
        set_base_dir,
        base_path,
        get_store_dir,
        get_temp_dir,
        get_executor_path,
        guard_worktree_cwd
    )
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from marketplace_paths import (
    PLAN_DIR_NAME,
    _find_plan_root_from_cwd,
    resolve_main_anchored_path,
)
from toon_parser import serialize_toon

# Plan-marshall runtime state (plans, archived-plans, run-configuration.json,
# lessons-learned, logs) is resolved by the SINGLE uniform cwd-relative rule
# (ADR-002): set_base_dir() override → PLAN_BASE_DIR → walk up from the current
# working directory to the nearest ``.plan/local`` ancestor. Phases 1-4 resolve
# to the main checkout (cwd is main); phase-5+ resolve to the pinned worktree
# (cwd is pinned there). The SOLE execution-time invariant is that the working
# directory is never changed away from the worktree during phase-5+. The plan
# directory and the executor MOVE into the worktree at phase-5 start and move
# back at finalize; the shared corpora (lessons-learned/, archived-plans/) and
# the merge.lock stay main-anchored by design.
#
# The SINGLE cwd-unchanged invariant — "during phase-5+ the cwd never leaves
# the worktree" — is realized as a caller-side GUARD, not a script side effect.
# A subprocess cannot mutate its parent's cwd, so pinning cwd is the caller's
# (orchestrator's) responsibility; the lifecycle scripts (prepare_execute.py
# D4, integrate_into_main.py D5) and phase-5+ manage-* callers ASSERT the
# invariant by calling guard_worktree_cwd(plan_id) (below). The guard verifies
# the current cwd is the expected worktree path and returns an error envelope
# when cwd has left the worktree — it never SETS the cwd.

# Runtime-overridable base directory (set by set_base_dir for tests).
# None means "resolve from environment / git on each call".
_BASE_DIR_OVERRIDE: Path | None = None


def now_utc_iso() -> str:
    """Get current UTC time as ISO 8601 string with Z suffix.

    Returns:
        ISO 8601 formatted timestamp, e.g., '2025-12-02T10:30:00Z'
    """
    return datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def parse_duration(duration_str: str) -> 'timedelta':
    """Parse a duration string like '7d', '24h', '30m' into a timedelta.

    Args:
        duration_str: Duration string with suffix d (days), h (hours), or m (minutes)

    Returns:
        timedelta object

    Raises:
        ValueError: If format is invalid
    """
    import re
    from datetime import timedelta

    match = re.match(r'^(\d+)([dhm])$', duration_str.strip())
    if not match:
        raise ValueError(f"Invalid duration format: '{duration_str}'. Use Nd, Nh, or Nm.")
    value = int(match.group(1))
    unit = match.group(2)
    if unit == 'd':
        return timedelta(days=value)
    if unit == 'h':
        return timedelta(hours=value)
    return timedelta(minutes=value)


def format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like '5.2s', '3m12s', '1h5m'
    """
    if seconds < 60:
        return f'{seconds:.1f}s'
    if seconds < 3600:
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f'{m}m{s}s'
    h = int(seconds // 3600)
    m = int(seconds % 3600 // 60)
    return f'{h}h{m}m'


def format_tokens_short(n: int) -> str:
    """Format an integer token count as an abbreviated decimal-suffix string.

    Used by the finalize-summary [OK] rows where horizontal space is tight; the
    Phase Breakdown table in metrics.md continues to use comma-grouped values.
    Negative input is clamped to zero.

    Args:
        n: Token count.

    Returns:
        Plain integer string for ``n < 1_000`` (``"599"``), K-suffix for
        ``1_000 <= n < 1_000_000`` (``"12K"``, ``"12.5K"``, ``"599K"``), and
        M-suffix for ``n >= 1_000_000`` (``"1.2M"``, ``"12M"``). Trailing
        ``.0`` is trimmed in both suffix branches.
    """
    if n < 0:
        n = 0
    if n < 1_000:
        return str(n)
    if n < 1_000_000:
        scaled = n / 1_000
        rendered = f'{scaled:.1f}'
        if rendered.endswith('.0'):
            rendered = rendered[:-2]
        return f'{rendered}K'
    scaled = n / 1_000_000
    rendered = f'{scaled:.1f}'
    if rendered.endswith('.0'):
        rendered = rendered[:-2]
    return f'{rendered}M'


def get_worktree_root() -> Path:
    """Return the project-local worktree root for plan-marshall.

    Resolves to ``<base_dir>/worktrees`` where ``<base_dir>`` is the
    plan-local runtime-state root returned by :func:`get_base_dir`. In
    production this is ``<plan-root>/.plan/local/worktrees`` where
    ``<plan-root>`` is resolved by the uniform cwd rule (ADR-002) — worktrees
    live under the existing plan-local tree so they inherit the
    ``Write(.plan/**)`` permission and sit next to other plan-scoped state.

    Anchoring on :func:`get_base_dir` (the uniform cwd-relative resolver, ADR-002)
    means ``get_worktree_root`` honours the ``PLAN_BASE_DIR`` env var and the
    :func:`set_base_dir` override, so tests that isolate runtime state under a
    tmp directory also isolate the worktree root — no leakage into the real
    repo's ``.plan/local/worktrees``.

    Raises:
        RuntimeError: when the base directory cannot be resolved (no override,
            no ``PLAN_BASE_DIR``, and no ``.plan/local`` ancestor of the current
            working directory). Worktrees require a base directory to anchor
            against.
    """
    return get_base_dir() / 'worktrees'


def guard_worktree_cwd(plan_id: str) -> dict[str, Any] | None:
    """Caller-side guard asserting the process cwd is the plan's worktree root.

    This helper is the script-side realization of the SINGLE cwd-unchanged
    invariant (ADR-002 / Option 5'): during phase-5+ the orchestrator pins its
    cwd to the moved-in worktree and never changes it away until finalize moves
    the plan dir back. The lifecycle scripts (``prepare_execute.py`` D4,
    ``integrate_into_main.py`` D5) and phase-5+ ``manage-*`` callers ASSERT this
    invariant by calling this guard at the top of their action.

    The guard ASSERTS; it never SETS the caller's cwd. A subprocess cannot
    mutate its parent's working directory, so the invariant cannot be a script
    side effect — pinning cwd is the caller's responsibility (the orchestrator
    pins it to the path returned by ``prepare_execute``). This function only
    reports whether the current cwd matches the expected worktree path.

    Returns ``None`` (assertion passes) when the current working directory
    resolves to the canonical worktree root for ``plan_id``
    (``get_worktree_root() / plan_id``). Returns a structured error envelope
    (``status: error``, ``error: cwd_left_worktree``) when cwd has left the
    worktree — the caller surfaces it as a TOON refusal. Returns ``None`` when
    the worktree root cannot be resolved (no base dir) OR when the canonical
    worktree directory does not exist on disk: in those cases there is no
    worktree to be pinned to (a main-checkout plan, or a pre-materialization
    window), so the guard is not applicable and must not fire a false positive.

    Args:
        plan_id: Plan identifier whose worktree the cwd is expected to be.

    Returns:
        ``None`` when the assertion passes or is not applicable; a structured
        error dict ``{status, error, expected_worktree, actual_cwd, message}``
        when cwd has demonstrably left the worktree.
    """
    try:
        expected = (get_worktree_root() / plan_id).resolve()
    except RuntimeError:
        # No resolvable base dir → no worktree to anchor against. Not
        # applicable (main-checkout flow or unconfigured test harness).
        return None
    if not expected.is_dir():
        # The worktree directory does not exist on disk — either a
        # main-checkout plan (no worktree) or a pre-materialization window
        # before phase-5 created it. Nothing to be pinned to; not applicable.
        return None
    actual = Path.cwd().resolve()
    if actual == expected:
        return None
    return {
        'status': 'error',
        'error': 'cwd_left_worktree',
        'plan_id': plan_id,
        'expected_worktree': str(expected),
        'actual_cwd': str(actual),
        'message': (
            f'cwd-unchanged invariant violated for plan {plan_id!r}: the process '
            f'working directory is {str(actual)!r} but the plan worktree is '
            f'{str(expected)!r}. Phase-5+ callers MUST keep cwd pinned to the '
            'worktree (the path returned by prepare_execute); this guard asserts '
            'the invariant and never sets the cwd itself.'
        ),
    }


def _resolve_plan_root() -> Path | None:
    """Resolve the plan-root directory by the uniform cwd rule, with a
    clean-checkout git fallback.

    Primary: walk up from cwd to the nearest ``.plan/local`` ancestor
    (:func:`_find_plan_root_from_cwd`). Fallback: when no such ancestor exists —
    CI runners, fresh clones, and consumer installs have no ``.plan/local`` yet
    because ``.plan/`` is gitignored — resolve the enclosing git working tree
    via ``git rev-parse --show-toplevel``. This restores the clean-environment
    robustness the prior ``git_main_checkout_root`` resolver provided while
    keeping the cwd-walk-up as the primary path (ADR-002): the git toplevel is
    consulted ONLY as a last resort, so phase-5+ cwd-pinning is never overridden
    when ``.plan/local`` is present. Returns ``None`` only when neither resolves
    (no ``.plan/local`` ancestor AND not inside a git repository).
    """
    root = _find_plan_root_from_cwd()
    if root is not None:
        return root
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None
    toplevel = result.stdout.strip()
    return Path(toplevel) if toplevel else None


def get_executor_path() -> Path:
    """Return the canonical path to ``.plan/execute-script.py``.

    The executor is resolved cwd-relatively (ADR-002): the parent of the
    base directory returned by :func:`get_base_dir` (i.e. the ``.plan`` dir of
    whichever checkout the working directory is in). During phase-5+ the
    working directory is pinned to the worktree, so this resolves the
    worktree-resident executor moved in at phase-5 start; during the finalize
    regenerate-on-main step the working directory is main, so it resolves
    main's executor.

    Joins the existing ``get_plan_dir`` / ``get_base_dir`` /
    ``get_worktree_root`` helper family.

    Returns:
        Path to ``<plan-root>/.plan/execute-script.py`` where ``<plan-root>`` is
        resolved by the uniform cwd rule.

    Raises:
        RuntimeError: when the base directory cannot be resolved (no override,
            no ``PLAN_BASE_DIR``, no ``.plan/local`` ancestor of cwd, AND the
            cwd is not inside a git repository — see :func:`_resolve_plan_root`).
    """
    # Honour the set_base_dir() / PLAN_BASE_DIR override exactly as get_base_dir
    # does, but anchor the executor at <override>/execute-script.py (the override
    # IS the .plan-local stand-in in tests). In production, walk up from cwd to
    # the nearest .plan/local ancestor (its parent <plan-root>/.plan holds the
    # executor): worktree-resident during phase-5+, main during the finalize
    # regenerate-on-main path.
    if _BASE_DIR_OVERRIDE is not None:
        return Path(_BASE_DIR_OVERRIDE) / 'execute-script.py'
    env_dir = os.environ.get('PLAN_BASE_DIR')
    if env_dir:
        return Path(env_dir) / 'execute-script.py'
    root = _resolve_plan_root()
    if root is None:
        raise RuntimeError(
            'get_executor_path() requires a resolvable plan root; no .plan/local '
            'ancestor of the current working directory could be found. '
            'Set PLAN_BASE_DIR to override (tests).'
        )
    return root / PLAN_DIR_NAME / 'execute-script.py'


def normalize_to_repo_relative(path: str) -> str:
    """Normalize absolute file paths to repository-relative paths.

    If the path is already relative, returns it unchanged.
    If absolute, attempts to strip the git repo root prefix.

    Args:
        path: File path (absolute or relative)

    Returns:
        Repository-relative path string
    """
    if not path.startswith('/'):
        return path
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        repo_root = result.stdout.strip()
        if path.startswith(repo_root + '/'):
            return path[len(repo_root) + 1 :]
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return path


def get_base_dir() -> Path:
    """Get the base directory for plan-marshall runtime state.

    Resolution follows the SINGLE uniform cwd-relative rule (ADR-002):
        1. Explicit set_base_dir() override (tests).
        2. PLAN_BASE_DIR environment variable (tests, user override).
        3. ``<plan-root>/.plan/local`` where ``<plan-root>`` is the nearest
           ancestor of the current working directory containing ``.plan/local``.

    Phases 1-4 resolve to the main checkout (cwd is main); phase-5+ resolve to
    the pinned worktree (cwd is pinned there). There is no per-phase branch and
    no sideways resolution — every path is found by walking up from cwd.

    Raises:
        RuntimeError: when none of the above resolve (no override, no env var,
            no ``.plan/local`` ancestor of the current working directory, AND
            the cwd is not inside a git repository — the git-toplevel fallback
            in :func:`_resolve_plan_root` covers clean checkouts / CI / fresh
            clones that have no ``.plan/local`` yet).
    """
    if _BASE_DIR_OVERRIDE is not None:
        return _BASE_DIR_OVERRIDE
    env_dir = os.environ.get('PLAN_BASE_DIR')
    if env_dir:
        return Path(env_dir)
    root = _resolve_plan_root()
    if root is None:
        raise RuntimeError(
            'plan-marshall runtime state requires a resolvable plan root; '
            'no .plan/local ancestor of the current working directory could be '
            'found. Set PLAN_BASE_DIR to override (tests).'
        )
    return root / PLAN_DIR_NAME / 'local'


def set_base_dir(path: Path | str) -> None:
    """Override the base directory for workflow files.

    Args:
        path: New base directory path

    Note:
        This is primarily for testing purposes. In production,
        the default per-project global directory should be used.
    """
    global _BASE_DIR_OVERRIDE
    _BASE_DIR_OVERRIDE = Path(path)


def base_path(*parts: str) -> Path:
    """Construct a path within the workflow base directory.

    Args:
        *parts: Path components to join

    Returns:
        Full path including the workflow base directory

    Example:
        >>> base_path('plans', 'my-task', 'plan.md')
        PosixPath('.plan/local/plans/my-task/plan.md')
    """
    return get_base_dir().joinpath(*parts)


def get_temp_dir(subdir: str | None = None) -> Path:
    """Get temp directory under the repo-local tracked config dir.

    Args:
        subdir: Optional subdirectory name within temp

    Returns:
        Path to ``.plan/temp[/subdir]`` inside the repo checkout.

    Note:
        temp/ intentionally stays project-local (unlike the runtime state
        under get_base_dir()) so each worktree gets its own isolated temp,
        build logs sit next to the source they came from, and the existing
        ``Write(.plan/**)`` permission keeps covering it. Resolution
        honours PLAN_TRACKED_CONFIG_DIR / PLAN_BASE_DIR overrides via
        get_tracked_config_dir().
    """
    temp_path = get_tracked_config_dir() / 'temp'
    if subdir:
        return temp_path / subdir
    return temp_path


def get_store_dir(store: str, entry_id: str) -> Path:
    """Resolve the root directory for an entry of a named runtime-state store.

    This is the ONE parameterized store-root mechanism for entry-shaped stores
    in the manage-* path layer — stores addressed by an ``entry_id`` (a plan id
    or an epic id). Non-entry-shaped machine-wide state (``build-queue.json``,
    ``credentials/``) is NOT resolved here: it anchors to the distinct
    machine-global home-root tier, ``marketplace_paths.home_root()``, which
    returns a single host-wide ``~/.plan-marshall`` directory shared across every
    checkout. No new store name is added for that tier; it is a separate
    mechanism, not a store. Each store below maps to its own resolution rule:

    - ``store='plans'`` — routes through the existing cwd-relative
      :func:`base_path` (``{base_dir}/plans/{entry_id}``, ADR-002 unchanged):
      plan state moves into the pinned worktree during phase-5+ and resolves
      wherever the working directory is.
    - ``store='orchestrator'`` — routes through
      :func:`marketplace_paths.resolve_main_anchored_path`
      (``<main-root>/.plan/local/orchestrator/{entry_id}``): orchestrator
      state is cross-session shared state that stays main-anchored regardless
      of caller cwd, joining the bounded main-anchored exception set.

    Args:
        store: Store name — ``'plans'`` or ``'orchestrator'``.
        entry_id: Entry identifier within the store (a plan id or an epic id).

    Returns:
        Path to the entry's root directory under the selected store.

    Raises:
        ValueError: when ``store`` is not a known store name, or when an
            ``'orchestrator'`` ``entry_id`` contains a path-traversal or
            path-separator component (``..``, ``/``, ``\\``, or an embedded
            null byte).
    """
    if store == 'plans':
        return base_path('plans', entry_id)
    if store == 'orchestrator':
        # entry_id (an epic slug) flows unvalidated from CLI callers straight
        # into the main-anchored join below, and this is the single choke point
        # for every orchestrator-store consumer — including
        # claude_runtime.py's _read_orchestrator_title_state(slug), which reads
        # this function directly without going through orchestrator.py's
        # _validate_slug. Reject traversal and separator components here so no
        # caller can escape the orchestrator/ subtree.
        _reject_unsafe_entry_id(entry_id)
        return resolve_main_anchored_path(f'orchestrator/{entry_id}')
    raise ValueError(
        f"unknown store {store!r}: expected 'plans' or 'orchestrator'"
    )


def _reject_unsafe_entry_id(entry_id: str) -> None:
    """Reject an orchestrator-store ``entry_id`` that could escape the subtree.

    Guards the single ``get_store_dir(store='orchestrator', ...)`` choke point
    against path traversal (``..``), path separators (``/`` or ``\\``), and
    embedded null bytes before the value is interpolated into a filesystem
    join. An empty or whitespace-only value is likewise rejected — it cannot
    name a real entry directory.

    Args:
        entry_id: Orchestrator-store entry identifier (an epic slug).

    Raises:
        ValueError: when ``entry_id`` is empty/whitespace-only or contains
            ``..``, ``/``, ``\\``, or a null byte.
    """
    if not entry_id or not entry_id.strip():
        raise ValueError('orchestrator entry_id must be a non-empty identifier')
    if (
        '..' in entry_id
        or '/' in entry_id
        or '\\' in entry_id
        or '\x00' in entry_id
    ):
        raise ValueError(
            f'unsafe orchestrator entry_id {entry_id!r}: must not contain '
            "'..', '/', '\\', or a null byte"
        )


def get_plan_dir(plan_id: str) -> Path:
    """Get the plan directory path for a given plan ID.

    Delegates to :func:`get_store_dir` with ``store='plans'`` — behavior is
    byte-identical to the previous direct ``base_path('plans', plan_id)``.

    Args:
        plan_id: Plan identifier

    Returns:
        Path to {base_dir}/plans/{plan_id}/
    """
    return get_store_dir('plans', plan_id)


class PlanNotFoundError(Exception):
    """Raised by :func:`require_plan_exists` when the plan directory or its
    ``status.json`` sentinel is missing.

    Carries the resolved ``plan_dir`` so call sites can surface it in their
    structured error envelopes (TOON ``error: plan_not_found``).
    """

    def __init__(self, plan_id: str, plan_dir: Path, reason: str) -> None:
        self.plan_id = plan_id
        self.plan_dir = plan_dir
        self.reason = reason
        super().__init__(
            f"plan '{plan_id}' not found: {reason} (expected at {plan_dir})"
        )


def require_plan_exists(plan_id: str) -> Path:
    """Assert a plan directory exists and looks initialized; return its path.

    A plan is considered initialized when its directory exists AND contains a
    ``status.json`` sentinel — the marker that ``phase-1-init`` writes once
    the plan has been formally created. Bare directory existence is NOT
    sufficient (a stray ``mkdir`` from an earlier orphan-creating call site
    must not satisfy the guard).

    Call this BEFORE any ``parent.mkdir(...)`` whose parent is a
    ``{base_dir}/plans/{plan_id}/...`` path, to prevent silent orphan-plan
    creation by scripts that hold a ``plan_id`` but were never gated on
    plan existence.

    Args:
        plan_id: Plan identifier.

    Returns:
        Resolved path to the plan directory.

    Raises:
        PlanNotFoundError: when the plan directory does not exist OR when it
            exists but is missing the ``status.json`` sentinel. The exception
            exposes ``plan_id``, ``plan_dir``, and a human-readable ``reason``
            string suitable for TOON ``message`` fields.
    """
    plan_dir = get_plan_dir(plan_id)
    if not plan_dir.is_dir():
        raise PlanNotFoundError(plan_id, plan_dir, 'plan directory does not exist')
    if not (plan_dir / 'status.json').is_file():
        raise PlanNotFoundError(
            plan_id, plan_dir, 'plan directory exists but is missing status.json'
        )
    return plan_dir


def get_tracked_config_dir() -> Path:
    """Get the repo-local tracked configuration directory.

    Returns the repo-local ``.plan/`` directory where tracked files live
    (``marshal.json`` and ``project-architecture/``). Unlike get_base_dir(),
    this normally points at the repo — not the per-project global directory.

    Resolution order:
        1. Explicit set_base_dir() override (tests).
        2. PLAN_TRACKED_CONFIG_DIR environment variable (tests, fine-grained
           override).
        3. PLAN_BASE_DIR environment variable (backward compatibility for
           tests that already stage both runtime state AND marshal.json in
           the same fixture directory).
        4. ``<plan-root>/.plan`` where ``<plan-root>`` is the nearest ancestor
           of the current working directory containing ``.plan/local`` (the
           uniform cwd rule, ADR-002).
        5. ./.plan relative to cwd (fallback).
    """
    if _BASE_DIR_OVERRIDE is not None:
        return _BASE_DIR_OVERRIDE
    env_tracked = os.environ.get('PLAN_TRACKED_CONFIG_DIR')
    if env_tracked:
        return Path(env_tracked)
    env_base = os.environ.get('PLAN_BASE_DIR')
    if env_base:
        return Path(env_base)
    root = _find_plan_root_from_cwd()
    if root is not None:
        return root / PLAN_DIR_NAME
    return Path(PLAN_DIR_NAME)


def get_marshal_path() -> Path:
    """Path to the tracked marshal.json file."""
    return get_tracked_config_dir() / 'marshal.json'


def read_json(path: str | Path, default: Any = None) -> Any:
    """Read and parse a JSON file, returning default if not found or unreadable.

    Args:
        path: Path to JSON file
        default: Value to return if file doesn't exist (default: empty dict)

    Returns:
        Parsed JSON content, or default if the file does not exist, is
        unreadable (e.g. a directory, permission denied), or contains
        unparseable JSON. All failure modes degrade deterministically to
        default rather than raising.
    """
    if default is None:
        default = {}
    p = Path(path)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: str | Path, data: Any) -> None:
    """Write data as formatted JSON, creating parent dirs as needed.

    Args:
        path: Target file path
        data: Data to serialize as JSON
    """
    atomic_write_file(path, json.dumps(data, indent=2))


def atomic_write_file(path: str | Path, content: str) -> None:
    """Write file atomically using temp file + rename pattern.

    Args:
        path: Target file path
        content: Content to write

    Raises:
        OSError: If write or rename fails
    """
    path = Path(path)

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file first, then rename (atomic on most systems)
    fd, temp_path = tempfile.mkstemp(suffix=path.suffix, prefix='.tmp_', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
            # Ensure content ends with newline
            if content and not content.endswith('\n'):
                f.write('\n')
        os.replace(temp_path, path)
    except Exception:
        if Path(temp_path).exists():
            os.unlink(temp_path)
        raise


def ensure_directory(path: str | Path) -> Path:
    """Create directory and parents if needed.

    Args:
        path: File or directory path

    Returns:
        Path object for the directory

    Note:
        If path looks like a file (has extension), creates parent directory.
        Otherwise creates the directory itself.
    """
    path = Path(path)

    # If path has a file extension, assume it's a file path
    if path.suffix:
        target_dir = path.parent
    else:
        target_dir = path

    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def output_toon(data: dict[str, Any]) -> None:
    """Print TOON formatted data to stdout.

    Generic TOON output helper for scripts that need to emit structured responses.

    Args:
        data: Dictionary to serialize as TOON
    """
    print(serialize_toon(data))


def format_toon_value(value: Any) -> str:
    """Format a value for TOON output.

    Args:
        value: Value to format

    Returns:
        Formatted string
    """
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, list):
        return '+'.join(str(v) for v in value)
    return str(value)


def print_toon_table(name: str, items: list, fields: list) -> None:
    """Print a TOON table with tab-separated columns.

    Args:
        name: Table name
        items: List of dicts
        fields: List of field names to include
    """
    field_spec = ','.join(fields)
    print(f'{name}[{len(items)}]{{{field_spec}}}:')
    for item in items:
        values = [format_toon_value(item.get(f, '')) for f in fields]
        print('\t'.join(values))


def print_toon_list(name: str, items: list) -> None:
    """Print a TOON list.

    Args:
        name: List name
        items: List of values
    """
    print(f'{name}[{len(items)}]:')
    for item in items:
        print(f'  - {item}')


def print_toon_kv(key: str, value: Any, indent: int = 0) -> None:
    """Print a key-value pair in TOON format.

    Args:
        key: Key name
        value: Value (can be str, int, bool, list, dict)
        indent: Indentation level
    """
    prefix = '  ' * indent
    if isinstance(value, dict):
        print(f'{prefix}{key}:')
        for k, v in value.items():
            print_toon_kv(k, v, indent + 1)
    elif isinstance(value, list):
        print(f'{prefix}{key}[{len(value)}]:')
        for item in value:
            print(f'{prefix}  - {item}')
    else:
        formatted = format_toon_value(value)
        print(f'{prefix}{key}: {formatted}')


def output_success(operation: str, **kwargs: Any) -> None:
    """Print TOON success output to stdout.

    Args:
        operation: Name of the operation
        **kwargs: Additional fields to include in output
    """
    result = {'status': 'success', 'success': True, 'operation': operation}
    result.update(kwargs)
    print(serialize_toon(result))


def output_error(operation: str, error: str) -> None:
    """Print TOON error output to stderr (canonical low-level variant).

    This is the shared base implementation. Domain-specific variants exist in
    ci_base.py, _tasks_core.py, and _documents_core.py.
    Per manage-contract.md: prefer output_toon_error() for manage-* scripts.
    """
    result = {'status': 'error', 'success': False, 'operation': operation, 'error': error}
    print(serialize_toon(result), file=sys.stderr)


def output_toon_error(error_code: str, message: str, **kwargs: Any) -> None:
    """Print TOON error output to stdout following the manage-* contract.

    Standard error format: status=error, error=<code>, message=<msg>.

    Args:
        error_code: Machine-readable error code (e.g., 'invalid_plan_id')
        message: Human-readable error description
        **kwargs: Additional fields to include in output
    """
    result: dict[str, Any] = {'status': 'error', 'error': error_code, 'message': message}
    result.update(kwargs)
    print(serialize_toon(result))


def parse_markdown_metadata(content: str) -> dict[str, str]:
    """Parse key=value metadata from markdown content.

    Parses metadata at the start of markdown content that uses key=value format.
    Metadata ends at first blank line or markdown heading.

    Supports dot notation for nested keys: component.type=command

    Args:
        content: Full markdown file content

    Returns:
        Dictionary of metadata key-value pairs

    Example:
        >>> content = '''id=example-001
        ... component.type=command
        ... applied=false
        ...
        ... # Title
        ... Content here...'''
        >>> parse_markdown_metadata(content)
        {'id': 'example-001', 'component.type': 'command', 'applied': 'false'}
    """
    metadata = {}
    lines = content.split('\n')

    for line in lines:
        line = line.strip()

        # Stop at blank line or heading
        if not line or line.startswith('#'):
            break

        # Parse key=value
        if '=' in line:
            key, value = line.split('=', 1)
            metadata[key.strip()] = value.strip()

    return metadata


def generate_markdown_metadata(data: dict[str, str]) -> str:
    """Generate key=value metadata block from dictionary.

    Args:
        data: Dictionary of metadata key-value pairs

    Returns:
        Formatted metadata block string

    Example:
        >>> data = {'id': 'example-001', 'component.type': 'command'}
        >>> print(generate_markdown_metadata(data))
        id=example-001
        component.type=command
    """
    lines = []
    for key, value in data.items():
        lines.append(f'{key}={value}')
    return '\n'.join(lines)


def update_markdown_metadata(content: str, updates: dict[str, str]) -> str:
    """Update specific metadata fields in markdown content.

    Preserves existing metadata and content, only updating specified keys.

    Args:
        content: Full markdown file content
        updates: Dictionary of key-value pairs to update

    Returns:
        Updated content with modified metadata
    """
    lines = content.split('\n')
    metadata_end = 0
    metadata_lines = []
    found_keys = set()

    # Find metadata lines and their end position
    for i, line in enumerate(lines):
        stripped = line.strip()

        # Stop at blank line or heading
        if not stripped or stripped.startswith('#'):
            metadata_end = i
            break

        # Parse existing metadata line
        if '=' in stripped:
            key = stripped.split('=', 1)[0].strip()
            if key in updates:
                metadata_lines.append(f'{key}={updates[key]}')
                found_keys.add(key)
            else:
                metadata_lines.append(line)
        else:
            metadata_lines.append(line)
    else:
        # No blank line found, all content is metadata
        metadata_end = len(lines)

    # Add any new keys not found in existing metadata
    for key, value in updates.items():
        if key not in found_keys:
            metadata_lines.append(f'{key}={value}')

    # Reconstruct content
    remaining = lines[metadata_end:]
    return '\n'.join(metadata_lines + remaining)


def get_metadata_content_split(content: str) -> tuple[str, str]:
    """Split markdown content into metadata and body.

    Args:
        content: Full markdown file content

    Returns:
        Tuple of (metadata_block, body_content)
    """
    lines = content.split('\n')
    metadata_lines = []
    body_start = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Stop at blank line or heading
        if not stripped or stripped.startswith('#'):
            body_start = i
            break

        # This is a metadata line
        if '=' in stripped:
            metadata_lines.append(line)

    metadata_block = '\n'.join(metadata_lines)
    body = '\n'.join(lines[body_start:])

    return metadata_block, body


def safe_main(main_fn: Any) -> Any:
    """Decorator for script entry points that catches unhandled exceptions.

    Wraps the main function so that an uncaught exception is rendered as a
    structured ``status: error`` TOON on **stdout** (via ``output_toon_error``)
    and the process exits with code 1, instead of printing a raw traceback or
    writing the error to stderr. Emitting on stdout matches the canonical
    ``manage-*`` TOON-on-stdout output contract
    (``pm-plugin-development:plugin-script-architecture/standards/output-contract.md``):
    a genuine crash is exit 1 carrying a parseable diagnostic payload, never an
    info-free empty-stdout exit 1. ``sys.exit(1)`` is retained, so the exit code
    still distinguishes a crash (1) from an operation failure (0).

    Usage:
        @safe_main
        def main() -> int:
            ...
            return 0

        if __name__ == '__main__':
            main()  # calls sys.exit internally
    """
    import functools

    @functools.wraps(main_fn)
    def wrapper() -> None:
        try:
            sys.exit(main_fn())
        except KeyboardInterrupt:
            sys.exit(130)
        except SystemExit:
            raise
        except Exception as e:
            output_toon_error('internal_error', str(e))
            sys.exit(1)

    return wrapper


def copy_tree(src: Path, dst: Path) -> None:
    """Recursively copy ``src`` directory tree into ``dst``.

    Generic recursive directory-copy helper exposed via the ``copy-tree`` CLI
    subcommand. It copies a directory tree verbatim, skipping symlinks and
    failing loudly when the destination already exists.

    Behaviour:
        - Recursive copy of every regular file in ``src`` into ``dst``.
        - Symlinks are skipped (not followed) — the copy is a static copy of
          the on-disk tree, never indirected through symlinks.
        - Parent directories of ``dst`` are created on demand (``mkdir -p``).
        - Raises ``FileExistsError`` when ``dst`` already exists. Callers MUST
          either choose a fresh destination path or remove ``dst`` before
          calling — this helper never silently merges over an existing tree.
        - Implementation delegates to ``shutil.copytree`` with
          ``symlinks=False`` (skip symlinks) and ``dirs_exist_ok=False``
          (raise on existing destination).

    Args:
        src: Source directory to copy from. Must exist and be a directory.
        dst: Destination directory. Must NOT exist; parent directories are
            created automatically.

    Raises:
        FileNotFoundError: when ``src`` does not exist.
        NotADirectoryError: when ``src`` exists but is not a directory.
        FileExistsError: when ``dst`` already exists.
    """
    src_path = Path(src)
    dst_path = Path(dst)

    if not src_path.exists():
        raise FileNotFoundError(f'copy_tree source does not exist: {src_path}')
    if not src_path.is_dir():
        raise NotADirectoryError(f'copy_tree source is not a directory: {src_path}')
    if dst_path.exists():
        raise FileExistsError(f'copy_tree destination already exists: {dst_path}')

    # Ensure parent of dst exists (mkdir -p semantics for the parent only;
    # dst itself is created by copytree).
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    # shutil.copytree walks the source tree; symlinks=False would convert any
    # symlink it visits into a copy of its target (following file symlinks AND
    # recursing into directory symlinks). A copy_function-only filter cannot
    # block directory symlinks because copytree decides whether to recurse
    # before invoking copy_function on the directory's children. To skip
    # symlinks entirely (file AND directory), filter them out at the directory
    # listing level via the `ignore` callable so copytree never sees them.
    def _ignore_symlinks(directory: str, names: list[str]) -> list[str]:
        return [name for name in names if (Path(directory) / name).is_symlink()]

    shutil.copytree(
        src_path,
        dst_path,
        symlinks=False,
        ignore=_ignore_symlinks,
        ignore_dangling_symlinks=True,
        dirs_exist_ok=False,
    )


def _cli_copy_tree(args: argparse.Namespace) -> int:
    """CLI handler: ``file_ops copy-tree --src SRC --dst DST``.

    Wraps :func:`copy_tree` for invocation via the marketplace executor
    (e.g. from ``phase-1-init/SKILL.md``). Resolves ``src`` and ``dst`` to
    absolute paths against the current working directory, then delegates to
    the library function. Errors surface as the standard manage-* TOON
    contract (``status: error``, ``error: <code>``, ``message: ...``).
    """
    src = Path(args.src).resolve()
    dst = Path(args.dst).resolve()

    try:
        copy_tree(src, dst)
    except FileNotFoundError as exc:
        output_toon_error('src_not_found', str(exc), src=str(src), dst=str(dst))
        return 1
    except NotADirectoryError as exc:
        output_toon_error('src_not_directory', str(exc), src=str(src), dst=str(dst))
        return 1
    except FileExistsError as exc:
        output_toon_error('dst_already_exists', str(exc), src=str(src), dst=str(dst))
        return 1

    output_toon(
        {
            'status': 'success',
            'operation': 'copy-tree',
            'src': str(src),
            'dst': str(dst),
        }
    )
    return 0


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for file_ops CLI subcommands."""
    parser = argparse.ArgumentParser(
        prog='file_ops',
        description='File operations utility (CLI wrappers around library helpers).',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    cp = subparsers.add_parser(
        'copy-tree',
        help='Recursively copy a directory tree (symlinks skipped, fails if destination exists).',
        allow_abbrev=False,
    )
    cp.add_argument('--src', required=True, help='Source directory path.')
    cp.add_argument('--dst', required=True, help='Destination directory path (must not exist).')
    cp.set_defaults(handler=_cli_copy_tree)

    return parser


def _main() -> int:
    """CLI entry-point. Dispatches to the selected subcommand handler."""
    parser = _build_arg_parser()
    args = parser.parse_args()
    return int(args.handler(args))


if __name__ == '__main__':
    sys.exit(_main())
