# SPDX-License-Identifier: FSL-1.1-ALv2
"""``orchestrator land`` — ``snapshot``, ``bind`` and ``status`` against real git.

A land starts by committing the ledger paths of the shared ledger worktree,
pushing that commit to the remote head branch without force, and recording the
pushed commit in a local-only marker ref. ``bind`` then records which PR carries
it, and ``status`` reports where the tree stands. These tests run every one of
those steps against a real bare ``origin``, a real main checkout and the real
shared worktree — nothing below the handler is mocked — and assert what git
itself holds afterwards: the commit's file list, the refs, and the remote branch.

The sandbox fixture asserts on teardown that the guard file is gone and the
worktree directory still exists, so both hold after EVERY outcome below, the
error ones included.
"""

import subprocess

import _locks_core
import _orchestrator_land
import pytest
from _orchestrator_land_fixtures import (
    LandSandbox,
    bind,
    build_land_sandbox,
    resync,
    snapshot,
    status,
)
from _orchestrator_worktree_fixtures import git, write_marshal
from run_config import read_commit_trailer

_EPIC_MD = '.plan/orchestrator/epic-alpha/epic.md'
_QUEUE_ROW = '.plan/orchestrator/epic-alpha/queue/PLAN-01.json'
_LOG = '.plan/orchestrator/epic-alpha/logs/orchestrator.log'


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    built = build_land_sandbox(tmp_path, monkeypatch)
    yield built
    assert not built.guard.exists(), 'the land guard file must be released after every outcome'
    assert built.tree.is_dir(), 'the shared ledger worktree must survive every outcome'


def _committed_paths(sandbox: LandSandbox, rev: str = 'HEAD') -> list[str]:
    return sorted(git(sandbox.tree, 'show', '--name-only', '--pretty=format:', rev).split())


# =============================================================================
# snapshot — what is committed, pushed and recorded
# =============================================================================


def test_snapshot_commits_only_ledger_paths_and_pushes_them(sandbox):
    """Ledger paths are committed and pushed; a stray file and ``logs/`` are left alone."""
    sandbox.write(_EPIC_MD, '# epic alpha\n')
    sandbox.write(_LOG, 'machine-local audit line\n')
    stray = sandbox.write('notes.txt', 'not ledger state\n')
    (sandbox.tree / 'README.md').write_text('edited outside the ledger\n', encoding='utf-8')

    result = snapshot()

    assert result['status'] == 'success'
    assert result['outcome'] == 'pushed'
    head = sandbox.ref('HEAD')
    assert result['head_sha'] == head
    assert _committed_paths(sandbox) == [_EPIC_MD]
    # The stray file and the non-ledger edit are exactly as they were: uncommitted, unstaged.
    assert stray.read_text(encoding='utf-8') == 'not ledger state\n'
    pending = [line.strip() for line in git(sandbox.tree, 'status', '--porcelain=v1').splitlines()]
    assert sorted(pending) == ['?? notes.txt', 'M README.md']
    # The ignored log is still on disk and was never staged.
    assert (sandbox.tree / _LOG).is_file()
    assert git(sandbox.tree, 'ls-files', '--', _LOG) == ''
    # The pushed commit is what the marker and the remote head branch both name.
    assert sandbox.marker() == head
    assert sandbox.remote_head() == head


def test_snapshot_commit_is_a_conventional_commit_ending_in_the_resolved_trailer(sandbox):
    sandbox.write(_EPIC_MD, '# epic alpha\n')

    snapshot()

    message = git(sandbox.tree, 'log', '-1', '--pretty=%B')
    assert message.splitlines()[0].startswith('chore(orchestrator): ')
    assert message.rstrip().splitlines()[-1] == read_commit_trailer()['trailer']


def test_snapshot_on_a_clean_tree_returns_nothing_to_land(sandbox):
    head_before = sandbox.ref('HEAD')

    result = snapshot()

    assert result['status'] == 'success'
    assert result['outcome'] == 'nothing_to_land'
    assert sandbox.ref('HEAD') == head_before
    assert sandbox.marker() is None
    assert sandbox.remote_head() is None


