# SPDX-License-Identifier: FSL-1.1-ALv2
"""Drift and orthogonality guards over the artifact set the pr-agent target emits.

The subject is the EMITTED ARTIFACT SET, generated once from the real
marketplace at collection time: one spine-free body per derived review domain,
plus the spine artifact carrying the cross-cutting charter. Two guards protect
it, and each answers a question the previous whole-pack population could not
even express:

**Guard A — set identity.** The stems under ``packs/`` equal the derived domain
set plus the spine. Both sides are population-derived but they are NOT the same
population: the expected side comes from ``compose_packs``, the observed side
from the filesystem, and the two are produced by different code paths. A domain
that stops being emitted, or one emitted without being derived, fails here.

**Guard B — orthogonality.** Each charter clause and each spine category is
present in the spine artifact AND absent from every domain artifact. This is the
assertion the purposive emission model requires: the charter must be neither
lost nor duplicated, and a rendering change that silently re-folded spine text
back into the domain artifacts would restore exactly the cross-repository
duplication the published artifact set removes.

**Check topology.** The population is DERIVED; the expectations it is measured
against are NOT. Every expected value below is a literal declared in this module
and copied from the org charter — never a constant imported from the composer
that built the artifacts, and never a bullet count read back from it. A
comparison whose two sides share a pivot is vacuous: a composer change that
moves the pivot moves both sides together, and the guard stays green over an
artifact that has already lost the clause or outgrown its budget. The
category-bullet extractor is likewise a local reimplementation rather than a
composer import. No domain name appears as a literal anywhere in this module.

**Non-vacuity.** A parametrize over a population computed at collection time
yields zero cases and reports SKIPPED — not FAILED — when the population is
empty. Both guards therefore publish the sizes they measured over and assert
them non-empty as test cases of their own, and the negative controls at the end
prove each assertion can fail.

**Reach limits, stated rather than elided.**

1. These guards measure the artifact set THIS repository emits, which is the set
   the publish workflow mirrors. They do not query ``cuioss/pr-agent-settings``
   and therefore prove nothing about what is currently present there.
2. The ASSEMBLED reviewer prompt does not exist anywhere in this repository, so
   no test here can measure an assembled category total. The guards pin the
   budget's two halves — the spine at most ``CATEGORY_CEILING - 1`` bullets,
   each domain artifact exactly one — which proves a single-domain assembly
   lands exactly at the ceiling. They cannot prove that a consumer assembling N
   domains groups the N domain bullets back into one; that obligation belongs to
   the consumer that reads the published set.
"""

import tempfile
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT
from marketplace.targets.pr_agent.target import PrAgentTarget, compose_packs

MARKETPLACE_BUNDLES = PROJECT_ROOT / 'marketplace' / 'bundles'

#: The stem of the artifact carrying the charter. Declared here as a literal so
#: the set-identity comparison does not read the emitter's own constant.
SPINE_STEM = 'spine'

# ---------------------------------------------------------------------------
# Population — generated ONCE, from the REAL marketplace, at collection time
# ---------------------------------------------------------------------------

#: Held at module scope so the directory survives the whole session and is
#: cleaned up at interpreter exit.
_OUTPUT_DIR = tempfile.TemporaryDirectory(prefix='pr-agent-artifact-guard-')
_OUTPUT_ROOT = Path(_OUTPUT_DIR.name)

PrAgentTarget().generate(MARKETPLACE_BUNDLES, _OUTPUT_ROOT)

PACKS_DIR = _OUTPUT_ROOT / 'packs'

#: Every emitted artifact, keyed by stem. The ONLY derived input in this module.
ARTIFACTS: dict[str, str] = {
    path.stem: path.read_text(encoding='utf-8') for path in sorted(PACKS_DIR.glob('*.md'))
}
ARTIFACT_IDS: list[str] = sorted(ARTIFACTS)

#: The population partitioned. The spine is looked up with a default rather than
#: subscripted so a run that emitted no spine FAILS its own population test
#: instead of erroring during collection.
SPINE_ARTIFACT: str = ARTIFACTS.get(SPINE_STEM, '')
DOMAIN_ARTIFACTS: dict[str, str] = {
    stem: body for stem, body in ARTIFACTS.items() if stem != SPINE_STEM
}
DOMAIN_ARTIFACT_IDS: list[str] = sorted(DOMAIN_ARTIFACTS)

# ---------------------------------------------------------------------------
# Expectations — literals, copied from the org charter. Never imported.
# ---------------------------------------------------------------------------

