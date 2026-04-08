"""
Credential extension for GitHub CI provider integration.

Extension point: plan-marshall:extension-api/standards/ext-point-provider

Declares credential requirements for the workflow-integration-github skill.
GitHub uses system-level authentication (gh CLI login), not
HTTP headers managed by plan-marshall.

Discovered by manage-providers via discover_credential_providers().
"""


def get_credential_providers():
    """Return credential provider declarations for GitHub CI integration."""
    return [
        {
            'skill_name': 'workflow-integration-github',
            'display_name': 'GitHub CLI (gh)',
            'auth_type': 'system',
            'default_url': 'https://github.com',
            'description': 'GitHub CI provider via gh CLI — PRs, issues, CI status, reviews',
            'verify_command': 'gh auth status',
        },
    ]
