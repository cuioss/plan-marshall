# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for executor refresh after a script-set-changing worktree rebase.

The per-tree executor (``.plan/execute-script.py``) is DERIVED state: it embeds
a notation→path map generated from the bundle tree as it stood when the
worktree was materialised (``prepare_execute._generate_worktree_executor``).

``worktree-rebase-to`` replays the feature branch onto a newly-fetched
``origin/{base}``. When those upstream commits added, removed, or renamed a
bundle script, the embedded map no longer describes the tree — and nothing
regenerated it. Every subsequent dispatch in that worktree resolves notations
against a stale map, so a notation introduced upstream cannot be resolved at
all. EVERY finalize rebase routes through this one verb — callers today include
``finalize-step-sync-baseline`` (``order: 3``), ``automatic-review``
(``order: 30``, refusal-recovery path) and ``branch-cleanup`` (``order: 70``) —
so the refresh belongs here rather than in any caller, and a new caller inherits
it without having to know it exists.

The refresh is:

- **conditional on the rebase having replayed commits** — a ``noop`` rebase
  changed no files, so there is nothing to drift.
- **conditional on POSITIVELY detected drift** — ``generate_executor drift``
  compares the embedded map against the live bundle state. An indeterminate
  verdict reports ``unknown`` and regenerates NOTHING: a spurious regeneration
  in a tree with no vendored bundles could replace a working executor with an
  empty one, which is strictly worse than the stale map it would be guarding.
- **non-fatal** — the rebase already succeeded and moved HEAD. A refresh
  failure is reported on the payload, never converted into a rebase failure.
