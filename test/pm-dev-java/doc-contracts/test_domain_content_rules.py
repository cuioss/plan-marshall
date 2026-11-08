# SPDX-License-Identifier: FSL-1.1-ALv2
"""Doc-contract tests for the domain content rules this plan lands.

Each test pins one rule the guidance must carry, against the real bundle
document that owns it. They read the shipped Markdown, never a copy, so a rule
that is deleted — or reworded away from every token the test names — reds here.
A reword that keeps those tokens is not caught; the tokens are the contract this
file pins, not a substitute for review.

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

#: Withholding language never belongs in a harvestable review rule. These phrases
#: instruct a reviewer to suppress a finding it could otherwise substantiate; the
#: list is the quality bar § 10 of ``review-rubric.md`` states, kept here because a
#: rule that carries one reads as a suppression instruction to the in-run reviewer
#: exactly as it did to the retired pack generator that first measured them.
_WITHHOLDING_MARKERS: tuple[str, ...] = (
    'do not duplicate',
    'avoid duplicating',
    'prefer one well-evidenced',
    'only when you can name the concrete input',
)


def _section(body: str, heading: str) -> str:
    """The text of one Markdown section, up to the next same-or-higher heading."""
    level = len(heading) - len(heading.lstrip('#'))
    start = body.index(heading + '\n')
    rest = body[start + len(heading) + 1 :]
    stop = re.search(rf'^#{{1,{level}}} ', rest, re.MULTILINE)
    return rest[: stop.start()] if stop else rest


def _bullets(section: str) -> list[str]:
    """The bullets of a section, with wrapped continuation lines joined.

    Fenced code is skipped, matching the pack generator, so a rule that appears
    only inside an example is not counted as a published rule.
    """
    bullets: list[str] = []
    in_fence = False
    for line in section.splitlines():
        if line.strip().startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith('- '):
            bullets.append(line[2:].strip())
        elif bullets and line.strip() and line[:1].isspace():
            bullets[-1] = f'{bullets[-1]} {line.strip()}'
    return [bullet for bullet in bullets if bullet]


def _review_rules(skill_dir: Path) -> list[str]:
    """The bullets of a skill's ``## Review Rules`` block."""
    return _bullets(_section((skill_dir / 'SKILL.md').read_text(encoding='utf-8'), '## Review Rules'))


def _assert_harvestable(rule: str) -> None:
    """The mechanical half of the harvestable-block contract.

    Section 10's remaining clauses — one rule per bullet, mechanism-naming wording,
    addressed to a reviewer — are semantic: the parser already yields one bullet
    per rule, and the per-rule needles in the tests below pin the mechanism each
    rule names. What a test can enforce mechanically is that the bullet carries
    text and none of the withholding phrases.
    """
    assert rule.strip(), 'a harvested rule must carry text'
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


# ---------------------------------------------------------------------------
# D3 — invisible and bidirectional characters are built from code points
# ---------------------------------------------------------------------------

#: The rule's load-bearing tokens. A document that names the escape but drops
#: the reviewability reason, or names the reason but shows no code point, is a
#: partial statement of the rule this test pins.
_D3_TOKENS = ('code point', 'invisible', 'bidirectional', 'S6389')


def _assert_code_point_rule(text: str, where: str) -> None:
    detached = [token for token in _D3_TOKENS if token.lower() not in text.lower()]
    assert not detached, f'{where} does not state the rule: missing {detached}'
    assert '\\u' in text or 'Character.toChars' in text, f'{where} carries no code-point example'


def test_cui_http_testing_skill_states_the_code_point_rule_in_step_3():
    text = (get_skill_dir('pm-dev-java-cui', 'cui-http-testing') / 'SKILL.md').read_text(encoding='utf-8')
    _assert_code_point_rule(
        _section(text, '### Step 3: Drive Adversarial / Negative-Path Tests (For Security-Relevant HTTP Code)'),
        'SKILL.md Step 3',
    )


def test_cui_http_testing_standard_states_the_code_point_rule_in_the_attack_database_section():
    text = (get_skill_dir('pm-dev-java-cui', 'cui-http-testing') / 'standards' / 'testing-mockwebserver.md').read_text(
        encoding='utf-8'
    )
    _assert_code_point_rule(
        _section(text, '## Adversarial / Negative-Path Testing'), 'testing-mockwebserver.md attack section'
    )


# ---------------------------------------------------------------------------
# D4 — the switch guidance says when exhaustiveness is checked
# ---------------------------------------------------------------------------


