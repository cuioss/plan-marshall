#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for antigravity_runtime.py — Google Antigravity implementation of Runtime ABC."""

import json
from pathlib import Path
from typing import Any

import pytest
from antigravity_runtime import AntigravityRuntime
from platform_runtime import _make_runtime
from toon_parser import parse_toon


@pytest.fixture()
def runtime() -> AntigravityRuntime:
    """Return a fresh AntigravityRuntime instance."""
    return AntigravityRuntime()


def _parse(toon_str: str) -> dict:
    """Parse a TOON string and assert it is a dict."""
    result = parse_toon(toon_str)
    assert isinstance(result, dict), f'parse_toon returned non-dict: {toon_str!r}'
    return result


# =============================================================================
# Registration & Runtime Info
# =============================================================================


def test_make_runtime_antigravity():
    """_make_runtime('antigravity') returns an AntigravityRuntime instance."""
    rt = _make_runtime('antigravity')
    assert isinstance(rt, AntigravityRuntime)


def test_runtime_info(runtime: AntigravityRuntime):
    """runtime_info reports antigravity harness."""
    info = _parse(runtime.runtime_info())
    assert info['status'] == 'success'
    assert info['harness'] == 'antigravity'


def test_harness_bash_timeout_ceiling(runtime: AntigravityRuntime):
    """Antigravity enforces a 600-second bash ceiling."""
    res = _parse(runtime.harness_bash_timeout_ceiling())
    assert res['ceiling_seconds'] == 600


# =============================================================================
# Layout Operations
# =============================================================================


def test_layout_skill_roots(runtime: AntigravityRuntime):
    """layout_skill_roots returns project-local skill roots for Antigravity."""
    result = _parse(runtime.layout_skill_roots())
    assert result['status'] == 'success'
    roots = result['roots']
    assert '.agents/skills' in roots
    assert '.agents/plugins/plan-marshall/skills' in roots


def test_layout_bundle_cache_root(runtime: AntigravityRuntime):
    """layout_bundle_cache_root returns global Antigravity plugin skill roots."""
    result = _parse(runtime.layout_bundle_cache_root())
    assert result['status'] == 'success'
    roots = result['roots']
    assert any('.gemini/config/plugins/plan-marshall/skills' in r for r in roots)


# =============================================================================
# Project Initial Setup
# =============================================================================


def test_project_initial_setup(runtime: AntigravityRuntime, tmp_path: Path):
    """project_initial_setup creates .plan/ and initializes marshal.json with antigravity target."""
    result = _parse(runtime.project_initial_setup(str(tmp_path), 'antigravity'))
    assert result['status'] == 'success'
    assert result['target'] == 'antigravity'
    assert result['marshal_written'] is True

    marshal_file = tmp_path / '.plan' / 'marshal.json'
    assert marshal_file.is_file()
    data = json.loads(marshal_file.read_text(encoding='utf-8'))
    assert data['runtime']['target'] == 'antigravity'
    assert (tmp_path / '.plan' / 'temp').is_dir()


