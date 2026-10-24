#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Derivation guard for the branch-cleanup conflict gate (PLAN-LB-53 D2).

The observed failure this file pins: the Conflict-Severity Classifier reported
``overlap_with_content_conflict … needs_user``, and branch-cleanup still told the
operator "No rebase or force-push will happen — the merge queue rebases", then
asked them to wait for a queue the PR could not enter. The conflict surfaced much
later and was hand-rebased, force-pushed and merged without a second question.

Two mechanisms replace that:

(1) **The question is composed from the verdict, and it states the conflict.**
    ``conflict_gate gate`` returns ``question_required``, the prompt (naming the
    conflicting files and the base) and ``queue_wait: forbidden``. A content
    conflict with no files to name is refused outright rather than asked about
    vaguely.
(2) **The answer authorizes the action, per action.** ``push-authorization``
    resolves the selected option label and admits a rebase or a force-push only
    when that option's own ``authorizes`` list contains it. Free text authorizes
    nothing.

Vacuity traps avoided, both observed in this area: a question-text assertion is
made against the STRUCTURED description the script returns (never against a
sentence in the document), and every "not offered" assertion is paired with a
positive control that the same predicate DOES accept the authorizing option — so a
predicate that matched nothing could not pass.
"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from typing import Any, cast

import pytest

from conftest import MARKETPLACE_ROOT, load_script_module

_conflict = load_script_module('plan-marshall', 'phase-6-finalize', 'conflict_gate.py', '_d2_conflict_gate')

evaluate_gate = _conflict.evaluate_gate
authorize_push = _conflict.authorize_push
cmd_gate = _conflict.cmd_gate
_split_conflicts = _conflict._split_conflicts

_BRANCH_CLEANUP_DOC: Path = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'standards' / 'branch-cleanup.md'
)

_CONFLICT_FILES = ['src/main/java/de/cuioss/Api.java', 'src/main/java/de/cuioss/ApiBuilder.java']
_BASE = 'main'


def _content_conflict_gate(**overrides) -> dict[str, Any]:
    kwargs = {
        'classification': 'overlap_with_content_conflict',
        'decision': 'needs_user',
        'conflicts': list(_CONFLICT_FILES),
        'base': _BASE,
        'threshold': 'no_overlap_only',
        'use_merge_queue': False,
        'state': 'open',
    }
    kwargs.update(overrides)
    return cast(dict[str, Any], evaluate_gate(**kwargs))


# ---------------------------------------------------------------------------
# Done when: needs_user becomes a question naming the files, with no queue wait
# ---------------------------------------------------------------------------


def test_a_content_conflict_becomes_a_question_naming_the_files_and_the_base():
    """The gate asks, and the question states the conflict it is asking about.

    Done-when clause: *"a test feeds `overlap_with_content_conflict` / `needs_user`
    into branch-cleanup and reads a question naming the conflicting files and no
    merge-queue wait"*.
    """
    payload = _content_conflict_gate()

    assert payload['status'] == 'success', payload
    assert payload['question_required'] is True
    assert payload['decision'] == 'needs_user'
    assert payload['conflicting_files'] == _CONFLICT_FILES

    description = str(payload['prompt_description'])
    for path in _CONFLICT_FILES:
        assert path in description, f'the question does not name {path!r}: {description!r}'
    assert _BASE in description
    assert _BASE in payload['prompt_question']


def test_the_content_conflict_gate_forbids_a_merge_queue_wait():
    """``queue_wait: forbidden``, and no offered option waits for a queue.

    The queue wait is the specific untruth of the observed run: it was promised as
    the path while nothing was actually waiting on a queue.
    """
    payload = _content_conflict_gate()

    assert payload['queue_wait'] == 'forbidden'
    assert 'queue_wait_reason' in payload
    assert payload['plan_actions'] == [], 'a question that asks nothing may claim no planned action'
    for option in payload['options']:
        label = option['label'].lower()
        description = option['description'].lower()
        assert 'queue' not in label, f'option {option["label"]!r} offers a queue wait'
        assert 'merge queue' not in description, f'option {option["label"]!r} describes a queue wait'


