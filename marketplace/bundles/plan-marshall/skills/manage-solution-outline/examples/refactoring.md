# Solution: Refactor Authentication Module

plan_id: refactor-auth-module
created: 2025-12-10T10:00:00Z
compatibility: deprecation — Add deprecation markers to old code, provide migration path

## Summary

Refactor the monolithic AuthenticationService into smaller, focused components following single responsibility principle. Extract token handling, session management, and user lookup into separate services.

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Authentication Module Refactoring                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  BEFORE                              AFTER                                   │
│  ══════                              ═════                                   │
│                                                                              │
│  ┌─────────────────────┐            ┌─────────────────────┐                │
│  │ AuthenticationSvc   │            │ AuthenticationSvc   │                │
│  │ (monolith)          │            │ (orchestrator)      │                │
│  │                     │            │                     │                │
│  │ • generateToken()   │            │ • authenticate()    │                │
│  │ • validateToken()   │    ───▶    │ • logout()          │                │
│  │ • refreshToken()    │            │                     │                │
│  │ • createSession()   │            └──────────┬──────────┘                │
│  │ • invalidateSession │                       │                            │
│  │ • findByUsername()  │         ┌─────────────┼─────────────┐             │
│  │ • findById()        │         │             │             │             │
│  └─────────────────────┘         ▼             ▼             ▼             │
│                           ┌───────────┐ ┌───────────┐ ┌───────────┐        │
│                           │TokenSvc   │ │SessionMgr │ │UserLookup │        │
│                           │           │ │           │ │Svc        │        │
│                           │• generate │ │• create   │ │• findBy   │        │
│                           │• validate │ │• invalidate│ │  Username│        │
│                           │• refresh  │ │• get      │ │• findById │        │
│                           │• revoke   │ │• timeout  │ │• cache    │        │
│                           └───────────┘ └───────────┘ └───────────┘        │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Package structure:                                                          │
│  de.cuioss.auth/                                                            │
│  ├── AuthenticationService.java  (refactored - orchestrator)                │
│  ├── token/TokenService.java     (new)                                      │
│  ├── session/SessionManager.java (new)                                      │
│  └── user/UserLookupService.java (new)                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Deliverables

### 1. Extract TokenService

**Metadata:**
- change_type: tech_debt
- execution_mode: automated
- domain: java
- module: cui-authentication
- depends: none

**Profiles:**
- implementation

**Affected files:**
- `src/main/java/de/cuioss/auth/AuthenticationService.java`
- `src/main/java/de/cuioss/auth/token/TokenService.java`

**Change per file:** `TokenService.java` — new class in `de.cuioss.auth.token` receiving `generateToken()`, `validateToken()`, `refreshToken()`, and `revokeToken()` moved verbatim from `AuthenticationService`; `AuthenticationService.java` — replace moved method bodies with CDI-injected `TokenService` delegation calls.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-maven:maven run --targets compile`
- Criteria: Compiles without error

**Success Criteria:**
- `TokenService` contains all four token methods
- `AuthenticationService` delegates to `TokenService` with no duplicated logic

### 2. Extract SessionManager

**Metadata:**
- change_type: tech_debt
- execution_mode: automated
- domain: java
- module: cui-authentication
- depends: 1

**Profiles:**
- implementation

**Affected files:**
- `src/main/java/de/cuioss/auth/AuthenticationService.java`
- `src/main/java/de/cuioss/auth/session/SessionManager.java`

**Change per file:** `SessionManager.java` — new class in `de.cuioss.auth.session` receiving `createSession()`, `invalidateSession()`, `getSession()`, and session timeout handling; `AuthenticationService.java` — inject `SessionManager` via CDI and delegate the four session methods.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-maven:maven run --targets compile`
- Criteria: Compiles without error

**Success Criteria:**
- Session lifecycle is fully owned by `SessionManager`
- `AuthenticationService` no longer contains session state

### 3. Extract UserLookupService

**Metadata:**
- change_type: tech_debt
- execution_mode: automated
- domain: java
- module: cui-authentication
- depends: 2

**Profiles:**
- implementation

**Affected files:**
- `src/main/java/de/cuioss/auth/AuthenticationService.java`
- `src/main/java/de/cuioss/auth/user/UserLookupService.java`

**Change per file:** `UserLookupService.java` — new class in `de.cuioss.auth.user` receiving `findByUsername()`, `findById()`, and user caching logic; `AuthenticationService.java` — inject `UserLookupService` via CDI and delegate user resolution calls.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-maven:maven run --targets compile`
- Criteria: Compiles without error

**Success Criteria:**
- All user resolution and caching logic lives in `UserLookupService`
- No user-lookup code remains in `AuthenticationService`

### 4. Update AuthenticationService

**Metadata:**
- change_type: tech_debt
- execution_mode: automated
- domain: java
- module: cui-authentication
- depends: 3

**Profiles:**
- implementation

**Affected files:**
- `src/main/java/de/cuioss/auth/AuthenticationService.java`

**Change per file:** Retain only `authenticate()` and `logout()` orchestration logic; all three extracted services are injected via `@Inject`; remove any residual duplicated logic; add `@ApplicationScoped` CDI scope annotation if not already present.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-maven:maven run --targets compile`
- Criteria: Compiles without error

**Success Criteria:**
- `AuthenticationService` contains only orchestration logic
- All three services are injected and used exclusively via delegation

### 5. Migrate tests

**Metadata:**
- change_type: tech_debt
- execution_mode: automated
- domain: java
- module: cui-authentication
- depends: 4

**Profiles:**
- implementation
- module_testing

**Affected files:**
- `src/test/java/de/cuioss/auth/token/TokenServiceTest.java`
- `src/test/java/de/cuioss/auth/session/SessionManagerTest.java`
- `src/test/java/de/cuioss/auth/user/UserLookupServiceTest.java`
- `src/test/java/de/cuioss/auth/AuthenticationServiceTest.java`

**Change per file:** `TokenServiceTest.java`, `SessionManagerTest.java`, `UserLookupServiceTest.java` — new test classes exercising each extracted service in isolation; `AuthenticationServiceTest.java` — replace direct logic tests with mock-injected delegation tests using Mockito or Weld.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-maven:maven run --targets test`
- Criteria: All tests pass with no failures

**Success Criteria:**
- Each extracted service has dedicated test coverage
- `AuthenticationServiceTest` mocks the three injected services
- No behaviour change detected (characterisation tests pass)

### 6. Update documentation

**Metadata:**
- change_type: tech_debt
- execution_mode: manual
- domain: java
- module: cui-authentication
- depends: 5

**Profiles:**
- implementation

**Affected files:**
- `docs/architecture/authentication-module.adoc`
- `README.md`

**Change per file:** `authentication-module.adoc` — update the package diagram and class-relationship section to reflect the new four-class structure (orchestrator + three extracted services); `README.md` — revise the authentication module overview paragraph to describe the new design.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-maven:maven run --targets verify`
- Criteria: Full verify passes

**Success Criteria:**
- Package diagram matches the implemented structure
- No references to the old monolithic `AuthenticationService` design remain in documentation

## Approach

1. Create new classes with interfaces
2. Move code method by method
3. Update tests incrementally
4. Verify no behavior change (characterization tests)
5. Clean up AuthenticationService

## Dependencies

None - internal refactoring only.

## Risks and Mitigations

- **Risk**: Breaking existing behavior
  - **Mitigation**: Characterization tests before refactoring
- **Risk**: Circular dependencies
  - **Mitigation**: Clear dependency direction, interface segregation
