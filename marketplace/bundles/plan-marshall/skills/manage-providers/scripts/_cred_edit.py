# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Edit existing credentials.

Updates non-secret fields (URL, auth_type) via CLI args, and idempotently
upserts extra non-secret fields (KEY=VALUE) into the provider config.
For secret changes, the user edits the credential file directly.
"""

import argparse

from _providers_core import (
    VALID_AUTH_TYPES,
    check_credential_completeness,
    get_project_name,
    load_credential,
    read_provider_config,
    save_credential,
    write_provider_config,
)
from file_ops import output_toon  # type: ignore[import-not-found]


def _upsert_extra_fields(skill: str, extra_pairs: list[str]) -> list[str]:
    """Idempotently upsert KEY=VALUE extras into the provider config.

    Extra fields live in marshal.json under ``credentials_config.{skill}`` —
    separate from the credential file that holds the token — so this upsert
    never touches or drops the stored token. Each supplied key is added when
    absent and replaced in place when present; all other existing extras are
    preserved. Running with the same pairs twice yields the same end state.

    Args:
        skill: Skill name keying the provider config.
        extra_pairs: Repeatable ``KEY=VALUE`` strings; entries without ``=``
            are ignored.

    Returns:
        The list of keys that were upserted (in supplied order).
    """
    provider_config = dict(read_provider_config(skill))
    upserted_keys: list[str] = []
    for pair in extra_pairs:
        if '=' in pair:
            key, value = pair.split('=', 1)
            provider_config[key] = value
            upserted_keys.append(key)

    if upserted_keys:
        write_provider_config(skill, provider_config)

    return upserted_keys


def run_edit(args: argparse.Namespace) -> int:
    """Execute the edit subcommand."""
    skill = args.skill
    scope = args.scope
    project_name = get_project_name() if scope == 'project' else None

    if not skill:
        output_toon({'status': 'error', 'message': '--skill is required for edit'})
        return 0

    existing = load_credential(skill, scope, project_name)
    if not existing:
        output_toon(
            {
                'status': 'error',
                'message': f'No credentials found for {skill} (scope: {scope})',
            }
        )
        return 0

    # Update non-secret fields from CLI args, keep existing otherwise
    url = getattr(args, 'url', None) or existing.get('url', '')
    auth_type = getattr(args, 'auth_type', None) or existing.get('auth_type', 'token')
    if auth_type not in VALID_AUTH_TYPES:
        output_toon({'status': 'error', 'message': f'Invalid auth type: {auth_type}'})
        return 0

    # Copy the existing credential so the stored token (and any other secret
    # fields) carry through untouched — only the non-secret URL/auth_type change.
    data = dict(existing)
    data['url'] = url
    data['auth_type'] = auth_type

    path = save_credential(skill, data, scope, project_name)

    # Idempotently upsert any --extra KEY=VALUE pairs into the provider config.
    extra_pairs = getattr(args, 'extra', None) or []
    extras_upserted = _upsert_extra_fields(skill, extra_pairs)

    completeness = check_credential_completeness(skill, scope, project_name)

    result: dict = {
        'status': 'success',
        'skill': skill,
        'scope': scope,
        'action': 'edited',
        'path': str(path),
        'needs_editing': not completeness['complete'],
        'placeholders': completeness.get('placeholders', []),
    }
    if extras_upserted:
        result['extras_upserted'] = extras_upserted

    output_toon(result)
    return 0
