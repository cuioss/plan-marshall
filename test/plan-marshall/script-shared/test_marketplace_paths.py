"""Tests for marketplace_paths shared module.

Resolution follows a SINGLE uniform cwd/worktree-relative rule (ADR-002):
PLAN_BASE_DIR override → walk up from cwd to the nearest ``.plan/local``
ancestor. There is no ``git rev-parse --git-common-dir`` sideways resolution.
``find_marketplace_path`` resolves ``marketplace/bundles`` by walking up from
cwd. These tests pin both PLAN_BASE_DIR and cwd and never contend for the real
``.plan/`` under ``-n auto``.
"""

import subprocess
from pathlib import Path

import marketplace_paths
import pytest
from marketplace_paths import (
    CLAUDE_DIR,
    PLAN_DIR_NAME,
    PLUGIN_CACHE_SUBPATH,
    _find_plan_root_from_cwd,
    find_marketplace_path,
    get_base_path,
    get_plugin_cache_path,
    get_temp_dir,
    resolve_main_anchored_path,
    safe_relative_path,
)


class TestNoGitMainCheckoutRoot:
    """Regression guard for the removal of the git-common-dir resolver.

    ``git_main_checkout_root`` / ``_resolve_git_main_checkout_root`` were the
    sideways ``git rev-parse --git-common-dir`` resolution path that the uniform
    cwd rule (ADR-002) replaced. This guard fails if either symbol is ever
    reintroduced into the shared module.
    """

    def test_git_main_checkout_root_is_not_a_module_attribute(self):
        assert not hasattr(marketplace_paths, 'git_main_checkout_root')

    def test_resolve_git_main_checkout_root_is_not_a_module_attribute(self):
        assert not hasattr(marketplace_paths, '_resolve_git_main_checkout_root')


class TestNoOrphanGetPlanDir:
    """Regression guard for the orphan-removal of ``get_plan_dir``.

    ``get_plan_dir`` was a duplicate base resolver removed from
    ``marketplace_paths`` (deliverable 2). Runtime plan-dir resolution lives
    solely in ``tools-file-ops/file_ops.py``. This guard fails if the orphan
    is ever reintroduced into the shared module, re-creating the duplication.
    """

    def test_get_plan_dir_is_not_a_module_attribute(self):
        # Arrange / Act: introspect the imported shared module.
        has_attr = hasattr(marketplace_paths, 'get_plan_dir')
        # Assert: the orphan must not exist on marketplace_paths.
        assert not has_attr


class TestFindPlanRootFromCwd:
    """The uniform cwd walk-up: nearest ancestor of cwd containing .plan/local."""

    def test_cwd_in_root_with_plan_local(self, tmp_path, monkeypatch):
        (tmp_path / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        assert _find_plan_root_from_cwd() == tmp_path.resolve()

    def test_cwd_below_root_walks_up_to_nearest(self, tmp_path, monkeypatch):
        (tmp_path / '.plan' / 'local').mkdir(parents=True)
        deep = tmp_path / 'a' / 'b' / 'c'
        deep.mkdir(parents=True)
        monkeypatch.chdir(deep)
        assert _find_plan_root_from_cwd() == tmp_path.resolve()

    def test_cwd_pinned_in_worktree_resolves_worktree_resident(self, tmp_path, monkeypatch):
        # A moved-in worktree has its own .plan/local; cwd pinned inside it
        # resolves to the worktree, not the main checkout above it.
        main = tmp_path / 'main'
        (main / '.plan' / 'local').mkdir(parents=True)
        worktree = main / '.plan' / 'local' / 'worktrees' / 'plan-x'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)
        assert _find_plan_root_from_cwd() == worktree.resolve()

    def test_cwd_in_unpopulated_worktree_falls_back_to_ancestor(self, tmp_path, monkeypatch):
        # A materialized-but-not-yet-populated worktree (no .plan/local) falls
        # back to the nearest ancestor that has one — the main checkout.
        main = tmp_path / 'main'
        (main / '.plan' / 'local').mkdir(parents=True)
        worktree = main / 'sub' / 'plan-x'
        worktree.mkdir(parents=True)
        monkeypatch.chdir(worktree)
        assert _find_plan_root_from_cwd() == main.resolve()

    def test_no_plan_local_ancestor_returns_none(self, tmp_path, monkeypatch):
        bare = tmp_path / 'bare'
        bare.mkdir()
        monkeypatch.chdir(bare)
        assert _find_plan_root_from_cwd() is None


