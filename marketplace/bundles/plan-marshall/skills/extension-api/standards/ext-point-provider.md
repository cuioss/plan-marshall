# Extension Point: Provider

> **Type**: Standalone Convention | **Hook**: `credential_extension.py` file | **Implementations**: 1 | **Status**: Active

## Overview

Credential extensions declare external tool authentication needs for individual skills. Unlike other extension points, credential extensions are **not** part of `ExtensionBase` — they use a standalone `credential_extension.py` file convention. This is because credential needs are per-skill (e.g., a Sonar integration skill), not per-domain-bundle.

## Implementor Requirements

### Convention

- **File location**: `marketplace/bundles/{bundle}/skills/{skill}/scripts/credential_extension.py`
- **Required function**: `get_credential_providers() -> list[dict]`
- **Discovery**: `_credentials_core.discover_credential_providers()` scans `skills/*/scripts/credential_extension.py` across all bundles
- **Consumer**: `manage-providers` skill

### Implementor Reference

Credential extensions use a Python docstring reference (no SKILL.md frontmatter):

```python
"""Extension point: plan-marshall:extension-api/standards/ext-point-provider"""
```

### Implementation Pattern

```python
"""Extension point: plan-marshall:extension-api/standards/ext-point-provider"""

def get_credential_providers() -> list[dict]:
    return [
        {
            'skill_name': 'workflow-integration-sonar',
            'display_name': 'SonarCloud/SonarQube',
            'auth_type': 'token',
            'default_url': 'https://sonarcloud.io',
            'header_name': 'Authorization',
            'header_value_template': 'Bearer {token}',
            'verify_endpoint': '/api/authentication/validate',
            'verify_method': 'GET',
            'description': 'SonarCloud/SonarQube code quality platform',
        },
    ]
```

### Why Not Part of ExtensionBase?

Credential needs are per-skill, not per-domain-bundle. A domain bundle may have zero or many skills that need credentials. The `ExtensionBase` class models domain-level capabilities (skills, triage, recipes), while credential extensions model individual skill-level authentication requirements.

## Runtime Invocation Contract

### Parameters

None — discovery is automatic via filesystem scanning.

### Pre-Conditions

- `credential_extension.py` exists at `{bundle}/skills/{skill}/scripts/credential_extension.py`
- File contains a `get_credential_providers()` function

### Post-Conditions

- Returns list of provider dicts with authentication configuration
- Each provider is registerable by `manage-providers`
- Credentials are stored in `.plan/credentials/`

## Hook API

### Python API

```python
def get_credential_providers() -> list[dict]:
    """Return credential provider definitions.

    Each dict describes an external service that needs authentication.
    """
```

### Return Structure

Each dict in the returned list:

| Field | Type | Description |
|-------|------|-------------|
| `skill_name` | str | Skill identifier (e.g., `workflow-integration-sonar`) |
| `display_name` | str | Human-readable name |
| `auth_type` | str | Default auth type (`none`, `token`, `basic`) |
| `default_url` | str | Default base URL |
| `header_name` | str | HTTP header name for token auth |
| `header_value_template` | str | Header value template (e.g., `Bearer {token}`) |
| `verify_endpoint` | str | Endpoint for connectivity verification |
| `verify_method` | str | HTTP method for verification |
| `description` | str | Provider description |

## Storage

Credentials are stored in `.plan/credentials/` (not in marshal.json). Discovery results are not persisted — they are resolved at runtime by `_credentials_core.discover_credential_providers()`.

## Current Implementations

| Bundle | Skill | Provider |
|--------|-------|----------|
| plan-marshall | workflow-integration-sonar | SonarCloud/SonarQube |
