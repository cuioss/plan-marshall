#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for the review-versus-gate delta signal (plan 130 D2).

*"What did review catch that the in-house gates did not"* is the only direct read
on gate/review parity available, and it arrives free on every PR: the gates run
before review (`pre-push-quality-gate` at order 5, self-review at 7, against
`automatic-review` at 30), so a finding filed against a tree the gates already
passed IS a gate escape. No per-finding gate attribution is needed.

**But "the gates passed" is not "the gates saw this tree".** Source-mutating steps
run between certification and review — `finalize-step-simplify` (8) and
`finalize-step-security-audit` (9), and the gate itself (5), whose own item-5f
commit lands after the tree it just certified — and a forward pass never returns to
order 5 to re-gate their edits, so the escape claim rests on the gate-certified tree
and the reviewed tree being the SAME tree, proven by SHA rather than assumed. No
count is pinned here: membership is whatever each step's declared `mutates_source`
makes it, so a step that declares the fact later is covered by its own declaration.

Three properties make the signal usable rather than harmful, and all are tested
here in the direction that matters:

* **Refusal-PRs are excluded BY CONSTRUCTION.** The bots refuse frequently, so an
  absence of review findings is often an absence of *review*, not of defects. A
  metric that counted a refusal-PR as "zero escapes" would report improving parity
  precisely as reviewer coverage collapsed — this epic's named failure mode. The
  guard is structural: the share is emitted only at FULL coverage, so a collapse
  can only ever move the metric from a number to NO number, never to a better one.

* **Partition before any rate.** The escape set is mixed: some escapes are
  *gate-addressable* (a lint family absent from the select list — a gate
  CONFIGURATION finding), others *gate-structural* (documentation-prose semantics,
  behaviour under un-supplied inputs). A share computed before that partition would
  read a configuration gap as evidence of a structural bot-only class. An
  unpartitioned finding therefore withholds the share rather than being bucketed by
  default.

* **The escape claim is anchored to a tree.** A gate verdict, a gate-certified SHA,
  and a reviewed SHA — each absent or mismatched one excludes the PR, so a finding
  on a line the gates never saw is never counted as a miss they made.
