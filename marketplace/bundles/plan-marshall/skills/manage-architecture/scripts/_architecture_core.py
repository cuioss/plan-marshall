#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared utilities for architecture scripts.

Project architecture data lives under ``.plan/project-architecture/`` and is
split into two kinds of file:

- ``_project.json`` — top-level project metadata; the ``modules`` field is the
  index of "which modules exist". Persisted on disk by ``discover``.
- ``{module}/enriched.json`` — LLM-curated fields for one module
  (responsibility, purpose, key_packages, skills_by_profile, …). Persisted on
  disk; expensive to regenerate.

``derived.json`` (paths, packages, dependencies, file inventories) is
ephemeral — computed on demand by crawling the live worktree filesystem on
every read. It is NOT persisted to disk; ``load_module_derived`` always calls
``crawl_module_derived`` internally.

``_project.json`` and ``enriched.json`` are still written via the tmp-then-swap
pattern: callers build the new layout under ``project-architecture.tmp/`` and
call ``swap_data_dir(tmp_dir)`` which ``os.replace``s it onto the real path. A
forced interruption mid-write leaves either the old layout or the new layout
intact, never half-written state.
"""

import copy
import fnmatch
import json
import os
import shutil
from pathlib import Path
from typing import Any, NoReturn

from constants import (
    DIR_ARCHITECTURE,
    DIR_PER_MODULE_DERIVED,
    DIR_PER_MODULE_ENRICHED,
    FILE_PROJECT_META,
)

# Data sub-directory for architecture files (appended to base dir / project_dir)
_ARCHITECTURE_SUBDIR = DIR_ARCHITECTURE

# project-architecture/ lives under the *tracked* .plan/ directory in the repo,
# not the runtime base dir — it is checked in alongside marshal.json.
_TRACKED_CONFIG_SUBDIR = '.plan'

# Tmp suffix used for the atomic tmp+swap protocol on `discover --force`.
_TMP_SUFFIX = '.tmp'


# =============================================================================
# Exceptions
# =============================================================================


class ArchitectureError(Exception):
    """Base exception for architecture errors."""

    pass


class DataNotFoundError(ArchitectureError):
    """Raised when required data files are missing."""

    pass


class ModuleNotFoundInProjectError(ArchitectureError):
    """Raised when a module is not found in the data."""

    pass


class CommandNotFoundError(ArchitectureError):
    """Raised when a command is not found for a module."""

    pass


# =============================================================================
# Path Helpers
# =============================================================================


# Relative sub-path for project-architecture inside a repo checkout. Kept
# relative (not absolute) so callers can compose it with project_dir.
DATA_DIR = Path(_TRACKED_CONFIG_SUBDIR) / _ARCHITECTURE_SUBDIR


def get_data_dir(project_dir: str = '.') -> Path:
    """Get the project-architecture data directory path.

    project-architecture/ lives under the tracked .plan/ directory of the
    repository — the same location as marshal.json. The project_dir
    parameter identifies which repo root to look in (tests pass a tmp dir).
    """
    return Path(project_dir) / DATA_DIR


def get_tmp_data_dir(project_dir: str = '.') -> Path:
    """Get the tmp staging directory used for atomic ``discover --force`` writes.

    Resolves to ``{project_dir}/.plan/project-architecture.tmp/``. Callers build
    the new layout here, then call ``swap_data_dir(tmp_dir)`` to atomically
    replace the real directory.
    """
    real = get_data_dir(project_dir)
    return real.with_name(real.name + _TMP_SUFFIX)


def get_project_meta_path(project_dir: str = '.') -> Path:
    """Path to the top-level ``_project.json`` file."""
    return get_data_dir(project_dir) / FILE_PROJECT_META


def get_module_dir(module_name: str, project_dir: str = '.') -> Path:
    """Path to a module's directory under project-architecture."""
    return get_data_dir(project_dir) / module_name


def get_module_derived_path(module_name: str, project_dir: str = '.') -> Path:
    """Path to a module's ``derived.json``."""
    return get_module_dir(module_name, project_dir) / DIR_PER_MODULE_DERIVED


def get_module_enriched_path(module_name: str, project_dir: str = '.') -> Path:
    """Path to a module's ``enriched.json``."""
    return get_module_dir(module_name, project_dir) / DIR_PER_MODULE_ENRICHED


