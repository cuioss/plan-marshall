# SPDX-License-Identifier: FSL-1.1-ALv2
"""Plugin pin-trap detector.

Three stores must agree about which plugin-cache version is live: the **cache**
directories (with their ``.orphaned_at`` markers), the plugin **registry**
(``installPath`` + ``version`` per entry), and the generated **executor**. When
they disagree, a stale read can seat a session on a retired version — a pin gap
that manufactures a false-green at the merge boundary.

What this module owns is DETECTION, never repair. The registry is the plugin
manager's file; this detector **writes nothing**. Repair is operator-only and is
stated as text (see the ``REMEDY_*`` constants and :func:`Verdict.remedy`).

The oracle (``evaluate``) is a pure function over two :class:`StoreObservation`
snapshots. Its design encodes lessons each learned from a check being wrong in
production:

* It gates load-safety on ``executor == installPath`` and **names the field it
  read** (``installPath``) — an unnamed "the pin" is unfalsifiable.
* It asserts ``installPath == version`` as a **separate** conjunct — a registry
  disagreeing with itself is a distinct defect from one disagreeing with the
  cache.
* It treats the unmarked set as **registry-derived, not an independent witness**
  (the foreign GC forces it into agreement with the registry), and uses it only
  to detect the post-sync GC-exposure window.
* It compares pin content against source as **"N of M files match; K diverge"**,
  never a boolean, and **degrades honestly** — a partial scan says so.
* It **double-samples**: two observations taken seconds apart must agree, or the
  verdict is ``indeterminate`` (a survey is a read-during-write; the false FAIL
  is the dangerous direction because it acts).
* ``indeterminate`` is its **own outcome**, distinct from both pass and fail.
* It reports its **sampling instant**, the **population size**, and the **newest
  marker's age** — so "the sweep saturated" is distinguishable from "nothing has
  been marked yet".
* It reports **divergence and GC-exposure as separate axes**, so shape 6
  (divergence without GC exposure — "repair when convenient") does not rank
  alongside shape 1 (saturation — "repair before the fuse burns").

The live filesystem adapters (``observe_*``, ``read_*``, ``compare_pin_content``)
read the three stores into these structures. The live plugin cache is not present
in a fresh clone, so the module is exercised against FIXTURE trees; the adapters
are written to be driven by ``tmp_path`` fixtures rather than the operator's
machine.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Version-key — MIRRORS marketplace_bundles._version_sort_key semantics.
# The executor's embedded resolver and the shared selector both order version
# dirs by digit-run tuples ('0.1.1069' -> (0, 1, 1069)); the loader-selection
# model below (D4) must order identically, so it re-derives the same key here.
# ---------------------------------------------------------------------------
_DIGITS_RE = re.compile(r'\d+')
_VERSION_DIR_RE = re.compile(r'^\d+\.\d+')

# The marker file whose EXISTENCE (never content) flags a version dir orphaned.
ORPHAN_MARKER_NAME = '.orphaned_at'


def _version_key(name: str) -> tuple[int, ...]:
    """Digit-run tuple for ``name`` (matches ``marketplace_bundles._version_sort_key``)."""
    return tuple(int(part) for part in _DIGITS_RE.findall(name))


# ---------------------------------------------------------------------------
# Outcomes and shape codes
# ---------------------------------------------------------------------------
OUTCOME_PASS = 'pass'
OUTCOME_FAIL = 'fail'
OUTCOME_INDETERMINATE = 'indeterminate'

SHAPE_1_SATURATION = 'shape1:empty-unmarked-set'
SHAPE_2_PIN_MARKED_NEWER_UNMARKED = 'shape2:pin-orphan-marked-newer-unmarked'
SHAPE_3_STALE_UNMARKED_BESIDE_PIN = 'shape3:stale-unmarked-beside-pin'
SHAPE_4_PIN_DIVERGES_FROM_SOURCE = 'shape4:pin-diverges-from-source'
SHAPE_5_REGISTRY_SELF_DISAGREES = 'shape5:registry-installPath-vs-version'
SHAPE_6_DIVERGENCE_NO_GC = 'shape6:divergence-without-gc-exposure'

# The load-safety gate reads THIS registry field; the verdict names it so the
# check is falsifiable rather than depending on an unstated choice of "the pin".
GATE_FIELD = 'installPath'

_UNMARKED_DERIVED_NOTE = (
    'The unmarked set is REGISTRY-DERIVED, not an independent witness: the foreign '
    'garbage collector deletes the marker from the registry installPath directory '
    'and marks every other, so it lags the registry. It is used here only to detect '
    'the post-sync GC-exposure window, never as corroboration of installPath.'
)

_SESSION_SEATING_NOTE = (
    'This store triad does NOT measure the session\'s own seating (the body loaded '
    'at session start). That value appears in neither the registry, the executor, '
    'nor the marker set; use assert_loaded_version() against the loader\'s announced '
    'base directory to check the in-run loaded body.'
)

_AXES_NOTE = (
    'Divergence and GC-exposure are reported as SEPARATE axes. A divergence without '
    'GC exposure (shape 6) is "repair when convenient"; saturation (shape 1) is '
    '"repair before the fuse burns".'
)

# ---------------------------------------------------------------------------
# Operator remedy text (D3) — stated, never implied. The detector reports what
# to run; a session restart does NOT fix it; the in-run remedy is to read the
# pinned skill file directly.
# ---------------------------------------------------------------------------
REMEDY_OPERATOR = (
    'Repair is operator-only — this detector writes nothing. To repair the cache and '
    'executor: (1) re-run the cache sync (`/sync-plugin-cache`) to move the cache '
    'forward; (2) prune the superseded version dirs with the marshall-steward '
    'cache-retention sweep (`plan-marshall:marshall-steward:cache_retention sweep`); '
    '(3) regenerate the executor. Do NOT write the plugin registry — it is the plugin '
    "manager's file, and a second writer is a defect in its own right."
)
REMEDY_NO_RESTART = (
    'A session restart does NOT fix this: the loaded registry keeps serving the stale '
    'body when asked, hours later, regardless of a restart.'
)
REMEDY_IN_RUN_TEMPLATE = (
    'In-run remedy: read the pinned skill file DIRECTLY from the registry installPath '
    '({install_path}) rather than trusting the loader\'s resolved body.'
)
REMEDY_RESAMPLE = (
    'Indeterminate is not a pass: re-sample (the stores were mid-write, or a store '
    'could not be read). Do not launch on an indeterminate verdict without resolving '
    'it — a false clean here is the failure this detector exists to prevent.'
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class VersionDir:
    """One plugin-cache version directory and whether it carries the orphan marker.

    ``marked`` records only the EXISTENCE of ``.orphaned_at`` — its content is
    never read, because the field has a foreign co-producer (Claude Code's GC
    writes epoch-ms; our writer writes ISO-8601) and a content-dependent rule
    would bind this detector to a format the repository does not own.
    """

    name: str
    marked: bool


@dataclass(frozen=True)
class ContentComparison:
    """Pin-content-vs-source comparison, reported as a count and never a boolean.

    ``matched`` of ``total`` source files hashed identically in the pin dir;
    ``diverged`` is the remainder of the SCANNED files. ``scanned`` defaults to
    ``total`` (a full scan); a smaller value marks a partial scan, which
    :meth:`render` states explicitly so a degraded comparison can never read as
    clean.
    """

    matched: int
    total: int
    diverged: int
    scanned: int | None = None

    @property
    def _scanned(self) -> int:
        return self.total if self.scanned is None else self.scanned

    @property
    def partial(self) -> bool:
        return self._scanned < self.total

    def render(self) -> str:
        base = f'{self.matched} of {self.total} files match; {self.diverged} diverge'
        if self.partial:
            base += f' (PARTIAL scan: {self._scanned} of {self.total} scanned)'
        return base


@dataclass(frozen=True)
class StoreObservation:
    """One snapshot of the three stores at a single instant.

    ``None`` fields mean the store could not be read — a state the oracle keeps
    distinct from both pass and fail. ``version_dirs`` is the cache population;
    ``content`` is the installPath dir compared against source (``None`` when not
    compared). ``newest_marker_age_seconds`` is REPORTED for diagnosis, never fed
    into the oracle decision (an age-based staleness heuristic is out of scope —
    markers get re-written, resetting apparent age).
    """

    executor_version: str | None
    install_path_version: str | None
    registry_version: str | None
    version_dirs: tuple[VersionDir, ...]
    content: ContentComparison | None = None
    newest_marker_age_seconds: float | None = None


@dataclass(frozen=True)
class Verdict:
    """The detector's verdict — an outcome plus the evidence it was derived from."""

    outcome: str
    reason: str
    shapes: tuple[str, ...] = ()
    divergences: tuple[str, ...] = ()
    gc_exposures: tuple[str, ...] = ()
    field_read: str = GATE_FIELD
    loader_selected_version: str | None = None
    content: str | None = None
    sampling_instant: str = ''
    population_size: int = 0
    newest_marker_age_seconds: float | None = None
    remedy: str = ''
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            'outcome': self.outcome,
            'reason': self.reason,
            'shapes': list(self.shapes),
            'divergences': list(self.divergences),
            'gc_exposures': list(self.gc_exposures),
            'field_read': self.field_read,
            'loader_selected_version': self.loader_selected_version,
            'content': self.content,
            'sampling_instant': self.sampling_instant,
            'population_size': self.population_size,
            'newest_marker_age_seconds': self.newest_marker_age_seconds,
            'remedy': self.remedy,
            'notes': list(self.notes),
        }


