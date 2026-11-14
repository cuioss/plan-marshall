#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``review-gate`` verb — the review half of the merge gate.

The lane decided its review half from prose: section 7 named an unresolved
thread and an outside-diff finding, and nothing read a reviewer's Follow-ups or
Nitpick sections, so a pull request could merge with those findings open while
the landing said "all handled". The verb is the decision a script makes instead,
from the surfaces the CI abstraction returns on the head:

* an unresolved thread (``path:line``) refuses the merge;
* a body finding with no disposition refuses it;
* a resolved thread whose last BOT comment says the concern remains refuses it —
  resolution is not silence, and a lane reply below the bot's restatement never
  discharges it;
* an unreadable or truncated read refuses it, because an unread read is not an
  empty one;
* a pull request with none of these is allowed.

Each refusing case is also asserted against a stub that checks only unresolved
threads, which is the pre-fix policy: the stub must answer "allowed" where the
verb answers "refused", or the fixture proves nothing about what changed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import github_re_review
import pytest

from conftest import get_scripts_dir, load_script_module, parse_ns, run_script

lane = load_script_module('plan-marshall', 'runbook-lane', 'runbook_lane.py', 'runbook_lane_review_gate_mod')

cmd_review_gate = lane.cmd_review_gate

_SCRIPT = get_scripts_dir('plan-marshall', 'runbook-lane') / 'runbook_lane.py'

_NITPICK_BODY = (
    '**Actionable comments posted: 0**\n\n'
    '<details>\n<summary>🧹 Nitpick comments (2)</summary><blockquote>\n'
    '<details>\n<summary>src/a.py (2)</summary>\nrename the helper\n</details>\n'
    '</blockquote></details>\n\n'
    '<details>\n<summary>Follow-ups (1)</summary>\n'
    'the same guard exists in src/b.py\n'
    '</details>\n'
)

_OUTSIDE_DIFF_BODY = (
    '**Actionable comments posted: 0**\n\n'
    '<details>\n<summary>⛔ Outside diff range comments (1)</summary><blockquote>\n'
    'the same guard exists in src/b.py\n'
    '</blockquote></details>\n'
)

#: OBSERVED shapes from CodeRabbit's review bodies on ``cuioss/plan-marshall#1940``
#: (review ``PRR_kwDOQ3xasM8AAAABWsFY6g`` and the later ones): the section title is
#: the colon spelling ``Nitpick comments: 1``, and each row carries a
#: ``<!-- cr-comment:v1:…`` marker. The body below is CONSTRUCTED from those shapes:
#: the titles and markers are the observed ones, the prose is shortened.
_COLON_COUNTED_NITPICK_BODY = (
    '**Actionable comments posted: 0**\n\n'
    '<details>\n<summary>🧹 Nitpick comments: 3</summary><blockquote>\n'
    '<dl>\n'
    '<dd>rename the helper\n<!-- cr-comment:v1:1111111111111111111111 --></dd>\n'
    '<dd>drop the unused import\n<!-- cr-comment:v1:2222222222222222222222 --></dd>\n'
    '<dd>guard the backoff cap\n<!-- cr-comment:v1:3333333333333333333333 --></dd>\n'
    '</dl>\n'
    '</blockquote></details>\n'
)

#: The same section with NO declared count, carrying only the three observed row
#: markers — the shape the row-marker reader exists for.
_MARKER_ONLY_NITPICK_BODY = (
    '**Actionable comments posted: 0**\n\n'
    '<details>\n<summary>🧹 Nitpick comments</summary><blockquote>\n'
    '<dl>\n'
    '<dd>rename the helper\n<!-- cr-comment:v1:1111111111111111111111 --></dd>\n'
    '<dd>drop the unused import\n<!-- cr-comment:v1:2222222222222222222222 --></dd>\n'
    '<dd>guard the backoff cap\n<!-- cr-comment:v1:3333333333333333333333 --></dd>\n'
    '</dl>\n'
    '</blockquote></details>\n'
)


def _inline(
    *,
    thread_id: str = 'T1',
    resolved: bool = False,
    body: str = 'the guard coerces UNKNOWN',
    author: str = 'coderabbitai',
    path: str = 'src/mod.py',
    line: int = 42,
) -> dict:
    return {
        'kind': 'inline',
        'id': f'{thread_id}-c',
        'thread_id': thread_id,
        'author': author,
        'body': body,
        'path': path,
        'line': line,
        'resolved': resolved,
        'created_at': '2026-11-07T10:00:00Z',
        'updated_at': '2026-11-07T10:00:00Z',
        'commit_id': 'a' * 40,
        'reply_to_id': '',
        'thread_reply': False,
    }


def _review_body(body: str, author: str = 'coderabbitai', commit_id: str = 'a' * 40) -> dict:
    return {
        'kind': 'review_body',
        'id': 'review-1',
        'thread_id': '',
        'author': author,
        'body': body,
        'path': '',
        'line': 0,
        'resolved': False,
        'created_at': '2026-11-07T10:00:00Z',
        'updated_at': '2026-11-07T10:00:00Z',
        'commit_id': commit_id,
        'reply_to_id': '',
        'thread_reply': False,
    }


def _read(*comments: dict, complete: bool = True, status: str = 'success') -> dict:
    if status != 'success':
        return {'status': 'error', 'operation': 'pr_comments', 'error': 'GraphQL query failed: boom'}
    unresolved = sum(1 for comment in comments if comment['kind'] == 'inline' and not comment['resolved'])
    return {
        'status': 'success',
        'operation': 'pr_comments',
        'provider': 'github',
        'pr_number': 7,
        'total': len(comments),
        'unresolved': unresolved,
        'complete': complete,
        'connections': [],
        'comments': list(comments),
    }


def _args(*dispositions: str):
    argv = ['review-gate', '--pr-number', '7']
    for disposition in dispositions:
        argv += ['--disposition', disposition]
    return parse_ns('plan-marshall', 'runbook-lane', 'runbook_lane.py', *argv)


def _args_with_reviewers(*reviewers: str):
    argv = ['review-gate', '--pr-number', '7']
    for reviewer in reviewers:
        argv += ['--required-reviewer', reviewer]
    return parse_ns('plan-marshall', 'runbook-lane', 'runbook_lane.py', *argv)


def _raw_read(comments: list[dict], *, complete: bool = True, status: str = 'success') -> dict:
    """The ONE comment read the gate decides on — the provider's raw records."""
    if status != 'success':
        return {'status': 'error', 'operation': 'pr_comments', 'error': 'GraphQL query failed: boom'}
    return {
        'status': 'success',
        'operation': 'pr_comments',
        'provider': 'github',
        'pr_number': 7,
        'total': len(comments),
        'unresolved': 0,
        'complete': complete,
        'connections': [],
        'comments': list(comments),
    }


