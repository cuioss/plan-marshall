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
* the taxonomy's doc/code closure holds in BOTH directions — no classifier member
  is undocumented, no documented member is unproducible — and the contract's own
  closure-count sentence agrees with the derived member count;
* every DOCUMENTED call site of the two invocation families quotes its
  interpolated list-flag placeholders, over a site population derived by scanning
  the marketplace tree;
* every DOCUMENTED call site additionally resolves to a recorded EVIDENCE CLASS —
  the ``reads`` axis of the participation-site population's own expectation record
  for the script the site's executor notation names — so a call site that invokes a
  participation script ``test_participation_site_population.py`` holds no record for
  fails here instead of escaping both populations;
* a crashed participation gate is an UNKNOWN verdict at both families and at both
  consuming documents — never a recorded pass;
* each advertised invocation form agrees with its live argparse surface on the
  optionality of every list flag;
* the FULL declared optional-flag surface of ``review_completeness check`` is
  classified — every long option the live parser declares is assigned a coverage
  arm, so a flag whose shape the ``--*-bots`` family pattern cannot match (the
  ``store_true`` ``--not-triggered``) cannot escape every sweep unnoticed;
* every ``N blocking members`` count stated anywhere in the marketplace tree
  agrees with the blocking subset derived from ``_UNPROVEN_STATES`` — which is
  strictly smaller than the taxonomy, so reaching for the taxonomy's size there
  is the specific error guarded.

