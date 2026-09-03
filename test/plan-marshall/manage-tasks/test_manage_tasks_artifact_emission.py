#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ``[ARTIFACT]`` channel is script-owned, and it fires against a REAL base.

``[OUTCOME]`` was moved into ``manage-tasks finalize-step`` because a
caller-side emission is lost when an execution-context is re-dispatched before
it fires. ``[ARTIFACT]`` sat one paragraph below it in the same standard and
stayed prose-instructed, so it inherited exactly that loss.

⛔ These tests run against a REAL git repository with a REAL recorded baseline,
not against a stubbed differ. The archetype this deliverable had to avoid is
readers-and-tests-but-no-writer: at the time of the change no script read or
wrote ``task_start_sha``, so a test that only proved "the code path exists"
would have passed against a channel that could never fire. Every assertion below
therefore starts from a commit, mutates the tree, and reads what the script
actually emitted.
"""


from __future__ import annotations

import subprocess

import pytest

from conftest import load_script_module

_artifacts = load_script_module(
    'plan-marshall', 'manage-tasks', '_task_artifacts.py', module_name='_task_artifacts_test_mod'
)

#: Long enough that git's similarity detection scores the rename at 100%.
_RENAME_BODY = 'a stable body line\n' * 20


def _git(root, *argv: str) -> None:
    subprocess.run(['git', '-C', str(root), *argv], check=True, capture_output=True, text=True)


def _head(root) -> str:
    completed = subprocess.run(
        ['git', '-C', str(root), 'rev-parse', 'HEAD'],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


@pytest.fixture
def git_repo(tmp_path):
    """A real repository with one commit, holding the fixtures each case mutates."""
    root = tmp_path / 'repo'
    root.mkdir()
    _git(root, 'init', '-q')
    _git(root, 'config', 'user.email', 'test@example.com')
    _git(root, 'config', 'user.name', 'Test')
    (root / 'kept.txt').write_text('base\n', encoding='utf-8')
    (root / 'doomed.txt').write_text('bye\n', encoding='utf-8')
    (root / 'renamed-from.txt').write_text(_RENAME_BODY, encoding='utf-8')
    _git(root, 'add', '-A')
    _git(root, 'commit', '-q', '-m', 'base')
    return root


def _bodies(messages: list[str]) -> set[str]:
    """Strip the caller prefix so a case asserts the MESSAGE, not the prefix.

    The prefix has its own dedicated test below — asserting it in every case
    would be one assertion repeated N times rather than N assertions.
    """
    return {message.split(') ', 1)[1] for message in messages}


class TestStatusCodeMapping:
    """Each git status code maps to exactly one documented message shape."""

    def test_a_modified_file_is_reported_as_written(self, git_repo):
        base = _head(git_repo)
        (git_repo / 'kept.txt').write_text('changed\n', encoding='utf-8')

        messages = _artifacts.artifact_messages(7, base, root=git_repo)

        assert _bodies(messages) == {'Wrote kept.txt'}

    def test_a_deleted_file_is_reported_as_deleted(self, git_repo):
        base = _head(git_repo)
        (git_repo / 'doomed.txt').unlink()

        messages = _artifacts.artifact_messages(7, base, root=git_repo)

        assert _bodies(messages) == {'Deleted doomed.txt'}

    def test_a_rename_produces_exactly_one_line(self, git_repo):
        """Never a delete plus a write — that leaves the intent ambiguous."""
        base = _head(git_repo)
        _git(git_repo, 'mv', 'renamed-from.txt', 'renamed-to.txt')

        messages = _artifacts.artifact_messages(7, base, root=git_repo)

        assert messages == [
            '[ARTIFACT] (plan-marshall:phase-5-execute:7) '
            'Renamed renamed-from.txt -> renamed-to.txt'
        ]

    def test_an_untracked_new_file_is_reported(self, git_repo):
        """⛔ A created file is in NO ``git diff`` output until it is staged.

        Omitting the untracked walk would silently drop every new file a task
        wrote — the largest class of artifact an implementation task produces.
        """
        base = _head(git_repo)
        (git_repo / 'brand-new.txt').write_text('new\n', encoding='utf-8')

        messages = _artifacts.artifact_messages(7, base, root=git_repo)

        assert _bodies(messages) == {'Wrote brand-new.txt'}

    def test_an_unchanged_tree_emits_nothing(self, git_repo):
        """The negative control — a differ that fired on everything would pass alone."""
        assert _artifacts.artifact_messages(7, _head(git_repo), root=git_repo) == []


class TestDiffBase:
    """The diff is taken against the WORKING TREE, and against the RECORDED base."""

    def test_uncommitted_edits_are_seen(self, git_repo):
        """⛔ The window this channel covers is entirely pre-commit.

        A ``{base}..HEAD`` comparison is empty here — the task's edits have not
        been committed yet, and will not be until the per-deliverable chain
        tail. A test that committed first would pass against the wrong form.
        """
        base = _head(git_repo)
        (git_repo / 'kept.txt').write_text('uncommitted\n', encoding='utf-8')

        assert _head(git_repo) == base
        assert _bodies(_artifacts.artifact_messages(7, base, root=git_repo)) == {'Wrote kept.txt'}

    def test_committed_changes_are_still_seen(self, git_repo):
        """The complementary control: the base is a commit, so a commit since it counts."""
        base = _head(git_repo)
        (git_repo / 'kept.txt').write_text('committed\n', encoding='utf-8')
        _git(git_repo, 'commit', '-q', '-am', 'later')

        assert _head(git_repo) != base
        assert _bodies(_artifacts.artifact_messages(7, base, root=git_repo)) == {'Wrote kept.txt'}

    def test_an_unresolvable_base_emits_nothing_rather_than_raising(self, git_repo):
        """An audit channel must never take the task-closing call down."""
        assert _artifacts.artifact_messages(7, 'deadbeef' * 5, root=git_repo) == []


class TestCallerPrefix:
    """The three-segment prefix carries the numeric task id."""

    def test_the_prefix_names_the_task_number(self, git_repo):
        base = _head(git_repo)
        (git_repo / 'kept.txt').write_text('changed\n', encoding='utf-8')

        messages = _artifacts.artifact_messages(42, base, root=git_repo)

        assert messages[0].startswith('[ARTIFACT] (plan-marshall:phase-5-execute:42) ')


class TestBaselineCapture:
    """``task_start_sha`` has a writer, and it is idempotent."""

    def test_the_baseline_is_recorded_on_the_task(self, git_repo, monkeypatch):
        monkeypatch.setattr(_artifacts, 'cwd_checkout_root', lambda: str(git_repo))
        task: dict = {}

        captured = _artifacts.capture_task_start_sha(task)

        assert captured == _head(git_repo)
        assert task[_artifacts.TASK_START_SHA_FIELD] == _head(git_repo)

    def test_a_second_capture_does_not_move_the_base(self, git_repo, monkeypatch):
        """⛔ A re-entry that re-based would silently shrink the artifact list.

        Only the edits made after the re-entry would then be reported, and the
        loss would be invisible: the list is still non-empty and still plausible.
        """
        monkeypatch.setattr(_artifacts, 'cwd_checkout_root', lambda: str(git_repo))
        task: dict = {}
        first = _artifacts.capture_task_start_sha(task)
        (git_repo / 'kept.txt').write_text('advanced\n', encoding='utf-8')
        _git(git_repo, 'commit', '-q', '-am', 'advance')

        second = _artifacts.capture_task_start_sha(task)

        assert _head(git_repo) != first
        assert second == first
        assert task[_artifacts.TASK_START_SHA_FIELD] == first

    def test_an_unresolvable_head_writes_no_baseline(self, tmp_path, monkeypatch):
        """A fabricated base is worse than an honestly-absent one."""
        not_a_repo = tmp_path / 'plain'
        not_a_repo.mkdir()
        monkeypatch.setattr(_artifacts, 'cwd_checkout_root', lambda: str(not_a_repo))
        task: dict = {}

        assert _artifacts.capture_task_start_sha(task) is None
        assert _artifacts.TASK_START_SHA_FIELD not in task


class TestEmissionGate:
    """A task with no recorded baseline emits nothing at all."""

    def test_no_baseline_emits_no_lines(self, git_repo, monkeypatch):
        monkeypatch.setattr(_artifacts, 'cwd_checkout_root', lambda: str(git_repo))
        (git_repo / 'kept.txt').write_text('changed\n', encoding='utf-8')

        assert _artifacts.emit_artifact_lines('some-plan', 7, {}) == []

    def test_a_recorded_baseline_emits_the_lines(self, git_repo, monkeypatch):
        """The matched positive control: the gate above must not be vacuous."""
        monkeypatch.setattr(_artifacts, 'cwd_checkout_root', lambda: str(git_repo))
        emitted: list[str] = []
        monkeypatch.setattr(
            _artifacts,
            'log_entry',
            lambda _kind, _plan, _level, message: emitted.append(message),
        )
        task = {_artifacts.TASK_START_SHA_FIELD: _head(git_repo)}
        (git_repo / 'kept.txt').write_text('changed\n', encoding='utf-8')

        returned = _artifacts.emit_artifact_lines('some-plan', 7, task)

        assert _bodies(returned) == {'Wrote kept.txt'}
        assert emitted == returned
