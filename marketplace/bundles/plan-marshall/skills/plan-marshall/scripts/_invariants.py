# ruff: noqa: I001
"""Pluggable invariant registry for phase_handshake.

Each invariant is a tuple ``(name, applies_fn, capture_fn)``.

- ``applies_fn(plan_id, status_metadata) -> bool`` gates applicability.
- ``capture_fn(plan_id, status_metadata, phase) -> Any | None`` returns the
  captured value (stringified when stored). Returning ``None`` means
  "not applicable" and the column is stored as an empty string.

Adding a new invariant: append one tuple to ``INVARIANTS``. Nothing else
in the handshake plumbing needs to change.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from _git_helpers import git_dirty_count, git_dirty_files, git_head  # type: ignore[import-not-found]
from constants import QGATE_PHASES  # type: ignore[import-not-found]
from file_ops import get_base_dir, get_worktree_root  # type: ignore[import-not-found]
from marketplace_paths import find_marketplace_path  # type: ignore[import-not-found]
from toon_parser import parse_toon  # type: ignore[import-not-found]


class PhaseStepsIncomplete(Exception):
    """Raised by the ``phase_steps_complete`` invariant capture when a phase
    declares ``required-steps.md`` but ``status.metadata.phase_steps[phase]``
    is missing required entries, has entries with ``outcome != 'done'``
    (``skipped`` counts as failure), or has entries stored in the legacy
    bare-string shape (drift — the caller must migrate to the dict shape
    produced by ``mark-step-done``).

    ``cmd_capture`` catches this and surfaces a structured error payload so
    phase skills cannot advance on silently skipped steps.
    """

    def __init__(
        self,
        phase: str,
        missing: list[str],
        not_done: list[dict[str, str]],
        legacy_format: list[str] | None = None,
    ):
        self.phase = phase
        self.missing = missing
        self.not_done = not_done
        self.legacy_format = legacy_format or []
        parts: list[str] = []
        if missing:
            parts.append(f'missing={missing}')
        if not_done:
            parts.append(f'not_done={not_done}')
        if self.legacy_format:
            parts.append(f'legacy_format={self.legacy_format}')
        super().__init__(f'phase_steps_complete failed for phase {phase!r}: ' + ', '.join(parts))


class BlockingFindingsPresent(Exception):
    """Raised by ``_capture_pending_findings_blocking_count`` when capturing
    at a guarded phase boundary while one or more *blocking-type* findings
    remain in ``pending`` resolution.

    The blocking-type partition is read from ``marshal.json`` at
    ``plan.phase-{phase}.blocking_finding_types`` (a list of finding-type
    strings). Resolutions counting as "resolved" are ``fixed``,
    ``suppressed``, ``accepted``, ``taken_into_account``; only ``pending``
    counts toward the block.

    Guarded boundaries (where this exception fires):

    - phase ``6-finalize`` capture (covers the ``5-execute → 6-finalize``
      transition; a phase-5-execute capture for the next phase persists
      first, and the marshal then issues a ``capture --phase 6-finalize``
      which surfaces this exception when blocking counts are non-zero).
    - The intra-finalize boundaries (``automated-review → branch-cleanup``
      and ``sonar-roundtrip → next``) are guarded by the phase-6-finalize
      orchestrator re-issuing ``phase_handshake capture --phase 6-finalize``
      at those checkpoints; the same exception fires.

    All other phase captures **read** the rows (so retrospective analysis
    sees pending counts at each handshake) but do **not** raise — see the
    early-return inside the capture function.

    ``cmd_capture`` translates this into a structured TOON error payload so
    callers cannot persist a row that legitimises a phase advance with
    pending blockers in flight.
    """

    def __init__(
        self,
        phase: str,
        blocking_count: int,
        per_type: dict[str, int],
        blocking_types: list[str],
    ):
        self.phase = phase
        self.blocking_count = blocking_count
        self.per_type = per_type
        self.blocking_types = blocking_types
        super().__init__(
            f'pending_findings_blocking_count failed for phase {phase!r}: '
            f'blocking_count={blocking_count}, blocking_types={blocking_types}, '
            f'per_type={per_type}'
        )


class WorktreeMetadataDrift(Exception):
    """Raised when an on-disk worktree directory exists at the canonical
    location ``.plan/local/worktrees/{plan_id}`` but ``status.metadata``
    reports ``use_worktree != true`` (or the field is missing entirely).

    This is the inverse of the existing ``worktree_unresolved`` failure
    in ``_handshake_commands._resolve_worktree_assertion`` — that one
    fires when metadata claims a worktree exists but the disk path is
    missing/invalid. ``WorktreeMetadataDrift`` fires in the opposite
    direction: the disk path IS present but metadata denies it. Both
    failure modes refuse to advance under ``--strict`` so the writer-
    chain bug surfaced by lesson ``2026-05-08-14-001`` (where
    ``phase-1-init`` returned ``use_worktree=true`` and the worktree dir
    was created but the persisted metadata silently reverted to
    ``use_worktree=false``) cannot run silently.

    The constructor formats a descriptive message and keeps the
    structured fields (``plan_id``, ``worktree_dir``, ``use_worktree``)
    as attributes so callers (``cmd_capture`` / ``cmd_verify``) can
    surface a TOON error payload and refuse to persist the row.
    """

    def __init__(
        self,
        plan_id: str,
        worktree_dir: str,
        use_worktree: Any,
    ):
        self.plan_id = plan_id
        self.worktree_dir = worktree_dir
        self.use_worktree = use_worktree
        super().__init__(
            f'worktree_metadata_drift for plan {plan_id!r}: orphan worktree directory '
            f'at {worktree_dir!r} but metadata.use_worktree={use_worktree!r}'
        )


class MainCheckoutDirtiedDuringPlan(Exception):
    """Raised when the main checkout's dirty-file set is a proper superset of
    the previous-boundary baseline during a worktree-routed plan.

    This is the layer-D enforcement gap surfaced by lesson
    ``2026-05-08-08-001``: layers A/B/C of worktree routing are closed
    (``manage-*`` cwd-agnostic, ``--plan-id`` auto-routing, raw tool flags
    using the resolved path), but layer D (any tool that touches the
    filesystem free-form — ``Edit`` / ``Write`` / ``Bash`` / external CLIs)
    has no enforcement and relies on prompt discipline alone. The original
    lesson proposed a ``PreToolUse`` hook; that approach was rejected during
    refine for being host-platform-specific (Claude-Code-only — fails on
    OpenCode and any future adapter target) and brittle (settings.json
    mutation, absolute paths, version drift).

    The chosen approach is filesystem-state-based at every phase boundary:
    ``_capture_main_dirty_files`` records the (filtered) dirty-path set from
    the main checkout on every capture, and ``_verify_main_dirty_drift``
    (invoked from ``cmd_verify`` against the persisted baseline row) raises
    this exception when:

    1. ``metadata.use_worktree==true`` (gated — main-checkout plans dirty
       freely without tripping the invariant), AND
    2. The live dirty-file set is a *proper superset* of the captured
       baseline (i.e., contains every baseline path AND at least one new
       path the baseline did not have).

    The proper-superset rule is deliberate: a pre-existing dirty file that
    persists across boundaries (baseline-equal) is not a leak — it predates
    the current plan. Only newly-dirty paths between captures count as
    drift, so the operator sees only the paths that actually leaked into
    main during this phase boundary.

    The constructor formats a descriptive message and keeps the structured
    fields (``plan_id``, ``phase``, ``baseline``, ``observed``,
    ``newly_dirty``) as attributes so callers (``cmd_verify``) can surface
    a TOON error payload (``error: main_checkout_dirtied_during_plan``)
    listing the offending paths. Under ``--strict`` the verify path turns
    this into a non-zero exit so the boundary refuses to advance until the
    unauthorized changes are reverted (or moved into the worktree branch).

    See ``workflow-integration-git/standards/worktree-handling.md`` § layer
    D for the recovery loop ("boundary refuses → revert leaked
    main-checkout changes (or git checkout main && git mv them into the
    worktree branch) → retry boundary").
    """

    def __init__(
        self,
        plan_id: str,
        phase: str,
        baseline: list[str],
        observed: list[str],
        newly_dirty: list[str],
    ):
        self.plan_id = plan_id
        self.phase = phase
        self.baseline = baseline
        self.observed = observed
        self.newly_dirty = newly_dirty
        super().__init__(
            f'main_checkout_dirtied_during_plan for plan {plan_id!r} at phase {phase!r}: '
            f'{len(newly_dirty)} newly-dirty path(s) leaked into main checkout '
            f'beyond baseline — {newly_dirty}'
        )


class TaskGraphInvalid(Exception):
    """Raised by the ``task_graph_valid`` invariant capture when the plan's
    task dependency graph has a cycle or a dangling reference (a
    ``depends_on`` entry that does not match any existing task number).

    Shaped like :class:`PhaseStepsIncomplete`: the constructor formats a
    descriptive message and keeps the structured fields (``cycle``,
    ``dangling``) as attributes so callers can surface a structured error
    payload and refuse to persist the handshake row — thereby blocking the
    phase transition on a broken task graph.
    """

    def __init__(
        self,
        cycle: list[str],
        dangling: list[dict[str, str]],
    ):
        self.cycle = cycle
        self.dangling = dangling
        parts: list[str] = []
        if cycle:
            parts.append(f'cycle={cycle}')
        if dangling:
            parts.append(f'dangling={dangling}')
        super().__init__('task_graph_valid failed: ' + ', '.join(parts))


AppliesFn = Callable[[str, dict[str, Any]], bool]
CaptureFn = Callable[[str, dict[str, Any], str], Any]


# --- helpers --------------------------------------------------------------


def _repo_root() -> Path:
    """Main git checkout root inferred from the plan-marshall base directory.

    ``get_base_dir()`` resolves to ``<root>/.plan/local`` in production, so the
    parent chain `.plan/local → .plan → root` identifies the main checkout.
    In tests, ``PLAN_BASE_DIR`` may point somewhere else; in that case we fall
    back to the current working directory.
    """
    try:
        base = get_base_dir()
    except RuntimeError:
        return Path.cwd()
    if base.name == 'local' and base.parent.name == '.plan':
        return base.parent.parent
    return Path.cwd()


def _worktree_applicable(_plan_id: str, metadata: dict[str, Any]) -> bool:
    return bool(metadata.get('worktree_path'))


def _always(_plan_id: str, _metadata: dict[str, Any]) -> bool:
    return True


def _run_script(args: list[str]) -> str | None:
    """Invoke ``execute-script.py`` with ``args`` and return stdout on success."""
    repo = _repo_root()
    executor = repo / '.plan' / 'execute-script.py'
    if not executor.exists():
        return None
    cmd = ['python3', str(executor), *args]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=60,
            env=os.environ.copy(),
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _hash_dict(payload: Any) -> str:
    """Stable SHA256 of a JSON-serializable payload (keys sorted recursively)."""
    blob = json.dumps(payload, sort_keys=True, separators=(',', ':'), default=str)
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()[:16]


# --- phase required-steps resolution -------------------------------------


def _resolve_required_steps_path(phase: str) -> Path | None:
    """Return the ``required-steps.md`` path for a phase skill, if present.

    Resolution rule (documented in ``references/phase-handshake.md``):
    phase skills live at ``marketplace/bundles/plan-marshall/skills/phase-{phase}``
    by convention — where ``phase`` is the phase key such as ``6-finalize``.
    The required-steps declaration, if the phase opts in, is the sibling file
    ``standards/required-steps.md`` inside that skill directory. Returns
    ``None`` if the marketplace root cannot be located or the file is absent.
    """
    bundles = find_marketplace_path()
    if bundles is None:
        return None
    candidate = bundles / 'plan-marshall' / 'skills' / f'phase-{phase}' / 'standards' / 'required-steps.md'
    return candidate if candidate.is_file() else None


def _parse_required_steps(path: Path) -> list[str]:
    """Parse a ``required-steps.md`` file into an ordered list of step names.

    Format: markdown with one step per line in a bullet item, e.g.::

        - commit-push
        - create-pr
        - record-metrics

    Lines that do not start with ``- `` (after stripping whitespace) are
    ignored. Duplicates are preserved in declaration order; callers should
    treat the list as a set for the completeness check.
    """
    steps: list[str] = []
    try:
        content = path.read_text(encoding='utf-8')
    except OSError:
        return steps
    for raw in content.splitlines():
        line = raw.strip()
        if not line.startswith('- '):
            continue
        name = line[2:].strip()
        # Trim inline backticks/formatting if present.
        if name.startswith('`') and name.endswith('`') and len(name) >= 2:
            name = name[1:-1]
        if name:
            steps.append(name)
    return steps


def _read_manifest_steps(plan_id: str, phase: str) -> set[str] | None:
    """Return the set of step IDs scheduled in the plan's execution manifest
    for ``phase``, or ``None`` when the manifest cannot be read.

    The manifest lives at ``<base>/plans/{plan_id}/execution.toon`` and stores
    the phase step list under ``phase_{N}.steps`` where ``N`` is the leading
    numeric segment of the phase key (e.g. ``6-finalize`` → ``phase_6``). Step
    IDs are returned verbatim — bare for built-ins (``commit-push``), prefixed
    for project / fully-qualified steps (``project:finalize-step-...``) — so
    they match the entries parsed from ``required-steps.md`` by exact string.

    Returns ``None`` (rather than an empty set) on any read/parse failure so the
    caller can distinguish "manifest unreadable — fall back to the full required
    list" from "manifest read, phase schedules zero required steps".
    """
    section = f'phase_{phase.split("-", 1)[0]}'
    try:
        manifest_path = get_base_dir() / 'plans' / plan_id / 'execution.toon'
        if not manifest_path.is_file():
            return None
        parsed = parse_toon(manifest_path.read_text(encoding='utf-8'))
    except (OSError, ValueError, KeyError):
        return None
    if not isinstance(parsed, dict):
        return None
    phase_block = parsed.get(section)
    if not isinstance(phase_block, dict):
        return None
    steps = phase_block.get('steps')
    if not isinstance(steps, list):
        return None
    return {str(step) for step in steps}


# --- capture functions ---------------------------------------------------


def _capture_main_sha(_plan_id: str, _metadata: dict[str, Any], _phase: str) -> Any:
    return git_head(_repo_root())


def _capture_main_dirty(_plan_id: str, _metadata: dict[str, Any], _phase: str) -> Any:
    return git_dirty_count(_repo_root())


def _filter_main_dirty_paths(paths: list[str]) -> list[str]:
    """Filter ``paths`` to exclude entries that legitimately live in the main
    checkout regardless of worktree state.

    The single filter rule: drop every path that begins with ``.plan/``.
    The plan-marshall ``.plan/`` directory holds plan metadata, status
    files, lessons, lessons-aggregate working state, etc. During phases 1-4
    these resolve to the main checkout's ``.plan/local/`` via the uniform
    cwd walk-up (cwd is main; ADR-002), so dirtying ``.plan/`` is part of
    normal phase-boundary bookkeeping and MUST NOT trip the layer-D drift
    invariant.

    Operates on the porcelain-string set (sorted, deduplicated) returned by
    :func:`_git_helpers.git_dirty_files`; preserves sort order so callers
    can diff successive captures with set semantics.
    """
    return [p for p in paths if not p.startswith('.plan/')]


def _capture_main_dirty_files(_plan_id: str, _metadata: dict[str, Any], _phase: str) -> Any:
    """Sorted list of main-checkout dirty paths, filtered to exclude ``.plan/``.

    Layer-D enforcement capture (paired with :func:`_verify_main_dirty_drift`
    which is invoked at verify time, not via the registry — drift detection
    is comparison-based and needs the persisted baseline row, which the
    capture-time signature does not expose).

    Returns ``None`` when the dirty-file probe fails (not a git repository
    or git invocation error) so the calling capture's "not applicable"
    contract leaves the column empty in stored rows. Otherwise returns the
    sorted, ``.plan/``-filtered list — callers persist the list verbatim
    via the TOON list field on the handshake row.

    The capture is keyed on ``main_dirty_files`` and complements the
    existing scalar ``main_dirty`` column: ``main_dirty`` answers "how many
    dirty paths?" (drives retrospective summaries), ``main_dirty_files``
    answers "which paths?" (drives layer-D drift detection). Both are
    captured every boundary to keep the columns aligned.

    See :class:`MainCheckoutDirtiedDuringPlan` for the matching exception
    raised by the verify-time drift check, and
    ``workflow-integration-git/standards/worktree-handling.md`` § layer D
    for the operator-facing recovery loop.
    """
    raw = git_dirty_files(_repo_root())
    if raw is None:
        return None
    return _filter_main_dirty_paths(raw)


def _main_dirty_drift_diff(baseline: list[str], observed: list[str]) -> list[str]:
    """Return the proper-superset diff between ``baseline`` and ``observed``.

    Result is the list of paths present in ``observed`` but absent from
    ``baseline``, sorted. An empty result means the live set is a (non-strict)
    subset of the baseline — no drift. A non-empty result means the live set
    is a proper superset (strictly contains everything in baseline plus at
    least one additional path), so layer-D drift fires.

    The proper-superset rule deliberately ignores baseline-only paths (a
    file that was dirty at capture and got cleaned by the next boundary
    is not a leak) and identical-set captures (no movement). It only flags
    *new* dirty paths added between boundaries — exactly the leak signal
    the layer-D enforcement is meant to catch.

    Set-difference semantics; callers pass the sorted list returned by
    :func:`_capture_main_dirty_files` (or the persisted TOON list field).
    """
    baseline_set = set(baseline)
    return sorted(p for p in observed if p not in baseline_set)


def _capture_worktree_sha(_plan_id: str, metadata: dict[str, Any], _phase: str) -> Any:
    wt = metadata.get('worktree_path')
    if not wt:
        return None
    return git_head(wt)


def _capture_worktree_dirty(_plan_id: str, metadata: dict[str, Any], _phase: str) -> Any:
    wt = metadata.get('worktree_path')
    if not wt:
        return None
    return git_dirty_count(wt)


def _is_truthy_metadata(value: Any) -> bool:
    """Decide whether a metadata field expressing a boolean is true.

    Mirrors the helper of the same name in ``_handshake_commands.py`` so
    invariant captures here stay self-contained (no cross-module import
    cycle). TOON serialises booleans through ``parse_toon`` to Python
    ``bool``; tolerates the string forms ``'true'``/``'True'``/``'1'``
    for robustness against future TOON schema changes.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {'true', '1', 'yes'}
    if isinstance(value, int):
        return value != 0
    return False


def _worktree_orphan_dir(plan_id: str) -> Path | None:
    """Return the canonical worktree directory if it exists on disk.

    The convention (documented in ``phase-1-init/SKILL.md`` Step 6) is
    ``<repo_root>/.plan/local/worktrees/{plan_id}``, resolved via
    ``file_ops.get_worktree_root()`` (worktree-aware, anchored on the git
    common-dir). Returns ``None`` when the directory is absent or no main
    checkout root resolves — callers interpret that as "no orphan detection
    applicable".
    """
    try:
        candidate = get_worktree_root() / plan_id
    except RuntimeError:
        return None
    return candidate if candidate.is_dir() else None


# Phases whose entry boundary precedes worktree materialization. Mirrors
# the constant in ``_handshake_commands._PRE_MATERIALIZATION_PHASES``;
# kept inline so this module stays self-contained and avoids a cross-module
# import cycle.
_PRE_MATERIALIZATION_PHASES: frozenset[str] = frozenset({
    '1-init',
    '2-refine',
    '3-outline',
    '4-plan',
})


def _capture_worktree_orphan(plan_id: str, metadata: dict[str, Any], phase: str) -> Any:
    """Inverse-direction worktree invariant: orphan dir + metadata says no worktree.

    Tri-state contract aligned with
    :func:`_handshake_commands._resolve_worktree_assertion`:

    - ``use_worktree==true`` AND orphan directory is the canonical
      ``<repo>/.plan/local/worktrees/{plan_id}`` path AND ``phase`` is
      in the pre-materialization set (``1-init``/``2-refine``/``3-outline``/
      ``4-plan``) → deferred-but-not-yet-materialized window; capture
      returns ``None``. The orchestrator routed the plan through a
      worktree but ``phase-5-execute`` has not yet created the on-disk
      directory, so the orphan-looking shape is the legitimate
      transitional state.
    - ``use_worktree==true`` for any other shape (post-materialization
      phase or non-canonical orphan path) → return ``None`` because the
      metadata→disk direction is owned by
      ``_resolve_worktree_assertion`` (which already refuses to advance
      post-materialization when the path is missing/stale).
    - ``use_worktree`` not truthy AND orphan directory exists → writer-
      chain drift. Raises :class:`WorktreeMetadataDrift` so
      ``cmd_capture`` surfaces ``error: worktree_metadata_drift`` and
      refuses to persist the handshake row. Under ``--strict`` the
      verify path turns this into a non-zero exit.

    Returns ``None`` when the orphan directory is absent (no drift to
    detect regardless of metadata state).
    """
    orphan = _worktree_orphan_dir(plan_id)
    if orphan is None:
        return None
    use_worktree = metadata.get('use_worktree')
    if _is_truthy_metadata(use_worktree):
        # Metadata-says-true direction is the full responsibility of
        # ``_resolve_worktree_assertion`` — both pre- and
        # post-materialization phases pass here. ``phase`` is unused in
        # this branch by design; the parameter is kept on the function
        # signature for symmetry with the disk-says-true direction below.
        del phase  # explicit acknowledgement that the truthy branch is phase-agnostic
        return None
    raise WorktreeMetadataDrift(
        plan_id=plan_id,
        worktree_dir=str(orphan),
        use_worktree=use_worktree,
    )


# Required top-level keys that phase-1-init promises to write into
# references.json (branch, base_branch, modified_files). The list is sorted
# so the hash payload is deterministic regardless of insertion order.
_REFERENCES_REQUIRED_KEYS: tuple[str, ...] = ('base_branch', 'branch', 'modified_files')


def _capture_references_valid(plan_id: str, _metadata: dict[str, Any], _phase: str) -> Any:
    """Drift-detection hash over the structural health of references.json.

    Phase-1-init is the sole writer of ``references.json``; every downstream
    phase depends on the file existing and having the structural fields that
    phase-1-init promises (``branch``, ``base_branch``, ``modified_files``).
    Silent deletion, corruption to a non-dict, or a missing required field
    survives all current invariants and only surfaces at random call sites.

    This invariant caps that gap by emitting a deterministic hash over:

    .. code-block:: python

        {
            'present': bool,               # file exists and is non-empty
            'top_level_is_dict': bool,     # parsed value is a dict
            'required_field_set': [...],   # sorted list of required keys
                                           # that are present in the file
        }

    On success the hash is stable across successive capture/verify calls as
    long as the file remains unchanged. Any of the four failure modes (missing
    file, non-dict content, removed required field, corrupted file) changes
    the hash, surfacing as drift.

    The invariant is passive (never raises) — the runtime :func:`require_references`
    safety net handles the downstream error; the invariant is the upstream
    guard that makes drift visible at every phase boundary.

    Returns ``None`` only when the plan directory itself cannot be resolved,
    which matches the other capture functions' "not applicable" contract.
    """
    stdout = _run_script(
        [
            'plan-marshall:manage-references:manage-references',
            'read',
            '--plan-id',
            plan_id,
        ]
    )
    if stdout is None:
        # Executor unreachable — treat as "file absent / unknown" so the hash
        # captures a deterministic absent-state fingerprint rather than None
        # (None would leave the column empty and skip the drift comparison).
        return _hash_dict({'present': False, 'top_level_is_dict': False, 'required_field_set': []})
    try:
        parsed = parse_toon(stdout)
    except Exception:
        return _hash_dict({'present': False, 'top_level_is_dict': False, 'required_field_set': []})

    # Distinguish between the three possible states:
    # 1. File not found (manage-references read emits status: error / file_not_found)
    # 2. File found and valid dict — check required keys (``references`` sub-key)
    if parsed.get('status') == 'error':
        return _hash_dict({'present': False, 'top_level_is_dict': False, 'required_field_set': []})

    refs = parsed.get('references')
    if not isinstance(refs, dict):
        # ``read`` always wraps the payload under ``references``; a non-dict
        # value here means the file was corrupted to a non-object JSON type.
        return _hash_dict({'present': True, 'top_level_is_dict': False, 'required_field_set': []})

    present_required = sorted(k for k in _REFERENCES_REQUIRED_KEYS if k in refs)
    return _hash_dict({
        'present': True,
        'top_level_is_dict': True,
        'required_field_set': present_required,
    })


def _capture_task_state_hash(plan_id: str, _metadata: dict[str, Any], _phase: str) -> Any:
    """Drift-detection hash over every task's status, depends_on, and per-step
    {status, intent} outcomes.

    The per-step payload folds in each step's required ``intent`` alongside its
    ``status`` so an out-of-band intent mutation between phase boundaries changes
    the hash — intent authoritatively drives the files_exist Q-Gate, so a silent
    flip must surface as phase-handshake drift. No new INVARIANTS row is added;
    the existing ``task_state_hash`` simply becomes intent-sensitive.

    ``manage-tasks list`` emits a *tabular* ``tasks_table`` whose reachable
    fields are only ``number, title, domain, profile, deliverable, status,
    progress`` — ``depends_on`` and ``sub_steps``/``steps`` are NOT on that
    table. To access the rich fields this hash depends on, we iterate the
    task numbers from the table and call ``manage-tasks read --task-number N`` per
    task (same pattern as :func:`_capture_task_graph_valid`).

    Returns ``None`` when ``list`` or any ``read`` cannot be parsed, matching
    the other capture functions' "not applicable" semantics. An empty plan
    yields the stable zero-task hash.
    """
    list_stdout = _run_script(
        [
            'plan-marshall:manage-tasks:manage-tasks',
            'list',
            '--plan-id',
            plan_id,
        ]
    )
    if list_stdout is None:
        return None
    try:
        list_parsed = parse_toon(list_stdout)
    except Exception:
        return None
    tasks_table = list_parsed.get('tasks_table') or []
    if not isinstance(tasks_table, list):
        return None

    numbers: list[int] = []
    for row in tasks_table:
        if not isinstance(row, dict):
            continue
        n = _normalize_task_ref(row.get('number'))
        if n is not None:
            numbers.append(n)

    reduced: list[dict[str, Any]] = []
    for n in numbers:
        task_stdout = _run_script(
            [
                'plan-marshall:manage-tasks:manage-tasks',
                'read',
                '--plan-id',
                plan_id,
                '--task-number',
                str(n),
            ]
        )
        if task_stdout is None:
            return None
        try:
            task_parsed = parse_toon(task_stdout)
        except Exception:
            return None
        task = task_parsed.get('task')
        if not isinstance(task, dict):
            return None
        steps = task.get('steps') or []
        # Each per-step payload carries BOTH the step status ('s') and the
        # required intent ('i'), so the hash is sensitive to a silent intent
        # mutation between phase boundaries (intent authoritatively drives the
        # files_exist Q-Gate). The status contribution is preserved unchanged so
        # status-drift detection continues to fire.
        step_outcomes: list[dict[str, str]] = []
        if isinstance(steps, list):
            for step in steps:
                if isinstance(step, dict):
                    step_outcomes.append(
                        {'s': str(step.get('status', '')), 'i': str(step.get('intent', ''))}
                    )
        depends = task.get('depends_on') or []
        if not isinstance(depends, list):
            depends = []
        reduced.append(
            {
                'n': n,
                's': str(task.get('status', '')),
                'o': step_outcomes,
                'd': sorted(str(d) for d in depends),
            }
        )

    reduced.sort(key=lambda x: x.get('n') or 0)
    return _hash_dict(reduced)


def _normalize_task_ref(raw: Any) -> int | None:
    """Normalize a ``depends_on`` entry to an integer task number.

    Accepts integers directly and strings of the shape ``TASK-1`` or
    ``TASK-001`` (the two formats produced by ``_build_done_set``).
    Returns ``None`` when the value cannot be parsed so the caller can
    surface it as a dangling reference.
    """
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if text.startswith('TASK-'):
            text = text[len('TASK-') :]
        if text.isdigit():
            return int(text)
    return None


def _capture_task_graph_valid(plan_id: str, _metadata: dict[str, Any], _phase: str) -> Any:
    """Validate the plan's task dependency graph.

    Loads every task via ``manage-tasks list`` (for the full number set)
    and then ``manage-tasks read`` (for each task's ``depends_on``), builds
    the adjacency graph, and checks two properties:

    - **No cycles** — DFS with WHITE/GRAY/BLACK coloring; a GRAY-hit edge
      closes a cycle and the GRAY stack from entry to hit is captured as
      the cycle path (formatted as ``TASK-{n}`` strings).
    - **No dangling references** — every ``depends_on`` entry must resolve
      to an existing task number.

    On success returns ``_hash_dict(sorted_edges)`` where edges are
    ``(src, dst)`` integer tuples — a stable 16-char hex SHA256 prefix
    matching the pattern used by the other hash invariants. An empty task
    list yields the zero-edge hash (stable, non-raising).

    On failure raises :class:`TaskGraphInvalid` so ``cmd_capture`` refuses
    to persist the handshake row and blocks the phase transition.

    Returns ``None`` if the tasks cannot be loaded (e.g. executor missing
    during a unit-test harness that doesn't provide the plan directory).
    """
    stdout = _run_script(
        [
            'plan-marshall:manage-tasks:manage-tasks',
            'list',
            '--plan-id',
            plan_id,
        ]
    )
    if stdout is None:
        return None
    try:
        parsed = parse_toon(stdout)
    except Exception:
        return None
    tasks_table = parsed.get('tasks_table') or parsed.get('tasks') or []
    if not isinstance(tasks_table, list):
        return None

    # Collect task numbers from the list; an empty list is valid (zero-edge).
    numbers: list[int] = []
    for row in tasks_table:
        if not isinstance(row, dict):
            continue
        n = _normalize_task_ref(row.get('number'))
        if n is not None:
            numbers.append(n)

    # Pull depends_on per task via ``read`` — ``list`` does not surface it.
    adjacency: dict[int, list[int | None]] = {n: [] for n in numbers}
    dangling: list[dict[str, str]] = []
    for n in numbers:
        task_stdout = _run_script(
            [
                'plan-marshall:manage-tasks:manage-tasks',
                'read',
                '--plan-id',
                plan_id,
                '--task-number',
                str(n),
            ]
        )
        if task_stdout is None:
            continue
        try:
            task_parsed = parse_toon(task_stdout)
        except Exception:
            continue
        task = task_parsed.get('task') or {}
        if not isinstance(task, dict):
            continue
        deps = task.get('depends_on') or []
        if not isinstance(deps, list):
            continue
        for raw in deps:
            target = _normalize_task_ref(raw)
            if target is None or target not in adjacency:
                dangling.append({'task': f'TASK-{n}', 'missing': str(raw)})
                continue
            adjacency[n].append(target)

    # DFS cycle detection (WHITE=0, GRAY=1, BLACK=2). Capture the first cycle
    # found, formatted as TASK-{n} strings from entry node through closing edge.
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[int, int] = dict.fromkeys(adjacency, WHITE)
    cycle_path: list[str] = []

    def _dfs(start: int) -> bool:
        stack: list[tuple[int, int]] = [(start, 0)]
        path: list[int] = []
        color[start] = GRAY
        path.append(start)
        while stack:
            node, idx = stack[-1]
            neighbors = adjacency.get(node, [])
            if idx >= len(neighbors):
                color[node] = BLACK
                stack.pop()
                if path:
                    path.pop()
                continue
            # Advance pointer for this stack frame before recursing.
            stack[-1] = (node, idx + 1)
            nxt = neighbors[idx]
            if nxt is None:
                continue
            state = color.get(nxt, WHITE)
            if state == GRAY:
                # Close the cycle from the first occurrence of nxt in path.
                try:
                    cut = path.index(nxt)
                except ValueError:
                    cut = 0
                cycle_nodes = path[cut:] + [nxt]
                cycle_path.extend(f'TASK-{m}' for m in cycle_nodes)
                return True
            if state == WHITE:
                color[nxt] = GRAY
                path.append(nxt)
                stack.append((nxt, 0))
        return False

    for start in sorted(adjacency.keys()):
        if color[start] == WHITE:
            if _dfs(start):
                break

    if cycle_path or dangling:
        raise TaskGraphInvalid(cycle=cycle_path, dangling=dangling)

    edges: list[tuple[int, int]] = []
    for src in sorted(adjacency.keys()):
        for dst in adjacency[src]:
            if dst is None:
                continue
            edges.append((src, dst))
    edges.sort()
    # JSON serialization turns tuples into lists; normalize up front for
    # deterministic hashing across Python versions.
    return _hash_dict([list(edge) for edge in edges])


def _capture_unfinished_tasks_count(plan_id: str, _metadata: dict[str, Any], _phase: str) -> Any:
    """Count of unfinished tasks (``status: pending`` OR ``status: in_progress``).

    Mirrors the broadened predicate of ``manage-tasks loop-exit-guard``: both
    ``pending`` (never started) and ``in_progress`` (started but not finalized)
    are unfinished terminal states that block clean exit. Drives the
    phase-5-execute transition guard: if any unfinished task remains when the
    orchestrator tries to transition to ``6-finalize``, the guard refuses.
    Captured every phase so retrospective analysis sees the unfinished-queue
    size at each boundary; non-zero values at later phases indicate orphaned
    fix tasks or abandoned mid-flight dispatches.

    The capture invokes ``loop-exit-guard`` so the count tracks the same
    on-disk machinery the runtime guard reads. If the guard call is
    unreachable, fall back to two separate ``list --status`` reads (the
    inline historical path) so the row is still captured.
    """
    stdout = _run_script(
        [
            'plan-marshall:manage-tasks:manage-tasks',
            'loop-exit-guard',
            '--plan-id',
            plan_id,
        ]
    )
    if stdout is not None:
        try:
            parsed = parse_toon(stdout)
        except Exception:
            parsed = None
        if isinstance(parsed, dict):
            pending = parsed.get('pending_count')
            in_progress = parsed.get('in_progress_count')

            def _as_int(value: Any) -> int | None:
                if isinstance(value, int):
                    return value
                if isinstance(value, str) and value.isdigit():
                    return int(value)
                return None

            pending_int = _as_int(pending)
            in_progress_int = _as_int(in_progress)
            if pending_int is not None and in_progress_int is not None:
                return pending_int + in_progress_int

    # Fallback: read the two unfinished buckets directly via `list --status`.
    total = 0
    for status in ('pending', 'in_progress'):
        bucket_stdout = _run_script(
            [
                'plan-marshall:manage-tasks:manage-tasks',
                'list',
                '--status',
                status,
                '--plan-id',
                plan_id,
            ]
        )
        if bucket_stdout is None:
            return None
        try:
            bucket_parsed = parse_toon(bucket_stdout)
        except Exception:
            return None
        rows = bucket_parsed.get('tasks_table') or bucket_parsed.get('tasks') or []
        if not isinstance(rows, list):
            return None
        total += len(rows)
    return total


def _capture_qgate_open_count(plan_id: str, _metadata: dict[str, Any], phase: str) -> Any:
    if phase == '1-init':
        # Q-Gate findings are scoped to phases 2-refine onward; manage-findings
        # rejects --phase 1-init, so short-circuit to a trivially-zero result.
        return 0
    stdout = _run_script(
        [
            'plan-marshall:manage-findings:manage-findings',
            'qgate',
            'list',
            '--plan-id',
            plan_id,
            '--phase',
            phase,
            '--resolution',
            'pending',
        ]
    )
    if stdout is None:
        return None
    try:
        parsed = parse_toon(stdout)
    except Exception:
        return None
    count = parsed.get('filtered_count')
    if isinstance(count, int):
        return count
    if isinstance(count, str) and count.isdigit():
        return int(count)
    return None


# --- pending-finding invariants ------------------------------------------

# All finding types tracked by ``manage-findings`` (mirrors the taxonomy in
# ``tools-file-ops/scripts/constants.py``). Kept inline so the invariant
# capture has no run-time dependency on the constants module beyond the
# existing executor hop, and so the row contract stays stable when new
# types are added centrally (the registry simply reads the per-phase config
# slot to decide which types block).
_PENDING_FINDING_TYPES: tuple[str, ...] = (
    'bug',
    'improvement',
    'anti-pattern',
    'triage',
    'tip',
    'insight',
    'best-practice',
    'build-error',
    'test-failure',
    'lint-issue',
    'sonar-issue',
    'pr-comment',
)

# Phases at which a non-zero ``pending_findings_blocking_count`` raises
# :class:`BlockingFindingsPresent` to refuse the capture. Other phases
# capture the row passively (read-only — see capture function).
_BLOCKING_BOUNDARIES: frozenset[str] = frozenset({'6-finalize'})


def _query_pending_count_for_type(plan_id: str, finding_type: str) -> int | None:
    """Return the count of ``pending`` findings for ``finding_type``.

    Drives both the per-type breakdown and the blocking-count summary.
    Routes through ``manage-findings query --type T --resolution pending``
    so it picks up the per-type JSONL split introduced in TASK-1 without
    duplicating the query logic.

    Returns ``None`` when the executor cannot be reached or the output is
    unparseable so the calling capture can surface "not applicable" via the
    existing capture-returns-None contract.
    """
    stdout = _run_script(
        [
            'plan-marshall:manage-findings:manage-findings',
            'list',
            '--plan-id',
            plan_id,
            '--type',
            finding_type,
            '--resolution',
            'pending',
        ]
    )
    if stdout is None:
        return None
    try:
        parsed = parse_toon(stdout)
    except Exception:
        return None
    count = parsed.get('filtered_count')
    if isinstance(count, int):
        return count
    if isinstance(count, str) and count.isdigit():
        return int(count)
    # Some manage-findings paths emit ``count`` instead of ``filtered_count``.
    alt = parsed.get('count')
    if isinstance(alt, int):
        return alt
    if isinstance(alt, str) and alt.isdigit():
        return int(alt)
    return None


def _query_pending_qgate_count_aggregated(plan_id: str) -> int | None:
    """Sum ``pending`` Q-Gate findings across every phase.

    Q-Gate findings live in ``findings/qgate-{phase}.jsonl`` per-phase files
    rather than the canonical per-type ``findings/{type}.jsonl`` layout, so
    they cannot be reached via ``manage-findings query --type qgate``
    (``query_findings`` only iterates :data:`tools-file-ops/scripts/constants.py:FINDING_TYPES`,
    which excludes ``qgate``). Producer-mismatch findings filed by
    ``add_qgate_finding(...)`` from ``github_pr.py`` / ``gitlab_pr.py`` /
    ``sonar.py`` / ``_build_shared.py`` therefore did not surface in the
    blocking-count check before this helper existed — see lesson
    ``2026-05-05-11-001`` follow-up plan ``findings-pipeline-blocking-fixes``.

    Loops :data:`QGATE_PHASES` and sums each per-phase
    ``manage-findings qgate list --phase {p} --resolution pending`` result's
    ``filtered_count``. The aggregation makes the blocking gate phase-agnostic
    with respect to where producers chose to file their Q-Gate rows: a
    ``5-execute`` row produced during the ``6-finalize`` step still blocks
    the ``5-execute → 6-finalize`` boundary because the aggregated total is
    non-zero regardless of phase label.

    Returns ``None`` when ANY per-phase query fails (executor unreachable or
    output unparseable). Returning ``None`` triggers the calling capture's
    "not applicable" contract — preferring to record an empty column over
    silently under-counting and letting a transition advance.
    """
    total = 0
    for qphase in QGATE_PHASES:
        stdout = _run_script(
            [
                'plan-marshall:manage-findings:manage-findings',
                'qgate',
                'list',
                '--plan-id',
                plan_id,
                '--phase',
                qphase,
                '--resolution',
                'pending',
            ]
        )
        if stdout is None:
            return None
        try:
            parsed = parse_toon(stdout)
        except Exception:
            return None
        count = parsed.get('filtered_count')
        if isinstance(count, int):
            total += count
            continue
        if isinstance(count, str) and count.isdigit():
            total += int(count)
            continue
        alt = parsed.get('count')
        if isinstance(alt, int):
            total += alt
            continue
        if isinstance(alt, str) and alt.isdigit():
            total += int(alt)
            continue
        return None
    return total


def _read_blocking_finding_types(plan_id: str, phase: str) -> list[str] | None:
    """Read ``plan.phase-{phase}.blocking_finding_types`` from ``marshal.json``.

    Uses ``manage-config plan phase-{phase} get --field blocking_finding_types``.
    Returns ``None`` when the field is absent or cannot be parsed — callers
    treat ``None`` as "no blocking partition configured for this phase, so
    nothing blocks". An empty list explicitly configures "no blocking
    types" and is returned as ``[]``.
    """
    stdout = _run_script(
        [
            'plan-marshall:manage-config:manage-config',
            'plan',
            f'phase-{phase}',
            'get',
            '--field',
            'blocking_finding_types',
            '--audit-plan-id',
            plan_id,
        ]
    )
    if stdout is None:
        return None
    try:
        parsed = parse_toon(stdout)
    except Exception:
        return None
    raw = parsed.get('value')
    if raw is None:
        return None
    # ``manage-config`` serializes lists as TOON arrays which ``parse_toon``
    # decodes to Python lists. Tolerate the comma-separated string fallback
    # for robustness.
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item)]
    if isinstance(raw, str):
        items = [item.strip() for item in raw.split(',') if item.strip()]
        return items
    return None


