"""
Provider extension for Git integration.

Extension point: plan-marshall:extension-api/standards/ext-point-provider

Declares provider requirements for the workflow-integration-git skill.
Git uses system-level authentication (git CLI configured via global
git config or OS credential helpers), not HTTP headers managed by
plan-marshall.

Discovered by discover-and-persist and persisted to marshal.json.
"""


def get_provider_declarations():
    """Return provider declarations for Git integration."""
    return [
        {
            'skill_name': 'plan-marshall:workflow-integration-git',
            'category': 'version-control',
            'display_name': 'Git CLI',
            'description': 'Git version control via git CLI — commit, push, branch operations',
            'verify_command': 'git config user.name',
        },
    ]
