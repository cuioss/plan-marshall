#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Doc-contract regression for how ``pre-submission-self-review`` may be closed.

``pre-submission-self-review.md`` documents three ways the step reaches
``done``, and only one of them rests on the verifier's stop answer:

* **verifier** — Step 4 Branch A records ``done`` once Step 3b answered
  ``may_close: yes``.
* **not-run** — the zero-generator fallback records ``done`` with no verifier
  answer, because no surfacer ran and there is no round to ask about.
* **operator** — ``manage-status loop-back close`` records ``done`` as an
  operator override, once the step's round budget has refused the next round.

The two existing guards in ``test_pre_submission_self_review_verdict_verdict.py``
sweep the Step 4 branches. They cannot see a close written anywhere else in the
document, and the operator close is written in ``## Round-loop termination``.
This file extends the sweep to the whole document:

(a) Every documented close is one of the three kinds above. A fenced call that
    records ``done`` and is none of them — a bare forced ``mark-step-done``, for
    instance — fails here.
(b) The closes that carry no verifier answer are exactly the not-run fallback
    and the operator close. A third such close fails here.
(c) Every ``mark-step-done`` close sits inside Step 4, where the two existing
    guards read it; the operator close sits inside the termination section.
(d) The only ``manage-status`` verbs the document invokes that can record a
    step are ``mark-step-done`` and ``loop-back close``. A new step-recording
    verb fails here until it is classified.
(e) The termination criterion lists exactly one bullet per close kind.
(f) The operator close is told apart from a verifier close by the facts it
    records, and the document names the value the code records.

Each detector is paired with a mutation guard run against synthetic prose, so a
parser that matched nothing could not leave its assertion vacuously green.
"""

from __future__ import annotations

import re

from _dispatch_roster import section_lines
from conftest import MARKETPLACE_ROOT, load_script_module

_WORKFLOW_DOC = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'workflow' / 'pre-submission-self-review.md'
)

_loop_back = load_script_module('plan-marshall', 'manage-status', '_cmd_loop_back.py', '_operator_close_doc_loop_back')

_STEP_4_HEADING = '### Step 4: Mark Step Complete (inline)'
_VERIFIER_STEP_HEADING = '### Step 3b: Independent verification (dispatch)'
_TERMINATION_HEADING = '## Round-loop termination: converged, not run, and out of budget'

_SUBSECTION_STOPS = ('### ', '## ', '# ')
_SECTION_STOPS = ('## ', '# ')

_FENCED_BASH = re.compile(r'```bash\n(.*?)```', re.DOTALL)
_MANAGE_STATUS_CALL = re.compile(r'manage-status:manage-status\s+(.*)')

_VERB_MARK = 'mark-step-done'
_VERB_CLOSE = 'loop-back close'

#: ``manage-status`` verbs this document invokes that cannot record a step.
_READ_ONLY_VERBS = frozenset({'metadata', 'read'})

#: The verbs through which this document may record the step.
_STEP_RECORDING_VERBS = frozenset({_VERB_MARK, _VERB_CLOSE})

_KIND_VERIFIER = 'verifier'
_KIND_NOT_RUN = 'not-run'
_KIND_OPERATOR = 'operator'
_KIND_UNCLASSIFIED = 'unclassified'

#: The closes that record ``done`` without a verifier answer. This set IS the
#: contract: adding a member is a decision to document another close that no
#: second party agreed to, and it is made here, in the open.
_CLOSES_WITHOUT_A_VERIFIER_ANSWER = frozenset({_KIND_NOT_RUN, _KIND_OPERATOR})

_NOT_RUN_VERDICT = 'self-review not run:'
_STOP_ANSWER_FACT = 'may_close='

#: Each close kind, mapped to the phrase that marks its bullet in the
#: termination criterion.
_TERMINATION_BULLET_MARKERS = {
    _KIND_VERIFIER: 'Step 4 Branch A',
    _KIND_NOT_RUN: 'zero-generator',
    _KIND_OPERATOR: _VERB_CLOSE,
}

_TERMINATION_CRITERION_MARKER = '**The termination criterion'
_BULLET = re.compile(r'^- \*\*([^*]+)\*\* — ', re.MULTILINE)

_VERIFIER_ENUM = re.compile(r'^\s*(may_close|acceptance):\s*([a-z_]+(?:\s*\|\s*[a-z_]+)+)\s*$', re.MULTILINE)


def _doc_text() -> str:
    text: str = _WORKFLOW_DOC.read_text(encoding='utf-8')
    return text


def _section(text: str, heading: str, stops: tuple[str, ...]) -> str:
    return '\n'.join(section_lines(text, heading, stops))


def _manage_status_calls(text: str) -> list[tuple[str, str]]:
    """Return ``(verb, block)`` for every fenced ``manage-status`` call in ``text``.

    The verb is every token between the script notation and the first flag, so
    a two-token verb such as ``loop-back close`` is read whole. Line
    continuations are joined first: a call written across several lines is one
    call.
    """
    calls: list[tuple[str, str]] = []
    for block in _FENCED_BASH.findall(text):
        joined = re.sub(r'\\\n\s*', ' ', block)
        for line in joined.splitlines():
            match = _MANAGE_STATUS_CALL.search(line)
            if not match:
                continue
            verb_tokens: list[str] = []
            for token in match.group(1).split():
                if token.startswith('-'):
                    break
                verb_tokens.append(token)
            calls.append((' '.join(verb_tokens), block))
    return calls


def _records_done(verb: str, block: str) -> bool:
    """Whether a fenced call records the step ``done``.

    A templated mark such as ``--outcome {done|failed}`` names ``done`` among
    its alternatives and so counts: read as no outcome at all, it would drop
    out of the sweep.
    """
    if verb == _VERB_CLOSE:
        return True
    if verb != _VERB_MARK:
        return False
    outcomes = re.findall(r'--outcome\s+(\{[^}]*\}|[a-z_]+)', block)
    return any('done' in outcome.strip('{}').split('|') for outcome in outcomes)


def _close_kind(verb: str, block: str) -> str:
    """Classify one done-recording call by what authorises it."""
    if verb == _VERB_CLOSE:
        return _KIND_OPERATOR
    if verb == _VERB_MARK and _STOP_ANSWER_FACT in block:
        return _KIND_VERIFIER
    if verb == _VERB_MARK and _NOT_RUN_VERDICT in block:
        return _KIND_NOT_RUN
    return _KIND_UNCLASSIFIED


def _closes(text: str) -> list[tuple[str, str, str]]:
    """Return ``(kind, verb, block)`` for every documented close in ``text``."""
    return [
        (_close_kind(verb, block), verb, block)
        for verb, block in _manage_status_calls(text)
        if _records_done(verb, block)
    ]


def _termination_bullets(section: str) -> dict[str, str]:
    """Map each termination-criterion bullet name to its body.

    Read from the criterion marker onward only: the section's earlier bullets
    describe the two halves of the review, not ways the step closes.
    """
    _before, marker, criterion = section.partition(_TERMINATION_CRITERION_MARKER)
    if not marker:
        return {}
    matches = list(_BULLET.finditer(criterion))
    bullets: dict[str, str] = {}
    for position, match in enumerate(matches):
        end = matches[position + 1].start() if position + 1 < len(matches) else len(criterion)
        bullets[match.group(1)] = criterion[match.start() : end]
    return bullets


def _bullets_claimed_by(bullets: dict[str, str]) -> dict[str, list[str]]:
    """Map each close kind to the bullets carrying its marker."""
    return {
        kind: [name for name, body in bullets.items() if marker in body]
        for kind, marker in _TERMINATION_BULLET_MARKERS.items()
    }


def _unclaimed_bullets(bullets: dict[str, str]) -> list[str]:
    """Bullets no close kind's marker matches."""
    return [
        name
        for name, body in bullets.items()
        if not any(marker in body for marker in _TERMINATION_BULLET_MARKERS.values())
    ]


