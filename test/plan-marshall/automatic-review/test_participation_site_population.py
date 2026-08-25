#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The participation-site population, derived from the tree rather than listed.

Nothing else pins the set of sites that credit participation, or that decide
whether a comment is new information. Without such a population a new crediting
site can be added and no test notices — the hand-maintained-roster defect class
the participation work exists to close.

The population is DERIVED: every file under ``marketplace/bundles/**`` carrying
one of the :data:`SEED_SYMBOLS` is a participation site, and each site carries an
expectation record stating what it reads, what it anchors on, and whether its
verdict is idempotent. Adding a crediting site without a record fails at IMPORT,
so the gap cannot hide behind a skipped or unwritten test.

The seed is guarded in BOTH directions, because a seed protects nothing on its
own:

- **No stale member** — every seed symbol must resolve to at least one site.
  A seed that resolves nowhere is a symbol the tree no longer has, and it would
  silently shrink the population it was meant to widen.
- **No missed member** — an AST walk of the producer, its private helper and the
  registry collects module- and class-level names carrying any
  :data:`VOCABULARY_STEMS` stem, and every candidate must be either seeded or
  carry a written exclusion reason recorded here.

The expectation records describe the code's CURRENT behaviour, so a change that
moves a site's anchor or its idempotence updates its record in the same change.

⛔ This module does NOT re-derive the currency-subject BOT population. That lives
in ``test/plan-marshall/workflow-integration-github/_github_pr_fixtures.py``, and
a second registry-derived tuple here would be exactly the duplicate definition
the site population exists to forbid. The subject here is the SITE set.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

from conftest import get_script_path, get_skill_dir

#: The symbol family a participation site is recognised by. Copied verbatim from
#: the deliverable's specification — these are the names the credit-granting and
#: new-information decisions are written in.
SEED_SYMBOLS: tuple[str, ...] = (
    '_reviewed_at_merge_candidate',
    'participation_requires_update',
    'participation_evidence',
    'head_sha_verified',
    'stale_participation',
    'existing_comment_keys',
    '_is_self_authored_response',
)

#: Name fragments that make an AST-collected symbol a participation CANDIDATE.
VOCABULARY_STEMS: tuple[str, ...] = (
    'particip',
    'reviewed',
    'stale',
    'head_sha',
    'comment_key',
    'merge_candidate',
)

#: File suffixes the site scan reads. Published because the population's reach is
#: exactly its scan's reach: a site in a suffix not listed here is not covered.
SCANNED_SUFFIXES: tuple[str, ...] = ('.py', '.md')

# The bundles root, resolved through conftest's skill accessor rather than by
# ``Path(__file__).parents[N]`` arithmetic (test/README.md § What conftest owns).
_BUNDLES_ROOT: Path = get_skill_dir('plan-marshall', 'automatic-review').parents[2]

#: The modules the no-missed-member drift check AST-walks.
_AST_WALKED_MODULES: tuple[Path, ...] = (
    get_script_path('plan-marshall', 'workflow-integration-github', 'github_pr.py'),
    get_script_path('plan-marshall', 'workflow-integration-github', '_github_pr.py'),
    get_script_path('plan-marshall', 'automatic-review', 'bot_registry.py'),
)


class VacuousPopulationError(AssertionError):
    """A derived population is empty, so every verdict over it is vacuous."""


class UnrecordedSiteError(AssertionError):
    """A participation site carries no expectation record."""


def scan_sites(symbols: tuple[str, ...]) -> tuple[dict[str, tuple[str, ...]], int]:
    """Return ``{relative path: symbols found}`` plus the number of files read.

    Parametrized on ``symbols`` so the same scan that derives the population can be
    re-run against a symbol the tree does not carry — the matched negative control
    that proves a stale seed really would resolve to nothing.
    """
    found: dict[str, tuple[str, ...]] = {}
    scanned = 0
    for path in sorted(_BUNDLES_ROOT.rglob('*')):
        if not path.is_file() or path.suffix not in SCANNED_SUFFIXES:
            continue
        scanned += 1
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        hits = tuple(symbol for symbol in symbols if symbol in text)
        if hits:
            found[path.relative_to(_BUNDLES_ROOT.parent.parent).as_posix()] = hits
    return found, scanned


SITE_SEEDS, SCANNED_FILE_COUNT = scan_sites(SEED_SYMBOLS)

#: The participation-site population, in deterministic path order.
PARTICIPATION_SITES: tuple[str, ...] = tuple(sorted(SITE_SEEDS))

#: The published size of the participation-site population.
PARTICIPATION_SITE_COUNT: int = len(PARTICIPATION_SITES)


@dataclass(frozen=True)
class SiteExpectation:
    """What one participation site reads, anchors on, and guarantees."""

    reads: str
    anchors_on: str
    idempotent: str
    note: str


#: Closed vocabularies. A record may not answer in free text, because an
#: unconstrained answer is one no reader can compare across sites.
READS_VOCABULARY = frozenset(
    {'live_comment_scan', 'currency_ledger', 'deduped_projection', 'registry_data', 'producer_sets', 'normative_text'}
)
ANCHOR_VOCABULARY = frozenset({'commit_sha', 'timestamp', 'both', 'none'})
IDEMPOTENT_VOCABULARY = frozenset({'yes', 'no', 'not_applicable'})

_SKILLS = 'marketplace/bundles/plan-marshall/skills'

#: One record per participation site. Enforced TOTAL at import.
SITE_EXPECTATIONS: dict[str, SiteExpectation] = {
    f'{_SKILLS}/automatic-review/SKILL.md': SiteExpectation(
        'normative_text',
        'both',
        'not_applicable',
        'The step body that applies the contract: it consumes the producer’s SHA-anchored '
        'currency verdict and separately drives the timestamp-anchored completion poll. It '
        'computes no verdict of its own.',
    ),
    f'{_SKILLS}/automatic-review/scripts/bot_registry.py': SiteExpectation(
        'registry_data',
        'none',
        'yes',
        'Declares each bot’s participation_evidence and participation_requires_update. A pure '
        'read over the parsed standards docs — it observes nothing, so it anchors on nothing.',
    ),
    f'{_SKILLS}/automatic-review/scripts/review_completeness.py': SiteExpectation(
        'producer_sets',
        'none',
        'yes',
        'Classifies each bot into the failure taxonomy from the producer’s emitted observation '
        'sets. It re-anchors nothing, so its verdict is a pure function of its inputs.',
    ),
    f'{_SKILLS}/automatic-review/standards/bot-participation-contract.md': SiteExpectation(
        'normative_text',
        'commit_sha',
        'not_applicable',
        'The contract itself — the single source of the currency rule. It STATES the anchor '
        'rather than evaluating it.',
    ),
    f'{_SKILLS}/automatic-review/standards/coderabbit.md': SiteExpectation(
        'registry_data',
        'none',
        'yes',
        'Per-bot registry record. Declares participation_requires_update: false, so this bot '
        'appends a new comment per review and never reaches the currency test.',
    ),
    f'{_SKILLS}/automatic-review/standards/pr-agent.md': SiteExpectation(
        'registry_data',
        'none',
        'yes',
        'Per-bot registry record. Declares participation_requires_update: true — the only bot '
        'that reaches the currency test today.',
    ),
    f'{_SKILLS}/automatic-review/standards/sourcery.md': SiteExpectation(
        'registry_data',
        'none',
        'yes',
        'Per-bot registry record. Declares participation_requires_update: false.',
    ),
    f'{_SKILLS}/phase-6-finalize/standards/branch-cleanup-rereview.md': SiteExpectation(
        'normative_text',
        'commit_sha',
        'not_applicable',
        'Re-review routing: reads head_sha_verified to tell a completed re-review from a '
        'decline. States the anchor, evaluates nothing.',
    ),
    f'{_SKILLS}/phase-6-finalize/standards/branch-cleanup.md': SiteExpectation(
        'normative_text',
        'commit_sha',
        'not_applicable',
        'The merge barrier’s routing rules over the producer’s participation sets, including '
        'stale_participation and the head_sha_verified decline shape.',
    ),
    f'{_SKILLS}/tools-integration-ci/standards/api-contract.md': SiteExpectation(
        'normative_text',
        'timestamp',
        'not_applicable',
        'Documents the wait-for-comments movement arm, which selects on '
        'participation_requires_update and anchors on a timestamp. It is the WAIT’s contract, '
        'not a participation credit.',
    ),
    f'{_SKILLS}/tools-integration-ci/standards/pr-review-operations.md': SiteExpectation(
        'normative_text',
        'commit_sha',
        'not_applicable',
        'The abstraction layer’s description of the producer’s participation and '
        'stale-participation sets.',
    ),
    f'{_SKILLS}/workflow-integration-github/SKILL.md': SiteExpectation(
        'normative_text',
        'both',
        'not_applicable',
        'Publishes the producer’s SHA-anchored return contract AND the timestamp-anchored '
        'github_ops pr wait-for-comments completion predicate — two anchors on one surface.',
    ),
    f'{_SKILLS}/workflow-integration-github/scripts/_github_pr.py': SiteExpectation(
        'live_comment_scan',
        'timestamp',
        'yes',
        'Hosts the wait predicate’s movement arm (_detect_movement_bots) and its answerability '
        'read. It reads the fetched comment list and matches movement since the wait started; '
        'it grants no participation credit.',
    ),
    f'{_SKILLS}/workflow-integration-github/scripts/github_pr.py': SiteExpectation(
        'currency_ledger',
        'commit_sha',
        'yes',
        'The producer. Evaluates the currency test for a participation_requires_update bot '
        'against the merge-candidate SHA, reading the durable currency ledger it writes on '
        'credit, and reports a failed test in stale_participation_bots[].',
    ),
    f'{_SKILLS}/workflow-integration-github/scripts/github_re_review.py': SiteExpectation(
        'live_comment_scan',
        'both',
        'no',
        'The re-review awaiter: a review matched by reviewed-commit SHA yields '
        'head_sha_verified: true, a comment matched by timestamp yields false. Its verdict '
        'depends on when it is asked, so it is not idempotent.',
    ),
    f'{_SKILLS}/workflow-pr-doctor/standards/automated-review-lifecycle.md': SiteExpectation(
        'normative_text',
        'commit_sha',
        'not_applicable',
        'The lifecycle narrative over the producer’s participation and stale-participation '
        'sets.',
    ),
}

#: AST candidates that are NOT seed symbols, each with the reason it is not one.
#: An exclusion says "not a seed", never "not participation-adjacent".
#:
#: The currency ledger's own storage symbols are absent from this dict because they are
#: absent from the CANDIDATE SET: named for what they hold
#: (``_CURRENCY_LEDGER_ARTIFACT`` / ``_currency_ledger_path`` and their pre-rename
#: read-only twins), they carry no :data:`VOCABULARY_STEMS` stem and so are never
#: collected. That is not a shrunken population — it is the storage layer resolving
#: uniformly, the way its sibling readers ``_recorded_currency_records`` /
#: ``_record_currency_records`` always have. Their exclusion REASON was always
#: "storage naming, not a crediting decision", and the names now say so themselves.
CANDIDATE_EXCLUSIONS: dict[str, str] = {
    '_existing_pr_comment_keys': (
        'The FILING dedup’s key reconstruction: it decides whether a comment is new '
        'INFORMATION to file, never whether a bot participated. Its site is already in the '
        'population through the seed existing_comment_keys, which names the key set it rebuilds.'
    ),
}

#: The two members whose classification is recorded rather than inferred.
CLASSIFIED_MEMBERS: dict[str, str] = {
    'github_ops pr wait-for-comments completion predicate': (
        'TIMESTAMP-ANCHORED, and correct for a wait. A wait asks "did anything move since I '
        'started?", which is a different question from "did this review the merge candidate?". '
        'Anchoring the poll on the merge-candidate SHA would end the wait on a comment that '
        'never moved, and would run an in-place re-reviewer to the full timeout because its '
        'comment count never grows. The arm grants no participation credit — it decides when to '
        'stop polling; the credit is granted afterwards by the producer’s currency test.'
    ),
    '_is_self_authored_response': (
        'The THIRD comment-identity in force, alongside the filing dedup key and the currency '
        'ledger key. The widened dedup identity does NOT subsume it, and cannot: this '
        'recogniser matches by BODY SHAPE (start-anchored on the batched-response heading), '
        'while the dedup matches by IDENTITY. Every turn of the respond -> re-fetch cycle posts '
        'a comment with a NEW comment_id, so no dedup key ever matches it; adding an updated_at '
        'term makes that key strictly MORE discriminating, so it can only ever file more, never '
        'less. Both stages must stay.'
    ),
}


def guard_non_empty(population: tuple[str, ...], name: str, derivation: str) -> tuple[str, ...]:
    """Return ``population``, or raise when it is empty.

    Raises:
        VacuousPopulationError: when ``population`` is empty.
    """
    if not population:
        raise VacuousPopulationError(
            f'{name} is empty — derived from {derivation}. A verdict over an empty population '
            f'reports clean while covering nothing.'
        )
    return population


def guard_every_site_recorded(
    sites: tuple[str, ...], expectations: dict[str, SiteExpectation]
) -> tuple[str, ...]:
    """Return ``sites``, or raise naming the sites carrying no expectation record.

    Raises:
        UnrecordedSiteError: when any site has no record.
    """
    unrecorded = [site for site in sites if site not in expectations]
    if unrecorded:
        raise UnrecordedSiteError(
            'participation site(s) with no expectation record: '
            + ', '.join(unrecorded)
            + ' — state what the site reads, what it anchors on, and whether its verdict is '
            'idempotent in SITE_EXPECTATIONS.'
        )
    return sites


def _vocabulary_candidates(module_path: Path) -> set[str]:
    """Module- and class-level names in ``module_path`` carrying a vocabulary stem."""
    names: set[str] = set()

    def record(node: ast.AST) -> None:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)

    for node in ast.parse(module_path.read_text(encoding='utf-8')).body:
        record(node)
        if isinstance(node, ast.ClassDef):
            for child in node.body:
                record(child)
    return {name for name in names if any(stem in name.lower() for stem in VOCABULARY_STEMS)}


# Import-time guards. A gap in either is a collection error, not a silent skip.
guard_non_empty(PARTICIPATION_SITES, 'PARTICIPATION_SITES', f'{SCANNED_FILE_COUNT} scanned files')
guard_every_site_recorded(PARTICIPATION_SITES, SITE_EXPECTATIONS)


def test_the_site_population_publishes_a_non_zero_size():
    """The population is non-empty and its size is published, not merely asserted."""
    assert PARTICIPATION_SITE_COUNT == len(PARTICIPATION_SITES)
    assert PARTICIPATION_SITE_COUNT > 0
    assert SCANNED_FILE_COUNT > PARTICIPATION_SITE_COUNT


def test_the_vacuity_guard_fires_on_an_empty_population():
    """The import-time guard is exercised: it passes the real set and rejects an empty one."""
    assert guard_non_empty(PARTICIPATION_SITES, 'PARTICIPATION_SITES', 'the real scan')
    with pytest.raises(VacuousPopulationError, match='reports clean while covering nothing'):
        guard_non_empty((), 'PARTICIPATION_SITES', 'a scan that matched nothing')


def test_the_unrecorded_site_guard_fires_on_a_site_with_no_record():
    """A crediting site added without an expectation record is rejected at import."""
    assert guard_every_site_recorded(PARTICIPATION_SITES, SITE_EXPECTATIONS)
    with pytest.raises(UnrecordedSiteError, match='no expectation record'):
        guard_every_site_recorded((*PARTICIPATION_SITES, 'a/new/crediting_site.py'), SITE_EXPECTATIONS)


@pytest.mark.parametrize('seed', SEED_SYMBOLS)
def test_every_seed_symbol_resolves_to_at_least_one_site(seed):
    """No stale member: a seed resolving nowhere silently shrinks the population."""
    carriers = [site for site, seeds in SITE_SEEDS.items() if seed in seeds]
    assert carriers, (
        f'seed symbol {seed!r} resolves to no file under marketplace/bundles/** '
        f'({SCANNED_FILE_COUNT} files scanned) — it names a symbol the tree no longer has'
    )


def test_the_no_stale_member_check_resolves_nothing_for_an_absent_symbol():
    """Matched negative control: a seed that went stale really would resolve to no site.

    Without it the resolution check above is only ever observed on symbols the tree
    carries, which proves the scan can find things — never that it can fail to.
    """
    found, scanned = scan_sites(('_a_participation_symbol_this_tree_does_not_carry',))
    assert found == {}
    assert scanned == SCANNED_FILE_COUNT


@pytest.mark.parametrize('module_path', _AST_WALKED_MODULES, ids=lambda p: p.name)
def test_every_vocabulary_candidate_is_seeded_or_excluded(module_path):
    """No missed member: a participation-shaped symbol is seeded or has a written reason."""
    unaccounted = sorted(
        name
        for name in _vocabulary_candidates(module_path)
        if name not in SEED_SYMBOLS and name not in CANDIDATE_EXCLUSIONS
    )
    assert not unaccounted, (
        f'{module_path.name} defines participation-vocabulary symbol(s) that are neither seeded '
        f'nor excluded: {unaccounted}. Add each to SEED_SYMBOLS, or to CANDIDATE_EXCLUSIONS with '
        f'the reason it is not a seed.'
    )


def test_the_ast_walk_finds_candidates_at_all():
    """The no-missed-member check is not vacuous — the walk really collects candidates."""
    collected = set().union(*(_vocabulary_candidates(path) for path in _AST_WALKED_MODULES))
    assert collected
    assert collected & set(SEED_SYMBOLS)


def test_the_no_missed_member_check_depends_on_the_written_exclusions():
    """Matched negative control: without the exclusions the accounting does NOT pass.

    A check whose passing state survives emptying its own allowance is checking
    nothing. Dropping ``CANDIDATE_EXCLUSIONS`` must leave real unaccounted candidates.
    """
    collected = set().union(*(_vocabulary_candidates(path) for path in _AST_WALKED_MODULES))
    assert [name for name in collected if name not in SEED_SYMBOLS]
    assert set(CANDIDATE_EXCLUSIONS) <= collected
    assert all(reason.strip() for reason in CANDIDATE_EXCLUSIONS.values())


@pytest.mark.parametrize('site', PARTICIPATION_SITES)
def test_every_expectation_record_answers_in_the_closed_vocabulary(site):
    """A record may not answer in free text — an unconstrained answer compares to nothing."""
    record = SITE_EXPECTATIONS[site]
    assert record.reads in READS_VOCABULARY
    assert record.anchors_on in ANCHOR_VOCABULARY
    assert record.idempotent in IDEMPOTENT_VOCABULARY
    assert record.note.strip()


def test_no_expectation_record_is_stale():
    """Every record names a site the scan still finds."""
    stale = sorted(set(SITE_EXPECTATIONS) - set(PARTICIPATION_SITES))
    assert not stale, f'expectation record(s) for site(s) the scan no longer finds: {stale}'


@pytest.mark.parametrize('member', sorted(CLASSIFIED_MEMBERS))
def test_the_explicitly_classified_members_carry_their_classification(member):
    """The two members whose classification is recorded rather than inferred."""
    assert CLASSIFIED_MEMBERS[member].strip()


def test_the_classified_members_are_exactly_the_two_that_were_decided():
    """Neither classification may be dropped, and a third is a new decision to record."""
    assert set(CLASSIFIED_MEMBERS) == {
        'github_ops pr wait-for-comments completion predicate',
        '_is_self_authored_response',
    }
