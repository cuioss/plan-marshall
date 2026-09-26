#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2


"""Tests for the marshal.json build_map seed under the top-level build block.

Covers the relocated, required build_map cluster and the three behaviours the
build_map-seed-scope fix introduces:

- build-map seed writes the aggregated {domain: [{glob, role, build_class}]}
  structure under ``build.map`` (relocated from the top level).
- Write-once: a re-seed never clobbers an existing seed, so a user correction
  made directly to the seeded entries survives.
- merge_build_map reads from ``build.map`` and fails closed
  (raises) when the block is absent — there is no override layer.
- Regression: ``build.map`` is present after seed, and the retired
  ``build_map_overrides`` / ``activation_globs`` keys are never written.

It also covers the seed AGGREGATOR WIRING: ``aggregate_build_map`` collects every
registered extension's explicit ``(pattern, role)`` routes (``classify_globs()``)
through the ``script-shared`` route deriver (``derive_globs_from_tree``, reached
via the ``extension_discovery.derive_build_map_globs`` bridge) — so a production
``.py`` file living OUTSIDE ``scripts/`` is caught because a declared route covers
it. These tests drive the aggregator end-to-end against a deterministic extension
(no ``_FAKE_AGGREGATED`` patch) so the wiring itself — not a stub — is exercised.

The three fix-specific suites at the end cover:

- **Applicability-scoping** — ``aggregate_build_map`` includes a domain's routes
  only when that domain's ``applies_to_module()`` is applicable for at least one
  discovered project module; non-applicable domains are dropped even though they
  declare routes, and an empty discovered-module set yields an empty aggregation.
- **Init-seed removal** — ``cmd_init`` / ``get_default_config()`` no longer seed
  ``build.map``; the block is materialised at wizard Step 8b
  (``build-map seed``) after architecture discovery.
- **Force reseed** — ``build-map seed --force`` clears any existing block and
  re-derives it (``action: re-derived``); the default seed stays write-once
  (``action: preserved``), and a user correction is overwritten by ``--force``.
"""

# ruff: noqa: I001, E402

import importlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from argparse import Namespace
from pathlib import Path

import pytest


from conftest import load_script_module

_cmd_build_map_mod = load_script_module(
    'plan-marshall', 'manage-config', '_cmd_build_map.py', module_name='_cmd_build_map_for_build_map_test'
)
_cmd_init_mod = load_script_module(
    'plan-marshall', 'manage-config', '_cmd_init.py', module_name='_cmd_init_for_build_map_test'
)

# Resolve the SAME _config_core module the handler imported its helpers from, so
# patching aggregate_build_map there is what seed_build_map_into() actually sees.
# (_cmd_build_map does `from _config_core import seed_build_map_into`, binding the
# function to that module's globals — not to any importlib-renamed copy.)
_config_core_mod = sys.modules[_cmd_build_map_mod.seed_build_map_into.__module__]

# The _config_defaults module backing get_default_config() — exercised directly
# by the init-seed-removal suite. Resolved via _cmd_init's import so the test
# asserts against the same module object the init handler uses.
_config_defaults_mod = importlib.import_module('_config_defaults')


# A deterministic fake aggregation result so the seed tests do not depend on the
# live extension set. Mirrors the real {domain: [{glob, role, build_class}]} shape.
_FAKE_AGGREGATED = {
    'python': [
        {'glob': 'scripts/*.py', 'role': 'production', 'build_class': 'compile'},
        {'glob': 'test/**/*.py', 'role': 'test', 'build_class': 'module-tests'},
    ],
}


# =============================================================================
# Seed aggregator wiring — real tree-derivation (no _FAKE_AGGREGATED patch)
# =============================================================================
#
# These tests exercise the actual wiring: aggregate_build_map() hands every
# registered extension's portable classify_globs() vocabulary to the
# script-shared tree-deriver (derive_globs_from_tree) against the REAL tree, so
# a production .py OUTSIDE scripts/ is caught because it exists in the tree.
# Unlike the write-once tests above, NO _FAKE_AGGREGATED stub is patched — the
# aggregator runs for real against a synthetic fixture tree, with only its
# environmental collaborators redirected: the extension set it discovers and the
# project modules it scopes against (applicability ground truth).

