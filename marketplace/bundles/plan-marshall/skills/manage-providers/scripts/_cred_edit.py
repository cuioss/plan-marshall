"""
Edit existing credentials.

Updates non-secret fields (URL, auth_type) via CLI args.
For secret changes, the user edits the credential file directly.
"""

from _providers_core import (
    VALID_AUTH_TYPES,
    check_credential_completeness,
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
        return 0

    existing = load_credential(skill, scope, project_name)
    if not existing:
        output_toon({
            'status': 'error',
            'message': f'No credentials found for {skill} (scope: {scope})',
        })
        return 0

    # Update non-secret fields from CLI args, keep existing otherwise
    url = getattr(args, 'url', None) or existing.get('url', '')
    auth_type = getattr(args, 'auth_type', None) or existing.get('auth_type', 'token')
    if auth_type not in VALID_AUTH_TYPES:
        output_toon({'status': 'error', 'message': f'Invalid auth type: {auth_type}'})
        return 0

    data = dict(existing)
    data['url'] = url
    data['auth_type'] = auth_type

    path = save_credential(skill, data, scope, project_name)
    register_credential_metadata(skill, scope, str(path))

    completeness = check_credential_completeness(skill, scope, project_name)

    output_toon({
        'status': 'success',
        'skill': skill,
        'scope': scope,
        'action': 'edited',
        'path': str(path),
        'needs_editing': not completeness['complete'],
        'placeholders': completeness.get('placeholders', []),
    })
    return 0
