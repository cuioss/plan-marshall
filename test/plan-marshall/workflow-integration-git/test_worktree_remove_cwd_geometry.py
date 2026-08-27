#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Real-resolver cwd-geometry regression suite for ``git-workflow worktree-remove``.

Both of ``cmd_worktree_remove``'s preconditions are decided by **where the calling
process stands**:

* ``plan_dir_not_moved_back`` — probed through ``marketplace_paths.main_checkout_root``
  (git's common dir), which names main from any linked worktree. Its predecessor
  probed through the cwd-relative walk-up, so a caller standing inside the worktree
  satisfied the guard with the very plan-state copy the removal was about to destroy.
* ``cwd_inside_removal_target`` — a containment test between ``Path.cwd()`` and the
  resolved removal target.

Neither failure mode is observable by a test that patches a path resolver: a patched
resolver returns whatever the test told it to and cannot report where the process is
standing, so the pre-fix and post-fix implementations answer identically under it.
This suite therefore varies **cwd and nothing else**, over a real ``git init`` main
checkout with a real ``git worktree add`` linked worktree, using ``monkeypatch.chdir``.
``_find_plan_root_from_cwd`` and ``main_checkout_root`` are NEVER patched here — that
is the deliverable, not an implementation detail.

The geometry mirrors production: the worktree is nested under the main checkout at
``main/.plan/local/worktrees/{plan_id}``, so main is an ANCESTOR of the target and the
containment test has to distinguish "inside the target" from "inside the repository".

The one stubbed seam, and why
-----------------------------
``file_ops._query_worktree_path`` — the single ``manage-status get-worktree-path``
subprocess boundary in the codebase, stubbed through the shared
``patch_query_worktree_path`` helper. It is stubbed for a structural reason, not for
convenience: this fixture anchors ``PLAN_BASE_DIR`` at ``main/.plan/local``, which is
the SAME directory ``_plan_dir_on_main_checkout`` probes. In the pre-move-back
geometry the plan dir is deliberately absent from main — so serving the persisted
worktree path out of that store would fail for exactly the reason the guard is being
asserted about, and the run would never reach the guard at all.

The stub is safe for this suite's purpose because it is **cwd-invariant**: it returns
one constant absolute path regardless of where the process stands, so it cannot mask a
cwd-sensitive defect. Every resolver that DOES read cwd runs for real.

Matrix, and which cells are the positive cases
----------------------------------------------
``TestCwdGeometryMatrix`` walks the full cross-product of the two axes the two
preconditions read — caller cwd (main / worktree) and plan-dir residency (landed on
main / not landed). Each cell differs from its neighbours along exactly one axis,
which is what makes the pair matched:

===============  ==============  ================================
caller cwd       landed on main  expected outcome
===============  ==============  ================================
main             no              ``plan_dir_not_moved_back``
main             yes             removal proceeds
worktree         no              ``plan_dir_not_moved_back``
worktree         yes             ``cwd_inside_removal_target``
===============  ==============  ================================

The two ``worktree`` rows are the POSITIVE cases — each was demonstrated failing
against the corresponding pre-fix implementation, which is the check that the suite is
capable of observing the defect at all. The two ``main`` rows are the matched negative
CONTROLS and pass both before and after the fix; that is what makes the positive rows'
refusals attributable to cwd rather than to anything the fixture arranged.

The ``worktree``/landed row is also the unpatched analogue of the neutralised-predicate
case: the move-back predicate genuinely reports success there (main really does hold the
plan dir), so the containment refusal is shown to rest on its own defence without any
predicate being forced.

Every refusal asserts that the worktree-resident ``status.json`` is still on disk
afterwards. The return code alone would not show that the file these guards exist to
protect survived — which is the property under test.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from _resolve_project_dir_fixtures import patch_query_worktree_path

from conftest import load_script_module, parse_ns

_GIT_WF = ('plan-marshall', 'workflow-integration-git', 'git-workflow.py')

git_workflow = load_script_module(*_GIT_WF)

_PLAN_ID = 'cwd-geometry-plan'
_BRANCH = f'feature/{_PLAN_ID}'

# Built by the script's OWN parser so every default the production CLI applies is
# present, and hoisted to module scope because ``parse_ns`` re-executes the script
# module on each call. ``cmd_worktree_remove`` never mutates its namespace, so one
# instance per flag combination is safe to share across tests.
_NS_PLAIN = parse_ns(*_GIT_WF, 'worktree-remove', '--plan-id', _PLAN_ID, register=False)
_NS_FORCE = parse_ns(
    *_GIT_WF, 'worktree-remove', '--plan-id', _PLAN_ID, '--force', register=False
)


def _init_main_repo(main: Path) -> None:
    """Seed a real main checkout whose ``.gitignore`` covers ``.plan/``.

    The ignore rule matters: worktree-resident plan state is untracked, and
    ``git worktree remove`` without ``--force`` refuses a worktree carrying untracked
    files. Ignoring ``.plan/`` keeps the plan state from blocking the non-force removal,
    so the only thing that can refuse is one of the two preconditions under test.
    """
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(main)], check=True)
    subprocess.run(['git', '-C', str(main), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(main), 'config', 'user.name', 'Test'], check=True)
    (main / '.gitignore').write_text('.plan/\n')
    (main / 'file.txt').write_text('one\n')
    subprocess.run(['git', '-C', str(main), 'add', '.'], check=True, capture_output=True)
    subprocess.run(
        ['git', '-C', str(main), 'commit', '-q', '-m', 'init'], check=True, capture_output=True
    )


