"""
Credential configuration with file-based secret entry.

Creates credential files with placeholder values for secrets.
The user edits the file directly to add real secrets.
No interactive input, no secrets through the LLM.
"""

from _providers_core import (
    SECRET_PLACEHOLDERS,
    check_credential_completeness,
    get_project_name,
    load_credential,
    load_declared_providers,
    read_provider_config,
    register_credential_metadata,
    save_credential,
    write_provider_config,
)
from file_ops import output_toon  # type: ignore[import-not-found]


def run_configure(args) -> int:
    """Execute the configure subcommand."""
    providers = load_declared_providers()

    if not providers:
        output_toon({'status': 'error', 'message': 'No credential extensions found in marketplace'})
        return 0

    if not args.skill:
        output_toon({'status': 'error', 'message': '--skill is required'})
        return 0

    provider = _find_provider(providers, args.skill)
    if not provider:
        output_toon({
            'status': 'error',
            'message': f'No credential extension found for skill: {args.skill}',
            'available': [p['skill_name'] for p in providers],
        })
        return 0

    skill_name = provider['skill_name']
    scope = args.scope

    # Infer auth type from convention:
    # - verify_command present → system auth (CLI tool)
    # - header_name present → token auth (API with auth header)
    # - Otherwise → token (default for HTTP APIs)
    # CLI --auth-type override is still respected if provided
    if provider.get('verify_command'):
        inferred_auth = 'system'
    elif provider.get('header_name'):
        inferred_auth = 'token'
    else:
        inferred_auth = 'token'
    auth_type = getattr(args, 'auth_type', None) or inferred_auth

    default_url = provider.get('default_url', '')
    url = getattr(args, 'url', None) or default_url
    if not url and auth_type != 'system':
        output_toon({'status': 'error', 'message': 'URL is required — provide --url'})
        return 0

    # Check if credential already exists
    project_name = get_project_name() if scope == 'project' else None
    completeness = check_credential_completeness(skill_name, scope, project_name)

    if completeness['exists']:
        # Load existing to compare auth_type and URL — if mismatch, reconfigure
        existing = load_credential(skill_name, scope, project_name)
        existing_auth = existing.get('auth_type', 'none') if existing else 'none'
        # URL is in marshal.json (preferred) or credential file (legacy fallback)
        existing_provider_config = read_provider_config(skill_name)
        existing_url = existing_provider_config.get('url', '') or (
            existing.get('url', '') if existing else ''
        )

        if existing_auth == auth_type and existing_url == url:
            if completeness['complete']:
                output_toon({
                    'status': 'exists_complete',
                    'skill': skill_name,
                    'scope': scope,
                    'path': completeness['path'],
                    'needs_editing': False,
                })
                return 0
            else:
                output_toon({
                    'status': 'exists_incomplete',
                    'skill': skill_name,
                    'scope': scope,
                    'path': completeness['path'],
                    'needs_editing': True,
                    'placeholders': completeness['placeholders'],
                })
                return 0
        # auth_type or URL mismatch — fall through to reconfigure

    # Build credential data — secrets only (system auth has no secrets)
    data: dict = {
        'skill': skill_name,
        'auth_type': auth_type,
    }

    if auth_type == 'token':
        data['header_name'] = provider.get('header_name', 'Authorization')
        data['header_value_template'] = provider.get('header_value_template', 'Bearer {token}')
        data['token'] = SECRET_PLACEHOLDERS['token']
    elif auth_type == 'basic':
        data['username'] = SECRET_PLACEHOLDERS['username']
        data['password'] = SECRET_PLACEHOLDERS['password']
    # auth_type == 'system': no secrets needed, just skill + auth_type for registration

    # Save credential file (secrets only)
    path = save_credential(skill_name, data, scope, project_name)

    # Write non-secret config to marshal.json
    provider_config: dict[str, str] = {'url': url}
    extra_fields = getattr(args, 'extra', None) or []
    for pair in extra_fields:
        if '=' in pair:
            key, value = pair.split('=', 1)
            provider_config[key] = value
    write_provider_config(skill_name, provider_config)

    # Register metadata (no secrets)
    register_credential_metadata(skill_name, scope, str(path), verified=False)

    completeness = check_credential_completeness(skill_name, scope, project_name)
    result = {
        'status': 'created',
        'skill': skill_name,
        'scope': scope,
        'auth_type': auth_type,
        'url': url,
        'path': str(path),
        'needs_editing': not completeness['complete'],
    }
    if not completeness['complete']:
        result['placeholders'] = completeness['placeholders']

    output_toon(result)
    return 0


def _find_provider(providers: list[dict], skill_name: str) -> dict | None:
    """Find provider by skill name."""
    for p in providers:
        if p.get('skill_name') == skill_name:
            return p
    return None
