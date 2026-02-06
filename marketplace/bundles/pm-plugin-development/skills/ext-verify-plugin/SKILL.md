---
name: ext-verify-plugin
description: Verification command knowledge for plugin development outline agents
user-invocable: false
allowed-tools: Read
---

# Plugin Development Verification Knowledge

Provides verification command knowledge for outline agents when creating deliverable verification sections.

## Purpose

This skill centralizes correct plugin-doctor syntax and bundle verification commands. It is loaded directly by the 4 pm-plugin-development outline agents via frontmatter.

**Key Principle**: This skill provides **knowledge**, not workflow control. Outline agents own the process.

## When This Skill is Loaded

Loaded by plugin development outline agents (`change-{type}-outline-agent`) during deliverable creation:

1. Component deliverables need plugin-doctor commands
2. Test deliverables need module-test commands
3. Bundle-level deliverables need full verification commands

## Standards

| Document | Purpose |
|----------|---------|
| [component-verification.md](standards/component-verification.md) | Plugin-doctor invocation per component type |
| [bundle-verification.md](standards/bundle-verification.md) | Bundle-level test and quality commands |

## Quick Reference

### Component Verification Commands

| Component Type | Plugin-Doctor Command |
|----------------|----------------------|
| Skills | `/pm-plugin-development:plugin-doctor scope=skills skill-name={name}` |
| Agents | `/pm-plugin-development:plugin-doctor scope=agents agent-name={name}` |
| Commands | `/pm-plugin-development:plugin-doctor scope=commands command-name={name}` |
| Scripts | `/pm-plugin-development:plugin-doctor scope=scripts script-name={name}` |

### Test and Bundle Verification Commands

| Purpose | Command |
|---------|---------|
| Run module tests | `./pw module-tests {bundle}` |
| Full bundle verification | `./pw verify {bundle}` |

### Decision Guidelines

| Deliverable Type | Verification Pattern |
|------------------|---------------------|
| New/modified component | Plugin-doctor for specific component type |
| New/modified tests | `./pw module-tests {bundle}` |
| Multi-component changes | `./pw verify {bundle}` for final deliverable |
| Plugin.json registration | Plugin-doctor for the registered component |

## Related Documents

- [pm-plugin-development:plugin-architecture](../plugin-architecture/SKILL.md) - Plugin patterns
- [pm-plugin-development:plugin-doctor](../plugin-doctor/SKILL.md) - Plugin-doctor skill
