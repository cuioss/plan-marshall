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

The tests use temporary git repositories as fixtures and exercise
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
import subprocess
from argparse import Namespace
from pathlib import Path

import pytest

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

    Deliverable 2: the rebase now targets ``origin/{base}``, so advancing the
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

    return cmd_worktree_rebase_to(Namespace(plan_id=plan_id, base=base))


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
    """Branch is strictly ahead of base — rebase succeeds (no-op fast-forward)."""

    def test_ahead_state_rebases_successfully(self, rebase_env: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        _create_branch_worktree(rebase_env['main_repo'], rebase_env['worktree'], 'feature/ahead')
        # Add a commit on the branch only.
        _commit_file(rebase_env['worktree'], 'feature.txt', 'feature\n', 'feat: add feature')

        result = _invoke_rebase(rebase_env, monkeypatch)

        assert result['status'] == 'success'
        assert result['state'] == 'ahead'
        assert result['action'] == 'rebased'
        assert result['ahead'] == 1
        assert result['behind'] == 0
        assert 'rebased' in result['message']
        # The branch tip commit must still be present in the worktree.
        assert (rebase_env['worktree'] / 'feature.txt').exists()


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
        rebase_in_progress = (
            (rebase_env['worktree'] / '.git' / 'rebase-merge').exists()
            or (rebase_env['worktree'] / '.git' / 'rebase-apply').exists()
        )
        assert rebase_in_progress, 'conflict state must leave rebase in progress'


# ---------------------------------------------------------------------------
# State 6 — detached
# ---------------------------------------------------------------------------


class TestRebaseToDetached:
    """HEAD detached in the worktree — reject without attempting rebase."""

    def test_detached_state_rejects_with_error(self, rebase_env: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        _create_branch_worktree(rebase_env['main_repo'], rebase_env['worktree'], 'feature/detached')
        # Detach HEAD by checking out the commit SHA explicitly.
        head_sha = _git(rebase_env['worktree'], 'rev-parse', 'HEAD').stdout.strip()
        _git(rebase_env['worktree'], 'checkout', '--detach', head_sha)

        result = _invoke_rebase(rebase_env, monkeypatch)

        assert result['status'] == 'error'
        assert result['state'] == 'detached'
        assert result['error'] == 'detached_head'
        assert 'detached' in result['message'].lower()
        # No rebase should have started.
        assert not (rebase_env['worktree'] / '.git' / 'rebase-merge').exists()


# ---------------------------------------------------------------------------
# State 7 — missing-base
# ---------------------------------------------------------------------------


class TestRebaseToMissingBase:
    """``--base`` does not resolve — short-circuit error before rebase."""

    def test_missing_base_returns_error(self, rebase_env: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        _create_branch_worktree(rebase_env['main_repo'], rebase_env['worktree'], 'feature/missing-base')

        result = _invoke_rebase(rebase_env, monkeypatch, base='nonexistent-branch')

        assert result['status'] == 'error'
        assert result['state'] == 'missing-base'
        assert result['error'] == 'missing_base'
        assert 'nonexistent-branch' in result['message']


# ---------------------------------------------------------------------------
# State 8 — missing-target
# ---------------------------------------------------------------------------


class TestRebaseToMissingTarget:
    """Two flavours of missing-target: directory absent vs. plan unresolved."""

    def test_missing_target_directory_returns_error(self, rebase_env: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        # Resolver succeeds and points at a path that does not exist on disk.
        # ``main_root`` still resolves so the dispatcher reaches
        # ``_detect_worktree_state`` and sees the missing directory.
        bogus = rebase_env['tmp_root'] / 'never-created'

        result = _invoke_rebase(rebase_env, monkeypatch, resolver_target=bogus)

        assert result['status'] == 'error'
        assert result['state'] == 'missing-target'
        assert result['error'] == 'missing_target'
        assert str(bogus) in result['message']
        assert result['worktree_path'] == str(bogus)

    def test_missing_plan_resolution_returns_error(self, rebase_env: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        # Resolver short-circuits with the same error shape that
        # ``manage-status get-worktree-path`` would return for an unknown plan.
        # The rebase command must propagate it verbatim and never attempt to
        # inspect the worktree.
        resolver_error = {
            'status': 'error',
            'plan_id': 'plan-x',
            'error': 'no_worktree_configured',
            'message': 'No worktree configured for this plan',
        }

        result = _invoke_rebase(rebase_env, monkeypatch, resolver_target=None, resolver_error=resolver_error)

        assert result['status'] == 'error'
        assert result['error'] == 'no_worktree_configured'
        assert result['plan_id'] == 'plan-x'


# ---------------------------------------------------------------------------
# Deliverable 2 — stale-local-base regression (related lesson 2026-06-03-13-001)
# ---------------------------------------------------------------------------


class TestRebaseToStaleLocalBaseRegression:
    """origin/{base} advanced past the worktree's local {base} — one rebase lands it.

    The defect: rebasing onto the bare local ``{base}`` ref left the branch behind
    ``origin/{base}`` (the orchestrator only fetched origin, never advanced local
    base), failing branch protection's "up to date with base" check. The fix
    fetches and rebases onto ``origin/{base}`` so a SINGLE invocation lands the
    branch up-to-date with the remote tip: ``git log HEAD..origin/{base}`` is empty
    after one rebase.
    """

    def test_single_rebase_lands_branch_on_advanced_origin_base(
        self, rebase_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _create_branch_worktree(rebase_env['main_repo'], rebase_env['worktree'], 'feature/stale-base')
        # The branch has its own commit (so it is not a trivial fast-forward).
        _commit_file(rebase_env['worktree'], 'feature.txt', 'feature\n', 'feat: add feature')
        # Advance ORIGIN's main with a DISJOINT file (no conflict) WITHOUT advancing
        # the worktree's local ``main`` — the stale-local-base scenario.
        _advance_origin_main(rebase_env['main_repo'], 'upstream.txt', 'upstream\n', 'feat: advance origin main')

        # The worktree's local ``main`` is still at the original commit; only
        # ``origin/main`` (after the production fetch) carries the upstream commit.
        result = _invoke_rebase(rebase_env, monkeypatch)

        assert result['status'] == 'success', result
        assert result['action'] == 'rebased'
        assert result['rebase_ref'] == 'origin/main'

        # The decisive assertion: after a SINGLE rebase, the branch contains the
        # upstream commit — HEAD..origin/main is empty.
        log_out = _git(rebase_env['worktree'], 'log', '--oneline', 'HEAD..origin/main').stdout.strip()
        assert log_out == '', f'branch still behind origin/main after one rebase: {log_out!r}'
        # Both the upstream file and the branch's own commit are present.
        assert (rebase_env['worktree'] / 'upstream.txt').exists()
        assert (rebase_env['worktree'] / 'feature.txt').exists()


# ---------------------------------------------------------------------------
# Deliverable 2 — no-origin fallback to the local {base} ref
# ---------------------------------------------------------------------------


class TestRebaseToNoRemoteFallback:
    """A worktree with no ``origin`` remote falls back to rebasing onto local {base}."""

    def test_no_origin_remote_rebases_onto_local_base(
        self, rebase_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        main_repo = rebase_env['main_repo']
        # Build a feature branch in the main repo with NO origin remote. The
        # worktree IS the main repo here (no clone, no origin); resolver and
        # base-ref resolution both point at this single repo.
        _git(main_repo, 'checkout', '-q', '-b', 'feature/no-remote', 'main')
        # Advance local ``main`` so the branch is behind it (the only base ref
        # available without a remote).
        _advance_main_via_branch_switch(
            main_repo, 'main_only.txt', 'main only\n', 'feat: advance local main', 'feature/no-remote'
        )

        result = _invoke_rebase(
            rebase_env, monkeypatch, base='main', resolver_target=main_repo, main_root=main_repo
        )

        assert result['status'] == 'success', result
        assert result['action'] == 'rebased'
        # No origin remote → rebase_ref falls back to the bare local ``main``.
        assert result['rebase_ref'] == 'main'
        assert (main_repo / 'main_only.txt').exists()


# ---------------------------------------------------------------------------
# Direct unit coverage of _detect_worktree_state — pins the contract that
# cmd_worktree_rebase_to relies on for dispatching to the eight states.
# ---------------------------------------------------------------------------


class TestDetectWorktreeState:
    """Probe ``_detect_worktree_state`` directly for each label."""

    def test_detect_missing_target(self, rebase_env: dict) -> None:
        bogus = rebase_env['tmp_root'] / 'never-created'

        state, evidence = _detect_worktree_state(bogus, 'main', rebase_env['main_repo'])

        assert state == 'missing-target'
        assert evidence['worktree_path'] == str(bogus)

    def test_detect_missing_base(self, rebase_env: dict) -> None:
        _create_branch_worktree(rebase_env['main_repo'], rebase_env['worktree'], 'feature/x')

        state, evidence = _detect_worktree_state(rebase_env['worktree'], 'no-such-ref', rebase_env['main_repo'])

        assert state == 'missing-base'
        assert evidence['base'] == 'no-such-ref'

    def test_detect_clean(self, rebase_env: dict) -> None:
        _create_branch_worktree(rebase_env['main_repo'], rebase_env['worktree'], 'feature/x')

        state, evidence = _detect_worktree_state(rebase_env['worktree'], 'main', rebase_env['main_repo'])

        assert state == 'clean'
        assert evidence['ahead'] == 0
        assert evidence['behind'] == 0
        assert evidence['head_branch'] == 'feature/x'
