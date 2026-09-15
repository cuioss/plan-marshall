# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Shared marketplace bundle discovery and resolution.

Provides bundle discovery, name extraction, path resolution, and PYTHONPATH
building for marketplace scripts. Used by generate_executor.py,
scan-marketplace-inventory.py, and other scripts that work with bundles.
"""

import os
import re
from collections.abc import Callable
from pathlib import Path


def select_live_version_dir(bundle_dir: Path, is_candidate: Callable[[Path], bool]) -> Path | None:
    """Select the newest eligible version directory of ``bundle_dir``, or ``None``.

    The single authority for the "which cached version dir does this bundle
    resolve to?" decision. Callers contribute ONLY their own eligibility
    predicate (``is_candidate``: manifest present / requested subpath present /
    ``skills/`` present); ordering (the ``_version_sort_key`` numeric tuple) is
    decided here and nowhere else, so two call sites in the same process can
    never resolve to different version dirs.

    **Numerically-newest-eligible wins.** Among the version dirs that satisfy
    ``is_candidate``, the one whose ``_version_sort_key`` is highest is returned.
    When no subdirectory satisfies ``is_candidate`` — or ``bundle_dir`` is
    unreadable — the result is ``None``: a loud failure the caller must handle,
    never a silent resolution to the wrong version. Selecting the newest (rather
    than the lexically-first ``iterdir`` result) is what stops a stale older
    version dir from shadowing the current one on the cross-skill import path.

    **The plugin-cache ``.orphaned_at`` marker is not consulted.** The field has
    a foreign co-producer — Claude Code's own plugin GC writes the same filename
    on its own schedule — so it is a variable this repository neither owns nor can
    version, and no resolver-time decision turns on it. Picking the newest
    eligible dir needs no currency signal from the marker: a sync only ever adds
    a *newer* version dir, so newest-wins already resolves to the current
    version, and pruning the superseded dirs is the ``marshall-steward``
    ``cache_retention sweep``'s union-keep job, not a resolver's.

    Args:
        bundle_dir: Directory whose immediate subdirectories are the version dirs.
        is_candidate: Caller-supplied eligibility predicate over a version dir.

    Returns:
        The newest eligible version dir, or ``None`` when ``bundle_dir`` is
        unreadable or no subdirectory satisfies ``is_candidate``.
    """
    try:
        version_dirs = [d for d in bundle_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    except OSError:
        return None
    candidates = [d for d in version_dirs if is_candidate(d)]
    if not candidates:
        return None
    return max(candidates, key=lambda d: _version_sort_key(d.name))


def find_bundles(base_path: Path) -> list[Path]:
    """Find bundle directories, selecting one version dir per bundle.

    Locates ``.claude-plugin/plugin.json`` files, then reduces each bundle to a
    single directory:

    - In the versioned plugin-cache layout (``.../plan-marshall/0.1-BETA/``), a
      directory whose name matches ``^\\d+\\.\\d+`` is a version directory. Version
      directories sharing a parent belong to the same bundle and are reduced by
      :func:`select_live_version_dir`, to which this function contributes only its
      eligibility predicate: "carries a ``.claude-plugin/plugin.json``". The
      ordering (newest-eligible wins) lives in the selector, so this leg can
      never diverge from ``resolve_bundle_path`` or ``collect_script_dirs``.
    - In the non-versioned marketplace layout, each bundle directory forms its own
      singleton group and passes through unchanged — even when its name happens to
      match the version-dir digit pattern (e.g. ``1.0-my-bundle``). The version-dir
      check is gated on ``bundle_dir.parent != base_path`` so a top-level bundle
      whose name starts with digits is never merged into a version group keyed by
      ``base_path`` itself, which would otherwise silently discard sibling bundles
      that also match the pattern.
    """
    versioned_groups: dict[Path, list[Path]] = {}
    singletons: list[Path] = []
    seen: set[Path] = set()
    for plugin_json in base_path.rglob('.claude-plugin/plugin.json'):
        bundle_dir = plugin_json.parent.parent
        if bundle_dir in seen:
            continue
        seen.add(bundle_dir)
        if bundle_dir.parent != base_path and re.match(r'^\d+\.\d+', bundle_dir.name):
            versioned_groups.setdefault(bundle_dir.parent, []).append(bundle_dir)
        else:
            singletons.append(bundle_dir)

    selected: list[Path] = list(singletons)
    for parent, version_dirs in versioned_groups.items():
        # Eligibility: "this version dir carries a .claude-plugin/plugin.json" —
        # i.e. it is one of the dirs the rglob above discovered for this bundle.
        group = set(version_dirs)
        chosen = select_live_version_dir(parent, group.__contains__)
        if chosen is not None:
            selected.append(chosen)
    return sorted(selected)


def extract_bundle_name(bundle_dir: Path) -> str:
    """Extract bundle name, handling versioned plugin-cache structure.

    For versioned structure (plugin-cache): .../plan-marshall/0.1-BETA/ -> "plan-marshall"
    For non-versioned structure (marketplace): .../plan-marshall/ -> "plan-marshall"
    """
    name = bundle_dir.name
    if re.match(r'^\d+\.\d+', name):
        return bundle_dir.parent.name
    return name


def resolve_bundle_path(base_path: Path, bundle_name: str, subpath: str) -> Path:
    """Resolve path within a bundle, handling versioned cache structure.

    Tries versioned path first (plugin-cache with version dir), then non-versioned (marketplace).

    Args:
        base_path: Path to bundles directory (plugin-cache or marketplace)
        bundle_name: Name of the bundle (e.g., 'plan-marshall')
        subpath: Path within the bundle (e.g., 'skills/foo/scripts/bar.py')
    """
    bundle_dir = base_path / bundle_name

    if bundle_dir.is_dir():
        # Eligibility only: "this version dir carries the requested subpath".
        # Ordering (newest-eligible wins) is decided by select_live_version_dir,
        # so this leg resolves to the same version dir as find_bundles and
        # collect_script_dirs.
        selected = select_live_version_dir(bundle_dir, lambda d: (d / subpath).exists())
        if selected is not None:
            return selected / subpath

    return bundle_dir / subpath


def _version_sort_key(version_name: str) -> tuple[int, ...]:
    """Parse a version directory name into a comparable integer tuple.

    Extracts each run of digits in document order so the newest version dir
    sorts highest: ``'0.1.1069'`` -> ``(0, 1, 1069)``, ``'0.1-BETA'`` -> ``(0, 1)``.
    A name with no digits yields the empty tuple (sorts lowest).
    """
    return tuple(int(part) for part in re.findall(r'\d+', version_name))


def collect_script_dirs(base_path: Path) -> list[str]:
    """Collect all skill script directories from bundles.

    Discovers script directories and their immediate subdirectories,
    enabling cross-skill imports for scripts organized in subdirectory trees.

    Args:
        base_path: Path to bundles directory (plugin-cache or marketplace)

    Returns:
        List of script directory paths (parent dirs first, then subdirs)
    """
    script_dirs: list[str] = []

    for bundle_dir in base_path.iterdir():
        if not bundle_dir.is_dir() or bundle_dir.name.startswith('.'):
            continue

        # Determine base directories to scan for skills:
        # versioned (plugin-cache) -> the ONE live version subdir; non-versioned ->
        # bundle itself. Scanning every version dir pollutes PYTHONPATH with
        # multiple versions of the same script, so an older version can shadow the
        # current one. Eligibility here is only "this version dir carries a skills/
        # tree"; select_live_version_dir picks the newest eligible one.
        selected = select_live_version_dir(bundle_dir, lambda d: (d / 'skills').is_dir())
        scan_roots = [selected] if selected is not None else [bundle_dir]

        for root in scan_roots:
            skills_dir = root / 'skills'
            if not skills_dir.exists():
                continue
            for skill_dir in skills_dir.iterdir():
                if skill_dir.is_dir():
                    scripts_dir = skill_dir / 'scripts'
                    if scripts_dir.exists():
                        script_dirs.append(str(scripts_dir))

    subdirs: list[str] = []
    for scripts_path in script_dirs:
        scripts_dir = Path(scripts_path)
        for child in scripts_dir.iterdir():
            if child.is_dir() and not child.name.startswith('.') and not child.name == '__pycache__':
                subdirs.append(str(child))

    script_dirs.extend(subdirs)
    return script_dirs


def resolve_bundles_root(script_file: Path) -> Path:
    """Resolve the bundles root directory by walking up from a script file.

    Walks parents of ``script_file`` and returns the first ancestor that
    contains a ``plan-marshall`` bundle — detected by the presence of either:

    - ``plan-marshall/.claude-plugin/plugin.json`` (marketplace/source layout)
    - ``plan-marshall/<version>/.claude-plugin/plugin.json`` (plugin-cache layout)

    Uses identity walking (no index arithmetic). Raises ``RuntimeError`` with
    the full walked parent chain if no such ancestor exists, so import-time
    misconfiguration fails loudly instead of silently returning a wrong path.

    Args:
        script_file: Path to the calling script (typically ``Path(__file__)``).

    Returns:
        The bundles root directory (e.g. ``.../marketplace/bundles``).

    Raises:
        RuntimeError: If no ancestor contains a ``plan-marshall`` bundle.
    """
    start = Path(script_file).resolve()
    walked: list[Path] = []
    for ancestor in start.parents:
        walked.append(ancestor)
        candidate = ancestor / 'plan-marshall'
        if not candidate.is_dir():
            continue
        if (candidate / '.claude-plugin' / 'plugin.json').is_file():
            return ancestor
        for version_dir in candidate.iterdir():
            if (
                version_dir.is_dir()
                and not version_dir.name.startswith('.')
                and (version_dir / '.claude-plugin' / 'plugin.json').is_file()
            ):
                return ancestor
    chain = '\n  '.join(str(p) for p in walked)
    raise RuntimeError(
        f"resolve_bundles_root: could not locate a 'plan-marshall' bundle above {start}. Walked parents:\n  {chain}"
    )


def resolve_skills_root(script_file: Path) -> Path:
    """Resolve the ``skills`` directory anchor by walking up from a script file.

    Walks parents of ``script_file`` and returns the first ancestor named
    ``skills`` whose parent contains a ``.claude-plugin/plugin.json`` (i.e. is
    a bundle directory). Uses identity walking (no index arithmetic). Raises
    ``RuntimeError`` with the full walked parent chain if no such ancestor
    exists, so import-time misconfiguration fails loudly.

    Args:
        script_file: Path to the calling script (typically ``Path(__file__)``).

    Returns:
        The ``skills`` directory inside the owning bundle.

    Raises:
        RuntimeError: If no ``skills`` ancestor with a sibling bundle manifest
            is found.
    """
    start = Path(script_file).resolve()
    walked: list[Path] = []
    for ancestor in start.parents:
        walked.append(ancestor)
        if ancestor.name != 'skills':
            continue
        if (ancestor.parent / '.claude-plugin' / 'plugin.json').is_file():
            return ancestor
    chain = '\n  '.join(str(p) for p in walked)
    raise RuntimeError(
        f"resolve_skills_root: could not locate a 'skills' directory inside "
        f'a bundle above {start}. Walked parents:\n  {chain}'
    )


def build_pythonpath(base_path: Path) -> str:
    """Build PYTHONPATH from all skill script directories.

    Enables cross-skill imports for scripts called via subprocess.

    Args:
        base_path: Path to bundles directory (plugin-cache or marketplace)

    Returns:
        PYTHONPATH string with all skill script directories
    """
    return os.pathsep.join(collect_script_dirs(base_path))
