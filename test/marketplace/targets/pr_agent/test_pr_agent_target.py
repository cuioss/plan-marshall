# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the pr-agent instruction-pack export target.

The subject is the target's DERIVATION and EMISSION contract: the domain set is
scanned out of the source marketplace rather than hand-transcribed, a run emits
exactly one pack, and the target declares itself not-a-bundle-tree so the CLI's
generic post-emit steps stay off its output.

Every test builds its own fixture marketplace, so the assertions do not depend on
which bundles the real marketplace happens to ship today.
"""

import tomllib
from pathlib import Path

import pytest

from marketplace.targets import TARGET_REGISTRY
from marketplace.targets.claude.target import ClaudeTarget
from marketplace.targets.pr_agent.target import (
    ANTI_FABRICATION_CLAUSE,
    CONFIG_FILENAME,
    MAX_CATEGORY_BULLETS,
    SUBSTANTIATION_CLAUSE,
    PrAgentTarget,
    compose_packs,
    discover_domains,
    discover_spine_topics,
)

# The pack text is measured against literals declared HERE, never against a value
# read back from the composer that produced it: a comparison whose two sides share
# a pivot moves together and stays green over a pack that has drifted.
EXPECTED_CATEGORY_CEILING = 10
WITHHOLDING_DENY_LIST = (
    'do not duplicate',
    'prefer one well-evidenced',
    'only when you can name the concrete input',
    'avoid duplicating',
)


def _write_skill(
    bundles_dir: Path,
    bundle: str,
    skill: str,
    *,
    prohibited: tuple[str, ...] = (),
    constraints: tuple[str, ...] = (),
) -> Path:
    """Write a minimal SKILL.md carrying an ``## Enforcement`` block."""
    skill_dir = bundles_dir / bundle / 'skills' / skill
    skill_dir.mkdir(parents=True, exist_ok=True)
    lines = ['---', f'name: {skill}', 'mode: knowledge', '---', '', f'# {skill}', '', '## Enforcement', '']
    if prohibited:
        lines.append('**Prohibited actions:**')
        lines.extend(f'- {rule}' for rule in prohibited)
        lines.append('')
    if constraints:
        lines.append('**Constraints:**')
        lines.extend(f'- {rule}' for rule in constraints)
        lines.append('')
    lines.extend(['## Something Else', '', '- not an enforcement rule', ''])
    (skill_dir / 'SKILL.md').write_text('\n'.join(lines), encoding='utf-8')
    return skill_dir


def _fixture_marketplace(tmp_path: Path) -> Path:
    """A marketplace holding exactly one derivable domain plus the spine."""
    bundles = tmp_path / 'bundles'
    _write_skill(
        bundles,
        'pm-fixture-java',
        'java-security',
        prohibited=('Do not log credentials',),
        constraints=('Inbound payloads are validated at the trust boundary',),
    )
    _write_skill(bundles, 'pm-fixture-java', 'arch-gate-java', prohibited=('Do not mutate source from the gate',))
    _write_skill(bundles, 'pm-fixture-java', 'ext-triage-java', prohibited=('Do not auto-suppress a finding',))

    spine_standards = bundles / 'plan-marshall' / 'skills' / 'persona-security-expert' / 'standards'
    spine_standards.mkdir(parents=True)
    (spine_standards / 'owasp-top-ten.md').write_text('# owasp\n', encoding='utf-8')
    (spine_standards / 'secrets-handling.md').write_text('# secrets\n', encoding='utf-8')
    return bundles


def _category_bullets(pack: str) -> list[str]:
    """The category bullet list — the bullets above the domain-rules block."""
    bullets: list[str] = []
    for line in pack.splitlines():
        if line.startswith('Domain rules'):
            break
        if line.startswith('- '):
            bullets.append(line[2:])
    return bullets


class TestRegistration:
    """The target registers itself and declares its capability flags."""

    def test_registered_under_pr_agent(self):
        assert TARGET_REGISTRY['pr-agent'] is PrAgentTarget

    def test_name_is_pr_agent(self):
        assert PrAgentTarget().name == 'pr-agent'

    def test_emits_no_agents_or_commands(self):
        target = PrAgentTarget()
        assert target.supports_agents() is False
        assert target.supports_commands() is False

    def test_config_dir_is_the_package_directory(self):
        assert PrAgentTarget().config_dir.name == 'pr_agent'

    def test_is_not_a_bundle_tree(self):
        assert PrAgentTarget().emits_bundle_tree is False

    def test_bundle_tree_target_keeps_the_default(self):
        # Positive control for the gate: the property defaults to True, so only a
        # target that opts out is skipped by the CLI's post-emit steps.
        assert ClaudeTarget().emits_bundle_tree is True


