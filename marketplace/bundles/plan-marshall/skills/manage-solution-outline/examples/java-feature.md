# Solution: Add JWT Token Validation Service

plan_id: add-jwt-validation
created: 2025-12-10T10:00:00Z
compatibility: breaking — Clean-slate approach, no deprecation nor transitionary comments

## Summary

Implement a JWT token validation service for the authentication module. The service will validate tokens, extract claims, and integrate with the existing security context.

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         JWT Validation Service                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐  │
│  │ JwtConfiguration │─────▶│JwtValidationSvc  │◀─────│   KeyProvider    │  │
│  │                  │      │                  │      │   (existing)     │  │
│  │ • issuer         │      │ • validate()     │      └──────────────────┘  │
│  │ • audience       │      │ • extractClaims()│                             │
│  │ • clock-skew     │      │ • isExpired()    │      ┌──────────────────┐  │
│  └──────────────────┘      └────────┬─────────┘      │   jjwt-api       │  │
│                                     │                │   (dependency)   │  │
│                                     ▼                └──────────────────┘  │
│                            ┌──────────────────┐                             │
│                            │  SecurityContext │                             │
│                            │    (existing)    │                             │
│                            └──────────────────┘                             │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Package: de.cuioss.auth.jwt                                                │
│  New files: JwtValidationService.java, JwtConfiguration.java                │
│  Tests: JwtValidationServiceTest.java                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Deliverables

### 1. Create JwtValidationService class

**Metadata:**
- change_type: feature
- execution_mode: automated
- domain: java
- module: cui-authentication
- depends: none

**Profiles:**
- implementation

**Affected files:**
- `src/main/java/de/cuioss/auth/jwt/JwtValidationService.java`

**Change per file:** New class in package `de.cuioss.auth.jwt`; implements `validate(String token)`, `extractClaims(String token)`, and `isExpired(String token)`; depends on `KeyProvider` for signature verification; supports RS256 and HS256 algorithms via `io.jsonwebtoken:jjwt-api`.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-maven:maven run --targets compile`
- Criteria: Compiles without error

**Success Criteria:**
- Service validates JWT signatures using the existing `KeyProvider`
- Standard claims (`sub`, `iss`, `exp`, `iat`) are extractable
- RS256 and HS256 algorithm paths are both reachable

### 2. Add configuration support

**Metadata:**
- change_type: feature
- execution_mode: automated
- domain: java
- module: cui-authentication
- depends: 1

**Profiles:**
- implementation

**Affected files:**
- `src/main/java/de/cuioss/auth/jwt/JwtConfiguration.java`
- `src/main/resources/application.properties`

**Change per file:** `JwtConfiguration.java` — new `@ConfigurationProperties`-bound class with fields `issuer`, `audience`, and `clockSkewSeconds`; `application.properties` — document the three keys `auth.jwt.issuer`, `auth.jwt.audience`, `auth.jwt.clock-skew` with example values.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-maven:maven run --targets compile`
- Criteria: Compiles without error

**Success Criteria:**
- All three configuration keys are bound and accessible at runtime
- `JwtValidationService` uses `JwtConfiguration` for issuer, audience, and clock-skew checks

### 3. Implement unit tests

**Metadata:**
- change_type: feature
- execution_mode: automated
- domain: java
- module: cui-authentication
- depends: 2

**Profiles:**
- implementation
- module_testing

**Affected files:**
- `src/test/java/de/cuioss/auth/jwt/JwtValidationServiceTest.java`

**Change per file:** New test class covering: valid token acceptance, expired token rejection, invalid signature rejection, missing required claims, and clock-skew tolerance boundary cases. Uses `io.jsonwebtoken:jjwt-impl` to build test tokens inline.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-maven:maven run --targets test`
- Criteria: All tests pass with no failures

**Success Criteria:**
- All five test scenarios pass
- Line coverage on `JwtValidationService` is ≥ 80 %
- No test relies on external network or real keys

### 4. Add JavaDoc documentation

**Metadata:**
- change_type: feature
- execution_mode: automated
- domain: java
- module: cui-authentication
- depends: 3

**Profiles:**
- implementation

**Affected files:**
- `src/main/java/de/cuioss/auth/jwt/JwtValidationService.java`
- `src/main/java/de/cuioss/auth/jwt/JwtConfiguration.java`

**Change per file:** Add class-level Javadoc with a usage example to both classes; document every public method with `@param`, `@return`, and `@throws`; document each configuration field in `JwtConfiguration` with its key name and valid value range.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-maven:maven run --targets verify`
- Criteria: Full verify including Javadoc linting passes without warnings

**Success Criteria:**
- All public API elements have complete Javadoc
- `mvn javadoc:javadoc` produces no warnings for the `de.cuioss.auth.jwt` package

## Approach

1. Start with interface definition
2. Implement core validation logic
3. Add configuration binding
4. Write tests in parallel (TDD where practical)
5. Document as we go

## Dependencies

- `io.jsonwebtoken:jjwt-api:0.12.3`
- `io.jsonwebtoken:jjwt-impl:0.12.3` (runtime)
- `io.jsonwebtoken:jjwt-jackson:0.12.3` (runtime)

## Risks and Mitigations

- **Risk**: Key rotation complexity
  - **Mitigation**: Use KeyProvider abstraction, defer rotation to later iteration
