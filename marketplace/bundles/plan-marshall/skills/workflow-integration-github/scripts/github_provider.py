"""
Provider extension for GitHub CI provider integration.

Extension point: plan-marshall:extension-api/standards/ext-point-provider

Declares provider requirements for the workflow-integration-github skill.
GitHub uses system-level authentication (gh CLI login), not
HTTP headers managed by plan-marshall.

Discovered by discover-and-persist and persisted to marshal.json.
"""


def get_provider_declarations():
    """Return provider declarations for GitHub CI integration."""
    return [
        {
            'skill_name': 'plan-marshall:workflow-integration-github',
            'category': 'ci',
            'display_name': 'GitHub CLI (gh)',
            'default_url': 'https://github.com',
            'description': 'GitHub CI provider via gh CLI — PRs, issues, CI status, reviews',
            'verify_command': 'gh auth status',
        },
    ]
