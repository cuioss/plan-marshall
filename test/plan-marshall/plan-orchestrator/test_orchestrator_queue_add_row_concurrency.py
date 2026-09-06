#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Concurrency proof for ``queue --add-row``, carried by a MATCHED PAIR.

The claim under test is not "the append works" but "the append is safe where
the form it replaces is not", and a single arm cannot establish that. So the two
controls run the same two-writer race, from the same starting queue, through the
same ``rmw_json`` critical section, under the same forced interleaving, and
differ in EXACTLY ONE dimension — which array each writer commits:

* **Positive control** — each writer commits the array it finds FRESH inside the
  lock, by calling the production :func:`_append_plan_row`. Both rows survive.
* **Negative control** — each writer commits an array it computed from its own
  PRE-LOCK read. One row is lost, because the value that decided the array was
  already stale by the time the lock was held.

**The interleaving is FORCED, not hoped for** (option (a) of the two the fix
considered: an in-process ``threading.Barrier`` pair, chosen because it needs no
production change — no test seam was added to ``orchestrator.py`` or
``_locks_core.py``). Every writer performs its pre-lock read, then blocks on one
:class:`threading.Barrier`; no writer may commit until EVERY writer has read.
That is what makes the negative arm's loss a property of the read-read-write-write
INTERLEAVING rather than of a single snapshot hoisted into the test body, and it
is what makes both arms deterministic instead of reporting whichever schedule
the OS happened to supply.

What each arm can actually detect, stated without overclaim:

* The **positive** arm goes RED if ``--add-row`` stops deriving its array from
  the fresh in-lock read — moving the append outside the critical section, or
  committing a pre-lock snapshot, loses a row under this interleaving.
* The **negative** arm goes RED if the barrier ever stops forcing the
  interleaving (a harness regression), because the writers would then serialize
  and both rows would survive. It is the arm that keeps the positive arm
  honest: it demonstrates that this interleaving IS lossy for a writer that
  commits a stale array, so the positive arm's green is a property of the write
  form and not of the race being too weak to lose anything.

Residual limitations, stated rather than omitted:

* The negative arm's unsafe writer is a TEST-LOCAL writer, not a production
  code path. It models the whole-array write form (compute from a pre-lock read,
  then assign) that ``manage-status update-field --field plans`` performs for
  ``decompose``'s bulk seed; it does not execute that script. A whole-array
  setter takes the caller's complete array and has no merge semantics to add, so
  "the bulk path is made safe" is not a change that could exist — the earlier
  claim that this arm would go red on it named an impossible event and has been
  removed.
* The pair establishes safety against THIS interleaving (every writer reads
  before any writer commits), which is the lost-update schedule the critical
  section exists to defeat. It does not enumerate every possible interleaving.

Each arm also asserts the writer population it ACTUALLY ran, so a degenerate
zero-writer run cannot pass green on an empty race. Accidental serialization is
ruled out by construction rather than by assertion: a serialized harness would
leave the first writer waiting at the barrier until it times out, and the
resulting :class:`threading.BrokenBarrierError` fails the test.
"""


from __future__ import annotations

import json
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from conftest import load_script_module

#: The orchestrator script's address, as module-level string constants so the
#: ``load_script_module`` call stays statically resolvable.
_ORCH_BUNDLE = 'plan-marshall'
_ORCH_SKILL = 'plan-orchestrator'
_ORCH_SCRIPT = 'orchestrator.py'

#: Loaded IN-PROCESS rather than driven through ``run_script``: the pair needs
#: to release both writers from one barrier at the read/commit boundary, and a
#: subprocess cannot be held there. Registered under its own name so it never
#: displaces the registration ``test_orchestrator.py`` publishes.
_orch = load_script_module(
    _ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, 'orchestrator_concurrency_script'
)

_append_plan_row = _orch._append_plan_row
_rmw_json = _orch.rmw_json

FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'

#: The number of writers each arm races. Both arms assert they actually ran this
#: many, so neither can report success over a race that never happened.
WRITER_COUNT = 2

#: Seconds a writer will wait at the barrier for its peers. Generous enough that
#: a loaded CI machine never trips it, and finite so a serialized harness fails
#: with ``BrokenBarrierError`` instead of hanging the suite.
BARRIER_TIMEOUT_SECONDS = 30

#: The ids the two racing writers each try to add. Distinct by construction: the
#: subject is a LOST UPDATE, not a duplicate-id collision, so the two writers
#: must never be competing for the same row.
RACED_PLAN_IDS = ('PLAN-02', 'PLAN-03')

#: The row already in the queue when each race starts. The positive control
#: asserts it comes through unmutated, which is what separates "both appends
#: landed" from "the whole array was rewritten and happened to keep three rows".
PRE_EXISTING_ID = 'PLAN-01'


def _make_plan(plan_id: str, status: str = 'staged') -> dict:
    """One queue row in the layout contract's shape."""
    return {
        'id': plan_id,
        'slug': plan_id.lower(),
        'workstream': 'WS-01',
        'status': status,
        'plan_marshall_plan_id': '',
        'pr': '',
        'landing': '',
    }


