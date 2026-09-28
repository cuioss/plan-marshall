#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end routing of every script consumer through the orchestrator store seam.

With ``orchestrator.use_worktree`` ON, every script consumer of the orchestrator
ledger store — ``manage-status`` and ``manage-logging`` with ``--store
orchestrator``, ``orchestrator.py`` ``scaffold`` / ``queue --add-row`` / ``corpus
epics`` / ``archive``, and the plan-side ``inbox write`` / ``read`` — reads and
writes only under the ONE shared ledger worktree, including when the caller
stands in a plan worktree, and the main checkout's ledger paths stay clean. With
the knob OFF the same calls land on the checkout the caller stands in, exactly as
before, and no shared tree is created. ``inbox detect`` is a pure parse of the
logical pointer and reads no store at all; it is exercised to pin that it keeps
classifying the pointer identically under both knob positions.

Every call crosses the real subprocess boundary (``run_script`` with a
constructed argv and an explicit ``cwd``) against a real sandbox — a bare
``origin``, a main checkout, and a linked plan worktree that carries its own
``.plan/local`` exactly as a moved-in plan worktree does — with no base-dir
override in the environment. The per-consumer refusal cases live in
``test_orchestrator_worktree_refusal.py``.
"""

from pathlib import Path

import pytest
from _orchestrator_worktree_fixtures import build_ledger_repo, git, use_real_resolver, write_marshal
from toon_parser import parse_toon

from conftest import get_script_path, run_script

MANAGE_STATUS = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')
MANAGE_LOGGING = get_script_path('plan-marshall', 'manage-logging', 'manage-logging.py')
ORCHESTRATOR = get_script_path('plan-marshall', 'plan-orchestrator', 'orchestrator.py')

_SLUG = 'epic-alpha'
_SENDER = 'plan-sender'
_POINTER = '.plan/orchestrator/epic-alpha/plans/PLAN-01-alpha.md'
_LEDGER_PATHSPECS = ('.plan/orchestrator', '.plan/archived-orchestrators')


def _sandbox(tmp_path: Path, monkeypatch, *, knob: bool):
    """A real sandbox with the knob set to ``knob`` and no override in the environment."""
    use_real_resolver(monkeypatch)
    monkeypatch.delenv('PLAN_TRACKED_CONFIG_DIR', raising=False)
    repo = build_ledger_repo(tmp_path)
    (repo.plan_worktree / '.plan' / 'local').mkdir(parents=True)
    write_marshal(repo.main, {'orchestrator': {'use_worktree': knob}})
    return repo


def _call(script: Path, *args: str, cwd: Path) -> dict:
    """Run one consumer and return its TOON payload, failing on a crash exit."""
    result = run_script(script, *args, cwd=cwd, timeout=60)
    assert result.returncode == 0, f'{script.name} {args}: rc={result.returncode} stdout={result.stdout!r}'
    return parse_toon(result.stdout) if result.stdout.strip() else {}


def _ledger_porcelain(checkout: Path) -> str:
    return git(checkout, 'status', '--porcelain', '--untracked-files=all', '--', *_LEDGER_PATHSPECS)


def _drive_main_side(repo) -> dict[str, dict]:
    """Create, scaffold, stage and log an epic from the MAIN checkout."""
    main = repo.main
    return {
        'create': _call(
            MANAGE_STATUS, 'create', '--plan-id', _SLUG, '--title', 'Alpha', '--store', 'orchestrator', cwd=main
        ),
        'scaffold': _call(ORCHESTRATOR, 'scaffold', '--slug', _SLUG, cwd=main),
        'add_row': _call(
            ORCHESTRATOR,
            'queue',
            '--slug',
            _SLUG,
            '--add-row',
            'PLAN-01',
            '--slug-value',
            'alpha-one',
            '--workstream',
            'WS-01',
            cwd=main,
        ),
        'log': _call(
            MANAGE_LOGGING,
            'work',
            '--plan-id',
            _SLUG,
            '--store',
            'orchestrator',
            '--level',
            'INFO',
            '--message',
            'routed entry',
            cwd=main,
        ),
        'epics': _call(ORCHESTRATOR, 'corpus', 'epics', cwd=main),
    }


class TestKnobOn:
    """Every consumer touches only the shared ledger worktree."""

    @pytest.fixture
    def repo(self, tmp_path, monkeypatch):
        return _sandbox(tmp_path, monkeypatch, knob=True)

    def test_main_side_consumers_write_only_under_the_shared_worktree(self, repo):
        shared = repo.expected_worktree / '.plan' / 'orchestrator' / _SLUG

        results = _drive_main_side(repo)

        assert Path(results['create']['file']).resolve() == shared / 'status.json'
        assert Path(results['scaffold']['root']).resolve() == shared
        assert (shared / 'queue' / 'PLAN-01.json').is_file()
        assert (shared / 'logs' / 'work.log').read_text(encoding='utf-8').count('routed entry') == 1
        active_root = next(root for root in results['epics']['roots'] if root['scope'] == 'active')
        assert Path(active_root['path']).resolve() == shared.parent
        assert results['epics']['active'] == [_SLUG]
        assert _ledger_porcelain(repo.main) == ''

    def test_plan_worktree_inbox_write_lands_in_the_shared_worktree_and_reads_back(self, repo, tmp_path):
        _drive_main_side(repo)
        payload = tmp_path / 'payload.md'
        payload.write_text('## Finding\n\nRouted from a plan worktree.\n', encoding='utf-8')

        written = _call(
            ORCHESTRATOR,
            'inbox',
            'write',
            '--slug',
            _SLUG,
            '--sender-type',
            'plan',
            '--sender-id',
            _SENDER,
            '--kind',
            'finding',
            '--payload-file',
            str(payload),
            cwd=repo.plan_worktree,
        )
        listed = _call(ORCHESTRATOR, 'inbox', 'list', '--slug', _SLUG, cwd=repo.main)
        read = _call(ORCHESTRATOR, 'inbox', 'read', '--slug', _SLUG, '--plan-id', _SENDER, cwd=repo.plan_worktree)

        inbox = repo.expected_worktree / '.plan' / 'orchestrator' / _SLUG / 'inbox'
        assert Path(written['path']).resolve().parent == inbox
        assert listed['count'] == 1
        # The plan worktree's OWN .plan holds no epic tree, so ``unmeasured`` would
        # mean the read looked there; ``never_delivered`` is a positive reading of
        # the shared tree's epic, whose mailbox was simply never written to.
        assert (read['status'], read['delivery_state']) == ('success', 'never_delivered')
        assert _ledger_porcelain(repo.main) == ''
        assert _ledger_porcelain(repo.plan_worktree) == ''

    def test_archive_relocates_the_epic_inside_the_shared_worktree(self, repo):
        _drive_main_side(repo)
        _call(
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

        archived = _call(ORCHESTRATOR, 'archive', '--slug', _SLUG, cwd=repo.main)

        store = repo.expected_worktree / '.plan'
        assert Path(archived['archived_to']).resolve() == store / 'archived-orchestrators' / _SLUG
        assert not (store / 'orchestrator' / _SLUG).exists()
        assert _ledger_porcelain(repo.main) == ''

    def test_inbox_detect_classifies_the_logical_pointer(self, repo):
        detected = _call(ORCHESTRATOR, 'inbox', 'detect', '--source-id', _POINTER, cwd=repo.plan_worktree)

        assert (detected['orchestrated'], detected['epic']) == (True, _SLUG)


class TestKnobOffControl:
    """With the knob off the same calls land on the caller's checkout, as before."""

    @pytest.fixture
    def repo(self, tmp_path, monkeypatch):
        return _sandbox(tmp_path, monkeypatch, knob=False)

    def test_main_side_consumers_write_to_the_main_checkout_and_create_no_shared_tree(self, repo):
        local = (repo.main / '.plan' / 'orchestrator' / _SLUG).resolve()

        results = _drive_main_side(repo)

        assert Path(results['create']['file']).resolve() == local / 'status.json'
        assert Path(results['scaffold']['root']).resolve() == local
        assert (local / 'logs' / 'work.log').is_file()
        assert _ledger_porcelain(repo.main) != ''
        assert not repo.expected_worktree.exists()

    def test_inbox_detect_classifies_the_logical_pointer_identically(self, repo):
        detected = _call(ORCHESTRATOR, 'inbox', 'detect', '--source-id', _POINTER, cwd=repo.plan_worktree)

        assert (detected['orchestrated'], detected['epic']) == (True, _SLUG)