def test_snapshot_returns_in_flight_and_commits_nothing_while_a_land_is_recorded(sandbox):
    sandbox.write(_EPIC_MD, '# epic alpha\n')
    first = snapshot()
    sandbox.write(_QUEUE_ROW, '{"id": "PLAN-01"}\n')

    result = snapshot()

    assert result['status'] == 'success'
    assert result['outcome'] == 'in_flight'
    assert result['pushed_marker'] == first['head_sha']
    assert sandbox.ref('HEAD') == first['head_sha']
    assert sandbox.marker() == first['head_sha']
    # The new ledger edit is still pending — neither committed nor staged.
    assert git(sandbox.tree, 'status', '--porcelain=v1', '--untracked-files=all') == f'?? {_QUEUE_ROW}'


def test_snapshot_extend_commits_on_top_and_moves_the_marker_and_the_binding(sandbox):
    sandbox.write(_EPIC_MD, '# epic alpha\n')
    first = snapshot()
    bind(7)
    sandbox.write(_QUEUE_ROW, '{"id": "PLAN-01"}\n')

    result = snapshot(extend=True)

    assert result['outcome'] == 'pushed'
    head = sandbox.ref('HEAD')
    assert head != first['head_sha']
    assert sandbox.ref('HEAD~1') == first['head_sha']
    assert _committed_paths(sandbox) == [_QUEUE_ROW]
    assert sandbox.marker() == head
    assert sandbox.bindings() == {f'{_orchestrator_land.BINDING_REF_PREFIX}7': head}
    assert sandbox.remote_head() == head
    assert result['bound_pr'] == 7


@pytest.mark.parametrize('new_edit', [False, True], ids=['nothing-new', 'with-a-new-edit'])
def test_snapshot_extend_recreates_a_deleted_remote_branch(sandbox, new_edit):
    """The push runs under ``--extend`` even with nothing new, so a deleted remote branch comes back."""
    sandbox.write(_EPIC_MD, '# epic alpha\n')
    first = snapshot()
    sandbox.delete_remote_head()
    assert sandbox.remote_head() is None
    if new_edit:
        sandbox.write(_QUEUE_ROW, '{"id": "PLAN-01"}\n')

    result = snapshot(extend=True)

    assert result['outcome'] == 'pushed'
    head = sandbox.ref('HEAD')
    assert (head != first['head_sha']) is new_edit
    assert sandbox.remote_head() == head
    assert sandbox.marker() == head


def test_a_rejected_push_keeps_the_commit_and_records_no_land(sandbox):
    foreign = sandbox.push_foreign_commit_to_remote_head()
    sandbox.write(_EPIC_MD, '# epic alpha\n')

    result = snapshot()

    assert result['status'] == 'error'
    assert result['error'] == 'ledger_push_rejected'
    assert result['remote_branch'] == 'present'
    assert result['remote_branch_contained'] is False
    # The commit was made and is kept; nothing claims it was pushed.
    assert result['head_sha'] == sandbox.ref('HEAD')
    assert _committed_paths(sandbox) == [_EPIC_MD]
    assert sandbox.marker() is None
    assert sandbox.bindings() == {}
    assert sandbox.remote_head() == foreign


