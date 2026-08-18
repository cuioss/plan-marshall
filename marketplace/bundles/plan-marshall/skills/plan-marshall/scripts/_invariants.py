# SPDX-License-Identifier: FSL-1.1-ALv2
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

from _git_helpers import git_dirty_count, git_dirty_files, git_head
from _plan_state_exemption import partition_plan_state_exemption
from constants import QGATE_PHASES
from file_ops import get_base_dir, get_marshal_path
from marketplace_paths import (
    base_dir_override_active,
    find_marketplace_path,
    main_checkout_root,
)
from toon_parser import parse_toon


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
    at a guarded phase boundary while one or more *actionable-type* findings
    remain in ``pending`` resolution.

    The actionable-vs-knowledge partition is a FIXED, hardcoded rule (see
    :data:`_ACTIONABLE_FINDING_TYPES`) — NOT a per-phase ``marshal.json``
    config slot. ACTIONABLE types (``build-error``, ``test-failure``,
    ``lint-issue``, ``sonar-issue``, ``qgate``, ``pr-comment``) block when
    pending; KNOWLEDGE types (``insight``, ``tip``, ``best-practice``,
    ``improvement``) are NEVER counted. This is NOT naive
    "any pending finding blocks": knowledge types are excluded by the fixed
    rule. Resolutions counting as "resolved" are ``fixed``, ``suppressed``,
    ``accepted``, ``taken_into_account``, and ``rejected`` (the
    validity-verification / ext-point-verify refuted-finding state); only
    ``pending`` counts toward the block. The blocking count is computed by
    querying ``--resolution pending`` exclusively, so any non-``pending``
    resolution — ``rejected`` included — is structurally non-blocking: a
    ``rejected`` finding is never returned by the pending query and therefore
    cannot raise the gate.

    The ``blocking_types`` attribute carries the hardcoded actionable set so
    the structured TOON error payload (``error: blocking_findings_present``)
    surfaces which finding types are gated, preserving the consumer envelope
    contract in ``_handshake_commands.py``.

    Firing sites (where this exception surfaces):

    - The finalize **merge boundary**, where ``branch-cleanup`` runs
      ``phase_handshake findings-check --phase 6-finalize`` before the merge
      (the exception fires on a pending actionable finding and blocks the merge).
    - The finalize **completion boundary**, where the lifecycle verbs
      (``manage-status transition --completed 6-finalize`` /
      ``manage-status archive``) call :func:`assert_finalize_findings_clean`
      and refuse to mark the plan complete while an actionable finding is
      pending. This is a STATE the boundary asserts — armed by *reaching* the
      boundary — rather than a capture *call* that must have been issued
      earlier. A missing call used to be indistinguishable from a passing
      gate (both leave no row and raise nothing); the completion boundary
      closes that by evaluating the findings directly.

    The ``5-execute → 6-finalize`` transition is **not** a firing site: it
    inlines ``phase_handshake verify --phase 5-execute --strict``, which detects
    drift on the captured ``5-execute`` row but does not raise this exception —
    the raise is gated on ``phase == '6-finalize'``, and the self-review findings
    the gate catches are filed *during* finalize, after that boundary. A composite
    ``capture --phase 6-finalize`` would raise, but no orchestration step issues
    one; the two firing sites above are the actual arming, a state rather than a
    never-emitted call.

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


