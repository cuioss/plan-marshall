# Extension Point: Provider

> **Type**: Standalone Convention | **Hook**: `{provider}_provider.py` file | **Implementations**: 4 | **Status**: Active

## Overview

Provider extensions declare external tool authentication needs for individual skills. Unlike other extension points, provider extensions are **not** part of `ExtensionBase` — they use a standalone `{provider}_provider.py` file convention. This is because provider needs are per-skill (e.g., a Sonar integration skill), not per-domain-bundle.

## Implementor Requirements

### Convention

- **File location**: the consuming skill's scripts directory, using the filename convention `{provider}_provider.py` (where `{provider}` is the provider key, e.g. `github`, `sonar`).
- **Required function**: `get_provider_declarations() -> list[dict]`
- **Discovery**: `_list_providers.run_discover_and_persist()` scans PYTHONPATH for `*_provider.py` and persists to marshal.json; `_providers_core.load_declared_providers()` reads from marshal.json at runtime
- **Consumer**: `manage-providers` skill

### Implementor Reference

Provider extensions use a Python docstring reference (no SKILL.md frontmatter):

```python
"""Extension point: plan-marshall:extension-api/standards/ext-point-provider"""
```

### Implementation Pattern

```python
"""Extension point: plan-marshall:extension-api/standards/ext-point-provider"""

def get_provider_declarations() -> list[dict]:
    return [
        {
            'skill_name': 'plan-marshall:workflow-integration-sonar',
            'category': 'other',
            'display_name': 'SonarCloud/SonarQube',
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

Provider needs are per-skill, not per-domain-bundle. A domain bundle may have zero or many skills that need providers. The `ExtensionBase` class models domain-level capabilities (skills, triage, recipes), while provider extensions model individual skill-level authentication requirements.

## Runtime Invocation Contract

### Parameters

None — discovery is automatic via filesystem scanning.

### Pre-Conditions

- A `{provider}_provider.py` file exists in the consuming skill's scripts subdirectory
- File contains a `get_provider_declarations()` function

### Post-Conditions

- Returns list of provider dicts with authentication configuration
- Each provider is registerable by `manage-providers`
- Credentials are stored in `.plan/credentials/`

## Hook API

### Python API

```python
def get_provider_declarations() -> list[dict]:
    """Return provider definitions.

    Each dict describes an external service that needs authentication.
    """
```

### Return Structure

Each dict in the returned list:

| Field | Type | Description |
|-------|------|-------------|
| `skill_name` | str | Bundle-prefixed skill identifier (e.g., `plan-marshall:workflow-integration-sonar`) |
| `display_name` | str | Human-readable name |
| `default_url` | str | Default base URL |
| `header_name` | str | HTTP header name for token auth |
| `header_value_template` | str | Header value template (e.g., `Bearer {token}`) |
| `verify_endpoint` | str | Endpoint for connectivity verification |
| `verify_method` | str | HTTP method for verification |
| `description` | str | Provider description |
| `category` | str | Provider category for cardinality enforcement (`version-control`, `ci`, `other`) |

## Persisted vs Wizard-time Fields

Provider declarations contain both persisted and transient fields. Only a subset is written to `marshal.json` by `discover-and-persist`:

| Persistence | Fields | Purpose |
|-------------|--------|---------|
| **Persisted to marshal.json** | `skill_name`, `category`, `verify_command`, `url`, `description` | Runtime provider identity, cardinality, health checks, API endpoint, display |
| **Wizard-time only (NOT persisted)** | `display_name`, `default_url`, `header_name`, `header_value_template`, `verify_endpoint`, `verify_method`, `extra_fields` | Used during interactive setup only. `default_url` is mapped to `url` on persist; git providers resolve `url` from `git remote get-url origin` |

The wizard reads transient fields from the provider declaration functions at setup time. After setup, only the 5-field persist contract remains in marshal.json.

## Categories and Cardinality

Provider declarations include a `category` field that determines cardinality rules during activation:

| Category | Cardinality | Enforcement |
|----------|-------------|-------------|
| `version-control` | Exactly 1 | Auto-selected (git always active) |
| `ci` | 0 or 1 | Single-select (GitHub XOR GitLab) |
| `other` | 0..N | MultiSelect |

The `discover-and-persist` command validates these rules before persisting to marshal.json. Invalid combinations (e.g., missing git, both CI providers) are rejected with validation errors.

## Storage

Credentials are stored in `~/.plan-marshall-credentials/` (not in marshal.json). Provider declarations are persisted to marshal.json by `discover-and-persist` and loaded at runtime by `_providers_core.load_declared_providers()`.

## Current Implementations

| Bundle | Skill | Provider | File |
|--------|-------|----------|------|
| plan-marshall | workflow-integration-github | GitHub CLI (gh) | `github_provider.py` |
| plan-marshall | workflow-integration-gitlab | GitLab CLI (glab) | `gitlab_provider.py` |
| plan-marshall | workflow-integration-sonar | SonarCloud/SonarQube | `sonar_provider.py` |
| plan-marshall | workflow-integration-git | Git CLI | `git_provider.py` |
