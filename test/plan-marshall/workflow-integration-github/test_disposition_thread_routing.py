#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-cutting suite: every thread-bearing disposition reaches its own thread.

Fail-first suite for D5. Against the pre-fix code ``cmd_post_responses``
discriminated on the presence of an extractable ``thread_id`` rather than on the
finding's thread-BEARING-ness, so an inline comment whose thread_id was missing
silently fell through into the batched PR-level comment — reported as delivered
while the reviewer's own thread stayed unanswered and unresolved. Every assertion
below about an inline finding landing in ``untransmitted[]`` was red.

Cross-cutting counterpart to ``test_comments_stage.py``'s ``TestPostResponses``,
which pins the per-disposition unit behaviour one finding at a time. This suite
drives a MIXED finding set through one ``post_responses`` run and pins the routing
as a whole:

* every thread-bearing finding is transmitted in its OWN thread, keyed by its own
  ``thread_id`` — never positionally, never collapsed;
* only genuinely threadless kinds appear in the batched body;
* an undeliverable in-thread reply lands in ``untransmitted[]`` with
  ``status: partial``, never in the batch.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from conftest import get_script_path, load_script_module

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-github', 'github_pr.py')

# Resolved by (bundle, skill, file), which is what keeps this distinct from the
# gitlab sibling despite the two scripts sharing a role.
github_pr = load_script_module('plan-marshall', 'workflow-integration-github', 'github_pr.py')

cmd_fetch_findings = github_pr.cmd_fetch_findings
cmd_post_responses = github_pr.cmd_post_responses

# The publish-shape vocabulary, split by whether the provider gives it a thread.
THREAD_BEARING_KINDS = ('inline',)
THREADLESS_KINDS = ('review_body', 'issue_comment')


class _Args:
    """The minimal argv shape both verbs read."""

    required_bots = ''
    optional_bots = ''

    def __init__(self, plan_id: str, pr_number: int = 700) -> None:
        self.plan_id = plan_id
        self.pr_number = pr_number


#: The commit every staged ``fixed`` finding is stamped with. A ``fixed`` reply is
#: held until its fix commit is stamped and reaches the pull request head, and this
#: suite is about where a transmitted reply GOES, so every finding is released.
_FIX_COMMIT = 'a1b2c3d4e5f60718293a4b5c6d7e8f9012345678'


@pytest.fixture(autouse=True)
def _stub_provider():
    """Keep the producer off the network; tests re-patch inside their own blocks.

    ``run_gh`` answers the provider's compare read with ``ahead``: the stamped fix
    commit reaches the pull request head, so the hold-back releases every reply.
    It is the same seam ``test_comments_stage_post.py`` drives.
    """
    with (
        patch('github_pr._github.check_auth', return_value=(True, '')),
        patch('github_pr._github.fetch_pr_head_sha', return_value='stub-head-sha'),
        patch('github_pr._github.run_gh', return_value=(0, 'ahead\n', '')),
    ):
        yield


def _stage(plan_id: str, comments: list[dict]) -> dict:
    """File one pr-comment finding per comment; return comment_id -> hash_id."""
    with patch('github_pr._github.fetch_pr_comments_data') as mock_fetch:
        mock_fetch.return_value = {
            'status': 'success',
            'provider': 'github',
            'comments': comments,
            'total': len(comments),
            'unresolved': len(comments),
        }
        result = cmd_fetch_findings(_Args(plan_id))

    assert result['status'] == 'success', result
    assert result['count_stored'] == len(comments), result

    from _findings_core import query_findings

    stored = query_findings(plan_id, finding_type='pr-comment')['findings']
    mapping: dict[str, str] = {}
    for finding in stored:
        for line in (finding.get('detail') or '').splitlines():
            if line.startswith('comment_id:'):
                mapping[line.split(':', 1)[1].strip()] = finding['hash_id']
    assert len(mapping) == len(comments), mapping
    return mapping


def _comment(comment_id: str, kind: str, thread_id: str) -> dict:
    """One substantive comment of the given kind, with the given thread anchor."""
    return {
        'id': comment_id,
        'kind': kind,
        'author': 'reviewer',
        'body': f'A substantive concern about null handling in {comment_id}.',
        'path': 'src/Main.java' if kind == 'inline' else '',
        'line': 42 if kind == 'inline' else 0,
        'thread_id': thread_id,
    }


