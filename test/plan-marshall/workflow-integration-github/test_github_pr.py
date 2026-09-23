# SPDX-License-Identifier: FSL-1.1-ALv2
"""``github_pr.cmd_fetch_findings``: the self-response filter keyed on author identity.

The self-response stage recognises this workflow's own batched ``post_responses``
comment by WHO wrote it — the workflow identity, read through
``_github_pr.get_viewer_login`` — with a transmission shape REQUIRED beside it:

- workflow identity + opening heading      -> self-response, not filed
- workflow identity + section signature,
  no heading                               -> emitter bypass, not filed, reported
- workflow identity + neither shape        -> a genuine operator comment, filed
- any other author + heading               -> filed; another author's comment is never ours
- identity unreadable                      -> heading-only fallback, disclosed

The findings store is REAL (isolated via the autouse ``plan_context``
``PLAN_BASE_DIR`` sandbox); only the GitHub provider surface and the identity read
are monkeypatched, and the raw ``run_gh`` seam is stubbed to fail so no case can
shell out to a real ``gh``.
"""

import argparse

import pytest

from conftest import load_script_module

PLAN_IDS: tuple[str, ...] = (
    'gh-pr-identity-bypass',
    'gh-pr-identity-bypass-report',
    'gh-pr-identity-foreign-heading',
    'gh-pr-identity-foreign-quote',
    'gh-pr-identity-not-needed',
    'gh-pr-identity-plain',
    'gh-pr-identity-self',
    'gh-pr-identity-unresolved',
)
github_pr = load_script_module('plan-marshall', 'workflow-integration-github', 'github_pr.py', 'github_pr')
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


def _patch_provider(monkeypatch, comments, login=WORKFLOW_LOGIN):
    """Stub the provider surface and the workflow identity read.

    ``login=None`` simulates an unreadable identity. Returns the list the identity
    stub appends to on every call, so a case can assert whether it was read at all.
    """
    identity_reads: list[int] = []

    def _viewer_login():
        identity_reads.append(1)
        if login is None:
            return None, 'viewer read failed'
        return login, ''

    monkeypatch.setattr(github_pr, 'get_viewer_login', _viewer_login)
    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_pr._github, 'fetch_pr_head_committed_at', lambda pr_number: '')
    monkeypatch.setattr(github_pr._github, 'fetch_pr_head_sha', lambda pr_number: 'deadbeef')
    monkeypatch.setattr(
        github_pr._github,
        'fetch_pr_comments_data',
        lambda pr_number, unresolved_only=False: {
            'status': 'success',
            'provider': 'github',
            'comments': list(comments),
            'total': len(comments),
            'unresolved': len(comments),
        },
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
