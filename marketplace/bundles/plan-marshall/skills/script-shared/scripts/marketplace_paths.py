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


def find_marketplace_path(script_bundles_dir: Path | None = None) -> Path | None:
    """Find marketplace/bundles directory.

    When ``script_bundles_dir`` is provided, it is used directly — the caller
    has resolved the path from ``__file__`` (typically 5 levels up from the
    script) so it is correct regardless of the current working directory.

    When ``script_bundles_dir`` is ``None`` (e.g. the script lives outside
    the marketplace source tree, such as when executed from the plugin
    cache), fall back to cwd-based discovery.

    Args:
        script_bundles_dir: Script-relative bundles path resolved from
                            ``__file__``. Preferred when available.
    """
    if script_bundles_dir and script_bundles_dir.is_dir():
        return script_bundles_dir
    if (Path.cwd() / MARKETPLACE_BUNDLES_PATH).is_dir():
        return Path.cwd() / MARKETPLACE_BUNDLES_PATH
    if (Path.cwd().parent / MARKETPLACE_BUNDLES_PATH).is_dir():
        return Path.cwd().parent / MARKETPLACE_BUNDLES_PATH
    return None


def get_plugin_cache_path() -> Path | None:
    """Get plugin cache path if it exists."""
    cache_path = Path.home() / CLAUDE_DIR / PLUGIN_CACHE_SUBPATH
    return cache_path if cache_path.is_dir() else None


def get_base_path(scope: str = 'auto', script_bundles_dir: Path | None = None) -> Path:
    """Determine base path based on scope.

    Args:
        scope: Discovery scope. Valid values:
            - 'auto': tries marketplace first, then plugin-cache (default)
            - 'marketplace': force marketplace context
            - 'plugin-cache': force plugin cache context
            - 'cache-first': tries plugin-cache first, then marketplace (executor default)
            - 'global': ~/.claude
            - 'project': ./.claude
        script_bundles_dir: Optional script-relative bundles path for fallback

    Returns:
        Path to the bundles directory (or .claude for global/project scope)

    Raises:
        FileNotFoundError: If requested context is not available
        ValueError: If scope is invalid
    """
    if scope == 'auto':
        marketplace = find_marketplace_path(script_bundles_dir)
        if marketplace:
            return marketplace
        cache = get_plugin_cache_path()
        if cache:
            return cache
        raise FileNotFoundError(
            f'Neither {MARKETPLACE_BUNDLES_PATH} nor plugin cache found. '
            f'Run from marketplace repo or ensure plugin is installed.'
        )

    if scope == 'cache-first':
        cache = get_plugin_cache_path()
        if cache:
            return cache
        marketplace = find_marketplace_path(script_bundles_dir)
        if marketplace:
            return marketplace
        raise FileNotFoundError(
            f'Neither plugin cache ({Path.home() / CLAUDE_DIR / PLUGIN_CACHE_SUBPATH}) '
            f'nor {MARKETPLACE_BUNDLES_PATH} found. '
            f'Ensure plugin is installed or run from marketplace repo.'
        )

    if scope == 'marketplace':
        marketplace = find_marketplace_path(script_bundles_dir)
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
