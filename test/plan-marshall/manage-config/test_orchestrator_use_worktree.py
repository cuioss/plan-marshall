#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``orchestrator get/set --field use_worktree`` in manage-config.

The knob is read AND written only against the MAIN checkout's ``marshal.json``,
and a flip is refused while ledger state would be stranded on the side being
left. Every case runs against a real sandbox — a bare ``origin`` remote, a main
checkout, and a linked plan worktree under ``.plan/local/worktrees/`` — with the
base-dir override cleared, so the main checkout is resolved through git exactly
as in production. The cwd selects where the caller stands, and the handler's
write target (``_config_core.MARSHAL_PATH``) is pointed at that checkout's
``marshal.json``.
"""

# ruff: noqa: I001

import json
import subprocess
from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path

import pytest

import file_ops
from _orchestrator_worktree_fixtures import build_ledger_repo, commit_file, git, use_real_resolver
from conftest import load_script_module

_cmd_orchestrator_mod = load_script_module(
    'plan-marshall',
    'manage-config',
    '_cmd_orchestrator.py',
    module_name='_cmd_orchestrator_for_use_worktree_test',
)
_config_core = _cmd_orchestrator_mod._config_core

cmd_orchestrator_get = _cmd_orchestrator_mod.cmd_orchestrator_get
cmd_orchestrator_set = _cmd_orchestrator_mod.cmd_orchestrator_set

# Identity and signing are pinned per call so a developer's global git config
# cannot decide the outcome.
_GIT_CONFIG = ('-c', 'user.name=use-worktree-test', '-c', 'user.email=test@example.com', '-c', 'commit.gpgsign=false')

_LEDGER_BRANCH = 'chore/orchestrator-ledger'
_DIRTY_LEDGER_PATH = '.plan/orchestrator/epic-a/inbox.md'


def _git(cwd: Path, *args: str) -> str:
    """Run a test-controlled git command in ``cwd`` and return its stripped stdout."""
    result = subprocess.run(
        ['git', *_GIT_CONFIG, *args], cwd=cwd, check=True, capture_output=True, text=True, timeout=30
    )
    return result.stdout.strip()


@dataclass(frozen=True)
class _Sandbox:
    main: Path
    plan_worktree: Path

    @property
    def ledger_worktree(self) -> Path:
        """The main-anchored location of the shared ledger worktree."""
        return self.main / '.plan' / 'local' / 'worktrees' / '_orchestrator'

    def create_ledger_worktree(self) -> Path:
        """Register the shared ledger worktree on its branch at ``origin/main``."""
        _git(self.main, 'worktree', 'add', '-b', _LEDGER_BRANCH, str(self.ledger_worktree), 'origin/main')
        return self.ledger_worktree


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """A real origin / main / plan-worktree topology with the cwd on the main checkout."""
    monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
    monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
    origin = tmp_path / 'origin.git'
    _git(tmp_path, 'init', '--bare', '--initial-branch=main', str(origin))
    main = tmp_path / 'main'
    main.mkdir()
    _git(main, 'init', '--initial-branch=main')
    _git(main, 'remote', 'add', 'origin', str(origin))
    (main / 'README.md').write_text('sandbox\n', encoding='utf-8')
    _git(main, 'add', 'README.md')
    _git(main, 'commit', '-m', 'init')
    _git(main, 'push', '--set-upstream', 'origin', 'main')
    plan_worktree = main / '.plan' / 'local' / 'worktrees' / 'plan-under-test'
    _git(main, 'worktree', 'add', '-b', 'feature/plan-under-test', str(plan_worktree))
    monkeypatch.chdir(main)
    return _Sandbox(main=main, plan_worktree=plan_worktree)


def _write_marshal(checkout: Path, config: dict) -> Path:
    path = checkout / '.plan' / 'marshal.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    return path


def _stand_in(monkeypatch, checkout: Path, config: dict) -> Path:
    """Put the caller in ``checkout``: cwd there, and the handler writing its ``marshal.json``."""
    path = _write_marshal(checkout, config)
    monkeypatch.chdir(checkout)
    monkeypatch.setattr(_config_core, 'MARSHAL_PATH', path)
    return path


def _dirty(checkout: Path, relpath: str = _DIRTY_LEDGER_PATH) -> None:
    target = checkout / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('uncommitted ledger state\n', encoding='utf-8')


def _set(value: str) -> dict:
    result: dict = cmd_orchestrator_set(Namespace(field='use_worktree', value=value))
    return result


class TestRoundTrip:
    """``set`` persists a bool on the main checkout and ``get`` reads it back."""

    def test_set_on_the_main_checkout_persists_and_get_reads_it_back(self, sandbox, monkeypatch):
        path = _stand_in(monkeypatch, sandbox.main, {'orchestrator': {'use_worktree': False}})

        result = _set('true')
        read = cmd_orchestrator_get(Namespace(field='use_worktree'))

        assert (result['status'], result['value']) == ('success', True)
        assert json.loads(path.read_text(encoding='utf-8'))['orchestrator']['use_worktree'] is True
        assert (read['status'], read['value'], read['set']) == ('success', True, True)
        assert Path(read['knob_path']).resolve() == path.resolve()

    @pytest.mark.parametrize('value', ['maybe', '2', ''])
    def test_non_bool_value_is_rejected_and_nothing_is_written(self, sandbox, monkeypatch, value):
        path = _stand_in(monkeypatch, sandbox.main, {'orchestrator': {'use_worktree': False}})
        before = path.read_bytes()

        result = _set(value)

        assert result['status'] == 'error'
        assert 'use_worktree' in result['error']
        assert path.read_bytes() == before


class TestMainCheckoutWriteGuard:
    """A write that would not land in the main checkout's ``marshal.json`` is refused."""

    def test_set_from_a_linked_worktree_is_refused_and_writes_nothing(self, sandbox, monkeypatch):
        main_path = _write_marshal(sandbox.main, {'orchestrator': {'use_worktree': False}})
        worktree_path = _stand_in(monkeypatch, sandbox.plan_worktree, {'orchestrator': {'use_worktree': False}})
        main_before, worktree_before = main_path.read_bytes(), worktree_path.read_bytes()

        result = _set('true')

        assert (result['status'], result['error']) == ('error', 'use_worktree_requires_main_checkout')
        assert Path(result['write_path']).resolve() == worktree_path.resolve()
        assert Path(result['knob_path']).resolve() == main_path.resolve()
        assert (main_path.read_bytes(), worktree_path.read_bytes()) == (main_before, worktree_before)

    def test_the_same_set_from_the_main_checkout_succeeds(self, sandbox, monkeypatch):
        """Matched control: only the checkout the caller stands in differs from the refusal above."""
        _write_marshal(sandbox.plan_worktree, {'orchestrator': {'use_worktree': False}})
        _stand_in(monkeypatch, sandbox.main, {'orchestrator': {'use_worktree': False}})

        assert _set('true')['status'] == 'success'

    def test_get_from_a_linked_worktree_reports_the_main_checkouts_value(self, sandbox, monkeypatch):
        _write_marshal(sandbox.main, {'orchestrator': {'use_worktree': True}})
        _stand_in(monkeypatch, sandbox.plan_worktree, {'orchestrator': {'use_worktree': False}})

        read = cmd_orchestrator_get(Namespace(field='use_worktree'))

        assert (read['status'], read['value'], read['set']) == ('success', True, True)


