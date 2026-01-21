#!/usr/bin/env python3
"""Tests for scan-marketplace-inventory.py script.

Migrated from test-scan-marketplace-inventory.sh - tests marketplace inventory
scanning including basic discovery, resource filtering, description extraction,
TOON validity, bundle structure, script discovery, and error handling.
"""

from pathlib import Path
from typing import Any

from toon_parser import parse_toon  # type: ignore[import-not-found]

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import get_script_path, run_script

# Script under test
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SCRIPT_PATH = get_script_path('pm-plugin-development', 'tools-marketplace-inventory', 'scan-marketplace-inventory.py')

# Keys that are metadata, not bundle names
METADATA_KEYS = {'status', 'scope', 'base_path', 'statistics'}


def get_bundles(data: dict) -> list[dict[str, Any]]:
    """Extract bundle dicts from data where bundles are top-level keys.

    The new format has bundles as top-level keys (e.g., 'plan-marshall:', 'pm-workflow:')
    rather than a 'bundles' list. This helper extracts them as a list of dicts
    with 'name' field added for backward compatibility with tests.
    """
    bundles = []
    for key, value in data.items():
        if key not in METADATA_KEYS and isinstance(value, dict):
            # Add name field from key for compatibility
            bundle = {'name': key, **value}
            bundles.append(bundle)
    return bundles


# =============================================================================
# Tests - Basic Discovery
# =============================================================================


def test_default_scan_finds_bundles():
    """Test direct-result scan finds at least 5 bundles."""
    result = run_script(SCRIPT_PATH, '--direct-result')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    total_bundles = data.get('statistics', {}).get('total_bundles', 0)
    assert total_bundles >= 5, f'Should find at least 5 bundles, found {total_bundles}'


def test_default_scan_finds_agents():
    """Test direct-result scan finds at least 1 agent."""
    result = run_script(SCRIPT_PATH, '--direct-result')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    total_agents = data.get('statistics', {}).get('total_agents', 0)
    assert total_agents >= 1, f'Should find at least 1 agent, found {total_agents}'


def test_default_scan_finds_commands():
    """Test direct-result scan finds at least 3 commands."""
    result = run_script(SCRIPT_PATH, '--direct-result')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    total_commands = data.get('statistics', {}).get('total_commands', 0)
    assert total_commands >= 3, f'Should find at least 3 commands, found {total_commands}'


def test_default_scan_finds_skills():
    """Test direct-result scan finds at least 20 skills."""
    result = run_script(SCRIPT_PATH, '--direct-result')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    total_skills = data.get('statistics', {}).get('total_skills', 0)
    assert total_skills >= 20, f'Should find at least 20 skills, found {total_skills}'


def test_default_scope_is_auto():
    """Test default scope is auto (tries marketplace first, then plugin-cache)."""
    result = run_script(SCRIPT_PATH, '--direct-result')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    scope = data.get('scope')
    assert scope == 'auto', f"Default scope should be 'auto', got '{scope}'"


# =============================================================================
# Tests - Resource Filtering
# =============================================================================


def test_agents_only_no_commands():
    """Test agents-only filter has no commands."""
    result = run_script(SCRIPT_PATH, '--direct-result', '--resource-types', 'agents')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    total_commands = data.get('statistics', {}).get('total_commands', 0)
    assert total_commands == 0, f'Agents-only should have 0 commands, found {total_commands}'


def test_agents_only_no_skills():
    """Test agents-only filter has no skills."""
    result = run_script(SCRIPT_PATH, '--direct-result', '--resource-types', 'agents')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    total_skills = data.get('statistics', {}).get('total_skills', 0)
    assert total_skills == 0, f'Agents-only should have 0 skills, found {total_skills}'


def test_agents_only_has_agents():
    """Test agents-only filter has agents."""
    result = run_script(SCRIPT_PATH, '--direct-result', '--resource-types', 'agents')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    total_agents = data.get('statistics', {}).get('total_agents', 0)
    assert total_agents >= 1, f'Agents-only should have at least 1 agent, found {total_agents}'


def test_commands_only_no_agents():
    """Test commands-only filter has no agents."""
    result = run_script(SCRIPT_PATH, '--direct-result', '--resource-types', 'commands')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    total_agents = data.get('statistics', {}).get('total_agents', 0)
    assert total_agents == 0, f'Commands-only should have 0 agents, found {total_agents}'


