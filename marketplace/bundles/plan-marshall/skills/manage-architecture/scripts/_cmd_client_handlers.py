#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Argparse ``cmd_*`` handlers for the architecture client commands.

Extracted verbatim from ``_cmd_client``; the facade re-exports every public
name here. Covers the CLI handlers (info, modules, graph, module, overview,
commands, resolve, derive-verification, profiles, siblings, path, neighbors,
impact, files, which-module, find, search, diff-modules,
descriptor-regression-check) and their private helpers, including the Bucket B
execution-tier augmentation, the files-inventory readers, the snapshot diff, and
the descriptor regression gate.

The files-inventory readers (``find`` / ``search`` / ``which-module``) read
through the ``_resolve_module_inventory`` seam: an in-scope elided category is
self-scanned uncapped against the module's real worktree, and any read path that
cannot self-scan reports ``truncated: true`` (with the elided category names and
true counts) instead of silently treating the writer's sample as the whole list.
``find`` globs the PATH; ``search --content`` scans the file BODY.
"""

import argparse
import fnmatch
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from _architecture_core import (
    DATA_DIR,
    FILE_CATEGORIES,
    DataNotFoundError,
    ModuleNotFoundInProjectError,
    classify_changed_path,
    crawl_all_modules,
    error_result_command_not_found,
    error_result_module_not_found,
    get_root_module,
    iter_modules,
    load_merged_build_map,
    load_module_derived,
    load_module_enriched_or_empty,
    load_project_meta,
    longest_containing_prefix,
    require_project_meta_result,
    resolve_module_for_path,
    resolve_path_attribution,
)
from _cmd_client_build import (
    _classify_build_executable,
    _compute_execution_tier_fields,
    _lookup_bash_timeout,
)
from _cmd_client_query import (
    NEIGHBORS_DEPTH_CAP,
    _load_module_or_raise,
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
from _cmd_client_render import (
    DEFAULT_OVERVIEW_BUDGET,
    render_module_markdown,
    render_overview,
)
from constants import (
    DIR_PER_MODULE_DERIVED,
    FILE_PROJECT_META,
)

# =============================================================================
# CLI Handlers
# =============================================================================


def _extract_profile_keys(skills_by_profile: dict[str, Any]) -> set[str]:
    """Extract profile keys from skills_by_profile structure."""
    return set(skills_by_profile.keys())


def cmd_info(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for info command."""
    try:
        info = get_project_info(args.project_dir)
        return {'status': 'success', **info}
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_modules(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for modules command."""
    try:
        command_filter = getattr(args, 'filter_command', None)
        physical_path_filter = getattr(args, 'physical_path', None)

        if command_filter:
            modules = get_modules_with_command(command_filter, args.project_dir)
            return {'status': 'success', 'command': command_filter, 'modules': modules}
        elif physical_path_filter:
            modules = get_modules_by_physical_path(physical_path_filter, args.project_dir)
            return {'status': 'success', 'physical_path': physical_path_filter, 'modules': modules}
        else:
            modules = get_modules_list(args.project_dir)
            return {'status': 'success', 'modules': modules}
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_graph(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for graph command.

    The ``resolvers[]`` / ``resolver_count`` provenance pair rides through from
    :func:`get_module_graph`'s result, so an empty graph is never vacuous:
    ``resolver_count: 0`` means no resolver ran, while ``resolver_count: N`` means
    N resolvers ran and found no edges. Each edge additionally carries
    ``producers[]`` naming the resolver ids that derived it.
    """
    try:
        result = get_module_graph(args.project_dir, args.full)
        return {'status': 'success', **result}
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_module(args: argparse.Namespace) -> Any:
    """CLI handler for module command.

    Returns a TOON dict by default. When `--full --budget N` is supplied, returns
    a markdown string for a token-bounded module deep-dive instead. `--budget`
    without `--full` is silently a no-op (TOON output, identical to plain `--full`).
    """
    try:
        # Resolve module name (root if not provided), then merge.
        module_name = args.module or get_root_module(args.project_dir)
        if not module_name:
            raise ModuleNotFoundInProjectError('No modules found', [])
        budget = getattr(args, 'budget', None)
        if args.full and budget is not None:
            return render_module_markdown(module_name, args.project_dir, budget)
        module = get_module_info(module_name, args.full, args.project_dir)
        return {'status': 'success', 'module': module}
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError:
        try:
            modules = get_modules_list(args.project_dir)
        except Exception:
            modules = []
        return error_result_module_not_found(args.module, modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_overview(args: argparse.Namespace) -> Any:
    """CLI handler for overview command. Returns markdown string."""
    try:
        budget = getattr(args, 'budget', DEFAULT_OVERVIEW_BUDGET)
        return render_overview(args.project_dir, budget)
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_commands(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for commands command."""
    try:
        result = get_module_commands(args.module, args.project_dir)
        return {'status': 'success', **result}
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError:
        try:
            modules = get_modules_list(args.project_dir)
        except Exception:
            modules = []
        return error_result_module_not_found(args.module, modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_resolve(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for resolve command.

    When the resolved ``executable`` is a Bucket B build notation, the result
    is augmented with four additional fields (``bash_timeout_seconds``,
    ``exceeds_bash_ceiling``, ``execution_tier``, ``hint``) derived from the
    persisted run-config timeout and whether that key has ever been measured
    (an unmeasured command fails closed to ``orchestrator``). Non-build
    executables return today's TOON
    shape unchanged. See the module-level "Build-executable classification"
    section for the full contract.
    """
    try:
        result = resolve_command(args.resolve_command, args.module, args.project_dir)
        # Augment with adaptive-timeout / execution-tier fields when the
        # executable is a Bucket B build notation.
        augmented = {'status': 'success', **_augment_resolved(result, args.project_dir)}
        return augmented
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError:
        try:
            modules = get_modules_list(args.project_dir)
        except Exception:
            modules = []
        return error_result_module_not_found(args.module, modules)
    except ValueError:
        # Command not found at the resolved module. Resolve the ``default``
        # alias here too so the error names the real root module, matching the
        # alias handling in ``resolve_command``.
        try:
            requested = None if args.module == 'default' else args.module
            resolved_module = requested or get_root_module(args.project_dir) or ''
            if resolved_module:
                derived = load_module_derived(resolved_module, args.project_dir)
                commands = list(derived.get('commands', {}).keys())
            else:
                commands = []
        except Exception:
            resolved_module = args.module or ''
            commands = []
        return error_result_command_not_found(resolved_module, args.resolve_command, commands)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def _augment_resolved(executable_result: dict[str, Any], project_dir: str) -> dict[str, Any]:
    """Apply the Bucket B execution-tier augmentation to a resolved command dict.

    Shared by ``cmd_resolve`` and the deriver: when the resolved ``executable``
    is a Bucket B build notation, attach the ``bash_timeout_seconds`` /
    ``exceeds_bash_ceiling`` / ``execution_tier`` / ``hint`` quartet so the
    per-task timeout routing keeps working for derived commands exactly as it
    does for a direct ``resolve`` call.

    The quartet is NOT a pure function of the stamp alone: ``execution_tier``
    (and, on the fail-closed branch, ``hint``) also depends on whether the
    command key has ever been measured, so the lookup returns the
    ``(stamp, measured)`` pair and both are forwarded to the field computation.
    A ``None`` lookup still means "modules unavailable" and leaves the resolved
    dict unaugmented.
    """
    augmented = dict(executable_result)
    classification = _classify_build_executable(executable_result.get('executable', ''))
    if classification is not None:
        tool_name, command_args = classification
        lookup = _lookup_bash_timeout(tool_name, command_args, project_dir)
        if lookup is not None:
            stamp, measured = lookup
            augmented.update(_compute_execution_tier_fields(stamp, measured))
    return augmented


# =============================================================================
# Build-class → command derivation (derive-verification)
# =============================================================================
#
# The build_class IS the canonical ``architecture resolve --command`` verb: a
# ``compile``/``module-tests``/``verify`` build_class resolves directly to the
# command of the same name (no indirection map). ``none`` is NOT
# architecture-resolved (it derives nothing), so the deriver handles it
# explicitly. The single source of truth for this contract is
# ``manage-architecture/standards/resolve-command.md`` §
# "Build-class → verification command".


def _resolve_verbs_for_build_class(build_class: str) -> list[str]:
    """Return the ``architecture resolve --command`` verbs for a build_class.

    The ``build_class`` names the canonical command directly, so it resolves as
    itself — except ``module-tests``, whose test gate is the two-rung ladder
    ``test-compile`` **+** ``module-tests`` (compile the tests, then run them).
    ``none`` is handled by the deriver before this is reached and yields an empty
    verb list here. The single source of truth for this mapping is
    ``manage-architecture/standards/resolve-command.md`` §
    "Build-class → verification command".
    """
    if build_class == 'compile':
        return ['compile']
    if build_class == 'module-tests':
        return ['test-compile', 'module-tests']
    if build_class == 'verify':
        return ['verify']
    return []


def cmd_derive_verification(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for ``derive-verification`` — the single deterministic deriver.

    Reads the merged ``build_map`` from marshal.json, classifies each changed
    artifact's role+build_class (longest-glob-wins), groups by build_class, and
    emits the architecture-resolved verification command set per the
    build_class → command table. The deriver is pure and deterministic: the
    same (changed artifacts, build_map, architecture) always yields the same
    command list. A docs-only changed set derives ZERO Python builds — this is
    what structurally ends the docs-only build recurrence.

    See ``manage-architecture/standards/resolve-command.md`` §
    "Build-class → verification command" for the canonical mapping.
    """
    raw = args.changed_artifacts or ''
    paths = [p.strip() for p in raw.split(',') if p.strip()]
    project_dir = args.project_dir

    merged = load_merged_build_map(project_dir)

    classified: list[dict[str, str]] = []
    unclaimed: list[str] = []
    for path in paths:
        classification = classify_changed_path(path, merged)
        if classification is None:
            unclaimed.append(path)
            continue
        build_class, domain = classification
        classified.append({'path': path, 'build_class': build_class, 'domain': domain})

    # De-duplicate derived commands by their executable string so a changed set
    # touching N production files in one module derives ONE compile, not N.
    commands: list[dict[str, str]] = []
    seen_executables: set[str] = set()

    for item in classified:
        path = item['path']
        build_class = item['build_class']

        if build_class == 'none':
            continue

        resolve_verbs = _resolve_verbs_for_build_class(build_class)
        if not resolve_verbs:
            # Unknown build_class (should never happen — closed enum). Skip
            # rather than crash; the unclaimed/unknown surface below records it.
            unclaimed.append(path)
            continue

        module_name = resolve_module_for_path(path, project_dir, preferred_domain=item['domain'])
        for verb in resolve_verbs:
            try:
                resolved = resolve_command(verb, module_name, project_dir)
            except (ValueError, ModuleNotFoundInProjectError, DataNotFoundError):
                continue
            augmented = _augment_resolved(resolved, project_dir)
            if augmented.get('executable') and augmented['executable'] not in seen_executables:
                seen_executables.add(augmented['executable'])
                commands.append({'build_class': build_class, 'path': path, **augmented})

    return {
        'status': 'success',
        'changed_count': len(paths),
        'classified_count': len(classified),
        'command_count': len(commands),
        'unclaimed': sorted(set(unclaimed)),
        'commands': commands,
    }


def cmd_profiles(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for profiles command.

    Extract unique profile keys from skills_by_profile for given modules.
    Used by marshall-steward to auto-discover profiles for task_executors config.
    """
    try:
        all_modules = iter_modules(args.project_dir)

        if args.modules:
            module_names = [m.strip() for m in args.modules.split(',')]
            for name in module_names:
                if name not in all_modules:
                    raise ModuleNotFoundInProjectError(f'Module not found: {name}', all_modules)
        else:
            module_names = list(all_modules)

        profiles: set[str] = set()
        modules_analyzed: list[str] = []

        for module_name in module_names:
            module_enriched = load_module_enriched_or_empty(module_name, args.project_dir)
            skills_by_profile = module_enriched.get('skills_by_profile', {})
            if skills_by_profile:
                modules_analyzed.append(module_name)
                profiles.update(_extract_profile_keys(skills_by_profile))

        return {
            'status': 'success',
            'count': len(profiles),
            'profiles': sorted(profiles),
            'modules_analyzed': sorted(modules_analyzed),
        }
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError as e:
        try:
            modules = iter_modules(args.project_dir)
        except Exception:
            modules = []
        return error_result_module_not_found(str(e), modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_siblings(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for siblings command.

    Find sibling virtual modules for a given module.
    """
    try:
        siblings = get_sibling_modules(args.module, args.project_dir)

        result: dict[str, Any] = {
            'status': 'success',
            'module': args.module,
            'siblings': siblings,
        }

        if not siblings:
            result['note'] = 'Module is not a virtual module or has no siblings'

        return result
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError:
        try:
            modules = get_modules_list(args.project_dir)
        except Exception:
            modules = []
        return error_result_module_not_found(args.module, modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def _modules_from_exception_or_fallback(exc: ModuleNotFoundInProjectError, project_dir: str) -> list[str]:
    """Prefer the module list embedded in the exception; fall back to a re-read.

    ``ModuleNotFoundInProjectError`` carries the available module names in
    ``args[1]`` when raised from the architecture core helpers. CLI handlers
    that already provoked the exception can reuse that list rather than
    re-loading ``_project.json``. Defensive fallback to ``get_modules_list``
    handles one-arg constructions and unforeseen call sites.
    """
    if len(exc.args) >= 2 and isinstance(exc.args[1], list):
        return list(exc.args[1])
    try:
        return get_modules_list(project_dir)
    except Exception:
        return []


def cmd_path(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for path command.

    Carries the resolver provenance so an unreachable answer is never vacuous:
    ``resolver_count: 0`` with ``path: null`` means no resolver ran (there were no
    edges to walk), while ``resolver_count: N`` with ``path: null`` means N
    resolvers ran and no path exists.
    """
    try:
        path, resolvers = get_module_path(args.source, args.target, args.project_dir)
        return {
            'status': 'success',
            'source': args.source,
            'target': args.target,
            'path': path,
            'resolvers': resolvers,
            'resolver_count': len(resolvers),
        }
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError as e:
        modules = _modules_from_exception_or_fallback(e, args.project_dir)
        missing = e.args[0].split(': ', 1)[-1] if e.args else args.source
        return error_result_module_not_found(missing, modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_neighbors(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for neighbors command.

    Carries the resolver provenance so a lone-module answer is never vacuous:
    ``resolver_count: 0`` with only the starting module in ``neighbors`` means no
    resolver ran, while ``resolver_count: N`` means N resolvers ran and the module
    genuinely has no neighbours within the requested depth.
    """
    try:
        neighbors, resolvers = get_module_neighbors(args.module, args.depth, args.project_dir)
        return {
            'status': 'success',
            'module': args.module,
            'depth': min(args.depth, NEIGHBORS_DEPTH_CAP),
            'neighbors': neighbors,
            'resolvers': resolvers,
            'resolver_count': len(resolvers),
        }
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError as e:
        modules = _modules_from_exception_or_fallback(e, args.project_dir)
        return error_result_module_not_found(args.module, modules)
    except ValueError as e:
        return {'status': 'error', 'error': str(e)}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_impact(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for impact command.

    Carries the resolver provenance so an empty impact set is never vacuous:
    ``resolver_count: 0`` with ``impact: []`` means no resolver ran (nothing could
    have depended on the module), while ``resolver_count: N`` with ``impact: []``
    means N resolvers ran and nothing depends on it.
    """
    try:
        impact, resolvers = get_module_impact(args.module, args.project_dir)
        return {
            'status': 'success',
            'module': args.module,
            'impact': impact,
            'resolvers': resolvers,
            'resolver_count': len(resolvers),
        }
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError as e:
        modules = _modules_from_exception_or_fallback(e, args.project_dir)
        return error_result_module_not_found(args.module, modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


# =============================================================================
# Files Inventory Readers (files / which-module / find / search)
# =============================================================================


def _flatten_inventory(files_block: dict[str, Any]) -> list[tuple[str, str]]:
    """Flatten a ``files`` block into ``(category, path)`` pairs.

    Elided categories contribute their ``sample`` paths only. This is the
    sample-only flattener consumed *inside* ``_resolve_module_inventory``: the
    reader seam self-scans an in-scope elided category and reports
    ``truncated: true`` when it cannot, so ``find`` / ``which-module`` no longer
    silently treat the sample as the whole list (the confident-false-negative
    defect). Direct callers of this helper still see sample-only pairs.
    """
    pairs: list[tuple[str, str]] = []
    for category, value in files_block.items():
        if isinstance(value, list):
            for path in value:
                pairs.append((category, path))
        elif isinstance(value, dict) and 'sample' in value:
            for path in value['sample']:
                pairs.append((category, path))
    return pairs


def _self_scan_inventory(derived: dict[str, Any], project_dir: str) -> list[tuple[str, str]] | None:
    """Uncapped self-scan of a module's real worktree roots, or ``None`` if impossible.

    Deferred-import ``build_module_files_inventory`` from ``_cmd_manage`` — the
    same circular-import-breaking idiom used in
    ``_architecture_core._compute_all_modules`` — resolve the module root, and
    when it exists on disk re-run the git-ignore-aware walk UNCAPPED. Returns the
    flattened ``(category, path)`` pairs, or ``None`` when the module root is
    absent (the disk-derived / fixture path) or the walk raises ``OSError``.
    """
    paths = derived.get('paths') or {}
    module_rel = (paths.get('module') or '').strip()
    if not module_rel:
        return None

    project_path = Path(project_dir).resolve()
    module_root = (project_path / module_rel).resolve()
    try:
        if not module_root.is_dir():
            # Disk-derived / fixture module with no real worktree directory.
            return None

        # Deferred import — ``_cmd_manage`` imports from this handlers module's
        # sibling core at module level, so a top-level import here risks a cycle.
        from _cmd_manage import _load_gitignore, build_module_files_inventory

        project_root_rules = _load_gitignore(project_path / '.gitignore')
        inventory = build_module_files_inventory(derived, project_path, project_root_rules)
    except OSError:
        return None

    pairs: list[tuple[str, str]] = []
    for category, path_list in inventory.items():
        for path in path_list:
            pairs.append((category, path))
    return pairs


def _resolve_module_inventory(
    module_name: str,
    derived: dict[str, Any],
    project_dir: str,
    category_filter: str | None = None,
) -> tuple[list[tuple[str, str]], list[dict[str, Any]]]:
    """Resolve a module's ``(category, path)`` inventory, self-scanning past elision.

    The reader-boundary fix for the confident-false-negative defect
    (ADR-009, *status reporting fails closed with an explicit unknown state*):
    ``_flatten_inventory`` alone consumes an over-cap category's ``sample`` as if
    it were the whole list, so a real file that sorts past the sample horizon
    yields a confident ``count: 0``. This seam repairs that at the reader:

    * When no in-scope category is elided (``category_filter`` restricts which
      categories count; ``None`` counts every category), return
      ``(_flatten_inventory(files_block), [])`` — the byte-identical fast path
      with zero extra filesystem work.
    * When an in-scope category IS elided, attempt an uncapped SELF-SCAN of the
      module's real worktree roots. On success return the full ``(category,
      path)`` pairs with an empty truncation list.
    * When the self-scan is impossible (module root absent — the disk-derived /
      fixture path) or raises ``OSError``, fall back to the sample pairs and
      record one TRUTHFUL-TRUNCATION entry per elided in-scope category:
      ``{module, category, elided_count, sample_size}``.

    Returns ``(pairs, truncation_entries)``; ``truncation_entries`` is empty
    whenever the answer is complete (fast path or successful self-scan).
    """
    files_block = derived.get('files') or {}

    elided_categories: list[tuple[str, dict[str, Any]]] = [
        (category, value)
        for category, value in files_block.items()
        if isinstance(value, dict) and 'elided' in value and category_filter in (None, category)
    ]

    if not elided_categories:
        # Fast path — no in-scope category elided, no extra filesystem work.
        return _flatten_inventory(files_block), []

    self_scanned = _self_scan_inventory(derived, project_dir)
    if self_scanned is not None:
        return self_scanned, []

    # Self-scan impossible — degrade to a truthful truncation signal, still
    # contributing the sample pairs so a match inside the sample is not lost.
    truncation_entries: list[dict[str, Any]] = [
        {
            'module': module_name,
            'category': category,
            'elided_count': value['elided'],
            'sample_size': len(value.get('sample') or []),
        }
        for category, value in elided_categories
    ]
    return _flatten_inventory(files_block), truncation_entries


def _unknown_category_result(category: str) -> dict[str, Any]:
    """Return the shared ``unknown_category`` error payload for the two readers.

    The discriminator is membership in :data:`FILE_CATEGORIES` — the declared
    vocabulary — NOT membership in a module's ``files`` block. That distinction
    is load-bearing: the block is built with ``setdefault``, so a category with
    no files in a module is simply absent as a key. Testing block membership
    would make "unknown category" and "in-taxonomy but empty here" the same
    observable condition, which is exactly the confident-false-negative this
    error removes.

    The payload advertises the vocabulary itself so a caller never has to guess
    the valid names, and so the published list cannot drift from the constant.
    """
    return {
        'status': 'error',
        'error': 'unknown_category',
        'category': category,
        'valid_categories': sorted(FILE_CATEGORIES),
    }


def cmd_files(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for the ``files`` reader.

    Loads the target module's ``derived.json`` and returns its ``files``
    block. When ``--category`` is supplied, the response is narrowed to
    that single bucket (and the ``elided``/``sample`` shape is preserved
    verbatim if the bucket was capped).

    An unrecognised ``--category`` is an ``unknown_category`` error rather than
    a confident empty list; a recognised category that this module does not
    populate remains a legitimate ``status: success`` with ``files: []``. The
    category check runs before module resolution because it is pure argument
    validation and applies regardless of module.
    """
    category = getattr(args, 'category', None)
    if category and category not in FILE_CATEGORIES:
        return _unknown_category_result(category)

    try:
        derived = _load_module_or_raise(args.module, args.project_dir)
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError:
        try:
            modules = get_modules_list(args.project_dir)
        except Exception:
            modules = []
        return error_result_module_not_found(args.module, modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

    files_block = derived.get('files') or {}

    if category:
        # The category is known-valid here. An absent bucket means the module
        # simply has no file in that category — a legitimate empty answer.
        bucket = files_block.get(category)
        return {
            'status': 'success',
            'module': args.module,
            'category': category,
            'files': [] if bucket is None else bucket,
        }

    return {
        'status': 'success',
        'module': args.module,
        'files': files_block,
    }


def cmd_which_module(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for the ``which-module`` reader.

    Resolves a path to its owning module. The primary signal is exact
    membership in a module's crawled ``files`` inventory, tie-broken by the
    longest ``paths.module`` prefix — so a file under
    ``marketplace/bundles/pm-dev-java/...`` resolves to ``pm-dev-java``, not the
    project-root ``default`` module.

    A containment fallback covers paths that the inventory does not surface as an
    exact, module-specific match. The crawled inventory elides large categories
    to a sample (so most ``test/**`` files never appear as an exact hit), and
    project-local dotfile trees such as ``.claude/skills/**`` are never
    inventoried at all. Resolution order:

        1. Exact-inventory match that is more specific than the root
           (``paths.module`` length > 0).
        2. Longest ``paths.sources ∪ paths.tests`` prefix that contains the path
           (the union of ``paths.tests`` lets a ``test/**`` path resolve to its
           owning module instead of the root).
        3. Path-attribution seam (Axis-D): the merged set of bundle-contributed
           ``(path_prefix, module)`` claims, resolved by longest containing
           prefix. See ``extension-api/standards/ext-point-path-attribution.md``.
        4. Root-inventory match (the length-0 ``default`` module), when present.

    The exact-inventory step reads through ``_resolve_module_inventory`` (with
    ``category_filter=None``), so an in-scope elided category is self-scanned
    uncapped rather than trusting its sample. The result always carries
    ``truncated: bool`` and ``elided: list[dict]`` (empty when clean) per ADR-009
    fail-closed reporting — a truthful ``truncated: true`` can accompany a
    resolved module as well as a ``module: null``.

    The result likewise always carries the Axis-D provenance pair
    ``attributors: list[str]`` (the sorted ids of the attributors that ran) and
    ``attributor_count: int``, plus ``attributor_notes: list[dict]`` carrying any
    condition that suppressed a claim. Both provenance fields are present on
    EVERY response shape — resolved, null, and truncated alike — so no caller
    branches on a missing key, exactly as ``truncated`` / ``elided`` are. The
    seam therefore runs on every call rather than only on rung-3 fallthrough;
    the merge is memoized at process lifetime, so the cost is one merge per
    process, not one per call. The distinction this buys mirrors Tier 1's
    ``resolver_count``:

        - ``attributor_count: 0`` with ``module: null`` — **no attributor ran**.
          The unattributed path is an absence of capability, not a finding.
        - ``attributor_count: N`` with ``module: null`` — **N attributors ran and
          none claimed this path**. A real, positive answer.

    A path whose claim was suppressed by an ownership collision answers
    ``module: null`` accompanied by the reporting note, never a bare confident
    null.
    """
    target = args.path
    try:
        module_names = iter_modules(args.project_dir)
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

    inventory_best: tuple[int, str] | None = None  # (paths.module length, name)
    containment_best: tuple[int, str] | None = None  # (sources∪tests prefix length, name)
    truncation_entries: list[dict[str, Any]] = []
    for name in module_names:
        try:
            derived = load_module_derived(name, args.project_dir)
        except DataNotFoundError:
            continue
        paths = derived.get('paths') or {}
        module_path = (paths.get('module') or '').strip()
        # Normalize the root module's path ('.' or '') to a prefix length of 0
        # so its exact-inventory hit is not treated as "more specific than the
        # root" at the length-0 tie-break below ('.'.rstrip('/') is still '.',
        # length 1, which would otherwise short-circuit the containment fallback).
        module_path_norm = '' if module_path in ('.', '') else module_path.rstrip('/')

        pairs, module_truncations = _resolve_module_inventory(name, derived, args.project_dir, None)
        truncation_entries.extend(module_truncations)
        for _category, path in pairs:
            if path == target:
                candidate = (len(module_path_norm), name)
                if inventory_best is None or candidate[0] > inventory_best[0] or (
                    candidate[0] == inventory_best[0] and candidate[1] < inventory_best[1]
                ):
                    inventory_best = candidate
                break

        containment_len = longest_containing_prefix(target, paths)
        if containment_len is not None:
            candidate = (containment_len, name)
            if containment_best is None or candidate[0] > containment_best[0] or (
                candidate[0] == containment_best[0] and candidate[1] < containment_best[1]
            ):
                containment_best = candidate

    # The seam runs unconditionally, not only on rung-3 fallthrough: the
    # provenance pair below is present on every response shape, and an
    # ``attributor_count`` reported only when rung 3 happened to be reached would
    # read as "no attributor ran" on every path rungs 1-2 already resolved.
    attribution_owner, attributor_reports = resolve_path_attribution(target, module_names)

    # 1. Exact-inventory match more specific than the root.
    if inventory_best is not None and inventory_best[0] > 0:
        resolved: str | None = inventory_best[1]
    # 2. Longest sources ∪ tests containment prefix.
    elif containment_best is not None:
        resolved = containment_best[1]
    # 3. Path-attribution seam (Axis-D bundle-contributed claims).
    elif attribution_owner is not None:
        resolved = attribution_owner
    # 4. Root-inventory match (the length-0 default module), when present.
    elif inventory_best is not None:
        resolved = inventory_best[1]
    else:
        resolved = None

    return {
        'status': 'success',
        'path': target,
        'module': resolved,
        'attributors': [report['id'] for report in attributor_reports],
        'attributor_count': len(attributor_reports),
        'attributor_notes': [
            {'attributor': report['id'], 'note': note}
            for report in attributor_reports
            for note in report['notes']
        ],
        'truncated': bool(truncation_entries),
        'elided': truncation_entries,
    }


def cmd_find(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for the ``find`` reader.

    Cross-module pattern search across the inventory. ``--pattern`` is
    glob-style (``fnmatch``), case-sensitive, anchored to the full path.
    ``--category`` narrows the search to one bucket. An in-scope elided category
    is self-scanned uncapped through ``_resolve_module_inventory`` rather than
    contributing only its ``sample``; when the self-scan is impossible the result
    reports ``truncated: true`` with the elided category names and true counts
    instead of a bare negative. The result always carries ``truncated: bool`` and
    ``elided: list[dict]`` (empty when clean) per ADR-009 fail-closed reporting.

    An unrecognised ``--category`` is an ``unknown_category`` error rather than a
    confident ``count: 0`` — the same two-way split ``cmd_files`` applies, and
    for the same reason. A recognised category that no module populates still
    returns ``count: 0``.
    """
    pattern = args.pattern
    category_filter = getattr(args, 'category', None)

    if category_filter and category_filter not in FILE_CATEGORIES:
        return _unknown_category_result(category_filter)

    try:
        module_names = iter_modules(args.project_dir)
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

    results: list[dict[str, str]] = []
    truncation_entries: list[dict[str, Any]] = []
    for name in module_names:
        try:
            derived = load_module_derived(name, args.project_dir)
        except DataNotFoundError:
            continue
        pairs, module_truncations = _resolve_module_inventory(
            name, derived, args.project_dir, category_filter
        )
        truncation_entries.extend(module_truncations)
        for category, path in pairs:
            if category_filter and category != category_filter:
                continue
            if fnmatch.fnmatchcase(path, pattern):
                results.append({'module': name, 'category': category, 'path': path})

    results.sort(key=lambda item: (item['module'], item['category'], item['path']))

    return {
        'status': 'success',
        'pattern': pattern,
        'category': category_filter,
        'count': len(results),
        'results': results,
        'truncated': bool(truncation_entries),
        'elided': truncation_entries,
    }


def cmd_search(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for the ``search`` reader's ``--content`` mode.

    The content-search sibling of :func:`cmd_find`: same inputs, same
    ``iter_modules`` -> ``load_module_derived`` -> ``_resolve_module_inventory``
    seam, same module/category attribution, same ADR-009 truncation reporting.
    Only the per-file predicate differs — ``find`` globs the PATH, ``search
    --content`` scans the file BODY — so a hit inside a file whose path does not
    mention the pattern (the exact gap ``find`` cannot close) is reachable.

    ``--pattern`` is compiled as a Python regex; ``--literal`` compiles
    ``re.escape(pattern)`` instead, so a pattern carrying shell metacharacters is
    matched verbatim. No caller input ever reaches a shell. A pattern that fails
    to compile returns ``status: error, error: invalid_pattern`` carrying the
    compile message — required boundary handling on untrusted caller input.

    The compile carries ``re.MULTILINE``, so ``^`` and ``$`` anchor to
    line-start / line-end — the semantics ``grep``, ``ripgrep`` and the harness
    ``Grep`` tool all give them, and therefore the semantics a caller writing
    ``^Skill:`` already expects. Without the flag the body is one string and the
    anchors would mean file-start / file-end, turning an ordinary anchored
    pattern into a silent ``count: 0`` over a fully-scanned corpus — a confident
    negative, which is precisely what ``files_scanned`` exists to prevent.
    ``match_count`` stays a real count under the flag: ``finditer`` still walks
    every non-overlapping match in the file, so an anchored pattern hitting three
    separate lines reports 3, never a first-hit short-circuit.

    **The response carries NO matching line bodies — a settled decision, not an
    omission.** A hit reports only *where* it is (``module``, ``category``,
    ``path``) and *how strongly* (``match_count``, the number of non-overlapping
    matches in that file). Returning line bodies would make the response size a
    function of the corpus's match density rather than of its file count, so one
    broad sweep could emit an unbounded payload into the caller's context.
    ``match_count`` is what replaces the lines: it lets a caller rank the hit
    list and spend a ``Read`` on the few files that matter.

    Two anti-vacuity fields ride alongside the ADR-009 ``truncated`` / ``elided``
    pair, for the same fail-closed reason the sibling verbs carry
    ``resolver_count`` / ``attributor_count``:

    * ``files_scanned`` (int) — ``count: 0`` with ``files_scanned: 0`` means
      *nothing was searched*; ``count: 0`` with ``files_scanned: N`` means *N
      files were searched and the pattern is genuinely absent*. The two are never
      the same observable condition.
    * ``unreadable`` (list of ``{path, reason}``, empty when clean) — a file
      skipped for a decode or OS error is REPORTED, never silently suppressed
      (ADR-014). Binary and undecodable files land here.

    Deliberately NOT echoed: a ``mode`` field. ``--content`` is the only mode
    today, so echoing it would be a constant-valued response key — vacuous now,
    and worth adding only when a second mode makes it discriminating.

    An unrecognised ``--category`` is an ``unknown_category`` error rather than a
    confident ``count: 0`` — the same two-way split ``cmd_files`` / ``cmd_find``
    apply, and for the same reason.
    """
    pattern = args.pattern
    literal = bool(getattr(args, 'literal', False))
    category_filter = getattr(args, 'category', None)

    if category_filter and category_filter not in FILE_CATEGORIES:
        return _unknown_category_result(category_filter)

    try:
        compiled = re.compile(re.escape(pattern) if literal else pattern, re.MULTILINE)
    except re.error as e:
        return {
            'status': 'error',
            'error': 'invalid_pattern',
            'pattern': pattern,
            'literal': literal,
            'message': str(e),
        }

    try:
        module_names = iter_modules(args.project_dir)
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

    project_path = Path(args.project_dir)
    results: list[dict[str, Any]] = []
    truncation_entries: list[dict[str, Any]] = []
    unreadable: list[dict[str, str]] = []
    files_scanned = 0

    for name in module_names:
        try:
            derived = load_module_derived(name, args.project_dir)
        except DataNotFoundError:
            continue
        pairs, module_truncations = _resolve_module_inventory(
            name, derived, args.project_dir, category_filter
        )
        truncation_entries.extend(module_truncations)
        for category, path in pairs:
            if category_filter and category != category_filter:
                continue
            try:
                text = (project_path / path).read_text(encoding='utf-8')
            except UnicodeDecodeError:
                unreadable.append({'path': path, 'reason': 'decode_error'})
                continue
            except OSError:
                unreadable.append({'path': path, 'reason': 'os_error'})
                continue
            files_scanned += 1
            match_count = sum(1 for _ in compiled.finditer(text))
            if match_count:
                results.append(
                    {'module': name, 'category': category, 'path': path, 'match_count': match_count}
                )

    results.sort(key=lambda item: (item['module'], item['category'], item['path']))

    return {
        'status': 'success',
        'pattern': pattern,
        'literal': literal,
        'category': category_filter,
        'count': len(results),
        'results': results,
        'files_scanned': files_scanned,
        'unreadable': unreadable,
        'truncated': bool(truncation_entries),
        'elided': truncation_entries,
    }


# =============================================================================
# Snapshot Diff (diff-modules)
# =============================================================================


def _sha256_file(path: Path) -> str | None:
    """Return the sha256 hexdigest of ``path`` or None when the file is absent."""
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def _sha256_payload(payload: dict[str, Any] | None) -> str | None:
    """Return the sha256 hexdigest of a module's derived payload.

    Computed over the canonical JSON serialisation (``json.dumps(payload,
    sort_keys=True)``) so the digest is byte-identical to what
    ``_write_json`` would have written under the legacy on-disk model. Returns
    ``None`` when the payload is missing.
    """
    if payload is None:
        return None
    canonical = json.dumps(payload, indent=2, sort_keys=True).encode('utf-8')
    return hashlib.sha256(canonical).hexdigest()


def _resolve_snapshot_dir(pre: str) -> Path:
    """Resolve a ``--pre`` argument to a snapshot directory.

    The argument may be either the snapshot root containing ``_project.json``
    directly, or a project root whose ``.plan/project-architecture/`` subtree
    holds the snapshot. The first shape that points at an existing
    ``_project.json`` wins; callers handle the no-match case via
    ``snapshot_not_found``.
    """
    base = Path(pre)
    direct = base / FILE_PROJECT_META
    if direct.is_file():
        return base
    nested = base / DATA_DIR / FILE_PROJECT_META
    if nested.is_file():
        return base / DATA_DIR
    # Default to the direct shape so error reporting points at the simpler path.
    return base


def cmd_diff_modules(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for the ``diff-modules`` reader.

    Compares pre-snapshot per-module ``derived.json`` shas (read from the
    on-disk snapshot under ``--pre``) against the sha of the live on-demand
    crawl of the current project's modules, and classifies every module from
    the union of both module sets into one of four buckets: ``added``,
    ``removed``, ``changed``, ``unchanged``.

    The snapshot side keeps its file-based read because the snapshot is an
    on-disk artifact captured at some earlier point. The current side
    computes a fresh crawl-based sha; nothing reads
    ``{module}/derived.json`` from the current project's
    ``project-architecture/`` directory.

    Comparison surface is intentionally narrow — only ``derived.json`` shas
    matter. Differences confined to ``enriched.json`` (LLM-curated fields)
    never produce a ``changed`` classification.

    Error contract: when the snapshot directory or its ``_project.json`` is
    missing, returns ``status: error, error: snapshot_not_found, path: <pre>``.
    """
    pre_arg = args.pre
    snapshot_dir = _resolve_snapshot_dir(pre_arg)
    snapshot_meta_path = snapshot_dir / FILE_PROJECT_META

    if not snapshot_meta_path.is_file():
        return {
            'status': 'error',
            'error': 'snapshot_not_found',
            'path': pre_arg,
        }

    try:
        snapshot_meta = json.loads(snapshot_meta_path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        return {
            'status': 'error',
            'error': 'snapshot_not_found',
            'path': pre_arg,
            'detail': str(e),
        }

    snapshot_modules = set((snapshot_meta.get('modules') or {}).keys())

    current_modules_data = crawl_all_modules(args.project_dir)
    current_modules = set(current_modules_data.keys())
    if not current_modules:
        return require_project_meta_result(args.project_dir)

    added = sorted(current_modules - snapshot_modules)
    removed = sorted(snapshot_modules - current_modules)

    changed: list[str] = []
    unchanged: list[str] = []
    for name in sorted(snapshot_modules & current_modules):
        snap_sha = _sha256_file(snapshot_dir / name / DIR_PER_MODULE_DERIVED)
        # Use the pre-crawled data to avoid O(N^2) project walks: the
        # full crawl happened once above; each iteration just serialises
        # the already-computed payload dict.
        cur_sha = _sha256_payload(current_modules_data.get(name))
        # When the snapshot derived.json is missing on disk, or the live
        # crawl no longer surfaces the module, treat the pair as changed —
        # the index lists the module on both sides but the sha surface cannot
        # certify equality.
        if snap_sha is None or cur_sha is None or snap_sha != cur_sha:
            changed.append(name)
        else:
            unchanged.append(name)

    return {
        'status': 'success',
        'added': added,
        'removed': removed,
        'changed': changed,
        'unchanged': unchanged,
    }


# =============================================================================
# Descriptor Regression Check (descriptor-regression-check)
# =============================================================================


def _descriptor_text(value: Any) -> str:
    """Safely convert a descriptor field value to a stripped string.

    Non-string values (list, int, dict) are treated as empty rather than
    raising ``AttributeError`` when ``.strip()`` is called, so a malformed
    ``_project.json`` field cannot crash the regression check.
    """
    return value.strip() if isinstance(value, str) else ''


def _is_blanked(baseline_value: Any, current_value: Any) -> bool:
    """Whether a descriptor field transitioned from non-empty to empty.

    Treats ``None`` and whitespace-only strings as empty on both sides, so a
    curated value being wiped to ``''`` (the legacy ``api_discover`` blanking
    behaviour) is the only transition that returns ``True``. A field that was
    already empty in the baseline never counts as regressive.
    """
    had_value = bool(_descriptor_text(baseline_value))
    has_value = bool(_descriptor_text(current_value))
    return had_value and not has_value


def cmd_descriptor_regression_check(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for the ``descriptor-regression-check`` commit gate.

    Compares the baseline ``_project.json`` (read from the on-disk snapshot
    under ``--pre``) against the regenerated descriptor at the current
    project's ``.plan/project-architecture/_project.json`` and classifies the
    project-identity delta as regressive or benign. This is the defense-in-depth
    backstop for the ``api_discover`` identity-preservation fix: even if a future
    source path reintroduces the worktree-basename corruption, the
    ``architecture-refresh`` commit gate refuses to commit a regressive delta.

    Regressive predicates (each contributes one ``violations[]`` entry):

    * ``name`` — the baseline carried a curated name AND the regenerated name
      differs from it. A regenerated name equal to the project-dir basename (the
      canonical worktree/plan-id corruption) is reported with that signature; any
      other divergence from the curated baseline name is also regressive.
    * ``description`` — transitioned from non-empty to empty (curated text wiped).
    * ``description_reasoning`` — transitioned from non-empty to empty.

    A benign refresh (identity preserved, only the ``modules`` index changing as
    modules are added/removed) returns ``regressive: false`` with no violations.

    Error contract: when the snapshot directory or its ``_project.json`` is
    missing, returns ``status: error, error: snapshot_not_found, path: <pre>``;
    when the current project's ``_project.json`` is absent, returns the standard
    ``require_project_meta_result`` error.
    """
    pre_arg = args.pre
    snapshot_dir = _resolve_snapshot_dir(pre_arg)
    baseline_meta_path = snapshot_dir / FILE_PROJECT_META

    if not baseline_meta_path.is_file():
        return {
            'status': 'error',
            'error': 'snapshot_not_found',
            'path': pre_arg,
        }

    try:
        baseline_meta = json.loads(baseline_meta_path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        return {
            'status': 'error',
            'error': 'snapshot_not_found',
            'path': pre_arg,
            'detail': str(e),
        }

    try:
        current_meta = load_project_meta(args.project_dir)
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)

    project_basename = Path(args.project_dir).resolve().name

    violations: list[dict[str, str]] = []

    baseline_name = _descriptor_text(baseline_meta.get('name'))
    current_name = _descriptor_text(current_meta.get('name'))
    if baseline_name and current_name != baseline_name:
        if current_name == project_basename:
            reason = (
                f'name overwritten with the project-dir basename "{project_basename}" '
                f'(curated name was "{baseline_name}")'
            )
        else:
            reason = f'name changed from curated "{baseline_name}" to "{current_name}"'
        violations.append({'field': 'name', 'reason': reason})

    if _is_blanked(baseline_meta.get('description'), current_meta.get('description')):
        violations.append({'field': 'description', 'reason': 'curated description blanked'})

    if _is_blanked(baseline_meta.get('description_reasoning'), current_meta.get('description_reasoning')):
        violations.append(
            {'field': 'description_reasoning', 'reason': 'curated description_reasoning blanked'}
        )

    return {
        'status': 'success',
        'regressive': bool(violations),
        'violations': violations,
    }
