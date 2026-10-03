# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``pr queue-state`` — the single-read merge-queue state verb.

The verb reports where a PR is relative to the merge queue from one observation:
the PR's own state, its queue membership, whether auto-merge is armed, and its
newest merge-group workflow run. Three of those fields are tri-state — a read
that could not be completed reports ``indeterminate``, never ``False`` — and the
verb is an error only when the PR itself could not be read.

Every test drives the real handler down to ``github_ops.run_gh``, the lowest
subprocess primitive, and asserts the argv constructed there.
"""

import argparse

import _github_pr
import github_ops
import pytest
from _pr_queue_fixtures import (
    MERGE_SHA,
    PR_NUMBER,
    PR_VIEW_ARGV,
    QUEUE_GRAPHQL_ARGV,
    RUN_LIST_ARGV,
    QueueWorld,
    install_gh,
    merge_group_run,
    queued_world,
)


def _args() -> argparse.Namespace:
    return argparse.Namespace(pr_number=PR_NUMBER)


def _queue_state(monkeypatch, world: QueueWorld):
    stub = install_gh(monkeypatch, [world])
    return github_ops.cmd_pr_queue_state(_args()), stub


# =============================================================================
# Constructed argv at the run_gh primitive
# =============================================================================


def test_queue_state_constructs_the_three_provider_reads(monkeypatch):
    """One observation is exactly one pr view, one queue GraphQL read and one run list."""
    _, stub = _queue_state(monkeypatch, queued_world())

    assert stub.calls_starting('pr', 'view') == [PR_VIEW_ARGV]
    assert stub.calls_starting('api', 'graphql') == [QUEUE_GRAPHQL_ARGV]
    assert stub.calls_starting('run', 'list') == [RUN_LIST_ARGV]


def test_queue_state_passes_the_pr_number_as_a_typed_graphql_variable(monkeypatch):
    """The PR number travels as ``-F`` (typed Int), the owner and repo as ``-f`` strings."""
    _, stub = _queue_state(monkeypatch, queued_world())

    (graphql_argv,) = stub.calls_starting('api', 'graphql')
    assert graphql_argv[-2:] == ['-F', f'number={PR_NUMBER}']
    assert graphql_argv[4:8] == ['-f', 'owner=octo', '-f', 'repo=repo']


# =============================================================================
# PR in the queue / out of the queue
# =============================================================================


def test_queue_state_reports_a_queued_pr(monkeypatch):
    result, _ = _queue_state(monkeypatch, queued_world(position=3))

    assert result['status'] == 'success'
    assert result['operation'] == 'pr_queue_state'
    assert result['pr_number'] == PR_NUMBER
    assert result['pr_state'] == 'open'
    assert result['merge_commit_sha'] is None
    assert result['in_queue'] is True
    assert result['queue_position'] == 3
    assert result['queue_entry_state'] == 'QUEUED'
    assert result['auto_merge_armed'] is False
    assert result['merge_group_run'] == {
        'found': True,
        'run_id': 900,
        'status': 'in_progress',
        'conclusion': None,
        'url': 'https://github.com/octo/repo/actions/runs/900',
    }


def test_queue_state_reports_a_dequeued_pr_with_its_failed_merge_group_run(monkeypatch):
    world = QueueWorld(runs=[merge_group_run(run_id=901, conclusion='failure')])

    result, _ = _queue_state(monkeypatch, world)

    assert result['status'] == 'success'
    assert result['pr_state'] == 'open'
    assert result['in_queue'] is False
    assert result['queue_position'] is None
    assert result['queue_entry_state'] is None
    assert result['auto_merge_armed'] is False
    assert result['merge_group_run']['found'] is True
    assert result['merge_group_run']['run_id'] == 901
    assert result['merge_group_run']['status'] == 'completed'
    assert result['merge_group_run']['conclusion'] == 'failure'


def test_queue_state_reports_armed_auto_merge(monkeypatch):
    world = QueueWorld(auto_merge={'enabledAt': '2026-01-01T00:00:00Z'})

    result, _ = _queue_state(monkeypatch, world)

    assert result['status'] == 'success'
    assert result['in_queue'] is False
    assert result['auto_merge_armed'] is True


def test_queue_state_reports_a_merged_pr_with_its_landing_commit(monkeypatch):
    world = QueueWorld(state='MERGED', merge_commit=MERGE_SHA)

    result, _ = _queue_state(monkeypatch, world)

    assert result['status'] == 'success'
    assert result['pr_state'] == 'merged'
    assert result['merge_commit_sha'] == MERGE_SHA
    assert result['in_queue'] is False


def test_queue_state_reports_a_closed_pr_without_a_landing_commit(monkeypatch):
    world = QueueWorld(state='CLOSED')

    result, _ = _queue_state(monkeypatch, world)

    assert result['status'] == 'success'
    assert result['pr_state'] == 'closed'
    assert result['merge_commit_sha'] is None


# =============================================================================
# The newest merge-group run for THIS PR
# =============================================================================


def test_queue_state_selects_the_newest_run_of_this_pr(monkeypatch):
    """An older run of the PR, and a run of a PR whose number merely shares a prefix, are not it."""
    world = QueueWorld(
        runs=[
            merge_group_run(run_id=910, conclusion='success', created_at='2026-01-01T00:00:00Z'),
            merge_group_run(run_id=912, conclusion='failure', created_at='2026-01-03T00:00:00Z'),
            merge_group_run(run_id=911, conclusion='cancelled', created_at='2026-01-02T00:00:00Z'),
            merge_group_run(
                run_id=999, pr_number=PR_NUMBER * 10, conclusion='success', created_at='2026-01-09T00:00:00Z'
            ),
        ]
    )

    result, _ = _queue_state(monkeypatch, world)

    assert result['merge_group_run']['run_id'] == 912
    assert result['merge_group_run']['conclusion'] == 'failure'


def test_queue_state_reports_no_merge_group_run_when_the_list_was_read_to_its_end(monkeypatch):
    world = QueueWorld(runs=[merge_group_run(run_id=920, pr_number=7)])

    result, _ = _queue_state(monkeypatch, world)

    assert result['status'] == 'success'
    assert result['merge_group_run'] == {
        'found': False,
        'run_id': None,
        'status': None,
        'conclusion': None,
        'url': None,
    }


def test_queue_state_reports_run_indeterminate_when_the_list_reached_its_bound(monkeypatch):
    """A full listing with no match may have an older run behind it — its absence is not established."""
    limit = github_ops.MERGE_GROUP_RUN_LIST_LIMIT
    world = QueueWorld(runs=[merge_group_run(run_id=1000 + n, pr_number=7) for n in range(limit)])

    result, _ = _queue_state(monkeypatch, world)

    assert result['status'] == 'success'
    assert result['merge_group_run']['found'] == _github_pr.QUEUE_READ_INDETERMINATE
    assert result['merge_group_run']['found'] is not False


def test_queue_state_reports_run_indeterminate_when_the_run_list_read_fails(monkeypatch):
    world = QueueWorld(run_list_fails=True)

    result, _ = _queue_state(monkeypatch, world)

    assert result['status'] == 'success'
    assert result['pr_state'] == 'open'
    assert result['merge_group_run']['found'] == _github_pr.QUEUE_READ_INDETERMINATE


# =============================================================================
# A failed queue read is indeterminate, never "not in the queue"
# =============================================================================


def test_queue_state_reports_indeterminate_when_the_graphql_queue_read_fails(monkeypatch):
    world = QueueWorld(graphql_fails=True, runs=[merge_group_run(run_id=930, conclusion='failure')])

    result, _ = _queue_state(monkeypatch, world)

    assert result['status'] == 'success'
    assert result['pr_state'] == 'open'
    assert result['in_queue'] == _github_pr.QUEUE_READ_INDETERMINATE
    assert result['in_queue'] is not False
    assert result['auto_merge_armed'] == _github_pr.QUEUE_READ_INDETERMINATE
    assert result['auto_merge_armed'] is not False
    assert result['queue_position'] is None
    assert 'read failed' in result['observation']


# =============================================================================
# The PR itself could not be read
# =============================================================================


def test_queue_state_returns_pr_read_failed_when_pr_view_fails(monkeypatch):
    world = QueueWorld(view_fails=True, view_stderr='HTTP 502: Bad Gateway')

    result, stub = _queue_state(monkeypatch, world)

    assert result['status'] == 'error'
    assert result['operation'] == 'pr_queue_state'
    assert result['error'] == _github_pr.PR_READ_FAILED
    assert result['pr_number'] == PR_NUMBER
    assert result['context'] == 'HTTP 502: Bad Gateway'
    assert 'pr_state' not in result
    assert 'in_queue' not in result
    # Nothing past the failed PR read was attempted.
    assert stub.calls_starting('api', 'graphql') == []
    assert stub.calls_starting('run', 'list') == []


def test_queue_state_returns_pr_read_failed_for_a_state_outside_the_closed_set(monkeypatch):
    world = QueueWorld(state='LOCKED')

    result, _ = _queue_state(monkeypatch, world)

    assert result['status'] == 'error'
    assert result['error'] == _github_pr.PR_READ_FAILED
    assert 'locked' in result['message']


@pytest.mark.parametrize(
    ('verb', 'handler_name'),
    [
        ('queue-state', 'cmd_pr_queue_state'),
        ('wait-for-queue-settle', 'cmd_pr_wait_for_queue_settle'),
    ],
)
def test_queue_verbs_are_exported_from_the_ops_module(verb, handler_name):
    """Both handlers are reachable on ``github_ops``, where ``main()`` builds its dispatch table.

    The export is asserted by the handler's defining module and name rather than by
    object identity: the scripts directory can be imported as more than one module
    instance in one test session, so ``github_ops``'s ``_github_pr`` and this
    module's ``_github_pr`` are not guaranteed to be the same object. What the
    export contract fixes is that ``github_ops`` re-exports the handler DEFINED in
    ``_github_pr`` under its own name — not a same-named redefinition of it.
    """
    handler = getattr(github_ops, handler_name)

    assert callable(handler), verb
    assert handler.__name__ == handler_name
    assert handler.__qualname__ == handler_name
    assert handler.__module__.rpartition('.')[2] == '_github_pr'
    assert callable(getattr(_github_pr, handler_name))
