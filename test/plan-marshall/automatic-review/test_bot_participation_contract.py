#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Contract-level suite for ``standards/bot-participation-contract.md``.

Cross-cutting counterpart to the co-located unit suites. Those pin per-component
BEHAVIOUR (``test_review_completeness.py`` owns the predicate's verdicts,
``test_upgrade.py`` owns the migration's four input states,
``test_comments_stage.py`` owns the producer's filters). This suite pins the
CONTRACT the components jointly implement:

* both participation knobs default to the EMPTY string on a fresh project;
* ``never_asked`` / ``migrated`` / ``answered`` are three distinguishable
  provenance states, so a never-asked key stays distinct from an answered-empty
  one;
* THIS repository's step params carry the settled two-list configuration;
* an unlisted bot is warned-about and STILL ingested (the warn-but-ingest rule);
* the failure taxonomy is EXHAUSTIVE — every classified bot lands in exactly one
  member, over a bot set derived from ``bot_registry.bot_kinds()``;
* every DOCUMENTED call site of the two invocation families quotes its
  interpolated list-flag placeholders, over a site population derived by scanning
  the marketplace tree;
* a crashed participation gate is an UNKNOWN verdict at both families and at both
  consuming documents — never a recorded pass;
* each advertised invocation form agrees with its live argparse surface on the
  optionality of every list flag.

Every set-guarding assertion derives its population from the registry (for bots),
from a repository scan (for call sites), or from the live argparse surface (for
list flags) rather than a hard-coded literal list, so a bot added or retired in a
standards doc, a fifth call site added in a future doc, or a sixth list flag added
to the parser is covered here automatically instead of silently escaping the
sweep. Each sub-population is additionally guarded against vacuity: a derivation
that matched nothing FAILS rather than reporting a healthy aggregate over an
empty set.
"""

from __future__ import annotations

import itertools
import json
import re
import sys
from unittest.mock import patch

import pytest

from _bot_flag_derivation import derive_bot_flags
from conftest import PLAN_DIR_NAME, PROJECT_ROOT, get_script_path, run_script

_AR_SCRIPTS = get_script_path('plan-marshall', 'automatic-review', 'review_completeness.py').parent
_GH_SCRIPTS = get_script_path(
    'plan-marshall', 'workflow-integration-github', 'github_pr.py'
).parent

for _dir in (_AR_SCRIPTS, _GH_SCRIPTS):
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))

import bot_registry  # noqa: E402
import review_completeness as rc  # noqa: E402

_CONTRACT_DOC = _AR_SCRIPTS.parent / 'standards' / 'bot-participation-contract.md'
_AR_SKILL = _AR_SCRIPTS.parent / 'SKILL.md'
_RC_SCRIPT = get_script_path('plan-marshall', 'automatic-review', 'review_completeness.py')

# THIS repository's tracked config, resolved through conftest's project anchor so
# the suite is cwd-independent.
_MARSHAL_JSON = PROJECT_ROOT / PLAN_DIR_NAME / 'marshal.json'
_AUTOMATIC_REVIEW_STEP_ID = 'plan-marshall:automatic-review'


def _live_step_params() -> dict:
    """Return this repository's tracked ``plan-marshall:automatic-review`` params."""
    config = json.loads(_MARSHAL_JSON.read_text(encoding='utf-8'))
    params: dict = config['plan']['phase-6-finalize']['steps'][_AUTOMATIC_REVIEW_STEP_ID]
    return params

# The three provenance values the contract declares. Sourced from the contract doc
# itself rather than restated as a convenience literal.
_PROVENANCE_STATES = ('never_asked', 'migrated', 'answered')

# The five closed NON-participation members. ``participated`` is deliberately NOT
# a member — it is the complement the taxonomy exists to distinguish from.
_NON_PARTICIPATION_MEMBERS = (
    rc.STATE_ABSENT,
    rc.STATE_IN_PROGRESS,
    rc.STATE_REFUSED_AWAITABLE,
    rc.STATE_REFUSED_HARD,
    rc.STATE_PARTICIPATED_BUT_EMPTY,
)


def _registered_bots() -> list[str]:
    """The bot population, DERIVED from the registry — never a literal list."""
    bots = bot_registry.bot_kinds()
    assert bots, 'registry must declare at least one bot for these sweeps to mean anything'
    return bots


def _configurable_defaults() -> dict[str, str]:
    """Parse ``key``/``default`` pairs out of automatic-review SKILL.md's frontmatter.

    This is the source marshall-steward seeds a fresh project's step params from,
    so it is the authoritative statement of "what a project starts with".
    """
    skill_md = _AR_SKILL.read_text(encoding='utf-8').splitlines()
    defaults: dict[str, str] = {}
    current: str | None = None
    for raw in skill_md:
        stripped = raw.strip()
        if stripped.startswith('- key:'):
            current = stripped.split(':', 1)[1].strip()
        elif stripped.startswith('default:') and current is not None:
            value = stripped.split(':', 1)[1].strip()
            defaults[current] = value.strip('"').strip("'")
            current = None
    return defaults


class TestKnobDefaults:
    """Both knobs default to EMPTY, and the emptiness is load-bearing."""

    @pytest.mark.parametrize('key', ['required_bots', 'optional_bots'])
    def test_both_knobs_default_to_the_empty_string(self, key):
        """A fresh project starts with neither list populated.

        The default MUST be the empty string rather than a seeded bot list: a
        seeded default would silently impose a participation obligation the
        operator never agreed to, and would be indistinguishable from an answer.
        Read from the ``configurable:`` block that marshall-steward actually seeds
        from, so a drift between the declared default and the seeded one fails here.
        """
        declared = _configurable_defaults()

        assert key in declared, f'{key} must be a declared configurable knob'
        assert declared[key] == '', f'{key} must default to the EMPTY string'

    def test_empty_required_bots_satisfies_the_quorum_vacuously(self, plan_context):
        """An answered-empty required list is a legitimate configured state.

        The contract calls this out explicitly: an operator who answers "none" has
        configured the system, not misconfigured it, so the quorum is vacuously
        satisfied rather than warned about.
        """
        plan_id = 'bpc-vacuous-quorum'
        plan_context.plan_dir_for(plan_id)

        result = rc.check_completeness(plan_id, [])

        assert result['participation_complete'] is True


class TestProvenanceIsThreeDistinguishableStates:
    """never_asked / migrated / answered are three states, not two."""

    def test_the_contract_declares_exactly_three_provenance_states(self):
        """All three are documented, so none can be quietly collapsed."""
        doc = _CONTRACT_DOC.read_text(encoding='utf-8')
        for state in _PROVENANCE_STATES:
            assert f'`{state}`' in doc, f'{state} must be a documented provenance state'

    def test_the_three_states_are_pairwise_distinct(self):
        """Collapsing any pair would erase a distinction the contract needs.

        ``never_asked`` vs ``answered`` is the load-bearing pair — collapsing them
        would make "the operator has not been asked yet" indistinguishable from
        "the operator deliberately chose no required bots", two states that
        warrant opposite handling. ``migrated`` is distinct from both: it was
        seeded by the legacy auto-map, not by an operator answer, so it may be
        overwritten by a later answer while an ``answered`` value may not.
        """
        for left, right in itertools.combinations(_PROVENANCE_STATES, 2):
            assert left != right

    def test_answered_empty_is_an_answer_not_an_absence(self):
        """The distinction that motivates the three states, stated normatively."""
        doc = _CONTRACT_DOC.read_text(encoding='utf-8')
        assert 'including an explicit answer of none' in doc


class TestThisRepositorysSettledConfiguration:
    """This repo's own step params, as settled by the operator."""

    def test_required_and_optional_lists_are_the_settled_two_list_split(self):
        """PR-Agent is the SOLE required bot; CodeRabbit and Sourcery are optional.

        Operator decision, on **reliability**: pr-agent is the only reviewer with
        neither a per-account review quota nor a diff-size refusal. CodeRabbit
        carries a rolling per-developer quota and Sourcery a weekly diff-character
        cap, so requiring either makes routine review-coverage gaps gate the merge
        — the failure mode that repeatedly forced merge-anyway decisions.

        Optional is NOT dropped: an optional bot is still fetched, classified and
        triaged, and its findings are acted on. It simply cannot hold the step
        open by being rate-limited. CodeRabbit earns its place there — it produced
        two real findings (one Major) that the required-bot pass missed.

        The seeded defaults are both empty by design (never-asked), so the
        operative classification lives only in each project's own marshal.json.
        Pinning it closes the enabled-bots-vs-operative drift gap: a documented
        reviewer roster that silently disagrees with the config the pipeline
        actually reads is invisible at every other surface.
        """
        params = _live_step_params()

        assert params['required_bots'] == 'pr-agent'
        assert params['optional_bots'] == 'coderabbit,sourcery'

    def test_the_retired_single_list_key_does_not_survive(self):
        """``enabled_bots`` must be gone from the operative config, not shadowed."""
        assert 'enabled_bots' not in _live_step_params()

    def test_every_configured_bot_has_a_registry_record(self):
        """A configured bot with no standards doc would resolve to nothing.

        Derives the expected population from the registry, so this catches a
        config naming a bot that was never registered AND a registry doc that was
        retired out from under the config.
        """
        params = _live_step_params()
        configured = [
            b.strip()
            for key in ('required_bots', 'optional_bots')
            for b in params[key].split(',')
            if b.strip()
        ]

        registered = _registered_bots()
        for bot in configured:
            assert bot in registered, f'{bot} is configured but has no registry record'

    def test_provenance_is_a_real_answer_not_the_never_asked_placeholder(self):
        """The value was migrated or answered — otherwise create-pr reads it as unasked."""
        provenance = _live_step_params()['bot_lists_provenance']

        assert provenance in _PROVENANCE_STATES
        assert provenance != 'never_asked'


class TestWarnButIngest:
    """An unlisted bot is warned-about and STILL ingested."""

    def test_unclassified_bot_is_warned_about_and_its_comment_is_kept(self, plan_context):
        """Classification carries CLASSIFICATION, not ADMISSION.

        Dropping an unclassified bot's comments would make a configuration
        omission silently destroy real review signal — invisible precisely when
        the operator had not yet thought about that bot. The comment is stored and
        the gap is surfaced instead.
        """
        import github_pr

        plan_id = 'bpc-warn-but-ingest'
        plan_context.plan_dir_for(plan_id)

        class _Args:
            pr_number = 900
            required_bots = 'coderabbit'
            optional_bots = ''

            def __init__(self, plan: str) -> None:
                self.plan_id = plan

        comments = [
            {
                'id': 'U1',
                'kind': 'inline',
                'author': 'sourcery-ai',
                'body': 'The retry loop can spin forever when the backoff cap is zero.',
                'path': 'src/Retry.java',
                'line': 31,
                'thread_id': 'PRRT_u1',
            },
        ]

        with (
            patch('github_pr._github.check_auth', return_value=(True, '')),
            patch('github_pr._github.fetch_pr_head_sha', return_value='sha'),
            patch('github_pr._github.fetch_pr_comments_data') as mock_fetch,
        ):
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': comments,
                'total': 1,
                'unresolved': 1,
            }
            result = github_pr.cmd_fetch_findings(_Args(plan_id))

        # Warned about...
        assert result['unclassified_bots'] == ['sourcery']
        # ...and STILL ingested. The warning is not a drop.
        assert result['count_stored'] == 1
        assert result['count_skipped_noise'] == 0


