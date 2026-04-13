"""Tests for marketplace_bundles shared module."""

from pathlib import Path

import pytest
from marketplace_bundles import (
    build_pythonpath,
    collect_script_dirs,
    extract_bundle_name,
    find_bundles,
    resolve_bundle_path,
    resolve_bundles_root,
    resolve_skills_root,
)


def _create_bundle(base: Path, name: str, version: str | None = None) -> Path:
    """Helper to create a bundle directory with plugin.json."""
    if version:
        bundle_dir = base / name / version
    else:
        bundle_dir = base / name
    plugin_dir = bundle_dir / '.claude-plugin'
    plugin_dir.mkdir(parents=True)
    (plugin_dir / 'plugin.json').write_text('{}')
    return bundle_dir


class TestFindBundles:
    def test_finds_marketplace_bundles(self, tmp_path):
        _create_bundle(tmp_path, 'bundle-a')
        _create_bundle(tmp_path, 'bundle-b')
        result = find_bundles(tmp_path)
        names = [b.name for b in result]
        assert 'bundle-a' in names
        assert 'bundle-b' in names

    def test_finds_versioned_bundles(self, tmp_path):
        _create_bundle(tmp_path, 'bundle-a', '0.1-BETA')
        result = find_bundles(tmp_path)
        assert len(result) == 1
        assert result[0].name == '0.1-BETA'

    def test_empty_directory(self, tmp_path):
        assert find_bundles(tmp_path) == []


class TestExtractBundleName:
    def test_marketplace_structure(self, tmp_path):
        bundle = tmp_path / 'plan-marshall'
        bundle.mkdir()
        assert extract_bundle_name(bundle) == 'plan-marshall'

    def test_versioned_cache_structure(self, tmp_path):
        version_dir = tmp_path / 'plan-marshall' / '0.1-BETA'
        version_dir.mkdir(parents=True)
        assert extract_bundle_name(version_dir) == 'plan-marshall'

    def test_numeric_version_pattern(self, tmp_path):
        version_dir = tmp_path / 'my-bundle' / '2.0.0-rc1'
        version_dir.mkdir(parents=True)
        assert extract_bundle_name(version_dir) == 'my-bundle'


class TestResolveBundlePath:
    def test_marketplace_structure(self, tmp_path):
        target = tmp_path / 'plan-marshall' / 'skills' / 'foo' / 'bar.py'
        target.parent.mkdir(parents=True)
        target.write_text('content')
        result = resolve_bundle_path(tmp_path, 'plan-marshall', 'skills/foo/bar.py')
        assert result == target

    def test_versioned_structure(self, tmp_path):
        target = tmp_path / 'plan-marshall' / '0.1-BETA' / 'skills' / 'foo' / 'bar.py'
        target.parent.mkdir(parents=True)
        target.write_text('content')
        result = resolve_bundle_path(tmp_path, 'plan-marshall', 'skills/foo/bar.py')
        assert result == target

    def test_nonexistent_returns_fallback_path(self, tmp_path):
        result = resolve_bundle_path(tmp_path, 'missing', 'some/path')
        assert result == tmp_path / 'missing' / 'some' / 'path'


class TestCollectScriptDirs:
    def test_marketplace_structure(self, tmp_path):
        scripts = tmp_path / 'bundle-a' / 'skills' / 'skill-x' / 'scripts'
        scripts.mkdir(parents=True)
        result = collect_script_dirs(tmp_path)
        assert str(scripts) in result

    def test_includes_subdirs(self, tmp_path):
        scripts = tmp_path / 'bundle-a' / 'skills' / 'skill-x' / 'scripts'
        subdir = scripts / 'build'
        subdir.mkdir(parents=True)
        result = collect_script_dirs(tmp_path)
        assert str(scripts) in result
        assert str(subdir) in result

    def test_excludes_pycache(self, tmp_path):
        scripts = tmp_path / 'bundle-a' / 'skills' / 'skill-x' / 'scripts'
        pycache = scripts / '__pycache__'
        pycache.mkdir(parents=True)
        result = collect_script_dirs(tmp_path)
        assert str(pycache) not in result

    def test_versioned_structure(self, tmp_path):
        scripts = tmp_path / 'bundle-a' / '1.0' / 'skills' / 'skill-x' / 'scripts'
        scripts.mkdir(parents=True)
        # Need a skills dir for version detection
        result = collect_script_dirs(tmp_path)
        assert str(scripts) in result


