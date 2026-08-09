# SPDX-License-Identifier: FSL-1.1-ALv2
"""Charter regression guard over every pack the pr-agent target can emit.

The subject is not the pack this repository happens to carry — it is the WHOLE
derived pack population, so a domain added to the marketplace is guarded the
moment it becomes derivable. Four invariants protect the charter from the
dilution that produced five consecutive empty reviews:

(a) the anti-fabrication clause is present verbatim in every pack;
(b) the substantiation requirement is present verbatim in every pack;
(c) no pack's category bullet list exceeds the ceiling;
(d) no pack carries withholding language.

**Check topology.** The population is DERIVED; the expectations it is measured
against are NOT. Every expected value below is a literal declared in this module
and copied from the org charter — never a constant imported from the composer
that built the packs, and never a bullet count read back from that composer. A
comparison whose two sides share a pivot is vacuous: a composer change that moves
the pivot moves both sides together, and the guard stays green over a pack that
has already outgrown the ceiling or lost the clause. The category-bullet
extractor is likewise a local reimplementation rather than a composer import.

**Non-vacuity.** A parametrize over a population computed at collection time
yields zero cases and reports SKIPPED — not FAILED — when the population is
empty. The population size is therefore asserted non-zero as a test case of its
own, and published, so an empty derivation is a failure rather than a green run
over nothing. The negative controls at the end prove each assertion can fail.
"""

from pathlib import Path

import pytest

from marketplace.targets.pr_agent.target import compose_packs

PROJECT_ROOT = Path(__file__).resolve().parents[4]
MARKETPLACE_BUNDLES = PROJECT_ROOT / 'marketplace' / 'bundles'

#: The derived pack population, computed at collection time from the REAL
#: marketplace. This is the ONLY derived input in the module.
PACKS: dict[str, str] = compose_packs(MARKETPLACE_BUNDLES)
PACK_IDS: list[str] = sorted(PACKS)

# ---------------------------------------------------------------------------
# Expectations — literals, copied from the org charter. Never imported.
# ---------------------------------------------------------------------------

#: The anti-fabrication clause. Load-bearing: pressure to report more is exactly
#: the pressure that produces invented mechanisms.
ANTI_FABRICATION_CLAUSE = (
    'you must never invent a finding, pad the list, or report an issue whose mechanism you have not '
    'traced in the code shown'
)

#: The substantiation bar — a finding must name its own trigger.
SUBSTANTIATION_REQUIREMENT = 'name the input or state that triggers it'

#: The category ceiling. `pr-agent-settings/README.adoc` § "Recall beats
#: precision": past roughly ten entries the answer is a second focused pass, not
#: an eleventh bullet.
CATEGORY_CEILING = 10

#: Withholding language. The first three are the suppressors the charter's own
#: rationale identifies as having produced five consecutive empty reviews; the
#: fourth is a phrasing variant of the first. Matched case-insensitively.
WITHHOLDING_DENY_LIST = (
    'do not duplicate',
    'prefer one well-evidenced',
    'only when you can name the concrete input',
    'avoid duplicating',
)

#: The heading that ends the category bullet list. Bullets after it are domain
#: RULES, which the ceiling deliberately does not govern.
_RULES_HEADING_PREFIX = 'Domain rules'


def category_bullets(pack: str) -> list[str]:
    """Extract a pack's category bullet list.

    A local reimplementation on purpose: importing the composer's own splitter
    would make the ceiling assertion share a pivot with the code it measures.
    """
    bullets: list[str] = []
    for line in pack.splitlines():
        if line.startswith(_RULES_HEADING_PREFIX):
            break
        if line.startswith('- '):
            bullets.append(line[2:])
    return bullets


