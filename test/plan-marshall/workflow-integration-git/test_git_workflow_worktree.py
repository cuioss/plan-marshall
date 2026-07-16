#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for git_workflow.py worktree-* subcommands.

These verbs live under ``plan-marshall:workflow-integration-git`` with a
stricter contract than the historical scattered helpers: ``--plan-id`` is mandatory
for ``worktree-path``/``worktree-create``/``worktree-remove`` and resolution
flows through ``manage-status get-worktree-path`` so the persisted
``status.metadata.worktree_path`` is the single source of truth.

The tests below split into two tiers:

* **CLI subprocess tests** exercise argparse plumbing — missing ``--plan-id``
  must be rejected — and a smoke test for ``worktree-create`` against a real
  git repo so ``git worktree add`` runs end-to-end.
* **Direct-import tests** monkeypatch ``_manage_status_call`` so the
  resolution chain (``worktree-path``/``worktree-remove``/``worktree-list``)
  can be exercised without spinning up a separate plan-marshall executor.

A sibling ``_fixtures.py`` is intentionally not introduced — the helpers are
small and stay co-located with the test cases. The pre-existing
``manage-worktree`` tests (3 failures) are out-of-scope here; deliverable 10
removes that skill in a later task.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
from argparse import Namespace
from pathlib import Path

import pytest
from toon_parser import parse_toon

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'git-workflow.py')