import extension_base
from extension_base import (
    ROLE_CONFIG,
    ROLE_PRODUCTION,
    ROLE_TEST,
    BuildExtensionBase,
)

# The extension_discovery module that aggregate_build_map() resolves
# derive_build_map_globs / discover_all_extensions / discover_project_modules
# from at call time. Importing it here gives the tests the same object to
# monkeypatch.
_extension_discovery_mod = importlib.import_module('extension_discovery')


# An applicable module set — one synthetic discovered module. aggregate_build_map's
# applicability filter calls discover_project_modules(project_root) and iterates
# modules.values(); the value shape only needs to round-trip through each fake
# extension's applies_to_module(), so a minimal dict suffices.
_APPLICABLE_MODULES = {'status': 'success', 'modules': {'core': {'name': 'core'}}}
_NO_MODULES = {'status': 'success', 'modules': {}}


# Tracked files matching the stub extensions' routes. The route deriver
# (derive_globs_from_tree) now prunes any route whose pattern matches no
# git-tracked file, so the aggregator's project_root must be a git tree carrying
# one file per route the stub declares (marketplace/targets/*.py production and
# test/*.py test), or every route would be pruned as dead.
_STUB_ROUTE_TRACKED_FILES = ['marketplace/targets/generate.py', 'test/sample_test.py']


# =============================================================================
# build-map drift — read-only diff of persisted build.map vs live derivation
# =============================================================================
#
# `build-map drift` (cmd_build_map_drift → compute_build_map_drift) diffs the
# live derived map (aggregate_build_map) against the persisted build.map block
# (get_build_map) on the per-domain `glob` surface, returning `in_sync` plus a
# `drift: {domain: {added_globs, removed_globs}}` block. It is read-only: it
# never calls save_config, so marshal.json is byte-identical after a drift call.
#
# These tests drive the handler against the same deterministic monkeypatch
# scaffold the seed tests use (patching aggregate_build_map on _config_core), so
# the derived side is controlled while the persisted side comes from the seeded
# marshal.json the plan_context fixture redirects MARSHAL_PATH to.


# A second deterministic aggregation that ADDS a domain glob relative to
# _FAKE_AGGREGATED (gains `scripts/extra.py`) — used to surface added_globs.
_FAKE_AGGREGATED_WITH_ADDED = {
    'python': [
        {'glob': 'scripts/*.py', 'role': 'production', 'build_class': 'compile'},
        {'glob': 'scripts/extra.py', 'role': 'production', 'build_class': 'compile'},
        {'glob': 'test/**/*.py', 'role': 'test', 'build_class': 'module-tests'},
    ],
}

# A third deterministic aggregation that REMOVES a glob relative to
# _FAKE_AGGREGATED (drops the test route) — used to surface removed_globs.
_FAKE_AGGREGATED_WITH_REMOVED = {
    'python': [
        {'glob': 'scripts/*.py', 'role': 'production', 'build_class': 'compile'},
    ],
}

from _manage_config_build_map_seed_fixtures_surface_module import _patch_aggregate

from _manage_config_build_map_seed_fixtures_surface_patch_aggregate import _PythonRouteExtension

from _manage_config_build_map_seed_fixtures_surface_pythonrouteextension import _NoRouteExtension

from _manage_config_build_map_seed_fixtures_surface_norouteextension import _make_tracked_project_root

from _manage_config_build_map_seed_fixtures_surface_make_tracked import _wire_real_aggregator

from _manage_config_build_map_seed_fixtures_surface_wire_real import _NonApplicablePythonExtension

from _manage_config_build_map_seed_fixtures_surface_nonapplicablepythonextension import _RaisingApplicabilityExtension

from _manage_config_build_map_seed_fixtures_surface_raisingapplicabilityextension import _LiveAndDeadRouteExtension

from _manage_config_build_map_seed_fixtures_surface_liveanddeadrouteextension import _MultiModuleSubdirConfigExtension

from _manage_config_build_map_seed_fixtures_surface_multimodulesubdirconfigextension import _seed_with
