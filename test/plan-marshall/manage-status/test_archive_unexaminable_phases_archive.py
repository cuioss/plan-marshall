# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_archive_unexaminable_phases_fixtures import (
    Any,
    Namespace,
    Path,
    _seed_plan_with_an_unreadable_phase_row,
    cmd_archive,
    cmd_create,
    cmd_update_phase,
    json,
)


class TestArchiveOfAnUnexaminableRecord:
    """Refuse without a reason; preserve the lifecycle state with one; never claim complete."""

    def test_a_no_reason_archive_is_refused_and_changes_nothing(self, plan_context: Any) -> None:
        """Fail closed: the findings gate cannot establish that ``6-finalize`` is closed.

        The refusal is asserted together with the untouched document, because a guard
        that returned an error AFTER writing would still have corrupted the record it
        declined to archive.
        """
        plan_id = 'archive-unexaminable-refused'
        status_path = _seed_plan_with_an_unreadable_phase_row(plan_context, plan_id)
        before = status_path.read_text(encoding='utf-8')

        result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))

        assert result['status'] == 'error', result
        assert result['error'] == 'phases_unexaminable', result
        assert result['unexaminable'], 'The refusal must name what could not be read.'
        assert 'archived_to' not in result, result
        assert plan_context.plan_dir_for(plan_id).exists(), 'The refused archive must move nothing.'
        assert status_path.read_text(encoding='utf-8') == before, 'The refused archive must write nothing.'

    def test_a_reason_archive_proceeds_but_preserves_the_lifecycle_state(self, plan_context: Any) -> None:
        """A deliberate close is never stranded — but it may not claim ``complete``.

        ``complete`` is the post-finalize sentinel dormant consumers match on, so
        writing it over a record whose open-phase set is unknown asserts a completion
        nothing established. The phases that WERE established open are still closed,
        which is what separates preserving the state from refusing to act.
        """
        plan_id = 'archive-unexaminable-with-reason'
        _seed_plan_with_an_unreadable_phase_row(plan_context, plan_id)

        result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason='superseded_by_another_plan'))

        assert result['status'] == 'success', result
        assert result['phase_closure'] == 'partial', result
        assert result['phase_closure_reason'], 'A partial closure must name its shortfall.'

        archived = json.loads((Path(result['archived_to']) / 'status.json').read_text(encoding='utf-8'))
        assert archived['current_phase'] != 'complete', (
            f'A record whose phases could not be read in full must not be archived as complete; got {archived!r}.'
        )
        assert archived['current_phase'] == '1-init', archived['current_phase']
        readable = {row['name']: row['status'] for row in archived['phases'] if isinstance(row, dict)}
        assert readable['1-init'] == 'done', f'A phase established as open must still be closed; got {readable!r}.'
        assert readable['3-outline'] == 'pending', f'A never-started phase must stay pending; got {readable!r}.'
        assert 'not-a-phase-record' in archived['phases'], 'The unreadable row is preserved, not rewritten.'

    def test_a_well_formed_record_with_no_open_phase_still_completes(self, plan_context: Any) -> None:
        """Matched control: the ordinary no-open-phase archive still reaches ``complete``.

        The load-bearing half of the pair above. Without it, both cells are equally
        consistent with an archiver that refuses everything, or that has simply
        stopped writing the sentinel — and the reader cannot tell a post-condition
        that is SATISFIED from one that is merely unreachable.
        """
        plan_id = 'archive-examinable-control'
        cmd_create(
            Namespace(
                plan_id=plan_id,
                title='Examinable Archive Control',
                phases='1-init,2-refine,3-outline',
                force=False,
            )
        )
        for phase in ('1-init', '2-refine', '3-outline'):
            cmd_update_phase(Namespace(plan_id=plan_id, phase=phase, status='done'))

        result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))

        assert result['status'] == 'success', result
        assert result['phase_closure'] == 'complete', result
        assert 'phase_closure_reason' not in result, f'A complete closure has no shortfall to name; got {result!r}.'
        archived = json.loads((Path(result['archived_to']) / 'status.json').read_text(encoding='utf-8'))
        assert archived['current_phase'] == 'complete', archived['current_phase']
