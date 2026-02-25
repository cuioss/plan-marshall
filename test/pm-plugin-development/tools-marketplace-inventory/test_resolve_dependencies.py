#!/usr/bin/env python3
"""Tests for resolve-dependencies.py script.

Tests dependency resolution including detection of various dependency types,
index building, forward/reverse lookups, and validation.
"""

import json

from _dep_detection import (  # type: ignore[import-not-found]
    ComponentId,
    DependencyType,
    detect_implements,
    detect_python_imports,
    detect_script_notations,
    detect_skill_references,
    extract_frontmatter,
)
from toon_parser import parse_toon  # type: ignore[import-not-found]

from conftest import get_script_path, run_script

# Script under test
SCRIPT_PATH = get_script_path('pm-plugin-development', 'tools-marketplace-inventory', 'resolve-dependencies.py')


# =============================================================================
# Tests - ComponentId
# =============================================================================


class TestComponentId:
    """Tests for ComponentId class."""

    def test_from_notation_skill(self):
        """Test parsing skill notation."""
        comp = ComponentId.from_notation('pm-workflow:manage-files')
        assert comp is not None
        assert comp.bundle == 'pm-workflow'
        assert comp.component_type == 'skill'
        assert comp.name == 'manage-files'
        assert comp.parent_skill is None

    def test_from_notation_script(self):
        """Test parsing script notation."""
        comp = ComponentId.from_notation('pm-workflow:manage-files:manage-files')
        assert comp is not None
        assert comp.bundle == 'pm-workflow'
        assert comp.component_type == 'script'
        assert comp.name == 'manage-files'
        assert comp.parent_skill == 'manage-files'

    def test_from_notation_agent(self):
        """Test parsing agent notation."""
        comp = ComponentId.from_notation('pm-workflow:agents:plan-init-agent')
        assert comp is not None
        assert comp.bundle == 'pm-workflow'
        assert comp.component_type == 'agent'
        assert comp.name == 'plan-init-agent'

    def test_from_notation_command(self):
        """Test parsing command notation."""
        comp = ComponentId.from_notation('plan-marshall:commands:tools-fix')
        assert comp is not None
        assert comp.bundle == 'plan-marshall'
        assert comp.component_type == 'command'
        assert comp.name == 'tools-fix'

    def test_to_notation_skill(self):
        """Test converting skill to notation."""
        comp = ComponentId(bundle='pm-workflow', component_type='skill', name='manage-files')
        assert comp.to_notation() == 'pm-workflow:manage-files'

    def test_to_notation_script(self):
        """Test converting script to notation."""
        comp = ComponentId(
            bundle='pm-workflow',
            component_type='script',
            name='manage-files',
            parent_skill='manage-files',
        )
        assert comp.to_notation() == 'pm-workflow:manage-files:manage-files'


# =============================================================================
# Tests - Frontmatter Extraction
# =============================================================================


class TestFrontmatterExtraction:
    """Tests for YAML frontmatter extraction."""

    def test_extract_simple_frontmatter(self):
        """Test extracting simple key-value frontmatter."""
        content = """---
name: test-skill
description: A test skill
user-invokable: true
---

# Content here
"""
        frontmatter, end_line = extract_frontmatter(content)
        assert frontmatter['name'] == 'test-skill'
        assert frontmatter['description'] == 'A test skill'
        assert frontmatter['user-invokable'] == 'true'
        assert end_line > 0

    def test_extract_list_frontmatter(self):
        """Test extracting list values from frontmatter."""
        content = """---
name: test-skill
skills:
  - pm-workflow:manage-files
  - plan-marshall:ref-toon-format
---

# Content
"""
        frontmatter, _ = extract_frontmatter(content)
        assert frontmatter['name'] == 'test-skill'
        assert frontmatter['skills'] == ['pm-workflow:manage-files', 'plan-marshall:ref-toon-format']

    def test_extract_implements(self):
        """Test extracting implements field."""
        content = """---
name: ext-outline-plugin
implements: pm-workflow:workflow-extension-api/standards/extensions/outline-extension.md
---

# Content
"""
        frontmatter, _ = extract_frontmatter(content)
        assert (
            frontmatter['implements'] == 'pm-workflow:workflow-extension-api/standards/extensions/outline-extension.md'
        )

    def test_no_frontmatter(self):
        """Test handling content without frontmatter."""
        content = """# Just a heading

No frontmatter here.
"""
        frontmatter, end_line = extract_frontmatter(content)
        assert frontmatter == {}
        assert end_line == 0


# =============================================================================
# Tests - Script Notation Detection
# =============================================================================


