"""
Shared marketplace path resolution.

Provides centralized path discovery for marketplace bundles and plugin cache.
Used by generate_executor.py, scan-marketplace-inventory.py, and other scripts
that need to locate marketplace infrastructure.

Resolution follows a SINGLE uniform cwd/worktree-relative rule (see ADR-002):
``set_base_dir()`` override (file_ops) → ``PLAN_BASE_DIR`` env override → walk
up from the current working directory to the nearest ancestor containing a
``.plan/local`` directory. There is no per-phase branch and no sideways
resolution indirection — phases 1-4 resolve to the main checkout because the
working directory IS main, and phase-5+ resolve to the pinned worktree because
the working directory is pinned there. The single deliberate exception is the
merge lock (``merge_lock.py``), which always resolves to the main checkout;
every other resolution in the codebase is cwd-relative.
"""

import os
from pathlib import Path

# Central configuration
PLAN_DIR_NAME = os.environ.get('PLAN_DIR_NAME', '.plan')
MARKETPLACE_BUNDLES_PATH = 'marketplace/bundles'
CLAUDE_DIR = '.claude'
PLUGIN_CACHE_SUBPATH = 'plugins/cache/plan-marshall'


# =============================================================================
# Uniform cwd-relative plan-root resolver
# =============================================================================
# This primitive lives here (in script-shared, the foundation bundle) and is
# imported by tools-file-ops/file_ops.py. Do NOT duplicate it — the lesson
# from PR #160 review was to consolidate, not maintain parallel copies.


def _find_plan_root_from_cwd() -> Path | None:
    """Walk up from the current working directory to the nearest ancestor
    containing a ``.plan/local`` directory and return that ancestor.

    This is the single uniform cwd-relative discovery step (ADR-002). It finds
    the FIRST ancestor whose ``<ancestor>/.plan/local`` directory exists, so a
    working directory inside a materialized-but-not-yet-populated worktree (no
    ``.plan/local`` yet) falls back to the nearest enclosing ancestor that does
    have one — during the move-in window that is still the main checkout. There
    is no sideways resolution; every path is found by walking up from cwd.

    Returns:
        The ancestor directory containing ``.plan/local``, or ``None`` when no
        ancestor of the current working directory contains one.
    """
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / PLAN_DIR_NAME / 'local').is_dir():
            return candidate
    return None


def get_temp_dir(subdir: str) -> Path:
    """Get temp directory under the cwd-relative ``.plan/temp/{subdir}``.

    temp/ stays alongside the runtime state resolved by the uniform cwd rule so
    each worktree keeps its own isolated temp and the existing
    ``Write(.plan/**)`` permission keeps covering it.

    Resolution precedence: ``PLAN_BASE_DIR`` override (tests) → cwd walk-up to
    the nearest ``.plan/local`` ancestor → relative ``.plan/temp`` fallback.
    """
    env_dir = os.environ.get('PLAN_BASE_DIR')
    if env_dir:
        return Path(env_dir) / 'temp' / subdir
    root = _find_plan_root_from_cwd()
    if root is not None:
        return root / PLAN_DIR_NAME / 'temp' / subdir
    return Path(PLAN_DIR_NAME) / 'temp' / subdir


def safe_relative_path(path: Path) -> str:
    """Return path relative to cwd if possible, otherwise absolute path."""
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def find_marketplace_path(marketplace_root: Path | None = None) -> Path | None:
    """Find ``marketplace/bundles`` directory using a four-step resolution order.

    Resolution order (highest priority first):

    1. Explicit ``marketplace_root`` parameter — used as the anchor when caller
       provides an absolute path. The function returns
       ``marketplace_root / 'marketplace/bundles'`` if that directory exists.
    2. ``PM_MARKETPLACE_ROOT`` environment variable — same anchor semantics as
       the explicit parameter, but sourced from the environment.
    3. cwd walk-up — probes ``Path.cwd()`` and each ancestor for the standard
       ``marketplace/bundles`` layout. Under the uniform cwd rule (ADR-002) the
       working directory IS main (phases 1-4) or the pinned worktree (phase-5+),
       so the source tree is found by walking up from cwd; there is no
       sideways resolution indirection.
    4. cwd/parent discovery — the legacy fallback that probes ``Path.cwd()`` and
       its immediate parent for the standard ``marketplace/bundles`` layout.
       Retained for backward-compat with first-run bootstrap scenarios.

    Args:
        marketplace_root: Optional explicit override. When provided, takes
            precedence over the env var, script-relative walk, and cwd
            discovery. Must point at a directory that contains
            ``marketplace/bundles``.

    Returns:
        Path to ``marketplace/bundles`` if any branch resolves, otherwise None.
    """
    # Branch 1: explicit override
    if marketplace_root is not None:
        candidate = Path(marketplace_root) / MARKETPLACE_BUNDLES_PATH
        if candidate.is_dir():
            return candidate
        return None

    # Branch 2: environment variable
    env_root = os.environ.get('PM_MARKETPLACE_ROOT')
    if env_root:
        candidate = Path(env_root) / MARKETPLACE_BUNDLES_PATH
        if candidate.is_dir():
            return candidate
        return None

    # Branch 3: cwd walk-up resolution
    # The source marketplace/bundles tree lives at whichever checkout the
    # working directory is in — main (phases 1-4) or the pinned worktree
    # (phase-5+). Walk up from cwd to the nearest ancestor that contains
    # marketplace/bundles (ADR-002 uniform cwd rule).
    cwd = Path.cwd().resolve()
    for candidate_root in (cwd, *cwd.parents):
        candidate = candidate_root / MARKETPLACE_BUNDLES_PATH
        if candidate.is_dir():
            return candidate

    # Branch 4: cwd/parent discovery (legacy bootstrap fallback)
    if (Path.cwd() / MARKETPLACE_BUNDLES_PATH).is_dir():
        return Path.cwd() / MARKETPLACE_BUNDLES_PATH
    if (Path.cwd().parent / MARKETPLACE_BUNDLES_PATH).is_dir():
        return Path.cwd().parent / MARKETPLACE_BUNDLES_PATH
    return None