class MainCheckoutDirtiedDuringPlan(Exception):
    """Raised when the main checkout's dirty-file set is a proper superset of
    the previous-boundary baseline during a worktree-routed plan.

    This is the layer-D enforcement gap: layers A/B/C of worktree routing are
    closed (``manage-*`` cwd-agnostic, ``--plan-id`` auto-routing, raw tool
    flags using the resolved path), but layer D (any tool that touches the
    filesystem free-form — ``Edit`` / ``Write`` / ``Bash`` / external CLIs)
    has no enforcement and relies on prompt discipline alone. A ``PreToolUse``
    hook was considered and rejected for being host-platform-specific
    (Claude-Code-only — fails on
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


class MainCaptureReadTheWorktree(Exception):
    """Raised by :func:`capture_all` when the ``main_*`` columns were read from
    the plan's own worktree instead of from main.

    ``main_sha`` equals ``worktree_sha`` **and** the two columns resolved to the
    same directory, so one tree is being reported under two names. That is a
    capture bug, not a valid row, so ``cmd_capture`` surfaces a structured error
    and refuses to persist.

    ⚠ **The evidence is the resolved PATHS, not the row.** The comparison reads
    :func:`_main_repo_root` (a live git probe) and ``metadata.worktree_path``;
    neither is a stored column. So this refusal is available at capture time and
    NOT to a later reader of the persisted row, for whom an equal pair is merely
    ambiguous — see ``plan-marshall:plan-retrospective`` →
    ``references/invariant-check-summary.md`` for what such a reader can do
    instead.

    ⚠ **The refused ``main_sha`` is not necessarily a commit that never reached
    main.** Under a base-dir override the resolver follows the working
    directory, so a plan whose feature branch carries no commit can trip this
    refusal on a value that IS main's HEAD. The defect being refused is the
    mis-resolution, not the commit.

    ⛔ **Equal commits alone are NOT the trigger** — the same-tree resolution is.
    Two DISTINCT trees can legitimately hold one commit: a worktree-backed plan
    whose feature branch carries no commit of its own yet still has its HEAD on
    the commit it branched from. That state is produced by the shipped phase-5
    flow (``phase-5-execute`` Step 2.5 materializes the worktree unconditionally,
    before the ``early_terminate`` short-circuit, so an analysis-only plan never
    commits on its branch), and refusing it would hard-block a legitimate
    boundary with no override escape. It is therefore permitted, and the row it
    writes is a correct one — ``main_sha`` genuinely is main's HEAD.

    A plan with no persisted ``metadata.worktree_path`` captures no
    ``worktree_sha`` at all (see :func:`_worktree_in_use`, which keys on that
    path and does NOT read ``use_worktree``), so there is nothing to compare and
    this refusal cannot fire.
    """

    def __init__(
        self,
        phase: str,
        sha: str,
        *,
        main_root: Path,
        worktree_path: Path,
    ) -> None:
        self.phase = phase
        self.sha = sha
        self.main_root = str(main_root)
        self.worktree_path = str(worktree_path)
        super().__init__(
            f'phase {phase}: the main-scoped capture read the plan worktree — '
            f'main_sha == worktree_sha ({sha}) and both resolved to '
            f'{main_root}. A column named for main must be read from main; '
            f'repair the main-anchored resolution (_main_repo_root) before '
            f're-entering the phase.'
        )


class TaskGraphInvalid(Exception):
    """Raised by the ``task_graph_valid`` invariant capture when the plan's
    task dependency graph has a cycle or a dangling reference (a
    ``depends_on`` entry that does not match any existing task number).

    Shaped like :class:`PhaseStepsIncomplete`: the constructor formats a
    descriptive message and keeps the structured fields (``cycle``,
    ``dangling``) as attributes so a caller can surface a structured error
    payload and refuse to persist the handshake row — thereby blocking the
    phase transition on a broken task graph.

    ⚠ **No caller currently does.** ``cmd_capture`` handles its four sibling
    capture-time exceptions and not this one, so the attributes are carried but
    never rendered; see :func:`_capture_task_graph_valid` for what reaches the
    operator instead.
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


class PrTitleMissing(Exception):
    """Raised by the ``pr_title_present`` invariant capture when the invariant
    applies (phase ``2-refine`` onward) but ``status.metadata.pr_title`` is
    absent or empty/whitespace-only.

    Shaped like :class:`PhaseStepsIncomplete` / :class:`TaskGraphInvalid`: the
    constructor formats a descriptive message and keeps the structured ``phase``
    field as an attribute so ``cmd_capture`` can surface a structured error
    payload (``error: pr_title_missing``) and refuse to persist the handshake
    row — thereby blocking the phase transition until phase-2-refine Step 13
    authors and persists the PR title.
    """

    def __init__(self, phase: str):
        self.phase = phase
        super().__init__(
            f'pr_title_present failed for phase {phase!r}: '
            'metadata.pr_title is absent or empty — phase-2-refine Step 13 must '
            'author and persist a commit-style PR title via '
            '`manage-status metadata --set --field pr_title`'
        )


AppliesFn = Callable[[str, dict[str, Any]], bool]
CaptureFn = Callable[[str, dict[str, Any], str], Any]


# --- helpers --------------------------------------------------------------


def _current_repo_root() -> Path:
    """The CURRENT checkout root, resolved by the uniform cwd rule (ADR-002).

    ``get_base_dir()`` resolves to ``<root>/.plan/local``, so the parent chain
    ``.plan/local → .plan → root`` identifies the checkout the working directory
    is standing in. In tests, ``PLAN_BASE_DIR`` may point somewhere else; in
    that case we fall back to the current working directory.

    This follows the pinned worktree at phase-5+ **by design** — that is what
    every cwd-relative consumer wants (the worktree-resident executor and the
    plan state moved in at phase-5 start; see ``file_ops.get_executor_path``).

    ⛔ It is therefore the WRONG resolver for a ``main_``-named capture: under a
    pinned worktree it returns the worktree, so a main-scoped column would
    silently record a feature-branch commit. Those captures use
    :func:`_main_repo_root` instead.
    """
    try:
        base = get_base_dir()
    except RuntimeError:
        return Path.cwd()
    if base.name == 'local' and base.parent.name == '.plan':
        return base.parent.parent
    return Path.cwd()


