# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Shared marketplace bundle discovery and resolution.

Provides bundle discovery, name extraction, path resolution, and PYTHONPATH
building for marketplace scripts. Used by generate_executor.py,
scan-marketplace-inventory.py, and other scripts that work with bundles.
"""

import os
import re
import sys
from collections.abc import Callable
from pathlib import Path


def _partition_version_dirs(
    bundle_dir: Path, is_candidate: Callable[[Path], bool]
) -> tuple[list[Path], list[Path]]:
    """Partition ``bundle_dir``'s version dirs into (eligible, live).

    The ONE place the ``.orphaned_at`` marker is read and the ONE place the
    retention pin is computed. :func:`select_live_version_dir` (which dir wins)
    and :func:`live_version_dirs` (which dirs are live) are both thin views over
    this partition, so the two can never disagree.

    ``live`` is the subset of ``eligible`` whose marker does not disqualify it: an
    unmarked dir, or the bundle's newest-on-disk (retention-pinned) dir whose mark
    is ignored outright.

    **Only the EXISTENCE of ``.orphaned_at`` is ever consulted. Its content is
    never read, parsed, or compared.** This is a binding invariant, not an
    incidental property of the ``.exists()`` call below. The reason is that the
    field has a foreign co-producer: Claude Code's own plugin GC writes the same
    filename with a raw epoch-ms payload, while our writer
    (``generate_executor._mark_superseded_version_dirs``) writes ISO-8601 UTC. Any
    content-dependent read here would couple this repository to a format it does
    not own and cannot version. The marker is therefore a pure boolean flag whose
    payload is deliberately opaque, and the encoding split is inert precisely
    because nothing downstream looks inside it.
    """
    try:
        version_dirs = [d for d in bundle_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    except OSError:
        return [], []
    if not version_dirs:
        return [], []
    pinned = max(version_dirs, key=lambda d: _version_sort_key(d.name))
    eligible = [d for d in version_dirs if is_candidate(d)]
    live = [d for d in eligible if d == pinned or not (d / '.orphaned_at').exists()]
    return eligible, live


def live_version_dirs(bundle_dir: Path, is_candidate: Callable[[Path], bool]) -> list[Path]:
    """Return the eligible version dirs of ``bundle_dir`` the marker policy treats as live.

    The plural view of the same policy :func:`select_live_version_dir` selects
    from — it re-implements nothing, both delegate to
    :func:`_partition_version_dirs`. Consumers that must COUNT live dirs (the
    executor preflight's multi-version-pollution detector) use this; consumers
    that need the ONE dir to resolve against use the selector.

    Args:
        bundle_dir: Directory whose immediate subdirectories are the version dirs.
        is_candidate: Caller-supplied eligibility predicate over a version dir.

    Returns:
        The live version dirs (possibly empty), in ``iterdir`` order.
    """
    _eligible, live = _partition_version_dirs(bundle_dir, is_candidate)
    return live


def select_live_version_dir(bundle_dir: Path, is_candidate: Callable[[Path], bool]) -> Path | None:
    """Select the live version directory of ``bundle_dir``, or ``None`` when none qualifies.

    This is the single authority for the "which cached version dir is live?"
    decision. Callers contribute ONLY their own eligibility predicate
    (``is_candidate``: manifest present / requested subpath present / ``skills/``
    present); liveness (the ``.orphaned_at`` marker semantics) and ordering (the
    ``_version_sort_key`` numeric tuple) are decided here and nowhere else, so
    two call sites in the same process can never resolve to different version
    dirs.

    Policy:

    - **Existence only.** Every rule below turns on whether ``.orphaned_at`` is
      PRESENT, never on what it contains — the marker's content is never read,
      parsed, or compared anywhere in this module. The field has a foreign
      co-producer (Claude Code's plugin GC writes it as raw epoch-ms, our writer
      writes ISO-8601 UTC), so a content-dependent rule would bind the selector to
      a format this repository does not own. Treat the marker as a boolean flag
      with a deliberately opaque payload. See
      :func:`_partition_version_dirs`, the single read site.
    - The bundle's **newest-on-disk** version dir is retention-pinned: it is what
      the highest-version-wins resolver — and the ``marshall-steward``
      ``cache_retention sweep`` keep-union — actually selects, so a ``.orphaned_at``
      mark on it is ignored outright. A mark is written at one point in time and
      nothing clears it when pruning later promotes that dir to newest-on-disk,
      so honouring the mark there would let a stale marker suppress the current
      version.
    - Otherwise a ``.orphaned_at`` mark disqualifies a candidate, and the
      numerically-newest surviving candidate wins (tiers 1 and 2 of the former
      ``find_bundles`` precedence collapse into this one selection: a live current
      version is by construction the newest unmarked candidate).
    - When *every* candidate is marked (saturation, reachable only when the pinned
      dir is not itself a candidate), a degraded fallback returns the newest
      candidate overall and emits a stderr line naming the bundle, the saturation
      condition, and its remedy. This guarantees a bundle with an eligible version
      dir on disk never contributes zero — the silent break the fallback closes —
      while keeping the degraded state diagnosable (ADR-009) rather than
      indistinguishable from routine noise.

    Args:
        bundle_dir: Directory whose immediate subdirectories are the version dirs.
        is_candidate: Caller-supplied eligibility predicate over a version dir.

    Returns:
        The selected version dir, or ``None`` when ``bundle_dir`` is unreadable or
        no subdirectory satisfies ``is_candidate``.
    """
    candidates, live = _partition_version_dirs(bundle_dir, is_candidate)
    if not candidates:
        return None
    if live:
        return max(live, key=lambda d: _version_sort_key(d.name))

    newest = max(candidates, key=lambda d: _version_sort_key(d.name))
    print(
        f'marketplace_bundles.select_live_version_dir: DEGRADED (orphan-marker saturation) for bundle '
        f"'{bundle_dir.name}' — all {len(candidates)} eligible version dir(s) carry .orphaned_at "
        f'and 0 are live, so the marker carries no currency signal; falling back to '
        f"newest eligible '{newest.name}'. Remedy: run the marshall-steward upgrade flow's "
        f'cache-retention-sweep sub-step '
        f'(plan-marshall:marshall-steward:cache_retention sweep) to prune the superseded '
        f'version dirs; the executor preflight no longer marks the retention-pinned '
        f'(newest-on-disk / provisioned / manifest-named) versions, so a re-run leaves at '
        f'least one dir live.',
        file=sys.stderr,
    )
    return newest


def find_bundles(base_path: Path) -> list[Path]:
    """Find bundle directories, selecting one version dir per bundle.

    Locates ``.claude-plugin/plugin.json`` files, then reduces each bundle to a
    single directory:

    - In the versioned plugin-cache layout (``.../plan-marshall/0.1-BETA/``), a
      directory whose name matches ``^\\d+\\.\\d+`` is a version directory. Version
      directories sharing a parent belong to the same bundle and are reduced by
      :func:`select_live_version_dir`, to which this function contributes only its
      eligibility predicate: "carries a ``.claude-plugin/plugin.json``". The
      marker semantics and the ordering live in the selector, so this leg can
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
        # Liveness and ordering are decided by select_live_version_dir, so this
        # leg resolves to the same version dir as find_bundles and
        # collect_script_dirs for any on-disk marker state.
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
        # tree"; select_live_version_dir decides liveness and ordering.
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
