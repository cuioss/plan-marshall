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
  to detect the post-sync GC-exposure window. **This repository's version
  selection does not consult the orphan marker at all** — see
  :func:`loader_selected_version` — so the marker set says nothing about which
  dir a session loads.
* It compares pin content against source as **"N of M files match; K diverge"**,
  never a boolean, and **degrades honestly** — a partial scan says so.
* It **double-samples**: two observations taken seconds apart must agree, or the
  verdict is ``indeterminate`` (a survey is a read-during-write; the false FAIL
  is the dangerous direction because it acts).
* ``indeterminate`` is its **own outcome**, distinct from both pass and fail.
* It reports its **sampling instant**, the **population size**, and the **newest
  marker's age** — so "the sweep saturated" is distinguishable from "nothing has
  been marked yet".
* It reports **divergence and GC-exposure as separate axes**, and saturation
  (shape 1) is REPORTED without failing the load-safety gate: the loader never
  reads the marker, so a fully-marked cache still resolves to the newest
  eligible dir and seats no session on the wrong body. It stays a GC-exposure
  observation because the foreign collector may delete those dirs.

Shape 3 and the tree it was named for
-------------------------------------
The shape-3 condition this module implements is *"two or more unmarked dirs AND
the loader resolves to a dir other than the registry pin"*
(:data:`SHAPE_3_LOADER_FOLLOWS_NON_PIN_DIR`). Under newest-eligible-wins that can
only fire when a NON-pin dir sorts HIGHER than the pin.

The literal tree the originating plan's "shape 3" described — an older stale
unmarked dir sitting beside a correct, NEWEST pin — is therefore a **PASS**, and
the ``test_shape3_literal_older_stale_beside_newest_pin_is_a_pass`` test pins
that. It is a pass because nothing is mis-seated: the loader already follows the
pin, and the older dir is unreachable. Whether that tree should nonetheless be
reported — it is equally the benign window right after a sync, before the
retention sweep runs — is a POLICY question about what counts as a finding, not
a defect. It is recorded as a proposal for an operator rather than decided here.

The live filesystem adapters (``observe_*``, ``read_*``, ``compare_pin_content``)
read the three stores into these structures. The live plugin cache is not present
in a fresh clone, so the module is exercised against FIXTURE trees; the adapters
are written to be driven by ``tmp_path`` fixtures rather than the operator's
machine.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
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
# Named for the condition the code EVALUATES, not for the tree the plan's shape 3
# described. The condition is "two or more unmarked dirs AND the loader resolves to
# a dir other than the registry pin" — which under newest-eligible-wins can only
# fire when a NON-pin dir sorts HIGHER than the pin. The literal tree shape 3 was
# written about (an older stale unmarked dir beside a correct NEWEST pin) is
# therefore a PASS: the loader already follows the pin, so nothing is mis-seated.
# Whether that tree should nonetheless be reported is a policy question, recorded
# as a proposal rather than decided here.
SHAPE_3_LOADER_FOLLOWS_NON_PIN_DIR = 'shape3:loader-follows-non-pin-dir'
SHAPE_4_PIN_DIVERGES_FROM_SOURCE = 'shape4:pin-diverges-from-source'
SHAPE_5_REGISTRY_SELF_DISAGREES = 'shape5:registry-installPath-vs-version'
SHAPE_6_DIVERGENCE_NO_GC = 'shape6:divergence-without-gc-exposure'

# Shapes that are REPORTED but do not fail the load-safety gate. Saturation was
# ranked as a failure — and in the repair-urgently tier — while the loader was
# believed to consult the orphan marker. It does not: with every dir marked, the
# newest eligible dir is still what resolves, so a saturated cache seats no
# session on the wrong body. It stays on the GC-exposure axis because the foreign
# collector may delete those dirs.
NON_BLOCKING_SHAPES = frozenset({SHAPE_1_SATURATION})

# The load-safety gate reads THIS registry field; the verdict names it so the
# check is falsifiable rather than depending on an unstated choice of "the pin".
GATE_FIELD = 'installPath'

