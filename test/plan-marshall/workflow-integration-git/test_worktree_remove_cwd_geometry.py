#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Real-resolver cwd-geometry regression suite for ``git-workflow worktree-remove``.

Both of ``cmd_worktree_remove``'s preconditions are decided by **where the calling
process stands**:

* ``plan_dir_not_moved_back`` — probed through
  ``marketplace_paths.resolve_main_anchored_path``, the one sanctioned main-anchored
  resolver, which names main from any linked worktree. Its predecessor probed through
  the cwd-relative walk-up, so a caller standing inside the worktree satisfied the
  guard with the very plan-state copy the removal was about to destroy.
* ``cwd_inside_removal_target`` — a containment test between ``Path.cwd()`` and the
  resolved removal target.

Neither failure mode is observable by a test that patches a path resolver: a patched
resolver returns whatever the test told it to and cannot report where the process is
standing, so the pre-fix and post-fix implementations answer identically under it.
This suite therefore varies **cwd and nothing else**, over a real ``git init`` main
checkout with a real ``git worktree add`` linked worktree, using ``monkeypatch.chdir``.
``_find_plan_root_from_cwd``, ``main_checkout_root`` and ``resolve_main_anchored_path``
are NEVER patched here — that is the deliverable, not an implementation detail.

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

Archived-plan reachability (``TestArchivedPlanReachability``)
-------------------------------------------------------------
The same real-worktree fixture also carries the structural-probe pair, because that
fallback is decided by the same two things this suite already stages for real: a
worktree that genuinely exists at the canonical ``get_worktree_root() / {plan_id}``
slot (with the ``.git`` link ``git worktree add`` plants, which the probe requires),
and what the MAIN checkout does or does not hold for the plan. Only the manage-status
seam is moved: it is made to FAIL, which is what an archived plan produces for real —
``status.json`` is no longer under ``plans/`` where manage-status looks.

The pair differs along ONE axis, whether main carries the ARCHIVED record:

* archived record present on main → the probe reaches the worktree AND the widened
  move-back predicate is satisfied, so the removal proceeds and reports
  ``resolution: structural_probe``;
* no record on main at all (the plan dir still resident in its worktree) → the probe
  still reaches the worktree, and the removal is still refused with
  ``plan_dir_not_moved_back``.

The negative is the load-bearing half: restoring REACHABILITY must not become a
BYPASS. A probe that reached the worktree and skipped the guard would pass the
positive cell just as well.

Override-anchored resolution (``TestOverrideBaseDirIsHonoured``)
----------------------------------------------------------------
⛔ Everything above runs with ``PLAN_BASE_DIR`` pinned at ``main/.plan/local`` — which
is *also* where a ``git rev-parse --git-common-dir`` walk from this fixture lands. The
override-honouring resolver and the pure-git one therefore COINCIDE BY CONSTRUCTION in
that geometry, so no cell above can tell them apart: a guard probing either one passes
every row identically. The blindness is structural, not an oversight of the matrix — no
amount of extra cells along the cwd axis reaches it.

``TestOverrideBaseDirIsHonoured`` breaks the coincidence by re-pointing
``PLAN_BASE_DIR`` at a store OUTSIDE the main checkout, somewhere the git-common-dir
walk cannot reach. The two resolvers then name two different trees, and the matched
pair drives the plan state into one tree at a time:

* landed under the OVERRIDE base only ⇒ the removal must proceed — this is the cell a
  ``main_checkout_root()``-derived probe fails, refusing ``plan_dir_not_moved_back``
  against a plan whose state really did move back;
* landed under the GIT-derived tree only ⇒ the removal must still be refused — the
  mirror, which a probe that consulted only the override would wrongly pass.