# =============================================================================
# Load / Save Operations
# =============================================================================


def _read_json(path: Path) -> dict[str, Any]:
    with open(path, encoding='utf-8') as f:
        result: dict[str, Any] = json.load(f)
        return result


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, sort_keys=True)


def load_project_meta(project_dir: str = '.') -> dict[str, Any]:
    """Load ``_project.json`` — the source of truth for module discovery.

    Raises:
        DataNotFoundError: If ``_project.json`` does not exist.
    """
    path = get_project_meta_path(project_dir)
    if not path.exists():
        raise DataNotFoundError(f"Project metadata not found. Run 'architecture.py discover' first. Expected: {path}")
    return _read_json(path)


def save_project_meta(meta: dict[str, Any], project_dir: str = '.') -> Path:
    """Save ``_project.json``."""
    path = get_project_meta_path(project_dir)
    _write_json(path, meta)
    return path


# Process-lifetime memo for ``crawl_all_modules``. Keyed by the resolved
# absolute ``project_dir`` string. Each value is the canonical (post-processed)
# module map for that project; callers receive a deep copy so a mutation by one
# caller never corrupts the cached object another caller will read.
#
# The crawl shells out to the build tools (e.g. Maven runs ``help:all-profiles
# dependency:tree`` per module), so a single ``architecture resolve`` against a
# multi-module repo would otherwise pay that cost once per ``load_module_derived``
# call — O(N²) subprocess invocations. Memoizing the crawl collapses that to one
# crawl per project per process. The cache is invalidated by
# :func:`invalidate_crawl_cache`, which ``swap_data_dir`` (the ``discover
# --force`` path) calls so a forced refresh re-crawls.
_CRAWL_CACHE: dict[str, dict[str, dict[str, Any]]] = {}


def invalidate_crawl_cache(project_dir: str | None = None) -> None:
    """Clear the ``crawl_all_modules`` memo for one project, or the whole cache.

    Args:
        project_dir: When given, only the entry for this project's resolved
            absolute path is dropped. When ``None``, the entire cache is
            cleared. ``swap_data_dir`` (the ``discover --force`` atomic-swap
            path) calls this so a forced refresh re-crawls instead of returning
            stale memoized data.
    """
    if project_dir is None:
        _CRAWL_CACHE.clear()
        return
    key = str(Path(project_dir).resolve())
    _CRAWL_CACHE.pop(key, None)


def crawl_all_modules(project_dir: str = '.') -> dict[str, dict[str, Any]]:
    """Compute per-module derived data for every module by crawling the worktree.

    Runs the extension discovery pipeline against ``project_dir`` and applies
    the in-memory ``_post_process_files`` pass that populates each module's
    ``files`` inventory. The result is the same shape ``derived.json`` would
    have on disk — a dict keyed by module name, each value being one module's
    derived payload.

    The crawl is rooted at ``Path(project_dir)``; it never falls back to
    ``Path.cwd()`` or ``git rev-parse --show-toplevel``. This is what gives
    ``--project-dir <worktree>`` callers worktree-correct results.

    Memoization: the crawl is expensive (it shells out to the build tools — e.g.
    Maven runs ``help:all-profiles dependency:tree`` per module). The result is
    memoized in :data:`_CRAWL_CACHE` keyed by the resolved absolute
    ``project_dir`` so repeated calls within one process — the common case for a
    single ``architecture resolve`` that touches several modules — crawl only
    once. Each call returns a deep copy of the cached map so a caller that
    mutates its result (e.g. ``_post_process_files`` runs in-place on the
    discovery output) cannot corrupt the shared cache for the next caller.
    :func:`invalidate_crawl_cache` clears the memo on forced refresh.

    The import of ``_post_process_files`` from ``_cmd_manage`` is deferred to
    call time to avoid the circular-import cycle (``_cmd_manage`` already
    imports from ``_architecture_core`` at module top).

    Synthetic-project fallback: when ``discover_project_modules`` yields no
    modules (e.g. unit-test fixtures that build a fake project tree under a
    tmp directory and seed ``.plan/project-architecture/<module>/derived.json``
    directly), fall back to reading any per-module ``derived.json`` files
    that already exist under ``project_dir``. This lets fixture-driven tests
    continue to seed module data via ``save_module_derived`` without having
    to also stage the build files an extension discoverer would look for.
    Production worktrees (which always have at least one real module) never
    hit this path.
    """
    project_path = Path(project_dir).resolve()
    cache_key = str(project_path)
    cached = _CRAWL_CACHE.get(cache_key)
    if cached is not None:
        return copy.deepcopy(cached)

    computed = _compute_all_modules(project_dir, project_path)
    _CRAWL_CACHE[cache_key] = computed
    return copy.deepcopy(computed)


