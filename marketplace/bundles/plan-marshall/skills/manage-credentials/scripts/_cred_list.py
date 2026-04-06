"""
List configured credential skills.

Outputs metadata only — never includes credential values.
"""

from _credentials_core import list_credential_metadata
from file_ops import output_toon  # type: ignore[import-not-found]


def run_list(args) -> int:
    """Execute the list subcommand."""
    scope = args.scope
    metadata = list_credential_metadata()

    if not metadata:
        output_toon({
            'status': 'success',
            'count': 0,
            'credentials': [],
        })
        return 0

    entries = []
    for skill_name, info in sorted(metadata.items()):
        entry_scope = info.get('scope', 'global')

        # Filter by scope if requested
        if scope != 'all' and entry_scope != scope:
            continue

        entries.append({
            'skill': skill_name,
            'scope': entry_scope,
            'active': info.get('active', False),
            'verified_at': info.get('verified_at', 'never'),
        })

    output_toon({
        'status': 'success',
        'count': len(entries),
        'credentials': entries,
    })
    return 0
