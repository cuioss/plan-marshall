# SPDX-License-Identifier: FSL-1.1-ALv2
"""``github_pr.cmd_fetch_findings``: the workflow-identity-keyed pre-filter stages.

The self-response stage recognises this workflow's own batched ``post_responses``
comment by WHO wrote it — the workflow identity, read through
``_github_pr.get_viewer_login`` — with a transmission shape REQUIRED beside it:

- workflow identity + opening heading      -> self-response, not filed
- workflow identity + section signature,
  no heading                               -> emitter bypass, not filed, reported
- workflow identity + neither shape        -> a genuine operator comment, filed
- any other author + heading               -> filed; another author's comment is never ours
- identity unreadable                      -> heading-only fallback, disclosed

The own-trigger stage excludes a re-review trigger this workflow posted by
PROVENANCE — workflow identity AND a stripped body equal to a registered trigger —
counting it apart from noise and recording which trigger it matched. An
exact-trigger body from anyone else keeps its noise disposition, and a comment that
merely quotes a trigger is filed.

The fetch's own coverage reaches the result: ``fetch_complete`` is True only when
the provider proved every connection read to its end, and ``capped_connections``
names each connection that was not. The capped and complete cases drive the REAL
provider parse path (``github_ops.fetch_pr_comments_data``) through a stubbed
``run_graphql``, so the pass-through is exercised end to end.

The shared noise layer reads only the commenter's OWN bare prose — fenced blocks,
blockquoted lines and ``<details>`` blocks are removed first — and drops a comment
only when a whole-comment acknowledgment pattern covers all of that prose within the
derived length bound. A phrase quoted in a block, or an AI-agent block riding
beside a genuine finding, never makes the comment an acknowledgment.

A recognised refusal never reaches ``actionable_count``: that count is derived
downstream from the stored ``pr-comment`` findings, so a Sourcery weekly-quota notice
and a Sourcery size-ceiling notice must each file NO finding, count in
``count_skipped_refusal`` and name the bot in ``refused_bots``. An unclassified
Sourcery ``review_body`` is the matched positive control — it is still stored, so the
fail-closed counted default stays in force.

A zero-stored fetch names which zero it is: ``stored_zero_state`` is ``no_coverage``
(no bot credited), ``covered_clean`` (a bot credited, nothing survived the filters)
or ``unreachable`` (an incomplete fetch, an unreadable merge candidate, or any
refusal), and ``unreachable`` outranks the other two — so a quota refusal riding in
an otherwise clean pass never reads as reviewed-and-clean.

``pr merge-queue`` reports ``enqueued: true`` only on an observed read of the PR's
own queue membership (``mergeQueue.entries``, paginated to its end); a failed read,
an incomplete list, or a complete list without the PR is ``indeterminate`` with its
reason — never ``true`` on an accepted enqueue call alone.

The findings store is REAL (isolated via the autouse ``plan_context``
``PLAN_BASE_DIR`` sandbox); only the GitHub provider surface and the identity read
are monkeypatched, and the raw ``run_gh`` seam is stubbed to fail so no case can
shell out to a real ``gh``.
"""

import argparse
import sys

import pytest

from conftest import load_script_module

PLAN_IDS: tuple[str, ...] = (
    'gh-pr-fetch-capped',
    'gh-pr-fetch-complete',
    'gh-pr-fetch-unclaimed',
    'gh-pr-identity-bypass',
    'gh-pr-identity-bypass-report',
    'gh-pr-identity-foreign-heading',
    'gh-pr-identity-foreign-quote',
    'gh-pr-identity-not-needed',
    'gh-pr-identity-plain',
    'gh-pr-identity-self',
    'gh-pr-identity-unresolved',
    'gh-pr-noise-ai-agent-block',
    'gh-pr-noise-blockquote-e2e',
    'gh-pr-noise-courtesy-opener',
    'gh-pr-own-trigger-bot-quote',
    'gh-pr-own-trigger-excluded',
    'gh-pr-own-trigger-foreign-exact',
    'gh-pr-own-trigger-unresolved',
    'gh-pr-refusal-pin-size-ceiling',
    'gh-pr-refusal-pin-unclassified-control',
    'gh-pr-refusal-pin-weekly-quota',
    'gh-pr-zero-state-covered-clean',
    'gh-pr-zero-state-no-coverage',
    'gh-pr-zero-state-precedence-head',
    'gh-pr-zero-state-precedence-incomplete',
    'gh-pr-zero-state-precedence-refusal',
    'gh-pr-zero-state-stored',
    'gh-pr-zero-state-unreachable-quota',
)
github_pr = load_script_module('plan-marshall', 'workflow-integration-github', 'github_pr.py', 'github_pr')
# The PR-handler module ``github_pr`` itself imports from — reused from sys.modules,
# so the merge-queue cases patch the same ``github_ops`` object the handler reads.
_github_pr = sys.modules['_github_pr']
_findings_core = load_script_module('plan-marshall', 'manage-findings', '_findings_core.py', '_findings_core')
query_findings = _findings_core.query_findings
query_qgate_findings = _findings_core.query_qgate_findings

#: The account ``post_responses`` posts under in these cases.
WORKFLOW_LOGIN = 'repo-owner'

#: A genuine reviewer — anyone who is not the workflow identity.
OTHER_AUTHOR = 'alice'


def _batched_body(comment_id='c1', reply='Fixed in the follow-up commit; the guard now covers the None case.'):
    """A real batched body, rendered by the production emitter."""
    return github_pr._build_batched_response_body([(comment_id, reply)])


def _bypass_body():
    """The batched structure with its opening heading replaced — the observed bypass shape.

    Derived from the production emitter so the section signature is exactly the one
    ``post_responses`` renders; only the heading differs.
    """
    return _batched_body().replace(github_pr._SELF_RESPONSE_HEADING, '## Non-goals (restored)', 1)


def _comment(comment_id, author, body):
    return {
        'id': comment_id,
        'author': author,
        'thread_id': '',
        'kind': 'issue_comment',
        'body': body,
        'resolved': False,
    }