def test_commands_only_has_commands():
    """Test commands-only filter has commands."""
    result = run_script(SCRIPT_PATH, '--direct-result', '--resource-types', 'commands')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    total_commands = data.get('statistics', {}).get('total_commands', 0)
    assert total_commands >= 3, f'Commands-only should have at least 3 commands, found {total_commands}'


def test_skills_only_no_agents():
    """Test skills-only filter has no agents."""
    result = run_script(SCRIPT_PATH, '--direct-result', '--resource-types', 'skills')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    total_agents = data.get('statistics', {}).get('total_agents', 0)
    assert total_agents == 0, f'Skills-only should have 0 agents, found {total_agents}'


def test_skills_only_has_skills():
    """Test skills-only filter has skills."""
    result = run_script(SCRIPT_PATH, '--direct-result', '--resource-types', 'skills')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    total_skills = data.get('statistics', {}).get('total_skills', 0)
    assert total_skills >= 20, f'Skills-only should have at least 20 skills, found {total_skills}'


def test_multiple_types_has_both():
    """Test multiple types filter has both agents and commands."""
    result = run_script(SCRIPT_PATH, '--direct-result', '--resource-types', 'agents,commands')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    total_agents = data.get('statistics', {}).get('total_agents', 0)
    assert total_agents >= 1, f'Multiple types should have at least 1 agent, found {total_agents}'


# =============================================================================
# Tests - Description Extraction
# =============================================================================


def test_no_descriptions_returns_null():
    """Test direct-result mode has no description fields without flag."""
    result = run_script(SCRIPT_PATH, '--direct-result')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)

    # In default mode (no --full), agents are just strings (names only), no description field
    # Check that no agent is a dict with a description field
    has_desc_count = sum(
        1
        for bundle in bundles
        for agent in bundle.get('agents', [])
        if isinstance(agent, dict) and 'description' in agent
    )
    assert has_desc_count == 0, (
        f'Should have no description fields without --include-descriptions, found {has_desc_count}'
    )


def test_with_descriptions_extracts_desc():
    """Test --full extracts descriptions."""
    import json

    # Use --full with --format json to get proper dict structure
    result = run_script(SCRIPT_PATH, '--direct-result', '--full', '--format', 'json')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = json.loads(result.stdout)
    bundles_dict = data.get('bundles', {})

    # Count agents with descriptions (JSON format has bundles as dict)
    desc_count = sum(
        1
        for bundle in bundles_dict.values()
        for agent in bundle.get('agents', [])
        if isinstance(agent, dict) and agent.get('description') is not None
    )
    assert desc_count > 0, f'Should find descriptions with --full, found {desc_count}'


# =============================================================================
# Tests - TOON Validity
# =============================================================================


def test_direct_result_produces_valid_toon():
    """Test --direct-result produces valid TOON."""
    result = run_script(SCRIPT_PATH, '--direct-result')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    try:
        parse_toon(result.stdout)
    except Exception as e:
        raise AssertionError(f'Direct result mode should produce valid TOON: {e}') from e


def test_with_descriptions_produces_valid_toon():
    """Test --include-descriptions with --direct-result produces valid TOON."""
    result = run_script(SCRIPT_PATH, '--direct-result', '--include-descriptions')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    try:
        parse_toon(result.stdout)
    except Exception as e:
        raise AssertionError(f'With descriptions should produce valid TOON: {e}') from e


def test_filtered_produces_valid_toon():
    """Test filtered mode with --direct-result produces valid TOON."""
    result = run_script(SCRIPT_PATH, '--direct-result', '--resource-types', 'agents')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    try:
        parse_toon(result.stdout)
    except Exception as e:
        raise AssertionError(f'Filtered mode should produce valid TOON: {e}') from e


# =============================================================================
# Tests - Bundle Structure
# =============================================================================


def test_bundles_have_required_fields():
    """Test bundles have required fields."""
    result = run_script(SCRIPT_PATH, '--direct-result')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)
    assert len(bundles) > 0, 'Should have at least one bundle'

    first_bundle = bundles[0]
    assert 'name' in first_bundle, 'Bundle should have name'
    assert 'path' in first_bundle, 'Bundle should have path'
    # Note: agents/commands/skills/scripts may not be present if empty
    # The new format only includes resource types that have entries


