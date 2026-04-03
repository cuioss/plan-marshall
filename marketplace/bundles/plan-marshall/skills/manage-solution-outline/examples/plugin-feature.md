# Solution: Create Build Caching Skill

plan_id: build-caching-skill
created: 2025-12-10T10:00:00Z
compatibility: breaking — Clean-slate approach, no deprecation nor transitionary comments

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

Python script for cache key generation, storage, restore, and cleanup operations.

**Metadata:**
- change_type: feature
- execution_mode: automated
- domain: plan-marshall-plugin-dev
- module: build-cache
- depends: none

**Profiles:**
- implementation
- module_testing

**Affected files:**
- `marketplace/bundles/pm-dev-builder/skills/build-cache/scripts/manage-cache.py`
- `test/builder/build-cache/test_manage_cache.py`

**Change per file:** Create `manage-cache.py` with subcommands: `key` (generate cache key from pom.xml, src/**, tool version, env vars), `store` (archive build output under the key), `restore` (extract cached output if key matches), and `clean` (remove entries older than a configurable TTL). Create test file covering key stability, key sensitivity, store/restore round-trip, and expiration.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "module-tests builder"`
- Criteria: All tests pass

**Success Criteria:**
- Same inputs always produce the same cache key (stability)
- Changing any input (pom.xml, src file, tool version) produces a different key (sensitivity)
- Store followed by restore reconstructs the exact output directory contents
- Clean removes only entries older than the configured TTL

### 2. Create SKILL.md definition

Define the skill interface, workflows, and script notation for the build-cache skill.

**Metadata:**
- change_type: feature
- execution_mode: manual
- domain: plan-marshall-plugin-dev
- module: build-cache
- depends: 1

**Profiles:**
- implementation

**Affected files:**
- `marketplace/bundles/pm-dev-builder/skills/build-cache/SKILL.md`

**Change per file:** Create SKILL.md with frontmatter (name, description, user-invocable: false), workflow sections for pre-build cache check/restore, post-build cache store, and maintenance/clean, with explicit `python3 .plan/execute-script.py` invocations using the correct notation.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "quality-gate builder"`
- Criteria: Plugin doctor reports no violations for the new skill

**Success Criteria:**
- Frontmatter is valid and all required fields are present
- All three workflows (pre-build, post-build, maintenance) are documented
- Script notation uses the canonical `pm-dev-builder:build-cache:manage-cache` format

### 3. Register skill in plugin.json

Register the new build-cache skill in the bundle manifest.

**Metadata:**
- change_type: feature
- execution_mode: manual
- domain: plan-marshall-plugin-dev
- module: build-cache
- depends: 2

**Profiles:**
- implementation

**Affected files:**
- `marketplace/bundles/pm-dev-builder/.claude-plugin/plugin.json`

**Change per file:** Add the `build-cache` skill entry to the `skills` array in the plugin manifest. Skill is context-loaded (not user-invocable), so it must be registered for `Skill:` directive resolution.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "quality-gate builder"`
- Criteria: Marketplace inventory shows build-cache as a registered skill

**Success Criteria:**
- `plugin.json` parses as valid JSON
- `build-cache` appears in the skills list with correct name and path
- Plugin doctor reports no manifest violations

### 4. Integrate with builder-maven-rules

Add cache hooks to the Maven build workflow in the existing builder-maven-rules skill.

**Metadata:**
- change_type: enhancement
- execution_mode: manual
- domain: plan-marshall-plugin-dev
- module: builder-maven-rules
- depends: 2,3

**Profiles:**
- implementation

**Affected files:**
- `marketplace/bundles/pm-dev-builder/skills/builder-maven-rules/SKILL.md`

**Change per file:** Insert two cache integration points into the Maven workflow: before `mvn compile`, invoke `manage-cache restore` and skip the build step on cache hit; after a successful build, invoke `manage-cache store` to persist outputs.

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "quality-gate builder"`
- Criteria: Plugin doctor reports no violations for the modified skill

**Success Criteria:**
- Pre-build cache check step is documented before the compile invocation
- Post-build cache store step is documented after a successful build
- Workflow remains coherent — cache miss path falls through to the normal build

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