@pytest.fixture
def geometry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Stage a real main checkout plus a real linked worktree, cwd pinned to main.

    Every path is ``resolve()``d up front. ``Path.cwd()`` reports the physical
    directory, and the containment test compares against it, so a fixture holding the
    symlinked spelling of ``tmp_path`` would compare two spellings of one directory and
    reach a verdict about the platform rather than about the code.
    """
    main = tmp_path / 'main'
    main.mkdir()
    main = main.resolve()
    _init_main_repo(main)

    # Production geometry: the worktree lives UNDER the main checkout's gitignored
    # .plan/local/, so main is an ancestor of the removal target.
    main_local = main / '.plan' / 'local'
    worktree = main_local / 'worktrees' / _PLAN_ID
    worktree.parent.mkdir(parents=True)
    subprocess.run(
        ['git', '-C', str(main), 'worktree', 'add', '-q', '-b', _BRANCH, str(worktree)],
        check=True,
        capture_output=True,
    )
    worktree = worktree.resolve()

    # Worktree-resident plan state — the sole authoritative copy before the move-back,
    # and the file whose survival every refusal below asserts.
    wt_plan_dir = worktree / '.plan' / 'local' / 'plans' / _PLAN_ID
    wt_plan_dir.mkdir(parents=True)
    (wt_plan_dir / 'status.json').write_text('{"sentinel": "worktree"}\n')

    monkeypatch.setenv('PLAN_BASE_DIR', str(main_local))
    import file_ops

    monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
    monkeypatch.chdir(main)

    return {'main': main, 'main_local': main_local, 'worktree': worktree}


def _land_plan_dir_on_main(geometry: dict[str, Path]) -> None:
    """Put the plan dir on main, the state ``integrate_into_main`` leaves behind.

    The worktree-resident copy is deliberately left in place. The guards under test
    never read it, so its presence cannot change any verdict — it is kept purely as the
    observable for the "the refusal protected the plan state" assertion, which would
    otherwise have nothing to look at once the plan dir has landed.
    """
    main_plan_dir = geometry['main_local'] / 'plans' / _PLAN_ID
    main_plan_dir.mkdir(parents=True)
    (main_plan_dir / 'status.json').write_text('{"sentinel": "main"}\n')


def _worktree_status_json(geometry: dict[str, Path]) -> Path:
    return geometry['worktree'] / '.plan' / 'local' / 'plans' / _PLAN_ID / 'status.json'


def _remove(geometry: dict[str, Path], *, force: bool = False) -> dict:
    """Invoke ``worktree-remove`` with only the manage-status subprocess seam stubbed."""
    with patch_query_worktree_path(True, str(geometry['worktree'])):
        return dict(git_workflow.cmd_worktree_remove(_NS_FORCE if force else _NS_PLAIN))


def _assert_refused(result: dict, geometry: dict[str, Path], expected_error: str) -> None:
    """Assert a refusal by its typed error AND by what the refusal protected."""
    assert result['status'] == 'error', result
    assert result['error'] == expected_error, (
        f'Expected the {expected_error} refusal, got {result!r}.'
    )
    assert result['worktree_path'] == str(geometry['worktree'])
    assert geometry['worktree'].is_dir(), 'The refusal must leave the worktree on disk.'
    assert _worktree_status_json(geometry).is_file(), (
        'The refusal exists to protect the worktree-resident plan state; the return '
        'code alone does not show that the file survived.'
    )


class TestCwdGeometryMatrix:
    """cwd x plan-dir-residency, over real resolvers and a real worktree."""

    @pytest.mark.parametrize(
        ('cwd_key', 'landed', 'expected_error'),
        [
            ('main', False, 'plan_dir_not_moved_back'),
            ('main', True, None),
            ('worktree', False, 'plan_dir_not_moved_back'),
            ('worktree', True, 'cwd_inside_removal_target'),
        ],
        ids=[
            'main-cwd-not-landed-refuses-move-back',
            'main-cwd-landed-succeeds',
            'worktree-cwd-not-landed-refuses-move-back',
            'worktree-cwd-landed-refuses-containment',
        ],
    )
    def test_each_cell_reaches_its_own_outcome(
        self,
        geometry: dict[str, Path],
        monkeypatch: pytest.MonkeyPatch,
        cwd_key: str,
        landed: bool,
        expected_error: str | None,
    ) -> None:
        """The four cells differ pairwise along ONE axis and must not collapse.

        The two ``worktree`` rows are the cells a resolver-patched suite cannot reach:
        with the walk-up probe the not-landed row read the worktree's own copy as
        "moved back", and with no containment test the landed row destroyed the
        directory its caller was standing in.
        """
        if landed:
            _land_plan_dir_on_main(geometry)
        monkeypatch.chdir(geometry[cwd_key])

        result = _remove(geometry)

        if expected_error is None:
            assert result['status'] == 'success', result
            assert result['action'] == 'removed'
            assert not geometry['worktree'].exists(), (
                'The control must reach the real removal, not merely report success.'
            )
        else:
            _assert_refused(result, geometry, expected_error)

    def test_the_containment_refusal_names_the_real_process_cwd(
        self, geometry: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The reported ``cwd`` is where the process actually stands.

        A resolver-patched test could reproduce the error CODE without this field
        being right; only a real ``chdir`` can show the payload naming the directory
        the process is in, which is the value the operator acts on.
        """
        _land_plan_dir_on_main(geometry)
        monkeypatch.chdir(geometry['worktree'])

        result = _remove(geometry)

        assert result['error'] == 'cwd_inside_removal_target', result
        assert Path(result['cwd']) == geometry['worktree']
        assert 'change directory out of the worktree' in result['message']
        assert 'Pass --force' not in result['message'], (
            'The message must name the remedy, not offer --force as one.'
        )


