"""Tests for git_workflow.py worktree-rebase-to subcommand.

Covers all eight documented worktree states the rebase dispatcher
recognises (per the docstring on ``_detect_worktree_state``):

    1. clean         — branch already at base; rebase is a no-op.
    2. dirty         — uncommitted changes; reject without touching git.
    3. ahead         — branch has commits base lacks; rebase succeeds.
    4. behind        — base has commits branch lacks; rebase fast-forwards.
    5. conflict      — rebase produces conflicts; status: conflict, with
                       conflict paths reported.
    6. detached      — HEAD is detached; reject.
    7. missing-base  — base ref does not resolve; error.
    8. missing-target — worktree path absent on disk OR the plan does
                        not exist (resolution fails); error.

The tests use temporary git repositories as fixtures (mirroring
``test_manage_worktree.py`` patterns) and exercise
``cmd_worktree_rebase_to`` via direct import. Plan-id resolution is
short-circuited by monkeypatching ``_resolve_worktree_path_for_plan``
so the tests never depend on the real plan-marshall executor or any
``manage-status`` state on disk.

Rebase target (Deliverable 2): ``cmd_worktree_rebase_to`` fetches
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
``test/plan-marshall/plan-retrospective/_fixtures.py`` for the wider
project convention.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path  # type: ignore[import-not-found]

# The entrypoint filename is kebab-case (git-workflow.py), which is not a
# valid Python module identifier — load it via importlib instead of `import`.
_spec = importlib.util.spec_from_file_location(
    'git_workflow', get_script_path('plan-marshall', 'workflow-integration-git', 'git-workflow.py')
)
assert _spec is not None and _spec.loader is not None
git_workflow = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(git_workflow)
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

    Mirrors the lightweight setup used by ``test_git_workflow.py`` for
    its analyze-diff CLI tests, with the addition of a tracked
    ``.gitignore`` so ``git worktree`` operations on derived worktrees
    do not get tripped up by untracked ``.plan/`` content.
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
    directory has its own ``.git`` *directory* (not a worktree pointer
    file). This matters for the conflict-detection code in
    ``cmd_worktree_rebase_to`` which probes ``target / '.git' /
    'rebase-merge'`` directly: in a real ``git worktree add`` checkout
    that path resolves through the pointer file and never matches, so
    the conflict state would mis-classify as ``rebase_failed``. The
    rebase dispatcher itself only requires that ``target`` is a working
    tree pointing at the branch we want to rebase, so a clone is
    semantically equivalent for the purposes of these tests while
    keeping the conflict path observable. Both repos share the same
    base commit because the clone is taken from ``main_repo``.
    """
    worktree.parent.mkdir(parents=True, exist_ok=True)
    _git(main_repo, 'clone', '-q', str(main_repo), str(worktree))
    _git(worktree, 'config', 'user.email', 't@t.test')
    _git(worktree, 'config', 'user.name', 'Test')
    # ``git clone`` checks out the default branch (``main`` here) and
    # registers ``origin/main``. Create a local feature branch off of
    # ``main`` and check it out so the rebase target is the branch the
    # production code expects.
    _git(worktree, 'checkout', '-q', '-b', branch, 'main')


def _commit_file(repo: Path, name: str, content: str, message: str) -> None:
    """Create or overwrite ``name`` with ``content`` and commit it."""
    (repo / name).write_text(content)
    _git(repo, 'add', name)
    _git(repo, 'commit', '-q', '-m', message)


def _advance_main_via_branch_switch(repo: Path, name: str, content: str, message: str, current_branch: str) -> None:
    """Commit ``name`` to ``main`` from inside ``repo`` and return to ``current_branch``.

    Used when the test fixture is a clone (rather than a worktree
    sharing object DB with the source repo). The clone has its own
    ``main`` ref, so advancing the base requires checking it out,
    committing, then restoring the feature branch.
    """
    _git(repo, 'checkout', '-q', 'main')
    _commit_file(repo, name, content, message)
    _git(repo, 'checkout', '-q', current_branch)


