#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Explicit findings-store handle and the closed state vocabulary it publishes.

The findings store is resolved cwd-relatively (ADR-002): ``plans/{plan_id}/``
moves INTO its worktree at phase-5 and back at finalize, so from the main
checkout the directory of a running plan is genuinely absent. Every read-side
surface used to hand that absence to ``jsonl_store.read_jsonl``, which returns
``[]`` for any non-existent path — making "this plan filed nothing" and "this
plan's directory is not under the root I resolved" byte-identical answers.

This module is the discriminator. :func:`resolve_findings_store` answers not
only *where* the store is but *whether it was reached, and how* — the same
explicit-handle shape ``manage-lessons`` ships in ``_lessons_io.LessonStore``.
Consumers merge :func:`store_state_fields` into every payload so a count is
always reported together with the substrate it was computed from, and refuse
(via :func:`unresolved_store_error`) rather than publish a zero for a store
they never reached.

Stdlib-only - no external dependencies (except shared modules via PYTHONPATH).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, NamedTuple

from constants import FILE_FINDINGS_DIR
from file_ops import get_base_dir, get_executor_path, get_store_dir
from marketplace_paths import PLAN_DIR_NAME, base_dir_override_active

#: The closed vocabulary :func:`resolve_findings_store` reports as ``resolution``.
#:
#: - ``cwd_relative`` — the store was anchored by the uniform cwd walk-up
#:   (ADR-002), which is the production path. It stands where the
#:   ``manage-lessons`` sibling has ``main_anchored``, because the findings store
#:   is cwd-keyed by design: it MOVES with its plan directory.
#: - ``override`` — a ``PLAN_BASE_DIR`` / ``set_base_dir()`` override stood in
#:   for the cwd walk-up, which is the test path.
#: - ``unresolved`` — no base directory could be resolved at all, so the caller
#:   never reached a store to look at.
#:
#: ``resolution`` answers "through which anchor", never "was anything there" —
#: that second question is :data:`FINDINGS_STORE_STATES`. Consumers assert
#: against this set rather than re-listing the literals.
STORE_RESOLUTIONS = frozenset({'cwd_relative', 'override', 'unresolved'})

#: The closed vocabulary :func:`resolve_findings_store` reports as ``state``.
#:
#: - ``present`` — the plan directory AND its ``artifacts/findings/`` both exist.
#: - ``missing`` — the plan directory exists but has no ``artifacts/findings/``
#:   yet. This is the BENIGN zero: a resolved plan that filed nothing. It keeps
#:   returning ``status: success`` with a genuine ``total_count: 0``.
#: - ``plan_absent`` — ``plans/{plan_id}/`` is not under the resolved root. The
#:   store was never reached, so no count computed against it means anything.
#: - ``unknown`` — the base directory itself could not be resolved, so not even
#:   the root is known.
#:
#: The state is decided on the PLAN directory, never on ``artifacts/findings/``:
#: a plan's first-ever finding legitimately creates that subdirectory, so a guard
#: keyed there would refuse every real plan's first write and turn the benign
#: zero into the inverse defect.
FINDINGS_STORE_STATES = frozenset({'present', 'missing', 'plan_absent', 'unknown'})

#: The subset of :data:`FINDINGS_STORE_STATES` on which a surface REFUSES.
#:
#: These are exactly the states in which the store was not reached, so a count,
#: a not-found verdict, or a write against it would be unsubstantiated. Held as
#: a named set because ``unresolved_store`` (the published boolean) and the
#: refusal branch in every consumer must be the same predicate.
UNREACHED_STORE_STATES = frozenset({'plan_absent', 'unknown'})

#: The canonical ``error`` code every surface returns for an unreached store.
FINDINGS_STORE_UNRESOLVED = 'findings_store_unresolved'

#: Wall-clock budget for the ``locate-plan-checkout`` consult (seconds).
_LOCATE_TIMEOUT_SECONDS = 20

#: Per-process memo of the ``locate-plan-checkout`` consult, keyed by
#: ``(resolved_root, plan_id)``. The consult spawns a subprocess, and a caller
#: that sweeps many findings would otherwise pay it once per call for the same
#: unreachable plan. The answer cannot change within a process without the
#: resolved root changing too, which is part of the key.
_LOCATE_CACHE: dict[tuple[str, str], Path | None] = {}


