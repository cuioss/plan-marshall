"""
Provider extension for SonarCloud/SonarQube integration.

Extension point: plan-marshall:extension-api/standards/ext-point-provider

Declares provider requirements for the workflow-integration-sonar skill.
Discovered by manage-providers via discover_provider_extensions().
"""


def get_provider_declarations():
    """Return provider declarations for Sonar integration."""
    return [{
        'skill_name': 'workflow-integration-sonar',
        'display_name': 'SonarCloud / SonarQube',
        'auth_type': 'token',
        'default_url': 'https://sonarcloud.io',
        'header_name': 'Authorization',
        'header_value_template': 'Bearer {token}',
        'verify_endpoint': '/api/system/status',
        'verify_method': 'GET',
        'description': 'SonarCloud/SonarQube code analysis platform',
        'extra_fields': [
            {
                'key': 'organization',
                'label': 'SonarCloud Organization',
                'required': False,
                'auto_detect': 'ci_org',
            },
            {
                'key': 'project_key',
                'label': 'SonarCloud Project Key',
                'required': True,
                'auto_detect': 'sonar_project_key',
            },
        ],
    }]
