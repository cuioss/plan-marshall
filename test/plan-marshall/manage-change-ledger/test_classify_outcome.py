#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``classify-outcome`` verb of ``manage-change-ledger`` — the
deterministic killed-job classifier.

The classifier is a pure function of three observable inputs — the
harness-reported job status (``completed`` | ``killed``), the byte count of
the job's captured output, and the presence of a matching ``kind=build``
ledger row (most-recent first, scoped to the REQUIRED ``--worktree-sha``) —
returning a fixed ``verdict``:

* ``externally_killed`` — the job reported ``killed``, OR (no matching row AND
  ``output_bytes == 0``, the whole-tree-kill signature where the executor died
  before stamping anything), OR the matching row itself carries
  ``status: killed`` (the child-kill signature — the executor survived to the
  boundary and stamped the kill). MUST render "externally killed — not flaky,
  do not blind-retry" in the agent-readable TOON.
* ``timeout`` — a matching row carries ``status: timeout`` (a clean timeout is
  never classified as a kill).
* ``error`` — a matching row carries ``status: error``: the build RAN TO
  COMPLETION and reported failures. It is a READ verdict, held apart from
  ``undecidable`` so a build whose failures were reported is never presented
  as one whose outcome nobody read; the remedy is to read the named log, never
  to re-dispatch.
* ``success`` — a matching row carries ``status: success``.
* ``undecidable`` — anything else, INCLUDING a matching row carrying the
  derived-only ``status: unknown``, which supports no verdict of its own.

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

        def append_build(
            self,
            *,
            status: str,
            worktree_sha: str = _SHA_A,
            notation: str = 'n',
            exit_code: int = 0,
            log_file: str | None = None,
        ):
            argv = [
                'append', '--kind', 'build', '--notation', notation,
                '--exit-code', str(exit_code), '--status', status,
                '--worktree-sha', worktree_sha,
            ]
            if log_file is not None:
                argv += ['--log-file', log_file]
            result = self.run(*argv)
            assert result.success, result.stderr
            return result

        def classify(
            self,
            *,
            job_status: str,
            output_bytes: int,
            worktree_sha: str = _SHA_A,
        ) -> dict:
            result = self.run(
                'classify-outcome',
                '--job-status', job_status,
                '--output-bytes', str(output_bytes),
                '--worktree-sha', worktree_sha,
            )
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


def test_killed_row_with_completed_job_is_externally_killed(env) -> None:
    """The child-kill signature: a matching row carrying ``status: killed``.

    The executor survived to the dispatch boundary and stamped the kill it
    observed, while the harness reported the job as completed. This MUST
    classify externally_killed, not undecidable — regression for the branch
    order that fell through to undecidable.
    """
    env.append_build(status='killed')

    data = env.classify(job_status='completed', output_bytes=0, worktree_sha=_SHA_A)

    assert data['verdict'] == 'externally_killed', data
    assert NO_BLIND_RETRY in data['message']
    assert NO_BLIND_RETRY in data['display_detail']


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


def test_unknown_row_is_undecidable(env) -> None:
    """The derived-only ``status: unknown`` supports no verdict of its own.

    ``unknown`` records an outcome the dispatch boundary could not determine,
    so it must read as "nobody decided" — never as a kill, a success, or a
    reported failure. This is the matched negative control for the ``error``
    arm below: it is the ONE status that legitimately reaches ``undecidable``
    through a present row, which is what makes the ``error`` arm's separate
    verdict meaningful rather than a relabelling of the same bucket.
    """
    env.append_build(status='unknown')

    data = env.classify(job_status='completed', output_bytes=42, worktree_sha=_SHA_A)

    assert data['verdict'] == 'undecidable', data


# ---------------------------------------------------------------------------
# error — a build that RAN and reported failures is not an unread outcome
# ---------------------------------------------------------------------------


def test_error_row_classifies_error_not_undecidable(env) -> None:
    """A matching row with ``status: error`` classifies ``error``.

    Regression for the pre-fix classifier, which carried no ``error`` arm and
    let such a row fall through to ``undecidable``. That was a factual
    misreport rather than a harmless imprecision: ``undecidable`` asserts that
    NO decisive signal was found, so it sent the caller to re-dispatch a build
    that had already run to completion and reported its failures. Against the
    pre-fix chain this assertion observes ``undecidable`` and fails.
    """
    env.append_build(status='error', exit_code=1, log_file='/tmp/build.log')

    data = env.classify(job_status='completed', output_bytes=42, worktree_sha=_SHA_A)

    assert data['verdict'] == 'error', data


