# SPDX-License-Identifier: FSL-1.1-ALv2
"""Guards over the code-review artifact set the cuioss-review-bot target emits.

The code-review set is a second derivation beside the security set: its domains
are the domain keys the bundles declare through ``get_skill_domains()``, its rules
are the ``## Review Rules`` bullets of the declaring bundle's default skills, and
its spine carries ``ref-code-quality``'s review blocks plus the charter.

Two halves:

* **The real marketplace** — no security rule and no security category reaches a
  code-review artifact, every derived domain has a rule-bearing pack, and a run
  emits both sets.
* **Fixture marketplaces** — the selection rules (declaring bundle only, defaults
  only, security skills excluded by construction, the spine bundle feeds the
  spine), the fail-closed reading of declarations and rule sources, and the
  emission contract (both sets, the security set unchanged, the prune).
"""

import re
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT
from marketplace.targets.cuioss_review_bot.target import (
    CuiossReviewBotTarget,
    discover_code_review_domains,
    discover_code_review_spine,
)

MARKETPLACE_BUNDLES = PROJECT_ROOT / 'marketplace' / 'bundles'

CODE_REVIEW_PREFIX = 'code-review-'
CODE_REVIEW_SPINE_STEM = 'code-review-spine'
SPINE_STEM = 'spine'
RULES_HEADING_PREFIXES = ('Domain rules', 'Cross-cutting review rules')
SECURITY_SKILL_EXCLUDED = 'persona-security-expert'