def _advance_origin_main(origin_repo: Path, name: str, content: str, message: str) -> None:
    """Commit ``name`` to ``origin_repo``'s ``main`` (the remote the worktree clones).

    Deliverable 2: the rebase now targets ``origin/{base}``, so advancing the
    base means committing to the ORIGIN's ``main`` (``main_repo``), then letting
    the production code's ``git fetch origin main`` pull the advance into the
    worktree's ``origin/main`` remote-tracking ref. The worktree's OWN local
    ``main`` is deliberately left stale to reproduce the defect scenario.
    """
    _commit_file(origin_repo, name, content, message)


# ---------------------------------------------------------------------------
# unittest-style scaffold: shared per-test cleanup of tmpdirs.
# ---------------------------------------------------------------------------


class _RebaseTestBase(unittest.TestCase):
    """Common per-test setup/teardown for rebase-to scenarios."""

    def setUp(self) -> None:
        self._tmp_root = Path(tempfile.mkdtemp(prefix='rebase-to-'))
        self.main_repo = self._tmp_root / 'main'
        # Worktree lives outside .claude/worktrees/ on purpose — the
        # rebase dispatcher does not enforce a particular layout, only
        # that the path resolves to a real git worktree.
        self.worktree = self._tmp_root / 'worktrees' / 'plan-x'
        _init_main_repo(self.main_repo)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp_root, ignore_errors=True)

    # ------------------------------------------------------------------
    # Helpers shared across rebase-to scenarios.
    # ------------------------------------------------------------------

    def _invoke_rebase(self, base: str = 'main', plan_id: str = 'plan-x') -> dict:
        """Invoke ``cmd_worktree_rebase_to`` with the shared monkeypatch shim.

        Subclasses set ``self._resolver_target`` / ``self._resolver_error`` /
        ``self._main_root`` before calling.
        """
        # ``unittest.TestCase`` does not have a built-in monkeypatch like
        # pytest, so we manually swap and restore via a tiny helper.
        target = getattr(self, '_resolver_target', self.worktree)
        error = getattr(self, '_resolver_error', None)
        # In production, ``main_root`` is the shared main checkout whose
        # object DB the worktree references via its ``.git`` pointer file.
        # The fixture uses ``git clone`` instead (so ``.git`` is a real
        # directory and conflict detection actually works), which means the
        # cloned repo IS its own DB — point base-ref resolution at it so
        # commits made on ``main`` inside the clone are visible.
        main_root = getattr(self, '_main_root', self.worktree)

        original_resolver = git_workflow._resolve_worktree_path_for_plan
        original_root = git_workflow._find_plan_root_from_cwd
        git_workflow._resolve_worktree_path_for_plan = lambda _pid: (target, error)
        git_workflow._find_plan_root_from_cwd = lambda: main_root
        try:
            return cmd_worktree_rebase_to(Namespace(plan_id=plan_id, base=base))
        finally:
            git_workflow._resolve_worktree_path_for_plan = original_resolver
            git_workflow._find_plan_root_from_cwd = original_root


# ---------------------------------------------------------------------------
# State 1 — clean
# ---------------------------------------------------------------------------


class TestRebaseToClean(_RebaseTestBase):
    """Branch already at base — rebase is a no-op success."""

    def test_clean_state_returns_noop_success(self) -> None:
        _create_branch_worktree(self.main_repo, self.worktree, 'feature/clean')
        # No commits on either side — branch and base point at the same SHA.

        result = self._invoke_rebase()

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['state'], 'clean')
        self.assertEqual(result['action'], 'noop')
        self.assertEqual(result['base'], 'main')
        self.assertEqual(result['head_branch'], 'feature/clean')
        self.assertEqual(result['ahead'], 0)
        self.assertEqual(result['behind'], 0)


# ---------------------------------------------------------------------------
# State 2 — dirty
# ---------------------------------------------------------------------------


