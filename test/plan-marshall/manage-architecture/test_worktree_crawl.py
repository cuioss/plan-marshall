#!/usr/bin/env python3
"""Tests for the worktree-aware crawl path.

The on-demand crawl roots its filesystem walk under ``Path(project_dir)``;
two distinct project roots with divergent layouts MUST yield distinct
crawl results. This pins the contract that callers passing
``--project-dir <worktree>`` (or threading ``project_dir`` through the
in-process API) get worktree-correct data — they never see the main
checkout.
"""

import tempfile

from conftest import load_script_module

_architecture_core = load_script_module('plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core')

crawl_all_modules = _architecture_core.crawl_all_modules
iter_modules = _architecture_core.iter_modules
save_module_derived = _architecture_core.save_module_derived
save_project_meta = _architecture_core.save_project_meta


def _seed_synthetic(tmpdir: str, modules: dict[str, dict]) -> None:
    save_project_meta(
        {
            'name': 'test-project',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {name: {} for name in modules},
        },
        tmpdir,
    )
    for name, data in modules.items():
        save_module_derived(name, data, tmpdir)


def test_two_project_roots_return_distinct_crawls():
    """Crawls rooted at distinct project_dir paths must yield distinct module sets."""
    with tempfile.TemporaryDirectory() as root_a, tempfile.TemporaryDirectory() as root_b:
        _seed_synthetic(root_a, {'alpha': {'name': 'alpha', 'paths': {'module': 'alpha'}}})
        _seed_synthetic(root_b, {'beta': {'name': 'beta', 'paths': {'module': 'beta'}}})

        a_modules = iter_modules(root_a)
        b_modules = iter_modules(root_b)

        assert a_modules == ['alpha']
        assert b_modules == ['beta']
        assert a_modules != b_modules


def test_crawl_all_modules_does_not_leak_between_project_dirs():
    """The crawl rooted at root_a must not see modules seeded under root_b."""
    with tempfile.TemporaryDirectory() as root_a, tempfile.TemporaryDirectory() as root_b:
        _seed_synthetic(
            root_a,
            {
                'shared-name': {'name': 'shared-name', 'paths': {'module': 'shared-name'}, 'side': 'A'},
            },
        )
        _seed_synthetic(
            root_b,
            {
                'shared-name': {'name': 'shared-name', 'paths': {'module': 'shared-name'}, 'side': 'B'},
            },
        )

        a_data = crawl_all_modules(root_a)
        b_data = crawl_all_modules(root_b)

        # Both have a module named 'shared-name' but their payloads differ —
        # the crawl correctly resolved against each project_dir.
        assert a_data['shared-name'].get('side') == 'A'
        assert b_data['shared-name'].get('side') == 'B'


def test_crawl_with_explicit_project_dir_does_not_consult_cwd():
    """The crawl never falls back to Path.cwd() — passing project_dir is authoritative.

    Sanity check: an explicit project_dir always governs, regardless of where
    the current working directory points. The crawl reads from project_dir's
    filesystem tree only.
    """
    with tempfile.TemporaryDirectory() as root_a, tempfile.TemporaryDirectory() as root_b:
        _seed_synthetic(root_a, {'a-mod': {'name': 'a-mod', 'paths': {'module': 'a-mod'}}})
        # root_b is empty — crawl_all_modules(root_b) must return {} even if
        # cwd happens to be root_a (we don't actually change cwd here; the
        # assertion is that explicit project_dir wins).
        b_data = crawl_all_modules(root_b)
        assert b_data == {}
