# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ``gh``-shaped world the merge-queue state and settle-wait tests run against.

``pr queue-state`` and ``pr wait-for-queue-settle`` are built on one observation
made of three provider reads: ``gh pr view``, the ``pullRequest`` GraphQL queue
read, and ``gh run list --event merge_group``. :class:`GhQueueStub` replaces the
lowest primitive all three reach — ``github_ops.run_gh`` — so the real
``view_pr_data``, ``run_graphql`` and ``list_merge_group_runs`` run unmodified and
every constructed argv is recorded for assertion.

The stub answers from a list of :class:`QueueWorld` snapshots. One snapshot serves
one whole observation; the ``pr view`` call that opens an observation advances to
the next snapshot, and the last snapshot repeats once the list is exhausted. A
settle-wait test therefore scripts "baseline, then poll 1, then poll 2" as a plain
list.

Neither test module ever shells out to the real ``gh``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import _github_pr
import github_ops

PR_NUMBER = 42
OWNER = 'octo'
REPO = 'repo'
MERGE_SHA = '0123456789abcdef0123456789abcdef01234567'

#: The exact argv ``view_pr_data`` builds for a PR-number selector.
PR_VIEW_ARGV = [
    'pr',
    'view',
    str(PR_NUMBER),
    '--json',
    'number,url,state,title,body,headRefName,baseRefName,isDraft,mergeable,mergeStateStatus,reviewDecision,mergeCommit',
]

#: The exact argv ``run_graphql`` builds for the PR's own queue read.
QUEUE_GRAPHQL_ARGV = [
    'api',
    'graphql',
    '-f',
    f'query={_github_pr.PULL_REQUEST_QUEUE_STATE_QUERY}',
    '-f',
    f'owner={OWNER}',
    '-f',
    f'repo={REPO}',
    '-F',
    f'number={PR_NUMBER}',
]

#: The exact argv ``list_merge_group_runs`` builds.
RUN_LIST_ARGV = [
    'run',
    'list',
    '--event',
    'merge_group',
    '--limit',
    str(github_ops.MERGE_GROUP_RUN_LIST_LIMIT),
    '--json',
    'databaseId,headBranch,status,conclusion,url,createdAt',
]


def merge_group_run(
    *,
    run_id: int,
    pr_number: int = PR_NUMBER,
    status: str = 'completed',
    conclusion: str | None = 'failure',
    created_at: str = '2026-01-01T00:00:00Z',
) -> dict:
    """One ``gh run list`` row for a merge-group run on the PR's temporary queue branch."""
    return {
        'databaseId': run_id,
        'headBranch': f'gh-readonly-queue/main/pr-{pr_number}-deadbeef',
        'status': status,
        'conclusion': conclusion,
        'url': f'https://github.com/{OWNER}/{REPO}/actions/runs/{run_id}',
        'createdAt': created_at,
    }


@dataclass
class QueueWorld:
    """What the three provider reads return during ONE observation.

    Attributes:
        state: ``gh pr view``'s ``state`` (``OPEN`` / ``MERGED`` / ``CLOSED``).
        merge_commit: The landing commit SHA, or ``None`` when the PR has none.
        view_fails: When true, ``gh pr view`` exits non-zero with ``view_stderr``.
        queue_entry: The ``mergeQueueEntry`` object, or ``None`` when unlisted.
        auto_merge: The ``autoMergeRequest`` object, or ``None`` when not armed.
        graphql_fails: When true, the queue GraphQL read exits non-zero.
        runs: The ``gh run list`` rows.
        run_list_fails: When true, ``gh run list`` exits non-zero.
    """

    state: str = 'OPEN'
    merge_commit: str | None = None
    view_fails: bool = False
    view_stderr: str = 'HTTP 502: Bad Gateway'
    queue_entry: dict | None = None
    auto_merge: dict | None = None
    graphql_fails: bool = False
    runs: list[dict] = field(default_factory=list)
    run_list_fails: bool = False


def queued_world(position: int = 1) -> QueueWorld:
    """An open PR listed in the merge queue with a merge-group run in progress."""
    return QueueWorld(
        queue_entry={'position': position, 'state': 'QUEUED'},
        runs=[merge_group_run(run_id=900, status='in_progress', conclusion=None)],
    )


class GhQueueStub:
    """``github_ops.run_gh`` stand-in answering from a list of :class:`QueueWorld`."""

    def __init__(self, worlds: list[QueueWorld]) -> None:
        assert worlds, 'a GhQueueStub needs at least one world'
        self._worlds = worlds
        self._observation = -1
        self.calls: list[list[str]] = []

    @property
    def _world(self) -> QueueWorld:
        return self._worlds[min(max(self._observation, 0), len(self._worlds) - 1)]

    def calls_starting(self, *prefix: str) -> list[list[str]]:
        """Every recorded argv that begins with ``prefix``."""
        return [call for call in self.calls if call[: len(prefix)] == list(prefix)]

    def __call__(self, args, capture_json=False, timeout=60):
        argv = list(args)
        self.calls.append(argv)
        if argv[:2] == ['auth', 'status']:
            return 0, '', ''
        if argv[:2] == ['repo', 'view']:
            return 0, json.dumps({'owner': {'login': OWNER}, 'name': REPO}), ''
        if argv[:2] == ['pr', 'view']:
            self._observation += 1
            world = self._world
            if world.view_fails:
                return 1, '', world.view_stderr
            merge_commit = {'oid': world.merge_commit} if world.merge_commit else None
            return 0, json.dumps({'number': PR_NUMBER, 'state': world.state, 'mergeCommit': merge_commit}), ''
        if argv[:2] == ['api', 'graphql']:
            world = self._world
            if world.graphql_fails:
                return 1, '', 'HTTP 502: Bad Gateway'
            pull_request = {'mergeQueueEntry': world.queue_entry, 'autoMergeRequest': world.auto_merge}
            return 0, json.dumps({'data': {'repository': {'pullRequest': pull_request}}}), ''
        if argv[:2] == ['run', 'list']:
            world = self._world
            if world.run_list_fails:
                return 1, '', 'HTTP 502: Bad Gateway'
            return 0, json.dumps(world.runs), ''
        return 1, '', f'unexpected gh invocation: {argv}'


def install_gh(monkeypatch, worlds: list[QueueWorld]) -> GhQueueStub:
    """Replace ``github_ops.run_gh`` with a :class:`GhQueueStub` and return it."""
    stub = GhQueueStub(worlds)
    monkeypatch.setattr(github_ops, 'run_gh', stub)
    return stub
