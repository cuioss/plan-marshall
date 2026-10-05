# SPDX-License-Identifier: FSL-1.1-ALv2
"""``orchestrator land resync`` against real git with a squash-merged base.

Once the land's PR has merged, the shared ledger worktree must continue on top
of the new base WITHOUT losing anything written to it since the snapshot. The
landing is a squash, so the commit on the base shares no ancestry with the
commits the tree pushed: ``resync`` therefore verifies the landed CONTENT, then
replays everything after the pushed marker onto the base.

Every test runs the real git sequence against a bare ``origin`` whose ``main`` a
peer clone squash-merges the pushed ledger branch into. Nothing below the handler
is mocked. A refusal is asserted to leave HEAD, the index, the working tree and
both land refs exactly as they were.

The sandbox fixture asserts on teardown that the guard file is gone and the
worktree directory still exists, so both hold after EVERY outcome below.
"""

import _orchestrator_land
import pytest
from _orchestrator_land_fixtures import (
    LandSandbox,
    bind,
    build_land_sandbox,
    resync,
    snapshot,
)
from _orchestrator_worktree_fixtures import git

_EPIC_MD = '.plan/orchestrator/epic-alpha/epic.md'
_QUEUE_ROW = '.plan/orchestrator/epic-alpha/queue/PLAN-01.json'
_LANDING = '.plan/orchestrator/epic-alpha/landings/PLAN-01.md'
_OTHER_EPIC = '.plan/orchestrator/epic-beta/epic.md'
_PR = 7
_BINDING = f'{_orchestrator_land.BINDING_REF_PREFIX}{_PR}'


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    built = build_land_sandbox(tmp_path, monkeypatch)
    yield built
    assert not built.guard.exists(), 'the land guard file must be released after every outcome'
    assert built.tree.is_dir(), 'the shared ledger worktree must survive every outcome'


def _push_a_land_of_two_commits(sandbox: LandSandbox) -> str:
    """Snapshot, extend with a second commit, bind the PR; return the pushed marker."""
    sandbox.write(_EPIC_MD, '# epic alpha\n')
    snapshot()
    sandbox.write(_QUEUE_ROW, '{"id": "PLAN-01"}\n')
    snapshot(extend=True)
    bind(_PR)
    marker = sandbox.marker()
    assert marker is not None
    assert git(sandbox.tree, 'rev-list', '--count', f'origin/main..{marker}') == '2'
    return marker


def _commit_in_tree(sandbox: LandSandbox, relpath: str, content: str) -> str:
    sandbox.write(relpath, content)
    git(sandbox.tree, 'add', relpath)
    git(sandbox.tree, 'commit', '-m', f'chore(orchestrator): write {relpath}')
    return git(sandbox.tree, 'rev-parse', 'HEAD')


def _read(sandbox: LandSandbox, relpath: str) -> str:
    return (sandbox.tree / relpath).read_text(encoding='utf-8')


# =============================================================================
# The landing path
# =============================================================================


def test_resync_after_a_squash_landing_puts_the_tree_on_the_base(sandbox):
    """Several pushed commits landed as ONE squash commit: the tree ends on it, cycle closed."""
    _push_a_land_of_two_commits(sandbox)
    merge = sandbox.squash_land()

    result = resync(_PR, merge)

    assert result['status'] == 'success'
    assert result['outcome'] == 'resynced'
    assert result['already_resynced'] is False
    assert result['replayed_commits'] == 0
    assert result['carried_uncommitted'] is False
    assert sandbox.ref('HEAD') == merge
    assert sandbox.ref('origin/main') == merge
    assert git(sandbox.tree, 'rev-parse', '--abbrev-ref', 'HEAD') == 'chore/orchestrator-ledger'
    assert git(sandbox.tree, 'status', '--porcelain=v1') == ''
    assert _read(sandbox, _EPIC_MD) == '# epic alpha\n'
    assert _read(sandbox, _QUEUE_ROW) == '{"id": "PLAN-01"}\n'
    # The cycle is closed: no marker, no binding.
    assert sandbox.marker() is None
    assert sandbox.bindings() == {}


def test_resync_fast_forwards_the_primary_checkout_base_branch(sandbox):
    _push_a_land_of_two_commits(sandbox)
    before = sandbox.ref('main', cwd=sandbox.repo.main)
    merge = sandbox.squash_land()

    result = resync(_PR, merge)

    assert before != merge
    assert result['main_fast_forward'] == 'done'
    assert sandbox.ref('main', cwd=sandbox.repo.main) == merge
    assert (sandbox.repo.main / _EPIC_MD).is_file()


