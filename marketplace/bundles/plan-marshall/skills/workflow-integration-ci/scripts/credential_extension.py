"""
Credential extension for CI provider integration (GitHub / GitLab).

Extension point: plan-marshall:extension-api/standards/ext-point-provider

Declares credential requirements for the workflow-integration-ci skill.
Both providers use system-level authentication (CLI login), not
HTTP headers managed by plan-marshall.

Discovered by manage-providers via discover_credential_providers().
"""


def get_credential_providers():
    """Return credential provider declarations for CI integration."""
    return [
        {
            'skill_name': 'tools-integration-ci-github',
            'display_name': 'GitHub CLI (gh)',
            'auth_type': 'system',
            'default_url': 'https://github.com',
            'description': 'GitHub CI provider via gh CLI — PRs, issues, CI status, reviews',
            'verify_command': 'gh auth status',
        },
        {
            'skill_name': 'tools-integration-ci-gitlab',
            'display_name': 'GitLab CLI (glab)',
            'auth_type': 'system',
            'default_url': 'https://gitlab.com',
            'description': 'GitLab CI provider via glab CLI — PRs, issues, CI status, reviews',
            'verify_command': 'glab auth status',
        },
    ]
