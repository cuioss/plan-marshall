"""
Provider extension for GitLab CI provider integration.

Extension point: plan-marshall:extension-api/standards/ext-point-provider

Declares provider requirements for the workflow-integration-gitlab skill.
GitLab uses system-level authentication (glab CLI login), not
HTTP headers managed by plan-marshall.

Discovered by discover-and-persist and persisted to marshal.json.
"""


def get_provider_declarations():
    """Return provider declarations for GitLab CI integration."""
    return [
        {
            'skill_name': 'plan-marshall:workflow-integration-gitlab',
            'category': 'ci',
            'display_name': 'GitLab CLI (glab)',
            'default_url': 'https://gitlab.com',
            'description': 'GitLab CI provider via glab CLI — MRs, issues, CI status, reviews',
            'verify_command': 'glab auth status',
            'detection': {
                'url_patterns': [r'gitlab\.com'],
                'directory_markers': ['.gitlab-ci.yml'],
                'enterprise_patterns': [r'gitlab\.', r'\.gitlab\.'],
            },
        },
    ]
