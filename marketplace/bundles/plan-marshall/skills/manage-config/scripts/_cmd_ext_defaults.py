"""
Extension defaults command handlers for manage-config.

Generic key-value storage for extension-set configuration defaults.
"""

import argparse
import json

from _config_core import (
    get_extension_defaults,
    load_config,
    require_initialized,
    save_config,
)


def cmd_ext_defaults(args: argparse.Namespace) -> dict:
    """Route ext-defaults subcommands."""
    handlers = {
        'get': cmd_ext_defaults_get,
        'set': cmd_ext_defaults_set,
        'set-default': cmd_ext_defaults_set_default,
        'list': cmd_ext_defaults_list,
        'remove': cmd_ext_defaults_remove,
    }
    handler = handlers.get(args.verb)
    if handler:
        return handler(args)
    return {'status': 'error', 'error': 'Unknown ext-defaults verb'}


def cmd_ext_defaults_get(args: argparse.Namespace) -> dict:
    """Get extension default value by key."""
    try:
        require_initialized()
        config = load_config()
        ext = get_extension_defaults(config)
        key = args.key

        if key not in ext:
            return {'status': 'not_found', 'key': key}

        value = ext[key]
        return {'status': 'success', 'key': key, 'value': value}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_ext_defaults_set(args: argparse.Namespace) -> dict:
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

        return {'status': 'success', 'key': key, 'value': value, 'action': 'set'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_ext_defaults_set_default(args: argparse.Namespace) -> dict:
    """Set extension default value only if key doesn't exist (write-once)."""
    try:
        require_initialized()
        config = load_config()
        ext = get_extension_defaults(config)

        key = args.key
        raw_value = args.value

        if key in ext:
            return {'status': 'skipped', 'key': key, 'reason': 'key_exists', 'existing_value': ext[key]}

        # Try to parse as JSON, fall back to string
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value

        ext[key] = value
        save_config(config)

        return {'status': 'success', 'key': key, 'value': value, 'action': 'set_default'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_ext_defaults_list(args: argparse.Namespace) -> dict:
    """List all extension defaults."""
    try:
        require_initialized()
        config = load_config()
        ext = get_extension_defaults(config)

        return {'status': 'success', 'extension_defaults': ext, 'count': len(ext)}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_ext_defaults_remove(args: argparse.Namespace) -> dict:
    """Remove extension default by key."""
    try:
        require_initialized()
        config = load_config()
        ext = get_extension_defaults(config)

        key = args.key

        if key not in ext:
            return {'status': 'skipped', 'key': key, 'reason': 'key_not_found'}

        del ext[key]
        save_config(config)

        return {'status': 'success', 'key': key, 'action': 'removed'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
