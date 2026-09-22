#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared isolation helpers for tools-permission-fix tests.

Hoisted from ``test_permission_fix.py`` and ``test_permission_fix_behavior.py``
statement-for-statement (carve 2, mirroring carve 1 ``_providers_fixtures.py``).
Test modules import these instead of redefining them, so the over-budget
modules split into ``test_*`` collection units without losing a single
assertion.
"""

import ast
import json
from pathlib import Path

import pytest


def write_settings(path, allow):
    """Write a minimal settings.json with the given allow list."""
    path.write_text(json.dumps({'permissions': {'allow': allow, 'deny': [], 'ask': []}}))


def read_allow(path):
    """Read back the allow list from a settings file."""
    return json.loads(path.read_text())['permissions']['allow']


def create_marketplace(tmp_path, bundles: dict[str, dict]) -> str:
    """Create a marketplace directory structure for testing.

    Args:
        tmp_path: Pytest tmp_path fixture
        bundles: dict of bundle_name -> {skills: [...], commands: [...]}

    Returns:
        Path to marketplace directory.
    """
    marketplace_dir = tmp_path / 'marketplace'
    plugin_dir = marketplace_dir / '.claude-plugin'
    plugin_dir.mkdir(parents=True)

    plugins = []
    for name, data in bundles.items():
        bundle_dir = marketplace_dir / 'bundles' / name
        bundle_plugin_dir = bundle_dir / '.claude-plugin'
        bundle_plugin_dir.mkdir(parents=True)

        plugin_json = {
            'name': name,
            'skills': data.get('skills', []),
            'commands': data.get('commands', []),
        }
        (bundle_plugin_dir / 'plugin.json').write_text(json.dumps(plugin_json))
        plugins.append({'name': name, 'source': f'./bundles/{name}'})

    marketplace_json = {'plugins': plugins}
    (plugin_dir / 'marketplace.json').write_text(json.dumps(marketplace_json))
    return str(marketplace_dir)


def write_marshal(tmp_path, phase_steps: dict[str, list[str]]) -> str:
    """Write a minimal marshal.json with the given phase steps."""
    marshal = {'plan': {phase: {'steps': steps} for phase, steps in phase_steps.items()}}
    marshal_file = tmp_path / 'marshal.json'
    marshal_file.write_text(json.dumps(marshal))
    return str(marshal_file)


def write_settings_str(tmp_path, allow: list[str]) -> str:
    """Write settings.json under tmp_path and return its path as string."""
    settings = {'permissions': {'allow': allow, 'deny': [], 'ask': []}}
    settings_file = tmp_path / 'settings.json'
    settings_file.write_text(json.dumps(settings))
    return str(settings_file)


def read_settings(path: str) -> dict:
    """Read a settings JSON file into a dict."""
    with open(path) as f:
        data: dict = json.load(f)
        return data


RETIRED_DEFAULT = 'Write(.plan/**)'


def seed_retired(path: Path) -> bytes:
    """Write a settings file carrying the retired rule; return its bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'permissions': {'allow': [RETIRED_DEFAULT], 'deny': [], 'ask': []}}))
    return path.read_bytes()


def allow_list(path: Path) -> list[str]:
    """Read the allow list from a settings file."""
    allow: list[str] = json.loads(path.read_text())['permissions']['allow']
    return allow


def build_project(tmp_path, monkeypatch, *, local: bool):
    """Build a project tree with a shared settings file and optionally a local one."""
    claude = tmp_path / '.claude'
    claude.mkdir(parents=True, exist_ok=True)
    write_settings(claude / 'settings.json', [])
    if local:
        write_settings(claude / 'settings.local.json', [])
    monkeypatch.chdir(tmp_path)
    return claude


def dual_file_project(tmp_path, monkeypatch):
    """A project where BOTH settings files exist, so the preference is observable."""
    claude = tmp_path / '.claude'
    claude.mkdir(parents=True, exist_ok=True)
    write_settings(claude / 'settings.json', [])
    write_settings(claude / 'settings.local.json', [])
    monkeypatch.chdir(tmp_path)
    return claude / 'settings.local.json'


def setup_project(tmp_path, allow):
    """Create tmp_path/.claude/settings.json and return its path."""
    claude_dir = tmp_path / '.claude'
    claude_dir.mkdir()
    settings_file = claude_dir / 'settings.json'
    write_settings(settings_file, allow)
    return settings_file


@pytest.fixture()
def in_tmp_cwd(tmp_path, monkeypatch):
    """Run with the process working directory inside an isolated tmp_path."""
    monkeypatch.chdir(tmp_path)


def force_opencode(monkeypatch):
    """Point the runtime-resolution seam at the OpenCode runtime."""
    import permission_common
    from opencode_runtime import OpenCodeRuntime

    monkeypatch.setattr(permission_common, '_runtime_for_target', lambda: OpenCodeRuntime())


def force_unsupported_runtime(monkeypatch):
    """Point the runtime-resolution seam at a runtime without permission support."""
    from unittest.mock import MagicMock

    import permission_common

    mock_rt = MagicMock()
    monkeypatch.setattr(permission_common, '_runtime_for_target', lambda: mock_rt)


def assert_declines(result):
    """Assert a non-Claude target returns a no-op without Claude DSL output."""
    assert result.get('status') == 'no-op'
    assert 'reason' in result
    # No Claude permission-DSL output may be produced.
    serialized = str(result)
    assert 'Bash(' not in serialized
    assert 'Skill(' not in serialized
    assert 'SlashCommand(' not in serialized


def seam_callers(source: str, seam: str) -> set[str]:
    """Names of the functions in ``source`` whose body calls ``seam`` by name.

    The seam's own definition is excluded, so a future recursive call cannot
    make the helper report itself as one of its own callers.
    """
    callers = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.FunctionDef) or node.name == seam:
            continue
        for inner in ast.walk(node):
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == seam:
                callers.add(node.name)
                break
    return callers


def roster_handlers(source: str, class_name: str) -> set[str]:
    """Names of the ``pf.cmd_*`` handlers driven inside ``class_name``."""
    covered = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for inner in ast.walk(node):
            func = inner.func if isinstance(inner, ast.Call) else None
            if (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == 'pf'
                and func.attr.startswith('cmd_')
            ):
                covered.add(func.attr)
    return covered
