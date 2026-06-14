"""
build-map and build-decision command handlers for manage-config.

The build.map block in marshal.json is the file-to-build
contract: a per-domain inventory of {glob, role, build_class} entries seeded
from each extension's explicit (pattern, role) routes. Each extension's
classify_globs() declares those routes directly (single-* fnmatch globs, never
recursive **); the script-shared route collector (derive_globs_from_tree)
gathers them verbatim per domain, and each (pattern, role) is then stamped with
its domain's classify_build_class(). A separate git-tracked completeness
validator (validate_tree_completeness) flags any tracked source file no declared
route covers. It is required and always seeded; user corrections are made
directly to the seeded entries (there is no separate override layer). The
default seed is write-once (an existing build_map is preserved); ``seed
--force`` clears any existing build_map and re-derives a clean one from the
current project state.

The ``build-decision`` verb is the centralized build-necessity decision API: it
returns a structured ``build`` / ``not_necessary`` verdict (the latter carrying a
log-friendly ``reason``) by delegating to the build-system-owned
``should_execute_build`` helper in ``script-shared``. The four former consumer
sites share this one entry point instead of each re-deriving the decision from
the build_map globs + live footprint.
"""

import argparse

from _config_core import (
    compute_build_map_drift,
    load_config,
    merge_build_map,
    require_initialized,
    save_config,
    seed_build_map_into,
)


def cmd_build_map(args: argparse.Namespace) -> dict:
    """Route build-map subcommands."""
    handlers = {
        'seed': cmd_build_map_seed,
        'read': cmd_build_map_read,
        'drift': cmd_build_map_drift,
    }
    handler = handlers.get(args.verb)
    if handler:
        return handler(args)
    return {'status': 'error', 'error': 'Unknown build-map verb'}


def cmd_build_map_seed(args: argparse.Namespace) -> dict:
    """Seed marshal.json::build.map from extension routes.

    Aggregates the per-domain build map by collecting each extension's explicit
    ``(pattern, role)`` routes (declared by ``classify_globs()``, gathered
    verbatim by the script-shared route collector) and stamping each with its
    domain's ``classify_build_class``, then writes it under ``build.map``.

    Default (``--force`` absent): write-once semantics — an existing seed is
    preserved (never clobbered), so user corrections survive a re-seed.

    With ``--force``: the write-once guard is bypassed — any existing
    ``build_map`` is cleared and re-derived from the current project state. Use
    this to discard stale or hand-edited entries and obtain a clean seed.
    """
    try:
        require_initialized()
        config = load_config()
        result = seed_build_map_into(config, force=getattr(args, 'force', False))
        if result['action'] in ('seeded', 're-derived'):
            save_config(config)
        return {
            'status': 'success',
            'action': result['action'],
            'domain_count': result['domain_count'],
            'build_map': result['build_map'],
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_build_map_read(args: argparse.Namespace) -> dict:
    """Return the effective build map from ``build.map``.

    Fails closed when the build_map is absent — ``merge_build_map`` raises and
    the error is surfaced in the result dict.
    """
    try:
        require_initialized()
        config = load_config()
        merged = merge_build_map(config)
        return {
            'status': 'success',
            'build_map': merged,
            'domain_count': len(merged),
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_build_map_drift(args: argparse.Namespace) -> dict:
    """Return the drift between the persisted ``build.map`` and the live derivation.

    Read-only: diffs the current derived map against the persisted block via
    :func:`compute_build_map_drift` and never calls ``save_config``. The result
    carries ``in_sync`` plus a per-domain ``drift: {domain: {added_globs,
    removed_globs}}`` block that the steward's re-run remediation gate consumes to
    decide whether to prompt for an interactive re-seed.
    """
    try:
        require_initialized()
        config = load_config()
        result = compute_build_map_drift(config)
        return {
            'status': 'success',
            'in_sync': result['in_sync'],
            'drift': result['drift'],
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_build_decision(args: argparse.Namespace) -> dict:
    """Return the centralized build-necessity verdict for a canonical command.

    Thin wrapper over the build-system-owned ``should_execute_build`` helper in
    ``script-shared`` (``extension_base``). The verdict is a pure function of the
    ``build.map`` globs and the live plan footprint:

    - ``decision: build`` when the footprint touches a registered build glob.
    - ``decision: not_necessary`` (with a non-empty ``reason``) when the build_map
      registers no globs, the footprint is empty, or the footprint intersects no
      build glob.

    All four former consumer sites (pre-push-quality-gate activation,
    phase-4-plan per-task verification derivation, the per-bundle classify logic)
    share this one entry point so the decision is never re-derived inline.
    """
    from extension_base import should_execute_build  # type: ignore[import-not-found]

    plan_id = getattr(args, 'plan_id', None) or getattr(args, 'audit_plan_id', None)
    if not plan_id:
        return {'status': 'error', 'error': 'build-decision requires --plan-id (or --audit-plan-id)'}
    try:
        verdict = should_execute_build(args.command, plan_id)
        return {'status': 'success', **verdict}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
