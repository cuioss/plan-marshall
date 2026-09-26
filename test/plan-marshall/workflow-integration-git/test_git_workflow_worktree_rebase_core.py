#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for git_workflow.py worktree-rebase-to subcommand.

Covers all eight documented worktree states the rebase dispatcher
recognises (per the docstring on ``_detect_worktree_state``):

    1. clean         — branch already at base; rebase is a no-op.
    2. dirty         — uncommitted changes; reject without touching git.
    3. ahead         — branch has commits base lacks. A STRICTLY-ahead branch
                       (behind == 0) already contains base, so the rebase
                       replays nothing and HEAD is unchanged: action ``noop``.
                       A diverged branch (ahead > 0 AND behind > 0, which
                       ``_detect_worktree_state`` also labels ``ahead``) does
                       replay and moves HEAD: action ``rebased``.
    4. behind        — base has commits branch lacks; rebase fast-forwards.
    5. conflict      — rebase produces conflicts; status: conflict, with
                       conflict paths reported.
    6. detached      — HEAD is detached; reject.
    7. missing-base  — base ref does not resolve; error.
    8. missing-target — worktree path absent on disk OR the plan does
                        not exist (resolution fails); error.

The tests use temporary git repositories as fixtures and exercise
``cmd_worktree_rebase_to`` via direct import. Plan-id resolution is
short-circuited by monkeypatching ``_resolve_worktree_path_for_plan``
so the tests never depend on the real plan-marshall executor or any
``manage-status`` state on disk.

Rebase target: ``cmd_worktree_rebase_to`` fetches
``origin/{base}`` and rebases onto the fetched remote tip — NOT the stale
local ``{base}`` ref. The fixtures clone from ``main_repo`` (so the worktree
has an ``origin`` remote and ``origin/main``); the base-advancing helper commits
to ``origin``'s (``main_repo``'s) ``main`` so the worktree's
``git fetch origin main`` (run by the production code) observes the advance.
``TestRebaseToStaleLocalBaseRegression`` asserts the defect fix directly:
``origin/main`` advanced past the worktree's local ``main`` is fully absorbed by
a SINGLE rebase. ``TestRebaseToNoRemoteFallback`` covers the soft-fallback to the
local ``{base}`` ref when the worktree has no ``origin`` remote.

