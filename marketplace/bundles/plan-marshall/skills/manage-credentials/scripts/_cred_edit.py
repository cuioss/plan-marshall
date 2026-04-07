"""
Edit existing credentials.

Re-prompts for token/password while preserving existing defaults
for URL, auth_type, and other fields.
"""

import getpass
import sys

from _credentials_core import (
    VALID_AUTH_TYPES,
    get_project_name,
    load_credential,
    register_credential_metadata,
    save_credential,
)
from file_ops import output_toon  # type: ignore[import-not-found]


def run_edit(args) -> int:
    """Execute the edit subcommand."""
    skill = args.skill
    scope = args.scope
    project_name = get_project_name() if scope == 'project' else None

    if not skill:
        output_toon({'status': 'error', 'message': '--skill is required for edit'})
        return 1

    existing = load_credential(skill, scope, project_name)
    if not existing:
        output_toon({
            'status': 'error',
            'message': f'No credentials found for {skill} (scope: {scope})',
        })
        return 1

    print(f'\nEditing credentials for: {skill} (scope: {scope})')
    print('Press Enter to keep existing values.\n')

    # URL — use CLI arg, else prompt if TTY, else keep existing
    current_url = existing.get('url', '')
    if getattr(args, 'url', None):
        url = args.url
    elif sys.stdin.isatty():
        url = input(f'Base URL [{current_url}]: ').strip() or current_url
    else:
        url = current_url

    # Auth type — use CLI arg, else prompt if TTY, else keep existing
    current_auth = existing.get('auth_type', 'token')
    if getattr(args, 'auth_type', None):
        auth_type = args.auth_type
    elif sys.stdin.isatty():
        auth_type = input(f'Auth type ({", ".join(VALID_AUTH_TYPES)}) [{current_auth}]: ').strip() or current_auth
    else:
        auth_type = current_auth
    if auth_type not in VALID_AUTH_TYPES:
        output_toon({'status': 'error', 'message': f'Invalid auth type: {auth_type}'})
        return 1

    data: dict = {
        'skill': skill,
        'url': url,
        'auth_type': auth_type,
    }

    if auth_type == 'token':
        data['header_name'] = existing.get('header_name', 'Authorization')
        data['header_value_template'] = existing.get('header_value_template', 'Bearer {token}')
        if sys.stdin.isatty():
            token = getpass.getpass('New token (Enter to keep existing): ')
            data['token'] = token if token else existing.get('token', '')
        else:
            data['token'] = existing.get('token', '')
    elif auth_type == 'basic':
        current_user = existing.get('username', '')
        if sys.stdin.isatty():
            data['username'] = input(f'Username [{current_user}]: ').strip() or current_user
            password = getpass.getpass('New password (Enter to keep existing): ')
            data['password'] = password if password else existing.get('password', '')
        else:
            data['username'] = current_user
            data['password'] = existing.get('password', '')

    path = save_credential(skill, data, scope, project_name)
    register_credential_metadata(skill, scope, str(path))

    output_toon({
        'status': 'success',
        'skill': skill,
        'scope': scope,
        'action': 'edited',
    })
    return 0