def _epic_dir(plan_context, slug: str) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / slug


def _write_status(plan_context, slug: str) -> Path:
    """Write the shared starting queue: one pre-existing row, nothing else."""
    doc = {
        'kind': 'orchestrator',
        'title': 'Concurrency Fixture Epic',
        'phase': 'orchestrating',
        'workstreams': ['WS-01'],
        'plans': [_make_plan(PRE_EXISTING_ID, status='running')],
        'resume_anchor': 'racing two writers',
        'metadata': {},
        'created': FIXED_TIMESTAMP,
        'updated': FIXED_TIMESTAMP,
    }
    path = _epic_dir(plan_context, slug) / 'status.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding='utf-8')
    return path


def _read_plans(path: Path) -> list[dict]:
    return list(json.loads(path.read_text(encoding='utf-8'))['plans'])


def _commit_stale_array(status_path: Path, stale: list[dict], row: dict) -> None:
    """The UNSAFE write form: commit an array decided by a PRE-LOCK read.

    Runs through the SAME ``rmw_json`` critical section the safe form uses, so
    the two arms are not separated by lock-vs-no-lock. What is unsafe is the
    VALUE: the mutator discards the fresh in-lock ``plans`` and assigns an array
    built from a read taken before the barrier released.
    """

    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        state['plans'] = [*stale, row]
        return state

    _rmw_json(status_path, _mutate)


def _race(
    status_path: Path, commit: Callable[[Path, list[dict], dict], None]
) -> list[str]:
    """Race :data:`WRITER_COUNT` writers with the read/commit boundary FORCED.

    Every writer takes its own pre-lock read, then blocks on the shared barrier
    until all its peers have read too; only then does any writer commit. The
    barrier is what turns "two writers happened to overlap" into the specific
    read-read-write-write interleaving both arms are judged under.

    Returns the plan id each writer committed, so a writer that never ran is
    visible as a missing entry rather than as a silently smaller race.
    """
    barrier = threading.Barrier(WRITER_COUNT)

    def _worker(index: int) -> str:
        row = _make_plan(RACED_PLAN_IDS[index])
        stale = _read_plans(status_path)
        barrier.wait(timeout=BARRIER_TIMEOUT_SECONDS)
        commit(status_path, stale, row)
        return row['id']

    with ThreadPoolExecutor(max_workers=WRITER_COUNT) as pool:
        return list(pool.map(_worker, range(WRITER_COUNT)))


@pytest.mark.xdist_group(name="orchestrator_add_row_contention")
class TestAddRowSharesTheCriticalSection:
    def test_concurrent_appends_both_survive(self, plan_context):
        """Positive control: both barrier-released ``--add-row`` writers land.

        Each writer reaches the lock holding a stale pre-lock read — the same
        input the negative arm loses on — and both rows still survive, because
        :func:`_append_plan_row` derives its array from the FRESH in-lock
        ``plans[]`` and ignores the stale one.
        """
        slug = 'race-add-row-epic'
        status_path = _write_status(plan_context, slug)

        def _safe_commit(_path: Path, _stale: list[dict], row: dict) -> None:
            _append_plan_row(slug, row)

        committed = _race(status_path, _safe_commit)

        # The population that actually ran — a zero-writer race cannot pass.
        assert len(committed) == WRITER_COUNT
        assert set(committed) == set(RACED_PLAN_IDS)

        plans = _read_plans(status_path)
        assert len(plans) == 1 + WRITER_COUNT
        assert {row['id'] for row in plans} == {PRE_EXISTING_ID, *RACED_PLAN_IDS}
        # The pre-existing row came through untouched — no writer rewrote the
        # array around it.
        assert _make_plan(PRE_EXISTING_ID, status='running') in plans

    def test_concurrent_stale_array_commits_lose_one(self, plan_context):
        """Negative control: committing a pre-lock array loses a write.

        The barrier holds every writer until all of them have read, so both
        commit an array that no longer reflects the queue — whichever commits
        second overwrites the other's row. Neither writer errors, which is
        exactly what makes the loss silent. Remove the barrier and this arm
        stops losing reliably; that is what it is here to detect.
        """
        slug = 'race-stale-array-epic'
        status_path = _write_status(plan_context, slug)

        committed = _race(status_path, _commit_stale_array)

        # Same population as the positive arm, and every writer completed.
        assert len(committed) == WRITER_COUNT
        assert set(committed) == set(RACED_PLAN_IDS)

        plans = _read_plans(status_path)
        # Grew by ONE, not by WRITER_COUNT: one row was silently dropped.
        assert len(plans) == 1 + 1
        surviving = {row['id'] for row in plans} & set(RACED_PLAN_IDS)
        assert len(surviving) == 1
