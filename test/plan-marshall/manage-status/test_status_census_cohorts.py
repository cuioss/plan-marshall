# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_status_census_fixtures import (
    _ARCHIVE_DATE,
    Path,
    _census,
    _records_for,
    _write_plan,
    pytest,
    store,
)


class TestCohortsAreCountedSeparately:
    """Three stores, three deliberately different figures, never blended."""

    @pytest.fixture
    def three_cohorts(self, store: Path) -> Path:
        """Populations 3 / 2 / 1 with open-phase counts 2 / 1 / 0.

        Both axes differ per cohort. Equal figures would leave a row carrying its
        neighbour's number — or the 6-plan total — indistinguishable from three correct
        rows.
        """
        open_phases = {'1-init': 'done', '5-execute': 'in_progress'}
        closed_phases = {'1-init': 'done', '5-execute': 'done'}

        for index in range(3):
            phases = open_phases if index < 2 else closed_phases
            _write_plan(store / 'plans' / f'live-plan-{index}', phases)

        for index in range(2):
            phases = open_phases if index < 1 else closed_phases
            worktree_plans = store / 'worktrees' / f'wt-{index}' / '.plan' / 'local' / 'plans'
            _write_plan(worktree_plans / f'wt-plan-{index}', phases)

        _write_plan(store / 'archived-plans' / f'{_ARCHIVE_DATE}-archived-plan', closed_phases)
        return store

    def test_each_cohort_reports_its_own_population_and_open_count(self, three_cohorts: Path) -> None:
        del three_cohorts  # The fixture's effect is the tree it seeded.

        result = _census()

        assert [row['cohort'] for row in result['cohorts']] == ['live', 'worktree', 'archived'], result
        assert [row['population'] for row in result['cohorts']] == [3, 2, 1], (
            f'Each cohort must report its OWN population, never a blended total; got {result["cohorts"]!r}.'
        )
        assert [row['open_phase_count'] for row in result['cohorts']] == [2, 1, 0], result['cohorts']
        assert all(row['coverage'] == 'complete' for row in result['cohorts']), result['cohorts']
        assert all(row['unreadable_count'] == 0 for row in result['cohorts']), result['cohorts']

    def test_the_open_phase_records_are_attributed_to_their_cohorts(self, three_cohorts: Path) -> None:
        """Each record names the store it came from, so the rows stay unblended."""
        del three_cohorts

        result = _census()

        assert sorted(record['id'] for record in _records_for(result, 'live')) == ['live-plan-0', 'live-plan-1']
        assert [record['id'] for record in _records_for(result, 'worktree')] == ['wt-plan-0']
        assert _records_for(result, 'archived') == []

    def test_the_anchor_reports_the_override_branch(self, three_cohorts: Path) -> None:
        """The second anchor label: a redirected store says so rather than claiming main.

        A reader must be able to tell a census of a real checkout from one of a
        stand-in store, which is what makes ``anchor`` worth reporting at all.
        """
        result = _census()

        assert result['anchor'] == 'override', result
        assert Path(result['anchor_path']) == three_cohorts
