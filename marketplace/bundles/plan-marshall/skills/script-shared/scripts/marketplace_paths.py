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
import subprocess
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


# =============================================================================
# Main-anchored resolution — THE single sanctioned exception (ADR-002)
# =============================================================================
# Every OTHER resolver in the codebase is uniform cwd-relative
# (``_find_plan_root_from_cwd`` above, ``file_ops.get_base_dir``). The function
# below is the ONE deliberate exception: it resolves to the MAIN checkout's
# ``.plan/local`` regardless of caller cwd. The resolution logic was lifted
# verbatim from ``merge_lock.py``'s private ``_resolve_main_lock_path`` /
# ``_main_checkout_root`` so all cross-session shared state shares one
# mechanism instead of proliferating ad-hoc git-common-dir copies.


def _override_is_set() -> bool:
    """Return True when file_ops has a ``set_base_dir()`` override installed.

    The ``import file_ops`` is deferred (in-function) on purpose:
    ``marketplace_paths`` is imported BY ``file_ops``, so a module-top import
    here would create a circular import. Mirrors ``merge_lock._override_is_set``.
    """
    import file_ops  # type: ignore[import-not-found]

    return getattr(file_ops, '_BASE_DIR_OVERRIDE', None) is not None


def _main_checkout_root() -> Path:
    """Return the MAIN checkout root via ``git rev-parse --git-common-dir``.

    The common dir is main's ``.git`` directory even when invoked from a linked
    worktree (a worktree's ``.git`` is a file, but the common dir always points
    at main); its parent is the main checkout root.

    Raises:
        RuntimeError: when git cannot resolve the common dir (not a repo).
    """
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--git-common-dir'],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f'cannot resolve main checkout via git common dir: {exc}') from exc
    # ``--path-format=absolute`` (Git >= 2.31) is intentionally NOT passed so the
    # resolver works on older Git (e.g. 2.25 on Ubuntu 20.04 LTS). Without it,
    # ``--git-common-dir`` returns an absolute path from a linked worktree but a
    # cwd-relative ``.git`` from the main checkout — resolve() only when the path
    # is not already absolute to avoid a redundant syscall.
    common_dir = Path(result.stdout.strip())
    if not common_dir.is_absolute():
        common_dir = common_dir.resolve()
    # The common dir is <main-root>/.git; its parent is the main checkout root.
    return common_dir.parent


def resolve_main_anchored_path(subpath: str | Path) -> Path:
    """Resolve ``subpath`` under the MAIN checkout's ``.plan/local``, cwd-independent.

    This is THE single sanctioned main-anchored exception resolver (ADR-002).
    It is the ONLY mechanism that resolves to the main checkout regardless of
    cwd; every other resolution in the codebase is uniform cwd-relative. New
    cross-session shared state MUST route through this function rather than
    re-implementing git-common-dir resolution. The bounded exception set is
    exactly: ``merge.lock``, ``run-configuration.json``, ``lessons-learned``.

    Resolution precedence:

      1. Test override — when ``PLAN_BASE_DIR`` is set or ``file_ops`` carries a
         ``set_base_dir()`` override, that directory IS the main-checkout
         ``.plan/local`` stand-in, so the result is ``<base>/subpath``. This
         preserves every existing ``PLAN_BASE_DIR``-based test in every consumer.
      2. Production — ``git rev-parse --git-common-dir`` resolves main's ``.git``
         even from a linked worktree; its parent is the main checkout root, so
         the result is ``<main-root>/.plan/local/subpath``.

    Args:
        subpath: Path under the main checkout's ``.plan/local`` to resolve.
            An empty string resolves to the ``.plan/local`` base itself.

    Returns:
        The absolute path to ``subpath`` anchored under the main checkout's
        ``.plan/local``.

    Raises:
        RuntimeError: in the production branch when git cannot resolve the
            common dir (not a repo and no override set).
    """
    # 1. Honour the test override exactly as file_ops.get_base_dir does. Under
    #    an override or PLAN_BASE_DIR, that directory stands in for the
    #    main-checkout .plan/local, so the subpath lives directly under it. The
    #    file_ops import is deferred — see _override_is_set's docstring.
    if os.environ.get('PLAN_BASE_DIR') or _override_is_set():
        import file_ops  # type: ignore[import-not-found]

        return file_ops.get_base_dir() / subpath

    # 2. Production: resolve the MAIN checkout via the git common dir, which
    #    points at main's .git even from a linked worktree.
    main_root = _main_checkout_root()
    return main_root / PLAN_DIR_NAME / 'local' / subpath


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
    # explicit override exists precisely to escape that branch.
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