There is no sibling ``conftest.py`` here on purpose — module-level
helper functions defined below provide the shared fixture-build
logic that pytest discovery cannot reach via auto-loading. See
``test/plan-marshall/plan-retrospective/_plan_retrospective_fixtures.py`` for the wider
project convention.
"""

from __future__ import annotations

import subprocess
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import load_script_module

# The entrypoint filename is kebab-case (git-workflow.py), which is not a
# valid Python module identifier — load it via importlib instead of `import`.
git_workflow = load_script_module('plan-marshall', 'workflow-integration-git', 'git-workflow.py', 'git_workflow')
_detect_worktree_state = git_workflow._detect_worktree_state
cmd_worktree_rebase_to = git_workflow.cmd_worktree_rebase_to


# ---------------------------------------------------------------------------
# Module-level fixture helpers (mirrors test/plan-marshall/plan-retrospective
# convention: no sibling conftest.py — explicit helpers callers invoke).
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run ``git -C {repo} args`` and return the CompletedProcess."""
    return subprocess.run(
        ['git', '-C', str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def _init_main_repo(repo: Path) -> None:
    """Initialise a main repo with a single committed file on ``main``.

    Adds a tracked ``.gitignore`` so ``git worktree`` operations on derived
    worktrees do not get tripped up by untracked ``.plan/`` content.
    """
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, 'init', '-q', '-b', 'main')
    _git(repo, 'config', 'user.email', 't@t.test')
    _git(repo, 'config', 'user.name', 'Test')
    (repo / '.gitignore').write_text('.plan/\n')
    (repo / 'file.txt').write_text('line 1\n')
    _git(repo, 'add', '.')
    _git(repo, 'commit', '-q', '-m', 'init')


def _create_branch_worktree(main_repo: Path, worktree: Path, branch: str) -> None:
    """Create ``branch`` and check it out in a sibling repo at ``worktree``.

    Uses ``git clone`` rather than ``git worktree add`` so the resulting
    directory has its own ``.git`` *directory* (not a worktree pointer file).
    This matters for the conflict-detection code in ``cmd_worktree_rebase_to``
    which probes ``target / '.git' / 'rebase-merge'`` directly: in a real
    ``git worktree add`` checkout that path resolves through the pointer file
    and never matches, so the conflict state would mis-classify as
    ``rebase_failed``. The rebase dispatcher only requires that ``target`` is a
    working tree pointing at the branch we want to rebase, so a clone is
    semantically equivalent for the purposes of these tests while keeping the
    conflict path observable. Both repos share the same base commit because the
    clone is taken from ``main_repo``.
    """
    worktree.parent.mkdir(parents=True, exist_ok=True)
    _git(main_repo, 'clone', '-q', str(main_repo), str(worktree))
    _git(worktree, 'config', 'user.email', 't@t.test')
    _git(worktree, 'config', 'user.name', 'Test')
    # ``git clone`` checks out the default branch (``main`` here) and registers
    # ``origin/main``. Create a local feature branch off of ``main`` and check it
    # out so the rebase target is the branch the production code expects.
    _git(worktree, 'checkout', '-q', '-b', branch, 'main')


def _commit_file(repo: Path, name: str, content: str, message: str) -> None:
    """Create or overwrite ``name`` with ``content`` and commit it."""
    (repo / name).write_text(content)
    _git(repo, 'add', name)
    _git(repo, 'commit', '-q', '-m', message)


def _advance_main_via_branch_switch(repo: Path, name: str, content: str, message: str, current_branch: str) -> None:
    """Commit ``name`` to ``main`` from inside ``repo`` and return to ``current_branch``.

    Used when the test fixture is a clone (rather than a worktree sharing object
    DB with the source repo). The clone has its own ``main`` ref, so advancing
    the base requires checking it out, committing, then restoring the feature
    branch.
    """
    _git(repo, 'checkout', '-q', 'main')
    _commit_file(repo, name, content, message)
    _git(repo, 'checkout', '-q', current_branch)


def _advance_origin_main(origin_repo: Path, name: str, content: str, message: str) -> None:
    """Commit ``name`` to ``origin_repo``'s ``main`` (the remote the worktree clones).

    The rebase targets ``origin/{base}``, so advancing the
    base means committing to the ORIGIN's ``main`` (``main_repo``), then letting
    the production code's ``git fetch origin main`` pull the advance into the
    worktree's ``origin/main`` remote-tracking ref. The worktree's OWN local
    ``main`` is deliberately left stale to reproduce the defect scenario.
    """
    _commit_file(origin_repo, name, content, message)


# ---------------------------------------------------------------------------
# Shared fixture + rebase-invocation helper (replaces the historical
# unittest _RebaseTestBase setUp/tearDown + manual monkeypatch swap).
# ---------------------------------------------------------------------------


@pytest.fixture
def rebase_env(tmp_path: Path) -> dict:
    """Stage a main repo + worktree-path slot under an isolated tmp tree."""
    main_repo = tmp_path / 'main'
    # Worktree lives outside .claude/worktrees/ on purpose — the rebase
    # dispatcher does not enforce a particular layout, only that the path
    # resolves to a real git worktree.
    worktree = tmp_path / 'worktrees' / 'plan-x'
    _init_main_repo(main_repo)
    return {'tmp_root': tmp_path, 'main_repo': main_repo, 'worktree': worktree}


def _invoke_rebase(
    env: dict,
    monkeypatch: pytest.MonkeyPatch,
    *,
    base: str = 'main',
    plan_id: str = 'plan-x',
    resolver_target: Path | None = None,
    resolver_error: dict | None = None,
    main_root: Path | None = None,
) -> dict:
    """Invoke ``cmd_worktree_rebase_to`` with the shared monkeypatch shim.

    ``resolver_target`` defaults to the staged worktree; ``main_root`` (the
    base-ref resolution anchor) defaults to the same worktree, since the fixture
    uses ``git clone`` (so ``.git`` is a real directory) and the cloned repo IS
    its own object DB.
    """
    target = resolver_target if resolver_target is not None else env['worktree']
    root = main_root if main_root is not None else target

    monkeypatch.setattr(git_workflow, '_resolve_worktree_path_for_plan', lambda _pid: (target, resolver_error))
    monkeypatch.setattr(git_workflow, '_find_plan_root_from_cwd', lambda: root)

    result: dict = cmd_worktree_rebase_to(Namespace(plan_id=plan_id, base=base))
    return result


# ---------------------------------------------------------------------------
# State 1 — clean
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# State 1 — clean
# ---------------------------------------------------------------------------


class TestRebaseToClean:
    """Branch already at base — rebase is a no-op success."""

    def test_clean_state_returns_noop_success(self, rebase_env: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        _create_branch_worktree(rebase_env['main_repo'], rebase_env['worktree'], 'feature/clean')
        # No commits on either side — branch and base point at the same SHA.

        result = _invoke_rebase(rebase_env, monkeypatch)

        assert result['status'] == 'success'
        assert result['state'] == 'clean'
        assert result['action'] == 'noop'
        assert result['base'] == 'main'
        assert result['head_branch'] == 'feature/clean'
        assert result['ahead'] == 0
        assert result['behind'] == 0


# ---------------------------------------------------------------------------
# State 2 — dirty
# ---------------------------------------------------------------------------


class TestRebaseToDirty:
    """Worktree has uncommitted changes — reject before touching git."""

    def test_dirty_state_rejects_with_error(self, rebase_env: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        _create_branch_worktree(rebase_env['main_repo'], rebase_env['worktree'], 'feature/dirty')
        # Introduce an unstaged modification.
        (rebase_env['worktree'] / 'file.txt').write_text('locally modified\n')

        result = _invoke_rebase(rebase_env, monkeypatch)

        assert result['status'] == 'error'
        assert result['state'] == 'dirty'
        assert result['error'] == 'dirty_worktree'
        assert 'uncommitted' in result['message']
        # No rebase should have been attempted, so no rebase-merge dir.
        assert not (rebase_env['worktree'] / '.git' / 'rebase-merge').exists()
        assert not (rebase_env['worktree'] / '.git' / 'rebase-apply').exists()


# ---------------------------------------------------------------------------
# State 3 — ahead
# ---------------------------------------------------------------------------


class TestRebaseToAhead:
    """Branch is strictly ahead of base — the rebase replays nothing.

    ``ahead == 1, behind == 0`` means the branch ALREADY contains
    ``origin/main``, so ``git rebase origin/main`` has nothing to replay and
    leaves HEAD untouched. The honest verdict is therefore ``action: 'noop'``:
    reporting ``'rebased'`` on this path asserts a history rewrite that provably
    did not happen. The ``rebased`` verdict belongs to the paths where HEAD
    actually moves — see ``TestRebaseToBehind`` (fast-forward),
    ``TestRebaseToNoRemoteFallback`` (fast-forward onto local base), and
    ``TestRebaseToStaleLocalBaseRegression`` (diverged, genuinely replays).
    """

    def test_ahead_state_replays_nothing_and_reports_noop(
        self, rebase_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _create_branch_worktree(rebase_env['main_repo'], rebase_env['worktree'], 'feature/ahead')
        # Add a commit on the branch only.
        _commit_file(rebase_env['worktree'], 'feature.txt', 'feature\n', 'feat: add feature')

        result = _invoke_rebase(rebase_env, monkeypatch)

        assert result['status'] == 'success'
        assert result['state'] == 'ahead'
        assert result['action'] == 'noop'
        assert result['ahead'] == 1
        assert result['behind'] == 0
        assert 'no rebase needed' in result['message']
        # The branch's own commit must survive the no-op rebase.
        assert (rebase_env['worktree'] / 'feature.txt').exists()

    def test_ahead_state_leaves_head_sha_unchanged(self, rebase_env: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        """Pin the ``noop`` verdict to history identity, not to the label alone.

        The ``action`` field is only trustworthy if it is derived from evidence.
        This asserts the evidence directly: the worktree's HEAD sha is byte-identical
        before and after the call, and the payload's own ``pre_sha`` / ``post_sha``
        report that same identity — so a future regression that re-hardcodes
        ``action: 'rebased'`` cannot pass by relabelling alone.
        """
        _create_branch_worktree(rebase_env['main_repo'], rebase_env['worktree'], 'feature/ahead-sha')
        _commit_file(rebase_env['worktree'], 'feature.txt', 'feature\n', 'feat: add feature')
        head_before = _git(rebase_env['worktree'], 'rev-parse', 'HEAD').stdout.strip()

        result = _invoke_rebase(rebase_env, monkeypatch)

        head_after = _git(rebase_env['worktree'], 'rev-parse', 'HEAD').stdout.strip()
        assert head_after == head_before, 'a zero-replay rebase must not move HEAD'
        # The payload substantiates the verdict with the same two SHAs.
        assert result['pre_sha'] == head_before
        assert result['post_sha'] == head_after
        assert result['action'] == 'noop'


# ---------------------------------------------------------------------------
# State 4 — behind
# ---------------------------------------------------------------------------


class TestRebaseToBehind:
    """Base advanced past branch tip — rebase incorporates the new base commits."""

    def test_behind_state_rebases_successfully(self, rebase_env: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        _create_branch_worktree(rebase_env['main_repo'], rebase_env['worktree'], 'feature/behind')
        # Advance ``origin``'s ``main`` (= main_repo) so the feature branch is
        # strictly behind ``origin/main``. The production code fetches origin/main
        # and computes behind against it; the worktree's stale local ``main`` is
        # irrelevant to the new target.
        _advance_origin_main(rebase_env['main_repo'], 'main_only.txt', 'main only\n', 'feat: advance origin main')

        result = _invoke_rebase(rebase_env, monkeypatch)

        assert result['status'] == 'success'
        assert result['state'] == 'behind'
        assert result['action'] == 'rebased'
        assert result['rebase_ref'] == 'origin/main'
        assert result['ahead'] == 0
        assert result['behind'] == 1
        # The new base commit's file should now be reachable from the worktree HEAD.
        assert (rebase_env['worktree'] / 'main_only.txt').exists()


# ---------------------------------------------------------------------------
# State 5 — conflict
# ---------------------------------------------------------------------------


class TestRebaseToConflict:
    """Branch and base touched the same line — rebase produces conflicts."""

    def test_conflict_state_reports_conflicting_paths(self, rebase_env: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        _create_branch_worktree(rebase_env['main_repo'], rebase_env['worktree'], 'feature/conflict')
        # ``origin/main`` and the branch both rewrite the same line of file.txt in
        # incompatible ways. Advance ORIGIN's main (= main_repo) so the rebase onto
        # the fetched origin/main produces the conflict.
        _advance_origin_main(rebase_env['main_repo'], 'file.txt', 'main version\n', 'fix: rewrite on origin main')
        _commit_file(rebase_env['worktree'], 'file.txt', 'feature version\n', 'feat: rewrite on branch')

        result = _invoke_rebase(rebase_env, monkeypatch)

        assert result['status'] == 'conflict'
        assert result['state'] == 'conflict'
        assert result['error'] == 'rebase_conflict'
        assert 'conflicts' in result
        assert 'file.txt' in result['conflicts']
        assert 'rebase --continue' in result['message']
        # The rebase must be left in progress so callers can resolve.
        rebase_in_progress = (rebase_env['worktree'] / '.git' / 'rebase-merge').exists() or (
            rebase_env['worktree'] / '.git' / 'rebase-apply'
        ).exists()
        assert rebase_in_progress, 'conflict state must leave rebase in progress'
