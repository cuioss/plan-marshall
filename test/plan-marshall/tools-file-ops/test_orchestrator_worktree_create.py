#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Creation lifecycle and drift detection of the shared orchestrator ledger worktree.

Covers ``ensure_orchestrator_worktree`` — first-use creation off
``origin/{base}``, unchanged reuse, local-branch reuse, the switch-on cutover
refusal, the unresolvable-base refusal, and the lost-race recovery — plus
``detect_ledger_drift`` directly. The resolution surface lives in
``test_orchestrator_worktree.py``.

Every case runs the real ``git worktree add`` against a real sandbox with a
bare ``origin`` remote; the only substitution is the lost-race case, which
hides an already-registered tree from the first registration probe to put the
add on the losing side of a race that cannot be scheduled deterministically.
"""

import orchestrator_worktree
import pytest
from _orchestrator_worktree_fixtures import build_ledger_repo, commit_file, git, use_real_resolver, write_marshal
from orchestrator_worktree import (
    ORCHESTRATOR_WORKTREE_BRANCH,
    OrchestratorStoreUnavailable,
    detect_ledger_drift,
    ensure_orchestrator_worktree,
)


@pytest.fixture
def ledger_repo(tmp_path, monkeypatch):
    """A real sandbox with the cwd on its main checkout and no base-dir override."""
    use_real_resolver(monkeypatch)
    repo = build_ledger_repo(tmp_path)
    monkeypatch.chdir(repo.main)
    return repo


def _head(checkout) -> str:
    return git(checkout, 'rev-parse', 'HEAD')


def _branch(checkout) -> str:
    return git(checkout, 'symbolic-ref', '--short', 'HEAD')


_LEDGER_PATH = '.plan/orchestrator/epic-a/status.json'
_LEDGER_CONTENT = '{"phase": "execute"}\n'


def _land_on_origin(repo, content: str) -> None:
    """Land ``content`` at the ledger path on ``origin/main`` under a fresh SHA, then fetch it."""
    commit_file(repo.peer, _LEDGER_PATH, content)
    git(repo.peer, 'push', 'origin', 'main')
    git(repo.main, 'fetch', 'origin', 'main')


class TestFirstUse:
    """The first call creates the tree on the ledger branch at the fetched base."""

    def test_creates_the_worktree_on_the_ledger_branch_at_the_fetched_origin_tip(self, ledger_repo):
        """The tree lands on ``origin/main`` as it stands on the remote.

        The peer advances ``origin`` after the main checkout last fetched, so a
        tree created from a stale local ``origin/main`` would sit one commit back.
        """
        remote_tip = ledger_repo.advance_origin('docs/remote-only.md')

        path = ensure_orchestrator_worktree()

        assert (path.resolve(), _branch(path), _head(path)) == (
            ledger_repo.expected_worktree,
            ORCHESTRATOR_WORKTREE_BRANCH,
            remote_tip,
        )

    def test_creates_the_tree_at_the_main_anchored_location_from_a_plan_worktree(self, ledger_repo, monkeypatch):
        monkeypatch.chdir(ledger_repo.plan_worktree)

        path = ensure_orchestrator_worktree()

        assert path.resolve() == ledger_repo.expected_worktree
        assert (ledger_repo.expected_worktree / 'README.md').is_file()

    def test_bases_the_tree_on_the_configured_default_base_branch(self, ledger_repo):
        git(ledger_repo.peer, 'checkout', '-b', 'develop')
        develop_tip = commit_file(ledger_repo.peer, 'docs/develop-only.md', 'develop\n')
        git(ledger_repo.peer, 'push', 'origin', 'develop')
        write_marshal(ledger_repo.main, {'project': {'default_base_branch': 'develop'}})

        path = ensure_orchestrator_worktree()

        assert _head(path) == develop_tip


class TestReuse:
    """An existing tree or branch is reused exactly as found."""

    def test_second_use_returns_the_existing_tree_unchanged(self, ledger_repo):
        first = ensure_orchestrator_worktree()
        head_before = _head(first)
        marker = first / 'untracked-marker.txt'
        marker.write_text('survives\n', encoding='utf-8')
        ledger_repo.advance_origin('docs/after-first-use.md')

        second = ensure_orchestrator_worktree()

        assert (second, _head(second), marker.is_file()) == (first, head_before, True)

    def test_reuses_an_existing_local_ledger_branch(self, ledger_repo):
        """An existing ``chore/orchestrator-ledger`` is checked out, not recreated.

        The branch points at the main checkout's commit while ``origin/main``
        has moved on, so a tree recreated from the base would carry the remote tip.
        """
        branch_tip = _head(ledger_repo.main)
        git(ledger_repo.main, 'branch', ORCHESTRATOR_WORKTREE_BRANCH, branch_tip)
        ledger_repo.advance_origin('docs/remote-only.md')

        path = ensure_orchestrator_worktree()

        assert (_branch(path), _head(path)) == (ORCHESTRATOR_WORKTREE_BRANCH, branch_tip)


class TestCutoverRefusal:
    """Uncommitted or unlanded ledger paths on the main checkout refuse creation."""

    def test_refuses_naming_every_dirty_and_unlanded_ledger_path(self, ledger_repo):
        commit_file(ledger_repo.main, '.plan/orchestrator/epic-a/status.json', '{}\n')
        git(ledger_repo.main, 'push', 'origin', 'main')
        (ledger_repo.main / '.plan/orchestrator/epic-a/status.json').write_text('{"edited": true}\n', encoding='utf-8')
        (ledger_repo.main / '.plan/orchestrator/epic-b').mkdir(parents=True)
        (ledger_repo.main / '.plan/orchestrator/epic-b/inbox.md').write_text('untracked\n', encoding='utf-8')
        commit_file(ledger_repo.main, '.plan/archived-orchestrators/epic-c/status.json', '{}\n')
        (ledger_repo.main / 'notes.md').write_text('non-ledger dirt\n', encoding='utf-8')

        with pytest.raises(OrchestratorStoreUnavailable) as exc_info:
            ensure_orchestrator_worktree()

        assert (exc_info.value.code, exc_info.value.fields['dirty_paths']) == (
            'ledger_cutover_refused',
            [
                '.plan/archived-orchestrators/epic-c/status.json',
                '.plan/orchestrator/epic-a/status.json',
                '.plan/orchestrator/epic-b/inbox.md',
            ],
        )
        assert not ledger_repo.expected_worktree.exists()

    def test_non_ledger_dirt_does_not_refuse(self, ledger_repo):
        """Matched negative control: dirt outside the ledger store never blocks the cutover.

        The main checkout carries an uncommitted file, an unpushed commit and a
        landed, clean ledger file — every shape the refusal above keys on, minus
        the ledger location.
        """
        commit_file(ledger_repo.main, '.plan/orchestrator/epic-a/status.json', '{}\n')
        git(ledger_repo.main, 'push', 'origin', 'main')
        commit_file(ledger_repo.main, 'docs/unpushed.md', 'local only\n')
        (ledger_repo.main / 'notes.md').write_text('non-ledger dirt\n', encoding='utf-8')

        path = ensure_orchestrator_worktree()

        assert path.resolve() == ledger_repo.expected_worktree


class TestBaseRefUnresolvable:
    """A base the remote does not carry refuses before any tree is created."""

    def test_refuses_with_base_ref_unresolvable(self, ledger_repo):
        write_marshal(ledger_repo.main, {'project': {'default_base_branch': 'no-such-branch'}})

        with pytest.raises(OrchestratorStoreUnavailable) as exc_info:
            ensure_orchestrator_worktree()

        assert (exc_info.value.code, exc_info.value.fields['base_ref']) == (
            'base_ref_unresolvable',
            'origin/no-such-branch',
        )
        assert not ledger_repo.expected_worktree.exists()


class TestLostRace:
    """A failed add that leaves a valid ledger tree behind is a success.

    The positive case and :meth:`test_occupied_non_worktree_path_fails` are a
    matched pair: in both, ``git worktree add`` fails because the path is taken.
    Only the post-add re-check tells a winning peer's tree from an unusable
    directory, so the pair attributes the success to that re-check.
    """

    def test_returns_success_when_a_peer_created_the_tree_between_check_and_add(self, ledger_repo, monkeypatch):
        git(
            ledger_repo.main,
            'worktree',
            'add',
            '-b',
            ORCHESTRATOR_WORKTREE_BRANCH,
            str(ledger_repo.expected_worktree),
            'origin/main',
        )
        real_probe = orchestrator_worktree._registered_worktree_branch
        scripted_first_answer = iter([None])
        probe_results = []

        def probe_blind_to_the_first_check(main_root, path):
            result = next(scripted_first_answer, real_probe(main_root, path))
            probe_results.append(result)
            return result

        monkeypatch.setattr(orchestrator_worktree, '_registered_worktree_branch', probe_blind_to_the_first_check)

        path = ensure_orchestrator_worktree()

        assert (path.resolve(), probe_results) == (
            ledger_repo.expected_worktree,
            [None, ORCHESTRATOR_WORKTREE_BRANCH],
        )

    def test_occupied_non_worktree_path_fails(self, ledger_repo):
        ledger_repo.expected_worktree.mkdir(parents=True)
        (ledger_repo.expected_worktree / 'stray.txt').write_text('not a worktree\n', encoding='utf-8')

        with pytest.raises(OrchestratorStoreUnavailable) as exc_info:
            ensure_orchestrator_worktree()

        assert exc_info.value.code == 'orchestrator_worktree_create_failed'
        assert exc_info.value.fields['branch'] == ORCHESTRATOR_WORKTREE_BRANCH


class TestDetectLedgerDrift:
    """``detect_ledger_drift`` reports ledger paths only, and never a false clean."""

    def test_is_empty_for_a_clean_landed_checkout(self, ledger_repo):
        commit_file(ledger_repo.main, '.plan/orchestrator/epic-a/status.json', '{}\n')
        git(ledger_repo.main, 'push', 'origin', 'main')

        assert detect_ledger_drift(ledger_repo.main, 'origin/main') == []

    def test_reports_both_sides_of_a_staged_ledger_rename(self, ledger_repo):
        commit_file(ledger_repo.main, '.plan/orchestrator/epic-a/status.json', '{}\n')
        git(ledger_repo.main, 'push', 'origin', 'main')
        git(ledger_repo.main, 'mv', '.plan/orchestrator/epic-a/status.json', '.plan/orchestrator/epic-a/moved.json')

        drift = detect_ledger_drift(ledger_repo.main, 'origin/main')

        assert drift == ['.plan/orchestrator/epic-a/moved.json', '.plan/orchestrator/epic-a/status.json']

    @pytest.mark.parametrize(
        ('landed_content', 'expected'),
        [(_LEDGER_CONTENT, []), ('{"diverged": true}\n', [_LEDGER_PATH])],
        ids=['squash-landed-content-is-not-drift', 'content-absent-from-the-base-is-drift'],
    )
    def test_unlanded_is_decided_by_content_not_commit_ancestry(self, ledger_repo, landed_content, expected):
        """A ledger commit whose content reached the base under a different SHA is landed.

        The main checkout's ledger commit is never an ancestor of ``origin/main``;
        the peer lands content on the base the way a squash merge does. Only the
        landed content differs between the two cases.
        """
        commit_file(ledger_repo.main, _LEDGER_PATH, _LEDGER_CONTENT)
        _land_on_origin(ledger_repo, landed_content)

        assert detect_ledger_drift(ledger_repo.main, 'origin/main') == expected

    def test_ledger_content_only_on_the_base_is_not_drift(self, ledger_repo):
        """A ledger change the base carries and the checkout lacks strands nothing."""
        _land_on_origin(ledger_repo, _LEDGER_CONTENT)

        assert detect_ledger_drift(ledger_repo.main, 'origin/main') == []

    def test_raises_unevaluable_for_an_unknown_base_ref(self, ledger_repo):
        with pytest.raises(OrchestratorStoreUnavailable) as exc_info:
            detect_ledger_drift(ledger_repo.main, 'origin/no-such-branch')

        assert (exc_info.value.code, exc_info.value.fields['base_ref']) == (
            'ledger_drift_unevaluable',
            'origin/no-such-branch',
        )

    def test_raises_unevaluable_outside_a_repository(self, tmp_path, monkeypatch):
        outside = tmp_path / 'outside'
        outside.mkdir()
        monkeypatch.setenv('GIT_CEILING_DIRECTORIES', str(tmp_path))

        with pytest.raises(OrchestratorStoreUnavailable) as exc_info:
            detect_ledger_drift(outside, 'origin/main')

        assert exc_info.value.code == 'ledger_drift_unevaluable'