def _verdict(read: dict, *dispositions: str, reviewers: tuple[str, ...] = ()) -> Any:
    argv = ['review-gate', '--pr-number', '7']
    for disposition in dispositions:
        argv += ['--disposition', disposition]
    for reviewer in reviewers:
        argv += ['--required-reviewer', reviewer]
    with patch.object(lane, '_read_review_surfaces', return_value=read):
        return cmd_review_gate(parse_ns('plan-marshall', 'runbook-lane', 'runbook_lane.py', *argv))


def _finished_marker_body() -> str:
    return '<!-- final_review_risk_coverage:{"coveredCommitId":"' + 'a' * 40 + '","kind":"reviewed"} -->'


def _finished_marker_without_commit() -> str:
    """A readable, finished marker naming NO commit — a claim nobody can place."""
    return '<!-- final_review_risk_coverage:{"kind":"reviewed"} -->'


def _issue_comment(body: str, author: str = 'coderabbitai') -> dict:
    return {
        'kind': 'issue_comment',
        'id': 'issue-1',
        'thread_id': '',
        'author': author,
        'body': body,
        'path': '',
        'line': 0,
        'resolved': False,
        'created_at': '2026-11-07T10:00:00Z',
        'updated_at': '2026-11-07T10:00:00Z',
        'commit_id': '',
        'reply_to_id': '',
        'thread_reply': False,
    }


def _only_unresolved_threads_stub(read: dict) -> bool:
    """The pre-fix policy in miniature: a merge is refused only by an open thread.

    This is the verdict the lane reached from prose before the verb existed. It
    counts the unresolved threads it can see and asks nothing else — which is why
    it also allows an unreadable or truncated surface, and a body whose findings
    never became threads. A fixture that this stub allows and the verb refuses is
    exactly the finding the verb closes; one where both agree proves nothing about
    the change.
    """
    return not any(comment['kind'] == 'inline' and not comment['resolved'] for comment in read.get('comments') or [])


def test_an_open_thread_refuses_the_merge_and_names_its_location() -> None:
    verdict = _verdict(_read(_inline(resolved=False)))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'unresolved_review_threads'
    assert verdict['unresolved_review_threads'] == 1
    assert verdict['unresolved_threads'][0]['location'] == 'src/mod.py:42'


def test_a_body_finding_with_no_disposition_refuses_the_merge() -> None:
    verdict = _verdict(_read(_review_body(_OUTSIDE_DIFF_BODY)))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'body_findings_undisposed'
    assert verdict['undisposed'] == [{'reviewer': 'coderabbit', 'section': 'outside-diff', 'id': 'outside-diff-1'}]
    assert verdict['review_body_findings_total'] == 1
    assert verdict['review_body_findings_handled'] == 0


def test_a_disposed_body_finding_admits_the_merge() -> None:
    verdict = _verdict(_read(_review_body(_OUTSIDE_DIFF_BODY)), 'coderabbit outside-diff outside-diff-1 — abc1234')

    assert verdict['merge_allowed'] is True, verdict
    assert verdict['reason'] == 'all_handled'
    assert verdict['review_body_findings_handled'] == 1


def test_a_body_of_only_nitpicks_and_follow_ups_refuses_the_merge() -> None:
    """No thread and no outside-diff section — the shape the pre-fix gate let through."""
    read = _read(_review_body(_NITPICK_BODY))
    assert 'outside diff' not in _NITPICK_BODY, 'the fixture must carry no outside-diff section'
    assert not any(comment['kind'] == 'inline' for comment in read['comments'])

    verdict = _verdict(read)

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'body_findings_undisposed'
    assert verdict['review_body_findings_total'] == 3
    assert {(row['section'], row['id']) for row in verdict['undisposed']} == {
        ('nitpick', 'nitpick-1'),
        ('nitpick', 'nitpick-2'),
        ('followup', 'followup-1'),
    }


def test_a_resolved_thread_whose_last_reviewer_comment_restates_the_defect_refuses_the_merge() -> None:
    read = _read(
        _inline(thread_id='T1', resolved=True, body='the guard coerces UNKNOWN', author='coderabbitai'),
        _inline(thread_id='T1', resolved=True, body='fixed in abc1234', author='octocat'),
        _inline(
            thread_id='T1', resolved=True, body='This still applies: the guard is unchanged.', author='coderabbitai'
        ),
    )

    verdict = _verdict(read)

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'thread_concern_remains'
    assert verdict['threads'][0]['location'] == 'src/mod.py:42'


def test_a_resolved_thread_closed_with_an_acknowledgement_admits_the_merge() -> None:
    read = _read(
        _inline(thread_id='T1', resolved=True, body='the guard coerces UNKNOWN', author='coderabbitai'),
        _inline(thread_id='T1', resolved=True, body='Addressed in commit abc1234.', author='coderabbitai'),
        _inline(thread_id='T1', resolved=True, body='fixed in abc1234', author='octocat'),
    )

    verdict = _verdict(read)

    assert verdict['merge_allowed'] is True, verdict
    assert verdict['unresolved_review_threads'] == 0


def test_a_lane_reply_below_the_bot_s_restatement_does_not_discharge_the_concern() -> None:
    """The last BOT word is the finding's: a human "done" below it changes nothing.

    The shape the landing recorded on PLAN-LB-116: the bot restates the defect, the
    lane closes the thread with an acknowledgement, and the concern sits one comment
    above the last word. Reading ``thread[-1]`` let it through.
    """
    read = _read(
        _inline(thread_id='T1', resolved=True, body='the guard coerces UNKNOWN', author='coderabbitai'),
        _inline(thread_id='T1', resolved=True, body='fixed in abc1234', author='octocat'),
        _inline(
            thread_id='T1', resolved=True, body='This still applies: the guard is unchanged.', author='coderabbitai'
        ),
        _inline(thread_id='T1', resolved=True, body='done', author='octocat'),
    )

    verdict = _verdict(read)

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'thread_concern_remains'
    assert verdict['threads'][0]['location'] == 'src/mod.py:42'