# Executor-anchor statuses. The three non-anchored states are kept DISTINCT
# because they call for opposite handling: a split executor was read successfully
# and is internally inconsistent (a divergence the oracle must FAIL on), while an
# unreadable or unanchored one is a store the run could not look at (an
# ``indeterminate`` driver). Collapsing all three to ``None`` — the shape this
# reader had before — silently filed a demonstrated disagreement as "could not
# look", which is the false-clean direction.
EXECUTOR_ANCHORED = 'anchored'
EXECUTOR_UNREADABLE = 'unreadable'
EXECUTOR_NO_ANCHOR = 'no_anchor'
EXECUTOR_SPLIT = 'split'

_UNMARKED_DERIVED_NOTE = (
    'The unmarked set is REGISTRY-DERIVED, not an independent witness: the FOREIGN '
    'garbage collector deletes the marker from the registry installPath directory '
    'and marks every other, so it lags the registry. Its ONLY use here is the '
    'GC-EXPOSURE axis — which dirs the foreign collector has scheduled for '
    'deletion. It is never corroboration of installPath, and it says nothing about '
    'which dir the loader follows: this repository\'s version selection does not '
    'consult the marker at all.'
)

_SESSION_SEATING_NOTE = (
    'This store triad does NOT measure the session\'s own seating (the body loaded '
    'at session start). That value appears in neither the registry, the executor, '
    'nor the marker set; use assert_loaded_version() against the loader\'s announced '
    'base directory to check the in-run loaded body.'
)

_AXES_NOTE = (
    'Divergence and GC-exposure are reported as SEPARATE axes. Saturation (shape 1) '
    'is REPORTED but does not by itself fail the load-safety gate: the loader never '
    'reads the marker, so a fully-marked cache still resolves to the newest '
    'eligible dir. It remains a GC-exposure observation because the foreign '
    'collector may delete those dirs — a disk-space and availability concern, not a '
    'wrong-version-loaded one.'
)

