# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``analyze logs`` test modules.

Holds the module-level loads, constants and helpers the modules beside it
import. Below, verbatim, is the docstring of the module they were split from:

Tests for ``analyze-logs.py``.
"""


from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

from conftest import MARKETPLACE_ROOT

SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'analyze-logs.py'


# Direct import of analyze-logs.py (hyphenated filename → importlib). Used by
# the regression tests that call ``read_log`` in-process so they can
# capture stderr WARN lines reliably without shell-level quoting noise.
_spec = importlib.util.spec_from_file_location('analyze_logs', str(SCRIPT_PATH))


assert _spec is not None and _spec.loader is not None


_analyze_logs = importlib.util.module_from_spec(_spec)


_spec.loader.exec_module(_analyze_logs)


read_log = _analyze_logs.read_log


# =============================================================================
# Folded-in global-log per-plan signals
# =============================================================================
#
# Under the move-based finalize model the plan's OWN global logs
# (``{prefix}-YYYY-MM-DD.log``) are folded into ``<plan_dir>/logs/``. The
# ``analyze_folded_global_logs`` helper parses those folded-in copies for
# per-plan operational signals (error/non-INFO lines, slow calls, fixture
# leaks) — the per-plan replacement for the retired cross-plan
# ``global-log-analysis`` audit check.


def _line(ts: str, level: str, rest: str, *, hash_: str = '3befe7') -> str:
    """Build one folded-in global-log line in the bracketed grammar."""
    return f'[{ts}] [{level}] [{hash_}] {rest}'


def _write_folded_log(logs_dir: Path, name: str, lines: list[str]) -> None:
    """Write a folded-in global-log file under ``logs_dir/{name}``."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / name).write_text('\n'.join(lines) + '\n', encoding='utf-8')


def _git(repo: Path, *args: str) -> None:
    subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True)


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, 'init', '-b', 'main')
    _git(repo, 'config', 'user.email', 'test@example.com')
    _git(repo, 'config', 'user.name', 'Test')


# =============================================================================
# Voluntary-checkpoint polling detector (tightened)
# =============================================================================
#
# ``detect_voluntary_checkpoint_polling`` was tightened to fire a candidate pair
# ONLY when the 5-line window after an ``[ATTEMPT]`` line carries a GENUINE
# background-poll signal — a ``run_in_background=true`` marker, OR an
# ``until ... sleep ... done`` shell-loop shape. Bare polling-language keywords
# (``wait``, ``background``, ``sleep``) no longer trigger a candidate: those
# produced the false-positive class this detector was tightened to eliminate.
# CI-wait line shapes (``ci checks wait``, ``ci_complete_precondition``) are
# exempt — they contain a generic ``wait`` token but are legitimate synchronous
# CI waits, not voluntary-checkpoint polling.


def _attempt(rest: str = 'dispatch subagent') -> str:
    """Build one ``[ATTEMPT]`` work-log line in the bracketed grammar."""
    return f'[2026-06-13T10:00:00Z] [INFO] [abc123] [ATTEMPT] (plan-marshall:execute-task) {rest}'


def _plain(rest: str) -> str:
    """Build one non-ATTEMPT work-log line carrying arbitrary body text."""
    return f'[2026-06-13T10:00:01Z] [INFO] [def456] [STATUS] (plan-marshall:phase-5-execute) {rest}'


# ---------------------------------------------------------------------------
# D3 — build time from the change-ledger (the build-time oracle)
# ---------------------------------------------------------------------------


def _write_ledger(base: Path, rows: list[dict]) -> None:
    """Append kind=build rows to ``<base>/work/change-ledger.jsonl`` — the path
    ``resolve_ledger_path()`` derives from the fixture's PLAN_BASE_DIR."""
    work = base / 'work'
    work.mkdir(parents=True, exist_ok=True)
    with (work / 'change-ledger.jsonl').open('a', encoding='utf-8') as fh:
        for row in rows:
            fh.write(json.dumps(row) + '\n')


def _build_row(
    plan_id: str,
    *,
    dur,
    status: str = 'success',
    notation: str = 'plan-marshall:build-pyproject:pyproject_build',
    command: str = './pw verify',
) -> dict:
    return {
        'kind': 'build',
        'plan_id': plan_id,
        'notation': notation,
        'command': command,
        'duration_seconds': dur,
        'status': status,
        'timestamp_iso': '2026-06-01T10:00:00Z',
    }


# ---------------------------------------------------------------------------
# Aggregate script cost: the per-call ceiling answers "is any single call
# pathological?" and is STRUCTURALLY incapable of answering "what dominates total
# time?". These tests pin the complementary roll-up and assert the two are
# readable together — the ceiling stays, the roll-up is an addition.


def _hot_and_slow_log_lines() -> list[str]:
    """A folded global log where a fast script dominates cumulative wall-clock.

    ``pm:hot:hot``  — 100 calls x 0.2s  = 20.0s cumulative, max 0.2s
    ``pm:slow:slow``—   1 call  x 5.0s  =  5.0s cumulative, max 5.0s

    NEITHER call reaches the 30s per-call ceiling, so ``slow_call_count`` is 0
    for this corpus while ``pm:hot:hot`` owns 80% of all recorded time. That is
    the plan's thesis expressed as a fixture.
    """
    lines = [
        _line(f'2026-06-01T10:00:{i % 60:02d}Z', 'INFO', 'pm:hot:hot run (0.2s)')
        for i in range(100)
    ]
    lines.append(_line('2026-06-01T10:05:00Z', 'INFO', 'pm:slow:slow run (5.0s)'))
    return lines