def test_a_later_bot_acknowledgement_after_the_restatement_admits_the_merge() -> None:
    """The bot's own later acknowledgement without a marker is the discharge."""
    read = _read(
        _inline(thread_id='T1', resolved=True, body='the guard coerces UNKNOWN', author='coderabbitai'),
        _inline(thread_id='T1', resolved=True, body='fixed in abc1234', author='octocat'),
        _inline(
            thread_id='T1', resolved=True, body='This still applies: the guard is unchanged.', author='coderabbitai'
        ),
        _inline(thread_id='T1', resolved=True, body='done', author='octocat'),
        _inline(thread_id='T1', resolved=True, body='Addressed in commit def5678.', author='coderabbitai'),
    )

    verdict = _verdict(read)

    assert verdict['merge_allowed'] is True, verdict
    assert verdict['reason'] == 'all_handled'


def test_a_failed_read_refuses_the_merge() -> None:
    verdict = _verdict(_read(status='error'))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'undecidable_read'


def test_a_truncated_read_refuses_the_merge() -> None:
    """A clipped population is never published as a complete one."""
    verdict = _verdict(_read(_inline(), complete=False))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert 'truncated' in verdict['detail']


def test_an_unreadable_review_body_section_refuses_the_merge() -> None:
    """An unknown counted section is undecidable, never "no findings"."""
    body = '<details>\n<summary>🔍 Lint comments (2)</summary>\nuse the helper\n</details>\n'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert 'unreadable review-body section' in verdict['detail']


def test_a_colon_counted_section_counts_its_declared_findings() -> None:
    """OBSERVED #1940: the title is `Nitpick comments: 3`, not `Nitpick comments (3)`."""
    verdict = _verdict(_read(_review_body(_COLON_COUNTED_NITPICK_BODY)))

    assert verdict['review_body_findings_total'] == 3
    assert [row['id'] for row in verdict['undisposed']] == ['nitpick-1', 'nitpick-2', 'nitpick-3']


def test_one_disposition_does_not_clear_a_colon_counted_section_of_three() -> None:
    """The defect the colon spelling caused: one disposition cleared three findings."""
    verdict = _verdict(
        _read(_review_body(_COLON_COUNTED_NITPICK_BODY)),
        'coderabbit nitpick nitpick-1 — a1b2c3d',
    )

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'body_findings_undisposed'
    assert verdict['review_body_findings_total'] == 3
    assert verdict['review_body_findings_handled'] == 1
    assert [row['id'] for row in verdict['undisposed']] == ['nitpick-2', 'nitpick-3']


def test_an_undeclared_section_counts_its_row_markers() -> None:
    """OBSERVED #1940: each row carries a `<!-- cr-comment:v1:` marker."""
    verdict = _verdict(_read(_review_body(_MARKER_ONLY_NITPICK_BODY)))

    assert verdict['review_body_findings_total'] == 3
    assert [row['id'] for row in verdict['undisposed']] == ['nitpick-1', 'nitpick-2', 'nitpick-3']


@pytest.mark.parametrize('title', ['🔎 Potential issues: 2', '🔎 Potential issues (2)'])
def test_a_counted_title_that_is_neither_a_section_nor_a_label_is_undecidable(title: str) -> None:
    """A counted title the parser cannot place is a stop, never "no findings"."""
    body = f'<details>\n<summary>{title}</summary>\nuse the helper\n</details>\n'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert 'unreadable review-body section' in verdict['detail']


