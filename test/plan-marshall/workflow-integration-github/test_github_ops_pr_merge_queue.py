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


def _branch_ns(branch: str) -> argparse.Namespace:
    return argparse.Namespace(branch=branch, remote_only=True)


def _capture_branch_delete_run_gh(returncode: int = 0, stderr: str = ''):
    """Minimal run_gh stub for cmd_branch_delete tests."""
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        return returncode, '', stderr

    return run_gh_stub, captured


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


def _merge_queue_ns(*, pr_number: int | None = 42, head: str | None = None):
    """Build the argparse.Namespace cmd_pr_merge_queue expects.

    Mirrors the post-fix argparse surface: ``merge-queue`` declares ONLY
    ``--pr-number`` / ``--head`` — no ``--strategy``, no ``--delete-branch`` —
    so the Namespace carries exactly those two attributes.
    """
    return argparse.Namespace(pr_number=pr_number, head=head)


def _queue_entries_data(*, number: int = 42, head_ref: str = 'feature/x') -> dict:
    """One complete ``mergeQueue.entries`` page listing a single PR, as ``run_graphql`` returns it."""
    return {
        'repository': {
            'mergeQueue': {
                'entries': {
                    'totalCount': 1,
                    'pageInfo': {'hasNextPage': False, 'endCursor': None},
                    'nodes': [{'position': 1, 'pullRequest': {'number': number, 'headRefName': head_ref}}],
                }
            }
        }
    }


def _install_configured_queue(monkeypatch) -> dict:
    """Stub the base-branch probe as CONFIGURED and the queue as listing the PR.

    ``cmd_pr_merge_queue`` refuses before calling gh unless the PR's own base
    branch has a configured queue (the pre-condition), and reports ``enqueued:
    true`` only when the post-enqueue ``mergeQueue.entries`` read lists the PR. The
    membership read is stubbed at ``run_graphql`` — not at ``run_gh`` — so the
    captured ``run_gh`` calls stay exactly the enqueue itself.
    """
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
    monkeypatch.setattr(github_ops, 'run_graphql', lambda query, variables: (0, _queue_entries_data(), ''))
    return _install_probe(
        monkeypatch,
        discriminator=github_ops.MERGE_QUEUE_ELIGIBLE_CONFIGURED,
        detail='merge_queue rule active on branch',
    )


@pytest.mark.parametrize(
    'raw',
    [
        '2026-01-01T00:00:00Z',  # GitHub's own Z-suffixed UTC
        '2026-01-01T00:00:00+00:00',  # explicit UTC offset
        '2026-01-01T02:00:00+02:00',  # non-UTC offset
        '2026-01-01T00:00:00',  # NAIVE — must be normalized, never returned naive
    ],
)
def test_parse_merged_at_always_returns_aware(raw):
    """A naive stamp is normalized to UTC rather than returned naive.

    A naive datetime raises ``TypeError`` the instant it is compared against an
    aware one, which would turn the corroboration check into a crash.
    """
    import _github_pr

    parsed = _github_pr._parse_merged_at(raw)

    assert parsed is not None, raw
    assert parsed.tzinfo is not None, raw
    assert parsed.utcoffset() is not None, raw
    # Comparable against an aware instant without raising — the property that matters.
    # Every fixture above is dated in the past, so the relation is DEFINITE rather
    # than a tautology: a parse that returned a naive or wrongly-offset value fails here.
    assert parsed < datetime.now(UTC), raw


def test_branch_delete_simple_branch_name_is_unchanged(monkeypatch):
    """Plain branch names (no reserved characters) pass through quote() as
    identity — nothing to encode, so the endpoint keeps its literal form.
    """
    _install_common(monkeypatch)
    run_gh_stub, captured = _capture_branch_delete_run_gh(returncode=0)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.cmd_branch_delete(_branch_ns('main'))

    assert result['status'] == 'success', result

    endpoint = captured[0][-1]
    assert endpoint == 'repos/octo/repo/git/refs/heads/main', endpoint


def test_pr_auto_merge_reports_enabled_disposition_when_base_unconfigured(monkeypatch):
    """No queue on the base branch → plain auto-merge → ``disposition: enabled``."""
    _install_common(monkeypatch)
    _install_merge_preconditions(monkeypatch)
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.cmd_pr_auto_merge(_auto_merge_ns())

    assert result['status'] == 'success', result
    assert result['operation'] == 'pr_auto_merge'
    assert result['disposition'] == 'enabled', result
    assert result['base_branch'] == 'main', result
    # The exit-code-derived key is REMOVED with no alias.
    assert 'enabled' not in result, result
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert '--auto' in merge_call, merge_call
    assert '--admin' not in merge_call, merge_call