class FindingsStore(NamedTuple):
    """A resolved findings-store handle together with its resolution provenance.

    ``path`` is ``None`` exactly when ``resolution == 'unresolved'`` — no base
    directory was reached, so not even a candidate path can be composed. On every
    other resolution it is the absolute ``artifacts/findings/`` directory, which
    may or may not exist on disk; ``state`` is what says which.

    Callers compare ``resolution`` and ``state`` against a
    :data:`STORE_RESOLUTIONS` / :data:`FINDINGS_STORE_STATES` member by explicit
    equality — never by the truthiness of ``path``, which cannot tell a
    legitimately-empty store from one that was never reached.

    Attributes:
        path: The resolved absolute findings directory, or ``None`` when
            ``resolution == 'unresolved'``.
        resolution: One of :data:`STORE_RESOLUTIONS`.
        state: One of :data:`FINDINGS_STORE_STATES`.
        detail: Human-readable provenance naming the substrate (or, when the
            store was not reached, the reason) for direct inclusion in a
            report line.
    """

    path: Path | None
    resolution: str
    state: str
    detail: str


def _locate_plan_checkout(root: Path, plan_id: str) -> Path | None:
    """Return the worktree checkout root that holds ``plan_id``, or ``None``.

    Routes through the EXISTING ``git-workflow locate-plan-checkout`` verb rather
    than re-deriving a locator here: that verb already layers the canonical
    ``manage-status`` channel over the structural ``get_worktree_root() /
    {plan_id}`` probe, which is precisely the moved-in-from-main case this
    module exists to name.

    Two cheap gates run before the subprocess, because the consult costs a
    process spawn while the refusal it enriches has already been decided:

    1. **The worktree slot must exist.** Every locatable worktree is
       materialized at ``{root}/worktrees/{plan_id}`` — that is the layout
       ``worktree-create`` writes and the value it persists as
       ``metadata.worktree_path`` — so an absent slot means the verb has nothing
       to find and its answer is known in advance.
    2. **Per-process memo.** The answer is keyed by ``(root, plan_id)`` and
       cannot change within a process unless the resolved root does.

    Every failure mode — no resolvable executor, a non-zero exit, an unparsable
    payload, a ``current`` / ``not_found`` location — degrades to ``None``. The
    consult is an ENRICHMENT of a refusal that has already been decided, never
    the decision itself, so an unavailable locator must never change the verdict.
    """
    cache_key = (str(root), plan_id)
    if cache_key in _LOCATE_CACHE:
        return _LOCATE_CACHE[cache_key]

    located = _consult_locator(root, plan_id)
    _LOCATE_CACHE[cache_key] = located
    return located