# =============================================================================
# Tests - Script Discovery
# =============================================================================


def test_script_count_matches_filesystem():
    """Test script count matches filesystem count (excluding private modules)."""
    import subprocess

    # Count scripts on filesystem (excluding underscore-prefixed files = private modules)
    find_result = subprocess.run(
        [
            'find',
            str(PROJECT_ROOT / 'marketplace' / 'bundles'),
            '-path',
            '*/skills/*/scripts/*',
            '-type',
            'f',
            '(',
            '-name',
            '*.sh',
            '-o',
            '-name',
            '*.py',
            ')',
        ],
        capture_output=True,
        text=True,
    )
    # Filter out underscore-prefixed files (private modules per PEP 8)
    all_files = [line for line in find_result.stdout.strip().split('\n') if line]
    public_files = [f for f in all_files if not Path(f).name.startswith('_')]
    expected_count = len(public_files)

    # Get count from inventory
    result = run_script(SCRIPT_PATH, '--direct-result')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    actual_count = data.get('statistics', {}).get('total_scripts', 0)

    assert actual_count == expected_count, f'Script count mismatch: expected {expected_count}, got {actual_count}'


def test_scripts_have_path_formats():
    """Test scripts have path_formats structure when using --full flag."""
    import json

    # Note: Scripts always have path_formats structure (both in default and --full mode)
    result = run_script(SCRIPT_PATH, '--direct-result', '--full', '--format', 'json')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = json.loads(result.stdout)
    bundles_dict = data.get('bundles', {})

    # Count scripts with path_formats.absolute (JSON format)
    scripts_with_paths = sum(
        1
        for bundle in bundles_dict.values()
        for script in bundle.get('scripts', [])
        if isinstance(script, dict) and script.get('path_formats', {}).get('absolute') is not None
    )
    total_scripts = data.get('statistics', {}).get('total_scripts', 0)

    assert scripts_with_paths == total_scripts and total_scripts != 0, (
        f'All scripts should have path_formats: {scripts_with_paths} vs {total_scripts}'
    )


def test_scripts_have_notation_field():
    """Test all scripts have notation field in {bundle}:{skill}:{script} format."""
    import json

    result = run_script(SCRIPT_PATH, '--direct-result', '--resource-types', 'scripts', '--full', '--format', 'json')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = json.loads(result.stdout)
    bundles_dict = data.get('bundles', {})

    # Verify all scripts have notation field (JSON format has bundles as dict)
    for bundle_name, bundle in bundles_dict.items():
        for script in bundle.get('scripts', []):
            assert 'notation' in script, f'Script {script["name"]} missing notation field'
            notation = script['notation']
            skill_name = script['skill']
            script_name = script['name']
            expected = f'{bundle_name}:{skill_name}:{script_name}'
            assert notation == expected, f"Script notation mismatch: expected '{expected}', got '{notation}'"


def test_scripts_notation_format_valid():
    """Test notation follows {bundle}:{skill}:{script} format with two colons."""
    import json

    result = run_script(SCRIPT_PATH, '--direct-result', '--resource-types', 'scripts', '--full', '--format', 'json')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = json.loads(result.stdout)
    bundles_dict = data.get('bundles', {})

    for bundle in bundles_dict.values():
        for script in bundle.get('scripts', []):
            notation = script.get('notation', '')
            parts = notation.split(':')
            assert len(parts) == 3, f"Notation '{notation}' should have exactly two colons"
            assert parts[0], f"Notation '{notation}' should have non-empty bundle"
            assert parts[1], f"Notation '{notation}' should have non-empty skill"
            assert parts[2], f"Notation '{notation}' should have non-empty script"


def test_scripts_exclude_private_modules():
    """Test underscore-prefixed files (private modules) are excluded from scripts."""
    result = run_script(SCRIPT_PATH, '--direct-result', '--resource-types', 'scripts')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)

    # Verify no script names start with underscore
    # In default mode, scripts are strings (just names)
    for bundle in bundles:
        for script in bundle.get('scripts', []):
            script_name = script if isinstance(script, str) else script.get('name', '')
            assert not script_name.startswith('_'), (
                f"Private module '{script_name}' should not be included (underscore prefix = internal)"
            )


