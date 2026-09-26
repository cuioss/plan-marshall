# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_status_census_fixtures import (
    _ARCHIVE_DATE,
    Path,
    _census,
    _cohort,
    _records_for,
    _write_plan,
    pytest,
    store,
)


class TestOpenPhaseRecords:
    """The open-phase predicate is ``phases[]`` status — never the loop-back marker."""

    @pytest.fixture
    def archived_pair(self, store: Path) -> dict[str, str]:
        """Two archived records differing in the one thing the predicate may read.

        ``still-open`` holds two ``in_progress`` phases. ``closed-with-marker`` holds
        none — every phase is ``done`` — but still carries
        ``metadata.loop_back_reentry``, the shape a plan is left in after a sanctioned
        loop-back that later completed.
        """
        archived_root = store / 'archived-plans'
        open_id = f'{_ARCHIVE_DATE}-still-open'
        closed_id = f'{_ARCHIVE_DATE}-closed-with-marker'
        _write_plan(
            archived_root / open_id,
            {'1-init': 'done', '5-execute': 'in_progress', '6-finalize': 'in_progress'},
        )
        _write_plan(
            archived_root / closed_id,
            {'1-init': 'done', '5-execute': 'done', '6-finalize': 'done'},
            metadata={'loop_back_reentry': {'from_phase': '5-execute', 'to_phase': '3-outline'}},
        )
        return {'open_id': open_id, 'closed_id': closed_id}

    def test_every_in_progress_phase_of_a_record_is_reported(self, archived_pair: dict[str, str]) -> None:
        """A record with two open phases is reported once, naming BOTH phases.

        Reporting only the first would under-report exactly the population this verb
        exists to surface — and is the shape of the single-closure defect that motivated
        it.
        """
        result = _census()

        records = _records_for(result, 'archived')
        open_records = [record for record in records if record['id'] == archived_pair['open_id']]
        assert len(open_records) == 1, f'Expected one record for the open plan, got {records!r}.'
        assert set(open_records[0]['open_phases']) == {'5-execute', '6-finalize'}, open_records[0]
        assert _cohort(result, 'archived')['open_phase_count'] == 2, (
            'One archived record holds TWO open phases and the cohort count names '
            'phases, not plans, so it reports 2 over a single record.'
        )

    def test_a_closed_record_carrying_the_loop_back_marker_is_not_reported(self, archived_pair: dict[str, str]) -> None:
        """Matched control: the marker is present, every phase is ``done`` ⇒ absent.

        A predicate keyed on ``metadata.loop_back_reentry`` would report this record,
        which has nothing open. The marker says a loop-back was scheduled, not that a
        phase was left running.
        """
        result = _census()

        reported = [record['id'] for record in _records_for(result, 'archived')]
        assert archived_pair['closed_id'] not in reported, (
            'A record whose phases are all done holds no open phase, whatever marker '
            f'its metadata carries; got {reported!r}.'
        )

    def test_the_archived_id_is_the_dated_directory_name(self, archived_pair: dict[str, str]) -> None:
        """The reported id is the ``{YYYY-MM-DD}-{plan_id}`` directory ``archive`` writes.

        The date is a fixed past one, so an id reported as the bare plan id — or rebuilt
        from today's date — fails.
        """
        result = _census()

        reported = [record['id'] for record in _records_for(result, 'archived')]
        assert archived_pair['open_id'] in reported, reported
        assert archived_pair['open_id'].startswith(f'{_ARCHIVE_DATE}-'), archived_pair['open_id']
        assert 'still-open' not in reported, (
            'The archived cohort is keyed by the dated directory name, not by the bare plan id.'
        )


class TestOpenPhaseCountNamesPhasesNotPlans:
    """``open_phase_count`` is a phase total, and each cohort sums it independently.

    ``_scan_plan_container`` emits one record per PLAN, so a count taken as
    ``len(records)`` reads correctly for every single-open-phase plan and under-reports
    exactly the multi-open-phase ones — the loop-back state this verb exists to surface.
    Every cell here therefore holds the PLAN count fixed at one and varies only the
    number of open phases inside it, so a passing verdict cannot come from the two
    figures happening to coincide.
    """

    def test_one_plan_with_two_open_phases_counts_two(self, store: Path) -> None:
        """Population 1, one record, count 2 — the three figures are asserted together.

        Asserting the count alone would not distinguish a phase total from a plan total
        that happened to be wrong in the other direction; pinning ``population`` and the
        record count beside it makes the axis unambiguous.
        """
        _write_plan(
            store / 'plans' / 'two-open-plan',
            {'1-init': 'done', '5-execute': 'in_progress', '6-finalize': 'in_progress'},
        )

        result = _census()

        live = _cohort(result, 'live')
        assert live['coverage'] == 'complete', live
        assert live['population'] == 1, live
        assert len(_records_for(result, 'live')) == 1, 'One plan yields one record however many phases it holds.'
        assert live['open_phase_count'] == 2, (
            f'The field counts established open PHASES; a per-plan count reports 1 here. Got {live!r}.'
        )

    def test_one_plan_with_one_open_phase_counts_one(self, store: Path) -> None:
        """Matched control: the same single-plan shape with one phase open reports 1.

        The load-bearing half. Without it the cell above is equally consistent with a
        count that is simply inflated — a verb reporting the length of ``phases[]``, say
        — and the reader could not tell a phase total from a wrong number.
        """
        _write_plan(store / 'plans' / 'one-open-plan', {'1-init': 'done', '5-execute': 'in_progress'})

        result = _census()

        live = _cohort(result, 'live')
        assert live['coverage'] == 'complete', live
        assert live['population'] == 1, live
        assert live['open_phase_count'] == 1, live

    def test_the_worktree_cohort_sums_phases_too(self, store: Path) -> None:
        """The second accumulator, which sums independently and can miss the fix alone.

        ``_census_worktree_cohort`` builds its own row rather than delegating to
        ``_census_single_container``, so a correction applied to one leaves the other
        publishing a plan count under a phase name.
        """
        worktree_plans = store / 'worktrees' / 'wt-0' / '.plan' / 'local' / 'plans'
        _write_plan(
            worktree_plans / 'wt-two-open',
            {'1-init': 'done', '5-execute': 'in_progress', '6-finalize': 'in_progress'},
        )

        result = _census()

        worktree = _cohort(result, 'worktree')
        assert worktree['coverage'] == 'complete', worktree
        assert worktree['population'] == 1, worktree
        assert len(_records_for(result, 'worktree')) == 1, worktree
        assert worktree['open_phase_count'] == 2, worktree
