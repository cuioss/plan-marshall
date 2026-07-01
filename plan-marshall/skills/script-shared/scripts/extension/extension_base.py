#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Public API for extension.py implementations.

This module is the single public interface for domain bundle extensions.

Provides:
    - ExtensionBase: Abstract base class for extensions (Axis-A: skill-loading)
    - BuildExtensionBase: Abstract base class for build-system-owned
      file-to-build extensions (Axis-B: classify_globs / classify_paths /
      classify_path_specificity / classify_build_class)
    - Canonical command constants (re-exported from _extension_constants):
      CMD_*, CANONICAL_COMMANDS, PROFILE_PATTERNS, APPLICABLE_PROFILES
    - Build-class vocabulary (re-exported from _extension_constants):
      BUILD_CLASSES, BUILD_CLASS_*

Module discovery utilities (discover_descriptors, build_module_base, find_readme,
count_source_files, discover_packages, discover_js_sources, discover_sources,
ModuleBase, ModulePaths) are available via direct import from _build_discover.
"""

import fnmatch
import functools
import subprocess
from abc import ABC, abstractmethod
from posixpath import basename

# Re-export build vocabulary constants from private implementation.
from _extension_constants import (  # noqa: F401 — re-exported for backward compat
    ALL_CANONICAL_COMMANDS,
    BUILD_CLASS_BUILD_CONFIG_FULL,
    BUILD_CLASS_NONE,
    BUILD_CLASS_PROD_COMPILE,
    BUILD_CLASS_TEST_RUN,
    BUILD_CLASSES,
    BUILD_MAP_ROLES,
    CANONICAL_COMMANDS,
    CMD_ARCH_GATE,
    CMD_BENCHMARK,
    CMD_CLEAN,
    CMD_CLEAN_INSTALL,
    CMD_COMPILE,
    CMD_COVERAGE,
    CMD_INSTALL,
    CMD_INTEGRATION_TESTS,
    CMD_MODULE_TESTS,
    CMD_PACKAGE,
    CMD_QUALITY_GATE,
    CMD_TEST_COMPILE,
    CMD_VERIFY,
    PROFILE_PATTERNS,
    ROLE_CONFIG,
    ROLE_PRODUCTION,
    ROLE_TEST,
)
from _extension_constants import (
    APPLICABLE_PROFILES as _APPLICABLE_PROFILES,
)

# Suffixes that mark a tracked file as build-relevant source the completeness
# validator expects an explicit route to cover. A tracked file with one of these
# suffixes that no declared production/test route claims is reported as
# uncovered. The validator stays silent on every other tracked file (docs,
# config, data) and on every untracked file (``target/``, ``.venv/`` output).
_SOURCE_SUFFIXES: tuple[str, ...] = ('.py',)


def derive_globs_from_tree(
    project_root: str, extensions: list
) -> dict[str, list[tuple[str, str]]]:
    """Collect each build extension's explicit ``(pattern, role)`` build_map routes per domain.

    The shared base-lib consumer behind the build_map seed. Each registered build
    extension declares its build_map as explicit ``(pattern, role)`` routes via
    ``classify_globs()`` — an fnmatch-style glob pattern (e.g.
    ``marketplace/bundles/*.py``)
    paired with one of the three resolved roles (``production`` / ``test`` /
    ``config``). This function gathers those declared routes,
    keyed by the extension's first domain key, then filters them to the routes
    actually present in the project tree: a route survives only when at least one
    git-tracked file matches its ``pattern`` via :func:`_route_matches` (the same
    matcher the downstream ``manage-execution-manifest`` consumer and
    :func:`validate_tree_completeness` use). A bare-basename route (no ``/`` — e.g.
    ``pom.xml``, ``package.json``, ``tsconfig.json``) matches the config file
    *anywhere in the tree*, so a config file that lives only in subdirectories
    survives the prune; a path-bearing route matches against the whole
    repo-relative path with a single ``*`` spanning ``/``. Dead routes — patterns
    whose file type is absent from the tree (e.g. ``pom.xml``, ``*.tsx``,
    ``tsconfig.json`` on a project that has none) — are pruned before any consumer
    sees them, so the seed carries only live globs rather than the full
    theoretical toolchain superset.

    Tree completeness is a SEPARATE concern: :func:`validate_tree_completeness`
    scans git-tracked source files within build-covered roots and reports any
    such source file no declared route covers. The seed consumes the (now
    tree-filtered) routes here; the validator gates completeness.

    Args:
        project_root: Absolute path to the project root. The tracked-file list is
            read once from this root (via :func:`_list_tracked_files`) to prune
            routes whose pattern matches no file in the tree.
        extensions: List of :class:`BuildExtensionBase` instances exposing
            ``classify_globs()``, keyed by the domain each serves via
            ``get_skill_domains()``. Build extensions whose ``classify_globs()``
            returns no routes contribute nothing.

    Returns:
        A dict keyed by domain-key with a list of de-duplicated ``(pattern, role)``
        tuples as values, in deterministic sorted order, filtered to routes whose
        pattern matches at least one git-tracked file. Domains declaring no routes
        — or whose every route was pruned as dead — are omitted entirely. When
        several build extensions serve the same domain key (e.g. build-maven and
        build-gradle both serving ``java``), their routes are MERGED under that key
        — the per-domain route sets are unioned, not overwritten.
    """
    by_domain: dict[str, set[tuple[str, str]]] = {}

    for ext in extensions:
        try:
            routes = ext.classify_globs()
        except Exception:
            continue
        if not routes:
            continue

        domain_key = ''
        try:
            domains = ext.get_skill_domains()
            if domains:
                domain_key = str(domains[0].get('domain', {}).get('key', '') or '')
        except Exception:
            domain_key = ''
        if not domain_key:
            continue

        seen = by_domain.setdefault(domain_key, set())
        for route in routes:
            pattern, role = route
            if role not in BUILD_MAP_ROLES:
                continue
            seen.add((pattern, role))

    tracked = _list_tracked_files(project_root)
    return {
        key: live
        for key, routes in by_domain.items()
        if (
            live := sorted(
                route
                for route in routes
                if _pattern_matches_any(route[0], tracked)
            )
        )
    }


def _list_tracked_files(project_root: str) -> list[str]:
    """Return every git-tracked file path, repo-relative and forward-slashed.

    Runs ``git ls-files`` under ``project_root``. Tracked-only scoping is the
    completeness validator's containment boundary: untracked build / dependency
    output (``target/``, ``.venv/``, ``node_modules/``) never appears in the
    listing, so it is never flagged as uncovered. A non-repo root or a failed
    ``git`` invocation yields an empty list (the validator then reports nothing
    rather than crashing the seed).

    Args:
        project_root: Absolute path to the project root.

    Returns:
        Sorted list of repo-relative, forward-slash-separated tracked file paths.
    """
    try:
        completed = subprocess.run(
            ['git', '-C', project_root, 'ls-files', '-z'],
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    decoded = completed.stdout.decode('utf-8', errors='replace')
    rel_paths = [p.replace('\\', '/') for p in decoded.split('\0') if p]
    return sorted(rel_paths)


def _route_matches(path: str, pattern: str) -> bool:
    """Return True when repo-relative ``path`` matches route ``pattern``.

    A single matcher shared by the three build-map matching sites
    (:func:`derive_globs_from_tree` seed-prune, :func:`validate_tree_completeness`
    coverage check, :func:`should_execute_build` footprint loop). Two regimes,
    selected by whether the pattern names a directory segment:

    - **Bare-basename routes** (``pattern`` contains no ``/`` — e.g. ``pom.xml``,
      ``package.json``, ``tsconfig.json``): match on the path's *basename* via
      :func:`fnmatch.fnmatch`, so a config file is matched wherever it lives in the
      tree, not only at repo root. This is what keeps a subdirectory-only config
      file (``nifi-cuioss-ui/package.json``) in the seed and matched at
      build-decision time.
    - **Path-bearing routes** (``pattern`` contains ``/`` — e.g.
      ``marketplace/bundles/*.py``): match against the whole repo-relative path via
      :func:`fnmatch.fnmatch`, preserving the single-``*``-spans-``/`` behavior the
      downstream ``manage-execution-manifest`` consumer relies on.

    Args:
        path: Repo-relative, forward-slashed candidate path.
        pattern: A route glob — a bare basename (no ``/``) or a path-bearing glob.

    Returns:
        True when ``path`` matches ``pattern`` under the regime its shape selects.
    """
    if '/' not in pattern:
        return fnmatch.fnmatch(basename(path), pattern)
    return fnmatch.fnmatch(path, pattern)


@functools.lru_cache(maxsize=4)
def _tracked_basenames(tracked_tuple: tuple[str, ...]) -> list[str]:
    """Return the basenames of ``tracked_tuple``, cached by identity.

    Called by :func:`_pattern_matches_any` for every bare-basename pattern
    evaluated against the same tracked-file list.  A single ``discover`` call
    invokes :func:`_pattern_matches_any` once per route, all sharing the same
    ``tracked`` list — without caching, ``[basename(p) for p in tracked]`` is
    recomputed O(routes) times.  The ``lru_cache`` key is the tuple of paths, so
    each unique tracked-file snapshot is computed exactly once per process.

    Args:
        tracked_tuple: Repo-relative, forward-slashed candidate paths as a tuple
            (hashable for ``lru_cache`` keying).

    Returns:
        List of ``posixpath.basename`` values, one per entry in ``tracked_tuple``.
    """
    return [basename(p) for p in tracked_tuple]


def _pattern_matches_any(pattern: str, tracked: list[str]) -> bool:
    """Return True when route ``pattern`` matches at least one ``tracked`` path.

    The batch counterpart to the per-element :func:`_route_matches` truthiness
    loop. Both honour the same two regimes — :func:`_route_matches` decides them
    per (path, pattern) pair; this function decides the regime once for the whole
    corpus and hands the matching off to :func:`fnmatch.filter`, which does one
    batch pass instead of re-dispatching the matcher for every tracked file:

    - **Bare-basename routes** (``pattern`` contains no ``/``): match against the
      list of path *basenames*, so a config file is matched wherever it lives in
      the tree.  Basenames are computed once per unique ``tracked`` list via
      :func:`_tracked_basenames` (``lru_cache``-backed) to avoid O(routes × files)
      repeated work.
    - **Path-bearing routes** (``pattern`` contains ``/``): match against the
      whole repo-relative paths, preserving the single-``*``-spans-``/`` behavior.

    Args:
        pattern: A route glob — a bare basename (no ``/``) or a path-bearing glob.
        tracked: Repo-relative, forward-slashed candidate paths.

    Returns:
        True when ``pattern`` matches at least one path under the regime its shape
        selects — identical to ``any(_route_matches(p, pattern) for p in tracked)``.
    """
    if '/' not in pattern:
        return bool(fnmatch.filter(_tracked_basenames(tuple(tracked)), pattern))
    return bool(fnmatch.filter(tracked, pattern))


def _route_root(pattern: str) -> str:
    """Return the leading non-wildcard directory prefix of a route ``pattern``.

    The buildable-unit root of a route is the longest leading run of path
    segments that contain no glob wildcard (``*``/``?``/``[``). It is the tree a
    build extension actually claims:

    - ``marketplace/bundles/*.py`` → ``marketplace/bundles/`` (a directory root).
    - ``test/*.py`` → ``test/``.
    - ``build.py`` → ``build.py`` (an exact-file route; its own path is the root).
    - ``pyproject.toml`` → ``pyproject.toml``.

    A path is "within" a directory root when it is prefixed by ``root`` (with the
    trailing slash); an exact-file root matches only that file. The returned root
    carries a trailing ``/`` for directory roots and no trailing ``/`` for
    exact-file roots, so :func:`_within_buildable_roots` can distinguish the two.

    Args:
        pattern: A route glob (e.g. ``marketplace/bundles/*.py``) or an exact
            path (e.g. ``build.py``).

    Returns:
        The buildable-unit root string for ``pattern``.
    """
    segments = pattern.split('/')
    kept: list[str] = []
    for segment in segments:
        if any(ch in segment for ch in ('*', '?', '[')):
            break
        kept.append(segment)
    if len(kept) == len(segments):
        # No wildcard segment — the pattern is an exact path; it is its own root.
        return pattern
    # At least one wildcard segment was dropped — the kept prefix is a directory
    # root. Join with a trailing slash so prefix matching is segment-aligned.
    return '/'.join(kept) + '/' if kept else ''


def _within_buildable_roots(rel_path: str, roots: set[str]) -> bool:
    """Return True when ``rel_path`` falls under at least one buildable-unit root.

    A directory root (trailing ``/``) claims every path beneath it; an
    exact-file root (no trailing ``/``) claims only that exact path. The empty
    root ``''`` claims nothing (a fully-wildcarded pattern with no leading
    literal prefix declares no concrete tree).

    Args:
        rel_path: Repo-relative, forward-slashed tracked file path.
        roots: Set of buildable-unit roots from :func:`_route_root`.

    Returns:
        True when ``rel_path`` is a buildable unit (within a claimed root).
    """
    for root in roots:
        if not root:
            continue
        if root.endswith('/'):
            if rel_path.startswith(root):
                return True
        elif rel_path == root:
            return True
    return False


def validate_tree_completeness(project_root: str, extensions: list) -> list[str]:
    """Return uncovered git-tracked source files within buildable-unit roots.

    The completeness validator that replaces the old per-directory glob
    enumeration. Where the deriver once GUARANTEED coverage by emitting a glob
    per matched directory, the explicit-route contract instead lets domains
    declare compact routes and VALIDATES that those routes cover every tracked
    source file **within a build-covered tree**. A tracked ``.py`` an author's
    routes forgot but that lives under a buildable-unit root (e.g. a production
    module the routes did not enumerate inside ``marketplace/bundles/``) surfaces
    here as an uncovered path.

    The completeness denominator is **buildable units only**, NOT the full
    tracked-file universe. A buildable unit is a tracked source file that falls
    under a root some :class:`BuildExtensionBase` actually claims — derived from
    the leading non-wildcard prefix of each ``production``/``test`` route via
    :func:`_route_root`. A tracked ``.py`` outside every build-covered root (e.g.
    a one-off script in a directory no build system owns) is NOT a buildable unit
    and is never reported uncovered.

    The scan is git-tracked-only by construction (:func:`_list_tracked_files`),
    so untracked ``target/`` / ``.venv/`` output is never flagged. Only
    build-relevant source suffixes (:data:`_SOURCE_SUFFIXES`) are checked;
    documentation, config, and data files are ignored. A buildable-unit source
    file is covered when it matches at least one ``production`` or ``test`` route
    declared by any extension.

    Route patterns are matched with :func:`_route_matches` — the SAME matcher
    the downstream build_map consumer (``manage-execution-manifest``) uses. A
    path-bearing route matches via :func:`fnmatch.fnmatch` so a single ``*``
    matches across ``/`` (e.g. ``marketplace/targets/*.py`` covers
    ``marketplace/targets/generate.py`` and any file beneath ``targets/``); a
    bare-basename route (no ``/``) matches the file by basename anywhere in the
    tree. Routes are therefore declared with single-``*`` fnmatch globs (or bare
    basenames for config files), not recursive ``**`` forms.

    Args:
        project_root: Absolute path to the project root to scan.
        extensions: List of :class:`BuildExtensionBase` instances exposing
            ``classify_globs()``.

    Returns:
        Sorted list of repo-relative tracked source paths that are buildable
        units (within a build-covered root) yet covered by no declared route.
        Empty when every buildable-unit source file is covered.
    """
    source_routes: list[str] = []
    for ext in extensions:
        try:
            routes = ext.classify_globs()
        except Exception:
            continue
        for route in routes or []:
            pattern, role = route
            if role in (ROLE_PRODUCTION, ROLE_TEST):
                source_routes.append(pattern)

    # Buildable-unit denominator: only tracked source under a build-covered root
    # is a completeness candidate. The roots come from the production/test route
    # prefixes — the trees a BuildExtensionBase actually claims.
    buildable_roots = {_route_root(pattern) for pattern in source_routes}

    uncovered: list[str] = []
    for rel_path in _list_tracked_files(project_root):
        if not rel_path.endswith(_SOURCE_SUFFIXES):
            continue
        if not _within_buildable_roots(rel_path, buildable_roots):
            continue
        if not any(_route_matches(rel_path, pattern) for pattern in source_routes):
            uncovered.append(rel_path)
    return sorted(uncovered)


def _read_build_map_globs(project_root: str | None = None) -> list[str]:
    """Collect every non-empty ``glob`` from ``build.map`` in marshal.json.

    The build_map at the top-level ``build.map`` is the single source of truth
    for the file-to-build contract — every ``{glob, role, build_class}`` entry
    across all domains names a file type the project knows how to build. This is
    the build-decision activation gate: a build is necessary only when the live
    footprint touches one of these globs.

    Returns the deduplicated list of non-empty glob strings collected from every
    build_map entry, in first-seen order. Returns an empty list when marshal.json
    is missing, the ``build.map`` block is absent, or no entry
    carries a glob — :func:`should_execute_build` treats an empty list as "no
    build registered" and returns ``not_necessary``.

    Args:
        project_root: Accepted for signature parity with
            :func:`should_execute_build`; the marshal path is resolved from the
            current execution context (``file_ops.get_marshal_path`` honours the
            cwd-pinned / ``set_base_dir`` override), so this argument is not
            consumed here. The cross-skill ``file_ops`` import is deferred
            (in-function) so this foundational module carries no hard top-level
            dependency on another skill's scripts dir — build extensions import
            ``extension_base`` standalone.
    """
    del project_root  # resolved from execution context, not forwarded
    import json as _json

    from file_ops import get_marshal_path, read_json  # type: ignore[import-not-found]

    marshal_path = get_marshal_path()
    if not marshal_path.exists():
        return []
    try:
        data = read_json(marshal_path, default={})
    except (OSError, _json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []
    build = data.get('build')
    if not isinstance(build, dict):
        return []
    build_map = build.get('map')
    if not isinstance(build_map, dict):
        return []
    globs: list[str] = []
    seen: set[str] = set()
    for entries in build_map.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            glob = entry.get('glob')
            if isinstance(glob, str) and glob and glob not in seen:
                seen.add(glob)
                globs.append(glob)
    return globs


def _resolve_plan_footprint(plan_id: str) -> list[str]:
    """Derive the live plan footprint for ``plan_id`` on demand.

    Reads ``status.metadata.worktree_path`` to locate the worktree, then derives
    the footprint live via ``compute_plan_branch_diff`` (``{base}...HEAD`` ∪
    porcelain). Returns an empty list when no worktree is resolvable — the normal
    case during early compose (phase-4-plan), *before* phase-5 materialises the
    worktree. :func:`should_execute_build` treats an empty footprint as "nothing
    changed" and returns ``not_necessary``.

    The cross-skill ``file_ops`` / ``_references_core`` imports are deferred
    (in-function) for the same reason as :func:`_read_build_map_globs`: this
    foundational module carries no hard top-level dependency on another skill's
    scripts dir.

    Args:
        plan_id: Plan identifier whose footprint to resolve.
    """
    import json as _json
    import subprocess as _subprocess
    from pathlib import Path as _Path

    from _references_core import (  # type: ignore[import-not-found]
        compute_plan_branch_diff,
        resolve_base_ref,
    )
    from constants import FILE_REFERENCES, FILE_STATUS  # type: ignore[import-not-found]
    from file_ops import get_plan_dir, read_json  # type: ignore[import-not-found]

    status_path = get_plan_dir(plan_id) / FILE_STATUS
    if not status_path.exists():
        return []
    try:
        status = read_json(status_path, default={})
    except (OSError, _json.JSONDecodeError):
        return []
    if not isinstance(status, dict):
        return []
    metadata = status.get('metadata', {})
    if not isinstance(metadata, dict):
        return []
    worktree_path = metadata.get('worktree_path', '')
    if not isinstance(worktree_path, str) or not worktree_path:
        return []
    worktree = _Path(worktree_path)
    if not worktree.is_dir():
        return []

    refs_path = get_plan_dir(plan_id) / FILE_REFERENCES
    try:
        refs = read_json(refs_path, default={})
    except (OSError, _json.JSONDecodeError):
        refs = {}
    if not isinstance(refs, dict):
        refs = {}
    base_ref = resolve_base_ref(None, refs)
    try:
        footprint = compute_plan_branch_diff(worktree, base_ref)
    except _subprocess.CalledProcessError:
        return []
    return sorted(footprint)


def should_execute_build(
    canonical_command: str,
    plan_id: str,
    project_root: str | None = None,
) -> dict:
    """Decide whether ``canonical_command`` must run for ``plan_id``'s footprint.

    The single, build-system-owned home for the build-necessity decision that
    four consumer sites previously each re-derived (the pre-push-quality-gate
    activation in ``manage-execution-manifest``, the phase-4-plan per-task
    verification derivation, and the per-bundle Axis-B classify logic). The
    decision is a pure function of the ``build.map`` globs and the
    live plan footprint — no LLM judgement:

    1. Collect the build_map globs via :func:`_read_build_map_globs`.
    2. Resolve the live footprint via :func:`_resolve_plan_footprint`.
    3. Return ``not_necessary`` (with a log-friendly ``reason``) when the
       build_map registers no globs, OR the footprint is empty, OR the footprint
       intersects no build glob. Otherwise return ``build``.

    Args:
        canonical_command: The canonical command under decision (e.g.
            ``quality-gate`` / ``verify`` / ``coverage``). Echoed back on the
            ``build`` verdict so callers can resolve+run it without re-deriving.
        plan_id: Plan identifier whose footprint gates the decision.
        project_root: Accepted for signature parity; the marshal path resolves
            from the current execution context regardless of this value.

    Returns:
        A verdict dict. The ``build`` shape::

            {'decision': 'build', 'canonical_command': <command>}

        The ``not_necessary`` shape always carries a non-empty ``reason``::

            {'decision': 'not_necessary', 'reason': <log-friendly text>,
             'canonical_command': <command>}
    """
    globs = _read_build_map_globs(project_root)
    if not globs:
        return {
            'decision': 'not_necessary',
            'reason': 'build_map registers no globs — project has no buildable file types',
            'canonical_command': canonical_command,
        }

    footprint = _resolve_plan_footprint(plan_id)
    if not footprint:
        return {
            'decision': 'not_necessary',
            'reason': 'plan footprint is empty — no changed files to build',
            'canonical_command': canonical_command,
        }

    for path in footprint:
        for glob in globs:
            if _route_matches(path, glob):
                return {'decision': 'build', 'canonical_command': canonical_command}

    return {
        'decision': 'not_necessary',
        'reason': 'plan footprint touches no build_map glob — only non-buildable files changed',
        'canonical_command': canonical_command,
    }


class ExtensionBase(ABC):
    """Abstract base class for domain bundle extensions (Axis-A: skill-loading).

    Owns Axis-A of the extension contract only: skill-loading and the workflow
    extension hooks. The file-to-build map (Axis-B — ``classify_globs`` /
    ``classify_paths`` / ``classify_path_specificity`` / ``classify_build_class``)
    lives on the sibling :class:`BuildExtensionBase`, subclassed by the
    build-system-owned extensions. A language domain extension subclasses
    ``ExtensionBase`` only.

    Subclasses must implement:
        - get_skill_domains: Domain metadata and skill profiles

    All other methods have sensible defaults.
    Build bundles should override discover_modules() for module discovery.
    """

    # =========================================================================
    # Required Methods (must be implemented)
    # =========================================================================

    APPLICABLE_PROFILES = _APPLICABLE_PROFILES
    """Profile names iterated during _build_applicable_result(). Does not include 'core'
    which is always merged into each profile."""

    @abstractmethod
    def get_skill_domains(self) -> list[dict]:
        """Return all skill domains this extension provides.

        Returns:
            List of domain dicts. Each dict has domain identity and
            profile-based skill organization:
            {
                "domain": {
                    "key": str,          # Unique domain identifier
                    "name": str,         # Human-readable name
                    "description": str   # Domain description
                },
                "profiles": {
                    "core": {"defaults": [...], "optionals": [...]},
                    "implementation": {"defaults": [...], "optionals": [...]},
                    "module_testing": {"defaults": [...], "optionals": [...]},
                    "quality": {"defaults": [...], "optionals": [...]},
                    "documentation": {"defaults": [...], "optionals": [...]}  # Optional
                }
            }

        Most extensions return a single-element list. Multi-domain extensions
        (e.g., plan-marshall providing both 'build' and 'general-dev') return
        multiple elements.

        Skill Reference Format:
            Each skill entry in defaults/optionals can be either:
            - Object format (preferred): {"skill": "bundle:skill", "description": "..."}
            - String format: "bundle:skill"

        Standard Profiles:
            - core: Skills loaded for all profiles (foundation skills)
            - implementation: Code implementation skills
            - module_testing: Unit/module test skills
            - integration_testing: Integration test skills
            - quality: Quality/lint/format skills

        Cross-Domain Profile:
            - documentation: Documentation task skills (AsciiDoc, ADRs, interfaces).
              This profile is detected per-module during architecture enrichment
              when module has doc/*.adoc files. It represents a separate task type
              (like testing), not a variant of implementation.
        """
        pass

    # =========================================================================
    # Module Discovery Methods (override for build bundles)
    # =========================================================================

    def discover_modules(self, project_root: str) -> list:
        """Discover all modules with complete metadata.

        This is the primary API for module discovery. Returns comprehensive
        module information including metadata, dependencies, packages, and stats.

        Args:
            project_root: Absolute path to project root.

        Returns:
            List of module dicts. See module-discovery.md for complete
            contract including:
            - name, build_systems (array)
            - paths: {module, descriptor, sources, tests, readme}
            - metadata: snake_case fields (artifact_id, group_id, parent as string)
            - packages: object keyed by package name
            - dependencies: strings "groupId:artifactId:scope"
            - stats: {source_files, test_files}
            - commands: resolved canonical command strings

        Notes:
            - Override in build bundles to provide build-system-specific discovery
            - Default implementation returns empty list
            - Delegate to scripts in scripts/ directory for implementation
        """
        return []

    # =========================================================================
    # Configuration Callback (override to set project defaults)
    # =========================================================================

    def config_defaults(self, project_root: str) -> None:  # noqa: B027
        """Configure project-specific defaults in marshal.json.

        Called during project initialization, after extension loading but
        before workflow logic accesses configuration. This is the hook for
        extensions to set domain-specific defaults.

        Args:
            project_root: Absolute path to project root directory.

        Returns:
            None (void method)

        Contract:
            - MUST only write values if they don't already exist
            - MUST NOT override user-defined configuration
            - SHOULD use direct import from _config_core module
            - MAY skip silently if no defaults are needed

        Example:
            def config_defaults(self, project_root: str) -> None:
                from _config_core import ext_defaults_set_default
                # set_default returns True if set, False if key already existed
                ext_defaults_set_default("my_bundle.skip_profiles", "itest,native", project_root)

        See standards/extension-contract.md for complete documentation.
        """
        pass  # Default no-op implementation

    # =========================================================================
    # Workflow Extension Methods
    # =========================================================================

    def provides_triage(self) -> str | None:
        """Return triage skill reference if available.

        Returns:
            Skill reference as 'bundle:skill' (e.g., 'pm-dev-java:ext-triage-java')
            or None if no triage capability.

        Purpose:
            Triage skills categorize and prioritize findings during
            the plan-finalize phase.
        """
        return None

    def provides_outline_skill(self) -> str | None:
        """Return the domain-specific outline skill reference, or None.

        Returns:
            Skill reference as 'bundle:skill' (e.g.,
            'pm-plugin-development:ext-outline-workflow') or None.

            The skill's standards/change-{type}.md files contain
            domain-specific discovery, analysis, and deliverable
            creation logic. The change_type is passed to the skill
            for internal routing.

        Purpose:
            Loaded by the phase-3-outline skill. Provides domain-specific
            outline instructions instead of generic plan-marshall:phase-3-outline
            standards.

        Fallback:
            If a domain returns None, generic instructions from
            plan-marshall:phase-3-outline/standards/change-{type}.md
            are used.
        """
        return None

    def provides_recipes(self) -> list[dict]:
        """Return recipe definitions this extension provides.

        Recipes are predefined, repeatable transformations that bypass
        change-type detection and provide their own discovery, analysis,
        and deliverable patterns.

        Returns:
            List of recipe dicts, each containing:
            - key: str — Unique recipe identifier (e.g., 'refactor-to-profile-standards')
            - name: str — Human-readable display name
            - description: str — Description for recipe selection UI
            - skill: str — Fully-qualified skill reference (e.g., 'bundle:recipe-skill')
            - default_change_type: str — Change type for outline phase (e.g., 'tech_debt')
            - scope: str — Scope indicator (e.g., 'codebase_wide', 'module')

            Optional fields (set by user at plan creation time if omitted):
            - profile: str — Target profile (e.g., 'implementation', 'module_testing')
            - package_source: str — Package source (e.g., 'packages', 'test_packages')

        Notes:
            - The domain is auto-assigned from get_skill_domains() first entry
            - The source is auto-assigned as 'extension'
            - Default implementation returns empty list (no recipes)
        """
        return []

    def provides_retrospective_aspects(self) -> list[dict]:
        """Return domain-specific retrospective aspects for plan-retrospective.

        Each aspect declares a deterministic, script-backed analysis fragment
        that plan-retrospective merges into its aspect dispatch (Step 3) when
        the audited plan belongs to the aspect's declared domain. Domain-
        invariant aspects ship with the generic retrospective; this hook lets a
        domain bundle attach checks that are only meaningful for plans authored
        against its domain.

        Returns:
            List of aspect dicts, each containing:
            - aspect: str — Short aspect name used as the fragment key and the
              --aspect value passed to collect-fragments add (e.g.,
              'wrapper-tangle').
            - domain: str — Domain key gating the aspect. The retrospective
              merges the aspect only when the audited plan's domain matches
              (e.g., 'plan-marshall-plugin-dev').
            - script: str — Fully-qualified executor notation for the aspect's
              deterministic fragment producer.
            - reference: str — Skill-relative reference doc path documenting the
              aspect's detection contract and finding schema.
            - description: str — Human-readable description for report context.
            - order: int — Relative sort key used when merging domain aspects
              into the aspect table. Not enforced at runtime.

        See extension-api/standards/ext-point-retrospective.md for the full
        contract. Default implementation returns empty list (no domain-specific
        retrospective aspects).
        """
        return []

    def provides_arch_gate(self) -> dict | None:
        """Return this domain's arch-gate tool descriptor, or None.

        Optional additive hook mirroring provides_triage() / provides_outline_skill():
        a domain bundle overrides it to declare the native architectural-constraint
        tool that backs the ``arch-gate`` canonical command (e.g. ArchUnit for Java,
        import-linter for Python, dependency-cruiser for JavaScript). When the hook
        returns a non-None descriptor, ``skill-domains configure`` appends the
        ``default:verify:arch-gate`` per-deliverable read-only verify-step to
        ``phase-5-execute.verification_steps`` for the project. A domain that returns
        None appends nothing — the silent-skip default.

        There is a SINGLE execution model: a per-deliverable read-only verify-step
        that resolves through ``architecture resolve --command arch-gate`` and runs
        the domain's native tool as a structural-boundary gate, parsing its output
        into ``arch-constraint``-typed findings. There is NO execution-mode variant —
        the descriptor carries only the tool name (no ``execution_mode`` key).

        Returns:
            A descriptor dict ``{'tool': str}`` naming the native architectural-
            constraint tool, or None (the default) when the domain provides no
            arch-gate.
        """
        return None

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        """Check if this domain applies to a specific module and return resolved skills.

        Called during architecture enrichment to determine which skill domains
        apply to a module and what skills they provide. Each extension decides
        based on signals in the module's derived data and can customize which
        skills are defaults vs optionals per module.

        Args:
            module_data: Module dict from the module's derived.json
                (.plan/architecture/<module>/derived.json; the canonical
                module set lives in _project.json["modules"]) containing:
                build_systems, paths, dependencies, packages, metadata, stats
            active_profiles: Optional positive list of profiles to include.
                Overrides signal detection when provided (Layer 2/3).

        Returns:
            {
                'applicable': bool,
                'confidence': 'high' | 'medium' | 'low' | 'none',
                'signals': list[str],
                'additive_to': str | None,  # parent domain key (e.g., 'java')
                'skills_by_profile': {      # only when applicable
                    'implementation': {
                        'defaults': [{'skill': str, 'description': str}],
                        'optionals': [{'skill': str, 'description': str}]
                    },
                    ...
                }
            }

        Default returns not applicable. Override in extensions.
        Implementations typically call self.get_skill_domains() for base profiles,
        then adjust defaults/optionals based on module_data signals.
        """
        return {
            'applicable': False,
            'confidence': 'none',
            'signals': [],
            'additive_to': None,
            'skills_by_profile': {},
        }

    def _detect_applicable_profiles(self, profiles: dict, module_data: dict | None) -> set[str] | None:
        """Detect which profiles are applicable based on module signals.

        Returns set of applicable profile names, or None for no filtering
        (all defined profiles are included). Override in domain extensions
        for signal-based detection.

        Args:
            profiles: Dict of profile definitions from get_skill_domains()
            module_data: Module dict from the module's derived.json
                (.plan/architecture/<module>/derived.json), or None

        Returns:
            Set of applicable profile names, or None for no filtering.
        """
        return None

    def _build_applicable_result(
        self,
        confidence: str,
        signals: list[str],
        additive_to: str | None = None,
        module_data: dict | None = None,
        active_profiles: set[str] | None = None,
        domain_key: str | None = None,
    ) -> dict:
        """Build applicable result from own get_skill_domains() profiles.

        Note: Despite the underscore prefix, this is part of the public API
        for extension implementations. All extensions call this from applies_to_module().

        Merges 'core' profile into each non-core profile to produce a flat
        skills_by_profile dict ready for consumption.

        Domain selection: By default uses the first domain entry from
        get_skill_domains(). Multi-domain extensions can pass domain_key
        to select a specific domain (e.g., 'general-dev' instead of 'build').

        Profile filtering (three-layer resolution):
        1. active_profiles (explicit override from config or CLI) wins
        2. _detect_applicable_profiles() (signal-based detection) if no override
        3. All defined profiles if detection returns None

        Args:
            confidence: 'high', 'medium', or 'low'
            signals: List of signal strings explaining why applicable
            additive_to: Parent domain key if this is an additive domain
            module_data: Module dict for signal-based profile detection
            active_profiles: Explicit positive list of profiles to include
            domain_key: Select a specific domain by key instead of using
                the first entry. Required for multi-domain extensions.

        Returns:
            Full applies_to_module result dict with applicable=True
        """
        all_domains = self.get_skill_domains()
        if domain_key:
            domains = next(
                (d for d in all_domains if d.get('domain', {}).get('key') == domain_key),
                all_domains[0] if all_domains else {},
            )
        else:
            domains = all_domains[0] if all_domains else {}
        profiles = domains.get('profiles', {})
        core = profiles.get('core', {})
        core_defaults = core.get('defaults', [])
        core_optionals = core.get('optionals', [])

        # Determine which profiles are active (three-layer resolution)
        profile_filter: set[str] | None
        if active_profiles is not None:
            profile_filter = active_profiles
        else:
            profile_filter = self._detect_applicable_profiles(profiles, module_data)

        skills_by_profile: dict[str, dict] = {}
        for profile_name in self.APPLICABLE_PROFILES:
            if profile_name not in profiles:
                continue
            if profile_filter is not None and profile_name not in profile_filter:
                continue
            profile = profiles[profile_name]
            merged_defaults = list(core_defaults) + list(profile.get('defaults', []))
            merged_optionals = list(core_optionals) + list(profile.get('optionals', []))
            if merged_defaults or merged_optionals:
                skills_by_profile[profile_name] = {
                    'defaults': merged_defaults,
                    'optionals': merged_optionals,
                }
        return {
            'applicable': True,
            'confidence': confidence,
            'signals': signals,
            'additive_to': additive_to,
            'skills_by_profile': skills_by_profile,
        }


class BuildExtensionBase(ABC):  # noqa: B024 — ABC contract anchor; every Axis-B method has a default
    """Abstract base class for build-system-owned file-to-build extensions.

    Owns Axis-B of the extension contract: the file-to-build map. Where
    :class:`ExtensionBase` answers "what skills does this domain load" (Axis-A),
    a ``BuildExtensionBase`` subclass answers "what build does a changed file
    trigger." The two hierarchies are deliberately un-entangled — a build skill
    (``build-pyproject`` / ``build-maven`` / ``build-gradle`` / ``build-npm``)
    ships a ``BuildExtensionBase`` subclass declaring its ``(pattern, role)``
    routes, while the language domain extensions subclass only
    :class:`ExtensionBase`.

    The four methods below carry the same default implementations the
    file-to-build contract has always had:

        - ``classify_globs``: empty route list (a build extension owning no
          buildable file types contributes nothing).
        - ``classify_paths``: empty four-role dict (no-op claim).
        - ``classify_path_specificity``: ``0`` (no specificity score).
        - ``classify_build_class``: the role→build_class default map.

    The module-level :func:`derive_globs_from_tree` and
    :func:`validate_tree_completeness` functions iterate ``classify_globs()`` on
    ``BuildExtensionBase`` instances — they are the aggregator-facing consumers of
    the routes a subclass declares.

    There is no abstract method: every Axis-B method has a sensible default, so a
    subclass that overrides nothing is a valid (no-route) build extension. The
    ``ABC`` base marks the class as the Axis-B contract anchor.
    """

    def classify_paths(self, paths: list[str]) -> dict[str, list[str]]:
        """Classify each path into a file-role bucket owned by this extension.

        Build extensions own the predicates that decide which paths they claim
        and the role each claimed path plays (production / test / documentation /
        config). The default implementation is a no-op — build extensions that do
        not own any file types simply do not override this method.

        Args:
            paths: List of repo-relative path strings to classify. The
                aggregator passes every path under the plan's
                `references.affected_files` union. Build extensions are free to
                ignore paths their globs do not match.

        Returns:
            A dict keyed by file-role with list-of-claimed-paths values.
            The four roles are fixed by contract:

            - ``production``: source code that ships to production (e.g.,
              ``scripts/foo.py``, ``src/main/java/Foo.java``).
            - ``test``: test source code (e.g., ``test/foo_test.py``,
              ``src/test/java/FooIT.java``).
            - ``documentation``: human-readable documentation (e.g.,
              ``README.md``, ``standards/foo.md``, ``docs/foo.adoc``).
            - ``config``: build / lint / packaging configuration (e.g.,
              ``pom.xml``, ``pyproject.toml``, ``package.json``).

            Default returns the empty four-role dict
            ``{'production': [], 'test': [], 'documentation': [], 'config': []}``;
            the aggregator interprets this as "this extension claims
            nothing". The default is intentionally NOT
            ``NotImplementedError`` — extensions opting out is the common
            case.

        Aggregator responsibility (NOT this method's responsibility):

        - **Longest-glob-wins overlap resolution.** When two extensions claim
          the same path under different roles or different glob patterns,
          the aggregator (`manage-execution-manifest._classify_paths_via_extensions`)
          counts non-wildcard path-segment tokens in each extension's matched
          glob and the longest-glob wins. Ties break alphabetically on the
          extension's domain key.
        - **Unclaimed-path handling.** Paths no extension claims are tagged
          ``unknown`` by the aggregator and surface as a ``[STATUS]``
          warning. The aggregator never silently falls back to
          ``documentation_only``.
        - **Plan-wide bucket collapse.** The aggregator collapses per-path
          claims into one of six plan-wide bucket values: ``production_only``,
          ``test_only``, ``documentation_only``, ``mixed_code``,
          ``mixed_with_docs``, ``unknown``.

        Example (override in a build extension)::

            def classify_paths(self, paths: list[str]) -> dict[str, list[str]]:
                claims: dict[str, list[str]] = {
                    'production': [], 'test': [], 'documentation': [], 'config': []
                }
                for path in paths:
                    if path.endswith('.py') and path.startswith('scripts/'):
                        claims['production'].append(path)
                    elif path.endswith('.py') and (
                        path.startswith('test/') or path.startswith('tests/')
                    ):
                        claims['test'].append(path)
                    elif path in ('pyproject.toml',):
                        claims['config'].append(path)
                return claims

        See ``extension-api/standards/extension-contract.md`` § classify_paths()
        for the complete contract documentation.
        """
        return {'production': [], 'test': [], 'documentation': [], 'config': []}

    def classify_path_specificity(self, path: str, role: str) -> int:
        """Return the non-wildcard segment count of this extension's matched glob.

        Called by the manage-execution-manifest aggregator when more than one
        extension claims the same path. The aggregator uses the returned value
        to apply longest-glob-wins overlap resolution: the extension with the
        highest specificity score wins the path under its declared role.

        Args:
            path: The path that this extension claimed (in any role).
            role: The role under which this extension claimed the path
                (one of ``production`` / ``test`` / ``documentation`` /
                ``config``).

        Returns:
            Non-negative integer specificity score. Higher wins. The default
            returns ``0`` — build extensions that override ``classify_paths()``
            are expected to override this method as well, returning the count of
            non-wildcard path-segment tokens in the glob that matched ``path``
            for ``role``.

        Example::

            # An extension whose glob ``marketplace/bundles/*/skills/*/SKILL.md``
            # claimed the path ``marketplace/bundles/foo/skills/bar/SKILL.md``
            # for the ``documentation`` role returns 4 (the four explicit
            # segments: ``marketplace``, ``bundles``, ``skills``, ``SKILL.md``).
            def classify_path_specificity(self, path: str, role: str) -> int:
                if role == 'documentation' and path.endswith('SKILL.md'):
                    return 4
                return 0
        """
        return 0

    def classify_build_class(self, path: str, role: str) -> str:
        """Return the deterministic build_class for a (path, role) pair.

        The second leg of the file-to-build contract. Where ``classify_paths()``
        maps a path to a file role, this method maps the resulting (path, role)
        pair to a build_class — the deterministic classification a downstream
        consumer (``manage-execution-manifest``, ``phase-4-plan``) reads to derive
        the verification command set for a changed-artifact list without
        re-deriving the file type. This method is exactly parallel to
        ``classify_path_specificity`` (a separate per-(path, role) lookup, NOT a
        change to the four-role ``classify_paths()`` return shape).

        Args:
            path: The path this extension claimed (in any role). Supplied so a
                build extension may discriminate the build_class on the path
                itself when the role default is wrong; the default implementation
                ignores it.
            role: The role under which this extension claimed the path — one of
                ``production`` / ``test`` / ``config``.

        Returns:
            A member of the closed 4-value enum ``BUILD_CLASSES`` — each value
            NAMES the canonical command directly (no name-to-name indirection):

            - ``compile``: production source — resolves a ``compile``.
            - ``module-tests``: test source — resolves ``test-compile`` +
              ``module-tests``.
            - ``verify``: build/lint/packaging config — resolves a full reactor
              ``verify`` for the affected module.
            - ``none``: no build derives from this (path, role) pair.

            The default maps roles deterministically:
            ``production → compile``, ``test → module-tests``,
            ``config → verify``, and any unmatched role → ``none``. There is no
            ``documentation`` route role — documentation is not a build-system
            concern and has no build owner; doc-change recognition is a generic
            file-suffix fact owned by ``manage-execution-manifest``, not a
            build_class derived here. Build extensions that override
            ``classify_paths()`` inherit this default and override
            ``classify_build_class`` ONLY where the role→build_class default is
            wrong (e.g. a generated file whose path should derive ``none`` despite
            a ``production`` role).

        See ``extension-api/standards/extension-contract.md`` § classify_paths()
        for the complete contract documentation.
        """
        default_by_role = {
            'production': BUILD_CLASS_PROD_COMPILE,
            'test': BUILD_CLASS_TEST_RUN,
            'config': BUILD_CLASS_BUILD_CONFIG_FULL,
        }
        return default_by_role.get(role, BUILD_CLASS_NONE)

    def classify_globs(self) -> list[tuple[str, str]]:
        """Return this extension's explicit ``(pattern, role)`` build_map routes.

        Each tuple is ``(pattern, role)`` — a concrete glob pattern paired with
        one of the three resolved file roles. The route declares both WHAT this
        build extension owns and WHERE it lives, so the build_map seed consumes
        the routes verbatim: no tree scan enumerates one glob per directory.
        Patterns are matched with :func:`_route_matches` (the matcher the
        downstream ``manage-execution-manifest`` build_map consumer uses): a
        path-bearing route is matched against the whole repo-relative path via
        :func:`fnmatch.fnmatch`, so a single ``*`` matches across ``/`` — declare
        single-``*`` globs, NOT recursive ``**`` forms; a bare-basename config
        route (no ``/`` — e.g. ``pom.xml``, ``package.json``) matches the file by
        basename *anywhere in the tree*, so a config file that lives only in
        subdirectories is still kept in the seed and matched at build-decision
        time, not only a root-level instance. A production ``.py`` outside the
        obvious roots
        (e.g. ``marketplace/targets/*.py`` or every
        ``marketplace/bundles/*/skills/plan-marshall-plugin/*.py``) is covered by
        declaring a route whose pattern matches it. The git-tracked completeness
        validator (``validate_tree_completeness``) reports any tracked source
        file these routes forgot **within a build-covered root**, so an omitted
        production module surfaces as an uncovered path rather than being silently
        missed.

        Returns:
            A list of ``(pattern, role)`` tuples. ``pattern`` is an
            fnmatch-style glob (e.g. ``test/*.py``) or a bare basename for a
            config file (e.g. ``pyproject.toml``), which matches that file at any
            tree depth. ``role`` is one of the three
            ``BUILD_MAP_ROLES`` — ``production`` / ``test`` / ``config`` — and
            maps straight through to a ``classify_build_class``
            build_class with no name-to-name indirection. The default
            implementation returns an empty list: build extensions that own no
            buildable file types contribute no routes. Example for the python
            build extension:
            ``[('build.py', 'production'),
            ('marketplace/bundles/*.py', 'production'),
            ('marketplace/targets/*.py', 'production'),
            ('test/*.py', 'test')]``.

        This accessor is exactly parallel to ``classify_build_class`` and
        ``classify_path_specificity``: a per-extension lookup the aggregator
        consumes, NOT a change to the ``classify_paths()`` return shape.

        See ``extension-api/standards/extension-contract.md`` § classify_globs()
        for the complete contract documentation.
        """
        return []
