#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Producer vocabulary accept and reject directions for verification-feedback."""

from __future__ import annotations

import re
from pathlib import Path

from conftest import MARKETPLACE_ROOT, load_script_module

_DOC = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-marshall' / 'workflow' / 'verification-feedback.md'

_CI_VERIFY = load_script_module('plan-marshall', 'phase-6-finalize', 'ci_verify.py', '_producer_vocab_ci_verify')

#: The prose that declares the one accept-set, parsed rather than copied so the
#: test reads the contract the workflow actually states.
_ACCEPT_SET_SENTENCE = re.compile(r'Single accept-set: one of (?P<members>[^.]+)\.')


def _read_doc() -> str:
    """Return the workflow doc text."""
    return Path(_DOC).read_text(encoding='utf-8')


def _accept_set() -> set[str]:
    """Return the producer values the Inputs table accepts, parsed from the doc."""
    match = _ACCEPT_SET_SENTENCE.search(_read_doc())
    assert match is not None, 'the Inputs table must declare the single accept-set'
    members = set(re.findall(r'`([^`]+)`', match.group('members')))
    assert members, 'the accept-set sentence names no producer value'
    return members


def _ci_verify_producers(tmp_path) -> set[str]:
    """Collect every producer value ``ci_verify`` can return.

    Two sources: the pure classifier swept over every conclusion it branches on
    (under both wait outcomes), and the no-checks partition the classifier never
    reaches. Reading the module's own constant would only re-state the code; the
    sweep exercises the branches.
    """
    producers: set[str] = set()
    for conclusion in (
        'failure',
        'failed',
        'cancelled',
        'canceled',
        'action_required',
        'stale',
        'timed_out',
        'timeout',
        'pending',
        '',
    ):
        for workflow in ('verify', 'license/cla', 'build / sonar-build'):
            check = {'conclusion': conclusion, 'workflow_name': workflow}
            for wait_outcome in ('completed', 'deadline_exceeded'):
                producer, _subtype = _CI_VERIFY.classify_check(check, wait_outcome)
                producers.add(producer)

    no_checks = _CI_VERIFY.verify(
        plan_id='producer-vocab',
        pr_number=1,
        worktree_path=str(tmp_path),
        provider='github',
        final_status='none',
        wait_outcome='completed',
        head_sha='',
        ci_status_runner=lambda *_args: {'status': 'success', 'checks': []},
        persist_runner=lambda **_kwargs: {'status': 'success'},
        findings_runner=lambda **_kwargs: {'status': 'success'},
        mark_done_runner=lambda **_kwargs: {'status': 'success'},
        git_head_resolver=lambda *_args: 'x',
    )
    producers.update(no_checks['producers'])
    return producers


def test_every_producer_ci_verify_can_emit_is_accepted(tmp_path):
    """Every producer ``ci_verify`` returns is a member of the accept-set.

    This is the contract the red-CI route needs: the dispatcher hands the
    returned producer to ``verification-feedback``, whose Step 1 guard refuses
    anything outside the single accept-set with ``unknown_producer``.
    """
    producers = _ci_verify_producers(tmp_path)
    assert producers, 'the producer sweep found nothing — it cannot fail while claiming to guard'
    refused = sorted(producers - _accept_set())
    assert not refused, f'ci_verify returns producer value(s) the workflow refuses: {refused}'


def test_accept_set_is_the_expected_closed_vocabulary():
    """The Inputs table declares exactly the expected members.

    Parsing the set off the doc keeps the test reading the contract rather than
    a copy; pinning the parsed value keeps the guard able to fail when a member
    is silently dropped or added.
    """
    assert _accept_set() == {
        'build-runner',
        'sonar',
        'pr-comment',
        'plugin-doctor',
        'pr-state',
        'finalize-feedback',
        'ci-verify',
    }


def test_taxonomy_tags_are_subtypes_not_producer_values():
    """The ci-verify taxonomy tags are finding subtypes, never producer values.

    The former rule rejected `ci-verify-timeout` on every producer path while
    the taxonomy still carried it as a producer string. One producer value plus
    a subtype tag removes the contradiction: nothing in the taxonomy is a
    producer value, so nothing can be rejected as one.
    """
    text = _read_doc()
    assert 'ci-verify' in _accept_set(), 'the ci-verify producer must be accepted'
    assert 'ci-verify-timeout' not in _accept_set(), 'a taxonomy tag is not a producer value'
    assert 'ci_build_failure' in text, 'the subtype tags must be documented as the per-row distinction'


def test_ci_verify_branch_reaches_the_shared_ingestion_step():
    """A ``producer=ci-verify`` dispatch falls through to Step 1.4, not an error."""
    text = _read_doc()
    assert 'producer=ci-verify' in text, 'no Step 1 branch for the ci-verify producer'
    # Slice to the next ``###`` branch so a fall-through stated by a DIFFERENT
    # branch cannot satisfy this assertion.
    branch = text.split('producer=ci-verify', 1)[1].split('\n### ', 1)[0]
    assert 'Step 1.4' in branch, 'the ci-verify branch must fall through to the shared ingestion step'
    assert 'plan-marshall:phase-6-finalize' in branch, 'the branch must scope its store query to ci-verify findings'
    assert "--file-pattern '*artifacts/ci-runs/*'" in branch, (
        'the store query must use the leading wildcard: persisted pointers are '
        'anchored at `.plan` (`local/plans/{plan_id}/artifacts/...`)'
    )
    assert '--component plan-marshall:phase-6-finalize' in branch, (
        "the branch must scope the query to the executor's component"
    )


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


def test_step_8_releases_a_fixed_reply_only_on_the_head_once_its_ci_has_passed():
    """The release condition is the stamp on the head AND that head's CI having passed."""
    step_8 = _section(_read_doc(), _STEP_8_HEADING)

    assert 'a `fixed` reply waits for its fix commit and a passing head' in step_8
    assert (
        "The reply is released when that stamped commit is on the pull request head AND the head's CI has passed"
    ) in step_8
    assert '"fixed" points the reviewer at the head, so the head has to be shown to work first' in step_8
    # The escape flag stays the only bypass, and does not reach a stamped finding.
    assert 'The flag reaches a finding with no stamp only, and is the only bypass' in step_8
    assert 'is checked against the pull request head and that head\'s CI as in "Ordering" below' in step_8


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