class TestCutoverRefusal:
    """A flip is refused while ledger state would be stranded on the side being left."""

    def test_switch_on_is_refused_while_the_main_checkout_holds_a_dirty_ledger_path(self, sandbox, monkeypatch):
        path = _stand_in(monkeypatch, sandbox.main, {'orchestrator': {'use_worktree': False}})
        _dirty(sandbox.main)
        before = path.read_bytes()

        result = _set('true')

        assert (result['status'], result['error'], result['dirty_paths']) == (
            'error',
            'ledger_cutover_refused',
            [_DIRTY_LEDGER_PATH],
        )
        assert path.read_bytes() == before

    def test_switch_on_succeeds_when_only_non_ledger_paths_are_dirty(self, sandbox, monkeypatch):
        """Matched control: the same dirt outside the ledger store never blocks the switch-on."""
        _stand_in(monkeypatch, sandbox.main, {'orchestrator': {'use_worktree': False}})
        _dirty(sandbox.main, 'docs/notes.md')

        assert _set('true')['status'] == 'success'

    def test_switch_off_is_refused_while_the_shared_worktree_holds_a_dirty_ledger_path(self, sandbox, monkeypatch):
        path = _stand_in(monkeypatch, sandbox.main, {'orchestrator': {'use_worktree': True}})
        ledger_worktree = sandbox.create_ledger_worktree()
        _dirty(ledger_worktree)
        before = path.read_bytes()

        result = _set('false')

        assert (result['status'], result['error'], result['dirty_paths']) == (
            'error',
            'ledger_cutover_refused',
            [_DIRTY_LEDGER_PATH],
        )
        assert Path(result['checkout']).resolve() == ledger_worktree.resolve()
        assert path.read_bytes() == before

    def test_switch_off_succeeds_from_a_clean_shared_worktree(self, sandbox, monkeypatch):
        """Matched control: the shared worktree exists but strands nothing."""
        path = _stand_in(monkeypatch, sandbox.main, {'orchestrator': {'use_worktree': True}})
        sandbox.create_ledger_worktree()

        result = _set('false')

        assert result['status'] == 'success'
        assert json.loads(path.read_text(encoding='utf-8'))['orchestrator']['use_worktree'] is False

    def test_a_same_value_reset_does_not_run_the_drift_check(self, sandbox, monkeypatch):
        """A stored ``true`` re-set to ``true`` persists without consulting the detector.

        The main checkout is dirty, so a detector run would have refused; the spy
        pins that the success is the skipped check, not a clean one.
        """
        _stand_in(monkeypatch, sandbox.main, {'orchestrator': {'use_worktree': True}})
        _dirty(sandbox.main)
        calls: list = []
        monkeypatch.setattr(_cmd_orchestrator_mod, 'detect_ledger_drift', lambda *args: calls.append(args) or [])

        result = _set('true')

        assert (result['status'], calls) == ('success', [])

    def test_an_unfetchable_base_refuses_even_with_a_stale_base_ref_present(self, sandbox, monkeypatch):
        """A failed fetch fails closed; the stale local ``origin/main`` is not compared against.

        ``refs/remotes/origin/main`` still resolves after the remote moves away, so
        a drift check run without the fetch would read the clean checkout as clean.
        """
        path = _stand_in(monkeypatch, sandbox.main, {'orchestrator': {'use_worktree': False}})
        _git(sandbox.main, 'remote', 'set-url', 'origin', str(sandbox.main.parent / 'moved-away.git'))
        before = path.read_bytes()

        result = _set('true')

        assert (result['status'], result['error'], result['base_ref']) == (
            'error',
            'ledger_drift_unevaluable',
            'origin/main',
        )
        assert path.read_bytes() == before

    def test_an_unevaluable_drift_check_refuses_with_its_own_code(self, sandbox, monkeypatch):
        path = _stand_in(
            monkeypatch,
            sandbox.main,
            {'project': {'default_base_branch': 'no-such-branch'}, 'orchestrator': {'use_worktree': False}},
        )
        before = path.read_bytes()

        result = _set('true')

        assert (result['status'], result['error'], result['base_ref']) == (
            'error',
            'ledger_drift_unevaluable',
            'origin/no-such-branch',
        )
        assert path.read_bytes() == before