# =============================================================================
# Tests - Name Pattern Filtering
# =============================================================================


def test_name_pattern_filters_agents():
    """Test --name-pattern filters agents by pattern."""
    result = run_script(SCRIPT_PATH, '--direct-result', '--resource-types', 'agents', '--name-pattern', '*-plan-*')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)
    total_agents = data.get('statistics', {}).get('total_agents', 0)
    assert total_agents >= 1, 'Should find at least 1 plan-related agent'

    # Verify all agents match the pattern (agents are strings in default mode)
    for bundle in bundles:
        for agent in bundle.get('agents', []):
            agent_name = agent if isinstance(agent, str) else agent.get('name', '')
            assert '-plan-' in agent_name, f'Agent {agent_name} should match *-plan-* pattern'


def test_name_pattern_multiple_patterns():
    """Test --name-pattern with multiple pipe-separated patterns."""
    result = run_script(SCRIPT_PATH, '--direct-result', '--resource-types', 'agents', '--name-pattern', 'plan-*|task-*')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)
    total_agents = data.get('statistics', {}).get('total_agents', 0)
    assert total_agents >= 2, 'Should find at least 2 agents matching plan-* or task-* patterns'

    # Verify all agents match one of the patterns (agents are strings in default mode)
    for bundle in bundles:
        for agent in bundle.get('agents', []):
            agent_name = agent if isinstance(agent, str) else agent.get('name', '')
            assert agent_name.startswith('plan-') or agent_name.startswith('task-'), (
                f'Agent {agent_name} should match plan-* or task-* pattern'
            )


def test_name_pattern_no_matches():
    """Test --name-pattern with pattern that matches nothing."""
    result = run_script(SCRIPT_PATH, '--direct-result', '--name-pattern', 'nonexistent-xyz-pattern')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    total_resources = data.get('statistics', {}).get('total_resources', 0)
    assert total_resources == 0, 'Should find 0 resources with non-matching pattern'


def test_name_pattern_skills_filter():
    """Test --name-pattern filters skills."""
    result = run_script(SCRIPT_PATH, '--direct-result', '--resource-types', 'skills', '--name-pattern', 'plan-*')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)
    total_skills = data.get('statistics', {}).get('total_skills', 0)
    assert total_skills >= 1, 'Should find at least 1 skill starting with plan-'

    # Verify all skills match the pattern (skills are strings in default mode)
    for bundle in bundles:
        for skill in bundle.get('skills', []):
            skill_name = skill if isinstance(skill, str) else skill.get('name', '')
            assert skill_name.startswith('plan-'), f'Skill {skill_name} should start with plan-'


# =============================================================================
# Tests - Bundle Filtering
# =============================================================================


def test_bundles_filter_single():
    """Test --bundles filters to single bundle."""
    result = run_script(SCRIPT_PATH, '--direct-result', '--bundles', 'pm-workflow')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)
    assert len(bundles) == 1, f'Should have exactly 1 bundle, found {len(bundles)}'
    assert bundles[0]['name'] == 'pm-workflow', f"Bundle should be 'pm-workflow', got '{bundles[0]['name']}'"


def test_bundles_filter_multiple():
    """Test --bundles filters to multiple bundles."""
    result = run_script(SCRIPT_PATH, '--direct-result', '--bundles', 'pm-workflow,pm-dev-java')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)
    bundle_names = {b['name'] for b in bundles}
    assert bundle_names == {'pm-workflow', 'pm-dev-java'}, f'Expected pm-workflow and pm-dev-java, got {bundle_names}'


def test_bundles_filter_nonexistent():
    """Test --bundles with nonexistent bundle returns empty."""
    result = run_script(SCRIPT_PATH, '--direct-result', '--bundles', 'nonexistent-bundle')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)
    assert len(bundles) == 0, f'Should have 0 bundles for nonexistent filter, found {len(bundles)}'


# =============================================================================
# Tests - Combined Filtering
# =============================================================================