def test_java_17_switch_section_names_when_the_compiler_checks_exhaustiveness():
    text = (get_skill_dir('pm-dev-java', 'java-core') / 'standards' / 'java-17-features.md').read_text(encoding='utf-8')
    section = _section(text, '### From an if/else chain over a closed constant set')

    assert 'not exhaustiveness-checked' in section, 'the section must say the statement form is unchecked'
    assert 'switch statement therefore keeps its' in section, (
        'the section must say a constant-only switch statement keeps its default-throw'
    )


def test_java_core_review_rules_cover_a_default_removed_from_a_switch_statement():
    rules = _review_rules(get_skill_dir('pm-dev-java', 'java-core'))

    assert len(rules) == 6, f'the java-core block holds five rules plus the one this plan adds: {rules}'
    rule = _rule_containing(rules, 'switch statement', 'falls through')
    _assert_harvestable(rule)


# ---------------------------------------------------------------------------
# D5 — masking is not sanitising, and \p{Cntrl} is ASCII-only
# ---------------------------------------------------------------------------


def test_java_security_masking_pattern_says_masking_is_not_sanitising():
    text = (get_skill_dir('pm-dev-java', 'java-security') / 'standards' / 'java-security-patterns.md').read_text(
        encoding='utf-8'
    )
    masking = _section(text, '### Masking Pattern')

    assert 'mask' in masking.lower(), 'control: the section must still show the masking example'
    assert 'not sanitising' in masking.lower() or 'does not neutralise' in masking.lower(), (
        'masking must be stated as redaction, not neutralisation'
    )
    assert 'CR' in masking and 'LF' in masking, 'the statement must name the characters masking leaves in place'
    assert 'forge' in masking.lower(), 'the statement must name the consequence: a forged log line'


def test_secure_logging_names_the_c1_range_and_the_ascii_only_cntrl_class():
    standard = get_skill_dir('plan-marshall', 'persona-security-expert') / 'standards' / 'secure-logging.md'
    text = _section(standard.read_text(encoding='utf-8'), '## Log Injection (CWE-117): Attack and Prevention')

    assert 'U+0080' in text and 'U+009F' in text, 'the C1 range must be named explicitly'
    assert '\\p{Cntrl}' in text, 'the regex class must be named'
    assert 'ASCII' in text, 'the class must be described as ASCII-only'
    assert 'Character.isISOControl' in text, 'the check that covers the full set must be named'


def test_java_security_skill_points_at_the_code_home_and_the_persona_standard():
    """The skill keeps no second copy of the Java form; it points at both owning homes."""
    text = (get_skill_dir('pm-dev-java', 'java-security') / 'SKILL.md').read_text(encoding='utf-8')
    section = _section(text, '## Java Form — Neutralise Before Logging')

    assert 'java-security-patterns.md' in section, 'the section must point at the Java code home'
    assert 'secure-logging.md' in section, 'the section must point at the persona standard that owns the rule'
    assert 'private String neutralise' not in section, 'the section still repeats the Java implementation'
    assert 'Character.isISOControl' not in section, 'the section still repeats the paragraph the standard owns'


def test_cui_logging_points_at_the_value_neutralisation_rule():
    """The CUI section points at the owner and does not restate its check set."""
    text = (get_skill_dir('pm-dev-java-cui', 'cui-logging') / 'standards' / 'logging-standards.md').read_text(
        encoding='utf-8'
    )

    assert 'secure-logging.md' in text, 'the pointer must name the standard that owns the rule'
    for restated in ('Character.isISOControl', 'U+2028', 'U+2029'):
        assert restated not in text, (
            f'the pointer restates the check set the owner holds with {restated!r} — state once, point elsewhere'
        )


# ---------------------------------------------------------------------------
# D6 — the secure-logging text states one rule in one home, and its Java
# example follows the rule that owns it
# ---------------------------------------------------------------------------


def test_java_security_neutralise_escapes_a_control_character_instead_of_dropping_it():
    """The owning rule prefers escaping over dropping, so the example must not replace with `?`."""
    text = (get_skill_dir('pm-dev-java', 'java-security') / 'standards' / 'java-security-patterns.md').read_text(
        encoding='utf-8'
    )
    masking = _section(text, '### Masking Pattern')

    assert '\\\\u%04X' in masking, 'the neutralise example must escape the control character as a \\uXXXX escape'
    assert "? '?' : c" not in masking, 'the example still replaces the character with `?`, which drops it'
    assert 'reversible' in masking.lower(), (
        'the encoding must be reversible, so a literal `\\u000A` stays distinguishable from a newline'
    )
    assert 'escape introducer' in masking.lower(), 'the example must say the escape introducer itself is escaped'


