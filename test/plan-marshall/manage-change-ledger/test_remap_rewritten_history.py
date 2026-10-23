#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2

"""Tests for mapping rewritten commits back onto the append-only change-ledger.

A history rewrite (rebase, amend, cherry-pick) gives every replayed commit a new
SHA. The ledger is keyed by ``commit_sha`` and is pure-append, so every earlier
``kind=change`` row stops matching the branch and the 5-execute boundary reports
the whole branch unrecorded. The ``remap`` verb maps the rows of rewritten
commits onto their rewritten counterparts and APPENDS the mapped rows, leaving
the original rows in place.

Coverage:

* a rebased three-commit feature branch is remapped by patch-id, the 5-execute
  end-marker boundary no longer reports the branch unrecorded, and the ledger
  still holds the original rows;
* a message-only amend maps the same way (its patch is unchanged);
* a content-changing amend is reported unmapped — its patch changed, so it needs
  the explicit append path rather than a guessed mapping;
* an explicit old-to-new map (the map the rewriting step emits) is consumed and
  remapped;
* a second remap of the same rewrite is a no-op, so repeated invocations cannot
  grow the ledger with duplicate rows.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from conftest import get_script_path, load_script_module, run_script

_SCRIPT = get_script_path('plan-marshall', 'manage-change-ledger', 'manage-change-ledger.py')
_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_lb91_lifecycle')


def _git(repo: Path, *args: str) -> str:
    """Run one git command in ``repo`` and return its stripped stdout."""
    proc = subprocess.run(
        ['git', '-C', str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def _commit(repo: Path, path: str, content: str, message: str) -> str:
    """Write ``path``, commit it, and return the new commit SHA."""
    (repo / path).write_text(content, encoding='utf-8')
    _git(repo, 'add', path)
    _git(repo, 'commit', '-q', '-m', message)
    return _git(repo, 'rev-parse', 'HEAD')


class RewriteEnv:
    """A real git repo with a three-commit feature branch plus an isolated ledger."""

    def __init__(self, repo: Path, base: Path, shas: list[str], base_sha: str) -> None:
        self.repo = repo
        self.base = base
        self.shas = shas
        self.base_sha = base_sha
        self.overrides = {'PLAN_BASE_DIR': str(base)}
        self.ledger_path = base / 'work' / 'change-ledger.jsonl'

    def run(self, *args: str):
        return run_script(_SCRIPT, *args, cwd=str(self.repo), env_overrides=self.overrides)

    def record_all(self) -> None:
        """Append one ``kind=change`` row per feature-branch commit (git-sourced)."""
        for index, sha in enumerate(self.shas, start=1):
            result = self.run(
                'append',
                '--kind',
                'change',
                '--deliverable-id',
                str(index),
                '--commit-sha',
                sha,
                '--changed-paths',
                f'f{index}.txt',
            )
            assert result.success, result.stderr

    def ledger(self) -> list[dict]:
        return [json.loads(line) for line in self.ledger_path.read_text(encoding='utf-8').splitlines() if line.strip()]

    def change_rows(self) -> list[dict]:
        return [row for row in self.ledger() if row.get('kind') == 'change']

    def advance_main(self) -> None:
        """Land an upstream commit on ``main`` so the feature branch must replay."""
        _git(self.repo, 'checkout', '-q', 'main')
        _commit(self.repo, 'upstream.txt', 'upstream\n', 'upstream work')
        _git(self.repo, 'checkout', '-q', 'feature')

    def rebase_onto_main(self) -> None:
        _git(self.repo, 'rebase', '-q', 'main')


@pytest.fixture
def rewrite_env(tmp_path: Path) -> RewriteEnv:
    repo = tmp_path / 'repo'
    repo.mkdir()
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    _git(repo, 'config', 'user.email', 't@t.test')
    _git(repo, 'config', 'user.name', 'Test')
    base_sha = _commit(repo, 'base.txt', 'base\n', 'base')
    _git(repo, 'checkout', '-q', '-b', 'feature')
    shas = [_commit(repo, f'f{index}.txt', f'{index}\n', f'commit {index}') for index in (1, 2, 3)]
    base = tmp_path / 'base'
    base.mkdir()
    return RewriteEnv(repo=repo, base=base, shas=shas, base_sha=base_sha)


def _boundary_refusal(env: RewriteEnv, monkeypatch, plan_id: str = 'lb91-rewrite-fixture'):
    """Run the real 5-execute end-marker guard against the fixture repo."""
    plan_dir = env.base / 'plans' / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text('{}', encoding='utf-8')
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    monkeypatch.setenv('PLAN_BASE_DIR', str(env.base))
    return _lifecycle._phase_end_marker_refusal(
        plan_id,
        {'metadata': {'use_worktree': True, 'worktree_path': str(env.repo)}},
    )


def test_boundary_refuses_all_three_commits_after_rebase_before_remap(rewrite_env, monkeypatch) -> None:
    """A rebase alone leaves every recorded row mismatched (the hypothesis)."""
    rewrite_env.record_all()
    rewrite_env.advance_main()
    rewrite_env.rebase_onto_main()

    refusal = _boundary_refusal(rewrite_env, monkeypatch)

    assert refusal is not None
    assert refusal['error'] == 'execute_commits_unrecorded'
    assert refusal['unrecorded_count'] == 3
    assert refusal['branch_commit_count'] == 3


def test_rebase_remap_clears_the_boundary_and_keeps_original_rows(rewrite_env, monkeypatch) -> None:
    """Patch-id remap maps all three rewritten rows; the originals stay in place."""
    rewrite_env.record_all()
    rewrite_env.advance_main()
    rewrite_env.rebase_onto_main()
    rebased_shas = _git(rewrite_env.repo, 'rev-list', '--reverse', 'main..HEAD').splitlines()

    result = rewrite_env.run('remap', '--worktree-root', str(rewrite_env.repo))

    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'success'
    assert data['remap_count'] == 3
    assert {row['new_commit_sha'] for row in data['mappings']} == set(rebased_shas)

    # The boundary now sees every rewritten commit as recorded.
    assert _boundary_refusal(rewrite_env, monkeypatch) is None

    # Append-only: the original rows are still there, beside the mapped rows.
    rows = rewrite_env.change_rows()
    assert len(rows) == 6
    original_shas = {row['commit_sha'] for row in rows if 'remapped_from' not in row}
    assert original_shas == set(rewrite_env.shas)
    mapped = [row for row in rows if row.get('remapped_from')]
    assert {row['remapped_from'] for row in mapped} == set(rewrite_env.shas)
    assert {row['commit_sha'] for row in mapped} == set(rebased_shas)


def test_message_only_amend_maps_the_same_way(rewrite_env, monkeypatch) -> None:
    """A message-only amend keeps the patch, so patch-id still recovers it."""
    rewrite_env.record_all()
    head_before = _git(rewrite_env.repo, 'rev-parse', 'HEAD')
    _git(rewrite_env.repo, 'commit', '-q', '--amend', '-m', 'commit 3, reworded')
    amended = _git(rewrite_env.repo, 'rev-parse', 'HEAD')
    assert amended != head_before

    result = rewrite_env.run('remap', '--worktree-root', str(rewrite_env.repo))

    assert result.success, result.stderr
    data = result.toon()
    assert data['remap_count'] == 1
    assert data['mappings'] == [
        {
            'old_commit_sha': rewrite_env.shas[2],
            'new_commit_sha': amended,
        }
    ]
    assert _boundary_refusal(rewrite_env, monkeypatch) is None


def test_content_changing_amend_is_reported_unmapped(rewrite_env) -> None:
    """An amend whose patch changed has no patch-id counterpart — it stays unmapped."""
    rewrite_env.record_all()
    (rewrite_env.repo / 'f3.txt').write_text('3, edited\n', encoding='utf-8')
    _git(rewrite_env.repo, 'add', 'f3.txt')
    _git(rewrite_env.repo, 'commit', '-q', '--amend', '-m', 'commit 3, changed content')

    result = rewrite_env.run('remap', '--worktree-root', str(rewrite_env.repo))

    assert result.success, result.stderr
    data = result.toon()
    assert data['remap_count'] == 0
    assert data['unmapped'] == [rewrite_env.shas[2]]


def test_explicit_map_file_is_consumed(rewrite_env) -> None:
    """The map the rewriting step emits is consumed verbatim via ``--map-file``."""
    rewrite_env.record_all()
    (rewrite_env.repo / 'f3.txt').write_text('3, edited\n', encoding='utf-8')
    _git(rewrite_env.repo, 'add', 'f3.txt')
    _git(rewrite_env.repo, 'commit', '-q', '--amend', '-m', 'commit 3, changed content')
    amended = _git(rewrite_env.repo, 'rev-parse', 'HEAD')
    map_path = rewrite_env.base / 'sha-map.txt'
    map_path.write_text(f'{rewrite_env.shas[2]} {amended}\n', encoding='utf-8')

    result = rewrite_env.run('remap', '--worktree-root', str(rewrite_env.repo), '--map-file', str(map_path))

    assert result.success, result.stderr
    data = result.toon()
    assert data['remap_count'] == 1
    assert data['mappings'] == [{'old_commit_sha': rewrite_env.shas[2], 'new_commit_sha': amended}]


def test_second_remap_appends_nothing(rewrite_env) -> None:
    """A repeated remap of the same rewrite does not duplicate rows."""
    rewrite_env.record_all()
    rewrite_env.advance_main()
    rewrite_env.rebase_onto_main()

    first = rewrite_env.run('remap', '--worktree-root', str(rewrite_env.repo))
    assert first.toon()['remap_count'] == 3
    second = rewrite_env.run('remap', '--worktree-root', str(rewrite_env.repo))

    assert second.success, second.stderr
    assert second.toon()['remap_count'] == 0
    assert len(rewrite_env.change_rows()) == 6


def test_emit_map_dry_run_writes_the_map_without_appending_then_the_map_is_consumed(rewrite_env, monkeypatch) -> None:
    """The rewriting step's emit → consume flow maps the ledger in two passes.

    The first invocation proves the map and the ledger state are separate: it
    writes the map, appends nothing, and the boundary still refuses. The second
    consumes the emitted map and clears the boundary.
    """
    rewrite_env.record_all()
    rewrite_env.advance_main()
    rewrite_env.rebase_onto_main()
    rebased_shas = _git(rewrite_env.repo, 'rev-list', '--reverse', 'main..HEAD').splitlines()
    map_path = rewrite_env.base / 'sync-baseline-sha-map.json'

    emitted = rewrite_env.run(
        'remap',
        '--worktree-root',
        str(rewrite_env.repo),
        '--old-head',
        rewrite_env.shas[2],
        '--emit-map',
        str(map_path),
        '--dry-run',
    )

    assert emitted.success, emitted.stderr
    data = emitted.toon()
    assert data['remap_count'] == 3
    assert data['dry_run'] is True
    assert data['map_file'] == str(map_path)
    assert len(rewrite_env.change_rows()) == 3, 'a dry run must append nothing'
    applied = json.loads(map_path.read_text(encoding='utf-8'))
    assert set(applied) == set(rewrite_env.shas)
    assert set(applied.values()) == set(rebased_shas)
    assert _boundary_refusal(rewrite_env, monkeypatch) is not None, 'nothing was repaired yet'

    consumed = rewrite_env.run('remap', '--worktree-root', str(rewrite_env.repo), '--map-file', str(map_path))

    assert consumed.success, consumed.stderr
    assert consumed.toon()['remap_count'] == 3
    assert _boundary_refusal(rewrite_env, monkeypatch) is None


def test_inline_map_is_consumed(rewrite_env) -> None:
    """The comma-separated ``--map`` form maps an explicit old-to-new pair."""
    rewrite_env.record_all()
    (rewrite_env.repo / 'f3.txt').write_text('3, edited\n', encoding='utf-8')
    _git(rewrite_env.repo, 'add', 'f3.txt')
    _git(rewrite_env.repo, 'commit', '-q', '--amend', '-m', 'commit 3, changed content')
    amended = _git(rewrite_env.repo, 'rev-parse', 'HEAD')

    result = rewrite_env.run(
        'remap',
        '--worktree-root',
        str(rewrite_env.repo),
        '--map',
        f'{rewrite_env.shas[2]}:{amended}',
    )

    assert result.success, result.stderr
    assert result.toon()['remap_count'] == 1


def test_unparseable_map_line_is_refused(rewrite_env) -> None:
    """A typo'd map line fails loud instead of reading as a clean no-op."""
    rewrite_env.record_all()
    map_path = rewrite_env.base / 'broken-map.txt'
    map_path.write_text('not-a-sha-pair\n', encoding='utf-8')

    result = rewrite_env.run('remap', '--worktree-root', str(rewrite_env.repo), '--map-file', str(map_path))

    data = result.toon()
    assert data['status'] == 'error'
    assert data['error_code'] == 'INVALID_INPUT'
    assert len(rewrite_env.change_rows()) == 3, 'a refused map must append nothing'


