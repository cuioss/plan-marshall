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

Analyze the race condition.

**Affected class**: `de.cuioss.auth.session.SessionStore`

**Problem**:
- Thread A checks `isExpired()` → false
- Timeout thread marks session expired
- Timeout thread starts cleanup
- Thread A accesses session → NullPointerException

### 2. Implement atomic session state check

Add synchronized access to session state.

**Changes to** `SessionStore.java`:
- Add `ReentrantReadWriteLock` for session map
- Make `getSession()` and `invalidate()` atomic
- Use read lock for access, write lock for invalidation

### 3. Add grace period for cleanup

Delay physical removal after logical invalidation.

**Changes**:
- Mark session as `INVALIDATED` (logical)
- Return null for invalidated sessions
- Remove from map after grace period (physical)

### 4. Write regression test

Create test that reproduces the race condition.

**Test class**: `SessionStoreRaceConditionTest.java`

**Test approach**:
- Multiple threads accessing session
- Concurrent timeout trigger
- Verify no NPE, consistent behavior

### 5. Verify fix in integration test

End-to-end test with realistic load.

**Test**: `SessionTimeoutIntegrationTest.java`

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