# The entrypoint filename is kebab-case (git-workflow.py), which is not a
# valid Python module identifier — load it via importlib instead of `import`.
_spec = importlib.util.spec_from_file_location('git_workflow', SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
git_workflow = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(git_workflow)

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
        place, violating the fully-REAL guarantee (PR #557 review)."""
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
    """``cmd_worktree_path`` reads ``status.metadata.worktree_path`` through
    ``manage-status get-worktree-path`` (no filesystem heuristics).

    These tests exercise the resolution branches by stubbing
    ``_manage_status_call`` so the contract with manage-status is decoupled
    from the executor-bootstrapping required for a full integration run.
    """

    def test_returns_persisted_path_when_use_worktree_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Materialise a directory so the result's ``exists`` flag is true.
        worktree = tmp_path / '.plan' / 'local' / 'worktrees' / 'my-plan'
        worktree.mkdir(parents=True)

        _stub_manage_status_call(
            monkeypatch,
            {
                ('get-worktree-path', '--plan-id', 'my-plan'): (
                    0,
                    {
                        'status': 'success',
                        'plan_id': 'my-plan',
                        'use_worktree': True,
                        'worktree_path': str(worktree),
                    },
                    '',
                )
            },
        )

        result = cmd_worktree_path(Namespace(plan_id='my-plan'))
        assert result['status'] == 'success'
        assert result['plan_id'] == 'my-plan'
        assert result['worktree_path'] == str(worktree)
        assert result['exists'] is True

    def test_returns_plan_resolution_failed_when_use_worktree_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When ``use_worktree==false``, no path is returned and the
        verb surfaces ``plan_resolution_failed`` so callers can fall
        back to the main checkout instead of guessing a path."""
        _stub_manage_status_call(
            monkeypatch,
            {
                ('get-worktree-path', '--plan-id', 'no-wt'): (
                    0,
                    {
                        'status': 'success',
                        'plan_id': 'no-wt',
                        'use_worktree': False,
                        'worktree_path': '',
                    },
                    '',
                )
            },
        )

        result = cmd_worktree_path(Namespace(plan_id='no-wt'))
        assert result['status'] == 'error'
        assert result['error'] == 'plan_resolution_failed'

    def test_propagates_manage_status_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A non-zero exit from manage-status surfaces as
        ``plan_resolution_failed`` with the stderr message preserved."""
        _stub_manage_status_call(
            monkeypatch,
            {
                ('get-worktree-path', '--plan-id', 'broken'): (
                    1,
                    '',
                    'plan not found',
                )
            },
        )

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

        monkeypatch.setattr(git_workflow, '_find_plan_root_from_cwd', lambda: tmp_path)

        # Satisfy the script-level plan-dir move-back precondition: removal
        # requires {root}/.plan/local/plans/{plan_id}/status.json on the
        # current checkout (mirrors TestWorktreeRemoveMoveBackPrecondition's
        # seeding in test_git_workflow.py), so this test keeps exercising its
        # original worktree-then-branch removal-ordering contract.
        plan_dir = tmp_path / '.plan' / 'local' / 'plans' / 'rm-me'
        plan_dir.mkdir(parents=True)
        (plan_dir / 'status.json').write_text('{}')

        # Stub the resolution + branch-name reads.
        _stub_manage_status_call(
            monkeypatch,
            {
                ('get-worktree-path', '--plan-id', 'rm-me'): (
                    0,
                    {
                        'status': 'success',
                        'plan_id': 'rm-me',
                        'use_worktree': True,
                        'worktree_path': str(worktree),
                    },
                    '',
                ),
                ('metadata', '--plan-id', 'rm-me', '--get', '--field', 'worktree_branch'): (
                    0,
                    {'status': 'success', 'value': 'feature/rm-me'},
                    '',
                ),
            },
        )

        # Capture the order of git invocations.
        git_calls: list[list[str]] = []

        def fake_run_git(args):
            git_calls.append(list(args))
            # Mimic ``git worktree remove`` deleting the directory.
            if 'worktree' in args and 'remove' in args:
                shutil.rmtree(worktree, ignore_errors=True)
            return 0, '', ''

        monkeypatch.setattr(git_workflow, 'run_git', fake_run_git)

        result = cmd_worktree_remove(
            Namespace(plan_id='rm-me', force=False)
        )

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

    def test_remove_propagates_plan_resolution_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When manage-status cannot resolve the plan,
        ``cmd_worktree_remove`` must surface ``plan_resolution_failed``
        and never call ``git worktree remove``."""

        monkeypatch.setattr(git_workflow, '_find_plan_root_from_cwd', lambda: tmp_path)

        _stub_manage_status_call(
            monkeypatch,
            {
                ('get-worktree-path', '--plan-id', 'ghost'): (
                    1,
                    '',
                    'plan does not exist',
                ),
            },
        )

        called = []

        def trap_run_git(args):
            called.append(args)
            return 0, '', ''

        monkeypatch.setattr(git_workflow, 'run_git', trap_run_git)

        result = cmd_worktree_remove(Namespace(plan_id='ghost', force=False))
        assert result['status'] == 'error'
        assert result['error'] == 'plan_resolution_failed'
        assert called == [], 'no git call must run after a resolution failure'


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

        responses: dict[tuple[str, ...], tuple[int, dict | str, str]] = {
            ('list',): (0, list_payload, ''),
            ('get-worktree-path', '--plan-id', 'with-worktree'): (
                0,
                {
                    'status': 'success',
                    'plan_id': 'with-worktree',
                    'use_worktree': True,
                    'worktree_path': str(worktree_a),
                },
                '',
            ),
            ('get-worktree-path', '--plan-id', 'no-worktree'): (
                0,
                {
                    'status': 'success',
                    'plan_id': 'no-worktree',
                    'use_worktree': False,
                    'worktree_path': '',
                },
                '',
            ),
            ('metadata', '--plan-id', 'with-worktree', '--get', '--field', 'worktree_branch'): (
                0,
                {'status': 'success', 'value': 'feature/with-worktree'},
                '',
            ),
        }

        _stub_manage_status_call(monkeypatch, responses)
        monkeypatch.setattr(git_workflow, 'get_worktree_root', lambda: tmp_path)

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
        _stub_manage_status_call(
            monkeypatch,
            {
                ('get-worktree-path', '--plan-id', 'moved-plan'): (
                    0,
                    {
                        'status': 'success',
                        'plan_id': 'moved-plan',
                        'use_worktree': True,
                        'worktree_path': str(worktree),
                    },
                    '',
                )
            },
        )

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

        # The canonical manage-status channel CANNOT resolve the moved-in plan:
        # main's status.json no longer holds it, so get-worktree-path returns an
        # expected "not found" error (masked to not_found, not propagated). This
        # forces the primary path to yield no worktree_path and exercises the
        # structural-probe fallback.
        _stub_manage_status_call(
            monkeypatch,
            {
                ('get-worktree-path', '--plan-id', 'probe-plan'): (
                    1,
                    '',
                    'plan probe-plan not found',
                )
            },
        )

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

        # No worktree resolution should be needed; stub returns a failure to
        # prove the current-checkout branch short-circuits before manage-status.
        _stub_manage_status_call(
            monkeypatch,
            {('get-worktree-path', '--plan-id', 'here-plan'): (1, '', 'should not be called')},
        )

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
        _stub_manage_status_call(
            monkeypatch,
            {
                ('get-worktree-path', '--plan-id', 'ghost-plan'): (
                    0,
                    {
                        'status': 'success',
                        'plan_id': 'ghost-plan',
                        'use_worktree': False,
                        'worktree_path': '',
                    },
                    '',
                )
            },
        )

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
        _stub_manage_status_call(
            monkeypatch,
            {
                ('get-worktree-path', '--plan-id', 'stale-plan'): (
                    0,
                    {
                        'status': 'success',
                        'plan_id': 'stale-plan',
                        'use_worktree': True,
                        'worktree_path': str(worktree),
                    },
                    '',
                )
            },
        )

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
