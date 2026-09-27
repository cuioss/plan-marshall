# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_manage_status_transition_archive.py: archive marks."""

from _manage_status_manage_status_transition_archive_fixtures import (
    Namespace,
    Path,
    _seed_finalize_phase_plan,
    cmd_archive,
    json,
)


def test_archive_marks_final_phase_done_and_sets_complete(plan_context):
    """cmd_archive must close the active phase + set current_phase=complete BEFORE the move."""
    plan_id = 'archive-atomic-happy-path'
    _seed_finalize_phase_plan(plan_id)
    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False))

    assert result['status'] == 'success', f'archive failed: {result}'
    assert 'archived_to' in result, f'missing archived_to in {result}'

    archived_status_path = Path(result['archived_to']) / 'status.json'
    assert archived_status_path.exists(), (
        f'archived status.json missing at {archived_status_path} — '
        f'either move failed or archived_to points to wrong path'
    )

    archived_status = json.loads(archived_status_path.read_text(encoding='utf-8'))
    assert archived_status['current_phase'] == 'complete', (
        f"Expected archived current_phase='complete', got "
        f'{archived_status["current_phase"]!r}. Atomic-archive fix '
        f'regressed: cmd_archive is not setting the post-finalize sentinel '
        f'before shutil.move runs.'
    )
    # Widened from ``phases[-1]`` to EVERY phase. The single-index assertion was
    # precisely the blind spot that let the single-slot closure pass a green suite:
    # it read the one phase the retired ``next()`` happened to close, so a second
    # phase left ``in_progress`` was invisible to it.
    still_open = [p['name'] for p in archived_status['phases'] if p['status'] == 'in_progress']
    assert still_open == [], (
        f'Archive left {still_open!r} recorded in_progress. cmd_archive must close '
        f'EVERY open phase before shutil.move runs, not just the last one.'
    )
    observed = [(p['name'], p['status']) for p in archived_status['phases']]
    assert all(status == 'done' for _name, status in observed), (
        f'This seed started every phase, so archive must leave all of them done; got {observed!r}.'
    )
