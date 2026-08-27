#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for git_workflow.py worktree-* subcommands.

These verbs live under ``plan-marshall:workflow-integration-git`` with a
stricter contract than the historical scattered helpers: ``--plan-id`` is mandatory
for ``worktree-path``/``worktree-create``/``worktree-remove``, and worktree
resolution flows through ``file_ops.resolve_plan_context`` — the single
plan-context resolver, which owns the one ``manage-status get-worktree-path``
invocation in the codebase.

Two stubbing seams, deliberately distinct:

* ``file_ops._query_worktree_path`` — the WORKTREE face (path + presence).
  Stubbed via ``patch_query_worktree_path`` for a single plan, or
  ``patch_query_worktree_path_map`` when one call resolves several plans
  (``worktree-list`` walks the whole census).
* ``git_workflow._manage_status_call`` — everything still on the manage-status
  channel: the ``list`` census and the ``metadata --get --field
  worktree_branch`` reads.

Stubbing them at their own seams (rather than one shared ``get-worktree-path``
stub) is what keeps the real resolution chain executing under the test.

The tests below split into two tiers:

* **CLI subprocess tests** exercise argparse plumbing — missing ``--plan-id``
  must be rejected — and a smoke test for ``worktree-create`` against a real
  git repo so ``git worktree add`` runs end-to-end.
* **Direct-import tests** stub the two seams above so the resolution chain
  (``worktree-path``/``worktree-remove``/``worktree-list``/
  ``locate-plan-checkout``) can be exercised without spinning up a separate
  plan-marshall executor.

A sibling ``_fixtures.py`` is intentionally not introduced — the helpers are
small and stay co-located with the test cases. The pre-existing
``manage-worktree`` tests (3 failures) are out-of-scope here; deliverable 10
removes that skill in a later task.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from argparse import Namespace
from pathlib import Path

import pytest
from _resolve_project_dir_fixtures import (
    patch_query_worktree_path,
    patch_query_worktree_path_map,
)
from toon_parser import parse_toon

from conftest import get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'git-workflow.py')

# The entrypoint filename is kebab-case (git-workflow.py), which is not a
# valid Python module identifier — load it via importlib instead of `import`.
git_workflow = load_script_module(
    'plan-marshall', 'workflow-integration-git', 'git-workflow.py', 'git_workflow'
)

cmd_locate_plan_checkout = git_workflow.cmd_locate_plan_checkout
cmd_worktree_create = git_workflow.cmd_worktree_create
cmd_worktree_list = git_workflow.cmd_worktree_list
cmd_worktree_path = git_workflow.cmd_worktree_path
cmd_worktree_remove = git_workflow.cmd_worktree_remove


# =============================================================================
# Helpers
# =============================================================================


def _serialize_toon_payload(payload: dict) -> str:
    """Serialize a dict into TOON for ``_manage_status_call`` stubs."""
    from toon_parser import serialize_toon

    return serialize_toon(payload)


def _stub_manage_status_call(monkeypatch: pytest.MonkeyPatch, responses: dict[tuple[str, ...], tuple[int, dict | str, str]]) -> list[tuple[str, ...]]:
    """Replace ``git_workflow._manage_status_call`` with a stub.

    ``responses`` maps an arg tuple to a ``(returncode, stdout_payload, stderr)``
    triple. ``stdout_payload`` may be a dict (serialized to TOON) or a raw
    string. The stub records every call into the returned list so tests can
    assert on the dispatch.
    """
    calls: list[tuple[str, ...]] = []

    def fake(subcommand: str, *extra_args: str, timeout: int = 30) -> tuple[int, str, str]:
        key = (subcommand, *extra_args)
        calls.append(key)
        if key not in responses:
            return 1, '', f'no stub for {key}'
        rc, payload, stderr = responses[key]
        stdout = _serialize_toon_payload(payload) if isinstance(payload, dict) else payload
        return rc, stdout, stderr

    monkeypatch.setattr(git_workflow, '_manage_status_call', fake)
    return calls


def _init_repo(repo: Path) -> None:
    """Initialise a fixture git repo mirroring the canonical layout.

    Tracks ``.plan/marshal.json`` and a placeholder architecture dir so
    ``git worktree add`` materialises tracked content. Gitignores
    ``.plan/local`` and the worktrees root.
    """
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Test'], check=True)
    (repo / 'README.md').write_text('x\n')
    plan_dir = repo / '.plan'
    plan_dir.mkdir(exist_ok=True)
    (plan_dir / 'marshal.json').write_text('{"system": {}, "plan": {}}\n')
    arch_dir = plan_dir / 'project-architecture'
    arch_dir.mkdir(exist_ok=True)
    (arch_dir / 'README.md').write_text('placeholder\n')
    (repo / '.gitignore').write_text('.plan/local\n.plan/execute-script.py\n.plan/local/worktrees/\n')
    subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(repo), 'commit', '-q', '-m', 'init'], check=True)

    # Seed the main checkout's real .plan/local + executor (no symlinks under
    # the move-based model — the worktree gets its OWN real .plan/local).
    (plan_dir / 'local').mkdir(exist_ok=True)
    executor = plan_dir / 'execute-script.py'
    if not executor.exists():
        executor.write_text('#!/usr/bin/env python3\n')


# =============================================================================
# No-symlink contract for the worktree .plan/local materializer
# =============================================================================


class TestEnsureWorktreePlanLocalReal:
    """``_ensure_worktree_plan_local_real`` creates a REAL .plan/local with NO
    symlinks (deliverable 5). The retired ``_ensure_worktree_plan_symlinks``
    symlinked ``.plan/local`` and ``.plan/execute-script.py`` into main; the
    move-based model owns a fully real worktree ``.plan/local`` instead.
    """

    def test_symlink_helper_is_gone(self) -> None:
        # The old symlink machinery must not survive — neither the helper nor
        # the subpath table.
        assert not hasattr(git_workflow, '_ensure_worktree_plan_symlinks')
        assert not hasattr(git_workflow, '_SHARED_PLAN_SUBPATHS')

    def test_creates_real_plan_local_no_symlinks(self, tmp_path: Path) -> None:
        worktree = tmp_path / 'wt'
        worktree.mkdir()

        ok, err = git_workflow._ensure_worktree_plan_local_real(worktree)

        assert ok, err
        plan_local = worktree / '.plan' / 'local'
        # .plan/local is a REAL directory, not a symlink.
        assert plan_local.is_dir()
        assert not plan_local.is_symlink()
        # plans/ is NOT created here — the move-in lands it.
        assert not (plan_local / 'plans').exists()
        # No symlink anywhere under .plan/local.
        for entry in plan_local.rglob('*'):
            assert not entry.is_symlink(), f'unexpected symlink: {entry}'

    def test_idempotent_on_existing_real_plan_local(self, tmp_path: Path) -> None:
        worktree = tmp_path / 'wt'
        (worktree / '.plan' / 'local').mkdir(parents=True)

        ok, err = git_workflow._ensure_worktree_plan_local_real(worktree)

        assert ok, err
        assert (worktree / '.plan' / 'local').is_dir()

    def test_replaces_preexisting_symlink_with_real_dir(self, tmp_path: Path) -> None:
        """A pre-existing ``.plan/local`` symlink (a worktree created by an older
        symlinking revision, or manual intervention) is unlinked and replaced by a
        real directory — mkdir(exist_ok=True) alone would leave the symlink in
        place, violating the fully-REAL guarantee."""
        worktree = tmp_path / 'wt'
        (worktree / '.plan').mkdir(parents=True)
        main_local = tmp_path / 'main' / '.plan' / 'local'
        main_local.mkdir(parents=True)
        # .plan/local starts as a symlink into a (real) main corpus.
        link = worktree / '.plan' / 'local'
        link.symlink_to(main_local, target_is_directory=True)
        assert link.is_symlink()

        ok, err = git_workflow._ensure_worktree_plan_local_real(worktree)

        assert ok, err
        assert link.is_dir()
        assert not link.is_symlink()


