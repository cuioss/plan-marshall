#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for plugin bundle discovery.

Tests the plugin_discover module that discovers marketplace bundles
and produces the per-bundle module dicts that ``manage-architecture``
persists into the per-module architecture layout
(``_project.json`` plus one ``{module}/derived.json`` per indexed
module under ``.plan/project-architecture/``). The
``_project.json["modules"]`` index is the source of truth — orphan
per-module directories are ignored.
"""

import json
import tempfile
from pathlib import Path

import plugin_discover
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

from conftest import load_script_module

# =============================================================================
# Cross-skill loader: import ``_architecture_core`` for layout fixtures.
#
# ``manage-architecture`` is the canonical writer of the per-module layout.
# We re-use its save_* helpers here so test fixtures stay in lock-step with
# the production persistence contract — if the on-disk shape ever changes,
# this import will fail loudly instead of letting these tests drift.
# =============================================================================


def _load_arch_core():
    return load_script_module('plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core')


_architecture_core = _load_arch_core()


# =============================================================================
# extract_frontmatter
#
# ``plugin_discover`` consumes the single canonical parser (imported from
# ``_dep_detection``), which returns the ``Frontmatter(present, raw, fields)``
# superset record. ``get_component_description`` reads ``.present``/``.raw``;
# these tests unpack the leading ``(present, raw)`` pair and discard ``fields``.
# =============================================================================


def test_valid_frontmatter():
    """Test extraction of valid YAML frontmatter."""
    content = """---
name: test-skill
description: A test skill
---

# Content here
"""

    has_fm, fm, _fields = extract_frontmatter(content)

    assert has_fm
    assert 'name: test-skill' in fm
    assert 'description: A test skill' in fm


def test_no_frontmatter():
    """Test content without frontmatter."""
    content = '# Just a header\n\nSome content.'

    has_fm, fm, _fields = extract_frontmatter(content)

    assert has_fm is False
    assert fm == ''


def test_unclosed_frontmatter():
    """Test frontmatter without closing delimiter."""
    content = """---
name: test-skill
description: A test skill

