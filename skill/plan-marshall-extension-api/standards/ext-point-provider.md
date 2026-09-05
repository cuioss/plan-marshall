# Extension Point: Provider

> **Type**: Standalone Convention | **Hook**: `{provider}_provider.py` file | **Implementations**: 4 | **Status**: Active

## Overview

Provider extensions declare external tool authentication needs for individual skills. Unlike other extension points, provider extensions are **not** part of `ExtensionBase` — they use a standalone `{provider}_provider.py` file convention. This is because provider needs are per-skill (e.g., a Sonar integration skill), not per-domain-bundle.

### Two transport lanes

A declaration picks exactly one of two transports, and the field it carries is what selects the lane:

| Lane | Selector field | Authentication | Health check |
|------|----------------|----------------|--------------|
| **System-auth (CLI)** | `verify_command` | The vendor CLI owns its own token store; plan-marshall writes no credential file | Runs `verify_command` and reads the result — `_providers_core.verify_system_auth()` |
| **Token-auth (REST)** | `header_name` + `verify_endpoint` | A token plan-marshall stores under `~/.plan-marshall/credentials/` | An HTTP round-trip to `verify_endpoint` via `RestClient` |

A CLI-lane declaration carries **no HTTP field at all** — no `default_url`, `header_name`, `header_value_template`, `verify_endpoint`, or `verify_method`. Its host is resolved by the CLI itself, which is why declaring a base URL for it would be inert. This contract implements the decision recorded in [ADR-018](../../../../../../doc/adr/018-CI_providers_integrate_via_their_official_CLI_API_providers_via_RestClient.adoc).

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

### Implementation Pattern — token-auth (REST) lane

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

### Implementation Pattern — system-auth (CLI) lane

```python
"""Extension point: plan-marshall:extension-api/standards/ext-point-provider"""

def get_provider_declarations() -> list[dict]:
    return [
        {
            'skill_name': 'plan-marshall:workflow-integration-github',
            'category': 'ci',
            'display_name': 'GitHub CLI (gh)',
            'description': 'GitHub CI provider via gh CLI — PRs, issues, CI status, reviews',
            'verify_command': 'gh auth status',
            'detection': {
                'url_patterns': [r'github\.com'],
                'directory_markers': ['.github'],
            },
        },
    ]
```

Note what is absent: no `default_url`, no `header_name`, no `verify_endpoint`. The `gh` CLI resolves its own host — including an enterprise host — from its own configuration, so a base URL declared here would never be read.

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
- Token-auth credentials are stored in `~/.plan-marshall/credentials/`; system-auth providers store none

## Hook API

### Python API

```python
def get_provider_declarations() -> list[dict]:
    """Return provider definitions.

    Each dict describes an external service that needs authentication.
    """
```

### Return Structure

Every declaration carries the common fields below, then the field set of exactly one transport lane.

**Common to both lanes:**

| Field | Type | Description |
|-------|------|-------------|
| `skill_name` | str | Bundle-prefixed skill identifier (e.g., `plan-marshall:workflow-integration-sonar`) |
| `category` | str | Provider category for cardinality enforcement (`version-control`, `ci`, `other`) |
| `display_name` | str | Human-readable name |
| `description` | str | Provider description |

**System-auth (CLI) lane:**

| Field | Type | Description |
|-------|------|-------------|
| `verify_command` | str | The CLI command run to verify authentication (e.g., `gh auth status`). Its presence is what selects this lane |
| `detection` | dict | Optional repository-detection patterns, consumed by `ci_health.detect_provider()` |

`detection` sub-keys:

| Sub-key | Type | Description |
|---------|------|-------------|
| `url_patterns` | list[str] | Regexes matched against the `origin` remote URL (e.g., `github\.com`) |
| `directory_markers` | list[str] | Repository-relative paths whose existence identifies the provider (e.g., `.github`) |
| `enterprise_patterns` | list[str] | Additional URL regexes for self-hosted / enterprise instances, matched after `url_patterns` |

A CLI-lane declaration carries **none** of the token-auth fields below.

**Token-auth (REST) lane:**

| Field | Type | Description |
|-------|------|-------------|
| `default_url` | str | Default base URL the wizard offers, persisted as `url` |
| `header_name` | str | HTTP header name for token auth |
| `header_value_template` | str | Header value template (e.g., `Bearer {token}`) |
| `verify_endpoint` | str | Endpoint for connectivity verification |
| `verify_method` | str | HTTP method for verification |
| `extra_fields` | list | Additional values the wizard collects at setup time |

## Persisted vs Wizard-time Fields

Provider declarations contain both persisted and transient fields. Only a subset is written to `marshal.json` by `discover-and-persist`:

| Persistence | Fields | Purpose |
|-------------|--------|---------|
| **Persisted to marshal.json** | `skill_name`, `category`, `verify_command`, `description`, and `url` when one resolves | Runtime provider identity, cardinality, health checks, API endpoint, display |
| **Wizard-time only (NOT persisted)** | `display_name`, `default_url`, `header_name`, `header_value_template`, `verify_endpoint`, `verify_method`, `extra_fields`, `detection` | Used during interactive setup (or, for `detection`, loaded from the declaration at runtime) — never written to marshal.json |

`url` is **derived, not declared**, and only two things produce it:

| Lane / category | `url` in marshal.json |
|-----------------|-----------------------|
| Token-auth (REST) | `default_url` mapped to `url` on persist — the REST lane's field |
| `version-control` | Resolved from `git remote get-url origin` |
| `ci` (CLI lane) | **Absent.** These providers declare no `default_url` and resolve their own host, so no `url` key is written. `list-providers` omits the key rather than rendering an empty string, which would read as a provider configured with a blank URL |

The wizard reads transient fields from the provider declaration functions at setup time. After setup, only the persist contract above remains in marshal.json.

## Categories and Cardinality

Provider declarations include a `category` field that determines cardinality rules during activation:

| Category | Cardinality | Enforcement |
|----------|-------------|-------------|
| `version-control` | Exactly 1 | Auto-selected (git always active) |
| `ci` | 0 or 1 | Single-select (GitHub XOR GitLab) |
| `other` | 0..N | MultiSelect |

The `discover-and-persist` command validates these rules before persisting to marshal.json. Invalid combinations (e.g., missing git, both CI providers) are rejected with validation errors.

## Storage

Token-auth (REST) credentials are stored in `~/.plan-marshall/credentials/` (under the machine-global home root, overridable via `PLAN_MARSHALL_HOME`; not in marshal.json). System-auth (CLI) providers store **no credential file at all** — the vendor CLI owns its own token store, which is the credential-at-rest avoidance ADR-018 records. Provider declarations are persisted to marshal.json by `discover-and-persist` and loaded at runtime by `_providers_core.load_declared_providers()`.

## Current Implementations

| Bundle | Skill | Provider | Lane | File |
|--------|-------|----------|------|------|
| plan-marshall | workflow-integration-github | GitHub CLI (gh) | System-auth (CLI) | `github_provider.py` |
| plan-marshall | workflow-integration-gitlab | GitLab CLI (glab) | System-auth (CLI) | `gitlab_provider.py` |
| plan-marshall | workflow-integration-sonar | SonarCloud/SonarQube | Token-auth (REST) | `sonar_provider.py` |
| plan-marshall | workflow-integration-git | Git CLI | System-auth (CLI) | `git_provider.py` |
