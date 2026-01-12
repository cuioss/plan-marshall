# LogMessages Documentation Standards

## Overview

Every LogMessages class MUST have corresponding documentation in AsciiDoc format. This documentation provides a comprehensive reference for all production log messages, enabling teams to understand, monitor, and troubleshoot system behavior.

## File Location

The documentation file must be located at:
```
doc/LogMessages.adoc
```

This file should be maintained in the project root's `doc/` directory alongside other project documentation (Requirements.adoc, Specification.adoc, etc.).

## Scope

**What to Document**:
- All INFO level messages (identifier range 001-099)
- All WARN level messages (identifier range 100-199)
- All ERROR level messages (identifier range 200-299)
- All FATAL level messages (identifier range 300-399)

**What NOT to Document**:
- DEBUG level messages (no LogRecord, no identifiers)
- TRACE level messages (no LogRecord, no identifiers)

## Document Structure

The LogMessages.adoc file must follow this structure:

```asciidoc
= Log Messages for [Module Name]
:toc: left
:toclevels: 2

== Overview

All messages follow the format: [Module-Prefix]-[identifier]: [message]

This document catalogs all production log messages for the [Module Name] module.
Each message includes an identifier, component, message template, and description.

== INFO Level (001-099)

[cols="1,1,2,2", options="header"]
|===
|ID |Component |Message |Description
|AUTH-001 |AUTH |User '%s' successfully logged in |Logged when a user successfully authenticates
|AUTH-002 |AUTH |User '%s' logged out |Logged when a user logs out of the system
|AUTH-003 |AUTH |Session created for user '%s' with validity '%s' |Logged when a new session is created
|===

== WARN Level (100-199)

[cols="1,1,2,2", options="header"]
|===
|ID |Component |Message |Description
|AUTH-100 |AUTH |Login failed for user '%s' |Logged when a login attempt fails
|AUTH-101 |AUTH |Rate limit exceeded for user '%s' |Logged when user exceeds allowed request rate
|AUTH-102 |AUTH |Clock skew detected: %s seconds |Logged when system clock differs from expected
|===

== ERROR Level (200-299)

[cols="1,1,2,2", options="header"]
|===
|ID |Component |Message |Description
|AUTH-200 |AUTH |Authentication error occurred: %s |Logged when a system error occurs during authentication
|AUTH-201 |AUTH |Database connection failed: %s |Logged when database connection cannot be established
|AUTH-202 |AUTH |Token validation failed for user '%s': %s |Logged when token validation fails
|===

== FATAL Level (300-399)

[cols="1,1,2,2", options="header"]
|===
|ID |Component |Message |Description
|AUTH-300 |AUTH |Critical authentication failure: %s |Logged when authentication system fails critically
|AUTH-301 |AUTH |Configuration invalid: %s |Logged when required configuration is missing or invalid
|===
```

## Table Format

Each log level section contains a table with four columns:

### Column Definitions

1. **ID** (Column 1)
   - Format: `[MODULE-PREFIX]-[IDENTIFIER]`
   - Example: `AUTH-001`, `TOKEN-100`, `DB-200`
   - Must match the LogRecord identifier exactly

2. **Component** (Column 2)
   - The module prefix from the LogMessages class
   - Example: `AUTH`, `TOKEN`, `DB`
   - Helps identify the source component

3. **Message** (Column 3)
   - The exact message template from the LogRecord
   - Must include all `%s` placeholders
   - Example: `User '%s' successfully logged in`

4. **Description** (Column 4)
   - Human-readable explanation of when this message is logged
   - Should describe the business/technical condition that triggers the message
   - Example: "Logged when a user successfully authenticates"

### Table Options

```asciidoc
[cols="1,1,2,2", options="header"]
```

- Column widths: `1,1,2,2` (ID and Component narrower, Message and Description wider)
- `options="header"` enables header row styling

## Documentation Rules

### 1. Exact Match Requirement

**The documentation MUST exactly match the implementation**:

```java
// In LogMessages class
public static final LogRecord USER_LOGIN = LogRecordModel.builder()
    .template("User %s logged in successfully")  // Template
    .prefix("AUTH")                                // Component
    .identifier(1)                                 // Identifier
    .build();
```

```asciidoc
// In LogMessages.adoc
|AUTH-001 |AUTH |User %s logged in successfully |Logged when a user successfully authenticates
```

**Verification checklist**:
- [ ] Identifier matches (AUTH-001 = prefix AUTH + identifier 1)
- [ ] Component matches (AUTH)
- [ ] Message template matches exactly (including `%s` placeholders)
- [ ] Description explains when the message is logged

### 2. Update Synchronization

**Documentation must be updated whenever log messages are modified**:

| Code Change | Required Documentation Update |
|------------|------------------------------|
| New LogRecord added | Add new row to appropriate table |
| LogRecord message changed | Update Message column |
| LogRecord identifier changed | Update ID column |
| LogRecord deleted | Remove row from table |
| Module prefix changed | Update all IDs and Component columns |

### 3. Organization by Level

**Messages must be organized in separate tables by log level**:

