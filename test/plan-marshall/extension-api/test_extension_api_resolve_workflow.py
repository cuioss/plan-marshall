#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``extension_api resolve-workflow``.

The verb gives a dispatched leaf ONE resolution path for a workflow notation:
the worktree's own ``marketplace/bundles`` copy when it exists, otherwise the
installed copy through the shared bundle-cache resolver. A consumer repository
has no ``marketplace/bundles`` tree, so the installed leg is the one that serves
it; a bundle-owning checkout resolves to the code the worktree actually carries.
"""

from __future__ import annotations

from pathlib import Path

import extension_api

from conftest import get_script_path, run_script


def _write(path: Path, text: str = 'body\n') -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


# =============================================================================
# Resolution order
# =============================================================================


def test_worktree_copy_wins_when_it_exists(tmp_path: Path) -> None:
    worktree = tmp_path / 'checkout'
    worktree_file = _write(worktree / 'marketplace' / 'bundles' / 'b' / 'skills' / 's' / 'workflow' / 'x.md')
    installed = tmp_path / 'cache'
    _write(installed / 'b' / '0.1.1' / 'skills' / 's' / 'workflow' / 'x.md')

    result = extension_api.resolve_workflow('b:s/workflow/x.md', str(worktree), cache_roots=(str(installed),))

    assert result['status'] == 'success'
    assert result['source'] == 'worktree'
    assert result['path'] == str(worktree_file.resolve())


def test_installed_copy_serves_a_consumer_repository(tmp_path: Path) -> None:
    worktree = tmp_path / 'consumer'
    worktree.mkdir()
    installed = tmp_path / 'cache'
    installed_file = _write(installed / 'b' / '0.1.7' / 'skills' / 's' / 'workflow' / 'x.md')

    result = extension_api.resolve_workflow('b:s/workflow/x.md', str(worktree), cache_roots=(str(installed),))

    assert result['status'] == 'success'
    assert result['source'] == 'installed'
    assert result['path'] == str(installed_file.resolve())


def test_newest_eligible_version_directory_wins(tmp_path: Path) -> None:
    worktree = tmp_path / 'consumer'
    worktree.mkdir()
    installed = tmp_path / 'cache'
    _write(installed / 'b' / '0.1.9' / 'skills' / 's' / 'workflow' / 'x.md')
    newest = _write(installed / 'b' / '0.1.10' / 'skills' / 's' / 'workflow' / 'x.md')
    # An older version that does NOT carry the file is never a candidate.
    (installed / 'b' / '0.1.11' / 'skills' / 's').mkdir(parents=True)

    result = extension_api.resolve_workflow('b:s/workflow/x.md', str(worktree), cache_roots=(str(installed),))

    assert result['status'] == 'success'
    assert result['path'] == str(newest.resolve())


def test_flat_layout_root_resolves(tmp_path: Path) -> None:
    worktree = tmp_path / 'consumer'
    worktree.mkdir()
    flat_root = tmp_path / 'flat'
    flat_file = _write(flat_root / 'skills' / 'b-s' / 'standards' / 'n.md')

    result = extension_api.resolve_workflow('b:s/standards/n.md', str(worktree), cache_roots=(str(flat_root),))

    assert result['status'] == 'success'
    assert result['source'] == 'installed'
    assert result['path'] == str(flat_file.resolve())


def test_skill_md_form_resolves(tmp_path: Path) -> None:
    worktree = tmp_path / 'checkout'
    skill_md = _write(worktree / 'marketplace' / 'bundles' / 'b' / 'skills' / 's' / 'SKILL.md')

    result = extension_api.resolve_workflow('b:s/SKILL.md', str(worktree))

    assert result['status'] == 'success'
    assert result['source'] == 'worktree'
    assert result['path'] == str(skill_md.resolve())


def test_not_found_names_both_probes(tmp_path: Path) -> None:
    worktree = tmp_path / 'consumer'
    worktree.mkdir()
    installed = tmp_path / 'cache'
    (installed / 'b' / '0.1.1' / 'skills' / 's').mkdir(parents=True)

    result = extension_api.resolve_workflow('b:s/workflow/x.md', str(worktree), cache_roots=(str(installed),))

    assert result['status'] == 'error'
    assert result['error'] == 'workflow_not_found'
    assert result['worktree_probe'].endswith('marketplace/bundles/b/skills/s/workflow/x.md')
    assert result['installed_probes']
    assert result['probed'][0] == result['worktree_probe']
    assert result['probed'][1] == result['installed_probes'][0]


def test_malformed_notation_is_not_found(tmp_path: Path) -> None:
    for notation in ('b:s', 'b:s/no-suffix', 'b:s/../x.md', '/abs:s/x.md', 'b:/x.md'):
        result = extension_api.resolve_workflow(notation, str(tmp_path))
        assert result['status'] == 'error', notation
        assert result['error'] == 'workflow_not_found', notation


# =============================================================================
# CLI surface
# =============================================================================


def test_cli_resolves_a_worktree_document(tmp_path: Path) -> None:
    worktree = tmp_path / 'checkout'
    worktree_file = _write(worktree / 'marketplace' / 'bundles' / 'b' / 'skills' / 's' / 'workflow' / 'x.md')

    result = run_script(
        get_script_path('plan-marshall', 'extension-api', 'extension_api.py'),
        'resolve-workflow',
        '--notation',
        'b:s/workflow/x.md',
        '--worktree',
        str(worktree),
    )

    assert result.success, result.stderr
    assert 'status: success' in result.stdout
    assert f'path: {worktree_file.resolve()}' in result.stdout
    assert 'source: worktree' in result.stdout


def test_cli_reports_workflow_not_found(tmp_path: Path) -> None:
    result = run_script(
        get_script_path('plan-marshall', 'extension-api', 'extension_api.py'),
        'resolve-workflow',
        '--notation',
        'b:s/workflow/missing.md',
        '--worktree',
        str(tmp_path),
    )

    assert result.success, result.stderr
    assert 'error: workflow_not_found' in result.stdout
    assert 'worktree_probe:' in result.stdout