def _verifier_vocabulary(section: str) -> dict[str, set[str]]:
    """The values the verifier may return for each of its two answers."""
    return {field: {value.strip() for value in values.split('|')} for field, values in _VERIFIER_ENUM.findall(section)}


# ---------------------------------------------------------------------------
# Sanity: the population the assertions read is not empty
# ---------------------------------------------------------------------------


def test_the_document_documents_at_least_one_close_of_each_kind():
    kinds = {kind for kind, _verb, _block in _closes(_doc_text())}

    assert kinds >= {_KIND_VERIFIER, _KIND_NOT_RUN, _KIND_OPERATOR}, (
        f'The close walk found only {sorted(kinds)}. Every assertion below is '
        f'quantified over the documented closes, so a kind the walk cannot see '
        f'is a kind nothing here checks.'
    )


# ---------------------------------------------------------------------------
# (a), (b) — the closed set of closes
# ---------------------------------------------------------------------------


def test_every_documented_close_is_one_of_the_three_known_kinds():
    unclassified = [block.strip() for kind, _verb, block in _closes(_doc_text()) if kind == _KIND_UNCLASSIFIED]

    assert not unclassified, (
        'The document records `done` through a call that is neither a verifier '
        'close, the zero-generator fallback, nor the operator close:\n\n'
        + '\n\n'.join(unclassified)
        + '\n\nA `done` no second party agreed to and no operator signed is the '
        'author closing the review on its own verdict.'
    )


