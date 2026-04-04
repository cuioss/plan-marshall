# Solution: Fix Session Timeout Race Condition

plan_id: fix-session-timeout-race
created: 2025-12-10T10:00:00Z
compatibility: breaking — Clean-slate approach, no deprecation nor transitionary comments

## Summary

Fix a race condition where concurrent requests can access a session after timeout has been triggered but before cleanup completes, causing intermittent authentication failures.

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Race Condition Analysis                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PROBLEM: Race between request thread and timeout thread                     │
│  ═══════                                                                     │
│                                                                              │
│  Thread A (request)          SessionStore           Timeout Thread           │
│  ──────────────────          ────────────           ──────────────           │
│        │                          │                       │                  │
│        │  isExpired()?            │                       │                  │
│        │─────────────────────────▶│                       │                  │
│        │◀─────────────────────────│ false                 │                  │
│        │                          │                       │                  │
│        │                          │◀──────────────────────│ markExpired()    │
│        │                          │                       │                  │
│        │                          │◀──────────────────────│ cleanup()        │
│        │                          │                       │ (removes map)    │
│        │  getSession()            │                       │                  │
│        │─────────────────────────▶│                       │                  │
│        │◀─────────────────────────│ NPE! (removed)        │                  │
│        │                          │                       │                  │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  SOLUTION: Atomic state check with grace period                              │
│  ════════                                                                    │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         SessionStore                                  │   │
│  │                                                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │   │
│  │  │ ReentrantReadWriteLock                                          │ │   │
│  │  │                                                                 │ │   │
│  │  │  getSession() ─────▶ readLock   ─────▶ check state ─────▶ return│ │   │
│  │  │                                                                 │ │   │
│  │  │  invalidate() ─────▶ writeLock  ─────▶ mark INVALIDATED        │ │   │
│  │  │                                        (logical delete)         │ │   │
│  │  │                                                                 │ │   │
│  │  │  cleanup()    ─────▶ writeLock  ─────▶ remove from map         │ │   │
│  │  │                      (after grace)     (physical delete)        │ │   │
│  │  └─────────────────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Session States: ACTIVE ──▶ INVALIDATED ──▶ (removed)                       │
│                             └── grace period ──┘                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Deliverables

### 1. Identify affected code paths

**Metadata:**
- change_type: analysis
- execution_mode: manual
- domain: java
- module: cui-authentication
- depends: none

**Profiles:**
- implementation

**Affected files:**
- `src/main/java/de/cuioss/auth/session/SessionStore.java`

**Change per file:** Read and annotate the race window — identify the exact lines where `isExpired()` returns false, where the timeout thread calls `markExpired()` and `cleanup()`, and where `getSession()` dereferences the removed map entry.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-maven:maven run --targets compile`
- Criteria: Compiles without error (no code changes yet)

**Success Criteria:**
- Race window is documented with thread A / timeout thread sequence
- Affected lines in `SessionStore.java` are identified

### 2. Implement atomic session state check

**Metadata:**
- change_type: bug_fix
- execution_mode: automated
- domain: java
- module: cui-authentication
- depends: 1

**Profiles:**
- implementation

**Affected files:**
- `src/main/java/de/cuioss/auth/session/SessionStore.java`

**Change per file:** Add `ReentrantReadWriteLock` field; wrap `getSession()` with read lock and `invalidate()` with write lock; introduce `SessionState` enum (`ACTIVE`, `INVALIDATED`) for logical delete before physical removal.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-maven:maven run --targets compile`
- Criteria: Compiles without error

**Success Criteria:**
- `getSession()` and `invalidate()` are atomic under concurrent access
- Read lock is used for access, write lock for invalidation

### 3. Add grace period for cleanup

**Metadata:**
- change_type: bug_fix
- execution_mode: automated
- domain: java
- module: cui-authentication
- depends: 2

**Profiles:**
- implementation

**Affected files:**
- `src/main/java/de/cuioss/auth/session/SessionStore.java`

**Change per file:** Add a configurable grace period (default 5 s) between logical invalidation (`INVALIDATED` state) and physical map removal; `getSession()` returns `null` for `INVALIDATED` sessions without waiting for physical removal.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-maven:maven run --targets compile`
- Criteria: Compiles without error

**Success Criteria:**
- Sessions are logically deleted before physical removal
- Grace period is configurable and defaults to a safe value

### 4. Write regression test

**Metadata:**
- change_type: bug_fix
- execution_mode: automated
- domain: java
- module: cui-authentication
- depends: 3

**Profiles:**
- implementation
- module_testing

**Affected files:**
- `src/test/java/de/cuioss/auth/session/SessionStoreRaceConditionTest.java`

**Change per file:** New test class that spawns multiple reader threads concurrently with a timeout trigger thread; asserts that no `NullPointerException` is thrown and that all threads observe consistent session state.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-maven:maven run --targets test`
- Criteria: All tests pass, including the new race condition test

**Success Criteria:**
- Test reliably reproduces the race condition without the fix
- Test passes consistently with the fix applied
- No `NullPointerException` under concurrent load

### 5. Verify fix in integration test

**Metadata:**
- change_type: verification
- execution_mode: automated
- domain: java
- module: cui-authentication
- depends: 4

**Profiles:**
- implementation
- module_testing

**Affected files:**
- `src/test/java/de/cuioss/auth/session/SessionTimeoutIntegrationTest.java`

**Change per file:** New integration test that exercises `SessionStore` under realistic concurrent load with multiple sessions timing out; verifies no authentication failures occur during the grace period.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-maven:maven run --targets verify`
- Criteria: Full verify passes including integration tests

**Success Criteria:**
- Integration test passes without errors under concurrent load
- No regression in existing authentication behaviour

## Approach

1. Write failing test that reproduces issue
2. Implement fix
3. Verify test passes
4. Run full test suite
5. Load test to confirm no regression

## Dependencies

None.

## Risks and Mitigations

- **Risk**: Lock contention affecting performance
  - **Mitigation**: Use read-write lock, measure before/after
- **Risk**: Grace period too short/long
  - **Mitigation**: Make configurable, default to safe value