def test_combined_bundle_and_name_pattern():
    """Test combining --bundles and --name-pattern filters."""
    result = run_script(
        SCRIPT_PATH, '--direct-result', '--bundles', 'pm-workflow', '--resource-types', 'agents', '--name-pattern', 'plan-*'
    )
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    bundles = get_bundles(data)
    assert len(bundles) == 1, 'Should have exactly 1 bundle'
    assert bundles[0]['name'] == 'pm-workflow', 'Bundle should be pm-workflow'

    # Should find plan-init-agent (thin agent pattern)
    agents = bundles[0].get('agents', [])
    assert len(agents) >= 1, 'Should find at least 1 plan-* agent in pm-workflow'
    for agent in agents:
        agent_name = agent if isinstance(agent, str) else agent.get('name', '')
        assert agent_name.startswith('plan-'), f'Agent {agent_name} should match plan-*'


# =============================================================================
# Tests - File Output (Default Behavior)
# =============================================================================


def test_default_file_output_creates_file(tmp_path, monkeypatch):
    """Test default mode (no --direct-result) creates a TOON file and prints summary."""
    # Set PLAN_BASE_DIR to temp location
    plan_dir = tmp_path / '.plan'
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    result = run_script(SCRIPT_PATH, '--bundles', 'pm-workflow')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    # Verify summary output contains expected fields
    output = result.stdout
    assert 'status: success' in output, 'Summary should contain status: success'
    assert 'output_mode: file' in output, 'Summary should contain output_mode: file'
    assert 'output_file:' in output, 'Summary should contain output_file path'
    assert 'next_step:' in output, 'Summary should contain next_step'

    # Verify file was created in expected location
    expected_dir = plan_dir / 'temp' / 'tools-marketplace-inventory'
    files = list(expected_dir.glob('inventory-*.toon'))
    assert len(files) == 1, f'Should create exactly one inventory file, found {len(files)}'


def test_default_file_output_summary_has_statistics(tmp_path, monkeypatch):
    """Test default file mode summary includes statistics."""
    # Set PLAN_BASE_DIR to temp location
    plan_dir = tmp_path / '.plan'
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    result = run_script(SCRIPT_PATH)
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    # Summary should include statistics
    output = result.stdout
    assert 'statistics:' in output, 'Summary should contain statistics'
    assert 'total_bundles:' in output, 'Summary should contain total_bundles'
    assert 'total_skills:' in output, 'Summary should contain total_skills'


def test_default_file_output_with_filters(tmp_path, monkeypatch):
    """Test default file mode works with bundle filter."""
    # Set PLAN_BASE_DIR to temp location
    plan_dir = tmp_path / '.plan'
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    result = run_script(SCRIPT_PATH, '--bundles', 'pm-dev-java')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    # Verify file was created in expected location
    expected_dir = plan_dir / 'temp' / 'tools-marketplace-inventory'
    files = list(expected_dir.glob('inventory-*.toon'))
    assert len(files) == 1, 'Should create inventory file with filter'

    # Read the TOON file and verify content
    content = files[0].read_text()
    assert 'pm-dev-java' in content, 'Inventory file should contain pm-dev-java bundle'


def test_default_file_output_creates_parent_dirs(tmp_path, monkeypatch):
    """Test default file mode creates parent directories if needed."""
    # Set PLAN_BASE_DIR to nested location
    plan_dir = tmp_path / 'nested' / 'deeply' / '.plan'
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    result = run_script(SCRIPT_PATH, '--bundles', 'plan-marshall')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    # Verify nested directory was created
    expected_dir = plan_dir / 'temp' / 'tools-marketplace-inventory'
    assert expected_dir.exists(), 'Should create nested directories'

    # Verify file was created
    files = list(expected_dir.glob('inventory-*.toon'))
    assert len(files) == 1, 'Should create inventory file in nested directory'


def test_file_output_respects_plan_base_dir(tmp_path, monkeypatch):
    """Test file output uses PLAN_BASE_DIR environment variable."""
    # Set PLAN_BASE_DIR to temp location
    plan_dir = tmp_path / 'custom-plan-dir'
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    result = run_script(SCRIPT_PATH, '--bundles', 'pm-workflow')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    # Verify file was created in expected location
    expected_dir = plan_dir / 'temp' / 'tools-marketplace-inventory'
    files = list(expected_dir.glob('inventory-*.toon'))
    assert len(files) == 1, f'Should create file in {expected_dir}'


