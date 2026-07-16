#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``classify-outcome`` verb of ``manage-change-ledger`` — the
deterministic killed-job classifier.

The classifier is a pure function of three observable inputs — the
harness-reported job status (``completed`` | ``killed``), the byte count of
the job's captured output, and the presence of a matching ``kind=build``
ledger row (most-recent first, scoped to ``--worktree-sha`` when supplied) —
returning a fixed ``verdict``:

* ``externally_killed`` — the job reported ``killed`` OR (no matching row AND
  ``output_bytes == 0``, the whole-tree-kill signature where the executor died
  before stamping anything). MUST render "externally killed — not flaky, do
  not blind-retry" in the agent-readable TOON.
* ``timeout`` — a matching row carries ``status: timeout`` (a clean timeout is
  never classified as a kill).
* ``success`` — a matching row carries ``status: success``.
* ``undecidable`` — anything else.

Tests drive the CLI end-to-end through :func:`conftest.run_script`, seeding
ledger rows through the ``append`` verb (the sole write path — a supplied
``--worktree-sha`` skips hash recomputation, so no git repo is needed) with
the ledger isolated under a per-test ``PLAN_BASE_DIR``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import get_script_path, run_script

_SCRIPT = get_script_path('plan-marshall', 'manage-change-ledger', 'manage-change-ledger.py')

_SHA_A = 'a' * 64
_SHA_B = 'b' * 64

NO_BLIND_RETRY = 'do not blind-retry'


@pytest.fixture
def env(tmp_path: Path):
    """An isolated ledger root (PLAN_BASE_DIR override) with CLI helpers."""
    base = tmp_path / 'base'
    base.mkdir()

    class Env:
        def __init__(self) -> None:
            self.base = base
            self.overrides = {'PLAN_BASE_DIR': str(base)}

        def run(self, *args: str):
            return run_script(
                _SCRIPT, *args, cwd=str(base), env_overrides=self.overrides
            )

        def append_build(self, *, status: str, worktree_sha: str = _SHA_A):
            result = self.run(
                'append', '--kind', 'build', '--notation', 'n',
                '--exit-code', '0', '--status', status,
                '--worktree-sha', worktree_sha,
            )
            assert result.success, result.stderr
            return result

        def classify(
            self,
            *,
            job_status: str,
            output_bytes: int,
            worktree_sha: str | None = None,
        ) -> dict:
            args = [
                'classify-outcome',
                '--job-status', job_status,
                '--output-bytes', str(output_bytes),
            ]
            if worktree_sha is not None:
                args.extend(['--worktree-sha', worktree_sha])
            result = self.run(*args)
            assert result.success, result.stderr
            data: dict = result.toon()
            return data

    return Env()


# ---------------------------------------------------------------------------
# externally_killed — the kill signature the request mandates
# ---------------------------------------------------------------------------


def test_killed_job_with_zero_bytes_is_externally_killed(env) -> None:
    """``killed`` + 0-byte output => externally_killed with the no-blind-retry verdict."""
    data = env.classify(job_status='killed', output_bytes=0)

    assert data['verdict'] == 'externally_killed', data
    assert NO_BLIND_RETRY in data['message']
    assert NO_BLIND_RETRY in data['display_detail']


def test_killed_job_report_wins_over_success_row(env) -> None:
    """A harness-reported kill classifies externally_killed even with a success row."""
    env.append_build(status='success')

    data = env.classify(job_status='killed', output_bytes=0, worktree_sha=_SHA_A)

    assert data['verdict'] == 'externally_killed', data
    assert NO_BLIND_RETRY in data['message']


def test_no_row_and_zero_bytes_is_externally_killed(env) -> None:
    """The whole-tree-kill signature: no ledger row + 0 bytes, job 'completed'.

    The executor died before the dispatch boundary could stamp anything, so
    the ABSENCE of a row is itself the signal — even though the harness
    reported the job as completed.
    """
    data = env.classify(job_status='completed', output_bytes=0)

    assert data['verdict'] == 'externally_killed', data
    assert NO_BLIND_RETRY in data['message']


def test_worktree_sha_scoping_treats_foreign_row_as_no_row(env) -> None:
    """A row stamped for a DIFFERENT sha does not defeat the kill signature."""
    env.append_build(status='success', worktree_sha=_SHA_A)

    data = env.classify(job_status='completed', output_bytes=0, worktree_sha=_SHA_B)

    assert data['verdict'] == 'externally_killed', data


# ---------------------------------------------------------------------------
# timeout / success — clean outcomes are never classified as kills
# ---------------------------------------------------------------------------


def test_timeout_row_classifies_timeout_not_externally_killed(env) -> None:
    """A clean timeout (row with ``status: timeout``) is NOT a kill.

    Even with a 0-byte output, the PRESENCE of the row proves the executor
    survived to the boundary — the kill signature requires the row's absence.
    """
    env.append_build(status='timeout')

    data = env.classify(job_status='completed', output_bytes=0, worktree_sha=_SHA_A)

    assert data['verdict'] == 'timeout', data
    assert NO_BLIND_RETRY not in data['message']


def test_success_row_classifies_success(env) -> None:
    """A clean success (row with ``status: success``) classifies success."""
    env.append_build(status='success')

    data = env.classify(job_status='completed', output_bytes=123, worktree_sha=_SHA_A)

    assert data['verdict'] == 'success', data
    assert NO_BLIND_RETRY not in data['message']


def test_most_recent_row_wins(env) -> None:
    """The matching row is the MOST RECENT kind=build entry."""
    env.append_build(status='success')
    env.append_build(status='timeout')

    data = env.classify(job_status='completed', output_bytes=0, worktree_sha=_SHA_A)

    assert data['verdict'] == 'timeout', data


# ---------------------------------------------------------------------------
# undecidable — no decisive signal
# ---------------------------------------------------------------------------


def test_completed_with_output_but_no_row_is_undecidable(env) -> None:
    """Job completed with output but no ledger row => undecidable (not a kill)."""
    data = env.classify(job_status='completed', output_bytes=42)

    assert data['verdict'] == 'undecidable', data


def test_error_row_is_undecidable(env) -> None:
    """A matching row with ``status: error`` maps to no fixed verdict => undecidable."""
    env.append_build(status='error')

    data = env.classify(job_status='completed', output_bytes=42, worktree_sha=_SHA_A)

    assert data['verdict'] == 'undecidable', data


# ---------------------------------------------------------------------------
# argparse surface
# ---------------------------------------------------------------------------


def test_job_status_is_choices_validated(env) -> None:
    """``--job-status`` accepts only completed|killed (argparse rejection)."""
    result = env.run(
        'classify-outcome', '--job-status', 'flaky', '--output-bytes', '0'
    )

    assert not result.success


def test_output_bytes_is_required(env) -> None:
    """``--output-bytes`` is a required argument."""
    result = env.run('classify-outcome', '--job-status', 'killed')

    assert not result.success