def _capture_pending_findings_by_type(
    plan_id: str,
    _metadata: dict[str, Any],
    _phase: str,
) -> Any:
    """Per-type breakdown of pending findings, captured at every boundary.

    Returns a stable, sorted compact summary of the form
    ``"bug=N,build-error=N,..."`` covering every type the project knows
    about. Returns ``None`` when no per-type query succeeds — callers
    interpret ``None`` as "not applicable" and skip the column.

    This row is always passive: it never raises. Retrospective analysis
    reads it to see the queue at each phase boundary; the blocking
    decision is the sole responsibility of
    :func:`_capture_pending_findings_blocking_count`.
    """
    parts: list[str] = []
    any_value = False
    for finding_type in _PENDING_FINDING_TYPES:
        count = _query_pending_count_for_type(plan_id, finding_type)
        if count is None:
            # Skip silently — partial visibility is acceptable for the
            # passive row; the blocking row enforces correctness.
            continue
        any_value = True
        parts.append(f'{finding_type}={count}')
    if not any_value:
        return None
    return ','.join(parts)


def _resolve_blocking_callable_registry() -> dict[str, Callable[[str, str], int | None]]:
    """Return the per-type query callable mapping merged from determine_mode.

    Reads ``_GLOBAL_BLOCKING_TYPES`` and ``_FINALIZE_BLOCKING_TYPES`` from
    ``marshall-steward:scripts/determine_mode.py`` and resolves each entry's
    callable thunk to the corresponding concrete query helper defined in
    this module. The two registered thunks (``_generic_query_thunk`` and
    ``_qgate_aggregated_query_thunk``) short-circuit to
    :func:`_query_pending_count_for_type` and
    :func:`_query_pending_qgate_count_aggregated` respectively, avoiding a
    second executor hop through the thunk's lazy import path.

    Returns an empty dict on import failure so the caller falls back to the
    generic per-type query (matches the prior single-helper behaviour for
    storage-canonical types).
    """
    try:
        from determine_mode import (  # type: ignore[import-not-found]
            _FINALIZE_BLOCKING_TYPES,
            _GLOBAL_BLOCKING_TYPES,
            BLOCKING_TYPE_CALLABLE_NAMES,
            GENERIC_PENDING_QUERY,
            QGATE_AGGREGATED_QUERY,
        )
    except ImportError:
        return {}

    # Resolve each thunk to its concrete helper so the dispatcher avoids the
    # thunk's lazy-import bounce on every call.
    concrete: dict[str, Callable[[str, str], int | None]] = {}

    def _resolve(thunk: Callable[[str, str], int | None]) -> Callable[[str, str], int | None]:
        name = BLOCKING_TYPE_CALLABLE_NAMES.get(thunk)
        if name == GENERIC_PENDING_QUERY:
            return _query_pending_count_for_type
        if name == QGATE_AGGREGATED_QUERY:
            return lambda plan_id, _ft: _query_pending_qgate_count_aggregated(plan_id)
        return thunk  # Fallback — preserves caller signature.

    merged: dict[str, Callable[[str, str], int | None]] = dict(_GLOBAL_BLOCKING_TYPES)
    merged.update(_FINALIZE_BLOCKING_TYPES)
    for finding_type, thunk in merged.items():
        concrete[finding_type] = _resolve(thunk)
    return concrete