def _main_repo_root() -> Path | None:
    """The MAIN checkout root — the tree the ``main_*`` columns claim to describe.

    Distinct from :func:`_current_repo_root`, which follows the pinned worktree
    at phase-5+. The property this resolver adds is **worktree-invariance**: it
    names the same main checkout from any tree in the repository, a linked
    worktree included. It is NOT cwd-independent in general — see the precision
    note below — and the defect it exists to close is precisely the worktree
    case.

    Precedence, in the shape ``marketplace_paths.resolve_main_anchored_path``
    (the single sanctioned main-anchored exception, ADR-002) uses — override
    first, then git:

    1. **Base-dir override** (``PLAN_BASE_DIR`` / ``set_base_dir()``) — delegate
       to :func:`_current_repo_root`. An override-based fixture has exactly one
       checkout, so main and current coincide there.
    2. **Production** — ``git rev-parse --git-common-dir`` points at main's
       ``.git`` even when invoked from a linked worktree; its parent is the main
       checkout root.

    ⚠ **Precision, because the strong claim is easy to over-state.** Neither
    branch is cwd-*independent*:

    - The override branch inherits ``_current_repo_root``'s own fallback. For
      the canonical override shape ``<root>/.plan/local`` it returns ``<root>``
      regardless of cwd; for a **flat** override (a bare directory, which is
      what the test sandbox installs) no checkout is named at all and the result
      is ``Path.cwd()``. That is harmless where it occurs — one checkout — but it
      is not cwd-independence, and this resolver does not claim it.
    - The git branch runs ``git rev-parse`` in the process cwd, so it resolves
      whichever *repository* the process is in. Within one repository it is
      invariant across main and every linked worktree, which is the property the
      ``main_*`` columns need.

    Returns:
        The main checkout root, or ``None`` when it cannot be resolved (not a
        git repository, or git is unavailable).

    ⛔ The ``None`` return is deliberate and MUST NOT be softened into a cwd
    fallback. An unresolvable main checkout is *unknown*, and a main-scoped
    column whose value is unknown is left EMPTY (the registry's documented
    "not applicable" contract) rather than filled with the tree the process
    happens to occupy. This applies to the git branch, where the defect lives;
    the override branch is a caller's explicit declaration of where state
    lives and is honoured as such.
    """
    if base_dir_override_active():
        return _current_repo_root()
    try:
        return main_checkout_root()
    except RuntimeError:
        return None


# Phases at and after which the worktree is materialized on disk (phase-5
# Step 2.5 creates the worktree directory and feature branch; phase-6 inherits
# it). The single source of truth for "is the worktree materialized?" — an
# empty ``worktree_path`` while one of these phases is active is the transient
# window between phase entry and Step 2.5's backfill, so these phases are
# treated as materialized regardless of the path value.
_WORKTREE_MATERIALIZED_PHASES: frozenset[str] = frozenset({
    '5-execute',
    '6-finalize',
})


def _worktree_materialized(metadata: dict[str, Any], phase: str | None) -> bool:
    """Unified worktree-applicability predicate.

    Returns ``True`` when the plan's worktree is materialized — either because
    ``metadata.worktree_path`` is present and non-empty (the worktree directory
    has been created and the path persisted) OR because ``phase`` is one of the
    materialization phases (:data:`_WORKTREE_MATERIALIZED_PHASES`), which covers
    the transient phase-5 window between phase entry and Step 2.5's path
    backfill.

    This is the single predicate both the invariant-applicability gate
    (:func:`_worktree_in_use`) and the phase-entry assertion
    (``_handshake_commands._resolve_worktree_assertion``) consult, so the two
    surfaces can never disagree on whether the worktree is in play.
    """
    raw = metadata.get('worktree_path')
    if raw is not None and str(raw).strip():
        return True
    return phase in _WORKTREE_MATERIALIZED_PHASES


