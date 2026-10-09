#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Producer vocabulary accept and reject directions for verification-feedback."""

from __future__ import annotations

from pathlib import Path

from conftest import MARKETPLACE_ROOT

_DOC = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-marshall' / 'workflow' / 'verification-feedback.md'

_ACCEPT_SET = (
    'build-runner',
    'sonar',
    'pr-comment',
    'plugin-doctor',
    'pr-state',
    'finalize-feedback',
)


def _read_doc() -> str:
    """Return the workflow doc text."""
    return Path(_DOC).read_text(encoding='utf-8')


def test_accept_set_lists_every_producer():
    """The Inputs table accepts every vocabulary member."""
    text = _read_doc()
    for producer in _ACCEPT_SET:
        assert f'`{producer}`' in text, f'accept-set member missing: {producer}'


def test_reject_direction_names_timeout_and_owner():
    """The reject direction states the timeout rejection with its owner."""
    text = _read_doc()
    assert 'ci-verify-timeout' in text, 'rejection target missing'
    assert 'rejected on every producer path' in text, 'rejection scope missing'
    assert 'default:ci-verify' in text, 'rejection owner missing'


def test_single_accept_set_without_second_list():
    """The doc carries one accept-set and no second producer list."""
    text = _read_doc()
    assert text.count('Single accept-set') == 1, 'vocabulary must declare one accept-set'


# ---------------------------------------------------------------------------
# Step 8 and Output: the held ``fixed`` reply
# ---------------------------------------------------------------------------

_STEP_8_HEADING = '## Step 8: Respond loop'
_OUTPUT_HEADING = '## Output'


def _section(text: str, heading: str) -> str:
    """Return the body of the ``##`` section that opens with ``heading``.

    The section runs to the next ``##`` heading. A missing heading fails here, so
    no pin below can pass over an empty slice.
    """
    assert heading in text, f'section heading missing: {heading}'
    start = text.index(heading)
    end = text.find('\n## ', start + len(heading))
    return text[start:] if end == -1 else text[start:end]


def test_step_8_states_that_a_fixed_reply_waits_for_its_stamped_commit():
    """The ordering: held, reported, not transmitted, and by which field."""
    step_8 = _section(_read_doc(), _STEP_8_HEADING)

    assert 'a `fixed` reply waits for its fix commit' in step_8
    assert '`deferred_until_commit[]`' in step_8
    assert '`count_deferred_until_commit`' in step_8
    assert '`fix_commit_sha`' in step_8
    assert '`manage-findings stamp-fix-commit`' in step_8
    assert 'it gets no thread reply and no resolve-thread call' in step_8
    assert 'does not make the run `partial`' in step_8


def test_step_8_holds_a_task_fix_and_an_inline_fix_alike():
    step_8 = _section(_read_doc(), _STEP_8_HEADING)

    assert 'A task fix and an inline fix are held alike' in step_8


def test_step_8_names_the_gitlab_verb_as_not_holding_the_reply():
    """The gap is stated where the rule is, so it is not read as covered."""
    step_8 = _section(_read_doc(), _STEP_8_HEADING)

    assert "The hold-back is the GitHub verb's only — a known gap" in step_8
    assert '`gitlab_pr post_responses`' in step_8
    assert 'transmits a `fixed` finding at once' in step_8


def test_step_8_says_what_the_reviewer_sees_on_each_path_without_a_fix_commit():
    """One row per path that ends after a ``fixed`` disposition with no commit."""
    step_8 = _section(_read_doc(), _STEP_8_HEADING)

    for path in (
        '| The fix task is dropped',
        '| The inline edit is discarded',
        '| The plan is abandoned before another respond pass runs. |',
        '| The finding is re-resolved to another disposition. |',
    ):
        assert path in step_8, f'no-commit path missing from Step 8: {path}'
    # The three paths with no commit leave the thread open and unanswered; the
    # fourth transmits the new disposition.
    assert step_8.count('No reply. The thread stays open.') == 3
    assert 'the new disposition is transmitted normally' in step_8


def test_the_other_four_dispositions_are_transmitted_in_the_first_pass():
    step_8 = _section(_read_doc(), _STEP_8_HEADING)

    assert '(`suppressed`, `accepted`, `taken_into_account`, `rejected`) are transmitted in this pass' in step_8


def test_output_keeps_the_single_annotation_fix_and_holds_its_reply_the_same_way():
    """The inline fix stays an inline-fixable disposition and is held like a task fix."""
    output = _section(_read_doc(), _OUTPUT_HEADING)

    assert 'single-annotation FIX' in output
    assert 'it is not counted in `fix_tasks_created`' in output
    assert 'its `fixed` reply is held until its commit is stamped' in output
