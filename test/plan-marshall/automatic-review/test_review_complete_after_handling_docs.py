# SPDX-License-Identifier: FSL-1.1-ALv2
"""The prose and the pins say the same thing about a handled CodeRabbit review.

Every document that used to state the re-review / currency behaviour for CodeRabbit
now states the done rule instead: one qualifying review, once every finding of it is
handled, is the review — no later head is re-triggered, awaited or demanded. The pins
below read the REAL documents, in the SECTION that stated the old behaviour, and each
document family carries a planted-copy control: the real text with its done-rule
sentence replaced by the old one must fail. A pin that only looks for the flag
somewhere in the file cannot fail that way, because the rest of the file still names
it — which is exactly the weakness these controls exist to close.
"""

from __future__ import annotations

import pytest

from conftest import PROJECT_ROOT, get_skill_dir

_FLAG = 'review_complete_after_handling'
_OLD = 'A stale CodeRabbit review is re-triggered after every push.'

_SKILLS = get_skill_dir('plan-marshall', 'automatic-review').parent


def _doc(*parts: str):
    return _SKILLS.joinpath(*parts)


#: label -> (path, section marker, the done-rule snippet that section must carry).
_SURFACE = {
    'automatic-review/SKILL.md': (
        _doc('automatic-review', 'SKILL.md'),
        '### Re-review after a loop-back fix commit (trigger B)',
        f'A bot declaring `{_FLAG}` is never in either list',
    ),
    'automatic-review/standards/coderabbit.md': (
        _doc('automatic-review', 'standards', 'coderabbit.md'),
        '## Re-review',
        'One handled review is the review',
    ),
    'automatic-review/standards/bot-participation-contract.md': (
        _doc('automatic-review', 'standards', 'bot-participation-contract.md'),
        '### The review-complete-after-handling declaration',
        'What the flag changes',
    ),
    'workflow-integration-github/SKILL.md': (
        _doc('workflow-integration-github', 'SKILL.md'),
        '#### The one handled review',
        'review_on_record_done',
    ),
    'phase-6-finalize/standards/branch-cleanup-rereview.md': (
        _doc('phase-6-finalize', 'standards', 'branch-cleanup-rereview.md'),
        '## Re-review the rebased HEAD (trigger A)',
        f'A bot declaring `{_FLAG}` is never re-reviewed here',
    ),
    'phase-6-finalize/standards/branch-cleanup.md': (
        _doc('phase-6-finalize', 'standards', 'branch-cleanup.md'),
        '#### Predicate 2 — required-bot participation against this HEAD',
        'appears in BOTH sets is DONE',
    ),
    'runbook-lane/SKILL.md': (
        _doc('runbook-lane', 'SKILL.md'),
        '## 7. Merge gate',
        'Satisfied by done',
    ),
    'runbook-lane/SKILL.md#section-6-step-6': (
        _doc('runbook-lane', 'SKILL.md'),
        '6. **After every push, re-trigger**',
        _FLAG,
    ),
    'manage-config/standards/data-model.md': (
        _doc('manage-config', 'standards', 'data-model.md'),
        '`re_review_on_loopback`',
        'never re-triggered for a later HEAD',
    ),
    'tools-integration-ci/standards/pr-review-operations.md': (
        _doc('tools-integration-ci', 'standards', 'pr-review-operations.md'),
        '- `participated_stale` — the bot DID publish',
        _FLAG,
    ),
    'workflow-pr-doctor/standards/automated-review-lifecycle.md': (
        _doc('workflow-pr-doctor', 'standards', 'automated-review-lifecycle.md'),
        '`participated_stale` (the bot published',
        _FLAG,
    ),
    'doc/user/configuration.adoc': (
        PROJECT_ROOT / 'doc' / 'user' / 'configuration.adoc',
        're_review_on_loopback` | `false`',
        _FLAG,
    ),
    'doc/user/parallelism-and-locking.adoc': (
        PROJECT_ROOT / 'doc' / 'user' / 'parallelism-and-locking.adoc',
        'NOTE: Leaving `re_review_on_loopback` off',
        _FLAG,
    ),
}

#: How far past the marker the snippet may sit. Wide enough for a section, narrow
#: enough that a sentence in a LATER section cannot satisfy this one.
_WINDOW = 6000


def _states_done_rule(text: str, marker: str, snippet: str) -> bool:
    """Whether the section opened by ``marker`` carries ``snippet``."""
    start = text.find(marker)
    if start < 0:
        return False
    return snippet in text[start : start + _WINDOW]


def test_the_predicate_rejects_a_planted_copy_of_the_old_sentence():
    """Negative control: the old sentence beside the marker does not state the rule."""
    planted = '## Re-review\n\n' + _OLD + '\n'

    assert not _states_done_rule(planted, '## Re-review', 'One handled review is the review')