class TestContainmentIsNotAStringPrefixTest:
    """Descendants are contained; a sibling sharing the target's prefix is not."""

    @pytest.mark.parametrize('subdir', ['nested', 'nested/deeper'], ids=['depth-1', 'depth-2'])
    def test_a_descendant_of_the_target_refuses(
        self, geometry: dict[str, Path], monkeypatch: pytest.MonkeyPatch, subdir: str
    ) -> None:
        _land_plan_dir_on_main(geometry)
        cwd = geometry['worktree'] / subdir
        cwd.mkdir(parents=True)
        monkeypatch.chdir(cwd)

        result = _remove(geometry)

        _assert_refused(result, geometry, 'cwd_inside_removal_target')
        assert Path(result['cwd']) == cwd

    def test_a_sibling_sharing_the_targets_path_prefix_is_not_contained(
        self, geometry: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Matched control for the containment predicate itself.

        ``{target}-sibling`` has the target's full path as a STRING prefix but is not
        beneath it, so a ``startswith``-shaped containment test would refuse here while
        the real one must not. The directory also sits inside the main checkout, so
        every real resolver still resolves — the cell differs from the refusing ones in
        cwd alone.
        """
        _land_plan_dir_on_main(geometry)
        sibling = Path(f'{geometry["worktree"]}-sibling')
        sibling.mkdir()
        monkeypatch.chdir(sibling)

        result = _remove(geometry)

        assert result['status'] == 'success', (
            f'A sibling path is not inside the removal target, got {result!r}.'
        )
        assert result['action'] == 'removed'
        assert not geometry['worktree'].exists()


class TestNeitherRefusalIsForceOverridable:
    """``--force`` keeps its dirty-tree meaning and buys no way past either guard."""

    @pytest.mark.parametrize(
        ('cwd_key', 'landed', 'expected_error'),
        [
            ('worktree', False, 'plan_dir_not_moved_back'),
            ('worktree', True, 'cwd_inside_removal_target'),
        ],
        ids=['move-back', 'containment'],
    )
    def test_force_does_not_override(
        self,
        geometry: dict[str, Path],
        monkeypatch: pytest.MonkeyPatch,
        cwd_key: str,
        landed: bool,
        expected_error: str,
    ) -> None:
        if landed:
            _land_plan_dir_on_main(geometry)
        monkeypatch.chdir(geometry[cwd_key])

        result = _remove(geometry, force=True)

        _assert_refused(result, geometry, expected_error)

    def test_force_still_removes_from_a_cwd_outside_the_target(
        self, geometry: dict[str, Path]
    ) -> None:
        """Matched control: ``--force`` is not being neutered, only not being a bypass.

        Without this, the two refusals above would be equally consistent with
        ``--force`` having stopped working altogether.
        """
        _land_plan_dir_on_main(geometry)

        result = _remove(geometry, force=True)

        assert result['status'] == 'success', result
        assert result['action'] == 'removed'
        assert not geometry['worktree'].exists()
