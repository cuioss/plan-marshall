#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Every CLI consumer surfaces an orchestrator store refusal as its own verdict.

With ``orchestrator.use_worktree`` ON and the seam forced to refuse — the main
checkout holds an uncommitted ledger path before first use, so the shared ledger
worktree is never created (``ledger_cutover_refused``) — each script entry point
that reaches the orchestrator store must return ``status: error`` carrying that
code and the offending path, with exit 0. None may convert the refusal into a
not-found, an empty result, a fail-open success, or a crash. Each case carries a
matched control over a CLEAN main checkout, where the same call does not report
the refusal, so every refusal assertion is shown to be able to fail.

``inbox detect`` is deliberately NOT in the refusal population: it is a pure
parse of the logical ``source_id`` pointer and reads no store, so there is no
refusal for it to surface. It is pinned separately as succeeding under the
refused sandbox, which is what keeps its absence from the table a measured fact
rather than an omission.

The sandboxes are module-scoped (a refused call writes nothing, and the clean
control's first call only creates the shared tree every later control reuses);
the environment is cleared per test so no base-dir override reaches the
subprocess.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from _orchestrator_worktree_fixtures import build_ledger_repo, write_marshal
from toon_parser import parse_toon

from conftest import get_script_path, run_script

MANAGE_STATUS = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')
MANAGE_LOGGING = get_script_path('plan-marshall', 'manage-logging', 'manage-logging.py')
MANAGE_PLAN_DOCUMENTS = get_script_path('plan-marshall', 'manage-plan-documents', 'manage-plan-documents.py')
ORCHESTRATOR = get_script_path('plan-marshall', 'plan-orchestrator', 'orchestrator.py')
EPIC_SURFACE_PARTITION = get_script_path(
    'pm-plugin-development', 'tools-epic-surface-partition', 'epic-surface-partition.py'
)

_SLUG = 'epic-alpha'
_SENDER = 'plan-sender'
_POINTER = '.plan/orchestrator/epic-alpha/plans/PLAN-01-alpha.md'
_DIRTY_PATH = '.plan/orchestrator/epic-alpha/epic.md'
_REFUSAL = 'ledger_cutover_refused'


def _build(root: Path, *, dirty: bool):
    repo = build_ledger_repo(root)
    (repo.plan_worktree / '.plan' / 'local').mkdir(parents=True)
    write_marshal(repo.main, {'orchestrator': {'use_worktree': True}})
    if dirty:
        target = repo.main / _DIRTY_PATH
        target.parent.mkdir(parents=True)
        target.write_text('# uncommitted ledger state\n', encoding='utf-8')
    (root / 'payload.md').write_text('## Finding\n\nA plan-side observation.\n', encoding='utf-8')
    return repo


@pytest.fixture(scope='module')
def refused_repo(tmp_path_factory):
    return _build(tmp_path_factory.mktemp('refused'), dirty=True)


@pytest.fixture(scope='module')
def clean_repo(tmp_path_factory):
    return _build(tmp_path_factory.mktemp('clean'), dirty=False)


@pytest.fixture(autouse=True)
def _no_override_in_the_environment(monkeypatch):
    """The subprocess inherits the environment; no override may stand in for main."""
    for name in ('PLAN_BASE_DIR', 'PLAN_TRACKED_CONFIG_DIR'):
        monkeypatch.delenv(name, raising=False)


#: ``{case id: (script, argv builder, cwd selector)}`` — one row per CLI entry
#: point that reaches the orchestrator store. The argv builder receives the
#: sandbox so a payload path can be composed from it.
_Argv = Callable[[Any], list[str]]
_CONSUMERS: dict[str, tuple[Path, _Argv, str]] = {
    'manage-status-read': (
        MANAGE_STATUS,
        lambda repo: ['read', '--plan-id', _SLUG, '--store', 'orchestrator'],
        'main',
    ),
    'manage-logging-work': (
        MANAGE_LOGGING,
        lambda repo: ['work', '--plan-id', _SLUG, '--store', 'orchestrator', '--level', 'INFO', '--message', 'm'],
        'main',
    ),
    'orchestrator-queue': (ORCHESTRATOR, lambda repo: ['queue', '--slug', _SLUG], 'main'),
    'orchestrator-archive': (ORCHESTRATOR, lambda repo: ['archive', '--slug', _SLUG], 'main'),
    'orchestrator-corpus-epics': (ORCHESTRATOR, lambda repo: ['corpus', 'epics'], 'main'),
    'inbox-write': (
        ORCHESTRATOR,
        lambda repo: [
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
            str(repo.main.parent / 'payload.md'),
        ],
        'plan_worktree',
    ),
    'inbox-read': (
        ORCHESTRATOR,
        lambda repo: ['inbox', 'read', '--slug', _SLUG, '--plan-id', _SENDER],
        'plan_worktree',
    ),
    'request-create-body-file': (
        MANAGE_PLAN_DOCUMENTS,
        lambda repo: [
            'request',
            'create',
            '--plan-id',
            'refusal-plan',
            '--title',
            'Refusal',
            '--source',
            'description',
            '--body-file',
            _POINTER,
        ],
        'main',
    ),
    'epic-surface-partition-classify': (
        EPIC_SURFACE_PARTITION,
        lambda repo: ['classify', '--epic', _SLUG],
        'main',
    ),
}


def _invoke(repo, case: str) -> tuple[int, dict]:
    script, argv, where = _CONSUMERS[case]
    result = run_script(script, *argv(repo), cwd=getattr(repo, where), timeout=60)
    payload = parse_toon(result.stdout) if result.stdout.strip() else {}
    return result.returncode, payload


@pytest.mark.parametrize('case', list(_CONSUMERS), ids=list(_CONSUMERS))
def test_refused_seam_surfaces_as_the_typed_error_with_exit_zero(refused_repo, case):
    code, payload = _invoke(refused_repo, case)

    assert code == 0, payload
    assert (payload.get('status'), payload.get('error')) == ('error', _REFUSAL), payload
    assert payload['dirty_paths'] == [_DIRTY_PATH]
    assert not refused_repo.expected_worktree.exists()


@pytest.mark.parametrize('case', list(_CONSUMERS), ids=list(_CONSUMERS))
def test_clean_control_does_not_report_the_refusal(clean_repo, case):
    """Matched control: over a clean main checkout the refusal is absent."""
    _code, payload = _invoke(clean_repo, case)

    assert payload.get('error') != _REFUSAL, payload
    assert clean_repo.expected_worktree.is_dir()


def test_inbox_detect_reads_no_store_and_succeeds_under_a_refused_seam(refused_repo):
    result = run_script(ORCHESTRATOR, 'inbox', 'detect', '--source-id', _POINTER, cwd=refused_repo.main)

    payload = parse_toon(result.stdout)
    assert (payload['status'], payload['orchestrated'], payload['epic']) == ('success', True, _SLUG)
    assert not refused_repo.expected_worktree.exists()
