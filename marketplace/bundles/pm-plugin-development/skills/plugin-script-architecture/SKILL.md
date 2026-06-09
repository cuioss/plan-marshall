---
name: plugin-script-architecture
description: Script development standards covering implementation patterns, testing, and output contracts
user-invocable: false
---

# Plugin Script Architecture Skill

## What This Skill Provides

- **Python Implementation**: Stdlib-only patterns, argparse, error handling
- **Testing Standards**: pytest infrastructure, test organization, fixtures
- **Output Contract**: TOON format, exit codes, error patterns

For script execution patterns, see: `plan-marshall:tools-script-executor`

## When to Activate

Activate when:
- Creating new scripts for skills
- Implementing test suites for scripts
- Reviewing script code quality

## Standards

### 1. Python Implementation
Load: `standards/python-implementation.md`

### 2. Testing Standards
Load: `standards/testing-standards.md`

### 3. Test Scaffolding Patterns
Load: `standards/test-scaffolding.md`

Contains: Canonical `# ruff: noqa: I001, E402` + `sys.path.insert(0, ...)` prologue for tests that import underscore-prefixed sibling modules from `marketplace/bundles/.../scripts/`. Citation: `test/plan-marshall/plan-marshall/test_phase_handshake.py` lines 2 and 20-29.

### 4. Output Contract
Load: `standards/output-contract.md`

### 5. Cross-Skill Integration
Load: `standards/cross-skill-integration.md`

**CRITICAL**: Scripts run via the executor must follow cross-skill integration patterns for imports, logging, and error handling.

### 6. Script Invocation in Documentation
See: `standards/cross-skill-integration.md` § "Script invocation in documentation"

The explicit-call-or-xref authoring rule for documented script invocations plus the `## Canonical invocations` section contract. Every documented `python3 .plan/execute-script.py {notation} …` call must be the exact-correct inline call or an xref to the owning skill's Canonical-invocations section, and every script-bearing skill publishes that section. Enforced at edit time by the `manage-invocation-invalid` and `missing-canonical-block` plugin-doctor rules.

### 7. New get/set Input Shape Validator
See: `standards/cross-skill-integration.md` § "New get/set input shape must pass its own validator"

A `get`/`set` verb whose value proposition IS a new input shape (a dotted path, glob, or compound key) must have that exact shape as its first boundary test, driven through the CLI entry point — the input validator is the part most likely to lag the feature and silently reject the shape the verb exists to support. The config-governance companion lives in [`plan-marshall:manage-config`](../../../plan-marshall/skills/manage-config/standards/config-design-principles.md) § "Config Design Principles".

## References

- `references/notation-spec.md` - Full notation specification
- `references/stdlib-modules.md` - Allowed Python standard library modules

## Related Skills

- `plan-marshall:tools-script-executor` - Script execution, notation resolution, plan-marshall command
- `pm-dev-python:python-best-practices` - General Python patterns (type hints, docstrings, async, data structures). This skill covers marketplace-specific script constraints (stdlib-only, executor integration, TOON output); for broader Python development standards, load that skill instead