class TestRebaseToDirty(_RebaseTestBase):
    """Worktree has uncommitted changes — reject before touching git."""

    def test_dirty_state_rejects_with_error(self) -> None:
        _create_branch_worktree(self.main_repo, self.worktree, 'feature/dirty')
        # Introduce an unstaged modification.
        (self.worktree / 'file.txt').write_text('locally modified\n')

        result = self._invoke_rebase()

        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['state'], 'dirty')
        self.assertEqual(result['error'], 'dirty_worktree')
        self.assertIn('uncommitted', result['message'])
        # No rebase should have been attempted, so no rebase-merge dir.
        self.assertFalse((self.worktree / '.git' / 'rebase-merge').exists())
        self.assertFalse((self.worktree / '.git' / 'rebase-apply').exists())


# ---------------------------------------------------------------------------
# State 3 — ahead
# ---------------------------------------------------------------------------


class TestRebaseToAhead(_RebaseTestBase):
    """Branch is strictly ahead of base — rebase succeeds (no-op fast-forward)."""

    def test_ahead_state_rebases_successfully(self) -> None:
        _create_branch_worktree(self.main_repo, self.worktree, 'feature/ahead')
        # Add a commit on the branch only.
        _commit_file(self.worktree, 'feature.txt', 'feature\n', 'feat: add feature')

        result = self._invoke_rebase()

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['state'], 'ahead')
        self.assertEqual(result['action'], 'rebased')
        self.assertEqual(result['ahead'], 1)
        self.assertEqual(result['behind'], 0)
        self.assertIn('rebased', result['message'])
        # The branch tip commit must still be present in the worktree.
        self.assertTrue((self.worktree / 'feature.txt').exists())


# ---------------------------------------------------------------------------
# State 4 — behind
# ---------------------------------------------------------------------------


class TestRebaseToBehind(_RebaseTestBase):
    """Base advanced past branch tip — rebase incorporates the new base commits."""

    def test_behind_state_rebases_successfully(self) -> None:
        _create_branch_worktree(self.main_repo, self.worktree, 'feature/behind')
        # Advance ``origin``'s ``main`` (= main_repo) so the feature branch is
        # strictly behind ``origin/main``. The production code fetches origin/main
        # and computes behind against it; the worktree's stale local ``main`` is
        # irrelevant to the new target.
        _advance_origin_main(self.main_repo, 'main_only.txt', 'main only\n', 'feat: advance origin main')

        result = self._invoke_rebase()

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['state'], 'behind')
        self.assertEqual(result['action'], 'rebased')
        self.assertEqual(result['rebase_ref'], 'origin/main')
        self.assertEqual(result['ahead'], 0)
        self.assertEqual(result['behind'], 1)
        # The new base commit's file should now be reachable from the
        # worktree HEAD.
        self.assertTrue((self.worktree / 'main_only.txt').exists())


# ---------------------------------------------------------------------------
# State 5 — conflict
# ---------------------------------------------------------------------------


class TestRebaseToConflict(_RebaseTestBase):
    """Branch and base touched the same line — rebase produces conflicts."""

    def test_conflict_state_reports_conflicting_paths(self) -> None:
        _create_branch_worktree(self.main_repo, self.worktree, 'feature/conflict')
        # ``origin/main`` and the branch both rewrite the same line of file.txt
        # in incompatible ways. Advance ORIGIN's main (= main_repo) so the rebase
        # onto the fetched origin/main produces the conflict.
        _advance_origin_main(self.main_repo, 'file.txt', 'main version\n', 'fix: rewrite on origin main')
        _commit_file(self.worktree, 'file.txt', 'feature version\n', 'feat: rewrite on branch')

        result = self._invoke_rebase()

        self.assertEqual(result['status'], 'conflict')
        self.assertEqual(result['state'], 'conflict')
        self.assertEqual(result['error'], 'rebase_conflict')
        self.assertIn('conflicts', result)
        self.assertIn('file.txt', result['conflicts'])
        self.assertIn('rebase --continue', result['message'])
        # The rebase must be left in progress so callers can resolve.
        rebase_in_progress = (
            (self.worktree / '.git' / 'rebase-merge').exists()
            or (self.worktree / '.git' / 'rebase-apply').exists()
        )
        self.assertTrue(rebase_in_progress, 'conflict state must leave rebase in progress')