def _compute_all_modules(project_dir: str, project_path: Path) -> dict[str, dict[str, Any]]:
    """Compute the canonical module map for ``project_dir`` (the cache-miss path).

    Separated from :func:`crawl_all_modules` so the memoization wrapper stays a
    thin cache lookup. Returns the post-processed module map; the caller stores
    it in :data:`_CRAWL_CACHE` and hands out deep copies.
    """
    # Local imports — deliberately deferred to function-call time.
    #
    # ``_post_process_files`` lives in ``_cmd_manage`` because it depends on
    # several file-classification helpers and constants co-located there. Moving
    # those ~300 lines to _architecture_core would invert the layering in the
    # opposite direction. The deferred import is the accepted Python idiom for
    # breaking circular-import cycles: ``_cmd_manage`` imports from
    # ``_architecture_core`` at module level, so a top-level import here would
    # create a true import-time cycle. Deferring to call time avoids the cycle
    # without relocating the file-processing logic.
    #
    # ``extension_discovery`` is kept local for the same reason — it is an
    # extension-API module that should not become a module-level dependency of
    # this low-level utility module.
    from _cmd_manage import _post_process_files
    from extension_discovery import discover_project_modules

    result = discover_project_modules(project_path)
    modules: dict[str, dict[str, Any]] = result.get('modules', {}) or {}
    if not modules:
        # Synthetic-project fallback (test-fixture seam — see docstring).
        # On-disk derived.json already contains the post-processed shape, so
        # do NOT run ``_post_process_files`` again over it — that would
        # overwrite the seeded payload with an empty filesystem walk.
        return _read_disk_derived(project_dir)
    _post_process_files(modules, project_dir)
    return modules


def _read_disk_derived(project_dir: str) -> dict[str, dict[str, Any]]:
    """Read any per-module ``derived.json`` files already on disk.

    Synthetic-project fallback used by ``crawl_all_modules`` when the
    extension discovery pipeline returns no modules — typically a unit-test
    fixture that seeded ``derived.json`` files but did not include real
    build files the discoverer would pick up. Production worktrees never
    hit this path because they always have at least one real module.

    Under the on-demand crawl model ``_project.json["modules"]`` is no
    longer the gatekeeper for what ``iter_modules`` surfaces: every
    per-module directory containing a ``derived.json`` is returned. This
    matches the live-crawl semantic — what is on disk is what exists.
    Callers that need the curated project-meta view should read
    ``_project.json`` directly via ``load_project_meta``.
    """
    data_dir = get_data_dir(project_dir)
    if not data_dir.exists() or not data_dir.is_dir():
        return {}

    out: dict[str, dict[str, Any]] = {}
    for entry in sorted(data_dir.iterdir()):
        if not entry.is_dir():
            continue
        derived_path = entry / 'derived.json'
        if derived_path.is_file():
            try:
                out[entry.name] = _read_json(derived_path)
            except (OSError, ValueError):
                continue
    return out


def crawl_module_derived(module_name: str, project_dir: str = '.') -> dict[str, Any]:
    """Compute one module's derived payload by crawling the worktree on demand.

    Convenience wrapper around ``crawl_all_modules`` that returns a single
    module's entry. Raises ``ModuleNotFoundInProjectError`` when the requested
    module is absent from the live crawl — callers that want a stable "empty
    dict" shape should consult ``crawl_all_modules`` directly.
    """
    modules = crawl_all_modules(project_dir)
    if module_name not in modules:
        raise ModuleNotFoundInProjectError(f'Module not found in live crawl: {module_name}')
    return modules[module_name]