def _worktree_in_use(_plan_id: str, metadata: dict[str, Any]) -> bool:
    """Gate worktree-state captures on the unified materialization predicate.

    The worktree-state invariants (``worktree_sha`` / ``worktree_dirty``)
    apply exactly when the plan's worktree is materialized. Delegates to
    :func:`_worktree_materialized` with ``phase=None`` so the gate is keyed on
    the persisted ``worktree_path`` alone — the capture functions themselves
    return ``None`` when ``worktree_path`` is not yet populated, so a
    pre-materialization capture simply records an empty column.
    """
    return _worktree_materialized(metadata, None)


def _always(_plan_id: str, _metadata: dict[str, Any]) -> bool:
    return True


def _run_script(args: list[str]) -> str | None:
    """Invoke ``execute-script.py`` with ``args`` and return stdout on success."""
    repo = _current_repo_root()
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

        - push
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
    IDs are returned verbatim — bare for built-ins (``push``), prefixed
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
    """HEAD SHA of the MAIN checkout, read worktree-invariantly.

    Read via :func:`_main_repo_root` — never the cwd-relative resolver, which
    under a pinned worktree would record the feature-branch commit in a column
    named for main. Returns ``None`` (column left empty) when the main checkout
    cannot be resolved, matching the registry's "not applicable" contract.

    ⚠ **Worktree-invariant, not cwd-independent** — see :func:`_main_repo_root`
    for which branch has which property. The value is stable across main and
    every linked worktree of one repository, which is what this column needs;
    it is not stable across repositories or under a flat base-dir override.
    """
    root = _main_repo_root()
    if root is None:
        return None
    return git_head(root)


def _capture_main_dirty(_plan_id: str, _metadata: dict[str, Any], _phase: str) -> Any:
    """Porcelain dirty-path count of the MAIN checkout, read worktree-invariantly.

    Same resolution contract — and the same worktree-invariant-not-cwd-independent
    caveat — as :func:`_capture_main_sha`.
    """
    root = _main_repo_root()
    if root is None:
        return None
    return git_dirty_count(root)


def _filter_main_dirty_paths(paths: list[str], tree: str | Path) -> list[str]:
    """Filter ``paths`` to the main-checkout dirty set that counts as drift.

    Delegates to the SHARED ``.plan/`` exemption
    (:func:`_plan_state_exemption.partition_plan_state_exemption`), which the
    post-run source guard also uses, so the two guards apply ONE rule rather than
    two copies of it — two copies is how the second guard stayed live after the
    first was noticed.

    A ``.plan/`` path is dropped ONLY when it is NOT git-tracked in ``tree``. The
    ``.plan/`` directory holds untracked runtime state (status, logs, lessons)
    whose churn during a worktree-routed plan is normal phase-boundary
    bookkeeping and MUST NOT trip the invariant — but it ALSO holds git-tracked
    files (``marshal.json``, the architecture descriptors), and a dirtied tracked
    one IS a real leak into the main checkout that must be reported. A path
    outside ``.plan/`` is kept unchanged.

    Args:
        paths: The porcelain-string set from :func:`_git_helpers.git_dirty_files`.
        tree: The main-checkout root ``paths`` were observed against, used to
            resolve trackedness.

    Returns:
        The retained (drift-relevant) subset, sorted and de-duplicated.
    """
    retained, _exempted = partition_plan_state_exemption(paths, tree)
    return retained


