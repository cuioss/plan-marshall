#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Build-queue concurrency limiter — the bounded-``k``-slot admitter with a FIFO
waiting queue.

Notation: ``plan-marshall:manage-locks:build_queue``

This standalone script is the **single shared reader/writer of the one
machine-global slot file** (``build-queue.json``): it caps how many build
sessions run concurrently across the whole host, and it is the ONE slot substrate
consumed by BOTH build-execute paths — marshalld's scheduler on the registered
path (the daemon coordinates access to the same file for builds it serves) AND
the in-process fallback (``_build_queue_slot``) on the unregistered / daemon-down
path. There is no separate project-level queue: one file, one slot budget, one
path per build, never stacked. The byte-identical-unregistered guarantee holds
*through* this shared file — an unregistered project still hits no daemon or
socket, yet its build acquires a slot against the same global file exactly as
before.

It persists ``active`` + ``waiting`` + ``run_log`` state in the machine-global
``build-queue.json`` (under ``home_root()``, ADR-008) and mutates it through the
shared TOCTOU-safe read-modify-write core (:func:`_locks_core.rmw_json`) — the
single serialization point over the shared file — so two sessions racing to
claim or free a slot can never both observe the same pre-state and both admit. It
is modeled on ``merge_lock.py`` (the ``k=1`` merge mutex); the build queue is the
``k>=1`` primitive that needs the FIFO waiting queue.

Every entry that enters the ``active`` set records an ``active_since`` activation
timestamp (distinct from ``ts``, the informational admit/enqueue time), set on a
first-acquire admit, an idempotent-waiting promotion, and a release
FIFO-promote. The self-healing reaper :func:`validate_lock_queue` runs implicitly
at the start of EVERY acquire and release — inside the SAME ``rmw_json``
mutation — and reaps any active entry whose age (``now - active_since``) exceeds
``2 × build_queue_upper_limit`` (the adaptive, monotonic-up, clamped ``[600 s,
3600 s]`` threshold tracked in the main-anchored ``run-configuration.json``),
freeing the slot, FIFO-promoting waiters, and emitting a WARN ``[LOCK]``
``reaped-stale`` event. This complements the dead-holder prune
(:func:`_prune_dead_active`): the prune clears a holder whose plan dir is GONE,
the reaper clears a hard-killed (``SIGKILL``-past-``finally``) holder whose plan
dir still exists.