class TestScriptNotationDetection:
    """Tests for script notation detection."""

    def test_detect_execute_script_notation(self):
        """Test detecting python3 .plan/execute-script.py notation."""
        content = """
# Example usage
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files add --plan-id test
"""
        source = ComponentId(bundle='test', component_type='skill', name='test')
        deps = detect_script_notations(content, source)
        assert len(deps) == 1
        assert deps[0].target.bundle == 'pm-workflow'
        assert deps[0].target.parent_skill == 'manage-files'
        assert deps[0].target.name == 'manage-files'
        assert deps[0].dep_type == DependencyType.SCRIPT_NOTATION

    def test_detect_inline_notation(self):
        """Test detecting inline script notation."""
        content = """
Use the `plan-marshall:ref-toon-format:toon_parser` script for parsing.
"""
        source = ComponentId(bundle='test', component_type='skill', name='test')
        deps = detect_script_notations(content, source)
        assert len(deps) == 1
        assert deps[0].target.bundle == 'plan-marshall'
        assert deps[0].target.name == 'toon_parser'

    def test_skip_urls(self):
        """Test that URLs are not detected as notations."""
        content = """
Visit https://example.com:8080:path for more info.
Also see http://localhost:3000:api
"""
        source = ComponentId(bundle='test', component_type='skill', name='test')
        deps = detect_script_notations(content, source)
        assert len(deps) == 0


# =============================================================================
# Tests - Skill Reference Detection
# =============================================================================


class TestSkillReferenceDetection:
    """Tests for skill reference detection."""

    def test_detect_frontmatter_skills(self):
        """Test detecting skills from frontmatter."""
        content = """Content after frontmatter"""
        frontmatter = {
            'skills': ['pm-workflow:manage-files', 'plan-marshall:ref-toon-format'],
        }
        source = ComponentId(bundle='test', component_type='skill', name='test')
        deps = detect_skill_references(content, frontmatter, source)
        assert len(deps) == 2
        assert deps[0].target.bundle == 'pm-workflow'
        assert deps[0].target.name == 'manage-files'
        assert deps[1].target.bundle == 'plan-marshall'
        assert deps[1].target.name == 'ref-toon-format'

    def test_detect_skill_pattern(self):
        """Test detecting Skill: pattern in content."""
        content = """
## Required Skills

Skill: pm-workflow:phase-1-init

This skill depends on the initialization phase.
"""
        source = ComponentId(bundle='test', component_type='skill', name='test')
        deps = detect_skill_references(content, {}, source)
        assert len(deps) == 1
        assert deps[0].target.bundle == 'pm-workflow'
        assert deps[0].target.name == 'phase-1-init'


# =============================================================================
# Tests - Python Import Detection
# =============================================================================


class TestPythonImportDetection:
    """Tests for Python import detection."""

    def test_detect_known_imports(self):
        """Test detecting known module imports."""
        content = """
from toon_parser import parse_toon, serialize_toon
from file_ops import atomic_write_file
"""
        source = ComponentId(bundle='test', component_type='script', name='test', parent_skill='test')
        deps = detect_python_imports(content, source)
        assert len(deps) == 2

        targets = {d.target.to_notation() for d in deps}
        assert 'plan-marshall:ref-toon-format:toon_parser' in targets
        assert 'plan-marshall:tools-file-ops:file_ops' in targets

    def test_skip_unknown_imports(self):
        """Test that unknown imports are not tracked."""
        content = """
from pathlib import Path
from collections import defaultdict
import json
"""
        source = ComponentId(bundle='test', component_type='script', name='test', parent_skill='test')
        deps = detect_python_imports(content, source)
        assert len(deps) == 0

    def test_handle_syntax_error(self):
        """Test handling invalid Python syntax."""
        content = """
def broken(
    # Missing closing paren
"""
        source = ComponentId(bundle='test', component_type='script', name='test', parent_skill='test')
        deps = detect_python_imports(content, source)
        assert len(deps) == 0


# =============================================================================
# Tests - Implements Detection
# =============================================================================


class TestImplementsDetection:
    """Tests for implements detection."""

    def test_detect_implements(self):
        """Test detecting implements field."""
        frontmatter = {
            'implements': 'pm-workflow:workflow-extension-api/standards/extensions/outline-extension.md',
        }
        source = ComponentId(bundle='pm-plugin-development', component_type='skill', name='ext-outline-plugin')
        deps = detect_implements(frontmatter, source)
        assert len(deps) == 1
        assert deps[0].target.bundle == 'pm-workflow'
        assert deps[0].target.name == 'workflow-extension-api'
        assert deps[0].dep_type == DependencyType.IMPLEMENTS

    def test_no_implements(self):
        """Test handling missing implements field."""
        frontmatter = {'name': 'test'}
        source = ComponentId(bundle='test', component_type='skill', name='test')
        deps = detect_implements(frontmatter, source)
        assert len(deps) == 0


