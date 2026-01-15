"""
Extension defaults command handlers for plan-marshall-config.

Generic key-value storage for extension-set configuration defaults.
"""

import argparse
import json

from _config_core import (
    EXIT_ERROR,
    EXIT_SUCCESS,
    get_extension_defaults,
    load_config,
    output,
    require_initialized,
    save_config,
)


def cmd_ext_defaults(args: argparse.Namespace) -> int:
    """Route ext-defaults subcommands."""
    if args.verb == 'get':
        return cmd_ext_defaults_get(args)
    elif args.verb == 'set':
        return cmd_ext_defaults_set(args)
    elif args.verb == 'set-default':
        return cmd_ext_defaults_set_default(args)
    elif args.verb == 'list':
        return cmd_ext_defaults_list(args)
    elif args.verb == 'remove':
        return cmd_ext_defaults_remove(args)
    return EXIT_ERROR


def cmd_ext_defaults_get(args: argparse.Namespace) -> int:
    """Get extension default value by key."""
    try:
        require_initialized()
        config = load_config()
        ext = get_extension_defaults(config)
        key = args.key

        if key not in ext:
            output({'status': 'not_found', 'key': key})
            return EXIT_SUCCESS

        value = ext[key]
        output({'status': 'success', 'key': key, 'value': value})
        return EXIT_SUCCESS
    except Exception as e:
        output({'status': 'error', 'error': str(e)})
        return EXIT_ERROR


def cmd_ext_defaults_set(args: argparse.Namespace) -> int:
    """Set extension default value (always overwrites)."""
    try:
        require_initialized()
        config = load_config()
        ext = get_extension_defaults(config)

        key = args.key
        raw_value = args.value

        # Try to parse as JSON, fall back to string
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value

        ext[key] = value
        save_config(config)

        output({'status': 'success', 'key': key, 'value': value, 'action': 'set'})
        return EXIT_SUCCESS
    except Exception as e:
        output({'status': 'error', 'error': str(e)})
        return EXIT_ERROR


def cmd_ext_defaults_set_default(args: argparse.Namespace) -> int:
    """Set extension default value only if key doesn't exist (write-once)."""
    try:
        require_initialized()
        config = load_config()
        ext = get_extension_defaults(config)

        key = args.key
        raw_value = args.value

        if key in ext:
            output({'status': 'skipped', 'key': key, 'reason': 'key_exists', 'existing_value': ext[key]})
            return EXIT_SUCCESS

        # Try to parse as JSON, fall back to string
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value

        ext[key] = value
        save_config(config)

        output({'status': 'success', 'key': key, 'value': value, 'action': 'set_default'})
        return EXIT_SUCCESS
    except Exception as e:
        output({'status': 'error', 'error': str(e)})
        return EXIT_ERROR


def cmd_ext_defaults_list(args: argparse.Namespace) -> int:
    """List all extension defaults."""
    try:
        require_initialized()
        config = load_config()
        ext = get_extension_defaults(config)

        output({'status': 'success', 'extension_defaults': ext, 'count': len(ext)})
        return EXIT_SUCCESS
    except Exception as e:
        output({'status': 'error', 'error': str(e)})
        return EXIT_ERROR


def cmd_ext_defaults_remove(args: argparse.Namespace) -> int:
    """Remove extension default by key."""
    try:
        require_initialized()
        config = load_config()
        ext = get_extension_defaults(config)

        key = args.key

        if key not in ext:
            output({'status': 'skipped', 'key': key, 'reason': 'key_not_found'})
            return EXIT_SUCCESS

        del ext[key]
        save_config(config)

        output({'status': 'success', 'key': key, 'action': 'removed'})
        return EXIT_SUCCESS
    except Exception as e:
        output({'status': 'error', 'error': str(e)})
        return EXIT_ERROR
