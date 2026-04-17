#!/usr/bin/env python3
"""
Credential management CLI dispatcher.

Routes subcommands to individual command modules for secure credential
storage, configuration, verification, and deny rule management.

Usage:
    credentials.py configure --skill <name> [--scope global|project]
    credentials.py check --skill <name> [--scope global|project]
    credentials.py edit --skill <name> [--scope global|project]
    credentials.py verify [--skill <name>] [--scope global|project]
    credentials.py discover-and-persist
    credentials.py list-providers
    credentials.py list [--scope global|project|all]
    credentials.py remove [--skill <name>] [--scope global|project]
    credentials.py ensure-denied [--target global|project]
"""

import argparse
import sys

from file_ops import safe_main  # type: ignore[import-not-found]


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Credential management for external tool authentication', allow_abbrev=False
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # configure
    configure_parser = subparsers.add_parser(
        'configure', help='Interactive credential setup wizard', allow_abbrev=False
    )
    configure_parser.add_argument('--skill', help='Skill name (skips selection menu if provided)')
    configure_parser.add_argument('--scope', choices=['global', 'project'], default='global',
                                  help='Credential scope (default: global)')
    configure_parser.add_argument('--url', help='Base URL (skips URL prompt)')
    configure_parser.add_argument('--auth-type', choices=['none', 'token', 'basic'],
                                  help='Auth type (skips auth type prompt)')
    configure_parser.add_argument('--extra', nargs='*', metavar='KEY=VALUE',
                                  help='Extra fields as key=value pairs (e.g., --extra organization=cuioss project_key=cuioss_plan-marshall)')

    # edit
    edit_parser = subparsers.add_parser('edit', help='Edit existing credentials', allow_abbrev=False)
    edit_parser.add_argument('--skill', help='Skill name')
    edit_parser.add_argument('--scope', choices=['global', 'project'], default='global',
                             help='Credential scope (default: global)')
    edit_parser.add_argument('--url', help='New base URL (skips URL prompt)')
    edit_parser.add_argument('--auth-type', choices=['none', 'token', 'basic'],
                             help='New auth type (skips auth type prompt)')

    # check
    check_parser = subparsers.add_parser(
        'check', help='Check credential completeness', allow_abbrev=False
    )
    check_parser.add_argument('--skill', required=True, help='Skill name')
    check_parser.add_argument('--scope', choices=['global', 'project'], default='global',
                              help='Credential scope (default: global)')

    # verify
    verify_parser = subparsers.add_parser(
        'verify', help='Test credential connectivity', allow_abbrev=False
    )
    verify_parser.add_argument('--skill', help='Skill name')
    verify_parser.add_argument('--scope', choices=['global', 'project'], default='global',
                               help='Credential scope (default: global)')

    # discover-and-persist
    dap_parser = subparsers.add_parser('discover-and-persist',
                                       help='Scan PYTHONPATH for provider declarations and persist to marshal.json',
                                       allow_abbrev=False)
    dap_parser.add_argument('--providers', help='Comma-separated skill names to activate (omit for discovery-only)')

    # list-providers
    subparsers.add_parser(
        'list-providers', help='List available credential providers from marshal.json', allow_abbrev=False
    )

    # find-by-category
    fbc_parser = subparsers.add_parser(
        'find-by-category', help='Find providers by category', allow_abbrev=False
    )
    fbc_parser.add_argument('--category', required=True, help='Provider category (e.g., ci, version-control)')

    # list
    list_parser = subparsers.add_parser(
        'list', help='List configured skills (no secrets)', allow_abbrev=False
    )
    list_parser.add_argument('--scope', choices=['global', 'project', 'all'], default='all',
                             help='Credential scope filter (default: all)')

    # remove
    remove_parser = subparsers.add_parser(
        'remove', help='Remove credential and metadata', allow_abbrev=False
    )
    remove_parser.add_argument('--skill', help='Skill name')
    remove_parser.add_argument('--scope', choices=['global', 'project'], default='global',
                               help='Credential scope (default: global)')

    # ensure-denied
    denied_parser = subparsers.add_parser(
        'ensure-denied', help='Add deny rules to Claude Code settings', allow_abbrev=False
    )
    denied_parser.add_argument('--target', choices=['global', 'project'], default='project',
                               help='Settings target (default: project)')

    args = parser.parse_args()

    # Route to command module (prefixed _cred_ to avoid PYTHONPATH namespace collisions)
    if args.command == 'configure':
        from _cred_configure import run_configure
        return run_configure(args)
    elif args.command == 'check':
        from _cred_check import run_check
        return run_check(args)
    elif args.command == 'edit':
        from _cred_edit import run_edit
        return run_edit(args)
    elif args.command == 'discover-and-persist':
        from _list_providers import run_discover_and_persist
        return run_discover_and_persist(args)
    elif args.command == 'list-providers':
        from _list_providers import run_list_providers
        return run_list_providers(args)
    elif args.command == 'find-by-category':
        from _list_providers import run_find_by_category
        return run_find_by_category(args)
    elif args.command == 'verify':
        from _cred_verify import run_verify
        return run_verify(args)
    elif args.command == 'list':
        from _cred_list import run_list
        return run_list(args)
    elif args.command == 'remove':
        from _cred_remove import run_remove
        return run_remove(args)
    elif args.command == 'ensure-denied':
        from _cred_ensure_denied import run_ensure_denied
        return run_ensure_denied(args)

    return 1


if __name__ == '__main__':
    sys.exit(main())