def test_the_authorizing_option_is_offered_as_a_positive_control():
    """The same option population DOES contain the rebase+push choice.

    Paired with the "no queue" assertion above so the predicate cannot pass by
    matching nothing: the option list is non-empty and contains the authorizing
    option, from which the negative assertion is then taken.
    """
    payload = _content_conflict_gate()
    labels = [option['label'] for option in payload['options']]

    assert labels, 'the gate offered no options at all, so the "no queue wait" assertion is vacuous'
    authorizing = [option for option in payload['options'] if 'force-push' in option['authorizes']]
    assert len(authorizing) == 1, f'expected exactly one option to authorize a force-push, got {authorizing}'
    assert authorizing[0]['label'] in labels


def test_a_content_conflict_without_files_is_refused():
    """A prompt that cannot name the conflict is not composed at all."""
    payload = _content_conflict_gate(conflicts=[])

    assert payload['status'] == 'error'
    assert payload['error'] == 'conflict_files_required'


def test_an_auto_proceed_verdict_asks_nothing_and_permits_the_queue_wait():
    """The prohibition is scoped to the asked path — the clean route is unchanged."""
    payload = evaluate_gate(
        classification='no_overlap',
        decision='auto_proceed',
        conflicts=[],
        base=_BASE,
        threshold='no_overlap_only',
        use_merge_queue=True,
        state='open',
    )

    assert payload['status'] == 'success'
    assert payload['question_required'] is False
    assert payload['queue_wait'] == 'permitted'
    assert payload['plan_actions'] == ['ci-snapshot', 'local-cleanup']
    assert 'options' not in payload


def test_the_immediate_merge_route_reports_the_actions_it_will_perform():
    """On the non-queue route the auto-proceed actions are the rebase and the push."""
    payload = evaluate_gate(
        classification='no_overlap',
        decision='auto_proceed',
        conflicts=[],
        base=_BASE,
        threshold='no_overlap_only',
        use_merge_queue=False,
        state='open',
    )

    assert payload['plan_actions'] == ['rebase', 'force-push', 'ci-wait', 'local-cleanup']


def test_a_merged_pr_asks_only_about_local_cleanup():
    """``state == merged`` has no conflict to route — it confirms cleanup, not a rebase."""
    payload = evaluate_gate(
        classification='no_overlap',
        decision='needs_user',
        conflicts=[],
        base=_BASE,
        threshold='no_overlap_only',
        use_merge_queue=False,
        state='merged',
    )

    assert payload['question_required'] is True
    assert payload['queue_wait'] == 'forbidden'
    assert payload['plan_actions'] == []
    # Neither merged option authorizes a push-preparation action: there is none to do.
    assert [option['authorizes'] for option in payload['options']] == [[], []]


def test_a_content_conflict_with_an_auto_proceed_decision_is_refused():
    """The two halves of the verdict must agree — a caller bug cannot skip the question."""
    payload = _content_conflict_gate(decision='auto_proceed')

    assert payload['status'] == 'error'
    assert payload['error'] == 'decision_contradicts_classification'


def test_an_unknown_classification_is_refused():
    """The vocabulary is closed; a verdict outside it is a caller error, not a guess."""
    payload = _content_conflict_gate(classification='conflicted')

    assert payload['status'] == 'error'
    assert payload['error'] == 'invalid_classification'


# ---------------------------------------------------------------------------
# Done when: the force-push is refused when the answer did not authorize it
# ---------------------------------------------------------------------------


def test_the_force_push_is_refused_when_the_answer_names_no_action():
    """A real gate option that authorizes nothing does not authorize a push.

    Done-when clause: *"a test reads the force-push refused when the operator's
    answer did not authorize it"*.
    """
    payload = _content_conflict_gate()
    stopping = next(option['label'] for option in payload['options'] if option['authorizes'] == [])

    result = authorize_push(stopping, 'force-push')

    assert result['status'] == 'error'
    assert result['error'] == 'push_not_authorized'
    assert result['authorized'] is False
    assert result['matched_option'] == stopping
    assert result['option_authorizes'] == []


def test_free_text_authorizes_nothing():
    """An answer that resolves to no option is not a selection, and says so."""
    result = authorize_push('ok, go ahead', 'force-push')

    assert result['status'] == 'error'
    assert result['error'] == 'push_not_authorized'
    assert result['authorized'] is False
    assert result['matched_option'] is None
    authorizing = result['authorizing_options']
    assert authorizing, 'the refusal names no authorizing option, so it gives the caller nowhere to go'
    assert authorize_push(authorizing[0], 'force-push')['authorized'] is True


