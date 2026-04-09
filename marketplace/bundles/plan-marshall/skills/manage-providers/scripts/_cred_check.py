"""
Check credential completeness.

Reports whether a credential file exists and has all secrets filled in
(no placeholder values remaining).
"""

from _providers_core import (
    check_credential_completeness,
    get_project_name,
)
from file_ops import output_toon  # type: ignore[import-not-found]


def run_check(args) -> int:
    """Execute the check subcommand."""
    skill = args.skill
    scope = args.scope
    project_name = get_project_name() if scope == 'project' else None

    result = check_credential_completeness(skill, scope, project_name)

    if not result['exists']:
        output_toon({
            'status': 'not_found',
            'skill': skill,
            'scope': scope,
            'message': f'No credentials found for {skill} (scope: {scope})',
        })
        return 0

    if result['complete']:
        output_toon({
            'status': 'complete',
            'skill': skill,
            'scope': scope,
            'path': result['path'],
        })
    else:
        output_toon({
            'status': 'incomplete',
            'skill': skill,
            'scope': scope,
            'path': result['path'],
            'placeholders': result['placeholders'],
        })

    return 0
