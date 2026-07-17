#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Tests for the store-root abstraction in tools-file-ops/file_ops.py (D0).

Covers get_store_dir(store, entry_id):
- 'plans' store round-trips through base_path / get_plan_dir (byte-identical).
- 'orchestrator' store resolves main-anchored via resolve_main_anchored_path,
  honouring the PLAN_BASE_DIR test override.
- Unknown store values raise ValueError.
- Real-resolver E2E leg: the orchestrator store resolves to the MAIN checkout
  via git-common-dir even when cwd is a linked worktree (no mocking of the
  git resolution).
"""

import subprocess
import uuid
from pathlib import Path

import file_ops
import pytest
from file_ops import base_path, get_plan_dir, get_store_dir


def _random_id(prefix: str) -> str:
    return f'{prefix}-{uuid.uuid4().hex[:12]}'


class TestPlansStore:
    """The 'plans' store routes through the existing cwd-relative base_path."""

    def test_should_equal_get_plan_dir_for_any_plan_id(self):
        plan_id = _random_id('plan')

        store_root = get_store_dir('plans', plan_id)

        assert store_root == get_plan_dir(plan_id)

    def test_should_equal_base_path_plans_for_any_plan_id(self):
        plan_id = _random_id('plan')

        store_root = get_store_dir('plans', plan_id)

        assert store_root == base_path('plans', plan_id)

    def test_should_resolve_under_plan_base_dir_override(self, monkeypatch, tmp_path):
        plan_id = _random_id('plan')
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

        store_root = get_store_dir('plans', plan_id)

        assert store_root == tmp_path / 'plans' / plan_id


class TestOrchestratorStore:
    """The 'orchestrator' store routes through resolve_main_anchored_path."""

    def test_should_honour_plan_base_dir_override(self, monkeypatch, tmp_path):
        epic_id = _random_id('epic')
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

        store_root = get_store_dir('orchestrator', epic_id)

        assert store_root == tmp_path / f'orchestrator/{epic_id}'

    def test_should_honour_set_base_dir_override(self, monkeypatch, tmp_path):
        epic_id = _random_id('epic')
        monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', tmp_path)

        store_root = get_store_dir('orchestrator', epic_id)

        assert store_root == tmp_path / f'orchestrator/{epic_id}'


class TestUnknownStore:
    """Unknown store values are rejected via ValueError."""

    @pytest.mark.parametrize('store', ['archive', 'lessons', '', 'PLANS', 'orchestrator '])
    def test_should_raise_value_error_for_unknown_store(self, store):
        with pytest.raises(ValueError) as exc_info:
            get_store_dir(store, _random_id('entry'))

        assert repr(store) in str(exc_info.value)


def _git(*args: str, cwd: Path) -> None:
    # Test-controlled fixture helper: args are hardcoded test literals plus
    # caller-supplied git subcommands, never externally-sourced input; 'git'
    # is resolved via PATH intentionally so the fixture works across CI
    # runners without hardcoding an absolute git path.
    subprocess.run(  # noqa: S603
        ['git', '-c', 'user.name=store-root-test', '-c', 'user.email=test@example.com', *args],  # noqa: S607
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.fixture
def linked_worktree_repo(tmp_path):
    """A real git repo with a linked worktree — no mocking of git resolution."""
    main_repo = tmp_path / 'main-repo'
    main_repo.mkdir()
    _git('init', '--initial-branch=main', cwd=main_repo)
    _git('commit', '--allow-empty', '-m', 'init', cwd=main_repo)
    worktree = tmp_path / 'linked-worktree'
    _git('worktree', 'add', '-b', 'feature/store-root', str(worktree), cwd=main_repo)
    return main_repo, worktree


class TestRealResolverE2E:
    """Real-resolver E2E leg: git-common-dir resolution, no mocking."""

    def test_should_resolve_orchestrator_store_to_main_from_linked_worktree_cwd(
        self, monkeypatch, linked_worktree_repo
    ):
        main_repo, worktree = linked_worktree_repo
        epic_id = _random_id('epic')
        monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
        monkeypatch.chdir(worktree)

        store_root = get_store_dir('orchestrator', epic_id)

        expected = (main_repo / '.plan' / 'local' / 'orchestrator' / epic_id).resolve()
        assert store_root.resolve() == expected

    def test_should_resolve_orchestrator_store_to_main_from_main_checkout_cwd(
        self, monkeypatch, linked_worktree_repo
    ):
        main_repo, _worktree = linked_worktree_repo
        epic_id = _random_id('epic')
        monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
        monkeypatch.chdir(main_repo)

        store_root = get_store_dir('orchestrator', epic_id)

        expected = (main_repo / '.plan' / 'local' / 'orchestrator' / epic_id).resolve()
        assert store_root.resolve() == expected

    def test_should_support_real_directory_creation_under_resolved_root(
        self, monkeypatch, linked_worktree_repo
    ):
        main_repo, worktree = linked_worktree_repo
        epic_id = _random_id('epic')
        monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
        monkeypatch.chdir(worktree)

        store_root = get_store_dir('orchestrator', epic_id)
        store_root.mkdir(parents=True, exist_ok=False)

        created = main_repo / '.plan' / 'local' / 'orchestrator' / epic_id
        assert created.is_dir()
