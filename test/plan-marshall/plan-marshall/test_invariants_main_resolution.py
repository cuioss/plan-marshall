#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Main-anchored resolution for the ``main_*`` handshake columns.

A column named for main must be read from main. ``_current_repo_root`` is
cwd-relative by design (ADR-002) and follows the worktree the working directory
is pinned to from phase-5 onward, so the main-scoped captures resolve through
``_main_repo_root`` instead. This suite pins that split at the resolver and at
the captures:

* **the resolver** — ``_main_repo_root`` against a REAL linked worktree with cwd
  pinned into it, plus the override and not-a-repo branches. The resolver is
  where the defect lived, so it is asserted directly and not only through a
  capture that could pass for the wrong reason.
* **the captures** — ``_capture_main_sha`` records main's HEAD while
  ``_capture_worktree_sha`` records the worktree's, so the two columns of one
  row describe two different trees. One capture is asserted the other way round
  too: a real worktree whose branch carries no commit must be captured, not
  refused.

The capture-time refusal — which fires on the same-tree READ, not on equal
commits — lives in the sibling ``test_invariants_main_capture_refusal.py``.

The final test closes the loop onto the consumer: the retrospective
summariser's ``detect_drift`` must see no ``main_sha`` movement across the
boundary where cwd flips from main to the worktree, when main itself did not
move.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from conftest import get_script_path, load_script_module

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-marshall', 'phase_handshake.py')
SCRIPTS_DIR = SCRIPT_PATH.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _invariants as inv
import file_ops


def _git(cwd: Path, *args: str) -> str:
    """Run git in ``cwd`` and return stripped stdout, failing loudly."""
    result = subprocess.run(
        ['git', *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return result.stdout.strip()


def _init_main_repo(repo: Path) -> None:
    """Initialise a fixture repo whose ``.plan/local`` is gitignored.

    Mirrors ``test_marketplace_paths._init_repo`` so ``git worktree add``
    materialises a clean tree.
    """
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, 'init', '-q', '-b', 'main')
    _git(repo, 'config', 'user.email', 't@t.test')
    _git(repo, 'config', 'user.name', 'Test')
    (repo / 'README.md').write_text('x\n', encoding='utf-8')
    (repo / '.gitignore').write_text('.plan/local\n', encoding='utf-8')
    _git(repo, 'add', '.')
    _git(repo, 'commit', '-q', '-m', 'init')


@pytest.fixture()
def production_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear both base-dir overrides so the production git branch is exercised.

    The autouse ``_plan_base_dir_sandbox`` sets ``PLAN_BASE_DIR`` for every
    test, which would short-circuit ``_main_repo_root`` into its override
    branch and never reach the git-common-dir resolution under test. Mirrors
    ``test_marketplace_paths.TestResolveMainAnchoredPath.no_plan_base_dir``.
    """
    monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
    monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)


@pytest.fixture()
def main_and_worktree(tmp_path: Path) -> dict[str, Path]:
    """A real main checkout plus a real linked worktree on its own branch.

    The worktree carries one extra commit, so the two HEADs genuinely differ
    and an equal pair can only come from reading one tree twice.
    """
    main_repo = tmp_path / 'main'
    _init_main_repo(main_repo)
    worktree = tmp_path / 'wt'
    _git(main_repo, 'worktree', 'add', '-q', '-b', 'feature/plan', str(worktree))
    (worktree / 'work.txt').write_text('deliverable\n', encoding='utf-8')
    _git(worktree, 'add', 'work.txt')
    _git(worktree, 'commit', '-q', '-m', 'feat: deliverable')
    return {'main': main_repo, 'worktree': worktree}


# =============================================================================
# _main_repo_root / _current_repo_root — the resolver itself (D2)
# =============================================================================


def test_main_repo_root_resolves_to_main_from_pinned_worktree_cwd(
    main_and_worktree: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    production_resolution: None,
) -> None:
    """With cwd pinned to the worktree, the resolver still returns MAIN.

    This is the defect asserted at its own site: pre-fix the resolver inferred
    the root by walking up from the cwd-relative base directory and therefore
    returned the worktree.
    """
    monkeypatch.chdir(main_and_worktree['worktree'])

    resolved = inv._main_repo_root()

    assert resolved is not None
    assert resolved.resolve() == main_and_worktree['main'].resolve()
    assert resolved.resolve() != main_and_worktree['worktree'].resolve()


def test_current_repo_root_still_follows_pinned_worktree_cwd(
    main_and_worktree: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    production_resolution: None,
) -> None:
    """The cwd-relative resolver keeps following the worktree — by design.

    ``_run_script`` resolves the worktree-resident executor and the plan state
    moved in at phase-5 start through this resolver, so redirecting it to main
    would break every plan-state capture. The two resolvers must disagree here;
    that disagreement IS the fix.
    """
    worktree = main_and_worktree['worktree']
    (worktree / '.plan' / 'local').mkdir(parents=True)
    monkeypatch.chdir(worktree)

    assert inv._current_repo_root().resolve() == worktree.resolve()
    assert inv._current_repo_root().resolve() != main_and_worktree['main'].resolve()


def test_main_repo_root_honours_base_dir_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An active ``PLAN_BASE_DIR`` override wins over the git resolution.

    Keeps every override-based consumer test meaningful: the override directory
    stands in for the checkout's ``.plan/local``, and such a fixture has exactly
    one checkout, so main and current coincide.
    """
    main_base = tmp_path / 'stand-in' / '.plan' / 'local'
    main_base.mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))

    resolved = inv._main_repo_root()

    assert resolved is not None
    assert resolved.resolve() == (tmp_path / 'stand-in').resolve()