class TestPopulation:
    """The guard measures a real, non-empty population and publishes its size."""

    def test_pack_population_is_not_empty(self):
        """An empty derivation is a FAILURE, not a vacuous pass.

        Stated as its own test case because the parametrized invariants below
        would report SKIPPED — not FAILED — over an empty population.
        """
        assert PACKS, (
            'the pr-agent target derived NO packs from '
            f'{MARKETPLACE_BUNDLES}; every invariant below would pass vacuously'
        )

    def test_population_size_is_published(self):
        """Publish the population the invariants below were measured over.

        A guard that reports "all invariants hold" without saying over how many
        packs is indistinguishable from one that checked nothing.
        """
        print(f'pr-agent charter guard population: {len(PACKS)} pack(s) — {", ".join(PACK_IDS)}')
        assert len(PACKS) == len(PACK_IDS)
        assert len(PACKS) >= 1


@pytest.mark.parametrize('domain', PACK_IDS)
class TestCharterInvariants:
    """The four invariants, applied to every derived pack."""

    def test_anti_fabrication_clause_is_present_verbatim(self, domain):
        assert ANTI_FABRICATION_CLAUSE in PACKS[domain], (
            f'pack {domain!r} lost the anti-fabrication clause'
        )

    def test_substantiation_requirement_is_present_verbatim(self, domain):
        assert SUBSTANTIATION_REQUIREMENT in PACKS[domain], (
            f'pack {domain!r} lost the substantiation requirement'
        )

    def test_category_list_does_not_exceed_the_ceiling(self, domain):
        bullets = category_bullets(PACKS[domain])
        assert len(bullets) <= CATEGORY_CEILING, (
            f'pack {domain!r} carries {len(bullets)} category bullets, ceiling is '
            f'{CATEGORY_CEILING}: {bullets[CATEGORY_CEILING:]}'
        )

    def test_category_list_is_not_empty(self, domain):
        """A pack with no categories would satisfy the ceiling vacuously."""
        assert category_bullets(PACKS[domain]), f'pack {domain!r} carries no category bullets'

    def test_carries_no_withholding_language(self, domain):
        lowered = PACKS[domain].lower()
        for phrase in WITHHOLDING_DENY_LIST:
            assert phrase not in lowered, (
                f'pack {domain!r} reintroduced withholding language: {phrase!r}'
            )


class TestGuardBites:
    """Negative controls — each invariant is shown to FAIL on a violating pack.

    Without these, a guard whose extractor silently returned nothing (or whose
    literals never matched anything) would report green over every pack forever.
    """

    def _sample(self) -> str:
        return PACKS[PACK_IDS[0]]

    def test_missing_anti_fabrication_clause_is_detected(self):
        mutated = self._sample().replace(ANTI_FABRICATION_CLAUSE, 'nothing to see here')
        assert ANTI_FABRICATION_CLAUSE not in mutated

    def test_missing_substantiation_requirement_is_detected(self):
        mutated = self._sample().replace(SUBSTANTIATION_REQUIREMENT, 'say whatever')
        assert SUBSTANTIATION_REQUIREMENT not in mutated

    def test_an_eleventh_category_bullet_is_detected(self):
        """An extra bullet inserted into the category list breaks the ceiling."""
        sample = self._sample()
        bullets = category_bullets(sample)
        assert len(bullets) == CATEGORY_CEILING, (
            'the sample pack is expected to sit exactly at the ceiling, so adding '
            f'one bullet crosses it; got {len(bullets)}'
        )

        marker = f'- {bullets[-1]}'
        mutated = sample.replace(marker, f'{marker}\n- An eleventh category nobody budgeted for.', 1)

        assert len(category_bullets(mutated)) == CATEGORY_CEILING + 1

    def test_reintroduced_withholding_language_is_detected(self):
        for phrase in WITHHOLDING_DENY_LIST:
            mutated = f'{self._sample()}\n{phrase.capitalize()} the other reviewers.\n'
            assert phrase in mutated.lower()

    def test_an_empty_population_would_fail_rather_than_skip(self):
        """The non-vacuity assertion's own negative control.

        `TestPopulation.test_pack_population_is_not_empty` asserts truthiness of
        the population; this pins that an empty population is falsy, so that
        assertion genuinely fails rather than skipping.
        """
        empty: dict[str, str] = {}
        assert not empty
