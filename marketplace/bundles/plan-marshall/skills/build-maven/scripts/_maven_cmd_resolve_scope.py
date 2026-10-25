#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Maven ``resolve-test-scope`` — the scoped-test answer the pre-push gate asks.

The gate consults the ``resolve-test-scope`` verb of whichever build skill a
project's ``module-tests`` canonical resolves to. ``build-pyproject`` publishes
one; ``build-maven`` published none, so every Maven project took the gate's
DEGRADED path and the scoped-green / whole-tree-red divergence class went
un-gated.

The question is the same one, over Maven's shape. A reactor names its modules by
DIRECTORY, not by a ``marketplace/bundles/<b>`` path segment, so ownership is
answered by the longest module directory containing the path — the module's own
``paths.module`` from the architecture's Maven discovery, which is the same
module identity ``architecture which-module`` reports for the project. The
divergence decision itself is not re-implemented: it is the shared
:func:`_test_scope_divergence.resolve_test_scope`, handed this verb's ownership
resolver.

Consequences that matter to the gate:

* two modules in the footprint, or any path no module directory contains, yield
  ``divergence_possible: true`` and no ``recommended_target`` — the whole tree;
* exactly one module, every path owned, yields ``divergence_possible: false``
  with that module as ``recommended_target``;
* the reactor ROOT is not a module every path belongs to: a root-level file such
  as ``pom.xml`` is owned by no module, so it is reported in
  ``unresolved_paths`` and the run falls back to the whole tree. That is the
  fail-closed direction — a root POM change can move every module.

Everything is subprocess-free: modules come from
:func:`_maven_cmd_discover.discover_maven_modules` (a POM parse plus a filesystem
walk), never from a Maven invocation.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable

from _maven_cmd_discover import discover_maven_modules
from _test_scope_divergence import resolve_test_scope
from toon_parser import serialize_toon


def _module_ownership(modules: list) -> tuple[frozenset[str], Callable[[str], str | None]]:
    """Return the module-name set and the ``path -> module`` resolver for them.

    Ownership is the longest module directory containing the path. The reactor
    root (``paths.module`` of ``.`` or empty) is deliberately NOT a prefix: the
    root is the container of every module, not an owner of arbitrary files, and
    letting it claim them would report a root-POM change as safely scoped.

    Args:
        modules: Module dicts from ``discover_maven_modules``.

    Returns:
        ``(registered_modules, resolve)`` where ``resolve`` answers the owning
        module name or ``None``.
    """
    prefixes: list[tuple[str, str]] = []
    for module in modules:
        name = str(module.get('name') or '')
        path = str((module.get('paths') or {}).get('module') or '').strip('/')
        if name and path and path != '.':
            prefixes.append((path, name))
    prefixes.sort(key=lambda entry: len(entry[0]), reverse=True)

    registered = frozenset(name for _, name in prefixes)

    def resolve(path: str) -> str | None:
        for prefix, name in prefixes:
            if path == prefix or path.startswith(prefix + '/'):
                return name
        return None

    return registered, resolve


def _emit_error(error: str, message: str) -> int:
    """Emit a typed error envelope and return its exit code."""
    print(serialize_toon({'status': 'error', 'error': error, 'message': message}))
    return 2


def cmd_resolve_test_scope(args: argparse.Namespace) -> int:
    """Resolve the scoped module set and the divergence risk for a Maven project.

    Accepts the canonical ``--project-dir`` / ``--plan-id`` routing pair plus the
    optional task-scoped ``--changed-paths``, which supersedes the whole-plan
    footprint when present. A supplied-but-blank ``--changed-paths`` is refused:
    a footprint naming no file is a caller error, and resolving it as an empty
    footprint would report a scoped run as safe on no evidence.
    """
    from extension_base import _read_build_map_globs, _resolve_plan_footprint
    from marketplace_paths import names_real_plan

    project_dir = getattr(args, 'project_dir', None)
    changed_paths = getattr(args, 'changed_paths', None)
    globs = _read_build_map_globs(project_dir)

    footprint_resolvable = True
    if changed_paths is not None:
        footprint = [item.strip() for item in changed_paths.split(',') if item.strip()]
        if not footprint:
            return _emit_error(
                'empty_changed_paths',
                'resolve-test-scope received --changed-paths with no path in it; omit '
                '--changed-paths and pass --plan-id so the plan live footprint decides the scope',
            )
    else:
        plan_id = getattr(args, 'plan_id', None) or ''
        if not names_real_plan(plan_id):
            return _emit_error(
                'footprint_source_required',
                'resolve-test-scope requires --changed-paths (task-scoped) or --plan-id '
                '(whole-plan) to resolve the footprint',
            )
        resolved = _resolve_plan_footprint(plan_id)
        footprint_resolvable = resolved is not None
        footprint = resolved or []

    modules = discover_maven_modules(project_dir) if project_dir else []
    registered, resolve_owner = _module_ownership(modules)
    modules_resolvable = bool(registered)

    resolution = resolve_test_scope(
        footprint,
        globs,
        registered,
        bundle_modules=registered,
        module_for_path=resolve_owner,
    )
    if not footprint_resolvable or not modules_resolvable:
        # Nothing substantiates a scoped verdict: no module set, or no footprint.
        # Fail toward the whole tree rather than claim a scoped run is equivalent.
        resolution = type(resolution)(
            scoped_modules=(),
            divergence_possible=True,
            recommended_target=None,
            unresolved_paths=resolution.unresolved_paths,
            narrow_units=(),
            narrow_units_unresolved=(),
            named_only_modules=(),
            narrow_unit_module=None,
        )

    print(
        serialize_toon(
            {
                'status': 'success',
                'scoped_modules': list(resolution.scoped_modules),
                'divergence_possible': resolution.divergence_possible,
                'recommended_target': resolution.recommended_target,
                'unresolved_paths': list(resolution.unresolved_paths),
                'whole_tree_available': modules_resolvable,
                'footprint_resolvable': footprint_resolvable,
                'modules_resolvable': modules_resolvable,
            }
        )
    )
    return 0
