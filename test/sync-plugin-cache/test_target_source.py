#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the project-local list_bundles_and_versions.py helper.

After cluster 02 the helper's default --source-root is
``{cwd}/target/claude`` (was ``{cwd}/marketplace/bundles`` in the
pre-cluster-02 version). The bundle/version table is populated from
``target/claude/{bundle}/.claude-plugin/plugin.json``.

The script lives at
``.claude/skills/sync-plugin-cache/scripts/list_bundles_and_versions.py``
(project-local).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from conftest import PROJECT_ROOT
from toon_parser import parse_toon

_HELPER = (
    PROJECT_ROOT
    / '.claude'
    / 'skills'
    / 'sync-plugin-cache'
    / 'scripts'
    / 'list_bundles_and_versions.py'
)


def _write(path: Path, content: str | bytes = '') -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding='utf-8')


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_HELPER), *args],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=cwd,
    )


def test_default_source_root_is_target_claude(tmp_path: Path):
    """Default cwd-relative scan reads from target/claude/, not marketplace/bundles/."""
    cwd = tmp_path / 'project'
    target = cwd / 'target' / 'claude'
    plugin_doc = json.dumps({'name': 'demo', 'version': '0.7.0'}, indent=2) + '\n'
    _write(target / 'demo' / '.claude-plugin' / 'plugin.json', plugin_doc)
    # Also create a marketplace/bundles/ that should be IGNORED by the new default
    _write(
        cwd / 'marketplace' / 'bundles' / 'should-not-be-listed' / '.claude-plugin' / 'plugin.json',
        '{"name": "should-not-be-listed", "version": "9.9.9"}\n',
    )

    result = _run(cwd=cwd)
    assert result.returncode == 0, result.stderr
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'

    bundles = data.get('bundles', [])
    names = [b['name'] for b in bundles]
    assert names == ['demo'], f'expected only target/claude/ contents, got {names}'
    assert bundles[0]['version'] == '0.7.0'


def test_explicit_source_root_overrides_default(tmp_path: Path):
    custom = tmp_path / 'custom-target'
    plugin_doc = json.dumps({'name': 'alpha', 'version': '1.2.3'}, indent=2) + '\n'
    _write(custom / 'alpha' / '.claude-plugin' / 'plugin.json', plugin_doc)

    result = _run('--source-root', str(custom))
    assert result.returncode == 0
    data = parse_toon(result.stdout)
    bundles = data.get('bundles', [])
    assert [b['name'] for b in bundles] == ['alpha']
    assert bundles[0]['version'] == '1.2.3'


def test_directory_without_plugin_json_is_not_treated_as_bundle(tmp_path: Path):
    # A directory under target/claude/ without ``.claude-plugin/plugin.json``
    # is NOT a bundle — most notably the top-level ``.claude-plugin/``
    # directory that holds the marketplace.json registration manifest, plus
    # any stray non-bundle directory that may accumulate on the filesystem.
    target = tmp_path / 'target' / 'claude'
    _write(target / 'noplugin' / 'README.md', '# no plugin\n')
    _write(target / '.claude-plugin' / 'marketplace.json', '{}\n')
    _write(target / 'real-bundle' / '.claude-plugin' / 'plugin.json', '{"version": "1.0.0"}\n')

    result = _run('--source-root', str(target))
    assert result.returncode == 0
    data = parse_toon(result.stdout)
    bundles = data.get('bundles', [])
    names = [b['name'] for b in bundles]
    assert 'noplugin' not in names
    assert '.claude-plugin' not in names
    assert 'real-bundle' in names


def test_malformed_plugin_json_yields_unknown(tmp_path: Path):
    target = tmp_path / 'target' / 'claude'
    _write(target / 'bad' / '.claude-plugin' / 'plugin.json', 'not json {{{')

    result = _run('--source-root', str(target))
    assert result.returncode == 0
    data = parse_toon(result.stdout)
    bundles = data.get('bundles', [])
    assert any(b['name'] == 'bad' and b['version'] == 'unknown' for b in bundles)
