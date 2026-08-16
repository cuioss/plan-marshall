#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``merge-window-accounting`` — a blocked plan flags contention, an uncontended
one is clean, a high waiting count flags, an out-of-corpus lock is still
attributed, a reclaimed event is counted, and no logs yields no rows.
"""

from pathlib import Path

from _audit_fixtures import audit


def _write_merge_log(repo_root: Path, name: str, lines: str) -> None:
    """Stage a global log carrying `[LOCK] (merge:*)` lifecycle lines."""
    logs_dir = repo_root / ".plan" / "local" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / name).write_text(lines, encoding="utf-8")


def _lock_inputs(repo_root: Path, *plan_ids: str) -> list:
    """Build a corpus of PlanInputs for the named plan ids (no disk artifacts).

    ``cross_merge_window_accounting`` reads only the corpus plan-id set (for the
    ``in_corpus`` attribution column) plus the global logs under ``repo_root``, so
    the inputs are constructed directly rather than materialised on disk.
    """
    return [
        audit.PlanInputs(
            plan_id=pid,
            plan_dir=repo_root / ".plan" / "local" / "archived-plans" / pid,
        )
        for pid in plan_ids
    ]


def test_merge_window_blocked_plan_flags_contention(tmp_path):
    # A plan that was `blocked` (waited behind the FIFO front) records
    # merge_contention and is a genuine signal; its max_waiting rides on the
    # immediately-following indented waiting_count line.
    log = (
        "[2026-07-01T10:00:00Z] [INFO] [a] [LOCK] (merge:blocked) planA\n"
        "    waiting_count: 2\n"
        "[2026-07-01T10:05:00Z] [INFO] [b] [LOCK] (merge:acquired) planA\n"
        "    waiting_count: 0\n"
        "[2026-07-01T10:10:00Z] [INFO] [c] [LOCK] (merge:released) planA\n"
    )
    _write_merge_log(tmp_path, "work-2026-07-01.log", log)
    result = audit.cross_merge_window_accounting(_lock_inputs(tmp_path, "planA"), tmp_path)

    assert len(result["rows"]) == 1
    row = result["rows"][0]
    assert row["plan_id"] == "planA"
    assert row["in_corpus"] == "true"
    assert row["blocked"] == 1
    assert row["acquired"] == 1
    assert row["released"] == 1
    assert row["max_waiting"] == 2
    assert row["flags"] == "merge_contention"
    assert audit._merge_window_genuine(row) is True
    assert result["corpus"]["contended_plans"] == 1
    assert result["corpus"]["total_blocked"] == 1
    assert result["corpus"]["max_waiting_observed"] == 2


def test_merge_window_uncontended_plan_is_clean(tmp_path):
    # A plain acquire/release with no block and a queue depth of 1 (only this
    # plan) is uncontended: no flag, informational.
    log = (
        "[2026-07-01T11:00:00Z] [INFO] [a] [LOCK] (merge:acquired) planB\n"
        "    waiting_count: 1\n"
        "[2026-07-01T11:05:00Z] [INFO] [b] [LOCK] (merge:released) planB\n"
    )
    _write_merge_log(tmp_path, "work-2026-07-01.log", log)
    result = audit.cross_merge_window_accounting(_lock_inputs(tmp_path, "planB"), tmp_path)

    row = result["rows"][0]
    assert row["blocked"] == 0
    assert row["max_waiting"] == 1
    assert row["flags"] == ""
    assert audit._merge_window_genuine(row) is False
    assert result["corpus"]["contended_plans"] == 0


def test_merge_window_high_waiting_count_flags_contention(tmp_path):
    # Even without a `blocked` event, a max_waiting > 1 (other plans queued
    # behind this one) is contention — the plan held the mutex while others waited.
    log = (
        "[2026-07-01T12:00:00Z] [INFO] [a] [LOCK] (merge:acquired) planC\n"
        "    waiting_count: 3\n"
    )
    _write_merge_log(tmp_path, "work-2026-07-01.log", log)
    result = audit.cross_merge_window_accounting(_lock_inputs(tmp_path, "planC"), tmp_path)

    row = result["rows"][0]
    assert row["blocked"] == 0
    assert row["max_waiting"] == 3
    assert row["flags"] == "merge_contention"


def test_merge_window_attributes_out_of_corpus_lock(tmp_path):
    # A lock_id whose plan is NOT in the scanned corpus still emits a row (carried
    # for corpus totals) but is marked in_corpus=false.
    log = (
        "[2026-07-01T13:00:00Z] [INFO] [a] [LOCK] (merge:acquired) foreign-plan\n"
        "    waiting_count: 0\n"
    )
    _write_merge_log(tmp_path, "work-2026-07-01.log", log)
    result = audit.cross_merge_window_accounting(_lock_inputs(tmp_path, "planA"), tmp_path)

    assert len(result["rows"]) == 1
    assert result["rows"][0]["plan_id"] == "foreign-plan"
    assert result["rows"][0]["in_corpus"] == "false"


def test_merge_window_no_logs_yields_no_rows(tmp_path):
    # Best-effort: an absent logs dir yields no rows and zeroed corpus totals.
    result = audit.cross_merge_window_accounting(_lock_inputs(tmp_path, "planA"), tmp_path)
    assert result["rows"] == []
    assert result["corpus"]["plans_with_merge_events"] == 0
    assert result["corpus"]["max_waiting_observed"] == 0


def test_merge_window_reclaimed_event_counted(tmp_path):
    # The `reclaimed` event (a stale lock reclaimed) is bucketed and counted
    # per-plan without itself being contention.
    log = (
        "[2026-07-01T14:00:00Z] [INFO] [a] [LOCK] (merge:reclaimed) planD\n"
        "    waiting_count: 0\n"
    )
    _write_merge_log(tmp_path, "work-2026-07-01.log", log)
    result = audit.cross_merge_window_accounting(_lock_inputs(tmp_path, "planD"), tmp_path)

    row = result["rows"][0]
    assert row["reclaimed"] == 1
    assert row["flags"] == ""


def test_emit_merge_window_block_renders_header_and_severity(tmp_path):
    # The emitted block carries the corpus header scalars, the genuine_signal_count
    # summary, and the rows[] column set ending in severity.
    log = (
        "[2026-07-01T15:00:00Z] [INFO] [a] [LOCK] (merge:blocked) planE\n"
        "    waiting_count: 2\n"
        "[2026-07-01T15:05:00Z] [INFO] [b] [LOCK] (merge:acquired) planE\n"
    )
    _write_merge_log(tmp_path, "work-2026-07-01.log", log)
    result = audit.cross_merge_window_accounting(_lock_inputs(tmp_path, "planE"), tmp_path)

    block = audit.emit_merge_window_accounting_block(result)

    assert "check: merge-window-accounting" in block
    assert "status: success" in block
    assert "contended_plans: 1" in block
    assert "genuine_signal_count: 1" in block
    assert (
        "rows[1]{plan_id,in_corpus,acquired,released,blocked,reclaimed,"
        "max_waiting,flags,severity}:" in block
    )
    genuine_row = next(
        ln.strip() for ln in block.splitlines() if ln.strip().startswith("planE,")
    )
    assert genuine_row.endswith(",genuine")