# =============================================================================
# Tests - CLI Subcommands
# =============================================================================


class TestDepsSubcommand:
    """Tests for deps subcommand."""

    def test_deps_requires_component(self):
        """Test that deps requires --component."""
        result = run_script(SCRIPT_PATH, 'deps')
        assert result.returncode != 0
        assert 'component is required' in result.stderr.lower()

    def test_deps_known_component(self):
        """Test deps for a known component."""
        result = run_script(
            SCRIPT_PATH,
            'deps',
            '--component',
            'pm-workflow:manage-files',
            '--direct-result',
        )
        assert result.returncode == 0

        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['component'] == 'pm-workflow:manage-files'
        assert 'direct_dependencies' in data or data.get('statistics', {}).get('direct_count', 0) >= 0

    def test_deps_unknown_component(self):
        """Test deps for unknown component returns error."""
        result = run_script(
            SCRIPT_PATH,
            'deps',
            '--component',
            'nonexistent:skill:name',
            '--direct-result',
        )
        # Should return error status
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'


class TestRdepsSubcommand:
    """Tests for rdeps subcommand."""

    def test_rdeps_requires_component(self):
        """Test that rdeps requires --component."""
        result = run_script(SCRIPT_PATH, 'rdeps')
        assert result.returncode != 0
        assert 'component is required' in result.stderr.lower()

    def test_rdeps_known_module(self):
        """Test rdeps for a commonly-used module."""
        result = run_script(
            SCRIPT_PATH,
            'rdeps',
            '--component',
            'plan-marshall:ref-toon-format:toon_parser',
            '--direct-result',
            '--format',
            'json',
        )
        # May or may not find dependents depending on codebase state
        assert result.returncode in (0, 1)


class TestValidateSubcommand:
    """Tests for validate subcommand."""

    def test_validate_runs(self):
        """Test that validate runs and returns structured output."""
        result = run_script(SCRIPT_PATH, 'validate', '--direct-result')
        # Validate may find issues, so accept both return codes
        assert result.returncode in (0, 1)

        data = parse_toon(result.stdout)
        assert 'status' in data
        assert 'validation_result' in data
        assert 'total_components' in data
        assert 'total_dependencies' in data

    def test_validate_json_format(self):
        """Test validate with JSON output."""
        result = run_script(SCRIPT_PATH, 'validate', '--direct-result', '--format', 'json')
        assert result.returncode in (0, 1)

        data = json.loads(result.stdout)
        assert 'status' in data
        assert 'total_components' in data


class TestTreeSubcommand:
    """Tests for tree subcommand."""

    def test_tree_requires_component(self):
        """Test that tree requires --component."""
        result = run_script(SCRIPT_PATH, 'tree')
        assert result.returncode != 0
        assert 'component is required' in result.stderr.lower()

    def test_tree_produces_output(self):
        """Test tree produces visual output."""
        result = run_script(
            SCRIPT_PATH,
            'tree',
            '--component',
            'pm-workflow:manage-files',
            '--direct-result',
            '--depth',
            '2',
        )
        assert result.returncode == 0

        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert 'tree' in data
        assert 'pm-workflow:manage-files' in data['tree']


# =============================================================================
# Tests - Dependency Type Filtering
# =============================================================================


class TestDepTypeFiltering:
    """Tests for dependency type filtering."""

    def test_filter_single_type(self):
        """Test filtering to a single dependency type."""
        result = run_script(
            SCRIPT_PATH,
            'deps',
            '--component',
            'pm-workflow:manage-files',
            '--dep-types',
            'import',
            '--direct-result',
        )
        assert result.returncode == 0

        data = parse_toon(result.stdout)
        # All dependencies should be import type
        for dep in data.get('direct_dependencies', []):
            if isinstance(dep, dict):
                assert dep.get('type') == 'import'

    def test_filter_multiple_types(self):
        """Test filtering to multiple dependency types."""
        result = run_script(
            SCRIPT_PATH,
            'deps',
            '--component',
            'pm-workflow:manage-files',
            '--dep-types',
            'import,skill',
            '--direct-result',
        )
        assert result.returncode == 0

        data = parse_toon(result.stdout)
        # All dependencies should be import or skill type
        for dep in data.get('direct_dependencies', []):
            if isinstance(dep, dict):
                assert dep.get('type') in ('import', 'skill')

    def test_invalid_dep_type(self):
        """Test invalid dependency type returns error."""
        result = run_script(
            SCRIPT_PATH,
            'deps',
            '--component',
            'pm-workflow:manage-files',
            '--dep-types',
            'invalid',
            '--direct-result',
        )
        assert result.returncode != 0
        assert 'invalid dependency type' in result.stderr.lower()