def _capture_main_dirty_files(_plan_id: str, _metadata: dict[str, Any], _phase: str) -> Any:
    """Sorted list of main-checkout dirty paths, filtered to exclude UNTRACKED ``.plan/``.

    Layer-D enforcement capture (paired with :func:`_verify_main_dirty_drift`
    which is invoked at verify time, not via the registry — drift detection
    is comparison-based and needs the persisted baseline row, which the
    capture-time signature does not expose).

    Returns ``None`` when the MAIN checkout cannot be resolved
    (:func:`_main_repo_root`) or when the dirty-file probe against it fails
    (not a git repository or git invocation error), so the calling capture's
    "not applicable" contract leaves the column empty in stored rows. Otherwise returns the
    sorted, exemption-filtered list — the ``.plan/`` exemption drops only
    UNTRACKED plan state and retains a dirtied *tracked* ``.plan/`` file
    (``marshal.json``, a descriptor) as a real leak (see
    :func:`_filter_main_dirty_paths`). Callers persist the list verbatim
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
    repo = _main_repo_root()
    if repo is None:
        return None
    raw = git_dirty_files(repo)
    if raw is None:
        return None
    return _filter_main_dirty_paths(raw, repo)


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


# Required top-level keys that phase-1-init promises to write into
# references.json (branch, base_branch). The list is sorted so the hash
# payload is deterministic regardless of insertion order.
#
# ``modified_files`` was intentionally dropped from this set: it is no longer
# part of the references-invariant contract. A references.json written before
# the key was retired still passes ``references_valid`` because the key is
# absent from the required-keys intersection — the tolerant read path treats a
# missing ``modified_files`` as valid rather than as drift. This keeps the
# blocking ``references_valid`` handshake hash stable for in-flight plans whose
# references.json predates the change.
# SHIM(B): references.json written before the modified_files key was retired (excluded from the required-keys intersection).
# shim-owner: plan-marshall
# shim-floor: the change that dropped modified_files from the references required-key contract (_REFERENCES_REQUIRED_KEYS); the tolerant read treats a missing modified_files as valid rather than as drift. Predates this shallow clone's root (dcd3c00 / #1105), so not PR-pinnable here.
# shim-remove-when: no in-flight plan's references.json predates the key retirement.
_REFERENCES_REQUIRED_KEYS: tuple[str, ...] = ('base_branch', 'branch')


def _capture_references_valid(plan_id: str, _metadata: dict[str, Any], _phase: str) -> Any:
    """Drift-detection hash over the structural health of references.json.

    Phase-1-init is the sole writer of ``references.json``; every downstream
    phase depends on the file existing and having the structural fields that
    phase-1-init promises (``branch``, ``base_branch``). Silent deletion,
    corruption to a non-dict, or a missing required field survives all current
    invariants and only surfaces at random call sites.

    ``modified_files`` is no longer a required key (see
    :data:`_REFERENCES_REQUIRED_KEYS`); a references.json without it — whether
    written before the key was retired or by a writer that omits it — still
    produces a stable, passing hash because the key is excluded from the
    required-field intersection.

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

    On failure raises :class:`TaskGraphInvalid`, which leaves no handshake row
    persisted and blocks the phase transition.

    ⚠ **Unlike its four sibling capture-time exceptions, this one has no handler
    in ``cmd_capture``**, so it is not converted into a structured
    ``status: error`` payload with its ``cycle`` / ``dangling`` fields — it
    propagates out of the verb and ``file_ops.safe_main`` renders it as
    ``error: internal_error`` with exit 1. The boundary still fails closed (that
    part of the outcome is unchanged), but the operator loses the structured
    diagnosis. Pre-existing; noted here so the mechanism is not mistaken for the
    handled path the siblings take.

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

# FIXED, hardcoded actionable-vs-knowledge partition (user-approved; replaces
# the per-phase ``marshal.json`` ``blocking_finding_types`` config slot and the
# ``determine_mode`` partition import). ACTIONABLE finding types block when
# ``pending``; the KNOWLEDGE types (``insight``, ``tip``, ``best-practice``,
# ``improvement``) are NEVER counted. This is NOT naive "any pending finding
# blocks" — knowledge types are excluded by this fixed rule, which is the
# lifecycle guard the blocking gate requires. The set lives here so the
# invariant is self-sufficient: no config read, no cross-module import.
#
# ``qgate`` is in the set but lives in per-phase ``findings/qgate-{phase}.jsonl``
# files rather than the canonical per-type ``findings/{type}.jsonl`` layout, so
# it is counted via :func:`_query_pending_qgate_count_aggregated` (the qgate
# aggregation path) instead of the generic per-type query.
_ACTIONABLE_FINDING_TYPES: tuple[str, ...] = (
    'build-error',
    'test-failure',
    'lint-issue',
    'sonar-issue',
    'qgate',
    'pr-comment',
)


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
    blocking-count check before this helper existed.

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