class TestFailureTaxonomyIsExhaustive:
    """Every classified bot lands in exactly one taxonomy member."""

    def test_the_contract_documents_all_five_non_participation_members(self):
        doc = _CONTRACT_DOC.read_text(encoding='utf-8')
        for member in _NON_PARTICIPATION_MEMBERS:
            assert f'`{member}`' in doc, f'{member} must be a documented taxonomy member'

    @pytest.mark.parametrize(
        'observation',
        ['none', 'in_progress', 'refused', 'participated_empty', 'participated_with_findings'],
    )
    def test_every_registered_bot_classifies_into_exactly_one_member(
        self, observation, plan_context
    ):
        """Sweep the WHOLE registered population under each observation shape.

        The population comes from ``bot_registry.bot_kinds()``, so a bot added in a
        standards doc is swept automatically. The assertion is totality and
        mutual exclusivity — never a spot-check of one bot.
        """
        # ``_`` is not admissible in a plan_id (``^[a-z][a-z0-9-]*$``), and the
        # observation labels carry them. Derive the id through the same character
        # class the real store enforces, so the sweep exercises the predicate rather
        # than tripping plan-id validation inside the findings store.
        plan_id = f'bpc-taxonomy-{observation.replace("_", "-")}'
        plan_context.plan_dir_for(plan_id)
        bots = _registered_bots()

        kwargs: dict = {}
        if observation == 'in_progress':
            kwargs['in_progress_bots'] = bots
        elif observation == 'refused':
            kwargs['refused_bots'] = bots
        elif observation.startswith('participated'):
            kwargs['participated_bots'] = {
                bot: bot_registry.participation_evidence(bot)[0] for bot in bots
            }
            if observation == 'participated_with_findings':
                import _findings_core as fc

                for bot in bots:
                    added = fc.add_finding(
                        plan_id,
                        'pr-comment',
                        title=f'{bot} finding',
                        detail='d',
                        bot_kind=bot,
                        kind='inline',
                    )
                    assert added['status'] == 'success', added
                    fc.resolve_finding(plan_id, added['hash_id'], 'fixed')

        result = rc.check_completeness(plan_id, bots, **kwargs)

        classified = [r['bot_kind'] for r in result['bot_states']]
        # Total: every bot in the population is classified.
        assert sorted(classified) == sorted(bots)
        # Exactly one: no bot is classified twice.
        assert len(classified) == len(set(classified))
        # And into a KNOWN member — nothing escapes the closed taxonomy.
        known = set(_NON_PARTICIPATION_MEMBERS) | {rc.STATE_PARTICIPATED}
        assert {r['state'] for r in result['bot_states']} <= known

    def test_every_registered_bot_declares_a_rate_limit_class_that_splits_refusals(self):
        """The refusal split is registry-driven for the WHOLE population.

        A bot whose class is neither awaitable nor a known non-awaitable value
        still resolves — fail-closed — so no bot can produce an unclassifiable
        refusal.
        """
        for bot in _registered_bots():
            assert bot_registry.rate_limit_class(bot) in (
                'awaitable_window',
                'hard_quota',
                'unknown',
            )

    def test_every_registered_bot_declares_its_participation_evidence(self):
        """A bot with no declared evidence shape can never be proven a participant.

        Fail-closed is the correct behaviour, but a REGISTERED bot silently
        landing there would be a registry gap, not a design intent — so every
        registered bot must declare at least one publish shape.
        """
        for bot in _registered_bots():
            shapes = bot_registry.participation_evidence(bot)
            assert shapes, f'{bot} declares no participation_evidence'
            for shape in shapes:
                assert shape in ('review_body', 'inline', 'issue_comment'), (bot, shape)


