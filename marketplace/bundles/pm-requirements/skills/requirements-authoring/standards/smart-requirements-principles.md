# SMART Requirements Principles

Standards for creating requirements that follow SMART principles: Specific, Measurable, Achievable, Relevant, and Time-bound.

## SMART Principles Overview

All requirements must follow [SMART principles](https://www.atlassian.com/blog/productivity/how-to-write-smart-goals):

- **Specific**: Clear and unambiguous statements of what is needed
- **Measurable**: Testable and verifiable outcomes
- **Achievable**: Realistic within project constraints
- **Relevant**: Aligned with project goals and user needs
- **Time-bound**: Clear delivery expectations (when applicable)

## Specific Requirements

### Definition

Requirements must clearly state what the system must do without ambiguity.

### Good Examples

```asciidoc
✅ The system must support OAuth 2.0 authentication with PKCE extension
✅ Token validation must verify signature, expiration, and issuer claims
✅ The API must accept JSON requests with Content-Type: application/json
```

### Bad Examples

```asciidoc
❌ The system should handle authentication
❌ The system must be secure
❌ The API should work well
```

### Guidelines

- Use precise technical terms
- Specify exact standards or protocols
- Define clear boundaries and scope
- Avoid vague words like "handle", "support", "work well"

## Measurable Requirements

### Definition

Requirements must define testable criteria that can be objectively verified.

### Good Examples

```asciidoc
✅ Token validation must complete within 50ms for 95% of requests
✅ The system must support at least 1000 concurrent users
✅ API response codes must follow RFC 7231 HTTP status code standards
✅ Log entries must include ISO 8601 formatted timestamps
```

### Bad Examples

```asciidoc
❌ The system must be fast
❌ Authentication should be quick
❌ The system must handle many users
❌ Logs should be detailed
```

### Guidelines

- Include specific numeric thresholds
- Reference measurable standards (RFCs, specifications)
- Define percentiles for performance (95th, 99th)
- Specify exact formats and protocols

## Achievable Requirements

### Definition

Requirements must be realistic given project constraints, technology, and resources.

### Good Examples

```asciidoc
✅ The system must cache validation results for 5 minutes
✅ Token expiration must be configurable between 5 minutes and 24 hours
✅ The system must support RS256 and HS256 signature algorithms
```

### Bad Examples

```asciidoc
❌ The system must validate tokens in 0.001ms
❌ The system must support all JWT signature algorithms
❌ The system must achieve 100% uptime with no infrastructure
```

### Guidelines

- Consider technical constraints
- Account for realistic performance expectations
- Avoid absolute requirements (100% uptime, zero latency)
- Balance requirements with project resources

## Relevant Requirements

### Definition

Requirements must align with project goals and provide clear value.

### Good Examples

```asciidoc
✅ JWT-1: Token validation framework
   Relevant because: Core security requirement for API authentication

✅ JWT-4: Token expiration handling
   Relevant because: Prevents unauthorized access with expired tokens

✅ JWT-6: Security audit logging
   Relevant because: Enables security monitoring and incident response
```

### Bad Examples

```asciidoc
❌ The system must support XML configuration
   (When project uses YAML and has no XML requirement)

❌ The system must provide a GUI dashboard
   (For a library component with no UI requirement)
```

### Guidelines

- Every requirement should trace to a clear business or technical need
- Document rationale when relevance isn't obvious
- Challenge requirements that don't serve project goals
- Remove requirements that are "nice to have" but not necessary

## Time-bound Requirements (When Applicable)

### Definition

Requirements specify delivery expectations when timing is critical.

### Good Examples

```asciidoc
✅ JWT-5: Performance Requirements
   Token validation must complete within 50ms for 95% of requests

✅ JWT-4: Token Expiration Handling
   Expired tokens must be rejected within the configured clock skew tolerance (default: 60 seconds)
```

### When to Include Time Bounds

- Performance requirements (latency, throughput)
- Timeout and expiration handling
- Scheduled operations (backups, cleanup)
- Cache TTLs and refresh intervals

### When Time Bounds Are Not Applicable

- Functional capabilities (authentication support, data validation)
- Static configuration requirements
- Structural requirements (API design, data models)

## Testability

### Definition

Every requirement must be verifiable through testing.

### Testable Requirements

```asciidoc
✅ JWT-1: Token Validation Framework
   Test: Validate a correctly signed token → expect success
   Test: Validate an invalid signature → expect failure

✅ JWT-4: Token Expiration Handling
   Test: Validate expired token → expect rejection
   Test: Validate non-expired token → expect success
```

### Non-Testable Requirements

```asciidoc
❌ The system should be easy to use
   (How do you measure "easy"?)

❌ The code must be maintainable
   (Subjective and not verifiable through tests)
```

### Guidelines

- Define clear success criteria
- Specify expected inputs and outputs
- Enable automated test creation
- Provide concrete acceptance criteria

## Complete Requirements Examples

### Example 1: Authentication Requirement

```asciidoc
[#JWT-1]
=== JWT-1: Token Validation Framework

**Specific**: The system must validate JWT tokens according to RFC 7519

**Measurable**:
* Token validation must complete within 50ms for 95% of requests
* Validation must check signature, expiration, and issuer claims

**Achievable**: Standard JWT validation using established libraries

**Relevant**: Core security requirement for API authentication

**Testable**:
* Test valid token validation → success
* Test invalid signature → rejection
* Test expired token → rejection
* Test missing claims → rejection
```

### Example 2: Performance Requirement

```asciidoc
[#API-PERF-1]
=== API-PERF-1: Response Time Requirements

**Specific**: API endpoints must respond within defined latency thresholds

**Measurable**:
* 95th percentile response time ≤ 100ms
* 99th percentile response time ≤ 200ms
* Measured under load of 1000 concurrent users

**Achievable**: Achievable with proper caching and optimized queries

**Relevant**: Ensures acceptable user experience and system responsiveness

**Testable**: Load testing with performance monitoring tools
```

## Quality Checklist

Before finalizing requirements, verify each is:

- [ ] **Specific**: Clearly states what is needed
- [ ] **Measurable**: Includes testable criteria
- [ ] **Achievable**: Realistic within constraints
- [ ] **Relevant**: Aligned with project goals
- [ ] **Testable**: Can be verified through tests

## Common Anti-Patterns

### Vague Language

**Bad**: "The system should be secure"
**Good**: "The system must validate all input data against defined schemas and reject invalid requests with HTTP 400"

### Implementation Details

**Bad**: "The system must use a HashMap to store tokens"
**Good**: "The system must cache validated tokens to improve performance"

### Unmeasurable Claims

**Bad**: "The system should have good performance"
**Good**: "Token validation must complete within 50ms for 95% of requests"

### Irrelevant Features

**Bad**: "The system must support 50 different authentication methods"
**Good**: "The system must support OAuth 2.0 and OpenID Connect authentication"

## Integration with Testing

SMART requirements enable clear test case derivation:

```
Requirement JWT-1: Token validation must verify signature
→ Test Case: Valid signature → Accept token
→ Test Case: Invalid signature → Reject token

Requirement JWT-4: Expired tokens must be rejected
→ Test Case: Token with exp < now → Reject
→ Test Case: Token with exp > now → Accept
```

Every SMART requirement should map to at least one test case.