def load_module_derived(module_name: str, project_dir: str = '.') -> dict[str, Any]:
    """Return one module's derived payload by crawling the worktree.

    Backwards-compatible alias for ``crawl_module_derived``: kept so existing
    callers ("load derived for module X") continue to work without churn.

    Raises:
        DataNotFoundError: If the module is absent from the live crawl. The
            caller can disambiguate "module unknown" vs "module present but
            has no derived fields" by consulting ``iter_modules``.
    """
    try:
        return crawl_module_derived(module_name, project_dir)
    except ModuleNotFoundInProjectError as err:
        # Surface as DataNotFoundError to preserve the legacy contract that
        # callers can ``except DataNotFoundError`` after a discover-not-yet-run
        # condition. The discriminator is still useful because the legacy
        # ``derived.json missing`` failure mode collapses into the same shape.
        raise DataNotFoundError(
            f"Module '{module_name}' not present in live filesystem crawl of '{project_dir}'. "
            "Run 'architecture.py discover' to refresh the module index, or verify the module exists."
        ) from err


def save_module_derived(module_name: str, data: dict[str, Any], project_dir: str = '.') -> Path:
    """Write a ``derived.json`` file to disk — snapshot-fixture writer only.

    Under the on-demand crawl model production reads never load
    ``{module}/derived.json`` from disk; ``crawl_module_derived`` computes
    it in-memory on every request. This writer is retained for the single
    legitimate use case: building file-based snapshot fixtures consumed by
    ``cmd_diff_modules`` (which still reads the snapshot side from disk
    per deliverable 4 of plan ``architecture-files-on-demand``). Tests and
    snapshot tooling are the only callers.

    Production code MUST NOT use this writer to refresh the current-project
    derived data — derived data is ephemeral.

    Drops the crawl memo for ``project_dir``: this writer is the disk-fallback
    seam (and snapshot-fixture writer), so a write changes what the next crawl
    of that project should observe. Invalidating keeps the fallback path
    coherent when a test seeds, crawls, then re-seeds the same tmp project.
    """
    path = get_module_derived_path(module_name, project_dir)
    _write_json(path, data)
    invalidate_crawl_cache(project_dir)
    return path


def load_module_enriched(module_name: str, project_dir: str = '.') -> dict[str, Any]:
    """Load one module's ``enriched.json``.

    Raises:
        DataNotFoundError: If the file does not exist.
    """
    path = get_module_enriched_path(module_name, project_dir)
    if not path.exists():
        raise DataNotFoundError(
            f"Enrichment data not found for module '{module_name}'. Run 'architecture.py init' first. Expected: {path}"
        )
    return _read_json(path)


def load_module_enriched_or_empty(module_name: str, project_dir: str = '.') -> dict[str, Any]:
    """Load one module's ``enriched.json`` or return an empty dict.

    Use this when callers want to tolerate missing enrichment (e.g. read paths
    after ``discover`` but before ``init``).
    """
    path = get_module_enriched_path(module_name, project_dir)
    if not path.exists():
        return {}
    return _read_json(path)


def save_module_enriched(module_name: str, data: dict[str, Any], project_dir: str = '.') -> Path:
    """Save one module's ``enriched.json``."""
    path = get_module_enriched_path(module_name, project_dir)
    _write_json(path, data)
    return path


def iter_modules(project_dir: str = '.') -> list[str]:
    """Iterate module names by crawling the live worktree filesystem.

    The crawl is the canonical answer to "which modules exist" — it walks the
    extension discovery pipeline against ``project_dir`` so callers always
    see the modules that currently exist on disk, never a stale snapshot.

    Returns:
        Sorted list of module names. Empty list when the crawl yields no
        modules (e.g. a freshly-initialised greenfield project).
    """
    return sorted(crawl_all_modules(project_dir).keys())