def test_the_closes_without_a_verifier_answer_are_exactly_the_fallback_and_the_operator_close():
    """The pin the operator decision asked for: a third such close fails here."""
    without_answer = {kind for kind, _verb, _block in _closes(_doc_text()) if kind != _KIND_VERIFIER}

    assert without_answer == _CLOSES_WITHOUT_A_VERIFIER_ANSWER, (
        f'The document closes the step without a verifier `may_close: yes` on '
        f'{sorted(without_answer)}; the sanctioned set is '
        f'{sorted(_CLOSES_WITHOUT_A_VERIFIER_ANSWER)}. A close added to it is a '
        f'review that can end without anyone but its author agreeing.'
    )


def test_the_operator_close_is_invoked_once_in_the_whole_document():
    operator_blocks = {block for kind, _verb, block in _closes(_doc_text()) if kind == _KIND_OPERATOR}

    assert len(operator_blocks) == 1, (
        f'The operator close is invoked in {len(operator_blocks)} distinct fenced '
        f'calls. One mechanism is documented in one place; a second invocation '
        f'is a second contract to keep in step with the first.'
    )


# ---------------------------------------------------------------------------
# (c) — where each close is documented
# ---------------------------------------------------------------------------


def test_every_mark_step_done_close_sits_inside_step_4():
    """So the two existing Step 4 guards read every one of them."""
    doc = _doc_text()
    step_4 = _section(doc, _STEP_4_HEADING, _SUBSECTION_STOPS)

    outside = [block.strip() for _kind, verb, block in _closes(doc) if verb == _VERB_MARK and block not in step_4]

    assert not outside, (
        f'A `mark-step-done --outcome done` call is documented outside '
        f'{_STEP_4_HEADING!r}:\n\n' + '\n\n'.join(outside) + '\n\nThe guards that '
        'require a stop answer read Step 4 alone, so this call is one they never see.'
    )


def test_the_operator_close_sits_inside_the_termination_section():
    doc = _doc_text()
    termination = _section(doc, _TERMINATION_HEADING, _SECTION_STOPS)

    outside = [
        block.strip() for kind, _verb, block in _closes(doc) if kind == _KIND_OPERATOR and block not in termination
    ]

    assert not outside, (
        f'The operator close is invoked outside {_TERMINATION_HEADING!r}. That '
        f'section is where the close is told apart from a converged one, so an '
        f'invocation elsewhere is documented without that distinction beside it.'
    )


def test_step_4_documents_no_operator_close_of_its_own():
    """Step 4 points at the termination section for the close; it does not invoke it."""
    step_4 = _section(_doc_text(), _STEP_4_HEADING, _SUBSECTION_STOPS)

    assert '"Round-loop termination"' in step_4, (
        'Step 4 no longer points at the termination section, so a reader who '
        'reaches a budget refusal there is told of no sanctioned way to end the loop.'
    )
    assert not [kind for kind, _verb, _block in _closes(step_4) if kind == _KIND_OPERATOR]


# ---------------------------------------------------------------------------
# (d) — the verbs that can record the step
# ---------------------------------------------------------------------------


def test_the_only_step_recording_verbs_invoked_are_mark_step_done_and_loop_back_close():
    verbs = {verb for verb, _block in _manage_status_calls(_doc_text())}

    assert verbs - _READ_ONLY_VERBS == _STEP_RECORDING_VERBS, (
        f'The document invokes the manage-status verbs {sorted(verbs)}. Apart '
        f'from the read-only {sorted(_READ_ONLY_VERBS)}, the verbs that may '
        f'record this step are {sorted(_STEP_RECORDING_VERBS)}. A verb outside '
        f'both sets has not been classified as a way of closing the step or not.'
    )


# ---------------------------------------------------------------------------
# (e) — the termination criterion
# ---------------------------------------------------------------------------


def test_the_termination_criterion_lists_exactly_one_bullet_per_close_kind():
    bullets = _termination_bullets(_section(_doc_text(), _TERMINATION_HEADING, _SECTION_STOPS))
    assert bullets, 'No termination-criterion bullet parsed — the assertions below would be vacuous'

    claimed = _bullets_claimed_by(bullets)

    for kind, names in claimed.items():
        assert len(names) == 1, (
            f'The {kind!r} close is described by {len(names)} termination bullet(s) '
            f'({names}); exactly one must describe it.'
        )
    assert not _unclaimed_bullets(bullets), (
        f'Termination bullet(s) {_unclaimed_bullets(bullets)} describe a close '
        f'that is none of {sorted(_TERMINATION_BULLET_MARKERS)}.'
    )
    assert len(bullets) == len(_TERMINATION_BULLET_MARKERS)


# ---------------------------------------------------------------------------
# (f) — the recorded facts tell the operator close apart
# ---------------------------------------------------------------------------