def test_pr_auto_merge_reports_queue_disposition_when_base_configured(monkeypatch):
    """A configured queue on the base branch → the PR is ENQUEUED, not merely enabled.

    This is the regression the removed ``enabled: true`` could never express: the
    gh call succeeds identically in both cases, so only the base-branch probe can
    tell the two dispositions apart.
    """
    _install_common(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
    probe = _install_probe(
        monkeypatch,
        discriminator=github_ops.MERGE_QUEUE_ELIGIBLE_CONFIGURED,
        detail='merge_queue rule active on branch',
    )
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.cmd_pr_auto_merge(_auto_merge_ns())

    assert result['status'] == 'success', result
    assert result['disposition'] == 'enqueued', result
    assert result['disposition_detail'] == 'merge_queue rule active on branch', result
    assert 'enabled' not in result, result
    # The probe ran against the PR's OWN base branch, before the gh call.
    assert probe['branch'] == 'main', probe
    assert probe['calls'] == 1, probe


def test_stuck_state_gate_all_requirements_met(monkeypatch):
    """Approved + all checks SUCCESS + behind_by 0 → gate passes."""
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
                    'statusCheckRollup': [{'name': 'verify', 'conclusion': 'SUCCESS'}],
                    'mergeable': 'MERGEABLE',
                    'mergeStateStatus': 'BLOCKED',
                    'headRefOid': 'abc123',
                },
            ),
            compare=(0, {'behind_by': 0}),
        ),
    )

    ok, reason = github_ops._safe_merge_stuck_state_gate('42')

    assert ok is True, reason
    assert reason is None


def test_stuck_state_gate_failing_required_check(monkeypatch):
    """A non-SUCCESS required check fails the gate closed."""
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
                    'statusCheckRollup': [{'name': 'verify', 'conclusion': 'FAILURE'}],
                    'headRefOid': 'abc123',
                },
            ),
            compare=(0, {'behind_by': 0}),
        ),
    )

    ok, reason = github_ops._safe_merge_stuck_state_gate('42')

    assert ok is False
    assert 'verify' in reason and 'FAILURE' in reason


def test_stuck_state_gate_query_failure_fails_closed(monkeypatch):
    """A failed gate query fails closed rather than permitting the admin merge."""
    _install_common(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
    monkeypatch.setattr(
        github_ops,
        'run_gh',
        _gate_run_gh(view=(1, ''), compare=(0, {'behind_by': 0})),
    )

    ok, reason = github_ops._safe_merge_stuck_state_gate('42')

    assert ok is False
    assert 'gate query failed' in reason


def test_stuck_state_gate_non_list_rollup_fails_closed(monkeypatch):
    """A statusCheckRollup that is not a list fails closed."""
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
                    'statusCheckRollup': {'not': 'a list'},
                    'headRefOid': 'abc123',
                },
            ),
            compare=(0, {'behind_by': 0}),
        ),
    )

    ok, reason = github_ops._safe_merge_stuck_state_gate('42')

    assert ok is False
    assert 'not a list' in reason


def test_pr_merge_queue_enqueues_auto_only(monkeypatch):
    """The enqueue command is exactly ``['pr', 'merge', <id>, '--auto']``.

    No ``--strategy`` and no ``--delete-branch`` are forwarded, and the return
    envelope omits the removed ``strategy`` / ``delete_branch`` keys.
    """
    _install_common(monkeypatch)
    _install_configured_queue(monkeypatch)
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.cmd_pr_merge_queue(_merge_queue_ns(pr_number=42))

    assert result['status'] == 'success', result
    assert result['operation'] == 'pr_merge_queue'
    assert result['enqueued'] is True
    assert result['base_branch'] == 'main', result
    assert result['queue_precondition'] == 'merge_queue rule active on branch', result
    assert result['enqueue_observation'].startswith('mergeQueue(branch: main).entries lists the PR'), result
    assert 'enqueue_corroboration' not in result, result
    assert result['pr_number'] == 42
    # The removed keys must NOT reappear in the envelope.
    assert 'strategy' not in result, result
    assert 'delete_branch' not in result, result

    # Exactly one gh call, and it is exactly ``pr merge <id> --auto``.
    assert len(captured) == 1, captured
    merge_call = captured[0]
    assert merge_call == ['pr', 'merge', '42', '--auto'], merge_call
    assert '--delete-branch' not in merge_call, merge_call
    assert '--strategy' not in merge_call, merge_call
    # None of the strategy method flags leak either.
    for method_flag in ('--merge', '--squash', '--rebase'):
        assert method_flag not in merge_call, merge_call


