#!/usr/bin/env python3
"""Tests for scan-planning-inventory.py script.

Tests planning inventory scanning including core/derived categorization,
statistics calculation, output formats, and integration with marketplace-inventory.
"""

import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import TestRunner, run_script, get_script_path

# Script under test
SCRIPT_PATH = get_script_path('pm-workflow', 'planning-inventory', 'scan-planning-inventory.py')


def parse_json(output):
    """Parse JSON from output."""
    import json
    return json.loads(output)


# =============================================================================
# Tests - Basic Execution
# =============================================================================

def test_default_execution_succeeds():
    """Test default execution completes successfully."""
    result = run_script(SCRIPT_PATH)
    assert result.returncode == 0, f"Script returned error: {result.stderr}"


def test_default_produces_valid_json():
    """Test default mode produces valid JSON."""
    result = run_script(SCRIPT_PATH)
    assert result.returncode == 0, f"Script returned error: {result.stderr}"

    try:
        parse_json(result.stdout)
    except Exception as e:
        raise AssertionError(f"Default mode should produce valid JSON: {e}")


# =============================================================================
# Tests - Output Structure
# =============================================================================

def test_full_format_has_required_fields():
    """Test full format has required top-level fields."""
    result = run_script(SCRIPT_PATH, '--format', 'full')
    assert result.returncode == 0, f"Script returned error: {result.stderr}"

    data = parse_json(result.stdout)
    assert 'patterns' in data, "Should have patterns field"
    assert 'bundles_scanned' in data, "Should have bundles_scanned field"
    assert 'core' in data, "Should have core field"
    assert 'derived' in data, "Should have derived field"
    assert 'statistics' in data, "Should have statistics field"


def test_core_has_required_fields():
    """Test core section has required fields."""
    result = run_script(SCRIPT_PATH)
    assert result.returncode == 0, f"Script returned error: {result.stderr}"

    data = parse_json(result.stdout)
    core = data.get('core', {})
    assert 'bundle' in core, "Core should have bundle field"
    assert core['bundle'] == 'pm-workflow', "Core bundle should be 'pm-workflow'"
    assert 'agents' in core, "Core should have agents field"
    assert 'commands' in core, "Core should have commands field"
    assert 'skills' in core, "Core should have skills field"


def test_derived_is_list():
    """Test derived section is a list."""
    result = run_script(SCRIPT_PATH)
    assert result.returncode == 0, f"Script returned error: {result.stderr}"

    data = parse_json(result.stdout)
    derived = data.get('derived', [])
    assert isinstance(derived, list), "Derived should be a list"


def test_statistics_has_required_fields():
    """Test statistics section has required fields."""
    result = run_script(SCRIPT_PATH)
    assert result.returncode == 0, f"Script returned error: {result.stderr}"

    data = parse_json(result.stdout)
    stats = data.get('statistics', {})
    assert 'core' in stats, "Statistics should have core field"
    assert 'derived' in stats, "Statistics should have derived field"
    assert 'total_components' in stats, "Statistics should have total_components field"


# =============================================================================
# Tests - Core Components
# =============================================================================

def test_core_has_plan_skills():
    """Test core bundle contains planning-related skills."""
    result = run_script(SCRIPT_PATH)
    assert result.returncode == 0, f"Script returned error: {result.stderr}"

    data = parse_json(result.stdout)
    core_skills = data.get('core', {}).get('skills', [])
    skill_names = [s['name'] for s in core_skills]

    # Should have planning-related skills (matching inventory patterns)
    # Note: phase-* skills exist but need explicit pattern in inventory scanner
    planning_skills = [s for s in skill_names if 'plan' in s or s.startswith('manage-') or s.startswith('task-')]
    assert len(planning_skills) >= 5, f"Should have at least 5 planning-related skills, found {len(planning_skills)}"


def test_core_has_manage_skills():
    """Test core bundle contains manage-* skills."""
    result = run_script(SCRIPT_PATH)
    assert result.returncode == 0, f"Script returned error: {result.stderr}"

    data = parse_json(result.stdout)
    core_skills = data.get('core', {}).get('skills', [])
    skill_names = [s['name'] for s in core_skills]

    # Should have at least some manage-* skills
    manage_skills = [s for s in skill_names if s.startswith('manage-')]
    assert len(manage_skills) >= 5, f"Should have at least 5 manage-* skills, found {len(manage_skills)}"