def test_secure_logging_narrows_the_json_claim_to_the_string_grammar():
    """The owner states what JSON escapes and what it leaves for defence-in-depth.

    The former claim — JSON "automatically escape[s] CRLF and special characters,
    so forged entries cannot be injected" — was false: the string grammar covers
    the quote, the backslash and the C0 range only, so DEL, the C1 range and
    U+2028/U+2029 still have to be neutralised.
    """
    standard = get_skill_dir('plan-marshall', 'persona-security-expert') / 'standards' / 'secure-logging.md'
    section = _section(standard.read_text(encoding='utf-8'), '## Log Injection (CWE-117): Attack and Prevention')

    assert 'automatically escape' not in section, 'the owner still claims JSON escapes CRLF and all special characters'
    assert re.search(r'(?i)JSON string grammar', section), 'the owner must scope the claim to the JSON string grammar'
    assert 'quote' in section.lower() and 'backslash' in section.lower(), 'the owner must name what JSON escapes'
    assert 'U+0000' in section and 'U+001F' in section, 'the owner must name the escaped C0 range'
    assert 'DEL' in section and 'C1' in section, 'the owner must name the characters JSON leaves over'
    assert 'U+2028' in section and 'U+2029' in section, 'the owner must name the line separators it leaves over'
    assert re.search(r'(?i)still neutralised before the value is logged', section), (
        'the owner must say the residual set is neutralised before the value is logged'
    )


def test_java_security_points_at_the_owner_for_the_json_claim():
    """The leaf keeps the Java mechanics and points at the owner instead of restating the rule."""
    text = (get_skill_dir('pm-dev-java', 'java-security') / 'standards' / 'java-security-patterns.md').read_text(
        encoding='utf-8'
    )
    masking = _section(text, '### Masking Pattern')

    assert 'secure-logging.md' in masking, 'the Java leaf must point at the standard that owns the JSON claim'
    assert 'does not restate' in masking.lower(), 'the Java leaf must say it points rather than restates'
    for restated in ('U+0000', 'U+001F', 'quote', 'backslash'):
        assert restated not in masking, (
            f'the Java leaf still restates the owner rule with {restated!r} — state once, point elsewhere'
        )


def test_secure_logging_owns_u2028_u2029_and_scopes_the_cntrl_note():
    standard = get_skill_dir('plan-marshall', 'persona-security-expert') / 'standards' / 'secure-logging.md'
    section = _section(standard.read_text(encoding='utf-8'), '## Log Injection (CWE-117): Attack and Prevention')

    assert 'U+2028' in section and 'U+2029' in section, 'the owned set must name the two line separators'
    assert re.search(r'(?i)explicit U\+2028/U\+2029 test', section), (
        'the check that covers the set must name the explicit line-separator test, because '
        'Character.isISOControl does not match U+2028/U+2029'
    )
    assert re.search(r'(?i)default pattern flags', section), (
        'the ASCII-only note must be scoped to the default pattern flags'
    )
    assert 'UNICODE_CHARACTER_CLASS' in section, 'the note must name the flag that widens the character class'


def test_cui_logging_names_one_owner_for_the_value_neutralisation_principle():
    text = (get_skill_dir('pm-dev-java-cui', 'cui-logging') / 'standards' / 'logging-standards.md').read_text(
        encoding='utf-8'
    )
    section = _section(text, "### 4. Don't Log Sensitive Information")

    assert 'persona-security-expert' in section, 'the section must name the owner of the principle'
    assert 'pm-dev-java:java-security' not in section, (
        'the section names a second owner for the same principle — the paragraphs must agree on one home'
    )


def test_javadoc_ordering_rule_covers_the_method_body_as_well_as_the_caller():
    rules = _review_rules(get_skill_dir('pm-dev-java', 'javadoc'))
    rule = _rule_containing(rules, 'ordering', 'method')

    assert 'body' in rule.lower(), 'the rule must cover an ordering the method states about its own body'
    assert 'call' in rule.lower(), 'the rule must keep the caller-side ordering it already covered'


def test_java_17_switch_guidance_names_the_release_and_qualifies_the_enum_claim():
    text = (get_skill_dir('pm-dev-java', 'java-core') / 'standards' / 'java-17-features.md').read_text(encoding='utf-8')
    section = _section(text, '### From an if/else chain over a closed constant set')

    assert 'Java 21' in section, 'the enhanced-switch caveat must name the release it applies from'
    assert 'release that introduced pattern switches' in section, (
        'the caveat must name why that release is the boundary'
    )
    assert 'As a switch expression' in section, (
        'the "needs no `default`" claim must be qualified as the switch expression form, not the enum form'
    )