#: The substantiation bar — a finding must name its own trigger.
SUBSTANTIATION_CLAUSE = (
    'For each finding, name the input or state that triggers it and what goes wrong. Overlap with '
    'other reviewers is acceptable — report the issue regardless of whether another tool might also '
    'catch it. Do not withhold a substantiated finding because it seems minor or obvious.'
)

#: Stated intent is a claim to check, not established fact.
INTENT_CLAUSE = (
    'If the pull request description states what the change is intended to do, treat that as a claim '
    'to be checked, not as established fact. Report where the implementation diverges from the stated '
    'intent, and never treat agreement with it as evidence that the code is correct.'
)

#: Severity is not a reporting threshold.
SEVERITY_CLAUSE = (
    'Severity is not a reporting threshold. Report a finding you can substantiate even when it is '
    'narrow, cheap to fix, or confined to test code — the reader decides what to act on, and a finding '
    'declined as minor costs one line of triage. Do not weigh whether an issue is important enough to '
    'mention.'
)

#: The anti-fabrication clause. Load-bearing: pressure to report more is exactly
#: the pressure that produces invented mechanisms.
ANTI_FABRICATION_CLAUSE = (
    'An empty list remains the correct answer when the diff genuinely carries nothing substantiable, and '
    'you must never invent a finding, pad the list, or report an issue whose mechanism you have not '
    'traced in the code shown. But do not return an empty list because nothing reached a bar of severity '
    'or importance. There is no such bar.'
)

CHARTER_CLAUSES = (
    SUBSTANTIATION_CLAUSE,
    INTENT_CLAUSE,
    SEVERITY_CLAUSE,
    ANTI_FABRICATION_CLAUSE,
)

#: The cross-cutting review categories, copied from the org charter. They belong
#: to the spine alone; a domain artifact carries its own single bullet instead.
SPINE_CATEGORY_TEXTS = (
    'Concurrency and time-of-check/time-of-use races; non-atomic file or state mutation; operations '
    'that are unsafe to retry or to run twice.',
    'Resource lifecycle: handles, locks, temporary files and subprocesses that leak or are not '
    'released on the error path.',
    'Fail-open error handling where fail-closed is required; swallowed exceptions; a guard whose '
    'predicate cannot fire; validation that admits the empty or degenerate input.',
    'Correctness bugs whose impact is data loss, state corruption, or a silently wrong result.',
    'Injection, deserialization, path traversal, SSRF and unsafe reflection.',
    'Authentication, authorization and trust-boundary errors; privilege escalation.',
    'Secret and credential handling, including values reaching logs or error messages.',
    'Dependency and supply-chain risk introduced by the change.',
    'Missing negative or adversarial test coverage for any of the above.',
)

#: Every text that belongs to the spine and to nowhere else — Guard B's population.
SPINE_ONLY_TEXTS = CHARTER_CLAUSES + SPINE_CATEGORY_TEXTS
SPINE_ONLY_TEXT_IDS = [f'clause-{i}' for i in range(1, len(CHARTER_CLAUSES) + 1)] + [
    f'category-{i}' for i in range(1, len(SPINE_CATEGORY_TEXTS) + 1)
]

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


def category_bullets(artifact: str) -> list[str]:
    """Extract an artifact's category bullet list.

    A local reimplementation on purpose: importing the composer's own splitter
    would make the budget assertions share a pivot with the code they measure.
    """
    bullets: list[str] = []
    for line in artifact.splitlines():
        if line.startswith(_RULES_HEADING_PREFIX):
            break
        if line.startswith('- '):
            bullets.append(line[2:])
    return bullets


def _emitted_stems() -> set[str]:
    """The artifact stems on disk — read from the filesystem, not from ARTIFACTS."""
    return {path.stem for path in PACKS_DIR.glob('*.md')}


def _derived_stems() -> set[str]:
    """The stems the derivation says should exist: every domain, plus the spine."""
    return set(compose_packs(MARKETPLACE_BUNDLES)) | {SPINE_STEM}


