#!/usr/bin/env python3
"""Tests for skill-resolution commands in manage-config.

Tests resolve-domain-skills, resolve-workflow-skill-extension, get-skills-by-profile,
list-finalize-steps commands defined in _cmd_skill_resolution.py.

Tier 2 (direct import) tests with 1 subprocess test for CLI plumbing.
"""

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from test_helpers import SCRIPT_PATH, create_marshal_json, create_nested_marshal_json, patch_config_paths

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-config' / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_skill_domains = _load_module('_cmd_skill_domains', '_cmd_skill_domains.py')
_cmd_skill_resolution = _load_module('_cmd_skill_resolution', '_cmd_skill_resolution.py')

cmd_get_skills_by_profile = _cmd_skill_resolution.cmd_get_skills_by_profile
cmd_list_finalize_steps = _cmd_skill_resolution.cmd_list_finalize_steps
cmd_resolve_domain_skills = _cmd_skill_resolution.cmd_resolve_domain_skills
cmd_resolve_workflow_skill_extension = _cmd_skill_resolution.cmd_resolve_workflow_skill_extension

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import PlanContext, run_script  # noqa: E402

# =============================================================================
# resolve-domain-skills Tests (Tier 2)
# =============================================================================


def test_resolve_domain_skills_java_implementation():
    """Test resolve-domain-skills for java + implementation profile."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_domain_skills(Namespace(domain='java', profile='implementation'))

        assert result['status'] == 'success'
        defaults_str = str(result['defaults'])
        assert 'pm-dev-java:java-core' in defaults_str
        optionals_str = str(result['optionals'])
        assert 'pm-dev-java:java-cdi' in optionals_str
        # Should NOT include testing defaults
        assert 'pm-dev-java:junit-core' not in defaults_str


def test_resolve_domain_skills_java_testing():
    """Test resolve-domain-skills for java + module_testing profile."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_domain_skills(Namespace(domain='java', profile='module_testing'))

        assert result['status'] == 'success'
        defaults_str = str(result['defaults'])
        optionals_str = str(result['optionals'])
        assert 'pm-dev-java:java-core' in defaults_str
        assert 'pm-dev-java:junit-core' in defaults_str
        assert 'pm-dev-java:junit-integration' in optionals_str
        # Should NOT include implementation optionals
        assert 'pm-dev-java:java-cdi' not in optionals_str


def test_resolve_domain_skills_javascript_implementation():
    """Test resolve-domain-skills for javascript + implementation profile."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_domain_skills(Namespace(domain='javascript', profile='implementation'))

        assert result['status'] == 'success'
        defaults_str = str(result['defaults'])
        optionals_str = str(result['optionals'])
        assert 'pm-dev-frontend:javascript' in defaults_str
        assert 'pm-dev-frontend:lint-config' in optionals_str


def test_resolve_domain_skills_unknown_domain():
    """Test resolve-domain-skills with unknown domain returns error."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_domain_skills(Namespace(domain='unknown', profile='implementation'))

        assert result['status'] == 'error'
        assert 'unknown' in result['error'].lower()


def test_resolve_domain_skills_unknown_profile():
    """Test resolve-domain-skills with unknown profile returns error."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_domain_skills(Namespace(domain='java', profile='invalid-profile'))

        assert result['status'] == 'error'
        assert 'profile' in result['error'].lower()


def test_resolve_domain_skills_java_quality():
    """Test resolve-domain-skills for java + quality profile (finalize phase)."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_domain_skills(Namespace(domain='java', profile='quality'))

        assert result['status'] == 'success'
        defaults_str = str(result['defaults'])
        assert 'pm-dev-java:java-core' in defaults_str
        assert 'pm-dev-java:javadoc' in defaults_str


# =============================================================================
# resolve-workflow-skill-extension Tests (Tier 2)
# =============================================================================