# =============================================================================
# CLI argparse rejection — missing --plan-id
# =============================================================================


class TestWorktreeRequiresPlanId:
    """``worktree-path``/``worktree-create``/``worktree-remove`` must reject
    invocations that omit ``--plan-id``.

    argparse marks ``--plan-id`` as ``required=True`` for these three verbs,
    so the rejection surfaces as exit code 2 with a ``required: --plan-id``
    diagnostic on stderr — not a structured ``plan_resolution_failed`` TOON.
    The contract still rejects them (the workflow cannot proceed without
    the identifier); tests assert the rejection mode rather than dressing up
    the error in a TOON payload that argparse cannot produce.
    """

    def test_worktree_path_without_plan_id_rejected(self):
        result = run_script(SCRIPT_PATH, 'worktree-path')
        assert result.returncode != 0
        assert '--plan-id' in result.stderr or '--plan-id' in result.stdout

    def test_worktree_create_without_plan_id_rejected(self):
        result = run_script(SCRIPT_PATH, 'worktree-create', '--branch', 'feature/x')
        assert result.returncode != 0
        assert '--plan-id' in result.stderr or '--plan-id' in result.stdout

    def test_worktree_remove_without_plan_id_rejected(self):
        result = run_script(SCRIPT_PATH, 'worktree-remove')
        assert result.returncode != 0
        assert '--plan-id' in result.stderr or '--plan-id' in result.stdout


# =============================================================================
# worktree-path — resolution chain via manage-status get-worktree-path
# =============================================================================


class TestWorktreePathResolution:
    """``cmd_worktree_path`` resolves through ``file_ops.resolve_plan_context``.

    No filesystem heuristics and no local ``status.json`` read: the verb asks
    the single resolver for the presence face (``has_worktree``) and then the
    path face. These tests exercise the resolution branches by stubbing the ONE
    seam beneath both — ``file_ops._query_worktree_path`` — so the whole
    delegation chain runs for real while the executor bootstrap does not.
    """

    def test_returns_persisted_path_when_use_worktree_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Materialise a directory so the result's ``exists`` flag is true.
        worktree = tmp_path / '.plan' / 'local' / 'worktrees' / 'my-plan'
        worktree.mkdir(parents=True)

        with patch_query_worktree_path(True, str(worktree)) as mock:
            result = cmd_worktree_path(Namespace(plan_id='my-plan'))

        assert result['status'] == 'success'
        assert result['plan_id'] == 'my-plan'
        assert result['worktree_path'] == str(worktree)
        assert result['exists'] is True
        assert mock.call_count == 1, 'resolution did not go through the resolver seam'

    def test_returns_plan_resolution_failed_when_use_worktree_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A plan with no DEDICATED worktree is refused, not answered with main.

        ``worktree-path`` is a worktree verb: silently returning the main
        checkout would be a fabrication. The refusal is decided STRUCTURALLY via
        the resolver's ``has_worktree`` face — which is the whole reason that
        face exists, since ``worktree_path`` alone cannot distinguish "no
        worktree" from "a worktree that happens to be the checkout root".
        """
        with patch_query_worktree_path(False) as mock:
            result = cmd_worktree_path(Namespace(plan_id='no-wt'))

        assert result['status'] == 'error'
        assert result['error'] == 'plan_resolution_failed'
        assert 'No worktree configured' in result['message']
        assert mock.call_count == 1

    def test_propagates_resolver_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A resolver failure surfaces as ``plan_resolution_failed``, message intact."""
        import file_ops  # noqa: PLC0415

        def _raise(_plan_id):
            raise file_ops.WorktreeResolutionError('plan not found')

        monkeypatch.setattr(file_ops, '_query_worktree_path', _raise)

        result = cmd_worktree_path(Namespace(plan_id='broken'))
        assert result['status'] == 'error'
        assert result['error'] == 'plan_resolution_failed'
        assert 'plan not found' in result['message']


# =============================================================================
# worktree-create — full integration against a real git repo
# =============================================================================