def test_post_snapshot_commit_and_uncommitted_edit_both_survive_the_resync(sandbox):
    _push_a_land_of_two_commits(sandbox)
    _commit_in_tree(sandbox, _LANDING, '# landed after the snapshot\n')
    sandbox.write(_EPIC_MD, '# epic alpha\n\nedited while the PR was in the queue\n')
    sandbox.write(_OTHER_EPIC, '# a new epic, not yet added\n')
    merge = sandbox.squash_land()

    result = resync(_PR, merge)

    assert result['outcome'] == 'resynced'
    assert result['replayed_commits'] == 1
    assert result['carried_uncommitted'] is True
    # The post-snapshot commit now sits directly on the landed commit.
    assert sandbox.ref('HEAD~1') == merge
    assert git(sandbox.tree, 'show', '--name-only', '--pretty=format:', 'HEAD') == _LANDING
    assert _read(sandbox, _LANDING) == '# landed after the snapshot\n'
    # The uncommitted edit and the untracked file are still uncommitted, content intact.
    assert _read(sandbox, _EPIC_MD) == '# epic alpha\n\nedited while the PR was in the queue\n'
    assert _read(sandbox, _OTHER_EPIC) == '# a new epic, not yet added\n'
    pending = [line.strip() for line in git(sandbox.tree, 'status', '--porcelain=v1', '-uall').splitlines()]
    assert sorted(pending) == [f'?? {_OTHER_EPIC}', f'M {_EPIC_MD}']


def test_an_unrelated_ledger_path_changed_on_the_base_does_not_trip_the_content_check(sandbox):
    """Another landing touched a ledger path this land never changed: not a mismatch."""
    _push_a_land_of_two_commits(sandbox)
    sandbox.repo.advance_origin(_OTHER_EPIC)
    merge = sandbox.squash_land()

    result = resync(_PR, merge)

    assert result['outcome'] == 'resynced'
    assert sandbox.ref('HEAD') == merge
    assert (sandbox.tree / _OTHER_EPIC).is_file()


# =============================================================================
# Refusals — each changes nothing
# =============================================================================


def test_resync_refuses_without_a_land_in_flight(sandbox):
    sandbox.write(_EPIC_MD, '# epic alpha\n')
    base = sandbox.ref('origin/main')
    assert base is not None
    before = sandbox.tree_state()

    result = resync(_PR, base)

    assert result['status'] == 'error'
    assert result['error'] == 'no_land_in_flight'
    assert sandbox.tree_state() == before


@pytest.mark.parametrize('which', ['pushed-but-not-landed', 'unknown-commit'])
def test_resync_refuses_a_merge_commit_that_is_not_on_the_base(sandbox, which):
    marker = _push_a_land_of_two_commits(sandbox)
    merge_sha = marker if which == 'pushed-but-not-landed' else 'f' * 40
    before = sandbox.tree_state()

    result = resync(_PR, merge_sha)

    assert result['status'] == 'error'
    assert result['error'] == 'merge_commit_not_on_base'
    assert sandbox.tree_state() == before
    assert sandbox.remote_head() == marker


def test_resync_refuses_when_the_landed_content_differs_from_what_was_pushed(sandbox):
    marker = _push_a_land_of_two_commits(sandbox)
    main_before = sandbox.ref('main', cwd=sandbox.repo.main)
    merge = sandbox.squash_land(tamper=_EPIC_MD)
    before = sandbox.tree_state()

    result = resync(_PR, merge)

    assert result['status'] == 'error'
    assert result['error'] == 'resync_content_mismatch'
    assert result['mismatched_paths'] == [_EPIC_MD]
    assert sandbox.tree_state() == before
    # Nothing past the content check ran: remote branch kept, primary checkout not moved.
    assert sandbox.remote_head() == marker
    assert sandbox.ref('main', cwd=sandbox.repo.main) == main_before


def test_a_conflicting_replay_is_aborted_and_leaves_the_tree_exactly_as_it_was(sandbox):
    marker = _push_a_land_of_two_commits(sandbox)
    _commit_in_tree(sandbox, _EPIC_MD, '# epic alpha\n\nthe tree changed this line\n')
    sandbox.write(_QUEUE_ROW, '{"id": "PLAN-01", "status": "running"}\n')
    merge = sandbox.squash_land()
    # A later commit on the base rewrites the path the post-snapshot commit also rewrote.
    sandbox.repo.advance_origin(_EPIC_MD)
    before = sandbox.tree_state()
    epic_before = _read(sandbox, _EPIC_MD)
    row_before = _read(sandbox, _QUEUE_ROW)

    result = resync(_PR, merge)

    assert result['status'] == 'error'
    assert result['error'] == 'resync_conflict'
    assert result['head_restored'] is True
    assert result['pre_rebase_sha'] == before[0]
    assert result['stderr']
    # HEAD, index, working tree and both refs are identical to before.
    assert sandbox.tree_state() == before
    assert _read(sandbox, _EPIC_MD) == epic_before
    assert _read(sandbox, _QUEUE_ROW) == row_before
    assert git(sandbox.tree, 'rev-parse', '--abbrev-ref', 'HEAD') == 'chore/orchestrator-ledger'
    assert sandbox.marker() == marker
    assert sandbox.bindings() == {_BINDING: marker}