Every set-guarding assertion derives its population from the registry (for bots),
from a repository scan (for call sites), from the live argparse surface (for
flags), or from ``review_completeness``'s own ``STATE_`` constants (for taxonomy
members) rather than a hard-coded literal list, so a bot added or retired in a
standards doc, a fifth call site added in a future doc, a further flag added to the
parser, or a new classifier state is covered here automatically instead of silently
escaping the sweep. The taxonomy tuple keeps its explicit spelling — its order and
its ``len`` are load-bearing — but is asserted equal to the derived set at import,
which is the same guarantee by a different route.
Each sub-population is additionally guarded against vacuity: a derivation that
matched nothing FAILS rather than reporting a healthy aggregate over an empty set.
"""

from __future__ import annotations

import itertools
import json
import re
import sys
from unittest.mock import patch

import pytest

from _bot_flag_derivation import derive_bot_flags, derive_declared_flags
from conftest import PLAN_DIR_NAME, PROJECT_ROOT, get_script_path, run_script

# The EVIDENCE-CLASS vocabulary and its per-script records are OWNED by the
# participation-site population module and read from it here rather than restated.
# A second copy of either would be the duplicate-definition failure that population
# exists to forbid, and the call-site sweep below would then be able to report a
# class the population itself does not recognise.
from test_participation_site_population import READS_VOCABULARY, SITE_EXPECTATIONS

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

# The closed NON-participation members. ``participated`` is deliberately NOT a
# member — it is the complement the taxonomy exists to distinguish from.
#
# The last two are the REFINEMENTS of ``absent``, listed after the mutually
# independent observations because that is what they are: each says the bot
# published nothing, and each carries a remedy opposite to ``absent``'s escalation
# (re-trigger the stale review / trigger the review at all). ``declined`` sits among
# the independent observations: like a refusal, it says the bot engaged and would
# not review this commit, so it is not a refinement of ``absent``. Of the FOUR refusal
# members, three (``refused_awaitable`` / ``refused_hard`` / ``refused_unknown``) are the
# DEFAULT mapping of the bot's three-valued ``rate_limit_class`` — a default, not a
# bijection, because TWO per-refusal observations displace it. ``refused_structural``
# is one: a refusal whose observed CAUSE is a diff-size ceiling. The other reaches
# ``refused_unknown``: a refusal NO arm of the recognition stack could READ, which
# resolves there whatever the bot's declared class says, because nothing about an
# unparsed notice is known. Both overrides are checked BEFORE the class, because a
# class declared per BOT cannot separate observations made per REFUSAL. This tuple's
# LENGTH is load-bearing — the closure-count
# check below reads the contract's own prose count back as an integer and compares it
# against ``len`` here, which is what stops a member reaching the classifier and the
# table while the prose still claims fewer.
_NON_PARTICIPATION_MEMBERS = (
    rc.STATE_ABSENT,
    rc.STATE_IN_PROGRESS,
    rc.STATE_REFUSED_AWAITABLE,
    rc.STATE_REFUSED_HARD,
    rc.STATE_REFUSED_UNKNOWN,
    rc.STATE_REFUSED_STRUCTURAL,
    rc.STATE_PARTICIPATED_BUT_EMPTY,
    rc.STATE_DECLINED,
    rc.STATE_PARTICIPATED_STALE,
    rc.STATE_NOT_TRIGGERED,
)

# ...and the DERIVED population it must equal. The tuple above is retained for its
# order and its ``len``, both of which are load-bearing (see the comment above), so
# the derivation is asserted against it rather than replacing it.
#
# Without this equality the tuple is a hand-maintained mirror and the file breaks
# the derived-population rule its own docstring declares. Worse, the tuple is the
# SHARED PIVOT of two checks — the documented-set comparison and the closure-count
# comparison both read it — so a member that reached only the classifier would move
# both sides of the count together and every check would stay green over a set that
# is missing it. Asserting here makes that member fail at IMPORT, once, loudly.
#
# ``STATE_PARTICIPATED`` is the sole intended exclusion: it is the taxonomy's
# COMPLEMENT (the bot delivered a usable review), not a further member of it — see
# the module comment at ``review_completeness.py`` above ``STATE_ABSENT``. The
# cardinality is deliberately NOT spelled here: an ordinal written into a comment
# is a second statement of the taxonomy's size and the one that goes stale in
# silence, still reading as a claim about a set that has moved. The only place this
# module states the count is the failure message of the equality assertion below,
# which INTERPOLATES it from the tuple and therefore cannot drift from it. The
# ``vars(rc)`` sweep cannot pick up a ``STATE_``-prefixed name imported from
# elsewhere: ``rc`` imports only ``argparse``, ``sys``, ``bot_registry``, and
# ``query_findings``, none of which is ``STATE_``-prefixed, and the ``str`` filter
# below additionally excludes any non-constant binding a future import might add.
_DERIVED_NON_PARTICIPATION = frozenset(
    value
    for name, value in vars(rc).items()
    if name.startswith('STATE_') and name != 'STATE_PARTICIPATED' and isinstance(value, str)
)

assert _DERIVED_NON_PARTICIPATION, (
    'no STATE_ constant was derived from review_completeness — the taxonomy '
    'population is vacuous and every sweep over it would pass over an empty set'
)

assert frozenset(_NON_PARTICIPATION_MEMBERS) == _DERIVED_NON_PARTICIPATION, (
    f'the _NON_PARTICIPATION_MEMBERS tuple ({len(_NON_PARTICIPATION_MEMBERS)} members '
    f'spelled) has drifted from review_completeness ({len(_DERIVED_NON_PARTICIPATION)} '
    f'derived): '
    f'only in the tuple={sorted(frozenset(_NON_PARTICIPATION_MEMBERS) - _DERIVED_NON_PARTICIPATION)}, '
    f'only in the module={sorted(_DERIVED_NON_PARTICIPATION - frozenset(_NON_PARTICIPATION_MEMBERS))}. '
    f'{rc.STATE_PARTICIPATED!r} is the sole intended exclusion — the COMPLEMENT of the '
    f'{len(_DERIVED_NON_PARTICIPATION)}-member non-participation taxonomy, never member '
    f'{len(_DERIVED_NON_PARTICIPATION) + 1} of it'
)

assert len(_NON_PARTICIPATION_MEMBERS) == len(_DERIVED_NON_PARTICIPATION), (
    'the _NON_PARTICIPATION_MEMBERS tuple carries a duplicate — its len is '
    'load-bearing for the closure-count check, so a repeated member would '
    'overstate the taxonomy while the set equality above still held'
)

#: A member row of the failure-taxonomy table: the backticked identifier that opens
#: the row's leading cell. Anchored at the line start so only table rows match.
_MEMBER_ROW = re.compile(r'^\|\s*`(?P<member>[a-z_]+)`\s*\|', re.MULTILINE)

#: The contract's own closure-count sentence. Whitespace is collapsed before
#: matching, because the sentence wraps across a line break in the source.
_CLOSURE_COUNT = re.compile(r'classified into exactly one of (?P<count>\w+) members')

#: A consumer-side claim about how many taxonomy members BLOCK. The blocking
#: subset is ``_UNPROVEN_STATES``, which is strictly smaller than the taxonomy —
#: ``participated_but_empty`` is a member that never blocks — so a consumer doc
#: that reaches for the taxonomy's size here overstates the set it is describing.
_BLOCKING_COUNT = re.compile(r'(?P<count>\w+) blocking members')

#: Cardinal number words indexed by the value they name. The contract states its
#: closure count in PROSE, so reading it back has to cross the word/integer
#: boundary rather than grep for a digit that is not there.
_NUMBER_WORDS = (
    'zero',
    'one',
    'two',
    'three',
    'four',
    'five',
    'six',
    'seven',
    'eight',
    'nine',
    'ten',
    'eleven',
    'twelve',
)


def _failure_taxonomy_section() -> str:
    """Return the contract's ``## Failure taxonomy`` section body.

    Scoped to that ONE section deliberately: the document carries several other
    tables (provenance, publish shapes, marker surfaces, consumers) whose leading
    cell is also a backticked identifier, and a whole-document scan would admit
    those as phantom taxonomy members — inflating the documented set until the
    doc-to-code direction below could never fail.
    """
    doc = _CONTRACT_DOC.read_text(encoding='utf-8')
    section = re.search(
        r'^## Failure taxonomy$(?P<body>.*?)(?=^## )', doc, re.DOTALL | re.MULTILINE
    )
    assert section, 'the contract must carry a "## Failure taxonomy" section'
    return section.group('body')


def _documented_members() -> tuple[str, ...]:
    """The taxonomy members the CONTRACT documents, derived by parsing its table."""
    members = tuple(dict.fromkeys(_MEMBER_ROW.findall(_failure_taxonomy_section())))
    assert members, (
        'the failure-taxonomy table parsed to zero members — the scan is vacuous and '
        'the doc-to-code direction would pass over an empty set'
    )
    return members


def _stated_blocking_counts(text: str) -> tuple[int, ...]:
    """Every blocking-member COUNT ``text`` states, as integers.

    A ``N blocking members`` phrase whose ``N`` is a qualifier rather than a
    number ("the", "these") states no count and is skipped — writing no number
    is the preferred shape, so it is not a claim this check constrains. Both
    spellings of a real count are read: the cardinal word and the digit.
    """
    counts: list[int] = []
    for match in _BLOCKING_COUNT.finditer(' '.join(text.split())):
        word = match.group('count')
        if word in _NUMBER_WORDS:
            counts.append(_NUMBER_WORDS.index(word))
        elif word.isdigit():
            counts.append(int(word))
    return tuple(counts)


def _blocking_count_sites() -> tuple[tuple[str, int], ...]:
    """Return ``(relative_doc, stated_count)`` for every blocking-count claim.

    The population is DERIVED by walking the marketplace tree — the same shape
    ``_scan_invocation_sites()`` uses — rather than named in a literal doc list.
    A literal would be complete only until the next doc states a count, which is
    exactly the silent-escape this suite's population-derivation rule exists to
    prevent. Deriving it also reaches the contract doc itself, whose own
    blocking-subset prose is otherwise guarded by nothing.
    """
    sites: list[tuple[str, int]] = []
    for path in sorted(_MARKETPLACE_DOCS.rglob('*.md')):
        for stated in _stated_blocking_counts(path.read_text(encoding='utf-8')):
            sites.append((str(path.relative_to(_MARKETPLACE_DOCS)), stated))
    return tuple(sites)


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

    def test_the_contract_documents_every_non_participation_member(self):
        """Direction one — CODE to DOC: no classifier member is undocumented.

        The identifier names no count on purpose. A count in the name is a second
        place the cardinality is stated, and the one that goes stale silently: it
        keeps asserting truthfully while reading as a claim about a set size that
        has moved. The count belongs in the closure check below, where it is
        derived rather than spelled.
        """
        doc = _CONTRACT_DOC.read_text(encoding='utf-8')
        for member in _NON_PARTICIPATION_MEMBERS:
            assert f'`{member}`' in doc, f'{member} must be a documented taxonomy member'

    def test_every_documented_member_is_one_the_classifier_can_produce(self):
        """Direction two — DOC to CODE, which the direction above cannot see.

        A subset check in one direction only is satisfied by a documented set that
        has grown BEYOND the classifier: a member added to the contract table that
        ``classify_bot`` can never assign would leave the code-to-doc sweep green
        while the contract promised a state no consumer will ever observe. Closing
        the pair makes the two surfaces equal rather than merely overlapping.
        """
        documented = set(_documented_members())
        classifiable = set(_NON_PARTICIPATION_MEMBERS)

        assert documented <= classifiable, (
            f'the contract documents {sorted(documented - classifiable)} which the '
            f'classifier cannot produce — a documented member no consumer can observe'
        )

    def test_the_contracts_closure_count_agrees_with_the_derived_member_count(self):
        """The contract's prose count is checked against the derived cardinality.

        The two subset directions above make the table and the classifier agree,
        but neither reads the CLOSURE SENTENCE that tells a human how many members
        to expect. A widened taxonomy whose prose still says "five" understates the
        set at the one place a reader looks first, and nothing else in this suite
        would notice.
        """
        collapsed = ' '.join(_failure_taxonomy_section().split())
        match = _CLOSURE_COUNT.search(collapsed)
        assert match, 'the failure taxonomy must state its closure count in prose'

        word = match.group('count')
        assert word in _NUMBER_WORDS, (
            f'the closure count reads {word!r}, which is not a cardinal number word '
            f'this check can compare — spell the count as a word'
        )
        assert _NUMBER_WORDS.index(word) == len(_NON_PARTICIPATION_MEMBERS), (
            f'the contract closes the taxonomy at {word} members but '
            f'{len(_NON_PARTICIPATION_MEMBERS)} are derived: '
            f'{sorted(_NON_PARTICIPATION_MEMBERS)}'
        )

    def test_stated_blocking_counts_agree_with_the_derived_blocking_subset(self):
        """Every ``N blocking members`` claim in the tree is checked against code.

        The closure-count check above reads the CONTRACT doc's one closure
        sentence, so a count restated anywhere else is outside its reach. That
        gap is not hypothetical: the same wrong count appeared at two consumer
        sites, one of them contradicting its own enumeration three lines above,
        with nothing in this suite able to see either.

        The blocking subset is ``_UNPROVEN_STATES``, which is strictly smaller
        than the taxonomy — ``participated_but_empty`` is a member that never
        blocks — so reaching for the taxonomy's size here is the specific error
        guarded. Stating no count at all is the preferred shape, so a zero-match
        tree is a legitimate pass; the population guard below is what keeps that
        pass honest rather than vacuous.
        """
        blocking = len(rc._UNPROVEN_STATES)
        assert 0 < blocking < len(_NON_PARTICIPATION_MEMBERS), (
            f'the blocking subset ({blocking}) must be a non-empty PROPER subset of '
            f'the taxonomy ({len(_NON_PARTICIPATION_MEMBERS)}) — otherwise this check '
            f'cannot distinguish the two counts it exists to keep apart'
        )

        # The scanned population is the marketplace doc tree, NOT the match set:
        # zero matches is the preferred state, so the denominator that makes a
        # zero-match pass meaningful is how many docs were actually read.
        scanned = sum(1 for _ in _MARKETPLACE_DOCS.rglob('*.md'))
        assert scanned > 0, (
            f'{_MARKETPLACE_DOCS} yielded no markdown — the sweep is vacuous and a '
            f'clean result would mean nothing'
        )

        for doc, stated in _blocking_count_sites():
            assert stated == blocking, (
                f'{doc} claims {stated} blocking members but {blocking} are derived '
                f'from _UNPROVEN_STATES: {sorted(rc._UNPROVEN_STATES)}. Note the '
                f'taxonomy has {len(_NON_PARTICIPATION_MEMBERS)} members — the '
                f'blocking subset excludes the never-blocking ones'
            )

    def test_the_blocking_count_extractor_reads_real_counts_and_skips_qualifiers(self):
        """Positive and negative controls for the extractor the scan above uses.

        The scan passes over a doc set that currently states no count, so on its
        own it cannot show it would catch anything. These controls pin the
        discriminator directly: the exact wording of the two defects that
        reached review is read back as a count, the corrected wording is not,
        and the digit spelling is covered too.
        """
        taxonomy_size = len(_NON_PARTICIPATION_MEMBERS)

        # Positive: the two shipped defects, verbatim. Both stated the TAXONOMY
        # size where the BLOCKING subset was meant, which is the error itself. The
        # count word tracks the derived taxonomy size, so these read the current
        # cardinality rather than a frozen literal that would rot on the next member.
        assert _stated_blocking_counts(
            f'because two of the {_NUMBER_WORDS[taxonomy_size]} blocking members name a different remedy'
        ) == (taxonomy_size,)
        assert _stated_blocking_counts(f'{taxonomy_size} blocking members') == (taxonomy_size,)

        # Negative: the corrected wording states no count and must not be read
        # as one — otherwise the fix would itself trip the guard.
        assert _stated_blocking_counts(
            'because two of the blocking members name a different remedy'
        ) == ()
        assert _stated_blocking_counts('the blocking members enumerated above') == ()

        # And the defect the controls describe is genuinely a defect: the
        # taxonomy size is NOT the blocking count.
        assert taxonomy_size != len(rc._UNPROVEN_STATES)

    @pytest.mark.parametrize(
        'observation',
        [
            'none',
            'in_progress',
            'refused',
            'participated_empty',
            'participated_with_findings',
            'participated_stale',
            'declined',
            'not_triggered',
        ],
    )
    def test_every_registered_bot_classifies_into_exactly_one_member(
        self, observation, plan_context
    ):
        """Sweep the WHOLE registered population under each observation shape.

        The population comes from ``bot_registry.bot_kinds()``, so a bot added in a
        standards doc is swept automatically. The assertion is totality and
        mutual exclusivity — never a spot-check of one bot.

        The two widened shapes are swept here rather than spot-checked for the same
        reason as the original five: the property being pinned is that the taxonomy
        stays TOTAL and mutually exclusive over the whole bot population, and a
        member exercised against one bot proves neither.
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
        elif observation == 'participated_stale':
            # Matched by EXACT equality, and placed ahead of the prefix branch
            # below on purpose: ``participated_stale`` also starts with
            # ``participated``, so the prefix test would swallow it and feed the
            # shape through the proven-participation path instead — where every bot
            # resolves ``participated_but_empty`` and the widened member would
            # never be exercised while the case still reported green.
            kwargs['stale_participation_bots'] = bots
        elif observation == 'declined':
            kwargs['declined_bots'] = bots
        elif observation == 'not_triggered':
            # PR-wide rather than per-bot: a single bool, because the condition
            # ("no pull_request-event run exists for this PR") holds for every bot
            # at once. There is no observation set to key by bot here.
            kwargs['not_triggered'] = True
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
#: the live ``check`` parser so a newly added flag is swept without an edit here.
#: The ``review_completeness`` family may carry all of them; the ``fetch_findings``
#: family declares only the first two. The derivation matches the ``--*-bots``
#: family only, so the ``store_true`` ``--not-triggered`` is correctly absent: it
#: has no value to quote.
_ALL_LIST_FLAGS = tuple(flag for flag, _dest in derive_bot_flags(_RC_SCRIPT, 'check'))