# Content here
"""

    has_fm, fm, _fields = extract_frontmatter(content)

    assert has_fm is False


# =============================================================================
# extract_description_from_frontmatter
# =============================================================================


def test_simple_description():
    """Test extraction of simple description."""
    fm = 'name: test\ndescription: A simple description'

    desc = extract_description_from_frontmatter(fm)

    assert desc == 'A simple description'


def test_quoted_description():
    """Test extraction of quoted description."""
    fm = 'name: test\ndescription: "A quoted description"'

    desc = extract_description_from_frontmatter(fm)

    assert desc == 'A quoted description'


def test_no_description():
    """Test frontmatter without description field."""
    fm = 'name: test\nuser-invocable: true'

    desc = extract_description_from_frontmatter(fm)

    assert desc is None


# =============================================================================
# build_commands
# =============================================================================


def test_build_commands():
    """Test command generation for a bundle."""
    commands = build_commands('pm-plugin-development')

    # Should generate all 7 canonical commands
    assert 'compile' in commands
    assert 'test-compile' in commands
    assert 'module-tests' in commands
    assert 'quality-gate' in commands
    assert 'verify' in commands
    assert 'coverage' in commands
    assert 'clean' in commands
    # Commands should use pyproject_build via execute-script
    assert 'plan-marshall:build-pyproject:pyproject_build' in commands['module-tests']
    assert 'pm-plugin-development' in commands['module-tests']


# =============================================================================
# discover_bundles
# =============================================================================


def test_discover_bundles_in_project():
    """Test discovery finds bundles in real marketplace."""
    project_root = Path(__file__).parent.parent.parent.parent

    bundles = discover_bundles(str(project_root))

    assert len(bundles) > 0
    for bundle_path in bundles:
        assert bundle_path.name == 'plugin.json'
        assert bundle_path.exists()


def test_discover_bundles_nonexistent():
    """Test discovery returns empty for nonexistent path."""
    bundles = discover_bundles('/nonexistent/path')

    assert bundles == []


# =============================================================================
# load_plugin_json
# =============================================================================


def test_load_valid_plugin_json():
    """Test loading a valid plugin.json file."""
    project_root = Path(__file__).parent.parent.parent.parent
    plugin_path = (
        project_root / 'marketplace' / 'bundles' / 'pm-plugin-development' / '.claude-plugin' / 'plugin.json'
    )

    if plugin_path.exists():
        data = load_plugin_json(plugin_path)
        assert data is not None
        assert 'name' in data
        assert data['name'] == 'pm-plugin-development'


def test_load_nonexistent_file():
    """Test loading nonexistent file returns None."""
    data = load_plugin_json(Path('/nonexistent/plugin.json'))

    assert data is None


# =============================================================================
# discover_skills
# =============================================================================


def test_discover_skills_from_plugin_data():
    """Test skill discovery from plugin.json data."""
    project_root = Path(__file__).parent.parent.parent.parent
    bundle_dir = project_root / 'marketplace' / 'bundles' / 'pm-plugin-development'
    plugin_path = bundle_dir / '.claude-plugin' / 'plugin.json'

    if plugin_path.exists():
        plugin_data = load_plugin_json(plugin_path)
        packages = discover_skills(bundle_dir, plugin_data)

        assert len(packages) > 0
        for key in packages:
            assert key.startswith('skill:')
        for pkg in packages.values():
            assert pkg['type'] == 'skill'
            assert 'path' in pkg


# =============================================================================
# discover_agents
# =============================================================================


def test_discover_agents_from_plugin_data():
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
                assert key.startswith('agent:')
            for pkg in packages.values():
                assert pkg['type'] == 'agent'


# =============================================================================
# discover_commands
# =============================================================================


def test_discover_commands_from_plugin_data():
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
                assert key.startswith('command:')
            for pkg in packages.values():
                assert pkg['type'] == 'command'


# =============================================================================
# build_bundle_module
# =============================================================================


def test_build_bundle_module_structure():
    """Test module structure from real bundle."""
    project_root = Path(__file__).parent.parent.parent.parent
    bundle_dir = project_root / 'marketplace' / 'bundles' / 'pm-plugin-development'
    plugin_path = bundle_dir / '.claude-plugin' / 'plugin.json'

    if plugin_path.exists():
        plugin_data = load_plugin_json(plugin_path)
        module = build_bundle_module(plugin_path, project_root, plugin_data)

        assert module['name'] == 'pm-plugin-development'
        assert module['build_systems'] == [BUILD_SYSTEM]

        assert 'paths' in module
        assert module['paths']['module'] == 'marketplace/bundles/pm-plugin-development'
        assert module['paths']['descriptor'].endswith('plugin.json')

        assert 'metadata' in module
        assert module['metadata']['bundle_name'] == 'pm-plugin-development'

        assert 'packages' in module
        assert len(module['packages']) > 0

        assert 'stats' in module
        assert 'skill_count' in module['stats']

        assert 'commands' in module
        assert 'module-tests' in module['commands']
        assert 'quality-gate' in module['commands']


# =============================================================================
# discover_plugin_modules
# =============================================================================


def test_discover_plugin_modules_integration():
    """Integration test against real marketplace."""
    project_root = Path(__file__).parent.parent.parent.parent

    modules = discover_plugin_modules(str(project_root))

    # Should have bundle modules (no default root module — that comes from Python discovery)
    assert len(modules) > 0
    for module in modules:
        assert 'name' in module
        assert 'build_systems' in module
        assert module['build_systems'] == [BUILD_SYSTEM]
        assert 'paths' in module
        assert 'metadata' in module
        assert 'packages' in module
        assert 'dependencies' in module
        assert 'stats' in module
        assert 'commands' in module


def test_discover_plugin_modules_nonexistent():
    """Test discovery on path without marketplace."""
    modules = discover_plugin_modules('/tmp')

    # Should return empty list - not plan-marshall marketplace
    assert modules == []


# =============================================================================
# plan-marshall marketplace detection
# =============================================================================


def test_is_plan_marshall_marketplace_true():
    """Test detection of plan-marshall marketplace."""
    project_root = Path(__file__).parent.parent.parent.parent

    # Real project should be plan-marshall
    assert _is_plan_marshall_marketplace(str(project_root))


def test_is_plan_marshall_marketplace_false_no_file():
    """Test returns False when marketplace.json doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        assert _is_plan_marshall_marketplace(temp_dir) is False


def test_is_plan_marshall_marketplace_false_different_name():
    """Test returns False for different marketplace name."""
    with tempfile.TemporaryDirectory() as temp_dir:
        marketplace_dir = Path(temp_dir) / 'marketplace' / '.claude-plugin'
        marketplace_dir.mkdir(parents=True)
        marketplace_json = marketplace_dir / 'marketplace.json'
        marketplace_json.write_text(json.dumps({'name': 'other-marketplace', 'version': '1.0.0'}))

        assert _is_plan_marshall_marketplace(temp_dir) is False


