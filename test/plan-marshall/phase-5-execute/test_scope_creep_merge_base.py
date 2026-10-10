#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The scope-creep guard against a REAL repository.

Every other scope-creep suite patches the git reads, so none of them can show
that the range the guard diffs is the right one. This suite builds a throwaway
origin and a clone under the test's temporary directory and runs the guard's own
``git merge-base`` and ``git diff`` against them. Only two things are pointed at
the fixture: the worktree resolution (at the clone) and the plan directory (via
the ``plan_context`` fixture).

The property under test: the residual is the plan's OWN changes — the files the
branch changed since it diverged from its base — and never a file a base commit
changed, whether that commit is older than the branch point, newer than it, or
merged into the branch.

Each plan's references.json also carries a stale SHA recorded when the plan was
created, pointing at the origin's first commit. It is seeded only to prove the
guard ignores it: a diff from that SHA would count the base's own file as
residual in every case below.
"""

from __future__ import annotations

import json
import os
import subprocess
from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest

# PLAIN import, deliberately — matching the sibling suites, so the module is
# bound once and the patches below land on the copy ``cmd_check`` runs in.
import scope_creep_check as scc
from toon_parser import parse_toon

_BASE_FILE = 'base_changed.txt'
_LATER_BASE_FILE = 'base_changed_later.txt'
_PLAN_FILE = 'plan_changed.txt'


# ---------------------------------------------------------------------------
# Repository helpers
# ---------------------------------------------------------------------------


def _git(cwd: Path, *args: str) -> str:
    """Run git in ``cwd``, isolated from the developer's and the system's config."""
    env = dict(os.environ)
    env.update(
        {
            'GIT_CONFIG_GLOBAL': os.devnull,
            'GIT_CONFIG_SYSTEM': os.devnull,
            'GIT_AUTHOR_NAME': 'scope-creep-test',
            'GIT_AUTHOR_EMAIL': 'scope-creep-test@example.invalid',
            'GIT_COMMITTER_NAME': 'scope-creep-test',
            'GIT_COMMITTER_EMAIL': 'scope-creep-test@example.invalid',
        }
    )
    result = subprocess.run(['git', *args], cwd=cwd, env=env, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _commit_file(repo: Path, name: str, message: str) -> str:
    """Write ``name`` in ``repo``, commit it, and return the new commit's SHA."""
    (repo / name).write_text(f'{message}\n', encoding='utf-8')
    _git(repo, 'add', name)
    _git(repo, 'commit', '-m', message)
    return _git(repo, 'rev-parse', 'HEAD')


class _Repos:
    """A throwaway origin and a clone with a plan branch cut from the base."""

    def __init__(self, root: Path):
        self.origin = root / 'origin'
        self.clone = root / 'clone'
        self.origin.mkdir()
        _git(self.origin, 'init', '--initial-branch=main')
        # The stale baseline a plan created against this commit would have
        # recorded. The base then changes a file BEFORE the branch is cut.
        self.first_base_sha = _commit_file(self.origin, 'README.txt', 'initial commit')
        _commit_file(self.origin, _BASE_FILE, 'base changes a file before the branch is cut')
        _git(root, 'clone', str(self.origin), str(self.clone))
        _git(self.clone, 'checkout', '-b', 'feature/plan')
        _commit_file(self.clone, _PLAN_FILE, 'the plan changes its own file')

    def base_moves_on(self) -> None:
        """Land a further base commit and fetch it, so ``origin/main`` advances."""
        _commit_file(self.origin, _LATER_BASE_FILE, 'base changes another file after the branch was cut')
        _git(self.clone, 'fetch', 'origin')

    def merge_base_into_branch(self) -> None:
        """Merge the advanced base into the plan branch."""
        _git(self.clone, 'merge', '--no-edit', 'origin/main')


@pytest.fixture
def repos(tmp_path) -> _Repos:
    return _Repos(tmp_path)