def _capture_pending_findings_blocking_count(
    plan_id: str,
    _metadata: dict[str, Any],
    phase: str,
) -> Any:
    """Sum of pending findings whose type is *blocking* for ``phase``.

    Reads the per-phase ``blocking_finding_types`` partition from
    ``marshal.json``; if the slot is unset, no types are considered
    blocking for that phase and the count is ``0``. Otherwise, sums the
    pending counts across every configured blocking type.

    At a *guarded boundary* (``phase`` in :data:`_BLOCKING_BOUNDARIES`),
    a non-zero count raises :class:`BlockingFindingsPresent` so
    ``cmd_capture`` refuses to persist the handshake row — that gates the
    phase transition. At every other phase the count is returned as an int
    so retrospective analysis sees the queue size at each boundary; the
    transition itself is not blocked.

    Returns ``None`` when the executor cannot be reached for any of the
    underlying queries — matches the other captures' "not applicable"
    contract and keeps the column empty in stored rows.
    """
    blocking_types = _read_blocking_finding_types(plan_id, phase)
    if blocking_types is None:
        # No partition configured for this phase → nothing blocks; record 0.
        return 0
    if not blocking_types:
        return 0

    callable_registry = _resolve_blocking_callable_registry()
    per_type: dict[str, int] = {}
    total = 0
    for finding_type in blocking_types:
        query_fn = callable_registry.get(finding_type)
        if query_fn is None:
            # Type is configured to block but no callable is registered for
            # its storage shape. Fall back to the generic per-type query —
            # this preserves backward-compatibility for storage-canonical
            # types added centrally without a determine_mode.py update.
            query_fn = _query_pending_count_for_type
        count = query_fn(plan_id, finding_type)
        if count is None:
            # Partial query failure — fall back to "not applicable" rather
            # than under-counting and silently letting a transition
            # advance.
            return None
        per_type[finding_type] = count
        total += count

    if total > 0 and phase in _BLOCKING_BOUNDARIES:
        raise BlockingFindingsPresent(
            phase=phase,
            blocking_count=total,
            per_type=per_type,
            blocking_types=list(blocking_types),
        )
    return total


