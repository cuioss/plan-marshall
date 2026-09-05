#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Concurrency proof for ``queue --add-row``, carried by a MATCHED PAIR.

The claim under test is not "the append works" but "the append is safe where
the form it replaces is not", and a single arm cannot establish that. So the two
controls run the same two-writer race, against the same starting queue, under
the same harness, and differ ONLY in which write form the writers use:

* **Positive control** — two writers race ``queue --add-row`` for two DIFFERENT
  plan ids. Both rows survive, because each writer re-reads ``plans[]`` INSIDE
  the ``rmw_json`` critical section.
* **Negative control** — two writers race the bulk whole-array
  ``manage-status update-field --field plans`` rewrite, each computing its new
  array from the SAME pre-lock snapshot. One write is lost, because the read
  that decided the array happened outside the lock.

Neither arm can pass vacuously. The negative control goes RED if the bulk path
is ever made safe (it would then keep both rows), and the positive control goes
RED if ``--add-row`` is ever moved outside the critical section (it would then
lose one). Each arm also asserts the writer population it ACTUALLY ran, so a
degenerate zero-writer run — or a harness that serialized the writers by
accident — is visible as a failure rather than passing green on an empty race.
"""


from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from conftest import get_script_path, run_script

#: The two scripts' addresses, as module-level string constants so every
#: ``get_script_path`` call stays statically resolvable (never a star-unpacked
#: tuple).
_ORCH_BUNDLE = 'plan-marshall'
_ORCH_SKILL = 'plan-orchestrator'
_ORCH_SCRIPT = 'orchestrator.py'

_STATUS_BUNDLE = 'plan-marshall'
_STATUS_SKILL = 'manage-status'
_STATUS_SCRIPT = 'manage-status.py'

ORCH_SCRIPT_PATH = get_script_path(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT)
STATUS_SCRIPT_PATH = get_script_path(_STATUS_BUNDLE, _STATUS_SKILL, _STATUS_SCRIPT)

FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'

#: The number of writers each arm races. Both arms assert they actually ran this
#: many, so neither can report success over a race that never happened.
WRITER_COUNT = 2

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


def _race(worker) -> list:
    """Run :data:`WRITER_COUNT` writers concurrently, returning results in order."""
    with ThreadPoolExecutor(max_workers=WRITER_COUNT) as pool:
        return list(pool.map(worker, range(WRITER_COUNT)))


@pytest.mark.xdist_group(name="orchestrator_add_row_contention")
class TestAddRowSharesTheCriticalSection:
    def test_concurrent_appends_both_survive(self, plan_context):
        """Positive control: two racing ``--add-row`` writers both land a row.

        The append re-reads ``plans[]`` inside the critical section, so the
        second writer sees the first's committed row and appends after it.
        """
        slug = 'race-add-row-epic'
        status_path = _write_status(plan_context, slug)
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}

        def _append(index: int):
            plan_id = RACED_PLAN_IDS[index]
            return run_script(
                ORCH_SCRIPT_PATH,
                'queue',
                '--slug',
                slug,
                '--add-row',
                plan_id,
                '--slug-value',
                plan_id.lower(),
                '--workstream',
                'WS-01',
                env_overrides=env,
                timeout=30,
            )

        results = _race(_append)

        # The population that actually ran — a zero-writer race cannot pass.
        assert len(results) == WRITER_COUNT
        assert [r.returncode for r in results] == [0] * WRITER_COUNT
        assert all('operation: queue-add-row' in r.stdout for r in results)

        plans = _read_plans(status_path)
        assert len(plans) == 1 + WRITER_COUNT
        assert {row['id'] for row in plans} == {PRE_EXISTING_ID, *RACED_PLAN_IDS}
        # The pre-existing row came through untouched — no writer rewrote the
        # array around it.
        assert _make_plan(PRE_EXISTING_ID, status='running') in plans

    def test_concurrent_bulk_rewrites_lose_one(self, plan_context):
        """Negative control: the bulk whole-array rewrite loses a write.

        Both writers compute their new array from the SAME pre-lock snapshot —
        the read that decides the array happens outside any lock — so whichever
        commits second overwrites the other's row. Both writers still report
        success, which is exactly what makes the loss silent.
        """
        slug = 'race-bulk-epic'
        status_path = _write_status(plan_context, slug)
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}

        # The shared pre-lock read both writers decide from.
        snapshot = _read_plans(status_path)

        def _bulk_write(index: int):
            new_array = [*snapshot, _make_plan(RACED_PLAN_IDS[index])]
            return run_script(
                STATUS_SCRIPT_PATH,
                'update-field',
                '--plan-id',
                slug,
                '--field',
                'plans',
                '--value',
                json.dumps(new_array),
                '--store',
                'orchestrator',
                env_overrides=env,
                timeout=30,
            )

        results = _race(_bulk_write)

        # Same population as the positive arm, and both writers SUCCEEDED.
        assert len(results) == WRITER_COUNT
        assert [r.returncode for r in results] == [0] * WRITER_COUNT

        plans = _read_plans(status_path)
        # Grew by ONE, not by WRITER_COUNT: one row was silently dropped.
        assert len(plans) == 1 + 1
        surviving = {row['id'] for row in plans} & set(RACED_PLAN_IDS)
        assert len(surviving) == 1