#: The security review categories, as words. None may appear in a code-review
#: artifact: those categories belong to the security set alone.
SECURITY_CATEGORY_PATTERN = re.compile(
    r'\b(injection|deserializ\w*|path traversal|ssrf|authenticat\w*|authoriz\w*|privilege escalation|'
    r'secrets?|credentials?|supply[- ]chain)\b',
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Real-marketplace population — derived at collection time
# ---------------------------------------------------------------------------

REAL_DOMAINS = discover_code_review_domains(MARKETPLACE_BUNDLES)
REAL_DOMAIN_IDS = sorted(REAL_DOMAINS)

# ⛔ Binding-site vacuity guard: the parametrizations below collect zero cases
# over an empty population and would still report green.
assert REAL_DOMAIN_IDS, 'no code-review domain derives from the real marketplace'


def _security_skill_bullets(bundles: Path) -> set[str]:
    """Every bullet of every security skill — the text no code-review pack may carry."""
    bullets: set[str] = set()
    for skill_md in sorted(bundles.glob('*/skills/*/SKILL.md')):
        skill = skill_md.parent.name
        if not (skill.endswith('-security') or skill == SECURITY_SKILL_EXCLUDED):
            continue
        for line in skill_md.read_text(encoding='utf-8').splitlines():
            if line.startswith('- ') and len(line) > 30:
                bullets.add(line[2:].strip())
    return bullets


def _pack_bullets(artifact: str) -> list[str]:
    return [line[2:] for line in artifact.splitlines() if line.startswith('- ')]


def _category_bullets(artifact: str) -> list[str]:
    """The bullets above the rules block — a local splitter, not the composer's."""
    bullets: list[str] = []
    for line in artifact.splitlines():
        if line.startswith(RULES_HEADING_PREFIXES):
            break
        if line.startswith('- '):
            bullets.append(line[2:])
    return bullets


def _leaked_security_bullets(artifacts: dict[str, str], security_bullets: set[str]) -> list[str]:
    return sorted(
        f'{stem}: {bullet}'
        for stem, body in artifacts.items()
        for bullet in _pack_bullets(body)
        if bullet in security_bullets
    )


def _security_terms(artifacts: dict[str, str]) -> list[str]:
    return sorted(
        f'{stem}: {match.group(0)}'
        for stem, body in artifacts.items()
        for match in SECURITY_CATEGORY_PATTERN.finditer(body)
    )


@pytest.fixture(scope='module')
def real_artifacts(tmp_path_factory) -> dict[str, str]:
    out = tmp_path_factory.mktemp('code-review-packs')
    CuiossReviewBotTarget().generate(MARKETPLACE_BUNDLES, out)
    return {path.stem: path.read_text(encoding='utf-8') for path in sorted((out / 'packs').glob('*.md'))}


@pytest.fixture(scope='module')
def code_review_artifacts(real_artifacts) -> dict[str, str]:
    return {stem: body for stem, body in real_artifacts.items() if stem.startswith(CODE_REVIEW_PREFIX)}


class TestRealMarketplace:
    """The published code-review set carries no security text and covers every domain."""

    def test_both_sets_are_emitted(self, real_artifacts):
        assert SPINE_STEM in real_artifacts
        assert CODE_REVIEW_SPINE_STEM in real_artifacts
        assert {f'{CODE_REVIEW_PREFIX}{domain}' for domain in REAL_DOMAIN_IDS} <= set(real_artifacts)

    @pytest.mark.parametrize('domain', REAL_DOMAIN_IDS)
    def test_every_derived_domain_has_a_rule_bearing_pack(self, domain, code_review_artifacts):
        artifact = code_review_artifacts[f'{CODE_REVIEW_PREFIX}{domain}']

        assert REAL_DOMAINS[domain].rules, f'{domain} derives no review rule'
        assert REAL_DOMAINS[domain].rules[0] in artifact
        assert len(_category_bullets(artifact)) == 1

    def test_no_security_skill_is_a_rule_source(self):
        sources = [skill for domain in REAL_DOMAINS.values() for skill in domain.skills]

        assert sources, 'control: the derivation must name rule sources'
        offenders = [s for s in sources if s.endswith('-security') or s.endswith(f':{SECURITY_SKILL_EXCLUDED}')]
        assert not offenders

    def test_the_spine_bundle_contributes_no_pack(self):
        assert 'general-dev' not in REAL_DOMAINS

    def test_no_security_rule_reaches_a_code_review_artifact(self, code_review_artifacts):
        security_bullets = _security_skill_bullets(MARKETPLACE_BUNDLES)

        assert security_bullets, 'control: the security skills must yield bullets to compare against'
        assert _leaked_security_bullets(code_review_artifacts, security_bullets) == []

    def test_no_security_category_reaches_a_code_review_artifact(self, code_review_artifacts):
        assert _security_terms(code_review_artifacts) == []

    def test_the_leak_guards_bite(self, code_review_artifacts):
        """Both leak predicates fire on a code-review artifact carrying security text."""
        security_bullet = sorted(_security_skill_bullets(MARKETPLACE_BUNDLES))[0]
        with_rule = {'code-review-x': f'- {security_bullet}\n'}
        with_category = {'code-review-x': '- Injection and secret handling.\n'}

        assert _leaked_security_bullets(with_rule, {security_bullet}) == [f'code-review-x: {security_bullet}']
        assert _security_terms(with_category) == ['code-review-x: Injection', 'code-review-x: secret']

    def test_the_code_review_spine_holds_the_category_budget(self, code_review_artifacts):
        bullets = _category_bullets(code_review_artifacts[CODE_REVIEW_SPINE_STEM])

        assert bullets, 'the code-review spine carries no category'
        assert len(bullets) <= 9


# ---------------------------------------------------------------------------
# Fixture marketplaces
# ---------------------------------------------------------------------------

EXTENSION_TEMPLATE = """from extension_base import ExtensionBase


class Extension(ExtensionBase):
{methods}
"""

GO_CORE_RULES = (
    'A goroutine started without a cancellation path, so it outlives the request.',
    'A deferred close inside a loop, so handles pile up until the function returns.',
)
GO_TEST_RULE = 'A table test whose cases share one mutable fixture, so case order changes the verdict.'


def _write_skill(
    bundles: Path, bundle: str, skill: str, rules: tuple[str, ...], heading: str = '## Review Rules'
) -> None:
    skill_dir = bundles / bundle / 'skills' / skill
    skill_dir.mkdir(parents=True, exist_ok=True)
    lines = ['---', f'name: {skill}', '---', '', f'# {skill}', '', heading, '', 'Intro prose, not a rule.', '']
    lines.extend(f'- {rule}' for rule in rules)
    lines.extend(['', '## Later', '', '- not a review rule', ''])
    (skill_dir / 'SKILL.md').write_text('\n'.join(lines), encoding='utf-8')


def _domain(key: str, **defaults: list) -> dict:
    return {
        'domain': {'key': key, 'name': key, 'description': key},
        'profiles': {profile: {'defaults': list(skills), 'optionals': []} for profile, skills in defaults.items()},
    }


def _write_extension(bundles: Path, bundle: str, methods: str) -> Path:
    path = bundles / bundle / 'skills' / 'plan-marshall-plugin' / 'extension.py'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(EXTENSION_TEMPLATE.format(methods=methods), encoding='utf-8')
    return path


def _declare(bundles: Path, bundle: str, declarations: list) -> Path:
    return _write_extension(bundles, bundle, f'    def get_skill_domains(self):\n        return {declarations!r}\n')


@pytest.fixture
def bundles(tmp_path: Path) -> Path:
    """A marketplace with one code-review domain ``go``, a shared skill and the spine."""
    root = tmp_path / 'bundles'
    _write_skill(root, 'pm-fx-go', 'go-core', GO_CORE_RULES)
    _write_skill(root, 'pm-fx-go', 'go-testing', (GO_TEST_RULE,))
    _write_skill(root, 'pm-fx-go', 'go-style', ('An optional skill rule.',))
    _write_skill(root, 'pm-fx-go', 'go-security', ('A security skill rule.',))
    _write_skill(root, 'pm-fx-go', SECURITY_SKILL_EXCLUDED, ('A security persona rule.',))
    _write_skill(root, 'pm-fx-shared', 'shared-rules', ('A rule of a skill another bundle owns.',))
    declaration = _domain(
        'go',
        core=['pm-fx-go:go-core', {'skill': 'pm-fx-shared:shared-rules'}, f'pm-fx-go:{SECURITY_SKILL_EXCLUDED}'],
        module_testing=[{'skill': 'pm-fx-go:go-testing', 'description': 'tests'}],
        quality=['pm-fx-go:go-security'],
        security=['pm-fx-go:go-security'],
    )
    declaration['profiles']['implementation'] = {'defaults': [], 'optionals': ['pm-fx-go:go-style']}
    _declare(root, 'pm-fx-go', [declaration])
    _write_skill(
        root, 'plan-marshall', 'ref-code-quality', ('**Correctness** — a wrong result.',), '## Review Categories'
    )
    _declare(root, 'plan-marshall', [_domain('general-dev', implementation=['plan-marshall:ref-code-quality'])])
    return root


class TestSelection:
    """Which skills feed a domain's rules."""

    def test_rules_come_from_the_declaring_bundles_default_skills_in_profile_order(self, bundles):
        domain = discover_code_review_domains(bundles)['go']

        assert domain.rules == (*GO_CORE_RULES, GO_TEST_RULE)
        assert domain.skills == ('pm-fx-go:go-core', 'pm-fx-go:go-testing')
        assert domain.bundles == ('pm-fx-go',)

    def test_the_spine_bundle_domain_feeds_no_pack(self, bundles):
        assert sorted(discover_code_review_domains(bundles)) == ['go']

    def test_a_helper_method_declaration_is_read(self, bundles):
        _write_extension(
            bundles,
            'pm-fx-go',
            '    def get_skill_domains(self):\n        return [self._go()]\n\n'
            f'    def _go(self):\n        return {_domain("go", core=["pm-fx-go:go-core"])!r}\n',
        )

        assert discover_code_review_domains(bundles)['go'].rules == GO_CORE_RULES

    def test_a_non_literal_declaration_is_refused(self, bundles):
        _write_extension(bundles, 'pm-fx-go', '    def get_skill_domains(self):\n        return [build_domains()]\n')

        with pytest.raises(ValueError, match='cannot read statically'):
            discover_code_review_domains(bundles)

    def test_an_unreadable_rule_source_is_refused(self, bundles):
        _declare(bundles, 'pm-fx-go', [_domain('go', core=['pm-fx-go:go-missing'])])

        with pytest.raises(ValueError, match='cannot read the review-rule source'):
            discover_code_review_domains(bundles)

    def test_the_rule_budget_and_the_withholding_filter_apply(self, bundles):
        rules = (
            'Do not duplicate what the linter reports.',
            *(f'Rule number {n} names a mechanism.' for n in range(15)),
        )
        _write_skill(bundles, 'pm-fx-go', 'go-core', rules)

        harvested = discover_code_review_domains(bundles)['go'].rules

        assert len(harvested) == 12
        assert harvested[0] == 'Rule number 0 names a mechanism.'

    def test_a_wrapped_bullet_is_one_rule(self, bundles):
        skill_md = bundles / 'pm-fx-go' / 'skills' / 'go-testing' / 'SKILL.md'
        skill_md.write_text(
            skill_md.read_text(encoding='utf-8').replace(GO_TEST_RULE, 'A wrapped\n  rule.'), encoding='utf-8'
        )

        assert discover_code_review_domains(bundles)['go'].rules[-1] == 'A wrapped rule.'


class TestSpine:
    """The code-review spine's sources and budget."""

    def test_the_spine_reads_the_review_blocks_of_ref_code_quality(self, bundles):
        categories, rules = discover_code_review_spine(bundles)

        assert categories == ('**Correctness** — a wrong result.',)
        assert rules == ()

    def test_a_category_over_the_budget_is_refused(self, bundles):
        _write_skill(
            bundles,
            'plan-marshall',
            'ref-code-quality',
            tuple(f'Category {n}.' for n in range(10)),
            '## Review Categories',
        )

        with pytest.raises(ValueError, match='at most 9'):
            discover_code_review_spine(bundles)


class TestEmission:
    """Both sets are emitted, the security set is unchanged, the prune covers both."""

    def _stems(self, out: Path) -> list[str]:
        return sorted(path.stem for path in (out / 'packs').glob('*.md'))

    def test_both_sets_are_emitted_and_the_security_set_is_unchanged(self, bundles, tmp_path):
        out = tmp_path / 'out'
        extension = bundles / 'pm-fx-go' / 'skills' / 'plan-marshall-plugin' / 'extension.py'
        declared = extension.read_text(encoding='utf-8')
        extension.unlink()
        CuiossReviewBotTarget().generate(bundles, out)
        security_before = {stem: (out / 'packs' / f'{stem}.md').read_bytes() for stem in ('go', SPINE_STEM)}

        extension.write_text(declared, encoding='utf-8')
        CuiossReviewBotTarget().generate(bundles, out)

        assert self._stems(out) == ['code-review-go', CODE_REVIEW_SPINE_STEM, 'go', SPINE_STEM]
        assert {stem: (out / 'packs' / f'{stem}.md').read_bytes() for stem in ('go', SPINE_STEM)} == security_before

    def test_a_domain_that_stops_deriving_is_pruned(self, bundles, tmp_path):
        out = tmp_path / 'out'
        CuiossReviewBotTarget().generate(bundles, out)

        _declare(bundles, 'pm-fx-go', [])
        CuiossReviewBotTarget().generate(bundles, out)

        assert self._stems(out) == [CODE_REVIEW_SPINE_STEM, 'go', SPINE_STEM]

    def test_a_domain_key_named_like_the_spine_is_refused(self, bundles, tmp_path):
        out = tmp_path / 'out'
        _declare(bundles, 'pm-fx-go', [_domain('spine', core=['pm-fx-go:go-core'])])

        with pytest.raises(ValueError, match='collides with the code-review spine'):
            CuiossReviewBotTarget().generate(bundles, out)

        assert not out.exists(), 'a refused run must leave no half-written artifact set'
