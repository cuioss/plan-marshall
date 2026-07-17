# SPDX-License-Identifier: FSL-1.1-ALv2
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
the working directory is pinned there. The single deliberate exception mechanism
is ``resolve_main_anchored_path`` (below), which always resolves to the main
checkout for the bounded exception set — ``merge.lock``,
``run-configuration.json``, ``lessons-learned``, ``build-queue.json``,
``merge-queue.json``, ``orchestrator`` — every other resolution in the
codebase is cwd-relative.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# Central configuration
PLAN_DIR_NAME = os.environ.get('PLAN_DIR_NAME', '.plan')
MARKETPLACE_BUNDLES_PATH = 'marketplace/bundles'
# ``CLAUDE_DIR`` is retained ONLY as the global/project ``.claude`` settings
# anchor (Gap 1 territory) and to compose the Claude-default fallback roots
# below. It is no longer a project-local-SKILL or deployed-bundle discovery
# anchor — project-local-skill root resolution routes through
# ``get_project_skill_roots()`` and deployed-bundle discovery routes through
# ``get_bundle_cache_roots()``, both backed by the platform-runtime layout op.
CLAUDE_DIR = '.claude'
# ``PLUGIN_CACHE_SUBPATH`` is no longer a standalone Claude-only discovery
# anchor: live deployed-bundle discovery flows through the layout op
# (``get_bundle_cache_roots()``). It survives ONLY to compose the Claude-default
# fallback root used when no runtime is resolvable.
PLUGIN_CACHE_SUBPATH = 'plugins/cache/plan-marshall'

# Fallback project-local-skill root used when the platform-runtime layout op
# cannot be reached (no marshal.json, no marketplace tree, import failure).
# This is the Claude default — every supported environment that lacks a
# resolvable runtime is a Claude checkout.
_DEFAULT_SKILL_ROOTS = ('.claude/skills',)

# Per-process memoisation cache for the resolved project-local-skill roots.
# The active target is fixed by marshal.json for the lifetime of a process, so
# the layout op is invoked at most once — the documented mitigation for the
# subprocess/import hop on hot config/manifest paths.
_SKILL_ROOTS_CACHE: tuple[str, ...] | None = None

# Fallback deployed-bundle cache root used when the platform-runtime layout op
# cannot be reached. This is the Claude default — every supported environment
# that lacks a resolvable runtime is a Claude checkout.
_DEFAULT_BUNDLE_CACHE_ROOTS = (str(Path.home() / CLAUDE_DIR / PLUGIN_CACHE_SUBPATH),)

# Per-process memoisation cache for the resolved deployed-bundle cache roots.
_BUNDLE_CACHE_ROOTS_CACHE: tuple[str, ...] | None = None


# =============================================================================
# Project-local-skill root resolution (routes through platform-runtime)
# =============================================================================
# The single home for "where do project-local skills live per target" is the
# platform-runtime ``layout skill-roots`` operation. Consumers that scan for
# ``project:`` skills (finalize-steps, recipes, verify-steps, domain-attachable
# skills) MUST route through ``get_project_skill_roots()`` rather than
# hardcoding ``.claude/skills`` — that literal is now a Claude-only anchor owned
# by ``claude_runtime.py``.