# ---------------------------------------------------------------------------
# State 6 — detached
# ---------------------------------------------------------------------------


class TestRebaseToDetached(_RebaseTestBase):
    """HEAD detached in the worktree — reject without attempting rebase."""

    def test_detached_state_rejects_with_error(self) -> None:
        _create_branch_worktree(self.main_repo, self.worktree, 'feature/detached')
        # Detach HEAD by checking out the commit SHA explicitly.
        head_sha = _git(self.worktree, 'rev-parse', 'HEAD').stdout.strip()
        _git(self.worktree, 'checkout', '--detach', head_sha)

        result = self._invoke_rebase()

        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['state'], 'detached')
        self.assertEqual(result['error'], 'detached_head')
        self.assertIn('detached', result['message'].lower())
        # No rebase should have started.
        self.assertFalse((self.worktree / '.git' / 'rebase-merge').exists())


# ---------------------------------------------------------------------------
# State 7 — missing-base
# ---------------------------------------------------------------------------


class TestRebaseToMissingBase(_RebaseTestBase):
    """``--base`` does not resolve — short-circuit error before rebase."""

    def test_missing_base_returns_error(self) -> None:
        _create_branch_worktree(self.main_repo, self.worktree, 'feature/missing-base')

        result = self._invoke_rebase(base='nonexistent-branch')

        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['state'], 'missing-base')
        self.assertEqual(result['error'], 'missing_base')
        self.assertIn('nonexistent-branch', result['message'])


# ---------------------------------------------------------------------------
# State 8 — missing-target
# ---------------------------------------------------------------------------


class TestRebaseToMissingTarget(_RebaseTestBase):
    """Two flavours of missing-target: directory absent vs. plan unresolved."""

    def test_missing_target_directory_returns_error(self) -> None:
        # Resolver succeeds and points at a path that does not exist on disk.
        # ``main_root`` still resolves so the dispatcher reaches
        # ``_detect_worktree_state`` and sees the missing directory.
        bogus = self._tmp_root / 'never-created'
        self._resolver_target = bogus

        result = self._invoke_rebase()

        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['state'], 'missing-target')
        self.assertEqual(result['error'], 'missing_target')
        self.assertIn(str(bogus), result['message'])
        self.assertEqual(result['worktree_path'], str(bogus))

    def test_missing_plan_resolution_returns_error(self) -> None:
        # Resolver short-circuits with the same error shape that
        # ``manage-status get-worktree-path`` would return for an unknown plan.
        # The rebase command must propagate it verbatim and never attempt
        # to inspect the worktree.
        self._resolver_target = None
        self._resolver_error = {
            'status': 'error',
            'plan_id': 'plan-x',
            'error': 'no_worktree_configured',
            'message': 'No worktree configured for this plan',
        }

        result = self._invoke_rebase()

        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error'], 'no_worktree_configured')
        self.assertEqual(result['plan_id'], 'plan-x')


# ---------------------------------------------------------------------------
# Deliverable 2 — stale-local-base regression (related lesson 2026-06-03-13-001)
# ---------------------------------------------------------------------------