def test_project_initial_setup_preserves_existing_marshal(runtime: AntigravityRuntime, tmp_path: Path):
    """project_initial_setup merges into existing marshal.json."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir(parents=True)
    marshal_file = plan_dir / 'marshal.json'
    marshal_file.write_text(json.dumps({'custom_key': 'custom_value'}), encoding='utf-8')

    result = _parse(runtime.project_initial_setup(str(tmp_path), 'antigravity'))
    assert result['status'] == 'success'

    data = json.loads(marshal_file.read_text(encoding='utf-8'))
    assert data['custom_key'] == 'custom_value'
    assert data['runtime']['target'] == 'antigravity'


def test_project_install_hook(runtime: AntigravityRuntime, monkeypatch, tmp_path: Path):
    """project_install_hook creates .agents/hooks.json in project dir."""
    monkeypatch.chdir(tmp_path)
    result = _parse(runtime.project_install_hook('antigravity'))
    assert result['status'] == 'success'
    assert result['installed'] is True
    assert (tmp_path / '.agents' / 'hooks.json').is_file()

    # Second invocation notes already exists
    result2 = _parse(runtime.project_install_hook('antigravity'))
    assert result2['status'] == 'success'
    assert result2['installed'] is False


# =============================================================================
# Permission Settings Paths & Resolution
# =============================================================================


def test_permission_settings_path_global(runtime: AntigravityRuntime, monkeypatch, tmp_path: Path):
    """Global permission settings resolve to <gemini_config>/config.json."""
    gemini_cfg = tmp_path / 'gemini' / 'config'
    monkeypatch.setenv('GEMINI_CONFIG_DIR', str(gemini_cfg))

    path = runtime.permission_settings_path('global')
    assert path == str(gemini_cfg / 'config.json')


def test_permission_settings_path_invalid_scope(runtime: AntigravityRuntime):
    """Invalid scope raises ValueError."""
    with pytest.raises(ValueError, match='Unsupported scope'):
        runtime.permission_settings_path('invalid_scope')


def test_permission_settings_path_project_finds_existing(runtime: AntigravityRuntime, monkeypatch, tmp_path: Path):
    """permission_settings_path('project') matches project by folderUri."""
    gemini_cfg = tmp_path / 'gemini' / 'config'
    projects_dir = gemini_cfg / 'projects'
    projects_dir.mkdir(parents=True)
    monkeypatch.setenv('GEMINI_CONFIG_DIR', str(gemini_cfg))

    project_dir = tmp_path / 'my_project'
    project_dir.mkdir()

    proj_file = projects_dir / 'proj-123.json'
    proj_content = {
        'projectResources': {'resources': [{'gitFolder': {'folderUri': f'file://{project_dir.resolve()}'}}]},
        'permissionGrants': {'permissionGrants': {'allow': ['command(echo hello)']}},
    }
    proj_file.write_text(json.dumps(proj_content), encoding='utf-8')

    found_path = runtime.permission_settings_path('project', write=False, project_dir=str(project_dir))
    assert found_path == str(proj_file)


def test_permission_settings_path_project_creates_when_writing(
    runtime: AntigravityRuntime, monkeypatch, tmp_path: Path
):
    """permission_settings_path('project') creates new project file when write=True and none exists."""
    gemini_cfg = tmp_path / 'gemini' / 'config'
    monkeypatch.setenv('GEMINI_CONFIG_DIR', str(gemini_cfg))

    project_dir = tmp_path / 'new_project'
    project_dir.mkdir()

    created_path = runtime.permission_settings_path('project', write=True, project_dir=str(project_dir))
    created_file = Path(created_path)
    assert created_file.is_file()
    assert created_file.parent == gemini_cfg / 'projects'

    data = json.loads(created_file.read_text(encoding='utf-8'))
    resources = data.get('projectResources', {}).get('resources', [])
    assert any(r.get('gitFolder', {}).get('folderUri') == f'file://{project_dir.resolve()}' for r in resources)


# =============================================================================
# Permission Load / Save / Defaults
# =============================================================================


def test_permission_load_and_save_settings(runtime: AntigravityRuntime, tmp_path: Path):
    """permission_load_settings and permission_save_settings work with Antigravity JSON."""
    settings_file = tmp_path / 'settings.json'
    settings_data = {'userSettings': {'globalPermissionGrants': {'allow': ['command(test)']}}}

    runtime.permission_save_settings(str(settings_file), settings_data)
    assert settings_file.is_file()

    loaded = runtime.permission_load_settings(str(settings_file))
    assert loaded == settings_data


def test_permission_ensure_defaults(runtime: AntigravityRuntime, tmp_path: Path):
    """permission_ensure_defaults ensures command(python3 .plan/execute-script.py) and command(./pw)."""
    project_file = tmp_path / 'project.json'
    initial_data: dict[str, Any] = {'permissionGrants': {'permissionGrants': {'allow': ['read_file(**)']}}}
    project_file.write_text(json.dumps(initial_data), encoding='utf-8')

    result = runtime.permission_ensure_defaults(initial_data, str(project_file), dry_run=False)
    assert result['defaults_added_count'] == 4
    assert 'command(python3 .plan/execute-script.py)' in result['defaults_added']
    assert 'command(./pw)' in result['defaults_added']
    assert result['applied'] is True

    # Verify saved content
    saved_data = json.loads(project_file.read_text(encoding='utf-8'))
    allows = saved_data['permissionGrants']['permissionGrants']['allow']
    assert 'command(python3 .plan/execute-script.py)' in allows
    assert 'command(./pw)' in allows

    # Second run is idempotent (0 added)
    result2 = runtime.permission_ensure_defaults(saved_data, str(project_file), dry_run=False)
    assert result2['defaults_added_count'] == 0
    assert result2['applied'] is False


def test_permission_ensure_defaults_dry_run(runtime: AntigravityRuntime, tmp_path: Path):
    """permission_ensure_defaults dry run does not modify settings file."""
    project_file = tmp_path / 'project.json'
    initial_data: dict[str, Any] = {'permissionGrants': {'permissionGrants': {'allow': []}}}
    project_file.write_text(json.dumps(initial_data), encoding='utf-8')

    result = runtime.permission_ensure_defaults(initial_data, str(project_file), dry_run=True)
    assert result['defaults_added_count'] == 4
    assert result['applied'] is False

    saved_data = json.loads(project_file.read_text(encoding='utf-8'))
    assert saved_data['permissionGrants']['permissionGrants']['allow'] == []


# =============================================================================
# Subagent Dispatch & Metrics
# =============================================================================


def test_subagent_dispatch(runtime: AntigravityRuntime, tmp_path: Path):
    """subagent_dispatch returns invoke_subagent tool invocation."""
    prompt_file = tmp_path / 'prompt.md'
    prompt_file.write_text('Execute task for {plan_id}', encoding='utf-8')

    result = _parse(
        runtime.subagent_dispatch(
            'execution-context-level-3',
            str(prompt_file),
            {'plan_id': 'test-plan'},
        )
    )
    assert result['status'] == 'success'
    assert result['invocation']['tool'] == 'invoke_subagent'
    assert 'test-plan' in result['invocation']['prompt']


def test_metrics_capture(runtime: AntigravityRuntime):
    """metrics_capture captures total_tokens if supplied, else no-op."""
    res_tokens = _parse(runtime.metrics_capture('my-plan', 'phase-1-init', total_tokens=1500))
    assert res_tokens['status'] == 'success'
    assert res_tokens['tokens_captured'] == 1500

    res_noop = _parse(runtime.metrics_capture('my-plan', 'phase-1-init', total_tokens=None))
    assert res_noop['status'] == 'no-op'


# =============================================================================
# Health Check
# =============================================================================


def test_health_check(runtime: AntigravityRuntime, monkeypatch, tmp_path: Path):
    """health_check runs permissions, display, and mcp-diagnostics checks."""
    gemini_cfg = tmp_path / 'gemini' / 'config'
    gemini_cfg.mkdir(parents=True)
    (gemini_cfg / 'config.json').write_text('{}', encoding='utf-8')
    monkeypatch.setenv('GEMINI_CONFIG_DIR', str(gemini_cfg))

    result = _parse(runtime.health_check('permissions'))
    assert result['target'] == 'antigravity'
    assert result['status'] in ('healthy', 'warning')


# =============================================================================
# Permission Fix & Ensure Wildcards
# =============================================================================


def test_permission_fix_add_and_remove(
    runtime: AntigravityRuntime, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """permission_fix add and remove manipulate the permissions.allow list."""
    monkeypatch.chdir(tmp_path)
    res_add = _parse(runtime.permission_fix('project', 'ensure', ['python3 custom.py *'], False))
    assert res_add['status'] == 'success'
    assert res_add['operation'] == 'permission fix'
    assert res_add['added'] == 1

    res_rem = _parse(runtime.permission_fix('project', 'remove', ['python3 custom.py *'], False))
    assert res_rem['status'] == 'success'
    assert res_rem['removed'] == 1


def test_permission_fix_consolidate(
    runtime: AntigravityRuntime, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """permission_fix consolidate deduplicates grants in Antigravity."""
    monkeypatch.chdir(tmp_path)
    result = _parse(runtime.permission_fix('project', 'consolidate', [], False))
    assert result['status'] == 'success'
    assert result['operation'] == 'permission fix'


def test_permission_fix_protect_path_noop(runtime: AntigravityRuntime) -> None:
    """permission_fix protect-path returns honest no-op since Antigravity has no deny list."""
    result = _parse(runtime.permission_fix('project', 'protect-path', ['/tmp/creds'], False))
    assert result['status'] == 'no-op'
    assert result['operation'] == 'permission fix'
    assert 'Antigravity' in result['reason']


def test_permission_fix_invalid_scope(runtime: AntigravityRuntime) -> None:
    """permission_fix with invalid scope returns error."""
    result = _parse(runtime.permission_fix('invalid', 'ensure', [], False))
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_scope'


def test_permission_fix_invalid_operation(runtime: AntigravityRuntime) -> None:
    """permission_fix with invalid operation returns error."""
    result = _parse(runtime.permission_fix('project', 'invalid-op', [], False))
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_operation'


def test_permission_ensure_wildcards(
    runtime: AntigravityRuntime, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """permission_ensure_wildcards ensures default commands in Antigravity."""
    monkeypatch.chdir(tmp_path)
    result = _parse(runtime.permission_ensure_wildcards('project', 'marketplace/', False))
    assert result['status'] == 'success'
    assert result['operation'] == 'permission ensure-wildcards'
