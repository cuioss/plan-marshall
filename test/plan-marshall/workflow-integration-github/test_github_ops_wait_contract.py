"""GitHub-specific coverage for the ci/issue wait surface of github_ops.py.

The provider-agnostic poll-handler contract — dispatch-table registration, the
auth short-circuit, and the flip/timeout/``--expected`` matrix for the three
wait-for-* handlers — lives in ``_ci_wait_contract`` and is bound into this
module below, so it executes once for GitHub. What remains here is genuinely
GitHub-specific:

    - the ``gh``-shaped stub wiring (``run_gh`` / ``_RunGhStub``)
    - the ``gh run view --log-failed`` failure-path download + filter wiring,
      driven against the committed ``ci-logs/github/fail.log`` fixture
    - the p50-seeded first sleep and the ``gh run watch`` terminal-state tail,
      whose seams live in ``_github_ci``

Tests never shell out to the real ``gh`` CLI: every fetch helper and the auth
check are monkeypatched, and ``time.sleep`` is neutralised so timeout branches
run in constant time.
"""
import argparse

import _github_ci
import github_ops
import pytest
from _ci_wait_contract import (
    CI_LOG_FIXTURE_ROOT,
    CONTRACT_TESTS,
    _make_incrementing_clock,
    _noop_sleep,
    _ok_auth,
    _resolve_plan_relative,
    test_ci_wait_for_status_flip_auth_failure_short_circuits,
    test_ci_wait_for_status_flip_completes_on_flip,
    test_ci_wait_for_status_flip_expected_any_accepts_failure,
    test_ci_wait_for_status_flip_expected_any_accepts_success,
    test_ci_wait_for_status_flip_expected_success_rejects_failure,
    test_ci_wait_for_status_flip_times_out_when_status_never_changes,
    test_dispatch_ci_wait_for_status_flip_registered,
    test_dispatch_issue_wait_for_close_registered,
    test_dispatch_issue_wait_for_label_registered,
    test_issue_wait_for_close_auth_failure_short_circuits,
    test_issue_wait_for_close_completes_on_flip,
    test_issue_wait_for_close_times_out_when_state_never_changes,
    test_issue_wait_for_label_absent_completes_when_label_disappears,
    test_issue_wait_for_label_auth_failure_short_circuits,
    test_issue_wait_for_label_present_completes_when_label_appears,
    test_issue_wait_for_label_times_out_when_label_state_never_changes,
)

_GITHUB_FAIL_LOG = CI_LOG_FIXTURE_ROOT / 'github' / 'fail.log'
@pytest.fixture
def ci_ops():
    """Feed the provider-agnostic contract this module's provider ops module."""
    return github_ops


def test_contract_surface_is_bound_for_github():
    """Every provider-agnostic contract test is bound in this module.

    Guards the "the contract runs once per provider" invariant: a contract test
    added to ``_ci_wait_contract`` but never imported here would otherwise be
    silently uncollected for GitHub.
    """
    missing = [name for name in CONTRACT_TESTS if name not in globals()]
    assert missing == [], missing