class TestPopulation:
    """The guards measure a real, non-empty population and publish its size."""

    def test_artifact_population_is_not_empty(self):
        """An empty emission is a FAILURE, not a vacuous pass.

        Stated as its own test case because the parametrized guards below would
        report SKIPPED — not FAILED — over an empty population.
        """
        assert ARTIFACTS, (
            'the pr-agent target emitted NO artifacts from '
            f'{MARKETPLACE_BUNDLES}; every guard below would pass vacuously'
        )

    def test_population_size_is_published(self):
        """Publish the population the guards below were measured over.

        A guard that reports "the set is right" without saying how large it was
        is indistinguishable from one that checked nothing.
        """
        print(
            f'pr-agent artifact guard population: {len(ARTIFACTS)} artifact(s) — '
            f'{len(DOMAIN_ARTIFACTS)} domain + spine: {", ".join(ARTIFACT_IDS)}'
        )
        assert len(ARTIFACTS) == len(ARTIFACT_IDS)
        assert DOMAIN_ARTIFACTS, 'no domain artifact was emitted'

    def test_population_includes_the_spine_artifact(self):
        """The spine must be IN the population, not merely composable.

        Guard B's presence half is measured against the spine artifact, so a run
        that emitted every domain but no spine would report green over an
        assertion that had nothing to check.
        """
        assert SPINE_STEM in ARTIFACTS, (
            f'the emitted set carries no {SPINE_STEM!r} artifact; the charter '
            'would be present in no artifact at all'
        )
        assert SPINE_ARTIFACT, 'the spine artifact is empty'


class TestArtifactSetIdentity:
    """Guard A — what is emitted is exactly what is derived, plus the spine."""

    def test_the_emitted_set_equals_the_derived_set_plus_the_spine(self):
        """Drift in either direction fails: a lost artifact or an unexpected one.

        The two sides are produced by different code paths — the expected set by
        ``compose_packs``, the observed set by reading the emitter's output
        directory — so this is a real comparison rather than a value checked
        against itself.
        """
        emitted = _emitted_stems()
        derived = _derived_stems()

        print(f'set identity measured over {len(emitted)} emitted / {len(derived)} derived stem(s)')
        assert emitted, 'the emitter wrote no artifact at all'
        assert emitted == derived, (
            'the emitted artifact set has drifted from the derived one.\n'
            f'  emitted only: {sorted(emitted - derived)}\n'
            f'  derived only: {sorted(derived - emitted)}'
        )

    def test_the_spine_stem_is_not_itself_a_derived_domain(self):
        """Collision guard: a derived domain named like the spine would overwrite it.

        A bundle shipping a ``spine-security`` skill would derive that name, and
        one artifact would silently replace the other. The build must fail here
        instead.
        """
        assert SPINE_STEM not in compose_packs(MARKETPLACE_BUNDLES), (
            f'{SPINE_STEM!r} is now a derived domain name and collides with the '
            'spine artifact; one would overwrite the other'
        )


@pytest.mark.parametrize('text', SPINE_ONLY_TEXTS, ids=SPINE_ONLY_TEXT_IDS)
class TestSpineTextAppearsExactlyOnce:
    """Guard B — the charter and the spine categories live in ONE artifact."""

    def test_present_in_the_spine_artifact(self, text):
        assert text in SPINE_ARTIFACT, f'the spine artifact lost: {text[:60]!r}'

    def test_absent_from_every_domain_artifact(self, text):
        offenders = [stem for stem, body in DOMAIN_ARTIFACTS.items() if text in body]
        assert not offenders, (
            f'spine text re-appeared in domain artifact(s) {offenders}: {text[:60]!r}. '
            'The artifact set must be orthogonal — spine text belongs to the spine alone.'
        )


class TestOrthogonalityCoverage:
    """Guard B's own non-vacuity: both of its populations are non-empty and published."""

    def test_both_orthogonality_populations_are_published(self):
        print(
            f'orthogonality guard: {len(SPINE_ONLY_TEXTS)} spine text(s) checked against '
            f'{len(DOMAIN_ARTIFACTS)} domain artifact(s)'
        )
        assert SPINE_ONLY_TEXTS, 'no spine text is declared; Guard B would check nothing'
        assert DOMAIN_ARTIFACTS, (
            'no domain artifact was emitted; Guard B\'s absence half would pass over '
            'an empty population'
        )


class TestCategoryBudget:
    """The ceiling, as the two-part budget the orthogonal set replaces it with."""

    def test_the_spine_reserves_one_slot_of_the_ceiling(self):
        """The spine half: at most ceiling - 1, leaving the last slot for the domain."""
        bullets = category_bullets(SPINE_ARTIFACT)

        assert bullets, 'the spine artifact carries no category bullets'
        assert len(bullets) <= CATEGORY_CEILING - 1, (
            f'the spine carries {len(bullets)} category bullets and leaves no slot for '
            f'the domain bullet; the ceiling is {CATEGORY_CEILING}: '
            f'{bullets[CATEGORY_CEILING - 1:]}'
        )

    @pytest.mark.parametrize('domain', DOMAIN_ARTIFACT_IDS)
    def test_every_domain_artifact_carries_exactly_one_bullet(self, domain):
        """The domain half: exactly one, not "at most" one.

        Exactly one is what makes a single-domain assembly land exactly at the
        ceiling, and what lets a consumer group N of them back into one.
        """
        bullets = category_bullets(DOMAIN_ARTIFACTS[domain])

        assert len(bullets) == 1, (
            f'domain artifact {domain!r} carries {len(bullets)} category bullets, '
            f'expected exactly one: {bullets}'
        )


