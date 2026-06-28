#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process behavioral tests for bootstrap_plugin.py detection logic.

The existing bootstrap_plugin suite covers state I/O and a couple of subprocess
smokes. This module exercises the remaining detection surface in-process —
runtime-target reading, Claude/OpenCode plugin-root detection, the cache/detect
flow in ``get_plugin_root``, the resolve helper, and the command handlers plus
``main()`` dispatch — so those branches are covered. Plugin-root probing is
driven with monkeypatched ``Path.home`` / tmp directory layouts so no real
plugin cache is consulted, and state writes are redirected into ``tmp_path``.
"""

import argparse
from pathlib import Path

import pytest

from conftest import load_script_module

bp = load_script_module(
    'plan-marshall', 'marshall-steward', 'bootstrap_plugin.py', 'bootstrap_plugin_behavior_cov'
)


@pytest.fixture
def bp_env(tmp_path, monkeypatch):
    """Redirect bootstrap state resolution into an isolated tmp directory."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setenv('PLAN_DIR_NAME', '.plan')
    import file_ops  # type: ignore[import-not-found]

    monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
    return tmp_path


# =============================================================================
# read_runtime_target
# =============================================================================


def test_read_runtime_target_defaults_to_claude_when_absent(tmp_path: Path):
    """read_runtime_target falls back to 'claude' when no marshal.json is found."""
    assert bp.read_runtime_target(cwd=str(tmp_path)) == 'claude'


def test_read_runtime_target_reads_configured_target(tmp_path: Path):
    """read_runtime_target returns the configured runtime.target value."""
    plan = tmp_path / '.plan'
    plan.mkdir()
    (plan / 'marshal.json').write_text('{"runtime": {"target": "opencode"}}')

    assert bp.read_runtime_target(cwd=str(tmp_path)) == 'opencode'


def test_read_runtime_target_claude_when_runtime_not_dict(tmp_path: Path):
    """read_runtime_target returns 'claude' when runtime is not a mapping."""
    plan = tmp_path / '.plan'
    plan.mkdir()
    (plan / 'marshal.json').write_text('{"runtime": "nope"}')

    assert bp.read_runtime_target(cwd=str(tmp_path)) == 'claude'


def test_read_runtime_target_claude_when_unparseable(tmp_path: Path):
    """read_runtime_target returns 'claude' for a malformed marshal.json."""
    plan = tmp_path / '.plan'
    plan.mkdir()
    (plan / 'marshal.json').write_text('{broken')

    assert bp.read_runtime_target(cwd=str(tmp_path)) == 'claude'


# =============================================================================
# _detect_claude_root
# =============================================================================


def test_detect_claude_root_none_when_cache_absent(tmp_path: Path, monkeypatch):
    """_detect_claude_root returns None when the plugin cache does not exist."""
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)

    assert bp._detect_claude_root() is None


def test_detect_claude_root_finds_marker(tmp_path: Path, monkeypatch):
    """_detect_claude_root returns the plugin dir holding a bundle marker file."""
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    version_dir = (
        tmp_path / '.claude' / 'plugins' / 'cache' / 'plan-marshall' / 'plan-marshall' / '1.0.0'
    )
    marker = version_dir / '.claude-plugin'
    marker.mkdir(parents=True)
    (marker / 'plugin.json').write_text('{}')

    root = bp._detect_claude_root()

    assert root is not None
    assert root.name == 'plan-marshall'


def test_detect_claude_root_none_without_marker(tmp_path: Path, monkeypatch):
    """_detect_claude_root returns None when no bundle carries the marker file."""
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    (tmp_path / '.claude' / 'plugins' / 'cache' / 'plan-marshall' / 'bundle' / '1.0.0').mkdir(
        parents=True
    )

    assert bp._detect_claude_root() is None


# =============================================================================
# _detect_opencode_root
# =============================================================================


def test_detect_opencode_root_via_env_config(tmp_path: Path, monkeypatch):
    """_detect_opencode_root finds a plan-marshall skill under OPENCODE_CONFIG_DIR."""
    monkeypatch.setattr(Path, 'home', lambda: tmp_path / 'empty-home')
    cfg = tmp_path / 'cfg'
    skills = cfg / 'skills'
    (skills / 'plan-marshall-core').mkdir(parents=True)
    monkeypatch.setenv('OPENCODE_CONFIG_DIR', str(cfg))

    root = bp._detect_opencode_root()

    assert root is not None
    assert root == skills.resolve()


