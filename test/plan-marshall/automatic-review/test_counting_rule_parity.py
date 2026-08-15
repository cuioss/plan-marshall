#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""The epic's counting rule has TWO implementations — this pins them together.

``bot-participation-contract.md`` § "The counting rule" is the epic's single source
of truth for how a reviewer's output is counted, and two counters apply it:

* ``automatic-review/scripts/review_gate_delta.py`` (the review-versus-gate delta),
  in the shared ``plan-marshall`` bundle;
* ``.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py``
  (the per-reviewer retrospective), project-local.

They are separate implementations, so the contract's Consumers table states that a
change to the rule must land in both. **An obligation with no mechanism is not a
fix** — and the two were in fact already wrong in the same way, each matching the
status-summary signature against ``title``/``detail`` where the comment text never
lives, each with a test fixture encoding that unreachable shape, so each "proved"
a carve-out that could not fire on a real record.

This file is the mechanism. It drives BOTH implementations over one shared corpus
and asserts they agree, so a change to either that is not mirrored fails here rather
than surfacing as two counters silently reporting different numbers over the same
findings.
"""

from __future__ import annotations

import sys

from conftest import PROJECT_ROOT, get_script_path

_DELTA_SCRIPTS = get_script_path('plan-marshall', 'automatic-review', 'review_gate_delta.py').parent
if str(_DELTA_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_DELTA_SCRIPTS))

_RETRO_SCRIPTS = (
    PROJECT_ROOT / '.claude' / 'skills' / 'finalize-step-review-retrospective' / 'scripts'
)
if str(_RETRO_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_RETRO_SCRIPTS))

import review_gate_delta as delta  # noqa: E402

# `review_retrospective` is project-local under `.claude/skills/`, outside every
# path mypy is pointed at, so it has no discoverable stub — hence
# `import-not-found` rather than the `import-untyped` a bundle module would give.
import review_retrospective as retro  # type: ignore[import-not-found]  # noqa: E402

#: One corpus, exercising every axis the rule distinguishes. Each entry carries the
#: REAL record shape — `title`/`detail` built from structured metadata, the comment
#: text in the promoted top-level `body` — because a corpus in the unreachable shape
#: is what let both implementations ship a carve-out that never fired.
_CORPUS: tuple[tuple[str, dict, bool], ...] = (
    (
        'inline is actionable',
        {
            'author': 'coderabbitai',
            'bot_kind': 'coderabbit',
            'kind': 'inline',
            'body': 'This index can be negative.',
        },
        True,
    ),
    (
        'issue_comment is meta',
        {
            'author': 'coderabbitai',
            'bot_kind': 'coderabbit',
            'kind': 'issue_comment',
            'body': '## Walkthrough',
        },
        False,
    ),
    (
        'status-summary review_body is meta',
        {
            'author': 'coderabbitai',
            'bot_kind': 'coderabbit',
            'kind': 'review_body',
            'title': 'PR #1 review_body comment by coderabbitai (1)',
            'detail': 'pr_number: 1\nkind: review_body',
            'body': 'Actionable comments posted: 5',
        },
        False,
    ),
    (
        'status signature only in title/detail does NOT make the body meta',
        {
            'author': 'coderabbitai',
            'bot_kind': 'coderabbit',
            'kind': 'review_body',
            'title': 'Actionable comments posted: 5',
            'detail': 'Actionable comments posted: 5',
            'body': 'The guard coerces UNKNOWN into a positive.',
        },
        True,
    ),
    (
        'status line followed by substance stays actionable',
        {
            'author': 'coderabbitai',
            'bot_kind': 'coderabbit',
            'kind': 'review_body',
            'body': 'Actionable comments posted: 1\n\nGuard the array bound here.',
        },
        True,
    ),
    (
        'substantive review_body from another reviewer is actionable',
        {
            'author': 'sourcery-ai',
            'bot_kind': 'sourcery',
            'kind': 'review_body',
            'body': 'Consider extracting the validation helper.',
        },
        True,
    ),
    (
        'the signature from a reviewer that declares no summary pattern is actionable',
        {
            'author': 'sourcery-ai',
            'bot_kind': 'sourcery',
            'kind': 'review_body',
            'body': 'Actionable comments posted: 2',
        },
        True,
    ),
    (
        'an unknown kind is meta',
        {'author': 'coderabbitai', 'bot_kind': 'coderabbit', 'kind': '', 'body': 'x'},
        False,
    ),
)


def test_the_corpus_covers_both_answers():
    """A parity corpus that is all-True or all-False proves agreement vacuously."""
    answers = {expected for _, _, expected in _CORPUS}

    assert answers == {True, False}


def test_both_implementations_agree_on_every_corpus_record():
    """One rule, two counters, one answer per record.

    A divergence here means the two are reporting different numbers over the same
    findings store — which is exactly what the contract's "must land in both"
    sentence asks for and, on its own, cannot enforce.
    """
    disagreements = [
        (label, delta._is_actionable(record), retro._is_actionable(record))
        for label, record, _ in _CORPUS
        if delta._is_actionable(record) != retro._is_actionable(record)
    ]

    assert not disagreements, (
        'the two counting-rule implementations disagree: '
        + '; '.join(f'{label}: delta={d} retro={r}' for label, d, r in disagreements)
    )


def test_both_implementations_match_the_expected_classification():
    """Agreement is necessary but not sufficient — they must both be RIGHT.

    Without this, the two could agree by being wrong in the same way, which is the
    state they were actually in before the body-field fix.
    """
    for label, record, expected in _CORPUS:
        assert delta._is_actionable(record) is expected, f'review_gate_delta: {label}'
        assert retro._is_actionable(record) is expected, f'review_retrospective: {label}'