class TestGetTempDir:
    def test_plan_base_dir_override_takes_precedence(self, monkeypatch):
        monkeypatch.setenv('PLAN_BASE_DIR', '/tmp/base-dir')
        result = get_temp_dir('my-tool')
        assert result == Path('/tmp/base-dir') / 'temp' / 'my-tool'

    def test_cwd_walk_up_anchors_temp(self, tmp_path, monkeypatch):
        monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
        (tmp_path / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        result = get_temp_dir('my-tool')
        assert result == tmp_path.resolve() / '.plan' / 'temp' / 'my-tool'


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
        monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)
        monkeypatch.chdir(tmp_path)
        result = find_marketplace_path()
        assert result == bundles

    def test_parent_cwd_discovery(self, tmp_path, monkeypatch):
        bundles = tmp_path / 'marketplace' / 'bundles'
        bundles.mkdir(parents=True)
        child = tmp_path / 'subdir'
        child.mkdir()
        monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)
        monkeypatch.chdir(child)
        result = find_marketplace_path()
        assert result == bundles

    def test_not_found(self, tmp_path, monkeypatch):
        # tmp_path is outside the repo, so the cwd walk-up finds no
        # marketplace/bundles ancestor.
        bare = tmp_path / 'bare'
        bare.mkdir()
        monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)
        monkeypatch.chdir(bare)
        result = find_marketplace_path()
        assert result is None