# =============================================================================
# Call-site population sweep — the argument-marshalling family
# =============================================================================
#
# SCOPE, STATED EXPLICITLY. This sweep covers ONE shell-marshalling family: the
# ARGUMENT-MARSHALLING family — an unquoted ``{placeholder}`` interpolated into a
# documented invocation's flag arguments, where an empty value collapses the flag
# and either steals the next token or trips an argparse rejection. It is NOT a
# repository-wide shell-marshalling audit, and it deliberately does not implement
# one.
#
# The two sibling families were INSPECTED at the same four confirmed sites and
# found INAPPLICABLE there, which is why they are stated rather than swept:
#
#   * command-chaining (``&&`` / ``;`` / ``&`` / a leading ``VAR=val``) — none of
#     the four sites chains commands; each documents exactly one invocation.
#   * bash-impersonation (``echo >``, heredocs, ``python3 -c``) — none of the four
#     sites shells out to compose content; every one is a direct executor call.
#
# A repository-wide audit of those two families is a separate, larger piece of
# work and is out of scope here.
#
# The site POPULATION is derived by scanning the marketplace tree, never
# hard-coded: a fifth call site added in a future doc is swept automatically
# instead of silently escaping. The scan is guarded against vacuity — an empty
# sub-population FAILS rather than passing quietly.

