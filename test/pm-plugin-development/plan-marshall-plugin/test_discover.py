#!/usr/bin/env python3
"""Tests for plugin bundle discovery.

Tests the plugin_discover module that discovers marketplace bundles
and generates module dicts for derived-data.json.
"""

import json
import tempfile
import unittest
from pathlib import Path

from plugin_discover import (
    BUILD_SYSTEM,
    _is_plan_marshall_marketplace,
    build_bundle_module,
    build_commands,
    build_default_module,
    discover_agents,
    discover_bundles,
    discover_commands,
    discover_plugin_modules,
    discover_skills,
    extract_description_from_frontmatter,
    extract_frontmatter,
    load_plugin_json,
)


class TestExtractFrontmatter(unittest.TestCase):
    """Tests for extract_frontmatter function."""

    def test_valid_frontmatter(self):
        """Test extraction of valid YAML frontmatter."""
        content = """---
name: test-skill
description: A test skill
---

# Content here
"""
        has_fm, fm = extract_frontmatter(content)
        self.assertTrue(has_fm)
        self.assertIn('name: test-skill', fm)
        self.assertIn('description: A test skill', fm)

    def test_no_frontmatter(self):
        """Test content without frontmatter."""
        content = '# Just a header\n\nSome content.'
        has_fm, fm = extract_frontmatter(content)
        self.assertFalse(has_fm)
        self.assertEqual(fm, '')

    def test_unclosed_frontmatter(self):
        """Test frontmatter without closing delimiter."""
        content = """---
name: test-skill
description: A test skill

# Content here
"""
        has_fm, fm = extract_frontmatter(content)
        self.assertFalse(has_fm)


class TestExtractDescription(unittest.TestCase):
    """Tests for extract_description_from_frontmatter function."""

    def test_simple_description(self):
        """Test extraction of simple description."""
        fm = 'name: test\ndescription: A simple description'
        desc = extract_description_from_frontmatter(fm)
        self.assertEqual(desc, 'A simple description')

    def test_quoted_description(self):
        """Test extraction of quoted description."""
        fm = 'name: test\ndescription: "A quoted description"'
        desc = extract_description_from_frontmatter(fm)
        self.assertEqual(desc, 'A quoted description')

    def test_no_description(self):
        """Test frontmatter without description field."""
        fm = 'name: test\nuser-invokable: true'
        desc = extract_description_from_frontmatter(fm)
        self.assertIsNone(desc)


class TestBuildCommands(unittest.TestCase):
    """Tests for build_commands function."""

    def test_build_commands(self):
        """Test command generation for a bundle."""
        commands = build_commands('pm-plugin-development')
        # Should generate all 7 canonical commands
        self.assertIn('compile', commands)
        self.assertIn('test-compile', commands)
        self.assertIn('module-tests', commands)
        self.assertIn('quality-gate', commands)
        self.assertIn('verify', commands)
        self.assertIn('coverage', commands)
        self.assertIn('clean', commands)
        # Commands should use python_build via execute-script
        self.assertIn('pm-dev-python:plan-marshall-plugin:python_build', commands['module-tests'])
        self.assertIn('pm-plugin-development', commands['module-tests'])


class TestBuildDefaultModule(unittest.TestCase):
    """Tests for build_default_module function."""

    def test_default_module_structure(self):
        """Test default module has required fields."""
        # Use project root for realistic paths
        project_root = Path(__file__).parent.parent.parent.parent
        module = build_default_module(project_root, 8)

        self.assertEqual(module['name'], 'default')
        self.assertEqual(module['build_systems'], [BUILD_SYSTEM])
        self.assertEqual(module['paths']['module'], '.')
        self.assertEqual(module['paths']['descriptor'], 'marketplace/.claude-plugin/marketplace.json')
        self.assertEqual(module['stats']['bundle_count'], 8)
        # Default module should have all 7 canonical commands
        self.assertIn('compile', module['commands'])
        self.assertIn('module-tests', module['commands'])
        self.assertIn('verify', module['commands'])
        # Commands should use python_build via execute-script
        self.assertIn('pm-dev-python:plan-marshall-plugin:python_build', module['commands']['module-tests'])


