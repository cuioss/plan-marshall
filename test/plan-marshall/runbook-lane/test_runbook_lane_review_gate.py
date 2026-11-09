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
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

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


def _review_body(body: str, author: str = 'coderabbitai') -> dict:
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
        'commit_id': 'a' * 40,
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


def _verdict(read: dict, *dispositions: str) -> Any:
    with patch.object(lane, '_read_review_surfaces', return_value=read):
        return cmd_review_gate(_args(*dispositions))


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


def test_a_disposition_that_does_not_name_its_evidence_is_refused() -> None:
    verdict = _verdict(_read(_review_body(_OUTSIDE_DIFF_BODY)), 'coderabbit outside-diff outside-diff-1 —')

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'disposition_unparsable'


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
    """The CI read flattens a body to one line; a count is read off the literal only."""
    flattened = '**Actionable comments posted:** <details><summary>src/a.py (3)</summary> rename the helper </details>'

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


def test_the_ci_read_is_the_abstraction_s_own_invocation(monkeypatch) -> None:
    """The one seam D1 rests on: the read goes through `ci`, never a CLI of its own."""
    seen: dict[str, Any] = {}

    def fake_run(argv, **kwargs):
        seen['argv'] = argv
        seen['cwd'] = kwargs.get('cwd')
        return SimpleNamespace(returncode=0, stdout='status: success\ncomplete: true\ncomments[0]:\n', stderr='')

    monkeypatch.setattr('subprocess.run', fake_run)

    lane._read_review_surfaces(7, Path('/tmp/project'))

    argv = seen['argv']
    assert 'python' in str(argv[0])
    assert str(argv[1]).endswith('execute-script.py')
    assert argv[2] == 'plan-marshall:tools-integration-ci:ci', 'the read must go through the CI abstraction'
    assert argv[3:6] == ['pr', 'comments', '--pr-number']
    assert argv[6] == '7'
    assert seen['cwd'] == '/tmp/project', 'the read runs in the project it was handed'