@dataclass(frozen=True)
class LoadedVersionVerdict:
    """Result of the mid-run assertion that a loaded body came from the pin (D2)."""

    outcome: str
    got_version: str | None
    expected_version: str
    reason: str
    remedy: str = ''

    def to_dict(self) -> dict:
        return {
            'outcome': self.outcome,
            'got_version': self.got_version,
            'expected_version': self.expected_version,
            'reason': self.reason,
            'remedy': self.remedy,
        }


# ---------------------------------------------------------------------------
# Derived facts
# ---------------------------------------------------------------------------
def _unmarked(dirs: tuple[VersionDir, ...]) -> list[VersionDir]:
    return [d for d in dirs if not d.marked]


def loader_selected_version(dirs: tuple[VersionDir, ...]) -> str | None:
    """The version dir the LOADER actually follows — established from the selector code.

    Mirrors ``marketplace_bundles.select_live_version_dir`` (D4): the newest-on-disk
    dir is retention-pinned and its marker is ignored outright; among the resulting
    live set (unmarked dirs plus that pin) the numerically-highest version-key wins;
    when every dir is marked the newest overall is the degraded fallback.

    The load-bearing consequence, and why D1 must NOT assume the loader resolves to
    the registry pin: with two unmarked dirs the loader follows the higher
    version-KEY, which can be a directory whose NAME sorts high while its CONTENT is
    stale — so the loaded dir and the registry ``installPath`` can diverge.
    """
    if not dirs:
        return None
    pinned = max(dirs, key=lambda d: _version_key(d.name))
    live = [d for d in dirs if d.name == pinned.name or not d.marked]
    pool = live or list(dirs)
    return max(pool, key=lambda d: _version_key(d.name)).name