def test_error_and_unknown_rows_yield_distinguishable_verdicts(env) -> None:
    """``error`` and ``unknown`` must not collapse into one verdict.

    Both are non-success outcomes and the pre-fix classifier returned the SAME
    ``undecidable`` value for both, so a caller could not tell a build that
    reported failures from one whose outcome the boundary never determined —
    two states with opposite remedies. Scoping the two rows to different
    worktree shas lets a single test observe both verdicts and compare them
    directly, rather than inferring the distinction from two isolated runs.
    """
    env.append_build(
        status='error', exit_code=1, log_file='/tmp/build.log', worktree_sha=_SHA_A
    )
    env.append_build(status='unknown', worktree_sha=_SHA_B)

    error_data = env.classify(
        job_status='completed', output_bytes=42, worktree_sha=_SHA_A
    )
    unknown_data = env.classify(
        job_status='completed', output_bytes=42, worktree_sha=_SHA_B
    )

    assert error_data['verdict'] == 'error', error_data
    assert unknown_data['verdict'] == 'undecidable', unknown_data
    assert error_data['verdict'] != unknown_data['verdict']


def test_error_message_names_notation_exit_code_and_log(env) -> None:
    """The ``error`` message carries the three fields that locate the failures.

    The verdict's value is that the caller can go read the reported failures,
    so a message rendering only the word "error" sends them looking for the
    build instead. The row is the verb's only witness, so the notation that was
    dispatched, the exit code it returned, and the log path must all survive
    into the message.
    """
    env.append_build(
        status='error',
        notation='plan-marshall:build-pyproject:pyproject_build',
        exit_code=2,
        log_file='/tmp/pm-build-4711.log',
    )

    data = env.classify(job_status='completed', output_bytes=42, worktree_sha=_SHA_A)

    assert data['verdict'] == 'error', data
    assert 'plan-marshall:build-pyproject:pyproject_build' in data['message']
    assert 'exit_code=2' in data['message']
    assert '/tmp/pm-build-4711.log' in data['message']
    assert NO_BLIND_RETRY not in data['message']


def test_error_display_detail_is_the_bounded_summary(env) -> None:
    """``display_detail`` stays bounded while ``message`` carries the log path.

    The error arm is the one verdict whose message embeds a filesystem path, so
    it can outrun the one-line summary the field is meant to hold; every other
    arm's text is already short enough to serve as its own summary. The two
    fields therefore diverge here and only here.
    """
    env.append_build(
        status='error', exit_code=1, log_file='/tmp/a-very-long-build-log-path.log'
    )

    data = env.classify(job_status='completed', output_bytes=42, worktree_sha=_SHA_A)

    assert data['display_detail'] == 'build reported failure — read the named log'
    assert data['display_detail'] != data['message']


def test_killed_job_report_wins_over_error_row(env) -> None:
    """A harness-reported kill outranks a matching ``error`` row.

    The ``error`` arm was inserted into an ordered ``elif`` chain, so this pins
    the branch order: a kill the harness observed is the stronger signal and
    must not be masked by the failure the build managed to report first.
    """
    env.append_build(status='error', exit_code=1, log_file='/tmp/build.log')

    data = env.classify(job_status='killed', output_bytes=0, worktree_sha=_SHA_A)

    assert data['verdict'] == 'externally_killed', data
    assert NO_BLIND_RETRY in data['message']


# ---------------------------------------------------------------------------
# argparse surface
# ---------------------------------------------------------------------------


def test_job_status_is_choices_validated(env) -> None:
    """``--job-status`` accepts only completed|killed (argparse rejection)."""
    result = env.run(
        'classify-outcome', '--job-status', 'flaky',
        '--output-bytes', '0', '--worktree-sha', _SHA_A,
    )

    assert not result.success


def test_output_bytes_is_required(env) -> None:
    """``--output-bytes`` is a required argument."""
    result = env.run(
        'classify-outcome', '--job-status', 'killed', '--worktree-sha', _SHA_A
    )

    assert not result.success


def test_worktree_sha_is_required(env) -> None:
    """``--worktree-sha`` is required — an unscoped cross-check could match a
    stale row from a different worktree state and misclassify a kill as
    success."""
    result = env.run(
        'classify-outcome', '--job-status', 'killed', '--output-bytes', '0'
    )

    assert not result.success