def _capture_config_hash(plan_id: str, _metadata: dict[str, Any], phase: str) -> Any:
    # Phase config keys use the `phase-{phase}` naming convention.
    stdout = _run_script(
        [
            'plan-marshall:manage-config:manage-config',
            'plan',
            f'phase-{phase}',
            'get',
            '--audit-plan-id',
            plan_id,
        ]
    )
    if stdout is None:
        return None
    try:
        parsed = parse_toon(stdout)
    except Exception:
        return _hash_dict(stdout.strip())
    return _hash_dict(parsed)


def _capture_phase_steps_complete(
    _plan_id: str,
    metadata: dict[str, Any],
    phase: str,
) -> Any:
    """Verify that every step in the phase's ``required-steps.md`` is marked
    ``done`` inside ``status.metadata.phase_steps[phase]``.

    - If the phase has no ``required-steps.md``, returns ``None`` (no-op —
      the column stays empty and is ignored during verify).
    - On success, returns the SHA256 of the stable-key required step list so
      drift verify can still detect a changed required set between capture
      and verify.
    - On failure (any required step missing, recorded with outcome !=
      ``done``, or stored in the legacy bare-string shape), raises
      ``PhaseStepsIncomplete`` so ``cmd_capture`` can surface a structured
      error and refuse to persist the row.

    ``skipped`` explicitly counts as failure per the cwd handshake spec —
    only ``done`` passes. Bare-string entries are rejected as legacy drift:
    ``mark-step-done`` now stores dicts of shape
    ``{"outcome": ..., "display_detail": ...}`` and there is no automatic
    migration for the old shape.
    """
    required_path = _resolve_required_steps_path(phase)
    if required_path is None:
        return None
    required = _parse_required_steps(required_path)
    if not required:
        return None

    # Activation note (required-steps.md): a required step ABSENT from the
    # plan's manifest.phase_{N}.steps is NOT enforced — the handshake checks
    # completion only for steps the manifest actually scheduled, so pruning a
    # step from the manifest (e.g. a docs-only plan that drops the test gate, or
    # a bug_fix plan whose composer omits architecture-refresh) never deadlocks
    # the phase transition. Intersect the declared required list with the
    # manifest's scheduled steps. Fall back to the full required list ONLY when
    # the manifest cannot be read at all (conservative — never silently drop
    # enforcement when scheduling is unknown).
    manifest_steps = _read_manifest_steps(_plan_id, phase)
    if manifest_steps is not None:
        required = [step for step in required if step in manifest_steps]
        if not required:
            return None

    phase_steps = metadata.get('phase_steps') or {}
    phase_entry: dict[str, Any] = {}
    if isinstance(phase_steps, dict):
        entry = phase_steps.get(phase)
        if isinstance(entry, dict):
            phase_entry = entry

    missing: list[str] = []
    not_done: list[dict[str, str]] = []
    legacy_format: list[str] = []
    for step in required:
        if step not in phase_entry:
            missing.append(step)
            continue
        raw = phase_entry.get(step)
        if isinstance(raw, str):
            legacy_format.append(step)
            continue
        outcome = raw.get('outcome') if isinstance(raw, dict) else None
        if outcome != 'done':
            not_done.append({'step': step, 'outcome': str(outcome or '')})

    if missing or not_done or legacy_format:
        raise PhaseStepsIncomplete(phase, missing, not_done, legacy_format)

    # Deterministic hash of the required step set for drift detection. We
    # hash the sorted list so registering a new required step (which also
    # requires a new capture) shows up as drift on verify of an older row.
    return _hash_dict(sorted(required))