def test_core_has_workflow_skills():
    """Test core bundle contains task-* skills for workflow execution."""
    result = run_script(SCRIPT_PATH)
    assert result.returncode == 0, f"Script returned error: {result.stderr}"

    data = parse_json(result.stdout)
    core_skills = data.get('core', {}).get('skills', [])
    skill_names = [s['name'] for s in core_skills]

    # Should have task-* skills for workflow execution
    # Note: wf-tool-* skills exist but aren't matched by inventory patterns
    task_skills = [s for s in skill_names if s.startswith('task-')]
    assert len(task_skills) >= 2, f"Should have at least 2 task-* skills, found {len(task_skills)}"


def test_core_has_commands():
    """Test core bundle contains commands."""
    result = run_script(SCRIPT_PATH)
    assert result.returncode == 0, f"Script returned error: {result.stderr}"

    data = parse_json(result.stdout)
    core_commands = data.get('core', {}).get('commands', [])
    assert len(core_commands) >= 4, f"Should have at least 4 commands, found {len(core_commands)}"

    # Verify specific commands are present
    command_names = [c['name'] for c in core_commands]
    expected_commands = ['task-implement', 'pr-doctor', 'plan-execute', 'plan-manage']
    for expected in expected_commands:
        assert expected in command_names, f"Should have {expected} command"


# =============================================================================
# Tests - Derived Components
# =============================================================================

def test_derived_plugin_has_plan_components():
    """Test pm-plugin-development derived bundle has plan components."""
    result = run_script(SCRIPT_PATH)
    assert result.returncode == 0, f"Script returned error: {result.stderr}"

    data = parse_json(result.stdout)
    derived = data.get('derived', [])

    plugin_bundle = next((d for d in derived if d['bundle'] == 'pm-plugin-development'), None)
    assert plugin_bundle is not None, "Should find pm-plugin-development in derived"

    # Should have plugin-task-plan, plugin-plan-implement skills
    # Note: ext-outline-plugin exists but isn't matched by inventory patterns (*-solution-outline)
    skill_names = [s['name'] for s in plugin_bundle.get('skills', [])]

    assert 'plugin-task-plan' in skill_names, "Should have plugin-task-plan skill"
    assert 'plugin-plan-implement' in skill_names, "Should have plugin-plan-implement skill"


def test_java_and_frontend_not_in_derived():
    """Test pm-dev-java and pm-dev-frontend are NOT in derived (planning components removed)."""
    result = run_script(SCRIPT_PATH)
    assert result.returncode == 0, f"Script returned error: {result.stderr}"

    data = parse_json(result.stdout)
    derived = data.get('derived', [])
    bundle_names = [d['bundle'] for d in derived]

    # These bundles no longer have planning-specific components
    assert 'pm-dev-java' not in bundle_names, "pm-dev-java should NOT be in derived (planning components removed)"
    assert 'pm-dev-frontend' not in bundle_names, "pm-dev-frontend should NOT be in derived (planning components removed)"


def test_derived_includes_plugin_tools():
    """Test derived includes pm-plugin-development bundle."""
    result = run_script(SCRIPT_PATH)
    assert result.returncode == 0, f"Script returned error: {result.stderr}"

    data = parse_json(result.stdout)
    derived = data.get('derived', [])
    bundle_names = [d['bundle'] for d in derived]
    assert 'pm-plugin-development' in bundle_names, "Derived should include pm-plugin-development"


# =============================================================================
# Tests - Summary Format
# =============================================================================

def test_summary_format_has_required_fields():
    """Test summary format has required fields."""
    result = run_script(SCRIPT_PATH, '--format', 'summary')
    assert result.returncode == 0, f"Script returned error: {result.stderr}"

    data = parse_json(result.stdout)
    assert 'core_bundle' in data, "Summary should have core_bundle field"
    assert 'core_components' in data, "Summary should have core_components field"
    assert 'derived_bundles' in data, "Summary should have derived_bundles field"
    assert 'statistics' in data, "Summary should have statistics field"