def _run_guard(
    plan_context,
    monkeypatch,
    capsys,
    repos: _Repos,
    plan_id: str,
    base_branch: str = 'main',
) -> tuple[int, dict[str, Any]]:
    """Seed a plan that declares nothing and run the guard against the clone."""
    plan_dir: Path = plan_context.plan_dir_for(plan_id)
    refs = {
        'base_branch': base_branch,
        # Stale, and deliberately so — see the module docstring.
        'plan_creation_sha': repos.first_base_sha,
        'affected_files': [],
    }
    (plan_dir / 'references.json').write_text(json.dumps(refs), encoding='utf-8')
    monkeypatch.setattr(scc, '_resolve_worktree', lambda _plan_id: repos.clone)

    rc = scc.cmd_check(Namespace(plan_id=plan_id, threshold=None))
    payload: dict[str, Any] = parse_toon(capsys.readouterr().out)
    return rc, payload


# ---------------------------------------------------------------------------
# The residual is the branch's own files
# ---------------------------------------------------------------------------


def test_fixture_reproduces_the_stale_baseline_defect(repos):
    """Control: a diff from the recorded SHA DOES cover the base's own file.

    Without this, the cases below could pass against a fixture in which the
    stale baseline and the merge-base happened to be the same commit, and would
    then prove nothing about which of the two the guard uses.
    """
    from_recorded_sha = _git(repos.clone, 'diff', '--name-only', f'{repos.first_base_sha}..HEAD').splitlines()

    assert sorted(from_recorded_sha) == sorted([_BASE_FILE, _PLAN_FILE])


def test_branch_cut_after_a_base_change_reads_only_its_own_file(plan_context, monkeypatch, capsys, repos):
    """A file the base changed before the branch was cut is not residual."""
    rc, payload = _run_guard(plan_context, monkeypatch, capsys, repos, 'scope-creep-real-branch-point')

    assert rc == 0
    assert payload['status'] == 'success'
    assert payload['residual_count'] == 1
    assert payload['residual_files'] == [_PLAN_FILE]


def test_base_moving_on_after_the_branch_was_cut_changes_nothing(plan_context, monkeypatch, capsys, repos):
    """A base commit newer than the branch point is not residual either."""
    repos.base_moves_on()

    rc, payload = _run_guard(plan_context, monkeypatch, capsys, repos, 'scope-creep-real-base-moved')

    assert rc == 0
    assert payload['status'] == 'success'
    assert payload['residual_count'] == 1
    assert payload['residual_files'] == [_PLAN_FILE]


def test_base_merged_into_the_branch_still_reads_only_the_branch_files(plan_context, monkeypatch, capsys, repos):
    """Merging the base into the branch brings its files in without making them residual."""
    repos.base_moves_on()
    repos.merge_base_into_branch()
    # The merged-in file really is on the branch now — the guard must leave it
    # out because of the range it diffs, not because the file is absent.
    assert (repos.clone / _LATER_BASE_FILE).is_file()

    rc, payload = _run_guard(plan_context, monkeypatch, capsys, repos, 'scope-creep-real-base-merged')

    assert rc == 0
    assert payload['status'] == 'success'
    assert payload['residual_count'] == 1
    assert payload['residual_files'] == [_PLAN_FILE]


# ---------------------------------------------------------------------------
# No merge-base, no measurement
# ---------------------------------------------------------------------------


def test_unresolvable_base_branch_is_could_not_look(plan_context, monkeypatch, capsys, repos):
    """An ``origin/{base_branch}`` that does not resolve yields no count at all."""
    rc, payload = _run_guard(
        plan_context,
        monkeypatch,
        capsys,
        repos,
        'scope-creep-real-no-base-ref',
        base_branch='no-such-branch',
    )

    assert rc == 0
    assert payload['status'] == 'could_not_look'
    assert payload['reason'] == 'merge_base_unresolved'
    assert 'origin/no-such-branch' in payload['detail']
    assert 'residual_count' not in payload
    assert 'residual_files' not in payload
    assert payload['finding_emitted'] is False
