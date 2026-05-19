#!/usr/bin/env python3
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
import subprocess
import sys
from pathlib import Path

from conftest import PlanContext  # type: ignore[import-not-found]

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


_SHA_A = 'a' * 40
_SHA_B = 'b' * 40
_PR = 123
_WORKTREE = '/nonexistent/worktree/path'  # Never read — git stub overrides.


# ---------------------------------------------------------------------------
# Test 1 — cache miss → ci wait succeeds → cache populated → second call
# returns ``satisfied`` without re-polling.
# ---------------------------------------------------------------------------


def test_cache_miss_then_hit_does_not_repoll():
    plan_id = 'ci-precond-cache-miss-then-hit'
    with PlanContext(plan_id=plan_id):
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


def test_head_advance_invalidates_cache():
    plan_id = 'ci-precond-head-advance'
    with PlanContext(plan_id=plan_id):
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


def test_ci_failure_returns_wait_failed_without_caching():
    plan_id = 'ci-precond-ci-failure'
    with PlanContext(plan_id=plan_id):
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


def test_ci_timeout_returns_wait_failed_with_timeout_reason():
    plan_id = 'ci-precond-timeout'
    with PlanContext(plan_id=plan_id):
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
        assert result['head_sha'] == _SHA_A
        assert result['ci_final_status'] == 'timeout', (
            'Timeout envelope must surface ci_final_status=timeout so the '
            'dispatcher can include the reason in the consumer step display'
        )
        cache_path = _cache_path(plan_id)
        assert not cache_path.exists(), (
            'Timeout outcomes must not be cached; re-entry must re-poll'
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
    # the future.
    assert 'usage: ci_complete_precondition.py' in completed.stdout, (
        f'Argparse usage banner missing from stdout: {completed.stdout!r}'
    )
    assert 'resolve' in completed.stdout, (
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


def test_failure_forwards_failing_checks_list():
    """A ``ci wait`` envelope with ``failing_checks`` MUST forward the list
    verbatim through the resolver return so the dispatcher can name the
    failing checks in the consumer step's display_detail and emit the
    structured triage finding documented in deliverable 5.
    """
    plan_id = 'ci-precond-failing-checks'
    with PlanContext(plan_id=plan_id):
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


def test_no_checks_returns_distinct_ci_final_status():
    """``final_status: none`` from ``ci wait`` MUST surface as
    ``ci_final_status: no_checks`` so the dispatcher can distinguish
    "CI never ran" from a real failure and route to the
    ``ci-verify-missing`` producer (deliverable 6).
    """
    plan_id = 'ci-precond-no-checks'
    with PlanContext(plan_id=plan_id):
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


def test_timeout_forwards_wait_outcome_deadline_exceeded():
    """A wait-deadline exhaustion MUST forward
    ``wait_outcome: deadline_exceeded`` and the still-running checks so the
    dispatcher routes to the ``ci-verify-timeout`` producer.
    """
    plan_id = 'ci-precond-timeout-forward'
    with PlanContext(plan_id=plan_id):
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
        )

        assert result['status'] == 'wait_failed'
        assert result['ci_final_status'] == 'timeout'
        assert result['wait_outcome'] == 'deadline_exceeded'
        assert [c['name'] for c in result['failing_checks']] == ['slow-deploy']


def test_satisfied_does_not_carry_failing_checks_field():
    """``satisfied`` (cache hit) MUST NOT include the failing_checks /
    wait_outcome fields — they are wait_failed-only signals. Deliverable 5
    specifies "satisfied and wait_succeeded outcomes produce no finding";
    the absence of the fields is the structural complement.
    """
    plan_id = 'ci-precond-satisfied-no-failing-checks'
    with PlanContext(plan_id=plan_id):
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


def test_wait_succeeded_does_not_carry_failing_checks_field():
    """``wait_succeeded`` (fresh poll succeeded) MUST NOT include
    failing_checks / wait_outcome — same rationale as satisfied above.
    """
    plan_id = 'ci-precond-wait-succeeded-no-failing-checks'
    with PlanContext(plan_id=plan_id):
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
