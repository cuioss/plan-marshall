#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``manage-status``' read-verb sibling-worktree resolution (D10).

Under ADR-002 a phase-5+ plan's directory MOVES into its own worktree, so it is
absent from every other checkout by design. ``require_status`` answered that
absence with a bare ``file_not_found``, a refusal structurally incapable of
returning presence for such a plan — and reading it as "the plan is dead"
destroyed live coordination state.

The fix has two halves, and both are pinned here:

* the READ verbs consult ``git-workflow locate-plan-checkout`` on a local miss and
  adopt the holding checkout's document, publishing WHICH checkout answered;
* the refusal, when no reachable checkout holds the plan, carries an explicit
  discriminator saying whether the look substantiates absence at all.

⛔ The fallback is read-only. ``require_status`` also gates the WRITE verbs, and
they commit through a LOCALLY resolved path, so a write that resolved a sibling
plan would write the document into the wrong tree. ``TestWriteVerbsKeepTheStrictGate``
reddens if that gate is removed.

**What is real and what is stubbed.** The git repository, the linked worktree, the
moved-in plan directory and every status read are REAL: the tests build the
production layout with ``git worktree add`` and point the resolver at the main
checkout's base, so the read genuinely runs from a different tree than the one
holding the plan. Only ``_run_locator`` — the process hop into ``git-workflow`` —
is stubbed, at its own named seam, standing in for that verb's documented
``{location, worktree_path}`` contract.
"""

from __future__ import annotations

import json
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest
from marketplace_paths import WORKTREES_DIRNAME
from toon_parser import parse_toon

from conftest import load_script_module, parse_ns

status_query = load_script_module(
    'plan-marshall', 'manage-status', '_status_query.py', '_status_query_sibling_worktree_under_test'
)
# ``_status_query``'s module body ran its ``from _status_core import ...`` above,
# which cached the core module under its own name. That instance — not a second
# ``load_script_module`` alias — is the one the query verbs actually call into, so
# it is the one a stub has to be attached to.
status_core = sys.modules['_status_core']

PLAN_ID = 'sibling-worktree-plan'


# =============================================================================
# Fixture helpers — a real repo with a real linked worktree
# =============================================================================


def _init_repo(repo: Path) -> None:
    """Initialise a fixture git repo in the canonical plan-marshall layout."""
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Test'], check=True)
    (repo / 'README.md').write_text('x\n', encoding='utf-8')
    plan_dir = repo / '.plan'
    plan_dir.mkdir(exist_ok=True)
    (plan_dir / 'marshal.json').write_text('{"system": {}, "plan": {}}\n', encoding='utf-8')
    (repo / '.gitignore').write_text('.plan/local\n.plan/execute-script.py\n', encoding='utf-8')
    subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(repo), 'commit', '-q', '-m', 'init'], check=True)
    (plan_dir / 'local' / 'plans').mkdir(parents=True, exist_ok=True)


def _status_document(current_phase: str = '5-execute') -> dict[str, object]:
    return {
        'title': 'A plan that moved into its worktree',
        'current_phase': current_phase,
        'phases': [
            {'name': '1-init', 'status': 'done'},
            {'name': '5-execute', 'status': 'in_progress'},
        ],
        'metadata': {'use_worktree': True},
        'created': '2026-01-01T00:00:00Z',
        'updated': '2026-01-01T00:00:00Z',
    }


def _add_linked_worktree(repo: Path, base: Path, plan_id: str) -> Path:
    """Create a REAL linked worktree at the canonical slot and move a plan into it.

    The slot is composed from the resolved base plus the shared
    :data:`WORKTREES_DIRNAME` segment — the same join ``worktree-create``
    materializes — so the fixture reproduces the production layout rather than an
    approximation of it. It is deliberately built from ``base`` (always under
    ``tmp_path``) rather than from whatever ``get_worktree_root()`` returns, so a
    resolver that failed to honour the override could never make a test write
    outside its own temporary tree; the precondition assertion in
    :func:`_assert_worktree_root_honours_override` is what checks the two agree.
    """
    worktree_root = base / WORKTREES_DIRNAME
    worktree_root.mkdir(parents=True, exist_ok=True)
    target = worktree_root / plan_id
    subprocess.run(
        ['git', '-C', str(repo), 'worktree', 'add', '-q', '-b', f'feature/{plan_id}', str(target)],
        check=True,
    )
    moved_in = target / '.plan' / 'local' / 'plans' / plan_id
    moved_in.mkdir(parents=True, exist_ok=True)
    (moved_in / 'status.json').write_text(json.dumps(_status_document()), encoding='utf-8')
    return target


def _assert_worktree_root_honours_override(base: Path) -> None:
    """Pin the layout the fixture was built against to the one the code resolves."""
    assert status_core.get_worktree_root() == base / WORKTREES_DIRNAME


@pytest.fixture
def main_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A real repo whose ``.plan/local`` is the resolved base. Returns that base."""
    repo = tmp_path / 'main'
    _init_repo(repo)
    base = repo / '.plan' / 'local'
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return base


def _ns(*argv: str) -> Namespace:
    """A namespace built by the production parser, so every default is the real one."""
    namespace: Namespace = parse_ns('plan-marshall', 'manage-status', 'manage-status.py', *argv, register=False)
    return namespace


def _stub_locator(monkeypatch: pytest.MonkeyPatch, lookup) -> list[str]:
    """Replace the process hop with ``lookup``; return the list of plan ids it saw."""
    seen: list[str] = []

    def fake(plan_id: str):
        seen.append(plan_id)
        return lookup

    monkeypatch.setattr(status_core, '_run_locator', fake)
    return seen


# =============================================================================
# A non-object ``metadata`` field is an input, not a crash
#
# status.json is on-disk and operator-editable, so ``"metadata": null`` is a
# reachable input rather than a hypothetical. Neither of the two guards that
# stood here keys on the VALUE: ``.get('metadata', {})`` applies its default only
# when the KEY IS ABSENT, and ``'metadata' not in status`` is satisfied by an
# explicit null — so both fell through to an AttributeError on None.
# =============================================================================


def _write_local_plan(base: Path, plan_id: str, metadata: object) -> Path:
    """Write a local plan document whose ``metadata`` field is ``metadata`` verbatim.

    Verbatim is the point: the fixture must be able to place a JSON ``null`` (and
    a non-object scalar) where every other fixture in this file places a dict.
    """
    plan_dir = base / 'plans' / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    document = _status_document('2-refine')
    document['metadata'] = metadata
    (plan_dir / 'status.json').write_text(json.dumps(document), encoding='utf-8')
    return plan_dir / 'status.json'