def _consult_locator(root: Path, plan_id: str) -> Path | None:
    """The uncached body of :func:`_locate_plan_checkout`."""
    if not (root / 'worktrees' / plan_id).is_dir():
        return None

    try:
        executor = get_executor_path()
    except RuntimeError:
        return None
    if not executor.is_file():
        return None

    try:
        completed = subprocess.run(  # noqa: S603 — fixed argv, no shell, no caller-supplied executable
            [
                sys.executable,
                str(executor),
                'plan-marshall:workflow-integration-git:git-workflow',
                'locate-plan-checkout',
                '--plan-id',
                plan_id,
            ],
            capture_output=True,
            text=True,
            timeout=_LOCATE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None

    try:
        from toon_parser import parse_toon  # noqa: PLC0415 — deferred: keeps import cost off the happy path

        parsed = parse_toon(completed.stdout)
    except Exception:  # noqa: BLE001 — a malformed consult degrades to "no other checkout known"
        return None

    if not isinstance(parsed, dict) or parsed.get('location') != 'worktree':
        return None
    worktree_path = parsed.get('worktree_path')
    return Path(str(worktree_path)) if worktree_path else None


def _classify(plan_dir: Path, resolution: str) -> FindingsStore:
    """Build the handle for a plan directory that EXISTS under the resolved root."""
    findings_dir = plan_dir / 'artifacts' / FILE_FINDINGS_DIR
    state = 'present' if findings_dir.is_dir() else 'missing'
    return FindingsStore(
        findings_dir,
        resolution,
        state,
        f'{findings_dir} (resolved {resolution}, {state})',
    )


def resolve_findings_store(plan_id: str, any_checkout: bool = False) -> FindingsStore:
    """Resolve a plan's findings store and report HOW — and WHETHER — it resolved.

    The explicit handle behind ``_findings_core.get_findings_dir``. Where that
    resolver answers only "where is the store", this one also answers "did I
    actually reach it, and through which anchor" — the discriminator every
    findings surface needs in order to distinguish a plan that filed nothing from
    a plan whose directory is not under the root it resolved.

    Args:
        plan_id: Plan identifier whose store is being resolved.
        any_checkout: When ``True`` and the plan directory is absent under the
            resolved root, adopt the store of the checkout that actually holds
            the plan (resolved through ``locate-plan-checkout``). READ-ONLY by
            construction at the call sites: only the five read verbs pass it, so
            a write verb can never reach another checkout's store.

    Returns:
        A :class:`FindingsStore` handle. Never raises for an unresolvable base
        directory — that is returned as ``resolution='unresolved'`` /
        ``state='unknown'`` / ``path=None`` so the caller can report it, rather
        than as an exception a caller might swallow into a zero.
    """
    resolution = 'override' if base_dir_override_active() else 'cwd_relative'

    try:
        root = get_base_dir()
        plan_dir = get_store_dir('plans', plan_id)
    except RuntimeError as exc:
        return FindingsStore(
            None,
            'unresolved',
            'unknown',
            f'cannot resolve the plan-marshall runtime-state root for plan {plan_id!r}: {exc}',
        )

    if plan_dir.is_dir():
        return _classify(plan_dir, resolution)

    # The plan directory is not under the resolved root. Name the checkout that
    # DOES hold it when one can be found — that is the fact an operator needs,
    # and (under ``any_checkout``) the store a read verb may legitimately adopt.
    holder = _locate_plan_checkout(root, plan_id)
    if any_checkout and holder is not None:
        foreign_plan_dir = holder / PLAN_DIR_NAME / 'local' / 'plans' / plan_id
        if foreign_plan_dir.is_dir():
            store = _classify(foreign_plan_dir, resolution)
            return store._replace(
                detail=f'{store.detail}; adopted from the checkout {holder} via --any-checkout'
            )

    detail = (
        f'plan directory {plan_dir} is absent under the resolved root {root}, so the findings '
        f'store for plan {plan_id!r} was never reached'
    )
    if holder is not None:
        detail += (
            f'; the plan currently lives in the checkout {holder} — re-run the read verb with '
            '--any-checkout to read it from there'
        )
    return FindingsStore(
        plan_dir / 'artifacts' / FILE_FINDINGS_DIR,
        resolution,
        'plan_absent',
        detail,
    )


def store_state_fields(store: FindingsStore) -> dict[str, Any]:
    """Return the payload fragment every findings surface merges into its return.

    Four fields, published together so a count is never reported without the
    substrate it was computed from:

    - ``store_resolution`` — which anchor resolved the root.
    - ``store_path`` — the findings directory, or ``None`` when unresolved.
    - ``findings_store_state`` — one of :data:`FINDINGS_STORE_STATES`.
    - ``unresolved_store`` — ``True`` exactly when the state is in
      :data:`UNREACHED_STORE_STATES`, i.e. when the surface refused because the
      store was never reached. It is DERIVED from the state rather than tracked
      separately, so the boolean and the discriminator cannot drift apart.
    """
    return {
        'store_resolution': store.resolution,
        'store_path': str(store.path) if store.path is not None else None,
        'findings_store_state': store.state,
        'unresolved_store': store.state in UNREACHED_STORE_STATES,
    }


def store_unreached(store: FindingsStore) -> bool:
    """Return whether ``store`` is in a state on which every surface must refuse."""
    return store.state in UNREACHED_STORE_STATES


def unresolved_store_error(plan_id: str, store: FindingsStore) -> dict[str, Any]:
    """Build the canonical refusal payload for a store that was never reached.

    Returned verbatim by every operation surface — read, write and ``add_`` alike
    — so one unreached store produces one error shape regardless of which verb
    met it. ``add_qgate_finding``'s four-valued status contract is untouched by
    this: ``error`` is already excluded from ``QGATE_PERSIST_OK``, so a caller
    testing membership in that set treats a refused add as not-in-store with no
    change at the call site.
    """
    return {
        'status': 'error',
        'error': FINDINGS_STORE_UNRESOLVED,
        'plan_id': plan_id,
        'message': store.detail,
        **store_state_fields(store),
    }