def test_resolve_workflow_skill_extension_java_outline():
    """Test resolve-workflow-skill-extension returns outline extension for java."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_workflow_skill_extension(Namespace(domain='java', type='outline'))

        assert result['status'] == 'success'
        assert result['extension'] == 'pm-dev-java:ext-outline-java'
        assert result['domain'] == 'java'
        assert result['type'] == 'outline'


def test_resolve_workflow_skill_extension_java_triage():
    """Test resolve-workflow-skill-extension returns triage extension for java."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_workflow_skill_extension(Namespace(domain='java', type='triage'))

        assert result['status'] == 'success'
        assert result['extension'] == 'pm-dev-java:ext-triage-java'


def test_resolve_workflow_skill_extension_javascript_outline():
    """Test resolve-workflow-skill-extension returns outline extension for javascript."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_workflow_skill_extension(Namespace(domain='javascript', type='outline'))

        assert result['status'] == 'success'
        assert result['extension'] == 'pm-dev-frontend:ext-outline-frontend'


def test_resolve_workflow_skill_extension_missing_type():
    """Test resolve-workflow-skill-extension returns null for missing extension type."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_workflow_skill_extension(Namespace(domain='javascript', type='triage'))

        assert result['status'] == 'success'
        assert result['extension'] is None


def test_resolve_workflow_skill_extension_unknown_domain():
    """Test resolve-workflow-skill-extension returns null for unknown domain (not error)."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_workflow_skill_extension(Namespace(domain='unknown', type='outline'))

        assert result['status'] == 'success'
        assert result['extension'] is None


def test_resolve_workflow_skill_extension_plugin_dev():
    """Test resolve-workflow-skill-extension returns extensions for plugin-dev domain."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_workflow_skill_extension(Namespace(
            domain='plan-marshall-plugin-dev', type='outline',
        ))

        assert result['status'] == 'success'
        assert result['extension'] == 'pm-plugin-development:ext-outline-workflow'


# =============================================================================
# get-skills-by-profile Tests (Tier 2)
# =============================================================================


def test_get_skills_by_profile_java():
    """Test get-skills-by-profile loads profile-keyed skills from extension.py."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_get_skills_by_profile(Namespace(domain='java'))

        assert result['status'] == 'success'
        assert 'skills_by_profile' in result
        assert 'implementation' in result['skills_by_profile']
        assert 'module_testing' in result['skills_by_profile']
        # integration_testing should NOT appear as standalone profile for java
        assert 'integration_testing' not in result['skills_by_profile']


def test_get_skills_by_profile_includes_core_skills():
    """Test get-skills-by-profile includes core skills in all profiles."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_get_skills_by_profile(Namespace(domain='java'))

        assert result['status'] == 'success'
        # Core skill should appear in every profile
        for profile_skills in result['skills_by_profile'].values():
            assert 'pm-dev-java:java-core' in profile_skills


def test_get_skills_by_profile_includes_profile_skills():
    """Test get-skills-by-profile includes profile-specific skills."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_get_skills_by_profile(Namespace(domain='java'))

        assert result['status'] == 'success'
        assert 'pm-dev-java:junit-core' in result['skills_by_profile']['module_testing']


def test_get_skills_by_profile_javascript():
    """Test get-skills-by-profile works for javascript domain."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_get_skills_by_profile(Namespace(domain='javascript'))

        assert result['status'] == 'success'
        assert 'skills_by_profile' in result
        all_skills = str(result['skills_by_profile'])
        assert 'pm-dev-frontend:javascript' in all_skills


def test_get_skills_by_profile_unknown_domain():
    """Test get-skills-by-profile returns error for unknown domain."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_get_skills_by_profile(Namespace(domain='unknown'))

        assert result['status'] == 'error'
        assert 'unknown' in result['error'].lower()


def test_get_skills_by_profile_flat_domain_fallback():
    """Test get-skills-by-profile returns core skills for flat structure domain (no bundle)."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_get_skills_by_profile(Namespace(domain='java'))

        assert result['status'] == 'success'
        assert 'skills_by_profile' in result