def _patch_provider(monkeypatch, comments, login=WORKFLOW_LOGIN, *, complete=None, head_sha='deadbeef'):
    """Stub the provider surface and the workflow identity read.

    ``login=None`` simulates an unreadable identity. ``complete`` is the provider's
    completeness claim: ``None`` omits it (the result then reads as not complete),
    ``True`` claims every connection was read to its end with none capped.
    ``head_sha=''`` simulates a failed merge-candidate read. Returns the list the
    identity stub appends to on every call, so a case can assert whether it was read
    at all.
    """
    provider_result = {
        'status': 'success',
        'provider': 'github',
        'comments': list(comments),
        'total': len(comments),
        'unresolved': len(comments),
    }
    if complete is not None:
        provider_result['complete'] = complete
        provider_result['connections'] = []
    identity_reads: list[int] = []

    def _viewer_login():
        identity_reads.append(1)
        if login is None:
            return None, 'viewer read failed'
        return login, ''

    monkeypatch.setattr(github_pr, 'get_viewer_login', _viewer_login)
    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_pr._github, 'fetch_pr_head_committed_at', lambda pr_number: '')
    monkeypatch.setattr(github_pr._github, 'fetch_pr_head_sha', lambda pr_number: head_sha)
    monkeypatch.setattr(
        github_pr._github,
        'fetch_pr_comments_data',
        lambda pr_number, unresolved_only=False: dict(provider_result),
    )
    monkeypatch.setattr(github_pr._github, 'run_gh', lambda *_a, **_k: (1, '', 'run_gh is stubbed in this module'))
    return identity_reads


def _run_fetch(plan_id, pr_number=301):
    return github_pr.cmd_fetch_findings(argparse.Namespace(pr_number=pr_number, plan_id=plan_id))


def _stored_comment_ids(plan_id):
    ids = []
    for finding in query_findings(plan_id, finding_type='pr-comment')['findings']:
        for line in (finding.get('detail') or '').splitlines():
            if line.startswith('comment_id:'):
                ids.append(line.split(':', 1)[1].strip())
    return ids


def test_workflow_authored_bypass_body_is_not_filed_as_a_finding(plan_context, monkeypatch):
    """A workflow-authored body opening ``## Non-goals (restored)`` with the batch signature.

    Fail-first case: under the heading-only filter this body did not open with the
    heading, so it was filed as a review finding. Keyed on identity it is our own
    output and files nothing.
    """
    plan_id = 'gh-pr-identity-bypass'
    _patch_provider(monkeypatch, [_comment('mine-1', WORKFLOW_LOGIN, _bypass_body())])

    result = _run_fetch(plan_id)

    assert result['status'] == 'success'
    assert result['count_stored'] == 0
    assert _stored_comment_ids(plan_id) == []
    assert result['producer_mismatch_hash_id'] is None


def test_emitter_bypass_is_counted_and_reported_as_a_qgate_finding(plan_context, monkeypatch):
    """The bypass is REPORTED, never silently swallowed: its own counter and one Q-Gate finding."""
    plan_id = 'gh-pr-identity-bypass-report'
    _patch_provider(monkeypatch, [_comment('mine-1', WORKFLOW_LOGIN, _bypass_body())])

    result = _run_fetch(plan_id)

    assert result['count_skipped_emitter_bypass'] == 1
    assert result['count_skipped_self_response'] == 0
    assert result['count_skipped_noise'] == 0
    assert result['workflow_identity'] == github_pr.WORKFLOW_IDENTITY_RESOLVED
    bypass = [
        f
        for f in query_qgate_findings(plan_id, '5-execute')['findings']
        if f.get('title', '').startswith('(emitter-bypass)')
    ]
    assert len(bypass) == 1
    assert bypass[0]['hash_id'] == result['emitter_bypass_hash_id']
    assert 'mine-1' in bypass[0].get('detail', '')
    assert 'emitter_bypass_persist_failed' not in result


def test_workflow_authored_heading_body_is_a_self_response(plan_context, monkeypatch):
    """The emitter's own output — identity plus opening heading — is skipped as a self-response."""
    plan_id = 'gh-pr-identity-self'
    _patch_provider(monkeypatch, [_comment('mine-1', WORKFLOW_LOGIN, _batched_body())])

    result = _run_fetch(plan_id)

    assert result['count_skipped_self_response'] == 1
    assert result['count_skipped_emitter_bypass'] == 0
    assert result['count_stored'] == 0
    assert result['emitter_bypass_hash_id'] is None


@pytest.mark.parametrize(
    ('plan_id', 'body'),
    [
        ('gh-pr-identity-foreign-heading', _batched_body()),
        (
            'gh-pr-identity-foreign-quote',
            'I disagree with this reply:\n> ' + github_pr._SELF_RESPONSE_HEADING + '\n> Fixed in the follow-up.',
        ),
    ],
    ids=['opens-with-heading', 'quotes-heading'],
)
def test_another_authors_heading_body_is_filed(plan_context, monkeypatch, plan_id, body):
    """The heading alone never makes a comment ours: another author's comment is filed."""
    _patch_provider(monkeypatch, [_comment('theirs-1', OTHER_AUTHOR, body)])

    result = _run_fetch(plan_id)

    assert result['count_skipped_self_response'] == 0
    assert result['count_skipped_emitter_bypass'] == 0
    assert result['count_stored'] == 1
    assert _stored_comment_ids(plan_id) == ['theirs-1']


def test_workflow_authored_plain_comment_is_filed(plan_context, monkeypatch):
    """The repo-owner account is also a genuine reviewer: a shape-less comment of its own is filed."""
    plan_id = 'gh-pr-identity-plain'
    _patch_provider(
        monkeypatch,
        [
            _comment('mine-plain', WORKFLOW_LOGIN, 'Please also cover the empty-list case in the parser.'),
            _comment('mine-bypass', WORKFLOW_LOGIN, _bypass_body()),
        ],
    )

    result = _run_fetch(plan_id)

    assert result['count_stored'] == 1
    assert _stored_comment_ids(plan_id) == ['mine-plain']


def test_identity_login_comparison_ignores_case_and_bot_suffix():
    """GitHub logins compare case-insensitively, and an App login may carry ``[bot]``."""
    assert github_pr._same_login('Repo-Owner', 'repo-owner')
    assert github_pr._same_login('release-app', 'release-app[bot]')
    assert not github_pr._same_login('alice', 'repo-owner')
    assert not github_pr._same_login('repo-owner', None)


