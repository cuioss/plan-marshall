#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The main-capture refusal tests CONTAINMENT, not directory equality.

``_assert_main_capture_read_main`` refuses a handshake row whose ``main_*``
columns were read from the plan's own worktree. The refusal condition is that
the main-scoped resolution landed AT OR INSIDE ``metadata.worktree_path`` — not
that it landed exactly ON it.

**Why the distinction is not academic.** ``_main_repo_root`` delegates to
``_current_repo_root`` whenever a base-dir override is active, and
``_current_repo_root`` falls back to ``Path.cwd()`` for a FLAT override — a bare
directory that names no checkout, which is exactly what the test sandbox
installs. Under a pinned worktree the process cwd is the worktree root or, just
as often, a directory beneath it. An exact-equality check sees the first and is
blind to the second, so a ``main_sha`` read from ``<worktree>/scripts`` passed
the guard and was persisted under a column named for main.

Every case here drives a REAL linked git worktree rather than a synthesised
path, because the guard compares resolved filesystem paths and a fabricated
``worktree_path`` could satisfy the comparison without ever being a worktree.

``test_subdirectory_case_is_invisible_to_an_equality_check`` is the mutation
control: it asserts the sub-path case is genuinely NOT equal to the worktree
root, so the parametrized refusal above it cannot be passing for the reason the
old implementation would have passed for.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import _invariants
import pytest
from _invariants import MainCaptureReadTheWorktree

#: One commit id standing in for "main_sha == worktree_sha". The guard reads the
#: equality of the two columns, never their content, so a literal is honest here
#: and keeps the fixture from depending on git's actual hashes.
_SHARED_SHA = 'a' * 40

_PHASE = '5-execute'


def _git(cwd: Path, *args: str) -> str:
    """Run one git command in ``cwd``, failing loudly on a non-zero exit."""
    result = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def _main_checkout(root: Path) -> Path:
    """Create a real git repository with one commit, so a worktree can link to it."""
    main = root / 'main'
    main.mkdir(parents=True)
    _git(main, 'init', '-b', 'main')
    _git(main, 'config', 'user.email', 'test@example.com')
    _git(main, 'config', 'user.name', 'Test')
    (main / 'seed.txt').write_text('seed\n', encoding='utf-8')
    _git(main, 'add', 'seed.txt')
    _git(main, 'commit', '-m', 'seed')
    return main


def _linked_worktree(main: Path, name: str) -> Path:
    """Add a REAL linked worktree at the production path shape."""
    worktree = main / '.plan' / 'local' / 'worktrees' / name
    worktree.parent.mkdir(parents=True, exist_ok=True)
    _git(main, 'worktree', 'add', '-b', f'feature/{name}', str(worktree))
    return worktree


@pytest.fixture
def worktree_repo(tmp_path, monkeypatch):
    """A main checkout, a real linked worktree, and a FLAT base-dir override.

    The flat override is load-bearing rather than incidental: it is what makes
    ``_main_repo_root`` resolve through ``Path.cwd()``, which is the production
    mechanism by which a main-scoped read can land inside the worktree at all.
    Set explicitly here rather than inherited from the autouse sandbox, so the
    test states the precondition it depends on instead of assuming the sandbox's
    shape.
    """
    main = _main_checkout(tmp_path)
    worktree = _linked_worktree(main, 'wt')
    flat_base = tmp_path / 'flat-base'
    flat_base.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(flat_base))
    return main, worktree


def _cwd_for(kind: str, main: Path, worktree: Path) -> Path:
    """Resolve a parametrized cwd label to a real directory on disk."""
    if kind == 'worktree_root':
        return worktree
    if kind == 'worktree_subdir':
        target = worktree / 'scripts'
        target.mkdir(parents=True, exist_ok=True)
        return target
    if kind == 'worktree_nested_subdir':
        target = worktree / 'marketplace' / 'bundles' / 'x'
        target.mkdir(parents=True, exist_ok=True)
        return target
    if kind == 'main_root':
        return main
    raise AssertionError(f'unknown cwd kind {kind!r}')