Both directions are asserted because a probe that reads the wrong tree fails one of
them whichever tree it reads. The producer this pins the guard to is
``integrate_into_main``, which resolves its move-back destination as
``resolve_main_anchored_path(f'plans/{plan_id}')`` — the same call, so guard and
producer cannot derive different paths.
"""

from __future__ import annotations

import subprocess
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from _resolve_project_dir_fixtures import patch_query_worktree_path

from conftest import load_script_module, parse_ns

#: The script under test, hoisted as three module-level constants rather than only as
#: the tuple below. The loader-contract guard resolves each registration statically, and
#: a ``load_script_module(*_GIT_WF)`` unpacking leaves the script position unreadable to
#: it: the call still publishes ``git_workflow`` in ``sys.modules`` at run time, but as a
#: registration the collision guard cannot see. Naming the positionals keeps it visible.
#: ⛔ Do not collapse the load below back to an unpacking. The ``parse_ns`` calls may
#: keep using ``_GIT_WF`` — they pass ``register=False`` and so publish nothing.
_BUNDLE = 'plan-marshall'
_SKILL = 'workflow-integration-git'
_SCRIPT = 'git-workflow.py'
_GIT_WF = (_BUNDLE, _SKILL, _SCRIPT)

git_workflow = load_script_module(_BUNDLE, _SKILL, _SCRIPT)

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


#: A FIXED archive date, deliberately not "today". ``manage-status archive`` writes the
#: destination as ``{YYYY-MM-DD}-{plan_id}``, so pinning an arbitrary past date is what
#: shows the guard matches the date SHAPE rather than a date it recomputed itself.
_ARCHIVE_DATE = '2026-01-15'


def _archive_plan_record_on_main(geometry: dict[str, Path]) -> Path:
    """Put the ARCHIVED record on main, the state ``manage-status archive`` leaves.

    Mirrors ``_cmd_lifecycle.cmd_archive``'s own destination construction —
    ``{base}/archived-plans/{YYYY-MM-DD}-{plan_id}`` — rather than the bare
    ``{plan_id}`` shape some prose spells, because the code is what the guard has to
    agree with. No live ``plans/{plan_id}`` directory is created: an archived plan has
    none, which is exactly why manage-status can no longer resolve its worktree.
    """
    archived = geometry['main_local'] / 'archived-plans' / f'{_ARCHIVE_DATE}-{_PLAN_ID}'
    archived.mkdir(parents=True)
    (archived / 'status.json').write_text('{"sentinel": "archived"}\n')
    return archived


def _land_plan_dir_under(base: Path) -> Path:
    """Land the plan dir under an arbitrary ``.plan/local`` stand-in.

    Spelled ``{base}/plans/{plan_id}/status.json`` because that is what
    ``resolve_main_anchored_path('plans/{plan_id}')`` yields on its override branch:
    the override directory IS the ``.plan/local`` stand-in, so the subpath sits
    directly under it with no ``.plan/local`` segment of its own.
    """
    plan_dir = base / 'plans' / _PLAN_ID
    plan_dir.mkdir(parents=True)
    (plan_dir / 'status.json').write_text('{"sentinel": "override-base"}\n')
    return plan_dir


def _worktree_status_json(geometry: dict[str, Path]) -> Path:
    return geometry['worktree'] / '.plan' / 'local' / 'plans' / _PLAN_ID / 'status.json'


def _remove(geometry: dict[str, Path], *, force: bool = False) -> dict:
    """Invoke ``worktree-remove`` with only the manage-status subprocess seam stubbed."""
    with patch_query_worktree_path(True, str(geometry['worktree'])):
        return dict(git_workflow.cmd_worktree_remove(_NS_FORCE if force else _NS_PLAIN))


@contextmanager
def _manage_status_cannot_resolve():
    """Make the manage-status channel REFUSE, as it does for an archived plan.

    An archived plan's ``status.json`` no longer sits under ``.plan/local/plans/``,
    so ``manage-status get-worktree-path`` cannot resolve it — the resolver raises and
    ``_resolve_worktree_path_for_plan`` returns ``plan_resolution_failed``. This stands
    in for that state at the one subprocess seam, leaving every filesystem resolver the
    structural probe and the move-back guard use running for real.
    """
    import file_ops

    def _raise(_plan_id: str):
        raise file_ops.WorktreeResolutionError('status.json not found')

    with patch('file_ops._query_worktree_path', new=_raise):
        yield


def _remove_unresolvable(geometry: dict[str, Path], *, force: bool = False) -> dict:
    """Invoke ``worktree-remove`` with the manage-status channel refusing."""
    del geometry  # The probe derives the target itself; nothing is handed to it.
    with _manage_status_cannot_resolve():
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


class TestArchivedPlanReachability:
    """The structural-probe fallback restores REACHABILITY, never a bypass.

    Every cell runs with the manage-status channel refusing — the archived-plan state —
    so the probe is the only thing that can produce a target. The matched pair differs
    in ONE thing: whether main carries the archived record the widened move-back
    predicate accepts.
    """

    def test_an_archived_plan_is_removable_through_the_structural_probe(
        self, geometry: dict[str, Path]
    ) -> None:
        """Positive: archived record on main, worktree present ⇒ removal proceeds.

        Before the fallback existed the resolver's refusal ended the verb here, so the
        worktree of every archived plan was unreachable — the exact tree an operator
        needs to clean up once finalize has archived the record.
        """
        archived = _archive_plan_record_on_main(geometry)
        assert not (geometry['main_local'] / 'plans' / _PLAN_ID).exists(), (
            'The archived cell must carry NO live plan dir on main — otherwise the '
            'live half of the predicate would decide the outcome and the archived '
            'half would go unexercised.'
        )

        result = _remove_unresolvable(geometry)

        assert result['status'] == 'success', result
        assert result['action'] == 'removed'
        assert result['resolution'] == 'structural_probe', (
            'The payload must name the path taken so an operator can tell an '
            f'archived-plan recovery from a routine removal; got {result!r}.'
        )
        assert result['worktree_path'] == str(geometry['worktree'])
        assert not geometry['worktree'].exists(), (
            'The positive cell must reach the real removal, not merely report success.'
        )
        assert (archived / 'status.json').is_file(), (
            'The archived record lives on main and must be untouched by the removal.'
        )

    def test_a_plan_still_resident_in_its_worktree_is_still_refused(
        self, geometry: dict[str, Path]
    ) -> None:
        """Negative control: the probe hits, and the guard still refuses.

        The load-bearing half of the pair. The probe reaches the SAME worktree as the
        positive cell — the only difference is that main holds no record of the plan,
        live or archived, so its sole authoritative copy is still inside the tree the
        removal would destroy. A fallback that reached the worktree and skipped the
        guard would pass the positive cell just as well as the real one does.
        """
        assert not (geometry['main_local'] / 'plans' / _PLAN_ID).exists()
        assert not (geometry['main_local'] / 'archived-plans').exists()

        result = _remove_unresolvable(geometry)

        _assert_refused(result, geometry, 'plan_dir_not_moved_back')

    def test_the_probe_path_refusal_is_not_force_overridable(
        self, geometry: dict[str, Path]
    ) -> None:
        """``--force`` buys no way past the guard on the probe path either.

        Force-independence was established for the metadata resolution path; the probe
        path reaches the same guard by a different route, and a route is exactly the
        kind of thing a guard gets accidentally bypassed along.
        """
        result = _remove_unresolvable(geometry, force=True)

        _assert_refused(result, geometry, 'plan_dir_not_moved_back')

    def test_a_missed_probe_still_propagates_the_resolvers_own_diagnosis(
        self, geometry: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Matched control for the probe itself: no worktree ⇒ nothing is invented.

        With the canonical slot emptied the probe misses, so the resolver's own
        ``plan_resolution_failed`` must survive verbatim rather than being replaced by
        a worse-informed refusal — and no git call may run against a target the verb
        could not resolve.
        """
        _archive_plan_record_on_main(geometry)
        subprocess.run(
            [
                'git',
                '-C',
                str(geometry['main']),
                'worktree',
                'remove',
                '--force',
                str(geometry['worktree']),
            ],
            check=True,
            capture_output=True,
        )
        assert not geometry['worktree'].exists()

        called: list[list[str]] = []

        def trap_run_git(args):
            called.append(list(args))
            return 0, '', ''

        monkeypatch.setattr(git_workflow, 'run_git', trap_run_git)

        result = _remove_unresolvable(geometry)

        assert result['status'] == 'error', result
        assert result['error'] == 'plan_resolution_failed'
        assert called == [], 'no git call may run after a resolution failure the probe missed'