"""

from __future__ import annotations

import subprocess
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import load_script_module

git_workflow = load_script_module(
    'plan-marshall', 'workflow-integration-git', 'git-workflow.py', 'git_workflow_exec_refresh'
)

cmd_worktree_rebase_to = git_workflow.cmd_worktree_rebase_to


# ---------------------------------------------------------------------------
# Git fixture helpers (mirrors test_git_workflow_worktree_rebase.py)
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ['git', '-C', str(repo), *args], capture_output=True, text=True, check=check
    )


def _init_main_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, 'init', '-q', '-b', 'main')
    _git(repo, 'config', 'user.email', 't@t.test')
    _git(repo, 'config', 'user.name', 'Test')
    (repo / '.gitignore').write_text('.plan/\n')
    (repo / 'file.txt').write_text('line 1\n')
    _git(repo, 'add', '.')
    _git(repo, 'commit', '-q', '-m', 'init')


def _clone_branch(main_repo: Path, worktree: Path, branch: str) -> None:
    worktree.parent.mkdir(parents=True, exist_ok=True)
    _git(main_repo, 'clone', '-q', str(main_repo), str(worktree))
    _git(worktree, 'config', 'user.email', 't@t.test')
    _git(worktree, 'config', 'user.name', 'Test')
    _git(worktree, 'checkout', '-q', '-b', branch, 'main')


def _commit(repo: Path, name: str, content: str, message: str) -> None:
    (repo / name).write_text(content)
    _git(repo, 'add', name)
    _git(repo, 'commit', '-q', '-m', message)


@pytest.fixture
def env(tmp_path: Path) -> dict:
    main_repo = tmp_path / 'main'
    worktree = tmp_path / 'worktrees' / 'plan-x'
    _init_main_repo(main_repo)
    _clone_branch(main_repo, worktree, 'feature/plan-x')
    return {'main_repo': main_repo, 'worktree': worktree}


class _GeneratorSpy:
    """Stand in for the ``generate_executor.py`` subprocess seam.

    Records the verbs invoked and returns a canned TOON per verb, so the tests
    assert on the DECISION (probe, then regenerate or not) without needing a
    vendored bundle tree in the fixture.

    ``lands_executor`` controls whether a successful ``generate`` actually
    writes the executor file, so the on-disk post-assertion is exercisable: a
    generator that exits 0 having written nothing must NOT be reported as a
    successful regeneration.
    """

    def __init__(
        self,
        drift_status: str = 'ok',
        generate_rc: int = 0,
        lands_executor: bool = True,
    ):
        self._drift_status = drift_status
        self._generate_rc = generate_rc
        self._lands_executor = lands_executor
        self.verbs: list[str] = []

    def __call__(self, worktree: Path, verb: str, *_args: str):
        self.verbs.append(verb)
        if verb == 'drift':
            if self._drift_status == 'UNREADABLE':
                return 0, 'garbage not toon\n', ''
            return 0, f'status: success\ndrift_status: {self._drift_status}\n', ''
        if self._generate_rc == 0 and self._lands_executor:
            slot = git_workflow.worktree_executor_path(worktree)
            slot.parent.mkdir(parents=True, exist_ok=True)
            slot.write_text('#!/usr/bin/env python3\n# generated\n')
        return self._generate_rc, 'status: success\n', '' if self._generate_rc == 0 else 'boom'


def _invoke(env: dict, monkeypatch, spy=None, base: str = 'main') -> dict:
    target = env['worktree']
    monkeypatch.setattr(
        git_workflow, '_resolve_worktree_path_for_plan', lambda _pid: (target, None)
    )
    monkeypatch.setattr(git_workflow, '_find_plan_root_from_cwd', lambda: target)
    if spy is not None:
        monkeypatch.setattr(git_workflow, '_run_generate_executor', spy)
    result: dict = cmd_worktree_rebase_to(Namespace(plan_id='plan-x', base=base))
    return result


# ---------------------------------------------------------------------------
# The defect: a rebase that replays commits must refresh a drifted executor
# ---------------------------------------------------------------------------


class TestDriftedExecutorIsRegenerated:
    def test_replayed_rebase_with_drift_regenerates_the_executor(self, env, monkeypatch):
        # Upstream advances AND the branch has its own commit, so the rebase
        # genuinely replays (action: rebased).
        _commit(env['main_repo'], 'upstream.txt', 'new\n', 'upstream script change')
        _commit(env['worktree'], 'local.txt', 'mine\n', 'local work')

        spy = _GeneratorSpy(drift_status='drift')
        result = _invoke(env, monkeypatch, spy)

        assert result['status'] == 'success'
        assert result['action'] == 'rebased'
        assert result['executor_drift'] == 'drift'
        assert result['executor_regenerated'] is True
        assert spy.verbs == ['drift', 'generate'], (
            'a drifted script set must be probed and then regenerated, '
            f'got {spy.verbs}'
        )

    def test_replayed_rebase_without_drift_does_not_regenerate(self, env, monkeypatch):
        _commit(env['main_repo'], 'upstream.txt', 'new\n', 'upstream doc change')
        _commit(env['worktree'], 'local.txt', 'mine\n', 'local work')

        spy = _GeneratorSpy(drift_status='ok')
        result = _invoke(env, monkeypatch, spy)

        assert result['action'] == 'rebased'
        assert result['executor_drift'] == 'ok'
        assert result['executor_regenerated'] is False
        assert spy.verbs == ['drift'], 'an unchanged script set must not regenerate'


class TestNoopRebaseSkipsTheProbe:
    def test_noop_rebase_does_not_probe_for_drift(self, env, monkeypatch):
        """Nothing was replayed, so no upstream file can have landed."""
        spy = _GeneratorSpy(drift_status='drift')
        result = _invoke(env, monkeypatch, spy)

        assert result['status'] == 'success'
        assert result['action'] == 'noop'
        assert spy.verbs == [], 'a no-op rebase must not pay for a drift probe'
        assert result['executor_regenerated'] is False


class TestRefreshIsNonFatal:
    def test_failed_generation_does_not_fail_the_rebase(self, env, monkeypatch):
        """HEAD already moved — a refresh failure must not masquerade as a
        rebase failure, or the caller would abort a rebase that succeeded."""
        _commit(env['main_repo'], 'upstream.txt', 'new\n', 'upstream')
        _commit(env['worktree'], 'local.txt', 'mine\n', 'local work')

        spy = _GeneratorSpy(drift_status='drift', generate_rc=1)
        result = _invoke(env, monkeypatch, spy)

        assert result['status'] == 'success', 'the rebase itself succeeded'
        assert result['action'] == 'rebased'
        assert result['executor_regenerated'] is False
        assert result['executor_detail'], 'the failure must be reported, not swallowed'

    def test_indeterminate_drift_regenerates_nothing(self, env, monkeypatch):
        """Report `unknown`, act on nothing.

        A tree with no vendored bundles yields an unreadable drift verdict;
        regenerating there could replace a working executor with an empty one,
        which is worse than the stale map this refresh exists to prevent.
        """
        _commit(env['main_repo'], 'upstream.txt', 'new\n', 'upstream')
        _commit(env['worktree'], 'local.txt', 'mine\n', 'local work')

        spy = _GeneratorSpy(drift_status='UNREADABLE')
        result = _invoke(env, monkeypatch, spy)

        assert result['status'] == 'success'
        assert result['executor_drift'] == 'unknown'
        assert result['executor_regenerated'] is False
        assert spy.verbs == ['drift'], 'an indeterminate verdict must not regenerate'


class TestSuccessIsDerivedFromDiskNotExitCode:
    def test_generation_exiting_zero_without_landing_a_file_is_not_success(
        self, env, monkeypatch
    ):
        """`returncode == 0` is not proof the executor exists.

        The generator can exit 0 having written nothing when marketplace
        anchoring lands nowhere. Reporting that as `executor_regenerated: True`
        would claim a refreshed executor that is not on disk — the same rule
        `prepare_execute._generate_worktree_executor` states for this generator.
        """
        _commit(env['main_repo'], 'upstream.txt', 'new\n', 'upstream')
        _commit(env['worktree'], 'local.txt', 'mine\n', 'local work')

        spy = _GeneratorSpy(drift_status='drift', lands_executor=False)
        result = _invoke(env, monkeypatch, spy)

        assert result['status'] == 'success', 'the rebase itself succeeded'
        assert spy.verbs == ['drift', 'generate'], 'generation was attempted'
        assert result['executor_regenerated'] is False, (
            'no executor landed on disk, so the refresh did not succeed'
        )
        assert 'no executor landed' in result['executor_detail']

    def test_generation_that_lands_a_file_is_success(self, env, monkeypatch):
        _commit(env['main_repo'], 'upstream.txt', 'new\n', 'upstream')
        _commit(env['worktree'], 'local.txt', 'mine\n', 'local work')

        spy = _GeneratorSpy(drift_status='drift', lands_executor=True)
        result = _invoke(env, monkeypatch, spy)

        assert result['executor_regenerated'] is True
        assert git_workflow.worktree_executor_path(env['worktree']).is_file()


class TestSubprocessSeamShape:
    """Pin the ACTUAL command the seam issues, and the live script's contract.

    Every test above replaces ``_run_generate_executor`` wholesale, so none of
    them would catch a drift in the verb names, the flag, the cwd pin, or the
    field the probe reads. These pin the seam against the real
    ``generate_executor.py`` so a rename there fails here rather than silently
    at runtime.
    """

    def test_seam_issues_the_expected_argv_and_pins_cwd(self, env, monkeypatch):
        captured: dict = {}

        def _fake_run(argv, **kwargs):
            captured['argv'] = argv
            captured['cwd'] = kwargs.get('cwd')

            class _R:
                returncode = 0
                stdout = 'status: success\ndrift_status: ok\n'
                stderr = ''

            return _R()

        monkeypatch.setattr(git_workflow.subprocess, 'run', _fake_run)
        git_workflow._run_generate_executor(env['worktree'], 'drift')

        argv = captured['argv']
        assert argv[1].endswith('generate_executor.py')
        assert argv[2] == 'drift'
        assert '--marketplace-root' in argv
        assert argv[argv.index('--marketplace-root') + 1] == str(env['worktree'])
        assert captured['cwd'] == str(env['worktree']), (
            'cwd MUST be pinned to the worktree — the generator resolves its '
            "OUTPUT location by walking up from cwd, so an unpinned call would "
            "rewrite main's executor"
        )

    def test_live_generator_exposes_the_verbs_and_field_the_seam_relies_on(self):
        """The real script must still carry `drift`, `generate`, and `drift_status`."""
        # Guard BEFORE the read, not after it: `read_text` on a missing path
        # raises FileNotFoundError and the actionable message below would never
        # be reached — a bypass placed after the work it guards, which is the
        # exact anti-pattern this plan's D4c promotes into ref-code-quality
        # standards/code-organization.md § Guard Clauses.
        assert git_workflow._GENERATE_EXECUTOR_PATH.is_file(), (
            f'generator not found at {git_workflow._GENERATE_EXECUTOR_PATH}'
        )
        source = git_workflow._GENERATE_EXECUTOR_PATH.read_text(encoding='utf-8')
        assert "'drift'" in source, 'the drift subcommand the probe calls'
        assert "'generate'" in source, 'the generate subcommand the refresh calls'
        assert "'drift_status'" in source, 'the field the probe parses'
        assert "'--marketplace-root'" in source, 'the flag the seam passes'


class TestConflictPathIsUnaffected:
    def test_conflicting_rebase_does_not_probe(self, env, monkeypatch):
        """A conflicted rebase left no coherent tree to regenerate from."""
        _commit(env['main_repo'], 'file.txt', 'upstream edit\n', 'upstream')
        _commit(env['worktree'], 'file.txt', 'local edit\n', 'local')

        spy = _GeneratorSpy(drift_status='drift')
        result = _invoke(env, monkeypatch, spy)

        assert result['status'] == 'conflict'
        assert spy.verbs == []
