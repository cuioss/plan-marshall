# SPDX-License-Identifier: FSL-1.1-ALv2
"""Doc-contract tests for the domain content rules this plan lands.

Each test pins one rule the guidance must carry, against the real bundle
document that owns it. They read the shipped Markdown, never a copy, so a rule
that is deleted or reworded into something else reds here.

The review-rule helpers below read a ``## Review Rules`` block the way the
code-review pack generator does: bullets of that section, wrapped continuation
lines joined, up to the next heading of the same-or-higher level. The block
contract itself is stated once in ``review-rubric.md`` section 10 and is not
restated in the documents under test.
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import get_skill_dir

#: Phrases that make the pack generator drop a harvested rule. A rule written
#: with one never reaches a reviewer, so its presence is a defect, not a style
#: preference.
_WITHHOLDING_MARKERS = (
    'do not duplicate',
    'only when you can name',
    'do not report',
    "don't report",
    'no need to report',
)


def _section(body: str, heading: str) -> str:
    """The text of one Markdown section, up to the next same-or-higher heading."""
    level = len(heading) - len(heading.lstrip('#'))
    start = body.index(heading + '\n')
    rest = body[start + len(heading) + 1 :]
    stop = re.search(rf'^#{{1,{level}}} ', rest, re.MULTILINE)
    return rest[: stop.start()] if stop else rest


def _bullets(section: str) -> list[str]:
    """The bullets of a section, with wrapped continuation lines joined."""
    bullets: list[str] = []
    for line in section.splitlines():
        if line.startswith('- '):
            bullets.append(line[2:].strip())
        elif bullets and line.strip() and line[:1].isspace():
            bullets[-1] = f'{bullets[-1]} {line.strip()}'
    return [bullet for bullet in bullets if bullet]


def _review_rules(skill_dir: Path) -> list[str]:
    """The bullets of a skill's ``## Review Rules`` block."""
    return _bullets(_section((skill_dir / 'SKILL.md').read_text(encoding='utf-8'), '## Review Rules'))


def _assert_harvestable(rule: str) -> None:
    """The harvestable-block contract, applied to one rule.

    One rule per bullet is structural (the caller reads bullets), so what is
    checked here is the pair a reader can see: a mechanism-naming ``so`` clause
    and no withholding phrase.
    """
    assert rule.strip(), 'a harvested rule must carry text'
    assert ' so ' in rule, f'a rule must name the mechanism that goes wrong: {rule!r}'
    lowered = rule.lower()
    offenders = [marker for marker in _WITHHOLDING_MARKERS if marker in lowered]
    assert not offenders, f'a rule carries withholding language {offenders}: {rule!r}'


def _rule_containing(rules: list[str], *needles: str) -> str:
    """The single rule whose text carries every needle, else a diagnostic failure."""
    hits = [rule for rule in rules if all(needle.lower() in rule.lower() for needle in needles)]
    assert len(hits) == 1, f'expected exactly one rule carrying {needles}, found {hits}'
    return hits[0]


# ---------------------------------------------------------------------------
# D1 — JavaDoc review rules: restated counts and unverified ordering claims
# ---------------------------------------------------------------------------


def test_javadoc_review_rules_hold_the_restated_count_and_ordering_rules():
    rules = _review_rules(get_skill_dir('pm-dev-java', 'javadoc'))

    assert len(rules) == 6, f'the javadoc block holds four rules plus the two this plan adds: {rules}'

    count_rule = _rule_containing(rules, 'count', 'declaring')
    _assert_harvestable(count_rule)

    ordering_rule = _rule_containing(rules, 'ordering', 'call')
    _assert_harvestable(ordering_rule)


def test_javadoc_method_standard_requires_checking_an_ordering_claim_at_the_caller():
    standard = get_skill_dir('pm-dev-java', 'javadoc') / 'standards' / 'javadoc-method-documentation.md'
    text = standard.read_text(encoding='utf-8')

    assert 'the caller' in text, 'the method-documentation standard must name the caller check'
    assert 'ordering claim' in text, 'the standard must name the claim it sends the author to check'
    assert 'Check the call site' in text, 'the verification half must tell the author where to look'


# ---------------------------------------------------------------------------
# D2 — JUnit review rules: tests that cannot fail, and spec citations
# ---------------------------------------------------------------------------

#: One needle tuple per new rule. Each tuple must select exactly one rule, so a
#: rule that silently drops out of the block is a failure here rather than a
#: smaller count nobody reads.
_D2_RULE_NEEDLES = (
    ('anchor', 'concrete'),
    ('builder default', 'explicitly'),
    ('vacuous',),
    ('cardinality',),
    ('clause',),
    ('fail-open',),
)


def test_junit_review_rules_cover_the_six_cannot_fail_and_citation_shapes():
    rules = _review_rules(get_skill_dir('pm-dev-java', 'junit-core'))

    assert len(rules) == 10, f'the junit-core block holds four rules plus the six this plan adds: {rules}'
    for needles in _D2_RULE_NEEDLES:
        _assert_harvestable(_rule_containing(rules, *needles))


def test_junit_testing_standard_explains_each_shape_with_a_before_and_after():
    standard = get_skill_dir('pm-dev-java', 'junit-core') / 'standards' / 'testing-junit-core.md'
    section = _section(standard.read_text(encoding='utf-8'), '## Tests That Cannot Fail')

    shapes = [block for block in re.split(r'^### ', section, flags=re.MULTILINE)[1:] if block.strip()]
    assert len(shapes) == 6, f'the standard must give one subsection per shape: {len(shapes)} found'
    for shape in shapes:
        heading = shape.splitlines()[0]
        assert 'Before' in shape, f'{heading} carries no before example'
        assert 'After' in shape, f'{heading} carries no after example'

    assert 'persona-module-tester' in section, 'the section must point at the language-agnostic form'
    assert 'positive control' in section.lower(), 'the pointer must name the matched positive control'
    assert 'non-vacuity' in section.lower(), 'the pointer must name the non-vacuity guidance'


def test_cui_skills_point_at_the_cannot_fail_rules_without_restating_them():
    for skill in ('cui-testing', 'cui-http-testing'):
        text = (get_skill_dir('pm-dev-java-cui', skill) / 'SKILL.md').read_text(encoding='utf-8')
        assert 'Tests That Cannot Fail' in text, f'{skill} must point at the junit-core section'
        assert 'pm-dev-java:junit-core' in text, f'{skill} must name the skill that owns the rule'

