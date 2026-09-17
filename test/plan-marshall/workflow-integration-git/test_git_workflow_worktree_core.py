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
small and stay co-located with the test cases.
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

from conftest import PROJECT_ROOT, get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'git-workflow.py')

# The entrypoint filename is kebab-case (git-workflow.py), which is not a
# valid Python module identifier — load it via importlib instead of `import`.
git_workflow = load_script_module('plan-marshall', 'workflow-integration-git', 'git-workflow.py', 'git_workflow')

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


def _stub_manage_status_call(
    monkeypatch: pytest.MonkeyPatch, responses: dict[tuple[str, ...], tuple[int, dict | str, str]]
) -> list[tuple[str, ...]]:
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
    import file_ops  # local import: the handle is needed only to patch a seam here

    monkeypatch.setenv('PLAN_BASE_DIR', str(root / '.plan' / 'local'))
    monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)


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


def _stage_removal(root: Path, monkeypatch: pytest.MonkeyPatch, *, plan_id: str, extra_files: int = 0) -> Path:
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


def _record_run_git(monkeypatch: pytest.MonkeyPatch, worktree: Path, *, rc: int = 0, stderr: str = '') -> list[dict]:
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



# =============================================================================
# No-symlink contract for the worktree .plan/local materializer
# =============================================================================


class TestEnsureWorktreePlanLocalReal:
    """``_ensure_worktree_plan_local_real`` creates a REAL .plan/local with NO
    symlinks. The retired ``_ensure_worktree_plan_symlinks``
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

    def test_returns_plan_resolution_failed_when_use_worktree_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
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

    def test_propagates_resolver_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A resolver failure surfaces as ``plan_resolution_failed``, message intact."""
        import file_ops  # local import: the handle is needed only to patch a seam here

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

    def test_create_writes_metadata_via_manage_status(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
                (
                    'metadata',
                    '--plan-id',
                    'my-plan',
                    '--set',
                    '--field',
                    'worktree_path',
                    '--value',
                    str(target_root / 'my-plan'),
                ): (
                    0,
                    {'status': 'success'},
                    '',
                ),
                (
                    'metadata',
                    '--plan-id',
                    'my-plan',
                    '--set',
                    '--field',
                    'worktree_branch',
                    '--value',
                    'feature/my-plan',
                ): (
                    0,
                    {'status': 'success'},
                    '',
                ),
            },
        )

        result = cmd_worktree_create(Namespace(plan_id='my-plan', branch='feature/my-plan', base=None))

        assert result['status'] == 'success', result
        assert result['plan_id'] == 'my-plan'
        assert result['worktree_path'] == str(target_root / 'my-plan')
        assert result['branch'] == 'feature/my-plan'

        # All three metadata fields must have been persisted via manage-status.
        recorded_fields = {call[5] for call in calls if len(call) >= 6 and call[0] == 'metadata' and call[3] == '--set'}
        assert recorded_fields == {'use_worktree', 'worktree_path', 'worktree_branch'}

    def test_create_rejects_when_not_in_git_repo(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Outside a git repo, ``get_worktree_root()`` raises and the verb
        emits ``plan_resolution_failed`` instead of leaking the exception."""

        def raising():
            raise RuntimeError('requires a git repository')

        monkeypatch.setattr(git_workflow, 'get_worktree_root', raising)

        result = cmd_worktree_create(Namespace(plan_id='no-repo', branch='feature/no-repo', base=None))
        assert result['status'] == 'error'
        assert result['error'] == 'plan_resolution_failed'