class TestDomainDerivation:
    """The domain set is scanned out of the marketplace, never hand-transcribed."""

    def test_derives_domain_from_the_security_skill(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)

        domains = discover_domains(bundles)

        assert sorted(domains) == ['java']
        assert domains['java'].bundles == ('pm-fixture-java',)
        assert domains['java'].kinds == ('security', 'arch-gate', 'ext-triage')

    def test_added_bundle_appears_in_the_derived_set_with_no_code_change(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)
        before = sorted(discover_domains(bundles))

        _write_skill(bundles, 'pm-fixture-ruby', 'ruby-security', prohibited=('Do not eval untrusted input',))
        after = sorted(discover_domains(bundles))

        assert before == ['java']
        assert after == ['java', 'ruby'], 'the derived set must widen from the fixture alone'

    def test_domain_derivable_from_a_triage_skill_alone(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)

        _write_skill(bundles, 'pm-fixture-docs', 'ext-triage-docs')
        domains = discover_domains(bundles)

        assert 'docs' in domains
        assert domains['docs'].kinds == ('ext-triage',)
        assert domains['docs'].rules == ()

    def test_spine_bundle_is_not_a_domain(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)

        assert 'persona' not in discover_domains(bundles)
        assert 'plan-marshall' not in discover_domains(bundles)

    def test_spine_topics_derive_from_the_spine_standards(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)

        assert discover_spine_topics(bundles) == ('owasp top ten', 'secrets handling')

    def test_spine_topics_empty_when_the_spine_is_absent(self, tmp_path):
        bundles = tmp_path / 'bundles'
        _write_skill(bundles, 'pm-fixture-java', 'java-security')

        assert discover_spine_topics(bundles) == ()

    def test_rules_come_from_the_security_skill_only(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)

        rules = discover_domains(bundles)['java'].rules

        assert 'Do not log credentials' in rules
        assert 'Inbound payloads are validated at the trust boundary' in rules
        # arch-gate / ext-triage enforcement blocks govern how those skills are
        # OPERATED, not what the domain's code may do — they are not domain rules.
        assert 'Do not mutate source from the gate' not in rules
        assert 'Do not auto-suppress a finding' not in rules

    def test_non_enforcement_bullets_are_not_harvested(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)

        assert 'not an enforcement rule' not in discover_domains(bundles)['java'].rules

    def test_withholding_language_is_dropped_from_harvested_rules(self, tmp_path):
        bundles = tmp_path / 'bundles'
        _write_skill(
            bundles,
            'pm-fixture-java',
            'java-security',
            prohibited=('Do not duplicate the central model here', 'Do not log credentials'),
        )

        rules = discover_domains(bundles)['java'].rules

        assert rules == ('Do not log credentials',)