_MARKETPLACE_DOCS = PROJECT_ROOT / 'marketplace' / 'bundles'

#: The list flags whose interpolated placeholders must be quoted, derived from
#: the live ``check`` parser so a sixth flag is swept without an edit here. The
#: ``review_completeness`` family may carry all of them; the ``fetch_findings``
#: family declares only the first two.
_ALL_LIST_FLAGS = tuple(flag for flag, _dest in derive_bot_flags(_RC_SCRIPT, 'check'))

_FAMILY_A = 'review_completeness check'
_FAMILY_B = 'github_pr fetch_findings'

#: ``(family, doc-suffix, section-substring, expected list-flag count)`` for the
#: four CONFIRMED call sites. The counts differ per site and are asserted per
#: site: the participation guard passes all five, the pre-merge barrier's
#: Predicate 2 passes four (it never observes an in-progress bot of its own), and
#: both producer sites pass the two classification flags.
_CONFIRMED_SITES = (
    pytest.param(
        _FAMILY_A,
        'automatic-review/SKILL.md',
        'Step-done participation guard',
        5,
        id='family-a-step-done-participation-guard',
    ),
    pytest.param(
        _FAMILY_A,
        'phase-6-finalize/standards/branch-cleanup.md',
        'Predicate 2',
        4,
        id='family-a-premerge-barrier-predicate-2',
    ),
    pytest.param(
        _FAMILY_B,
        'automatic-review/SKILL.md',
        'Producer: FIND',
        2,
        id='family-b-producer-find',
    ),
    pytest.param(
        _FAMILY_B,
        'phase-6-finalize/standards/branch-cleanup.md',
        'Re-fetch bot comments against the current HEAD',
        2,
        id='family-b-premerge-barrier-refetch',
    ),
)