# --- registry ------------------------------------------------------------

INVARIANTS: list[tuple[str, AppliesFn, CaptureFn]] = [
    ('main_sha', _always, _capture_main_sha),
    ('main_dirty', _always, _capture_main_dirty),
    ('main_dirty_files', _always, _capture_main_dirty_files),
    ('worktree_sha', _worktree_applicable, _capture_worktree_sha),
    ('worktree_dirty', _worktree_applicable, _capture_worktree_dirty),
    ('worktree_orphan', _always, _capture_worktree_orphan),
    ('references_valid', _always, _capture_references_valid),
    ('task_state_hash', _always, _capture_task_state_hash),
    ('qgate_open_count', _always, _capture_qgate_open_count),
    ('config_hash', _always, _capture_config_hash),
    ('unfinished_tasks_count', _always, _capture_unfinished_tasks_count),
    ('phase_steps_complete', _always, _capture_phase_steps_complete),
    ('task_graph_valid', _always, _capture_task_graph_valid),
    ('pending_findings_by_type', _always, _capture_pending_findings_by_type),
    ('pending_findings_blocking_count', _always, _capture_pending_findings_blocking_count),
]


# --- blocking-scope classification ---------------------------------------
#
# Parallel map keyed by invariant name documenting which phase boundaries
# treat a drift in the captured value as ``status: drift`` versus as
# informational-only (drift is persisted in handshakes.toon for retrospective
# analysis but does not contribute to ``drift_count`` and does not surface
# in ``diffs[]``). Three classification values are recognised:
#
# - ``'blocking_at_every_boundary'`` — drift at any phase entry raises
#   ``status: drift`` and exits non-zero under ``--strict``. This is the
#   pre-existing behaviour for every invariant.
# - ``frozenset({'5-execute'})`` (or any other frozenset of phase keys) —
#   drift is blocking only at the named phase keys, informational at every
#   other phase. The phase keys are the ``--phase`` argument values passed
#   to ``phase_handshake verify`` (i.e. the *captured* phase whose row is
#   being re-verified, which by the handshake's call convention is the
#   phase the orchestrator is transitioning OUT of). For example,
#   ``frozenset({'5-execute'})`` means drift is blocking at the
#   ``5-execute → 6-finalize`` boundary (``verify --phase 5-execute``)
#   and informational at every planning-phase boundary
#   (``verify --phase 1-init`` through ``verify --phase 4-plan``).
# - ``'informational_only'`` — drift is never blocking; the column is
#   captured for retrospective analysis only.
#
# Rationale (lesson behind this deliverable): ``main_sha`` / ``main_dirty``
# can change between planning-phase boundaries (1→2, 2→3, 3→4, 4→5) for
# reasons unrelated to the in-flight plan (an upstream commit lands on the
# default branch during a long-paused planning phase). Treating those
# changes as blocking forces a manual override / re-capture loop with no
# corresponding correctness gain — the planning artefacts (request,
# outline, task list) do not depend on the main SHA. At the
# ``5-execute → 6-finalize`` boundary, however, ``main_sha`` change DOES
# matter (it can invalidate the integration premise the just-built changes
# were merged on top of), so those two invariants remain blocking there.
#
# Other invariants (``task_state_hash``, ``qgate_open_count``,
# ``config_hash``, ``references_valid``, ``phase_steps_complete``,
# ``pending_findings_blocking_count``, ``unfinished_tasks_count``,
# ``pending_findings_by_type``, ``task_graph_valid``) describe plan-internal
# state that should remain stable across every boundary and stay blocking
# everywhere.
#
# Retained-vs-relaxed worktree-state drift map (Option 5', ADR-002):
#
# - ``main_dirty_files`` (layer-D leak-into-main), ``worktree_sha``,
#   ``worktree_dirty``, ``worktree_orphan`` are RELAXED for the phase-5+
#   boundaries the cwd-pinned move model makes safe and RETAINED for the
#   phases-1-4 boundaries (scope ``_WORKTREE_STATE_DRIFT_BLOCKING_PHASES``).
#   Once phase-5 materializes the worktree and moves the plan dir in, the
#   orchestrator's cwd IS the worktree and the single cwd-unchanged invariant
#   (asserted by ``file_ops.guard_worktree_cwd``) keeps it pinned there, so a
#   sideways worktree-SHA/dirty comparison and a leak-into-main guard have
#   nothing to catch. They still matter at the planning-phase boundaries that
#   run on main, where a leak or an orphan-dir/metadata mismatch can occur.
#   The layer-D verify check ``_check_main_dirty_drift`` mirrors this gate:
#   it fires only for the pre-materialization phases. The discriminator is
#   the boundary phase already known to the handshake — NOT a runtime
#   resolver branch — so the handshake never references a removed check at a
#   boundary that still needs it.