def test_the_predicate_accepts_the_rule_in_its_section():
    """Positive control over the same synthetic family."""
    fresh = '## Re-review\n\nOne handled review is the review.\n'

    assert _states_done_rule(fresh, '## Re-review', 'One handled review is the review')


@pytest.mark.parametrize('label', sorted(_SURFACE))
def test_each_surface_document_states_the_done_rule_in_its_section(label):
    """A document that drifts back to the old wording fails HERE, not in review."""
    path, marker, snippet = _SURFACE[label]
    assert path.is_file(), f'{label} is missing at {path}'
    assert _states_done_rule(path.read_text(encoding='utf-8'), marker, snippet), (
        f'{label} does not state the done rule in the section opened by {marker!r}'
    )


#: Real sentences the plan retired, quoted exactly as the old documents carried them.
#: None may reappear anywhere in the tree. Unlike an invented literal, a hit on one of
#: these IS the old behaviour coming back.
_RETIRED = (
    'Without such a reply the bot stays stale and is re-triggered. See',
    'its review is on record for the merge candidate and pending_findings',
)
_OLD = _RETIRED[0]


@pytest.mark.parametrize('label', sorted(_SURFACE))
def test_a_planted_copy_of_the_old_wording_fails_in_every_document(label):
    """Mutation control per pinned document: remove the rule, the pin must go red.

    The mutation replaces the rule sentence the pin searches for with the retired
    wording, so the control proves the pin is anchored to the rule text rather than to
    the flag's presence elsewhere in the file. It is a mutation by construction — the
    mutation IS what the pin is meant to catch.
    """
    path, marker, snippet = _SURFACE[label]
    text = path.read_text(encoding='utf-8')
    assert _states_done_rule(text, marker, snippet), f'{label} does not carry the rule sentence to mutate'

    planted = text.replace(snippet, _OLD)
    assert planted != text, f'the rule sentence is not in {label} — the control would be vacuous'
    assert not _states_done_rule(planted, marker, snippet), (
        f'a planted copy of the old sentence still passes for {label}: the pin is too loose'
    )


def test_coderabbit_registry_block_declares_the_flag():
    """The rule is registry data, declared in the bot's own machine-readable block."""
    path = _SURFACE['automatic-review/standards/coderabbit.md'][0]
    block = path.read_text(encoding='utf-8').split('```yaml', 1)[1].split('```', 1)[0]

    assert f'{_FLAG}: true' in block


def _documents_under(root):
    return [path for pattern in ('*.md', '*.adoc') for path in root.rglob(pattern)]


def _states_old_sentence(text: str) -> bool:
    return any(sentence in text for sentence in _RETIRED)


def test_no_document_states_the_retired_wording():
    """No document anywhere may still say a stale CodeRabbit review is re-triggered."""
    documents = _documents_under(_SKILLS) + _documents_under(PROJECT_ROOT / 'doc')
    assert documents, 'no documents were discovered — the sweep would be vacuous'
    offenders = [
        str(path.relative_to(PROJECT_ROOT))
        for path in documents
        if _states_old_sentence(path.read_text(encoding='utf-8'))
    ]

    assert offenders == [], f'documents state the retired wording: {offenders}'


@pytest.mark.parametrize('sentence', _RETIRED)
def test_the_retired_wording_sweep_detects_each_planted_sentence(sentence, tmp_path):
    """Positive control: every retired sentence IS reported when planted."""
    assert sentence not in ''.join(path.read_text(encoding='utf-8') for path in _documents_under(_SKILLS)), (
        f'the retired sentence is still in the tree: {sentence!r}'
    )
    planted = tmp_path / 'planted.md'
    planted.write_text(f'## Re-review\n\n{sentence}\n', encoding='utf-8')

    assert _states_old_sentence(planted.read_text(encoding='utf-8'))


def test_the_triggered_whatever_the_gate_says_sentence_is_bound_to_an_unflagged_bot():
    """The old absolute sentence survives only beside the bot the rule does not cover."""
    text = _SURFACE['automatic-review/SKILL.md'][0].read_text(encoding='utf-8')
    section = text.split('### Re-review after a loop-back fix commit (trigger B)', 1)[1].split('\n### ', 1)[0]

    assert 'triggered whatever the knob says' in section
    assert f'A bot declaring `{_FLAG}` is never in either list' in section


def test_the_operator_policy_is_scoped_to_the_no_review_case():
    """The "nothing is a reason to merge without the review" ruling names its scope."""
    text = _SURFACE['automatic-review/standards/coderabbit.md'][0].read_text(encoding='utf-8')

    assert 'no-review case' in text
    assert 'Nothing about a spent quota is a reason to merge without the review.' in text