#: Matches a list flag and the token that follows it inside a fenced command. The
#: alternation is built from the SAME parser-derived tuple as ``_ALL_LIST_FLAGS``
#: rather than restated as a second literal — a sixth flag reaches the quoting
#: scan automatically. Longest-first ordering keeps a flag that is a prefix of
#: another from shadowing it.
_FLAG_VALUE = re.compile(
    '(?P<flag>'
    + '|'.join(re.escape(flag) for flag in sorted(_ALL_LIST_FLAGS, key=len, reverse=True))
    + r')(?:[ \t]+(?P<value>\S+))?'
)


def _scan_invocation_sites() -> list[tuple[str, str, str, str]]:
    """Return ``(family, doc, section, command)`` for every documented invocation.

    Walks every markdown file under ``marketplace/bundles`` and collects each
    fenced code block that invokes one of the two families, tagging it with the
    nearest preceding heading so a site is addressable BY NAME rather than by
    line number. Backslash continuations are folded so a multi-line invocation is
    one command string.
    """
    sites: list[tuple[str, str, str, str]] = []
    for path in sorted(_MARKETPLACE_DOCS.rglob('*.md')):
        heading = ''
        in_fence = False
        block: list[str] = []
        block_heading = ''
        for raw in path.read_text(encoding='utf-8').splitlines():
            if raw.lstrip().startswith('```'):
                if in_fence:
                    command = re.sub(r'\\\n\s*', ' ', '\n'.join(block))
                    family = _classify_invocation(command)
                    if family:
                        rel = str(path.relative_to(_MARKETPLACE_DOCS))
                        sites.append((family, rel, block_heading, command))
                    block = []
                    in_fence = False
                else:
                    in_fence = True
                    block_heading = heading
                continue
            if in_fence:
                block.append(raw)
            elif raw.startswith('#'):
                heading = raw.lstrip('#').strip()
    return sites


