"""
List available credential providers from marketplace extensions.

Discovers credential_extension.py files across all bundles and returns
provider declarations — what CAN be configured, not what IS configured.
"""

from _credentials_core import discover_credential_providers
from file_ops import output_toon  # type: ignore[import-not-found]


def run_list_providers(args) -> int:
    """Execute the list-providers subcommand."""
    providers = discover_credential_providers()

    formatted = []
    for p in providers:
        entry: dict = {
            'skill_name': p.get('skill_name', ''),
            'display_name': p.get('display_name', ''),
            'auth_type': p.get('auth_type', 'token'),
            'default_url': p.get('default_url', ''),
            'description': p.get('description', ''),
        }
        if p.get('extra_fields'):
            entry['extra_fields'] = p['extra_fields']
        formatted.append(entry)

    output_toon({
        'status': 'success',
        'count': len(providers),
        'providers': formatted,
    })
    return 0
