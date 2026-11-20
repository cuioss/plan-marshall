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

import re
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import github_re_review
import pytest

from conftest import get_scripts_dir, load_script_module, parse_ns, run_script

lane = load_script_module('plan-marshall', 'runbook-lane', 'runbook_lane.py', 'runbook_lane_review_gate_mod')

cmd_review_gate = lane.cmd_review_gate

_SCRIPT = get_scripts_dir('plan-marshall', 'runbook-lane') / 'runbook_lane.py'
_SKILL = get_scripts_dir('plan-marshall', 'runbook-lane').parent / 'SKILL.md'

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


#: The `[!CAUTION]` block of CodeRabbit's review body on ``cuioss/plan-marshall#1983``
#: (review ``PRR_kwDOQ3xasM8AAAABX-4gkw``), CAPTURED, in the DISPLAY form the gate parses —
#: the read flattens a body to one line, so the flattened text IS what the parser reads.
#: The bold-line heading, the finding row under it and the ``cr-comment`` marker are
#: verbatim; the nested ``Suggested fix`` ``<details>`` between the prose and the marker,
#: whose diff carries no heading and no count, is omitted.
_CAPTURED_CAUTION_1983 = (
    '> [!CAUTION] > Some comments are outside the diff and can’t be posted inline due to GitHub '
    'limitations. >  > **⚠️ Outside diff range comments (1)** >  > <details> > <summary><strong>'
    '<picture><img src="https://storage.googleapis.com/coderabbit_public_assets/review-comment-icons-v1/'
    'major-16.svg" width="16" height="16" align="absmiddle" alt=""></picture> Major</strong> · Fold '
    'the body before the no-unreviewed-commit literal test. · <code>_github_pr.py:944</code></summary>'
    '<blockquote> > <dl> > <dd> > <br> >  > '
    '`marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py:944` > '
    '**<picture><img src="https://storage.googleapis.com/coderabbit_public_assets/review-comment-icons-v1/'
    'major-16.svg" width="16" height="16" align="absmiddle" alt=""></picture> Major** · '
    '**Functional Correctness** · **Quick win** >  > '
    '**Fold the body before the no-unreviewed-commit literal test.** >  > '
    '`refusal_layers` now matches registry phrases case-insensitively. `refusal_condition` still '
    'matches the sentence-case literals against the raw body. A reply such as '
    '`ALREADY REVIEWED THE LAST COMMIT.` is therefore recognized as a refusal but gets the '
    '`rate_limited` condition. The registry says that condition is awaitable and that the reply is '
    'never waited for. Recovery can then take the wait branch for a reply that opens no window. >  > '
    '<!-- cr-comment:v1:d21c21fd4506d11cecbf67f8 --> >  > _Source: Path instructions_ >  > '
    '</dd> > </dl> > </blockquote></details>'
)

#: The same `[!CAUTION]` shape on ``cuioss/plan-marshall#1984`` (review
#: ``PRR_kwDOQ3xasM8AAAABX_oUvg``), CAPTURED in the display form. Its finding names a
#: different file and span, which is what makes it a second observation rather than a
#: copy of the #1983 one.
_CAPTURED_CAUTION_1984 = (
    '> [!CAUTION] > Some comments are outside the diff and can’t be posted inline due to GitHub '
    'limitations. >  > **⚠️ Outside diff range comments (1)** >  > <details> > <summary><strong>'
    '<picture><img src="https://storage.googleapis.com/coderabbit_public_assets/review-comment-icons-v1/'
    'major-16.svg" width="16" height="16" align="absmiddle" alt=""></picture> Major</strong> · Use '
    'content-based reconciliation before certifying the bridge. · '
    '<code>configure_harness.py:142-144</code></summary><blockquote> > <dl> > <dd> > <br> >  > '
    '`marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/configure_harness.py:142-144` > '
    '**<picture><img src="https://storage.googleapis.com/coderabbit_public_assets/review-comment-icons-v1/'
    'major-16.svg" width="16" height="16" align="absmiddle" alt=""></picture> Major** · '
    '**Data Integrity & Integration** · **Quick win** >  > '
    '**Use content-based reconciliation before certifying the bridge.** >  > '
    'If `CLAUDE.md` changes and the bridge write fails, the existing bridge can retain the current '
    'version marker and stale rules. >  > <!-- cr-comment:v1:20b0cc43aed9f3216ab716e7 --> >  > '
    '_Source: Path instructions_ >  > </dd> > </dl> > </blockquote></details>'
)

#: The status line each review body of #1984 opens with — verbatim. The two bodies count 4
#: and 3, and the gate reads both bodies' counts into one per-reviewer ledger.
_CAPTURED_ACTIONABLE_LINE_1984_FIRST = '<!-- coderabbit-ai-generated:v1 -->  **Actionable comments posted: 4**'
_CAPTURED_ACTIONABLE_LINE_1984_SECOND = '<!-- coderabbit-ai-generated:v1 -->  **Actionable comments posted: 3**'

#: The counted, non-finding file list the review bodies carry — verbatim title, the file
#: rows shortened. It is a BOUNDARY: it ends the CAUTION block's span and mints nothing.
_CAPTURED_FILES_SELECTED_TITLE = (
    '<h6><details><summary><picture><img src="https://storage.googleapis.com/coderabbit_public_assets/'
    'review-comment-icons-v1/info.svg" width="12" height="12" align="absmiddle" alt=""></picture> '
    'Files selected for processing: 15</summary><dl><dd><br>* `a.py`</dd></dl></details></h6>'
)

#: The #1983 review body as the gate reads it: the generated marker, the captured CAUTION
#: block, and the counted file list that closes it. Every part is captured or verbatim.
_CAPTURED_CAUTION_1983_BODY = (
    f'<!-- coderabbit-ai-generated:v1 -->  {_CAPTURED_CAUTION_1983}  {_CAPTURED_FILES_SELECTED_TITLE}'
)

#: The two #1984 review bodies the gate reads, composed from the captured parts above. Both
#: open with their captured status line, and both close with the captured file list.
_CAPTURED_1984_BODY_FIRST = (
    f'{_CAPTURED_ACTIONABLE_LINE_1984_FIRST}  {_CAPTURED_CAUTION_1984}  {_CAPTURED_FILES_SELECTED_TITLE}'
)
_CAPTURED_1984_BODY_SECOND = f'{_CAPTURED_ACTIONABLE_LINE_1984_SECOND}  {_CAPTURED_FILES_SELECTED_TITLE}'

