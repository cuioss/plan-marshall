# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_archive_unexaminable_phases.py: the."""

from _manage_status_archive_unexaminable_phases_fixtures import (
    _EXAMINABLE_SHAPES,
    _EXPECTED_EXAMINABLE_SIZE,
    _EXPECTED_OPEN_NAMES,
    _EXPECTED_UNEXAMINABLE_SIZE,
    _OUTSIDE_THE_VOCABULARY,
    _UNEXAMINABLE_SHAPES,
    _VOCABULARY,
    PHASE_STATUS_DONE,
    VALID_PHASE_STATUSES,
    _status_core,
    _status_document,
    pytest,
)


class TestTheScanDiscriminates:
    """Two populations, opposite verdicts — neither collapses into the other."""

    def test_both_populations_are_non_trivial_and_disjoint(self) -> None:
        """Pins the sizes the sweeps below draw from, before they draw from them.

        A sweep over an empty (or silently shrunken) population reports zero failures
        and is indistinguishable from a clean one. The examinable size is DERIVED from
        the declared vocabulary, and every declared status is asserted to be exercised
        by some shape — a status added to ``VALID_PHASE_STATUSES`` therefore fails here
        rather than joining the codebase with no case anywhere.
        """
        assert _VOCABULARY, 'the declared status vocabulary is empty'
        assert len(_UNEXAMINABLE_SHAPES) == _EXPECTED_UNEXAMINABLE_SIZE, sorted(_UNEXAMINABLE_SHAPES)
        assert len(_EXAMINABLE_SHAPES) == _EXPECTED_EXAMINABLE_SIZE, sorted(_EXAMINABLE_SHAPES)
        assert not set(_UNEXAMINABLE_SHAPES) & set(_EXAMINABLE_SHAPES), (
            'A shape named in both populations would be asserted to hold two opposite verdicts.'
        )
        swept_statuses = {row['status'] for shape in _EXAMINABLE_SHAPES.values() for row in shape}
        assert swept_statuses == set(VALID_PHASE_STATUSES), (
            'Every declared phase status must appear in the examinable population; '
            f'declared {sorted(VALID_PHASE_STATUSES)!r}, swept {sorted(swept_statuses)!r}.'
        )
        assert _OUTSIDE_THE_VOCABULARY not in VALID_PHASE_STATUSES, (
            f'The invalid sentinel must sit outside the declared set; got {_OUTSIDE_THE_VOCABULARY!r}.'
        )
        assert set(_EXPECTED_OPEN_NAMES) == set(_EXAMINABLE_SHAPES), (
            'Every examinable shape must carry an expected open-phase answer, or the '
            'sweep below silently skips the ones it has no expectation for.'
        )

    def test_every_malformed_shape_reports_that_it_could_not_be_examined(self) -> None:
        """Each malformed shape must say so, and say what it could not read."""
        failures: dict[str, str] = {}
        for name, phases in _UNEXAMINABLE_SHAPES.items():
            scan = _status_core.in_progress_phases(_status_document(phases))
            if scan.examinable:
                failures[name] = 'reported examinable'
            elif not scan.unexaminable:
                failures[name] = 'reported unexaminable but named nothing'

        assert failures == {}, (
            f'Swept {len(_UNEXAMINABLE_SHAPES)} malformed shape(s); each must report '
            f'examinable=False and name what it could not read. Failures: {failures!r}'
        )

    def test_every_well_formed_shape_reports_a_complete_reading(self) -> None:
        """Matched control: a readable structure is never degraded.

        The load-bearing half. Without it the sweep above passes against a scan that
        reports ``examinable: False`` for every input — which would refuse every
        no-reason archive and degrade every census cohort.
        """
        failures: dict[str, tuple[str, ...]] = {}
        for name, phases in _EXAMINABLE_SHAPES.items():
            scan = _status_core.in_progress_phases(_status_document(phases))
            if not scan.examinable:
                failures[name] = scan.unexaminable

        assert failures == {}, (
            f'Swept {len(_EXAMINABLE_SHAPES)} well-formed shape(s); every one must be '
            f'readable in full. Failures: {failures!r}'
        )

    def test_the_open_phase_set_is_still_reported_for_each_readable_shape(self) -> None:
        """The scan reports WHAT IS OPEN, not merely whether it could look.

        Without this, ``examinable: True`` could be reported by a scan that never
        found anything — and the archive's closure loop would silently close nothing.
        """
        observed = {
            name: [phase['name'] for phase in _status_core.in_progress_phases(_status_document(phases)).phases]
            for name, phases in _EXAMINABLE_SHAPES.items()
        }

        assert observed == _EXPECTED_OPEN_NAMES, observed

    def test_a_partially_malformed_structure_still_reports_the_phases_it_established(self) -> None:
        """One unreadable row does not discard the rows that read cleanly.

        The two facts are independent: ``phases`` carries what WAS established and
        ``unexaminable`` says the set may be incomplete. Dropping the readable half
        would trade a false zero for a different false answer.
        """
        document = _status_document(
            [
                {'name': '5-execute', 'status': 'in_progress'},
                'not-a-phase-record',
                {'name': '6-finalize', 'status': 'pending'},
            ]
        )

        scan = _status_core.in_progress_phases(document)

        assert [phase['name'] for phase in scan.phases] == ['5-execute'], scan.phases
        assert scan.examinable is False, scan
        assert len(scan.unexaminable) == 1, scan.unexaminable
        assert 'phases[1]' in scan.unexaminable[0], scan.unexaminable

    @pytest.mark.parametrize(
        'shape',
        ['a_row_with_no_name', 'a_row_with_an_empty_name', 'a_row_with_a_non_string_name'],
        ids=['absent', 'empty', 'non_string'],
    )
    def test_an_unidentifiable_row_is_never_reported_as_an_open_phase(self, shape: str) -> None:
        """A row without a usable ``name`` is a shortfall, not the phase named ``''``.

        Each of the three rows carries ``status: in_progress``, so a scan that skipped
        the name check would ADMIT it — and the census projection would then publish
        ``open_phases: ['']`` on a cohort still reading ``coverage: complete``. The
        assertion is therefore two-sided: the row must be absent from ``phases`` AND
        named in ``unexaminable``, because either half alone is satisfiable by a scan
        that simply discards what it cannot classify.
        """
        scan = _status_core.in_progress_phases(_status_document(_UNEXAMINABLE_SHAPES[shape]))

        assert scan.examinable is False, scan
        assert [phase['name'] for phase in scan.phases] == [], (
            f'An unidentifiable row must not reach the reported open-phase set; got {scan.phases!r}.'
        )
        assert any('phases[1]' in note and 'name' in note for note in scan.unexaminable), scan.unexaminable

    def test_the_reported_phases_are_the_live_records_not_copies(self) -> None:
        """``cmd_archive`` closes a phase by mutating what the scan handed it.

        Returning copies would make the archiver's closure loop a no-op that still
        reported success — the phases would stay ``in_progress`` in the record.
        """
        document = _status_document([{'name': '5-execute', 'status': 'in_progress'}])

        scan = _status_core.in_progress_phases(document)
        scan.phases[0]['status'] = 'done'

        assert document['phases'][0]['status'] == 'done', document

    @pytest.mark.parametrize(
        'shape',
        [f'only_{PHASE_STATUS_DONE}', 'a_row_that_is_a_string'],
        ids=['examinable', 'unexaminable'],
    )
    def test_the_scan_has_no_truth_value(self, shape: str) -> None:
        """``bool()`` raises for BOTH states, so the retired idiom cannot survive.

        Parametrized over one member of each population deliberately: a type that
        raised only for the unexaminable state would still let ``if not scan:`` read
        as a valid completion test on the ordinary path, leaving the retired idiom
        alive and silently wrong the one time it mattered.
        """
        phases = {**_EXAMINABLE_SHAPES, **_UNEXAMINABLE_SHAPES}[shape]
        scan = _status_core.in_progress_phases(_status_document(phases))

        with pytest.raises(TypeError, match='no truth value'):
            bool(scan)