#: The FULL declared optional-flag surface of ``review_completeness check``, derived
#: from the same live parser by the wider entry point. This is the POPULATION the
#: coverage ledger below is asserted total over, and the reason a valueless flag can
#: no longer escape every sweep: ``_ALL_LIST_FLAGS`` comes from a ``--*-bots``
#: family pattern that structurally cannot match ``--not-triggered``, so a
#: consumer measuring its coverage against the family alone measured it against a
#: population the boolean was never in.
_ALL_DECLARED_FLAGS = derive_declared_flags(_RC_SCRIPT, 'check')

#: The declared flags OUTSIDE the ``--*-bots`` family, each mapped to the arm that
#: covers it. Together with ``_ALL_LIST_FLAGS`` this must exhaust
#: ``_ALL_DECLARED_FLAGS``; the equality is what turns a newly declared flag into a
#: FAILURE demanding classification rather than a silent coverage hole. A flag of a
#: shape no existing derivation matches therefore cannot be added without someone
#: naming where it is covered.
_NON_LIST_FLAG_COVERAGE = {
    '--plan-id': (
        'the required findings-store selector — exercised at the constructed-argv '
        'boundary by every check invocation in TestCrashedGateNeverRecordsAPass'
    ),
    '--not-triggered': (
        'the store_true PR-wide observable — the member it assigns is swept over the '
        'whole bot population by the not_triggered shape of the taxonomy parametrize, '
        'and its CLI boundary is owned by test_review_completeness.py'
    ),
    '--triage-ran': (
        'the store_true verdict modifier — owned by test_review_completeness.py, '
        "whose triage-state matrix pins both of the predicate's two modes"
    ),
    '--refused-causes': (
        'the pair-form CAUSE overlay (bot_kind:cause) — a --*-causes flag OUTSIDE the '
        '--*-bots family. STATE-DETERMINING for a size cause (it resolves the bot to '
        'refused_structural whatever its rate_limit_class says) and advisory for every '
        'other; it gates nothing either way. Its CLI boundary, the refusal_causes[] '
        'output, and the malformed-shape rejection are owned by '
        'test_review_completeness.py, and the structural member it can assign is swept '
        'over the whole bot population by the taxonomy parametrize'
    ),
    '--refusal-size-caps': (
        'the pair-form CAP overlay (bot_kind:cap) — a --*-caps flag OUTSIDE the '
        '--*-bots family, carrying the ceiling a structural refusal stated so the gap '
        'is auditable against the measured diff size. Purely reported: it assigns no '
        'member and gates nothing. Its CLI boundary, the cap column in refusal_causes[], '
        'and the unknown-cap rendering are owned by test_structural_refusal.py'
    ),
    '--measured-diff-size': (
        'the scalar PR-wide diff measurement — neither a --*-bots flag nor a pair-form '
        'overlay, because it is a property of the PR rather than of a bot. It is the '
        'other half of an auditable coverage gap (a cap without the size that hit it is '
        'a claim taken on trust); it assigns no member and gates nothing. Its CLI '
        'boundary and the unknown-when-unmeasured rendering are owned by '
        'test_structural_refusal.py'
    ),
}