def test_summary_core_components_structure():
    """Test summary core_components has correct structure."""
    result = run_script(SCRIPT_PATH, '--format', 'summary')
    assert result.returncode == 0, f"Script returned error: {result.stderr}"

    data = parse_json(result.stdout)
    core_components = data.get('core_components', [])

    assert isinstance(core_components, list), "core_components should be a list"
    for component in core_components:
        assert 'type' in component, "Each component should have type"
        assert 'names' in component, "Each component should have names"
        assert isinstance(component['names'], list), "names should be a list"


def test_summary_derived_bundles_structure():
    """Test summary derived_bundles has correct structure."""
    result = run_script(SCRIPT_PATH, '--format', 'summary')
    assert result.returncode == 0, f"Script returned error: {result.stderr}"

    data = parse_json(result.stdout)
    derived_bundles = data.get('derived_bundles', [])

    assert isinstance(derived_bundles, list), "derived_bundles should be a list"
    for bundle in derived_bundles:
        assert 'bundle' in bundle, "Each derived bundle should have bundle name"


# =============================================================================
# Tests - Statistics
# =============================================================================

def test_statistics_totals_are_consistent():
    """Test statistics totals are consistent with component counts."""
    result = run_script(SCRIPT_PATH)
    assert result.returncode == 0, f"Script returned error: {result.stderr}"

    data = parse_json(result.stdout)
    stats = data.get('statistics', {})
    core = data.get('core', {})
    derived = data.get('derived', [])

    # Core stats should match actual counts
    core_stats = stats.get('core', {})
    assert core_stats.get('agents') == len(core.get('agents', [])), "Core agent count mismatch"
    assert core_stats.get('commands') == len(core.get('commands', [])), "Core command count mismatch"
    assert core_stats.get('skills') == len(core.get('skills', [])), "Core skill count mismatch"

    # Derived stats should sum correctly
    derived_stats = stats.get('derived', {})
    actual_derived_agents = sum(len(d.get('agents', [])) for d in derived)
    assert derived_stats.get('agents') == actual_derived_agents, "Derived agent count mismatch"


def test_total_components_is_sum():
    """Test total_components equals core + derived totals."""
    result = run_script(SCRIPT_PATH)
    assert result.returncode == 0, f"Script returned error: {result.stderr}"

    data = parse_json(result.stdout)
    stats = data.get('statistics', {})

    core_total = stats.get('core', {}).get('total', 0)
    derived_total = stats.get('derived', {}).get('total', 0)
    total_components = stats.get('total_components', 0)

    assert total_components == core_total + derived_total, \
        f"Total components ({total_components}) should equal core ({core_total}) + derived ({derived_total})"


# =============================================================================
# Tests - Description Extraction
# =============================================================================

def test_include_descriptions_adds_descriptions():
    """Test --include-descriptions adds description fields."""
    result = run_script(SCRIPT_PATH, '--include-descriptions')
    assert result.returncode == 0, f"Script returned error: {result.stderr}"

    data = parse_json(result.stdout)
    core_skills = data.get('core', {}).get('skills', [])

    # At least some skills should have descriptions
    skills_with_desc = [s for s in core_skills if s.get('description')]
    assert len(skills_with_desc) > 0, "Should have at least one skill with description"


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        # Basic Execution
        test_default_execution_succeeds,
        test_default_produces_valid_json,
        # Output Structure
        test_full_format_has_required_fields,
        test_core_has_required_fields,
        test_derived_is_list,
        test_statistics_has_required_fields,
        # Core Components
        test_core_has_plan_skills,
        test_core_has_manage_skills,
        test_core_has_workflow_skills,
        test_core_has_commands,
        # Derived Components
        test_derived_plugin_has_plan_components,
        test_java_and_frontend_not_in_derived,
        test_derived_includes_plugin_tools,
        # Summary Format
        test_summary_format_has_required_fields,
        test_summary_core_components_structure,
        test_summary_derived_bundles_structure,
        # Statistics
        test_statistics_totals_are_consistent,
        test_total_components_is_sum,
        # Description Extraction
        test_include_descriptions_adds_descriptions,
    ])
    sys.exit(runner.run())