_LANDED_LEDGER_PATH = '.plan/orchestrator/epic-a/status.json'
_LANDED_LEDGER_CONTENT = '{"phase": "execute"}\n'


@pytest.fixture
def ledger_repo(tmp_path, monkeypatch):
    """A real sandbox whose shared ledger worktree carries one committed ledger change."""
    use_real_resolver(monkeypatch)
    repo = build_ledger_repo(tmp_path)
    git(repo.main, 'worktree', 'add', '-b', _LEDGER_BRANCH, str(repo.expected_worktree), 'origin/main')
    commit_file(repo.expected_worktree, _LANDED_LEDGER_PATH, _LANDED_LEDGER_CONTENT)
    return repo


class TestSwitchOffAfterLanding:
    """Switch-off compares the shared worktree's ledger content with the freshly fetched base.

    The peer lands content on ``origin/main`` the way a squash merge does — a new
    commit, never an ancestor of the ledger branch — and the main checkout never
    fetches it, so only the handler's own fetch can bring it into the comparison.
    """

    @staticmethod
    def _land_on_origin(repo, content: str) -> None:
        commit_file(repo.peer, _LANDED_LEDGER_PATH, content)
        git(repo.peer, 'push', 'origin', 'main')

    def test_switch_off_is_not_refused_once_the_ledger_content_landed_under_a_new_sha(self, ledger_repo, monkeypatch):
        path = _stand_in(monkeypatch, ledger_repo.main, {'orchestrator': {'use_worktree': True}})
        self._land_on_origin(ledger_repo, _LANDED_LEDGER_CONTENT)

        result = _set('false')

        assert result['status'] == 'success', result
        assert json.loads(path.read_text(encoding='utf-8'))['orchestrator']['use_worktree'] is False

    def test_switch_off_is_refused_naming_ledger_content_the_base_lacks(self, ledger_repo, monkeypatch):
        """Matched control: the same topology, but the landed content differs from the ledger commit."""
        path = _stand_in(monkeypatch, ledger_repo.main, {'orchestrator': {'use_worktree': True}})
        self._land_on_origin(ledger_repo, '{"phase": "outline"}\n')
        before = path.read_bytes()

        result = _set('false')

        assert (result['status'], result['error'], result['dirty_paths']) == (
            'error',
            'ledger_cutover_refused',
            [_LANDED_LEDGER_PATH],
        )
        assert path.read_bytes() == before
