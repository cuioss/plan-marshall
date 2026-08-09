# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the pr-agent instruction-pack export target.

The subject is the target's DERIVATION, COMPOSITION and EMISSION contract: the
domain set is scanned out of the source marketplace rather than hand-transcribed,
a run emits exactly one pack (which may compose several domains), and the target
declares itself not-a-bundle-tree so the CLI's generic post-emit steps stay off
its output.

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
    compose_selection,
    discover_domains,
    discover_spine_topics,
    parse_pack_selection,
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


def _two_domain_marketplace(tmp_path: Path) -> Path:
    """A marketplace deriving TWO rule-bearing domains, for composition tests."""
    bundles = _fixture_marketplace(tmp_path)
    _write_skill(
        bundles,
        'pm-fixture-ruby',
        'ruby-security',
        prohibited=('Do not eval untrusted input',),
        constraints=('Gems are pinned by checksum',),
    )
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


class TestPackSelectionParsing:
    """A selection is normalized once, and an empty one is rejected loudly."""

    def test_single_domain_string(self):
        assert parse_pack_selection('java') == ('java',)

    def test_comma_separated_string_splits_in_order(self):
        assert parse_pack_selection('python,plugin') == ('python', 'plugin')

    def test_whitespace_around_entries_is_stripped(self):
        assert parse_pack_selection(' python , plugin ') == ('python', 'plugin')

    def test_sequence_input_is_accepted(self):
        assert parse_pack_selection(['python', 'plugin']) == ('python', 'plugin')

    def test_duplicates_are_dropped_preserving_first_position(self):
        # A duplicate would double the domain's rule list in the composed pack.
        assert parse_pack_selection('python,plugin,python') == ('python', 'plugin')

    def test_empty_selection_is_rejected(self):
        with pytest.raises(ValueError, match='empty pack selection'):
            parse_pack_selection(' , ')