def test_detect_opencode_root_via_relative_root(tmp_path: Path, monkeypatch):
    """_detect_opencode_root finds a plan-marshall skill under .opencode/skills."""
    monkeypatch.setattr(Path, 'home', lambda: tmp_path / 'empty-home')
    monkeypatch.delenv('OPENCODE_CONFIG_DIR', raising=False)
    work = tmp_path / 'work'
    (work / '.opencode' / 'skills' / 'plan-marshall-x').mkdir(parents=True)
    monkeypatch.chdir(work)

    root = bp._detect_opencode_root()

    assert root is not None
    assert root.name == 'skills'


def test_detect_opencode_root_none_when_no_skills(tmp_path: Path, monkeypatch):
    """_detect_opencode_root returns None when no discovery root carries a skill."""
    monkeypatch.setattr(Path, 'home', lambda: tmp_path / 'empty-home')
    monkeypatch.delenv('OPENCODE_CONFIG_DIR', raising=False)
    empty = tmp_path / 'empty-work'
    empty.mkdir()
    monkeypatch.chdir(empty)

    assert bp._detect_opencode_root() is None


# =============================================================================
# detect_plugin_root dispatch
# =============================================================================


def test_detect_plugin_root_routes_to_opencode(monkeypatch):
    """detect_plugin_root delegates to the OpenCode resolver for that target."""
    sentinel = Path('/fake/opencode')
    monkeypatch.setattr(bp, '_detect_opencode_root', lambda: sentinel)

    assert bp.detect_plugin_root(target='opencode') == sentinel


def test_detect_plugin_root_routes_to_claude(monkeypatch):
    """detect_plugin_root delegates to the Claude resolver for that target."""
    sentinel = Path('/fake/claude')
    monkeypatch.setattr(bp, '_detect_claude_root', lambda: sentinel)

    assert bp.detect_plugin_root(target='claude') == sentinel


def test_detect_plugin_root_auto_reads_runtime_target(monkeypatch):
    """detect_plugin_root resolves the target from marshal.json when omitted."""
    monkeypatch.setattr(bp, 'read_runtime_target', lambda: 'claude')
    sentinel = Path('/fake/auto')
    monkeypatch.setattr(bp, '_detect_claude_root', lambda: sentinel)

    assert bp.detect_plugin_root() == sentinel


# =============================================================================
# get_plugin_root
# =============================================================================


def test_get_plugin_root_returns_cached(bp_env, tmp_path):
    """get_plugin_root returns a still-existing cached root with source 'cached'."""
    cached = tmp_path / 'cached-root'
    cached.mkdir()
    bp.write_state({'plugin_root': str(cached)})

    root, source = bp.get_plugin_root(target='claude')

    assert root == cached
    assert source == 'cached'


def test_get_plugin_root_redetects_when_cache_stale(bp_env, tmp_path, monkeypatch):
    """get_plugin_root re-detects when the cached path no longer exists."""
    bp.write_state({'plugin_root': str(tmp_path / 'gone')})
    fresh = tmp_path / 'fresh'
    fresh.mkdir()
    monkeypatch.setattr(bp, 'detect_plugin_root', lambda target=None: fresh)

    root, source = bp.get_plugin_root(target='claude')

    assert root == fresh
    assert source == 'detected'


def test_get_plugin_root_detected_persists_state(bp_env, tmp_path, monkeypatch):
    """get_plugin_root caches a freshly detected root into the state file."""
    fresh = tmp_path / 'detected'
    fresh.mkdir()
    monkeypatch.setattr(bp, 'detect_plugin_root', lambda target=None: fresh)

    root, source = bp.get_plugin_root(refresh=True, target='claude')

    assert root == fresh
    assert source == 'detected'
    assert bp.read_state()['plugin_root'] == str(fresh)


def test_get_plugin_root_not_found(bp_env, monkeypatch):
    """get_plugin_root reports 'not_found' when detection yields nothing."""
    monkeypatch.setattr(bp, 'detect_plugin_root', lambda target=None: None)

    root, source = bp.get_plugin_root(refresh=True, target='claude')

    assert root is None
    assert source == 'not_found'


# =============================================================================
# resolve_bundle_path (extra branch)
# =============================================================================


def test_resolve_bundle_path_none_when_subpath_missing(tmp_path: Path):
    """resolve_bundle_path returns None when the bundle exists but the subpath does not."""
    root = tmp_path / 'cache'
    (root / 'plan-marshall' / '1.0.0').mkdir(parents=True)

    assert bp.resolve_bundle_path(root, 'plan-marshall', 'skills/missing/SKILL.md') is None


# =============================================================================
# cmd_get_root / cmd_resolve
# =============================================================================


