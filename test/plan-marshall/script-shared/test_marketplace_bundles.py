# SPDX-License-Identifier: FSL-1.1-ALv2
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


def _create_bundle(base: Path, name: str, version: str | None = None, orphaned: bool = False) -> Path:
    """Helper to create a bundle directory with plugin.json.

    When ``orphaned`` is set, a ``.orphaned_at`` marker file is placed in the
    bundle directory so cache-scanning helpers skip it.
    """
    if version:
        bundle_dir = base / name / version
    else:
        bundle_dir = base / name
    plugin_dir = bundle_dir / '.claude-plugin'
    plugin_dir.mkdir(parents=True)
    (plugin_dir / 'plugin.json').write_text('{}')
    if orphaned:
        (bundle_dir / '.orphaned_at').write_text('2026-01-01T00:00:00Z')
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

    def test_multi_version_selects_newest(self, tmp_path):
        # Two cache version dirs for the same bundle: find_bundles returns only the
        # NEWEST ('1.0.10' -> (1, 0, 10)), not the lexically-first ('1.0.0'), so a
        # stale dir cannot shadow the current one in the last-write-wins merge.
        _create_bundle(tmp_path, 'bundle-a', '1.0.0')
        new = _create_bundle(tmp_path, 'bundle-a', '1.0.10')
        assert find_bundles(tmp_path) == [new]

    def test_orphaned_version_skipped(self, tmp_path):
        # The numerically-newest dir carries a .orphaned_at marker and must be
        # skipped, so the older non-orphaned dir is returned instead.
        live = _create_bundle(tmp_path, 'bundle-a', '1.0.0')
        _create_bundle(tmp_path, 'bundle-a', '1.0.10', orphaned=True)
        assert find_bundles(tmp_path) == [live]

    def test_current_version_orphaned_selects_older_live(self, tmp_path):
        # Tier 2: the numerically-newest ("current") version dir is orphaned, but an
        # older version dir is still live/non-orphaned. The three-tier precedence
        # must fall through to the newest *live* dir — an orphaned current version
        # never shadows a live one.
        live = _create_bundle(tmp_path, 'bundle-a', '1.0.0')
        _create_bundle(tmp_path, 'bundle-a', '1.0.10', orphaned=True)
        assert find_bundles(tmp_path) == [live]

    def test_all_versions_orphaned_degraded_fallback(self, tmp_path, capsys):
        # Tier 3: every version dir is orphaned. The degraded fallback returns the
        # newest-on-disk dir regardless of the orphan marker, so the bundle is
        # present (never contribute-zero), and a stderr log line names the bundle.
        _create_bundle(tmp_path, 'bundle-a', '1.0.0', orphaned=True)
        newest = _create_bundle(tmp_path, 'bundle-a', '1.0.10', orphaned=True)
        assert find_bundles(tmp_path) == [newest]
        stderr = capsys.readouterr().err
        assert 'degraded fallback' in stderr
        assert 'bundle-a' in stderr

    def test_non_versioned_bundle_starting_with_digits(self, tmp_path):
        # A non-versioned bundle whose name starts with digits (e.g. '1.0-my-bundle')
        # must be treated as a singleton, not grouped by its parent (base_path) and
        # discarded in favor of a sibling that also matches the version-dir pattern.
        b1 = _create_bundle(tmp_path, '1.0-bundle-a')
        b2 = _create_bundle(tmp_path, '2.0-bundle-b')
        assert sorted(find_bundles(tmp_path)) == sorted([b1, b2])


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

    def test_multi_version_selects_newest(self, tmp_path):
        # Two cache version dirs carry the same subpath: the resolver must return
        # the NEWEST ('1.0.10' -> (1, 0, 10)), not the lexically-first ('1.0.0').
        old = tmp_path / 'plan-marshall' / '1.0.0' / 'skills' / 'foo' / 'bar.py'
        new = tmp_path / 'plan-marshall' / '1.0.10' / 'skills' / 'foo' / 'bar.py'
        old.parent.mkdir(parents=True)
        new.parent.mkdir(parents=True)
        old.write_text('old')
        new.write_text('new')
        result = resolve_bundle_path(tmp_path, 'plan-marshall', 'skills/foo/bar.py')
        assert result == new


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

    def test_multi_version_selects_newest_only(self, tmp_path):
        # Two version dirs for the same bundle: only the newest must be scanned,
        # so an older version cannot pollute PYTHONPATH and shadow the newest.
        old_scripts = tmp_path / 'bundle-a' / '0.1.100' / 'skills' / 'skill-x' / 'scripts'
        new_scripts = tmp_path / 'bundle-a' / '0.1.200' / 'skills' / 'skill-x' / 'scripts'
        old_scripts.mkdir(parents=True)
        new_scripts.mkdir(parents=True)
        result = collect_script_dirs(tmp_path)
        assert str(new_scripts) in result
        assert str(old_scripts) not in result

    def test_multi_version_numbered_beats_beta(self, tmp_path):
        # A numbered build (0.1.5 -> (0, 1, 5)) sorts newer than a bare beta
        # (0.1-BETA -> (0, 1)); the numbered version dir wins.
        beta_scripts = tmp_path / 'bundle-a' / '0.1-BETA' / 'skills' / 'skill-x' / 'scripts'
        numbered_scripts = tmp_path / 'bundle-a' / '0.1.5' / 'skills' / 'skill-x' / 'scripts'
        beta_scripts.mkdir(parents=True)
        numbered_scripts.mkdir(parents=True)
        result = collect_script_dirs(tmp_path)
        assert str(numbered_scripts) in result
        assert str(beta_scripts) not in result

    def test_multi_version_subdirs_from_newest_only(self, tmp_path):
        # The newest-only selection also governs the scripts/ subdir expansion:
        # an older version's scripts subdir must not appear in the result.
        old_sub = tmp_path / 'bundle-a' / '0.1.100' / 'skills' / 'skill-x' / 'scripts' / 'build'
        new_sub = tmp_path / 'bundle-a' / '0.1.200' / 'skills' / 'skill-x' / 'scripts' / 'build'
        old_sub.mkdir(parents=True)
        new_sub.mkdir(parents=True)
        result = collect_script_dirs(tmp_path)
        assert str(new_sub) in result
        assert str(old_sub) not in result


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
