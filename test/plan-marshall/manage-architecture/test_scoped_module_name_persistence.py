#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Characterization: a ``/``-bearing module name does not round-trip through the
snapshot-fixture writer.

npm's dominant naming convention is the scope (``@scope/pkg``), so the npm
derivation resolver routinely produces edges whose endpoints contain a ``/``.
That is fine for the resolver — an edge is a pair of strings — but it collides
with how the architecture store lays out per-module files on disk:
``get_module_dir`` joins the module name onto the data directory, so
``@sample/core`` becomes TWO directories, and ``_read_disk_derived`` (the
synthetic-project fallback) scans only the data directory's IMMEDIATE children.
The scoped module is therefore invisible to that fallback.

**This is a property of the fixture path, not of production.** Under the
on-demand crawl model ``crawl_all_modules`` runs live extension discovery and
only falls back to reading seeded ``derived.json`` files when discovery yields
nothing — which is a unit-test shape, not a real worktree. A real npm workspace
is discovered live, and a ``/`` in a package name is never a filesystem question
there.

These tests exist because the constraint is otherwise invisible and its failure
mode is silent: seeding a scoped module produces no error, and the module simply
does not appear. That silence is what makes it worth pinning — a future test
author who seeds ``@scope/pkg`` and asserts on the resulting graph would
otherwise get a passing test that measured nothing. The sibling end-to-end module
(``test_native_resolver_graph_impact.py``) copies its npm fixture into a temp
project root for exactly this reason, rather than seeding it.
"""

import json
import tempfile
from pathlib import Path

import pytest

from conftest import load_script_module

_architecture_core = load_script_module(
    'plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core'
)

get_data_dir = _architecture_core.get_data_dir
get_module_derived_path = _architecture_core.get_module_derived_path
save_module_derived = _architecture_core.save_module_derived
iter_modules = _architecture_core.iter_modules
invalidate_crawl_cache = _architecture_core.invalidate_crawl_cache

SCOPED = '@sample/core'
FLAT = 'sample-core'


def _module(name: str) -> dict:
    return {'name': name, 'build_systems': ['npm'], 'metadata': {'name': name}, 'dependencies': []}


def _seeded_project(tmpdir: str) -> None:
    """Seed one scoped and one flat module, then drop the crawl memo."""
    save_module_derived(SCOPED, _module(SCOPED), tmpdir)
    save_module_derived(FLAT, _module(FLAT), tmpdir)
    invalidate_crawl_cache(tmpdir)


def test_a_scoped_module_name_nests_into_two_directories():
    """The mechanism: the name is joined onto the path, so ``/`` is a separator."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = get_module_derived_path(SCOPED, tmpdir)
        data_dir = get_data_dir(tmpdir)

        assert path.relative_to(data_dir) == Path('@sample') / 'core' / 'derived.json'


def test_the_scoped_module_is_written_but_the_disk_fallback_does_not_surface_it():
    """The silent failure this module exists to make visible.

    The write succeeds and the file is really there — so nothing signals a
    problem — yet the module is absent from the fallback's view.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seeded_project(tmpdir)

        written = get_module_derived_path(SCOPED, tmpdir)
        assert written.is_file(), 'the write itself succeeds — that is what makes the loss silent'
        assert json.loads(written.read_text())['name'] == SCOPED

        assert SCOPED not in iter_modules(tmpdir)


def test_a_flat_module_name_seeded_the_same_way_is_surfaced():
    """The control. Without it, the assertion above could pass for any reason."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seeded_project(tmpdir)

        assert FLAT in iter_modules(tmpdir)


@pytest.mark.parametrize('name', ['@sample/core', 'group/sub'])
def test_no_name_containing_a_slash_survives_the_disk_fallback(name):
    """Not npm-specific: any ``/`` in a module name has the same consequence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        save_module_derived(name, _module(name), tmpdir)
        invalidate_crawl_cache(tmpdir)

        assert name not in iter_modules(tmpdir)