def test_unresolved_identity_degrades_to_heading_only_and_is_disclosed(plan_context, monkeypatch):
    """An unreadable identity falls back to the heading test and says so.

    With no identity, the heading-opening body is skipped whoever wrote it (the
    fallback), the bypass shape cannot be recognised and is filed, and the result
    discloses ``workflow_identity: unresolved`` rather than reading as resolved.
    """
    plan_id = 'gh-pr-identity-unresolved'
    _patch_provider(
        monkeypatch,
        [
            _comment('heading-1', OTHER_AUTHOR, _batched_body()),
            _comment('bypass-1', WORKFLOW_LOGIN, _bypass_body()),
        ],
        login=None,
    )

    result = _run_fetch(plan_id)

    assert result['workflow_identity'] == github_pr.WORKFLOW_IDENTITY_UNRESOLVED
    assert result['count_skipped_self_response'] == 1
    assert result['count_skipped_emitter_bypass'] == 0
    assert _stored_comment_ids(plan_id) == ['bypass-1']


def test_identity_is_not_read_when_no_comment_carries_a_transmission_shape(plan_context, monkeypatch):
    """No heading and no section signature: no stage needs the identity, so it is not read."""
    plan_id = 'gh-pr-identity-not-needed'
    identity_reads = _patch_provider(
        monkeypatch, [_comment('theirs-1', OTHER_AUTHOR, 'The retry loop never resets its counter.')]
    )

    result = _run_fetch(plan_id)

    assert identity_reads == []
    assert result['workflow_identity'] == github_pr.WORKFLOW_IDENTITY_NOT_NEEDED
    assert result['count_stored'] == 1


def test_emitter_and_recognizer_share_the_section_signature():
    """The rendered batch carries the signature constant the bypass recognizer reads."""
    body = _batched_body(comment_id='c9')
    assert github_pr._BATCHED_SECTION_PREFIX + ' `c9`' in body
    assert body.startswith(github_pr._SELF_RESPONSE_HEADING)


# ============================================================================
# Own-trigger exclusion by provenance
# ============================================================================


def _registered_triggers() -> list[str]:
    """Every registered re-review trigger, derived from the bot registry.

    The same data the trigger poster sends and ``is_registered_trigger_comment``
    reads, so the cases below exercise the real registered set rather than a
    hand-copied string. Guarded non-empty: an empty registry would let every case
    pass over no trigger at all.
    """
    registry = github_pr.bot_registry
    triggers = sorted({t.strip() for t in (registry.trigger_comment(k) for k in registry.bot_kinds()) if t.strip()})
    assert triggers, 'bot registry declares no re-review trigger — the own-trigger cases would be vacuous'
    return triggers


def test_workflow_authored_trigger_is_excluded_by_provenance_and_reported(plan_context, monkeypatch):
    """A trigger this workflow posted is excluded in its own counter and recorded with its trigger.

    Fail-first case: before the provenance stage the same comment was dropped inside
    the noise filter and counted in ``count_skipped_noise``, with no record of which
    trigger it was. Every registered trigger is covered, and one is padded with
    whitespace to pin that the recorded trigger is the stripped, registered form.
    """
    plan_id = 'gh-pr-own-trigger-excluded'
    triggers = _registered_triggers()
    comments = [_comment(f'trig-{i}', WORKFLOW_LOGIN, trigger) for i, trigger in enumerate(triggers)]
    comments.append(_comment('trig-padded', WORKFLOW_LOGIN, f'\n  {triggers[0]}  \n'))
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(plan_id)

    assert result['status'] == 'success'
    assert result['workflow_identity'] == github_pr.WORKFLOW_IDENTITY_RESOLVED
    assert result['count_skipped_own_trigger'] == len(triggers) + 1
    assert result['count_skipped_noise'] == 0
    assert result['count_stored'] == 0
    assert _stored_comment_ids(plan_id) == []
    assert result['producer_mismatch_hash_id'] is None
    expected = [{'comment_id': f'trig-{i}', 'trigger': trigger} for i, trigger in enumerate(triggers)]
    expected.append({'comment_id': 'trig-padded', 'trigger': triggers[0]})
    assert result['own_trigger_exclusions'] == expected


def test_another_authors_exact_trigger_keeps_the_noise_disposition(plan_context, monkeypatch):
    """Provenance, not shape: the same exact trigger from anyone else is not excluded as ours."""
    plan_id = 'gh-pr-own-trigger-foreign-exact'
    trigger = _registered_triggers()[0]
    _patch_provider(monkeypatch, [_comment('theirs-trig', OTHER_AUTHOR, trigger)])

    result = _run_fetch(plan_id)

    assert result['count_skipped_own_trigger'] == 0
    assert result['own_trigger_exclusions'] == []
    assert result['count_skipped_noise'] == 1
    assert result['count_stored'] == 0


def test_bot_comment_quoting_a_trigger_is_ingested(plan_context, monkeypatch):
    """Matched negative control: a genuine bot review comment that quotes a trigger string is filed.

    Quoting is not an exact match, so the comment is neither an own trigger nor
    trigger noise — it is review feedback and must reach the store.
    """
    plan_id = 'gh-pr-own-trigger-bot-quote'
    trigger = _registered_triggers()[0]
    body = (
        'Consider handling the None case here before dereferencing the parsed config; '
        f'once that guard is in place, post `{trigger}` so the new commit gets a fresh pass.'
    )
    bot_comment = {
        'id': 'bot-quote-1',
        'author': 'coderabbitai',
        'thread_id': 'PRRT_quote',
        'kind': 'inline',
        'body': body,
        'path': 'src/config.py',
        'line': 12,
        'resolved': False,
    }
    _patch_provider(monkeypatch, [bot_comment])

    result = _run_fetch(plan_id)

    assert result['count_skipped_own_trigger'] == 0
    assert result['count_skipped_noise'] == 0
    assert result['count_stored'] == 1
    assert _stored_comment_ids(plan_id) == ['bot-quote-1']


def test_unresolved_identity_keeps_a_workflow_trigger_as_noise_and_discloses(plan_context, monkeypatch):
    """Without a readable identity nothing can be attributed to the workflow: noise, disclosed."""
    plan_id = 'gh-pr-own-trigger-unresolved'
    trigger = _registered_triggers()[0]
    identity_reads = _patch_provider(monkeypatch, [_comment('trig-1', WORKFLOW_LOGIN, trigger)], login=None)

    result = _run_fetch(plan_id)

    assert identity_reads == [1]
    assert result['workflow_identity'] == github_pr.WORKFLOW_IDENTITY_UNRESOLVED
    assert result['count_skipped_own_trigger'] == 0
    assert result['own_trigger_exclusions'] == []
    assert result['count_skipped_noise'] == 1
    assert result['count_stored'] == 0


