#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-55 D3 — a refusal on the merge candidate outranks stale participation.

``review_completeness.classify_bot`` used to check proven participation FIRST,
unconditionally, so a bot that reviewed an older head and then refused the merge
candidate resolved ``participated``. Participation that the producer itself
reports as NOT covering the merge candidate (``stale_participation_bots``) must
not outrank the bot's own statement that it will not review that candidate.

The matched negative is the same bot with CURRENT participation: a review of the
merge candidate still outranks a later, redundant refusal, because that review is
evidence the refusal does not contradict.
"""

from __future__ import annotations

import pytest

from conftest import load_script_module

rc = load_script_module('plan-marshall', 'automatic-review', 'review_completeness.py', register=False)


def _classify(
    *,
    proven=None,
    stale=None,
    refused=None,
    declined=None,
    has_findings=False,
):
    """Classify one bot through the production entry point."""
    return rc.classify_bot(
        'coderabbit',
        dict(proven or {}),
        has_findings,
        set(),
        set(refused or ()),
        stale,
        False,
        set(declined or ()),
    )


def test_a_refusal_outranks_participation_that_does_not_cover_the_candidate():
    """Older-head review + current-head refusal resolves a refusal member."""
    state = _classify(
        proven={'coderabbit': 'inline'},
        stale={'coderabbit'},
        refused={'coderabbit'},
    )

    assert state not in (rc.STATE_PARTICIPATED, rc.STATE_PARTICIPATED_BUT_EMPTY), (
        f'a refusal on the merge candidate was outranked by participation that does not cover it: {state}'
    )
    assert state.startswith('refused_'), f'expected a refusal member, got {state}'


def test_a_decline_outranks_participation_that_does_not_cover_the_candidate():
    """Older-head review + a re-review decline resolves ``declined``, not participated."""
    state = _classify(
        proven={'coderabbit': 'inline'},
        stale={'coderabbit'},
        declined={'coderabbit'},
    )

    assert state == rc.STATE_DECLINED, f'expected declined, got {state}'


def test_participation_that_covers_the_candidate_still_outranks_a_refusal():
    """⛔ MATCHED CONTROL — current participation is not displaced by a refusal.

    Same bot, same refusal, only the participation's currency differs: a review of
    the merge candidate is exactly the evidence the quorum asks for, so a later
    quota notice about a redundant re-trigger must not deny it.
    """
    state = _classify(proven={'coderabbit': 'inline'}, refused={'coderabbit'})

    assert state == rc.STATE_PARTICIPATED_BUT_EMPTY, f'expected current participation to win, got {state}'


@pytest.mark.parametrize('declined', [{}, {'coderabbit'}, None])
def test_a_refusal_with_no_participation_at_all_still_resolves_refused(declined):
    """The no-participation case is unchanged by the new precedence."""
    state = _classify(refused={'coderabbit'}, declined=declined)

    assert state.startswith('refused_'), f'expected a refusal member, got {state}'