class TestResolveBundlesRoot:
    def test_source_layout(self, tmp_path):
        # tmp_path/marketplace/bundles/plan-marshall/.claude-plugin/plugin.json
        bundles = tmp_path / 'marketplace' / 'bundles'
        plan_marshall = bundles / 'plan-marshall'
        (plan_marshall / '.claude-plugin').mkdir(parents=True)
        (plan_marshall / '.claude-plugin' / 'plugin.json').write_text('{}')
        script = plan_marshall / 'skills' / 'foo' / 'scripts' / 'bar.py'
        script.parent.mkdir(parents=True)
        script.write_text('# script')
        assert resolve_bundles_root(script) == bundles

    def test_cache_layout(self, tmp_path):
        # tmp_path/cache/plan-marshall/0.1-BETA/.claude-plugin/plugin.json
        cache = tmp_path / 'cache'
        version_dir = cache / 'plan-marshall' / '0.1-BETA'
        (version_dir / '.claude-plugin').mkdir(parents=True)
        (version_dir / '.claude-plugin' / 'plugin.json').write_text('{}')
        script = version_dir / 'skills' / 'foo' / 'scripts' / 'bar.py'
        script.parent.mkdir(parents=True)
        script.write_text('# script')
        assert resolve_bundles_root(script) == cache

    def test_raises_outside_bundle(self, tmp_path):
        script = tmp_path / 'a' / 'b' / 'c.py'
        script.parent.mkdir(parents=True)
        script.write_text('# script')
        with pytest.raises(RuntimeError, match='resolve_bundles_root'):
            resolve_bundles_root(script)


class TestResolveSkillsRoot:
    def test_happy_path(self, tmp_path):
        bundle = tmp_path / 'marketplace' / 'bundles' / 'plan-marshall'
        (bundle / '.claude-plugin').mkdir(parents=True)
        (bundle / '.claude-plugin' / 'plugin.json').write_text('{}')
        script = bundle / 'skills' / 'foo' / 'scripts' / 'bar.py'
        script.parent.mkdir(parents=True)
        script.write_text('# script')
        assert resolve_skills_root(script) == bundle / 'skills'

    def test_cache_layout(self, tmp_path):
        version_dir = tmp_path / 'cache' / 'plan-marshall' / '0.1-BETA'
        (version_dir / '.claude-plugin').mkdir(parents=True)
        (version_dir / '.claude-plugin' / 'plugin.json').write_text('{}')
        script = version_dir / 'skills' / 'foo' / 'scripts' / 'bar.py'
        script.parent.mkdir(parents=True)
        script.write_text('# script')
        assert resolve_skills_root(script) == version_dir / 'skills'

    def test_raises_outside_skill(self, tmp_path):
        # 'skills' dir exists but no sibling .claude-plugin/plugin.json
        skills = tmp_path / 'random' / 'skills'
        script = skills / 'foo' / 'bar.py'
        script.parent.mkdir(parents=True)
        script.write_text('# script')
        with pytest.raises(RuntimeError, match='resolve_skills_root'):
            resolve_skills_root(script)

    def test_raises_when_no_skills_ancestor(self, tmp_path):
        script = tmp_path / 'a' / 'b' / 'c.py'
        script.parent.mkdir(parents=True)
        script.write_text('# script')
        with pytest.raises(RuntimeError, match='resolve_skills_root'):
            resolve_skills_root(script)


class TestBuildPythonpath:
    def test_returns_joined_dirs(self, tmp_path):
        scripts = tmp_path / 'bundle-a' / 'skills' / 'skill-x' / 'scripts'
        scripts.mkdir(parents=True)
        result = build_pythonpath(tmp_path)
        assert str(scripts) in result
