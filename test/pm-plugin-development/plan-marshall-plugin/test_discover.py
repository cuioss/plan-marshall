#!/usr/bin/env python3
"""Tests for plugin bundle discovery.

Tests the plugin_discover module that discovers marketplace bundles
and produces the per-bundle module dicts that ``manage-architecture``
persists into the per-module architecture layout
(``_project.json`` plus one ``{module}/derived.json`` per indexed
module under ``.plan/project-architecture/``). The
``_project.json["modules"]`` index is the source of truth — orphan
per-module directories are ignored.
"""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from plugin_discover import (
    BUILD_SYSTEM,
    _is_plan_marshall_marketplace,
    build_bundle_module,
    build_commands,
    discover_agents,
    discover_bundles,
    discover_commands,
    discover_plugin_modules,
    discover_skills,
    extract_description_from_frontmatter,
    extract_frontmatter,
    load_plugin_json,
)

# =============================================================================
# Cross-skill loader: import ``_architecture_core`` for layout fixtures.
#
# ``manage-architecture`` is the canonical writer of the per-module layout.
# We re-use its save_* helpers here so test fixtures stay in lock-step with
# the production persistence contract — if the on-disk shape ever changes,
# this import will fail loudly instead of letting these tests drift.
# =============================================================================

_ARCH_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-architecture'
    / 'scripts'
)


def _load_arch_core():
    spec = importlib.util.spec_from_file_location(
        '_architecture_core', _ARCH_SCRIPTS_DIR / '_architecture_core.py'
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules['_architecture_core'] = mod
    spec.loader.exec_module(mod)
    return mod


_architecture_core = _load_arch_core()


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
        fm = 'name: test\nuser-invocable: true'
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
        self.assertIn('plan-marshall:build-python:python_build', commands['module-tests'])
        self.assertIn('pm-plugin-development', commands['module-tests'])


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

            # pm-plugin-development may have zero commands; when present, validate shape.
            if packages:
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

        # Should have bundle modules (no default root module — that comes from Python discovery)
        self.assertGreater(len(modules), 0)

        # All modules should be bundle modules with marshall-plugin build system
        for module in modules:
            self.assertIn('name', module)
            self.assertIn('build_systems', module)
            self.assertEqual(module['build_systems'], [BUILD_SYSTEM])
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


class TestPerModuleLayoutFixtures(unittest.TestCase):
    """Exercise the per-module architecture layout end-to-end.

    Each test seeds a top-level ``_project.json`` plus one
    ``{module}/derived.json`` per indexed module using the canonical
    ``manage-architecture`` save helpers, then asserts the layout matches
    the contract that ``_project.json["modules"]`` is the source of truth
    and orphan per-module directories are ignored.
    """

    def _seed_layout(self, tmp_root: Path, modules: dict[str, dict]) -> None:
        """Write ``_project.json`` plus per-module ``derived.json`` files."""
        _architecture_core.save_project_meta(
            {
                'name': 'test-project',
                'description': '',
                'description_reasoning': '',
                'extensions_used': ['pm-plugin-development'],
                'modules': {name: {} for name in modules},
            },
            str(tmp_root),
        )
        for name, derived in modules.items():
            _architecture_core.save_module_derived(name, derived, str(tmp_root))

    def test_seeded_layout_round_trips_via_iter_modules(self):
        """``_project.json["modules"]`` is the canonical iteration index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            modules = {
                'pm-plugin-development': {
                    'name': 'pm-plugin-development',
                    'build_systems': [BUILD_SYSTEM],
                    'paths': {'module': 'marketplace/bundles/pm-plugin-development'},
                    'metadata': {'bundle_name': 'pm-plugin-development'},
                    'packages': {'skill:plugin-doctor': {'type': 'skill', 'path': 'skills/plugin-doctor'}},
                    'dependencies': [],
                    'stats': {'skill_count': 1, 'agent_count': 0, 'command_count': 0},
                    'commands': build_commands('pm-plugin-development'),
                },
                'plan-marshall': {
                    'name': 'plan-marshall',
                    'build_systems': [BUILD_SYSTEM],
                    'paths': {'module': 'marketplace/bundles/plan-marshall'},
                    'metadata': {'bundle_name': 'plan-marshall'},
                    'packages': {},
                    'dependencies': [],
                    'stats': {'skill_count': 0, 'agent_count': 0, 'command_count': 0},
                    'commands': build_commands('plan-marshall'),
                },
            }
            self._seed_layout(tmp_root, modules)

            iterated = list(_architecture_core.iter_modules(str(tmp_root)))
            self.assertEqual(sorted(iterated), ['plan-marshall', 'pm-plugin-development'])

            for name, expected in modules.items():
                loaded = _architecture_core.load_module_derived(name, str(tmp_root))
                self.assertEqual(loaded, expected)

    def test_orphan_module_directory_is_ignored(self):
        """Per-module dirs absent from ``_project.json["modules"]`` are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            modules = {
                'pm-plugin-development': {
                    'name': 'pm-plugin-development',
                    'build_systems': [BUILD_SYSTEM],
                    'paths': {'module': 'marketplace/bundles/pm-plugin-development'},
                    'metadata': {'bundle_name': 'pm-plugin-development'},
                    'packages': {},
                    'dependencies': [],
                    'stats': {'skill_count': 0, 'agent_count': 0, 'command_count': 0},
                    'commands': build_commands('pm-plugin-development'),
                },
            }
            self._seed_layout(tmp_root, modules)

            # Drop a stray module directory NOT listed in _project.json["modules"].
            arch_dir = tmp_root / _architecture_core.DATA_DIR
            stray_dir = arch_dir / 'orphan-bundle'
            stray_dir.mkdir(parents=True)
            (stray_dir / 'derived.json').write_text(json.dumps({'name': 'orphan-bundle'}))

            iterated = list(_architecture_core.iter_modules(str(tmp_root)))
            self.assertEqual(iterated, ['pm-plugin-development'])
            self.assertNotIn('orphan-bundle', iterated)

    def test_layout_paths_match_contract(self):
        """Seeded files land at the documented per-module paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            modules = {
                'pm-plugin-development': {
                    'name': 'pm-plugin-development',
                    'build_systems': [BUILD_SYSTEM],
                    'paths': {'module': 'marketplace/bundles/pm-plugin-development'},
                    'metadata': {'bundle_name': 'pm-plugin-development'},
                    'packages': {},
                    'dependencies': [],
                    'stats': {'skill_count': 0, 'agent_count': 0, 'command_count': 0},
                    'commands': build_commands('pm-plugin-development'),
                },
            }
            self._seed_layout(tmp_root, modules)

            arch_dir = tmp_root / _architecture_core.DATA_DIR
            self.assertTrue((arch_dir / '_project.json').is_file())
            self.assertTrue((arch_dir / 'pm-plugin-development' / 'derived.json').is_file())


if __name__ == '__main__':
    unittest.main()