class TestComposedSelection:
    """A pack may compose several domains — grouped, and inside the ceiling."""

    def test_composed_pack_carries_every_selected_domains_rules(self, tmp_path):
        bundles = _two_domain_marketplace(tmp_path)

        pack = compose_selection(bundles, ('java', 'ruby'))

        assert 'Do not log credentials' in pack
        assert 'Do not eval untrusted input' in pack

    def test_composed_pack_stays_within_the_category_ceiling(self, tmp_path):
        """The ceiling is held by GROUPING, not by widening it.

        This is the invariant the composition exists to preserve: one category
        per domain would put a two-domain pack at eleven bullets.
        """
        bundles = _two_domain_marketplace(tmp_path)

        bullets = _category_bullets(compose_selection(bundles, ('java', 'ruby')))

        assert len(bullets) <= EXPECTED_CATEGORY_CEILING

    def test_composing_a_domain_adds_no_category_bullet(self, tmp_path):
        """CONTROL for the grouping claim: the bullet count does not grow with N.

        Without this, the ceiling assertion above would also pass for a
        composition that happened to sit one under the ceiling by luck.
        """
        bundles = _two_domain_marketplace(tmp_path)

        one = _category_bullets(compose_selection(bundles, ('java',)))
        two = _category_bullets(compose_selection(bundles, ('java', 'ruby')))

        assert len(one) == len(two)

    def test_composed_domain_bullet_names_every_selected_domain(self, tmp_path):
        bundles = _two_domain_marketplace(tmp_path)

        bullets = _category_bullets(compose_selection(bundles, ('java', 'ruby')))
        domain_bullet = next(b for b in bullets if b.startswith('Defects specific to'))

        assert 'java' in domain_bullet
        assert 'ruby' in domain_bullet

    def test_composed_rules_are_tagged_with_their_domain(self, tmp_path):
        bundles = _two_domain_marketplace(tmp_path)

        pack = compose_selection(bundles, ('java', 'ruby'))

        assert '- [java] Do not log credentials' in pack
        assert '- [ruby] Do not eval untrusted input' in pack

    def test_single_domain_rules_carry_no_tag(self, tmp_path):
        """A one-domain pack needs no tag — the whole pack is that domain."""
        bundles = _two_domain_marketplace(tmp_path)

        pack = compose_selection(bundles, ('java',))

        assert '- Do not log credentials' in pack
        assert '[java]' not in pack

    def test_selection_order_is_the_caller_s(self, tmp_path):
        bundles = _two_domain_marketplace(tmp_path)

        assert 'scoped to the java and ruby domains' in compose_selection(bundles, ('java', 'ruby'))
        assert 'scoped to the ruby and java domains' in compose_selection(bundles, ('ruby', 'java'))

    def test_composed_pack_keeps_the_charter_clauses(self, tmp_path):
        bundles = _two_domain_marketplace(tmp_path)

        pack = compose_selection(bundles, ('java', 'ruby'))

        assert SUBSTANTIATION_CLAUSE in pack
        assert ANTI_FABRICATION_CLAUSE in pack

    def test_ruleless_domain_in_a_composition_promises_no_rule_list(self, tmp_path):
        bundles = _two_domain_marketplace(tmp_path)
        _write_skill(bundles, 'pm-fixture-docs', 'ext-triage-docs')

        bullets = _category_bullets(compose_selection(bundles, ('java', 'docs')))
        domain_bullet = next(b for b in bullets if b.startswith('Defects specific to'))

        # java's rules are promised; docs is described by its standards instead.
        assert 'java code are listed under "Domain rules" below' in domain_bullet
        assert 'governs docs through its defect-triage standards' in domain_bullet

    def test_unknown_domain_in_a_selection_is_rejected(self, tmp_path):
        bundles = _two_domain_marketplace(tmp_path)

        with pytest.raises(ValueError, match='unknown pack') as excinfo:
            compose_selection(bundles, ('java', 'cobol'))

        assert 'cobol' in str(excinfo.value)


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

    def test_emits_one_file_for_a_composed_selection(self, tmp_path):
        bundles = _two_domain_marketplace(tmp_path)
        out = tmp_path / 'out'

        written = PrAgentTarget(pack='java,ruby').generate(bundles, out)

        assert written == [out / CONFIG_FILENAME]
        assert sorted(p.name for p in out.iterdir()) == [CONFIG_FILENAME]

    def test_composed_selection_reaches_the_emitted_config(self, tmp_path):
        bundles = _two_domain_marketplace(tmp_path)
        out = tmp_path / 'out'

        PrAgentTarget(pack='java,ruby').generate(bundles, out)
        instructions = tomllib.loads((out / CONFIG_FILENAME).read_text(encoding='utf-8'))[
            'pr_reviewer'
        ]['extra_instructions']

        assert 'Do not log credentials' in instructions
        assert 'Do not eval untrusted input' in instructions

    def test_header_regenerate_command_reproduces_the_composed_file(self, tmp_path):
        """The header's regenerate line must name the SELECTION, not just the target.

        A regenerate line without --packs would name a command producing a
        different file, and following it would silently narrow the repository's
        review to the default selection.
        """
        bundles = _two_domain_marketplace(tmp_path)
        out = tmp_path / 'out'

        PrAgentTarget(pack='java,ruby').generate(bundles, out)
        emitted = (out / CONFIG_FILENAME).read_text(encoding='utf-8')

        assert '# Pack: java,ruby.' in emitted
        assert '--packs java,ruby' in emitted

    def test_target_selection_is_available_both_split_and_joined(self):
        target = PrAgentTarget(pack='java,ruby')

        assert target.packs == ('java', 'ruby')
        assert target.pack == 'java,ruby'

    def test_default_selection_composes_this_repository_s_two_domains(self):
        """The no-argument default is the composed selection, not one language."""
        assert PrAgentTarget().packs == ('python', 'plugin')