def test_unresolvable_recorded_row_is_reported_not_dropped(rewrite_env) -> None:
    """A row whose SHA is not in this repository is named, never silently skipped."""
    rewrite_env.record_all()
    ghost = 'f' * 40
    appended = rewrite_env.run(
        'append',
        '--kind',
        'change',
        '--deliverable-id',
        '99',
        '--commit-sha',
        ghost,
        '--changed-paths',
        'ghost.txt',
    )
    assert appended.success, appended.stderr

    result = rewrite_env.run('remap', '--worktree-root', str(rewrite_env.repo))

    assert result.success, result.stderr
    data = result.toon()
    assert data['remap_count'] == 0
    assert ghost in data['unresolved'], f'The unresolvable row must be reported, got {data!r}'


def test_partial_explicit_map_reports_the_rows_it_left_stale(rewrite_env) -> None:
    """An explicit map covering part of the branch is a partial repair, and says so."""
    rewrite_env.record_all()
    rewrite_env.advance_main()
    rewrite_env.rebase_onto_main()
    rebased_shas = _git(rewrite_env.repo, 'rev-list', '--reverse', 'main..HEAD').splitlines()

    result = rewrite_env.run(
        'remap',
        '--worktree-root',
        str(rewrite_env.repo),
        '--map',
        f'{rewrite_env.shas[0]}:{rebased_shas[0]}',
    )

    assert result.success, result.stderr
    data = result.toon()
    assert data['remap_count'] == 1
    assert set(data['unmapped']) == {rewrite_env.shas[1], rewrite_env.shas[2]}, (
        f'The rows the map left stale must be reported, got {data!r}'
    )


def test_explicit_map_key_with_no_recorded_row_is_reported(rewrite_env) -> None:
    """A map key that names no ledger row cannot be a completed repair."""
    rewrite_env.record_all()

    result = rewrite_env.run(
        'remap',
        '--worktree-root',
        str(rewrite_env.repo),
        '--map',
        f'{rewrite_env.base_sha}:{rewrite_env.shas[0]}',
    )

    assert result.success, result.stderr
    data = result.toon()
    assert data['remap_count'] == 0
    assert rewrite_env.base_sha in data['unmapped'], (
        f'A resolvable map key with no ledger row must be reported, got {data!r}'
    )