_FAMILY_A = 'review_completeness check'
_FAMILY_B = 'github_pr fetch_findings'

#: ``(family, doc-suffix, section-substring, expected list-flag count)`` for the
#: four CONFIRMED call sites. Each count is stated ONCE, here, and nowhere else in
#: this module: the comparative sentence describing how the sites differ is rendered
#: from this tuple by :func:`_confirmed_count_summary` and asserted by
#: :meth:`TestCallSitePopulation.test_the_confirmed_sites_do_not_share_one_flag_count`,
#: so a count that moves cannot leave a stale restatement standing in prose.
#:
#: The counts differ per site because the sites genuinely interpolate different
#: flags, and they are therefore asserted per site rather than in aggregate. Which
#: flags each site carries is a property of what that site can observe: the
#: pre-merge barrier's Predicate 2 never observes an in-progress bot of its own,
#: while the step-done participation guard threads one forward from its own
#: completion poll. Both family-A sites forward the two per-refusal overlays and
#: the ``--declined-bots`` observation their re-review consumer accumulates;
#: ``--unrecognised-refusal-bots`` rides the same ``fetch_findings`` return, and is
#: state-determining at the barrier — the one site that renders an operator prompt —
#: so a refusal no arm could read must not resolve there by the bot's declared class.
#: Both producer sites pass the two classification flags.
#:
#: ``--not-triggered`` deliberately moves NEITHER count. It is a ``store_true``
#: bool rather than a ``--*-bots`` list flag, so it carries no interpolated
#: placeholder to quote — which is also why ``derive_bot_flags`` does not surface
#: it and why the quoting sweep has nothing to say about it. Both family-A sites
#: pass it bare.
#: ``(site id, family, doc-suffix, section-substring, expected list-flag count)``.
#: Held as typed rows rather than as ``pytest.param`` objects so the two derivations
#: below read the counts as integers instead of reflecting over a parametrisation.
_CONFIRMED_SITE_ROWS: tuple[tuple[str, str, str, str, int], ...] = (
    (
        'family-a-step-done-participation-guard',
        _FAMILY_A,
        'automatic-review/SKILL.md',
        'Step-done participation guard',
        8,
    ),
    (
        'family-a-premerge-barrier-predicate-2',
        _FAMILY_A,
        'phase-6-finalize/standards/branch-cleanup.md',
        'Predicate 2',
        7,
    ),
    (
        'family-b-producer-find',
        _FAMILY_B,
        'automatic-review/SKILL.md',
        'Producer: FIND',
        2,
    ),
    (
        'family-b-premerge-barrier-refetch',
        _FAMILY_B,
        'phase-6-finalize/standards/branch-cleanup.md',
        'Re-fetch bot comments against the current HEAD',
        2,
    ),
)