def _volatile_signature(obs: StoreObservation) -> tuple:
    """The facts that a read-during-write can flip between two samples.

    The marker set is the volatile one the double-sample guards; the registry and
    executor reads are included so a mid-write to any of them also forces
    ``indeterminate`` rather than a verdict over an inconsistent snapshot.
    """
    return (
        tuple(sorted((d.name, d.marked) for d in obs.version_dirs)),
        obs.install_path_version,
        obs.registry_version,
        obs.executor_version,
    )


# ---------------------------------------------------------------------------
# The oracle
# ---------------------------------------------------------------------------
def evaluate(
    sample_a: StoreObservation,
    sample_b: StoreObservation,
    *,
    sampling_instant: str,
) -> Verdict:
    """Double-sampled six-shape oracle over two store snapshots.

    The two samples MUST agree on their volatile facts; disagreement yields
    ``indeterminate`` (a read-during-write, whose false FAIL is the dangerous
    direction because it triggers action). On agreement the single-sample oracle
    runs over ``sample_a``.
    """
    population = len(sample_a.version_dirs)
    if _volatile_signature(sample_a) != _volatile_signature(sample_b):
        return Verdict(
            outcome=OUTCOME_INDETERMINATE,
            reason=(
                'read_during_write: the two samples disagreed, so the stores were '
                'mid-write. No verdict is issued over an inconsistent snapshot.'
            ),
            loader_selected_version=loader_selected_version(sample_a.version_dirs),
            sampling_instant=sampling_instant,
            population_size=population,
            newest_marker_age_seconds=sample_a.newest_marker_age_seconds,
            remedy=REMEDY_RESAMPLE,
            notes=(_UNMARKED_DERIVED_NOTE, _AXES_NOTE, _SESSION_SEATING_NOTE),
        )
    return _evaluate_single(sample_a, sampling_instant)