@pytest.mark.parametrize(
    ('cwd_kind', 'refuses'),
    [
        # The worktree root itself — the only case the retired equality check saw.
        ('worktree_root', True),
        # One level down, and several levels down: both describe the worktree
        # just as surely, and both were invisible to equality.
        ('worktree_subdir', True),
        ('worktree_nested_subdir', True),
        # Outside the worktree entirely — a genuine main-scoped read, permitted.
        ('main_root', False),
    ],
)
def test_containment_decides_the_refusal(worktree_repo, monkeypatch, cwd_kind, refuses):
    """A main-scoped read from anywhere at-or-inside the worktree is refused."""
    main, worktree = worktree_repo
    monkeypatch.chdir(_cwd_for(cwd_kind, main, worktree))

    captured = {'main_sha': _SHARED_SHA, 'worktree_sha': _SHARED_SHA}
    metadata = {'worktree_path': str(worktree)}

    if refuses:
        with pytest.raises(MainCaptureReadTheWorktree) as excinfo:
            _invariants._assert_main_capture_read_main(captured, metadata, _PHASE)
        message = str(excinfo.value)
        # The message must name BOTH resolved paths, because "these two are the
        # same tree" is the claim the operator has to check.
        assert str(worktree) in message
        assert _SHARED_SHA in message
    else:
        assert _invariants._assert_main_capture_read_main(captured, metadata, _PHASE) is None


def test_subdirectory_case_is_invisible_to_an_equality_check(worktree_repo, monkeypatch):
    """Mutation control: the sub-path case is NOT directory equality.

    Without this, ``test_containment_decides_the_refusal``'s ``worktree_subdir``
    row could be passing because the path happened to equal the worktree root,
    which would make the whole parametrization agree with the implementation it
    replaced.
    """
    main, worktree = worktree_repo
    subdir = _cwd_for('worktree_subdir', main, worktree)

    assert subdir.resolve() != worktree.resolve()
    assert subdir.resolve().is_relative_to(worktree.resolve())


def test_distinct_trees_sharing_one_commit_are_permitted(worktree_repo, monkeypatch):
    """Equal commits alone are NOT the trigger — the containment is.

    A worktree-backed plan whose feature branch carries no commit of its own
    legitimately has ``main_sha == worktree_sha``. The shipped phase-5 flow
    produces that state (Step 2.5 materializes the worktree before the
    ``early_terminate`` short-circuit), so refusing it would hard-block a
    correct boundary with no escape.
    """
    main, worktree = worktree_repo
    monkeypatch.chdir(main)

    captured = {'main_sha': _SHARED_SHA, 'worktree_sha': _SHARED_SHA}
    metadata = {'worktree_path': str(worktree)}

    assert _invariants._assert_main_capture_read_main(captured, metadata, _PHASE) is None


@pytest.mark.parametrize('cwd_kind', ['worktree_root', 'worktree_subdir'])
def test_unequal_shas_never_refuse_however_contained(worktree_repo, monkeypatch, cwd_kind):
    """Containment alone is not enough — the two columns must also be equal.

    The guard's first clause short-circuits on unequal SHAs, so a contained
    resolution with two different commits is not the state being refused.
    """
    main, worktree = worktree_repo
    monkeypatch.chdir(_cwd_for(cwd_kind, main, worktree))

    captured = {'main_sha': _SHARED_SHA, 'worktree_sha': 'b' * 40}
    metadata = {'worktree_path': str(worktree)}

    assert _invariants._assert_main_capture_read_main(captured, metadata, _PHASE) is None


@pytest.mark.parametrize(
    'captured',
    [
        pytest.param({'worktree_sha': _SHARED_SHA}, id='no_main_sha'),
        pytest.param({'main_sha': _SHARED_SHA}, id='no_worktree_sha'),
        pytest.param({}, id='neither_captured'),
    ],
)
def test_a_missing_column_short_circuits_before_any_path_work(worktree_repo, monkeypatch, captured):
    """A plan with no worktree captures no ``worktree_sha``, so nothing is compared."""
    main, worktree = worktree_repo
    monkeypatch.chdir(_cwd_for('worktree_subdir', main, worktree))

    metadata = {'worktree_path': str(worktree)}

    assert _invariants._assert_main_capture_read_main(captured, metadata, _PHASE) is None


def test_absent_worktree_path_cannot_refuse(worktree_repo, monkeypatch):
    """Without a persisted ``worktree_path`` there is no containment to test."""
    main, worktree = worktree_repo
    monkeypatch.chdir(_cwd_for('worktree_subdir', main, worktree))

    captured = {'main_sha': _SHARED_SHA, 'worktree_sha': _SHARED_SHA}

    assert _invariants._assert_main_capture_read_main(captured, {}, _PHASE) is None
