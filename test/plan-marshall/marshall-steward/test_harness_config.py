#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit test suite for local harness configuration (REQ-STEW-1..4).

Tests active harness verification via determine_mode.py check-harness / mode,
deterministic local harness state writing via configure_harness.py, schema validation
(strictly no timestamps), multi-harness coexistence, staleness detection, and
worktree inheritance via resolve_main_anchored_path.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

from conftest import load_script_module

dm = load_script_module('plan-marshall', 'marshall-steward', 'determine_mode.py', 'determine_mode_harness_cov')
ch = load_script_module('plan-marshall', 'marshall-steward', 'configure_harness.py', 'configure_harness_cov')


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def plan_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Set up an isolated project environment with .plan/local and override PLAN_BASE_DIR."""
    project_dir = tmp_path / 'project'
    project_dir.mkdir(parents=True, exist_ok=True)
    plan_dir = project_dir / '.plan'
    plan_local = plan_dir / 'local'
    plan_local.mkdir(parents=True, exist_ok=True)

    # Put a mock executor in place
    executor = plan_dir / 'execute-script.py'
    executor.write_text('#!/usr/bin/env python3\nprint("mock executor")\n')

    # Put a mock marshal.json in place
    (plan_dir / 'marshal.json').write_text(json.dumps({'schema_version': 1, 'project': {}}))

    # Mock harness paths so check_harness_paths_valid succeeds for tests
    (project_dir / 'marketplace' / 'bundles').mkdir(parents=True, exist_ok=True)
    (project_dir / 'CLAUDE.md').write_text('# Claude config\n')
    (project_dir / 'AGENTS.md').write_text('# Agents config\n')

    # Anchor resolve_main_anchored_path via PLAN_BASE_DIR
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_local))

    return {
        'project_dir': project_dir,
        'plan_dir': plan_dir,
        'plan_local': plan_local,
        'executor': executor,
    }


# =============================================================================
# REQ-STEW-1 & REQ-STEW-2: check_harness & configure_harness behavior
# =============================================================================


def test_check_harness_missing_config(plan_env):
    """check_harness reports unconfigured when .plan/local/harness/{harness}.json is missing."""
    plan_dir = plan_env['plan_dir']
    project_dir = plan_env['project_dir']

    res = dm.check_harness(harness_override='claude', plan_dir=plan_dir, project_dir=project_dir)

    assert res['status'] == 'success'
    assert res['harness'] == 'claude'
    assert res['configured'] is False
    assert res['reason'] == 'harness_config_missing'
    assert res['action_required'] == 'configure_harness'
    assert 'harness/claude.json' in res['config_path']


def test_configure_harness_writes_valid_schema_no_timestamps(plan_env):
    """configure_harness creates valid schema with strictly no timestamps."""
    plan_dir = plan_env['plan_dir']
    project_dir = plan_env['project_dir']

    res = ch.configure_harness(
        harness_override='antigravity',
        auto_sandbox_elevation=True,
        plan_dir=plan_dir,
        project_dir=project_dir,
    )

    assert res['status'] == 'success'
    assert res['harness'] == 'antigravity'
    assert res['configured'] is True
    assert 'config_path' in res
    assert 'dist_manifest_sha' in res

    config_path = Path(res['config_path'])
    assert config_path.is_file()

    content = config_path.read_text(encoding='utf-8')
    data = json.loads(content)

    # Schema assertions
    assert data['schema_version'] == 1
    assert data['harness'] == 'antigravity'
    assert data['target_source'] == 'explicit'
    assert isinstance(data['dist_manifest_sha'], str)
    assert len(data['dist_manifest_sha']) == 64  # SHA-256 hex string

    checks = data['checks']
    assert isinstance(checks, dict)
    assert checks['rules_emitted'] is True
    assert checks['harness_paths_valid'] is True
    assert checks['executor_ready'] is True

    settings = data['settings']
    assert isinstance(settings, dict)
    assert settings['auto_sandbox_elevation'] is True

    # Strictly no timestamps requirement (REQ-STEW-2)
    # Check for keys or patterns like time, date, timestamp, created_at, updated_at, ISO 8601
    forbidden_keys = {'time', 'date', 'timestamp', 'created_at', 'updated_at', 'created', 'updated'}
    all_keys = set(data.keys()) | set(checks.keys()) | set(settings.keys())
    assert not (all_keys & forbidden_keys), f'Forbidden timestamp keys found: {all_keys & forbidden_keys}'

    # Verify no ISO-8601 timestamp string in JSON
    iso_timestamp_pattern = re.compile(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}')
    assert not iso_timestamp_pattern.search(content), f'ISO timestamp found in config: {content}'

    # Post-condition: check_harness must report configured
    check_res = dm.check_harness(harness_override='antigravity', plan_dir=plan_dir, project_dir=project_dir)
    assert check_res['status'] == 'success'
    assert check_res['configured'] is True
    assert check_res['reason'] == 'configured'
    assert check_res['dist_manifest_sha'] == data['dist_manifest_sha']


def test_check_harness_invalid_schema_or_corrupt_json(plan_env):
    """check_harness reports harness_config_invalid when file is malformed or invalid schema."""
    plan_dir = plan_env['plan_dir']
    project_dir = plan_env['project_dir']

    config_path = dm.resolve_harness_config_path('claude')
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Corrupt JSON
    config_path.write_text('{invalid-json')
    res = dm.check_harness(harness_override='claude', plan_dir=plan_dir, project_dir=project_dir)
    assert res['configured'] is False
    assert res['reason'] == 'harness_config_invalid'

    # 2. Missing schema_version or wrong harness
    config_path.write_text(json.dumps({'schema_version': 2, 'harness': 'claude'}))
    res = dm.check_harness(harness_override='claude', plan_dir=plan_dir, project_dir=project_dir)
    assert res['configured'] is False
    assert res['reason'] == 'harness_config_invalid'


def test_check_harness_missing_executor_check(plan_env):
    """check_harness reports executor_missing when executor_ready is False or file absent."""
    plan_dir = plan_env['plan_dir']
    project_dir = plan_env['project_dir']

    ch.configure_harness(harness_override='claude', plan_dir=plan_dir, project_dir=project_dir)

    # Remove executor
    plan_env['executor'].unlink()

    res = dm.check_harness(harness_override='claude', plan_dir=plan_dir, project_dir=project_dir)
    assert res['configured'] is False
    assert res['reason'] == 'executor_missing'


def test_check_harness_invalid_paths(plan_env, monkeypatch: pytest.MonkeyPatch):
    """check_harness reports harness_paths_invalid when paths check fails."""
    plan_dir = plan_env['plan_dir']
    project_dir = plan_env['project_dir']

    ch.configure_harness(harness_override='claude', plan_dir=plan_dir, project_dir=project_dir)

    # Mock check_harness_paths_valid to return False
    monkeypatch.setattr(dm, 'check_harness_paths_valid', lambda harness, proj=None: False)

    res = dm.check_harness(harness_override='claude', plan_dir=plan_dir, project_dir=project_dir)
    assert res['configured'] is False
    assert res['reason'] == 'harness_paths_invalid'


def test_check_harness_staleness_and_refresh(plan_env):
    """check_harness detects stale manifest and configure_harness refreshes it."""
    plan_dir = plan_env['plan_dir']
    project_dir = plan_env['project_dir']

    # Configure initially
    ch.configure_harness(harness_override='opencode', plan_dir=plan_dir, project_dir=project_dir)

    config_path = dm.resolve_harness_config_path('opencode')
    data = json.loads(config_path.read_text(encoding='utf-8'))

    # Mutate dist_manifest_sha to simulate stale bundle/executor
    data['dist_manifest_sha'] = '0000000000000000000000000000000000000000000000000000000000000000'
    config_path.write_text(json.dumps(data, indent=2))

    # Check detects staleness
    res = dm.check_harness(harness_override='opencode', plan_dir=plan_dir, project_dir=project_dir)
    assert res['configured'] is False
    assert res['reason'] == 'harness_config_stale'
    assert res['action_required'] == 'configure_harness'

    # Re-running configure_harness refreshes state
    refresh_res = ch.configure_harness(harness_override='opencode', plan_dir=plan_dir, project_dir=project_dir)
    assert refresh_res['configured'] is True

    # Now check is valid again
    post_res = dm.check_harness(harness_override='opencode', plan_dir=plan_dir, project_dir=project_dir)
    assert post_res['configured'] is True
    assert post_res['reason'] == 'configured'


def test_multi_harness_coexistence(plan_env, monkeypatch: pytest.MonkeyPatch):
    """Multiple harnesses can be configured and coexist under .plan/local/harness/ without collision."""
    plan_dir = plan_env['plan_dir']
    project_dir = plan_env['project_dir']

    # Configure claude
    ch.configure_harness(harness_override='claude', plan_dir=plan_dir, project_dir=project_dir)
    # Configure antigravity
    ch.configure_harness(harness_override='antigravity', plan_dir=plan_dir, project_dir=project_dir)
    # Configure opencode
    ch.configure_harness(harness_override='opencode', plan_dir=plan_dir, project_dir=project_dir)

    harness_dir = plan_env['plan_local'] / 'harness'
    assert (harness_dir / 'claude.json').is_file()
    assert (harness_dir / 'antigravity.json').is_file()
    assert (harness_dir / 'opencode.json').is_file()

    # Verify each independently
    res_c = dm.check_harness(harness_override='claude', plan_dir=plan_dir, project_dir=project_dir)
    assert res_c['configured'] is True
    assert res_c['harness'] == 'claude'

    res_a = dm.check_harness(harness_override='antigravity', plan_dir=plan_dir, project_dir=project_dir)
    assert res_a['configured'] is True
    assert res_a['harness'] == 'antigravity'

    res_o = dm.check_harness(harness_override='opencode', plan_dir=plan_dir, project_dir=project_dir)
    assert res_o['configured'] is True
    assert res_o['harness'] == 'opencode'

    # Environment variable resolution test
    monkeypatch.setenv('ANTIGRAVITY_AGENT', '1')
    res_env = dm.check_harness(plan_dir=plan_dir, project_dir=project_dir)
    assert res_env['harness'] == 'antigravity'
    assert res_env['target_source'] == 'env'
    assert res_env['configured'] is True


def test_determine_mode_includes_harness_fields(plan_env):
    """determine_mode includes harness, target_source, harness_configured, and harness_reason."""
    plan_dir = plan_env['plan_dir']
    project_dir = plan_env['project_dir']

    # Before configure
    res = dm.determine_mode(plan_dir)
    assert res['status'] == 'success'
    assert res['mode'] == 'menu'
    assert 'harness' in res
    assert 'target_source' in res
    assert res['harness_configured'] is False
    assert res['harness_reason'] == 'harness_config_missing'

    # After configure
    ch.configure_harness(harness_override=res['harness'], plan_dir=plan_dir, project_dir=project_dir)

    res_configured = dm.determine_mode(plan_dir)
    assert res_configured['harness_configured'] is True
    assert res_configured['harness_reason'] == 'configured'


def test_worktree_inheritance_via_resolve_main_anchored_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A simulated worktree reads the main checkout's harness state via resolve_main_anchored_path."""
    main_plan_local = tmp_path / 'main' / '.plan' / 'local'
    main_plan_local.mkdir(parents=True, exist_ok=True)

    # Set base dir override to main's plan_local
    monkeypatch.setenv('PLAN_BASE_DIR', str(main_plan_local))

    # Configure harness on main
    main_project = tmp_path / 'main'
    main_plan = tmp_path / 'main' / '.plan'
    (main_plan / 'execute-script.py').write_text('# executor')
    (main_project / 'marketplace' / 'bundles').mkdir(parents=True, exist_ok=True)
    (main_project / 'CLAUDE.md').write_text('# claude')

    ch.configure_harness(harness_override='claude', plan_dir=main_plan, project_dir=main_project)
    assert (main_plan_local / 'harness' / 'claude.json').is_file()

    # Now simulate a worktree: worktree has its own plan_dir with executor, but no harness/ directory
    worktree_project = tmp_path / 'worktree'
    worktree_plan = worktree_project / '.plan'
    worktree_plan.mkdir(parents=True, exist_ok=True)
    (worktree_plan / 'execute-script.py').write_text('# executor')
    (worktree_project / 'marketplace' / 'bundles').mkdir(parents=True, exist_ok=True)
    (worktree_project / 'CLAUDE.md').write_text('# claude')

    # Because PLAN_BASE_DIR anchors to main_plan_local, check_harness from worktree
    # will resolve to main's harness config!
    wt_res = dm.check_harness(harness_override='claude', plan_dir=worktree_plan, project_dir=worktree_project)
    assert wt_res['configured'] is True, f'Unexpected check_harness result: {wt_res}'
    assert wt_res['reason'] == 'configured'
    assert wt_res['config_path'] == str(main_plan_local / 'harness' / 'claude.json')


def test_cli_dispatch_check_harness(plan_env, monkeypatch: pytest.MonkeyPatch, capsys):
    """determine_mode.py CLI routes check-harness and outputs TOON."""
    plan_dir = plan_env['plan_dir']
    monkeypatch.setattr(
        sys,
        'argv',
        ['determine_mode', 'check-harness', '--harness', 'claude', '--plan-dir', str(plan_dir)],
    )

    rc = dm.main()
    assert rc == 0
    out = capsys.readouterr().out
    assert 'status: success' in out
    assert 'harness: claude' in out
    assert 'configured: false' in out
    assert 'reason: harness_config_missing' in out


def test_cli_dispatch_configure_harness(plan_env, monkeypatch: pytest.MonkeyPatch, capsys):
    """configure_harness.py CLI runs deterministic setup and outputs TOON."""
    plan_dir = plan_env['plan_dir']
    project_dir = plan_env['project_dir']
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'configure_harness',
            '--harness',
            'antigravity',
            '--auto-sandbox-elevation',
            '--plan-dir',
            str(plan_dir),
            '--project-dir',
            str(project_dir),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        ch.main()
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert 'status: success' in out
    assert 'harness: antigravity' in out
    assert 'configured: true' in out