#: The same rows as the parametrisation the per-site sweep consumes, built from them
#: rather than spelled a second time.
_CONFIRMED_SITES = tuple(
    pytest.param(family, doc, section, count, id=site_id)
    for site_id, family, doc, section, count in _CONFIRMED_SITE_ROWS
)

#: Matches a list flag and the token that follows it inside a fenced command. The
#: alternation is built from the SAME parser-derived tuple as ``_ALL_LIST_FLAGS``
#: rather than restated as a second literal — a newly added flag reaches the quoting
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


def _confirmed_counts_by_family() -> dict[str, dict[str, int]]:
    """``{family: {site id: expected flag count}}``, read off ``_CONFIRMED_SITE_ROWS``."""
    grouped: dict[str, dict[str, int]] = {}
    for site_id, family, _doc, _section, count in _CONFIRMED_SITE_ROWS:
        grouped.setdefault(family, {})[site_id] = count
    return grouped


def _confirmed_count_summary() -> str:
    """Render the per-site flag counts as a sentence DERIVED from the tuple.

    The comparative statement ("these sites carry different flag sets, so one shared
    count would hide a site that dropped one flag and gained another") is the reason
    the counts are per-site, and it used to be written out in prose beside the tuple
    — where it named specific flags and specific counts, and went stale the moment a
    site gained a flag. Rendering it instead means the only statement of any count in
    this module is the tuple itself.
    """
    return '; '.join(
        f'{site_id} interpolates {count} list flag(s)'
        for site_id, _family, _doc, _section, count in _CONFIRMED_SITE_ROWS
    )