BlockingScope = str | frozenset[str]

# Phase boundaries at which the worktree-state drift invariants still add
# value, keyed on the boundary phase the handshake verifies (the phase being
# transitioned OUT of). Under the move-based, cwd-pinned hermetic worktree
# model (ADR-002 / Option 5'), the on-disk worktree directory and feature
# branch are materialized at phase-5 start and the plan dir is MOVED into the
# worktree; from that point the orchestrator's cwd IS the worktree and never
# leaves it (the single cwd-unchanged invariant, asserted by
# ``file_ops.guard_worktree_cwd``). The sideways worktree-state comparisons
# (worktree_sha / worktree_dirty / worktree_orphan) and the layer-D
# leak-into-main guard (main_dirty_files) are therefore STRUCTURALLY MOOT at
# the ``5-execute → 6-finalize`` boundary: plan work lands in the worktree by
# construction, so there is nothing for these checks to catch. They REMAIN
# blocking at the planning-phase boundaries (1→2, 2→3, 3→4, 4→5), which still
# run on the main checkout where a leak could legitimately occur. The
# discriminator is the boundary phase, NOT a runtime resolver branch.
_WORKTREE_STATE_DRIFT_BLOCKING_PHASES: frozenset[str] = frozenset({
    '1-init',
    '2-refine',
    '3-outline',
    '4-plan',
})