# ---------------------------------------------------------------------------
# Operator remedy text (D3) — stated, never implied. The detector reports what
# to run; a session restart does NOT fix it; the in-run remedy is to read the
# pinned skill file directly.
# ---------------------------------------------------------------------------
# Every step names a command the operator can type AS GIVEN. That is stricter
# than naming a surface: the retention sweep is a read-only DRY RUN unless
# `--apply` is passed, so a remedy naming the bare verb would describe a prune
# that does not happen — an operator following it literally sees a clean report,
# no error, and moves on believing the cache was pruned.
REMEDY_OPERATOR = (
    'Repair is operator-only — this detector writes nothing. To repair the cache and '
    'executor: (1) re-run the cache sync (`/sync-plugin-cache`) to move the cache '
    'forward; (2) prune the superseded version dirs with the marshall-steward '
    'cache-retention sweep — `python3 .plan/execute-script.py '
    'plan-marshall:marshall-steward:cache_retention sweep --apply` (WITHOUT `--apply` '
    'the sweep is a read-only dry run and removes nothing); '
    '(3) regenerate the executor by re-running the steward wizard (`/marshall-steward`), '
    'which rewrites `.plan/execute-script.py` against the refreshed cache. '
    'Do NOT write the plugin registry — it is the plugin '
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

    ``matched`` of ``total`` paths hashed identically in the pin dir; ``diverged``
    is the remainder of the SCANNED paths. ``total`` is the size of the UNION of
    the source and pin path sets, so a file the pin carries and source does not —
    retired-file residue — is inside the denominator rather than invisible to it;
    ``extra_in_pin`` counts that subset and :meth:`render` reports it distinctly,
    so residue is never mistaken for a content edit.

    ``scanned`` defaults to ``total`` (a full scan); a smaller value marks a
    partial scan, which :meth:`render` states explicitly so a degraded comparison
    can never read as clean.

    A comparison that walked ZERO paths, or one whose source or pin side could
    not be enumerated, is UNUSABLE: it is evidence about nothing, and the oracle
    must not resolve it as a pass. :attr:`usable` is the predicate, and
    :attr:`unusable_because` carries the reason — which distinguishes an
    unreadable directory from a genuinely empty one, because the two call for
    different operator action.
    """

    matched: int
    total: int
    diverged: int
    scanned: int | None = None
    extra_in_pin: int = 0
    unusable_reason: str | None = None

    @property
    def scanned_count(self) -> int:
        """Paths actually read on both sides (``total`` when ``scanned`` is unset)."""
        return self.total if self.scanned is None else self.scanned

    @property
    def partial(self) -> bool:
        return self.scanned_count < self.total

    @property
    def unusable_because(self) -> str | None:
        """Why this comparison is not evidence, or ``None`` when it is.

        An explicitly recorded reason wins; a comparison over zero paths is
        unusable whether or not the adapter recorded why, so a hand-built
        ``ContentComparison(0, 0, 0)`` cannot satisfy a pass either.

        ⛔ A NON-EMPTY union none of whose paths could be read is the same
        nothing, and it was missing here. ``compare_pin_content`` reaches that
        state when every source-side ``read_bytes`` raises: the result carries
        ``total > 0`` with ``scanned == 0``, ``diverged == 0`` and no explicit
        reason, so ``usable`` was True, ``diverged > 0`` was False, and
        ``_evaluate_single`` resolved it as "the pin content matches source"
        after reading zero bytes. The COUNT of paths in the union is not
        evidence about their contents — the same false-clean direction this
        class rejects for a zero-path walk.
        """
        if self.unusable_reason is not None:
            return self.unusable_reason
        if self.total == 0:
            return (
                'empty_comparison: the comparison walked ZERO paths, so it is '
                'evidence about nothing'
            )
        if self.scanned_count == 0:
            return (
                f'nothing_scanned: all {self.total} paths in the union failed to '
                'read, so the byte comparison is evidence about nothing'
            )
        return None

    @property
    def usable(self) -> bool:
        """True when this comparison is evidence about at least one path."""
        return self.unusable_because is None

    def signature(self) -> tuple:
        """The counts a read-during-write can flip between two samples."""
        return (self.matched, self.total, self.diverged, self.scanned_count, self.extra_in_pin)

    def render(self) -> str:
        if not self.usable:
            return f'NOT COMPARABLE ({self.unusable_because})'
        base = f'{self.matched} of {self.total} files match; {self.diverged} diverge'
        if self.extra_in_pin:
            base += (
                f' ({self.extra_in_pin} present in the pin and ABSENT from source '
                '— retired-file residue, not a content edit)'
            )
        if self.partial:
            base += f' (PARTIAL scan: {self.scanned_count} of {self.total} scanned)'
        return base


@dataclass(frozen=True)
class ExecutorAnchor:
    """What the executor's embedded paths say about the version they anchor at.

    ``status`` is one of the four ``EXECUTOR_*`` constants. ``version`` is set
    only for :data:`EXECUTOR_ANCHORED`; ``versions`` carries every distinct
    version segment found, which is what makes a :data:`EXECUTOR_SPLIT` result
    reportable by name rather than as a bare "could not read".
    """

    status: str
    version: str | None = None
    versions: tuple[str, ...] = ()


@dataclass(frozen=True)
class StoreObservation:
    """One snapshot of the three stores at a single instant.

    ``None`` fields mean the store could not be read — a state the oracle keeps
    distinct from both pass and fail. ``version_dirs`` is the cache population;
    ``content`` is the installPath dir compared against source (``None`` when not
    compared). ``executor_anchor`` carries WHY ``executor_version`` is ``None``
    when it is, so a version-SPLIT executor is reported as the disagreement it is
    rather than as an unreadable store. ``eligible_versions`` is the set of dirs
    satisfying the loader's eligibility predicate for the subpath under test
    (``None`` when every dir is eligible), which is what lets the loader model
    reproduce a BACKWARD resolution rather than always resolving forward.
    ``newest_marker_age_seconds`` is REPORTED
    for diagnosis, never fed into the oracle decision (an age-based staleness
    heuristic is out of scope — markers get re-written, resetting apparent age).
    """

    executor_version: str | None
    install_path_version: str | None
    registry_version: str | None
    version_dirs: tuple[VersionDir, ...]
    content: ContentComparison | None = None
    newest_marker_age_seconds: float | None = None
    executor_anchor: ExecutorAnchor | None = None
    eligible_versions: frozenset[str] | None = None


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


def loader_selected_version(
    dirs: tuple[VersionDir, ...],
    eligible: frozenset[str] | None = None,
) -> str | None:
    """The version dir the LOADER actually follows — established from the selector code.

    Mirrors ``marketplace_bundles.select_live_version_dir``: among the version
    dirs that satisfy the caller's ELIGIBILITY predicate, the numerically-highest
    version-key wins. **The ``.orphaned_at`` marker is never consulted**, by that
    selector or by this model.

    The body once partitioned the dirs into a marker-exempt newest one and a set
    of unmarked ones, with a third branch for the all-marked case, and the
    docstring described a marker-aware selector to match. Both were fiction: the
    marker-exempt dir was ``max(dirs)``, it was unconditionally a member of the
    other set, and the maximum of a set containing its own maximum is that
    maximum — so every branch returned the newest dir on disk whatever any marker
    said. The model is now the one line it always evaluated.

    ``eligible`` restricts the pool to the version dirs that carry the subpath
    under test, mirroring the per-request predicate the real resolver supplies.
    ``None`` means every dir is eligible. An eligibility set that excludes every
    dir yields ``None`` — the selector's own loud failure, never a silent
    resolution to an ineligible dir.

    **Why the eligibility set matters, and why the divergence is reachable.**
    ``marketplace_bundles.resolve_bundle_path`` passes a PER-REQUEST predicate,
    ``lambda d: (d / subpath).exists()`` — so two requests in the same process
    can resolve to different version dirs, and a request for a subpath that
    exists ONLY in an older dir resolves BACKWARD to it. That is the incident
    this detector was built for. It is a different predicate from the one
    ``collect_script_dirs`` supplies for the PYTHONPATH walk,
    ``lambda d: (d / 'skills').is_dir()`` — a directory-existence test that is
    the same for every request and therefore resolves forward to the newest dir
    carrying a ``skills/`` tree. Modelling the loader without an eligibility set
    can only ever reproduce the second, and would report the first as agreement.
    """
    if not dirs:
        return None
    pool = [d for d in dirs if eligible is None or d.name in eligible]
    if not pool:
        return None
    return max(pool, key=lambda d: _version_key(d.name)).name


def _volatile_signature(obs: StoreObservation) -> tuple:
    """The facts that a read-during-write can flip between two samples.

    EVERY axis the oracle reads is included, because the double-sample guard's
    whole claim is that the two samples agreed — a claim it cannot make about an
    axis it never compared. The marker set is the volatile one the guard was
    built for; the registry and executor reads are here so a mid-write to either
    forces ``indeterminate``; the CONTENT counts are here because the content
    comparison is the longest read in the observation and therefore the axis most
    likely to straddle a write, and omitting it let the guard issue a confident
    verdict over two samples that demonstrably disagreed on it. The executor
    anchor's status and version set are included for the same reason: two
    differently-split executor reads both leave ``executor_version`` at ``None``
    and would otherwise compare equal. ``eligible_versions`` is here because
    ``_evaluate_single`` reads it to compute ``loader``, which drives both the
    loader divergence and ``SHAPE_3_LOADER_FOLLOWS_NON_PIN_DIR`` — and the gap
    was reachable: ``observe`` derives eligibility from whether the requested
    subpath EXISTS under each version dir, so a subpath materialising inside a
    non-pin dir between the two reads flips the selected loader while every
    other axis compares equal. The docstring claimed every axis was covered
    while this one had no mechanism behind the claim.
    """
    anchor = obs.executor_anchor
    return (
        tuple(sorted((d.name, d.marked) for d in obs.version_dirs)),
        obs.install_path_version,
        obs.registry_version,
        obs.executor_version,
        None if anchor is None else (anchor.status, anchor.versions),
        None if obs.content is None else obs.content.signature(),
        None if obs.eligible_versions is None else tuple(sorted(obs.eligible_versions)),
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

    ⛔ **Passing the SAME observation twice defeats the guard entirely.** The
    comparison then asserts that a value equals itself, which it always does, and
    the double-sample conjunct is satisfied without anything having been sampled
    twice. :func:`observe_twice` is the supported producer: it takes two
    independent reads separated by an injectable delay. ``observe`` returns one
    observation and is not a substitute for it.
    """
    population = len(sample_a.version_dirs)
    if _volatile_signature(sample_a) != _volatile_signature(sample_b):
        return Verdict(
            outcome=OUTCOME_INDETERMINATE,
            reason=(
                'read_during_write: the two samples disagreed, so the stores were '
                'mid-write. No verdict is issued over an inconsistent snapshot.'
            ),
            loader_selected_version=loader_selected_version(
                sample_a.version_dirs, sample_a.eligible_versions
            ),
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
    executor_anchor = obs.executor_anchor
    loader = loader_selected_version(dirs, obs.eligible_versions)

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
    # Conjunct 4 — content vs source, as a count, never a boolean. Gated on
    # `usable`: a comparison that walked zero paths has a `diverged` of 0 for the
    # same reason it has a `matched` of 0, so reading its silence as agreement
    # would issue a verdict over an axis nothing looked at.
    if content is not None and content.usable and content.diverged > 0:
        divergences.append(f'pin content diverges from source: {content.render()}')
    # Conjunct 5 — the executor read succeeded and its embedded paths disagree
    # with EACH OTHER. Distinct from an unreadable executor: this is a
    # demonstrated disagreement, so it belongs on the divergence axis rather than
    # on the could-not-look list.
    if executor_anchor is not None and executor_anchor.status == EXECUTOR_SPLIT:
        divergences.append(
            'executor is version-SPLIT across its embedded paths: '
            + ', '.join(executor_anchor.versions)
        )

    # --- GC-exposure axis (a load-bearing dir is orphan-marked, or saturation) ---
    # ``blocking_gc_exposures`` is the subset that FAILS the load-safety gate. The
    # two lists are built separately rather than filtered apart afterwards: a
    # filter keyed on the message text would silently stop excluding saturation
    # the moment anyone reworded it.
    blocking_gc_exposures: list[str] = []
    pin_dir = next((d for d in dirs if d.name == ipv), None) if ipv is not None else None
    if dirs and not unmarked:
        gc_exposures.append('saturation: every eligible version dir carries .orphaned_at')
        shapes.append(SHAPE_1_SATURATION)
    if pin_dir is not None and pin_dir.marked:
        exposure = f'{GATE_FIELD} dir {pin_dir.name} is orphan-marked (scheduled for deletion)'
        gc_exposures.append(exposure)
        blocking_gc_exposures.append(exposure)
        pin_key = _version_key(pin_dir.name)
        newer_unmarked = [d for d in unmarked if _version_key(d.name) > pin_key]
        if newer_unmarked:
            shapes.append(SHAPE_2_PIN_MARKED_NEWER_UNMARKED)

    # --- Shape 3: two+ unmarked and the loader follows a dir other than the pin ---
    if len(unmarked) >= 2 and ipv is not None and loader is not None and loader != ipv:
        shapes.append(SHAPE_3_LOADER_FOLLOWS_NON_PIN_DIR)

    # --- Shape 4: the ONLY unmarked dir IS the pin, yet the pin diverges from source ---
    if (
        ipv is not None
        and unmarked_names == {ipv}
        and content is not None
        and content.usable
        and content.diverged > 0
    ):
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
        or (content is not None and content.usable and content.diverged > 0)
    )
    already_specific = any(
        s in shapes for s in (SHAPE_3_LOADER_FOLLOWS_NON_PIN_DIR, SHAPE_4_PIN_DIVERGES_FROM_SOURCE)
    )
    if cache_divergence and not gc_exposures and not already_specific:
        shapes.append(SHAPE_6_DIVERGENCE_NO_GC)

    # --- Outcome: fail wins; then could-not-look; then content-not-compared; then pass ---
    unreadable: list[str] = []
    # A version-SPLIT executor is NOT unreadable — it was read, and it disagrees
    # with itself. It is reported on the divergence axis above.
    if ev is None and not (executor_anchor is not None and executor_anchor.status == EXECUTOR_SPLIT):
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

    # Saturation is reported on both the shape list and the GC-exposure axis but
    # does not fail the gate — see NON_BLOCKING_SHAPES. Everything else does.
    blocking_shapes = [s for s in shapes if s not in NON_BLOCKING_SHAPES]
    if blocking_shapes or divergences or blocking_gc_exposures:
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
    elif not content.usable:
        # The comparison ran and is not evidence — an unreadable directory, or a
        # walk over zero paths. Either way the content conjunct was never
        # actually tested, so the pass arm is unreachable from here.
        outcome = OUTCOME_INDETERMINATE
        reason = f'could_not_look: {content.unusable_because}'
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


def read_executor_anchored_version(executor_path: Path) -> ExecutorAnchor:
    """Read which plugin-cache version dir the executor's embedded paths anchor at.

    The generated executor embeds absolute script paths under
    ``.../cache/{plugin}/{version}/skills/...``. This scans the executor text for
    those version segments and reports one of four states, kept distinct because
    they are not the same fact about the executor:

    * :data:`EXECUTOR_ANCHORED` — the embedded paths agree on one version, which
      is carried in ``version``;
    * :data:`EXECUTOR_UNREADABLE` — the file could not be read at all;
    * :data:`EXECUTOR_NO_ANCHOR` — it was read and carries no such segment (the
      marketplace-layout executor, or a corrupt one);
    * :data:`EXECUTOR_SPLIT` — it was read and its embedded paths name MORE THAN
      ONE version. ``versions`` carries them all, so the oracle can name the
      conflict instead of filing a demonstrated disagreement as an unread store.

    Every non-anchored state leaves ``version`` at ``None``, so the load-safety
    gate stays fail-closed: an executor whose version is not established never
    satisfies ``executor == installPath``.
    """
    try:
        text = executor_path.read_text(encoding='utf-8')
    except OSError:
        return ExecutorAnchor(status=EXECUTOR_UNREADABLE)
    versions = tuple(sorted(set(re.findall(r'/cache/[^/]+/(\d+\.\d+[^/\'"]*)/skills/', text))))
    if len(versions) == 1:
        return ExecutorAnchor(status=EXECUTOR_ANCHORED, version=versions[0], versions=versions)
    if not versions:
        return ExecutorAnchor(status=EXECUTOR_NO_ANCHOR)
    return ExecutorAnchor(status=EXECUTOR_SPLIT, versions=versions)


def _relative_file_set(base: Path) -> set[Path] | None:
    """Every file under ``base``, as paths relative to it — ``None`` if unwalkable.

    ``None`` is a genuinely different answer from ``set()``: a directory that is
    ABSENT or could not be enumerated is unknown, while one that exists and holds
    nothing is known to be empty, and the comparison must not read the first as
    the second.

    The ``is_dir()`` test is load-bearing rather than defensive. ``rglob`` over a
    path that does not exist does NOT raise — it yields nothing — so relying on
    the ``OSError`` alone would report a missing directory as an empty one, which
    is the same launder-an-absence-into-an-observation defect this module exists
    to prevent, one level down.
    """
    try:
        if not base.is_dir():
            return None
        return {p.relative_to(base) for p in base.rglob('*') if p.is_file()}
    except OSError:
        return None


def compare_pin_content(pin_dir: Path, source_dir: Path) -> ContentComparison:
    """Compare the pin dir against source by bytes, over the UNION of both sides.

    Returns a count — "N of M match; K diverge" — never a boolean, so a
    divergence on a handful of files is actionable rather than laundered into
    "stale".

    ``total`` is the size of the union of the two path sets, NOT the source side
    alone. Enumerating only source made a pin dir that is a strict SUPERSET of it
    read as a complete match, which is exactly the retired-file residue this
    detector exists to catch: the extra files are counted into ``diverged`` and
    reported separately as ``extra_in_pin``.

    The three ways a path can fail to match are kept apart, because two of them
    are findings and the third is not:

    * the pin LACKS a source file, or holds different bytes → a divergence, and
      the path counts as scanned;
    * the pin holds a file source does not → a divergence and an ``extra_in_pin``;
    * a path could not be READ on either side → genuinely UNSCANNED, so the scan
      is partial and says so. Counting an unread path as diverged would fail on
      an axis nothing looked at.

    A comparison whose source or pin side is ABSENT or could not be enumerated,
    or that walks zero paths over two directories that both exist, is returned
    UNUSABLE with the reason recorded — the cases stay distinguishable, because a
    missing directory and an empty one call for different operator action.
    """
    source_rels = _relative_file_set(source_dir)
    if source_rels is None:
        return ContentComparison(
            matched=0,
            total=0,
            diverged=0,
            scanned=0,
            unusable_reason=(
                f'source_unreadable: {source_dir} is absent or could not be enumerated'
            ),
        )
    pin_rels = _relative_file_set(pin_dir)
    if pin_rels is None:
        return ContentComparison(
            matched=0,
            total=0,
            diverged=0,
            scanned=0,
            unusable_reason=(
                f'pin_unreadable: {pin_dir} is absent or could not be enumerated'
            ),
        )

    union = sorted(source_rels | pin_rels)
    total = len(union)
    if total == 0:
        return ContentComparison(
            matched=0,
            total=0,
            diverged=0,
            scanned=0,
            unusable_reason=(
                f'empty_comparison: neither {pin_dir} nor {source_dir} holds any '
                'file, so the comparison walked ZERO paths'
            ),
        )

    matched = 0
    diverged = 0
    unscanned = 0
    extra_in_pin = 0
    for rel in union:
        if rel not in source_rels:
            extra_in_pin += 1
            diverged += 1
            continue
        try:
            src_bytes = (source_dir / rel).read_bytes()
        except OSError:
            unscanned += 1
            continue
        try:
            pin_bytes = (pin_dir / rel).read_bytes()
        except FileNotFoundError:
            diverged += 1
            continue
        except OSError:
            unscanned += 1
            continue
        if src_bytes == pin_bytes:
            matched += 1
        else:
            diverged += 1

    return ContentComparison(
        matched=matched,
        total=total,
        diverged=diverged,
        scanned=total - unscanned,
        extra_in_pin=extra_in_pin,
    )


def observe(
    *,
    cache_bundle_dir: Path,
    registry_path: Path,
    plugin_name: str,
    executor_path: Path,
    source_dir: Path | None = None,
    now: datetime | None = None,
    subpath: str | None = None,
) -> StoreObservation:
    """Assemble a :class:`StoreObservation` by reading the three live stores.

    ``source_dir`` enables the content conjunct: when given (and the installPath
    dir is present), the pin's content is compared against it; otherwise
    ``content`` is ``None`` and the oracle reports the content axis as
    not-compared (an ``indeterminate`` driver, never a silent pass).

    ``subpath`` names the bundle-relative path a caller would actually request
    (``skills/{skill}/scripts/{script}.py``). When given, the eligibility set is
    populated from the version dirs that actually CARRY it — mirroring the
    per-request predicate ``marketplace_bundles.resolve_bundle_path`` supplies,
    which is the mechanism by which a resolution goes backward. Omitting it
    leaves every dir eligible, which models the PYTHONPATH walk's
    directory-existence predicate instead and cannot reproduce a backward
    resolution.
    """
    version_dirs, marker_age = observe_cache_version_dirs(cache_bundle_dir, now=now)
    eligible: frozenset[str] | None = None
    if subpath is not None:
        eligible = frozenset(
            d.name for d in version_dirs if (cache_bundle_dir / d.name / subpath).exists()
        )
    install_version, registry_version = read_registry_entry(registry_path, plugin_name)
    executor_anchor = read_executor_anchored_version(executor_path)
    executor_version = executor_anchor.version
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
        executor_anchor=executor_anchor,
        eligible_versions=eligible,
    )


