"""
build-map command handlers for manage-config.

The build_map block in marshal.json is the file-to-build contract: a per-domain
inventory of {glob, role, build_class} entries seeded from every registered
extension's classify_globs() + classify_build_class(). The user-override layer
(build_map_overrides) survives re-seeding and wins by glob at read time.
"""

import argparse

from _config_core import (
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
    }
    handler = handlers.get(args.verb)
    if handler:
        return handler(args)
    return {'status': 'error', 'error': 'Unknown build-map verb'}


def cmd_build_map_seed(args: argparse.Namespace) -> dict:
    """Seed marshal.json::build_map from the extensions (write-once).

    Aggregates the per-domain build map from every registered extension and
    writes it under the top-level ``build_map`` key with write-once semantics —
    an existing seed is preserved (never clobbered), so user corrections survive
    a re-seed. The ``build_map_overrides`` array is left untouched.
    """
    try:
        require_initialized()
        config = load_config()
        result = seed_build_map_into(config)
        if result['action'] == 'seeded':
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
    """Return the merged effective build map (seed ∪ overrides, overrides win)."""
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
