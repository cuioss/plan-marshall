"""
Shared marketplace path resolution.

Provides centralized path discovery for marketplace bundles and plugin cache.
Used by generate_executor.py, scan-marketplace-inventory.py, and other scripts
that need to locate marketplace infrastructure.
"""

import os
import subprocess
from pathlib import Path

# Central configuration
PLAN_DIR_NAME = os.environ.get('PLAN_DIR_NAME', '.plan')
MARKETPLACE_BUNDLES_PATH = 'marketplace/bundles'
CLAUDE_DIR = '.claude'
PLUGIN_CACHE_SUBPATH = 'plugins/cache/plan-marshall'
GLOBAL_PLAN_MARSHALL_ROOT = Path.home() / '.plan-marshall'


def _git_main_checkout_root() -> Path | None:
    """Return the main git checkout root, or None if not in a git repo.

    Worktree-safe: uses --git-common-dir so worktrees resolve to the same
    main checkout as the primary working tree.
    """
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


def get_plan_dir() -> Path:
    """Get the plan-marshall base directory.

    Resolution order mirrors tools-file-ops.get_base_dir():
        1. PLAN_BASE_DIR environment variable (tests, user override).
        2. Per-project global directory ~/.plan-marshall/{project-name}/
           when inside a git repository.
        3. Repo-local .plan/ fallback (outside a git repo).
    """
    env_dir = os.environ.get('PLAN_BASE_DIR')
    if env_dir:
        return Path(env_dir)
    root = _git_main_checkout_root()
    if root is not None:
        return GLOBAL_PLAN_MARSHALL_ROOT / root.name
    return Path(PLAN_DIR_NAME)


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
    root = _git_main_checkout_root()
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