INVARIANT_BLOCKING_SCOPE: dict[str, BlockingScope] = {
    'main_sha': frozenset({'5-execute'}),
    'main_dirty': frozenset({'5-execute'}),
    # Relaxed for phase-5+ per Option 5' (cwd-pinned move model): the layer-D
    # leak-into-main guard is moot once the orchestrator's cwd is the worktree.
    # Retained for the phases-1-4 boundaries that still operate on main.
    'main_dirty_files': _WORKTREE_STATE_DRIFT_BLOCKING_PHASES,
    # Relaxed for phase-5+: the sideways worktree-SHA / worktree-dirty
    # comparisons are subsumed by main_sha / main_dirty once cwd IS the
    # worktree. The inverse-direction worktree_orphan writer-chain check is
    # likewise moot post-materialization (the move-in makes the worktree-
    # resident plan dir the signal); it stays blocking at the planning-phase
    # boundaries where an orphan-dir-vs-metadata mismatch can still surface.
    'worktree_sha': _WORKTREE_STATE_DRIFT_BLOCKING_PHASES,
    'worktree_dirty': _WORKTREE_STATE_DRIFT_BLOCKING_PHASES,
    'worktree_orphan': _WORKTREE_STATE_DRIFT_BLOCKING_PHASES,
    'references_valid': 'blocking_at_every_boundary',
    'task_state_hash': 'blocking_at_every_boundary',
    'qgate_open_count': 'blocking_at_every_boundary',
    'config_hash': 'blocking_at_every_boundary',
    'unfinished_tasks_count': 'blocking_at_every_boundary',
    'phase_steps_complete': 'blocking_at_every_boundary',
    'task_graph_valid': 'blocking_at_every_boundary',
    'pending_findings_by_type': 'blocking_at_every_boundary',
    'pending_findings_blocking_count': 'blocking_at_every_boundary',
}


