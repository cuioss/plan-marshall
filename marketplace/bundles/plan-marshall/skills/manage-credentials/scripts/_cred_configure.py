"""
Interactive credential configuration wizard.

Discovers available credential extensions, presents selection menu,
prompts for URL/auth/token via getpass, writes credential file,
and registers metadata.
"""

import getpass
import sys

from _credentials_core import (
    VALID_AUTH_TYPES,
    discover_credential_providers,
    get_project_name,
    register_credential_metadata,
    save_credential,
)
from file_ops import output_toon  # type: ignore[import-not-found]


def run_configure(args) -> int:
    """Execute the configure subcommand."""
    providers = discover_credential_providers()

    if not providers:
        output_toon({'status': 'error', 'message': 'No credential extensions found in marketplace'})
        return 1

    # Select provider
    if args.skill:
        provider = _find_provider(providers, args.skill)
        if not provider:
            output_toon({
                'status': 'error',
                'message': f'No credential extension found for skill: {args.skill}',
                'available': [p['skill_name'] for p in providers],
            })
            return 1
    elif sys.stdin.isatty():
        provider = _select_provider(providers)
        if not provider:
            output_toon({'status': 'cancelled', 'message': 'No provider selected'})
            return 0
    else:
        output_toon({'status': 'error', 'message': '--skill is required when not running interactively'})
        return 1

    skill_name = provider['skill_name']
    scope = args.scope

    # Prompt for configuration
    print(f'\nConfiguring credentials for: {provider.get("display_name", skill_name)}')
    print(f'Description: {provider.get("description", "N/A")}')
    print(f'Scope: {scope}')
    print()

    # URL — use CLI arg, else prompt if TTY, else use provider default
    default_url = provider.get('default_url', '')
    if getattr(args, 'url', None):
        url = args.url
    elif sys.stdin.isatty():
        url_prompt = f'Base URL [{default_url}]: ' if default_url else 'Base URL: '
        url = input(url_prompt).strip() or default_url
    else:
        url = default_url
    if not url:
        output_toon({'status': 'error', 'message': 'URL is required — provide --url or run interactively'})
        return 1

    # Auth type — use CLI arg, else prompt if TTY, else use provider default
    default_auth = provider.get('auth_type', 'token')
    if getattr(args, 'auth_type', None):
        auth_type = args.auth_type
    elif sys.stdin.isatty():
        auth_prompt = f'Auth type ({", ".join(VALID_AUTH_TYPES)}) [{default_auth}]: '
        auth_type = input(auth_prompt).strip() or default_auth
    else:
        auth_type = default_auth
    if auth_type not in VALID_AUTH_TYPES:
        output_toon({'status': 'error', 'message': f'Invalid auth type: {auth_type}'})
        return 1

    # Build credential data
    data: dict = {
        'skill': skill_name,
        'url': url,
        'auth_type': auth_type,
    }

    if auth_type == 'token':
        data['header_name'] = provider.get('header_name', 'Authorization')
        data['header_value_template'] = provider.get('header_value_template', 'Bearer {token}')
        if not sys.stdin.isatty():
            output_toon({'status': 'error', 'message': 'Token input requires interactive terminal — run with ! prefix'})
            return 1
        token = getpass.getpass('Token: ')
        if not token:
            output_toon({'status': 'error', 'message': 'Token is required'})
            return 1
        data['token'] = token
    elif auth_type == 'basic':
        if not sys.stdin.isatty():
            output_toon({'status': 'error', 'message': 'Username/password input requires interactive terminal — run with ! prefix'})
            return 1
        username = input('Username: ').strip()
        if not username:
            output_toon({'status': 'error', 'message': 'Username is required'})
            return 1
        data['username'] = username
        data['password'] = getpass.getpass('Password: ')
    # auth_type == 'none': no secret needed, completes without interactive prompt

    # Optional verification
    verified = False
    if getattr(args, 'verify', None) is True:
        verified = _verify_connectivity(data, provider)
    elif getattr(args, 'verify', None) is False:
        pass  # --no-verify: skip
    elif sys.stdin.isatty():
        verify_prompt = input('\nVerify connectivity now? [Y/n]: ').strip().lower()
        if verify_prompt != 'n':
            verified = _verify_connectivity(data, provider)

    # Save credential file
    project_name = get_project_name() if scope == 'project' else None
    path = save_credential(skill_name, data, scope, project_name)

    # Register metadata (no secrets)
    register_credential_metadata(skill_name, scope, str(path), verified)

    # Output confirmation (no secrets)
    output_toon({
        'status': 'success',
        'skill': skill_name,
        'scope': scope,
        'auth_type': auth_type,
        'url': url,
        'verified': verified,
    })
    return 0


def _find_provider(providers: list[dict], skill_name: str) -> dict | None:
    """Find provider by skill name."""
    for p in providers:
        if p.get('skill_name') == skill_name:
            return p
    return None


def _select_provider(providers: list[dict]) -> dict | None:
    """Present numbered selection menu and return selected provider."""
    print('\nAvailable credential providers:')
    for i, p in enumerate(providers, 1):
        display = p.get('display_name', p['skill_name'])
        desc = p.get('description', '')
        print(f'  {i}. {display} — {desc}')
    print('  0. Cancel')
    print()

    try:
        choice = input('Select provider: ').strip()
        idx = int(choice)
        if idx == 0:
            return None
        if 1 <= idx <= len(providers):
            return providers[idx - 1]
    except (ValueError, IndexError):
        pass

    print('Invalid selection', file=sys.stderr)
    return None


def _verify_connectivity(data: dict, provider: dict) -> bool:
    """Test connectivity using RestClient. Returns True on success."""
    from _credentials_core import RestClient

    verify_endpoint = provider.get('verify_endpoint', '/')
    verify_method = provider.get('verify_method', 'GET')

    headers: dict[str, str] = {}
    auth_type = data.get('auth_type', 'none')
    if auth_type == 'token':
        header_name = data.get('header_name', 'Authorization')
        template = data.get('header_value_template', 'Bearer {token}')
        headers[header_name] = template.format(token=data.get('token', ''))
    elif auth_type == 'basic':
        import base64
        encoded = base64.b64encode(
            f'{data.get("username", "")}:{data.get("password", "")}'.encode()
        ).decode()
        headers['Authorization'] = f'Basic {encoded}'

    try:
        client = RestClient(data['url'], headers)
        client.request(verify_method, verify_endpoint)
        print('  Verification: SUCCESS')
        client.close()
        return True
    except Exception as e:
        # Don't expose credentials in error output
        print(f'  Verification: FAILED — {type(e).__name__}')
        return False