def _evaluate_single(obs: StoreObservation, sampling_instant: str) -> Verdict:
    dirs = obs.version_dirs
    unmarked = _unmarked(dirs)
    unmarked_names = {d.name for d in unmarked}
    ipv = obs.install_path_version
    rv = obs.registry_version
    ev = obs.executor_version
    content = obs.content
    loader = loader_selected_version(dirs)

    shapes: list[str] = []
    divergences: list[str] = []
    gc_exposures: list[str] = []

    # --- Divergence axis (stores disagree about the live/correct version) ---
    # Conjunct 1 — load-safety gate, naming the field it read.
    if ev is not None and ipv is not None and ev != ipv:
        divergences.append(f'executor({ev}) != {GATE_FIELD}({ipv})')
    # Conjunct 2 — registry self-consistency, a SEPARATE conjunct.
    if ipv is not None and rv is not None and ipv != rv:
        divergences.append(f'{GATE_FIELD}({ipv}) != version({rv})')
        shapes.append(SHAPE_5_REGISTRY_SELF_DISAGREES)
    # D4 — the loader follows a dir other than the registry pin.
    if loader is not None and ipv is not None and loader != ipv:
        divergences.append(f'loader_selected({loader}) != {GATE_FIELD}({ipv})')
    # Conjunct 4 — content vs source, as a count, never a boolean.
    if content is not None and content.diverged > 0:
        divergences.append(f'pin content diverges from source: {content.render()}')

    # --- GC-exposure axis (a load-bearing dir is orphan-marked, or saturation) ---
    pin_dir = next((d for d in dirs if d.name == ipv), None) if ipv is not None else None
    if dirs and not unmarked:
        gc_exposures.append('saturation: every eligible version dir carries .orphaned_at')
        shapes.append(SHAPE_1_SATURATION)
    if pin_dir is not None and pin_dir.marked:
        gc_exposures.append(f'{GATE_FIELD} dir {pin_dir.name} is orphan-marked (scheduled for deletion)')
        pin_key = _version_key(pin_dir.name)
        newer_unmarked = [d for d in unmarked if _version_key(d.name) > pin_key]
        if newer_unmarked:
            shapes.append(SHAPE_2_PIN_MARKED_NEWER_UNMARKED)

    # --- Shape 3: two+ unmarked and the loader follows a dir other than the pin ---
    if len(unmarked) >= 2 and ipv is not None and loader is not None and loader != ipv:
        shapes.append(SHAPE_3_STALE_UNMARKED_BESIDE_PIN)

    # --- Shape 4: the ONLY unmarked dir IS the pin, yet the pin diverges from source ---
    if ipv is not None and unmarked_names == {ipv} and content is not None and content.diverged > 0:
        shapes.append(SHAPE_4_PIN_DIVERGES_FROM_SOURCE)

    # --- Shape 6: a cache-selection divergence with NO GC exposure ("repair when
    # convenient"), and not already explained by the specific shapes 3/4. It is
    # the RESIDUAL of the divergence axis restricted to the live-dir selection
    # (executor / loader / content) — the registry-self disagreement (shape 5) is
    # orthogonal and does not raise it. Kept distinct from shape 1 by the
    # not-gc_exposures guard: saturation always carries a GC exposure.
    cache_divergence = (
        (ev is not None and ipv is not None and ev != ipv)
        or (loader is not None and ipv is not None and loader != ipv)
        or (content is not None and content.diverged > 0)
    )
    already_specific = any(
        s in shapes for s in (SHAPE_3_STALE_UNMARKED_BESIDE_PIN, SHAPE_4_PIN_DIVERGES_FROM_SOURCE)
    )
    if cache_divergence and not gc_exposures and not already_specific:
        shapes.append(SHAPE_6_DIVERGENCE_NO_GC)

    # --- Outcome: fail wins; then could-not-look; then content-not-compared; then pass ---
    unreadable: list[str] = []
    if ev is None:
        unreadable.append('executor')
    if ipv is None:
        unreadable.append(f'registry.{GATE_FIELD}')
    if rv is None:
        unreadable.append('registry.version')
    if not dirs:
        unreadable.append('cache (no version dirs)')

    # Deduplicate while preserving order (shape 5 / saturation may be added twice
    # across the two axes above; a shape is reported once).
    shapes = list(dict.fromkeys(shapes))

    if shapes or divergences or gc_exposures:
        outcome = OUTCOME_FAIL
        reason = 'pin gap detected: the three stores do not agree'
        if unreadable:
            reason += f' (and could not read: {", ".join(unreadable)})'
        remedy = _fail_remedy(ipv)
    elif unreadable:
        outcome = OUTCOME_INDETERMINATE
        reason = f'could_not_look: {", ".join(unreadable)}'
        remedy = REMEDY_RESAMPLE
    elif content is None:
        outcome = OUTCOME_INDETERMINATE
        reason = 'could_not_look: pin content was not compared against source'
        remedy = REMEDY_RESAMPLE
    else:
        outcome = OUTCOME_PASS
        reason = 'all three stores agree and the pin content matches source'
        remedy = ''

    return Verdict(
        outcome=outcome,
        reason=reason,
        shapes=tuple(shapes),
        divergences=tuple(divergences),
        gc_exposures=tuple(gc_exposures),
        field_read=GATE_FIELD,
        loader_selected_version=loader,
        content=content.render() if content is not None else None,
        sampling_instant=sampling_instant,
        population_size=len(dirs),
        newest_marker_age_seconds=obs.newest_marker_age_seconds,
        remedy=remedy,
        notes=(_UNMARKED_DERIVED_NOTE, _AXES_NOTE, _SESSION_SEATING_NOTE),
    )