def observe_twice(
    *,
    delay_seconds: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
    **observe_kwargs,
) -> tuple[StoreObservation, StoreObservation]:
    """Take the TWO observations :func:`evaluate` double-samples over.

    The double-sample guard has no meaning unless the two samples are genuinely
    independent reads separated in time. ``observe`` returns ONE observation, and
    nothing exported a paired variant — so every caller had to pass the same
    observation twice, which satisfies the guard by construction and reduces it
    to an assertion that a value equals itself.

    ``sleep`` is injected so a test can drive the pairing with a fake clock and a
    fixture that mutates between the two reads, at no wall-clock cost. Every
    other keyword is forwarded verbatim to :func:`observe`, so the pair is read
    through exactly the same adapters as a single observation.
    """
    first = observe(**observe_kwargs)
    sleep(delay_seconds)
    second = observe(**observe_kwargs)
    return first, second


__all__ = [
    'ContentComparison',
    'EXECUTOR_ANCHORED',
    'EXECUTOR_NO_ANCHOR',
    'EXECUTOR_SPLIT',
    'EXECUTOR_UNREADABLE',
    'ExecutorAnchor',
    'GATE_FIELD',
    'LoadedVersionVerdict',
    'NON_BLOCKING_SHAPES',
    'OUTCOME_FAIL',
    'OUTCOME_INDETERMINATE',
    'OUTCOME_PASS',
    'SHAPE_1_SATURATION',
    'SHAPE_2_PIN_MARKED_NEWER_UNMARKED',
    'SHAPE_3_LOADER_FOLLOWS_NON_PIN_DIR',
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
    'observe_twice',
    'read_executor_anchored_version',
    'read_registry_entry',
]