#: The reported `Minor comments` shape, HAND-BUILT here (the consumer repository's body is
#: not readable from this checkout): a `<picture>`-wrapped counted title with one row.
_PICTURE_MINOR_COMMENTS_BODY = (
    '<!-- coderabbit-ai-generated:v1 -->  **Actionable comments posted: 0**  '
    '<details><summary><picture><source media="(prefers-color-scheme: dark)" '
    'srcset="minor-dark.svg"><img src="minor.svg" width="16" height="16" '
    'align="absmiddle" alt=""></picture> Minor comments: 25</summary><blockquote> '
    '<dl><dd>one minor note</dd></dl> </blockquote></details>'
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


def test_an_unrecognised_counted_section_is_counted_not_refused() -> None:
    """A title the parser does not know is findings to dispose of, never a stop.

    The review body never changes between runs, so refusing the whole review on one
    unseen title answered the same `undecidable_read` for ever: the pull request could
    not be merged and no disposition could clear it. Its declared count is findings of
    kind `unclassified`, which the gate blocks on until each one is disposed of.
    """
    body = '<details>\n<summary>🔍 Lint comments (2)</summary>\nuse the helper\n</details>\n'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'body_findings_undisposed'
    assert verdict['review_body_findings_total'] == 2
    assert [row['id'] for row in verdict['undisposed']] == ['unclassified-1', 'unclassified-2']


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
def test_a_counted_title_in_neither_table_reads_its_count_as_unclassified(title: str) -> None:
    """A counted title in neither table is findings, in either count spelling."""
    body = f'<details>\n<summary>{title}</summary>\nuse the helper\n</details>\n'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['reason'] == 'body_findings_undisposed', verdict
    assert verdict['review_body_findings_total'] == 2
    assert [row['id'] for row in verdict['undisposed']] == ['unclassified-1', 'unclassified-2']


def test_each_unclassified_finding_takes_its_own_disposition() -> None:
    """The ledger discharges them one at a time, exactly like every other section's."""
    body = '<details>\n<summary>🔎 Potential issues (2)</summary>\nfirst\nsecond\n</details>\n'
    read = _read(_review_body(body))

    one_disposed = _verdict(read, 'coderabbit unclassified unclassified-1 — abc1234')

    assert one_disposed['reason'] == 'body_findings_undisposed', one_disposed
    assert one_disposed['review_body_findings_handled'] == 1
    assert [row['id'] for row in one_disposed['undisposed']] == ['unclassified-2']

    both_disposed = _verdict(
        read,
        'coderabbit unclassified unclassified-1 — abc1234',
        'coderabbit unclassified unclassified-2 — abc1234',
    )

    assert both_disposed['reason'] == 'all_handled', both_disposed


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


def test_a_decorated_unknown_section_is_counted_as_unclassified() -> None:
    """Bold markers must hide neither a counted section nor the findings it declares."""
    body = '<details>\n<summary>**Lint comments (2)**</summary>\nuse the helper\n</details>\n'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['reason'] == 'body_findings_undisposed', verdict
    assert [row['id'] for row in verdict['undisposed']] == ['unclassified-1', 'unclassified-2']


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


def test_a_picture_wrapped_minor_comments_title_reads_its_declared_findings() -> None:
    """REPORTED from a consumer repository's body, HAND-BUILT here and labelled as such.

    The report (pm-mcp-core#496, relayed through the operator) is a `<picture>`-prefixed
    counted `Minor comments: 25` heading the gate could not map; that body is not readable
    from this checkout, so this fixture reproduces the reported SHAPE and says so rather
    than presenting itself as a capture. One finding row per item, so the declared count is
    the block's findings — of kind `minor`, never `unclassified`.
    """
    read = _read(_review_body(_PICTURE_MINOR_COMMENTS_BODY))

    verdict = _verdict(read)

    assert verdict['reason'] == 'body_findings_undisposed', verdict
    assert verdict['review_body_findings_total'] == 25
    assert [row['id'] for row in verdict['undisposed']] == [f'minor-{n}' for n in range(1, 26)]
    assert {row['section'] for row in verdict['undisposed']} == {'minor'}

    dispositions = tuple(f'coderabbit minor minor-{n} — abc1234' for n in range(1, 26))

    assert _verdict(read, *dispositions)['reason'] == 'all_handled'


def test_the_captured_1983_caution_block_reads_one_outside_diff_finding() -> None:
    """⛔ OBSERVED #1983: the gate read this review body as ZERO findings.

    The heading is a BOLD line inside a `[!CAUTION]` block and the finding rides a
    `<summary>` row that declares no count, so nothing in the `<summary>` heading shape
    named the section. One Major finding went unread and the gate admitted the merge.
    """
    read = _read(_review_body(_CAPTURED_CAUTION_1983_BODY))

    verdict = _verdict(read)

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [(row['section'], row['id']) for row in verdict['undisposed']] == [('outside-diff', 'outside-diff-1')]
    assert verdict['reason'] == 'body_findings_undisposed'

    assert _verdict(read, 'coderabbit outside-diff outside-diff-1 — abc1234')['reason'] == 'all_handled'


def test_the_captured_1984_bodies_read_seven_inline_and_one_outside_diff() -> None:
    """⛔ OBSERVED #1984: two review bodies, and the outside-diff block riding the first.

    The two bodies declare 4 and 3 actionable findings, which the status-line reader mints
    into ONE per-reviewer ledger (inline-1..7), and the `[!CAUTION]` block adds the
    outside-diff finding the bold-line heading now names. The id ORDER is load-bearing: it
    shows the `**Actionable comments posted: N**` line stayed a status line and did not
    become a bold-heading section ahead of the CAUTION block.
    """
    first = _CAPTURED_1984_BODY_FIRST
    second = _CAPTURED_1984_BODY_SECOND
    read = _read(_review_body(first), _review_body(second))

    verdict = _verdict(read)

    assert verdict['review_body_findings_total'] == 8, verdict
    assert [row['id'] for row in verdict['undisposed']] == [
        'outside-diff-1',
        'inline-1',
        'inline-2',
        'inline-3',
        'inline-4',
        'inline-5',
        'inline-6',
        'inline-7',
    ]


def test_the_actionable_status_line_is_not_read_as_a_bold_heading() -> None:
    """`**Actionable comments posted: 4**` is a status line, not an inline section.

    The distinguishing fact is the id ORDER: read as a heading, it would mint its four
    inline findings ahead of the nitpick; read as the status line the inline-count reader
    owns, the nitpick comes first and the four follow, which is one attribution per
    declaration and no double count.
    """
    body = (
        '**Actionable comments posted: 4**\n'
        '<details>\n<summary>🧹 Nitpick comments (1)</summary><blockquote>\n'
        '<dl><dd>rename the helper</dd></dl>\n'
        '</blockquote></details>\n'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 5, verdict
    assert [row['id'] for row in verdict['undisposed']] == [
        'nitpick-1',
        'inline-1',
        'inline-2',
        'inline-3',
        'inline-4',
    ]


def test_a_counted_per_file_group_under_an_unclassified_heading_is_content() -> None:
    """The nested per-file counts belong to the heading above them, once each.

    Reading each nested group as its own `unclassified` heading would count the block
    twice: the heading's declared 2 AND the two per-file groups' 1s.
    """
    body = (
        '<details><summary>🔎 Potential issues (2)</summary><blockquote>'
        '<details><summary>src/a.py (1)</summary>rename the helper</details>'
        '<details><summary>src/b.py (1)</summary>drop the import</details>'
        '</blockquote></details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 2, verdict
    assert [row['id'] for row in verdict['undisposed']] == ['unclassified-1', 'unclassified-2']


def test_a_counted_row_inside_a_bold_headed_block_belongs_to_that_block() -> None:
    """The CAUTION block's rows are its content, whatever they declare.

    A per-file row that carries its own count is the block's finding, not a second
    section: counting it separately would report one finding twice.
    """
    body = (
        '> [!CAUTION] > **⚠️ Outside diff range comments (1)** >  > <details> > '
        '<summary>Major · src/a.py (2)</summary> > the guard coerces UNKNOWN > </details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [(row['section'], row['id']) for row in verdict['undisposed']] == [('outside-diff', 'outside-diff-1')]


def test_a_section_following_a_bold_headed_block_is_still_counted() -> None:
    """⛔ A bold heading owns ONE block; a section in the next one is a section.

    Reading every block opened after a bold heading as that heading's row would drop the
    findings of a section that merely follows it — the under-count this gate exists to
    prevent, and the shape a CAUTION block sits beside in real bodies.
    """
    body = (
        '> [!CAUTION] > **⚠️ Outside diff range comments (1)** >  > <details> > '
        '<summary>Major · x · <code>a.py:3</code></summary> > the guard coerces UNKNOWN > </details> '
        '<details><summary>🧹 Nitpick comments (2)</summary><blockquote> first second </blockquote></details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 3, verdict
    assert [row['id'] for row in verdict['undisposed']] == ['outside-diff-1', 'nitpick-1', 'nitpick-2']


def test_a_label_shaped_quote_in_a_row_body_is_not_a_heading() -> None:
    """⛔ A quoted section title must not end the enclosing section's span.

    The quote sits after a `<code>` sample inside the row's `<dd>`. Reading it as a
    heading would end the nitpick span at the quote and lose the row marker after it —
    a silent under-count of exactly the finding the row states.
    """
    body = (
        '<details><summary>🧹 Nitpick comments</summary><blockquote><dl><dd>'
        'see <code>a.py:3</code> **Outside diff range comments (1)** rename the helper '
        '<!-- cr-comment:v1:aaaaaaaaaaaaaaaaaaaaaaaa -->'
        '</dd></dl></blockquote></details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [(row['section'], row['id']) for row in verdict['undisposed']] == [('nitpick', 'nitpick-1')]


def test_an_unclosed_bold_block_owns_nothing() -> None:
    """⛔ An unbalanced `<details>` must not swallow every section after it — and must not pass.

    A block with no matching close cannot be shown to end anywhere, so the heading owns
    nothing; and because the heading declares findings over a block nobody can read, the body
    is a stop rather than an `all_handled`.
    """
    body = (
        '**⚠️ Outside diff range comments (1)** <details> <summary>Major · a.py</summary> fix '
        '<summary>🧹 Nitpick comments (2)</summary> a b'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert 'never closed' in verdict['detail']


def test_a_bold_mention_in_prose_owns_no_block_and_mints_nothing() -> None:
    """⛔ A heading quoted in a sentence is not a heading.

    An ordinary row block follows the sentence and the section comes after it, so the fixture
    discriminates: without the adjacency guard the mention would own that row block and mint
    `outside-diff-1`. Minting the span as a heading would leave a phantom finding that
    survives every disposition of the real ones.
    """
    body = (
        '**Outside diff range comments (1)** is empty this time. '
        '<details><summary>Major · a.py</summary> fix </details>'
        '<details><summary>🧹 Nitpick comments (2)</summary><blockquote> a b </blockquote></details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 2, verdict
    assert [row['id'] for row in verdict['undisposed']] == ['nitpick-1', 'nitpick-2']


def test_a_bold_label_quoted_in_a_code_span_is_not_a_heading() -> None:
    """⛔ A label inside backticks is a quotation, and owns nothing."""
    body = (
        'The rule reads `**Outside diff range comments (1)**` in the lane text. '
        '<details><summary>Notes</summary> prose only </details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 0, verdict


def test_an_unclosed_adjacent_row_block_stops_the_gate() -> None:
    """⛔ A declared heading beside a block that never closes is a stop, not a silent zero."""
    body = '**Outside diff range comments (1)** <details><summary>Major · a.py</summary> fix'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert 'never closed' in verdict['detail']


def test_a_bold_heading_does_not_own_a_bare_counted_section() -> None:
    """⛔ `Potential issues (2)` is a section; `Major · a.py (2)` is a row.

    Extending the bold heading's ownership over the sibling section would drop its two
    findings, and disposing the heading's one finding would then clear the gate.
    """
    body = (
        '**Outside diff range comments (1)** '
        '<details><summary>Major · a.py (2)</summary> fix </details>'
        '<details><summary>🔎 Potential issues (2)</summary> first second </details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 3, verdict
    assert [row['section'] for row in verdict['undisposed']] == ['outside-diff', 'unclassified', 'unclassified']


def test_an_outer_section_reads_the_rows_below_a_nested_bold_heading() -> None:
    """⛔ A nested bold section must not end the outer section's scan.

    One marked nitpick row sits before the nested CAUTION section and one after it; both are
    the outer section's, and the nested heading's own interval is counted by the nested
    heading.
    """
    body = (
        '<details><summary>🧹 Nitpick comments</summary><blockquote>'
        'first <!-- cr-comment:v1:aaaaaaaaaaaaaaaaaaaaaaaa --> '
        '**Outside diff range comments (1)** '
        '<details><summary>Major · b.py</summary> fix </details> '
        'second <!-- cr-comment:v1:bbbbbbbbbbbbbbbbbbbbbbbb -->'
        '</blockquote></details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 3, verdict
    assert [row['section'] for row in verdict['undisposed']] == ['nitpick', 'nitpick', 'outside-diff']


def test_a_br_tag_between_a_bold_heading_and_its_block_is_markup() -> None:
    """`<br>` is markup, not prose: the heading still owns the block below it."""
    body = (
        '**Outside diff range comments (1)**<br>'
        '<details><summary>Major · src/a.py (2)</summary> the guard coerces UNKNOWN </details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [row['id'] for row in verdict['undisposed']] == ['outside-diff-1']


def test_a_bold_heading_does_not_own_a_declared_non_finding_list() -> None:
    """⛔ Ownership stops at a file list, so its 15 rows are never the heading's findings."""
    body = (
        '**Outside diff range comments** '
        '<details><summary>Major · a.py</summary> fix <!-- cr-comment:v1:aaaaaaaaaaaaaaaaaaaaaaaa --> </details>'
        '<details><summary>Files selected for processing: 15</summary> * `a.py` </details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [row['id'] for row in verdict['undisposed']] == ['outside-diff-1']


def test_an_unclosed_code_sample_does_not_pair_with_a_later_close() -> None:
    """⛔ A close tag in a LATER block must not close an opener in this one.

    Pairing them would spread the prose region over the CAUTION heading between them, and its
    finding would never reach the gate.
    """
    body = (
        '<details><summary>🧹 Nitpick comments (1)</summary><blockquote>'
        '<dl><dd>see <code>a.py:3 and the guard </dd></dl></blockquote></details> '
        '**Outside diff range comments (1)** '
        '<details><summary>Major · b.py</summary> see <code>b.py:9</code> </details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert [row['section'] for row in verdict['undisposed']] == ['nitpick', 'outside-diff'], verdict


def test_a_bold_heading_owns_consecutive_sibling_blocks() -> None:
    """An undeclared bold heading counts the row markers of BOTH blocks it introduces."""
    body = (
        '**Outside diff range comments** '
        '<details><summary>Major · a.py</summary> first <!-- cr-comment:v1:aaaaaaaaaaaaaaaaaaaaaaaa --> </details>'
        '<details><summary>Major · b.py</summary> second <!-- cr-comment:v1:bbbbbbbbbbbbbbbbbbbbbbbb --> </details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 2, verdict
    assert [row['id'] for row in verdict['undisposed']] == ['outside-diff-1', 'outside-diff-2']


def test_an_implausible_declared_count_stops_the_gate() -> None:
    """⛔ A body declaring more findings than the gate enumerates is a stop, not an allocation.

    Refusing with a named cause keeps a hostile or broken title from exhausting the process,
    and — unlike clipping — it cannot let a partial disposition list clear the block.
    """
    body = '<details><summary>🔎 Potential issues (999999)</summary> one row </details>'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert 'this gate will enumerate' in verdict['detail']


def test_a_bold_heading_does_not_swallow_a_nested_findings_section() -> None:
    """A declared bold heading beside a nested findings section counts BOTH.

    The heading's own count and the nested section's findings are two statements; treating
    the section as the heading's row would lose the section.
    """
    body = (
        '**Outside diff range comments (1)** '
        '<details><summary>Major · a.py</summary> fix '
        '<details><summary>🧹 Nitpick comments (2)</summary> a b </details>'
        '</details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 3, verdict
    assert [row['id'] for row in verdict['undisposed']] == ['outside-diff-1', 'nitpick-1', 'nitpick-2']


def test_an_unclosed_code_sample_does_not_hide_a_later_bold_heading() -> None:
    """⛔ One unterminated `<code>` must not silence every heading after it.

    The open region stops at the end of the block it sits in, so the CAUTION heading below
    is still read.
    """
    body = (
        '<details><summary>🧹 Nitpick comments (1)</summary><blockquote>'
        '<dl><dd>see <code>a.py:3 and the guard </dd></dl></blockquote></details> '
        '**Outside diff range comments (1)** <details><summary>Major · b.py</summary> fix </details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert [row['section'] for row in verdict['undisposed']] == ['nitpick', 'outside-diff'], verdict


def test_a_counted_group_nested_deep_inside_a_bold_block_is_not_counted_twice() -> None:
    """⛔ A row nested one block deeper is still the bold heading's row, not a section.

    The nested group's own `<details>` is not the owned opener, so a filter keyed on the
    innermost opener would miss it: it would be minted as its own section AND summed into
    the heading's count.
    """
    body = (
        '> [!CAUTION] > **Outside diff range comments** >  > <details> > '
        '<summary>Major · a.py</summary> > '
        '<details><summary>src/a.py (2)</summary> > first > second > </details> '
        '> </details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 2, verdict
    assert [row['section'] for row in verdict['undisposed']] == ['outside-diff', 'outside-diff']


def test_a_bold_heading_mentioned_in_a_sentence_mints_nothing_but_one_over_a_row_counts() -> None:
    """⛔ The mention rule is scoped to the SENTENCE, not to a prose row on its own line.

    Until PLAN-LB-168 this fixture pinned a broader rule: a bold label with no `<details>`
    after it always minted nothing. That rule was the under-count path D1 closes, so the
    reason is now the mention: prose on the SAME line as the closing marker continues the
    heading's own sentence (`**…(1)** > nothing to expand`), which makes it a quotation of
    a heading rather than a heading over what follows. A counted heading on its own line
    above a prose row is counted instead — the second fixture below, which the old rule
    read as zero.

    The summary below is at the TOP level: the mention must not swallow it, and it does not
    — the summary is counted and nothing else is.
    """
    body = (
        '> [!CAUTION] > **⚠️ Outside diff range comments (1)** > nothing to expand '
        '<summary>🧹 Nitpick comments (2)</summary> rename the helper'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 2, verdict
    assert [row['id'] for row in verdict['undisposed']] == ['nitpick-1', 'nitpick-2']

    row_body = (
        '> [!CAUTION]\n'
        '> **⚠️ Outside diff range comments (1)**\n'
        '> nothing to expand\n'
        '<summary>🧹 Nitpick comments (2)</summary> rename the helper'
    )

    row_verdict = _verdict(_read(_review_body(row_body)))

    assert row_verdict['review_body_findings_total'] == 3, row_verdict
    assert [row['section'] for row in row_verdict['undisposed']] == ['outside-diff', 'nitpick', 'nitpick']


def test_a_bold_label_closing_its_block_owns_no_following_section() -> None:
    """⛔ The label sits at a depth whose block closes before the next section opens.

    A bold label that ends the block it lives in owns nothing that follows: that is another
    section's block, and its findings are not the label's rows. The label also mints nothing,
    so the section below is the only thing the body reports.
    """
    body = (
        '<details><summary>ℹ️ Review info</summary> **Outside diff range comments (1)** </details>'
        '<details><summary>🧹 Nitpick comments (2)</summary><blockquote> first second </blockquote></details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 2, verdict
    assert [row['id'] for row in verdict['undisposed']] == ['nitpick-1', 'nitpick-2']


def test_a_block_whose_summary_names_a_section_belongs_to_that_section() -> None:
    """A block opening with a findings-section summary is that section's, not the bold line's.

    Handing it to the bold heading would read a nitpick section as outside-diff rows; leaving
    it to the section keeps its findings (and the bold heading, owning nothing, adds none).
    """
    body = '**Outside diff range comments** <details><summary>🧹 Nitpick comments (2)</summary> first second </details>'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 2, verdict
    assert [(row['section'], row['id']) for row in verdict['undisposed']] == [
        ('nitpick', 'nitpick-1'),
        ('nitpick', 'nitpick-2'),
    ]


def test_a_bold_heading_in_the_colon_count_spelling_declares_its_count() -> None:
    """Both count spellings are counts, on a BOLD heading as on a `<summary>` one."""
    body = (
        '> [!CAUTION] > **Outside diff range comments: 2** >  > <details> > '
        '<summary>Major · src/a.py</summary> > first > </details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 2, verdict
    assert [row['id'] for row in verdict['undisposed']] == ['outside-diff-1', 'outside-diff-2']


def test_a_bold_heading_with_no_declared_count_counts_its_rows() -> None:
    """A bold heading that declares no count is counted from the rows below it."""
    body = (
        '> [!CAUTION] > **Outside diff range comments** >  > <details> > '
        '<summary>Major · src/a.py</summary> > the guard coerces UNKNOWN '
        '<!-- cr-comment:v1:aaaaaaaaaaaaaaaaaaaaaaaa --> > </details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [row['id'] for row in verdict['undisposed']] == ['outside-diff-1']


def test_unclassified_findings_are_numbered_across_review_bodies() -> None:
    """One disposition must discharge one finding, across bodies as within one."""
    body = '<details><summary>🔎 Potential issues (1)</summary>use the helper</details>'

    verdict = _verdict(_read(_review_body(body), _review_body(body)))

    assert verdict['review_body_findings_total'] == 2, verdict
    assert [row['id'] for row in verdict['undisposed']] == ['unclassified-1', 'unclassified-2']


def test_a_top_level_per_file_summary_is_unclassified_findings() -> None:
    """An observed per-file grouping with no recognised section above it is still counted."""
    body = '<details><summary>src/a.py (3)</summary> rename the helper </details>\n'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['reason'] == 'body_findings_undisposed', verdict
    assert verdict['review_body_findings_total'] == 3
    assert [row['id'] for row in verdict['undisposed']] == [
        'unclassified-1',
        'unclassified-2',
        'unclassified-3',
    ]


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


def test_a_read_without_a_coverage_signal_is_undecidable() -> None:
    """A read that publishes no coverage signal cannot be shown whole.

    The GitHub read always publishes ``complete``, so an envelope without it is a
    malformed or truncated one: the gate stops on it, exactly as it stops on an
    incomplete read, rather than inventing a verdict of its own.
    """
    read = _read(_review_body('**Actionable comments posted: 0**'))
    del read['complete']

    verdict = _verdict(read)

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert 'no completeness signal' in verdict['detail']
    assert 'truncated' not in verdict['detail'], 'an absent coverage key is not a drained-connection report'


def _documented_review_gate_reasons() -> set[str]:
    """The reason tokens the lane text's ``review-gate`` section states as verdicts.

    EVERY paragraph that states a verdict contributes, not only the refusal list: the
    provider paragraph below it names ``undecidable_read`` in running prose, and a pin
    that read the first paragraph alone let a stale reason survive there.

    A reason is a token in a VERDICT position — the parenthesised reason of a refusal, or
    the token the verb "answers" — because the same paragraphs spell section names, the
    count keys and ``reason`` itself in backticks, and those are not reasons.
    """
    text = _SKILL.read_text(encoding='utf-8')
    section = text.split('### review-gate', 1)[1].split('\n## ', 1)[0]
    paragraphs = [
        paragraph for paragraph in section.split('\n\n') if '`merge_allowed' in paragraph or 'answers `' in paragraph
    ]
    reasons: set[str] = set()
    for paragraph in paragraphs:
        reasons.update(re.findall(r'\(`([a-z][a-z_]*)`', paragraph))
        reasons.update(re.findall(r'answers `([a-z][a-z_]*)`', paragraph))
        reasons.update(re.findall(r'with `([a-z][a-z_]*)`', paragraph))
    return reasons


def _reasons_the_verdict_can_return() -> set[str]:
    """The ``reason`` literals inside ``_review_gate_verdict`` — no other verb's."""
    source = _SCRIPT.read_text(encoding='utf-8')
    start = source.index('def _review_gate_verdict(')
    end = source.index('\ndef cmd_review_gate(', start)
    return set(re.findall(r"'reason': '([a-z][a-z_]*)'", source[start:end]))


def test_the_lane_text_names_no_reason_the_verdict_cannot_return() -> None:
    """⛔ Every reason the contract names is one the verdict can actually answer.

    A refusal reason the verb cannot return describes a decision the code cannot make,
    so a reader who hits it looks for a remedy that does not exist. The documented list
    is read from the ``review-gate`` section and compared with the reason literals
    ``_review_gate_verdict`` returns.
    """
    documented = _documented_review_gate_reasons()
    produced = _reasons_the_verdict_can_return()

    assert 'undecidable_read' in documented, 'the review-gate reason list was not found in the lane text'
    assert documented <= produced, f'named in the lane text but unreachable: {sorted(documented - produced)}'


def test_the_documented_reasons_cover_the_provider_paragraph_too() -> None:
    """⛔ A reason named in the provider paragraph must be one the verb can return.

    The provider paragraph states a reason of its own, in running prose rather than in the
    refusal list. A pin scoped to that list never read it, so a stale reason — one the code
    cannot answer — could sit there and pass. This reads the paragraph's own statement and
    checks it against the code's reason literals.
    """
    section = _SKILL.read_text(encoding='utf-8').split('### review-gate', 1)[1].split('\n## ', 1)[0]
    provider_paragraph = next(paragraph for paragraph in section.split('\n\n') if 'The read is GitHub' in paragraph)
    named = set(re.findall(r'answers `([a-z][a-z_]*)`', provider_paragraph))

    assert named, 'the provider paragraph names no reason any more — re-point this pin'
    produced = _reasons_the_verdict_can_return()
    assert named <= produced, f'named in the provider paragraph but unreachable: {sorted(named - produced)}'


def _section_seven() -> str:
    """The lane text's section 7, the merge gate, on one line for prose assertions."""
    text = _SKILL.read_text(encoding='utf-8')
    section = text.split('\n## 7. Merge gate', 1)[1].split('\n## 8. ', 1)[0]
    return ' '.join(section.split())


def test_the_merge_gate_states_the_reach_of_an_operator_selection() -> None:
    """⛔ A selection covers later heads only while they add no new logic.

    The rule has to be READABLE and testable from the document alone: the operational
    test is the path list of the diff between the selected head and the merge head, and
    the direction is fail-closed. Without it a lane merged on a record the operator made
    over a head they had seen, while a later head moved production code under it.
    """
    section = _section_seven()

    assert 'diff --name-only --no-renames {selected_head} {merge_head}' in section
    assert 'adds no new logic when' in section
    assert 'documentation (`.md`, `.adoc`) or a test file' in section
    assert 'the default fails closed' in section
    assert 'puts the head to the operator again' in section


def test_the_merge_gate_restates_the_two_rulings_about_the_standing_authorization() -> None:
    """The lane does not read the ledger, so the rulings it must not re-litigate are here."""
    section = _section_seven()

    assert 'because the lane does not read the ledger' in section
    assert 'stays as written' in section
    assert 'CHANGED logic' in section
    assert 'covered by that authorization' in section


def test_the_refusal_record_docstring_states_the_scope_the_record_has() -> None:
    """⛔ The module header must not claim the record covers a skip it never sees.

    The same module's later paragraph says a skip a gate AHEAD of the refusal test drops
    is "skipped with no record". The header said both discriminators "append every refusal
    they skip", which is the opposite claim, so a reader trusting it would read a missing
    record as a refusal that never happened.
    """
    source = Path(github_re_review.__file__).read_text(encoding='utf-8')
    header = source.split('**A rejected refusal is RECORDED', 1)[1].split('Accepted tradeoff', 1)[0]

    assert 'every refusal the refusal test reaches' in header.lower(), header
    assert 'append every refusal they skip' not in header


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
        _read(_review_body('<details><summary>🔎 Potential issues (2)</summary>use the helper</details>')),
        _read(_review_body(_PICTURE_MINOR_COMMENTS_BODY)),
        _read(_review_body(_CAPTURED_CAUTION_1983_BODY)),
    ],
    ids=[
        'body-finding',
        'nitpicks-and-follow-ups',
        'concern-remains',
        'concern-remains-after-lane-reply',
        'undecidable',
        'unclassified-section',
        'minor-comments',
        'caution-outside-diff',
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


def _forbid_cli(*_args, **_kwargs):
    """The single-fetch pin: no CLI may be spawned for the gate's read.

    ``pytest.fail`` raises a ``BaseException``, so ``ci_base.run_cli``'s blanket
    ``except Exception`` cannot swallow it: a read routed through the CLI helper trips
    this pin exactly as a direct ``subprocess.run`` does.
    """
    pytest.fail('the review gate must not spawn a CLI for its read')


@pytest.mark.usefixtures('restore_default_cwd')
def test_the_gate_fetches_the_surface_once_and_spawns_no_cli(monkeypatch, outside_repo_dir) -> None:
    """⛔ ONE fetch decides the whole verdict: threads, findings and reviews.

    The gate takes the provider's data once, in-process, and derives the flattened
    display form itself — asserted here by counting fetches AND by pinning that no CLI
    is spawned at all. The directory carries no ``.plan/marshal.json``, so a route read
    from the filesystem would stop the gate before the fetch; the module fixture pins
    the route, and the fetch count is what proves the read happened exactly once.
    """
    fetches: list[int] = []

    def fake_fetch(pr_number, unresolved_only=False):
        fetches.append(pr_number)
        return _raw_read([])

    monkeypatch.chdir(outside_repo_dir)
    monkeypatch.setattr(github_re_review, 'fetch_pr_comments_data', fake_fetch)
    monkeypatch.setattr('subprocess.run', _forbid_cli)

    verdict = cmd_review_gate(_args_with_reviewers('coderabbit'))

    assert fetches == [7], 'exactly one provider fetch per verdict'
    assert verdict['reason'] == 'required_review_missing'


def test_the_no_cli_pin_trips_for_a_read_routed_through_run_cli(monkeypatch) -> None:
    """⛔ ``ci_base.run_cli`` swallows every ``Exception``, so the pin is not one.

    A second read routed through the CLI helper is invisible to a pin that raises an
    ``Exception``: ``run_cli`` catches it and returns a failure tuple. This asserts the
    pin's own escape, which is what makes such a read fail the single-fetch test
    instead of passing silently.
    """
    import ci_base

    monkeypatch.setattr('subprocess.run', _forbid_cli)

    with pytest.raises(pytest.fail.Exception, match='must not spawn'):
        ci_base.run_cli('gh', ['pr', 'view'])


@pytest.mark.parametrize('provider', ['gitlab', None])
def test_a_project_that_does_not_route_to_github_is_never_read(monkeypatch, provider) -> None:
    """⛔ The provider gate runs BEFORE the fetch, so no foreign surface is read.

    The read is gated on the route, not on ``gh`` failing: a project configured for
    another provider, sitting in a GitHub-resolvable checkout, would otherwise read an
    empty GitHub comment set and answer ``all_handled`` over comments its own CI never
    publishes.
    """
    import ci_base

    fetched: list[int] = []

    def record_fetch(pr_number, **_kwargs):
        fetched.append(pr_number)
        return _raw_read([])

    monkeypatch.setattr(ci_base, 'resolve_ci_provider', lambda _project_dir: provider)
    monkeypatch.setattr(github_re_review, 'fetch_pr_comments_data', record_fetch)

    read = lane._read_review_surfaces(7, Path('.'))

    assert read['status'] == 'error'
    assert (provider or 'no resolvable CI provider') in read['error']
    assert fetched == [], 'the fetch must not run for a provider the gate cannot read'


def test_the_read_runs_in_the_project_it_was_handed(monkeypatch) -> None:
    """The one fetch is routed to ``project_dir``, which is how ``gh`` finds the repo."""
    import ci_base

    original = ci_base.get_default_cwd()
    monkeypatch.setattr(ci_base, 'resolve_ci_provider', lambda _project_dir: 'github')
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
# the opener must start a line — refuses the claim, and a display read would destroy
# the line structure that rule reads.
#
# These tests stub ONE read seam — ``github_re_review.fetch_pr_comments_data``, the
# single in-process fetch — so the lane's own read functions and its predicate site run
# for real. The provider resolver is stubbed too, by the module's ``github_provider``
# fixture: it pins the route, not the data the gate reads.

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


@pytest.fixture(autouse=True)
def github_provider(monkeypatch):
    """Route the read to GitHub, independent of the ambient project configuration.

    ``resolve_ci_provider`` walks up from the project directory the gate is handed, so
    a read driven against ``'.'`` would otherwise depend on the ``.plan/marshal.json``
    above whatever directory the suite happens to run from. Autouse, so no test that
    drives the real read can forget it.
    """
    import ci_base

    monkeypatch.setattr(ci_base, 'resolve_ci_provider', lambda _project_dir: 'github')


def _verdict_through_the_read_seams(
    monkeypatch,
    raw_comments: list[dict],
    *,
    raw_read: dict | None = None,
    reviewers: tuple[str, ...] = ('coderabbit',),
) -> Any:
    """Drive ``review-gate`` with only the ONE fetch stubbed.

    No subprocess and no TOON: the gate fetches once, in-process, and derives the
    display form itself. A test that had to stub a second transport would be proof
    the gate reads the surface twice. The provider resolver is pinned by the module
    fixture, so the outcome never depends on the ambient project configuration.
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


@pytest.mark.usefixtures('restore_default_cwd')
def test_a_comment_entry_that_cannot_be_flattened_is_undecidable(monkeypatch) -> None:
    """⛔ A malformed comment entry is classified, never a traceback.

    The flatten reads every entry before the dict filter, so an entry that is not a
    mapping raises there. A crash states no verdict at all, so the gate answers
    ``undecidable_read`` and names the failure it hit.
    """
    verdict = _verdict_through_the_read_seams(
        monkeypatch,
        [],
        raw_read={'status': 'success', 'complete': True, 'comments': ['not-a-comment']},
    )

    assert verdict['merge_allowed'] is False, verdict
    assert verdict['reason'] == 'undecidable_read', verdict
    assert 'display form' in verdict['detail'], verdict


@pytest.mark.usefixtures('restore_default_cwd')
def test_the_read_classifies_an_unimportable_provider_module(monkeypatch) -> None:
    """⛔ The imports sit inside the guard, so a broken import is a classified stop.

    A ``None`` entry in ``sys.modules`` makes the import statement itself raise
    ``ImportError`` rather than the fetch, so a green classified read here is what
    shows the imports were not hoisted above the ``try``.
    """
    monkeypatch.setitem(sys.modules, 'ci_base', None)

    read = lane._read_review_surfaces(7, Path('.'))

    assert read['status'] == 'error'
    assert 'ci_base' in read['error']


@pytest.mark.usefixtures('restore_default_cwd')
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


# ---------------------------------------------------------------------------
# The four under-count paths of PLAN-LB-162 (PLAN-LB-168)
#
# The one direction this gate never takes is FEWER findings than the body
# declares. Each case below is HAND-BUILT from the path traced in PLAN-LB-168
# (the review bodies that produced them are not readable from this checkout):
# the shape is reproduced and asserted either as the declared count or as a
# NAMED stop, never as a silent zero.
# ---------------------------------------------------------------------------


def test_a_counted_bold_heading_over_plain_markdown_rows_mints_its_declared_count() -> None:
    """⛔ D1: a counted bold heading whose rows are plain markdown owns no block.

    HAND-BUILT from the under-count PLAN-LB-168 D1 traces: the heading declares one
    finding and the row below it is a bullet, with no `<details>` anywhere to own. The
    old ownership rule read "owns no block" as "mints nothing", so the declaration
    became zero findings and the gate could answer `all_handled` over it.
    """
    body = '**⚠️ Outside diff range comments (1)**\n\n- `src/a.py:12` rename the helper\n'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [(row['section'], row['id']) for row in verdict['undisposed']] == [('outside-diff', 'outside-diff-1')]


def test_a_counted_bold_heading_before_a_section_block_mints_its_declared_count() -> None:
    """⛔ D1: a counted bold heading followed directly by a SECTION block.

    HAND-BUILT from the second D1 shape: the block below the heading opens a findings
    section, so the heading owns nothing — and its declaration used to be dropped while
    the section's own two findings were counted. The declaration is read as one finding
    beside the section's two.
    """
    body = (
        '**⚠️ Outside diff range comments (1)**\n\n'
        '<details><summary>🧹 Nitpick comments (2)</summary> first second </details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 3, verdict
    assert [row['section'] for row in verdict['undisposed']] == ['outside-diff', 'nitpick', 'nitpick']


def test_a_counted_bold_heading_before_a_file_list_mints_its_declared_count() -> None:
    """⛔ D1: a counted bold heading followed directly by a file-list block.

    HAND-BUILT from the third D1 shape: the file list is a declared non-finding block, so
    the heading owns nothing and the block mints nothing — which left the heading's own
    declaration unread. It is now counted; the file list stays a boundary and adds none.
    """
    body = (
        '**⚠️ Outside diff range comments (1)**\n\n'
        '<details><summary>Files selected for processing: 15</summary> * `a.py` </details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [(row['section'], row['id']) for row in verdict['undisposed']] == [('outside-diff', 'outside-diff-1')]


def test_a_counted_unknown_wrapper_reads_the_recognised_section_it_encloses() -> None:
    """⛔ D2: a counted wrapper must not swallow the recognised section inside it.

    The input is PLAN-LB-168's own: `Review (1)` reads as an `unclassified` heading, the
    nested nitpick section became its CONTENT, and the wrapper's declared 1 won over the
    section's declared 10 — ten findings the body states and the gate never read. The
    wrapper is now read through and the section is counted as a section.
    """
    body = (
        '<details><summary>Review (1)</summary>'
        '<details><summary>🧹 Nitpick comments (10)</summary>'
        ' one two three four five six seven eight nine ten </details>'
        '</details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict.get('review_body_findings_total') == 10, verdict
    assert [row['id'] for row in verdict['undisposed']] == [f'nitpick-{n}' for n in range(1, 11)]


def test_a_counted_wrapper_carrying_content_beside_a_section_stops_the_gate() -> None:
    """⛔ D2: a wrapper whose own content sits beside the section is a stop, not a guess.

    Reading the wrapper through would drop whatever it says outside the section it
    encloses, so that shape stops with a cause naming the wrapper instead of counting
    fewer findings than the body states.
    """
    body = (
        '<details><summary>Review (1)</summary> read the section below '
        '<details><summary>🧹 Nitpick comments (2)</summary> a b </details>'
        '</details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['merge_allowed'] is False, verdict
    assert verdict['reason'] == 'undecidable_read', verdict
    assert 'wrapper' in verdict['detail'], verdict


def test_a_stray_bold_marker_earlier_in_the_body_does_not_shift_the_heading_pairing() -> None:
    """⛔ D3: an unpaired `**` earlier in the body must not consume the heading's opener.

    PLAN-LB-168's own input: `**kwargs` pairs the first two markers, so the real CAUTION
    heading's opening marker is spent as the closing one and the heading is never read.
    The heading is now read, and its finding counted.
    """
    body = 'x **kwargs y **⚠️ Outside diff range comments (1)** <details><summary>Major · a.py</summary> fix </details>'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [(row['section'], row['id']) for row in verdict['undisposed']] == [('outside-diff', 'outside-diff-1')]


def test_a_stray_backtick_earlier_in_the_body_does_not_hide_the_heading() -> None:
    """⛔ D3: the backtick filter pairs markers the same way, and hides a real heading.

    HAND-BUILT from the stray-backtick half of D3: one unmatched backtick turns everything
    up to the next one into a code span, and a heading inside that span was read as a
    QUOTE and dropped. A quotation is a code span that holds the heading and nothing else;
    this span holds prose, so the heading is read.
    """
    body = (
        'Run `x and see **⚠️ Outside diff range comments (1)** '
        '<details><summary>Major · a.py</summary> fix </details> before `y`'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [(row['section'], row['id']) for row in verdict['undisposed']] == [('outside-diff', 'outside-diff-1')]


def test_an_unclosed_code_in_a_nested_block_does_not_hide_a_heading_in_the_outer_block() -> None:
    """⛔ D4: an unclosed `<code>` is bounded by its own block at every depth.

    PLAN-LB-168's own input: the prose scan started at the innermost block still open at the
    heading — the outer wrapper here — so the inner block's unclosed `<code>` kept the code
    depth at 1 across the boundary and the CAUTION heading after it was read as prose, losing
    one declared finding. The scan is now per block, so the inner block's prose ends with it.
    """
    body = (
        '<details><summary>Walkthrough</summary>'
        '<details><summary>🧹 Nitpick comments (1)</summary><dd>see <code>a.py </dd></details> '
        '**Outside diff range comments (1)** <details><summary>Major · b.py</summary>fix</details>'
        '</details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert [row['section'] for row in verdict['undisposed']] == ['nitpick', 'outside-diff'], verdict


def test_a_dd_spanning_a_nested_block_keeps_the_heading_inside_it_a_quotation() -> None:
    """⛔ Round-1 guard (not red before the fix): a row body is prose for its WHOLE block.

    The `<dd>` opens in the outer block, a nested `<details>` opens and closes inside it, and a
    heading-shaped bold span sits after that nested block but still inside the `<dd>`. A prose
    scope that reset at the nested block would read the quote as a heading and mint a finding
    nobody wrote; the scope is per block, so the quote stays a quotation. This pins the shape a
    first, simpler prose bound broke, so it is a guard on the fix rather than on the defect.
    """
    body = (
        '<details><summary>🧹 Nitpick comments (1)</summary><dd> see '
        '<details><summary>src/a.py (2)</summary>x</details> '
        '**Outside diff range comments (1)** </dd></details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [(row['section'], row['id']) for row in verdict['undisposed']] == [('nitpick', 'nitpick-1')]


def test_a_blockless_counted_heading_nested_in_a_section_does_not_cut_its_rows() -> None:
    """⛔ D1's nesting edge: a nested counted heading must not END the section's span.

    The nitpick section carries three marked rows, one before a blockless counted CAUTION
    heading and two after it. Ending the section's span at that heading would lose the two
    after it while the heading's own declaration counted once — fewer findings than the body
    states. The heading is excluded from the boundary scan instead, so the section reads all
    three rows and the heading adds its own declaration.
    """
    body = (
        '<details><summary>🧹 Nitpick comments</summary><blockquote>'
        ' first <!-- cr-comment:v1:aaaaaaaaaaaaaaaaaaaaaaaa --> '
        '**Outside diff range comments (1)** - `src/a.py:12` rename '
        'second <!-- cr-comment:v1:bbbbbbbbbbbbbbbbbbbbbbbb --> '
        'third <!-- cr-comment:v1:cccccccccccccccccccccccc --> '
        '</blockquote></details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 4, verdict
    assert [row['section'] for row in verdict['undisposed']] == [
        'nitpick',
        'nitpick',
        'nitpick',
        'outside-diff',
    ]


def test_a_counted_wrapper_carrying_content_after_its_section_stops_the_gate() -> None:
    """⛔ D2: the wrapper's own content AFTER the enclosed section is a stop too.

    Reading through drops whatever the wrapper says beside the section it encloses, wherever
    that text sits. Content between or after the enclosed sections is as unattributable as
    content before them, so the whole interior is measured, not only the prefix.
    """
    body = (
        '<details><summary>Review (2)</summary>'
        '<details><summary>🧹 Nitpick comments (1)</summary>a</details>'
        ' a second concern of its own </details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['merge_allowed'] is False, verdict
    assert verdict['reason'] == 'undecidable_read', verdict
    assert 'wrapper' in verdict['detail'], verdict


def test_a_heading_glued_to_markup_is_still_read() -> None:
    """⛔ D3: an opener glued to punctuation (`>**⚠️ …**`) is an opener, not a closer.

    The captured CAUTION shape with the blockquote's space dropped. A rule that only asked
    "does text attach on the left" would spend this opening marker as a closer, leave no opener
    for the real one and lose the heading — fewer findings than the body declares. Markdown
    flanking reads it as an opener because punctuation sits on its left.
    """
    body = '>**⚠️ Outside diff range comments (1)** <details><summary>Major · a.py</summary> fix </details>'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [(row['section'], row['id']) for row in verdict['undisposed']] == [('outside-diff', 'outside-diff-1')]


def test_two_bold_runs_glued_together_are_both_read() -> None:
    """⛔ D3: `**A****B**` is two bold runs, not one lost span.

    The second run's opening marker has a marker to its left, so it is never read as a closer;
    the first run's closer can be, because a non-word character follows it. Both runs stay
    readable, and the second one heads a section here.
    """
    body = '**Major****⚠️ Outside diff range comments (1)** <details><summary>Major · a.py</summary> fix </details>'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [(row['section'], row['id']) for row in verdict['undisposed']] == [('outside-diff', 'outside-diff-1')]


def test_an_inline_section_does_not_suppress_a_larger_status_line() -> None:
    """⛔ D1/D3: two inline statements are read at the LARGER count, never the smaller.

    A blockless `**Inline comments (2)**` heading and an `**Actionable comments posted: 4**`
    status line both speak about the body's inline findings. Reading only the block would drop
    two findings the body declares; the shortfall is minted, so the four stand and the nitpick
    section is added beside them.
    """
    body = (
        '**Actionable comments posted: 4** **Inline comments (2)** '
        '<details><summary>🧹 Nitpick comments (1)</summary> a </details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 5, verdict
    assert [row['id'] for row in verdict['undisposed']] == [
        'inline-1',
        'inline-2',
        'nitpick-1',
        'inline-3',
        'inline-4',
    ]


def test_a_counted_wrapper_enclosing_a_blockless_summary_stops_the_gate() -> None:
    """⛔ D2: a section the wrapper encloses must own a CLOSED block, or the body stops.

    The enclosed `<summary>` sits with no `<details>` of its own, so nothing beside it can be
    told apart from what the wrapper itself says. Reading through would drop whichever of the
    two statements the body made, so the shape stops with a cause naming the wrapper.
    """
    body = '<details><summary>Review (2)</summary><summary>🧹 Nitpick comments (1)</summary> x </details>'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['merge_allowed'] is False, verdict
    assert verdict['reason'] == 'undecidable_read', verdict
    assert 'closed block of its own' in verdict['detail'], verdict


def test_a_triple_emphasis_heading_is_still_read() -> None:
    """⛔ CR: `***Heading (1)***` is a heading — the delimiter run's asterisks are not a title.

    A triple delimiter puts an asterisk inside the span's raw title, so a title carrying one was
    skipped and the heading lost — fewer findings than the body declares. The delimiter run is
    stripped from the edges of the title, and an asterisk INSIDE it still disqualifies the span.
    """
    body = '***Outside diff range comments (1)*** <details><summary>Major · a.py</summary> fix </details>'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [(row['section'], row['id']) for row in verdict['undisposed']] == [('outside-diff', 'outside-diff-1')]


def test_a_wrapper_enclosing_non_ascii_content_stops_the_gate() -> None:
    """⛔ CR: any non-whitespace text beside the enclosed section is the wrapper's own content.

    A letter-or-digit test passes a non-ASCII sentence and a symbol-only note, and reading
    through would drop both — the count the body states, unread.
    """
    for note in ('修复权限检查', '⚠️'):
        body = (
            f'<details><summary>Review (2)</summary> {note} '
            '<details><summary>🧹 Nitpick comments (1)</summary> a </details></details>'
        )

        verdict = _verdict(_read(_review_body(body)))

        assert verdict['merge_allowed'] is False, (note, verdict)
        assert verdict['reason'] == 'undecidable_read', (note, verdict)
        assert 'carries content beside' in verdict['detail'], (note, verdict)


def test_a_wrapper_nested_in_another_wrapper_is_validated_too() -> None:
    """⛔ CR: a transparent wrapper inside a counted wrapper must still be checked.

    `Review (1)` encloses `Group (2)`, which holds prose beside a recognised section. The inner
    wrapper is the outer one's CONTENT, so validating only the sections that get emitted skipped
    it and its prose was dropped; the check now runs before that filter.
    """
    body = (
        '<details><summary>Review (1)</summary>'
        '<details><summary>Group (2)</summary> a concern of its own '
        '<details><summary>🧹 Nitpick comments (1)</summary> x </details></details></details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['merge_allowed'] is False, verdict
    assert verdict['reason'] == 'undecidable_read', verdict
    assert "'Group (2)'" in verdict['detail'], verdict


def test_an_implausible_status_line_count_stops_the_gate() -> None:
    """⛔ CR: the inline shortfall is capped like every other count.

    An inline section of 1 beside a status line declaring a billion would pass the section's own
    limit check and then allocate the supplement, one dict per finding. The named stop covers the
    status line's count too.
    """
    body = (
        '**Actionable comments posted: 1000000000** **Inline comments (1)** '
        '<details><summary>🧹 Nitpick comments (1)</summary> a </details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['merge_allowed'] is False, verdict
    assert verdict['reason'] == 'undecidable_read', verdict
    assert 'this gate will enumerate' in verdict['detail'], verdict


def test_a_label_between_two_bold_runs_is_not_a_heading() -> None:
    """⛔ Round-1 guard (not red before the fix): two bold runs state no section between them.

    `**Major** Nitpick comments (2) **Quick win**` is one severity label, some prose and one
    win. Tiling every adjacent marker pair would read the middle prose as a nitpick heading and
    mint two findings nobody wrote; pairing an OPENER with the next CLOSING marker reads the
    two bold runs and nothing else.
    """
    body = (
        '**Major** Nitpick comments (2) **Quick win** '
        '<details><summary>🧹 Nitpick comments (1)</summary> only one </details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [(row['section'], row['id']) for row in verdict['undisposed']] == [('nitpick', 'nitpick-1')]


def test_the_plan_lb_162_controls_still_read_as_they_did() -> None:
    """The controls PLAN-LB-168 D5 requires, all of which held at `main` `46d3308ea`.

    The two captured review bodies read as the PLAN-LB-162 tests state, a bold heading
    MENTIONED in prose still mints nothing, and a bold heading that declares no count is
    still ignored. Each is asserted here so the four fixes cannot buy their counts by
    breaking one of them.
    """
    assert _verdict(_read(_review_body(_CAPTURED_CAUTION_1983_BODY)))['review_body_findings_total'] == 1

    read = _read(_review_body(_CAPTURED_1984_BODY_FIRST), _review_body(_CAPTURED_1984_BODY_SECOND))
    assert _verdict(read)['review_body_findings_total'] == 8

    prose = (
        '**Outside diff range comments (1)** is empty this time. '
        '<details><summary>Major · a.py</summary> fix </details>'
        '<details><summary>🧹 Nitpick comments (2)</summary> a b </details>'
    )
    prose_verdict = _verdict(_read(_review_body(prose)))
    assert prose_verdict['review_body_findings_total'] == 2, prose_verdict

    uncounted = (
        '**Outside diff range comments** <details><summary>🧹 Nitpick comments (2)</summary> first second </details>'
    )
    uncounted_verdict = _verdict(_read(_review_body(uncounted)))
    assert uncounted_verdict['review_body_findings_total'] == 2, uncounted_verdict


# ---------------------------------------------------------------------------
# PLAN-LB-172 D1 — the parser never reads fewer findings than a body declares,
# and where it cannot decide it stops. Each assertion below is red against the
# tree at ``c22d103fb``.
# ---------------------------------------------------------------------------


def test_a_top_level_code_sample_does_not_hide_a_heading_after_a_closed_block() -> None:
    """⛔ An unclosed top-level `<code>` ends with the closed block that follows it.

    The prose scope of the top-level text must not run past a top-level block that has
    closed: the CAUTION heading after the nitpick block is its own heading, and reading
    it as prose drops its finding with no stop.
    """
    body = (
        'Wrap it in <code> tags. '
        '<details><summary>🧹 Nitpick comments (1)</summary> a </details> '
        '**⚠️ Outside diff range comments (1)** <details><summary>Major · b.py</summary> fix </details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert [row['section'] for row in verdict['undisposed']] == ['nitpick', 'outside-diff'], verdict


def test_a_counted_heading_over_a_prose_row_on_its_own_line_counts_its_findings() -> None:
    """⛔ A counted heading on its own line is a heading, whatever the row below looks like.

    A prose row that starts with a letter is a row, not a continuation of the heading's
    sentence: only text on the SAME line as the closing marker makes it a mention. The
    raw body the gate holds carries the line break the display form has flattened.
    """
    body = '> [!CAUTION]\n> **⚠️ Outside diff range comments (1)**\n> Line 12: the guard coerces UNKNOWN\n'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [(row['section'], row['id']) for row in verdict['undisposed']] == [('outside-diff', 'outside-diff-1')]


def test_a_counted_wrapper_declaring_more_than_it_encloses_stops_the_gate() -> None:
    """⛔ `Review (5)` around one nitpick declares five findings and reads one.

    A wrapper that declares no more than the sections it encloses is a grouping and reads
    through; one that declares MORE than they account for leaves findings nobody can
    enumerate, so the body stops with a named reason instead of reading fewer.
    """
    body = (
        '<details><summary>Review (5)</summary>'
        '<details><summary>🧹 Nitpick comments (1)</summary> x </details></details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['merge_allowed'] is False, verdict
    assert verdict['reason'] == 'undecidable_read', verdict
    assert "'Review (5)'" in verdict['detail'], verdict


def test_a_digit_run_too_long_to_be_read_stops_the_gate() -> None:
    """⛔ `int()` on a digit run of thousands of characters must not raise a traceback.

    A count the parser cannot read is either read or a named stop — never a crash that
    states no verdict at all.
    """
    body = '<details><summary>🔎 Potential issues (' + '9' * 5000 + ')</summary> one row </details>'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['merge_allowed'] is False, verdict
    assert verdict['reason'] == 'undecidable_read', verdict
    assert 'this gate will enumerate' in verdict['detail'], verdict


def test_a_heading_whose_closer_is_followed_by_an_emoji_is_read() -> None:
    """⛔ A decoration right after the closing marker must not turn the closer into an opener.

    `**…(1)**🎯` loses the heading when the marker is read as an opener because the emoji
    is neither whitespace nor punctuation: the pending span IS a heading, so the marker
    closes it.
    """
    body = '**⚠️ Outside diff range comments (1)**🎯 <details><summary>Major · b.py</summary> fix </details>'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [row['id'] for row in verdict['undisposed']] == ['outside-diff-1']


def test_a_heading_glued_to_a_letter_beside_an_unpaired_opener_is_read() -> None:
    """⛔ A stale `**` earlier in the body must not spend the heading's own opener.

    `**stray text**Outside diff range comments (1)**` is a stray run, then a heading glued
    to a letter. Pairing the stray run with the heading's opener drops the heading; the
    second marker's pending span is the heading, so that marker opens rather than closing
    the stray run.
    """
    body = '**stray text**Outside diff range comments (1)** <details><summary>Major · b.py</summary> fix </details>'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [row['id'] for row in verdict['undisposed']] == ['outside-diff-1']


def test_a_mis_paired_single_backtick_cannot_quote_a_heading() -> None:
    """⛔ Backticks pair by RUN LENGTH, so a stray single cannot open a quotation.

    A single backtick left open, then a doubled fence, then a single again: pairing every
    second backtick pairs the doubled fence's second character with the heading's
    surrounding single backticks and drops the heading as a quotation.
    """
    body = (
        'x ` y `` z `` **Outside diff range comments (1)** ` w <details><summary>Major · b.py</summary> fix </details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [row['id'] for row in verdict['undisposed']] == ['outside-diff-1']


def test_a_non_finding_summary_nested_below_a_heading_does_not_silence_it() -> None:
    """⛔ Only a block's OWN opening summary titles the block.

    A summary-less block holding a counted heading and a nested `Files selected…` block is
    not a non-finding block: reading the first `<summary>` anywhere inside it silenced the
    heading.
    """
    body = (
        '<details> **Outside diff range comments (1)** '
        '<details><summary>Files selected for processing: 15</summary> * `a.py` </details>'
        '</details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [row['id'] for row in verdict['undisposed']] == ['outside-diff-1']


def test_a_counted_wrapper_around_an_uncounted_group_does_not_stop() -> None:
    """⛔ An uncounted group between a wrapper and its section is not the wrapper's content.

    The group's own `<summary>` text used to stay in the gap and stop the gate; a wrapper
    that says nothing beside the section it encloses reads through.
    """
    body = (
        '<details><summary>Review (1)</summary>'
        '<details><summary>Group</summary>'
        '<details><summary>🧹 Nitpick comments (1)</summary> x </details>'
        '</details></details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [row['id'] for row in verdict['undisposed']] == ['nitpick-1']


def test_the_enumeration_cap_binds_the_total_not_only_each_heading() -> None:
    """⛔ Many headings each just under the cap still enumerate more than the gate allows."""
    body = (
        '<details><summary>🔎 Potential issues (999)</summary> one </details>'
        '<details><summary>🔎 Potential issues (999)</summary> two </details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['merge_allowed'] is False, verdict
    assert verdict['reason'] == 'undecidable_read', verdict
    assert 'this gate will enumerate' in verdict['detail'], verdict


def test_an_unclosed_second_sibling_block_stops_the_gate() -> None:
    """⛔ A heading's second sibling that never closes must not be dropped silently."""
    body = (
        '**Outside diff range comments (1)** '
        '<details><summary>Major · a.py</summary> fix </details> '
        '<details><summary>Major · b.py</summary> second'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['merge_allowed'] is False, verdict
    assert verdict['reason'] == 'undecidable_read', verdict
    assert 'never closed' in verdict['detail'], verdict


_DECLARING_THREE = {
    'summary-counted': ('<details><summary>🧹 Nitpick comments (3)</summary> one two three </details>'),
    'colon-counted': ('<details><summary>🧹 Nitpick comments: 3</summary> one two three </details>'),
    'bold-over-block': ('**Outside diff range comments (3)** <details><summary>Major · a.py</summary> one </details>'),
    'bold-over-prose-row': ('> **⚠️ Outside diff range comments (3)**\n> Line 12: one two three\n'),
    'unclassified-counted-title': ('<details><summary>🔎 Potential issues (3)</summary> one two three </details>'),
    'bold-over-markdown-rows': (
        '**Outside diff range comments (3)**\n- `src/a.py:1` one\n- `src/a.py:2` two\n- `src/a.py:3` three\n'
    ),
    'wrapper-declaring-three': (
        '<details><summary>Review (3)</summary>'
        '<details><summary>🧹 Nitpick comments (3)</summary> one two three </details>'
        '</details>'
    ),
    'one-outer-block': (
        '<details><summary>Walkthrough</summary>'
        '<details><summary>🧹 Nitpick comments (3)</summary> one two three </details>'
        '</details>'
    ),
}


@pytest.mark.parametrize('shape', sorted(_DECLARING_THREE))
def test_a_body_declaring_three_never_reads_fewer_than_three_or_stops(shape: str) -> None:
    """A body declaring N findings is counted in full or stops — never read as fewer."""
    verdict = _verdict(_read(_review_body(_DECLARING_THREE[shape])))

    read_fewer = verdict.get('reason') != 'undecidable_read' and (verdict['review_body_findings_total'] < 3)
    assert not read_fewer, verdict


def test_a_prose_row_beside_a_section_in_a_group_is_wrapper_content() -> None:
    """⛔ Masking the whole group hid the prose row the wrapper had to account for.

    The wrapper declares one finding and encloses a section plus a prose row: masking
    only the group's title and the section leaves the row visible, so the wrapper stops
    instead of demanding a disposition only for the section.
    """
    body = (
        '<details><summary>Review (1)</summary>'
        '<details><summary>Group</summary>'
        '<details><summary>🧹 Nitpick comments (1)</summary> x </details>'
        'The retry loop never terminates.'
        '</details></details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['merge_allowed'] is False, verdict
    assert verdict['reason'] == 'undecidable_read', verdict
    assert 'carries content beside' in verdict['detail'], verdict


def test_a_wrapper_counts_the_rows_of_an_undeclared_child_section() -> None:
    """⛔ The wrapper's validation uses the child's own count, not one-per-child."""
    body = (
        '<details><summary>Review (2)</summary>'
        '<details><summary>Nitpick comments</summary>'
        '<!-- cr-comment:v1:aaaa --> one <!-- cr-comment:v1:bbbb --> two </details>'
        '</details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['reason'] != 'undecidable_read', verdict
    assert verdict['review_body_findings_total'] >= 2, verdict


def test_a_repeated_bold_title_counts_its_real_heading_once() -> None:
    """⛔ The raw occurrence must pair in order: `find()` always took the first one.

    The title first appears quoted inside a sentence and then heads the rows below it.
    Pairing the second display occurrence with the second raw occurrence is what makes
    the heading count; reading the first one as the heading dropped it as a mention.
    """
    body = 'The **Nitpick comments (1)** label changed.\n\n**Nitpick comments (1)**\n- `src/a.py:1` fix the timeout\n'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [row['id'] for row in verdict['undisposed']] == ['nitpick-1']


def test_a_prose_row_above_the_section_in_a_summary_less_group_is_not_masked() -> None:
    """⛔ The group's own summary is masked, never the nested section's.

    An unbounded summary search found the nested section's summary when the group
    carries none, and the mask then removed the prose finding written above it.
    """
    body = (
        '<details><summary>Review (1)</summary>'
        '<details> A separate finding. '
        '<details><summary>Nitpick comments (1)</summary> Another finding. </details>'
        '</details></details>'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['merge_allowed'] is False, verdict
    assert verdict['reason'] == 'undecidable_read', verdict
    assert 'carries content beside' in verdict['detail'], verdict


def test_markup_quoted_inside_a_fence_is_prose_not_structure() -> None:
    """A reviewer's quoted snippet is an EXAMPLE: it neither mints findings nor stops."""
    body = (
        'Analysis:\n'
        '```html\n'
        '<details><summary>Review (1)</summary>\n'
        '<details><summary>Nitpick comments (1)</summary> x </details>\n'
        '</details>\n'
        '```\n'
    )

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['reason'] != 'undecidable_read', verdict
    assert verdict['review_body_findings_total'] == 0, verdict


def test_a_bold_title_split_across_raw_lines_still_counts_its_rows() -> None:
    """The display form joins the raw lines, so the raw match allows a whitespace run."""
    body = '**Nitpick\ncomments (1)**\n- `src/a.py:1` fix the timeout\n'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [row['id'] for row in verdict['undisposed']] == ['nitpick-1']


def test_a_quoted_copy_inside_a_fence_does_not_hide_the_heading_below_it() -> None:
    """The occurrence index is built from the MASKED body, so the fenced copy is skipped."""
    body = '```html\n**Nitpick comments (1)**\n```\n\n**Nitpick comments (1)**\n- `src/a.py:1` fix the timeout\n'

    verdict = _verdict(_read(_review_body(body)))

    assert verdict['review_body_findings_total'] == 1, verdict
    assert [row['id'] for row in verdict['undisposed']] == ['nitpick-1']
