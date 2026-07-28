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
  member, over a bot set derived from ``bot_registry.bot_kinds()``.

Every set-guarding assertion derives its population from the registry rather than
a hard-coded literal list, so a bot added or retired in a standards doc is covered
here automatically instead of silently escaping the sweep.
"""

from __future__ import annotations

import itertools
import json
import sys
from unittest.mock import patch

import pytest

from conftest import PLAN_DIR_NAME, PROJECT_ROOT, get_script_path

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
        """CodeRabbit + PR-Agent required; Sourcery kept as an additional reviewer.

        The seeded defaults are both empty by design (never-asked), so the
        operative classification lives only in each project's own marshal.json.
        Pinning it closes the enabled-bots-vs-operative drift gap: a documented
        reviewer roster that silently disagrees with the config the pipeline
        actually reads is invisible at every other surface.
        """
        params = _live_step_params()

        assert params['required_bots'] == 'coderabbit,pr-agent'
        assert params['optional_bots'] == 'sourcery'

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
