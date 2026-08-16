#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``merge-window-accounting`` — a blocked plan flags contention, an uncontended
one is clean, a high waiting count flags, an out-of-corpus lock is still
attributed, a reclaimed event is counted, and an absent substrate is reported
``unmeasured`` rather than as a zero contention count.

The end-to-end cases drive the PRODUCTION emitter (``_locks_core.log_lock_event``)
rather than synthesising ``[LOCK]`` text, because a suite that writes its own
marker cannot detect the check reading a directory the emitter never writes to —
which is exactly the state this check was in. ``log_lock_event`` resolves its path
from the main-anchored base's PARENT (``.plan/logs/``) while the scan looked under
``.plan/local/logs/``, so no real emission was ever in scan range and the check's
zero was structural.

Raw-text staging is kept only for the parser cases below, where a hand-built line
is the point (queue-depth placement, an out-of-corpus lock id).
"""

import importlib
from pathlib import Path

import _locks_core
from _audit_fixtures import audit


def _write_merge_log(repo_root: Path, name: str, lines: str) -> None:
    """Stage a global log carrying `[LOCK] (merge:*)` lifecycle lines."""
    logs_dir = repo_root / ".plan" / "local" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / name).write_text(lines, encoding="utf-8")


def _emit_via_production(repo_root: Path, monkeypatch, events: list[tuple]) -> Path:
    """Emit `[LOCK]` merge events through the production emitter.

    Points ``PLAN_BASE_DIR`` at ``repo_root/.plan/local`` so
    ``_locks_core._resolve_lock_log_path`` resolves exactly as it does in
    production — the main-anchored base's parent plus ``logs/`` — and returns the
    path it actually wrote. The return value is asserted on rather than assumed,
    so a future change to where the emitter writes surfaces here instead of
    silently taking the check back out of scan range.

    Each event is ``(event, lock_id, fields)``.
    """
    base = repo_root / ".plan" / "local"
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("PLAN_BASE_DIR", str(base))
    for event, lock_id, fields in events:
        _locks_core.log_lock_event("merge", event, lock_id, **fields)
    return _locks_core._resolve_lock_log_path()


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


def test_merge_window_no_logs_is_unmeasured_not_zero(tmp_path):
    # Best-effort: an absent logs dir yields no rows. The load-bearing assertion is
    # `measured is False` — with no lock timeline to read, the corpus is SILENT
    # about contention, which is not the same claim as "no contention occurred".
    result = audit.cross_merge_window_accounting(_lock_inputs(tmp_path, "planA"), tmp_path)
    assert result["rows"] == []
    assert result["measured"] is False


def test_unmeasured_block_withholds_counts_and_says_why(tmp_path):
    """The `unmeasured` state must be textually distinguishable from a zero."""
    result = audit.cross_merge_window_accounting(_lock_inputs(tmp_path, "planA"), tmp_path)

    block = audit.emit_merge_window_accounting_block(result)

    assert "status: unmeasured" in block
    assert "status: success" not in block
    assert "unmeasured_reason:" in block
    # The counts a reader would take as a health verdict are ABSENT, not zeroed.
    assert "contended_plans:" not in block
    assert "total_blocked:" not in block
    # No genuine_signal_count means the retire-on-quiet streak reader records no
    # quiet run for this check — an unmeasured run must not advance a detector
    # toward its own retirement.
    assert "genuine_signal_count:" not in block


def test_lock_log_present_with_no_merge_events_is_a_measured_zero(tmp_path, monkeypatch):
    """The other side of the discriminator: read substrate, genuinely no events.

    Distinguishing this from the case above IS the deliverable — a zero that
    cannot be told apart from "no data" is the defect.
    """
    log_path = _emit_via_production(tmp_path, monkeypatch, [("acquired", "planA", {})])
    # Blank the timeline in place: the file (the substrate) exists and was read,
    # and it names no merge event.
    log_path.write_text("", encoding="utf-8")

    result = audit.cross_merge_window_accounting(_lock_inputs(tmp_path, "planA"), tmp_path)

    assert result["measured"] is True
    assert result["rows"] == []
    assert result["corpus"]["contended_plans"] == 0
    block = audit.emit_merge_window_accounting_block(result)
    assert "status: success" in block
    assert "contended_plans: 0" in block


def test_production_emitter_output_is_in_scan_range(tmp_path, monkeypatch):
    """The end-to-end contract: what the lock primitive writes, the check reads.

    Fails against a scan rooted only at `.plan/local/logs/`, which is where this
    check looked while `log_lock_event` wrote to `.plan/logs/`.
    """
    log_path = _emit_via_production(
        tmp_path,
        monkeypatch,
        [
            ("blocked", "planA", {"waiting_count": 2}),
            ("acquired", "planA", {"waiting_count": 0}),
            ("released", "planA", {"waiting_count": 0}),
        ],
    )
    # Pin WHERE production wrote, so a move out of scan range fails here.
    assert log_path.parent == tmp_path / ".plan" / "logs"
    assert log_path.parent in [
        tmp_path.joinpath(*parts) for parts in audit._LOCK_LOG_ROOTS
    ]

    result = audit.cross_merge_window_accounting(_lock_inputs(tmp_path, "planA"), tmp_path)

    assert result["measured"] is True
    assert len(result["rows"]) == 1
    row = result["rows"][0]
    assert row["plan_id"] == "planA"
    assert row["blocked"] == 1
    assert row["acquired"] == 1
    assert row["released"] == 1
    assert row["max_waiting"] == 2
    assert row["flags"] == "merge_contention"


def test_production_emitter_line_shape_is_what_the_parser_matches(tmp_path, monkeypatch):
    """Guard the marker text itself, not just the directory.

    The regex is matched against a line the emitter produced, so a change to the
    `[LOCK] ({lock}:{event}) {lock_id}` rendering breaks this rather than
    silently returning the check to a permanent zero.
    """
    log_path = _emit_via_production(
        tmp_path, monkeypatch, [("acquired", "plan-x", {"waiting_count": 4})]
    )
    line = next(
        ln for ln in log_path.read_text(encoding="utf-8").splitlines() if "[LOCK]" in ln
    )

    match = audit._LOCK_MERGE_RE.search(line)

    assert match is not None
    assert match.group("event") == "acquired"
    assert match.group("lock_id") == "plan-x"


def test_locks_core_module_is_the_production_one():
    """The emitter under test is production, not a test double."""
    assert importlib.import_module("_locks_core") is _locks_core
    assert _locks_core.__file__.endswith("manage-locks/scripts/_locks_core.py")


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