def test_main_repo_root_returns_none_outside_a_git_repository(
    outside_repo_dir: Path, monkeypatch: pytest.MonkeyPatch, production_resolution: None
) -> None:
    """Unresolvable main → ``None``, never a silent fall back to cwd.

    A cwd fallback is exactly the mis-resolution the resolver exists to end, so
    "unknown" must stay unknown and leave the column empty.

    Uses ``outside_repo_dir`` rather than ``tmp_path``: ``build.py`` pins
    pytest's ``--basetemp`` under the repo's own ``.plan/temp/``, so a
    ``tmp_path`` subdirectory is INSIDE this git worktree and ``git rev-parse``
    still resolves from it — the ``chdir`` would be inert and the test would
    prove only that the stub raises. The fixture allocates under ``$TMPDIR``,
    so the cwd genuinely has no repository above it and the real
    ``git rev-parse`` failure path is what produces the ``None`` — no stub is
    involved.
    """
    monkeypatch.chdir(outside_repo_dir)

    assert inv._main_repo_root() is None


# =============================================================================
# The main-scoped captures (D5a)
# =============================================================================


def test_capture_main_sha_records_main_head_not_the_pinned_worktree_head(
    main_and_worktree: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    production_resolution: None,
) -> None:
    """At the phase-5 boundary the two columns describe two different trees.

    The row that motivated this fix recorded a feature-branch commit under
    ``main_sha`` while ``worktree_sha`` sat beside it holding the same value.
    """
    main_repo = main_and_worktree['main']
    worktree = main_and_worktree['worktree']
    monkeypatch.chdir(worktree)
    metadata = {'use_worktree': True, 'worktree_path': str(worktree)}

    main_sha = inv._capture_main_sha('p', metadata, '5-execute')
    worktree_sha = inv._capture_worktree_sha('p', metadata, '5-execute')

    assert main_sha == _git(main_repo, 'rev-parse', 'HEAD')
    assert worktree_sha == _git(worktree, 'rev-parse', 'HEAD')
    assert main_sha != worktree_sha


def test_capture_main_dirty_reads_main_not_the_pinned_worktree(
    main_and_worktree: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    production_resolution: None,
) -> None:
    """The companion dirty count is read from the same tree as ``main_sha``.

    Dirties only the WORKTREE, so a count above zero can only mean the capture
    read the worktree instead of main.
    """
    worktree = main_and_worktree['worktree']
    (worktree / 'uncommitted.txt').write_text('scratch\n', encoding='utf-8')
    monkeypatch.chdir(worktree)

    assert inv._capture_main_dirty('p', {}, '5-execute') == 0
    assert inv._capture_worktree_dirty('p', {'worktree_path': str(worktree)}, '5-execute') == 1


