#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A writer that recorded NOTHING about the tree is the legacy shape the gate admits.

The ``kind=build`` tree-identity pair (``worktree_root`` /
``worktree_sha_at_dispatch``) is read by PRESENCE, not by null-ness:

* an ABSENT key means the writer never recorded the fact — exactly what every
  row written before the pair existed carries — so the row matches on its
  completion hash, as the gate has always matched;
* a PRESENT ``null`` means the writer TRIED and could not establish the fact,
  which is the one case where a mid-build rewrite would be invisible, so the gate
  refuses it.

Two production writers know nothing about the tree: the payload-less
``manage-change-ledger append --kind build`` CLI and the routing seam's
auxiliary row. Their rows must therefore carry neither key. The cases here drive
the CLI's REAL ``append`` verb over a real git repository and then put that row
in front of the REAL gate, because the pairing is the point: a writer that omits
the keys and a reader that refuses an absent key would each look right alone, and
the push gate would halt with a remedy that only writes another refused row.
"""

from __future__ import annotations

import json
import subprocess
from argparse import Namespace
from pathlib import Path

import pytest

# The two autouse fixtures are imported for their side effect: importing a
# fixture function into this module's namespace is what makes it available HERE,
# and both are declared autouse so every case below gets them.
from _pre_commit_verify_freshness_fixtures import (
    _build_is_necessary,
    _expected_notations_resolve,
    _freshness_mod,
)

from conftest import get_script_path, run_script

#: The notation the appended row reports; it is one the cross-check's pinned
#: resolver set contains, so no case here trips the attribution refusal.
_NOTATION = 'plan-marshall:build-pyproject:pyproject_build'

_PLAN_ID = 'lb-149-unrecorded-tree-row'

_APPEND_SCRIPT = get_script_path('plan-marshall', 'manage-change-ledger', 'manage-change-ledger.py')


def _git(repo: Path, *args: str) -> None:
    """Run a git command in ``repo``, raising on failure."""
    subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True)


def _init_repo(repo: Path) -> Path:
    """Initialise a real git repo with one committed file."""
    repo.mkdir(parents=True)
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    _git(repo, 'config', 'user.email', 't@t.test')
    _git(repo, 'config', 'user.name', 'Test')
    (repo / 'tracked.py').write_text('value = 1\n', encoding='utf-8')
    _git(repo, 'add', '.')
    _git(repo, 'commit', '-q', '-m', 'init')
    return repo


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """The tree the CLI computes its currency hash in."""
    return _init_repo(tmp_path / 'project')


def _append_build_row(repo: Path, tmp_path: Path) -> Path:
    """Append one successful build row through the CLI's real ``append`` verb.

    The ledger is routed under an isolated ``PLAN_BASE_DIR`` so the row lands in
    ``<base>/work/change-ledger.jsonl`` instead of the checkout's own ledger.
    """
    base = tmp_path / 'ledger-base'
    base.mkdir()
    result = run_script(
        _APPEND_SCRIPT,
        'append',
        '--kind',
        'build',
        '--notation',
        _NOTATION,
        '--exit-code',
        '0',
        '--status',
        'success',
        '--plan-id',
        _PLAN_ID,
        cwd=str(repo),
        env_overrides={'PLAN_BASE_DIR': str(base)},
    )
    assert result.returncode == 0, result.stderr
    return base / 'work' / 'change-ledger.jsonl'


def _read_row(ledger: Path) -> dict:
    lines = [line for line in ledger.read_text(encoding='utf-8').splitlines() if line.strip()]
    assert len(lines) == 1, lines
    row = json.loads(lines[0])
    assert isinstance(row, dict), row
    return row


class _PlanContext:
    """The one field the gate reads off the plan context."""

    def __init__(self, worktree_path: Path) -> None:
        self.worktree_path = str(worktree_path)


def test_the_cli_row_records_neither_tree_key(repo, tmp_path) -> None:
    """The payload-less writer states nothing about a tree it never saw.

    An omitted key is the legacy shape; a present ``null`` would be read as a
    failed capture and refused, and the CLI has no capture to fail.
    """
    row = _read_row(_append_build_row(repo, tmp_path))

    assert 'worktree_root' not in row
    assert 'worktree_sha_at_dispatch' not in row
    assert row['worktree_sha'], 'the completion hash the gate matches on is still recorded'


def test_the_cli_row_is_not_recorded_with_a_raw_dot_root(repo, tmp_path) -> None:
    """``.`` is never a recorded root: it names no tree a reader could compare."""
    row = _read_row(_append_build_row(repo, tmp_path))

    assert row.get('worktree_root') != '.'
    assert 'worktree_root' not in row


def test_the_gate_reads_a_cli_appended_row_as_fresh(repo, tmp_path, monkeypatch) -> None:
    """The row the CLI writes is credited by the gate, not refused as unreadable.

    Driven end to end: the CLI computes and stores the currency hash, and the
    gate recomputes it over the same tree and reads the row. A writer that
    stamped ``null`` here halted the push gate permanently, because the documented
    remedy — re-dispatch the build — produced another refused row.
    """
    ledger = _append_build_row(repo, tmp_path)
    monkeypatch.setattr(_freshness_mod, 'resolve_plan_context', lambda _plan_id, ensure=False: _PlanContext(repo))
    monkeypatch.setattr(_freshness_mod, 'resolve_ledger_path', lambda: ledger)
    # What the change requires is a separate question with its own suite; pinning
    # it leaves this case depending only on the row's tree-identity shape.
    monkeypatch.setattr(_freshness_mod, '_resolve_required_coverage', lambda _plan_id: (None, 'unused_in_this_case'))

    verdict = _freshness_mod.cmd_pre_commit_verify_freshness(Namespace(plan_id=_PLAN_ID))

    assert verdict['status'] == 'fresh', verdict
    assert Path(verdict['worktree_root']).resolve() == repo.resolve()
    assert verdict['matched_notation'] == _NOTATION