def _classify_invocation(command: str) -> str:
    """Return the invocation family a fenced command belongs to, or ``''``."""
    if 'automatic-review:review_completeness' in command and re.search(r'\bcheck\b', command):
        return _FAMILY_A
    if 'workflow-integration-github:github_pr' in command and 'fetch_findings' in command:
        return _FAMILY_B
    return ''


_INVOCATION_SITES = _scan_invocation_sites()


def _site_id(site: tuple[str, str, str, str]) -> str:
    """Human-readable, stable nodeid fragment naming the site.

    The id carries the family, the owning document and the section heading, so a
    failure names WHICH call site regressed without opening the test source.
    Punctuation is normalised to hyphens so the id stays a single readable token
    in a pytest nodeid.
    """
    family, doc, section, _command = site
    raw = f'{family}--{doc}--{section}'
    return re.sub(r'[^A-Za-z0-9]+', '-', raw).strip('-').lower()


def _find_confirmed(family: str, doc_suffix: str, section_substring: str) -> tuple:
    """Return the single scanned site matching a confirmed-site descriptor."""
    matches = [
        site
        for site in _INVOCATION_SITES
        if site[0] == family and site[1].endswith(doc_suffix) and section_substring in site[2]
    ]
    assert len(matches) == 1, (
        f'expected exactly one {family} site in {doc_suffix} under a heading containing '
        f'{section_substring!r}; found {[_site_id(m) for m in matches]}'
    )
    return matches[0]


def _interpolated_flags(command: str) -> list[tuple[str, str]]:
    """Return ``(flag, value)`` pairs whose value is a ``{placeholder}`` interpolation."""
    return [
        (match.group('flag'), match.group('value'))
        for match in _FLAG_VALUE.finditer(command)
        if match.group('value') and '{' in match.group('value')
    ]


class TestCallSitePopulation:
    """Every documented call site quotes its interpolated list-flag placeholders."""

    @pytest.mark.parametrize('family', [_FAMILY_A, _FAMILY_B])
    def test_each_family_is_a_non_empty_sub_population(self, family):
        """A scan that silently matched nothing must FAIL, not pass vacuously.

        The two families are asserted SEPARATELY: a scan that found only
        ``fetch_findings`` sites would otherwise report a healthy population while
        covering none of the predicate's own call sites, which is exactly the
        volume-read-as-coverage failure a single aggregate count hides.
        """
        members = [site for site in _INVOCATION_SITES if site[0] == family]

        assert members, f'no {family} call site was discovered — the scan is vacuous'

    def test_the_scan_discovered_at_least_the_four_confirmed_sites(self):
        """The per-site sweep below is parametrized over a NON-EMPTY population.

        A parametrize over an empty list produces a skip, not a failure, so the
        per-site sweep could report clean while covering nothing. This asserts the
        population's floor directly: the four confirmed sites are known to exist,
        so anything smaller means the scanner stopped matching.
        """
        assert len(_INVOCATION_SITES) >= len(_CONFIRMED_SITES)

    @pytest.mark.parametrize(
        ('family', 'doc_suffix', 'section_substring', 'expected_flag_count'),
        _CONFIRMED_SITES,
    )
    def test_confirmed_site_carries_its_own_flag_set_fully_quoted(
        self, family, doc_suffix, section_substring, expected_flag_count
    ):
        """Each confirmed site is asserted INDIVIDUALLY and BY NAME.

        Never one aggregate "all sites pass" assertion: an aggregate cannot say
        WHICH site regressed, and a site that stopped being discovered at all
        would silently shrink the aggregate rather than fail. The expected flag
        count is per-site, because the sites genuinely differ — the pre-merge
        barrier passes four flags, not the participation guard's five.
        """
        _family, doc, section, command = _find_confirmed(family, doc_suffix, section_substring)

        flags = _interpolated_flags(command)
        assert len(flags) == expected_flag_count, (
            f'{doc} / {section}: expected {expected_flag_count} interpolated list flags, '
            f'found {[f for f, _ in flags]}'
        )
        for flag, value in flags:
            assert value.startswith('"') and value.endswith('"'), (
                f'{doc} / {section}: {flag} interpolates {value} unquoted — an empty value '
                'collapses the flag and steals the next token or trips argparse exit 2'
            )

    @pytest.mark.parametrize('site', _INVOCATION_SITES, ids=_site_id)
    def test_every_discovered_site_quotes_its_interpolated_flags(self, site):
        """The population-wide invariant, asserted per member rather than in aggregate.

        Covers the confirmed four AND any site a future doc adds, so a fifth call
        site inherits the guard without a registry edit here.
        """
        _family, doc, section, command = site

        for flag, value in _interpolated_flags(command):
            assert value.startswith('"') and value.endswith('"'), (
                f'{doc} / {section}: {flag} interpolates {value} unquoted'
            )


