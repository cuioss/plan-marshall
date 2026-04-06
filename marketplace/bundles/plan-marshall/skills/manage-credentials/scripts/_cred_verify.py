"""
Verify credential connectivity.

Makes a test request using RestClient and updates verified_at metadata.
"""

from _credentials_core import (
    discover_credential_providers,
    get_authenticated_client,
    get_project_name,
    update_verified_at,
)
from file_ops import output_toon  # type: ignore[import-not-found]


def run_verify(args) -> int:
    """Execute the verify subcommand."""
    skill = args.skill
    scope = args.scope

    if not skill:
        output_toon({'status': 'error', 'message': '--skill is required for verify'})
        return 1

    # Find provider for verify endpoint
    providers = discover_credential_providers()
    provider = None
    for p in providers:
        if p.get('skill_name') == skill:
            provider = p
            break

    verify_endpoint = '/'
    verify_method = 'GET'
    if provider:
        verify_endpoint = provider.get('verify_endpoint', '/')
        verify_method = provider.get('verify_method', 'GET')

    try:
        project_name = get_project_name() if scope == 'project' else None
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
        return 1
    except Exception as e:
        # Don't expose credentials in error output
        output_toon({
            'status': 'error',
            'skill': skill,
            'verified': False,
            'error_type': type(e).__name__,
        })
        return 1
