# SPDX-License-Identifier: FSL-1.1-ALv2
"""The prose and the pins say the same thing about a handled CodeRabbit review.

Every document that used to state the re-review / currency behaviour for CodeRabbit
now states the done rule instead: one qualifying review, once every finding of it is
handled, is the review — no later head is re-triggered, awaited or demanded. The
pins below read the REAL documents, so a document that drifts back to the old
wording fails here rather than shipping.

The predicate is exercised against synthetic copies first, so a reader that always
answers "yes" cannot make the real assertions pass.
"""

from __future__ import annotations

import pytest

from conftest import PROJECT_ROOT, get_skill_dir

_FLAG = 'review_complete_after_handling'

_PM = get_skill_dir('plan-marshall', 'automatic-review').parent


def _skill_doc(*parts: str):
    return _PM.joinpath(*parts)


#: The documents that used to state the old behaviour, and therefore must state the rule.
_SURFACE = {
    'automatic-review/SKILL.md': _skill_doc('automatic-review', 'SKILL.md'),
    'automatic-review/standards/coderabbit.md': _skill_doc('automatic-review', 'standards', 'coderabbit.md'),
    'automatic-review/standards/bot-participation-contract.md': _skill_doc(
        'automatic-review', 'standards', 'bot-participation-contract.md'
    ),
    'workflow-integration-github/SKILL.md': _skill_doc('workflow-integration-github', 'SKILL.md'),
    'phase-6-finalize/standards/branch-cleanup-rereview.md': _skill_doc(
        'phase-6-finalize', 'standards', 'branch-cleanup-rereview.md'
    ),
    'phase-6-finalize/standards/branch-cleanup.md': _skill_doc('phase-6-finalize', 'standards', 'branch-cleanup.md'),
    'runbook-lane/SKILL.md': _skill_doc('runbook-lane', 'SKILL.md'),
    'manage-config/standards/data-model.md': _skill_doc('manage-config', 'standards', 'data-model.md'),
    'tools-integration-ci/standards/pr-review-operations.md': _skill_doc(
        'tools-integration-ci', 'standards', 'pr-review-operations.md'
    ),
    'workflow-pr-doctor/standards/automated-review-lifecycle.md': _skill_doc(
        'workflow-pr-doctor', 'standards', 'automated-review-lifecycle.md'
    ),
    'doc/user/configuration.adoc': PROJECT_ROOT / 'doc' / 'user' / 'configuration.adoc',
    'doc/user/parallelism-and-locking.adoc': PROJECT_ROOT / 'doc' / 'user' / 'parallelism-and-locking.adoc',
}


def _states_done_rule(text: str) -> bool:
    """Whether ``text`` states the done rule by its registry flag."""
    return _FLAG in text


_OLD_WORDING = """\
A required bot whose participation is stale is triggered whatever the knob says.
"""


def test_the_predicate_rejects_a_planted_copy_of_the_old_wording():
    """Negative control: the old sentence alone does not state the rule."""
    assert not _states_done_rule(_OLD_WORDING)


def test_the_predicate_accepts_a_copy_that_states_the_rule():
    """Positive control over the same synthetic family."""
    assert _states_done_rule('A bot declaring `review_complete_after_handling` is never triggered again.')


@pytest.mark.parametrize('label', sorted(_SURFACE))
def test_each_surface_document_states_the_done_rule(label):
    """Fail on a planted copy of the old sentence in ANY surface document's family."""
    path = _SURFACE[label]
    assert path.is_file(), f'{label} is missing at {path}'
    assert _states_done_rule(path.read_text(encoding='utf-8')), f'{label} does not state the done rule'


def test_coderabbit_registry_block_declares_the_flag():
    """The rule is registry data, declared in the bot's own machine-readable block."""
    text = _SURFACE['automatic-review/standards/coderabbit.md'].read_text(encoding='utf-8')
    block = text.split('```yaml', 1)[1].split('```', 1)[0]

    assert f'{_FLAG}: true' in block


def test_the_triggered_whatever_the_gate_says_sentence_is_bound_to_an_unflagged_bot():
    """The old absolute sentence survives only beside the bot the rule does not cover."""
    text = _SURFACE['automatic-review/SKILL.md'].read_text(encoding='utf-8')
    section = text.split('### Re-review after a loop-back fix commit (trigger B)', 1)[1]
    section = section.split('\n### ', 1)[0]

    assert 'triggered whatever the knob says' in section
    assert f'A bot declaring `{_FLAG}` is never in either list' in section


def test_the_operator_policy_is_scoped_to_the_no_review_case():
    """The "nothing is a reason to merge without the review" ruling names its scope."""
    text = _SURFACE['automatic-review/standards/coderabbit.md'].read_text(encoding='utf-8')

    assert 'no-review case' in text
    assert 'Nothing about a spent quota is a reason to merge without the review.' in text


def test_the_lane_merge_gate_states_the_done_satisfaction():
    """Section 7's first condition names the reviewer class the currency demand skips."""
    text = _SURFACE['runbook-lane/SKILL.md'].read_text(encoding='utf-8')
    merge_gate = text.split('## 7. Merge gate', 1)[1]

    assert f'marks `{_FLAG}`' in merge_gate
    assert 'Satisfied by done' in merge_gate
