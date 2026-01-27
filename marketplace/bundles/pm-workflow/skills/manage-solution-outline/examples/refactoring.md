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

Move token-related logic to dedicated service.

**New class**: `de.cuioss.auth.token.TokenService`

**Extract from** `AuthenticationService`:
- `generateToken()`
- `validateToken()`
- `refreshToken()`
- `revokeToken()`

**Keep in** `AuthenticationService`:
- Delegation calls to TokenService

### 2. Extract SessionManager

Separate session lifecycle management.

**New class**: `de.cuioss.auth.session.SessionManager`

**Extract**:
- `createSession()`
- `invalidateSession()`
- `getSession()`
- Session timeout handling

### 3. Extract UserLookupService

Isolate user resolution logic.

**New class**: `de.cuioss.auth.user.UserLookupService`

**Extract**:
- `findByUsername()`
- `findById()`
- User caching logic

### 4. Update AuthenticationService

Refactor to orchestrator role.

**Changes**:
- Inject new services via CDI
- Delegate to extracted services
- Keep only authentication orchestration

### 5. Migrate tests

Update test structure to match new classes.

**New test classes**:
- `TokenServiceTest.java`
- `SessionManagerTest.java`
- `UserLookupServiceTest.java`

**Update**: `AuthenticationServiceTest.java` - mock new dependencies

### 6. Update documentation

Revise architecture documentation.

**Update**:
- Package diagram
- Class relationships
- README.md

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
