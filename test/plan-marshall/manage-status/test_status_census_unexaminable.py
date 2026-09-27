# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_status_census_fixtures import (
    _RETAINED_OPEN_PHASE,
    Path,
    _census,
    _cohort,
    _records_for,
    _write_plan,
    _write_unnamed_phase_plan,
    _write_unreadable_phases_plan,
    store,
)


class TestUnexaminablePhasesDegradeTheCohort:
    """A member whose ``phases`` will not read is still a member — and still a shortfall.

    This is the third shortfall kind, one level in from the other two. The
    ``status.json`` parsed, so the directory IS established as a plan and belongs in
    ``population``; what could not be established is its open-phase SET. Reporting
    ``open_phase_count`` over it as though the record had been read is the false zero
    at the heart of this cohort's honesty property, so the cohort degrades instead.
    """

    def test_a_member_whose_phases_will_not_read_degrades_its_cohort(self, store: Path) -> None:
        """``partial``, the member counted, the shortfall credited and the plan named.

        The retained open phase is asserted on the RECORD, located by the broken plan's
        own id: the count alone would be satisfied by the readable sibling contributing
        both, which is precisely the reading a ``done`` fixture row used to permit.
        """
        _write_plan(store / 'plans' / 'readable-plan', {'1-init': 'done', '5-execute': 'in_progress'})
        _write_unreadable_phases_plan(store / 'plans' / 'unreadable-phases-plan')

        result = _census()

        live = _cohort(result, 'live')
        assert live['coverage'] == 'partial', live
        assert live['population'] == 2, f'Its status.json parsed, so the plan IS an established member; got {live!r}.'
        assert live['unreadable_count'] == 1, f'The unread open-phase set must be credited; got {live!r}.'
        assert 'unreadable-phases-plan' in live['reason'], live

        retained = [record for record in _records_for(result, 'live') if record['id'] == 'unreadable-phases-plan']
        assert len(retained) == 1, (
            f'A positively-established open phase survives an unexaminable phase list; got {retained!r}.'
        )
        assert retained[0]['open_phases'] == [_RETAINED_OPEN_PHASE], retained[0]
        assert live['open_phase_count'] == 2, (
            'Both established open phases stay visible under partial coverage — the '
            f'readable plan and the retained one; got {live!r}.'
        )

    def test_the_same_shortfall_one_level_deeper_degrades_the_worktree_cohort(self, store: Path) -> None:
        """The worktree cohort accumulates its own counts, so it needs its own cell.

        A fix applied to the single-container path alone leaves this cohort reporting
        ``complete`` over a moved-in plan whose phases nobody could read — and counting
        the retained open phase is a second accumulator that can independently miss it.
        """
        worktree_plans = store / 'worktrees' / 'wt-0' / '.plan' / 'local' / 'plans'
        _write_plan(worktree_plans / 'wt-plan-0', {'1-init': 'done', '5-execute': 'in_progress'})
        _write_unreadable_phases_plan(worktree_plans / 'wt-plan-broken')

        result = _census()

        worktree = _cohort(result, 'worktree')
        assert worktree['coverage'] == 'partial', worktree
        assert worktree['population'] == 2, worktree
        assert worktree['unreadable_count'] == 1, worktree
        assert 'wt-0/wt-plan-broken' in worktree['reason'], (
            f'A bare plan name would be ambiguous across worktrees; got {worktree!r}.'
        )

        retained = [record for record in _records_for(result, 'worktree') if record['id'] == 'wt-plan-broken']
        assert len(retained) == 1, f'The retained open phase must survive one level deeper too; got {retained!r}.'
        assert retained[0]['open_phases'] == [_RETAINED_OPEN_PHASE], retained[0]
        assert worktree['open_phase_count'] == 2, worktree

    def test_a_row_with_no_usable_name_degrades_the_cohort_instead_of_reporting_an_empty_name(
        self, store: Path
    ) -> None:
        """An unidentifiable ``in_progress`` row is a shortfall, never ``open_phases: ['']``.

        The row is well-formed apart from its missing ``name``, so it would be
        classified OPEN on its status alone — and the projection would then render it as
        the phase named ``''`` on a cohort still claiming ``coverage: complete``. Both
        halves are asserted: the cohort degrades, AND no record anywhere carries an
        empty name. Asserting only the coverage would pass against a scan that degraded
        the cohort and still published the unusable record.
        """
        _write_plan(store / 'plans' / 'readable-plan', {'1-init': 'done', '5-execute': 'in_progress'})
        _write_unnamed_phase_plan(store / 'plans' / 'unnamed-phase-plan')

        result = _census()

        live = _cohort(result, 'live')
        assert live['coverage'] == 'partial', f'A row nobody can identify is a part that went unread; got {live!r}.'
        assert live['population'] == 2, live
        assert live['unreadable_count'] == 1, live
        assert 'unnamed-phase-plan' in live['reason'], live
        assert live['open_phase_count'] == 1, f'Only the readable plan contributes an open phase; got {live!r}.'

        reported_names = [name for record in result['open_phase_records'] for name in record['open_phases']]
        assert '' not in reported_names, (
            f'A synthesised empty phase name is an unusable open-phase record; got {reported_names!r}.'
        )
        assert 'unnamed-phase-plan' not in [record['id'] for record in _records_for(result, 'live')], (
            'The plan established no readable open phase, so it contributes no record.'
        )

    def test_a_member_whose_phases_read_cleanly_keeps_the_cohort_complete(self, store: Path) -> None:
        """Matched control: the identical tree MINUS the unreadable-phases member.

        The load-bearing half. Without it both cells above pass equally against a
        census that degrades every cohort it is handed — which would make ``partial``
        as uninformative as the false zero it replaced.
        """
        _write_plan(store / 'plans' / 'readable-plan', {'1-init': 'done', '5-execute': 'in_progress'})
        _write_plan(store / 'plans' / 'second-readable-plan', {'1-init': 'done', '5-execute': 'done'})

        result = _census()

        live = _cohort(result, 'live')
        assert live['coverage'] == 'complete', live
        assert live['population'] == 2, live
        assert live['unreadable_count'] == 0, live
        assert live['open_phase_count'] == 1, live
        assert 'reason' not in live, f'A complete cohort has no shortfall to name; got {live!r}.'
