# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for cmd_pr_merge branch-delete refactor.

After the refactor:
* ``cmd_pr_merge`` MUST NOT pass ``--delete-branch`` to ``gh pr merge``.
* When the caller requests ``--delete-branch``, the merge is performed first
  and (on success) the PR head branch is deleted remotely via
  ``cmd_branch_delete`` (REST ``DELETE /git/refs/heads/{branch}``).
* No local git state (checkout, ``git branch -D``) may be touched by this
  handler — that is the caller's responsibility.

The worktree fork exercises the scenario ``gh pr merge --delete-branch``
cannot serve: the merge must finish cleanly and the branch delete must
round-trip purely through the REST leaf, never through local git.
"""

import argparse
import json
from datetime import UTC, datetime

import github_ops
import pytest
from _ci_wait_contract import _ok_auth


def _install_common(monkeypatch):
    """Install auth + owner/repo stubs used by every scenario.

    Tests override ``run_gh`` explicitly below; this helper only installs the
    pieces that are orthogonal to the merge/delete wiring.
    """
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(
        github_ops,
        'get_repo_info',
        lambda: ('octo', 'repo'),
    )


def _install_probe(
    monkeypatch,
    *,
    discriminator: str | None = None,
    detail: str = 'no merge_queue rule on branch',
    error: str | None = None,
    merge_method: str | None = None,
) -> dict:
    """Stub ``github_ops._probe_merge_queue_state`` for the safe-merge preflight.

    Returns a capture dict recording the ``(owner, repo, branch)`` the probe was
    called with plus a call count, so tests can assert base-branch specificity.
    The four-tuple return shape ``(discriminator, detail, error, merge_method)``
    mirrors the production ``_probe_merge_queue_state`` signature exactly, so a
    green fixture cannot diverge from the production data shape. By
    default the probe reports ``eligible_unconfigured`` with ``merge_method=None``
    so the preflight proceeds to the normal merge path unchanged.
    """
    if discriminator is None:
        discriminator = github_ops.MERGE_QUEUE_ELIGIBLE_UNCONFIGURED
    captured: dict = {'owner': None, 'repo': None, 'branch': None, 'calls': 0}

    def probe_stub(owner, repo, branch):
        captured['owner'] = owner
        captured['repo'] = repo
        captured['branch'] = branch
        captured['calls'] += 1
        return discriminator, detail, error, merge_method

    monkeypatch.setattr(github_ops, '_probe_merge_queue_state', probe_stub)
    return captured


def _pr_view_success_payload() -> dict:
    """Minimal ``view_pr_data`` success payload with a head branch."""
    return {
        'status': 'success',
        'operation': 'pr_view',
        'pr_number': 42,
        'pr_url': 'https://github.com/octo/repo/pull/42',
        'state': 'open',
        'title': 'T',
        'head_branch': 'feature/x',
        'base_branch': 'main',
        'is_draft': 'false',
        'mergeable': 'mergeable',
        'merge_state': 'clean',
    }


_CORROBORATION_PAYLOADS: dict[str, dict] = {
    # Landed merge — the only shape that corroborates.
    'merged': {
        'state': 'MERGED',
        'mergedAt': '2026-01-01T00:00:00Z',
        'baseRefName': 'main',
        'headRefOid': 'abc123',
    },
    # The closed-unmerged signature: the merge command reports success but
    # GitHub closed the PR without merging it.
    'closed': {
        'state': 'CLOSED',
        'mergedAt': None,
        'baseRefName': 'main',
        'headRefOid': 'abc123',
    },
    # The merge silently did nothing and the PR is still open.
    'open': {
        'state': 'OPEN',
        'mergedAt': None,
        'baseRefName': 'main',
        'headRefOid': 'abc123',
    },
    # A wrongly-shaped record: the key EXISTS but carries no usable instant. A
    # narrow presence check would pass here; the value-meaning assertion must not.
    'merged_without_timestamp': {
        'state': 'MERGED',
        'mergedAt': None,
        'baseRefName': 'main',
        'headRefOid': 'abc123',
    },
}


def _install_merge_preconditions(monkeypatch, *, view_payload: dict | None = None) -> dict:
    """Install the stubs ``cmd_pr_merge``'s own guards require.

    ``cmd_pr_merge`` now runs the shared base-branch merge-queue preflight before
    merging, so every direct ``cmd_pr_merge`` test needs BOTH the probe stub and
    a ``view_pr_data`` that resolves a base branch — otherwise the test would be
    exercising the preflight's fail-closed path rather than the merge wiring it
    means to assert. Returns the probe capture dict.
    """
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: view_payload or _pr_view_success_payload())
    return _install_probe(monkeypatch)


def _merge_ns(*, delete_branch: bool, pr_number: int | None = 42, head: str | None = None):
    return argparse.Namespace(
        pr_number=pr_number,
        head=head,
        strategy='merge',
        delete_branch=delete_branch,
    )


def _auto_merge_ns(*, pr_number: int | None = 42, head: str | None = None, strategy: str = 'squash'):
    return argparse.Namespace(pr_number=pr_number, head=head, strategy=strategy)


def _gate_run_gh(*, view, compare):
    """run_gh stub dispatching the gate's two query shapes.

    ``view`` / ``compare`` are ``(returncode, json_obj_or_str)`` tuples for the
    ``gh pr view --json ...`` and ``gh api .../compare/...`` calls respectively.
    """

    def _payload(obj):
        return obj if isinstance(obj, str) else json.dumps(obj)

    def run_gh_stub(args, capture_json=False, timeout=60):
        if args[:2] == ['pr', 'view']:
            rc, obj = view
            return rc, _payload(obj), '' if rc == 0 else 'view failed'
        if args[:1] == ['api']:
            rc, obj = compare
            return rc, _payload(obj), '' if rc == 0 else 'compare failed'
        return 0, '', ''

    return run_gh_stub


def test_pr_merge_squash_rejects_ancestry_only_evidence(monkeypatch):
    """A squash merge is NOT corroborated by base-contains-head ancestry.

    A squash rewrites the branch into a new commit, so the head SHA never becomes
    an ancestor of the base — admitting ancestry there would corroborate a merge
    that did not happen. The strategy therefore selects the admissible evidence.
    """
    _install_common(monkeypatch)
    _install_merge_preconditions(monkeypatch)
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        if args[:2] == ['pr', 'merge']:
            return 0, '', ''
        if args[:2] == ['pr', 'view']:
            return 0, json.dumps(_CORROBORATION_PAYLOADS['open']), ''
        # An ancestry probe would hit the compare endpoint and report containment.
        if args[:1] == ['api']:
            return 0, json.dumps({'status': 'behind'}), ''
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = _merge_ns(delete_branch=False)
    ns.strategy = 'squash'
    result = github_ops.cmd_pr_merge(ns)

    assert result['status'] == 'error', result
    # The compare endpoint was never consulted — ancestry is not admissible here.
    compare_calls = [c for c in captured if c[:1] == ['api']]
    assert compare_calls == [], compare_calls


def test_pr_merge_rebase_accepts_ancestry_evidence(monkeypatch):
    """A rebase merge IS corroborated by base-contains-head ancestry.

    ``rebase`` and ``merge`` land the head commits on the base verbatim, so
    ancestry is positive evidence even when the PR record has not yet flipped.
    """
    _install_common(monkeypatch)
    _install_merge_preconditions(monkeypatch)

    def run_gh_stub(args, capture_json=False, timeout=60):
        if args[:2] == ['pr', 'merge']:
            return 0, '', ''
        if args[:2] == ['pr', 'view']:
            return 0, json.dumps(_CORROBORATION_PAYLOADS['open']), ''
        if args[:1] == ['api']:
            return 0, json.dumps({'status': 'behind'}), ''
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = _merge_ns(delete_branch=False)
    ns.strategy = 'rebase'
    result = github_ops.cmd_pr_merge(ns)

    assert result['status'] == 'success', result
    assert result['merged'] is True, result
    assert 'contains head' in result['merge_corroboration'], result


@pytest.mark.parametrize('compare_status', ['ahead', 'diverged', 'identical'])
def test_pr_merge_ancestry_arm_reads_compare_status(monkeypatch, compare_status):
    """The ancestry arm asserts the compare STATUS value, not the response's shape.

    ``identical`` and ``behind`` mean the base contains the head; ``ahead`` and
    ``diverged`` mean it does not. A presence-only check on the compare payload
    would corroborate all four.
    """
    _install_common(monkeypatch)
    _install_merge_preconditions(monkeypatch)

    def run_gh_stub(args, capture_json=False, timeout=60):
        if args[:2] == ['pr', 'merge']:
            return 0, '', ''
        if args[:2] == ['pr', 'view']:
            return 0, json.dumps(_CORROBORATION_PAYLOADS['open']), ''
        if args[:1] == ['api']:
            return 0, json.dumps({'status': compare_status}), ''
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = _merge_ns(delete_branch=False)
    ns.strategy = 'merge'
    result = github_ops.cmd_pr_merge(ns)

    if compare_status == 'identical':
        assert result['status'] == 'success', result
        assert result['merged'] is True, result
    else:
        assert result['status'] == 'error', result


def test_pr_auto_merge_probe_error_fails_closed(monkeypatch):
    """An unresolvable queue state is an error, never a guessed disposition."""
    _install_common(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
    _install_probe(
        monkeypatch,
        discriminator=github_ops.MERGE_QUEUE_INELIGIBLE,
        detail='branch rules endpoint unreachable',
        error='the gh token lacks the scope to read repository rulesets',
    )
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.cmd_pr_auto_merge(_auto_merge_ns())

    assert result['status'] == 'error', result
    assert 'scope' in result['error'], result
    # The probe precedes the call, so no auto-merge was scheduled as a side effect.
    assert captured == [], captured


def test_stuck_state_gate_review_not_approved(monkeypatch):
    """A non-approved review decision fails the gate closed."""
    _install_common(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
    monkeypatch.setattr(
        github_ops,
        'run_gh',
        _gate_run_gh(
            view=(
                0,
                {
                    'reviewDecision': 'REVIEW_REQUIRED',
                    'statusCheckRollup': [{'name': 'verify', 'conclusion': 'SUCCESS'}],
                    'headRefOid': 'abc123',
                },
            ),
            compare=(0, {'behind_by': 0}),
        ),
    )

    ok, reason = github_ops._safe_merge_stuck_state_gate('42')

    assert ok is False
    assert 'not approved' in reason


def test_stuck_state_gate_check_not_concluded(monkeypatch):
    """An in-progress (no-conclusion) required check fails the gate closed."""
    _install_common(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
    monkeypatch.setattr(
        github_ops,
        'run_gh',
        _gate_run_gh(
            view=(
                0,
                {
                    'reviewDecision': 'APPROVED',
                    'statusCheckRollup': [{'name': 'verify', 'status': 'IN_PROGRESS'}],
                    'headRefOid': 'abc123',
                },
            ),
            compare=(0, {'behind_by': 0}),
        ),
    )

    ok, reason = github_ops._safe_merge_stuck_state_gate('42')

    assert ok is False
    assert 'has not concluded' in reason


def test_stuck_state_gate_unparseable_json_fails_closed(monkeypatch):
    """Unparseable gate-query JSON fails closed."""
    _install_common(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
    monkeypatch.setattr(
        github_ops,
        'run_gh',
        _gate_run_gh(view=(0, 'not-json{'), compare=(0, {'behind_by': 0})),
    )

    ok, reason = github_ops._safe_merge_stuck_state_gate('42')

    assert ok is False
    assert 'could not be parsed' in reason


def test_behind_by_zero_compare_missing_field_fails_closed(monkeypatch):
    """A compare response missing behind_by fails closed."""
    _install_common(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
    monkeypatch.setattr(
        github_ops,
        'run_gh',
        _gate_run_gh(view=(0, {'behind_by': None}), compare=(0, {})),
    )

    ok, reason = github_ops._safe_merge_behind_by_zero('42', 'abc123')

    assert ok is False
    assert 'missing behind_by' in reason