# ============================================================================
# Fetch coverage reaches the fetch_findings result
# ============================================================================


def _page(nodes, *, has_next=False, cursor=None, total=None):
    """A GraphQL connection object: nodes, ``totalCount`` and ``pageInfo``."""
    return {
        'totalCount': len(nodes) if total is None else total,
        'pageInfo': {'hasNextPage': has_next, 'endCursor': cursor},
        'nodes': nodes,
    }


def _issue_comment_node(comment_id, body):
    return {
        'id': comment_id,
        'body': body,
        'author': {'login': OTHER_AUTHOR},
        'createdAt': '2026-03-03T10:00:00Z',
        'updatedAt': '2026-03-03T10:00:00Z',
    }


def _patch_graphql_provider(monkeypatch, *, issue_comments):
    """Drive the REAL provider parse path: only transport, auth and repo reads are stubbed.

    Reviews and review threads are empty and exhausted; ``issue_comments`` is the
    issue-level comment connection object the first page returns.
    """
    github_ops = github_pr._github
    first_page = {
        'repository': {
            'pullRequest': {
                'reviewThreads': _page([]),
                'reviews': _page([]),
                'comments': issue_comments,
            }
        }
    }

    def fake_run_graphql(query, variables):
        assert query == github_ops.REVIEW_THREADS_QUERY, 'no follow-up page is served in these cases'
        return 0, first_page, ''

    monkeypatch.setattr(github_pr, 'get_viewer_login', lambda: (WORKFLOW_LOGIN, ''))
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('cuioss', 'plan-marshall'))
    monkeypatch.setattr(github_ops, 'run_graphql', fake_run_graphql)
    monkeypatch.setattr(github_ops, 'fetch_pr_head_committed_at', lambda pr_number: '')
    monkeypatch.setattr(github_ops, 'fetch_pr_head_sha', lambda pr_number: 'deadbeef')
    monkeypatch.setattr(github_ops, 'run_gh', lambda *_a, **_k: (1, '', 'run_gh is stubbed in this module'))


def test_capped_fetch_surfaces_as_incomplete_in_the_result(plan_context, monkeypatch):
    """A connection the provider could not read to its end is disclosed, not read as the whole set.

    Fail-first case: before the coverage fields existed the fetch_findings result
    carried no completeness claim at all, so a clipped comment set was
    indistinguishable from a complete one. The comment that WAS fetched is still filed.
    """
    plan_id = 'gh-pr-fetch-capped'
    _patch_graphql_provider(
        monkeypatch,
        issue_comments=_page(
            [_issue_comment_node('ic-1', 'The retry loop never resets its counter.')],
            has_next=True,
            cursor=None,
            total=250,
        ),
    )

    result = _run_fetch(plan_id)

    assert result['status'] == 'success'
    assert result['fetch_complete'] is False
    assert result['capped_connections'] == [
        {
            'connection': github_pr._github.CONNECTION_ISSUE_COMMENTS,
            'observed': 1,
            'cap': github_pr._github._COMMENT_CONNECTION_PAGE_SIZE,
            'total': 250,
            'capped': True,
        }
    ]
    assert result['count_stored'] == 1
    assert _stored_comment_ids(plan_id) == ['ic-1']


def test_complete_fetch_reports_complete_with_no_capped_connection(plan_context, monkeypatch):
    """Matched positive control: every connection read to its end reads as complete."""
    plan_id = 'gh-pr-fetch-complete'
    _patch_graphql_provider(
        monkeypatch,
        issue_comments=_page([_issue_comment_node('ic-1', 'The retry loop never resets its counter.')]),
    )

    result = _run_fetch(plan_id)

    assert result['fetch_complete'] is True
    assert result['capped_connections'] == []
    assert result['count_stored'] == 1


def test_provider_result_without_a_completeness_claim_is_not_complete(plan_context, monkeypatch):
    """An absent claim establishes nothing: a provider result carrying no coverage is not complete."""
    plan_id = 'gh-pr-fetch-unclaimed'
    _patch_provider(monkeypatch, [_comment('theirs-1', OTHER_AUTHOR, 'The retry loop never resets its counter.')])

    result = _run_fetch(plan_id)

    assert result['fetch_complete'] is False
    assert result['capped_connections'] == []
    assert result['count_stored'] == 1


# ============================================================================
# Shared noise layer: whole-comment acknowledgments over the commenter's own prose
# ============================================================================

#: The four phrases the shared layer used to match as UNANCHORED substrings, each in
#: the whole-comment form its rewritten entry recognises when it stands alone.
_ACK_PHRASES = ('looks good', 'ship it', 'no objection', 'dependabot[bot]')

_GENUINE_FINDING = 'The retry loop never resets its counter; reset it after a success.'


def _ai_agent_block(phrase):
    """A CodeRabbit-style collapsed AI-agent prompt block whose quoted text carries ``phrase``."""
    return (
        '<details>\n'
        '<summary>Prompt for AI Agents</summary>\n\n'
        '```\n'
        f'In src/retry.py the reviewer said "{phrase}" about the backoff, but verify the counter reset.\n'
        '```\n\n'
        '</details>'
    )


@pytest.mark.parametrize('phrase', _ACK_PHRASES)
def test_finding_beside_an_ai_agent_block_quoting_an_acknowledgment_is_not_noise(phrase):
    """Fail-first case: a genuine finding is never discarded for what a collapsed block quotes.

    Before the fix the shared layer searched the WHOLE lowered body, so the phrase
    inside the AI-agent block discarded the finding as acknowledgment noise.
    """
    body = f'{_GENUINE_FINDING}\n\n{_ai_agent_block(phrase)}'

    assert not github_pr._is_obvious_noise(body, 'coderabbit')
    assert not github_pr._is_obvious_noise(body, None)
    # Matched control: the same finding without the block is not noise either.
    assert not github_pr._is_obvious_noise(_GENUINE_FINDING, 'coderabbit')