def _resolve_all(plan_id: str, mapping: dict[str, str]) -> None:
    """Give every staged finding a ``fixed`` disposition whose reply is released.

    Each finding is resolved ``fixed`` and then stamped with its fix commit through
    the store's own writer, so it reaches the transmit path the routing assertions
    are about. Without the stamp ``post_responses`` would hold every one of them and
    no test below would observe any routing at all.
    """
    from _findings_core import resolve_finding, stamp_fix_commit

    for comment_id, hash_id in mapping.items():
        outcome = resolve_finding(plan_id, hash_id, 'fixed', detail=f'Addressed {comment_id}.')
        assert outcome['status'] == 'success', outcome
        stamped = stamp_fix_commit(plan_id, _FIX_COMMIT, hash_id=hash_id)
        assert stamped['hash_ids'] == [hash_id], stamped


class TestMixedFindingSetRouting:
    """One run over a mixed set: each disposition takes the path its kind dictates."""

    @pytest.fixture
    def mixed(self, plan_context):
        """Two thread-bearing findings with real threads, plus both threadless kinds."""
        plan_id = 'dtr-mixed'
        plan_context.plan_dir_for(plan_id)
        comments = [
            _comment('I1', 'inline', 'PRRT_i1'),
            _comment('I2', 'inline', 'PRRT_i2'),
            _comment('RB', 'review_body', ''),
            _comment('IC', 'issue_comment', ''),
        ]
        mapping = _stage(plan_id, comments)
        _resolve_all(plan_id, mapping)
        return plan_id, mapping

    def test_every_thread_bearing_finding_replies_in_its_own_thread(self, mixed):
        """Each inline disposition is keyed by ITS OWN thread_id — never positionally.

        The relational keying is the property: two inline findings must produce
        two distinct thread targets, so a disposition can never be delivered into
        the wrong reviewer's thread.
        """
        plan_id, mapping = mixed
        calls = []

        def _graphql(mutation, variables):
            calls.append(variables)
            return 0, {}, ''

        with (
            patch('github_pr._github.run_graphql', side_effect=_graphql),
            patch(
                'github_pr._github.post_pr_comment',
                return_value={'status': 'success', 'operation': 'post_pr_comment'},
            ),
        ):
            result = cmd_post_responses(_Args(plan_id))

        assert result['status'] == 'success'
        threaded = [r for r in result['responded'] if r['transmit_mode'] == 'thread_reply']
        assert {r['thread_id'] for r in threaded} == {'PRRT_i1', 'PRRT_i2'}
        assert {r['hash_id'] for r in threaded} == {mapping['I1'], mapping['I2']}
        # Each thread got a reply AND a resolve — two mutations per thread.
        assert sorted(v['threadId'] for v in calls) == [
            'PRRT_i1',
            'PRRT_i1',
            'PRRT_i2',
            'PRRT_i2',
        ]
        # Every threaded disposition is truthfully reported as resolved on the provider.
        assert all(r['resolved_on_provider'] is True for r in threaded)

    def test_only_threadless_kinds_appear_in_the_batched_body(self, mixed):
        """The batch carries the threadless anchors and NOTHING thread-bearing.

        Asserted in both directions against one body, so a batch that quietly
        absorbed an inline finding cannot pass on the positive half alone.
        """
        plan_id, _mapping = mixed
        posted = []

        def _post(pr_number, body):
            posted.append(body)
            return {'status': 'success', 'operation': 'post_pr_comment', 'pr_number': pr_number}

        with (
            patch('github_pr._github.run_graphql', return_value=(0, {}, '')),
            patch('github_pr._github.post_pr_comment', side_effect=_post),
        ):
            result = cmd_post_responses(_Args(plan_id))

        assert len(posted) == 1, 'the threadless dispositions go out as ONE batched comment'
        body = posted[0]
        # Present: both genuinely threadless anchors.
        assert 'RB' in body
        assert 'IC' in body
        # Absent: neither thread-bearing anchor may leak into the batch.
        assert 'I1' not in body
        assert 'I2' not in body

        batched = [r for r in result['responded'] if r['transmit_mode'] == 'batched_issue_comment']
        assert {r['comment_id'] for r in batched} == {'RB', 'IC'}
        # An issue comment has no resolvable thread — reporting True would be a lie.
        assert all(r['resolved_on_provider'] is False for r in batched)

    def test_the_whole_mixed_set_is_transmitted_with_nothing_dropped(self, mixed):
        """Totality: every staged disposition is accounted for on exactly one list."""
        plan_id, mapping = mixed

        with (
            patch('github_pr._github.run_graphql', return_value=(0, {}, '')),
            patch(
                'github_pr._github.post_pr_comment',
                return_value={'status': 'success', 'operation': 'post_pr_comment'},
            ),
        ):
            result = cmd_post_responses(_Args(plan_id))

        accounted = (
            [r['hash_id'] for r in result['responded']]
            + [r['hash_id'] for r in result['skipped']]
            + [r['hash_id'] for r in result['untransmitted']]
            + [r['hash_id'] for r in result['deferred_until_commit']]
        )
        assert sorted(accounted) == sorted(mapping.values())
        assert len(accounted) == len(set(accounted)), 'no disposition is reported twice'
        # Every finding here is stamped, so none is held: the whole set is transmitted.
        assert result['deferred_until_commit'] == []
        assert len(result['responded']) == len(mapping)