def test_snapshot_body_groups_the_changed_paths_per_epic_and_category(sandbox):
    paths = {
        '.plan/orchestrator/epic-alpha/queue/PLAN-01.json': 'queue rows',
        '.plan/orchestrator/epic-alpha/plans/PLAN-01-alpha.md': 'plan specs',
        '.plan/orchestrator/epic-alpha/status.json': 'anchor/header',
        '.plan/orchestrator/epic-alpha/resume_anchor.md': 'anchor/header',
        '.plan/orchestrator/epic-alpha/landings/PLAN-01.md': 'landings',
        '.plan/orchestrator/epic-alpha/inbox/sender-001.md': 'inbox',
        '.plan/orchestrator/epic-alpha/epic.md': 'other',
        '.plan/orchestrator/epic-beta/queue/PLAN-02.json': 'queue rows',
        '.plan/archived-orchestrators/epic-old/epic.md': 'other',
    }
    for path in paths:
        sandbox.write(path, f'content of {path}\n')

    result = snapshot()

    assert result['land_paths'] == len(paths)
    assert result['title'] == f'chore(orchestrator-ledger): land ledger for 3 epics ({len(paths)} paths)'
    sections = result['body'].split('\n## ')
    by_epic = {section.splitlines()[0]: section for section in sections[1:]}
    assert sorted(by_epic) == ['epic-alpha', 'epic-beta', 'epic-old (archived)']
    for path, category in paths.items():
        epic = next(name for name in by_epic if name.split(' ')[0] in path)
        block = by_epic[epic].split(f'**{category}**', 1)
        assert len(block) == 2, f'{epic} carries no {category} group'
        assert f'- `A {path}`' in block[1].split('\n**', 1)[0]
    assert '**anchor/header** (2)' in by_epic['epic-alpha']
    assert 'Co-Authored-By' not in result['body']


def test_snapshot_title_names_the_epic_when_one_epic_changed(sandbox):
    sandbox.write(_EPIC_MD, '# epic alpha\n')

    result = snapshot()

    assert result['title'] == 'chore(orchestrator-ledger): land epic-alpha ledger (1 path)'


def test_the_guard_is_held_while_the_ledger_is_staged(sandbox, monkeypatch):
    """Control for the teardown assertion: the guard file it checks is the one the verb holds."""
    seen: list[bool] = []
    real_stage = _orchestrator_land._stage_ledger

    def observing_stage(checkout):
        seen.append(sandbox.guard.exists())
        return real_stage(checkout)

    monkeypatch.setattr(_orchestrator_land, '_stage_ledger', observing_stage)
    sandbox.write(_EPIC_MD, '# epic alpha\n')

    snapshot()

    assert seen == [True]


def test_the_guarded_budget_ends_before_the_guard_can_be_reclaimed():
    budget = _orchestrator_land._GUARD_WORK_SECONDS + _orchestrator_land._GUARD_ABORT_SECONDS

    assert 0 < budget < _locks_core._GUARD_STALE_SECONDS


def test_git_calls_under_the_guard_are_bounded_by_the_section_budget(sandbox, monkeypatch):
    """Guarded calls run on what is left of the budget; the push, outside the guard, on the plain bound."""
    calls: list[tuple[bool, bool, float | None]] = []
    real_run = subprocess.run

    def recording_run(cmd, **kwargs):
        calls.append((sandbox.guard.exists(), 'push' in cmd, kwargs.get('timeout')))
        return real_run(cmd, **kwargs)

    monkeypatch.setattr(_orchestrator_land.subprocess, 'run', recording_run)
    sandbox.write(_EPIC_MD, '# epic alpha\n')

    result = snapshot()
    recorded = list(calls)

    assert result['outcome'] == 'pushed'
    guarded = [timeout for held, _, timeout in recorded if held]
    assert guarded
    assert all(timeout is not None and 0 < timeout <= _orchestrator_land._GUARD_WORK_SECONDS for timeout in guarded)
    assert [timeout for held, is_push, timeout in recorded if is_push and not held] == [
        _orchestrator_land._GIT_TIMEOUT_SECONDS
    ]


def test_a_guarded_section_out_of_budget_is_a_guard_timeout_that_changes_nothing(sandbox, monkeypatch):
    sandbox.write(_EPIC_MD, '# epic alpha\n')
    before = sandbox.tree_state()
    monkeypatch.setattr(_orchestrator_land, '_GUARD_WORK_SECONDS', 0.0)

    result = snapshot()

    assert result['status'] == 'error'
    assert result['error'] == 'land_guard_timeout'
    assert sandbox.tree_state() == before
    assert sandbox.remote_head() is None


# =============================================================================
# bind
# =============================================================================


def test_bind_refuses_without_a_land_in_flight(sandbox):
    result = bind(7)

    assert result['status'] == 'error'
    assert result['error'] == 'no_land_in_flight'
    assert sandbox.bindings() == {}