@pytest.mark.parametrize('phrase', _ACK_PHRASES)
@pytest.mark.parametrize(
    'wrap',
    [
        pytest.param(lambda p: f'```\n{p}\n```', id='fenced'),
        pytest.param(lambda p: f'> {p}', id='blockquote'),
        pytest.param(lambda p: f'<details>{p}</details>', id='details'),
    ],
)
def test_a_phrase_quoted_in_a_block_at_or_below_the_bound_survives(phrase, wrap):
    """Adversarial: short enough for the length guard, yet the phrase is not the commenter's prose.

    Every body here is at or below the derived length bound, so only the coverage
    guard — the removal of quoted and collapsed regions — keeps it out of the drop.
    """
    body = wrap(phrase)
    assert len(body) <= github_pr._ACKNOWLEDGMENT_MAX_LENGTH, 'the adversarial case must sit inside the length bound'

    assert not github_pr._is_obvious_noise(body, None)
    assert not github_pr._is_obvious_noise(body, 'coderabbit')


@pytest.mark.parametrize('body', ['Looks good to me', 'Ship it!', 'No objection.', 'dependabot[bot]', 'LGTM'])
def test_a_bare_acknowledgment_is_still_dropped(body):
    """Matched positive control: a comment that IS an acknowledgment, as a whole, stays noise."""
    assert github_pr._is_obvious_noise(body, None)


def test_an_opening_acknowledgment_ahead_of_a_finding_is_not_noise():
    """The coverage guard: an opening "LGTM, but ..." cannot carry a finding out of the store."""
    body = 'LGTM, but the retry loop never resets its counter after a success, so the backoff grows forever.'

    assert not github_pr._is_obvious_noise(body, None)


def test_a_courtesy_only_run_beyond_the_length_bound_is_not_noise():
    """The length guard: a run the coverage guard accepts as pure courtesy is kept once it exceeds the bound."""
    body = 'LGTM, thanks, looks good to me, nothing further from me!'
    assert len(body) > github_pr._ACKNOWLEDGMENT_MAX_LENGTH
    # The coverage guard alone would drop it: an ignore pattern covers the whole prose.
    assert any(pattern.fullmatch(github_pr._own_prose(body)) for pattern in github_pr._COMPILED_IGNORE)

    assert not github_pr._is_obvious_noise(body, None)


def test_an_acknowledgment_phrase_inside_a_larger_comment_is_not_noise():
    """The coverage guard: a pattern must cover the WHOLE prose, never a phrase inside it."""
    body = 'Mostly fine; no objection to the rename.'

    assert not github_pr._is_obvious_noise(body, None)


#: Short findings that OPEN with a courtesy word — each inside the length bound, so
#: only the courtesy tail decides that the text after the opener is not courtesy.
_COURTESY_OPENED_FINDINGS = (
    'Noted. This will crash on empty input.',
    'thanks - but this leaks the file handle',
)


@pytest.mark.parametrize('body', _COURTESY_OPENED_FINDINGS, ids=['noted-then-finding', 'thanks-then-finding'])
def test_a_finding_that_opens_with_a_courtesy_word_is_not_noise(body):
    """The text after an opening courtesy word must itself be courtesy, never arbitrary content."""
    assert len(body) <= github_pr._ACKNOWLEDGMENT_MAX_LENGTH, 'the case must sit inside the length bound'

    assert not github_pr._is_obvious_noise(body, None)
    assert not github_pr._is_obvious_noise(body, 'coderabbit')


@pytest.mark.parametrize(
    'body',
    ['LGTM, nothing further from me.', 'Thanks!', 'Noted, thanks.', 'ack, looks good to me'],
)
def test_an_acknowledgment_with_a_courtesy_tail_is_still_dropped(body):
    """Matched positive control: an opener followed only by courtesy and punctuation stays noise."""
    assert github_pr._is_obvious_noise(body, None)


def test_courtesy_opened_findings_are_filed_end_to_end(plan_context, monkeypatch):
    """Through ``fetch_findings``: both courtesy-opened findings are filed, the bare acknowledgment is not."""
    plan_id = 'gh-pr-noise-courtesy-opener'
    comments = [_comment(f'polite-{i}', OTHER_AUTHOR, body) for i, body in enumerate(_COURTESY_OPENED_FINDINGS)]
    comments.append(_comment('ack-control', OTHER_AUTHOR, 'LGTM, nothing further from me.'))
    _patch_provider(monkeypatch, comments)

    result = _run_fetch(plan_id)

    assert result['count_skipped_noise'] == 1
    assert result['count_stored'] == len(_COURTESY_OPENED_FINDINGS)
    assert sorted(_stored_comment_ids(plan_id)) == [f'polite-{i}' for i in range(len(_COURTESY_OPENED_FINDINGS))]


def test_the_body_digest_edit_term_ignores_line_structure():
    """The dedup digest is computed over the flattened body the provider used to deliver.

    The fetch now keeps a body's line structure, so a stored comment keyed on a body
    digest must re-dedupe under the new shape instead of re-filing.
    """
    multi_line = {'body': 'Guard the bound.\n\tThen re-run.'}
    flattened = {'body': 'Guard the bound.  Then re-run.'}

    assert github_pr._comment_edit_term(multi_line) == github_pr._comment_edit_term(flattened)


def test_blockquoted_acknowledgment_over_a_finding_is_filed_end_to_end(plan_context, monkeypatch):
    """End to end over the REAL provider parse path: the line structure reaches the producer.

    Fail-first case: the provider flattened every newline before the producer saw the
    body, so the blockquote was invisible and the quoted ``Looks good to me`` dropped
    the whole comment as noise.
    """
    plan_id = 'gh-pr-noise-blockquote-e2e'
    body = f'> Looks good to me\n\n{_GENUINE_FINDING}'
    _patch_graphql_provider(monkeypatch, issue_comments=_page([_issue_comment_node('ic-quote', body)]))

    result = _run_fetch(plan_id)

    assert result['count_skipped_noise'] == 0
    assert result['count_stored'] == 1
    assert _stored_comment_ids(plan_id) == ['ic-quote']