It exposes two actions:

  * ``acquire`` — resolve the admission for ``--plan-id`` **idempotently** under
    the serialized read-modify-write: first run the implicit
    :func:`validate_lock_queue` reaper, then prune any dead active holders (their
    plan dir lives in NEITHER the main checkout NOR the holder's worktree — the
    shared :func:`_locks_core.holder_is_dead` predicate), then — if the plan
    already holds an ``active`` slot OR already has a ``waiting`` entry — REUSE
    that existing id without creating a duplicate (the waiting entry KEEPS its
    FIFO position, and is promoted to ``active`` only when a freed slot makes it
    eligible). Only a plan with no existing entry gets a fresh id
    ``{plan_id}:{uuid4}`` and is appended to ``active`` (stamped ``active_since``)
    → ``admission: admitted`` (slot free) or to the back of ``waiting`` →
    ``admission: blocked`` (at capacity). The script does NOT loop or wait — the
    wait+retry loop is the build wrapper's responsibility (D6); because re-polling
    ``acquire`` is idempotent, the wrapper re-polls WITHOUT releasing first, so a
    ``blocked`` plan retains its FIFO place rather than being shuffled to the
    back. A ``blocked`` admission is a structured signal the caller re-polls
    against, not an error.
  * ``release`` — first run the implicit :func:`validate_lock_queue` reaper, then
    remove ``--id`` from ``active`` (and defensively from ``waiting``),
    FIFO-promote the front waiting entry (the first list element — serialized
    append order) into the freed slot
    when capacity allows (stamping the promoted entry's ``active_since``), and —
    only on a real release — append an id+timestamp entry to the ``run_log``,
    pruning it to the most recent 100 entries so ``build-queue.json`` stays
    bounded. After the commit it recomputes the adaptive
    ``build_queue_upper_limit`` from the released entry's held duration
    (``now - active_since``), persisting ``max(current, held)`` clamped to
    ``[600 s, 3600 s]`` so the reap threshold tracks the longest observed real
    build without ever exceeding a 1 h ceiling.

**Machine-global resolution — the host-wide home-root tier:** the queue file
resolves under the machine-global home root (:func:`marketplace_paths.home_root`,
``~/.plan-marshall/build-queue.json`` by default, overridable via
``PLAN_MARSHALL_HOME``) regardless of the caller's cwd, because build-session
coordination spans EVERY checkout on the host, not just one repository: sessions
in different repos must all contend for the one shared queue. This is distinct
from the per-repo main-anchored exception (``merge.lock``,
``run-configuration.json``, ``lessons-learned``, ``merge-queue.json``,
``orchestrator``) that ``merge_lock`` still uses — build-queue.json is NOT a
member of that per-repo bounded set; it belongs to the machine-global tier.
Because the queue records holders from multiple checkouts, each active/waiting
entry is stamped at acquire with ``project_root = str(main_checkout_root())`` so
its liveness is later judged against the checkout it originated in.

**The cap is machine-global too.** ``max_slots`` is resolved through
:func:`_machine_config.resolve_max_slots`, reading the machine-global
``machine-config.json`` — NOT the calling repository's ``marshal.json``. A
per-caller cap over a shared queue is a cap two callers can disagree on while
contending for the same slots, and the shared resolver is cwd-independent, so a
process that has moved its working directory can no longer degrade silently to
the default. Every ``acquire`` / ``release`` result therefore reports
``max_slots_source`` beside ``max_slots`` (plus ``max_slots_detail`` when that
source is not ``machine_config``), because the value alone cannot distinguish a
configured 5 from a fallback 5.

**A surviving per-repo cap key is reported, never honoured.** ``acquire`` reads
the CALLER's own ``marshal.json`` — via the cwd-relative
:func:`file_ops.get_marshal_path`, which is the correct resolver here precisely
because the question is about the caller's repository — for the SOLE purpose of
detecting a demoted ``build.queue.max_slots``. The value never reaches the
admitted cap. When the key is present the result carries
``per_repo_max_slots: {value, in_effect: false}`` and one
``per_repo_max_slots_not_in_effect`` warning, so a repository that still
configures the old key learns that it does nothing on every queued build rather
than silently believing a cap it does not have. The result ALWAYS carries a
``warnings`` list — empty when nothing applies — so a consumer iterates it
unconditionally and never has to branch on whether the key is there; an
optional-key shape is what makes a consumer forget to look.

**Cap disagreement is reported, never reconciled.** Because the cap is resolved
per process while the queue is shared host-wide, two sessions can still admit
against different caps — a daemon started before a ``config set``, or a caller
whose machine-global file became unreadable. Every new entry is therefore stamped
at admission with ``admitted_under_max_slots``, the cap it was actually admitted
under, and a promotion carries that original stamp forward unchanged (the entry
dict moves between ``waiting`` and ``active``; the stamp is never rewritten).
``acquire`` compares its own resolved cap against the stamps of every
pre-existing active and waiting entry and reports the verdict as
``cap_agreement``: ``disagree`` when any stamped entry was admitted under a
different cap, otherwise ``unknown`` when at least one entry carries no usable
stamp, otherwise ``agree``. ``disagree`` outranks ``unknown`` because a proven
disagreement is not made less true by a second entry that could not be compared.

The verdict always rides with its population, so an ``agree`` can never be read
off a comparison that never happened: ``cap_compared_count`` is how many entries
were examined — the population itself, ``0`` for an empty queue — and
``cap_unstamped_count`` how many of those could not be compared, with the
remainder being the entries actually compared. An entry with no stamp, or one
whose stamp is not a positive ``int``, counts as unstamped and is NEVER counted
as agreement (ADR-009 and
``manage-locks/standards/scope-limited-negative-is-unknown.md``: a scope-limited
negative is ``unknown``, not a clean negative). ``cap_disagreement[]`` names each
disagreeing holder (``id``, ``plan_id``, ``project_root``,
``admitted_under_max_slots``) so the report identifies the projects involved and
not merely that a conflict exists.

**Reporting is the whole of it.** Admission logic is unchanged: the admitting
caller applies ITS OWN cap, existing stamps are left exactly as they were
admitted, and neither value is picked as authoritative — reconciling the two is
deliberately out of scope, because choosing a winner is what a per-caller cap
over a shared queue cannot do correctly. The comparison and the stamp both happen
inside the SAME serialized ``rmw_json`` mutation that admits, so the verdict
describes exactly the queue state the admission decided against, with no
check-then-act window between observing the disagreement and admitting.

**Concurrency correctness (TOCTOU / check-then-act):** the admit/release cycle is
a read-modify-write (read the queue → decide admit/promote → write the queue) —
a classic check-then-act window across concurrent build sessions. Every mutation
runs inside :func:`_locks_core.rmw_json`, which serializes the cycle with an
``O_EXCL`` guard-file mutex and commits via an atomic temp-file replace, so the
slot boundary is never over-admitted and a FIFO promote never double-promotes or
loses a waiting entry. The TOCTOU / check-then-act mitigation menu lives in
``ref-code-quality/standards/code-organization.md#toctou--check-then-act-hazards``
and is not duplicated here.

**FIFO ordering — list position is the single source of truth.** The ``waiting``
list order IS the arrival order: every enqueue/dequeue mutation runs inside the
serialized ``rmw_json`` critical section, so the list records plans in the exact
order their enqueues were serialized. Every FIFO decision — the reaper promote,
the idempotent re-poll promote-eligibility check, and the release promote —
therefore selects by list position via :func:`_fifo_front_n`. The admit-``ts``
field is **informational only** (it feeds the ``run_log`` audit tail): it is
sampled from the wall clock BEFORE the rmw section is entered, so under
concurrent enqueue it can disagree with the order the appends actually landed,
and a ``min(ts)`` selector could elect a different entry than the file's first —
splitting the queue's notion of "front". This mirrors the invariant its sibling
``merge_lock._fifo_front`` already encodes.

**Holder liveness via the shared core (no duplicate).** The plan-liveness
predicate is :func:`_locks_core.holder_is_dead`, imported from the shared
coordination core, NOT re-implemented here — a holder is dead when its plan dir
lives in NEITHER the checkout NOR the worktree of the project that recorded it.
Because the queue is machine-global, the prune passes each entry's stamped
``project_root`` so a foreign project's live holder is judged against its OWN
checkout and never reclaimed by a session in a different repo. The plan_id is
recovered from the admission id (everything before the trailing ``:{uuid4}``), so
a crashed session whose plan dir is gone has its active slot reclaimed under
contention without ever evicting a live slot holder.

**[LOCK] observability (best-effort, OUTSIDE the atomic window).** Each build-queue
lifecycle outcome emits a ``[LOCK]`` event through the shared
:func:`_locks_core.log_lock_event` helper into the SINGLE main-anchored global
lock-event log — always AFTER ``rmw_json`` commits, NEVER from inside the
``_mutate`` callback (which ``rmw_json``'s docstring forbids from doing its own
I/O). ``acquire`` emits ``acquired`` on an ``admitted`` outcome and ``blocked``
on a ``blocked`` outcome (carrying ``active_count`` / ``waiting_count``; the
waiter on a block is this ``plan_id``); ``release`` emits ``released`` on a real
release and ALSO ``acquired`` for a FIFO-promoted waiter (its slot was just
granted, so the promotion is recorded in the same timeline). BOTH actions emit a
WARN-level ``reaped-stale`` event (carrying ``held`` and ``threshold``) for each
over-age active entry the implicit :func:`validate_lock_queue` reaper reclaimed.
A no-op release emits nothing. ``acquire`` additionally emits ONE WARN-level
``cap-disagreement`` event — one per acquire, not one per disagreeing holder —
whenever ``cap_agreement`` is ``disagree``, carrying the caller's cap and source
and the disagreeing holders. The ``lock_id`` is the admission id
``{plan_id}:{uuid4}``. A
logging failure is swallowed and cannot affect admission/release.
"""

from __future__ import annotations

import time
import uuid
from argparse import Namespace
from pathlib import Path
from typing import Any

from _locks_core import holder_is_dead, log_lock_event, rmw_json
from _machine_config import (
    SOURCE_MACHINE_CONFIG,
    CapResolution,
    per_repo_max_slots_warning,
    read_per_repo_max_slots,
    resolve_max_slots,
)
from file_ops import get_marshal_path
from marketplace_paths import (
    ensure_home_root,
    main_checkout_root,
)
from run_config import (
    _read_build_queue_upper_limit,
    _write_build_queue_upper_limit,
)
from triage_helpers import (
    ErrorCode,
    create_workflow_cli,
    make_error,
    print_toon,
    safe_main,
)

_QUEUE_FILENAME = 'build-queue.json'

STAMP_ADMITTED_UNDER_MAX_SLOTS = 'admitted_under_max_slots'
"""Entry field recording the cap an entry was ACTUALLY admitted under.

Written once, at admission, and never rewritten — a promotion moves the entry
dict from ``waiting`` to ``active`` and carries the original stamp with it. The
stamp is what makes a cap disagreement observable at all: without it, two
sessions admitting against different caps leave a queue whose entries are
indistinguishable from entries admitted under one agreed cap.
"""

CAP_AGREEMENT_AGREE = 'agree'
"""Every pre-existing entry carries a stamp equal to the caller's resolved cap."""

CAP_AGREEMENT_DISAGREE = 'disagree'
"""At least one pre-existing entry was admitted under a different cap."""

CAP_AGREEMENT_UNKNOWN = 'unknown'
"""Nothing disagreed, but at least one entry could not be compared at all.

Distinct from :data:`CAP_AGREEMENT_AGREE` on purpose: an entry with no usable
stamp is a comparison that did not happen, and reporting it as agreement is the
scope-limited-negative-as-clean-negative error ADR-009 forbids.
"""

WARNING_CAP_DISAGREEMENT = 'cap_disagreement'
"""Warning ``code`` for a detected, unreconciled cap disagreement.

The code — not the message text — is what consumers deduplicate on, mirroring
:data:`_machine_config.WARNING_PER_REPO_MAX_SLOTS_NOT_IN_EFFECT`.
"""


# ---------------------------------------------------------------------------
# Main-anchored resolution + config
# ---------------------------------------------------------------------------


def _resolve_queue_path() -> Path:
    """Resolve the build-queue path under the machine-global home root.

    The build queue coordinates build sessions across EVERY checkout on the host,
    so it lives under the machine-global home-root tier
    (:func:`marketplace_paths.home_root`) — ``~/.plan-marshall/build-queue.json``
    by default, overridable via ``PLAN_MARSHALL_HOME`` — NOT a per-repo
    main-anchored path. It is host-wide and does not depend on git resolution.

    Routes through :func:`marketplace_paths.ensure_home_root` so the home root
    is created ``0o700`` on first touch — a mode-less parent ``mkdir`` would
    leave machine-global queue state world-listable.
    """
    return ensure_home_root() / _QUEUE_FILENAME


def _cap_fields(cap: CapResolution) -> dict[str, Any]:
    """Return the cap-reporting fields every admission/release result carries.

    ``max_slots_source`` is reported unconditionally, because the cap VALUE
    alone cannot distinguish a configured 5 from a fallback 5 — a consumer that
    needs to know whether the cap was actually configured reads the source.
    ``max_slots_detail`` rides along only when the source is not
    :data:`_machine_config.SOURCE_MACHINE_CONFIG`, since a nominal resolution
    has nothing to explain.

    Args:
        cap: The resolution returned by
            :func:`_machine_config.resolve_max_slots`.

    Returns:
        The result fields to merge into an ``acquire`` / ``release`` payload.
    """
    fields: dict[str, Any] = {'max_slots': cap.value, 'max_slots_source': cap.source}
    if cap.source != SOURCE_MACHINE_CONFIG:
        fields['max_slots_detail'] = cap.detail
    return fields


def _demotion_fields(cap: CapResolution) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Return the demoted-per-repo-key report fields for an ``acquire`` result.

    Reads the CALLER's own ``marshal.json`` — :func:`file_ops.get_marshal_path`
    is cwd-relative, which is right here because the question being asked IS
    "does the repository this build is running in still configure the old key?".
    That is the opposite of the cap resolution itself, which must be
    cwd-independent; the two resolvers are deliberately different because they
    answer different questions.

    The value read here NEVER influences the admitted cap. It is reported so an
    operator learns their key is inert, and reported on every queued build
    because a once-off notice is one an operator who inherited the repository
    never saw.

    Args:
        cap: The machine-global resolution actually in effect, named in the
            warning so the operator sees what replaced their key.

    Returns:
        ``(fields, warnings)`` — ``fields`` is empty when no per-repo key is
        present, else ``{'per_repo_max_slots': {'value', 'in_effect': False}}``;
        ``warnings`` holds the one not-in-effect warning, or is empty.

        The warnings are returned SEPARATELY rather than as a ``warnings`` key
        because the result's ``warnings`` list now has two independent producers
        (this demotion report and the cap-disagreement report), and a helper that
        owned the key would silently win or lose against the other on a dict
        merge. The always-present-``warnings`` invariant is a property of the
        RESULT payload, assembled by :func:`run_acquire`, not of this helper.
    """
    marshal_path = get_marshal_path()
    raw = read_per_repo_max_slots(marshal_path)
    if raw is None:
        return {}, []
    return (
        {'per_repo_max_slots': {'value': raw, 'in_effect': False}},
        [per_repo_max_slots_warning(marshal_path, raw, cap)],
    )


def _stamped_cap(entry: dict[str, Any]) -> int | None:
    """Return an entry's usable ``admitted_under_max_slots`` stamp, else ``None``.

    A stamp is usable only when it is a positive ``int`` — the same shape the cap
    resolver guarantees. A ``bool`` is rejected despite being an ``int`` subclass,
    so a ``true`` written into the queue file never reads as a cap of 1.

    ``None`` means "this entry cannot be compared", which the classifier counts
    toward :data:`CAP_AGREEMENT_UNKNOWN`. It deliberately does NOT mean "this
    entry agrees": an absent or malformed stamp is a missing measurement, and
    treating a missing measurement as a match is what would let a real
    disagreement report as ``agree``.
    """
    raw = entry.get(STAMP_ADMITTED_UNDER_MAX_SLOTS)
    if isinstance(raw, bool) or not isinstance(raw, int) or raw <= 0:
        return None
    return raw


def _classify_cap_agreement(
    caller_cap: int,
    active: list[dict[str, Any]],
    waiting: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare ``caller_cap`` against every pre-existing entry's admission stamp.

    A pure computation over the passed-in lists — it performs NO file I/O,
    because it runs inside the ``rmw_json`` ``_mutate`` callback, whose contract
    forbids that. Called AFTER the reaper and the dead-holder prune, so a reaped
    or pruned entry's stamp never contributes a disagreement nobody can act on,
    and BEFORE the caller's own entry is appended, so an empty queue reports a
    population of ``0`` rather than counting the entry this very call is about to
    create.

    Args:
        caller_cap: The cap THIS caller resolved and will admit against.
        active: The post-reap, post-prune active entries.
        waiting: The waiting entries.

    Returns:
        The four result fields: ``cap_agreement`` (see the three
        ``CAP_AGREEMENT_*`` constants), ``cap_compared_count`` — the examined
        POPULATION, so that a verdict is never separable from the number of
        entries behind it — ``cap_unstamped_count`` (how many of that population
        could not be compared), and ``cap_disagreement`` (one row per disagreeing
        holder). The entries actually compared are the population minus the
        unstamped ones; publishing the population is what makes an ``agree`` over
        an empty queue visible as such instead of reading like a clean bill of
        health.
    """
    entries = [*active, *waiting]
    unstamped = 0
    disagreeing: list[dict[str, Any]] = []
    for entry in entries:
        stamp = _stamped_cap(entry)
        if stamp is None:
            unstamped += 1
            continue
        if stamp != caller_cap:
            disagreeing.append(
                {
                    'id': entry['id'],
                    'plan_id': entry.get('plan_id'),
                    'project_root': entry.get('project_root'),
                    STAMP_ADMITTED_UNDER_MAX_SLOTS: stamp,
                }
            )

    if disagreeing:
        agreement = CAP_AGREEMENT_DISAGREE
    elif unstamped:
        agreement = CAP_AGREEMENT_UNKNOWN
    else:
        agreement = CAP_AGREEMENT_AGREE

    return {
        'cap_agreement': agreement,
        'cap_compared_count': len(entries),
        'cap_unstamped_count': unstamped,
        'cap_disagreement': disagreeing,
    }


def _cap_disagreement_warning(cap: CapResolution, rows: list[dict[str, Any]]) -> dict[str, str]:
    """Build the ``cap_disagreement`` warning naming both caps and the holders.

    The message states the cap this build admits against (with its source, since
    the value alone cannot distinguish a configured 5 from a fallback 5), the cap
    each conflicting holder was admitted under, and which project that holder
    came from — a warning naming only "the caps disagree" leaves the operator
    with no way to find the other side of the conflict.

    It also states that nothing was reconciled, because that is the deliverable's
    contract rather than an implementation detail: the admitting caller applies
    its own cap and no value is treated as authoritative. No remedy command is
    offered, for the same reason — a per-caller cap over a shared queue has no
    single correct winner, so there is no one-step fix to name.

    Args:
        cap: The caller's own machine-global resolution, in effect for THIS admit.
        rows: The ``cap_disagreement`` rows from :func:`_classify_cap_agreement`
            (non-empty; the caller only builds this warning on ``disagree``).

    Returns:
        ``{'code': ..., 'message': ...}`` — ``code`` is
        :data:`WARNING_CAP_DISAGREEMENT`, the stable identity consumers
        deduplicate on.
    """
    holders = '; '.join(
        f'{row["id"]} (project={row["project_root"] or "unrecorded"}) '
        f'admitted under max_slots={row[STAMP_ADMITTED_UNDER_MAX_SLOTS]}'
        for row in rows
    )
    entries = 'entry' if len(rows) == 1 else 'entries'
    return {
        'code': WARNING_CAP_DISAGREEMENT,
        'message': (
            f'This build admits against max_slots={cap.value} '
            f'(source={cap.source}, path={cap.path}), but the machine-global build queue '
            f'already holds {len(rows)} {entries} admitted under a different cap: {holders}. '
            f'The disagreement is reported, never reconciled: this caller applies its own cap, '
            f'the existing stamps are left exactly as they were admitted, and neither value is '
            f'treated as authoritative.'
        ),
    }


# ---------------------------------------------------------------------------
# State shape helpers
# ---------------------------------------------------------------------------


def _entry_list(state: dict[str, Any], key: str) -> list[dict[str, Any]]:
    """Return ``state[key]`` as a list of entry dicts, treating junk as empty.

    A corrupt or absent ``active`` / ``waiting`` / ``run_log`` value (missing,
    non-list, or holding non-dict elements) degrades to an empty list so a
    malformed file is rebuilt from scratch rather than crashing the mutator.
    """
    raw = state.get(key)
    if not isinstance(raw, list):
        return []
    return [e for e in raw if isinstance(e, dict) and isinstance(e.get('id'), str)]


def _plan_id_of(entry_id: str) -> str:
    """Recover the holder ``plan_id`` from an admission id ``{plan_id}:{uuid4}``.

    The id is composed as ``{plan_id}:{uuid4}`` and a plan_id may itself contain
    colons, so the plan_id is everything BEFORE the final colon. An id with no
    colon (malformed) yields an empty plan_id, which :func:`holder_is_dead`
    treats as dead — so a malformed active entry is reclaimable.
    """
    head, sep, _tail = entry_id.rpartition(':')
    return head if sep else ''


def _fifo_front_n(waiting: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    """Return the ``n`` FIFO-front entries (first by serialized arrival order).

    The ``waiting`` list order IS the arrival order: every enqueue/dequeue mutation
    runs inside the serialized :func:`_locks_core.rmw_json` critical section, so the
    list records plans in the exact order their enqueues were serialized. The first
    ``n`` list entries are therefore the ``n`` longest-waiting plans and the only
    promotion-eligible ones. List position — NOT the informational admit-``ts``
    field — is the single ordering key: ``ts`` is sampled per call from the wall
    clock BEFORE the rmw section is entered, and under concurrent enqueue it can
    disagree with serialization order (a ``ts`` sampled before the rmw section does
    not reflect when the append actually landed), so selecting the front by
    ``min(ts)`` could pick a different entry than the file's first and split the
    queue's notion of "front". Using list position keeps one source of truth for
    arrival order, mirroring :func:`merge_lock._fifo_front`.

    A non-positive ``n`` yields the empty list, so a caller at capacity (``free``
    computed as zero or negative) promotes nothing.
    """
    if n <= 0:
        return []
    return waiting[:n]


def _prune_dead_active(active: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop active entries whose holder plan is dead (crashed session reclaim).

    A holder is dead when its plan dir lives in NEITHER the checkout NOR the
    worktree of the project that recorded it. Because the queue is machine-global
    (shared across every checkout), each entry's liveness is judged against the
    project it originated in — its stamped ``project_root`` — via
    ``holder_is_dead(plan_id, project_root=e.get('project_root'))``, so a FOREIGN
    project's live holder is never reclaimed by a session in a different checkout.
    A legacy entry lacking ``project_root`` falls back to caller-anchored
    resolution (``project_root=None``), which is harmless under the breaking
    clean-start. Reclaiming dead active slots before the capacity check frees
    slots wedged by a crashed build session without ever evicting a LIVE holder.
    """
    # SHIM(B): machine-global queue entry lacking project_root, written before acquire stamped it.
    # shim-owner: manage-locks
    # shim-floor: the machine-global-queue change that had acquire stamp each entry's originating project_root (in-code anchor: the "breaking clean-start" this docstring names)
    # shim-remove-when: no live queue entry lacks project_root
    return [e for e in active if not holder_is_dead(_plan_id_of(e['id']), project_root=e.get('project_root'))]


def validate_lock_queue(state: dict[str, Any], now: float, upper_limit: int, max_slots: int) -> list[dict[str, Any]]:
    """Reap over-age active entries and FIFO-promote waiters into freed slots.

    A pure mutation over the passed-in ``state`` (it does NO file I/O — it is
    called from inside an ``rmw_json`` ``_mutate`` callback, which the rmw
    contract forbids from performing its own I/O). It is the queue's positive,
    time-based self-healing reaper, complementing the dead-holder prune
    (:func:`_prune_dead_active`): a holder that was hard-killed (``SIGKILL`` past
    the Python ``finally``) leaves a *live-looking* active entry — its plan dir
    still exists — that the liveness prune never clears, so without a time-based
    reaper its slot starves the queue indefinitely.

    The reap threshold is ``2 × upper_limit`` (the ``2 ×`` safety factor over the
    already monotonic-up adaptive limit makes a false reap of a genuinely long
    build vanishingly unlikely). Age is measured from ``active_since`` — the
    wall-clock time the entry entered ``active`` — NOT from the informational
    admit/enqueue ``ts``: a promoted entry's ``ts`` is its
    original enqueue time, so measuring age from ``ts`` would over-age a recently
    promoted entry. An entry with NO ``active_since`` (written before this change
    shipped) is treated as ``now`` and is therefore never reaped on first contact.

    After reaping, waiting entries are FIFO-promoted by list position
    (:func:`_fifo_front_n` — serialized append order, never admit-``ts``)
    into the freed slots up to ``max_slots``, each stamped with a fresh
    ``active_since``. The function mutates ``state['active']`` / ``state['waiting']``
    in place and returns the list of reaped entries (each carrying its ``id`` and
    computed ``held`` duration) so the caller can emit a best-effort
    ``reaped-stale`` ``[LOCK]`` event AFTER the ``rmw_json`` commit.
    """
    threshold = 2 * upper_limit
    active = _entry_list(state, 'active')
    waiting = _entry_list(state, 'waiting')

    reaped: list[dict[str, Any]] = []
    survivors: list[dict[str, Any]] = []
    for entry in active:
        # SHIM(B): queue entry lacking active_since, written before that field shipped.
        # shim-owner: manage-locks
        # shim-floor: the change that added this time-based over-age reaper, which began stamping active_since when an entry enters active and measures age from it (not the enqueue ts)
        # shim-remove-when: no live queue entry lacks active_since
        active_since = entry.get('active_since', now)
        held = now - active_since
        if held > threshold:
            reaped.append({'id': entry['id'], 'held': held})
        else:
            survivors.append(entry)
    active = survivors

    # FIFO-promote the front waiting entries (by list position — serialized append
    # order) into the slots freed by the reap, stamping a fresh active_since on
    # each promoted entry.
    if waiting and len(active) < max_slots:
        free = max_slots - len(active)
        promotable = _fifo_front_n(waiting, free)
        promoted_ids = {e['id'] for e in promotable}
        for entry in promotable:
            entry['active_since'] = now
            active.append(entry)
        waiting = [e for e in waiting if e['id'] not in promoted_ids]

    state['active'] = active
    state['waiting'] = waiting
    return reaped


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def run_acquire(args: Namespace) -> dict[str, Any]:
    """Acquire a build slot for ``--plan-id`` (admit or enqueue), idempotently.

    Under the serialized read-modify-write, prunes dead active holders, then
    resolves the admission for ``plan_id`` **idempotently**:

    * If ``plan_id`` already holds an ``active`` slot, its existing id is returned
      with ``admission: admitted`` — no new entry, no slot double-claim.
    * If ``plan_id`` already has a ``waiting`` entry, that entry KEEPS its FIFO
      position (it is NOT re-appended to the back). When a slot has since freed up
      and the entry is now within the first ``max_slots - len(active)`` waiting
      entries **by list position** (serialized append order — never admit-``ts``),
      it is promoted to ``active`` → ``admission:
      admitted`` (reusing its existing id); otherwise it stays ``blocked`` with
      the same id.
    * Only when ``plan_id`` has NO existing entry is a fresh admission id
      ``{plan_id}:{uuid4}`` generated and admitted (slot free) or enqueued at the
      back of the FIFO waiting queue (at capacity).

    Idempotence is the FIFO-preservation guarantee: the build wrapper re-polls
    ``acquire`` while blocked WITHOUT releasing first, so a queued plan retains its
    place rather than being shuffled to the back on every poll. A ``blocked``
    result is a structured signal the wrapper re-polls against, not an error.

    Every result also reports the demoted per-repo cap key (see
    :func:`_demotion_fields`): a ``warnings`` list — always present, empty when
    nothing applies — plus ``per_repo_max_slots`` when the caller's
    ``marshal.json`` still carries the inert key. That read never influences the
    admitted cap, which comes solely from the machine-global resolver.

    Every result additionally reports the cap-disagreement verdict (see
    :func:`_classify_cap_agreement`): ``cap_agreement`` with its population
    (``cap_compared_count`` / ``cap_unstamped_count``) and ``cap_disagreement[]``,
    plus a second ``warnings`` entry and ONE WARN ``[LOCK]``
    ``cap-disagreement`` event on a ``disagree``. The verdict changes NOTHING
    about the admission: this caller's cap is applied, existing stamps are left
    untouched, and neither cap is picked as authoritative.
    """
    plan_id: str = args.plan_id
    queue_path = _resolve_queue_path()
    # Stamp this session's originating checkout so a foreign project's live holder
    # is judged against ITS checkout (machine-global queue). main_checkout_root()
    # raises when the caller is not in a git repo — a real error for a build.
    try:
        project_root = str(main_checkout_root())
    except RuntimeError as exc:
        return make_error(str(exc), code=ErrorCode.NOT_FOUND, plan_id=plan_id)

    cap = resolve_max_slots()
    max_slots = cap.value
    upper_limit = _read_build_queue_upper_limit()
    new_entry_id = f'{plan_id}:{uuid.uuid4()}'
    ts = time.time()
    outcome: dict[str, Any] = {'reaped': []}

    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        # Self-healing reaper FIRST (inside the SAME rmw_json mutation): reap any
        # over-age active entry and FIFO-promote waiters into the freed slots,
        # then run the existing prune/admit logic on the reaped state. Running it
        # here (not as a separate rmw call) keeps the reap + admit decision in one
        # serialized read-modify-write, so a reap can never race a concurrent admit.
        outcome['reaped'] = validate_lock_queue(state, ts, upper_limit, max_slots)

        active = _prune_dead_active(_entry_list(state, 'active'))
        waiting = _entry_list(state, 'waiting')
        run_log = _entry_list(state, 'run_log')

        # Cap-disagreement detection — after the reaper and the dead-holder prune
        # (so a reclaimed entry's stamp raises no conflict nobody can act on) and
        # BEFORE this caller's own entry is appended (so the reported population
        # is the queue this admission decided against, not one that includes
        # itself: an empty queue must report cap_compared_count 0). Inside the
        # same rmw_json mutation as the admit, so there is no window between
        # observing the disagreement and admitting. Pure computation — no I/O.
        outcome.update(_classify_cap_agreement(max_slots, active, waiting))

        # Idempotent fast-path: a plan already holding an active slot keeps it.
        existing_active = next((e for e in active if e.get('plan_id') == plan_id), None)
        if existing_active is not None:
            outcome['id'] = existing_active['id']
            outcome['admission'] = 'admitted'
            outcome['active_count'] = len(active)
            outcome['waiting_count'] = len(waiting)
            return {'active': active, 'waiting': waiting, 'run_log': run_log}

        # Idempotent re-poll: a plan already in the waiting queue keeps its FIFO
        # position. Promote it ONLY when a slot has freed up AND it is within the
        # available-slot prefix of the waiting queue by list position (serialized
        # append order) — never re-append to the back.
        existing_waiting = next((e for e in waiting if e.get('plan_id') == plan_id), None)
        if existing_waiting is not None:
            free = max_slots - len(active)
            promotable = _fifo_front_n(waiting, free)
            if any(e['id'] == existing_waiting['id'] for e in promotable):
                waiting = [e for e in waiting if e['id'] != existing_waiting['id']]
                existing_waiting['active_since'] = time.time()
                active.append(existing_waiting)
                outcome['admission'] = 'admitted'
            else:
                outcome['admission'] = 'blocked'
            outcome['id'] = existing_waiting['id']
            outcome['active_count'] = len(active)
            outcome['waiting_count'] = len(waiting)
            return {'active': active, 'waiting': waiting, 'run_log': run_log}

        # First acquire for this plan: admit when a slot is free, else enqueue at
        # the back of the FIFO waiting queue. An admitted entry records
        # active_since (the slot activation time used by the reaper); a queued
        # entry does not — it is not active yet. Every new entry is stamped with
        # project_root so the machine-global prune judges its liveness against the
        # checkout it originated in, and with admitted_under_max_slots — the cap
        # it was ACTUALLY admitted under — so a later caller resolving a different
        # cap can detect the disagreement. Both stamps are set before the
        # admit/enqueue branch, so a waiting entry carries them from the moment it
        # is queued and a promotion later moves this same dict unchanged.
        entry = {
            'id': new_entry_id,
            'plan_id': plan_id,
            'ts': ts,
            'project_root': project_root,
            STAMP_ADMITTED_UNDER_MAX_SLOTS: max_slots,
        }
        if len(active) < max_slots:
            entry['active_since'] = ts
            active.append(entry)
            outcome['admission'] = 'admitted'
        else:
            waiting.append(entry)
            outcome['admission'] = 'blocked'
        outcome['id'] = new_entry_id
        outcome['active_count'] = len(active)
        outcome['waiting_count'] = len(waiting)
        return {'active': active, 'waiting': waiting, 'run_log': run_log}

    rmw_json(queue_path, _mutate)

    # [LOCK] reaped-stale emission — best-effort, AFTER rmw_json commits (never
    # from inside _mutate). One WARN event per reaped over-age active entry.
    for reaped in outcome['reaped']:
        log_lock_event(
            'build',
            'reaped-stale',
            lock_id=reaped['id'],
            held=reaped['held'],
            threshold=2 * upper_limit,
        )

    # [LOCK] cap-disagreement emission — best-effort, AFTER rmw_json commits
    # (never from inside _mutate). ONE WARN event per acquire, not one per
    # disagreeing holder: the disagreement is a single property of this admission,
    # and the holders it involves ride along as a field.
    if outcome['cap_agreement'] == CAP_AGREEMENT_DISAGREE:
        log_lock_event(
            'build',
            'cap-disagreement',
            lock_id=outcome['id'],
            caller_max_slots=max_slots,
            caller_max_slots_source=cap.source,
            disagreeing_count=len(outcome['cap_disagreement']),
            compared_count=outcome['cap_compared_count'],
            unstamped_count=outcome['cap_unstamped_count'],
            disagreeing_holders='; '.join(
                f'{row["id"]}@{row[STAMP_ADMITTED_UNDER_MAX_SLOTS]}' for row in outcome['cap_disagreement']
            ),
        )

    # [LOCK] emission — best-effort, AFTER rmw_json commits (never from inside
    # _mutate). `admitted` → `acquired`; `blocked` → `blocked` (waiter is self).
    if outcome['admission'] == 'admitted':
        log_lock_event(
            'build',
            'acquired',
            lock_id=outcome['id'],
            active_count=outcome['active_count'],
            waiting_count=outcome['waiting_count'],
        )
    else:
        log_lock_event(
            'build',
            'blocked',
            lock_id=outcome['id'],
            waiter=plan_id,
            active_count=outcome['active_count'],
            waiting_count=outcome['waiting_count'],
        )

    # The result's `warnings` list has TWO producers — the demoted per-repo key
    # and the cap disagreement — so it is assembled here rather than owned by
    # either helper, and it is ALWAYS present (empty when nothing applies) so a
    # consumer iterates it unconditionally.
    demotion_fields, warnings = _demotion_fields(cap)
    if outcome['cap_agreement'] == CAP_AGREEMENT_DISAGREE:
        warnings.append(_cap_disagreement_warning(cap, outcome['cap_disagreement']))

    return {
        'status': 'success',
        'plan_id': plan_id,
        'id': outcome['id'],
        'admission': outcome['admission'],
        **_cap_fields(cap),
        **demotion_fields,
        'warnings': warnings,
        'cap_agreement': outcome['cap_agreement'],
        'cap_compared_count': outcome['cap_compared_count'],
        'cap_unstamped_count': outcome['cap_unstamped_count'],
        'cap_disagreement': outcome['cap_disagreement'],
        'active_count': outcome['active_count'],
        'waiting_count': outcome['waiting_count'],
        'queue_path': str(queue_path),
    }


def run_release(args: Namespace) -> dict[str, Any]:
    """Release the build slot held by ``--id`` and FIFO-promote the next waiter.

    Removes ``--id`` from ``active`` (and defensively from ``waiting``, so a
    release of a still-queued id is benign), then — when a slot is now free —
    FIFO-promotes the front waiting entry (the first list element — serialized
    append order, never admit-``ts``) into ``active`` and
    records it as the ``promoted`` id. On a real release (the id was actually
    present), appends an id+timestamp entry to the ``run_log`` and prunes it to
    the most recent 100 entries so ``build-queue.json`` stays bounded; a no-op
    release of an absent id leaves the ``run_log`` untouched. Releasing an id
    that is not present is an idempotent no-op success (``action: noop``) so a
    crashed-and-retried release does not error.
    """
    plan_id: str = args.plan_id
    target_id: str = args.id
    try:
        queue_path = _resolve_queue_path()
    except RuntimeError as exc:
        return make_error(str(exc), code=ErrorCode.NOT_FOUND, plan_id=plan_id)

    cap = resolve_max_slots()
    max_slots = cap.value
    upper_limit = _read_build_queue_upper_limit()
    now = time.time()
    outcome: dict[str, Any] = {'reaped': [], 'held': None}

    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        # Self-healing reaper FIRST (inside the SAME rmw_json mutation), then the
        # existing release/promote logic runs on the reaped state — one serialized
        # read-modify-write covering reap + release.
        outcome['reaped'] = validate_lock_queue(state, now, upper_limit, max_slots)

        active = _entry_list(state, 'active')
        waiting = _entry_list(state, 'waiting')
        run_log = _entry_list(state, 'run_log')

        # Capture the released entry's active_since so the caller can compute the
        # held duration for the adaptive-limit recompute (only meaningful when the
        # released id was a real active holder).
        released_entry = next((e for e in active if e['id'] == target_id), None)
        if released_entry is not None and 'active_since' in released_entry:
            outcome['held'] = now - released_entry['active_since']

        before = len(active) + len(waiting)
        active = [e for e in active if e['id'] != target_id]
        waiting = [e for e in waiting if e['id'] != target_id]
        removed = (len(active) + len(waiting)) < before
        outcome['action'] = 'released' if removed else 'noop'

        # FIFO-promote the front waiting entry (by list position — serialized
        # append order) when the release freed a slot. Each released slot promotes
        # exactly one distinct waiting entry — never two — so concurrent releases
        # (serialized by the rmw guard) cannot double-promote or lose a waiting
        # entry. The promoted entry is stamped with a fresh active_since (it is
        # only now active).
        promoted: str | None = None
        if waiting and len(active) < max_slots:
            front = _fifo_front_n(waiting, 1)[0]
            waiting = [e for e in waiting if e['id'] != front['id']]
            front['active_since'] = time.time()
            active.append(front)
            promoted = front['id']
        outcome['promoted'] = promoted

        # Append to the run_log ONLY on a real release (the id was actually
        # present in active/waiting), so a no-op release of an absent id does not
        # accrete a stale entry, then prune to the most recent 100 entries — the
        # log is a bounded audit tail, not an unbounded history, so build-queue.json
        # cannot grow without limit across a long-lived cluster.
        if removed:
            run_log.append({'id': target_id, 'plan_id': plan_id, 'ts': time.time()})
            run_log = run_log[-100:]
        outcome['active_count'] = len(active)
        outcome['waiting_count'] = len(waiting)
        return {'active': active, 'waiting': waiting, 'run_log': run_log}

    rmw_json(queue_path, _mutate)

    # Adaptive-limit recompute (clamped [600, 3600]) — OUTSIDE _mutate (it writes
    # a SEPARATE config file, not the queue file). The new limit tracks the
    # longest observed real build held-duration monotonically-up; persist only
    # when it would actually change. _write_build_queue_upper_limit clamps to
    # [600, 3600], so a single anomalously long held lock cannot ratchet the
    # stored limit past the 3600 s ceiling.
    held = outcome['held']
    if held is not None:
        new_limit = max(upper_limit, int(held))
        if new_limit != upper_limit:
            _write_build_queue_upper_limit(new_limit)

    # [LOCK] reaped-stale emission — best-effort, AFTER rmw_json commits (never
    # from inside _mutate). One WARN event per reaped over-age active entry.
    for reaped in outcome['reaped']:
        log_lock_event(
            'build',
            'reaped-stale',
            lock_id=reaped['id'],
            held=reaped['held'],
            threshold=2 * upper_limit,
        )

    # [LOCK] emission — best-effort, AFTER rmw_json commits (never from inside
    # _mutate). A real release emits `released`; a no-op release emits nothing.
    # A FIFO-promoted waiter additionally emits `acquired` (its slot was just
    # granted), recording the promotion in the same main-anchored timeline.
    if outcome['action'] == 'released':
        log_lock_event(
            'build',
            'released',
            lock_id=target_id,
            active_count=outcome['active_count'],
            waiting_count=outcome['waiting_count'],
        )
        if outcome['promoted'] is not None:
            log_lock_event(
                'build',
                'acquired',
                lock_id=outcome['promoted'],
                active_count=outcome['active_count'],
                waiting_count=outcome['waiting_count'],
            )

    return {
        'status': 'success',
        'plan_id': plan_id,
        'id': target_id,
        'action': outcome['action'],
        'promoted': outcome['promoted'],
        **_cap_fields(cap),
        'active_count': outcome['active_count'],
        'waiting_count': outcome['waiting_count'],
        'queue_path': str(queue_path),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    """Entry point — ``acquire`` / ``release`` actions."""
    parser = create_workflow_cli(
        description='Build-queue concurrency limiter: bounded-k-slot admitter with a FIFO waiting queue',
        epilog="""
Examples:
  build_queue.py acquire --plan-id EXAMPLE-PLAN
  build_queue.py release --plan-id EXAMPLE-PLAN --id EXAMPLE-PLAN:UUID
""",
        subcommands=[
            {
                'name': 'acquire',
                'help': 'Admit a build slot (or enqueue when at capacity)',
                'handler': run_acquire,
                'args': [
                    {
                        'flags': ['--plan-id'],
                        'dest': 'plan_id',
                        'required': True,
                        'help': 'Holder source — the plan_id acquiring a slot (mandatory)',
                    },
                ],
            },
            {
                'name': 'release',
                'help': 'Release a build slot and FIFO-promote the oldest waiting entry',
                'handler': run_release,
                'args': [
                    {
                        'flags': ['--plan-id'],
                        'dest': 'plan_id',
                        'required': True,
                        'help': 'Holder source — the plan_id releasing a slot (mandatory)',
                    },
                    {
                        'flags': ['--id'],
                        'dest': 'id',
                        'required': True,
                        'help': 'The admission id returned by acquire (mandatory)',
                    },
                ],
            },
        ],
    )
    args = parser.parse_args()
    return print_toon(args.func(args))


if __name__ == '__main__':
    safe_main(main)()