def test_a_replay_that_runs_out_of_the_guard_budget_is_aborted_like_a_conflict(sandbox, monkeypatch):
    marker = _push_a_land_of_two_commits(sandbox)
    _commit_in_tree(sandbox, _LANDING, '# landed after the snapshot\n')
    merge = sandbox.squash_land()
    before = sandbox.tree_state()
    real_git = _orchestrator_land._git

    def git_whose_replay_runs_out(cwd, *args):
        if args[0] == 'rebase' and '--abort' not in args:
            raise TimeoutError('the guarded land section ran out of its time budget')
        return real_git(cwd, *args)

    monkeypatch.setattr(_orchestrator_land, '_git', git_whose_replay_runs_out)

    result = resync(_PR, merge)

    assert result['status'] == 'error'
    assert result['error'] == 'resync_conflict'
    assert result['head_restored'] is True
    assert 'time budget' in result['stderr']
    assert sandbox.tree_state() == before
    assert sandbox.marker() == marker


def test_a_guard_timeout_reports_the_steps_that_already_ran_and_a_rerun_closes_the_cycle(sandbox, monkeypatch):
    marker = _push_a_land_of_two_commits(sandbox)
    merge = sandbox.squash_land()
    before = sandbox.tree_state()

    with monkeypatch.context() as patched:
        patched.setattr(_orchestrator_land, '_GUARD_WORK_SECONDS', 0.0)
        result = resync(_PR, merge)

    assert result['status'] == 'error'
    assert result['error'] == 'land_guard_timeout'
    # The steps ahead of the guard ran and are reported; the tree and both refs are untouched.
    assert result['main_fast_forward'] == 'done'
    assert result['remote_branch_cleanup'] == 'deleted'
    assert sandbox.ref('main', cwd=sandbox.repo.main) == merge
    assert sandbox.remote_head() is None
    assert sandbox.tree_state() == before
    assert sandbox.marker() == marker

    rerun = resync(_PR, merge)

    assert rerun['outcome'] == 'resynced'
    assert rerun['remote_branch_cleanup'] == 'already_absent'
    assert sandbox.ref('HEAD') == merge
    assert sandbox.marker() is None


def test_a_second_resync_after_a_rebase_by_hand_only_closes_the_cycle(sandbox):
    marker = _push_a_land_of_two_commits(sandbox)
    merge = sandbox.squash_land()
    git(sandbox.tree, 'fetch', 'origin', 'main')
    git(sandbox.tree, 'rebase', '--onto', 'origin/main', marker)
    assert sandbox.ref('HEAD') == merge
    assert sandbox.marker() == marker

    result = resync(_PR, merge)

    assert result['outcome'] == 'resynced'
    assert result['already_resynced'] is True
    assert result['replayed_commits'] == 0
    assert sandbox.ref('HEAD') == merge
    assert sandbox.marker() is None
    assert sandbox.bindings() == {}


# =============================================================================
# The landed remote head branch
# =============================================================================


def test_the_remote_head_branch_is_deleted_while_it_still_points_at_the_marker(sandbox):
    marker = _push_a_land_of_two_commits(sandbox)
    merge = sandbox.squash_land()
    assert sandbox.remote_head() == marker

    result = resync(_PR, merge)

    assert result['remote_branch_cleanup'] == 'deleted'
    assert sandbox.remote_head() is None


def test_an_already_deleted_remote_head_branch_is_reported_as_already_absent(sandbox):
    _push_a_land_of_two_commits(sandbox)
    merge = sandbox.squash_land()
    sandbox.delete_remote_head()

    result = resync(_PR, merge)

    assert result['outcome'] == 'resynced'
    assert result['remote_branch_cleanup'] == 'already_absent'


def test_a_remote_head_branch_that_moved_past_the_marker_is_kept(sandbox):
    """The remote branch gained a commit after the land: deleting it would lose unlanded work."""
    _push_a_land_of_two_commits(sandbox)
    merge = sandbox.squash_land()
    moved_to = sandbox.push_foreign_commit_to_remote_head()

    result = resync(_PR, merge)

    assert result['outcome'] == 'resynced'
    assert result['remote_branch_cleanup'] == 'kept_diverged'
    assert sandbox.remote_head() == moved_to