# =============================================================================
# The crashed-gate-records-a-pass regression (#1063), end to end for both families
# =============================================================================

_GH_SCRIPT = get_script_path('plan-marshall', 'workflow-integration-github', 'github_pr.py')

_BRANCH_CLEANUP_DOC = (
    _AR_SCRIPTS.parent.parent / 'phase-6-finalize' / 'standards' / 'branch-cleanup.md'
)
_GH_SKILL = _GH_SCRIPT.parent.parent / 'SKILL.md'


class TestCrashedGateNeverRecordsAPass:
    """A zero-participation invocation must neither crash nor be recorded as a pass."""

    def test_family_a_zero_participation_does_not_exit_2(self, plan_context):
        """The predicate survives the collapsed shape instead of rejecting it.

        Driven through the constructed-argv subprocess runner — the boundary where
        the pre-fix parser actually failed.
        """
        plan_id = 'bpc-1063-family-a'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            _RC_SCRIPT,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            '--optional-bots',
            '--participated-bots',
            '--in-progress-bots',
            '--refused-bots',
        )

        assert result.returncode != 2, result.stderr
        assert 'expected one argument' not in result.stderr

    def test_family_a_zero_participation_is_not_recorded_as_a_pass(self, plan_context):
        """Surviving the parse must not buy a pass for an unreviewed diff.

        With a real required set and NO observation of any kind, the verdict is
        ``false`` and both required bots are named unproven. This is the half of
        the fix that stops the relaxation becoming the defect it replaced.
        """
        plan_id = 'bpc-1063-family-a-verdict'
        plan_context.plan_dir_for(plan_id)

        result = run_script(
            _RC_SCRIPT,
            'check',
            '--plan-id',
            plan_id,
            '--required-bots',
            'coderabbit,pr-agent',
            '--optional-bots',
            '--participated-bots',
            '--in-progress-bots',
            '--refused-bots',
        )

        assert result.success, result.stderr
        assert 'participation_complete: false' in result.stdout
        assert 'unproven_bots[2]' in result.stdout

    def test_family_b_zero_participation_does_not_exit_2(self):
        """The producer survives the collapsed shape too — both families, not one.

        ``PATH`` is emptied so ``gh`` is unresolvable and the run cannot reach the
        network: the process clears argparse and then fails at the provider
        boundary, which is precisely the boundary under test.
        """
        result = run_script(
            _GH_SCRIPT,
            'fetch_findings',
            '--pr-number',
            '1',
            '--plan-id',
            'bpc-1063-family-b',
            '--required-bots',
            '--optional-bots',
            env_overrides={'PATH': ''},
        )

        assert result.returncode != 2, result.stderr
        assert 'expected one argument' not in result.stderr

    def test_automatic_review_doc_carries_an_unknown_branch(self):
        """The consuming doc routes a crashed predicate to UNKNOWN, never to false."""
        doc = _AR_SKILL.read_text(encoding='utf-8')

        assert 'UNKNOWN verdict' in doc
        assert 'no `participation_complete` field' in doc
        assert '--outcome loop_back' in doc

    def test_automatic_review_doc_excludes_the_force_done_hatch_from_unknown(self):
        """The escape hatch presupposes a verdict, so it cannot apply to UNKNOWN.

        Without this exclusion the hatch would let an operator force past a gate
        that named no blocking bot and no state — a force-done with nothing to
        weigh, which is a pass in all but name.
        """
        doc = _AR_SKILL.read_text(encoding='utf-8')

        assert 'UNAVAILABLE for an UNKNOWN' in doc

    def test_branch_cleanup_doc_carries_an_unknown_branch_for_both_calls(self):
        """The barrier's UNKNOWN branch covers the predicate AND its upstream input.

        Predicate 2 consumes ``participated_bots`` / ``refused_bots`` from the
        ``fetch_findings`` call above it, so a non-zero exit THERE leaves the
        predicate with absent inputs. Feeding an empty participation set to a
        fail-closed predicate would manufacture a verdict nobody computed, so the
        barrier must refuse to evaluate Predicate 2 at all.
        """
        doc = _BRANCH_CLEANUP_DOC.read_text(encoding='utf-8')

        assert 'UNKNOWN — the predicate itself failed' in doc
        assert 'UNKNOWN — the re-fetch itself failed' in doc
        assert 'NOT evaluating Predicate 2' in doc
        assert '{barrier_mode}' in doc