# =============================================================================
# list-finalize-steps Tests (Tier 2)
# =============================================================================


def test_list_finalize_steps_returns_built_in():
    """Test list-finalize-steps returns built-in steps with default: prefix."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_list_finalize_steps(Namespace())

        assert result['status'] == 'success'
        step_names = [s['name'] for s in result['steps']]
        assert 'default:commit-push' in step_names
        assert 'default:create-pr' in step_names
        assert 'default:record-metrics' in step_names
        assert 'default:archive-plan' in step_names
        assert 'default:branch-cleanup' in step_names


def test_list_finalize_steps_count():
    """Test list-finalize-steps returns correct count for built-in steps."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_list_finalize_steps(Namespace())

        assert result['status'] == 'success'
        assert result['count'] >= 7


def test_list_finalize_steps_discovers_project_skills():
    """Test list-finalize-steps discovers project-local finalize-step-* skills.

    Scans .claude/skills/ relative to cwd, so keep as subprocess.
    """
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        skill_dir = ctx.fixture_dir / '.claude' / 'skills' / 'finalize-step-hello-world'
        skill_dir.mkdir(parents=True)
        (skill_dir / 'SKILL.md').write_text(
            '---\nname: finalize-step-hello-world\ndescription: Hello World\n---\n\n# Hello World\n'
        )

        result = run_script(SCRIPT_PATH, 'list-finalize-steps', cwd=ctx.fixture_dir)

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'project:finalize-step-hello-world' in result.stdout
        assert 'Hello World' in result.stdout


# =============================================================================
# list-finalize-steps ordering tests (lock in sync-plugin-cache head placement)
# =============================================================================


def _run_discovery_in_cwd(cwd: Path) -> list[dict]:
    """Invoke _discover_all_finalize_steps() with cwd switched to the given path.

    The discovery scans ``.claude/skills/`` relative to the process cwd, so tests
    that exercise project-level skill ordering must chdir into an isolated temp
    directory that contains the desired skill layout. The real
    ``cmd_list_finalize_steps`` wraps the discovery; we call the inner helper
    directly to get the raw list without TOON serialization.

    Uses an isolated ``tmp_path`` (rather than the shared PlanContext fixture
    directory) so per-test ``.claude/skills/`` layouts cannot contaminate
    neighboring tests.
    """
    import os

    original_cwd = os.getcwd()
    try:
        os.chdir(cwd)
        return _cmd_skill_resolution._discover_all_finalize_steps()
    finally:
        os.chdir(original_cwd)


def test_list_finalize_steps_without_sync_skill_starts_with_built_ins(tmp_path):
    """Without a sync-plugin-cache project skill, output starts with built-in steps."""
    # tmp_path has no .claude/skills directory -> built-ins come first.
    with patch.object(_cmd_skill_resolution, 'discover_all_extensions', return_value=[]):
        steps = _run_discovery_in_cwd(tmp_path)

    assert len(steps) > 0
    # First entry must be a built-in default: step (not a project:sync-plugin-cache)
    first = steps[0]
    assert first['source'] == 'built-in'
    assert first['name'].startswith('default:')
    # And no project:finalize-step-sync-plugin-cache anywhere in the list
    names = [s['name'] for s in steps]
    assert 'project:finalize-step-sync-plugin-cache' not in names


def test_list_finalize_steps_with_sync_skill_places_it_first(tmp_path):
    """When finalize-step-sync-plugin-cache project skill exists, it is placed first."""
    sync_dir = tmp_path / '.claude' / 'skills' / 'finalize-step-sync-plugin-cache'
    sync_dir.mkdir(parents=True)
    (sync_dir / 'SKILL.md').write_text(
        '---\nname: finalize-step-sync-plugin-cache\ndescription: Sync plugin cache\n---\n\n# Sync\n'
    )

    with patch.object(_cmd_skill_resolution, 'discover_all_extensions', return_value=[]):
        steps = _run_discovery_in_cwd(tmp_path)

    assert len(steps) > 0
    assert steps[0]['name'] == 'project:finalize-step-sync-plugin-cache'
    assert steps[0]['source'] == 'project'