- Separate section for each level (INFO, WARN, ERROR, FATAL)
- Tables within each section
- No mixing of levels in a single table
- Levels appear in order: INFO → WARN → ERROR → FATAL

### 4. Identifier Range Compliance

**Identifiers in each table must follow the standard ranges**:

- INFO section: Only 001-099 identifiers
- WARN section: Only 100-199 identifiers
- ERROR section: Only 200-299 identifiers
- FATAL section: Only 300-399 identifiers

### 5. No DEBUG/TRACE Documentation

**DEBUG and TRACE messages are NOT documented**:

- They don't use LogRecord
- They don't have identifiers
- They are development-only messages
- Documentation focuses on production-observable messages

## Complete Example

Here's a complete example for an authentication module:

```asciidoc
= Log Messages for Portal Authentication Module
:toc: left
:toclevels: 2

== Overview

All messages follow the format: PortalAuth-[identifier]: [message]

This document catalogs all production log messages for the Portal Authentication module.
Each message includes an identifier, component, message template, and description.

== INFO Level (001-099)

[cols="1,1,2,2", options="header"]
|===
|ID |Component |Message |Description
|PortalAuth-001 |AUTH |User '%s' successfully logged in |Logged when a user successfully authenticates
|PortalAuth-002 |AUTH |User '%s' logged out |Logged when a user logs out of the system
|PortalAuth-003 |AUTH |Session created for user '%s' with validity '%s' |Logged when a new session is created for authenticated user
|PortalAuth-004 |AUTH |Password changed for user '%s' |Logged when a user successfully changes their password
|===

== WARN Level (100-199)

[cols="1,1,2,2", options="header"]
|===
|ID |Component |Message |Description
|PortalAuth-100 |AUTH |Login failed for user '%s' |Logged when a login attempt fails due to invalid credentials
|PortalAuth-101 |AUTH |Rate limit exceeded for user '%s' |Logged when user exceeds allowed authentication request rate
|PortalAuth-102 |AUTH |Clock skew detected: %s seconds |Logged when system clock differs significantly from token timestamps
|PortalAuth-103 |AUTH |Deprecated authentication method used: %s |Logged when client uses deprecated authentication approach
|===

== ERROR Level (200-299)

[cols="1,1,2,2", options="header"]
|===
|ID |Component |Message |Description
|PortalAuth-200 |AUTH |Authentication error occurred: %s |Logged when a system error occurs during authentication process
|PortalAuth-201 |AUTH |Database connection failed: %s |Logged when database connection cannot be established for authentication
|PortalAuth-202 |AUTH |Token validation failed for user '%s': %s |Logged when JWT token validation fails
|PortalAuth-203 |AUTH |Session store error: %s |Logged when session storage/retrieval encounters an error
|===

== FATAL Level (300-399)

[cols="1,1,2,2", options="header"]
|===
|ID |Component |Message |Description
|PortalAuth-300 |AUTH |Critical authentication failure: %s |Logged when authentication system fails critically and cannot recover
|PortalAuth-301 |AUTH |Required configuration missing: %s |Logged when essential authentication configuration is missing
|PortalAuth-302 |AUTH |Key management system unavailable |Logged when cryptographic key management system is unreachable
|===
```

## Integration with Project Documentation

The LogMessages.adoc file should be:

1. **Linked from Specification.adoc**:
   ```asciidoc
   * link:LogMessages.adoc[Log Messages]
   ```

2. **Listed in project structure**:
   ```
   project-root/
   ├── doc/
   │   ├── Requirements.adoc
   │   ├── Specification.adoc
   │   ├── LogMessages.adoc  ← Here
   │   └── specification/
   │       └── ...
   ```

3. **Version controlled**: Track changes in git alongside code
4. **Reviewed in pull requests**: Documentation changes reviewed with code changes
5. **Updated in same commit**: Update documentation in the same commit as LogMessages code changes

## Quality Checklist

When creating or updating LogMessages.adoc:

- [ ] File exists at `doc/LogMessages.adoc`
- [ ] Contains all INFO level messages (001-099)
- [ ] Contains all WARN level messages (100-199)
- [ ] Contains all ERROR level messages (200-299)
- [ ] Contains all FATAL level messages (300-399)
- [ ] No DEBUG or TRACE messages documented
- [ ] All identifiers match implementation exactly
- [ ] All message templates match implementation exactly
- [ ] All component prefixes match implementation
- [ ] Tables organized by log level
- [ ] Each message has a description
- [ ] AsciiDoc syntax is correct
- [ ] File is linked from Specification.adoc
- [ ] Changes committed with corresponding code changes

## Benefits

Maintaining comprehensive LogMessages documentation provides:

1. **Operational Visibility**: Teams know what messages mean and when they occur
2. **Monitoring Setup**: Enables creation of alerts based on specific message identifiers
3. **Troubleshooting**: Helps diagnose issues by understanding message context
4. **Knowledge Transfer**: New team members can understand system behavior
5. **Compliance**: Provides audit trail of system events and error conditions
6. **Documentation Accuracy**: Enforces synchronization between code and documentation