def _read_runtime_target() -> str:
    """Read ``runtime.target`` from the nearest ``.plan/marshal.json``.

    Walks up from the current working directory; returns ``"claude"`` when the
    file is absent or malformed (every runtime-less environment is Claude).
    """
    cwd = Path.cwd().resolve()
    for parent in (cwd, *cwd.parents):
        candidate = parent / PLAN_DIR_NAME / 'marshal.json'
        if candidate.is_file():
            try:
                data = json.loads(candidate.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                return 'claude'
            if isinstance(data, dict):
                runtime = data.get('runtime')
                if isinstance(runtime, dict):
                    target = runtime.get('target')
                    if isinstance(target, str) and target:
                        return target
            return 'claude'
    return 'claude'


def _find_skills_root() -> Path | None:
    """Locate the marketplace ``skills/`` root by walking ancestors of this file.

    The root is the first ancestor named ``skills`` whose parent holds a
    ``.claude-plugin/plugin.json`` bundle manifest. Returns ``None`` when no
    such ancestor exists (e.g. running from the plugin cache).
    """
    for ancestor in Path(__file__).resolve().parents:
        if ancestor.name == 'skills' and (
            ancestor.parent / '.claude-plugin' / 'plugin.json'
        ).is_file():
            return ancestor
    return None


def _invoke_layout_op(target: str, method_name: str = 'layout_skill_roots') -> tuple[str, ...] | None:
    """Call a platform-runtime layout op for ``target`` and parse its ``roots``.

    Imports the platform-runtime scripts in-process (no executor dependency),
    instantiates the target's ``Runtime`` subclass, calls the op named by
    ``method_name`` (``layout_skill_roots`` or ``layout_bundle_cache_root``),
    and parses the ``roots`` list out of the op's TOON. Returns ``None`` on any
    resolution failure so the caller can fall back to the Claude default.
    """
    skills_root = _find_skills_root()
    if skills_root is None:
        return None

    for lib in ('ref-toon-format', 'platform-runtime'):
        lib_dir = str(skills_root / lib / 'scripts')
        if lib_dir not in sys.path:
            sys.path.append(lib_dir)

    try:
        from toon_parser import parse_toon

        if target == 'opencode':
            from opencode_runtime import OpenCodeRuntime

            runtime: Any = OpenCodeRuntime()
        else:
            from claude_runtime import ClaudeRuntime

            runtime = ClaudeRuntime()
        parsed = parse_toon(getattr(runtime, method_name)())
    except Exception:
        return None

    roots = parsed.get('roots') if isinstance(parsed, dict) else None
    if isinstance(roots, list) and roots:
        return tuple(str(r) for r in roots)
    return None


def get_project_skill_roots() -> tuple[str, ...]:
    """Return the project-local-skill discovery root(s) for the active target.

    Routes through the platform-runtime ``layout skill-roots`` op, memoised per
    process. On Claude this is ``('.claude/skills',)``; on OpenCode it is the
    multi-root list mirroring the executor's discovery order. Falls back to the
    Claude default when no runtime is resolvable (no marshal.json, no
    marketplace tree, or an import failure) so build/test environments without a
    configured runtime keep working.

    The returned roots are relative project-local paths (or ``~``-anchored
    user-global paths on OpenCode); callers resolve each against the relevant
    base directory and probe in list order (first match wins).
    """
    global _SKILL_ROOTS_CACHE
    if _SKILL_ROOTS_CACHE is not None:
        return _SKILL_ROOTS_CACHE

    roots = _invoke_layout_op(_read_runtime_target())
    _SKILL_ROOTS_CACHE = roots if roots is not None else _DEFAULT_SKILL_ROOTS
    return _SKILL_ROOTS_CACHE


def get_bundle_cache_roots() -> tuple[str, ...]:
    """Return the deployed-bundle (plugin-cache) discovery root(s) for the target.

    Routes through the platform-runtime ``layout bundle-cache-root`` op,
    memoised per process. On Claude this is the single
    ``~/.claude/plugins/cache/plan-marshall`` cache root; on OpenCode it is the
    ``~``-anchored user-global skill roots (OpenCode has no separate plugin
    cache). Falls back to the Claude default when no runtime is resolvable.

    The returned roots are absolute (``~``-expanded) paths; callers probe in
    list order (first existing match wins).
    """
    global _BUNDLE_CACHE_ROOTS_CACHE
    if _BUNDLE_CACHE_ROOTS_CACHE is not None:
        return _BUNDLE_CACHE_ROOTS_CACHE

    roots = _invoke_layout_op(_read_runtime_target(), 'layout_bundle_cache_root')
    _BUNDLE_CACHE_ROOTS_CACHE = roots if roots is not None else _DEFAULT_BUNDLE_CACHE_ROOTS
    return _BUNDLE_CACHE_ROOTS_CACHE


def _first_existing_bundle_cache_root() -> Path | None:
    """Return the first deployed-bundle cache root that exists on disk, else None."""
    for root in get_bundle_cache_roots():
        candidate = Path(root).expanduser()
        if candidate.is_dir():
            return candidate
    return None


def _resolve_skill_root(root: str, base: Path) -> Path:
    """Resolve a single layout-op root string against ``base``.

    ``~``-anchored roots (OpenCode user-global) and absolute roots resolve
    independently of ``base``; relative roots resolve under ``base``.
    """
    expanded = Path(root).expanduser()
    if expanded.is_absolute():
        return expanded
    return base / root


def resolve_project_skill_path(rel_subpath: str, base: Path | None = None) -> Path:
    """Resolve a project-local-skill subpath against the active target's roots.

    Probes each project-local-skill root in priority order (first existing
    match wins) for ``{root}/{rel_subpath}`` under ``base`` (defaulting to the
    current working directory). Returns the first path that exists on disk, or
    — when none exists — the path under the FIRST (highest-priority) root, so
    the caller gets a deterministic non-existent path to report.

    Args:
        rel_subpath: Subpath beneath a skill root, e.g.
            ``"sync-plugin-cache/SKILL.md"``.
        base: Project root to resolve relative roots against; defaults to cwd.

    Returns:
        The resolved path (first existing match, else the highest-priority
        candidate).
    """
    anchor = base if base is not None else Path.cwd()
    roots = get_project_skill_roots()
    first_candidate: Path | None = None
    for root in roots:
        candidate = _resolve_skill_root(root, anchor) / rel_subpath
        if first_candidate is None:
            first_candidate = candidate
        if candidate.exists():
            return candidate
    # No root matched; return the highest-priority candidate for reporting.
    assert first_candidate is not None  # get_project_skill_roots is never empty
    return first_candidate


def iter_project_skill_dirs(base: Path | None = None) -> list[Path]:
    """Return every project-local-skill directory across the active target's roots.

    Iterates each project-local-skill root (in priority order) and collects the
    immediate child directories of each root that exists. A skill name present
    under more than one root is yielded once per root in which it appears, in
    root priority order, so a higher-priority root's copy is encountered first.

    Args:
        base: Project root to resolve relative roots against; defaults to cwd.

    Returns:
        A list of skill directory ``Path`` objects (may be empty when no root
        exists on disk).
    """
    anchor = base if base is not None else Path.cwd()
    dirs: list[Path] = []
    for root in get_project_skill_roots():
        root_dir = _resolve_skill_root(root, anchor)
        if not root_dir.is_dir():
            continue
        for child in sorted(root_dir.iterdir()):
            if child.is_dir():
                dirs.append(child)
    return dirs


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
    import file_ops

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
    exactly: ``merge.lock``, ``run-configuration.json``, ``lessons-learned``,
    ``build-queue.json``, ``merge-queue.json``, ``orchestrator``.

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
        import file_ops

        return file_ops.get_base_dir() / subpath

    # 2. Production: resolve the MAIN checkout via the git common dir, which
    #    points at main's .git even from a linked worktree.
    main_root = _main_checkout_root()
    return main_root / PLAN_DIR_NAME / 'local' / subpath


def main_anchored_store_owns_bundle(bundle: str) -> bool:
    """Return whether the main-anchored store repo owns ``bundle``'s source tree.

    Repo ownership is the filesystem existence of
    ``{main_checkout_root}/marketplace/bundles/{bundle}`` — the store repo owns a
    bundle exactly when it carries that bundle's source directory. This is the
    ownership predicate the manage-lessons cross-repo wrong-store guard consults
    before allocating a lesson into the (ADR-002 main-anchored) lessons store.

    A test override short-circuits to ``True`` (guard-satisfied): when
    ``PLAN_BASE_DIR`` is set or ``file_ops`` carries a ``set_base_dir()``
    override, the override directory stands in for the main-checkout
    ``.plan/local`` and is not a real marketplace tree, so every override-based
    test keeps passing without tripping the guard.

    Args:
        bundle: Bundle name parsed from a ``bundle:skill[:script]`` component
            notation (e.g. ``plan-marshall``).

    Returns:
        ``True`` when an override is active OR the resolved main checkout owns the
        bundle's source directory; ``False`` otherwise.

    Raises:
        RuntimeError: in the production branch when git cannot resolve the main
            checkout (not a repo and no override set).
    """
    # Reject invalid bundle names before any path construction. An empty string
    # would resolve to the bundles directory itself (which exists, incorrectly
    # returning True), and pathlib silently discards the left-hand operand when
    # the right-hand side is an absolute path or contains a separator — either of
    # which could bypass the ownership guard. The current-/parent-directory
    # references '.' and '..' also resolve to existing directories (the bundles
    # dir itself and marketplace/ respectively), so they must be rejected too. A
    # valid bundle is a single simple directory name with no path separators and
    # no traversal segment.
    if not bundle or bundle in ('.', '..') or '/' in bundle or '\\' in bundle:
        return False

    if os.environ.get('PLAN_BASE_DIR') or _override_is_set():
        return True

    main_root = _main_checkout_root()
    return (main_root / MARKETPLACE_BUNDLES_PATH / bundle).is_dir()


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
    """Find ``marketplace/bundles`` directory using a three-step resolution order.

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

    return None


def get_plugin_cache_path() -> Path | None:
    """Get the deployed-bundle cache path if it exists.

    Routes through the platform-runtime ``layout bundle-cache-root`` op
    (memoised) and returns the first cache root that exists on disk, or
    ``None`` when none is materialized.
    """
    return _first_existing_bundle_cache_root()


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
            :func:`find_marketplace_path` for the full three-step resolution
            order (explicit param → ``PM_MARKETPLACE_ROOT`` env var →
            cwd walk-up).

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
        if explicit_anchor:
            # An explicit anchor short-circuits on the marketplace and raises
            # without cache fallback, preserving the explicit-anchor contract.
            marketplace = find_marketplace_path(marketplace_root=marketplace_root)
            if marketplace:
                return marketplace
            raise FileNotFoundError(
                f'Explicit marketplace anchor did not resolve to {MARKETPLACE_BUNDLES_PATH}. '
                f'Set --marketplace-root or PM_MARKETPLACE_ROOT to a directory containing '
                f'{MARKETPLACE_BUNDLES_PATH}.'
            )
        marketplace = find_marketplace_path(marketplace_root=marketplace_root)
        if marketplace:
            return marketplace
        cache = get_plugin_cache_path()
        if cache:
            return cache
        raise FileNotFoundError(
            f'Neither {MARKETPLACE_BUNDLES_PATH} nor a deployed-bundle cache '
            f'({", ".join(get_bundle_cache_roots())}) found. '
            f'Run from marketplace repo root or ensure the plugin is installed.'
        )

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
            f'Neither a deployed-bundle cache ({", ".join(get_bundle_cache_roots())}) '
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
        raise FileNotFoundError(
            f'Deployed-bundle cache not found: {", ".join(get_bundle_cache_roots())}'
        )

    if scope == 'global':
        return Path.home() / CLAUDE_DIR

    if scope == 'project':
        return Path.cwd() / CLAUDE_DIR

    raise ValueError(f'Invalid scope: {scope}')