def swap_data_dir(tmp_dir: Path, project_dir: str = '.') -> Path:
    """Atomically replace ``project-architecture/`` with the contents of ``tmp_dir``.

    Implements the tmp-then-swap pattern that gives ``discover --force`` its
    atomicity guarantee: callers build the entire new layout under ``tmp_dir``
    (typically the path returned by ``get_tmp_data_dir()``), then this function
    swaps it into place using a backup-rename so the data directory is never
    absent on disk:

        1. Clean any stale ``project-architecture.old/`` left over from a
           previously interrupted swap.
        2. Rename the existing ``project-architecture/`` to
           ``project-architecture.old/`` (atomic on the same filesystem).
        3. ``os.replace`` ``tmp_dir`` onto the real path.
        4. Delete the backup.

    Compared to the older rmtree-then-replace flow, this closes the window where
    the data directory does not exist on disk: between steps 2 and 3 the backup
    is the canonical layout, and the rename in step 2 is atomic. A forced
    interruption either before, during, or after the rename leaves the project
    in a consistent state — the next ``discover --force`` will pick up the
    leftover ``.old/`` and clean it in step 1.

    Args:
        tmp_dir: Source directory containing the new layout. Must exist.
        project_dir: Project directory path.

    Returns:
        The final ``project-architecture/`` path.

    Raises:
        FileNotFoundError: If ``tmp_dir`` does not exist.
    """
    tmp_dir = Path(tmp_dir)
    if not tmp_dir.exists():
        raise FileNotFoundError(f'tmp data dir does not exist: {tmp_dir}')

    real = get_data_dir(project_dir)
    real.parent.mkdir(parents=True, exist_ok=True)

    backup = real.with_name(real.name + '.old')

    # Step 1: Clean any stale backup left over from a previously interrupted swap.
    if backup.exists():
        shutil.rmtree(backup)

    # Step 2: Move the current layout aside (atomic rename on same filesystem).
    if real.exists():
        os.replace(real, backup)

    # Step 3: Move the staged layout into place.
    os.replace(tmp_dir, real)

    # Step 4: Delete the backup now that the new layout is live.
    if backup.exists():
        shutil.rmtree(backup)

    # A forced refresh (``discover --force``) just replaced the on-disk layout;
    # drop the memoized crawl for this project so the next read re-crawls
    # against the freshly-swapped tree rather than returning a stale snapshot.
    invalidate_crawl_cache(project_dir)

    return real


# =============================================================================
# Module Helpers
# =============================================================================


def get_root_module(project_dir: str = '.') -> str | None:
    """Get the root module name (the module sitting at the project root).

    Determined by:
        1. Module whose ``paths.module`` is ``"."`` or empty (project root).
        2. Fallback: first module in ``_project.json``'s ``modules`` index.

    Returns:
        Module name, or None if the project has no modules.
    """
    try:
        modules = crawl_all_modules(project_dir)
    except DataNotFoundError:
        return None
    if not modules:
        return None
    # Single crawl, then iterate the returned map directly — no per-module
    # ``load_module_derived`` re-crawl. ``crawl_all_modules`` is memoized so the
    # first reader pays for the crawl and this iteration is over the cached map.
    # Iterate names in sorted order so the fallback (first module) is
    # deterministic, matching the historical ``iter_modules`` contract.
    for name in sorted(modules.keys()):
        data = modules[name]
        paths = data.get('paths', {})
        module_path = paths.get('module', '')
        if module_path in ('.', ''):
            return name
    return sorted(modules.keys())[0]


def merge_module_data(module_name: str, project_dir: str = '.') -> dict[str, Any]:
    """Merge derived and enriched data for a single module.

    Loads ``{module}/derived.json`` and ``{module}/enriched.json`` (the latter
    treated as empty when missing), then overlays enriched fields onto derived
    data. Enriched values that are falsy do NOT overwrite derived values — this
    matches the legacy semantics that downstream callers depend on.

    Raises:
        DataNotFoundError: If ``derived.json`` is missing for the named module.
    """
    derived = load_module_derived(module_name, project_dir)
    enriched = load_module_enriched_or_empty(module_name, project_dir)

    merged = dict(derived)
    for key, value in enriched.items():
        if value:
            merged[key] = value
    return merged


# =============================================================================
# Build-Map Derivation (derive-verification)
# =============================================================================
#
# The deriver is the SINGLE deterministic consumer of the build_map contract.
# It reads the build_map from marshal.json (build.map, single
# source of truth — no override layer),
# classifies each changed-artifact path to a build_class (longest-glob-wins),
# resolves the owning module per path, and lets the CLI handler emit the
# architecture-resolved verification command set per the build_class →
# command table. This core carries the pure, project_dir-honoring half:
# build_map loading, glob classification, and module resolution. Command
# resolution + execution-tier augmentation live in the ``_cmd_client`` handler
# (it already owns ``resolve_command`` and the tier helpers).