def test_a_captured_counted_non_finding_title_is_not_a_finding() -> None:
    """OBSERVED #1940: `Files selected for processing: 19` is counted and holds no finding."""
    body = (
        '<details>\n'
        '<summary>📒 Files selected for processing: 19</summary>\n'
        '* `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py`\n'
        '</details>\n'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['merge_allowed'] is True, verdict
    assert verdict['review_body_findings_total'] == 0


def test_a_captured_incremental_skip_notice_is_not_a_finding() -> None:
    """OBSERVED #1952: an incremental review's "Files skipped …" block is a diagnostic.

    The block carries a declared count (``: 1``) inside a ``<picture>``-wrapped
    ``<summary>``, which is why the counted-title rule refused it as unreadable on the
    PR this title was captured from. It states what the reviewer did NOT re-read, so it
    is neither a findings section nor a stop.
    """
    body = (
        '<details>\n<summary><picture><source media="(prefers-color-scheme: dark)" '
        'srcset="x-dark.svg"><img src="x.svg" width="16" height="16" align="absmiddle" '
        'alt=""></picture> Files skipped from review as they are similar to previous '
        'changes: 1</summary>\n<dl><dd>\n'
        '* `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`\n'
        '</dd></dl>\n</details>\n'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['merge_allowed'] is True, verdict
    assert verdict['review_body_findings_total'] == 0


#: CodeRabbit's "nothing to review here" block, captured verbatim from the review body
#: on ``cuioss/plan-marshall#1964`` (review ``PRR_kwDOQ3xasM8AAAABXbfesw``). The icon
#: URLs, the counted title and the listed file are the ones the reviewer posted; the
#: line breaks are the ones its markup carries.
_CAPTURED_NO_REVIEWABLE_CHANGES_BLOCK = (
    '<details>\n'
    '<summary><picture><source media="(prefers-color-scheme: dark)" '
    'srcset="https://storage.googleapis.com/coderabbit_public_assets/review-comment-icons-v1/'
    'file-no-changes-dark.svg"><img src="https://storage.googleapis.com/coderabbit_public_assets/'
    'review-comment-icons-v1/file-no-changes.svg" width="16" height="16" align="absmiddle" '
    'alt=""></picture> Files with no reviewable changes: 1</summary>\n'
    '<dl><dd>\n'
    '* opencode.json\n'
    '</dd></dl>\n'
    '</details>\n'
)


def test_a_captured_incremental_no_reviewable_changes_notice_is_not_a_finding() -> None:
    """OBSERVED #1964: "Files with no reviewable changes" is a file list, not a stop.

    Captured verbatim from the review body on PR #1964, where the counted title
    (``: 1``) inside a ``<picture>``-wrapped ``<summary>`` made the counted-title rule
    refuse the whole body as unreadable. The block names files the reviewer found
    nothing to say about, so it contributes no finding.
    """
    verdict = _verdict(_read(_review_body(_CAPTURED_NO_REVIEWABLE_CHANGES_BLOCK)))

    assert verdict['merge_allowed'] is True, verdict
    assert verdict['review_body_findings_total'] == 0


def test_the_captured_block_beside_a_findings_section_reads_only_the_findings() -> None:
    """The captured label is a BOUNDARY: it contributes nothing and hides nothing."""
    body = _OUTSIDE_DIFF_BODY + _CAPTURED_NO_REVIEWABLE_CHANGES_BLOCK

    verdict = _verdict(_read(_review_body(body)), 'coderabbit outside-diff outside-diff-1 — f1670af19')

    assert verdict['reason'] == 'all_handled', verdict
    assert verdict['review_body_findings_total'] == 1


def test_the_no_reviewable_changes_block_is_the_captured_one() -> None:
    """The fixture IS the capture, so a placeholder icon would make it a reconstruction.

    The asset host, the two icon files and the listed path are the reviewer's own. A
    fixture carrying placeholders reads identically locally while never having been
    observed — the one thing a captured block exists to establish.
    """
    block = _CAPTURED_NO_REVIEWABLE_CHANGES_BLOCK

    assert 'https://storage.googleapis.com/coderabbit_public_assets/review-comment-icons-v1/' in block
    assert 'file-no-changes-dark.svg' in block
    assert 'file-no-changes.svg' in block
    assert 'Files with no reviewable changes: 1' in block
    assert '* opencode.json' in block


def test_a_counted_non_finding_block_ends_the_span_of_the_section_before_it() -> None:
    """A non-finding block is a BOUNDARY, not content of the section above it.

    An uncounted nitpick section followed by a counted file list would otherwise count
    the list's entry as a second nitpick, so one real finding would arrive as two and the
    gate would still block after the real one was disposed. The block contributes no
    finding of its own and must not extend the previous section's span.
    """
    body = (
        '<details>\n<summary>🧹 Nitpick comments</summary><blockquote>\n'
        '<dl><dd>\n<details>\n'
        '<summary>marketplace/bundles/plan-marshall/skills/x.py: 1</summary>\n'
        '<blockquote><dl><dd>rename the helper</dd></dl></blockquote>\n'
        '</details>\n</dd></dl>\n'
        '</blockquote></details>\n\n'
        '<details>\n<summary>📒 Files selected for processing: 1</summary>\n'
        '<dl><dd>* `marketplace/bundles/plan-marshall/skills/x.py`</dd></dl>\n'
        '</details>\n'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [row['id'] for row in verdict['undisposed']] == ['nitpick-1']


def test_a_captured_body_with_counted_non_finding_sections_reads_one_nitpick() -> None:
    """CONSTRUCTED body from OBSERVED #1940 titles beside one nitpick.

    The titles are the ones the captured review body carries (review
    ``PRR_kwDOQ3xasM8AAAABWsFY6g`` on ``cuioss/plan-marshall#1940``: `Review info`,
    `Run configuration`, `Commits`, `Files selected for processing: 19`), so the
    counted titles the reviewer really posts do not turn a readable review into a
    false block. The prose and nesting are shortened; the titles are verbatim.
    """
    body = (
        '<!-- coderabbit-ai-generated:v1 -->\n'
        '**Actionable comments posted: 1**\n\n'
        '<h6>\n<details>\n<summary>ℹ️ Review info</summary>\n<dl><dd>run configuration</dd></dl>\n</details>\n\n'
        '<details>\n<summary>📒 Files selected for processing: 19</summary>\n'
        '<dl><dd>* `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py`</dd></dl>\n'
        '</details>\n</h6>\n\n'
        '<details>\n<summary>🧹 Nitpick comments: 1</summary><blockquote>\n'
        '<dl><dd>\n<details>\n'
        '<summary>marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py: 1</summary>\n'
        '<blockquote><dl><dd>rename the helper\n<!-- cr-comment:v1:aaaaaaaaaaaaaaaaaaaaaaaa --></dd></dl></blockquote>\n'
        '</details>\n</dd></dl>\n'
        '</blockquote></details>\n'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['reason'] == 'body_findings_undisposed', verdict
    # One inline count from the status line ("Actionable comments posted: 1") and one
    # nitpick — the counted non-finding block mints nothing and blocks nothing.
    assert verdict['review_body_findings_total'] == 2
    assert [row['id'] for row in verdict['undisposed']] == ['nitpick-1', 'inline-1']


@pytest.mark.parametrize('title', ['**Nitpick comments (3)**', '🧹 Nitpick comments: 3'])
def test_a_decorated_section_title_still_declares_its_count(title: str) -> None:
    """Decoration around the count does not hide it: bold markers and emoji are noise."""
    body = f'<details>\n<summary>{title}</summary>\nfirst\nsecond\nthird\n</details>\n'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 3


def test_a_markup_wrapped_section_title_still_counts_its_declared_findings() -> None:
    """OBSERVED #1940: the summary wraps its heading in a `<picture>` icon."""
    body = (
        '<details>\n'
        '<summary><picture><img src="https://example.invalid/brush-cleaning.svg" alt=""></picture> '
        'Nitpick comments: 2</summary><blockquote>\n'
        'first\n<!-- cr-comment:v1:aaaaaaaaaaaaaaaaaaaaaaaa -->\n'
        'second\n<!-- cr-comment:v1:bbbbbbbbbbbbbbbbbbbbbbbb -->\n'
        '</blockquote></details>\n'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 2
    assert [row['id'] for row in verdict['undisposed']] == ['nitpick-1', 'nitpick-2']


def test_a_decorated_unreadable_section_is_still_undecidable() -> None:
    """Bold markers must not hide a counted section the parser cannot place."""
    body = '<details>\n<summary>**Lint comments (2)**</summary>\nuse the helper\n</details>\n'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert 'unreadable review-body section' in verdict['detail']


def test_a_counted_additional_comments_section_counts_its_findings() -> None:
    """A counted `Additional comments (N)` is counted, never declared away.

    The #1940 capture does not carry the section, so it is not *shown* to be
    boilerplate; counting it is the fail-closed read and leaves no false pass.
    """
    body = '<details>\n<summary>🔇 Additional comments (2)</summary>\nfirst\nsecond\n</details>\n'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['reason'] == 'body_findings_undisposed', verdict
    assert verdict['review_body_findings_total'] == 2
    assert [row['id'] for row in verdict['undisposed']] == ['additional-1', 'additional-2']


@pytest.mark.parametrize(
    'title',
    [
        '📒 Files selected for processing: 19',
        '🙈 Files ignored due to path filters (4)',
        'ℹ️ Review info (2)',
        '⚙️ Run configuration: 3',
        '🔀 Commits (5)',
    ],
)
def test_a_counted_declared_non_finding_title_is_not_a_finding(title: str) -> None:
    """The declared non-finding labels stay non-findings when a count rides the title.

    Provenance: `Files selected for processing: 19` is OBSERVED with its count on
    #1940; `Review info`, `Run configuration` and `Commits` are OBSERVED there
    uncounted, so their counts are CONSTRUCTED; `Files ignored due to path filters (4)`
    is spec-named, with a CONSTRUCTED count. The label wins over the count in every
    case.
    """
    body = f'<details>\n<summary>{title}</summary>\n* `a.py`\n</details>\n'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['merge_allowed'] is True, verdict
    assert verdict['review_body_findings_total'] == 0


def test_a_bare_location_suffix_is_not_read_as_a_count() -> None:
    """`src/a.py:12` is a location, not a twelve-finding declaration."""
    body = (
        '<details>\n<summary>🧹 Nitpick comments</summary><blockquote>\n'
        '<details>\n<summary>src/a.py:12</summary>\nrename the helper\n</details>\n'
        '</blockquote></details>\n'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1


def test_a_top_level_per_file_summary_is_undecidable() -> None:
    """An observed per-file grouping with no recognised section above it cannot be placed."""
    body = '<details><summary>src/a.py (3)</summary> rename the helper </details>\n'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert 'unreadable review-body section' in verdict['detail']


def test_a_disposition_that_does_not_name_its_evidence_is_refused() -> None:
    verdict = _verdict(_read(_review_body(_OUTSIDE_DIFF_BODY)), 'coderabbit outside-diff outside-diff-1 —')

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'disposition_unparsable'


@pytest.mark.parametrize('evidence', ['TBD', 'TBD.', '-', 'n/a', 'TODO', 'none', 'pending'])
def test_a_placeholder_evidence_does_not_dispose_the_finding(evidence: str) -> None:
    """A placeholder is what a line says when nothing was decided."""
    disposition = f'coderabbit outside-diff outside-diff-1 — {evidence}'

    verdict = _verdict(_read(_review_body(_OUTSIDE_DIFF_BODY)), disposition)

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'disposition_unparsable'
    assert verdict['refused'] == [disposition]


@pytest.mark.parametrize(
    'evidence',
    ['a1b2c3d', 'fixed in a1b2c3d', 'declined: the call is deliberate and documented'],
)
def test_a_real_commit_or_reason_disposes_the_finding(evidence: str) -> None:
    verdict = _verdict(_read(_review_body(_OUTSIDE_DIFF_BODY)), f'coderabbit outside-diff outside-diff-1 — {evidence}')

    assert verdict['merge_allowed'] is True, verdict
    assert verdict['reason'] == 'all_handled'


def test_a_placeholder_embedded_in_a_stated_reason_is_a_stated_reason() -> None:
    """The comparison is over the whole evidence token, never per word.

    A word-wise test would refuse a real reason that happens to contain ``none`` or
    ``later`` ("none of the callers use this"); the rule the spec states is that the
    evidence as a whole is a commit or a reason outside the placeholder set.
    """
    verdict = _verdict(
        _read(_review_body(_OUTSIDE_DIFF_BODY)),
        'coderabbit outside-diff outside-diff-1 — n/a — see later',
    )

    assert verdict['merge_allowed'] is True, verdict
    assert verdict['reason'] == 'all_handled'


def test_an_unrecognised_record_kind_refuses_the_merge() -> None:
    """A record shape the verb does not know is a surface it cannot read."""
    read = _read()
    read['comments'] = [{**_inline(), 'kind': 'thread_comment'}]

    verdict = _verdict(read)

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert 'thread_comment' in verdict['detail']


def test_a_read_without_a_coverage_signal_is_its_own_reason() -> None:
    """A provider that publishes no coverage cannot be shown whole — not a truncation."""
    read = _read(_review_body('**Actionable comments posted: 0**'))
    del read['complete']
    read['provider'] = 'gitlab'

    verdict = _verdict(read)

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'coverage_unavailable'
    assert verdict['provider'] == 'gitlab'


def test_a_human_review_body_is_a_finding_source_too() -> None:
    """The gate covers every reviewer's body, not only the registered bots'."""
    read = _read(_review_body(_OUTSIDE_DIFF_BODY, author='octocat'))

    verdict = _verdict(read)

    assert verdict['merge_allowed'] is False
    assert verdict['undisposed'][0]['reviewer'] == 'octocat'


def test_two_review_bodies_do_not_share_finding_ids() -> None:
    """One disposition must discharge one finding, not one per review body."""
    read = _read(_review_body(_NITPICK_BODY), _review_body(_NITPICK_BODY))

    verdict = _verdict(read)

    assert verdict['review_body_findings_total'] == 6
    assert [row['id'] for row in verdict['undisposed']] == [
        'nitpick-1',
        'nitpick-2',
        'followup-1',
        'nitpick-3',
        'nitpick-4',
        'followup-2',
    ]


def test_a_flattened_body_does_not_mint_a_phantom_inline_count() -> None:
    """The CI read flattens a body to one line; a count is read off the literal only.

    The counted block is a declared non-finding label, so the one-line shape proves
    the status literal mints no inline count without turning the body undecidable.
    """
    flattened = (
        '**Actionable comments posted:** '
        '<details><summary>📒 Files selected for processing: 3</summary> rename the helper </details>'
    )

    verdict = _verdict(_read(_review_body(flattened)))

    assert verdict['review_body_findings_total'] == 0
    assert verdict['merge_allowed'] is True, verdict


def test_a_review_body_with_no_author_refuses_the_merge() -> None:
    """An unattributable body's findings could never be disposed by name."""
    body = _review_body(_OUTSIDE_DIFF_BODY, author='')

    verdict = _verdict(_read(body))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert 'no attributable author' in verdict['detail']


def test_a_nested_file_summary_is_not_read_as_an_unreadable_section() -> None:
    """A per-file grouping inside a section is content, not a heading.

    The reviewer nests ``<summary>path (n)</summary>`` inside a section block; a
    file path that happens to contain ``comment`` or ``nitpick`` must not stop the
    gate on a body the reviewer meant to be readable.
    """
    body = (
        '**Actionable comments posted: 0**\n\n'
        '<details>\n<summary>🧹 Nitpick comments (1)</summary><blockquote>\n'
        '<details>\n<summary>src/comments.py (1)</summary>\nrename the helper\n</details>\n'
        '</blockquote></details>\n'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['reason'] == 'body_findings_undisposed', verdict
    assert verdict['review_body_findings_total'] == 1
    assert [row['id'] for row in verdict['undisposed']] == ['nitpick-1']


def test_a_nested_summary_deeper_than_a_section_never_raises_undecidable() -> None:
    """The depth rule, stated as a control: any depth-2 summary is content."""
    body = (
        '<details>\n<summary>Outside-diff comments (2)</summary><blockquote>\n'
        '<details>\n<summary>src/nitpick_notes.md (3)</summary>\nsee the note\n</details>\n'
        '</blockquote></details>\n'
    )

    verdict = _verdict(_read(_review_body(body)), 'coderabbit outside-diff outside-diff-1 — abc1234')

    assert verdict['reason'] == 'body_findings_undisposed', verdict
    assert verdict['review_body_findings_total'] == 2


def test_a_section_wrapped_in_an_unrecognised_block_is_still_a_section() -> None:
    """Nesting inside an unknown block is not containment: its findings must survive."""
    body = (
        '<details>\n<summary>Review details</summary>\n'
        '<details>\n<summary>Nitpick comments (1)</summary>\nx\n</details>\n'
        '</details>\n'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['reason'] == 'body_findings_undisposed', verdict
    assert verdict['review_body_findings_total'] == 1


def test_a_body_wrapped_in_one_outer_block_still_counts_its_sections() -> None:
    """The whole body in one ``<details>`` must not drop every finding."""
    body = (
        '<details>\n<summary>Walkthrough</summary>\n'
        '<details>\n<summary>🧹 Nitpick comments (2)</summary><blockquote>\n'
        '<details>\n<summary>src/a.py (2)</summary>\nrename the helper\n</details>\n'
        '</blockquote></details>\n'
        '</details>\n'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['reason'] == 'body_findings_undisposed', verdict
    assert verdict['review_body_findings_total'] == 2


def test_a_summary_inside_an_unrecognised_group_inside_a_section_is_content() -> None:
    """The nearest RECOGNISED section decides containment, not the nearest block."""
    body = (
        '<details>\n<summary>🧹 Nitpick comments (1)</summary><blockquote>\n'
        '<details>\n<summary>src/module (1)</summary>\n'
        '<details>\n<summary>src/comments.py (2)</summary>\nrename the helper\n</details>\n'
        '</details>\n'
        '</blockquote></details>\n'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['reason'] == 'body_findings_undisposed', verdict
    assert verdict['review_body_findings_total'] == 1


def test_a_bot_confirming_a_fix_beside_a_new_concern_does_not_trip_the_gate() -> None:
    """A resolved thread whose bot confirms it — and names a DIFFERENT concern — is handled."""
    read = _read(
        _inline(thread_id='T1', resolved=True, body='the guard coerces UNKNOWN', author='coderabbitai'),
        _inline(
            thread_id='T1',
            resolved=True,
            body='Thanks, the parser is fixed. A separate Sonar concern remains: hotspots are not counted.',
            author='coderabbitai',
        ),
    )

    verdict = _verdict(read)

    assert verdict['merge_allowed'] is True, verdict
    assert verdict['reason'] == 'all_handled'


def test_a_clean_pull_request_admits_the_merge() -> None:
    verdict = _verdict(_read(_review_body('**Actionable comments posted: 0**\n\nLGTM\n')))

    assert verdict['merge_allowed'] is True, verdict
    assert verdict['reason'] == 'all_handled'
    assert verdict['review_body_findings_total'] == 0
    assert verdict['review_body_findings_handled'] == 0


@pytest.mark.parametrize(
    'read',
    [
        _read(_review_body(_OUTSIDE_DIFF_BODY)),
        _read(_review_body(_NITPICK_BODY)),
        _read(
            _inline(thread_id='T1', resolved=True, body='still applies', author='coderabbitai'),
        ),
        _read(
            _inline(thread_id='T1', resolved=True, body='the guard coerces UNKNOWN', author='coderabbitai'),
            _inline(thread_id='T1', resolved=True, body='fixed in abc1234', author='octocat'),
            _inline(
                thread_id='T1',
                resolved=True,
                body='This still applies: the guard is unchanged.',
                author='coderabbitai',
            ),
            _inline(thread_id='T1', resolved=True, body='done', author='octocat'),
        ),
        _read(status='error'),
    ],
    ids=[
        'body-finding',
        'nitpicks-and-follow-ups',
        'concern-remains',
        'concern-remains-after-lane-reply',
        'undecidable',
    ],
)
def test_each_refusing_case_is_red_against_the_unresolved_threads_only_stub(read) -> None:
    """The pre-fix policy allows every one of these; the verb refuses them."""
    stub_allows = _only_unresolved_threads_stub(read)

    verdict = _verdict(read)

    assert stub_allows is True, 'the fixture is not discriminating: the pre-fix policy also refuses it'
    assert verdict['merge_allowed'] is False


def test_the_verb_is_reachable_through_its_cli_surface() -> None:
    result = run_script(_SCRIPT, 'review-gate', '--pr-number', '0')

    assert result.success, result.stderr
    assert result.toon()['error'] == 'invalid_pr_number'


def test_the_gate_fetches_the_surface_once_and_spawns_no_cli(monkeypatch) -> None:
    """⛔ ONE fetch decides the whole verdict: threads, findings and reviews.

    The gate used to take the display read and the raw read as two snapshots, so a
    review or thread landing between them was credited by one half and unseen by the
    other. It now fetches the provider's data once, in-process, and derives the
    flattened display form itself — asserted here by counting fetches AND by pinning
    that no subprocess is spawned at all.
    """
    fetches: list[int] = []

    def fake_fetch(pr_number, unresolved_only=False):
        fetches.append(pr_number)
        return _raw_read([])

    def forbid_run(*_args, **_kwargs):
        raise AssertionError('the review gate must not spawn a CLI for its read')

    monkeypatch.setattr(github_re_review, 'fetch_pr_comments_data', fake_fetch)
    monkeypatch.setattr('subprocess.run', forbid_run)

    verdict = cmd_review_gate(_args_with_reviewers('coderabbit'))

    assert fetches == [7], 'exactly one provider fetch per verdict'
    assert verdict['reason'] == 'required_review_missing'


def test_the_read_runs_in_the_project_it_was_handed(monkeypatch) -> None:
    """The one fetch is routed to ``project_dir``, which is how ``gh`` finds the repo."""
    import ci_base

    original = ci_base.get_default_cwd()
    monkeypatch.setattr(github_re_review, 'fetch_pr_comments_data', lambda _pr, unresolved_only=False: _raw_read([]))
    try:
        lane._read_review_surfaces(7, Path('/tmp/project'))
        assert ci_base.get_default_cwd() == '/tmp/project'
    finally:
        ci_base.set_default_cwd(original)


# ---------------------------------------------------------------------------
# The done rule's precondition: a named required reviewer must HAVE a review
# ---------------------------------------------------------------------------


def test_a_named_required_reviewer_with_no_review_refuses_the_merge() -> None:
    """⛔ The flag alone never waives the currency demand: a review must exist."""
    verdict = _verdict(_read(), reviewers=('coderabbit',))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'required_review_missing'
    assert verdict['missing_required_reviews'] == ['coderabbit']


def test_a_named_required_reviewer_with_a_formal_review_passes() -> None:
    """MATCHED CONTROL — the same read plus one formal review record admits the merge."""
    verdict = _verdict(_read(_review_body('No actionable comments were generated')), reviewers=('coderabbit',))

    assert verdict['merge_allowed'] is True
    assert verdict['reason'] == 'all_handled'
    assert verdict['required_reviewers'] == ['coderabbit']


def test_a_named_required_reviewer_with_a_finished_marker_summary_passes() -> None:
    """The other qualifying artifact: a readable kind=reviewed marker naming a commit."""
    verdict = _verdict(_read(_issue_comment(_finished_marker_body())), reviewers=('coderabbit',))

    assert verdict['merge_allowed'] is True


def test_a_named_required_reviewer_with_only_a_walkthrough_is_refused() -> None:
    """A marker-less walkthrough is not a review, so the done precondition fails."""
    verdict = _verdict(_read(_issue_comment('## Walkthrough\n\nsome prose')), reviewers=('coderabbit',))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'required_review_missing'


def test_a_named_required_reviewer_with_only_a_refusal_is_refused() -> None:
    """A refusal submitted as a review object is not a review either."""
    verdict = _verdict(
        _read(_review_body('> ## Review limit reached > Please wait 12 minutes before requesting another review.')),
        reviewers=('coderabbit',),
    )

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'required_review_missing'


def test_a_review_body_without_a_commit_and_without_a_marker_is_refused() -> None:
    """§ 7 requires a formal review WITH a commit id: an empty one proves no head."""
    verdict = _verdict(
        _read(_review_body('No actionable comments were generated', commit_id='')), reviewers=('coderabbit',)
    )

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'required_review_missing'


def test_a_marker_on_its_own_line_after_a_prose_line_names_its_commit() -> None:
    """HOLDS AT THE BASE: prose, then the marker on its own line, is the bot's claim."""
    body = 'Some prose first.\n' + _finished_marker_body() + '\n'

    verdict = _verdict(_read(_issue_comment(body)), reviewers=('coderabbit',))

    assert verdict['merge_allowed'] is True


def test_a_marker_inside_a_plain_closed_fence_is_not_a_qualifying_review() -> None:
    """⛔ A marker quoted inside a fenced example is not the bot's own claim.

    Reading it as one would let a walkthrough that shows the marker — as documentation,
    not as a verdict — satisfy the done precondition and merge a pull request nobody
    reviewed.
    """
    body = 'A summary explains the marker:\n```text\n' + _finished_marker_body() + '\n```\n'

    verdict = _verdict(_read(_issue_comment(body)), reviewers=('coderabbit',))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'required_review_missing'


def test_a_marker_outside_a_fenced_example_keeps_its_claim() -> None:
    """MATCHED CONTROL — a fence-shaped span on a prose line opens no block."""
    body = 'Prose with a fenced example: ```text code ```\n' + _finished_marker_body() + '\n'

    verdict = _verdict(_read(_issue_comment(body)), reviewers=('coderabbit',))

    assert verdict['merge_allowed'] is True


def test_several_comments_are_each_read_for_a_marker() -> None:
    """HOLDS AT THE BASE: the check scans past the first comment.

    The FIRST comment carries no marker, so a loop that reads only the first answers
    `required_review_missing`; both later comments carry one, so every marker counts.
    """
    comments = [
        _issue_comment('## Walkthrough\n\nsome prose before the review completes'),
        _issue_comment('first comment\n' + _finished_marker_body()),
        _issue_comment('a second comment\n' + _finished_marker_body()),
    ]

    verdict = _verdict(_read(*comments), reviewers=('coderabbit',))

    assert verdict['merge_allowed'] is True, verdict
    assert 'missing_required_reviews' not in verdict


def test_a_fence_like_run_in_prose_is_not_a_closing_fence() -> None:
    """⛔ ```` ```not-a-close ```` is prose, not a closer — in the raw body too.

    The reader closes a fence only on a run with nothing after it, so the marker on
    the line below stays inside the block and is never the bot's claim.
    """
    body = '```text\n```not-a-close\n' + _finished_marker_body() + '\n```\n'

    verdict = _verdict(_read(_issue_comment(body)), reviewers=('coderabbit',))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'required_review_missing'


def test_an_enumerative_refusal_with_a_commit_is_a_qualifying_review(monkeypatch) -> None:
    """The lane asks the producer's predicate, so the enumerative arm changes nothing.

    The arm answers a different question at a different pipeline position; the
    producer's finished-review test reads ``_is_refusal_notice`` alone.
    """
    import _github_pr

    monkeypatch.setattr(_github_pr, 'UNRECOGNISED_REFUSAL_MAX_CHARS', 200)
    body = 'Please resubmit this pull request later.'
    assert _github_pr._is_unrecognised_refusal(body, 'coderabbit') is True
    assert _github_pr._is_refusal_notice(body, 'coderabbit') is False

    verdict = _verdict(_read(_review_body(body, commit_id='b' * 40)), reviewers=('coderabbit',))

    assert verdict['merge_allowed'] is True


def test_a_marker_beside_a_refusal_notice_is_still_a_finished_review() -> None:
    """The producer admits this combination; the lane's check must agree with it."""
    body = '> ## Review limit reached\n' + _finished_marker_body()
    verdict = _verdict(_read(_review_body(body, commit_id='')), reviewers=('coderabbit',))

    assert verdict['merge_allowed'] is True


def test_a_case_variant_refusal_is_not_a_qualifying_review() -> None:
    """⛔ A registered refusal phrase in another letter case is still a refusal.

    The body carries a commit and no notice presentation, so only the registry arm can
    read it — and that arm matches case-insensitively.
    """
    verdict = _verdict(_read(_review_body('REVIEW LIMIT REACHED', commit_id='b' * 40)), reviewers=('coderabbit',))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'required_review_missing'


def test_a_commit_less_marker_does_not_lift_a_refusal() -> None:
    """⛔ The exemption is a marker NAMING A COMMIT, never merely `kind: reviewed`."""
    body = '> ## Review limit reached\n' + _finished_marker_without_commit()
    verdict = _verdict(_read(_review_body(body, commit_id='b' * 40)), reviewers=('coderabbit',))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'required_review_missing'


def test_a_marker_in_a_shape_the_bot_does_not_publish_is_not_evidence() -> None:
    """The producer admits only the bot's own declared shapes; Sourcery publishes no summary."""
    verdict = _verdict(_read(_issue_comment(_finished_marker_body(), author='sourcery-ai')), reviewers=('sourcery',))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'required_review_missing'


def test_a_required_reviewer_with_findings_and_dispositions_is_admitted() -> None:
    """Both inputs travel together: the reviewer check does not bypass finding dispositions."""
    read = _read(_review_body(_NITPICK_BODY))
    verdict = _verdict(read, 'coderabbit nitpick nitpick-1 — f1670af19', reviewers=('coderabbit',))

    assert verdict['review_body_findings_total'] == 3
    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'body_findings_undisposed'


def test_an_unnamed_reviewer_population_leaves_the_verdict_unchanged() -> None:
    """The new input is opt-in: a call that names no reviewer behaves exactly as before."""
    verdict = _verdict(_read())

    assert verdict['merge_allowed'] is True
    assert 'required_reviewers' not in verdict


# ---------------------------------------------------------------------------
# The required-reviewer check reads the provider's RAW bodies
# ---------------------------------------------------------------------------
#
# The lane asks its predicate about the provider's raw text. The shapes below are
# the ones a flattened read could not decide: a marker quoted inside a fenced
# example, and a marker written as a blockquote, an inline code span or an indented
# code block. Every one of them is a place where the marker reader's opener rule —
# the opener must start a line — refuses the claim, and a display read destroyed the
# line structure that rule reads.
#
# These tests stub the TWO TRANSPORT seams only — ``subprocess.run`` (the display
# read) and ``github_re_review.fetch_pr_comments_data`` (the raw read) — so the
# lane's own read functions and its predicate site run for real. The display read is
# stubbed with what the provider actually gives it: ``flatten_comment_body`` of the
# raw text, the same call ``ci pr comments`` makes.

_QUOTED_MARKER_CONSTRUCTIONS: dict[str, str] = {
    # A: the fence's second line is content, so the marker never leaves the block.
    'A-fence-then-content-line': '```\n``` not-closer\n{marker}\n```\n',
    # B: prose carrying an inline span, then a real fence around the marker.
    'B-inline-span-before-fence': 'See ```code```.\n```\n{marker}\n```\n',
    # C: a four-space-indented run is indented code, not a fence, so the real one opens.
    'C-indented-run-before-fence': '    ```\n```\n{marker}\n```\n',
    # D: the three non-fence shapes the marker reader rejects by its opener position.
    'D-blockquoted-marker': '> {marker}\n',
    'D-inline-code-marker': '`{marker}`\n',
    'D-indented-marker': '    {marker}\n',
}


@pytest.fixture
def restore_default_cwd():
    """Restore the process-global working tree the read installs.

    Restores the value it FOUND, not ``None``: a test that resets the default
    unconditionally would clobber one an earlier test on the same worker had set.
    """
    import ci_base

    original = ci_base.get_default_cwd()
    yield
    ci_base.set_default_cwd(original)


def _verdict_through_the_read_seams(
    monkeypatch,
    raw_comments: list[dict],
    *,
    raw_read: dict | None = None,
    reviewers: tuple[str, ...] = ('coderabbit',),
) -> Any:
    """Drive ``review-gate`` with only the ONE provider fetch stubbed.

    No subprocess and no TOON: the gate fetches once, in-process, and derives the
    display form itself. A test that had to stub a second transport would be proof
    the gate reads the surface twice.
    """
    monkeypatch.setattr(
        github_re_review,
        'fetch_pr_comments_data',
        lambda _pr_number, unresolved_only=False: raw_read if raw_read is not None else _raw_read(raw_comments),
    )
    return cmd_review_gate(_args_with_reviewers(*reviewers))


@pytest.mark.usefixtures('restore_default_cwd')
@pytest.mark.parametrize('label', sorted(_QUOTED_MARKER_CONSTRUCTIONS))
def test_a_quoted_marker_is_not_a_qualifying_review(monkeypatch, label: str) -> None:
    """⛔ Every quoted shape answers `required_review_missing` on the raw bodies."""
    body = _QUOTED_MARKER_CONSTRUCTIONS[label].format(marker=_finished_marker_body())

    verdict = _verdict_through_the_read_seams(monkeypatch, [_issue_comment(body)])

    assert verdict['merge_allowed'] is False, verdict
    assert verdict['reason'] == 'required_review_missing'


@pytest.mark.usefixtures('restore_default_cwd')
def test_the_raw_seam_still_admits_a_marker_on_its_own_line(monkeypatch) -> None:
    """MATCHED CONTROL — the same seam admits an unquoted marker."""
    body = 'Some prose first.\n' + _finished_marker_body() + '\n'

    verdict = _verdict_through_the_read_seams(monkeypatch, [_issue_comment(body)])

    assert verdict['merge_allowed'] is True, verdict


@pytest.mark.usefixtures('restore_default_cwd')
@pytest.mark.parametrize(
    ('label', 'raw_read'),
    [
        ('truncated', {'status': 'success', 'complete': False, 'comments': []}),
        ('failed', {'status': 'error', 'error': 'GraphQL query failed: boom'}),
    ],
)
def test_an_incomplete_raw_read_is_undecidable_never_missing(monkeypatch, label: str, raw_read: dict) -> None:
    """⛔ A read that did not complete answers neither "present" nor "missing"."""
    verdict = _verdict_through_the_read_seams(monkeypatch, [], raw_read=raw_read)

    assert verdict['merge_allowed'] is False, verdict
    assert verdict['reason'] == 'undecidable_read', verdict


@pytest.mark.parametrize('raised', [AttributeError('owner is None'), ImportError('no provider module')])
def test_a_read_that_raises_is_classified_never_a_traceback(monkeypatch, raised: Exception) -> None:
    """⛔ The guard covers the imports and the repo lookup, not only the fetch.

    ``get_repo_info`` dereferences its own JSON, so a malformed ``gh repo view`` reply
    raises ``AttributeError`` one frame below the fetch; a broken provider import raises
    ``ImportError``. Both must come back as a readable failure the gate can classify,
    because a crash states no verdict at all.
    """

    def boom(*_args, **_kwargs):
        raise raised

    monkeypatch.setattr(github_re_review, 'fetch_pr_comments_data', boom)

    read = lane._read_review_surfaces(7, Path('.'))

    assert read['status'] == 'error'
    assert str(raised) in read['error']