class TestHeldFindingsTakeNoRoute:
    """⛔ MATCHED CONTROL for the suite's stamped helper.

    The same mixed set, resolved ``fixed`` and NOT stamped, is routed nowhere: no
    thread mutation, no batched comment, and every finding on the deferred list. This
    is what shows the routing assertions above depend on the stamp and are not
    passing over findings the hold would have stopped.
    """

    def test_an_unstamped_mixed_set_is_held_whole(self, plan_context):
        from _findings_core import resolve_finding

        plan_id = 'dtr-mixed-unstamped'
        plan_context.plan_dir_for(plan_id)
        mapping = _stage(
            plan_id,
            [
                _comment('I1', 'inline', 'PRRT_i1'),
                _comment('RB', 'review_body', ''),
                _comment('IC', 'issue_comment', ''),
            ],
        )
        for comment_id, hash_id in mapping.items():
            resolve_finding(plan_id, hash_id, 'fixed', detail=f'Addressed {comment_id}.')

        with (
            patch('github_pr._github.run_graphql', return_value=(0, {}, '')) as mock_graphql,
            patch('github_pr._github.post_pr_comment') as mock_post,
        ):
            result = cmd_post_responses(_Args(plan_id))

        mock_graphql.assert_not_called()
        mock_post.assert_not_called()
        assert result['status'] == 'success'
        assert result['responded'] == []
        assert result['untransmitted'] == []
        assert sorted(r['hash_id'] for r in result['deferred_until_commit']) == sorted(mapping.values())
        assert {r['reason'] for r in result['deferred_until_commit']} == {'no_fix_commit'}