def test_bind_writes_exactly_one_binding_ref_and_is_idempotent(sandbox):
    sandbox.write(_EPIC_MD, '# epic alpha\n')
    marker = snapshot()['head_sha']

    first = bind(7)
    second = bind(7)

    assert first == second
    assert first['outcome'] == 'bound'
    assert first['pr_number'] == 7
    assert first['pushed_marker'] == marker
    assert sandbox.bindings() == {f'{_orchestrator_land.BINDING_REF_PREFIX}7': marker}


def test_bind_replaces_an_earlier_binding(sandbox):
    sandbox.write(_EPIC_MD, '# epic alpha\n')
    marker = snapshot()['head_sha']
    bind(7)

    result = bind(9)

    assert result['outcome'] == 'bound'
    assert sandbox.bindings() == {f'{_orchestrator_land.BINDING_REF_PREFIX}9': marker}


# =============================================================================
# status
# =============================================================================


def test_status_reports_pending_work_before_any_land(sandbox):
    sandbox.write(_EPIC_MD, '# epic alpha\n')

    result = status()

    assert result['status'] == 'success'
    assert result['store_checkout'] == str(sandbox.tree)
    assert result['branch'] == 'chore/orchestrator-ledger'
    assert result['base_branch'] == 'main'
    assert result['pending_paths'] == [_EPIC_MD]
    assert result['unpushed_commits'] == 0
    assert result['pushed_marker'] is None
    assert result['bound_pr'] is None
    assert result['remote_branch'] == 'absent'
    # status is read-only: the pending edit is still pending.
    assert git(sandbox.tree, 'status', '--porcelain=v1', '--untracked-files=all') == f'?? {_EPIC_MD}'


def test_status_reports_the_bound_pr_and_a_contained_remote_branch(sandbox):
    sandbox.write(_EPIC_MD, '# epic alpha\n')
    marker = snapshot()['head_sha']
    bind(7)

    result = status()

    assert result['pending_paths'] == []
    assert result['unpushed_commits'] == 0
    assert result['pushed_marker'] == marker
    assert result['bound_pr'] == 7
    assert result['remote_branch'] == 'present'
    assert result['remote_branch_contained'] is True


def test_status_counts_commits_made_after_the_pushed_marker(sandbox):
    sandbox.write(_EPIC_MD, '# epic alpha\n')
    snapshot()
    sandbox.write(_QUEUE_ROW, '{"id": "PLAN-01"}\n')
    git(sandbox.tree, 'add', _QUEUE_ROW)
    git(sandbox.tree, 'commit', '-m', 'chore(orchestrator): a later ledger write')

    assert status()['unpushed_commits'] == 1


def test_status_reports_a_diverged_remote_branch_as_not_contained(sandbox):
    sandbox.write(_EPIC_MD, '# epic alpha\n')
    snapshot()
    sandbox.push_foreign_commit_to_remote_head()

    result = status()

    assert result['remote_branch'] == 'present'
    assert result['remote_branch_contained'] is False


def test_status_reports_an_unreachable_remote_as_unknown_never_absent(sandbox, tmp_path):
    git(sandbox.repo.main, 'remote', 'set-url', 'origin', str(tmp_path / 'no-such-remote.git'))

    result = status()

    assert result['remote_branch'] == 'unknown'
    assert result['remote_branch_contained'] == 'unknown'


# =============================================================================
# knob off
# =============================================================================


@pytest.mark.parametrize(
    'verb',
    [status, snapshot, lambda: bind(7), lambda: resync(7, '0123456789abcdef0123456789abcdef01234567')],
    ids=['status', 'snapshot', 'bind', 'resync'],
)
def test_every_verb_refuses_while_the_knob_is_off(sandbox, verb):
    sandbox.write(_EPIC_MD, '# epic alpha\n')
    write_marshal(sandbox.repo.main, {'orchestrator': {'use_worktree': False}})
    before = sandbox.tree_state()

    result = verb()

    assert result['status'] == 'error'
    assert result['error'] == 'land_requires_use_worktree'
    assert sandbox.tree_state() == before
    assert sandbox.remote_head() is None
