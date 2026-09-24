#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Concurrency proof for ``queue --add-row``, carried by a MATCHED PAIR.

The claim under test is not "the append works" but "the append is safe where
the form it replaces is not", and a single arm cannot establish that. So the two
controls run the same two-writer race, from the same starting queue, under the
same forced interleaving, and differ in the WRITE FORM each writer uses:

* **Positive control** — each writer stages its row through the production
  :func:`_append_plan_row`, which creates ONE row file in the per-concern
  layout. Both rows survive: the two writers write two different files.
* **Negative control** — each writer runs a TEST-LOCAL legacy whole-array writer
  against a monolithic-layout fixture: it commits a ``plans[]`` array computed
  from its own PRE-LOCK read, through the same ``rmw_json`` critical section.
  One row is lost, because the value that decided the array was already stale
  by the time the lock was held.

**The interleaving is FORCED, not hoped for.** An in-process
``threading.Barrier`` holds every writer after its pre-lock read; no writer may
commit until EVERY writer has read. That is what makes the negative arm's loss
a property of the read-read-write-write INTERLEAVING rather than of a single
snapshot hoisted into the test body, and it is what makes both arms
deterministic instead of reporting whichever schedule the OS happened to supply.

What each arm can actually detect, stated without overclaim:

* The **positive** arm goes RED if staging stops being a one-row-file create:
  if it rewrites another row file (the pre-existing row must stay
  byte-identical), drops a raced row, or hands the two raced rows colliding
  ``seq`` values. The barrier forces only the TEST'S OWN pre-lock read — the
  production writer discards that read and lists the queue itself inside its
  queue-scoped critical section after the barrier releases — so this arm does
  not model a writer that commits from a stale read; that shape is the
  negative arm's.
* The **negative** arm goes RED if the barrier ever stops forcing the
  interleaving (a harness regression), because the writers would then serialize
  and both rows would survive. It keeps the positive arm honest: it demonstrates
  that this interleaving IS lossy for a whole-array writer, so the positive arm's
  green is a property of the layout and write form, not of a race too weak to
  lose anything.

Residual limitations, stated rather than omitted:

* The negative arm's writer is TEST-LOCAL: it models the retired whole-document
  write form, and there is no longer a production code path that commits a
  whole queue array.
* The pair establishes safety against THIS interleaving (every writer reads
  before any writer commits), which is the lost-update schedule. It does not
  enumerate every possible interleaving.

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
from _ledger_fixtures import read_rows, write_ledger, write_legacy_status

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
_orch = load_script_module(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, 'orchestrator_concurrency_script')

#: The shared read-modify-write critical section the negative arm's legacy
#: writer commits through — the same primitive the retired whole-array form used.
_locks_core = load_script_module('plan-marshall', 'manage-locks', '_locks_core.py', '_locks_core_concurrency')

_append_plan_row = _orch._append_plan_row
_rmw_json = _locks_core.rmw_json

FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'

#: The ids the racing writers each try to add — the raced POPULATION, and the
#: single source of truth for how many writers there are. Distinct by
#: construction: the subject is a LOST UPDATE, not a duplicate-id collision.
RACED_PLAN_IDS = ('PLAN-02', 'PLAN-03')

#: The number of writers each arm races, DERIVED from the population above so a
#: third id raises the writer count with it.
WRITER_COUNT = len(RACED_PLAN_IDS)

#: Seconds a writer will wait at the barrier for its peers — finite, so a
#: serialized harness fails with ``BrokenBarrierError`` instead of hanging.
BARRIER_TIMEOUT_SECONDS = 30

#: The row already in the queue when each race starts. The positive control
#: asserts it comes through unmutated.
PRE_EXISTING_ID = 'PLAN-01'


def _make_plan(plan_id: str, status: str = 'staged') -> dict[str, str]:
    """One queue row in the layout contract's seed shape."""
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


