"""
Credential extension for GitLab CI provider integration.

Extension point: plan-marshall:extension-api/standards/ext-point-provider

Declares credential requirements for the workflow-integration-gitlab skill.
GitLab uses system-level authentication (glab CLI login), not
HTTP headers managed by plan-marshall.

Discovered by manage-providers via discover_credential_providers().
"""


def get_credential_providers():
    """Return credential provider declarations for GitLab CI integration."""
    return [
        {
            'skill_name': 'workflow-integration-gitlab',
            'display_name': 'GitLab CLI (glab)',
            'auth_type': 'system',
            'default_url': 'https://gitlab.com',
            'description': 'GitLab CI provider via glab CLI — MRs, issues, CI status, reviews',
            'verify_command': 'glab auth status',
        },
    ]