def test_cmd_get_root_success(monkeypatch):
    """cmd_get_root returns a success envelope with the resolved plugin root."""
    monkeypatch.setattr(bp, 'get_plugin_root', lambda refresh, target: (Path('/p'), 'detected'))

    result = bp.cmd_get_root(argparse.Namespace(refresh=False, target='claude'))

    assert result['status'] == 'success'
    assert result['plugin_root'] == '/p'
    assert result['target'] == 'claude'


def test_cmd_get_root_error_claude_hint(monkeypatch):
    """cmd_get_root returns an error with the Claude-specific hint when not found."""
    monkeypatch.setattr(bp, 'get_plugin_root', lambda refresh, target: (None, 'not_found'))

    result = bp.cmd_get_root(argparse.Namespace(refresh=False, target='claude'))

    assert result['status'] == 'error'
    assert 'Claude Code' in result['hint']


def test_cmd_get_root_error_opencode_hint(monkeypatch):
    """cmd_get_root returns the OpenCode-specific hint when not found for that target."""
    monkeypatch.setattr(bp, 'get_plugin_root', lambda refresh, target: (None, 'not_found'))

    result = bp.cmd_get_root(argparse.Namespace(refresh=False, target='opencode'))

    assert result['status'] == 'error'
    assert 'OpenCode' in result['hint']


def test_cmd_resolve_plugin_not_found(monkeypatch):
    """cmd_resolve errors when the plugin root cannot be resolved."""
    monkeypatch.setattr(bp, 'get_plugin_root', lambda: (None, 'not_found'))

    result = bp.cmd_resolve(argparse.Namespace(bundle='b', path='p'))

    assert result['status'] == 'error'
    assert result['error'] == 'Plugin root not found'


def test_cmd_resolve_success(tmp_path: Path, monkeypatch):
    """cmd_resolve returns the resolved path for an existing bundle subpath."""
    root = tmp_path / 'cache'
    target = root / 'plan-marshall' / '1.0.0' / 'skills' / 's' / 'SKILL.md'
    target.parent.mkdir(parents=True)
    target.write_text('# skill')
    monkeypatch.setattr(bp, 'get_plugin_root', lambda: (root, 'cached'))

    result = bp.cmd_resolve(argparse.Namespace(bundle='plan-marshall', path='skills/s/SKILL.md'))

    assert result['status'] == 'success'
    assert result['resolved_path'] == str(target)


def test_cmd_resolve_path_not_found(tmp_path: Path, monkeypatch):
    """cmd_resolve errors when the bundle resolves but the subpath is absent."""
    root = tmp_path / 'cache'
    (root / 'plan-marshall' / '1.0.0').mkdir(parents=True)
    monkeypatch.setattr(bp, 'get_plugin_root', lambda: (root, 'cached'))

    result = bp.cmd_resolve(argparse.Namespace(bundle='plan-marshall', path='skills/x/SKILL.md'))

    assert result['status'] == 'error'
    assert 'Path not found' in result['error']


# =============================================================================
# main() dispatch (safe_main wraps with sys.exit)
# =============================================================================


def test_main_get_root_dispatch(monkeypatch, capsys):
    """main() routes 'get-root' and emits the resolved root as TOON."""
    monkeypatch.setattr(bp, 'get_plugin_root', lambda refresh, target: (Path('/root'), 'detected'))
    monkeypatch.setattr(bp, 'read_runtime_target', lambda *a, **k: 'claude')
    monkeypatch.setattr('sys.argv', ['bootstrap_plugin', 'get-root'])

    with pytest.raises(SystemExit) as exc:
        bp.main()

    assert exc.value.code in (0, None)
    assert 'plugin_root' in capsys.readouterr().out


def test_main_resolve_dispatch(tmp_path: Path, monkeypatch, capsys):
    """main() routes 'resolve' and emits the resolved path as TOON."""
    root = tmp_path / 'cache'
    target = root / 'plan-marshall' / '1.0.0' / 'skills' / 's' / 'SKILL.md'
    target.parent.mkdir(parents=True)
    target.write_text('# skill')
    monkeypatch.setattr(bp, 'get_plugin_root', lambda: (root, 'cached'))
    monkeypatch.setattr(
        'sys.argv',
        ['bootstrap_plugin', 'resolve', '--bundle', 'plan-marshall', '--path', 'skills/s/SKILL.md'],
    )

    with pytest.raises(SystemExit) as exc:
        bp.main()

    assert exc.value.code in (0, None)
    assert 'resolved_path' in capsys.readouterr().out