class TestDiscoverBundles(unittest.TestCase):
    """Tests for discover_bundles function."""

    def test_discover_bundles_in_project(self):
        """Test discovery finds bundles in real marketplace."""
        project_root = Path(__file__).parent.parent.parent.parent
        bundles = discover_bundles(str(project_root))

        # Should find multiple bundles
        self.assertGreater(len(bundles), 0)

        # All results should be plugin.json paths
        for bundle_path in bundles:
            self.assertTrue(bundle_path.name == 'plugin.json')
            self.assertTrue(bundle_path.exists())

    def test_discover_bundles_nonexistent(self):
        """Test discovery returns empty for nonexistent path."""
        bundles = discover_bundles('/nonexistent/path')
        self.assertEqual(bundles, [])


class TestLoadPluginJson(unittest.TestCase):
    """Tests for load_plugin_json function."""

    def test_load_valid_plugin_json(self):
        """Test loading a valid plugin.json file."""
        project_root = Path(__file__).parent.parent.parent.parent
        plugin_path = (
            project_root / 'marketplace' / 'bundles' / 'pm-plugin-development' / '.claude-plugin' / 'plugin.json'
        )

        if plugin_path.exists():
            data = load_plugin_json(plugin_path)
            self.assertIsNotNone(data)
            self.assertIn('name', data)
            self.assertEqual(data['name'], 'pm-plugin-development')

    def test_load_nonexistent_file(self):
        """Test loading nonexistent file returns None."""
        data = load_plugin_json(Path('/nonexistent/plugin.json'))
        self.assertIsNone(data)


class TestDiscoverSkills(unittest.TestCase):
    """Tests for discover_skills function."""

    def test_discover_skills_from_plugin_data(self):
        """Test skill discovery from plugin.json data."""
        project_root = Path(__file__).parent.parent.parent.parent
        bundle_dir = project_root / 'marketplace' / 'bundles' / 'pm-plugin-development'
        plugin_path = bundle_dir / '.claude-plugin' / 'plugin.json'

        if plugin_path.exists():
            plugin_data = load_plugin_json(plugin_path)
            packages = discover_skills(bundle_dir, plugin_data)

            # Should find skills
            self.assertGreater(len(packages), 0)

            # All keys should have skill: prefix
            for key in packages:
                self.assertTrue(key.startswith('skill:'))

            # Each package should have type and path
            for pkg in packages.values():
                self.assertEqual(pkg['type'], 'skill')
                self.assertIn('path', pkg)


class TestDiscoverAgents(unittest.TestCase):
    """Tests for discover_agents function."""

    def test_discover_agents_from_plugin_data(self):
        """Test agent discovery from plugin.json data."""
        project_root = Path(__file__).parent.parent.parent.parent
        bundle_dir = project_root / 'marketplace' / 'bundles' / 'pm-plugin-development'
        plugin_path = bundle_dir / '.claude-plugin' / 'plugin.json'

        if plugin_path.exists():
            plugin_data = load_plugin_json(plugin_path)
            packages = discover_agents(bundle_dir, plugin_data)

            # pm-plugin-development has at least one agent
            if packages:
                for key in packages:
                    self.assertTrue(key.startswith('agent:'))
                for pkg in packages.values():
                    self.assertEqual(pkg['type'], 'agent')


class TestDiscoverCommands(unittest.TestCase):
    """Tests for discover_commands function."""

    def test_discover_commands_from_plugin_data(self):
        """Test command discovery from plugin.json data."""
        project_root = Path(__file__).parent.parent.parent.parent
        bundle_dir = project_root / 'marketplace' / 'bundles' / 'pm-plugin-development'
        plugin_path = bundle_dir / '.claude-plugin' / 'plugin.json'

        if plugin_path.exists():
            plugin_data = load_plugin_json(plugin_path)
            packages = discover_commands(bundle_dir, plugin_data)

            # Should find commands
            self.assertGreater(len(packages), 0)

            for key in packages:
                self.assertTrue(key.startswith('command:'))
            for pkg in packages.values():
                self.assertEqual(pkg['type'], 'command')


class TestBuildBundleModule(unittest.TestCase):
    """Tests for build_bundle_module function."""

    def test_build_bundle_module_structure(self):
        """Test module structure from real bundle."""
        project_root = Path(__file__).parent.parent.parent.parent
        bundle_dir = project_root / 'marketplace' / 'bundles' / 'pm-plugin-development'
        plugin_path = bundle_dir / '.claude-plugin' / 'plugin.json'

        if plugin_path.exists():
            plugin_data = load_plugin_json(plugin_path)
            module = build_bundle_module(plugin_path, project_root, plugin_data)

            # Check required fields
            self.assertEqual(module['name'], 'pm-plugin-development')
            self.assertEqual(module['build_systems'], [BUILD_SYSTEM])

            # Check paths
            self.assertIn('paths', module)
            self.assertEqual(module['paths']['module'], 'marketplace/bundles/pm-plugin-development')
            self.assertTrue(module['paths']['descriptor'].endswith('plugin.json'))

            # Check metadata
            self.assertIn('metadata', module)
            self.assertEqual(module['metadata']['bundle_name'], 'pm-plugin-development')

            # Check packages exist
            self.assertIn('packages', module)
            self.assertGreater(len(module['packages']), 0)

            # Check stats
            self.assertIn('stats', module)
            self.assertIn('skill_count', module['stats'])

            # Check commands
            self.assertIn('commands', module)
            self.assertIn('module-tests', module['commands'])
            self.assertIn('quality-gate', module['commands'])


