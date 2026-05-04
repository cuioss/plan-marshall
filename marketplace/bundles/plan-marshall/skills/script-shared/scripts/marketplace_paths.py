"""
Shared marketplace path resolution.

Provides centralized path discovery for marketplace bundles and plugin cache.
Used by generate_executor.py, scan-marketplace-inventory.py, and other scripts
that need to locate marketplace infrastructure.

Runtime plan-marshall state lives at ``<git_main_checkout_root>/.plan/local/``
(project-local, covered by the existing ``Write(.plan/**)`` permission).
"""

import functools
import os
import subprocess
from pathlib import Path

# Central configuration
PLAN_DIR_NAME = os.environ.get('PLAN_DIR_NAME', '.plan')
MARKETPLACE_BUNDLES_PATH = 'marketplace/bundles'
CLAUDE_DIR = '.claude'
PLUGIN_CACHE_SUBPATH = 'plugins/cache/plan-marshall'


# =============================================================================
# Canonical git-root + project-dir-name resolver
# =============================================================================
# These primitives live here (in script-shared, the foundation bundle) and are
# imported by tools-file-ops/file_ops.py. Do NOT duplicate them — the lesson
# from PR #160 review was to consolidate, not maintain parallel copies.


@functools.lru_cache(maxsize=8)
def _resolve_git_main_checkout_root(cwd_marker: str) -> Path | None:
    """Cached worker for git_main_checkout_root.

    Cache key is the resolved absolute cwd at call time, so a test that
    monkeypatches ``os.chdir`` into a different directory gets a fresh
    lookup. ``maxsize=8`` is enough to absorb cwd-juggling test loops
    while keeping production (single cwd) effectively cache-of-one.
    """
    del cwd_marker  # only used as the cache key
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None
    common_dir = result.stdout.strip()
    if not common_dir:
        return None
    return Path(common_dir).parent


def git_main_checkout_root() -> Path | None:
    """Return the main git checkout root, or None if not in a git repo.

    Worktree-safe: uses ``git rev-parse --git-common-dir`` so worktrees
    resolve to the same main checkout as the primary working tree. The
    result is cached per cwd to avoid spawning a git subprocess on every
    base-dir lookup.
    """
    return _resolve_git_main_checkout_root(os.getcwd())


def get_plan_dir() -> Path:
    """Get the plan-marshall runtime-state base directory.

    Resolution order mirrors tools-file-ops.get_base_dir():
        1. PLAN_BASE_DIR environment variable (tests, user override).
        2. ``<git_main_checkout_root>/.plan/local`` when inside a git repo.

    Raises:
        RuntimeError: when neither resolves (no env var, not inside a
            git repository).
    """
    env_dir = os.environ.get('PLAN_BASE_DIR')
    if env_dir:
        return Path(env_dir)
    root = git_main_checkout_root()
    if root is None:
        raise RuntimeError(
            'plan-marshall runtime state requires a git checkout; '
            'no main checkout root could be resolved from cwd. '
            'Set PLAN_BASE_DIR to override (tests).'
        )
    return root / PLAN_DIR_NAME / 'local'


def get_temp_dir(subdir: str) -> Path:
    """Get temp directory under the repo-local .plan/temp/{subdir}.

    temp/ intentionally stays project-local (unlike runtime state under
    get_plan_dir()) so each worktree keeps its own isolated temp and the
    existing ``Write(.plan/**)`` permission keeps covering it.

    When PLAN_BASE_DIR is set (tests), it takes precedence and temp lands
    under that override directory for consistency with file_ops.get_temp_dir.
    """
    env_dir = os.environ.get('PLAN_BASE_DIR')
    if env_dir:
        return Path(env_dir) / 'temp' / subdir
    root = git_main_checkout_root()
    if root is not None:
        return root / '.plan' / 'temp' / subdir
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
    3. Script-relative walk via ``Path(__file__).resolve().parents[6]`` — anchors
       to the marketplace root that contains this very file. This is robust to
       cwd changes and worktrees because the script's own location is fixed
       relative to the repository layout.
    4. cwd-based discovery — the legacy fallback that probes ``Path.cwd()`` and
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

    # Branch 3: script-relative walk
    # marketplace_paths.py lives at:
    #   <root>/marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py
    # parents[6] is therefore the marketplace root that contains marketplace/bundles.
    try:
        script_anchor = Path(__file__).resolve().parents[6]
    except IndexError:
        script_anchor = None
    if script_anchor is not None:
        candidate = script_anchor / MARKETPLACE_BUNDLES_PATH
        if candidate.is_dir():
            return candidate

    # Branch 4: cwd-based discovery (legacy bootstrap fallback)
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
