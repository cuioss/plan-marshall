# Requirement Prefix Selection

Standards for selecting and using requirement prefixes in CUI projects.

## Prefix Purpose

The requirement prefix serves as:

- Unique identifier namespace for requirements
- Quick project/domain identifier
- Basis for requirement numbering scheme
- Reference point for cross-document linking

## Prefix Characteristics

**Length**: 3-5 characters

**Format**: Uppercase letters, may include hyphens

**Uniqueness**: Must be unique within your organization

**Relevance**: Must be meaningful and domain-appropriate

## Selection Process

When starting a new project:

1. **Analyze project domain**: What is the primary focus?
2. **Review recommended prefixes**: Check standard prefix list
3. **Check for conflicts**: Ensure prefix isn't already used
4. **Select prefix**: Choose the most appropriate option
5. **Document decision**: Record prefix in Requirements.adoc overview

## Recommended Prefixes by Domain

| Domain | Prefix | Usage Example | Typical Projects |
|--------|--------|---------------|------------------|
| Apache NiFi | `NIFI-` | NIFI-PROC-1 | NiFi processors, integrations |
| Security | `SEC-` | SEC-AUTH-1 | Security frameworks, auth systems |
| API Development | `API-` | API-REST-1 | REST APIs, GraphQL services |
| User Interface | `UI-` | UI-COMP-1 | UI components, frameworks |
| Database | `DB-` | DB-MIGR-1 | Database layers, migration tools |
| Integration | `INT-` | INT-KAFKA-1 | Integration middleware, connectors |
| Logging | `LOG-` | LOG-AUDIT-1 | Logging frameworks, audit systems |
| Testing | `TEST-` | TEST-PERF-1 | Testing frameworks, tools |
| Configuration | `CONF-` | CONF-MGMT-1 | Configuration management |
| Workflow | `WF-` | WF-ENGINE-1 | Workflow engines, orchestration |
| Message Queue | `MQ-` | MQ-BROKER-1 | Message queue systems |
| Cache | `CACHE-` | CACHE-DIST-1 | Caching systems |
| JWT | `JWT-` | JWT-VALID-1 | JWT processing, validation |
| Cloud | `CLOUD-` | CLOUD-DEPLOY-1 | Cloud infrastructure, deployment |

## Custom Prefixes

For projects not covered by standard prefixes:

**Guidelines**:
- Use project or product acronym
- Keep it short and memorable
- Ensure it's clearly related to the domain
- Document the prefix meaning in Requirements.adoc

**Examples**:
- Payment system: `PAY-`
- Document processing: `DOC-`
- Analytics platform: `ANLYT-`
- Notification service: `NOTIF-`

**Cross-Domain Projects**:

When a project spans multiple domains (e.g., "Security API" or "NiFi Integration"):
- **Primary domain approach**: Choose the domain that best represents the project's core purpose
  - Example: Security-focused API → Use `SEC-` with hierarchical structure: `SEC-API-1`
  - Example: NiFi processor development → Use `NIFI-` with context: `NIFI-PROC-1`
- **Composite approach**: For truly balanced multi-domain projects, create a composite prefix
  - Example: Security + API project → `SECAPI-` or `SEC-API-`
  - Example: Workflow + Integration → `WFINT-` or `WF-INT-`
- **Document the choice**: Always explain the prefix rationale in Requirements.adoc to avoid confusion

## Hierarchical Prefixes

For complex multi-component projects:

**Pattern**: `[SYSTEM]-[COMPONENT]-NUM`

**Examples**:
```
[#PLAT-AUTH-1]     # Platform Authentication requirement 1
[#PLAT-DB-1]       # Platform Database requirement 1
[#PLAT-API-1]      # Platform API requirement 1
```