def _fail_remedy(install_path_version: str | None) -> str:
    install = install_path_version or '<the registry installPath>'
    return ' '.join(
        (
            REMEDY_OPERATOR,
            REMEDY_NO_RESTART,
            REMEDY_IN_RUN_TEMPLATE.format(install_path=install),
        )
    )


# ---------------------------------------------------------------------------
# D2 — mid-run assertion that a loaded body came from the pinned version
# ---------------------------------------------------------------------------
def _version_from_announced_path(path_str: str) -> str | None:
    """Extract the version-dir segment from a loader-announced base directory string.

    The loader announces a path like
    ``~/.claude/plugins/cache/plan-marshall/0.1.1069/skills/{skill}/...``. The
    version dir is the segment immediately preceding ``skills``; when that anchor
    is absent, the last version-shaped segment is used. Returns ``None`` when no
    version-shaped segment is present, so a string the assertion cannot parse
    yields ``indeterminate`` rather than a false verdict.
    """
    parts = Path(path_str).parts
    if 'skills' in parts:
        idx = parts.index('skills')
        if idx > 0 and _VERSION_DIR_RE.match(parts[idx - 1]):
            return parts[idx - 1]
    version_segments = [p for p in parts if _VERSION_DIR_RE.match(p)]
    return version_segments[-1] if version_segments else None


def assert_loaded_version(announced_base_dir: str, pinned_version: str) -> LoadedVersionVerdict:
    """Assert a loaded skill body came from ``pinned_version`` (D2).

    A pre-launch pin check is necessary but not sufficient — a session can be
    seated on a stale body and only reveal it hours later, from inside its own
    dispatch. The loader announces its base directory; that string is the
    available evidence. This assertion FAILS CLOSED and states which version it
    got, rather than proceeding with a body from a version dozens behind.
    """
    got = _version_from_announced_path(announced_base_dir)
    if got is None:
        return LoadedVersionVerdict(
            outcome=OUTCOME_INDETERMINATE,
            got_version=None,
            expected_version=pinned_version,
            reason=(
                'could_not_look: the announced base directory carries no version '
                f'segment ({announced_base_dir!r}), so the loaded version is unknown.'
            ),
            remedy=REMEDY_RESAMPLE,
        )
    if got != pinned_version:
        return LoadedVersionVerdict(
            outcome=OUTCOME_FAIL,
            got_version=got,
            expected_version=pinned_version,
            reason=(
                f'loaded body came from {got}, NOT the pinned {pinned_version}. '
                'The loaded registry served a superseded body.'
            ),
            remedy=REMEDY_NO_RESTART + ' ' + REMEDY_IN_RUN_TEMPLATE.format(install_path=pinned_version),
        )
    return LoadedVersionVerdict(
        outcome=OUTCOME_PASS,
        got_version=got,
        expected_version=pinned_version,
        reason=f'loaded body matches the pin ({got}).',
    )