def test_ai_agent_block_finding_is_filed_end_to_end(plan_context, monkeypatch):
    """A CodeRabbit inline finding carrying an AI-agent block that quotes ``looks good`` is filed."""
    plan_id = 'gh-pr-noise-ai-agent-block'
    body = f'{_GENUINE_FINDING}\n\n{_ai_agent_block("looks good")}'
    _patch_provider(
        monkeypatch,
        [
            {
                'id': 'cr-agent',
                'author': 'coderabbitai',
                'thread_id': 'PRRT_agent',
                'kind': 'inline',
                'body': body,
                'path': 'src/retry.py',
                'line': 7,
                'resolved': False,
            }
        ],
    )

    result = _run_fetch(plan_id)

    assert result['count_skipped_noise'] == 0
    assert result['count_stored'] == 1
    assert _stored_comment_ids(plan_id) == ['cr-agent']


def test_the_display_path_flattens_while_the_data_path_keeps_lines(monkeypatch):
    """``fetch_comments`` (the producer's input) keeps newlines; ``fetch-comments`` (display) flattens them."""
    body = f'> Looks good to me\n\n{_GENUINE_FINDING}'
    _patch_graphql_provider(monkeypatch, issue_comments=_page([_issue_comment_node('ic-lines', body)]))

    data = github_pr.fetch_comments(301)
    display = github_pr.cmd_fetch_comments(argparse.Namespace(pr=301, unresolved_only=False))

    assert data['comments'][0]['body'] == body
    assert '\n' not in display['comments'][0]['body']
    assert display['comments'][0]['body'] == body.replace('\n', ' ')


# ============================================================================
# A recognised refusal never reaches actionable_count
# ============================================================================

#: Sourcery's account-level weekly diff-character quota notice, in its observed
#: *reached* wording. The figure is synthetic: the provider owns the real one.
_SOURCERY_WEEKLY_QUOTA_REFUSAL = 'Sorry, you have reached your weekly rate limit of 500000 diff characters.'

#: Sourcery's per-PR size-ceiling notice. The figure is synthetic for the same reason.
_SOURCERY_SIZE_CEILING_REFUSAL = (
    'Sorry, your pull request is larger than the review limit of 4242 diff characters. '
    'Please split it into smaller pull requests.'
)


def _sourcery_review_body(comment_id, body):
    """A Sourcery comment in its declared publish shape, ``review_body``."""
    return {
        'id': comment_id,
        'author': 'sourcery-ai',
        'thread_id': '',
        'kind': 'review_body',
        'body': body,
        'resolved': False,
    }


@pytest.mark.parametrize(
    ('plan_id', 'body', 'cause'),
    [
        ('gh-pr-refusal-pin-weekly-quota', _SOURCERY_WEEKLY_QUOTA_REFUSAL, 'quota'),
        ('gh-pr-refusal-pin-size-ceiling', _SOURCERY_SIZE_CEILING_REFUSAL, 'size'),
    ],
    ids=['weekly-quota', 'size-ceiling'],
)
def test_a_recognised_sourcery_refusal_files_no_finding(plan_context, monkeypatch, plan_id, body, cause):
    """A refusal is reported as a refusal and stored as nothing, so no count can score it.

    ``actionable_count`` is computed from the stored ``pr-comment`` findings; a notice
    that reached the store as a ``review_body`` once scored a resolved-as-fixed rate
    over a bot that never reviewed. Recognised here, the notice files nothing, is
    counted as a refusal rather than as noise, names its bot, and never falls through
    to the enumerative unrecognised-refusal arm.
    """
    _patch_provider(monkeypatch, [_sourcery_review_body('sr-refusal', body)])

    result = _run_fetch(plan_id)

    assert result['status'] == 'success'
    assert result['count_stored'] == 0
    assert _stored_comment_ids(plan_id) == []
    assert result['count_skipped_refusal'] == 1
    assert result['count_skipped_noise'] == 0
    assert result['refused_bots'] == ['sourcery']
    assert result['refused_causes'] == [{'bot_kind': 'sourcery', 'cause': cause}]
    assert result['unrecognised_refusal'] == []
    assert result['participated_bots'] == []
    assert result['producer_mismatch_hash_id'] is None


def test_an_unclassified_sourcery_review_body_is_still_stored(plan_context, monkeypatch):
    """Matched positive control: a review body no refusal arm recognises is counted.

    Same bot, same publish shape — only the body differs. It is stored as a finding
    and credits Sourcery's ``review_body`` participation, so the refusal pin above
    cannot be passing by withholding every Sourcery ``review_body``.
    """
    plan_id = 'gh-pr-refusal-pin-unclassified-control'
    _patch_provider(
        monkeypatch,
        [
            _sourcery_review_body(
                'sr-review',
                'Overall the change reads well, but the retry helper should be extracted into its own module.',
            )
        ],
    )

    result = _run_fetch(plan_id)

    assert result['status'] == 'success'
    assert result['count_stored'] == 1
    assert _stored_comment_ids(plan_id) == ['sr-review']
    assert result['count_skipped_refusal'] == 0
    assert result['refused_bots'] == []
    assert result['participated_bots'] == [{'bot_kind': 'sourcery', 'evidence_kind': 'review_body'}]


# ============================================================================
# A zero-stored fetch names which zero it is
# ============================================================================

#: A bare acknowledgment: the shared noise layer drops it, so it files nothing. As a
#: Sourcery ``review_body`` it still credits Sourcery's participation, because
#: participation is derived before any filter runs.
_BARE_ACKNOWLEDGMENT = 'LGTM'

_SOURCERY_CREDIT = [{'bot_kind': 'sourcery', 'evidence_kind': 'review_body'}]


def _human_acknowledgment():
    """A human's bare acknowledgment — dropped as noise, credits no bot."""
    return _comment('human-ack', OTHER_AUTHOR, _BARE_ACKNOWLEDGMENT)


def _sourcery_acknowledgment():
    """A Sourcery review that found nothing — dropped as noise, credits Sourcery."""
    return _sourcery_review_body('sr-ack', _BARE_ACKNOWLEDGMENT)