def test_pr_merge_queue_never_sends_flag_gh_would_reject(monkeypatch):
    """Fixture mirrors the real ``gh`` rejection: ``--delete-branch`` with a
    merge queue enabled fails with "Cannot use --delete-branch when merge queue
    enabled". The handler never sends the flag, so the enqueue succeeds.
    """
    _install_common(monkeypatch)
    _install_configured_queue(monkeypatch)
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        # Mirror the real gh rejection shape: reject if --delete-branch (or an
        # explicit strategy flag) ever reaches the merge-queue enqueue call.
        if '--delete-branch' in args:
            return 1, '', 'Cannot use --delete-branch when merge queue enabled'
        for method_flag in ('--merge', '--squash', '--rebase'):
            if method_flag in args:
                return 1, '', f'unexpected strategy flag {method_flag} on merge-queue enqueue'
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.cmd_pr_merge_queue(_merge_queue_ns(pr_number=42))

    # Because the flags are never sent, the rejection never fires.
    assert result['status'] == 'success', result
    assert result['enqueued'] is True
    merge_call = captured[0]
    assert merge_call == ['pr', 'merge', '42', '--auto'], merge_call


def test_pr_merge_queue_head_identifier(monkeypatch):
    """A ``--head`` identifier still enqueues via ``pr merge <branch> --auto``."""
    _install_common(monkeypatch)
    _install_configured_queue(monkeypatch)
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.cmd_pr_merge_queue(_merge_queue_ns(pr_number=None, head='feature/x'))

    assert result['status'] == 'success', result
    assert result['enqueued'] is True
    merge_call = captured[0]
    assert merge_call == ['pr', 'merge', 'feature/x', '--auto'], merge_call
    assert '--delete-branch' not in merge_call, merge_call
    assert '--strategy' not in merge_call, merge_call


@pytest.mark.parametrize(
    'discriminator',
    [
        github_ops.MERGE_QUEUE_ELIGIBLE_UNCONFIGURED,
        github_ops.MERGE_QUEUE_INELIGIBLE,
        github_ops.MERGE_QUEUE_UNSUPPORTED,
    ],
)
def test_cmd_pr_merge_queue_returns_error_when_base_has_no_configured_queue(monkeypatch, discriminator):
    """No configured queue on the base branch → error, and NO gh call at all.

    This is the defect the corroboration closes: ``gh pr merge --auto`` exits
    zero on an unconfigured base having quietly enabled PLAIN auto-merge, so the
    old exit-code-derived ``enqueued: true`` reported a successful enqueue for a
    PR that never joined any queue. The probe runs BEFORE the call so that
    side effect never happens either.
    """
    _install_common(monkeypatch)
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda head=None: _pr_view_success_payload())
    probe = _install_probe(monkeypatch, discriminator=discriminator, detail='no merge_queue rule on branch')
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    result = github_ops.cmd_pr_merge_queue(_merge_queue_ns(pr_number=42))

    assert result['status'] == 'error', result
    assert result['operation'] == 'pr_merge_queue'
    # The message names the base branch and BOTH remedies.
    assert 'main' in result['error'], result
    assert '/marshall-steward' in result['error'], result
    assert 'use_merge_queue' in result['error'], result
    assert 'ci pr safe-merge' in result['error'], result
    # No gh call was issued — the probe precedes the enqueue.
    assert captured == [], captured
    # The refusal is derived from exactly ONE probe, not from a retry loop that
    # happened to settle on an error: the base-branch state is read once and acted on.
    assert probe['calls'] == 1, probe


def _pr_state_data(*, entry: dict | None = None, auto_merge: dict | None = None) -> dict:
    """The PR's own ``pullRequest`` queue state, as ``run_graphql`` returns it."""
    return {
        'repository': {
            'pullRequest': {'state': 'OPEN', 'autoMergeRequest': auto_merge, 'mergeQueueEntry': entry},
        }
    }