"""

import pytest
from review_gate_delta import (
    PARTITION_GATE_ADDRESSABLE,
    PARTITION_GATE_STRUCTURAL,
    PARTITION_UNPARTITIONED,
    VERDICT_EXCLUDED,
    VERDICT_MEASURED,
    assess_delta,
)

_ROSTER = ['coderabbit', 'cuioss-review-bot', 'sourcery']

#: The tree the gates certified and the tree review reviewed — equal in the
#: measurable case, and the whole subject of the post-gate-mutation exclusion.
_SHA = 'a' * 40


def _finding(hash_id, bot_kind='coderabbit', kind='inline'):
    return {'hash_id': hash_id, 'bot_kind': bot_kind, 'kind': kind}


def _full_coverage(**overrides):
    """A fully-reviewed PR with a complete partition — the only shape that yields a share."""
    kwargs = {
        'findings': [_finding('f1'), _finding('f2'), _finding('f3')],
        'enabled_bots': _ROSTER,
        'reviewed_bots': list(_ROSTER),
        'gates_green': True,
        'gate_head_sha': _SHA,
        'reviewed_head_sha': _SHA,
        'partitions': {
            'f1': PARTITION_GATE_ADDRESSABLE,
            'f2': PARTITION_GATE_STRUCTURAL,
            'f3': PARTITION_GATE_STRUCTURAL,
        },
    }
    kwargs.update(overrides)
    return assess_delta(**kwargs)


# ---------------------------------------------------------------------------
# The measured case
# ---------------------------------------------------------------------------


def test_a_padded_registry_entry_still_matches(monkeypatch):
    """Both sides of a registry comparison are normalised — the project's rule.

    A padded entry must not silently disable the carve-out. The padding is INJECTED
    here: asserting against the real (unpadded) registry entry would pass with or
    without the `.strip()`, which is a guard that pins nothing.
    """
    import bot_registry
    from review_gate_delta import is_status_summary

    monkeypatch.setattr(bot_registry, 'review_body_summary_patterns', lambda _k: ['  Actionable comments posted:  '])

    assert is_status_summary({'bot_kind': 'coderabbit', 'kind': 'review_body', 'body': 'Actionable comments posted: 5'})


def test_an_empty_registry_entry_does_not_match_everything(monkeypatch):
    """An empty entry must not drop every review_body from that bot.

    Without the `if cleaned` filter, `''` is a prefix of every string, so a stray
    `- ""` in a registry doc would silently classify the bot's whole review output
    as boilerplate — a total, invisible suppression.
    """
    import bot_registry
    from review_gate_delta import is_status_summary

    monkeypatch.setattr(bot_registry, 'review_body_summary_patterns', lambda _k: ['', '   '])

    assert not is_status_summary({'bot_kind': 'coderabbit', 'kind': 'review_body', 'body': 'A real review comment.'})


def test_a_bot_login_carrying_the_bot_suffix_still_resolves(monkeypatch):
    """The author fallback normalises the login, so `[bot]` and casing still classify.

    Exercised through the classifier rather than the resolver alone, because the
    failure mode is silent: an unresolved login yields no patterns, so the carve-out
    simply never fires and every status summary counts as an escape.
    """
    from review_gate_delta import is_status_summary

    for login in ('coderabbitai[bot]', 'CodeRabbitAI', 'CodeRabbitAI[bot]'):
        assert is_status_summary({'author': login, 'kind': 'review_body', 'body': 'Actionable comments posted: 5'}), (
            login
        )


def test_a_bot_declaring_no_summary_pattern_keeps_every_review_body():
    """The fail-closed default is COUNTED, because dropping is the dangerous direction."""
    from review_gate_delta import is_status_summary

    assert not is_status_summary(
        {'bot_kind': 'sourcery', 'kind': 'review_body', 'body': 'Actionable comments posted: 2'}
    )


def test_a_status_line_followed_by_review_content_is_counted():
    """Strip-then-classify: review content BELOW the status line makes the body substantive.

    Fail-first case: the begins-with rule classified the whole body by its opening
    line, so a genuine review that opens with ``Actionable comments posted: N`` and
    carries its findings below was dropped from the escape count — the direction
    that flatters the gates.
    """
    from review_gate_delta import is_status_summary

    record = {
        'hash_id': 'status-plus-review',
        'bot_kind': 'coderabbit',
        'kind': 'review_body',
        'author': 'coderabbitai',
        'body': (
            '**Actionable comments posted: 1**\n\n'
            'The guard coerces UNKNOWN into a positive; check the sign before the comparison.\n\n'
            '<details>\n<summary>Review details</summary>\nconfiguration\n</details>'
        ),
    }

    assert not is_status_summary(record)

    result = assess_delta(
        findings=[record],
        enabled_bots=_ROSTER,
        reviewed_bots=list(_ROSTER),
        gates_green=True,
        gate_head_sha=_SHA,
        reviewed_head_sha=_SHA,
        partitions={'status-plus-review': PARTITION_GATE_STRUCTURAL},
    )

    assert result['escapes_total'] == 1


def test_a_pure_status_summary_with_nested_details_and_layout_stays_meta():
    """Matched control: the status line, nested collapsed blocks and layout only — still meta.

    Nested ``<details>`` peel from the inside out, and an HTML comment or a separator
    rule is layout, not a review claim, so none of them makes the summary substantive.
    """
    from review_gate_delta import is_status_summary

    body = (
        '**Actionable comments posted: 3**\n\n'
        '<details>\n<summary>Nitpick comments (2)</summary><blockquote>\n'
        '<details>\n<summary>src/a.py (1)</summary>\nrename the helper\n</details>\n'
        '</blockquote></details>\n\n'
        '<!-- This is an auto-generated comment by CodeRabbit -->\n\n'
        '---'
    )

    assert is_status_summary({'bot_kind': 'coderabbit', 'kind': 'review_body', 'body': body})


_STATUS_LINE = '**Actionable comments posted: 1**\n\n'


@pytest.mark.parametrize(
    'below_status_line',
    [
        '<details open><summary>Finding</summary>Fix the guard</details>',
        '<details open=""><summary>Finding</summary>Fix the guard</details>',
        '<details open="open"><summary>Finding</summary>Fix the guard</details>',
        '<DETAILS class="review" OPEN>\nFix the guard\n</DETAILS>',
        (
            '<details open><summary>Finding</summary>Fix the guard\n'
            '<details><summary>Review details</summary>configuration</details>\n'
            '</details>'
        ),
    ],
    ids=[
        'bare-open-attribute',
        'empty-valued-open-attribute',
        'self-valued-open-attribute',
        'uppercase-open-attribute-after-another-attribute',
        'collapsed-block-nested-inside-an-open-block',
    ],
)
def test_an_open_details_block_below_the_status_line_is_review_content(below_status_line):
    """An open block is displayed, so its content is classified rather than removed.

    ``open`` is an HTML boolean attribute: its presence alone expands the block. A
    collapsed block nested inside an open one is still removed, but the open block's
    own text remains and makes the body a counted ``review_body``.
    """
    from review_gate_delta import _is_actionable, is_status_summary

    record = {'bot_kind': 'coderabbit', 'kind': 'review_body', 'body': _STATUS_LINE + below_status_line}

    assert not is_status_summary(record)
    assert _is_actionable(record)


@pytest.mark.parametrize(
    'below_status_line',
    [
        '<details><summary>Review details</summary>configuration</details>',
        '<details class="open"><summary>Review details</summary>configuration</details>',
        '<details data-open="true"><summary>Review details</summary>configuration</details>',
        '<details><summary>Outer</summary><details open><summary>Inner</summary>text</details></details>',
        '<details open></details>\n<details open><summary></summary></details>',
    ],
    ids=[
        'collapsed-block',
        'open-only-inside-a-quoted-attribute-value',
        'attribute-name-merely-ending-in-open',
        'open-block-nested-inside-a-collapsed-block',
        'open-blocks-carrying-only-markup',
    ],
)
def test_collapsed_details_and_empty_open_blocks_below_the_status_line_stay_meta(below_status_line):
    """Matched control: nothing a reader sees below the status line carries text.

    A collapsed block is removed whole — including an open block nested inside it —
    an ``open`` token that is not the attribute name does not expand the block, and
    an open block holding only tags contributes no letter or digit.
    """
    from review_gate_delta import is_status_summary

    record = {'bot_kind': 'coderabbit', 'kind': 'review_body', 'body': _STATUS_LINE + below_status_line}

    assert is_status_summary(record)


def test_a_substantive_review_body_from_another_author_is_still_an_escape():
    """The carve-out is gated on the author AND the signature — not on the kind.

    Dropping every `review_body` would discard the surface where the review bots
    file their consolidated findings, which is the bulk of what they report.
    """
    findings = [
        {
            'hash_id': 'real',
            'bot_kind': 'sourcery',
            'kind': 'review_body',
            'author': 'sourcery-ai',
            'title': 'Guard coerces UNKNOWN into a positive',
            'detail': '',
        },
    ]

    result = assess_delta(
        findings=findings,
        enabled_bots=_ROSTER,
        reviewed_bots=list(_ROSTER),
        gates_green=True,
        gate_head_sha=_SHA,
        reviewed_head_sha=_SHA,
        partitions={'real': PARTITION_GATE_STRUCTURAL},
    )

    assert result['escapes_total'] == 1