# =============================================================================
# Advertised-form agreement — the documented shape matches the live argparse
# =============================================================================

#: Matches an optional-value flag rendering: ``[--flag [VALUE]]`` — the nested
#: bracket pair argparse itself emits for ``nargs='?'``.
def _optional_value_form(flag: str) -> re.Pattern:
    return re.compile(re.escape(f'[{flag} ') + r'\[[^\]]+\]\]')


def _help_text(script_path, *argv: str) -> str:
    """Return a subcommand's live argparse usage text."""
    result = run_script(script_path, *argv, '--help')
    assert result.success, result.stderr
    usage: str = result.stdout
    return usage


class TestAdvertisedFormsAgreeWithArgparse:
    """Each advertised form states the same optionality the live parser implements.

    An advertised form that lags its parser is the drift that made the defect
    invisible: the docs showed a mandatory-value flag while the callers passed an
    empty one, and nothing compared the two.
    """

    @pytest.mark.parametrize('flag', _ALL_LIST_FLAGS)
    def test_review_completeness_argparse_declares_optional_values(self, flag):
        """The live parser renders all five list flags with an optional value."""
        usage = _help_text(_RC_SCRIPT, 'check')

        assert _optional_value_form(flag).search(usage), f'{flag} usage: {usage}'

    @pytest.mark.parametrize('flag', ('--required-bots', '--optional-bots'))
    def test_github_pr_argparse_declares_optional_values(self, flag):
        """The producer's two classification flags likewise take an optional value."""
        usage = _help_text(_GH_SCRIPT, 'fetch_findings')

        assert _optional_value_form(flag).search(usage), f'{flag} usage: {usage}'

    @pytest.mark.parametrize('flag', _ALL_LIST_FLAGS)
    def test_automatic_review_canonical_block_matches_argparse(self, flag):
        """Advertised form 1 — the ``review_completeness — check`` canonical block."""
        doc = _AR_SKILL.read_text(encoding='utf-8')

        assert _optional_value_form(flag).search(doc), (
            f'{flag} must be advertised with an optional value in the canonical block'
        )

    @pytest.mark.parametrize('flag', ('--required-bots', '--optional-bots'))
    def test_github_canonical_block_matches_argparse(self, flag):
        """Advertised form 2 — the ``github_pr fetch_findings`` canonical block."""
        doc = _GH_SKILL.read_text(encoding='utf-8')

        assert _optional_value_form(flag).search(doc), (
            f'{flag} must be advertised with an optional value in the canonical block'
        )

    @pytest.mark.parametrize('flag', _ALL_LIST_FLAGS)
    def test_module_docstring_usage_line_matches_argparse(self, flag):
        """Advertised form 3 — the ``Usage:`` line in the script's own docstring."""
        docstring = rc.__doc__ or ''

        assert _optional_value_form(flag).search(docstring), (
            f'{flag} must be advertised with an optional value on the Usage: line'
        )