def _notation_pattern(script_name: str) -> re.Pattern:
    """Match the ``{bundle}:{skill}:{script}`` notation naming ``script_name``.

    Anchored on the SCRIPT the family already names rather than on the executor path,
    so this cannot fail to resolve a site :func:`_classify_invocation` accepted: that
    predicate keys on the very ``{skill}:{script}`` substring matched here, and the
    bundle segment in front of it is what completes the notation. Anchoring on
    ``execute-script.py`` instead would additionally require the two to be adjacent
    after continuation folding, which is a property of how the doc happens to wrap.
    """
    return re.compile(
        r'([a-z][a-z0-9-]*):([a-z][a-z0-9-]*):' + re.escape(script_name) + r'(?![0-9A-Za-z_])'
    )


def _invoked_script_path(family: str, command: str) -> str:
    """The repo-relative script path the site's own notation resolves to.

    Derived from the command text rather than mapped from the family by hand: the
    family string names the SCRIPT (its first token), and the bundle and skill come
    from the notation the site actually writes.
    """
    script_name = family.split()[0]
    paths = {
        f'marketplace/bundles/{bundle}/skills/{skill}/scripts/{script_name}.py'
        for bundle, skill in _notation_pattern(script_name).findall(command)
    }
    assert len(paths) == 1, (
        f'expected exactly one {script_name} notation in this {family} invocation; '
        f'resolved {sorted(paths)} from: {command.strip()[:200]!r}'
    )
    return next(iter(paths))


