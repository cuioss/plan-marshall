# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the pr-agent instruction-pack export target.

The subject is the target's DERIVATION, COMPOSITION and EMISSION contract: the
domain set is scanned out of the source marketplace rather than hand-transcribed,
a run emits an ORTHOGONAL artifact set — one spine-free body per derived domain
plus the spine carrying the charter exactly once — and the target declares itself
not-a-bundle-tree so the CLI's generic post-emit steps stay off its output.

Every test builds its own fixture marketplace, so the assertions do not depend on
which bundles the real marketplace happens to ship today.
"""

import shutil
from pathlib import Path

import pytest

from marketplace.targets import TARGET_REGISTRY
from marketplace.targets.claude.target import ClaudeTarget
from marketplace.targets.pr_agent.target import (
    ANTI_FABRICATION_CLAUSE,
    MAX_CATEGORY_BULLETS,
    SPINE_CATEGORIES,
    SUBSTANTIATION_CLAUSE,
    PrAgentTarget,
    compose_packs,
    compose_spine,
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

#: The stem of the one artifact carrying the charter. Declared locally so the
#: emission assertions do not share a pivot with the emitter's own constant.
SPINE_STEM = 'spine'


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
    """A marketplace deriving TWO rule-bearing domains."""
    bundles = _fixture_marketplace(tmp_path)
    _write_skill(
        bundles,
        'pm-fixture-ruby',
        'ruby-security',
        prohibited=('Do not eval untrusted input',),
        constraints=('Gems are pinned by checksum',),
    )
    return bundles


def _category_bullets(body: str) -> list[str]:
    """The category bullet list — the bullets above the domain-rules block."""
    bullets: list[str] = []
    for line in body.splitlines():
        if line.startswith('Domain rules'):
            break
        if line.startswith('- '):
            bullets.append(line[2:])
    return bullets


def _emitted_stems(out: Path) -> list[str]:
    """The artifact stems a run left under ``{out}/packs/``."""
    return sorted(path.stem for path in (out / 'packs').glob('*.md'))


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
    """The two renderers are DISJOINT, and together they hold the category budget."""

    def test_one_pack_per_derived_domain(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)
        _write_skill(bundles, 'pm-fixture-ruby', 'ruby-security', prohibited=('Do not eval untrusted input',))

        packs = compose_packs(bundles)

        assert sorted(packs) == ['java', 'ruby']

    def test_clauses_are_carried_verbatim_into_the_spine(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)

        spine = compose_spine(discover_spine_topics(bundles))

        assert SUBSTANTIATION_CLAUSE in spine
        assert ANTI_FABRICATION_CLAUSE in spine
        assert 'name the input or state that triggers it' in spine

    def test_no_domain_body_carries_a_charter_clause(self, tmp_path):
        """The absence half of the inversion — the charter lives in ONE place.

        Without this, the spine could be rendered correctly while every domain
        body still folded the same clauses in, which is exactly the duplication
        the orthogonal artifact set removes.
        """
        bundles = _fixture_marketplace(tmp_path)
        _write_skill(bundles, 'pm-fixture-docs', 'ext-triage-docs')

        packs = compose_packs(bundles)

        assert packs, 'the derived pack population must not be empty'
        for domain, body in packs.items():
            assert SUBSTANTIATION_CLAUSE not in body, domain
            assert ANTI_FABRICATION_CLAUSE not in body, domain

    def test_no_domain_body_carries_a_spine_category(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)

        body = compose_packs(bundles)['java']

        for category in SPINE_CATEGORIES:
            assert category not in body

    def test_spine_topics_reach_the_spine(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)

        assert 'owasp top ten' in compose_spine(discover_spine_topics(bundles))

    def test_spine_is_emitted_without_topics(self):
        """A fixture marketplace with no spine skill still yields a spine body.

        Only the foundations line is conditional; the clauses and categories are
        unconditional, so an absent spine skill cannot silently drop the charter.
        """
        spine = compose_spine(())

        assert ANTI_FABRICATION_CLAUSE in spine
        assert 'Cross-cutting foundations to apply in every review' not in spine

    def test_spine_reserves_one_slot_of_the_ceiling(self, tmp_path):
        """The spine half of the two-part budget."""
        bundles = _fixture_marketplace(tmp_path)

        bullets = _category_bullets(compose_spine(discover_spine_topics(bundles)))

        # Measured against a literal declared in this module, not against the
        # composer's own constant.
        assert len(bullets) <= EXPECTED_CATEGORY_CEILING - 1
        assert MAX_CATEGORY_BULLETS == EXPECTED_CATEGORY_CEILING

    def test_every_domain_body_carries_exactly_one_bullet(self, tmp_path):
        """The domain half of the two-part budget.

        Exactly one — not "at most" — is what makes a single-domain assembly land
        exactly at the ceiling and lets a consumer group N of them back into one.
        """
        bundles = _two_domain_marketplace(tmp_path)
        _write_skill(bundles, 'pm-fixture-docs', 'ext-triage-docs')

        packs = compose_packs(bundles)

        assert len(packs) == 3
        for domain, body in packs.items():
            assert len(_category_bullets(body)) == 1, domain

    def test_domain_bullet_survives_the_ceiling(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)

        bullets = _category_bullets(compose_packs(bundles)['java'])

        assert any(bullet.startswith('Defects specific to java:') for bullet in bullets)

    def test_no_pack_carries_withholding_language(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)
        bodies = dict(compose_packs(bundles))
        bodies[SPINE_STEM] = compose_spine(discover_spine_topics(bundles))

        for name, body in bodies.items():
            lowered = body.lower()
            for phrase in WITHHOLDING_DENY_LIST:
                assert phrase not in lowered, (name, phrase)

    def test_domain_rules_reach_the_pack(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)

        body = compose_packs(bundles)['java']

        assert 'Do not log credentials' in body
        assert 'Inbound payloads are validated at the trust boundary' in body

    def test_a_ruleless_domain_promises_no_rule_list(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)
        _write_skill(bundles, 'pm-fixture-docs', 'ext-triage-docs')

        body = compose_packs(bundles)['docs']

        assert 'Domain rules' not in body
        assert 'listed under "Domain rules" below' not in body


class TestEmission:
    """A run emits the whole artifact set under ``packs/``, and a re-run REPLACES it.

    "Replaces" is the load-bearing word and is asserted in both directions: a
    re-run widens the set when a domain starts deriving, and narrows it when one
    stops. Without the narrowing half, a run could only ever add — leaving a
    de-derived domain's artifact in the published set, where it reads as current.
    """

    def test_emits_one_artifact_per_derived_domain_plus_the_spine(self, tmp_path):
        bundles = _two_domain_marketplace(tmp_path)
        out = tmp_path / 'out'

        written = PrAgentTarget().generate(bundles, out)

        assert written == [out / 'packs' / 'java.md', out / 'packs' / 'ruby.md', out / 'packs' / 'spine.md']
        assert _emitted_stems(out) == ['java', 'ruby', SPINE_STEM]

    def test_emitted_set_widens_with_the_derived_set(self, tmp_path):
        """CONTROL for the set identity: the emitted set is derived, not fixed."""
        bundles = _fixture_marketplace(tmp_path)
        out = tmp_path / 'out'
        PrAgentTarget().generate(bundles, out)
        before = _emitted_stems(out)

        _write_skill(bundles, 'pm-fixture-ruby', 'ruby-security', prohibited=('Do not eval untrusted input',))
        PrAgentTarget().generate(bundles, out)

        assert before == ['java', SPINE_STEM]
        assert _emitted_stems(out) == ['java', 'ruby', SPINE_STEM]

    def test_emitted_set_narrows_with_the_derived_set(self, tmp_path):
        """The mirror of the widening control: a de-derived domain is PRUNED.

        Writing the new set over the old one is not enough. A domain whose
        standards skill is removed stops deriving, but its artifact from the
        previous run survives untouched in ``packs/`` — so the published set
        carries a domain this repository no longer states any rules for, and
        every remaining file still looks freshly generated. Nothing downstream
        can see the difference: the publish workflow's count-before-delete guard
        reads a plausible count either way.
        """
        bundles = _two_domain_marketplace(tmp_path)
        out = tmp_path / 'out'
        PrAgentTarget().generate(bundles, out)
        before = _emitted_stems(out)

        shutil.rmtree(bundles / 'pm-fixture-ruby')
        written = PrAgentTarget().generate(bundles, out)

        assert before == ['java', 'ruby', SPINE_STEM]
        assert _emitted_stems(out) == ['java', SPINE_STEM]
        assert not (out / 'packs' / 'ruby.md').exists()
        # the emitted set and the returned set agree — the prune does not strand
        # a path the caller was told was written
        assert sorted(p.stem for p in written) == _emitted_stems(out)

    def test_an_unmanaged_file_in_packs_survives_the_prune(self, tmp_path):
        """The prune reclaims only what this generator wrote.

        Negative control for the prune above. ``packs/`` is an output directory,
        not a directory this target owns outright: a file without the generated
        header was put there by someone, and deleting it would make the prune a
        directory-clearing step rather than a set-equality one.
        """
        bundles = _fixture_marketplace(tmp_path)
        out = tmp_path / 'out'
        PrAgentTarget().generate(bundles, out)
        hand_written = out / 'packs' / 'notes.md'
        hand_written.write_text('# reviewer notes, not generated\n', encoding='utf-8')

        PrAgentTarget().generate(bundles, out)

        assert hand_written.is_file()
        assert hand_written.read_text(encoding='utf-8') == '# reviewer notes, not generated\n'

    def test_no_repo_local_config_is_emitted(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)
        out = tmp_path / 'out'

        PrAgentTarget().generate(bundles, out)

        assert not (out / '.pr_agent.toml').exists()
        assert sorted(p.name for p in out.iterdir()) == ['packs']

    def test_every_artifact_carries_the_do_not_edit_header(self, tmp_path):
        bundles = _two_domain_marketplace(tmp_path)
        out = tmp_path / 'out'

        for path in PrAgentTarget().generate(bundles, out):
            text = path.read_text(encoding='utf-8')
            assert text.startswith('<!-- GENERATED ARTIFACT — do not edit by hand.'), path.name
            assert 'cuioss/plan-marshall' in text, path.name
            assert '--target pr-agent --output target/pr-agent' in text, path.name

    def test_a_domain_artifact_names_the_spine_as_not_optional(self, tmp_path):
        """The consumer-facing half of the orthogonality contract.

        A domain artifact deliberately carries no charter text, so a reader who
        applied one on its own would silently drop the substantiation bar.
        """
        bundles = _fixture_marketplace(tmp_path)
        out = tmp_path / 'out'

        PrAgentTarget().generate(bundles, out)

        domain_artifact = (out / 'packs' / 'java.md').read_text(encoding='utf-8')
        spine_artifact = (out / 'packs' / 'spine.md').read_text(encoding='utf-8')
        assert 'is applied alongside it and is not optional' in domain_artifact
        assert 'spine.md' in domain_artifact
        assert 'is not selectable' in spine_artifact

    def test_the_charter_reaches_the_spine_artifact_alone(self, tmp_path):
        bundles = _two_domain_marketplace(tmp_path)
        out = tmp_path / 'out'

        PrAgentTarget().generate(bundles, out)

        assert SUBSTANTIATION_CLAUSE in (out / 'packs' / 'spine.md').read_text(encoding='utf-8')
        for stem in ('java', 'ruby'):
            assert SUBSTANTIATION_CLAUSE not in (out / 'packs' / f'{stem}.md').read_text(encoding='utf-8')

    def test_rerun_is_byte_identical(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)
        out = tmp_path / 'out'

        PrAgentTarget().generate(bundles, out)
        first = {path.name: path.read_bytes() for path in (out / 'packs').glob('*.md')}
        PrAgentTarget().generate(bundles, out)

        assert {path.name: path.read_bytes() for path in (out / 'packs').glob('*.md')} == first

    def test_emission_writes_no_bundle_tree_artifacts(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)
        out = tmp_path / 'out'

        PrAgentTarget().generate(bundles, out)

        assert not (out / 'dist-manifest.json').exists()
        assert list(out.glob('**/plugin.json')) == []

    def test_missing_output_dir_is_rejected(self, tmp_path):
        bundles = _fixture_marketplace(tmp_path)

        with pytest.raises(ValueError, match='requires --output'):
            PrAgentTarget().generate(bundles, None)

    def test_marketplace_without_any_domain_is_rejected(self, tmp_path):
        bundles = tmp_path / 'bundles'
        (bundles / 'pm-empty' / 'skills').mkdir(parents=True)
        out = tmp_path / 'out'

        with pytest.raises(ValueError, match='no review domains derived'):
            PrAgentTarget().generate(bundles, out)

        assert not out.exists(), 'a rejected run must leave no half-written artifact set'