def _capture_pending_findings_blocking_count(
    plan_id: str,
    _metadata: dict[str, Any],
    phase: str,
) -> Any:
    """Sum of pending findings whose type is in the FIXED *actionable* set.

    Applies the hardcoded actionable-vs-knowledge rule
    (:data:`_ACTIONABLE_FINDING_TYPES`) — NOT a per-phase ``marshal.json``
    config partition. ACTIONABLE types (``build-error``, ``test-failure``,
    ``lint-issue``, ``sonar-issue``, ``qgate``, ``pr-comment``) count toward
    the block when ``pending``; KNOWLEDGE types (``insight``, ``tip``,
    ``best-practice``, ``improvement``) are NEVER counted. This is NOT naive
    "any pending finding blocks": knowledge types are excluded by the fixed
    rule.

    Each actionable type is counted via :func:`_query_pending_count_for_type`
    (the per-type JSONL query), except ``qgate`` which lives in per-phase
    ``findings/qgate-{phase}.jsonl`` files and is summed via
    :func:`_query_pending_qgate_count_aggregated` (the qgate aggregation
    path is preserved verbatim).

    Both query paths filter on ``--resolution pending``, so a finding closed
    with any non-``pending`` resolution — including ``rejected`` (the
    ext-point-verify refuted-finding state) — is never returned and contributes
    zero to the blocking count. A ``rejected`` finding is therefore provably
    non-blocking: it cannot raise :class:`BlockingFindingsPresent`.

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
    per_type: dict[str, int] = {}
    total = 0
    for finding_type in _ACTIONABLE_FINDING_TYPES:
        if finding_type == 'qgate':
            count = _query_pending_qgate_count_aggregated(plan_id)
        else:
            count = _query_pending_count_for_type(plan_id, finding_type)
        if count is None:
            # Partial query failure — fall back to "not applicable" rather
            # than under-counting and silently letting a transition advance.
            return None
        per_type[finding_type] = count
        total += count

    if total > 0 and phase in _BLOCKING_BOUNDARIES:
        raise BlockingFindingsPresent(
            phase=phase,
            blocking_count=total,
            per_type=per_type,
            blocking_types=list(_ACTIONABLE_FINDING_TYPES),
        )
    return total


def assert_finalize_findings_clean(plan_id: str, metadata: dict[str, Any]) -> int | None:
    """Self-arming blocking-findings STATE assertion for the finalize completion boundary.

    This is the ``call → state`` conversion at the heart of the merge-boundary
    guard. The blocking-findings gate historically fired only when a
    ``phase_handshake capture --phase 6-finalize`` *call* happened to be issued;
    a missing call left no row and raised nothing, so *"the gate never ran"* was
    indistinguishable from *"the gate passed"*. This helper bakes the guarded
    phase (:data:`_BLOCKING_BOUNDARIES` — ``6-finalize``) into the assertion so a
    caller cannot disarm it by passing a non-guarded phase: reaching the finalize
    completion boundary is itself the arming condition.

    Delegates to :func:`_capture_pending_findings_blocking_count` at the
    ``6-finalize`` phase, so it:

    - **raises** :class:`BlockingFindingsPresent` when any actionable-type finding
      is still ``pending`` (the boundary must refuse to mark the plan complete);
    - returns ``0`` when the actionable-findings state is clean;
    - returns ``None`` when the underlying query could not be evaluated (executor
      unreachable / partial query failure), matching the capture's
      "not applicable" contract. The completion-boundary caller treats ``None`` as
      *unevaluable* (see ``_cmd_lifecycle``); the fail-closed handling of a genuine
      partial query failure is owned by the pre-merge ``findings-check`` gate,
      where the executor is guaranteed present.

    The predicate itself is UNCHANGED — the actionable-vs-knowledge partition and
    the pending-resolution aggregation are exactly what
    :func:`_capture_pending_findings_blocking_count` already applies. This helper
    only fixes *where and how the gate is armed*.
    """
    count = _capture_pending_findings_blocking_count(plan_id, metadata, '6-finalize')
    if count is None:
        return None
    return int(count)


def _capture_config_hash(_plan_id: str, _metadata: dict[str, Any], _phase: str) -> Any:
    """Fingerprint the plan-governing configuration, independent of the phase.

    Returns a stable SHA of the ``plan`` section of ``marshal.json``. The value
    is deliberately **phase-independent**: the same configuration hashes to the
    same value at every boundary. That is what the two consumers need to
    discriminate:

    - the cross-phase drift scan (``summarize-invariants.detect_drift``) reports a
      drift only when the config genuinely changed between two phases, instead of
      firing at every boundary;
    - the same-phase re-verify (``_handshake_commands.cmd_verify``) still blocks on
      a real mid-phase config change (``blocking_at_every_boundary`` classification
      retained).

    This replaces the earlier ``manage-config plan phase-{phase} get`` capture,
    which had two defects. (1) It keyed the hash on ``phase-{phase}`` — a different
    config subtree at every phase — so the value changed at every boundary *by
    construction* and the cross-phase scan flagged a spurious drift every time (it
    could not tell a real config change from the phase simply advancing). (2) It
    passed ``--audit-plan-id``, which the ``plan`` noun does not accept, so the
    subprocess exited non-zero and the capture was silently ``None`` at every
    boundary — a signal that never fired at all. Reading the phase-independent
    ``plan`` section fixes both.

    The whole-checkout stability of ``marshal.json`` (worktree vs. main resolution
    when a plan edits ``marshal.json`` on its branch) is out of scope here — that
    is the repository-root resolver owned by the main-scoped-field plan.

    Returns ``None`` (not-applicable) when ``marshal.json`` is absent or
    unreadable, fail-closed, so a transient read failure never surfaces as a false
    "config emptied" drift.
    """
    marshal_path = get_marshal_path()
    if not marshal_path.exists():
        return None
    try:
        config = json.loads(marshal_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(config, dict):
        return None
    return _hash_dict(config.get('plan', {}))


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
        # SHIM(B): bare-string phase_steps entries; mark-step-done now stores dicts, so these are detected and rejected as legacy drift.
        # shim-owner: plan-marshall
        # shim-floor: the mark-step-done change that switched phase_steps step storage to {"outcome": ..., "display_detail": ...} dicts; there is no automatic migration for the old bare-string shape. Predates this shallow clone's root (dcd3c00 / #1105), so not PR-pinnable here.
        # shim-remove-when: no status.json can still carry a bare-string phase_steps entry.
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


def _capture_pr_title_present(_plan_id: str, metadata: dict[str, Any], phase: str) -> Any:
    """Verify that a commit-style PR title has been authored and persisted.

    phase-2-refine Step 13 authors a commit-style PR title from the clarified
    request and persists it to ``status.metadata.pr_title``; phase-6-finalize
    ``create-pr.md`` reads it as the deterministic ``--title`` source. This
    invariant guards that the title survives every boundary from refine onward.

    Phase gate (lives inside the capture, mirroring
    :func:`_capture_qgate_open_count` — the ``applies_fn`` signature is
    ``(plan_id, metadata)`` and does NOT receive ``phase``, so the
    phase-conditional logic MUST branch on ``phase`` here, registered with
    :func:`_always`):

    - At ``1-init`` the title does not yet exist (refine authors it), so return
      ``None`` — the column stays empty pre-refine and is skipped during verify.
    - At ``2-refine`` and every later phase, read ``metadata.pr_title``:
      - non-empty after ``str(...).strip()`` → return a stable present-sentinel
        hash ``_hash_dict({'present': True})``. The sentinel encodes only the
        PRESENCE of the title, not its content, so a legitimate title edit does
        NOT trip drift detection.
      - empty / missing / whitespace-only → raise :class:`PrTitleMissing` so
        ``cmd_capture`` surfaces a structured error and refuses to persist the
        row, blocking the boundary.
    """
    if phase == '1-init':
        return None
    raw = metadata.get('pr_title')
    if raw is not None and str(raw).strip():
        return _hash_dict({'present': True})
    raise PrTitleMissing(phase)


# --- registry ------------------------------------------------------------

INVARIANTS: list[tuple[str, AppliesFn, CaptureFn]] = [
    ('main_sha', _always, _capture_main_sha),
    ('main_dirty', _always, _capture_main_dirty),
    ('main_dirty_files', _always, _capture_main_dirty_files),
    ('worktree_sha', _worktree_in_use, _capture_worktree_sha),
    ('worktree_dirty', _worktree_in_use, _capture_worktree_dirty),
    ('references_valid', _always, _capture_references_valid),
    ('task_state_hash', _always, _capture_task_state_hash),
    ('qgate_open_count', _always, _capture_qgate_open_count),
    ('config_hash', _always, _capture_config_hash),
    ('unfinished_tasks_count', _always, _capture_unfinished_tasks_count),
    ('phase_steps_complete', _always, _capture_phase_steps_complete),
    ('task_graph_valid', _always, _capture_task_graph_valid),
    ('pending_findings_by_type', _always, _capture_pending_findings_by_type),
    ('pending_findings_blocking_count', _always, _capture_pending_findings_blocking_count),
    ('pr_title_present', _always, _capture_pr_title_present),
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
# - ``main_dirty_files`` (layer-D leak-into-main), ``worktree_sha`` and
#   ``worktree_dirty`` are RELAXED for the phase-5+ boundaries the cwd-pinned
#   move model makes safe and RETAINED for the phases-1-4 boundaries (scope
#   ``_WORKTREE_STATE_DRIFT_BLOCKING_PHASES``). Once phase-5 materializes the
#   worktree and moves the plan dir in, the orchestrator's cwd IS the worktree
#   and the single cwd-unchanged invariant (asserted by
#   ``file_ops.guard_worktree_cwd``) keeps it pinned there, so a sideways
#   worktree-SHA/dirty comparison and a leak-into-main guard have nothing to
#   catch. They still matter at the planning-phase boundaries that run on main,
#   where a leak can occur. The layer-D verify check ``_check_main_dirty_drift``
#   mirrors this gate: it fires only for the planning phases. The discriminator
#   is the boundary phase already known to the handshake — NOT a runtime
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
# (worktree_sha / worktree_dirty) and the layer-D
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
    # worktree. They stay blocking at the planning-phase boundaries.
    'worktree_sha': _WORKTREE_STATE_DRIFT_BLOCKING_PHASES,
    'worktree_dirty': _WORKTREE_STATE_DRIFT_BLOCKING_PHASES,
    'references_valid': 'blocking_at_every_boundary',
    'task_state_hash': 'blocking_at_every_boundary',
    'qgate_open_count': 'blocking_at_every_boundary',
    'config_hash': 'blocking_at_every_boundary',
    'unfinished_tasks_count': 'blocking_at_every_boundary',
    'phase_steps_complete': 'blocking_at_every_boundary',
    'task_graph_valid': 'blocking_at_every_boundary',
    'pending_findings_by_type': 'blocking_at_every_boundary',
    'pending_findings_blocking_count': 'blocking_at_every_boundary',
    'pr_title_present': 'blocking_at_every_boundary',
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


def _assert_main_capture_read_main(
    captured: dict[str, Any],
    metadata: dict[str, Any],
    phase: str,
) -> None:
    """Refuse a row whose ``main_*`` columns were read from the worktree.

    Reached only when BOTH ``main_sha`` and ``worktree_sha`` were captured —
    which is exactly "a ``worktree_path`` is persisted", since ``worktree_sha``
    is gated on :func:`_worktree_in_use`. A plan with no persisted path captures
    no ``worktree_sha`` and is never examined here.

    Equal commits are the *symptom*; the refusal condition is the *cause* —
    both columns resolving to the same directory. Two distinct trees holding one
    commit is a legitimate state (a feature branch with no commit of its own)
    and is permitted; see :class:`MainCaptureReadTheWorktree`.

    Both early returns below the equality check are unreachable by
    construction — an unresolvable main checkout captures no ``main_sha``, and
    an empty ``worktree_path`` captures no ``worktree_sha``, so either would
    have short-circuited on the first guard. They are kept as defence rather
    than as a fail-open branch.

    ``worktree_path`` is resolved against the process cwd, exactly as
    ``_capture_worktree_sha``'s own git probe is, so the two agree. A relative
    path could therefore make the comparison miss a same-tree read (a false
    negative — the safe direction); in production the path is absolute,
    persisted from ``git worktree add``.

    Raises:
        MainCaptureReadTheWorktree: when the two commits are equal AND the two
            columns resolved to the same directory.
    """
    main_sha = captured.get('main_sha')
    worktree_sha = captured.get('worktree_sha')
    if not main_sha or not worktree_sha or main_sha != worktree_sha:
        return
    main_root = _main_repo_root()
    raw_worktree = metadata.get('worktree_path')
    if main_root is None or not raw_worktree:
        return
    worktree_path = Path(str(raw_worktree))
    try:
        if main_root.resolve() != worktree_path.resolve():
            return
    except OSError:
        return
    raise MainCaptureReadTheWorktree(
        phase,
        str(main_sha),
        main_root=main_root,
        worktree_path=worktree_path,
    )


def capture_all(plan_id: str, metadata: dict[str, Any], phase: str) -> dict[str, Any]:
    """Run every applicable invariant and return name -> captured value.

    Non-applicable invariants are omitted from the return dict so callers can
    store empty strings or skip comparison during verify.

    Raises:
        PhaseStepsIncomplete: when the phase declares ``required-steps.md`` and
            ``status.metadata.phase_steps[phase]`` is incomplete.
        BlockingFindingsPresent: when an actionable finding is pending at a
            boundary that blocks on findings.
        TaskGraphInvalid: when the task graph carries a cycle or a dangling
            reference. Unhandled by ``cmd_capture`` — see
            :func:`_capture_task_graph_valid`.
        PrTitleMissing: when ``metadata.pr_title`` is absent from ``2-refine``
            onward.
        MainCaptureReadTheWorktree: when the ``main_*`` columns were read from
            the plan's own worktree (cross-field check, run after the registry
            loop rather than by a single invariant).
    """
    captured: dict[str, Any] = {}
    for name, applies_fn, capture_fn in INVARIANTS:
        if not applies_fn(plan_id, metadata):
            continue
        value = capture_fn(plan_id, metadata, phase)
        if value is None:
            continue
        captured[name] = value
    _assert_main_capture_read_main(captured, metadata, phase)
    return captured
