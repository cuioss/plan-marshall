"""
Verify credential connectivity.

Makes a test request using RestClient and updates verified_at metadata.
"""

from _credentials_core import (
    discover_credential_providers,
    get_authenticated_client,
    get_project_name,
    load_credential,
    update_verified_at,
    verify_system_auth,
)
from file_ops import output_toon  # type: ignore[import-not-found]


def run_verify(args) -> int:
    """Execute the verify subcommand."""
    skill = args.skill
    scope = args.scope

    if not skill:
        output_toon({'status': 'error', 'message': '--skill is required for verify'})
        return 0

    # Find provider for verify endpoint
    providers = discover_credential_providers()
    provider = None
    for p in providers:
        if p.get('skill_name') == skill:
            provider = p
            break

    # Determine auth_type from credential file or provider declaration
    project_name = get_project_name() if scope == 'project' else None
    credential = load_credential(skill, scope if scope != 'global' else 'auto', project_name)
    auth_type = None
    if credential:
        auth_type = credential.get('auth_type')
    if not auth_type and provider:
        auth_type = provider.get('auth_type')

    # System auth: run verify_command instead of HTTP connectivity check
    if auth_type == 'system':
        if not provider:
            output_toon({
                'status': 'error',
                'message': f'No provider extension found for system-auth skill: {skill}',
            })
            return 0

        result = verify_system_auth(provider)
        if result['success']:
            update_verified_at(skill)
        output_toon({
            'status': 'success' if result['success'] else 'error',
            'skill': skill,
            'verified': result['success'],
            'auth_type': 'system',
            'command': result['command'],
            'exit_code': result['exit_code'],
        })
        return 0

    # Token/basic/none auth: HTTP connectivity check
    verify_endpoint = '/'
    verify_method = 'GET'
    if provider:
        verify_endpoint = provider.get('verify_endpoint', '/')
        verify_method = provider.get('verify_method', 'GET')

    try:
        client = get_authenticated_client(skill, project_name)

        client.request(verify_method, verify_endpoint)
        client.close()

        update_verified_at(skill)

        output_toon({
            'status': 'success',
            'skill': skill,
            'verified': True,
            'endpoint': verify_endpoint,
        })
        return 0

    except FileNotFoundError:
        output_toon({
            'status': 'error',
            'message': f'No credentials configured for {skill}',
        })
        return 0
    except Exception as e:
        # Don't expose credentials in error output
        output_toon({
            'status': 'error',
            'skill': skill,
            'verified': False,
            'error_type': type(e).__name__,
        })
        return 0
