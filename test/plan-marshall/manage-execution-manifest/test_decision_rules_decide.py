# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_decision_rules_fixtures import (
    _compose_ns,
    _decide,
    _restore_footprint_resolver,
    _seed_marshal,
    _stub_footprint,
    cmd_compose,
)

# =============================================================================
# Test: the six-row matrix reports every subtraction it makes
# =============================================================================


class TestDecideSubtractionRecords:
    """Every narrowing row returns one ``{step, reason}`` record per removal.

    Five of the six matrix rows narrow a candidate list, and every one of them
    used to do it SILENTLY — the row returned only the body and its rule name, so
    a step the matrix removed left no trace an operator could read. The third
    return value closes that: the matrix's DECISIONS are unchanged, only their
    observability is.

    Each case therefore asserts the record set against the actual difference
    between the candidates it passed in and the steps that came out, rather than
    against a hand-written expected list. Deriving the expectation from the
    row's own output is what keeps these from degenerating into a restatement of
    the implementation — a row that stopped narrowing, or narrowed more, fails.
    """

    _PHASE_5 = ['quality-gate', 'module-tests', 'coverage']
    _PHASE_6 = ['push', 'ci-wait', 'lessons-capture', 'adr-propose', 'archive-plan', 'create-pr']

    def _decide_with(self, **overrides):
        kwargs = {
            'change_type': 'feature',
            'track': 'complex',
            'scope_estimate': 'multi_module',
            'recipe_key': None,
            'affected_files_count': 5,
            'phase_5_candidates': list(self._PHASE_5),
            'phase_6_candidates': list(self._PHASE_6),
        }
        kwargs.update(overrides)
        return _decide(**kwargs)

    @staticmethod
    def _assert_records_match_the_removals(body, dropped, phase_5_in, phase_6_in):
        """Assert the record set is exactly what the row actually removed.

        Derived from the row's own kept lists, so the assertion cannot drift into
        a copy of the implementation's hardcoded reason sets.
        """
        removed = [s for s in phase_5_in if s not in body['phase_5']['verification_steps']]
        removed += [s for s in phase_6_in if s not in body['phase_6']['steps']]
        assert [record['step'] for record in dropped] == removed
        assert all(record['reason'] for record in dropped), 'every record needs a non-empty reason'

    def test_early_terminate_analysis_records_every_drop(self):
        """Rule 1 empties phase-5 outright and narrows phase-6 to the analysis minimum."""
        body, rule, dropped = self._decide_with(change_type='analysis', affected_files_count=0)

        assert rule == 'early_terminate_analysis'
        self._assert_records_match_the_removals(body, dropped, self._PHASE_5, self._PHASE_6)
        # Every phase-5 candidate is removed, so each must be individually named.
        assert {r['step'] for r in dropped} >= set(self._PHASE_5)

    def test_recipe_row_records_every_drop(self):
        """Rule 2 narrows phase-5 to the core verify roles and drops legacy ci-wait."""
        body, rule, dropped = self._decide_with(recipe_key='recipe-surgical-fix')

        assert rule == 'recipe'
        self._assert_records_match_the_removals(body, dropped, self._PHASE_5, self._PHASE_6)
        assert 'ci-wait' in {r['step'] for r in dropped}

    def test_tests_only_row_records_every_drop(self):
        """Rule 4 narrows phase-5 to the module-tests role and leaves phase-6 whole."""
        body, rule, dropped = self._decide_with(change_type='verification', affected_files_count=3)

        assert rule == 'tests_only'
        self._assert_records_match_the_removals(body, dropped, self._PHASE_5, self._PHASE_6)
        assert body['phase_6']['steps'] == self._PHASE_6

    def test_surgical_bug_fix_row_records_every_drop(self):
        """Rule 5 narrows both phases, and the reason names the firing rule."""
        body, rule, dropped = self._decide_with(change_type='bug_fix', scope_estimate='surgical')

        assert rule == 'surgical_bug_fix'
        self._assert_records_match_the_removals(body, dropped, self._PHASE_5, self._PHASE_6)
        assert all('surgical_bug_fix' in record['reason'] for record in dropped)

    def test_verification_no_files_row_records_every_drop(self):
        """Rule 6 narrows phase-6 to the analysis minimum and keeps phase-5 whole."""
        body, rule, dropped = self._decide_with(change_type='verification', affected_files_count=0)

        assert rule == 'verification_no_files'
        self._assert_records_match_the_removals(body, dropped, self._PHASE_5, self._PHASE_6)
        assert body['phase_5']['verification_steps'] == self._PHASE_5

    def test_default_row_narrows_nothing_and_records_nothing(self):
        """Rule 7 is the safe baseline: no subtraction, so no records.

        The negative case matters as much as the positives — a helper that
        emitted a record per candidate regardless of removal would pass every
        test above and fail only here.
        """
        body, rule, dropped = self._decide_with()

        assert rule == 'default'
        assert dropped == []
        assert body['phase_5']['verification_steps'] == self._PHASE_5
        assert body['phase_6']['steps'] == self._PHASE_6

    def test_records_are_surfaced_on_the_compose_result(self, plan_context):
        """The records reach the compose result, not just ``_decide``'s return.

        The end-to-end half: a record list that never left the matrix would leave
        the drop just as invisible to an operator as before.
        """
        _seed_marshal(ci_provider=None)
        _stub_footprint(['some/file.py'])

        ns = _compose_ns(
            plan_id='qg-decide-records',
            change_type='bug_fix',
            scope_estimate='surgical',
            phase_5_steps='quality-gate,module-tests,coverage',
        )
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        records = result['decision_matrix_dropped']
        assert records, 'a narrowing row must surface its records on the compose result'
        assert all(record['step'] and record['reason'] for record in records)