def _install_unlisted_queue(monkeypatch, pr_state) -> list[dict]:
    """Configured queue whose complete entry list does NOT carry PR 42; the PR-state read answers ``pr_state``.

    ``pr_state`` is the ``(returncode, data, err)`` triple the PR-state query returns.
    Returns the captured variables of every PR-state read.
    """
    _install_configured_queue(monkeypatch)
    pr_reads: list[dict] = []

    def run_graphql_stub(query, variables):
        if 'mergeQueue(branch' in query:
            return 0, _queue_entries_data(number=7, head_ref='feature/other'), ''
        pr_reads.append(dict(variables))
        return pr_state

    monkeypatch.setattr(github_ops, 'run_graphql', run_graphql_stub)
    monkeypatch.setattr(github_ops, 'run_gh', lambda args, capture_json=False, timeout=60: (0, '', ''))
    return pr_reads


@pytest.mark.parametrize(
    ('pr_state', 'enqueued', 'reason', 'observation_tail'),
    [
        (
            (0, _pr_state_data(entry={'position': 2, 'state': 'AWAITING_CHECKS'}), ''),
            True,
            None,
            'mergeQueueEntry lists the PR at position 2 (state AWAITING_CHECKS)',
        ),
        (
            (0, _pr_state_data(auto_merge={'enabledAt': '2026-01-01T00:00:00Z'}), ''),
            'indeterminate',
            'auto_merge_armed_awaiting_checks',
            'carries an autoMergeRequest and no mergeQueueEntry',
        ),
        (
            (0, _pr_state_data(), ''),
            'indeterminate',
            'pr_not_listed',
            'carries neither a mergeQueueEntry nor an autoMergeRequest',
        ),
        ((1, None, 'graphql error'), 'indeterminate', 'pr_not_listed', 'read failed: graphql error'),
        ((0, {'repository': {}}, ''), 'indeterminate', 'pr_not_listed', 'read returned no repository.pullRequest'),
    ],
    ids=['queue-entry-observed', 'auto-merge-armed', 'neither', 'pr-read-failed', 'pr-read-malformed'],
)
def test_an_unlisted_pr_is_classified_by_its_own_queue_state(monkeypatch, pr_state, enqueued, reason, observation_tail):
    """A PR absent from the entry list is read by number; only an entry there is a membership.

    An armed auto-merge is never ``enqueued: true``, and a failed PR read keeps
    ``pr_not_listed`` rather than guessing either way.
    """
    _install_common(monkeypatch)
    pr_reads = _install_unlisted_queue(monkeypatch, pr_state)

    result = github_ops.cmd_pr_merge_queue(_merge_queue_ns(pr_number=42))

    assert result['status'] == 'success', result
    assert result['enqueued'] == enqueued, result
    assert result.get('enqueue_unobserved_reason') == reason, result
    assert result['enqueue_observation'].startswith('mergeQueue(branch: main).entries read to its end'), result
    assert result['enqueue_observation'].endswith(observation_tail), result
    assert [read['number'] for read in pr_reads] == [42], pr_reads


def test_an_unlisted_pr_under_head_is_read_by_the_number_pr_view_resolves(monkeypatch):
    """The ``--head`` path selects the PR-state read by the number ``pr view`` returns for the branch."""
    _install_common(monkeypatch)
    pr_reads = _install_unlisted_queue(
        monkeypatch, (0, _pr_state_data(auto_merge={'enabledAt': '2026-01-01T00:00:00Z'}), '')
    )

    result = github_ops.cmd_pr_merge_queue(_merge_queue_ns(pr_number=None, head='feature/x'))

    assert result['enqueued'] == 'indeterminate', result
    assert result['enqueue_unobserved_reason'] == 'auto_merge_armed_awaiting_checks', result
    assert [read['number'] for read in pr_reads] == [42], pr_reads


def test_cmd_pr_merge_queue_probe_error_fails_closed(monkeypatch):
    """An unresolvable queue state refuses the enqueue rather than guessing."""
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

    result = github_ops.cmd_pr_merge_queue(_merge_queue_ns(pr_number=42))

    assert result['status'] == 'error', result
    assert 'scope' in result['error'], result
    assert captured == [], captured