def load_merged_build_map(project_dir: str = '.') -> dict[str, list[dict[str, str]]]:
    """Return the effective ``build.map`` for ``project_dir``.

    Reads ``{project_dir}/.plan/marshal.json`` directly (project_dir-honoring,
    mirroring the ``ext_defaults_*`` accessors) and delegates to the
    ``manage-config`` reader so the deriver consumes the exact same effective
    map the user sees via ``manage-config build-map read`` — the build_map at
    the top-level ``build.map`` (single source of truth, no override layer).

    Args:
        project_dir: Project directory containing ``.plan/marshal.json``.

    Returns:
        The ``{domain: [{glob, role, build_class}]}`` dict. An empty dict when
        the marshal.json is absent or carries no ``build.map``.
    """
    marshal_path = Path(project_dir) / '.plan' / 'marshal.json'
    if not marshal_path.exists():
        return {}
    try:
        config = json.loads(marshal_path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return _merge_build_map(config)


def _merge_build_map(config: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    """Delegate to ``manage-config`` ``merge_build_map`` (single source of read logic).

    The build_map read (from ``build.map``, single source of
    truth — no override layer) is owned by ``manage-config``'s
    ``_config_core.merge_build_map``. Importing it keeps one implementation
    rather than re-deriving it here. The ``manage-config`` scripts dir is added
    to ``sys.path`` lazily so the manage-architecture skill still imports
    cleanly when loaded in isolation. Both the import failure and the
    fail-closed ``BuildMapMissingError`` (absent build_map) degrade to "no
    build_map" (an empty dict) rather than crashing the deriver — the deriver's
    contract is "empty map when absent", not "raise".
    """
    import sys

    from marketplace_bundles import (
        resolve_bundle_path,
        resolve_bundles_root,
    )

    bundles_root = resolve_bundles_root(Path(__file__))
    config_scripts_dir = str(resolve_bundle_path(bundles_root, 'plan-marshall', 'skills/manage-config/scripts'))
    if config_scripts_dir not in sys.path:
        sys.path.insert(0, config_scripts_dir)
    try:
        from _config_core import BuildMapMissingError, merge_build_map
    except ImportError:
        return {}
    try:
        return merge_build_map(config)
    except BuildMapMissingError:
        return {}


def classify_changed_path(path: str, merged_build_map: dict[str, list[dict[str, str]]]) -> str | None:
    """Classify a single changed-artifact path to a build_class (longest-glob-wins).

    Matches ``path`` against every ``{glob, role, build_class}`` entry across
    all domains of ``merged_build_map`` using ``fnmatch`` — the same matcher the
    aggregator uses. When more than one glob matches, the longest glob wins
    (the deterministic "longest-glob-wins" precedence, with the glob string
    itself as the alphabetical tie-break). The build_map does not persist the
    per-entry integer specificity, so glob length is the specificity proxy.

    Args:
        path: A changed-artifact path (full repo-relative path).
        merged_build_map: The merged map from :func:`load_merged_build_map`.

    Returns:
        The winning ``build_class`` string, or ``None`` when no glob matches
        (the path is unclaimed — it derives no build).
    """
    matches: list[tuple[int, str, str]] = []  # (glob length, glob, build_class)
    for entries in merged_build_map.values():
        for entry in entries:
            glob = entry.get('glob')
            build_class = entry.get('build_class')
            if not glob or not build_class:
                continue
            if fnmatch.fnmatch(path, glob):
                matches.append((len(glob), glob, build_class))
    if not matches:
        return None
    # Longest glob wins; alphabetical glob tie-break (stable, deterministic).
    matches.sort(key=lambda item: (-item[0], item[1]))
    return matches[0][2]


# Project-local path-prefix map: prefixes that sit outside every module's
# declared ``paths.sources`` / ``paths.tests`` but still belong to a known
# module. The meta-project's own ``.claude/skills/**`` tree (project-local
# skills plus their tests under ``test/plan-marshall/**``) is owned by the
# ``plan-marshall`` module — the operator-confirmed owner. Each mapping is
# guarded by module existence at resolution time, so consumer projects that
# have no ``plan-marshall`` module are unaffected.
_PROJECT_LOCAL_PREFIX_MAP: tuple[tuple[str, str], ...] = (('.claude/skills', 'plan-marshall'),)


def project_local_module_for_path(path: str, module_names: list[str]) -> str | None:
    """Map a project-local path prefix to its owning module.

    Handles paths that sit outside every module's declared ``paths.sources`` /
    ``paths.tests`` but still belong to a known module — currently the
    meta-project's ``.claude/skills/**`` tree, owned by ``plan-marshall``. The
    mapping only fires when the target module is present in ``module_names``, so
    a consumer project without that module falls through to ``None``.

    Args:
        path: A repo-relative path.
        module_names: The list of modules known to the project.

    Returns:
        The owning module name when a project-local prefix contains ``path`` and
        that module exists, else ``None``.
    """
    for prefix, module in _PROJECT_LOCAL_PREFIX_MAP:
        normalized = prefix.rstrip('/')
        if path == normalized or path.startswith(normalized + '/'):
            return module if module in module_names else None
    return None


def longest_containing_prefix(path: str, paths: dict[str, Any]) -> int | None:
    """Longest ``paths.sources ∪ paths.tests`` directory prefix that contains ``path``.

    Returns the length of the longest source/test prefix directory that is an
    ancestor of (or equal to) ``path``, or ``None`` when none contains it.
    Root-ish prefixes (``''`` / ``'.'``) are skipped — they add no specificity
    over the root-module fallback. The union of ``paths.tests`` with
    ``paths.sources`` is deliberate: the resolver must consult ``paths.tests``,
    not ``paths.sources`` alone, so a ``test/**`` path resolves to its owning
    module instead of falling through to the project root.

    Args:
        path: A repo-relative path.
        paths: A module's ``paths`` block (``sources`` / ``tests`` are lists of
            repo-relative directory prefixes).

    Returns:
        The length of the longest containing source/test prefix, or ``None``.
    """
    best: int | None = None
    for key in ('sources', 'tests'):
        entries = paths.get(key) or []
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, str):
                continue
            normalized = entry.strip().rstrip('/')
            if normalized in ('', '.'):
                continue
            if path == normalized or path.startswith(normalized + '/'):
                length = len(normalized)
                if best is None or length > best:
                    best = length
    return best


def resolve_module_for_path(path: str, project_dir: str = '.') -> str | None:
    """Resolve the owning module for a changed path by longest containing prefix.

    Unlike the ``which-module`` reader (which prefers exact membership in a
    module's crawled files inventory), this resolver matches the changed path by
    directory-prefix containment and returns the most specific (longest-prefix)
    module. This tolerates changed artifacts that are newly-created files not yet
    in the crawled inventory — the deriver runs at plan time over a task's
    declared ``steps[].target`` list, which may include files that do not yet
    exist.

    Specificity is the longest of two signals per module: the ``paths.module``
    prefix and the ``paths.sources ∪ paths.tests`` containment prefix (the union
    ensures a ``test/**`` path resolves to its owning module rather than the
    project root). Resolution order:

        1. Most-specific containing module (prefix length > 0).
        2. Project-local prefix map (``.claude/skills/** → plan-marshall``).
        3. Root module (the length-0 fallback), when present.

    Args:
        path: A changed-artifact path (full repo-relative path).
        project_dir: Project directory path.

    Returns:
        The owning module name, or ``None`` when no module contains ``path`` and
        the project has no root module.
    """
    try:
        module_names = iter_modules(project_dir)
    except DataNotFoundError:
        return None

    best_specific: tuple[int, str] | None = None  # (prefix length > 0, module name)
    root_fallback: str | None = None
    for name in module_names:
        try:
            derived = load_module_derived(name, project_dir)
        except DataNotFoundError:
            continue
        paths = derived.get('paths') or {}
        module_path = (paths.get('module') or '').strip()

        if module_path in ('.', ''):
            # Root module: the length-0 fallback (matches anything).
            if root_fallback is None or name < root_fallback:
                root_fallback = name
            module_prefix_len: int | None = None
        elif path == module_path.rstrip('/') or path.startswith(module_path.rstrip('/') + '/'):
            module_prefix_len = len(module_path.rstrip('/'))
        else:
            module_prefix_len = None

        # sources ∪ tests containment.
        containment_len = longest_containing_prefix(path, paths)

        candidate_len = module_prefix_len
        if containment_len is not None and (candidate_len is None or containment_len > candidate_len):
            candidate_len = containment_len
        if candidate_len is None:
            continue
        candidate = (candidate_len, name)
        if best_specific is None or candidate[0] > best_specific[0] or (
            candidate[0] == best_specific[0] and candidate[1] < best_specific[1]
        ):
            best_specific = candidate

    if best_specific is not None:
        return best_specific[1]
    project_local = project_local_module_for_path(path, module_names)
    if project_local is not None:
        return project_local
    return root_fallback


# =============================================================================
# Error Handling
# =============================================================================


def error_exit(message: str, context: dict[str, Any] | None = None) -> NoReturn:
    """Print error in TOON format and raise ArchitectureError.

    CLI-boundary helper — only call from command handlers, not library functions.
    For library code, raise ArchitectureError or DataNotFoundError instead.
    """
    from toon_parser import serialize_toon

    error_data: dict[str, Any] = {'status': 'error', 'error': 'architecture_error', 'message': message}
    if context:
        error_data.update(context)
    print(serialize_toon(error_data))
    raise ArchitectureError(message)


def error_module_not_found(module_name: str, available: list[str]) -> NoReturn:
    error_exit('Module not found', {'module': module_name, 'available': available})


def error_command_not_found(module_name: str, command_name: str, available: list[str]) -> NoReturn:
    error_exit('Command not found', {'module': module_name, 'command': command_name, 'available': available})


def error_data_not_found(expected_file: str, resolution: str) -> NoReturn:
    error_exit('Data not found', {'expected_file': expected_file, 'resolution': resolution})


def require_project_meta(project_dir: str = '.') -> dict[str, Any]:
    """Load ``_project.json`` or exit with a structured error.

    Convenience wrapper that replaces repeated try/except DataNotFoundError
    blocks in CLI handlers. On success it returns the loaded dict; on failure
    it prints the standard error message and raises ArchitectureError.
    """
    try:
        return load_project_meta(project_dir)
    except DataNotFoundError:
        error_data_not_found(
            str(get_project_meta_path(project_dir)),
            "Run 'architecture.py discover' first",
        )
        raise  # unreachable – error_data_not_found raises ArchitectureError


def handle_module_not_found(module_name: str, project_dir: str) -> int:
    """Print module-not-found error with available modules list and return 1."""
    from toon_parser import serialize_toon

    try:
        modules = iter_modules(project_dir)
    except Exception:
        modules = []

    error_data: dict[str, Any] = {
        'status': 'error',
        'error': 'architecture_error',
        'message': 'Module not found',
        'module': module_name,
        'available': modules,
    }
    print(serialize_toon(error_data))
    return 1


def error_result_module_not_found(module_name: str, available: list[str]) -> dict[str, Any]:
    return {
        'status': 'error',
        'error': 'architecture_error',
        'message': 'Module not found',
        'module': module_name,
        'available': available,
    }


def error_result_command_not_found(module_name: str, command_name: str, available: list[str]) -> dict[str, Any]:
    return {
        'status': 'error',
        'error': 'architecture_error',
        'message': 'Command not found',
        'module': module_name,
        'command': command_name,
        'available': available,
    }


def require_project_meta_result(project_dir: str = '.') -> dict[str, Any]:
    """Return ``_project.json`` not found error dict."""
    return {
        'status': 'error',
        'error': 'data_not_found',
        'expected_file': str(get_project_meta_path(project_dir)),
        'resolution': "Run 'architecture.py discover' first",
    }


def handle_module_not_found_result(module_name: str, project_dir: str) -> dict[str, Any]:
    """Return module-not-found error dict with available modules list."""
    try:
        modules = iter_modules(project_dir)
    except Exception:
        modules = []

    return {
        'status': 'error',
        'error': 'architecture_error',
        'message': 'Module not found',
        'module': module_name,
        'available': modules,
    }


def print_skills_by_profile(skills_by_profile: dict[str, Any]) -> None:
    """Print skills_by_profile in TOON format."""
    print('skills_by_profile:')
    for profile, profile_data in skills_by_profile.items():
        print(f'  {profile}:')
        defaults = profile_data.get('defaults', [])
        optionals = profile_data.get('optionals', [])
        if defaults:
            print(f'    defaults[{len(defaults)}]{{skill,description}}:')
            for entry in defaults:
                if isinstance(entry, dict):
                    skill = entry.get('skill', '')
                    desc = entry.get('description', '')
                    print(f'      - {skill},"{desc}"')
                else:
                    print(f'      - {entry}')
        if optionals:
            print(f'    optionals[{len(optionals)}]{{skill,description}}:')
            for entry in optionals:
                if isinstance(entry, dict):
                    skill = entry.get('skill', '')
                    desc = entry.get('description', '')
                    print(f'      - {skill},"{desc}"')
                else:
                    print(f'      - {entry}')