def _starting_doc() -> dict[str, Any]:
    """The shared starting queue: one pre-existing row, nothing else."""
    return {
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


def _read_legacy_plans(path: Path) -> list[dict]:
    return list(json.loads(path.read_text(encoding='utf-8'))['plans'])


def _commit_stale_array(status_path: Path, stale: list[dict], row: dict) -> None:
    """The retired UNSAFE write form: commit an array decided by a PRE-LOCK read.

    Test-local. Runs through the ``rmw_json`` critical section, so the arm is not
    lock-vs-no-lock: what is unsafe is the VALUE — the mutator discards the fresh
    in-lock ``plans`` and assigns an array built from a read taken before the
    barrier released, restamping ``updated`` as every whole-document write did.
    """

    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        state['plans'] = [*stale, row]
        state['updated'] = FIXED_TIMESTAMP
        return state

    _rmw_json(status_path, _mutate)


def _race(read: Callable[[], list[dict]], commit: Callable[[list[dict], dict], None]) -> list[str]:
    """Race :data:`WRITER_COUNT` writers with the read/commit boundary FORCED.

    Every writer takes its own pre-lock read, then blocks on the shared barrier
    until all its peers have read too; only then does any writer commit.

    Returns the plan id each writer committed, so a writer that never ran is
    visible as a missing entry rather than as a silently smaller race.
    """
    barrier = threading.Barrier(WRITER_COUNT)

    def _worker(index: int) -> str:
        row = _make_plan(RACED_PLAN_IDS[index])
        stale = read()
        barrier.wait(timeout=BARRIER_TIMEOUT_SECONDS)
        commit(stale, row)
        return row['id']

    with ThreadPoolExecutor(max_workers=WRITER_COUNT) as pool:
        return list(pool.map(_worker, range(WRITER_COUNT)))


@pytest.mark.xdist_group(name='orchestrator_add_row_contention')
class TestAddRowIsAOneFileCreate:
    def test_concurrent_appends_both_survive(self, plan_context):
        """Positive control: both barrier-released ``--add-row`` writers land.

        The barrier forces only the test's own pre-lock read; ``_safe_commit``
        discards it, and ``_append_plan_row`` reads the queue itself after the
        barrier releases. What this arm detects is the write form: the
        pre-existing row file must stay byte-identical (no other row is
        rewritten), both raced rows must land (none is dropped), and the two
        must carry distinct ``seq`` values (no collision).
        """
        slug = 'race-add-row-epic'
        root = _epic_dir(plan_context, slug)
        write_ledger(root, _starting_doc())
        pre_existing_before = (root / 'queue' / f'{PRE_EXISTING_ID}.json').read_bytes()

        def _safe_commit(_stale: list[dict], row: dict) -> None:
            outcome = _append_plan_row(slug, row)
            assert 'row' in outcome, f'the staging of {row["id"]} was refused: {outcome}'

        committed = _race(lambda: read_rows(root), _safe_commit)

        # The population that actually ran — a zero-writer race cannot pass.
        assert len(committed) == WRITER_COUNT
        assert set(committed) == set(RACED_PLAN_IDS)

        rows = read_rows(root)
        assert len(rows) == 1 + WRITER_COUNT
        assert {row['id'] for row in rows} == {PRE_EXISTING_ID, *RACED_PLAN_IDS}
        # The pre-existing row file came through byte-identical — no writer
        # rewrote the queue around it.
        assert (root / 'queue' / f'{PRE_EXISTING_ID}.json').read_bytes() == pre_existing_before
        # The two raced rows were serialized by the queue-scoped critical
        # section, so they carry distinct ``seq`` values after the seeded row's.
        assert sorted(row['seq'] for row in rows if row['id'] in RACED_PLAN_IDS) == [2, 3]

    def test_concurrent_stale_array_commits_lose_one(self, plan_context):
        """Negative control: the legacy whole-array writer loses a write.

        The barrier holds every writer until all of them have read, so both
        commit an array that no longer reflects the queue — whichever commits
        second overwrites the other's row. Neither writer errors, which is
        exactly what makes the loss silent. Remove the barrier and this arm
        stops losing reliably; that is what it is here to detect.
        """
        slug = 'race-stale-array-epic'
        status_path = write_legacy_status(_epic_dir(plan_context, slug), _starting_doc())

        committed = _race(
            lambda: _read_legacy_plans(status_path),
            lambda stale, row: _commit_stale_array(status_path, stale, row),
        )

        # Same population as the positive arm, and every writer completed.
        assert len(committed) == WRITER_COUNT
        assert set(committed) == set(RACED_PLAN_IDS)

        plans = _read_legacy_plans(status_path)
        # Grew by ONE, not by WRITER_COUNT: one row was silently dropped.
        assert len(plans) == 1 + 1
        surviving = {row['id'] for row in plans} & set(RACED_PLAN_IDS)
        assert len(surviving) == 1