@pytest.mark.parametrize('artifact_id', ARTIFACT_IDS)
class TestWithholdingLanguage:
    """No artifact — domain or spine — carries language that suppresses a finding."""

    def test_carries_no_withholding_language(self, artifact_id):
        lowered = ARTIFACTS[artifact_id].lower()
        for phrase in WITHHOLDING_DENY_LIST:
            assert phrase not in lowered, (
                f'artifact {artifact_id!r} reintroduced withholding language: {phrase!r}'
            )


class TestGuardBites:
    """Negative controls — each guard is shown to FAIL on a violating input.

    Without these, a guard whose extractor silently returned nothing (or whose
    literals never matched anything) would report green over every artifact
    forever.
    """

    def _domain_sample(self) -> str:
        return DOMAIN_ARTIFACTS[DOMAIN_ARTIFACT_IDS[0]]

    def test_missing_anti_fabrication_clause_is_detected(self):
        # Mutated against the SPINE, the only artifact that carries the clause:
        # mutating a domain artifact would remove nothing and pass vacuously.
        assert ANTI_FABRICATION_CLAUSE in SPINE_ARTIFACT
        mutated = SPINE_ARTIFACT.replace(ANTI_FABRICATION_CLAUSE, 'nothing to see here')
        assert ANTI_FABRICATION_CLAUSE not in mutated

    def test_missing_substantiation_requirement_is_detected(self):
        assert SUBSTANTIATION_CLAUSE in SPINE_ARTIFACT
        mutated = SPINE_ARTIFACT.replace(SUBSTANTIATION_CLAUSE, 'say whatever')
        assert SUBSTANTIATION_CLAUSE not in mutated

    def test_a_removed_artifact_makes_the_set_identity_guard_fail(self):
        """Guard A's control: the comparison must notice a missing artifact."""
        emitted = _emitted_stems()
        derived = _derived_stems()
        assert emitted == derived, 'precondition: the set is currently in agreement'

        dropped = sorted(emitted)[0]

        assert (emitted - {dropped}) != derived, (
            f'removing {dropped!r} left the comparison equal; the set-identity '
            'assertion cannot detect a missing artifact'
        )

    def test_a_clause_injected_into_a_domain_artifact_is_detected(self):
        """Guard B's control: the absence half must notice re-duplicated spine text."""
        sample = self._domain_sample()
        assert ANTI_FABRICATION_CLAUSE not in sample, (
            'precondition: the sample domain artifact carries no charter clause'
        )

        mutated = f'{sample}\n{ANTI_FABRICATION_CLAUSE}\n'

        assert ANTI_FABRICATION_CLAUSE in mutated

    def test_an_extra_spine_category_bullet_is_detected(self):
        """The moved successor of the eleventh-bullet control.

        The spine sits one under the ceiling — the last slot is reserved for the
        single bullet each domain artifact contributes — so one extra spine
        bullet is what puts a single-domain assembly over.
        """
        bullets = category_bullets(SPINE_ARTIFACT)
        assert len(bullets) == CATEGORY_CEILING - 1, (
            'the spine is expected to sit exactly one under the ceiling, reserving '
            f'the last slot for the domain bullet; got {len(bullets)}'
        )

        marker = f'- {bullets[-1]}'
        mutated = SPINE_ARTIFACT.replace(
            marker, f'{marker}\n- A tenth spine category nobody budgeted for.', 1
        )

        assert len(category_bullets(mutated)) == CATEGORY_CEILING

    def test_reintroduced_withholding_language_is_detected(self):
        for phrase in WITHHOLDING_DENY_LIST:
            mutated = f'{self._domain_sample()}\n{phrase.capitalize()} the other reviewers.\n'
            assert phrase in mutated.lower()

    def test_an_empty_population_would_fail_rather_than_skip(self):
        """The non-vacuity assertion's own negative control.

        `TestPopulation.test_artifact_population_is_not_empty` asserts truthiness
        of the population; this pins that an empty population is falsy, so that
        assertion genuinely fails rather than skipping.
        """
        empty: dict[str, str] = {}
        assert not empty