@pytest.fixture
def external_base(
    geometry: dict[str, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Re-point ``PLAN_BASE_DIR`` at a store the git-common-dir walk cannot reach.

    Ordered after ``geometry`` because that fixture sets ``PLAN_BASE_DIR`` to
    ``main/.plan/local``, and this one must overwrite it. The directory is a SIBLING of
    the main checkout under ``tmp_path``, so ``git rev-parse --git-common-dir`` — which
    resolves ``main`` — can never name it. The assertion below states that separation
    rather than assuming it: if the two trees ever coincided, every cell in the class
    would pass under a probe reading either resolver, which is precisely the blindness
    this fixture exists to remove.
    """
    base = (tmp_path / 'external-plan-store').resolve()
    assert base != geometry['main_local'] and not base.is_relative_to(geometry['main']), (
        'The override base must lie outside the main checkout for the two resolvers '
        'to name different trees.'
    )
    base.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return base


class TestOverrideBaseDirIsHonoured:
    """The guard reads the OVERRIDE tree, which is the tree the move-back writes.

    Every other class in this file runs where the override tree and the git-derived
    tree are the same directory, so none of them can observe which resolver the guard
    uses. These cells pull the two apart and assert the guard follows the override in
    BOTH directions — the direction a pure-git probe gets wrong, and the mirror a
    pure-override probe would get wrong.
    """

    def test_a_plan_landed_under_the_override_base_satisfies_the_guard(
        self, geometry: dict[str, Path], external_base: Path
    ) -> None:
        """Positive: state landed where the move-back writes it ⇒ removal proceeds.

        This is the cell a ``main_checkout_root()``-derived probe fails. It would look
        under ``main/.plan/local/plans/`` — a tree the move-back never wrote to when an
        override is active — find nothing, and refuse ``plan_dir_not_moved_back``
        against a plan whose state genuinely did land. Because that refusal is
        deliberately not ``--force``-overridable, the failure has no escape hatch.
        """
        landed = _land_plan_dir_under(external_base)
        assert not (geometry['main_local'] / 'plans' / _PLAN_ID).exists(), (
            'The git-derived tree must be EMPTY here, or the cell would pass under a '
            'probe that never consulted the override.'
        )

        result = _remove(geometry)

        assert result['status'] == 'success', result
        assert result['action'] == 'removed'
        assert not geometry['worktree'].exists(), (
            'The positive cell must reach the real removal, not merely report success.'
        )
        assert (landed / 'status.json').is_file(), (
            'The landed plan state lives outside the worktree and must survive it.'
        )

    def test_a_plan_landed_only_under_the_git_derived_tree_is_still_refused(
        self, geometry: dict[str, Path], external_base: Path
    ) -> None:
        """Mirror control: the guard must not fall back to the git-derived tree.

        The same two trees as the cell above, with the plan state in the OTHER one.
        A probe that consulted only ``main_checkout_root()`` — or one that accepted a
        hit from either tree — passes here, and passing here means authorising the
        destruction of a worktree whose plan state the move-back never moved. Without
        this mirror the positive cell alone is equally consistent with a guard that had
        simply been weakened.
        """
        _land_plan_dir_on_main(geometry)
        assert not (external_base / 'plans' / _PLAN_ID).exists()

        result = _remove(geometry)

        _assert_refused(result, geometry, 'plan_dir_not_moved_back')

    def test_the_archived_scan_follows_the_override_base_too(
        self, geometry: dict[str, Path], external_base: Path
    ) -> None:
        """The archived half is resolved by the same rule as the live half.

        ``manage-status archive`` writes through ``get_archive_dir()`` —
        ``base_path(DIR_ARCHIVED)``, which honours the same override — so a guard whose
        live probe followed the override while its archive scan did not would refuse
        every archived plan under an override. The two halves are separate lookups in
        the predicate and need separate evidence.
        """
        archived = external_base / 'archived-plans' / f'{_ARCHIVE_DATE}-{_PLAN_ID}'
        archived.mkdir(parents=True)
        (archived / 'status.json').write_text('{"sentinel": "archived-override"}\n')
        assert not (external_base / 'plans' / _PLAN_ID).exists(), (
            'No live plan dir under the override base, or the live half of the '
            'predicate would decide the outcome and the archived half go unexercised.'
        )

        result = _remove(geometry)

        assert result['status'] == 'success', result
        assert result['action'] == 'removed'
        assert not geometry['worktree'].exists()
        assert (archived / 'status.json').is_file()
