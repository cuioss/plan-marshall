"""Tests for marketplace_paths shared module."""

from pathlib import Path

import marketplace_paths
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

    def test_default_resolves_local_subdir_inside_git_repo(self, tmp_path, monkeypatch):
        """Without an env override, the default resolves to
        ``<git_main_checkout_root>/.plan/local`` when called from inside
        a git repo.
        """
        import subprocess

        repo = tmp_path / 'repo'
        repo.mkdir()
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
        monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
        monkeypatch.chdir(repo)

        result = get_plan_dir()
        assert result.resolve() == (repo / '.plan' / 'local').resolve()


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


def _suppress_script_relative_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Force ``find_marketplace_path`` branch 3 (script-relative walk) to miss.

    Without this helper, the production ``__file__`` lives at
    ``<worktree>/marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py``
    so ``parents[6]`` resolves to the real worktree root which contains
    ``marketplace/bundles``. Branch 3 then short-circuits before branch 4
    (cwd-based fallback) can fire, breaking tests that exercise cwd discovery
    in isolation.

    We patch ``marketplace_paths.__file__`` to a deep synthetic path under
    ``tmp_path`` whose ``parents[6]`` does NOT contain ``marketplace/bundles``,
    so branch 3 falls through and branch 4 runs.
    """
    deep_dir = tmp_path / '__suppress' / 'a' / 'b' / 'c' / 'd' / 'e' / 'f' / 'g'
    deep_dir.mkdir(parents=True)
    fake_file = deep_dir / 'marketplace_paths.py'
    fake_file.touch()
    monkeypatch.setattr(marketplace_paths, '__file__', str(fake_file))


class TestFindMarketplacePath:
    def test_cwd_based_discovery(self, tmp_path, monkeypatch):
        _suppress_script_relative_branch(tmp_path, monkeypatch)
        bundles = tmp_path / 'marketplace' / 'bundles'
        bundles.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        result = find_marketplace_path()
        assert result == bundles

    def test_parent_cwd_discovery(self, tmp_path, monkeypatch):
        _suppress_script_relative_branch(tmp_path, monkeypatch)
        bundles = tmp_path / 'marketplace' / 'bundles'
        bundles.mkdir(parents=True)
        child = tmp_path / 'subdir'
        child.mkdir()
        monkeypatch.chdir(child)
        result = find_marketplace_path()
        assert result == bundles

    def test_not_found(self, tmp_path, monkeypatch):
        _suppress_script_relative_branch(tmp_path, monkeypatch)
        monkeypatch.chdir(tmp_path)
        result = find_marketplace_path()
        assert result is None


class TestFindMarketplacePathResolutionOrder:
    """Regression tests for the four-step resolution order in find_marketplace_path().

    Resolution priority (highest first):
        1. Explicit ``marketplace_root`` parameter
        2. ``PM_MARKETPLACE_ROOT`` environment variable
        3. Script-relative walk via ``Path(__file__).resolve().parents[6]``
        4. cwd-based discovery (legacy bootstrap fallback)

    Each branch short-circuits on a positive hit (and on a negative hit for the
    explicit param and env var branches — they do NOT fall through). Tests below
    pin each branch's priority and the early-return semantics.
    """

    @staticmethod
    def _make_bundles_root(base: Path, name: str) -> Path:
        """Create ``base/{name}/marketplace/bundles`` and return the anchor path.

        Returns the directory that should be passed as ``marketplace_root`` (i.e.
        the parent of ``marketplace/bundles``), not the bundles dir itself.
        """
        anchor = base / name
        (anchor / 'marketplace' / 'bundles').mkdir(parents=True)
        return anchor

    def test_explicit_param_wins_over_env_and_cwd(self, tmp_path, monkeypatch):
        """Branch 1 wins over branches 2, 3, and 4 when its candidate exists."""
        explicit_anchor = self._make_bundles_root(tmp_path, 'explicit')
        env_anchor = self._make_bundles_root(tmp_path, 'env')
        cwd_anchor = self._make_bundles_root(tmp_path, 'cwd')

        monkeypatch.setenv('PM_MARKETPLACE_ROOT', str(env_anchor))
        monkeypatch.chdir(cwd_anchor)

        result = find_marketplace_path(marketplace_root=explicit_anchor)
        assert result == explicit_anchor / 'marketplace' / 'bundles'

    def test_explicit_param_returns_none_without_falling_through(self, tmp_path, monkeypatch):
        """Branch 1 is a hard short-circuit: a missing candidate returns None
        even when env, script-relative, or cwd would otherwise resolve.
        """
        explicit_anchor = tmp_path / 'does-not-exist'
        env_anchor = self._make_bundles_root(tmp_path, 'env')
        cwd_anchor = self._make_bundles_root(tmp_path, 'cwd')

        monkeypatch.setenv('PM_MARKETPLACE_ROOT', str(env_anchor))
        monkeypatch.chdir(cwd_anchor)

        result = find_marketplace_path(marketplace_root=explicit_anchor)
        assert result is None

    def test_env_var_wins_over_script_relative_and_cwd(self, tmp_path, monkeypatch):
        """Branch 2 wins when no explicit param is given, even if script-relative
        and cwd would also resolve.
        """
        env_anchor = self._make_bundles_root(tmp_path, 'env')
        cwd_anchor = self._make_bundles_root(tmp_path, 'cwd')

        monkeypatch.setenv('PM_MARKETPLACE_ROOT', str(env_anchor))
        monkeypatch.chdir(cwd_anchor)
        # Script-relative would resolve to the real worktree, but env wins.

        result = find_marketplace_path()
        assert result == env_anchor / 'marketplace' / 'bundles'

    def test_env_var_loses_to_explicit_param(self, tmp_path, monkeypatch):
        """Explicit param overrides PM_MARKETPLACE_ROOT — establishes the
        precedence direction even when both candidates exist.
        """
        explicit_anchor = self._make_bundles_root(tmp_path, 'explicit')
        env_anchor = self._make_bundles_root(tmp_path, 'env')

        monkeypatch.setenv('PM_MARKETPLACE_ROOT', str(env_anchor))
        monkeypatch.chdir(tmp_path)

        result = find_marketplace_path(marketplace_root=explicit_anchor)
        assert result == explicit_anchor / 'marketplace' / 'bundles'

    def test_env_var_returns_none_without_falling_through(self, tmp_path, monkeypatch):
        """Branch 2 is a hard short-circuit: a missing candidate returns None
        even when script-relative or cwd would otherwise resolve.
        """
        env_anchor = tmp_path / 'env-missing'
        cwd_anchor = self._make_bundles_root(tmp_path, 'cwd')

        monkeypatch.setenv('PM_MARKETPLACE_ROOT', str(env_anchor))
        monkeypatch.chdir(cwd_anchor)

        result = find_marketplace_path()
        assert result is None

    def test_script_relative_resolves_when_param_and_env_unset(self, tmp_path, monkeypatch):
        """Branch 3 resolves using ``Path(__file__).resolve().parents[6]`` when
        both branches 1 and 2 are unset.

        We patch ``marketplace_paths.__file__`` to a synthetic path that anchors
        a freshly-created ``marketplace/bundles`` tree, so the assertion is
        deterministic regardless of where the test runs.
        """
        # Build the synthetic anchor: parents[6] of the patched __file__.
        # Layout: anchor/marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py
        anchor = tmp_path / 'synthetic-anchor'
        scripts_dir = (
            anchor
            / 'marketplace'
            / 'bundles'
            / 'plan-marshall'
            / 'skills'
            / 'script-shared'
            / 'scripts'
        )
        scripts_dir.mkdir(parents=True)
        fake_file = scripts_dir / 'marketplace_paths.py'
        fake_file.touch()

        monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)
        monkeypatch.chdir(tmp_path)  # No marketplace/bundles directly under cwd
        monkeypatch.setattr(marketplace_paths, '__file__', str(fake_file))

        result = find_marketplace_path()
        assert result == anchor / 'marketplace' / 'bundles'

    def test_cwd_fallback_only_fires_when_earlier_branches_fail(self, tmp_path, monkeypatch):
        """Branch 4 (cwd-based) only fires when explicit, env, and
        script-relative all fail to yield a valid bundles dir.

        We force script-relative to miss by patching ``__file__`` to a synthetic
        location whose ``parents[6]`` does NOT contain ``marketplace/bundles``,
        so resolution must fall through to the cwd-based legacy probe.
        """
        # Build a deep fake __file__ whose parents[6] is empty (no bundles dir).
        deep_dir = tmp_path / 'a' / 'b' / 'c' / 'd' / 'e' / 'f' / 'g'
        deep_dir.mkdir(parents=True)
        fake_file = deep_dir / 'marketplace_paths.py'
        fake_file.touch()

        # Set up cwd-based bundles dir under tmp_path.
        cwd_bundles = tmp_path / 'marketplace' / 'bundles'
        cwd_bundles.mkdir(parents=True)

        monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(marketplace_paths, '__file__', str(fake_file))

        result = find_marketplace_path()
        assert result == cwd_bundles


class TestGetBasePathResolutionOrder:
    """Regression tests verifying that ``get_base_path`` forwards the
    ``marketplace_root`` override to ``find_marketplace_path`` for the
    marketplace-aware scopes (auto, marketplace, cache-first).
    """

    @staticmethod
    def _make_bundles_root(base: Path, name: str) -> Path:
        anchor = base / name
        (anchor / 'marketplace' / 'bundles').mkdir(parents=True)
        return anchor

    def test_auto_explicit_param_wins_over_env_and_cwd(self, tmp_path, monkeypatch):
        explicit_anchor = self._make_bundles_root(tmp_path, 'explicit')
        env_anchor = self._make_bundles_root(tmp_path, 'env')
        cwd_anchor = self._make_bundles_root(tmp_path, 'cwd')

        monkeypatch.setenv('PM_MARKETPLACE_ROOT', str(env_anchor))
        monkeypatch.chdir(cwd_anchor)

        result = get_base_path('auto', marketplace_root=explicit_anchor)
        assert result == explicit_anchor / 'marketplace' / 'bundles'

    def test_auto_env_var_wins_when_param_unset(self, tmp_path, monkeypatch):
        env_anchor = self._make_bundles_root(tmp_path, 'env')
        cwd_anchor = self._make_bundles_root(tmp_path, 'cwd')

        monkeypatch.setenv('PM_MARKETPLACE_ROOT', str(env_anchor))
        monkeypatch.chdir(cwd_anchor)

        result = get_base_path('auto')
        assert result == env_anchor / 'marketplace' / 'bundles'

    def test_marketplace_scope_honors_explicit_param(self, tmp_path, monkeypatch):
        explicit_anchor = self._make_bundles_root(tmp_path, 'explicit')
        # cwd has no bundles, env unset — only the explicit param resolves.
        monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)
        monkeypatch.chdir(tmp_path)

        result = get_base_path('marketplace', marketplace_root=explicit_anchor)
        assert result == explicit_anchor / 'marketplace' / 'bundles'

    def test_cache_first_falls_through_to_marketplace_param(self, tmp_path, monkeypatch):
        """``cache-first`` uses the explicit param when no plugin cache exists."""
        explicit_anchor = self._make_bundles_root(tmp_path, 'explicit')
        # No plugin cache under tmp_path/.claude/plugins/cache/plan-marshall.
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)
        monkeypatch.chdir(tmp_path)

        result = get_base_path('cache-first', marketplace_root=explicit_anchor)
        assert result == explicit_anchor / 'marketplace' / 'bundles'

    def test_auto_raises_when_explicit_param_anchor_missing(self, tmp_path, monkeypatch):
        """Explicit param short-circuits even in get_base_path: a missing
        candidate raises FileNotFoundError without falling through to env or cwd.
        """
        explicit_anchor = tmp_path / 'does-not-exist'
        # Both env and cwd would otherwise satisfy auto.
        env_anchor = self._make_bundles_root(tmp_path, 'env')
        cwd_anchor = self._make_bundles_root(tmp_path, 'cwd')
        monkeypatch.setenv('PM_MARKETPLACE_ROOT', str(env_anchor))
        monkeypatch.chdir(cwd_anchor)

        with pytest.raises(FileNotFoundError):
            get_base_path('auto', marketplace_root=explicit_anchor)


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
        _suppress_script_relative_branch(tmp_path, monkeypatch)
        bundles = tmp_path / 'marketplace' / 'bundles'
        bundles.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        result = get_base_path('auto')
        assert result == bundles

    def test_auto_raises_without_marketplace(self, tmp_path, monkeypatch):
        """auto scope no longer falls back to cache; it requires marketplace."""
        _suppress_script_relative_branch(tmp_path, monkeypatch)
        monkeypatch.chdir(tmp_path)
        cache = tmp_path / CLAUDE_DIR / PLUGIN_CACHE_SUBPATH
        cache.mkdir(parents=True)
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        with pytest.raises(FileNotFoundError):
            get_base_path('auto')

    def test_auto_raises_when_nothing_found(self, tmp_path, monkeypatch):
        _suppress_script_relative_branch(tmp_path, monkeypatch)
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
        _suppress_script_relative_branch(tmp_path, monkeypatch)
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
