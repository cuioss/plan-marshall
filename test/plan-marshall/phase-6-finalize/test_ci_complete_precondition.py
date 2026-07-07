#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Unit tests for the phase-6-finalize CI-completion precondition resolver.

The helper at ``scripts/ci_complete_precondition.py`` is the dispatcher-side
implementation of the ``requires: [ci-complete]`` frontmatter declaration on
consumer finalize steps. These tests pin the four contracts documented in
the deliverable's Success Criteria:

1. Cache miss → inline ``ci wait`` → cache populated → a second call at the
   same HEAD returns ``satisfied`` without re-polling.
2. HEAD advance between calls → second call re-invokes ``ci wait`` (the
   cache entry is implicitly invalidated by SHA mismatch).
3. ``ci wait`` returns ``final_status: failure`` → helper returns
   ``wait_failed`` with ``ci_final_status: failure``; no cache entry is
   written.
4. ``ci wait`` returns ``status: timeout`` → helper returns ``wait_failed``
   with ``ci_final_status: timeout``; no cache entry is written.

The tests use the injectable seams (``ci_wait_runner`` / ``git_head_resolver``)
to avoid spawning real subprocesses or hitting live CI. Each test uses a
unique ``plan_id`` to prevent cross-test cache contamination (per
MEMORY.md "Test Isolation Pattern").
"""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

# Python 3.14's argparse colorizes ``--help`` output when the environment
# advertises color support (FORCE_COLOR / PYTHON_COLORS), injecting ANSI SGR
# escapes into the usage banner even under captured (non-TTY) stdout. Strip
# them so substring assertions on the banner are robust to color state.
_ANSI_SGR_RE = re.compile(r'\x1b\[[0-9;]*m')


def _strip_ansi(text: str) -> str:
    """Remove ANSI SGR color escapes from ``text``."""
    return _ANSI_SGR_RE.sub('', text)

# PlanContext fixture is provided automatically by conftest.py as `plan_context`.

# ---------------------------------------------------------------------------
# Module loading — the helper is registered in the executor mapping under
# the notation ``plan-marshall:phase-6-finalize:ci_complete_precondition``,
# but the unit tests still load it via importlib from the source path so
# the test seams (``ci_wait_runner`` / ``git_head_resolver``) can be
# injected at the Python-call level without spawning a subprocess. The
# executor-level invocation is exercised separately in
# :func:`test_executor_invocation_with_scrubbed_pythonpath` below.
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_resolver_mod = _load_module(
    'ci_complete_precondition',
    'ci_complete_precondition.py',
)
resolve = _resolver_mod.resolve
DEFAULT_CI_WAIT_TIMEOUT_SECONDS = _resolver_mod.DEFAULT_CI_WAIT_TIMEOUT_SECONDS
_cache_path = _resolver_mod._cache_path
_read_cache = _resolver_mod._read_cache

# ---------------------------------------------------------------------------
# Repo root anchor — the executor lives at ``<repo>/.plan/execute-script.py``
# and the renamed source script at the bundled path under
# ``marketplace/bundles/...``. The tests below subprocess the executor with
# a deliberately scrubbed environment, so we need an absolute anchor that
# does NOT depend on the parent process's cwd or PYTHONPATH.
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_EXECUTOR_PATH = _REPO_ROOT / '.plan' / 'execute-script.py'
_SOURCE_SCRIPT_PATH = _SCRIPTS_DIR / 'ci_complete_precondition.py'


# ---------------------------------------------------------------------------
# Test seams: deterministic stand-ins for git and the ci wait subprocess.
# ---------------------------------------------------------------------------


class _StubGitHead:
    """Deterministic ``git rev-parse HEAD`` substitute."""

    def __init__(self, sha: str) -> None:
        self.sha = sha
        self.calls: list[str] = []

    def __call__(self, worktree_path: str) -> str:
        self.calls.append(worktree_path)
        return self.sha


class _StubCiWait:
    """Records call count and returns canned envelopes per invocation."""

    def __init__(self, envelopes: list[dict]) -> None:
        self.envelopes = envelopes
        self.calls: list[tuple] = []

    def __call__(
        self,
        plan_id: str,
        pr_number: int,
        timeout_seconds: int,
        worktree_path: str,
    ) -> dict:
        self.calls.append((plan_id, pr_number, timeout_seconds, worktree_path))
        # Pop the next envelope; fail loudly if exhausted (test bug).
        if not self.envelopes:
            raise AssertionError(
                'Stub ci_wait_runner exhausted — test scheduled more calls '
                'than expected'
            )
        return self.envelopes.pop(0)


class _StubTimeoutSet:
    """Record every observed CI duration passed to the timeout_set seam."""

    def __init__(self) -> None:
        self.recorded: list[int] = []

    def __call__(self, duration_seconds: int) -> None:
        self.recorded.append(duration_seconds)


class _StubTimeoutGet:
    """Return canned ci:wait ceilings per successive resolve call."""

    def __init__(self, ceilings: list[int]) -> None:
        self.ceilings = ceilings
        self.calls: list[int] = []

    def __call__(self, default_seconds: int) -> int:
        self.calls.append(default_seconds)
        if not self.ceilings:
            return default_seconds
        return self.ceilings.pop(0)


class _StubClock:
    """Deterministic monotonic-clock stub returning successive tick values.

    ``resolve`` calls the clock exactly twice per invocation (immediately
    before and after the ``ci wait`` subprocess), so a list of ``[start, end]``
    ticks yields a measured elapsed of ``end - start``.
    """

    def __init__(self, ticks: list[float]) -> None:
        self.ticks = ticks
        self.calls = 0

    def __call__(self) -> float:
        value = self.ticks[self.calls]
        self.calls += 1
        return value


_SHA_A = 'a' * 40
_SHA_B = 'b' * 40
_PR = 123
_WORKTREE = '/nonexistent/worktree/path'  # Never read — git stub overrides.


# ---------------------------------------------------------------------------
# Test 1 — cache miss → ci wait succeeds → cache populated → second call
# returns ``satisfied`` without re-polling.
# ---------------------------------------------------------------------------


def test_cache_miss_then_hit_does_not_repoll(plan_context):
    plan_id = 'ci-precond-cache-miss-then-hit'
    git_stub = _StubGitHead(_SHA_A)
    # Only one envelope provided — a second call would raise.
    wait_stub = _StubCiWait(
        [{'status': 'success', 'final_status': 'success'}]
    )

    first = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
    )

    assert first['status'] == 'wait_succeeded'
    assert first['head_sha'] == _SHA_A
    assert first['ci_final_status'] == 'success'
    assert len(wait_stub.calls) == 1
    # Cache file written with the success outcome.
    cache_after = _read_cache(plan_id)
    assert cache_after is not None
    assert cache_after['head_sha'] == _SHA_A
    assert cache_after['ci_final_status'] == 'success'

    # Second call at the same HEAD with NO new ci wait envelopes.
    second = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
    )
    assert second['status'] == 'satisfied'
    assert second['head_sha'] == _SHA_A
    assert second['ci_final_status'] == 'success'
    # Critically: ci wait was NOT invoked a second time.
    assert len(wait_stub.calls) == 1, (
        'satisfied must short-circuit without re-invoking ci wait'
    )


# ---------------------------------------------------------------------------
# Test 2 — HEAD advance between calls re-invokes ci wait.
# ---------------------------------------------------------------------------


def test_head_advance_invalidates_cache(plan_context):
    plan_id = 'ci-precond-head-advance'
    # First call observes SHA_A; second observes SHA_B.
    git_stub = _StubGitHead(_SHA_A)
    wait_stub = _StubCiWait(
        [
            {'status': 'success', 'final_status': 'success'},
            {'status': 'success', 'final_status': 'success'},
        ]
    )

    first = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
    )
    assert first['status'] == 'wait_succeeded'
    assert first['head_sha'] == _SHA_A
    assert len(wait_stub.calls) == 1

    # Advance HEAD.
    git_stub.sha = _SHA_B

    second = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
    )
    # Cache is stale → resolver re-polls and reports wait_succeeded again.
    assert second['status'] == 'wait_succeeded'
    assert second['head_sha'] == _SHA_B
    assert len(wait_stub.calls) == 2, (
        'HEAD advance must force a fresh ci wait poll'
    )
    # Cache now reflects the new SHA.
    cache_after = _read_cache(plan_id)
    assert cache_after is not None
    assert cache_after['head_sha'] == _SHA_B


# ---------------------------------------------------------------------------
# Test 3 — ci wait returns final_status: failure → wait_failed, no cache.
# ---------------------------------------------------------------------------


def test_ci_failure_returns_wait_failed_without_caching(plan_context):
    plan_id = 'ci-precond-ci-failure'
    git_stub = _StubGitHead(_SHA_A)
    wait_stub = _StubCiWait(
        [{'status': 'success', 'final_status': 'failure'}]
    )

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
    )

    assert result['status'] == 'wait_failed'
    assert result['head_sha'] == _SHA_A
    assert result['ci_final_status'] == 'failure'
    # Critically: NO cache entry written on failure.
    cache_path = _cache_path(plan_id)
    assert not cache_path.exists(), (
        'Failure outcomes must not be cached; re-entry must re-poll'
    )


# ---------------------------------------------------------------------------
# Test 4 — ci wait timeout → wait_failed with timeout reason, no cache.
# ---------------------------------------------------------------------------


def test_ci_timeout_returns_wait_failed_with_timeout_reason(plan_context):
    plan_id = 'ci-precond-timeout'
    git_stub = _StubGitHead(_SHA_A)
    timeout_set_stub = _StubTimeoutSet()
    wait_stub = _StubCiWait(
        [
            {
                'status': 'error',
                'operation': 'ci_wait',
                'error': 'Timeout waiting for CI',
                'pr_number': _PR,
                'duration_sec': 600,
                'wait_outcome': 'deadline_exceeded',
                'last_status': 'pending',
            }
        ]
    )

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
        timeout_set_runner=timeout_set_stub,
    )

    assert result['status'] == 'wait_failed'
    assert result['head_sha'] == _SHA_A
    assert result['ci_final_status'] == 'timeout', (
        'Timeout envelope must surface ci_final_status=timeout so the '
        'dispatcher can include the reason in the consumer step display'
    )
    cache_path = _cache_path(plan_id)
    assert not cache_path.exists(), (
        'Timeout outcomes must not be cached; re-entry must re-poll'
    )
    # The deadline path records the provider's true duration so the ci:wait
    # ceiling ratchets upward — the starved-ratchet fix.
    assert timeout_set_stub.recorded == [600], (
        'A deadline_exceeded envelope carrying duration_sec must record it '
        'via timeout_set so the ci:wait ceiling can ratchet upward'
    )


# ---------------------------------------------------------------------------
# Deliverable 3 — the elapsed-at-deadline upward ratchet.
#
# When the ci:wait ceiling sits below the true CI duration, every wait hits
# deadline_exceeded before CI completes, so the success-path record never
# fires and the ceiling can never grow. The fix records the measured
# elapsed-at-deadline (>= the current ceiling) via the SAME timeout_set call
# so compute_weighted_timeout (0.80) + timeout_get (1.25) ratchet the ceiling
# upward across finalizes until it exceeds the true CI duration.
# ---------------------------------------------------------------------------


def test_deadline_exceeded_records_measured_elapsed_via_timeout_set(plan_context):
    """A synthetic deadline envelope WITHOUT duration_sec records the
    measured elapsed-at-deadline (>= the ceiling) via the timeout_set seam.
    """
    plan_id = 'ci-precond-elapsed-record'
    git_stub = _StubGitHead(_SHA_A)
    timeout_set_stub = _StubTimeoutSet()
    # No duration_sec — the elapsed fallback drives the record.
    wait_stub = _StubCiWait(
        [{'status': 'timeout', 'wait_outcome': 'deadline_exceeded'}]
    )
    # clock ticks [0, 605] → measured elapsed 605s, >= the 600s ceiling.
    clock = _StubClock([0.0, 605.0])

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        timeout_seconds=600,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
        timeout_set_runner=timeout_set_stub,
        monotonic_clock=clock,
    )

    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'timeout'
    assert timeout_set_stub.recorded == [605], (
        'The measured elapsed-at-deadline must be recorded so the ci:wait '
        'ceiling ratchets upward'
    )


def test_provider_duration_preferred_over_measured_elapsed(plan_context):
    """When the timeout envelope surfaces the provider's true check-run
    duration (duration_sec), it is preferred over the measured elapsed
    lower-bound — collapsing the geometric ratchet to a single step.
    """
    plan_id = 'ci-precond-provider-duration'
    git_stub = _StubGitHead(_SHA_A)
    timeout_set_stub = _StubTimeoutSet()
    wait_stub = _StubCiWait(
        [
            {
                'status': 'error',
                'wait_outcome': 'deadline_exceeded',
                'duration_sec': 800,
            }
        ]
    )
    # Measured elapsed would be 605, but the provider's 800 must win.
    clock = _StubClock([0.0, 605.0])

    resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        timeout_seconds=600,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
        timeout_set_runner=timeout_set_stub,
        monotonic_clock=clock,
    )

    assert timeout_set_stub.recorded == [800], (
        'Provider duration_sec must be preferred over the measured elapsed'
    )


def test_sub_ceiling_non_success_does_not_record(plan_context):
    """An immediate non-success envelope that did NOT consume the full wait
    (elapsed << ceiling, no duration_sec) MUST NOT record — a sub-ceiling
    observation would pull the ratchet DOWN via compute_weighted_timeout.
    """
    plan_id = 'ci-precond-sub-ceiling'
    git_stub = _StubGitHead(_SHA_A)
    timeout_set_stub = _StubTimeoutSet()
    # Executor-crash-style error envelope, no duration_sec.
    wait_stub = _StubCiWait(
        [{'status': 'error', 'error': 'executor crashed immediately'}]
    )
    # clock ticks [0, 3] → measured elapsed 3s, well below the 600s ceiling.
    clock = _StubClock([0.0, 3.0])

    resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        timeout_seconds=600,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
        timeout_set_runner=timeout_set_stub,
        monotonic_clock=clock,
    )

    assert timeout_set_stub.recorded == [], (
        'A sub-ceiling elapsed with no provider duration must not be recorded'
    )


def test_repeated_deadline_exceeded_ratchets_upward(plan_context):
    """Across finalizes, each deadline_exceeded records its elapsed-at-deadline;
    as the run-config mechanism grows the ceiling between calls, the recorded
    observations grow with it — proving resolve feeds the upward ratchet.
    """
    git_stub = _StubGitHead(_SHA_A)
    timeout_set_stub = _StubTimeoutSet()

    # Finalize 1: ceiling 600, elapsed 601 → records 601.
    resolve(
        plan_id='ci-precond-ratchet',
        worktree_path=_WORKTREE,
        pr_number=_PR,
        timeout_seconds=600,
        ci_wait_runner=_StubCiWait(
            [{'status': 'timeout', 'wait_outcome': 'deadline_exceeded'}]
        ),
        git_head_resolver=git_stub,
        timeout_set_runner=timeout_set_stub,
        monotonic_clock=_StubClock([0.0, 601.0]),
    )

    # Finalize 2: the ceiling has grown to 750 (the run-config ratchet);
    # a fresh deadline at elapsed 751 → records 751.
    resolve(
        plan_id='ci-precond-ratchet',
        worktree_path=_WORKTREE,
        pr_number=_PR,
        timeout_seconds=750,
        ci_wait_runner=_StubCiWait(
            [{'status': 'timeout', 'wait_outcome': 'deadline_exceeded'}]
        ),
        git_head_resolver=git_stub,
        timeout_set_runner=timeout_set_stub,
        monotonic_clock=_StubClock([0.0, 751.0]),
    )

    assert timeout_set_stub.recorded == [601, 751]
    assert timeout_set_stub.recorded[1] > timeout_set_stub.recorded[0], (
        'The recorded elapsed observations must grow as the ceiling ratchets up'
    )


# ---------------------------------------------------------------------------
# Test 5 — sanity check on the default timeout constant (regression guard
# against accidental ceiling reduction).
# ---------------------------------------------------------------------------


def test_default_timeout_matches_documented_ceiling():
    # The deliverable's design notes specify a 600s (10-minute) ceiling
    # matching the documented ci-wait budget. A change here would silently
    # tighten the precondition's tolerance, so we pin it.
    assert DEFAULT_CI_WAIT_TIMEOUT_SECONDS == 600


# ---------------------------------------------------------------------------
# Test 6 — regression guard: invoking the script via the executor notation
# with a deliberately scrubbed PYTHONPATH must still succeed. This pins the
# fix for lesson 2026-05-18-11-001: the prior underscore-prefixed helper
# carried an in-script ``sys.path`` self-bootstrap block that resolved the
# script-shared directory by walking parents of ``__file__``. When the
# script was relocated (e.g., when run from the plugin cache at
# ``target/claude/`` or from ``~/.claude/plugins/cache/`` rather than from
# the source tree), the parent-arithmetic landed one level too high and
# imports of ``toon_parser`` / ``marketplace_paths`` failed.
#
# The corrected helper drops the self-bootstrap entirely and trusts the
# executor proxy to inject PYTHONPATH. This test exercises that contract
# explicitly: it strips PYTHONPATH from the subprocess environment and
# invokes the executor with the documented notation. If the helper ever
# regrows a self-bootstrap that hard-codes parent traversal, this test
# would only mask the regression; the companion
# :func:`test_source_script_has_no_self_bootstrap` test below pins the
# absence of the legacy bootstrap pattern at the source-text level.
# ---------------------------------------------------------------------------


def test_executor_invocation_with_scrubbed_pythonpath():
    """Spawn the executor proxy with PYTHONPATH scrubbed and confirm the
    renamed helper still resolves cross-skill imports via the executor's
    injected paths.
    """
    # The executor must be present before the subprocess runs. The
    # session-level conftest bootstrap ensures this for fresh checkouts;
    # local dev environments and CI both pass through that path.
    assert _EXECUTOR_PATH.is_file(), (
        f'Executor missing at {_EXECUTOR_PATH} — '
        'conftest session bootstrap should have generated it'
    )

    # Build a deliberately scrubbed environment: drop PYTHONPATH and
    # PYTHONHOME entirely so the subprocess CANNOT inherit any path
    # injection from the calling pytest session. Keep PATH / HOME /
    # encoding vars so subprocess startup itself remains viable.
    scrubbed_env = {
        k: v
        for k, v in os.environ.items()
        if k not in {'PYTHONPATH', 'PYTHONHOME'}
    }
    # Belt-and-braces: even an inherited '' value would break our intent.
    assert 'PYTHONPATH' not in scrubbed_env
    assert 'PYTHONHOME' not in scrubbed_env

    completed = subprocess.run(
        [
            sys.executable,
            str(_EXECUTOR_PATH),
            'plan-marshall:phase-6-finalize:ci_complete_precondition',
            '--help',
        ],
        capture_output=True,
        text=True,
        env=scrubbed_env,
        cwd=str(_REPO_ROOT),
        timeout=30,
        check=False,
    )

    # The subprocess MUST exit cleanly. A non-zero exit here means the
    # renamed script failed to import its cross-skill dependencies under
    # the executor's PYTHONPATH injection — the exact failure mode the
    # lesson is meant to prevent.
    assert completed.returncode == 0, (
        f'Executor invocation failed (exit={completed.returncode}): '
        f'stdout={completed.stdout!r}, stderr={completed.stderr!r}'
    )

    # The argparse help banner MUST appear on stdout. We pin the script
    # filename (``ci_complete_precondition.py``) and the documented
    # ``resolve`` subcommand to guard against accidental rename drift in
    # the future. Strip ANSI color escapes first so the substring checks
    # hold whether or not Python 3.14's argparse colorized the banner.
    plain_stdout = _strip_ansi(completed.stdout)
    assert 'usage: ci_complete_precondition.py' in plain_stdout, (
        f'Argparse usage banner missing from stdout: {completed.stdout!r}'
    )
    assert 'resolve' in plain_stdout, (
        f'``resolve`` subcommand missing from help output: '
        f'{completed.stdout!r}'
    )


def test_source_script_has_no_self_bootstrap():
    """Pin the absence of the legacy ``sys.path`` self-bootstrap block.

    The pre-rename helper computed the script-shared directory via
    parent-arithmetic on ``__file__`` and called ``sys.path.insert(...)``
    inside the script body. That pattern broke when the script was
    relocated under ``target/claude/`` or the plugin cache because the
    parent count was hard-coded for the source tree layout. The
    executor-injected PYTHONPATH replaces this scheme.

    If a future change re-introduces a path-arithmetic ``sys.path``
    mutation in this script, the executor invocation may still succeed
    (the executor PYTHONPATH would mask the issue) but the regression
    would silently land. This text-level check catches it directly.
    """
    body = _SOURCE_SCRIPT_PATH.read_text(encoding='utf-8')

    # The legacy patterns we are guarding against.
    forbidden_markers = (
        # The exact identifiers the old self-bootstrap block defined.
        '_SCRIPTS_DIR',
        '_SCRIPT_SHARED',
        '_REF_TOON',
        # Any sys.path mutation inside the source script body. The
        # executor's PYTHONPATH injection is the only allowed mechanism.
        'sys.path.insert',
        'sys.path.append',
    )
    for marker in forbidden_markers:
        assert marker not in body, (
            f'Legacy self-bootstrap marker {marker!r} reappeared in '
            f'{_SOURCE_SCRIPT_PATH}. The renamed helper MUST rely on the '
            'executor proxy to inject PYTHONPATH; in-script sys.path '
            'mutation breaks when the script is relocated under '
            'target/claude/ or the plugin cache. See lesson '
            '2026-05-18-11-001.'
        )


# ---------------------------------------------------------------------------
# Lesson-2026-05-18-16-001 deliverable 5 — failing_checks + wait_outcome
# forwarding through the precondition resolver.
# ---------------------------------------------------------------------------


def test_failure_forwards_failing_checks_list(plan_context):
    """A ``ci wait`` envelope with ``failing_checks`` MUST forward the list
    verbatim through the resolver return so the dispatcher can name the
    failing checks in the consumer step's display_detail and emit the
    structured triage finding documented in deliverable 5.
    """
    plan_id = 'ci-precond-failing-checks'
    git_stub = _StubGitHead(_SHA_A)
    wait_stub = _StubCiWait(
        [
            {
                'status': 'success',
                'final_status': 'failure',
                'failing_checks': [
                    {'name': 'lint', 'conclusion': 'FAILURE'},
                    {'name': 'dep-review', 'conclusion': 'CANCELLED'},
                ],
                'wait_outcome': 'completed',
            }
        ]
    )

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
    )

    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'failure'
    assert result['failing_checks'] == [
        {'name': 'lint', 'conclusion': 'FAILURE'},
        {'name': 'dep-review', 'conclusion': 'CANCELLED'},
    ]
    assert result['wait_outcome'] == 'completed'


def test_no_checks_returns_distinct_ci_final_status(plan_context):
    """``final_status: none`` from ``ci wait`` MUST surface as
    ``ci_final_status: no_checks`` so the dispatcher can distinguish
    "CI never ran" from a real failure and route to the
    ``ci-verify-missing`` producer (deliverable 6).
    """
    plan_id = 'ci-precond-no-checks'
    git_stub = _StubGitHead(_SHA_A)
    wait_stub = _StubCiWait(
        [
            {
                'status': 'success',
                'final_status': 'none',
                'failing_checks': [],
                'wait_outcome': 'completed',
            }
        ]
    )

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
    )

    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'no_checks', (
        'no_checks must be distinct from failure so the dispatcher can '
        'route to ci-verify-missing instead of ci-verify-build'
    )
    assert result['failing_checks'] == []
    # Cache MUST remain absent — no_checks is a non-cacheable verdict.
    assert not _cache_path(plan_id).exists()


def test_timeout_forwards_wait_outcome_deadline_exceeded(plan_context):
    """A wait-deadline exhaustion MUST forward
    ``wait_outcome: deadline_exceeded`` and the still-running checks so the
    dispatcher routes to the ``ci-verify-timeout`` producer.
    """
    plan_id = 'ci-precond-timeout-forward'
    git_stub = _StubGitHead(_SHA_A)
    wait_stub = _StubCiWait(
        [
            {
                'status': 'error',
                'operation': 'ci_wait',
                'error': 'Timeout waiting for CI',
                'pr_number': _PR,
                'duration_sec': 600,
                'last_status': 'pending',
                'wait_outcome': 'deadline_exceeded',
                'failing_checks': [
                    {'name': 'slow-deploy', 'conclusion': 'PENDING'},
                ],
            }
        ]
    )

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
        timeout_set_runner=_StubTimeoutSet(),
    )

    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'timeout'
    assert result['wait_outcome'] == 'deadline_exceeded'
    assert [c['name'] for c in result['failing_checks']] == ['slow-deploy']


def test_satisfied_does_not_carry_failing_checks_field(plan_context):
    """``satisfied`` (cache hit) MUST NOT include the failing_checks /
    wait_outcome fields — they are wait_failed-only signals. Deliverable 5
    specifies "satisfied and wait_succeeded outcomes produce no finding";
    the absence of the fields is the structural complement.
    """
    plan_id = 'ci-precond-satisfied-no-failing-checks'
    git_stub = _StubGitHead(_SHA_A)
    # First call: populate the cache via wait_succeeded.
    wait_stub = _StubCiWait(
        [{'status': 'success', 'final_status': 'success'}]
    )
    resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
    )
    # Second call: cache hit → satisfied.
    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
    )

    assert result['status'] == 'satisfied'
    # The "no triage finding on satisfied" guarantee is structurally
    # enforced by the absence of the failing_checks field — the SKILL.md
    # dispatcher only emits findings when wait_failed is observed.
    assert 'failing_checks' not in result
    assert 'wait_outcome' not in result


def test_wait_succeeded_does_not_carry_failing_checks_field(plan_context):
    """``wait_succeeded`` (fresh poll succeeded) MUST NOT include
    failing_checks / wait_outcome — same rationale as satisfied above.
    """
    plan_id = 'ci-precond-wait-succeeded-no-failing-checks'
    git_stub = _StubGitHead(_SHA_A)
    wait_stub = _StubCiWait(
        [{'status': 'success', 'final_status': 'success'}]
    )

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
    )

    assert result['status'] == 'wait_succeeded'
    assert 'failing_checks' not in result
    assert 'wait_outcome' not in result


# ---------------------------------------------------------------------------
# Subcommand-vector regression — the resolver MUST invoke the executor with
# the ``checks wait`` primitive, NOT the non-existent ``ci wait`` subcommand.
# The ci.py executor's top-level choices are {pr, checks, issue, branch};
# the CI-wait primitive lives at ``checks wait``. A call carrying ``ci wait``
# is rejected by argparse with exit 2 and empty stdout, which made
# ``_run_ci_wait`` return ``{status: error}`` and ``resolve`` fall through
# to wait_failed / timeout for every plan. These tests pin the corrected
# vector at the command-construction level — the seam-injected tests above
# never observe the constructed cmd list.
# ---------------------------------------------------------------------------


class _CapturingSubprocessRun:
    """Records the ``cmd`` list passed to ``subprocess.run`` and returns a
    canned ``CompletedProcess`` carrying a parseable TOON envelope.
    """

    def __init__(self, stdout: str) -> None:
        self.stdout = stdout
        self.captured_cmd: list[str] | None = None

    def __call__(self, cmd, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        self.captured_cmd = list(cmd)
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout=self.stdout, stderr=''
        )


def test_run_ci_wait_uses_checks_wait_subcommand_vector(monkeypatch):
    """``_run_ci_wait`` MUST construct the executor command with the
    ``checks wait`` subcommand vector — never the non-existent ``ci wait``.
    """
    capturing = _CapturingSubprocessRun(
        stdout='status: success\nfinal_status: success\n'
    )
    monkeypatch.setattr(_resolver_mod.subprocess, 'run', capturing)

    result = _resolver_mod._run_ci_wait(
        plan_id='ci-precond-vector-check',
        pr_number=_PR,
        timeout_seconds=DEFAULT_CI_WAIT_TIMEOUT_SECONDS,
        worktree_path=str(_REPO_ROOT),
    )

    assert capturing.captured_cmd is not None
    cmd = capturing.captured_cmd
    # The corrected vector: 'checks' immediately followed by 'wait'.
    assert 'checks' in cmd, f'cmd missing "checks" segment: {cmd!r}'
    checks_idx = cmd.index('checks')
    assert cmd[checks_idx + 1] == 'wait', (
        f'"checks" must be immediately followed by "wait": {cmd!r}'
    )
    # The legacy non-existent vector MUST NOT be present: there must be no
    # 'ci' element immediately followed by 'wait'.
    for i, token in enumerate(cmd[:-1]):
        assert not (token == 'ci' and cmd[i + 1] == 'wait'), (
            f'legacy "ci wait" subcommand vector reappeared in {cmd!r} — '
            'the ci.py executor has no "ci" subcommand'
        )
    # The wait primitive's --pr-number / --timeout flags are unchanged.
    assert '--pr-number' in cmd
    assert '--timeout' in cmd
    # The envelope parsed cleanly into the success outcome.
    assert result.get('final_status') == 'success'


def test_run_ci_wait_success_envelope_yields_wait_succeeded(plan_context, monkeypatch):
    """End-to-end through ``resolve``: when the executor (subprocess.run)
    returns a success envelope, ``resolve`` MUST report ``wait_succeeded``.
    This pins the corrected vector all the way to the public return value
    without injecting the ``ci_wait_runner`` seam.
    """
    capturing = _CapturingSubprocessRun(
        stdout='status: success\nfinal_status: success\n'
    )
    monkeypatch.setattr(_resolver_mod.subprocess, 'run', capturing)

    plan_id = 'ci-precond-vector-end-to-end'
    result = resolve(
        plan_id=plan_id,
        worktree_path=str(_REPO_ROOT),
        pr_number=_PR,
        git_head_resolver=_StubGitHead(_SHA_A),
    )

    assert result['status'] == 'wait_succeeded'
    assert result['ci_final_status'] == 'success'
    # The real _run_ci_wait ran and constructed the corrected vector.
    assert capturing.captured_cmd is not None
    checks_idx = capturing.captured_cmd.index('checks')
    assert capturing.captured_cmd[checks_idx + 1] == 'wait'


# ---------------------------------------------------------------------------
# subprocess.TimeoutExpired except-branch — the ci wait subprocess can blow
# past even the outer host ceiling (timeout_seconds + 30) and wedge. Before
# the fix, subprocess.run raised subprocess.TimeoutExpired, which propagated
# uncaught through _run_ci_wait → resolve → cmd_resolve (cmd_resolve only
# catches RuntimeError), crashing the precondition resolver with a traceback
# instead of a TOON-shaped result. The fix catches TimeoutExpired in
# _run_ci_wait and returns a synthetic timeout-like envelope so resolve()
# routes it through the wait_failed / ci_final_status: timeout path the same
# way an inner ci-wait deadline does.
# ---------------------------------------------------------------------------


def _raise_timeout_expired(cmd, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
    """subprocess.run stand-in that always raises TimeoutExpired.

    Mirrors the real signature: subprocess.run forwards its ``timeout``
    kwarg into the exception so the message can name the breached ceiling.
    """
    raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get('timeout'))


def test_run_ci_wait_returns_timeout_envelope_on_subprocess_timeout(monkeypatch):
    """``_run_ci_wait`` MUST catch ``subprocess.TimeoutExpired`` and return a
    timeout-like envelope instead of propagating the exception.
    """
    monkeypatch.setattr(
        _resolver_mod.subprocess, 'run', _raise_timeout_expired
    )

    result = _resolver_mod._run_ci_wait(
        plan_id='ci-precond-subprocess-timeout',
        pr_number=_PR,
        timeout_seconds=DEFAULT_CI_WAIT_TIMEOUT_SECONDS,
        worktree_path=str(_REPO_ROOT),
    )

    # The envelope is a dict (no exception escaped) with the timeout markers.
    assert isinstance(result, dict)
    assert result['status'] == 'timeout', (
        'A wedged ci wait subprocess must surface a timeout-like envelope, '
        f'not {result.get("status")!r}'
    )
    assert result['wait_outcome'] == 'deadline_exceeded', (
        'The deadline_exceeded marker lets downstream consumers classify '
        'the precondition decision into the timeout triage producer'
    )
    # The error message names the breached host ceiling (timeout_seconds + 30).
    assert 'error' in result
    assert str(DEFAULT_CI_WAIT_TIMEOUT_SECONDS + 30) in result['error']


def test_resolve_routes_subprocess_timeout_to_wait_failed_timeout(
    plan_context, monkeypatch
):
    """End-to-end: a ``subprocess.TimeoutExpired`` from the real
    ``_run_ci_wait`` (driven through ``resolve`` without the ci_wait_runner
    seam) MUST resolve to ``wait_failed`` / ``ci_final_status: timeout`` and
    write no cache entry — the same terminal shape as an inner ci-wait
    deadline. This pins that the new except-branch envelope threads cleanly
    through resolve()'s non-success classification.
    """
    monkeypatch.setattr(
        _resolver_mod.subprocess, 'run', _raise_timeout_expired
    )

    plan_id = 'ci-precond-subprocess-timeout-end-to-end'
    result = resolve(
        plan_id=plan_id,
        worktree_path=str(_REPO_ROOT),
        pr_number=_PR,
        git_head_resolver=_StubGitHead(_SHA_A),
    )

    assert result['status'] == 'wait_failed'
    assert result['head_sha'] == _SHA_A
    assert result['ci_final_status'] == 'timeout'
    assert result['wait_outcome'] == 'deadline_exceeded'
    # Timeout outcomes are never cached — re-entry must re-poll.
    assert not _cache_path(plan_id).exists(), (
        'A subprocess-timeout outcome must not be cached'
    )


# ---------------------------------------------------------------------------
# Run-config-backed CI-wait timeout — deliverable 2. The resolver sources the
# ``ci wait --timeout`` ceiling from run-configuration.json (command key
# ``ci:wait``) instead of the hard-coded constant, and records the observed
# CI duration back after a successful wait so the ceiling adapts like
# build-command timeouts. These tests inject the timeout_get_runner /
# timeout_set_runner seams so no real run-configuration.json I/O occurs.
# ---------------------------------------------------------------------------


class _StubTimeoutGet:
    """Deterministic ``run_config timeout get`` substitute.

    Returns a fixed seeded value, ignoring the requested default — this
    models a run-configuration.json that already carries a ci:wait entry.
    """

    def __init__(self, seeded_value: int) -> None:
        self.seeded_value = seeded_value
        self.calls: list[int] = []

    def __call__(self, default_seconds: int) -> int:
        self.calls.append(default_seconds)
        return self.seeded_value


class _StubTimeoutGetMissing:
    """Models a run-configuration.json with no ci:wait entry — the helper
    echoes the supplied default straight back.
    """

    def __init__(self) -> None:
        self.calls: list[int] = []

    def __call__(self, default_seconds: int) -> int:
        self.calls.append(default_seconds)
        return default_seconds


class _StubTimeoutSet:
    """Records the durations written back via ``run_config timeout set``."""

    def __init__(self) -> None:
        self.durations: list[int] = []

    def __call__(self, duration_seconds: int) -> None:
        self.durations.append(duration_seconds)


def test_resolve_reads_timeout_from_run_config_entry(plan_context):
    """(a) When run-configuration.json carries a ci:wait entry, resolve()
    MUST forward that persisted value as the ci wait --timeout ceiling
    rather than the hard-coded DEFAULT_CI_WAIT_TIMEOUT_SECONDS.
    """
    plan_id = 'ci-precond-runconfig-seeded'
    get_stub = _StubTimeoutGet(seeded_value=420)
    set_stub = _StubTimeoutSet()
    wait_stub = _StubCiWait(
        [{'status': 'success', 'final_status': 'success'}]
    )

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=_StubGitHead(_SHA_A),
        timeout_get_runner=get_stub,
        timeout_set_runner=set_stub,
    )

    assert result['status'] == 'wait_succeeded'
    # The run-config lookup fired with the documented fallback default.
    assert get_stub.calls == [DEFAULT_CI_WAIT_TIMEOUT_SECONDS]
    # The seeded value (not the default) reached the ci wait runner.
    assert len(wait_stub.calls) == 1
    # _StubCiWait records (plan_id, pr_number, timeout_seconds, worktree).
    assert wait_stub.calls[0][2] == 420


def test_resolve_uses_default_timeout_when_no_run_config_entry(plan_context):
    """(b) With no ci:wait entry, the run-config helper echoes the supplied
    default, so resolve() falls back to DEFAULT_CI_WAIT_TIMEOUT_SECONDS.
    """
    plan_id = 'ci-precond-runconfig-missing'
    get_stub = _StubTimeoutGetMissing()
    set_stub = _StubTimeoutSet()
    wait_stub = _StubCiWait(
        [{'status': 'success', 'final_status': 'success'}]
    )

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=_StubGitHead(_SHA_A),
        timeout_get_runner=get_stub,
        timeout_set_runner=set_stub,
    )

    assert result['status'] == 'wait_succeeded'
    assert get_stub.calls == [DEFAULT_CI_WAIT_TIMEOUT_SECONDS]
    # The default propagated through to the ci wait runner unchanged.
    assert wait_stub.calls[0][2] == DEFAULT_CI_WAIT_TIMEOUT_SECONDS


def test_resolve_records_observed_duration_after_successful_wait(plan_context):
    """(c) After a successful ci wait, resolve() MUST write the observed
    ``duration_sec`` back via the run-config timeout-set helper so the
    ci:wait ceiling adapts to real run lengths.
    """
    plan_id = 'ci-precond-runconfig-writeback'
    get_stub = _StubTimeoutGetMissing()
    set_stub = _StubTimeoutSet()
    wait_stub = _StubCiWait(
        [
            {
                'status': 'success',
                'final_status': 'success',
                'duration_sec': 137,
            }
        ]
    )

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=_StubGitHead(_SHA_A),
        timeout_get_runner=get_stub,
        timeout_set_runner=set_stub,
    )

    assert result['status'] == 'wait_succeeded'
    # The observed duration was written back exactly once.
    assert set_stub.durations == [137]


def test_resolve_explicit_timeout_overrides_run_config_lookup(plan_context):
    """An explicit ``timeout_seconds`` argument bypasses the run-config
    lookup entirely — the get helper MUST NOT be consulted.
    """
    plan_id = 'ci-precond-runconfig-explicit'
    get_stub = _StubTimeoutGet(seeded_value=420)
    set_stub = _StubTimeoutSet()
    wait_stub = _StubCiWait(
        [{'status': 'success', 'final_status': 'success'}]
    )

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        timeout_seconds=55,
        ci_wait_runner=wait_stub,
        git_head_resolver=_StubGitHead(_SHA_A),
        timeout_get_runner=get_stub,
        timeout_set_runner=set_stub,
    )

    assert result['status'] == 'wait_succeeded'
    # The run-config get helper was never consulted.
    assert get_stub.calls == []
    # The explicit value reached the ci wait runner.
    assert wait_stub.calls[0][2] == 55


def test_consume_failures_mode_threads_wait_failed_envelope(plan_context):
    """Regression guard for deliverable 6.

    A failing CI run resolved with ``mode='consume-failures'`` MUST surface
    the full ``wait_failed`` envelope — ``failing_checks``, ``wait_outcome``,
    AND a ``mode: consume-failures`` echo — so the ``default:ci-verify``
    consumer body can classify the failures into the multi-failure-mode
    taxonomy. The previous strict-only resolver short-circuited the body
    on ``wait_failed``, making the classify → file-findings →
    verification-feedback → loop_back machinery unreachable on red CI.

    This test feeds a ``ci_wait_runner`` seam reporting a failure envelope
    with two failing checks and asserts the resolver output preserves the
    mode, the failing-check enumeration, and the wait outcome.
    """
    plan_id = 'ci-precond-consume-failures-mode'
    git_stub = _StubGitHead(_SHA_A)
    wait_stub = _StubCiWait(
        [
            {
                'status': 'success',
                'final_status': 'failure',
                'failing_checks': [
                    {'name': 'lint', 'conclusion': 'FAILURE'},
                    {'name': 'unit-tests', 'conclusion': 'FAILURE'},
                ],
                'wait_outcome': 'completed',
            }
        ]
    )

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
        mode='consume-failures',
    )

    # The wait_failed envelope was NOT short-circuited — the resolver
    # returned the failure envelope verbatim so the ci-verify body
    # can classify the failing checks.
    assert result['status'] == 'wait_failed', (
        f'consume-failures resolution must surface wait_failed, not '
        f'{result["status"]!r} — short-circuiting on wait_failed is '
        'the precise defect lesson 2026-05-22-16-001 deliverable 6 '
        'guards against'
    )
    assert result['ci_final_status'] == 'failure'
    # The mode echo is the load-bearing signal: consumers branch on
    # this field to decide whether to short-circuit or thread the
    # envelope through to their body.
    assert result['mode'] == 'consume-failures', (
        'resolver output must echo the mode value so consumers can '
        'tell strict-mode wait_failed (short-circuit) from '
        'consume-failures wait_failed (run body with envelope)'
    )
    # The full failing-check enumeration is preserved verbatim.
    assert result['failing_checks'] == [
        {'name': 'lint', 'conclusion': 'FAILURE'},
        {'name': 'unit-tests', 'conclusion': 'FAILURE'},
    ]
    assert result['wait_outcome'] == 'completed'


def test_consume_failures_mode_preserves_timeout_envelope(plan_context):
    """A timeout under consume-failures MUST still surface as wait_failed
    with ci_final_status=timeout — the consume-failures path is for
    *all* wait_failed shapes (failure, timeout, no_checks), not just
    final_status=failure.
    """
    plan_id = 'ci-precond-consume-failures-timeout'
    git_stub = _StubGitHead(_SHA_A)
    wait_stub = _StubCiWait(
        [
            {
                'status': 'error',
                'operation': 'ci_wait',
                'error': 'Timeout waiting for CI',
                'wait_outcome': 'deadline_exceeded',
                'failing_checks': [
                    {'name': 'slow-deploy', 'conclusion': 'PENDING'},
                ],
            }
        ]
    )

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
        mode='consume-failures',
    )

    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'timeout'
    assert result['mode'] == 'consume-failures'
    assert result['wait_outcome'] == 'deadline_exceeded'
    assert [c['name'] for c in result['failing_checks']] == ['slow-deploy']


def test_strict_mode_default_does_not_echo_consume_failures(plan_context):
    """Sanity guard: a default (strict) resolution MUST NOT echo
    ``mode: consume-failures`` — the mode echo is a load-bearing signal
    and accidentally setting it under strict would mis-route consumers
    into the consume-failures branch.
    """
    plan_id = 'ci-precond-strict-mode-default'
    git_stub = _StubGitHead(_SHA_A)
    wait_stub = _StubCiWait(
        [
            {
                'status': 'success',
                'final_status': 'failure',
                'failing_checks': [{'name': 'lint'}],
                'wait_outcome': 'completed',
            }
        ]
    )

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
        # No mode argument — defaults to strict.
    )

    assert result['status'] == 'wait_failed'
    # The mode echo is present on wait_failed but carries strict.
    assert result.get('mode') == 'strict'


def test_resolve_skips_writeback_when_duration_absent(plan_context):
    """When the ci wait envelope omits ``duration_sec``, resolve() MUST NOT
    write a bogus value back — the adaptive update is skipped.
    """
    plan_id = 'ci-precond-runconfig-no-duration'
    get_stub = _StubTimeoutGetMissing()
    set_stub = _StubTimeoutSet()
    # Envelope carries no duration_sec field.
    wait_stub = _StubCiWait(
        [{'status': 'success', 'final_status': 'success'}]
    )

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=_StubGitHead(_SHA_A),
        timeout_get_runner=get_stub,
        timeout_set_runner=set_stub,
    )

    assert result['status'] == 'wait_succeeded'
    # No duration → no write-back.
    assert set_stub.durations == []


# ---------------------------------------------------------------------------
# Fixture-driven tests — feed each representative ``ci checks wait`` TOON
# stdout through ``parse_toon`` and the resolver. Closes the test gap that
# lesson 2026-05-24-14-001 ("Mock-only unit tests cannot reproduce the live
# failure mode") identified: the existing seam-based tests pin the post-
# parse contract but never exercise parse_toon → resolve(). The fixtures
# live under test/plan-marshall/phase-6-finalize/fixtures/ci-wait/.
# ---------------------------------------------------------------------------


_FIXTURE_DIR = (
    _REPO_ROOT
    / 'test'
    / 'plan-marshall'
    / 'phase-6-finalize'
    / 'fixtures'
    / 'ci-wait'
)


def _load_parse_toon():
    """Import parse_toon from the ref-toon-format scripts directory."""
    parser_dir = (
        _REPO_ROOT
        / 'marketplace'
        / 'bundles'
        / 'plan-marshall'
        / 'skills'
        / 'ref-toon-format'
        / 'scripts'
    )
    spec = importlib.util.spec_from_file_location(
        'toon_parser', parser_dir / 'toon_parser.py'
    )
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.parse_toon


_parse_toon = _load_parse_toon()


def _make_fixture_wait_runner(parsed: dict):
    """Build a ci_wait_runner stub that returns the parsed-fixture dict."""

    def _runner(plan_id, pr_number, timeout_seconds, worktree_path):  # noqa: ARG001
        return parsed

    return _runner


def _run_fixture_through_resolver(fixture_path, plan_id):
    """Parse a fixture file and feed the parsed dict through resolve()."""
    raw = fixture_path.read_text()
    parsed = _parse_toon(raw)
    runner = _make_fixture_wait_runner(parsed)
    git_stub = _StubGitHead(_SHA_A)
    # Isolate the timeout-path ratchet write: a fixture carrying a
    # deadline_exceeded envelope with a duration_sec would otherwise call the
    # real run-config timeout-set subprocess. The no-op stub keeps the fixture
    # tests hermetic.
    return resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=runner,
        git_head_resolver=git_stub,
        timeout_set_runner=_StubTimeoutSet(),
    )


def test_fixture_dir_present():
    """The fixture set composed by deliverable 2 (plus the stress fixtures
    added under the phase-5-execute Q-Gate finding e2c3ee re-direction) must
    be present.

    The Q-Gate finding called for widening the fixture set with the six
    stressor categories (a-f) the original 9 captures didn't cover. The
    `check-name-special-chars` and `failing-checks-with-colon-names` fixtures
    surfaced a live bug in `parse_toon`'s `_parse_uniform_array` key/value
    detection heuristic — fixed in TASK-004.
    """
    assert _FIXTURE_DIR.is_dir(), f'Fixture directory missing: {_FIXTURE_DIR}'
    expected = {
        # Original 9 fixtures from deliverable 2 (TASK-002).
        'green-success.toon',
        'failure-with-failing-checks.toon',
        'no-checks.toon',
        'timeout-deadline-exceeded.toon',
        'pending-then-cancelled.toon',
        'mixed-success-failure.toon',
        'skipped-checks.toon',
        'single-check-success.toon',
        'many-checks-success.toon',
        # Stress fixtures added per Q-Gate finding e2c3ee (stressors a-f).
        'url-with-commas-and-quotes.toon',          # (a) commas/quotes in URL
        'check-name-special-chars.toon',            # (b) special chars in name
        'multi-line-error-summary.toon',            # (c) multi-line | content
        'older-gh-envelope.toon',                   # (d) older gh format
        'huge-checks-block.toon',                   # (e) >50 rows
        'mixed-skipped-cancelled-neutral.toon',     # (f) SKIPPED+CANCELLED+NEUTRAL
        # Additional failure-mode regression fixture surfaced by (b).
        'failing-checks-with-colon-names.toon',
    }
    found = {f.name for f in _FIXTURE_DIR.iterdir() if f.is_file() and f.suffix == '.toon'}
    assert expected == found, f'Fixture directory out of sync. Missing: {expected - found}, Extra: {found - expected}'


def test_fixture_green_success_resolves_to_success(plan_context):
    """The exact regression case from PR #454 — green fixture must classify
    as ``wait_succeeded / ci_final_status: success``. This is the headline
    mis-classification the lesson identifies; if this test fails, the
    parse-and-extract pipeline is broken."""
    fixture = _FIXTURE_DIR / 'green-success.toon'
    plan_id = 'ci-fixture-green-success'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_succeeded', (
        f"green-success.toon expected wait_succeeded, got "
        f"{result['status']} (ci_final_status="
        f"{result.get('ci_final_status')!r}). This is the headline "
        f"regression from PR #454."
    )
    assert result['ci_final_status'] == 'success'


def test_fixture_single_check_success_resolves_to_success(plan_context):
    """Smallest non-empty checks table — minimum parser surface."""
    fixture = _FIXTURE_DIR / 'single-check-success.toon'
    plan_id = 'ci-fixture-single-check-success'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_succeeded'
    assert result['ci_final_status'] == 'success'


def test_fixture_many_checks_success_resolves_to_success(plan_context):
    """Larger checks table — exercises the parser at realistic counts."""
    fixture = _FIXTURE_DIR / 'many-checks-success.toon'
    plan_id = 'ci-fixture-many-checks-success'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_succeeded'
    assert result['ci_final_status'] == 'success'


def test_fixture_skipped_checks_resolves_to_success(plan_context):
    """Mix of pass + skipping rows — variant of green-success."""
    fixture = _FIXTURE_DIR / 'skipped-checks.toon'
    plan_id = 'ci-fixture-skipped-checks'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_succeeded'
    assert result['ci_final_status'] == 'success'


def test_fixture_failure_with_failing_checks_resolves_to_failure(plan_context):
    """One failing check — exercises failing_checks[] enumeration."""
    fixture = _FIXTURE_DIR / 'failure-with-failing-checks.toon'
    plan_id = 'ci-fixture-failure-with-failing-checks'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'failure'
    assert len(result.get('failing_checks') or []) == 1


def test_fixture_mixed_success_failure_resolves_to_failure(plan_context):
    """Multiple failing checks alongside passing — multi-row failing list."""
    fixture = _FIXTURE_DIR / 'mixed-success-failure.toon'
    plan_id = 'ci-fixture-mixed-success-failure'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'failure'
    assert len(result.get('failing_checks') or []) == 2


def test_fixture_pending_then_cancelled_resolves_to_failure(plan_context):
    """All checks cancelled (non-failure terminal) — classifies as failure
    per the resolver contract (only success/none distinguish)."""
    fixture = _FIXTURE_DIR / 'pending-then-cancelled.toon'
    plan_id = 'ci-fixture-pending-then-cancelled'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'failure'


def test_fixture_no_checks_resolves_to_no_checks(plan_context):
    """Empty checks[] (no CI configured) — distinct from real failure."""
    fixture = _FIXTURE_DIR / 'no-checks.toon'
    plan_id = 'ci-fixture-no-checks'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'no_checks'


def test_fixture_timeout_deadline_exceeded_resolves_to_timeout(plan_context):
    """True timeout (deadline_exceeded) — distinct from the false-timeout
    mis-classification the lesson identifies."""
    fixture = _FIXTURE_DIR / 'timeout-deadline-exceeded.toon'
    plan_id = 'ci-fixture-timeout-deadline-exceeded'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'timeout'
    assert result.get('wait_outcome') == 'deadline_exceeded'


# ---------------------------------------------------------------------------
# Stress fixtures — Q-Gate finding e2c3ee re-direction. The six stressor
# categories (a-f) called out by the user's review of the first-pass
# fixture set:
#
#   (a) URLs containing commas/quotes inside the tab-separated row
#   (b) Check names with embedded special chars (colon, brackets, slash,
#       parentheses, spaces, '=')
#   (c) Multi-line embedded content via the TOON `|` block marker
#   (d) Older `gh` CLI envelope shapes (empty url / run_id fields)
#   (e) Very large `checks[N]` blocks (>50 rows)
#   (f) SKIPPED + CANCELLED + NEUTRAL conclusion combinations
#
# (b) and the companion `failing-checks-with-colon-names` fixture surfaced
# a live bug: `parse_toon`'s `_parse_uniform_array` key/value detection
# heuristic at the prior `re.match(r'^[a-zA-Z_][\w_]*\s*:', content)` line
# treated tab-separated rows whose first column contained `:` (e.g.
# `lint:strict`, `coverage:enforce`) as a new key/value pair and broke
# out of the array — silently truncating downstream rows. TASK-004 fixed
# this by adding `\t not in content` to the heuristic; these tests pin
# the corrected behaviour.
# ---------------------------------------------------------------------------


def test_fixture_url_with_commas_and_quotes_resolves_to_success(plan_context):
    """Stressor (a): commas and quotes inside URL columns of a tab-separated
    row must not break parsing — the tab-mode splitter ignores commas."""
    fixture = _FIXTURE_DIR / 'url-with-commas-and-quotes.toon'
    plan_id = 'ci-fixture-url-commas-quotes'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_succeeded'
    assert result['ci_final_status'] == 'success'


def test_fixture_check_name_special_chars_preserves_all_rows():
    """Stressor (b): check names containing special characters — including
    the bug-trigger colon (`lint:strict`, `coverage = 95%`) — must NOT
    short-circuit the inline-table parse.

    Before the TASK-004 fix, the parser's key/value detection heuristic
    treated `lint:strict\\tcompleted\\t...` as a new key/value pair after
    `.strip()` left the colon at offset 4, breaking out of the array and
    silently truncating downstream rows. This test pins the fix by feeding
    the raw fixture through `parse_toon` directly and asserting the full
    row count is preserved.
    """
    fixture = _FIXTURE_DIR / 'check-name-special-chars.toon'
    raw = fixture.read_text()
    parsed = _parse_toon(raw)
    assert len(parsed.get('checks') or []) == 5, (
        f"Expected 5 checks rows, got {len(parsed.get('checks') or [])}. "
        'The parser truncated the array — most likely the key/value '
        "detection heuristic in `_parse_uniform_array` fired on a row "
        "whose first column legitimately contains ':' (e.g. 'lint:strict')."
    )
    # The bug-trigger row must be present with name verbatim.
    names = [c['name'] for c in parsed['checks']]
    assert 'lint:strict' in names, f'lint:strict row missing: {names!r}'
    assert 'coverage = 95%' in names, f'coverage row missing: {names!r}'


def test_fixture_check_name_special_chars_resolves_to_success(plan_context):
    """End-to-end: the special-chars fixture still resolves to wait_succeeded."""
    fixture = _FIXTURE_DIR / 'check-name-special-chars.toon'
    plan_id = 'ci-fixture-check-name-special-chars'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_succeeded'
    assert result['ci_final_status'] == 'success'


def test_fixture_multi_line_error_summary_resolves_to_timeout(plan_context):
    """Stressor (c): multi-line `|` content in a top-level envelope field
    must parse without breaking the trailing `checks[N]:` table or the
    top-level `status: error` classification."""
    fixture = _FIXTURE_DIR / 'multi-line-error-summary.toon'
    plan_id = 'ci-fixture-multi-line-error'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'timeout'
    assert result.get('wait_outcome') == 'deadline_exceeded'
    # The failing_checks list captures the still-pending checks at deadline.
    assert len(result.get('failing_checks') or []) == 2


def test_fixture_older_gh_envelope_resolves_to_success(plan_context):
    """Stressor (d): older `gh` envelope shapes with empty url and run_id
    fields must still parse and resolve to success when final_status is set."""
    fixture = _FIXTURE_DIR / 'older-gh-envelope.toon'
    plan_id = 'ci-fixture-older-gh'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_succeeded'
    assert result['ci_final_status'] == 'success'


def test_fixture_huge_checks_block_resolves_to_success(plan_context):
    """Stressor (e): a >50-row checks block must parse without performance
    cliff and resolve cleanly. The fixture carries exactly 55 rows."""
    fixture = _FIXTURE_DIR / 'huge-checks-block.toon'
    plan_id = 'ci-fixture-huge-checks-block'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_succeeded'
    assert result['ci_final_status'] == 'success'
    # Verify the parser captured every row — pin the structural completeness.
    raw = fixture.read_text()
    parsed = _parse_toon(raw)
    assert len(parsed['checks']) == 55, (
        f"Expected all 55 rows, got {len(parsed['checks'])}"
    )


def test_fixture_mixed_skipped_cancelled_neutral_resolves_to_failure(plan_context):
    """Stressor (f): a mix of pass + SKIPPED + CANCELLED + NEUTRAL + FAIL
    conclusions where `final_status: failure` MUST classify as wait_failed
    and forward the failing_checks list verbatim."""
    fixture = _FIXTURE_DIR / 'mixed-skipped-cancelled-neutral.toon'
    plan_id = 'ci-fixture-mixed-conclusions'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'failure'
    failing_names = [c['name'] for c in result.get('failing_checks') or []]
    assert set(failing_names) == {'test', 'lint', 'security-scan'}, (
        f'Failing-check enumeration drifted: {failing_names!r}'
    )


def test_fixture_failing_checks_with_colon_names_forwards_full_list(plan_context):
    """Companion regression for stressor (b): when a `failing_checks[N]:`
    inline-table block has rows whose first column contains `:` (e.g.
    `lint:strict`, `coverage:enforce`), the resolver MUST forward the full
    failing-check enumeration — not a truncated/empty list.

    Pre-fix observed: `failing_checks` came back as `[]` because the parser
    broke out of the array on the first colon-bearing row, silently
    losing both failure entries. Consumers that route on `failing_checks`
    (e.g. ci-verify consume-failures mode) would receive no signal about
    which checks actually failed.
    """
    fixture = _FIXTURE_DIR / 'failing-checks-with-colon-names.toon'
    plan_id = 'ci-fixture-failing-colon-names'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'failure'
    failing_names = [c['name'] for c in result.get('failing_checks') or []]
    assert failing_names == ['lint:strict', 'coverage:enforce'], (
        f'Expected [lint:strict, coverage:enforce], got {failing_names!r}. '
        "If this is an empty list, the parser regression has returned — "
        'the key/value detection heuristic in _parse_uniform_array fired '
        'on the colon-bearing first column and truncated the array.'
    )


# ---------------------------------------------------------------------------
# Direct parser regression guard — pins the heuristic-fix at the parser
# level, independent of the resolver / fixture layout. If a future change
# re-introduces the bug (e.g. by reverting the `\\t not in content`
# guard), this test fails fast with a clear diagnostic.
# ---------------------------------------------------------------------------


def test_parse_toon_inline_table_handles_colon_in_first_column():
    """`parse_toon` MUST treat a tab-separated row whose first column
    contains a colon (e.g. CI check names like `lint:strict`) as a data
    row, NOT as a key/value pair.

    The pre-fix heuristic at `_parse_uniform_array`:

        if re.match(r'^[a-zA-Z_][\\w_]*\\s*:', content) and not ...:
            break

    matched `lint:strict\\tcompleted\\t...` after `.strip()` (the `\\s*`
    matched zero whitespace before the colon) and broke out of the
    array. The fix added `'\\t' not in content` to the heuristic.
    """
    toon = (
        'rows[3]{name,status,result}:\n'
        '\tlint:strict\tcompleted\tpass\n'
        '\tcoverage:enforce\tcompleted\tfail\n'
        '\tbuild\tcompleted\tpass\n'
        'sentinel: present\n'
    )
    parsed = _parse_toon(toon)
    rows = parsed.get('rows') or []
    assert len(rows) == 3, (
        f'Parser truncated colon-bearing tab-separated rows: got '
        f'{len(rows)}/3 rows. Heuristic regression in '
        '`_parse_uniform_array` — see TASK-004 fix.'
    )
    assert [r['name'] for r in rows] == [
        'lint:strict',
        'coverage:enforce',
        'build',
    ]
    # The post-table sentinel key/value MUST still be picked up — the
    # array-exit condition must work for genuine top-level keys.
    assert parsed.get('sentinel') == 'present', (
        'The fix must not interfere with array-exit on genuine top-level '
        'key/value pairs that follow the array.'
    )


def test_parse_toon_inline_table_handles_colon_in_first_column_csv():
    """`parse_toon` MUST treat a comma-separated row whose first column
    contains BOTH a hyphen AND a colon (e.g. plan-retrospective
    `failures[N]{notation,exit_code}` rows like
    ``plan-marshall:foo:bar,1``) as data, NOT as a key/value pair.

    The post-`\\t-guard` regression: extending the identifier character
    class to ``[\\w_-]*`` so hyphenated TOON keys still terminate arrays
    inadvertently made the heuristic match ``plan-marshall:`` at the
    start of a CSV row. The lookahead ``(?=\\s|$)`` after the colon
    re-tightens the heuristic — a real TOON key/value pair always has
    whitespace (or EOL) after the colon, CSV first-column-with-colon
    never does.
    """
    toon = (
        'failures[1]{notation,exit_code}:\n'
        '  plan-marshall:foo:bar,1\n'
        'sentinel: present\n'
    )
    parsed = _parse_toon(toon)
    failures = parsed.get('failures') or []
    assert len(failures) == 1, (
        f'Parser truncated colon-bearing comma-separated row: got '
        f'{len(failures)}/1 rows. The `[\\w_-]*` identifier widening '
        'matched `plan-marshall:` at the start of the row and broke out '
        'of the array — the `(?=\\s|$)` lookahead must re-tighten the '
        'heuristic.'
    )
    assert failures[0]['notation'] == 'plan-marshall:foo:bar'
    assert int(failures[0]['exit_code']) == 1
    assert parsed.get('sentinel') == 'present', (
        'The fix must not interfere with array-exit on genuine top-level '
        'key/value pairs that follow the array.'
    )


# ---------------------------------------------------------------------------
# Helper-based executor resolution — the precondition helper resolves the
# executor proxy via file_ops.get_executor_path() (the uniform cwd rule,
# ADR-002) rather than parent-arithmetic on __file__. These tests pin that the
# resolved path is forwarded into the spawned subprocess argv, and that a
# resolver failure (RuntimeError) degrades the helper to its default.
# ---------------------------------------------------------------------------


def test_run_config_timeout_get_uses_resolved_executor(tmp_path, monkeypatch):
    """_run_run_config_timeout_get spawns the helper-resolved executor path."""
    executor = tmp_path / 'execute-script.py'
    captured = {}

    def fake_run(cmd, *args, **kwargs):
        captured['cmd'] = cmd

        class _Proc:
            returncode = 0
            stdout = 'timeout_seconds: 777\n'
            stderr = ''

        return _Proc()

    monkeypatch.setattr(_resolver_mod, 'get_executor_path', lambda: executor)
    monkeypatch.setattr(_resolver_mod.subprocess, 'run', fake_run)

    result = _resolver_mod._run_run_config_timeout_get(600)

    assert result == 777
    assert str(executor) in captured['cmd']


def test_run_config_timeout_get_degrades_when_executor_unresolvable(monkeypatch):
    """When get_executor_path raises (no resolvable plan root), the helper
    degrades to the default without spawning a subprocess."""
    run_called = {'hit': False}

    def _should_not_run(*args, **kwargs):
        run_called['hit'] = True
        raise AssertionError('subprocess.run must not be called when unresolvable')

    def _raise_resolver():
        raise RuntimeError('no .plan/local ancestor of cwd')

    monkeypatch.setattr(_resolver_mod, 'get_executor_path', _raise_resolver)
    monkeypatch.setattr(_resolver_mod.subprocess, 'run', _should_not_run)

    result = _resolver_mod._run_run_config_timeout_get(600)

    assert result == 600
    assert run_called['hit'] is False