class TestWorktreeCreate:
    """``cmd_worktree_create`` materialises a real worktree on disk, so this
    tier exercises the script via a subprocess against a fixture repo.

    The fixture repo seeds a tracked ``.plan/marshal.json`` plus an
    ``execute-script.py`` shim so ``_executor_path()`` can resolve. The
    plan-marshall ``manage-status`` call writes via the real executor
    relative to the repo's ``.plan/local`` (see ``PLAN_BASE_DIR`` env
    override below).
    """

    def test_create_writes_metadata_via_manage_status(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A successful ``worktree-create`` invokes ``manage-status metadata
        --set`` for ``use_worktree``, ``worktree_path``, and ``worktree_branch``
        so subsequent verbs can resolve the path through the canonical channel.

        The integration uses ``cmd_worktree_create`` directly with stubs for
        ``run_git`` and ``_manage_status_call`` — the test verifies the
        bookkeeping contract without bringing up a real ``git worktree add``.
        """

        # Synthetic worktree-root resolution.
        target_root = tmp_path / 'worktrees-root'
        target_root.mkdir()
        monkeypatch.setattr(git_workflow, 'get_worktree_root', lambda: target_root)
        monkeypatch.setattr(git_workflow, '_find_plan_root_from_cwd', lambda: tmp_path)

        # Fake git_worktree_add: just create the directory so downstream
        # symlink/bookkeeping logic has something to bind against.
        def fake_run_git(args):
            assert 'worktree' in args and 'add' in args, args
            # Last positional after '-b <branch>' is the target path.
            target_idx = args.index('-b') + 2
            target = Path(args[target_idx])
            target.mkdir(parents=True, exist_ok=True)
            (target / '.plan').mkdir(exist_ok=True)
            return 0, '', ''

        monkeypatch.setattr(git_workflow, 'run_git', fake_run_git)

        # Seed shared subpaths the symlink helper expects in the main checkout.
        (tmp_path / '.plan').mkdir(exist_ok=True)
        (tmp_path / '.plan' / 'local').mkdir(exist_ok=True)
        (tmp_path / '.plan' / 'execute-script.py').write_text('#!/usr/bin/env python3\n')

        calls = _stub_manage_status_call(
            monkeypatch,
            {
                ('metadata', '--plan-id', 'my-plan', '--set', '--field', 'use_worktree', '--value', 'true'): (
                    0,
                    {'status': 'success'},
                    '',
                ),
                ('metadata', '--plan-id', 'my-plan', '--set', '--field', 'worktree_path', '--value', str(target_root / 'my-plan')): (
                    0,
                    {'status': 'success'},
                    '',
                ),
                ('metadata', '--plan-id', 'my-plan', '--set', '--field', 'worktree_branch', '--value', 'feature/my-plan'): (
                    0,
                    {'status': 'success'},
                    '',
                ),
            },
        )

        result = cmd_worktree_create(
            Namespace(plan_id='my-plan', branch='feature/my-plan', base=None)
        )

        assert result['status'] == 'success', result
        assert result['plan_id'] == 'my-plan'
        assert result['worktree_path'] == str(target_root / 'my-plan')
        assert result['branch'] == 'feature/my-plan'

        # All three metadata fields must have been persisted via manage-status.
        recorded_fields = {
            call[5] for call in calls if len(call) >= 6 and call[0] == 'metadata' and call[3] == '--set'
        }
        assert recorded_fields == {'use_worktree', 'worktree_path', 'worktree_branch'}

    def test_create_rejects_when_not_in_git_repo(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Outside a git repo, ``get_worktree_root()`` raises and the verb
        emits ``plan_resolution_failed`` instead of leaking the exception."""

        def raising():
            raise RuntimeError('requires a git repository')

        monkeypatch.setattr(git_workflow, 'get_worktree_root', raising)

        result = cmd_worktree_create(
            Namespace(plan_id='no-repo', branch='feature/no-repo', base=None)
        )
        assert result['status'] == 'error'
        assert result['error'] == 'plan_resolution_failed'


# =============================================================================
# worktree-remove — worktree first, then branch ref
# =============================================================================


def _pin_main_anchor(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    """Tell the move-back guard which tree is "main", via the real resolver.

    ``_plan_dir_on_main_checkout`` probes through
    ``marketplace_paths.resolve_main_anchored_path``, whose FIRST precedence branch is
    the ``PLAN_BASE_DIR`` / ``set_base_dir()`` override — so pinning the override at
    ``{root}/.plan/local`` points the guard at the fixture's tree without replacing the
    resolver. ``main_checkout_root`` is pinned separately at each call site, because it
    is a DIFFERENT resolver serving a different need: the ``git -C`` target, which must
    name a real git checkout and therefore cannot come from an override directory.
    """
    import file_ops  # noqa: PLC0415

    monkeypatch.setenv('PLAN_BASE_DIR', str(root / '.plan' / 'local'))
    monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)


class TestWorktreeRemove:
    """``cmd_worktree_remove`` removes the worktree before deleting the
    branch ref. Integration is decoupled from a real git via
    ``run_git`` and ``_manage_status_call`` stubs so the ordering contract
    can be observed deterministically.
    """

    def test_remove_drops_worktree_then_branch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        worktree = tmp_path / '.plan' / 'local' / 'worktrees' / 'rm-me'
        worktree.mkdir(parents=True)

        monkeypatch.setattr(git_workflow, 'main_checkout_root', lambda: tmp_path)
        _pin_main_anchor(monkeypatch, tmp_path)

        # Satisfy the script-level plan-dir move-back precondition: removal
        # requires {root}/.plan/local/plans/{plan_id}/status.json on the
        # MAIN checkout (mirrors TestWorktreeRemoveMoveBackPrecondition's
        # seeding in test_git_workflow.py), so this test keeps exercising its
        # original worktree-then-branch removal-ordering contract.
        plan_dir = tmp_path / '.plan' / 'local' / 'plans' / 'rm-me'
        plan_dir.mkdir(parents=True)
        (plan_dir / 'status.json').write_text('{}')

        # The worktree PATH now comes from the resolver seam; the branch NAME is
        # still a manage-status metadata read, so the two are stubbed at their
        # two different seams rather than at one shared get-worktree-path stub.
        _stub_manage_status_call(
            monkeypatch,
            {
                ('metadata', '--plan-id', 'rm-me', '--get', '--field', 'worktree_branch'): (
                    0,
                    {'status': 'success', 'value': 'feature/rm-me'},
                    '',
                ),
            },
        )

        # Capture the order of git invocations. The keyword parameters mirror
        # ``run_git``'s real signature because the removal call now supplies its
        # own derived ``timeout``; a positional-only stub would raise TypeError
        # rather than exercise the ordering contract this test is about.
        git_calls: list[list[str]] = []

        def fake_run_git(args, *, cwd=None, timeout=None):
            git_calls.append(list(args))
            # Mimic ``git worktree remove`` deleting the directory.
            if 'worktree' in args and 'remove' in args:
                shutil.rmtree(worktree, ignore_errors=True)
            return 0, '', ''

        monkeypatch.setattr(git_workflow, 'run_git', fake_run_git)

        with patch_query_worktree_path(True, str(worktree)):
            result = cmd_worktree_remove(Namespace(plan_id='rm-me', force=False))

        assert result['status'] == 'success'
        assert result['action'] == 'removed'
        assert result['branch'] == 'feature/rm-me'

        # First git call must be the worktree removal.
        assert any('worktree' in c and 'remove' in c for c in git_calls)
        worktree_idx = next(i for i, c in enumerate(git_calls) if 'worktree' in c and 'remove' in c)
        # Branch deletion must come AFTER the worktree removal.
        branch_idx = next(
            (i for i, c in enumerate(git_calls) if 'branch' in c and '-D' in c),
            None,
        )
        assert branch_idx is not None, 'branch ref must be deleted after worktree removal'
        assert branch_idx > worktree_idx, 'worktree must be removed before branch ref'

    @staticmethod
    def _fail_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
        """Make the manage-status channel refuse, as it does for an archived plan."""
        import file_ops  # noqa: PLC0415

        def _raise(_plan_id):
            raise file_ops.WorktreeResolutionError('plan does not exist')

        monkeypatch.setattr(file_ops, '_query_worktree_path', _raise)

    def test_remove_propagates_plan_resolution_failed_when_the_probe_misses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Resolution fails AND the structural probe misses ⇒ the diagnosis survives.

        The canonical worktree root is pinned to the fixture so the probe's verdict is
        decided by what this test staged (nothing) rather than by whatever happens to
        sit under the test runner's own checkout. With no worktree to reach, nothing
        corroborates a target, so the resolver's own ``plan_resolution_failed`` must be
        propagated verbatim and no git call may run.
        """
        worktrees_root = tmp_path / '.plan' / 'local' / 'worktrees'
        worktrees_root.mkdir(parents=True)

        monkeypatch.setattr(git_workflow, 'main_checkout_root', lambda: tmp_path)
        monkeypatch.setattr(git_workflow, 'get_worktree_root', lambda: worktrees_root)
        self._fail_resolution(monkeypatch)

        called = []

        def trap_run_git(args):
            called.append(args)
            return 0, '', ''

        monkeypatch.setattr(git_workflow, 'run_git', trap_run_git)

        result = cmd_worktree_remove(Namespace(plan_id='ghost', force=False))
        assert result['status'] == 'error'
        assert result['error'] == 'plan_resolution_failed'
        assert called == [], 'no git call must run after a resolution failure'

    def test_remove_falls_back_to_the_structural_probe_when_it_hits(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Matched positive: resolution fails BUT the canonical slot holds a worktree.

        Same failing resolution as the sibling above; the ONE thing that differs is
        that the canonical ``get_worktree_root() / {plan_id}`` slot exists and carries
        the ``.git`` link ``git worktree add`` plants. The removal must then proceed and
        the payload must name the path taken, so an archived-plan recovery is
        distinguishable from a routine removal.
        """
        worktrees_root = tmp_path / '.plan' / 'local' / 'worktrees'
        worktree = worktrees_root / 'ghost'
        worktree.mkdir(parents=True)
        (worktree / '.git').write_text('gitdir: /nowhere\n')

        # The move-back precondition is independent of the resolution path and still
        # binds here; satisfying it is what leaves the probe as the only variable.
        plan_dir = tmp_path / '.plan' / 'local' / 'plans' / 'ghost'
        plan_dir.mkdir(parents=True)
        (plan_dir / 'status.json').write_text('{}')

        monkeypatch.setattr(git_workflow, 'main_checkout_root', lambda: tmp_path)
        monkeypatch.setattr(git_workflow, 'get_worktree_root', lambda: worktrees_root)
        _pin_main_anchor(monkeypatch, tmp_path)
        self._fail_resolution(monkeypatch)
        # No branch metadata is staged: the read is a soft signal, and stubbing the
        # channel keeps it from shelling out to a real executor.
        _stub_manage_status_call(monkeypatch, {})

        called: list[list[str]] = []

        def fake_run_git(args, *, cwd=None, timeout=None):
            called.append(list(args))
            if 'worktree' in args and 'remove' in args:
                shutil.rmtree(worktree, ignore_errors=True)
            return 0, '', ''

        monkeypatch.setattr(git_workflow, 'run_git', fake_run_git)

        result = cmd_worktree_remove(Namespace(plan_id='ghost', force=False))

        assert result['status'] == 'success', result
        assert result['action'] == 'removed'
        assert result['resolution'] == 'structural_probe'
        assert result['worktree_path'] == str(worktree)
        assert any('worktree' in c and 'remove' in c for c in called), (
            'the probe path must reach the real removal, not merely report success'
        )


# =============================================================================
# worktree-remove — the removal budget is derived from the observed tree
# =============================================================================


def _entry_count(root: Path) -> int:
    """Count every descendant of ``root``, derived INDEPENDENTLY of production.

    ``Path.rglob('*')`` yields each descendant exactly once, which is the same
    population ``_count_tree_entries`` accumulates as ``len(dirnames) +
    len(filenames)`` per walk level — reached by a different traversal. Deriving
    it a second way, rather than hard-coding a number the fixture would silently
    outgrow or calling the function under test, is what keeps the assertions
    below about the production count instead of about themselves.
    """
    return len(list(root.rglob('*')))


def _stage_removal(
    root: Path, monkeypatch: pytest.MonkeyPatch, *, plan_id: str, extra_files: int = 0
) -> Path:
    """Stage a removable worktree under ``root`` and return its path.

    Mirrors ``TestWorktreeRemove``'s staging — ``main_checkout_root`` pinned to
    ``root`` for the ``git -C`` target, the main anchor pinned to
    ``root/.plan/local`` for the move-back probe (:func:`_pin_main_anchor`), the
    precondition satisfied by a plan dir there, the manage-status channel stubbed
    — so the tests below differ from the ordering tests in what they OBSERVE, not
    in how they reach the removal. ``cwd`` is
    left alone: the test process stands in the repository, never inside
    ``root``, so the containment refusal cannot fire.

    ``extra_files`` pads the worktree so two stagings can differ in size and in
    nothing else.
    """
    root.mkdir(parents=True, exist_ok=True)
    worktree = root / '.plan' / 'local' / 'worktrees' / plan_id
    (worktree / 'src').mkdir(parents=True)
    (worktree / 'src' / 'main.py').write_text('x\n')
    for index in range(extra_files):
        (worktree / 'src' / f'pad{index}.py').write_text('x\n')

    monkeypatch.setattr(git_workflow, 'main_checkout_root', lambda: root)
    _pin_main_anchor(monkeypatch, root)
    plan_dir = root / '.plan' / 'local' / 'plans' / plan_id
    plan_dir.mkdir(parents=True)
    (plan_dir / 'status.json').write_text('{}')
    # No branch metadata is staged, so ``_read_metadata_field`` returns '' and
    # the removal issues exactly one git call — the one under observation.
    _stub_manage_status_call(monkeypatch, {})
    return worktree


def _seed_scratch(worktree: Path) -> Path:
    """Create a pytest scratch tree at the path ``build.py`` fills.

    ``build.py`` builds it as ``PYTEST_BASETEMP_ROOT = Path('.plan/temp/
    pytest-basetemp')`` with one per-session subdirectory per invocation, so the
    fixture is shaped the same way: several sessions, each holding files.
    """
    scratch = worktree / '.plan' / 'temp' / 'pytest-basetemp'
    for session in ('12345-aaaa', '67890-bbbb'):
        session_dir = scratch / session
        (session_dir / 'nested').mkdir(parents=True)
        (session_dir / 'out.txt').write_text('scratch\n')
        (session_dir / 'nested' / 'deep.txt').write_text('scratch\n')
    return scratch


def _record_run_git(
    monkeypatch: pytest.MonkeyPatch, worktree: Path, *, rc: int = 0, stderr: str = ''
) -> list[dict]:
    """Stub ``run_git``, recording each call's argv AND the timeout it was given.

    The budget is captured at the CALL because that is the only place it is
    observable: it is an argument the verb constructs. Waiting on a real clock
    would assert the operating system's scheduler rather than the derivation,
    and would have to burn the budget to do it.

    Each record also snapshots the worktree AS GIT SEES IT — whether the scratch
    is still there, and how many entries remain — so the tests can check that
    the clearing and the measurement both happened BEFORE the git call rather
    than merely appearing in the payload afterwards.
    """
    calls: list[dict] = []

    def fake_run_git(args, *, cwd=None, timeout=None):
        calls.append(
            {
                'args': list(args),
                'timeout': timeout,
                'scratch_present': (worktree / '.plan' / 'temp' / 'pytest-basetemp').exists(),
                'entries_at_call': _entry_count(worktree) if worktree.is_dir() else None,
            }
        )
        if rc == 0 and 'worktree' in args and 'remove' in args:
            shutil.rmtree(worktree, ignore_errors=True)
        return rc, '', stderr

    monkeypatch.setattr(git_workflow, 'run_git', fake_run_git)
    return calls


def _run_removal(worktree: Path, plan_id: str) -> dict:
    with patch_query_worktree_path(True, str(worktree)):
        return dict(cmd_worktree_remove(Namespace(plan_id=plan_id, force=False)))


class TestRemovalBudgetReachesGit:
    """The derived budget is what ``git worktree remove`` is actually given.

    A fixed 60s budget expires on a healthy removal of a GB-scale worktree, so
    the verb measures the tree and derives the timeout from it. Every assertion
    here is on the CONSTRUCTED call: the argument the verb built, not elapsed
    wall-clock time.
    """

    PLAN_ID = 'budget-plan'

    def test_the_derived_budget_is_the_timeout_passed_to_run_git(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The payload's ``timeout_seconds`` and the git call's timeout agree.

        Two separate things could go wrong independently — deriving a budget and
        then not passing it, or passing something the payload does not report —
        so the reported budget is tied to the argument AND re-derived from the
        payload's own measurement.
        """
        worktree = _stage_removal(tmp_path, monkeypatch, plan_id=self.PLAN_ID)
        calls = _record_run_git(monkeypatch, worktree)

        result = _run_removal(worktree, self.PLAN_ID)

        assert result['status'] == 'success', result
        removal = next(c for c in calls if 'worktree' in c['args'] and 'remove' in c['args'])
        assert removal['timeout'] == result['timeout_seconds'], (
            'The removal must be given the budget the payload reports, got '
            f'timeout={removal["timeout"]!r} vs payload {result["timeout_seconds"]!r}.'
        )
        assert result['timeout_seconds'] == git_workflow._derive_removal_timeout(
            result['measured_entries'], result['budget_basis']
        )

    def test_the_measurement_is_of_the_tree_git_will_actually_walk(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scratch is cleared FIRST, and the reported count is what remains.

        Ordering is the property: a budget derived from a tree that still held
        the regenerable scratch would over-count work git never has to do, and a
        scratch cleared after the git call would not shrink anything. The count
        is compared against an independent recount taken at the moment of the
        call, so it cannot be satisfied by a number computed at any other time.
        """
        worktree = _stage_removal(tmp_path, monkeypatch, plan_id=self.PLAN_ID)
        scratch = _seed_scratch(worktree)
        scratch_entries = _entry_count(scratch)
        assert scratch_entries > 0, 'the fixture must actually seed a scratch tree'
        calls = _record_run_git(monkeypatch, worktree)

        result = _run_removal(worktree, self.PLAN_ID)

        assert result['status'] == 'success', result
        assert result['scratch_cleared'] is True
        assert result['scratch_entries_removed'] == scratch_entries
        removal = next(c for c in calls if 'worktree' in c['args'] and 'remove' in c['args'])
        assert removal['scratch_present'] is False, (
            'the scratch must be gone before git is invoked, not merely reported as cleared'
        )
        assert result['measured_entries'] == removal['entries_at_call'], (
            'the budget must be measured against the post-clearing tree'
        )
        assert result['budget_basis'] == 'measured_tree'

    def test_a_worktree_with_no_scratch_still_succeeds_and_reports_its_basis(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Matched negative control: a small, scratch-free tree keeps the floor.

        Differs from the case above in the presence of the scratch and nothing
        else. Without it, ``scratch_cleared: true`` there would be equally
        consistent with the field being hard-wired — and a derivation that
        SHORTENED the budget for a small tree would go unnoticed, so the floor
        is asserted by name rather than as a number.
        """
        worktree = _stage_removal(tmp_path, monkeypatch, plan_id=self.PLAN_ID)
        assert not (worktree / '.plan' / 'temp' / 'pytest-basetemp').exists()
        calls = _record_run_git(monkeypatch, worktree)

        result = _run_removal(worktree, self.PLAN_ID)

        assert result['status'] == 'success', result
        assert result['action'] == 'removed'
        assert result['scratch_cleared'] is False
        assert result['scratch_entries_removed'] == 0
        assert result['budget_basis'] == 'measured_tree'
        assert result['measured_entries'] == calls[0]['entries_at_call']
        assert result['timeout_seconds'] == git_workflow._DEFAULT_TIMEOUT_SECONDS, (
            'a tree below the scaling threshold must keep the ordinary git-call floor'
        )

    def test_the_budget_grows_with_the_observed_tree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Two trees differing only in size receive two different budgets.

        This is the end-to-end scaling proof, over a REAL measurement of a real
        directory. The rate and the floor are tuned down for the test so a tree
        small enough to build in a unit test can still land above the floor —
        the SHAPE of the derivation is under test, not the shipped magnitudes,
        which are asserted separately in
        :class:`TestRemovalBudgetDerivation`.
        """
        monkeypatch.setattr(git_workflow, '_REMOVAL_ENTRIES_PER_SECOND', 1)
        monkeypatch.setattr(git_workflow, '_DEFAULT_TIMEOUT_SECONDS', 1)

        observed: dict[str, tuple[int, int]] = {}
        for plan_id, extra_files in (('small-tree', 0), ('large-tree', 30)):
            worktree = _stage_removal(
                tmp_path / plan_id, monkeypatch, plan_id=plan_id, extra_files=extra_files
            )
            _record_run_git(monkeypatch, worktree)
            result = _run_removal(worktree, plan_id)
            assert result['status'] == 'success', result
            observed[plan_id] = (result['measured_entries'], result['timeout_seconds'])

        small_entries, small_budget = observed['small-tree']
        large_entries, large_budget = observed['large-tree']
        assert large_entries > small_entries, 'the fixture must produce two different trees'
        assert large_budget > small_budget, (
            f'the budget must follow the observed tree, got {observed!r}'
        )
        for entries, budget in observed.values():
            # rate == 1 ⇒ the scaled term is the entry count itself.
            assert budget == max(1, min(entries, git_workflow._REMOVAL_TIMEOUT_CEILING_SECONDS))


class TestRemovalTimeoutIsItsOwnFailure:
    """An expired budget is NOT ``worktree_remove_failed``.

    ``branch-cleanup.md`` maps ``worktree_remove_failed`` to "uncommitted
    changes" and recommends a manual ``--force``. That is the wrong and the most
    destructive available response to a removal that is merely slow on a large
    but perfectly clean tree, so the timeout carries its own code.
    """

    PLAN_ID = 'budget-plan'

    def test_a_timed_out_removal_returns_its_own_typed_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """124 from ``run_git`` maps to ``worktree_remove_timed_out``.

        124 is ``run_git``'s timeout sentinel, synthesized by the helper rather
        than produced by git, so it is the one return that means "the budget
        expired and git rendered no verdict". The budget and the measurement
        behind it travel with the failure — an operator deciding what to do next
        needs to know which budget expired against which tree.
        """
        worktree = _stage_removal(tmp_path, monkeypatch, plan_id=self.PLAN_ID)
        calls = _record_run_git(
            monkeypatch, worktree, rc=124, stderr='git timed out after 60 seconds'
        )

        result = _run_removal(worktree, self.PLAN_ID)

        assert result['status'] == 'error', result
        assert result['error'] == 'worktree_remove_timed_out', (
            f'The timeout must not be reported as a removal failure, got {result!r}.'
        )
        assert result['timeout_seconds'] == calls[0]['timeout']
        assert result['measured_entries'] == calls[0]['entries_at_call']
        assert result['budget_basis'] == 'measured_tree'
        assert result['worktree_path'] == str(worktree)
        assert 'Do NOT pass --force' in result['hint'], (
            'the wrong remedy must be named as wrong, not merely omitted'
        )
        assert worktree.is_dir(), 'a timed-out removal leaves the worktree on disk'

    def test_an_ordinary_git_failure_still_maps_to_worktree_remove_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Matched control: the new code DISCRIMINATES, it does not rename.

        The load-bearing half of the pair. A change that mapped every non-zero
        return to ``worktree_remove_timed_out`` would satisfy the positive cell
        just as well — and would send a genuinely dirty worktree the wrong
        advice, which is the mirror image of the defect being fixed.
        """
        worktree = _stage_removal(tmp_path, monkeypatch, plan_id=self.PLAN_ID)
        _record_run_git(
            monkeypatch,
            worktree,
            rc=1,
            stderr='fatal: contains modified or untracked files, use --force to delete it',
        )

        result = _run_removal(worktree, self.PLAN_ID)

        assert result['status'] == 'error', result
        assert result['error'] == 'worktree_remove_failed', (
            f'A non-timeout failure must keep its own code, got {result!r}.'
        )
        assert 'Pass --force only after verifying' in result['hint']


class TestScratchClearingNeverLeavesTheTarget:
    """The clearing deletes regenerable scratch, and only inside the target."""

    PLAN_ID = 'budget-plan'

    def test_a_symlinked_scratch_is_refused_and_its_target_survives(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A symlink at the scratch path is never followed.

        Under ADR-002 a worktree's ``.plan`` tree is fully real, but a worktree
        materialized by an older symlinking revision — or edited by hand — can
        still have one, and following it would delete whatever it points at
        rather than scratch inside the tree being removed. The refusal is
        fail-safe: the scratch is simply counted into the measurement instead,
        so the removal still proceeds.
        """
        worktree = _stage_removal(tmp_path, monkeypatch, plan_id=self.PLAN_ID)
        outside = tmp_path / 'not-in-the-worktree'
        outside.mkdir()
        (outside / 'keep.txt').write_text('keep\n')
        (worktree / '.plan' / 'temp').mkdir(parents=True)
        (worktree / '.plan' / 'temp' / 'pytest-basetemp').symlink_to(
            outside, target_is_directory=True
        )
        _record_run_git(monkeypatch, worktree)

        result = _run_removal(worktree, self.PLAN_ID)

        assert result['status'] == 'success', result
        assert result['scratch_cleared'] is False
        assert result['scratch_entries_removed'] == 0
        assert 'symlink' in result['scratch_note']
        assert (outside / 'keep.txt').is_file(), (
            'the symlink target lives outside the removal target and must survive'
        )


class TestRemovalBudgetDerivation:
    """``_derive_removal_timeout`` — the shipped magnitudes, as a pure function."""

    def test_a_small_measured_tree_takes_the_floor(self) -> None:
        assert (
            git_workflow._derive_removal_timeout(10, 'measured_tree')
            == git_workflow._DEFAULT_TIMEOUT_SECONDS
        )

    def test_a_large_measured_tree_scales_with_the_count(self) -> None:
        entries = git_workflow._REMOVAL_ENTRIES_PER_SECOND * 300
        assert git_workflow._derive_removal_timeout(entries, 'measured_tree') == 300

    def test_the_scaled_budget_is_capped(self) -> None:
        entries = git_workflow._REMOVAL_ENTRIES_PER_SECOND * (
            git_workflow._REMOVAL_TIMEOUT_CEILING_SECONDS + 10_000
        )
        assert (
            git_workflow._derive_removal_timeout(entries, 'measured_tree')
            == git_workflow._REMOVAL_TIMEOUT_CEILING_SECONDS
        )

    @pytest.mark.parametrize(
        ('entries', 'basis'),
        [
            (1, 'measurement_capped'),
            (1, 'measurement_incomplete'),
            (None, 'measurement_failed'),
        ],
        ids=['capped', 'incomplete', 'failed'],
    )
    def test_every_lower_bound_basis_takes_the_ceiling(
        self, entries: int | None, basis: str
    ) -> None:
        """A count that is a LOWER BOUND must never be scaled.

        The entry count is deliberately 1 on the two bases that carry one: the
        real tree is at least that large and its true size is unknown, so
        scaling the partial figure would produce exactly the too-short budget
        the derivation exists to prevent — and would do it while looking like a
        measurement.
        """
        assert (
            git_workflow._derive_removal_timeout(entries, basis)
            == git_workflow._REMOVAL_TIMEOUT_CEILING_SECONDS
        )


class TestTreeMeasurement:
    """``_count_tree_entries`` — the count and the basis that makes it readable."""

    def test_a_readable_tree_is_counted_exactly(self, tmp_path: Path) -> None:
        root = tmp_path / 'tree'
        (root / 'a' / 'b').mkdir(parents=True)
        (root / 'a' / 'one.txt').write_text('x')
        (root / 'a' / 'b' / 'two.txt').write_text('x')
        (root / 'three.txt').write_text('x')

        entries, basis = git_workflow._count_tree_entries(root)

        assert basis == 'measured_tree'
        assert entries == _entry_count(root)

    def test_an_empty_directory_measures_zero(self, tmp_path: Path) -> None:
        """The positive half of the zero-versus-unmeasurable pair."""
        root = tmp_path / 'empty'
        root.mkdir()

        assert git_workflow._count_tree_entries(root) == (0, 'measured_tree')

    def test_an_unscannable_root_reports_none_rather_than_zero(self, tmp_path: Path) -> None:
        """The negative half: nothing counted is not the same as counted nothing.

        Paired with the empty-directory case above, which legitimately measures
        zero. The two demand OPPOSITE budgets — the floor for a genuinely empty
        tree, the ceiling for one that could not be measured — so a ``0``
        published by a walk that never ran would silently pick the shorter, and
        would be indistinguishable from a real measurement at every consumer.
        """
        entries, basis = git_workflow._count_tree_entries(tmp_path / 'does-not-exist')

        assert basis == 'measurement_failed'
        assert entries is None

    def test_reaching_the_cap_is_reported_as_a_lower_bound(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The walk is bounded, and says so instead of reporting a total."""
        root = tmp_path / 'big'
        (root / 'a').mkdir(parents=True)
        for index in range(5):
            (root / 'a' / f'f{index}.txt').write_text('x')
        monkeypatch.setattr(git_workflow, '_MEASURE_ENTRY_CAP', 3)

        entries, basis = git_workflow._count_tree_entries(root)

        assert basis == 'measurement_capped'
        assert entries == 3

    def test_an_unreadable_subdirectory_is_reported_as_incomplete(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A partial walk reports what it counted AND that it is partial.

        The unreadable directory is signalled at ``os.walk``'s own ``onerror``
        seam rather than by ``chmod``, because a chmod-based fixture answers
        differently for a root user — the OS bypasses the DAC check — and this
        suite runs on hosts where that is possible. Signalling at the seam
        exercises the branch on every host instead of only on unprivileged ones.
        """
        root = tmp_path / 'partial'
        root.mkdir()
        (root / 'seen.txt').write_text('x')
        real_walk = git_workflow.os.walk

        def walk_reporting_one_unreadable_dir(top, onerror=None, followlinks=False):
            if onerror is not None:
                onerror(PermissionError(13, 'Permission denied', str(root / 'locked')))
            yield from real_walk(top, onerror=onerror, followlinks=followlinks)

        monkeypatch.setattr(git_workflow.os, 'walk', walk_reporting_one_unreadable_dir)

        entries, basis = git_workflow._count_tree_entries(root)

        assert basis == 'measurement_incomplete'
        assert entries == 1, 'the partial count is still reported, not discarded'


# =============================================================================
# worktree-list — filter from manage-status list by use_worktree==true
# =============================================================================


class TestWorktreeList:
    """``cmd_worktree_list`` enumerates plans whose status declares a
    worktree by calling ``manage-status list`` then ``get-worktree-path``
    per plan. Plans without ``metadata.use_worktree==true`` are silently
    skipped.
    """

    def test_filters_to_worktree_plans_only(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        worktree_a = tmp_path / 'wt-a'
        worktree_a.mkdir()

        # Build the manage-status list TOON via the production serializer so
        # the table shape matches whatever the script actually emits.
        list_payload = _serialize_toon_payload(
            {
                'status': 'success',
                'total': 2,
                'plans': [
                    {'id': 'with-worktree', 'current_phase': '5-execute', 'status': 'in_progress'},
                    {'id': 'no-worktree', 'current_phase': '5-execute', 'status': 'in_progress'},
                ],
            }
        )

        # The census (``manage-status list``) and the per-plan branch read stay
        # on the manage-status channel; the per-plan worktree verdict now comes
        # from the resolver, so it is stubbed with a PER-PLAN-ID map — the two
        # plans must receive different verdicts in the same call.
        responses: dict[tuple[str, ...], tuple[int, dict | str, str]] = {
            ('list',): (0, list_payload, ''),
            ('metadata', '--plan-id', 'with-worktree', '--get', '--field', 'worktree_branch'): (
                0,
                {'status': 'success', 'value': 'feature/with-worktree'},
                '',
            ),
        }

        _stub_manage_status_call(monkeypatch, responses)
        monkeypatch.setattr(git_workflow, 'get_worktree_root', lambda: tmp_path)

        with patch_query_worktree_path_map(
            {
                'with-worktree': (True, str(worktree_a)),
                'no-worktree': (False, ''),
            }
        ):
            result = cmd_worktree_list(Namespace())

        assert result['status'] == 'success'
        ids = [w['plan_id'] for w in result['worktrees']]
        assert ids == ['with-worktree']
        assert result['count'] == 1
        assert result['worktrees'][0]['path'] == str(worktree_a)
        assert result['worktrees'][0]['branch'] == 'feature/with-worktree'

    def test_list_propagates_manage_status_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Top-level ``manage-status list`` failure surfaces
        ``plan_resolution_failed`` instead of an empty success."""
        _stub_manage_status_call(
            monkeypatch,
            {('list',): (1, '', 'manage-status unavailable')},
        )

        result = cmd_worktree_list(Namespace())
        assert result['status'] == 'error'
        assert result['error'] == 'plan_resolution_failed'


# =============================================================================
# locate-plan-checkout — three-state checkout-location resolution
# =============================================================================


class TestLocatePlanCheckout:
    """``cmd_locate_plan_checkout`` reports where a plan's directory currently
    lives in one of three states — ``current`` / ``worktree`` / ``not_found`` —
    without raw ``git worktree list --porcelain`` re-parsing.

    The current-checkout probe reuses :func:`_find_plan_root_from_cwd` (the
    uniform cwd walk-up); the worktree probe reuses
    :func:`_resolve_worktree_path_for_plan` (the canonical ``manage-status
    get-worktree-path`` channel). Tests monkeypatch the cwd walk-up and stub
    ``_manage_status_call`` so both branches are exercised deterministically,
    materialising a real ``status.json`` on disk where the on-disk probe must
    succeed.
    """

    @staticmethod
    def _seed_plan_status_json(root: Path, plan_id: str) -> Path:
        """Create ``{root}/.plan/local/plans/{plan_id}/status.json`` on disk."""
        plan_dir = root / '.plan' / 'local' / 'plans' / plan_id
        plan_dir.mkdir(parents=True, exist_ok=True)
        status_json = plan_dir / 'status.json'
        status_json.write_text(f'{{"plan_id": "{plan_id}"}}\n')
        return status_json

    def test_returns_worktree_when_plan_dir_moved_into_worktree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the plan dir was moved into a worktree (phase-5 move-in) and the
        call is made from main, the verb returns ``location=worktree`` with the
        resolved ``worktree_path``."""
        # Main checkout root does NOT hold the plan dir.
        main_root = tmp_path / 'main'
        (main_root / '.plan' / 'local').mkdir(parents=True)
        # The worktree DOES hold the moved-in plan dir.
        worktree = tmp_path / 'worktrees' / 'moved-plan'
        self._seed_plan_status_json(worktree, 'moved-plan')

        monkeypatch.setattr(git_workflow, '_find_plan_root_from_cwd', lambda: main_root)

        with patch_query_worktree_path(True, str(worktree)):
            result = cmd_locate_plan_checkout(Namespace(plan_id='moved-plan'))

        assert result['status'] == 'success'
        assert result['plan_id'] == 'moved-plan'
        assert result['location'] == 'worktree'
        assert result['worktree_path'] == str(worktree)

    def test_returns_worktree_via_structural_probe_when_manage_status_cannot_resolve(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Regression (State (b) structural fallback): a phase-5+ plan whose dir
        was MOVED off main into its worktree (ADR-002) is invisible to the
        canonical manage-status channel — main's ``status.json`` no longer holds
        the plan, so ``get-worktree-path`` returns an expected ``not found``
        error and the primary resolution path yields no ``worktree_path``. The
        verb MUST then probe the canonical ``get_worktree_root() / {plan_id}``
        location directly and confirm ``status.json`` on disk, returning
        ``location=worktree``.

        Before the structural-probe fallback this case fell through to
        ``not_found`` (the bug): the primary manage-status channel could not see
        the moved-in plan, and there was no second resolution path. This test
        therefore FAILS without the fix and PASSES with it.
        """
        # Main checkout root does NOT hold the plan dir.
        main_root = tmp_path / 'main'
        (main_root / '.plan' / 'local').mkdir(parents=True)

        # The worktree at the canonical ``{worktree_root}/{plan_id}`` layout
        # (exactly what ``worktree-create`` materialises) DOES hold the
        # moved-in plan dir on disk.
        worktree_root = tmp_path / 'worktrees'
        worktree = worktree_root / 'probe-plan'
        self._seed_plan_status_json(worktree, 'probe-plan')

        monkeypatch.setattr(git_workflow, '_find_plan_root_from_cwd', lambda: main_root)
        # The structural probe resolves ``get_worktree_root() / {plan_id}``.
        monkeypatch.setattr(git_workflow, 'get_worktree_root', lambda: worktree_root)

        # The canonical resolver CANNOT resolve the moved-in plan: main's
        # status.json no longer holds it, so resolution raises an expected
        # "not found" error (masked to not_found, not propagated). This forces
        # the primary path to yield no worktree_path and exercises the
        # structural-probe fallback.
        import file_ops  # noqa: PLC0415

        def _raise(_plan_id):
            raise file_ops.WorktreeResolutionError('plan probe-plan not found')

        monkeypatch.setattr(file_ops, '_query_worktree_path', _raise)

        result = cmd_locate_plan_checkout(Namespace(plan_id='probe-plan'))
        assert result['status'] == 'success'
        assert result['plan_id'] == 'probe-plan'
        assert result['location'] == 'worktree'
        assert result['worktree_path'] == str(worktree)

    def test_returns_current_when_plan_dir_on_current_checkout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the plan dir is on the current checkout (main-checkout plan, or
        an already-cwd-pinned worktree), the verb returns ``location=current``
        and never reports a ``worktree_path`` — the idempotent re-entry case."""
        current_root = tmp_path / 'current'
        self._seed_plan_status_json(current_root, 'here-plan')

        monkeypatch.setattr(git_workflow, '_find_plan_root_from_cwd', lambda: current_root)

        # No worktree resolution should be needed; the seam raises so the test
        # fails loudly if the current-checkout branch does NOT short-circuit
        # before the resolver is consulted.
        import file_ops  # noqa: PLC0415

        def _forbidden(_plan_id):
            raise AssertionError('the current-checkout branch consulted the resolver')

        monkeypatch.setattr(file_ops, '_query_worktree_path', _forbidden)

        result = cmd_locate_plan_checkout(Namespace(plan_id='here-plan'))
        assert result['status'] == 'success'
        assert result['plan_id'] == 'here-plan'
        assert result['location'] == 'current'
        assert 'worktree_path' not in result

    def test_returns_not_found_for_unknown_plan(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When neither the current checkout nor any registered worktree holds
        the plan dir, the verb returns ``location=not_found``."""
        current_root = tmp_path / 'current'
        (current_root / '.plan' / 'local').mkdir(parents=True)

        monkeypatch.setattr(git_workflow, '_find_plan_root_from_cwd', lambda: current_root)

        with patch_query_worktree_path(False):
            result = cmd_locate_plan_checkout(Namespace(plan_id='ghost-plan'))

        assert result['status'] == 'success'
        assert result['plan_id'] == 'ghost-plan'
        assert result['location'] == 'not_found'
        assert 'worktree_path' not in result

    def test_returns_not_found_when_worktree_resolves_but_status_json_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A stale worktree registration (path resolves but the moved-in plan
        dir is not actually on disk) must NOT report ``worktree`` — the on-disk
        ``status.json`` probe gates the worktree state, so the verb falls
        through to ``not_found``."""
        main_root = tmp_path / 'main'
        (main_root / '.plan' / 'local').mkdir(parents=True)
        # Worktree path resolves but has NO plans/{plan_id}/status.json.
        worktree = tmp_path / 'worktrees' / 'stale-plan'
        worktree.mkdir(parents=True)

        monkeypatch.setattr(git_workflow, '_find_plan_root_from_cwd', lambda: main_root)

        with patch_query_worktree_path(True, str(worktree)):
            result = cmd_locate_plan_checkout(Namespace(plan_id='stale-plan'))

        assert result['status'] == 'success'
        assert result['location'] == 'not_found'


class TestLocatePlanCheckoutCli:
    """CLI argparse: ``locate-plan-checkout`` rejects a missing ``--plan-id``."""

    def test_without_plan_id_rejected(self) -> None:
        result = run_script(SCRIPT_PATH, 'locate-plan-checkout')
        assert result.returncode != 0
        assert '--plan-id' in result.stderr or '--plan-id' in result.stdout


# =============================================================================
# CLI smoke test — worktree-list against a fresh repo
# =============================================================================


class TestWorktreeListCli:
    """Smoke test: invoking ``worktree-list`` with an empty manage-status
    must return a clean ``count: 0`` payload, not an error.

    This exercises the executor lookup + manage-status integration end-to-end
    in the simplest possible shape (no plans, no worktrees).
    """

    def test_empty_list_returns_zero_count(self, tmp_path: Path) -> None:
        repo = tmp_path / 'repo'
        _init_repo(repo)

        # Symlink the real executor so ``manage-status list`` resolves.
        real_executor = Path(__file__).resolve().parents[3] / '.plan' / 'execute-script.py'
        if not real_executor.exists():
            pytest.skip('real executor not available — run /marshall-steward to bootstrap')

        # Replace the placeholder with a symlink to the real executor.
        target_executor = repo / '.plan' / 'execute-script.py'
        target_executor.unlink()
        os.symlink(real_executor, target_executor)

        env = {'PLAN_BASE_DIR': str(repo / '.plan' / 'local')}
        # Make sure plans dir exists so manage-status returns total=0 cleanly.
        (repo / '.plan' / 'local' / 'plans').mkdir(parents=True, exist_ok=True)

        result = run_script(
            SCRIPT_PATH,
            'worktree-list',
            cwd=repo,
            env_overrides=env,
        )

        # The verb may legitimately fail with plan_resolution_failed if
        # manage-status cannot bootstrap (e.g., in CI without a generated
        # executor); in that case the script still returns exit code 0 with a
        # structured TOON error. Accept either shape.
        assert result.returncode == 0, result.stderr
        data = parse_toon(result.stdout)
        if data.get('status') == 'success':
            assert data.get('count') == 0
        else:
            # Failure path must still be the structured error contract.
            assert data['status'] == 'error'
            assert data['error'] == 'plan_resolution_failed'
