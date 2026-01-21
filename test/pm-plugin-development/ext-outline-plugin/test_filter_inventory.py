#!/usr/bin/env python3
"""Tests for filter-inventory.py script.

Tests inventory filtering by bundle and component type for component analysis agents.
"""

import tempfile
from pathlib import Path

from toon_parser import parse_toon  # type: ignore[import-not-found]

from conftest import get_script_path, run_script

# Script under test
SCRIPT_PATH = get_script_path('pm-plugin-development', 'ext-outline-plugin', 'filter-inventory.py')


# =============================================================================
# Fixtures
# =============================================================================


SAMPLE_INVENTORY = """\
status: success
scope:
  affected_artifacts: [skills, commands, agents]
  bundle_scope: all

inventory:
  skills[4]:
    - marketplace/bundles/pm-dev-java/skills/java-cdi/SKILL.md
    - marketplace/bundles/pm-dev-java/skills/java-lombok/SKILL.md
    - marketplace/bundles/pm-dev-frontend/skills/cui-javascript/SKILL.md
    - marketplace/bundles/pm-workflow/skills/phase-1-init/SKILL.md
  commands[2]:
    - marketplace/bundles/pm-dev-java/commands/java-create.md
    - marketplace/bundles/pm-documents/commands/tools-verify-architecture-diagrams.md
  agents[3]:
    - marketplace/bundles/pm-dev-java/agents/java-implement-agent.md
    - marketplace/bundles/pm-workflow/agents/plan-init-agent.md
    - marketplace/bundles/pm-workflow/agents/task-plan-agent.md

total_files: 9
"""


def create_test_plan(tmp_dir: Path, plan_id: str, inventory_content: str) -> Path:
    """Create a test plan directory with inventory file."""
    plan_dir = tmp_dir / ".plan" / "plans" / plan_id / "work"
    plan_dir.mkdir(parents=True)
    inventory_path = plan_dir / "inventory_filtered.toon"
    inventory_path.write_text(inventory_content)
    return tmp_dir


# =============================================================================
# Tests - Basic Filtering
# =============================================================================


def test_filter_skills_by_bundle():
    """Test filtering skills for a specific bundle."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        create_test_plan(tmp_dir, "test-plan", SAMPLE_INVENTORY)

        result = run_script(
            SCRIPT_PATH,
            'filter', '--plan-id', 'test-plan',
            '--bundle', 'pm-dev-java', '--component-type', 'skills',
            cwd=tmp_dir
        )

        assert result.returncode == 0, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)

        assert data['status'] == 'success'
        assert data['bundle'] == 'pm-dev-java'
        assert data['component_type'] == 'skills'
        assert data['file_count'] == 2
        assert len(data['files']) == 2
        assert 'marketplace/bundles/pm-dev-java/skills/java-cdi/SKILL.md' in data['files']
        assert 'marketplace/bundles/pm-dev-java/skills/java-lombok/SKILL.md' in data['files']


def test_filter_agents_by_bundle():
    """Test filtering agents for a specific bundle."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        create_test_plan(tmp_dir, "test-plan", SAMPLE_INVENTORY)

        result = run_script(
            SCRIPT_PATH,
            'filter', '--plan-id', 'test-plan',
            '--bundle', 'pm-workflow', '--component-type', 'agents',
            cwd=tmp_dir
        )

        assert result.returncode == 0, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)

        assert data['status'] == 'success'
        assert data['bundle'] == 'pm-workflow'
        assert data['file_count'] == 2
        assert len(data['files']) == 2


def test_filter_commands_by_bundle():
    """Test filtering commands for a specific bundle."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        create_test_plan(tmp_dir, "test-plan", SAMPLE_INVENTORY)

        result = run_script(
            SCRIPT_PATH,
            'filter', '--plan-id', 'test-plan',
            '--bundle', 'pm-documents', '--component-type', 'commands',
            cwd=tmp_dir
        )

        assert result.returncode == 0, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)

        assert data['status'] == 'success'
        assert data['file_count'] == 1


# =============================================================================
# Tests - Empty Results
# =============================================================================


def test_filter_returns_empty_for_no_matches():
    """Test that filtering returns empty list when no files match."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        create_test_plan(tmp_dir, "test-plan", SAMPLE_INVENTORY)

        result = run_script(
            SCRIPT_PATH,
            'filter', '--plan-id', 'test-plan',
            '--bundle', 'nonexistent-bundle', '--component-type', 'skills',
            cwd=tmp_dir
        )

        assert result.returncode == 0, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)

        assert data['status'] == 'success'
        assert data['file_count'] == 0
        assert data['files'] == []


def test_filter_returns_empty_for_missing_component_type():
    """Test filtering returns empty when component type has no entries."""
    inventory_no_agents = """\
status: success
inventory:
  skills[1]:
    - marketplace/bundles/pm-dev-java/skills/java-cdi/SKILL.md
  commands[0]:
  agents[0]:
total_files: 1
"""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        create_test_plan(tmp_dir, "test-plan", inventory_no_agents)

        result = run_script(
            SCRIPT_PATH,
            'filter', '--plan-id', 'test-plan',
            '--bundle', 'pm-dev-java', '--component-type', 'agents',
            cwd=tmp_dir
        )

        assert result.returncode == 0
        data = parse_toon(result.stdout)
        assert data['file_count'] == 0


# =============================================================================
# Tests - Error Handling
# =============================================================================


def test_error_when_inventory_not_found():
    """Test error returned when inventory file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        # Create plan dir but NOT the inventory file
        plan_dir = tmp_dir / ".plan" / "plans" / "missing-inventory" / "work"
        plan_dir.mkdir(parents=True)

        result = run_script(
            SCRIPT_PATH,
            'filter', '--plan-id', 'missing-inventory',
            '--bundle', 'pm-dev-java', '--component-type', 'skills',
            cwd=tmp_dir
        )

        assert result.returncode == 1
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert 'Inventory not found' in data['message']


def test_error_when_plan_not_found():
    """Test error returned when plan directory doesn't exist."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        result = run_script(
            SCRIPT_PATH,
            'filter', '--plan-id', 'nonexistent-plan',
            '--bundle', 'pm-dev-java', '--component-type', 'skills',
            cwd=tmp_dir
        )

        assert result.returncode == 1
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'


# =============================================================================
# Tests - Output Format
# =============================================================================


def test_output_is_valid_toon():
    """Test that output is valid TOON format."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        create_test_plan(tmp_dir, "test-plan", SAMPLE_INVENTORY)

        result = run_script(
            SCRIPT_PATH,
            'filter', '--plan-id', 'test-plan',
            '--bundle', 'pm-dev-java', '--component-type', 'skills',
            cwd=tmp_dir
        )

        assert result.returncode == 0
        # Should parse without error
        data = parse_toon(result.stdout)
        assert 'status' in data
        assert 'bundle' in data
        assert 'component_type' in data
        assert 'file_count' in data
        assert 'files' in data