# ---------------------------------------------------------------------------
# Live filesystem adapters (I/O) — driven by fixture trees, since the live
# plugin cache is absent from a fresh clone.
# ---------------------------------------------------------------------------
def observe_cache_version_dirs(
    bundle_dir: Path,
    *,
    now: datetime | None = None,
) -> tuple[tuple[VersionDir, ...], float | None]:
    """Read the version dirs under ``bundle_dir`` with their orphan-marker state.

    Returns ``(version_dirs, newest_marker_age_seconds)``. Only the EXISTENCE of
    ``.orphaned_at`` is consulted; the newest marker's age is computed from mtimes
    for diagnosis only. A dotfile / non-directory entry is skipped. A read failure
    degrades to an empty tuple (the oracle then reports the cache as unreadable),
    never a crash.
    """
    stamp = now or datetime.now(UTC)
    try:
        entries = sorted(p for p in bundle_dir.iterdir() if p.is_dir() and not p.name.startswith('.'))
    except OSError:
        return (), None
    dirs: list[VersionDir] = []
    newest_marker_mtime: float | None = None
    for entry in entries:
        marker = entry / ORPHAN_MARKER_NAME
        marked = marker.exists()
        dirs.append(VersionDir(name=entry.name, marked=marked))
        if marked:
            try:
                mtime = marker.stat().st_mtime
            except OSError:
                mtime = None
            if mtime is not None and (newest_marker_mtime is None or mtime > newest_marker_mtime):
                newest_marker_mtime = mtime
    age = None if newest_marker_mtime is None else max(0.0, stamp.timestamp() - newest_marker_mtime)
    return tuple(dirs), age