class TestUndeliverableInThreadReplyIsNeverBatched:
    """A thread-bearing finding that cannot reach its thread is untransmitted."""

    def test_missing_thread_id_lands_in_untransmitted_not_the_batch(self, plan_context):
        """An inline comment ALWAYS has a provider thread — a missing id is a defect.

        This is the case that regressed: routing on thread_id presence made a
        missing id look like threadlessness, so the disposition was batched and
        reported delivered while the reviewer's thread stayed open.
        """
        plan_id = 'dtr-missing-thread'
        plan_context.plan_dir_for(plan_id)
        mapping = _stage(
            plan_id,
            [
                _comment('I1', 'inline', ''),  # thread-bearing kind, NO thread id
                _comment('RB', 'review_body', ''),  # genuinely threadless
            ],
        )
        _resolve_all(plan_id, mapping)

        posted = []

        def _post(pr_number, body):
            posted.append(body)
            return {'status': 'success', 'operation': 'post_pr_comment', 'pr_number': pr_number}

        with (
            patch('github_pr._github.run_graphql', return_value=(0, {}, '')),
            patch('github_pr._github.post_pr_comment', side_effect=_post),
        ):
            result = cmd_post_responses(_Args(plan_id))

        assert result['status'] == 'partial'
        assert result['count_untransmitted'] == 1
        assert result['untransmitted'][0]['hash_id'] == mapping['I1']
        # The batch still went out for the genuinely threadless finding...
        assert len(posted) == 1
        assert 'RB' in posted[0]
        # ...but the undeliverable inline disposition is NOT in it.
        assert 'I1' not in posted[0]

    def test_failed_thread_reply_lands_in_untransmitted_not_the_batch(self, plan_context):
        """The batch is not a fallback channel when the reply mutation fails."""
        plan_id = 'dtr-reply-fails'
        plan_context.plan_dir_for(plan_id)
        mapping = _stage(plan_id, [_comment('I1', 'inline', 'PRRT_boom')])
        _resolve_all(plan_id, mapping)

        with (
            patch('github_pr._github.run_graphql', return_value=(1, {}, 'thread not found')),
            patch('github_pr._github.post_pr_comment') as mock_post,
        ):
            result = cmd_post_responses(_Args(plan_id))

        assert result['status'] == 'partial'
        assert result['count_untransmitted'] == 1
        assert 'thread-reply failed' in result['untransmitted'][0]['reason']
        mock_post.assert_not_called()

    def test_an_undeliverable_reply_does_not_suppress_its_siblings(self, plan_context):
        """One undeliverable disposition never costs the deliverable ones.

        ``status: partial`` reports the mixed outcome truthfully: the reachable
        threads are still answered, and only the undeliverable one is listed.
        """
        plan_id = 'dtr-partial-mixed'
        plan_context.plan_dir_for(plan_id)
        mapping = _stage(
            plan_id,
            [
                _comment('I1', 'inline', ''),  # undeliverable
                _comment('I2', 'inline', 'PRRT_i2'),  # deliverable
                _comment('IC', 'issue_comment', ''),  # batched
            ],
        )
        _resolve_all(plan_id, mapping)

        with (
            patch('github_pr._github.run_graphql', return_value=(0, {}, '')),
            patch(
                'github_pr._github.post_pr_comment',
                return_value={'status': 'success', 'operation': 'post_pr_comment'},
            ),
        ):
            result = cmd_post_responses(_Args(plan_id))

        assert result['status'] == 'partial'
        assert [r['hash_id'] for r in result['untransmitted']] == [mapping['I1']]
        delivered = {r['hash_id']: r['transmit_mode'] for r in result['responded']}
        assert delivered[mapping['I2']] == 'thread_reply'
        assert delivered[mapping['IC']] == 'batched_issue_comment'

    @pytest.mark.parametrize('kind', THREADLESS_KINDS)
    def test_a_genuinely_threadless_kind_is_never_untransmitted_for_a_missing_thread(self, kind, plan_context):
        """The complement: absence of a thread is EXPECTED for these kinds.

        Pairs with the missing-thread test above so the discriminator under test is
        the finding's KIND, not the empty thread_id both cases share.
        """
        plan_id = f'dtr-threadless-{kind.replace("_", "-")}'
        plan_context.plan_dir_for(plan_id)
        mapping = _stage(plan_id, [_comment('T1', kind, '')])
        _resolve_all(plan_id, mapping)

        with (
            patch('github_pr._github.run_graphql', return_value=(0, {}, '')) as mock_graphql,
            patch(
                'github_pr._github.post_pr_comment',
                return_value={'status': 'success', 'operation': 'post_pr_comment'},
            ),
        ):
            result = cmd_post_responses(_Args(plan_id))

        assert result['status'] == 'success'
        assert result['count_untransmitted'] == 0
        assert result['responded'][0]['transmit_mode'] == 'batched_issue_comment'
        mock_graphql.assert_not_called()

    @pytest.mark.parametrize('kind', THREAD_BEARING_KINDS)
    def test_a_thread_bearing_kind_without_a_thread_is_always_untransmitted(self, kind, plan_context):
        """Swept over the thread-bearing vocabulary rather than pinned to one kind."""
        plan_id = f'dtr-bearing-{kind}'
        plan_context.plan_dir_for(plan_id)
        mapping = _stage(plan_id, [_comment('T1', kind, '')])
        _resolve_all(plan_id, mapping)

        with (
            patch('github_pr._github.run_graphql', return_value=(0, {}, '')),
            patch('github_pr._github.post_pr_comment') as mock_post,
        ):
            result = cmd_post_responses(_Args(plan_id))

        assert result['status'] == 'partial'
        assert result['untransmitted'][0]['hash_id'] == mapping['T1']
        mock_post.assert_not_called()