def _evidence_class(family: str, command: str) -> str:
    """The EVIDENCE CLASS a call site consumes, from the participation-site record.

    "Evidence class" is the ``reads`` axis of ``SiteExpectation`` — the closed
    vocabulary ``READS_VOCABULARY`` declares, whose members distinguish a live
    comment scan from the durable currency ledger from a deduped projection and the
    rest. It is recorded per participation SITE (the script), and this resolves it
    per documented CALL site by way of the script that site invokes.

    That is the assertion the call-site sweep was missing: it derived which script
    each site calls and never said anything about it, so a documented invocation of a
    participation script the site population holds no record for satisfied the
    quoting sweep here AND escaped the population there — a surface covered by
    neither, with each one's green run reading as coverage.
    """
    path = _invoked_script_path(family, command)
    record = SITE_EXPECTATIONS.get(path)
    assert record is not None, (
        f'{path} is invoked by a documented call site but carries no recorded evidence '
        f'class — test_participation_site_population.py holds no SITE_EXPECTATIONS '
        f'record for it. A participation script reachable from a documented invocation '
        f'must be a member of that population; add its record there rather than '
        f'exempting the call site here.'
    )
    return record.reads


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
        count is per-site because the sites genuinely differ in WHICH flags they
        interpolate, so a single shared count would hide a site that dropped one
        flag and gained another. Neither the counts nor the comparison between them
        is restated here: the counts live in ``_CONFIRMED_SITES``, and the sentence
        comparing them is rendered from that tuple by
        :func:`_confirmed_count_summary` — prose beside the tuple naming particular
        flags and particular counts is exactly the second statement that went stale
        when a site gained ``--declined-bots``.
        """
        _family, doc, section, command = _find_confirmed(family, doc_suffix, section_substring)

        flags = _interpolated_flags(command)
        assert len(flags) == expected_flag_count, (
            f'{doc} / {section}: expected {expected_flag_count} interpolated list flags, '
            f'found {[f for f, _ in flags]}. Confirmed-site counts, derived from '
            f'_CONFIRMED_SITES: {_confirmed_count_summary()}'
        )
        for flag, value in flags:
            assert value.startswith('"') and value.endswith('"'), (
                f'{doc} / {section}: {flag} interpolates {value} unquoted — an empty value '
                'collapses the flag and steals the next token or trips argparse exit 2'
            )

    def test_the_confirmed_sites_do_not_share_one_flag_count(self):
        """The per-site count is justified BY the tuple, not by a sentence beside it.

        The reason each confirmed site carries its own expected count — rather than
        one shared count for all four — is that the sites interpolate different flag
        sets. That reason was previously asserted only in prose, which named the
        specific flags and went false the moment the participation guard gained
        ``--declined-bots``. Here it is derived: at least one family must hold two
        sites whose counts differ, and if that ever stops being true the per-site
        shape is no longer buying anything and the claim beside the tuple has to be
        re-examined rather than left standing.
        """
        grouped = _confirmed_counts_by_family()

        assert grouped, '_CONFIRMED_SITES is empty — every per-site assertion is vacuous'
        differing = {
            family: sites for family, sites in grouped.items() if len(set(sites.values())) > 1
        }
        assert differing, (
            'no invocation family holds two confirmed sites with different flag counts, '
            'so the per-site count shape asserts nothing a single shared count would not. '
            f'Derived: {_confirmed_count_summary()}'
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

    @pytest.mark.parametrize('site', _INVOCATION_SITES, ids=_site_id)
    def test_every_discovered_site_records_the_evidence_class_it_consumes(self, site):
        """Each discovered site RESOLVES to a recorded evidence class, and it is asserted.

        The scan already derived which script every site invokes and then said
        nothing about it — the derived-but-unasserted axis this closes. Resolving it
        binds the two populations together: a documented invocation of a
        participation script that ``test_participation_site_population.py`` holds no
        ``SITE_EXPECTATIONS`` record for is a surface neither sweep covers, and both
        report green over it today.

        The class is additionally required to be a member of the closed
        ``READS_VOCABULARY``, so a record answering in free text — an answer no
        reader can compare across sites — fails here as well as there.
        """
        family, doc, section, command = site

        evidence_class = _evidence_class(family, command)

        assert evidence_class in READS_VOCABULARY, (
            f'{doc} / {section}: the invoked script records evidence class '
            f'{evidence_class!r}, which is outside the closed vocabulary '
            f'{sorted(READS_VOCABULARY)}'
        )

    def test_the_two_families_resolve_to_different_evidence_classes(self):
        """Matched positive control: the resolution DISCRIMINATES between sites.

        Every per-site assertion above would pass just as happily against a
        resolution that returned one constant for everything. The two families read
        genuinely different evidence — the predicate classifies from the producer's
        emitted observation sets, the producer evaluates the currency test against
        the ledger it writes — so the resolved classes must differ. If they ever
        legitimately converge, this control has to be re-pointed at some other
        discriminating pair rather than deleted.
        """
        by_family = {
            family: {
                _evidence_class(family, command)
                for site_family, _doc, _section, command in _INVOCATION_SITES
                if site_family == family
            }
            for family in (_FAMILY_A, _FAMILY_B)
        }

        for family, classes in by_family.items():
            assert classes, f'no {family} site resolved an evidence class — the control is vacuous'

        assert by_family[_FAMILY_A].isdisjoint(by_family[_FAMILY_B]), (
            f'both invocation families resolve the same evidence class(es) '
            f'({by_family}), so the resolution is not discriminating between them and '
            f'the per-site assertions above would pass against a constant'
        )

    def test_the_evidence_class_resolution_rejects_an_unrecorded_script(self):
        """Matched negative control: an unrecorded participation script FAILS.

        Without it the per-site assertions are only ever observed on scripts the
        population already records, which shows the lookup can succeed — never that
        it can fail. The synthetic notation is shaped exactly like a real one, so
        what is being rejected is the missing RECORD and nothing else.
        """
        with pytest.raises(AssertionError, match='no recorded evidence class'):
            _evidence_class(
                'phantom_participation_script check',
                'python3 .plan/execute-script.py '
                'plan-marshall:automatic-review:phantom_participation_script check --plan-id p',
            )

    def test_the_evidence_class_resolution_reads_the_bundle_from_the_notation(self):
        """Precision guard: the path is built from the notation, not from a fixed prefix.

        A resolver that ignored the bundle and skill segments would map every site
        onto one hard-coded path, and the negative control above would then be the
        only thing that could ever fail. Driving a notation whose bundle and skill
        differ from any real one shows both segments reach the resolved path.
        """
        resolved = _invoked_script_path(
            'review_completeness check',
            'python3 .plan/execute-script.py other-bundle:other-skill:review_completeness check',
        )

        assert resolved == 'marketplace/bundles/other-bundle/skills/other-skill/scripts/review_completeness.py'


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
        """The live parser renders every derived list flag with an optional value."""
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


# =============================================================================
# Declared-flag population closure — the sweep is total over the parser surface
# =============================================================================


class TestDeclaredFlagPopulationIsFullyClassified:
    """Every flag the live ``check`` parser declares is assigned a coverage arm.

    The gap this closes is structural rather than accidental. Every flag sweep in
    this suite derived its population from ``derive_bot_flags``, whose
    ``--[a-z][a-z-]*-bots`` pattern can only ever match the list-flag family — so a
    flag of any other shape was not *missed* by those sweeps, it was never a member
    of the population they swept. The boolean ``--not-triggered`` is the case that
    proved it: nothing in this suite could have failed on its account, and the
    absence of a failure read as coverage.
    """

    def test_the_boolean_not_triggered_flag_is_a_member_by_construction(self):
        """The widened population contains the flag the family pattern cannot match.

        The second assertion is the matched negative control for the first: it
        proves the two derivations genuinely differ HERE, on this flag, so the
        membership above is a property of the wider derivation rather than
        something the narrow one would have delivered anyway.
        """
        assert '--not-triggered' in _ALL_DECLARED_FLAGS, (
            f'--not-triggered must be derived from the live parser, not appended by '
            f'hand. derived population ({len(_ALL_DECLARED_FLAGS)}): '
            f'{list(_ALL_DECLARED_FLAGS)}'
        )
        assert '--not-triggered' not in _ALL_LIST_FLAGS, (
            'the --*-bots family derivation must NOT surface a valueless flag — if it '
            'does, the wider derivation is redundant and this ledger is dead weight'
        )

    def test_the_declared_flag_population_is_fully_classified(self):
        """The covered set EQUALS the population — a strict subset must FAIL.

        Asserted as equality in both directions on purpose. A subset check would
        pass while a newly declared flag sat outside every arm, which is precisely
        the state this suite was in; a superset check would pass while the ledger
        named a flag the parser no longer declares, leaving a retired flag's arm
        standing as coverage of nothing. The population size travels in the failure
        message so a derivation that silently SHRANK is visible as a number rather
        than as a smaller sweep reporting clean.
        """
        population = set(_ALL_DECLARED_FLAGS)
        covered = set(_ALL_LIST_FLAGS) | set(_NON_LIST_FLAG_COVERAGE)

        assert covered == population, (
            f'declared population ({len(population)}): {sorted(population)}; '
            f'covered ({len(covered)}): {sorted(covered)}; '
            f'unclassified: {sorted(population - covered)}; '
            f'no longer declared: {sorted(covered - population)}'
        )