class TestRebaseToStaleLocalBaseRegression(_RebaseTestBase):
    """origin/{base} advanced past the worktree's local {base} — one rebase lands it.

    The defect: rebasing onto the bare local ``{base}`` ref left the branch behind
    ``origin/{base}`` (the orchestrator only fetched origin, never advanced local
    base), failing branch protection's "up to date with base" check. The fix
    fetches and rebases onto ``origin/{base}`` so a SINGLE invocation lands the
    branch up-to-date with the remote tip. This is the exact assertion the
    request names: ``git log HEAD..origin/{base}`` is empty after one rebase.
    """

    def test_single_rebase_lands_branch_on_advanced_origin_base(self) -> None:
        _create_branch_worktree(self.main_repo, self.worktree, 'feature/stale-base')
        # The branch has its own commit (so it is not a trivial fast-forward).
        _commit_file(self.worktree, 'feature.txt', 'feature\n', 'feat: add feature')
        # Advance ORIGIN's main with a DISJOINT file (no conflict) WITHOUT
        # advancing the worktree's local ``main`` — the stale-local-base scenario.
        _advance_origin_main(self.main_repo, 'upstream.txt', 'upstream\n', 'feat: advance origin main')

        # The worktree's local ``main`` is still at the original commit; only
        # ``origin/main`` (after the production fetch) carries the upstream commit.
        result = self._invoke_rebase()

        self.assertEqual(result['status'], 'success', result)
        self.assertEqual(result['action'], 'rebased')
        self.assertEqual(result['rebase_ref'], 'origin/main')

        # The decisive assertion: after a SINGLE rebase, the branch contains the
        # upstream commit — HEAD..origin/main is empty.
        log_out = _git(
            self.worktree, 'log', '--oneline', 'HEAD..origin/main'
        ).stdout.strip()
        self.assertEqual(log_out, '', f'branch still behind origin/main after one rebase: {log_out!r}')
        # Both the upstream file and the branch's own commit are present.
        self.assertTrue((self.worktree / 'upstream.txt').exists())
        self.assertTrue((self.worktree / 'feature.txt').exists())


# ---------------------------------------------------------------------------
# Deliverable 2 — no-origin fallback to the local {base} ref
# ---------------------------------------------------------------------------


class TestRebaseToNoRemoteFallback(_RebaseTestBase):
    """A worktree with no ``origin`` remote falls back to rebasing onto local {base}."""

    def test_no_origin_remote_rebases_onto_local_base(self) -> None:
        # Build a standalone repo with a feature branch but NO origin remote.
        _git(self.main_repo, 'checkout', '-q', '-b', 'feature/no-remote', 'main')
        # The worktree IS the main repo here (no clone, no origin). Resolver and
        # base-ref resolution both point at this single repo.
        self._resolver_target = self.main_repo
        self._main_root = self.main_repo
        # Advance local ``main`` so the branch is behind it (the only base ref
        # available without a remote).
        _advance_main_via_branch_switch(
            self.main_repo, 'main_only.txt', 'main only\n', 'feat: advance local main', 'feature/no-remote'
        )

        result = self._invoke_rebase(base='main')

        self.assertEqual(result['status'], 'success', result)
        self.assertEqual(result['action'], 'rebased')
        # No origin remote → rebase_ref falls back to the bare local ``main``.
        self.assertEqual(result['rebase_ref'], 'main')
        self.assertTrue((self.main_repo / 'main_only.txt').exists())


# ---------------------------------------------------------------------------
# Direct unit coverage of _detect_worktree_state — pins the contract that
# cmd_worktree_rebase_to relies on for dispatching to the eight states.
# ---------------------------------------------------------------------------


class TestDetectWorktreeState(_RebaseTestBase):
    """Probe ``_detect_worktree_state`` directly for each label."""

    def test_detect_missing_target(self) -> None:
        bogus = self._tmp_root / 'never-created'
        state, evidence = _detect_worktree_state(bogus, 'main', self.main_repo)
        self.assertEqual(state, 'missing-target')
        self.assertEqual(evidence['worktree_path'], str(bogus))

    def test_detect_missing_base(self) -> None:
        _create_branch_worktree(self.main_repo, self.worktree, 'feature/x')
        state, evidence = _detect_worktree_state(self.worktree, 'no-such-ref', self.main_repo)
        self.assertEqual(state, 'missing-base')
        self.assertEqual(evidence['base'], 'no-such-ref')

    def test_detect_clean(self) -> None:
        _create_branch_worktree(self.main_repo, self.worktree, 'feature/x')
        state, evidence = _detect_worktree_state(self.worktree, 'main', self.main_repo)
        self.assertEqual(state, 'clean')
        self.assertEqual(evidence['ahead'], 0)
        self.assertEqual(evidence['behind'], 0)
        self.assertEqual(evidence['head_branch'], 'feature/x')


if __name__ == '__main__':
    unittest.main()