def test_the_termination_section_names_the_override_facts_the_code_records():
    termination = _section(_doc_text(), _TERMINATION_HEADING, _SECTION_STOPS)
    override = _loop_back.OPERATOR_OVERRIDE

    for fact in ('may_close', 'acceptance'):
        assert f'{fact}={override}' in termination, (
            f'{_TERMINATION_HEADING!r} does not state that the operator close '
            f'records {fact}={override}, which is the value `loop-back close` '
            f'writes. A document naming another value describes a record the '
            f'verb never produces.'
        )
    assert 'may_close=yes' in termination, (
        'The termination section does not state the fact a converged close '
        'carries, so the two closes are not contrasted where the operator close '
        'is introduced.'
    )


def test_the_override_value_is_outside_the_verifier_s_answer_vocabulary():
    """The two closes cannot record the same facts, whatever the verifier answers."""
    vocabulary = _verifier_vocabulary(_section(_doc_text(), _VERIFIER_STEP_HEADING, _SUBSECTION_STOPS))

    assert set(vocabulary) == {'may_close', 'acceptance'}, (
        f'The verifier return contract parsed as {vocabulary}; both answer '
        f'fields must be read for the comparison below to mean anything.'
    )
    for field, values in vocabulary.items():
        assert _loop_back.OPERATOR_OVERRIDE not in values, (
            f'The verifier may answer {field}: {_loop_back.OPERATOR_OVERRIDE}, so '
            f'a step record carrying that value no longer says an operator closed it.'
        )


# ---------------------------------------------------------------------------
# Mutation guards
# ---------------------------------------------------------------------------


def test_the_close_walk_flags_a_bare_forced_mark_and_passes_the_shipped_shapes():
    """A forced `done` with no stop answer and no not-run verdict is unclassified."""
    bare = (
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \\\n'
        '  --plan-id {plan_id} --phase 6-finalize --step default:pre-submission-self-review --outcome done \\\n'
        '  --display-detail "closed on a recorded deviation" --force\n'
        '```\n'
    )
    verifier = bare.replace('--force', '--fact acceptance={acceptance} --fact may_close={may_close} --force')
    not_run = bare.replace('closed on a recorded deviation', 'self-review not run: no surfacer implementor resolved')
    operator = (
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status loop-back close \\\n'
        '  --plan-id {plan_id} --step pre-submission-self-review --head {sha} --rationale "{rationale}"\n'
        '```\n'
    )
    loop_back = bare.replace('--outcome done', '--outcome loop_back --loop-back-target 6-finalize')

    assert [kind for kind, _verb, _block in _closes(bare)] == [_KIND_UNCLASSIFIED]
    assert [kind for kind, _verb, _block in _closes(verifier)] == [_KIND_VERIFIER]
    assert [kind for kind, _verb, _block in _closes(not_run)] == [_KIND_NOT_RUN]
    assert [kind for kind, _verb, _block in _closes(operator)] == [_KIND_OPERATOR]
    # A call that does not record done is not a close at all.
    assert _closes(loop_back) == []


def test_the_verb_walk_reads_a_two_token_verb_and_a_continued_call_whole():
    text = (
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status loop-back close \\\n'
        '  --plan-id {plan_id}\n'
        '```\n\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \\\n'
        '  --plan-id {plan_id} --get --field coverage_scope\n'
        '\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \\\n'
        '  --plan-id {plan_id}\n'
        '```\n'
    )

    assert [verb for verb, _block in _manage_status_calls(text)] == [_VERB_CLOSE, 'metadata', 'read']


def test_the_bullet_partition_flags_a_fourth_close_and_a_missing_one():
    three = (
        f'{_TERMINATION_CRITERION_MARKER} — three closes.** They differ.\n\n'
        '- **Converged** — the step closed on a clean pass (Step 4 Branch A).\n'
        '- **Not run** — the zero-generator close.\n'
        '- **Out of budget** — the operator ran `manage-status loop-back close`.\n'
    )
    four = three + '- **Timed out** — the dispatcher hand-forced a `done` after an hour.\n'
    two = three.replace('- **Not run** — the zero-generator close.\n', '')

    assert _unclaimed_bullets(_termination_bullets(three)) == []
    assert all(len(names) == 1 for names in _bullets_claimed_by(_termination_bullets(three)).values())
    assert _unclaimed_bullets(_termination_bullets(four)) == ['Timed out'], (
        'The bullet partition did not flag a fourth close, so a new way of '
        'closing the step could be listed without failing any assertion'
    )
    assert _bullets_claimed_by(_termination_bullets(two))[_KIND_NOT_RUN] == []


def test_the_verifier_vocabulary_parser_reads_both_answer_enumerations():
    contract = '        status: success\n        acceptance: accepted | refused\n        may_close: yes | no\n'

    assert _verifier_vocabulary(contract) == {'acceptance': {'accepted', 'refused'}, 'may_close': {'yes', 'no'}}