def test_list_finalize_steps_other_project_skills_remain_after_built_ins(tmp_path):
    """sync-plugin-cache is first, then all built-ins, then other project skills."""
    skills_root = tmp_path / '.claude' / 'skills'
    sync_dir = skills_root / 'finalize-step-sync-plugin-cache'
    sync_dir.mkdir(parents=True)
    (sync_dir / 'SKILL.md').write_text(
        '---\nname: finalize-step-sync-plugin-cache\ndescription: Sync plugin cache\n---\n\n# Sync\n'
    )

    other_dir = skills_root / 'finalize-step-zzz-other'
    other_dir.mkdir(parents=True)
    (other_dir / 'SKILL.md').write_text(
        '---\nname: finalize-step-zzz-other\ndescription: Another project finalize step\n---\n\n# Other\n'
    )

    with patch.object(_cmd_skill_resolution, 'discover_all_extensions', return_value=[]):
        steps = _run_discovery_in_cwd(tmp_path)

    names = [s['name'] for s in steps]
    # sync must be at index 0
    assert names[0] == 'project:finalize-step-sync-plugin-cache'

    sync_idx = names.index('project:finalize-step-sync-plugin-cache')
    other_idx = names.index('project:finalize-step-zzz-other')

    # Collect all built-in indices — they must all be after sync and before other
    built_in_indices = [i for i, s in enumerate(steps) if s['source'] == 'built-in']
    assert built_in_indices, 'Expected built-in steps in output'
    assert min(built_in_indices) > sync_idx, 'Built-ins must come after sync skill'
    assert max(built_in_indices) < other_idx, (
        'Built-ins must precede other project skills — other project skills must come last '
        'among project/built-in sources'
    )


def test_list_finalize_steps_extension_steps_come_last(tmp_path):
    """Extension-contributed steps appear after all built-in and project steps."""
    class _FakeExtModule:
        @staticmethod
        def provides_finalize_steps():
            return [
                {'name': 'ext:finalize-step-from-extension', 'description': 'Provided by extension'},
            ]

    fake_extensions = [{'bundle': 'fake-bundle', 'module': _FakeExtModule()}]

    # Also drop in sync skill to cover the full ordering contract
    skills_root = tmp_path / '.claude' / 'skills'
    sync_dir = skills_root / 'finalize-step-sync-plugin-cache'
    sync_dir.mkdir(parents=True)
    (sync_dir / 'SKILL.md').write_text(
        '---\nname: finalize-step-sync-plugin-cache\ndescription: Sync plugin cache\n---\n\n# Sync\n'
    )

    with patch.object(_cmd_skill_resolution, 'discover_all_extensions', return_value=fake_extensions):
        steps = _run_discovery_in_cwd(tmp_path)

    names = [s['name'] for s in steps]
    assert 'ext:finalize-step-from-extension' in names

    ext_idx = names.index('ext:finalize-step-from-extension')
    # Every non-extension entry must precede the extension entry
    for idx, step in enumerate(steps):
        if step['source'] == 'extension':
            continue
        assert idx < ext_idx, (
            f'Non-extension step {step["name"]!r} at {idx} must come before extension step '
            f'at {ext_idx}'
        )
    # And the extension entry carries source=extension
    assert steps[ext_idx]['source'] == 'extension'


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess)
# =============================================================================


def test_cli_resolve_domain_skills():
    """Test CLI plumbing: resolve-domain-skills outputs TOON."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'resolve-domain-skills', '--domain', 'java', '--profile', 'implementation')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'pm-dev-java:java-core' in result.stdout