# =============================================================================
# Tests - Custom Output Path (--output)
# =============================================================================


def test_output_param_creates_file_at_path(tmp_path):
    """Test --output parameter writes to specified path."""
    output_file = tmp_path / 'custom-inventory.toon'

    result = run_script(SCRIPT_PATH, '--output', str(output_file), '--bundles', 'pm-workflow')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    # Verify file was created at specified path
    assert output_file.exists(), f'Should create file at {output_file}'

    # Verify content is valid TOON
    content = output_file.read_text()
    data = parse_toon(content)
    bundles = get_bundles(data)
    assert len(bundles) == 1, 'Should have one bundle'
    assert bundles[0]['name'] == 'pm-workflow', 'Bundle should be pm-workflow'


def test_output_param_creates_parent_dirs(tmp_path):
    """Test --output parameter creates parent directories if needed."""
    output_file = tmp_path / 'nested' / 'deeply' / 'inventory.toon'

    result = run_script(SCRIPT_PATH, '--output', str(output_file), '--bundles', 'plan-marshall')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    # Verify file was created at specified path
    assert output_file.exists(), f'Should create file and parent dirs at {output_file}'


def test_output_param_summary_shows_custom_path(tmp_path):
    """Test --output parameter summary includes the custom path."""
    output_file = tmp_path / 'my-inventory.toon'

    result = run_script(SCRIPT_PATH, '--output', str(output_file), '--bundles', 'pm-workflow')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    # Verify summary contains custom path
    summary = parse_toon(result.stdout)
    assert summary.get('output_file') == str(output_file), f'Summary should show custom path, got {summary.get("output_file")}'


def test_output_param_ignores_plan_base_dir(tmp_path, monkeypatch):
    """Test --output parameter takes precedence over PLAN_BASE_DIR."""
    # Set PLAN_BASE_DIR to one location
    plan_dir = tmp_path / 'plan-base'
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    # But specify --output to a different location
    output_file = tmp_path / 'custom-output' / 'inventory.toon'

    result = run_script(SCRIPT_PATH, '--output', str(output_file), '--bundles', 'pm-workflow')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    # Verify file was created at custom path, not PLAN_BASE_DIR
    assert output_file.exists(), 'Should create file at --output path'
    plan_base_files = list((plan_dir / 'temp').glob('**/*.toon')) if plan_dir.exists() else []
    assert len(plan_base_files) == 0, 'Should NOT create file in PLAN_BASE_DIR when --output is specified'


def test_output_param_with_filters(tmp_path):
    """Test --output parameter works with resource and bundle filters."""
    output_file = tmp_path / 'filtered-inventory.toon'

    result = run_script(
        SCRIPT_PATH,
        '--output', str(output_file),
        '--bundles', 'pm-workflow',
        '--resource-types', 'skills',
        '--name-pattern', 'plan-*',
    )
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    # Verify file was created with filtered content
    assert output_file.exists(), f'Should create file at {output_file}'

    data = parse_toon(output_file.read_text())
    bundles = get_bundles(data)
    assert len(bundles) == 1, 'Should have one bundle'

    # Verify skills only (no agents, commands, scripts)
    bundle = bundles[0]
    # In the new format, empty arrays aren't included, so check count
    assert len(bundle.get('agents', [])) == 0, 'Should have 0 agents'
    assert len(bundle.get('commands', [])) == 0, 'Should have 0 commands'
    assert len(bundle.get('scripts', [])) == 0, 'Should have 0 scripts'
    assert len(bundle.get('skills', [])) >= 1, 'Should have at least 1 skill'


# =============================================================================
# Tests - Error Handling
# =============================================================================


def test_invalid_scope_returns_error():
    """Test invalid scope returns error."""
    result = run_script(SCRIPT_PATH, '--scope', 'invalid')
    assert result.returncode != 0, 'Invalid scope should return error'


def test_invalid_resource_type_returns_error():
    """Test invalid resource type returns error."""
    result = run_script(SCRIPT_PATH, '--resource-types', 'invalid')
    assert result.returncode != 0, 'Invalid resource type should return error'


# =============================================================================
# Main
# =============================================================================
