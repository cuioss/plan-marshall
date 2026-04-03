# Solution: Document API Authentication Flow

plan_id: document-api-auth
created: 2025-12-10T10:00:00Z
compatibility: breaking — Clean-slate approach, no deprecation nor transitionary comments

## Summary

Create comprehensive documentation for the API authentication flow, including sequence diagrams, configuration guide, and troubleshooting section.

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Documentation Structure                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  docs/modules/auth/                                                          │
│  │                                                                           │
│  ├── pages/                                                                  │
│  │   │                                                                       │
│  │   ├── overview.adoc ◀────────────────────────────────────────────────┐   │
│  │   │   • Supported auth methods                                       │   │
│  │   │   • When to use which                                            │   │
│  │   │   • Security considerations                                      │   │
│  │   │                                                                  │   │
│  │   ├── configuration.adoc ◀───────────────────────────────────────┐   │   │
│  │   │   • Required properties                                      │   │   │
│  │   │   • Optional tuning                                          │   │   │
│  │   │   • Environment-specific                                     │   │   │
│  │   │                                                              │   │   │
│  │   ├── api-reference.adoc ◀───────────────────────────────────┐   │   │   │
│  │   │   • POST /auth/token                                     │   │   │   │
│  │   │   • POST /auth/refresh                                   │   │   │   │
│  │   │   • POST /auth/revoke                                    │   │   │   │
│  │   │   • GET /auth/userinfo                                   │   │   │   │
│  │   │                                                          │   │   │   │
│  │   └── troubleshooting.adoc ◀─────────────────────────────┐   │   │   │   │
│  │       • Token validation failures                        │   │   │   │   │
│  │       • Clock skew issues                                │   │   │   │   │
│  │       • Debug logging                                    │   │   │   │   │
│  │                                                          │   │   │   │   │
│  └── images/                                                │   │   │   │   │
│      │                                                      │   │   │   │   │
│      ├── jwt-flow.puml ─────────────────────────────────────┼───┼───┼───┘   │
│      │   JWT token validation sequence                      │   │   │       │
│      │                                                      │   │   │       │
│      ├── oauth2-flow.puml ──────────────────────────────────┼───┼───┘       │
│      │   OAuth2 authorization code flow                     │   │           │
│      │                                                      │   │           │
│      └── refresh-flow.puml ─────────────────────────────────┼───┘           │
│          Token refresh sequence                             │               │
│                                                             │               │
│  ◀──────────────────────────────────────────────────────────┘               │
│  Cross-references between documents                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Deliverables

### 1. Create authentication overview

High-level documentation of auth mechanisms covering supported methods, usage guidance, and security considerations.

**Metadata:**
- change_type: feature
- execution_mode: manual
- domain: java
- module: auth-docs
- depends: none

**Profiles:**
- implementation

**Affected files:**
- `docs/modules/auth/pages/overview.adoc`

**Change per file:** Create new AsciiDoc page documenting supported auth methods (JWT, OAuth2, Basic), guidance on when to use each method, and security considerations.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-maven:maven run --targets verify -pl docs`
- Criteria: Antora site builds without errors

**Success Criteria:**
- All three auth methods are documented with examples
- Security considerations section covers token storage and transport
- File passes AsciiDoc lint checks

### 2. Add sequence diagrams

Visual flow documentation for the main authentication sequences.

**Metadata:**
- change_type: feature
- execution_mode: manual
- domain: java
- module: auth-docs
- depends: 1

**Profiles:**
- implementation

**Affected files:**
- `docs/modules/auth/images/jwt-flow.puml`
- `docs/modules/auth/images/oauth2-flow.puml`
- `docs/modules/auth/images/refresh-flow.puml`

**Change per file:** Create PlantUML sequence diagrams: JWT token validation flow, OAuth2 authorization code flow, and token refresh sequence.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-maven:maven run --targets verify -pl docs`
- Criteria: PlantUML diagrams render without errors in the Antora build

**Success Criteria:**
- All three diagrams render correctly
- Diagrams are cross-referenced from overview.adoc

### 3. Write configuration guide

Step-by-step setup instructions with required properties, optional tuning, and environment-specific settings.

**Metadata:**
- change_type: feature
- execution_mode: manual
- domain: java
- module: auth-docs
- depends: 1

**Profiles:**
- implementation

**Affected files:**
- `docs/modules/auth/pages/configuration.adoc`

**Change per file:** Create AsciiDoc configuration guide with sections for required properties, optional tuning parameters, environment-specific settings, and example configurations.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-maven:maven run --targets verify -pl docs`
- Criteria: Antora site builds without errors

**Success Criteria:**
- All required configuration properties are documented with types and defaults
- At least one complete example configuration is included
- Cross-references to overview.adoc are valid

### 4. Create troubleshooting guide

Common issues and solutions for auth failures.

**Metadata:**
- change_type: feature
- execution_mode: manual
- domain: java
- module: auth-docs
- depends: 1,3

**Profiles:**
- implementation

**Affected files:**
- `docs/modules/auth/pages/troubleshooting.adoc`

**Change per file:** Create AsciiDoc troubleshooting guide covering token validation failures, clock skew issues, key configuration problems, and debug logging setup.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-maven:maven run --targets verify -pl docs`
- Criteria: Antora site builds without errors

**Success Criteria:**
- Each issue includes symptom, cause, and resolution
- Debug logging section includes concrete log output examples
- Cross-references to configuration.adoc are valid

### 5. Add API reference

Endpoint documentation for all authentication endpoints.

**Metadata:**
- change_type: feature
- execution_mode: manual
- domain: java
- module: auth-docs
- depends: 1

**Profiles:**
- implementation

**Affected files:**
- `docs/modules/auth/pages/api-reference.adoc`

**Change per file:** Create AsciiDoc API reference documenting POST /auth/token, POST /auth/refresh, POST /auth/revoke, and GET /auth/userinfo with request/response schemas and examples.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-maven:maven run --targets verify -pl docs`
- Criteria: Antora site builds without errors

**Success Criteria:**
- All four endpoints are documented with request parameters and response schemas
- Each endpoint includes at least one request/response example
- Error response codes are documented for each endpoint

## Approach

1. Audit existing code for accurate documentation
2. Create diagrams first (visual overview)
3. Write configuration guide
4. Add troubleshooting based on support tickets
5. Generate API reference from OpenAPI spec

## Dependencies

- PlantUML for diagrams
- Antora for documentation site

## Risks and Mitigations

- **Risk**: Documentation gets outdated
  - **Mitigation**: Link to source where possible, add to PR checklist
