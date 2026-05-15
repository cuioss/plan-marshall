#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Unit tests for the phase-6-finalize CI-completion precondition resolver.

The helper at ``scripts/_ci_complete_precondition.py`` is the dispatcher-side
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
import sys
from pathlib import Path

from conftest import PlanContext  # type: ignore[import-not-found]

# ---------------------------------------------------------------------------
# Module loading — private underscore-prefixed helpers are not registered
# in the executor mapping, so we import via importlib from the source path.
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
    '_ci_complete_precondition',
    '_ci_complete_precondition.py',
)
resolve = _resolver_mod.resolve
DEFAULT_CI_WAIT_TIMEOUT_SECONDS = _resolver_mod.DEFAULT_CI_WAIT_TIMEOUT_SECONDS
_cache_path = _resolver_mod._cache_path
_read_cache = _resolver_mod._read_cache


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
