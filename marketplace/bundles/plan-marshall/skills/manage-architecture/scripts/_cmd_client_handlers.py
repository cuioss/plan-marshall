#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Argparse ``cmd_*`` handlers for the architecture client commands.

Extracted verbatim from ``_cmd_client``; the facade re-exports every public
name here. Covers the CLI handlers (info, modules, graph, module, overview,
commands, resolve, derive-verification, profiles, siblings, path, neighbors,
impact, files, which-module, find, diff-modules, descriptor-regression-check)
and their private helpers, including the Bucket B execution-tier augmentation,
the files-inventory readers, the snapshot diff, and the descriptor regression
gate.
"""

import argparse
import fnmatch
import hashlib
import json
from pathlib import Path
from typing import Any

from _architecture_core import (
    DATA_DIR,
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
    project_local_module_for_path,
    require_project_meta_result,
    resolve_module_for_path,
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
    """CLI handler for graph command."""
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
    persisted run-config timeout. Non-build executables return today's TOON
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
    """
    augmented = dict(executable_result)
    classification = _classify_build_executable(executable_result.get('executable', ''))
    if classification is not None:
        tool_name, command_args = classification
        bash_timeout = _lookup_bash_timeout(tool_name, command_args, project_dir)
        if bash_timeout is not None:
            augmented.update(_compute_execution_tier_fields(bash_timeout))
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
        build_class = classify_changed_path(path, merged)
        if build_class is None:
            unclaimed.append(path)
            continue
        classified.append({'path': path, 'build_class': build_class})

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

        module_name = resolve_module_for_path(path, project_dir)
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
    """CLI handler for path command."""
    try:
        path = get_module_path(args.source, args.target, args.project_dir)
        return {
            'status': 'success',
            'source': args.source,
            'target': args.target,
            'path': path,
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
    """CLI handler for neighbors command."""
    try:
        neighbors = get_module_neighbors(args.module, args.depth, args.project_dir)
        return {
            'status': 'success',
            'module': args.module,
            'depth': min(args.depth, NEIGHBORS_DEPTH_CAP),
            'neighbors': neighbors,
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
    """CLI handler for impact command."""
    try:
        impact = get_module_impact(args.module, args.project_dir)
        return {
            'status': 'success',
            'module': args.module,
            'impact': impact,
        }
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError as e:
        modules = _modules_from_exception_or_fallback(e, args.project_dir)
        return error_result_module_not_found(args.module, modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


# =============================================================================
# Files Inventory Readers (files / which-module / find)
# =============================================================================


def _flatten_inventory(files_block: dict[str, Any]) -> list[tuple[str, str]]:
    """Flatten a ``files`` block into ``(category, path)`` pairs.

    Elided categories contribute their ``sample`` paths only — callers that
    need the full list must fall back to Glob, which is the documented
    contract of the elision shape.
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


def cmd_files(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for the ``files`` reader.

    Loads the target module's ``derived.json`` and returns its ``files``
    block. When ``--category`` is supplied, the response is narrowed to
    that single bucket (and the ``elided``/``sample`` shape is preserved
    verbatim if the bucket was capped).
    """
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
    category = getattr(args, 'category', None)

    if category:
        bucket = files_block.get(category)
        if bucket is None:
            return {
                'status': 'success',
                'module': args.module,
                'category': category,
                'files': [],
            }
        return {
            'status': 'success',
            'module': args.module,
            'category': category,
            'files': bucket,
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
        3. Project-local prefix map (``.claude/skills/** → plan-marshall``).
        4. Root-inventory match (the length-0 ``default`` module), when present.
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
    for name in module_names:
        try:
            derived = load_module_derived(name, args.project_dir)
        except DataNotFoundError:
            continue
        paths = derived.get('paths') or {}
        module_path = (paths.get('module') or '').strip()

        files_block = derived.get('files') or {}
        for _category, path in _flatten_inventory(files_block):
            if path == target:
                candidate = (len(module_path.rstrip('/')), name)
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

    # 1. Exact-inventory match more specific than the root.
    if inventory_best is not None and inventory_best[0] > 0:
        resolved: str | None = inventory_best[1]
    # 2. Longest sources ∪ tests containment prefix.
    elif containment_best is not None:
        resolved = containment_best[1]
    # 3. Project-local prefix map (.claude/skills/** → plan-marshall).
    elif (project_local := project_local_module_for_path(target, module_names)) is not None:
        resolved = project_local
    # 4. Root-inventory match (the length-0 default module), when present.
    elif inventory_best is not None:
        resolved = inventory_best[1]
    else:
        resolved = None

    return {
        'status': 'success',
        'path': target,
        'module': resolved,
    }


def cmd_find(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for the ``find`` reader.

    Cross-module pattern search across the inventory. ``--pattern`` is
    glob-style (``fnmatch``), case-sensitive, anchored to the full path.
    ``--category`` narrows the search to one bucket. Elided buckets
    contribute their ``sample`` only — the same fallback contract as
    ``files``.
    """
    pattern = args.pattern
    category_filter = getattr(args, 'category', None)

    try:
        module_names = iter_modules(args.project_dir)
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

    results: list[dict[str, str]] = []
    for name in module_names:
        try:
            derived = load_module_derived(name, args.project_dir)
        except DataNotFoundError:
            continue
        files_block = derived.get('files') or {}
        for category, path in _flatten_inventory(files_block):
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