def test_capture_main_sha_leaves_column_empty_when_main_unresolvable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unresolvable main → ``None`` (empty column), never the ambient tree."""
    monkeypatch.setattr(inv, '_main_repo_root', lambda: None)
    monkeypatch.setattr(
        inv, 'git_head', lambda _root: pytest.fail('git must not be probed at all')
    )

    assert inv._capture_main_sha('p', {}, '5-execute') is None


def test_capture_main_dirty_files_leaves_column_empty_when_main_unresolvable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same contract for the layer-D path list."""
    monkeypatch.setattr(inv, '_main_repo_root', lambda: None)
    monkeypatch.setattr(
        inv, 'git_dirty_files', lambda _root: pytest.fail('git must not be probed at all')
    )

    assert inv._capture_main_dirty_files('p', {}, '5-execute') is None


def test_a_commit_less_feature_branch_is_captured_not_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, production_resolution: None
) -> None:
    """A REAL worktree whose branch carries no commit must capture, not refuse.

    ``phase-5-execute`` Step 2.5 materializes the worktree unconditionally,
    before the ``early_terminate`` short-circuit, so an analysis-only plan
    reaches its phase-5 boundary in exactly this state: two distinct trees, one
    commit, nothing wrong. Refusing it would hard-block the boundary with no
    override escape and write no ``5-execute`` row — which the summariser then
    classifies as "the phase did not complete its handshake".

    Deliberately built from a real ``git worktree add`` with **no** commit on the
    branch, rather than by stubbing ``git_head`` to one value: the whole point is
    that the equal pair here is genuine, and a stub cannot show that.
    """
    main_repo = tmp_path / 'main'
    _init_main_repo(main_repo)
    worktree = tmp_path / 'wt'
    _git(main_repo, 'worktree', 'add', '-q', '-b', 'feature/analysis-only', str(worktree))
    monkeypatch.chdir(worktree)
    monkeypatch.setattr(
        inv, 'INVARIANTS', [e for e in inv.INVARIANTS if e[0] in ('main_sha', 'worktree_sha')]
    )
    metadata = {'use_worktree': True, 'worktree_path': str(worktree)}

    captured = inv.capture_all('p', metadata, '5-execute')

    head = _git(main_repo, 'rev-parse', 'HEAD')
    assert captured == {'main_sha': head, 'worktree_sha': head}


# =============================================================================
# The drift consumer (D5c)
# =============================================================================


def test_summariser_sees_no_main_sha_drift_across_the_execute_boundary(
    main_and_worktree: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    production_resolution: None,
) -> None:
    """No drift warning across the boundary where cwd flips to the worktree.

    Rows are built by the REAL capture at both boundaries — cwd on main for the
    planning row, cwd pinned to the worktree for the execute row — so the drift
    verdict is derived rather than hand-fed. Pre-fix the execute row carried the
    feature-branch commit and the summariser reported ``main_sha`` drift on
    every worktree-backed plan while main had not moved.
    """
    summarize = load_script_module(
        'plan-marshall', 'plan-retrospective', 'summarize-invariants.py', 'si_drift_mod'
    )
    main_repo = main_and_worktree['main']
    worktree = main_and_worktree['worktree']
    metadata = {'use_worktree': True, 'worktree_path': str(worktree)}

    monkeypatch.chdir(main_repo)
    planning_sha = inv._capture_main_sha('p', metadata, '4-plan')
    monkeypatch.chdir(worktree)
    execute_sha = inv._capture_main_sha('p', metadata, '5-execute')

    phase_map = {
        '4-plan': {'main_sha': planning_sha},
        '5-execute': {'main_sha': execute_sha},
    }

    assert summarize.detect_drift(phase_map) == []