def test_is_plan_marshall_marketplace_true_with_plan_marshall_name():
    """Test returns True for plan-marshall name."""
    with tempfile.TemporaryDirectory() as temp_dir:
        marketplace_dir = Path(temp_dir) / 'marketplace' / '.claude-plugin'
        marketplace_dir.mkdir(parents=True)
        marketplace_json = marketplace_dir / 'marketplace.json'
        marketplace_json.write_text(json.dumps({'name': 'plan-marshall', 'version': '1.0.0'}))

        assert _is_plan_marshall_marketplace(temp_dir)


def test_discover_plugin_modules_returns_empty_for_non_plan_marshall():
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
        assert modules == []


# =============================================================================
# Per-module architecture layout fixtures
#
# Each test seeds a top-level ``_project.json`` plus one
# ``{module}/derived.json`` per indexed module using the canonical
# ``manage-architecture`` save helpers, then asserts the layout matches
# the contract that ``_project.json["modules"]`` is the source of truth
# and orphan per-module directories are ignored.
# =============================================================================


def _seed_layout(tmp_root: Path, modules: dict[str, dict]) -> None:
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


def test_seeded_layout_round_trips_via_iter_modules():
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
        _seed_layout(tmp_root, modules)

        iterated = list(_architecture_core.iter_modules(str(tmp_root)))
        assert sorted(iterated) == ['plan-marshall', 'pm-plugin-development']

        for name, expected in modules.items():
            loaded = _architecture_core.load_module_derived(name, str(tmp_root))
            assert loaded == expected


def test_orphan_module_directory_is_surfaced():
    """Under the on-demand crawl model, per-module dirs on disk are surfaced
    even when absent from ``_project.json["modules"]`` — the index is no
    longer the gatekeeper. The disk-fallback path returns every directory
    with a ``derived.json``; the project-meta index is consulted via
    ``load_project_meta`` when callers need the curated view.
    """
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
        _seed_layout(tmp_root, modules)

        # Drop a stray module directory NOT listed in _project.json["modules"].
        arch_dir = tmp_root / _architecture_core.DATA_DIR
        stray_dir = arch_dir / 'orphan-bundle'
        stray_dir.mkdir(parents=True)
        (stray_dir / 'derived.json').write_text(json.dumps({'name': 'orphan-bundle'}))

        iterated = list(_architecture_core.iter_modules(str(tmp_root)))
        assert 'pm-plugin-development' in iterated
        assert 'orphan-bundle' in iterated


def test_layout_paths_match_contract():
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
        _seed_layout(tmp_root, modules)

        arch_dir = tmp_root / _architecture_core.DATA_DIR
        assert (arch_dir / '_project.json').is_file()
        assert (arch_dir / 'pm-plugin-development' / 'derived.json').is_file()


# =============================================================================
# Extension API path resolution
#
# The ``EXTENSION_API_DIR`` anchor is resolved via the validated
# bundles-root helper plus ``resolve_bundle_path`` (no bare
# ``BUNDLES_DIR / 'plan-marshall' / 'skills' / ...`` concatenation).
# =============================================================================


def test_extension_api_dir_resolves_to_real_scripts_dir():
    """``EXTENSION_API_DIR`` points at the real extension-api scripts dir
    under the resolved bundles root.
    """
    extension_api_dir = plugin_discover.EXTENSION_API_DIR

    assert extension_api_dir.is_dir()
    assert extension_api_dir.name == 'scripts'
    assert extension_api_dir.parent.name == 'extension-api'


def test_resolve_bundle_path_prefers_version_pinned_cache_layout():
    """The rerouted call shape honours the version-pinned plugin-cache
    layout for the extension-api subpath.
    """
    from marketplace_bundles import resolve_bundle_path

    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        subpath = 'skills/extension-api/scripts'
        versioned = base / 'plan-marshall' / '0.1-BETA' / 'skills' / 'extension-api' / 'scripts'
        versioned.mkdir(parents=True)

        resolved = resolve_bundle_path(base, 'plan-marshall', subpath)

        assert resolved == versioned


def test_resolve_bundle_path_falls_back_to_non_versioned_layout():
    """When no version subdir holds the subpath, the non-versioned
    marketplace join is returned (source-checkout layout).
    """
    from marketplace_bundles import resolve_bundle_path

    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        subpath = 'skills/extension-api/scripts'

        resolved = resolve_bundle_path(base, 'plan-marshall', subpath)

        assert resolved == base / 'plan-marshall' / subpath