def test_the_three_zeros_render_differently_through_the_same_call(plan_context, monkeypatch):
    """Fail-first case: ``count_stored: 0`` alone cannot say which zero a pass is.

    Three passes through the same ``fetch_findings`` call, each storing nothing:
    a fully readable pass that credits no bot, a fully readable pass whose credited
    Sourcery review found nothing, and the same clean pass with a Sourcery
    weekly-quota refusal beside it. Before the verdict existed the three results
    were identical in every stored-count field — this test read ``stored_zero_state``
    off a result that did not carry it. Each precondition (credit, refusal count,
    completeness) is asserted, so a zero can only name itself for the stated reason.
    """
    cases = [
        ('gh-pr-zero-state-no-coverage', [_human_acknowledgment()]),
        ('gh-pr-zero-state-covered-clean', [_sourcery_acknowledgment()]),
        (
            'gh-pr-zero-state-unreachable-quota',
            [_sourcery_acknowledgment(), _sourcery_review_body('sr-quota', _SOURCERY_WEEKLY_QUOTA_REFUSAL)],
        ),
    ]
    results = {}
    for plan_id, comments in cases:
        _patch_provider(monkeypatch, comments, complete=True)
        results[plan_id] = _run_fetch(plan_id)

    for plan_id, result in results.items():
        assert result['status'] == 'success', plan_id
        assert result['count_stored'] == 0, plan_id
        assert _stored_comment_ids(plan_id) == [], plan_id
        assert result['fetch_complete'] is True, plan_id
        assert result['merge_candidate_sha_resolved'] is True, plan_id
        assert result['stored_zero_state_source'] == github_pr.ZERO_STATE_SOURCE_LOCAL, plan_id

    no_coverage = results['gh-pr-zero-state-no-coverage']
    assert no_coverage['participated_bots'] == []
    assert no_coverage['count_skipped_refusal'] == 0
    assert no_coverage['stored_zero_state'] == github_pr.ZERO_STATE_NO_COVERAGE

    covered_clean = results['gh-pr-zero-state-covered-clean']
    assert covered_clean['participated_bots'] == _SOURCERY_CREDIT
    assert covered_clean['count_skipped_refusal'] == 0
    assert covered_clean['stored_zero_state'] == github_pr.ZERO_STATE_COVERED_CLEAN

    # The clean pass above plus a quota refusal: the credit still stands, and the
    # refusal alone is what makes the clean value unreachable.
    quota = results['gh-pr-zero-state-unreachable-quota']
    assert quota['participated_bots'] == _SOURCERY_CREDIT
    assert quota['count_skipped_refusal'] == 1
    assert quota['refused_causes'] == [{'bot_kind': 'sourcery', 'cause': 'quota'}]
    assert quota['stored_zero_state'] == github_pr.ZERO_STATE_UNREACHABLE

    assert len({result['stored_zero_state'] for result in results.values()}) == len(cases)


@pytest.mark.parametrize(
    ('plan_id', 'extra_comments', 'complete', 'head_sha'),
    [
        pytest.param('gh-pr-zero-state-precedence-incomplete', [], None, 'deadbeef', id='incomplete-fetch'),
        pytest.param('gh-pr-zero-state-precedence-head', [], True, '', id='unread-merge-candidate'),
        pytest.param(
            'gh-pr-zero-state-precedence-refusal',
            [_sourcery_review_body('sr-size', _SOURCERY_SIZE_CEILING_REFUSAL)],
            True,
            'deadbeef',
            id='size-refusal',
        ),
    ],
)
def test_could_not_reach_outranks_covered_and_clean(
    plan_context, monkeypatch, plan_id, extra_comments, complete, head_sha
):
    """Precedence: each "could not reach" cause turns an otherwise clean pass into ``unreachable``.

    Every case carries the credited Sourcery review that found nothing — the pass
    that reads ``covered_clean`` on its own — plus exactly one cause: a fetch with no
    completeness claim, a failed merge-candidate read, or a refusal. None of them may
    surface as covered and clean.
    """
    _patch_provider(monkeypatch, [_sourcery_acknowledgment(), *extra_comments], complete=complete, head_sha=head_sha)

    result = _run_fetch(plan_id)

    assert result['status'] == 'success'
    assert result['count_stored'] == 0
    assert result['stored_zero_state'] == github_pr.ZERO_STATE_UNREACHABLE
    assert result['stored_zero_state'] != github_pr.ZERO_STATE_COVERED_CLEAN


def test_a_pass_that_stored_a_finding_is_not_a_zero(plan_context, monkeypatch):
    """Matched control: when a comment survives the filters, no zero describes the pass."""
    plan_id = 'gh-pr-zero-state-stored'
    _patch_provider(
        monkeypatch,
        [_comment('theirs-1', OTHER_AUTHOR, 'The retry loop never resets its counter.')],
        complete=True,
    )

    result = _run_fetch(plan_id)

    assert result['count_stored'] == 1
    assert result['stored_zero_state'] == github_pr.ZERO_STATE_NOT_APPLICABLE


# ============================================================================
# A merge-queue enqueue is reported observed only after reading queue membership
# ============================================================================

#: The ``github_ops`` module object the handler reads its seams from — patched
#: directly, so every stub reaches the exact module ``cmd_pr_merge_queue`` calls into.
_MQ_GITHUB = _github_pr.github_ops
_MQ_PR = 42
_MQ_HEAD = 'feature/x'


def _queue_page(numbers, *, has_next=False, cursor=None):
    """One ``mergeQueue.entries`` page as ``run_graphql`` returns it (``data`` already unwrapped)."""
    return {
        'repository': {
            'mergeQueue': {
                'entries': {
                    'totalCount': len(numbers),
                    'pageInfo': {'hasNextPage': has_next, 'endCursor': cursor},
                    'nodes': [
                        {'position': i + 1, 'pullRequest': {'number': n, 'headRefName': f'feature/{n}'}}
                        for i, n in enumerate(numbers)
                    ],
                }
            }
        }
    }


#: The PR's own queue state when it carries neither a queue entry nor an armed auto-merge.
_MQ_PR_STATE_NEITHER = (
    0,
    {'repository': {'pullRequest': {'state': 'OPEN', 'autoMergeRequest': None, 'mergeQueueEntry': None}}},
    '',
)


