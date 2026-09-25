# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_decision_rules_fixtures import (
    DEFAULT_PHASE_6_STEPS,
    _compose_ns,
    _mem,
    _restore_footprint_resolver,
    _seed_marshal,
    _stub_footprint,
    cmd_compose,
    result_phase_6_steps,
)


class TestNoRemovedSelfReviewSymbols:
    """The clean break left NO reference behind, in production or in test setup.

    Asserted explicitly rather than inferred from a monkeypatch failing, because
    ``setattr`` on a module SUCCEEDS for a name that no longer exists: a stale
    ``_mem._log_pre_submission_self_review_omitted = ...`` line in a test's setup
    would quietly re-create the dead attribute and this suite would never notice.
    """

    def test_removed_symbols_are_absent_from_the_module(self):
        for symbol in (
            '_apply_pre_submission_self_review_inactive',
            '_log_pre_submission_self_review_omitted',
        ):
            assert not hasattr(_mem, symbol), (
                f'{symbol} was removed in the clean break; a surviving attribute means '
                'some test setup re-created it via setattr'
            )

    def test_removed_compose_result_key_is_absent(self, plan_context):
        """The always-``False`` ``pre_submission_self_review_omitted`` key is gone."""
        _seed_marshal(ci_provider=None)
        _stub_footprint(['some/file.py'])

        ns = _compose_ns(plan_id='qg-self-review-nokey')
        result = cmd_compose(ns)

        assert result is not None
        assert 'pre_submission_self_review_omitted' not in result



# =============================================================================
# Test: no bot-enforcement guard — automatic-review governed by candidacy/lane
# =============================================================================


class TestNoBotEnforcementGuard:
    """The bot-enforcement guard (and its placement-validator twin) are removed.

    ``automatic-review`` is governed purely by its configured candidacy / ``lane``
    — compose never force-adds it back on GitHub/GitLab plans and never emits a
    ``bot_enforcement_violation`` error. Its presence tracks the candidate list and
    the lane resolution exactly.
    """

    def test_no_bot_enforcement_symbols_survive(self):
        """No bot-enforcement guard / placement-validator symbol remains on the module."""
        for symbol in (
            '_apply_bot_enforcement_guard',
            '_bot_enforcement_insert_index',
            '_validate_automatic_review_placement',
            '_log_bot_enforcement_guard_fired',
            '_log_bot_enforcement_guard_remediated',
            '_log_bot_enforcement_placement_violation',
        ):
            assert not hasattr(_mem, symbol), f'{symbol} must be deleted with the bot-enforcement guard'

    def test_github_plan_does_not_force_add_dropped_automatic_review(self, plan_context):
        _seed_marshal(ci_provider='github')
        _stub_footprint(['some/file.py'])

        # Candidate set EXCLUDES automatic-review; with no guard it stays absent.
        phase_6 = ','.join(s for s in DEFAULT_PHASE_6_STEPS if s != 'automatic-review')
        ns = _compose_ns(plan_id='qg-bot-github', phase_6_steps=phase_6)
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert result.get('error') != 'bot_enforcement_violation'
        assert 'automatic-review' not in result_phase_6_steps(result)

    def test_gitlab_plan_does_not_force_add_dropped_automatic_review(self, plan_context):
        _seed_marshal(ci_provider='gitlab')
        _stub_footprint(['some/file.py'])

        phase_6 = ','.join(s for s in DEFAULT_PHASE_6_STEPS if s != 'automatic-review')
        ns = _compose_ns(plan_id='qg-bot-gitlab', phase_6_steps=phase_6)
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert result.get('error') != 'bot_enforcement_violation'
        assert 'automatic-review' not in result_phase_6_steps(result)

    def test_present_when_in_candidates(self, plan_context):
        _seed_marshal(ci_provider='github')
        _stub_footprint(['some/file.py'])

        # multi_module feature keeps automatic-review (present in default candidates).
        ns = _compose_ns(plan_id='qg-bot-present')
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert 'automatic-review' in result_phase_6_steps(result)

    def test_absent_for_non_ci_plan_stays_absent(self, plan_context):
        _seed_marshal(ci_provider=None)
        _stub_footprint(['some/file.py'])

        phase_6 = ','.join(s for s in DEFAULT_PHASE_6_STEPS if s != 'automatic-review')
        ns = _compose_ns(plan_id='qg-bot-other', phase_6_steps=phase_6)
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert 'automatic-review' not in result_phase_6_steps(result)