def test_the_authorizing_option_admits_the_rebase_and_the_push():
    """The one option that names both actions authorizes both, and only those."""
    payload = _content_conflict_gate()
    authorizing = next(option['label'] for option in payload['options'] if 'force-push' in option['authorizes'])

    assert authorize_push(authorizing, 'force-push')['authorized'] is True
    assert authorize_push(authorizing, 'rebase')['authorized'] is True

    # ... and it still authorizes nothing outside its own label's actions.
    assert authorize_push(authorizing, 'merge')['error'] == 'unknown_action'


def test_answer_matching_tolerates_case_and_spacing_but_not_paraphrase():
    """A UI may return the label with different whitespace; it never paraphrases."""
    payload = _content_conflict_gate()
    authorizing = next(option['label'] for option in payload['options'] if 'force-push' in option['authorizes'])

    noisy = f'  {authorizing.upper().replace(" ", "   ")}  '
    assert authorize_push(noisy, 'force-push')['authorized'] is True
    assert authorize_push('Rebase and push please', 'force-push')['authorized'] is False


def test_a_blank_answer_is_refused() -> None:
    """Nothing is authorized by nothing."""
    result = authorize_push('   ', 'force-push')

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_answer'


def test_the_cli_wraps_both_verbs(capsys):
    """The executor-facing surface answers in TOON for both verbs."""
    cmd_gate(
        Namespace(
            plan_id='conflict-cli',
            classification='overlap_with_content_conflict',
            decision='needs_user',
            conflicts=','.join(_CONFLICT_FILES),
            base=_BASE,
            threshold='no_overlap_only',
            use_merge_queue=False,
            state='open',
            head_branch='feature/x',
            pr_url='https://example.test/pr/1',
        )
    )
    out = capsys.readouterr().out
    assert 'question_required: true' in out
    assert 'queue_wait: forbidden' in out
    assert _CONFLICT_FILES[0] in out


def test_the_conflict_list_is_split_and_deduped():
    """A repeated path in the classifier's list is one file, not two."""
    assert _split_conflicts('a.java, b.java,,a.java ') == ['a.java', 'b.java']


# ---------------------------------------------------------------------------
# The step document dispatches the gate (so the mechanism stays wired)
# ---------------------------------------------------------------------------


def test_branch_cleanup_dispatches_the_conflict_gate_before_composing_its_question():
    """The document routes its gate through the script, in both directions."""
    text = _BRANCH_CLEANUP_DOC.read_text(encoding='utf-8')

    gate_section = text.split('### Conflict-Severity Classifier', 1)[1].split('### Pre-Rebase Confirmation Gate', 1)[0]
    assert 'phase-6-finalize:conflict_gate gate' in gate_section, (
        'the classifier section no longer hands the verdict to conflict_gate gate, so the prompt is '
        'composed by hand again'
    )
    assert 'queue_wait: forbidden' in gate_section
    assert 'conflict_files_required' in gate_section

    rebase_section = text.split('### Rebase Branch onto Base', 1)[1].split('### Re-review the rebased HEAD', 1)[0]
    assert 'phase-6-finalize:conflict_gate push-authorization' in rebase_section, (
        'the force-push path no longer checks that the operator answer authorizes it'
    )
    # Both actions are checked at the sites that take them, so the rebase-specific
    # admission cannot quietly disappear while the force-push one keeps the test green.
    assert '--action rebase' in rebase_section, 'the rebase itself is no longer authorized at its site'
    assert '--action force-push' in rebase_section, 'the force-push is no longer authorized at its site'
    assert 'pre-commit-verify-freshness' in rebase_section, (
        'the force-push path no longer gates on pre-push freshness for the rebased head'
    )


def test_branch_cleanup_no_longer_presents_a_hand_written_pre_rebase_prompt():
    """The pre-rebase prompt template is gone — a hand-written one is what drifted."""
    text = _BRANCH_CLEANUP_DOC.read_text(encoding='utf-8')
    pre_rebase = text.split('### Pre-Rebase Confirmation Gate', 1)[1].split('### Safety Check: Other Open PRs', 1)[0]

    assert 'label: "Yes, proceed (recommended)"' not in pre_rebase, (
        'a hand-written option list is back in the pre-rebase gate: the option labels are the '
        'authorization vocabulary, so a second copy can authorize nothing the gate knows'
    )