def read_registry_entry(registry_path: Path, plugin_name: str) -> tuple[str | None, str | None]:
    """Read ``(installPath_version, version)`` for ``plugin_name`` from the registry.

    The registry is the plugin manager's JSON file, whose entries carry an
    ``installPath`` (a path ending in the version dir) and a ``version`` string.
    The exact nesting is the manager's to define and cannot be verified from a
    fresh clone, so this reader is deliberately liberal: it accepts the entries as
    a top-level object keyed by plugin name, or under a ``plugins`` key, or as a
    list of objects each carrying a ``name``. ``installPath_version`` is the
    basename of ``installPath``. Either field is ``None`` when absent or
    unreadable — the oracle then reports the registry as unreadable rather than
    inventing agreement.
    """
    try:
        data = json.loads(registry_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None, None
    entry = _find_registry_entry(data, plugin_name)
    if not isinstance(entry, dict):
        return None, None
    install_path = entry.get('installPath')
    version = entry.get('version')
    install_version = Path(install_path).name if isinstance(install_path, str) and install_path else None
    version = version if isinstance(version, str) and version else None
    return install_version, version


def _find_registry_entry(data: object, plugin_name: str) -> object:
    if isinstance(data, dict):
        if plugin_name in data:
            return data[plugin_name]
        plugins = data.get('plugins')
        if isinstance(plugins, dict) and plugin_name in plugins:
            return plugins[plugin_name]
        if isinstance(plugins, list):
            return _find_in_list(plugins, plugin_name)
    if isinstance(data, list):
        return _find_in_list(data, plugin_name)
    return None


def _find_in_list(items: list, plugin_name: str) -> object:
    for item in items:
        if isinstance(item, dict) and item.get('name') == plugin_name:
            return item
    return None


def read_executor_anchored_version(executor_path: Path) -> str | None:
    """Extract the plugin-cache version dir the executor's embedded paths anchor at.

    The generated executor embeds absolute script paths under
    ``.../cache/{plugin}/{version}/skills/...``. This scans the executor text for
    those version segments and returns the single version they agree on; it
    returns ``None`` when the file is unreadable or carries no such segment (the
    marketplace-layout executor, or a corrupt one), and — fail-closed — when the
    embedded paths disagree on the version (an internally version-split executor
    is not a single anchored version).
    """
    try:
        text = executor_path.read_text(encoding='utf-8')
    except OSError:
        return None
    versions = set(re.findall(r'/cache/[^/]+/(\d+\.\d+[^/\'"]*)/skills/', text))
    if len(versions) == 1:
        return str(next(iter(versions)))
    return None


def compare_pin_content(pin_dir: Path, source_dir: Path) -> ContentComparison:
    """Compare every source file against its counterpart in the pin dir, by bytes.

    Returns a count — "N of M match; K diverge" — never a boolean, so a
    divergence on a handful of files is actionable rather than laundered into
    "stale". A file that cannot be read on either side is counted as scanned-but-
    not-matched AND marks the scan partial, so a degraded comparison never reads
    as clean. ``total`` is the number of source files (the M the pin is measured
    against).
    """
    try:
        source_files = sorted(p for p in source_dir.rglob('*') if p.is_file())
    except OSError:
        return ContentComparison(matched=0, total=0, diverged=0, scanned=0)
    total = len(source_files)
    matched = 0
    scanned = 0
    unreadable = 0
    for src in source_files:
        rel = src.relative_to(source_dir)
        counterpart = pin_dir / rel
        try:
            src_bytes = src.read_bytes()
            pin_bytes = counterpart.read_bytes()
        except OSError:
            unreadable += 1
            continue
        scanned += 1
        if src_bytes == pin_bytes:
            matched += 1
    diverged = scanned - matched
    scanned_total = scanned + unreadable
    return ContentComparison(
        matched=matched,
        total=total,
        diverged=diverged + unreadable,
        scanned=scanned_total if scanned_total < total or unreadable else None,
    )


def observe(
    *,
    cache_bundle_dir: Path,
    registry_path: Path,
    plugin_name: str,
    executor_path: Path,
    source_dir: Path | None = None,
    now: datetime | None = None,
) -> StoreObservation:
    """Assemble a :class:`StoreObservation` by reading the three live stores.

    ``source_dir`` enables the content conjunct: when given (and the installPath
    dir is present), the pin's content is compared against it; otherwise
    ``content`` is ``None`` and the oracle reports the content axis as
    not-compared (an ``indeterminate`` driver, never a silent pass).
    """
    version_dirs, marker_age = observe_cache_version_dirs(cache_bundle_dir, now=now)
    install_version, registry_version = read_registry_entry(registry_path, plugin_name)
    executor_version = read_executor_anchored_version(executor_path)
    content: ContentComparison | None = None
    if source_dir is not None and install_version is not None:
        pin_dir = cache_bundle_dir / install_version
        if pin_dir.is_dir():
            content = compare_pin_content(pin_dir, source_dir)
    return StoreObservation(
        executor_version=executor_version,
        install_path_version=install_version,
        registry_version=registry_version,
        version_dirs=version_dirs,
        content=content,
        newest_marker_age_seconds=marker_age,
    )


__all__ = [
    'ContentComparison',
    'GATE_FIELD',
    'LoadedVersionVerdict',
    'OUTCOME_FAIL',
    'OUTCOME_INDETERMINATE',
    'OUTCOME_PASS',
    'SHAPE_1_SATURATION',
    'SHAPE_2_PIN_MARKED_NEWER_UNMARKED',
    'SHAPE_3_STALE_UNMARKED_BESIDE_PIN',
    'SHAPE_4_PIN_DIVERGES_FROM_SOURCE',
    'SHAPE_5_REGISTRY_SELF_DISAGREES',
    'SHAPE_6_DIVERGENCE_NO_GC',
    'StoreObservation',
    'Verdict',
    'VersionDir',
    'assert_loaded_version',
    'compare_pin_content',
    'evaluate',
    'loader_selected_version',
    'observe',
    'observe_cache_version_dirs',
    'read_executor_anchored_version',
    'read_registry_entry',
]
