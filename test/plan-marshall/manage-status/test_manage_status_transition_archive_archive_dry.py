# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_manage_status_transition_archive_fixtures import (
    Namespace,
    Path,
    _seed_finalize_phase_plan,
    _stub_finding_queries,
    cmd_archive,
)


def test_archive_dry_run_leaves_status_unchanged(plan_context):
    """--dry-run must NOT mutate status.json or create the archive directory."""
    plan_id = 'archive-atomic-dry-run'
    _seed_finalize_phase_plan(plan_id)

    live_status_path = plan_context.plan_dir_for(plan_id) / 'status.json'
    before = live_status_path.read_text(encoding='utf-8')

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=True))

    assert result['status'] == 'success'
    assert result.get('dry_run') is True, f'missing dry_run flag: {result}'
    assert 'would_archive_to' in result
    assert 'archived_to' not in result, f'dry-run must NOT report archived_to: {result}'

    assert not Path(result['would_archive_to']).exists(), (
        f'dry-run created the archive dir at {result["would_archive_to"]} — '
        f'atomic-archive write block leaked into the dry-run path; the '
        f'`if args.dry_run:` early-return must precede the write block.'
    )

    after = live_status_path.read_text(encoding='utf-8')
    assert before == after, (
        'dry-run mutated the live status.json — atomic-archive write '
        'block leaked into the dry-run path; verify the early-return '
        'on args.dry_run runs before the write_status call.'
    )


def test_archive_dry_run_with_reason_does_not_mutate_status(plan_context):
    """--dry-run with --reason must NOT mutate live status.json or archive."""
    plan_id = 'archive-reason-dry-run'
    _seed_finalize_phase_plan(plan_id)

    live_status_path = plan_context.plan_dir_for(plan_id) / 'status.json'
    before = live_status_path.read_text(encoding='utf-8')

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=True, reason='dangling_worktree'))

    assert result['status'] == 'success'
    assert result.get('dry_run') is True, f'missing dry_run flag: {result}'
    assert 'archived_to' not in result, f'dry-run must NOT report archived_to even with --reason: {result}'

    after = live_status_path.read_text(encoding='utf-8')
    assert before == after, (
        'dry-run with --reason mutated live status.json — the metadata '
        'write block leaked past the dry-run early-return.'
    )


def test_archive_dry_run_does_not_fire_findings_gate(plan_context, monkeypatch):
    """A dry-run archive returns before the gate — it makes no state change, so a
    pending finding must not turn a preview into a refusal."""
    _stub_finding_queries(monkeypatch, {'build-error': 1})
    plan_id = 'finalize-dryrun-archive'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=True, reason=None))

    assert result['status'] == 'success'
    assert result.get('dry_run') is True
    assert 'would_archive_to' in result