def get_plugin_cache_path() -> Path | None:
    """Get plugin cache path if it exists."""
    cache_path = Path.home() / CLAUDE_DIR / PLUGIN_CACHE_SUBPATH
    return cache_path if cache_path.is_dir() else None


def get_base_path(scope: str = 'auto', marketplace_root: Path | None = None) -> Path:
    """Determine base path based on scope.

    Args:
        scope: Discovery scope. Valid values:
            - 'auto': tries marketplace first, then plugin-cache (default)
            - 'marketplace': force marketplace context
            - 'plugin-cache': force plugin cache context
            - 'cache-first': tries plugin-cache first, then marketplace (executor default)
            - 'global': ~/.claude
            - 'project': ./.claude
        marketplace_root: Optional explicit override forwarded to
            :func:`find_marketplace_path`. Honored for the marketplace-aware
            scopes (``auto``, ``marketplace``, ``cache-first``); ignored for
            ``plugin-cache``, ``global``, and ``project`` scopes whose targets
            are not anchored on the marketplace root. See
            :func:`find_marketplace_path` for the full four-step resolution
            order (explicit param → ``PM_MARKETPLACE_ROOT`` env var →
            script-relative walk → cwd-based discovery).

    Returns:
        Path to the bundles directory (or .claude for global/project scope)

    Raises:
        FileNotFoundError: If requested context is not available
        ValueError: If scope is invalid
    """
    # An explicit anchor — either the function parameter or the
    # ``PM_MARKETPLACE_ROOT`` environment variable — must outrank the
    # plugin cache for ``cache-first`` (and ``auto``) scopes. Without this,
    # callers that pass ``marketplace_root=<worktree>`` (e.g.
    # generate_executor.py running inside an isolated worktree) would
    # silently regenerate the executor against the cached main checkout
    # because cache-first short-circuits on the first cache hit. The
    # explicit override exists precisely to escape that branch — see
    # lesson 2026-05-01-09-001 (consolidated 2026-04-29-06-001) for the
    # original failure mode.
    explicit_anchor = marketplace_root is not None or bool(os.environ.get('PM_MARKETPLACE_ROOT'))

    if scope == 'auto':
        marketplace = find_marketplace_path(marketplace_root=marketplace_root)
        if marketplace:
            return marketplace
        raise FileNotFoundError(f'{MARKETPLACE_BUNDLES_PATH} not found. Run from marketplace repo root.')

    if scope == 'cache-first':
        if explicit_anchor:
            # Skip the cache and resolve from the explicit anchor first.
            marketplace = find_marketplace_path(marketplace_root=marketplace_root)
            if marketplace:
                return marketplace
            raise FileNotFoundError(
                f'Explicit marketplace anchor did not resolve to {MARKETPLACE_BUNDLES_PATH}. '
                f'Set --marketplace-root or PM_MARKETPLACE_ROOT to a directory containing '
                f'{MARKETPLACE_BUNDLES_PATH}.'
            )
        cache = get_plugin_cache_path()
        if cache:
            return cache
        marketplace = find_marketplace_path(marketplace_root=marketplace_root)
        if marketplace:
            return marketplace
        raise FileNotFoundError(
            f'Neither plugin cache ({Path.home() / CLAUDE_DIR / PLUGIN_CACHE_SUBPATH}) '
            f'nor {MARKETPLACE_BUNDLES_PATH} found. '
            f'Ensure plugin is installed or run from marketplace repo.'
        )

    if scope == 'marketplace':
        marketplace = find_marketplace_path(marketplace_root=marketplace_root)
        if marketplace:
            return marketplace
        raise FileNotFoundError(f'{MARKETPLACE_BUNDLES_PATH} directory not found')

    if scope == 'plugin-cache':
        cache = get_plugin_cache_path()
        if cache:
            return cache
        raise FileNotFoundError(f'Plugin cache not found: {Path.home() / CLAUDE_DIR / PLUGIN_CACHE_SUBPATH}')

    if scope == 'global':
        return Path.home() / CLAUDE_DIR

    if scope == 'project':
        return Path.cwd() / CLAUDE_DIR

    raise ValueError(f'Invalid scope: {scope}')
