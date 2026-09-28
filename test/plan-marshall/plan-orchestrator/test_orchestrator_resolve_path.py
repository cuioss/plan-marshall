#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``orchestrator resolve-path`` publishes the store seam's answer and creates no epic tree.

The verb is the one sanctioned source of the epic tree's physical location for a
direct Read/Write/Edit instruction and of the ``git -C`` target for a ledger
commit. With ``orchestrator.use_worktree`` OFF it reports the checkout the caller
stands in, exactly where every store consumer resolves today; with it ON it
reports the shared, main-anchored ledger worktree — from the main checkout and
from a plan worktree alike. An absent epic yields the would-be active path with
``exists: false`` and is never created; an archived-only epic yields the archived
path; an unsafe slug is refused before the seam is touched; and a seam refusal
reaches the caller as the typed error with exit 0.

Every call crosses the real subprocess boundary against a real sandbox (a bare
``origin``, a main checkout, a linked plan worktree) with no base-dir override in
the environment, so resolution runs through git exactly as it does for a user.
"""

from pathlib import Path

import pytest
from _orchestrator_worktree_fixtures import build_ledger_repo, use_real_resolver, write_marshal
from toon_parser import parse_toon

from conftest import get_script_path, run_script

MANAGE_STATUS = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')
ORCHESTRATOR = get_script_path('plan-marshall', 'plan-orchestrator', 'orchestrator.py')

_SLUG = 'epic-alpha'
_DIRTY_PATH = '.plan/orchestrator/epic-alpha/epic.md'


def _sandbox(tmp_path: Path, monkeypatch, *, knob: bool, dirty: bool = False):
    """A real sandbox with the knob set to ``knob`` and no override in the environment."""
    use_real_resolver(monkeypatch)
    monkeypatch.delenv('PLAN_TRACKED_CONFIG_DIR', raising=False)
    repo = build_ledger_repo(tmp_path)
    (repo.plan_worktree / '.plan' / 'local').mkdir(parents=True)
    write_marshal(repo.main, {'orchestrator': {'use_worktree': knob}})
    if dirty:
        target = repo.main / _DIRTY_PATH
        target.parent.mkdir(parents=True)
        target.write_text('# uncommitted ledger state\n', encoding='utf-8')
    return repo


def _run(script: Path, *args: str, cwd: Path) -> tuple[int, dict]:
    result = run_script(script, *args, cwd=cwd, timeout=60)
    return result.returncode, (parse_toon(result.stdout) if result.stdout.strip() else {})


def _resolve(cwd: Path, slug: str = _SLUG) -> dict:
    code, payload = _run(ORCHESTRATOR, 'resolve-path', '--slug', slug, cwd=cwd)
    assert code == 0, payload
    return payload


def _ok(script: Path, *args: str, cwd: Path) -> dict:
    code, payload = _run(script, *args, cwd=cwd)
    assert code == 0 and payload.get('status') == 'success', payload
    return payload


class TestKnobOff:
    def test_reports_the_callers_checkout_and_creates_neither_tree(self, tmp_path, monkeypatch):
        repo = _sandbox(tmp_path, monkeypatch, knob=False)
        expected = (repo.main / '.plan' / 'orchestrator' / _SLUG).resolve()

        payload = _resolve(repo.main)

        assert payload['status'] == 'success'
        assert Path(payload['epic_dir']).resolve() == expected
        assert Path(payload['store_checkout']).resolve() == repo.main.resolve()
        assert (payload['exists'], payload['archived'], payload['use_worktree']) == (False, False, False)
        assert not expected.exists()
        assert not repo.expected_worktree.exists()

    def test_an_archived_only_epic_resolves_to_its_archived_home(self, tmp_path, monkeypatch):
        repo = _sandbox(tmp_path, monkeypatch, knob=False)
        _ok(MANAGE_STATUS, 'create', '--plan-id', _SLUG, '--title', 'Alpha', '--store', 'orchestrator', cwd=repo.main)
        _ok(ORCHESTRATOR, 'scaffold', '--slug', _SLUG, cwd=repo.main)
        _ok(
            MANAGE_STATUS,
            'update-field',
            '--plan-id',
            _SLUG,
            '--store',
            'orchestrator',
            '--field',
            'phase',
            '--value',
            'closed',
            cwd=repo.main,
        )
        _ok(ORCHESTRATOR, 'archive', '--slug', _SLUG, cwd=repo.main)

        payload = _resolve(repo.main)

        archived = (repo.main / '.plan' / 'archived-orchestrators' / _SLUG).resolve()
        assert Path(payload['epic_dir']).resolve() == archived
        assert (payload['exists'], payload['archived']) == (True, True)
        assert not (repo.main / '.plan' / 'orchestrator' / _SLUG).exists()


class TestKnobOn:
    @pytest.mark.parametrize('where', ['main', 'plan_worktree'])
    def test_resolves_under_the_shared_worktree_from_either_checkout(self, tmp_path, monkeypatch, where):
        repo = _sandbox(tmp_path, monkeypatch, knob=True)
        shared = repo.expected_worktree

        payload = _resolve(getattr(repo, where))

        assert Path(payload['epic_dir']).resolve() == shared / '.plan' / 'orchestrator' / _SLUG
        assert Path(payload['store_checkout']).resolve() == shared
        assert (payload['exists'], payload['archived'], payload['use_worktree']) == (False, False, True)
        assert not (shared / '.plan' / 'orchestrator' / _SLUG).exists()

    def test_a_scaffolded_epic_reports_exists(self, tmp_path, monkeypatch):
        # Matched control for the no-creation assertion above: once the tree is
        # scaffolded the same call reports it present, so ``exists: false`` is a
        # measured absence and not a constant.
        repo = _sandbox(tmp_path, monkeypatch, knob=True)
        _ok(ORCHESTRATOR, 'scaffold', '--slug', _SLUG, cwd=repo.main)

        payload = _resolve(repo.plan_worktree)

        assert (payload['exists'], payload['archived']) == (True, False)
        assert Path(payload['epic_dir']).resolve() == repo.expected_worktree / '.plan' / 'orchestrator' / _SLUG

    def test_an_unsafe_slug_is_refused_before_the_seam_is_touched(self, tmp_path, monkeypatch):
        repo = _sandbox(tmp_path, monkeypatch, knob=True)

        payload = _resolve(repo.main, slug='../escape')

        assert (payload['status'], payload['error']) == ('error', 'invalid_slug')
        assert not repo.expected_worktree.exists()


class TestSeamRefusal:
    def test_a_refused_seam_surfaces_as_the_typed_error_with_exit_zero(self, tmp_path, monkeypatch):
        repo = _sandbox(tmp_path, monkeypatch, knob=True, dirty=True)

        code, payload = _run(ORCHESTRATOR, 'resolve-path', '--slug', _SLUG, cwd=repo.main)

        assert code == 0, payload
        assert (payload.get('status'), payload.get('error')) == ('error', 'ledger_cutover_refused')
        assert payload['dirty_paths'] == [_DIRTY_PATH]
        assert not repo.expected_worktree.exists()

    def test_the_clean_control_resolves(self, tmp_path, monkeypatch):
        # Matched control: the same call over a clean main checkout succeeds and
        # creates the shared tree, so the refusal above is caused by the dirt.
        repo = _sandbox(tmp_path, monkeypatch, knob=True, dirty=False)

        code, payload = _run(ORCHESTRATOR, 'resolve-path', '--slug', _SLUG, cwd=repo.main)

        assert code == 0
        assert payload['status'] == 'success'
        assert repo.expected_worktree.is_dir()
