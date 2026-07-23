#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Client command handlers for architecture script (facade).

Handles: info, modules, graph, path, neighbors, impact, module, overview,
commands, resolve, profiles, siblings, files, which-module, find,
diff-modules, descriptor-regression-check.

Persistence model: ``_project.json`` and per-module ``enriched.json`` live on
disk under ``.plan/project-architecture/``; per-module ``derived.json`` is
ephemeral — every reader call resolves derived data via
``_architecture_core.load_module_derived`` which crawls the live worktree
filesystem rooted at ``args.project_dir`` / ``project_dir``. Every public
reader threads ``project_dir`` through to the core helpers; nothing falls back
to ``Path.cwd()`` or ``git rev-parse``.

This module is a thin facade: the implementation lives in co-located
``_cmd_client_*`` modules and is re-exported here so the public surface
(``_cmd_client.<name>``) that ``architecture.py`` imports and the tests
reference stays identical.

  * ``_cmd_client_build``    — Bucket B build-executable classification,
    build-config loading, bash-timeout lookup, execution-tier fields.
  * ``_cmd_client_query``    — project / module info readers, the lazy Maven
    enrichment cache (``_ENRICH_CACHE``), command resolution, and the
    dependency-graph path / neighbor / impact traversals.
  * ``_cmd_client_render``   — ``render_overview`` / ``render_module_markdown``
    and their per-section helpers.
  * ``_cmd_client_handlers`` — the argparse ``cmd_*`` handlers and their
    private helpers (augmentation, files inventory, snapshot diff, descriptor
    regression gate).

``_ENRICH_CACHE`` is re-exported by identity so ``_cmd_client._ENRICH_CACHE``
is the SAME object the query helpers mutate — ``.clear()`` therefore works
cross-module. ``_MARKETPLACE_BUNDLES_DIR`` is re-exported for the same
attribute-access surface the tests patch.
"""

import sys as _sys

# The test harness re-execs this facade (``load_script_module('_cmd_client')``)
# once per test file to rebind a freshly-loaded ``_architecture_core``. Drop any
# cached ``_cmd_client_*`` submodules first so their ``from _architecture_core
# import ...`` re-runs against the current instance on re-exec; otherwise the
# submodules keep a stale binding and exception-class / patch-target identity
# diverges across test files. In a normal single-import process (the executor)
# nothing is cached yet, so this is a no-op.
for _stale in ('_cmd_client_build', '_cmd_client_query', '_cmd_client_render', '_cmd_client_handlers'):
    _sys.modules.pop(_stale, None)

# Core re-exports: tests reference these as ``_cmd_client.<name>`` and they
# are part of the historical public surface of this module.
from _architecture_core import (  # noqa: E402, F401
    load_module_derived,
    load_module_enriched_or_empty,
    merge_module_data,
)
from _cmd_client_build import (  # noqa: E402, F401
    _BASH_CEILING_SECONDS,
    _BUILD_CONFIG_LOCATIONS,
    _BUILD_NOTATIONS,
    _HINT_ORCHESTRATOR,
    _HINT_PER_TASK_TEMPLATE,
    _MARKETPLACE_BUNDLES_DIR,
    _classify_build_executable,
    _compute_execution_tier_fields,
    _load_build_config,
    _lookup_bash_timeout,
)
from _cmd_client_handlers import (  # noqa: E402, F401
    _augment_resolved,
    _descriptor_text,
    _extract_profile_keys,
    _flatten_inventory,
    _is_blanked,
    _modules_from_exception_or_fallback,
    _resolve_module_inventory,
    _resolve_snapshot_dir,
    _resolve_verbs_for_build_class,
    _self_scan_inventory,
    _sha256_file,
    _sha256_payload,
    cmd_commands,
    cmd_derive_verification,
    cmd_descriptor_regression_check,
    cmd_diff_modules,
    cmd_files,
    cmd_find,
    cmd_graph,
    cmd_impact,
    cmd_info,
    cmd_module,
    cmd_modules,
    cmd_neighbors,
    cmd_overview,
    cmd_path,
    cmd_profiles,
    cmd_resolve,
    cmd_siblings,
    cmd_which_module,
)
from _cmd_client_query import (  # noqa: E402, F401
    _ENRICH_CACHE,
    _PROFILE_CANONICALS,
    NEIGHBORS_DEPTH_CAP,
    _apply_sibling_cross_links,
    _build_internal_deps_map,
    _command_executable,
    _enrich_maven_module_cached,
    _enrich_module_commands,
    _enriched_dependencies,
    _load_module_or_raise,
    _needs_profile_enrichment,
    get_module_commands,
    get_module_graph,
    get_module_impact,
    get_module_info,
    get_module_neighbors,
    get_module_path,
    get_modules_by_physical_path,
    get_modules_list,
    get_modules_with_command,
    get_project_info,
    get_sibling_modules,
    resolve_command,
)
from _cmd_client_render import (  # noqa: E402, F401
    _TRUNCATION_MARKER_PREFIX,
    DEFAULT_OVERVIEW_BUDGET,
    _apply_budget,
    _count_profile_skills,
    _render_adjacency_section,
    _render_modules_section,
    _render_project_section,
    _render_skills_by_profile_section,
    _truncation_marker,
    render_module_markdown,
    render_overview,
)