class TestDiscoverPluginModules(unittest.TestCase):
    """Tests for discover_plugin_modules function."""

    def test_discover_plugin_modules_integration(self):
        """Integration test against real marketplace."""
        project_root = Path(__file__).parent.parent.parent.parent
        modules = discover_plugin_modules(str(project_root))

        # Should have default module plus bundles
        self.assertGreater(len(modules), 1)

        # First module should be default
        self.assertEqual(modules[0]['name'], 'default')

        # All modules should have required structure
        for module in modules:
            self.assertIn('name', module)
            self.assertIn('build_systems', module)
            self.assertIn('paths', module)
            self.assertIn('metadata', module)
            self.assertIn('packages', module)
            self.assertIn('dependencies', module)
            self.assertIn('stats', module)
            self.assertIn('commands', module)

    def test_discover_plugin_modules_nonexistent(self):
        """Test discovery on path without marketplace."""
        modules = discover_plugin_modules('/tmp')
        # Should return empty list - not plan-marshall marketplace
        self.assertEqual(modules, [])


class TestMarketplaceCheck(unittest.TestCase):
    """Tests for plan-marshall marketplace detection."""

    def test_is_plan_marshall_marketplace_true(self):
        """Test detection of plan-marshall marketplace."""
        project_root = Path(__file__).parent.parent.parent.parent
        # Real project should be plan-marshall
        self.assertTrue(_is_plan_marshall_marketplace(str(project_root)))

    def test_is_plan_marshall_marketplace_false_no_file(self):
        """Test returns False when marketplace.json doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertFalse(_is_plan_marshall_marketplace(temp_dir))

    def test_is_plan_marshall_marketplace_false_different_name(self):
        """Test returns False for different marketplace name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            marketplace_dir = Path(temp_dir) / 'marketplace' / '.claude-plugin'
            marketplace_dir.mkdir(parents=True)
            marketplace_json = marketplace_dir / 'marketplace.json'
            marketplace_json.write_text(json.dumps({'name': 'other-marketplace', 'version': '1.0.0'}))

            self.assertFalse(_is_plan_marshall_marketplace(temp_dir))

    def test_is_plan_marshall_marketplace_true_with_plan_marshall_name(self):
        """Test returns True for plan-marshall name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            marketplace_dir = Path(temp_dir) / 'marketplace' / '.claude-plugin'
            marketplace_dir.mkdir(parents=True)
            marketplace_json = marketplace_dir / 'marketplace.json'
            marketplace_json.write_text(json.dumps({'name': 'plan-marshall', 'version': '1.0.0'}))

            self.assertTrue(_is_plan_marshall_marketplace(temp_dir))

    def test_discover_plugin_modules_returns_empty_for_non_plan_marshall(self):
        """discover_plugin_modules returns [] for non-plan-marshall projects.

        This extension is specific to plan-marshall marketplace.
        Other Python projects are handled by pm-dev-python instead.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create marketplace.json with different name
            marketplace_dir = Path(temp_dir) / 'marketplace' / '.claude-plugin'
            marketplace_dir.mkdir(parents=True)
            marketplace_json = marketplace_dir / 'marketplace.json'
            marketplace_json.write_text(json.dumps({'name': 'other-marketplace', 'version': '1.0.0'}))

            # Even with a valid bundles directory, should return []
            bundles_dir = Path(temp_dir) / 'marketplace' / 'bundles' / 'test-bundle' / '.claude-plugin'
            bundles_dir.mkdir(parents=True)
            (bundles_dir / 'plugin.json').write_text(json.dumps({'name': 'test-bundle', 'version': '1.0.0'}))

            modules = discover_plugin_modules(temp_dir)
            self.assertEqual(modules, [])


if __name__ == '__main__':
    unittest.main()