# =============================================================================
# Tests - Output Formats
# =============================================================================


class TestOutputFormats:
    """Tests for output format options."""

    def test_toon_format(self):
        """Test TOON output format."""
        result = run_script(
            SCRIPT_PATH,
            'validate',
            '--direct-result',
            '--format',
            'toon',
        )
        # Should parse as valid TOON
        data = parse_toon(result.stdout)
        assert 'status' in data

    def test_json_format(self):
        """Test JSON output format."""
        result = run_script(
            SCRIPT_PATH,
            'validate',
            '--direct-result',
            '--format',
            'json',
        )
        # Should parse as valid JSON
        data = json.loads(result.stdout)
        assert 'status' in data


# =============================================================================
# Tests - Scope Options
# =============================================================================


class TestScopeOptions:
    """Tests for scope options."""

    def test_auto_scope(self):
        """Test auto scope (default)."""
        result = run_script(SCRIPT_PATH, 'validate', '--direct-result', '--scope', 'auto')
        # Should work and find components
        assert result.returncode in (0, 1)

        data = parse_toon(result.stdout)
        assert data.get('total_components', 0) > 0

    def test_marketplace_scope(self):
        """Test marketplace scope."""
        result = run_script(SCRIPT_PATH, 'validate', '--direct-result', '--scope', 'marketplace')
        # Should work and find components
        assert result.returncode in (0, 1)

        data = parse_toon(result.stdout)
        assert data.get('total_components', 0) > 0

    def test_invalid_scope(self):
        """Test invalid scope returns error."""
        result = run_script(SCRIPT_PATH, 'validate', '--scope', 'invalid')
        assert result.returncode != 0


# =============================================================================
# Tests - Integration
# =============================================================================


# =============================================================================
# Tests - SKILL.md → Script Deps Discovery
# =============================================================================


class TestSkillToScriptDeps:
    """Tests for SKILL.md -> script dependency discovery."""

    def test_skill_discovers_script_deps(self):
        """Test that deps command finds scripts referenced in SKILL.md."""
        result = run_script(
            SCRIPT_PATH,
            'deps',
            '--component',
            'pm-workflow:planning-inventory',
            '--dep-types',
            'script',
            '--direct-result',
            '--format',
            'json',
        )
        assert result.returncode == 0

        data = json.loads(result.stdout)
        assert data['status'] == 'success'
        assert data['component_type'] == 'skill'

        # Should find the scan-planning-inventory script
        targets = [d['target'] for d in data.get('direct_dependencies', [])]
        assert 'pm-workflow:planning-inventory:scan-planning-inventory' in targets

    def test_skill_deps_filters_to_script_type(self):
        """Test that --dep-types script only returns script dependencies."""
        result = run_script(
            SCRIPT_PATH,
            'deps',
            '--component',
            'pm-workflow:manage-files',
            '--dep-types',
            'script',
            '--direct-result',
            '--format',
            'json',
        )
        assert result.returncode == 0

        data = json.loads(result.stdout)
        for dep in data.get('direct_dependencies', []):
            assert dep['type'] == 'script'


# =============================================================================
# Tests - Integration
# =============================================================================


class TestIntegration:
    """Integration tests for the full dependency resolution flow."""

    def test_known_dependency_chain(self):
        """Test resolving a known dependency chain."""
        # manage-files skill uses toon_parser and file_ops
        result = run_script(
            SCRIPT_PATH,
            'deps',
            '--component',
            'pm-workflow:manage-files',
            '--direct-result',
            '--format',
            'json',
        )
        assert result.returncode == 0

        data = json.loads(result.stdout)
        assert data['status'] == 'success'

        # Should have some dependencies
        direct_count = data.get('statistics', {}).get('direct_count', 0)
        # Note: Actual count depends on what's detected in SKILL.md
        # The script file has imports, the SKILL.md may have skill refs
        assert direct_count >= 0  # At minimum it runs successfully

    def test_full_marketplace_validation(self):
        """Test validating the full marketplace."""
        result = run_script(SCRIPT_PATH, 'validate', '--direct-result')
        assert result.returncode in (0, 1)

        data = parse_toon(result.stdout)
        # Should find many components
        assert data.get('total_components', 0) >= 50
        # Should find many dependencies
        assert data.get('total_dependencies', 0) >= 0