def _patch_merge_queue(monkeypatch, pages, pr_state=_MQ_PR_STATE_NEITHER):
    """Stub the enqueue path up to the membership read, and serve ``pages`` by cursor.

    ``pages`` maps the request cursor (``None`` for the first page) to the
    ``(returncode, data, error)`` triple ``run_graphql`` returns; ``pr_state`` is the
    triple the PR's own queue-state read returns once a complete list does not carry
    the PR. Returns the list of cursors the entry read requested and the captured
    ``run_gh`` argv, so a case can pin how far the read walked and that the enqueue
    itself ran.
    """
    requested: list = []
    gh_calls: list = []

    def fake_run_graphql(query, variables):
        if query == _github_pr.PULL_REQUEST_QUEUE_STATE_QUERY:
            return pr_state
        assert query == _github_pr.MERGE_QUEUE_ENTRIES_QUERY, query
        cursor = variables.get('cursor')
        requested.append(cursor)
        return pages[cursor]

    def fake_run_gh(args, capture_json=False, timeout=60):
        gh_calls.append(list(args))
        return 0, '', ''

    monkeypatch.setattr(_MQ_GITHUB, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(_MQ_GITHUB, 'get_repo_info', lambda: ('octo', 'repo'))
    monkeypatch.setattr(
        _MQ_GITHUB,
        'view_pr_data',
        lambda head=None: {'status': 'success', 'pr_number': _MQ_PR, 'base_branch': 'main', 'head_branch': _MQ_HEAD},
    )
    monkeypatch.setattr(
        _MQ_GITHUB,
        '_probe_merge_queue_state',
        lambda owner, repo, branch: (_MQ_GITHUB.MERGE_QUEUE_ELIGIBLE_CONFIGURED, 'merge_queue rule active', None, None),
    )
    monkeypatch.setattr(_MQ_GITHUB, 'run_graphql', fake_run_graphql)
    monkeypatch.setattr(_MQ_GITHUB, 'run_gh', fake_run_gh)
    return requested, gh_calls


def _enqueue(pr_number=_MQ_PR, head=None):
    return _github_pr.cmd_pr_merge_queue(argparse.Namespace(pr_number=pr_number, head=head))


def test_observed_membership_reports_enqueued_true(monkeypatch):
    """The PR is listed on the complete entry list: ``enqueued: true``, naming the read."""
    requested, gh_calls = _patch_merge_queue(monkeypatch, {None: (0, _queue_page([7, _MQ_PR]), '')})

    result = _enqueue()

    assert result['status'] == 'success', result
    assert result['enqueued'] is True
    assert result['enqueue_observation'] == 'mergeQueue(branch: main).entries lists the PR at position 2'
    assert result['queue_precondition'] == 'merge_queue rule active'
    assert 'enqueue_unobserved_reason' not in result
    assert requested == [None]
    assert gh_calls == [['pr', 'merge', str(_MQ_PR), '--auto']]


def test_membership_read_failure_is_indeterminate_never_true(monkeypatch):
    """Fail-first case: the accepted enqueue used to be reported ``true`` with no membership read at all."""
    _patch_merge_queue(monkeypatch, {None: (1, None, 'GraphQL: rate limited')})

    result = _enqueue()

    assert result['status'] == 'success', result
    assert result['enqueued'] == _github_pr.ENQUEUED_INDETERMINATE
    assert result['enqueued'] is not True
    assert result['enqueue_unobserved_reason'] == _github_pr.ENQUEUE_UNOBSERVED_READ_FAILED
    assert 'GraphQL: rate limited' in result['enqueue_observation']


def test_pr_absent_from_a_complete_list_is_indeterminate(monkeypatch):
    """A complete list that does not carry the PR is not a negative: it may have merged or been ejected.

    The PR's own state is read before settling, and here it carries neither a queue
    entry nor an armed auto-merge, so ``pr_not_listed`` stands.
    """
    requested, _gh_calls = _patch_merge_queue(monkeypatch, {None: (0, _queue_page([7, 8]), '')})

    result = _enqueue()

    assert result['enqueued'] == _github_pr.ENQUEUED_INDETERMINATE
    assert result['enqueue_unobserved_reason'] == _github_pr.ENQUEUE_UNOBSERVED_NOT_LISTED
    assert result['enqueue_observation'] == (
        'mergeQueue(branch: main).entries read to its end (2 entries); PR not listed; '
        'pullRequest(number: 42) carries neither a mergeQueueEntry nor an autoMergeRequest'
    )
    assert requested == [None]


def test_pr_found_on_a_second_page_is_observed(monkeypatch):
    """A page size is never a ceiling: the read follows the cursor and finds the PR on page two."""
    requested, _gh_calls = _patch_merge_queue(
        monkeypatch,
        {
            None: (0, _queue_page([7, 8], has_next=True, cursor='c1'), ''),
            'c1': (0, _queue_page([_MQ_PR]), ''),
        },
    )

    result = _enqueue()

    assert result['enqueued'] is True
    assert requested == [None, 'c1']


def test_an_entry_list_without_an_advancing_cursor_is_incomplete(monkeypatch):
    """More entries reported but no cursor to read them by: the absence proves nothing."""
    _patch_merge_queue(monkeypatch, {None: (0, _queue_page([7], has_next=True, cursor=None), '')})

    result = _enqueue()

    assert result['enqueued'] == _github_pr.ENQUEUED_INDETERMINATE
    assert result['enqueue_unobserved_reason'] == _github_pr.ENQUEUE_UNOBSERVED_INCOMPLETE


def test_a_page_without_a_readable_has_next_page_is_incomplete(monkeypatch):
    """A page whose ``pageInfo`` lacks ``hasNextPage`` is not a list read to its end.

    Only ``hasNextPage: false`` proves the end of the list; an absent flag is an
    unreadable page, so the absence of the PR from it proves nothing.
    """
    page = _queue_page([7, 8])
    del page['repository']['mergeQueue']['entries']['pageInfo']['hasNextPage']
    requested, _gh_calls = _patch_merge_queue(monkeypatch, {None: (0, page, '')})

    result = _enqueue()

    assert result['status'] == 'success', result
    assert result['enqueued'] == 'indeterminate'
    assert result['enqueue_unobserved_reason'] == 'entries_incomplete'
    assert result['enqueue_observation'] == (
        'mergeQueue(branch: main).entries page carried no readable hasNextPage after 2 entries'
    )
    assert requested == [None]


def test_a_head_selected_enqueue_matches_by_head_branch(monkeypatch):
    """Under ``--head`` the PR is matched by its head branch, never by reinterpreting it as a number."""
    _patch_merge_queue(monkeypatch, {None: (0, _queue_page([_MQ_PR]), '')})

    result = _enqueue(pr_number=None, head=f'feature/{_MQ_PR}')

    assert result['enqueued'] is True
