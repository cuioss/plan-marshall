# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Credential configuration with file-based secret entry.

Creates credential files with placeholder values for secrets.
The user edits the file directly to add real secrets.
No interactive input, no secrets through the LLM.
"""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

from _list_providers import find_provider_with_details  # type: ignore[import-not-found]
from _providers_core import (
    SECRET_PLACEHOLDERS,
    check_credential_completeness,
    get_project_name,
    load_credential,
    load_declared_providers,
    read_provider_config,
    save_credential,
    write_provider_config,
)
from file_ops import get_tracked_config_dir, output_toon  # type: ignore[import-not-found]

# Skill name of the Sonar provider — pom.xml auto-derivation is gated behind this
# provider so non-Sonar configure flows are byte-for-byte unchanged.
_SONAR_SKILL_NAME = 'plan-marshall:workflow-integration-sonar'

# pom.xml property names carrying the Sonar coordinates.
_POM_SONAR_PROPERTIES = {
    'organization': 'sonar.organization',
    'project_key': 'sonar.projectKey',
}


def _strip_ns(tag: object) -> str:
    """Return the local tag name, dropping any ``{namespace}`` prefix.

    Maven POMs declare the ``http://maven.apache.org/POM/4.0.0`` namespace, so
    ``ElementTree`` reports tags as ``{http://...}sonar.organization``. Matching
    on the local name handles both namespaced and namespace-less POMs.

    XML comments and processing instructions have callable (non-string) tags in
    ElementTree.  The type guard skips them cleanly instead of raising
    ``AttributeError``.
    """
    if not isinstance(tag, str):
        return ''
    return tag.rsplit('}', 1)[-1]


def _find_child(element: ET.Element, local_name: str) -> ET.Element | None:
    """Return the first direct child of ``element`` whose local tag matches."""
    for child in element:
        if _strip_ns(child.tag) == local_name:
            return child
    return None


def _find_project_pom() -> Path | None:
    """Locate the project-root ``pom.xml``, or ``None`` when absent.

    The project root is the parent of the tracked ``.plan`` config directory.
    Returns ``None`` (non-Maven project) when no ``pom.xml`` is present there.
    """
    project_root = get_tracked_config_dir().parent
    pom_path = project_root / 'pom.xml'
    return pom_path if pom_path.is_file() else None


def _parse_pom_sonar_properties(pom_path: Path) -> dict[str, str]:
    """Parse Sonar coordinates from a ``pom.xml``'s ``<properties>`` block.

    Reads ``<sonar.organization>`` and ``<sonar.projectKey>`` from
    ``/project/properties`` using stdlib ``xml.etree`` — no Maven subprocess.
    Mirrors the namespace-tolerant parsing in
    ``build-maven/scripts/_maven_cmd_discover.py::_parse_pom_xml``.

    Args:
        pom_path: Path to the ``pom.xml`` file.

    Returns:
        Dict with ``organization`` and/or ``project_key`` keys for any Sonar
        property present and non-empty. A malformed/unreadable POM, or one
        without the Sonar properties, yields an empty dict so derivation
        degrades gracefully.
    """
    try:
        root = ET.parse(pom_path).getroot()
    except (ET.ParseError, OSError):
        return {}

    properties_el = _find_child(root, 'properties')
    if properties_el is None:
        return {}

    derived: dict[str, str] = {}
    for config_key, pom_property in _POM_SONAR_PROPERTIES.items():
        prop_el = _find_child(properties_el, pom_property)
        if prop_el is not None and prop_el.text is not None:
            value = prop_el.text.strip()
            if value:
                derived[config_key] = value
    return derived


def run_configure(args: argparse.Namespace) -> int:
    """Execute the configure subcommand."""
    providers = load_declared_providers()

    if not providers:
        output_toon({'status': 'error', 'message': 'No credential extensions found in marketplace'})
        return 0

    if not args.skill:
        output_toon({'status': 'error', 'message': '--skill is required'})
        return 0

    provider = find_provider_with_details(args.skill)
    if not provider:
        output_toon(
            {
                'status': 'error',
                'message': f'No credential extension found for skill: {args.skill}',
                'available': [p['skill_name'] for p in providers],
            }
        )
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

    default_url = provider.get('url', '') or provider.get('default_url', '')
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
        existing_url = existing_provider_config.get('url', '') or (existing.get('url', '') if existing else '')

        if existing_auth == auth_type and existing_url == url:
            if completeness['complete']:
                output_toon(
                    {
                        'status': 'exists_complete',
                        'skill': skill_name,
                        'scope': scope,
                        'path': completeness['path'],
                        'needs_editing': False,
                    }
                )
                return 0
            else:
                output_toon(
                    {
                        'status': 'exists_incomplete',
                        'skill': skill_name,
                        'scope': scope,
                        'path': completeness['path'],
                        'needs_editing': True,
                        'placeholders': completeness['placeholders'],
                    }
                )
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
    supplied_keys: set[str] = set()
    for pair in extra_fields:
        if '=' in pair:
            key, value = pair.split('=', 1)
            provider_config[key] = value
            supplied_keys.add(key)

    # Sonar provider + Maven-detected: auto-derive organization/project_key from
    # pom.xml, and warn (non-fatally) when a user-supplied value disagrees.
    mismatch_warnings: list[dict[str, str]] = []
    if skill_name == _SONAR_SKILL_NAME:
        pom_path = _find_project_pom()
        if pom_path is not None:
            pom_values = _parse_pom_sonar_properties(pom_path)
            for config_key, pom_value in pom_values.items():
                if config_key in supplied_keys:
                    # User explicitly supplied this value — compare, never overwrite.
                    if provider_config[config_key] != pom_value:
                        mismatch_warnings.append(
                            {
                                'field': config_key,
                                'supplied': provider_config[config_key],
                                'pom_value': pom_value,
                            }
                        )
                else:
                    # Not supplied by the user — auto-derive from pom.xml.
                    provider_config[config_key] = pom_value

    write_provider_config(skill_name, provider_config)

    completeness = check_credential_completeness(skill_name, scope, project_name)
    result: dict = {
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
    if mismatch_warnings:
        result['warnings'] = [
            f"Supplied {w['field']}='{w['supplied']}' disagrees with pom.xml "
            f"<sonar.{'organization' if w['field'] == 'organization' else 'projectKey'}>"
            f"='{w['pom_value']}' — keeping the supplied value"
            for w in mismatch_warnings
        ]
        result['mismatches'] = mismatch_warnings

    output_toon(result)
    return 0


def _find_provider(providers: list[dict], skill_name: str) -> dict | None:
    """Find provider by skill name."""
    for p in providers:
        if p.get('skill_name') == skill_name:
            return p
    return None
