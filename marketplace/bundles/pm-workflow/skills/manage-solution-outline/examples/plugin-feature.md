# Solution: Create Build Caching Skill

plan_id: build-caching-skill
created: 2025-12-10T10:00:00Z

## Summary

Add a build caching skill to the builder bundle that caches build outputs and restores them when inputs haven't changed, reducing build times for unchanged modules.

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Build Cache Integration                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                        ┌──────────────────────┐                             │
│                        │  builder-maven-rules │                             │
│                        │                      │                             │
│                        │  mvn compile         │                             │
│                        └──────────┬───────────┘                             │
│                                   │                                          │
│              ┌────────────────────┼────────────────────┐                    │
│              │                    │                    │                    │
│              ▼                    ▼                    ▼                    │
│     ┌────────────────┐   ┌────────────────┐   ┌────────────────┐          │
│     │  PRE-BUILD     │   │    BUILD       │   │  POST-BUILD    │          │
│     │                │   │                │   │                │          │
│     │ cache restore  │   │ (if no hit)    │   │ cache store    │          │
│     │ ──────────────▶│   │                │──▶│                │          │
│     │ check key      │   │ actual build   │   │ save outputs   │          │
│     └───────┬────────┘   └────────────────┘   └───────┬────────┘          │
│             │                                         │                    │
│             │         ┌──────────────────┐            │                    │
│             └────────▶│   build-cache    │◀───────────┘                    │
│                       │                  │                                  │
│                       │ • key (hash)     │                                  │
│                       │ • store          │                                  │
│                       │ • restore        │                                  │
│                       │ • clean          │                                  │
│                       └────────┬─────────┘                                  │
│                                │                                            │
│                                ▼                                            │
│                       ┌──────────────────┐                                  │
│                       │  .cache/builds/  │                                  │
│                       │                  │                                  │
│                       │  {key}.tar.gz    │                                  │
│                       └──────────────────┘                                  │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Cache Key = hash(pom.xml + src/** + tool version + env vars)               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Deliverables

### 1. Create cache-management script

Python script for cache key generation and storage.

**Location**: `marketplace/bundles/pm-dev-builder/skills/build-cache/scripts/manage-cache.py`

**Commands**:
- `key` - Generate cache key from inputs (pom.xml, src/**)
- `store` - Store build output in cache
- `restore` - Restore from cache if key matches
- `clean` - Remove old cache entries

### 2. Create SKILL.md definition

Define the skill interface and workflows.

**Location**: `marketplace/bundles/pm-dev-builder/skills/build-cache/SKILL.md`

**Workflows**:
- Pre-build: Check cache, restore if hit
- Post-build: Store outputs if build succeeded
- Maintenance: Clean old entries

### 3. Add cache key generation logic

Implement robust cache key algorithm.

**Key inputs**:
- Hash of pom.xml / build.gradle / package.json
- Hash of source files (src/**)
- Build tool version
- Relevant environment variables

### 4. Integrate with builder-maven-rules

Add cache hooks to Maven build workflow.

**Changes to**: `marketplace/bundles/pm-dev-builder/skills/builder-maven-rules/SKILL.md`

**Integration points**:
- Before `mvn compile`: check cache
- After successful build: store cache

### 5. Add tests

**Test file**: `test/builder/build-cache/test_manage_cache.py`

**Test scenarios**:
- Cache key stability (same inputs → same key)
- Cache key sensitivity (changed input → different key)
- Store/restore round-trip
- Cache expiration

## Approach

1. Design cache key algorithm
2. Implement script with TDD
3. Create skill definition
4. Integrate with Maven workflow
5. Test end-to-end

## Dependencies

- Python `hashlib` (stdlib)
- Optional: compression for cache storage

## Risks and Mitigations

- **Risk**: Cache invalidation bugs (stale builds)
  - **Mitigation**: Conservative key inputs, include tool versions
- **Risk**: Disk space usage
  - **Mitigation**: Automatic cleanup of old entries
