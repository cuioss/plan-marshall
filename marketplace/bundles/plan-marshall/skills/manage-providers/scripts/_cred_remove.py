"""
Remove credential file and metadata.
"""

from _providers_core import get_project_name, remove_credential, unregister_credential_metadata
from file_ops import output_toon  # type: ignore[import-not-found]


def run_remove(args) -> int:
    """Execute the remove subcommand."""
    skill = args.skill
    scope = args.scope

    if not skill:
        output_toon({'status': 'error', 'message': '--skill is required for remove'})
        return 0

    project_name = get_project_name() if scope == 'project' else None
    removed = remove_credential(skill, scope, project_name)
    unregister_credential_metadata(skill)

    if removed:
        output_toon({
            'status': 'success',
            'skill': skill,
            'scope': scope,
            'action': 'removed',
        })
    else:
        output_toon({
            'status': 'success',
            'skill': skill,
            'scope': scope,
            'action': 'not_found',
            'message': f'No credential file found for {skill} (scope: {scope})',
        })

    return 0
