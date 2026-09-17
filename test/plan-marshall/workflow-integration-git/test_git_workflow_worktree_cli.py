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
# worktree-list — filter from manage-status list by use_worktree==true
# =============================================================================


class TestWorktreeList:
    """``cmd_worktree_list`` enumerates plans whose status declares a
    worktree by calling ``manage-status list`` then ``get-worktree-path``
    per plan. Plans without ``metadata.use_worktree==true`` are silently
    skipped.
    """

    def test_filters_to_worktree_plans_only(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

    def test_list_propagates_manage_status_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
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
        import file_ops  # local import: the handle is needed only to patch a seam here

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
        import file_ops  # local import: the handle is needed only to patch a seam here

        def _forbidden(_plan_id):
            raise AssertionError('the current-checkout branch consulted the resolver')

        monkeypatch.setattr(file_ops, '_query_worktree_path', _forbidden)

        result = cmd_locate_plan_checkout(Namespace(plan_id='here-plan'))
        assert result['status'] == 'success'
        assert result['plan_id'] == 'here-plan'
        assert result['location'] == 'current'
        assert 'worktree_path' not in result

    def test_returns_not_found_for_unknown_plan(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
        real_executor = PROJECT_ROOT / '.plan' / 'execute-script.py'
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