class TestPackComposition:
    """Every derived pack carries the charter's bars and respects the ceiling."""

    def test_one_pack_per_derived_domain(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)
        _write_skill(bundles, 'pm-fixture-ruby', 'ruby-security', prohibited=('Do not eval untrusted input',))

        packs = compose_packs(bundles)

        assert sorted(packs) == ['java', 'ruby']

    def test_clauses_are_carried_verbatim_into_every_pack(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)
        _write_skill(bundles, 'pm-fixture-docs', 'ext-triage-docs')

        packs = compose_packs(bundles)

        assert packs, 'the derived pack population must not be empty'
        for domain, pack in packs.items():
            assert SUBSTANTIATION_CLAUSE in pack, domain
            assert ANTI_FABRICATION_CLAUSE in pack, domain
            assert 'name the input or state that triggers it' in pack, domain

    def test_category_list_respects_the_ceiling(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)

        pack = compose_packs(bundles)['java']

        # Measured against a literal declared in this module, not against the
        # composer's own constant.
        assert len(_category_bullets(pack)) <= EXPECTED_CATEGORY_CEILING
        assert MAX_CATEGORY_BULLETS == EXPECTED_CATEGORY_CEILING

    def test_domain_bullet_survives_the_ceiling(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)

        bullets = _category_bullets(compose_packs(bundles)['java'])

        assert any(bullet.startswith('Defects specific to java:') for bullet in bullets)

    def test_no_pack_carries_withholding_language(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)

        for domain, pack in compose_packs(bundles).items():
            lowered = pack.lower()
            for phrase in WITHHOLDING_DENY_LIST:
                assert phrase not in lowered, (domain, phrase)

    def test_domain_rules_reach_the_pack(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)

        pack = compose_packs(bundles)['java']

        assert 'Do not log credentials' in pack
        assert 'Inbound payloads are validated at the trust boundary' in pack

    def test_spine_topics_reach_the_pack(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)

        assert 'owasp top ten' in compose_packs(bundles)['java']

    def test_a_ruleless_domain_promises_no_rule_list(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)
        _write_skill(bundles, 'pm-fixture-docs', 'ext-triage-docs')

        pack = compose_packs(bundles)['docs']

        assert 'Domain rules' not in pack
        assert 'listed under "Domain rules" below' not in pack


class TestEmission:
    """A run emits exactly one pack, and a re-run swaps rather than accumulates."""

    def test_emits_a_single_config_file(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)
        out = tmp_path / 'out'

        written = PrAgentTarget(pack='java').generate(bundles, out)

        assert written == [out / CONFIG_FILENAME]
        assert sorted(p.name for p in out.iterdir()) == [CONFIG_FILENAME]

    def test_config_carries_only_the_pr_reviewer_pack(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)
        out = tmp_path / 'out'

        PrAgentTarget(pack='java').generate(bundles, out)
        parsed = tomllib.loads((out / CONFIG_FILENAME).read_text(encoding='utf-8'))

        assert list(parsed) == ['pr_reviewer']
        assert list(parsed['pr_reviewer']) == ['extra_instructions']
        assert SUBSTANTIATION_CLAUSE in parsed['pr_reviewer']['extra_instructions']

    def test_rerun_with_a_different_pack_swaps_rather_than_appends(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)
        _write_skill(bundles, 'pm-fixture-ruby', 'ruby-security', prohibited=('Do not eval untrusted input',))
        out = tmp_path / 'out'

        PrAgentTarget(pack='java').generate(bundles, out)
        PrAgentTarget(pack='ruby').generate(bundles, out)

        assert sorted(p.name for p in out.iterdir()) == [CONFIG_FILENAME]
        emitted = (out / CONFIG_FILENAME).read_text(encoding='utf-8')
        assert 'scoped to the ruby domain' in emitted
        assert 'scoped to the java domain' not in emitted
        assert 'Do not log credentials' not in emitted

    def test_rerun_with_the_same_pack_is_byte_identical(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)
        out = tmp_path / 'out'

        PrAgentTarget(pack='java').generate(bundles, out)
        first = (out / CONFIG_FILENAME).read_bytes()
        PrAgentTarget(pack='java').generate(bundles, out)

        assert (out / CONFIG_FILENAME).read_bytes() == first

    def test_emission_writes_no_bundle_tree_artifacts(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)
        out = tmp_path / 'out'

        PrAgentTarget(pack='java').generate(bundles, out)

        assert not (out / 'dist-manifest.json').exists()
        assert list(out.glob('**/plugin.json')) == []

    def test_missing_output_dir_is_rejected(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)

        with pytest.raises(ValueError, match='requires --output'):
            PrAgentTarget(pack='java').generate(bundles, None)

    def test_unknown_pack_is_rejected_and_names_the_derived_set(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)

        with pytest.raises(ValueError, match='unknown pack') as excinfo:
            PrAgentTarget(pack='cobol').generate(bundles, tmp_path / 'out')

        assert 'java' in str(excinfo.value)

    def test_marketplace_without_any_domain_is_rejected(self, tmp_path):
        bundles = tmp_path / 'bundles'
        (bundles / 'pm-empty' / 'skills').mkdir(parents=True)

        with pytest.raises(ValueError, match='no review domains derived'):
            PrAgentTarget(pack='java').generate(bundles, tmp_path / 'out')
