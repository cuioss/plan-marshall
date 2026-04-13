"""Tests for marketplace_paths shared module."""

from pathlib import Path

import pytest
from marketplace_paths import (
    CLAUDE_DIR,
    PLUGIN_CACHE_SUBPATH,
    find_marketplace_path,
    get_base_path,
    get_plan_dir,
    get_plugin_cache_path,
    get_temp_dir,
    safe_relative_path,
)


class TestGetPlanDir:
    def test_plan_base_dir_override(self, monkeypatch):
        monkeypatch.setenv('PLAN_BASE_DIR', '/tmp/custom-plan')
        result = get_plan_dir()
        assert result == Path('/tmp/custom-plan')

    def test_default_resolves_global_dir_inside_git_repo(self, monkeypatch):
        """Without an env override, the default resolves to
        ~/.plan-marshall/{basename}-{path-hash} when called from inside a
        git repo. The hash suffix prevents collisions when two repos
        share a basename.
        """
        monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
        result = get_plan_dir()
        assert result.parent == Path.home() / '.plan-marshall'
        # basename + 8-char hex digest separated by a dash
        import re
        assert re.fullmatch(r'.+-[0-9a-f]{8}', result.name), result.name


class TestGetTempDir:
    def test_returns_subdir_under_plan_temp(self, monkeypatch):
        monkeypatch.setenv('PLAN_BASE_DIR', '/tmp/base-dir')
        result = get_temp_dir('my-tool')
        assert result == Path('/tmp/base-dir') / 'temp' / 'my-tool'


class TestSafeRelativePath:
    def test_relative_path_under_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        child = tmp_path / 'sub' / 'file.txt'
        assert safe_relative_path(child) == str(Path('sub') / 'file.txt')

    def test_absolute_path_outside_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        outside = Path('/some/other/path')
        assert safe_relative_path(outside) == '/some/other/path'


class TestFindMarketplacePath:
    def test_cwd_based_discovery(self, tmp_path, monkeypatch):
        bundles = tmp_path / 'marketplace' / 'bundles'
        bundles.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        result = find_marketplace_path()
        assert result == bundles

    def test_parent_cwd_discovery(self, tmp_path, monkeypatch):
        bundles = tmp_path / 'marketplace' / 'bundles'
        bundles.mkdir(parents=True)
        child = tmp_path / 'subdir'
        child.mkdir()
        monkeypatch.chdir(child)
        result = find_marketplace_path()
        assert result == bundles

    def test_script_fallback(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        script_bundles = tmp_path / 'script-bundles'
        script_bundles.mkdir()
        result = find_marketplace_path(script_bundles_dir=script_bundles)
        assert result == script_bundles

    def test_not_found(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = find_marketplace_path()
        assert result is None


class TestGetPluginCachePath:
    def test_cache_exists(self, tmp_path, monkeypatch):
        cache = tmp_path / CLAUDE_DIR / PLUGIN_CACHE_SUBPATH
        cache.mkdir(parents=True)
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        result = get_plugin_cache_path()
        assert result == cache

    def test_cache_not_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        result = get_plugin_cache_path()
        assert result is None


class TestGetBasePath:
    def test_auto_prefers_marketplace(self, tmp_path, monkeypatch):
        bundles = tmp_path / 'marketplace' / 'bundles'
        bundles.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        result = get_base_path('auto')
        assert result == bundles

    def test_auto_falls_back_to_cache(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cache = tmp_path / CLAUDE_DIR / PLUGIN_CACHE_SUBPATH
        cache.mkdir(parents=True)
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        result = get_base_path('auto')
        assert result == cache

    def test_auto_raises_when_nothing_found(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        with pytest.raises(FileNotFoundError):
            get_base_path('auto')

    def test_cache_first_prefers_cache(self, tmp_path, monkeypatch):
        bundles = tmp_path / 'marketplace' / 'bundles'
        bundles.mkdir(parents=True)
        cache = tmp_path / CLAUDE_DIR / PLUGIN_CACHE_SUBPATH
        cache.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        result = get_base_path('cache-first')
        assert result == cache

    def test_marketplace_scope(self, tmp_path, monkeypatch):
        bundles = tmp_path / 'marketplace' / 'bundles'
        bundles.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        result = get_base_path('marketplace')
        assert result == bundles

    def test_plugin_cache_scope(self, tmp_path, monkeypatch):
        cache = tmp_path / CLAUDE_DIR / PLUGIN_CACHE_SUBPATH
        cache.mkdir(parents=True)
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        result = get_base_path('plugin-cache')
        assert result == cache

    def test_global_scope(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        result = get_base_path('global')
        assert result == tmp_path / CLAUDE_DIR

    def test_project_scope(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = get_base_path('project')
        assert result == tmp_path / CLAUDE_DIR

    def test_invalid_scope_raises(self):
        with pytest.raises(ValueError, match='Invalid scope'):
            get_base_path('bogus')