def is_invariant_blocking_at_phase(invariant_name: str, phase: str) -> bool:
    """Return True when drift in ``invariant_name`` is blocking at ``phase``.

    ``phase`` is the ``--phase`` argument passed to
    ``phase_handshake verify`` — by the handshake's call convention this is
    the *captured* phase whose row is being re-verified, i.e. the phase the
    orchestrator is transitioning OUT of. For example, the
    ``5-execute → 6-finalize`` boundary is verified via
    ``verify --phase 5-execute``, so an invariant scoped to
    ``frozenset({'5-execute'})`` blocks at that boundary.

    Default behaviour for any unmapped invariant is
    ``blocking_at_every_boundary`` (fail-safe to the pre-classification
    behaviour) — new invariants added to ``INVARIANTS`` without a
    corresponding ``INVARIANT_BLOCKING_SCOPE`` entry retain the strict
    semantics until they are explicitly relaxed.
    """
    scope = INVARIANT_BLOCKING_SCOPE.get(invariant_name, 'blocking_at_every_boundary')
    if scope == 'blocking_at_every_boundary':
        return True
    if scope == 'informational_only':
        return False
    if isinstance(scope, frozenset):
        return phase in scope
    # Unknown scope value — fail safe to blocking so misconfiguration cannot
    # silently disable an invariant.
    return True


def capture_all(plan_id: str, metadata: dict[str, Any], phase: str) -> dict[str, Any]:
    """Run every applicable invariant and return name -> captured value.

    Non-applicable invariants are omitted from the return dict so callers can
    store empty strings or skip comparison during verify.
    """
    captured: dict[str, Any] = {}
    for name, applies_fn, capture_fn in INVARIANTS:
        if not applies_fn(plan_id, metadata):
            continue
        value = capture_fn(plan_id, metadata, phase)
        if value is None:
            continue
        captured[name] = value
    return captured