class TestFindMarketplacePathResolutionOrder:
    """Regression tests for the four-step resolution order in find_marketplace_path().

    Resolution priority (highest first):
        1. Explicit ``marketplace_root`` parameter
        2. ``PM_MARKETPLACE_ROOT`` environment variable
        3. cwd walk-up — nearest ancestor of cwd containing ``marketplace/bundles``
        4. cwd/parent discovery (legacy bootstrap fallback)

    Branches 1 and 2 are hard short-circuits (a missing candidate returns None
    without falling through). Branches 3 and 4 both probe cwd-relatively under
    the uniform cwd rule (ADR-002).
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
        even when env or cwd would otherwise resolve.
        """
        explicit_anchor = tmp_path / 'does-not-exist'
        env_anchor = self._make_bundles_root(tmp_path, 'env')
        cwd_anchor = self._make_bundles_root(tmp_path, 'cwd')

        monkeypatch.setenv('PM_MARKETPLACE_ROOT', str(env_anchor))
        monkeypatch.chdir(cwd_anchor)

        result = find_marketplace_path(marketplace_root=explicit_anchor)
        assert result is None

    def test_env_var_wins_over_cwd(self, tmp_path, monkeypatch):
        """Branch 2 wins when no explicit param is given, even if the cwd
        walk-up would also resolve.
        """
        env_anchor = self._make_bundles_root(tmp_path, 'env')
        cwd_anchor = self._make_bundles_root(tmp_path, 'cwd')

        monkeypatch.setenv('PM_MARKETPLACE_ROOT', str(env_anchor))
        monkeypatch.chdir(cwd_anchor)

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
        even when the cwd walk-up would otherwise resolve.
        """
        env_anchor = tmp_path / 'env-missing'
        cwd_anchor = self._make_bundles_root(tmp_path, 'cwd')

        monkeypatch.setenv('PM_MARKETPLACE_ROOT', str(env_anchor))
        monkeypatch.chdir(cwd_anchor)

        result = find_marketplace_path()
        assert result is None

    def test_cwd_walk_up_resolves_when_param_and_env_unset(self, tmp_path, monkeypatch):
        """Branch 3 resolves by walking up from cwd to the nearest ancestor
        containing ``marketplace/bundles`` when both branches 1 and 2 are unset.
        """
        anchor = tmp_path / 'synthetic-anchor'
        (anchor / 'marketplace' / 'bundles').mkdir(parents=True)
        deep = anchor / 'a' / 'b'
        deep.mkdir(parents=True)

        monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)
        monkeypatch.chdir(deep)

        result = find_marketplace_path()
        assert result == anchor / 'marketplace' / 'bundles'


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
        bare = tmp_path / 'bare'
        bare.mkdir()
        monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)
        monkeypatch.chdir(bare)

        result = get_base_path('marketplace', marketplace_root=explicit_anchor)
        assert result == explicit_anchor / 'marketplace' / 'bundles'

    def test_cache_first_falls_through_to_marketplace_param(self, tmp_path, monkeypatch):
        """``cache-first`` uses the explicit param when no plugin cache exists."""
        explicit_anchor = self._make_bundles_root(tmp_path, 'explicit')
        # No plugin cache under tmp_path/.claude/plugins/cache/plan-marshall.
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)
        bare = tmp_path / 'bare'
        bare.mkdir()
        monkeypatch.chdir(bare)

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
        bundles = tmp_path / 'marketplace' / 'bundles'
        bundles.mkdir(parents=True)
        monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)
        monkeypatch.chdir(tmp_path)
        result = get_base_path('auto')
        assert result == bundles

    def test_auto_raises_without_marketplace(self, tmp_path, monkeypatch):
        """auto scope no longer falls back to cache; it requires marketplace."""
        bare = tmp_path / 'bare'
        bare.mkdir()
        monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)
        monkeypatch.chdir(bare)
        cache = tmp_path / CLAUDE_DIR / PLUGIN_CACHE_SUBPATH
        cache.mkdir(parents=True)
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        with pytest.raises(FileNotFoundError):
            get_base_path('auto')

    def test_auto_raises_when_nothing_found(self, tmp_path, monkeypatch):
        bare = tmp_path / 'bare'
        bare.mkdir()
        monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)
        monkeypatch.chdir(bare)
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        with pytest.raises(FileNotFoundError):
            get_base_path('auto')

    def test_cache_first_prefers_cache(self, tmp_path, monkeypatch):
        bundles = tmp_path / 'marketplace' / 'bundles'
        bundles.mkdir(parents=True)
        cache = tmp_path / CLAUDE_DIR / PLUGIN_CACHE_SUBPATH
        cache.mkdir(parents=True)
        monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)
        result = get_base_path('cache-first')
        assert result == cache

    def test_marketplace_scope(self, tmp_path, monkeypatch):
        bundles = tmp_path / 'marketplace' / 'bundles'
        bundles.mkdir(parents=True)
        monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)
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


def _init_repo(repo: Path) -> None:
    """Initialise a fixture git repo so ``git worktree add`` runs end-to-end.

    Tracks a placeholder file and gitignores ``.plan/local`` so the worktree
    add materialises a clean tree. Mirrors the helper shape in
    ``test_git_workflow_worktree.py`` / ``test_git_merge_lock.py``.
    """
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Test'], check=True)
    (repo / 'README.md').write_text('x\n')
    (repo / '.gitignore').write_text('.plan/local\n.plan/local/worktrees/\n')
    subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(repo), 'commit', '-q', '-m', 'init'], check=True)


class TestResolveMainAnchoredPath:
    """The single sanctioned main-anchored exception resolver (ADR-002).

    Mirrors ``test_git_merge_lock.py``'s main-anchoring tests: override-first,
    worktree-cwd-resolves-to-main (real ``git worktree add``), and not-a-repo
    raises. The override-first branch keeps every PLAN_BASE_DIR-based consumer
    test green; the production branch resolves via the git common dir.
    """

    def test_resolve_main_anchored_path_honours_plan_base_dir_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange: PLAN_BASE_DIR set to a main-checkout stand-in; cwd pinned into
        # an unrelated worktree-like dir so we prove the override wins over cwd.
        main_base = tmp_path / 'main' / '.plan' / 'local'
        main_base.mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))
        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        # Act: resolve a subpath under the override.
        resolved = resolve_main_anchored_path('merge.lock')

        # Assert: lands under the override base, NOT the worktree-relative path.
        assert resolved == main_base / 'merge.lock'
        assert resolved != worktree / '.plan' / 'local' / 'merge.lock'

    def test_resolve_main_anchored_path_resolves_to_main_from_worktree_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange: a REAL git repo with a REAL linked worktree; no override set,
        # so the production git-common-dir branch is exercised. cwd is pinned
        # into the worktree.
        monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
        import file_ops  # type: ignore[import-not-found]

        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
        main_repo = tmp_path / 'main'
        main_repo.mkdir()
        _init_repo(main_repo)
        worktree = tmp_path / 'wt'
        subprocess.run(
            ['git', '-C', str(main_repo), 'worktree', 'add', '-q', '-b', 'feat', str(worktree)],
            check=True,
        )
        monkeypatch.chdir(worktree)

        # Act: resolve from inside the worktree cwd.
        resolved = resolve_main_anchored_path('merge.lock')

        # Assert: anchored under MAIN's .plan/local, NOT the worktree's.
        expected = main_repo.resolve() / PLAN_DIR_NAME / 'local' / 'merge.lock'
        assert resolved.resolve() == expected
        assert resolved.resolve() != (worktree.resolve() / PLAN_DIR_NAME / 'local' / 'merge.lock')

    def test_resolve_main_anchored_path_resolves_from_main_checkout_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange: a REAL git repo, no override, cwd pinned at the main checkout
        # itself (not a linked worktree) — the production branch must anchor at
        # the same main root.
        monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
        import file_ops  # type: ignore[import-not-found]

        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
        main_repo = tmp_path / 'main'
        main_repo.mkdir()
        _init_repo(main_repo)
        monkeypatch.chdir(main_repo)

        # Act: resolve from the main checkout cwd.
        resolved = resolve_main_anchored_path('run-configuration.json')

        # Assert: anchored under the main checkout's .plan/local.
        expected = main_repo.resolve() / PLAN_DIR_NAME / 'local' / 'run-configuration.json'
        assert resolved.resolve() == expected

    def test_resolve_main_anchored_path_lazy_file_ops_import_no_cycle(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange: force the override branch so the in-function ``import
        # file_ops`` executes; a circular import would surface as an ImportError
        # the moment resolve_main_anchored_path runs. The function returning a
        # path proves the lazy import resolved cleanly.
        main_base = tmp_path / 'main' / '.plan' / 'local'
        main_base.mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))

        # Act: invoke the override branch (exercises the deferred file_ops import).
        resolved = resolve_main_anchored_path('lessons-learned')

        # Assert: no ImportError raised; the path resolved under the override.
        assert resolved == main_base / 'lessons-learned'
        # Guard: marketplace_paths carries NO module-top file_ops import (the
        # import must stay in-function to avoid the import cycle).
        import inspect

        src = inspect.getsource(marketplace_paths)
        module_top = src.split('def ', 1)[0]
        assert 'import file_ops' not in module_top

    def test_resolve_main_anchored_path_raises_when_not_a_repo(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange: outside any git repo, no override — the production branch must
        # raise RuntimeError (identical contract to merge_lock).
        monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
        import file_ops  # type: ignore[import-not-found]

        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
        bare = tmp_path / 'bare'
        bare.mkdir()
        monkeypatch.chdir(bare)

        # Act / Assert: not a repo → RuntimeError.
        with pytest.raises(RuntimeError):
            resolve_main_anchored_path('merge.lock')
