---
name: pm-dev-frontend-ext-triage-js
description: Triage extension for JavaScript findings during plan-finalize phase
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# JavaScript Triage Extension

Provides decision-making knowledge for triaging JavaScript findings during the finalize phase.

## Purpose

This skill is a **triage extension** loaded by the plan-finalize workflow skill when processing JavaScript-related findings. It provides domain-specific knowledge for deciding whether to fix, suppress, or accept findings.

**Key Principle**: This skill provides **knowledge**, not workflow control. The finalize skill owns the process.

## When This Skill is Loaded

Loaded via `resolve-workflow-skill-extension --domain javascript --type triage` during finalize phase when:

1. ESLint reports rule violations
2. Jest test failures occur
3. Prettier formatting issues are detected
4. Stylelint reports CSS issues
5. PR review comment disposition is required (FIX, REPLY-AND-RESOLVE, or ESCALATE on bot review threads)
6. The JavaScript arch-gate (dependency-cruiser) emits `arch-constraint` findings for structural-boundary violations

## Standards

| Document | Purpose |
|----------|---------|
| [suppression.md](standards/suppression.md) | JavaScript suppression syntax (eslint-disable) |
| [severity.md](standards/severity.md) | JavaScript-specific severity guidelines and decision criteria |
| [pr-comment-disposition.md](standards/pr-comment-disposition.md) | PR review comment disposition (FIX / REPLY-AND-RESOLVE / ESCALATE) for JavaScript and CSS |

## Quick Reference

### Suppression Methods

| Finding Type | Syntax |
|--------------|--------|
| ESLint rule | `// eslint-disable-next-line rule-name` |
| ESLint block | `/* eslint-disable rule-name */` |
| Prettier | Not suppressible (fix or configure) |
| Stylelint | `/* stylelint-disable rule-name */` |

### Decision Guidelines

| Severity | Default Action |
|----------|----------------|
| error | **Fix** (blocks build/CI) |
| warn | Fix or suppress with justification |
| off | N/A (disabled rule) |

### Acceptable to Accept

- Generated code in `**/generated/**`, `**/dist/**`
- Legacy JavaScript files with tracked plan to address
- Test mocks requiring flexibility

### arch-constraint Findings (dependency-cruiser arch-gate)

The JavaScript arch-gate runs dependency-cruiser's module-graph rules as a dedicated invocation and emits one `arch-constraint`-typed finding per structural-boundary violation (a module-boundary rule, a forbidden-dependency rule, an orphan/circular-dependency rule), carrying the violated rule's identity in the finding's `rule` field. These findings route here for the per-finding disposition exactly as `lint-issue` / `sonar-issue` findings do:

| Disposition | When |
|-------------|------|
| **Fix** | The violation is a genuine structural-boundary breach — correct the import, break the cycle, or remove the forbidden cross-module dependency. This is the default for an `arch-constraint` finding. |
| **Suppress** | The rule does not apply to this specific case and the exception is documented — narrow the dependency-cruiser rule (e.g. a scoped `pathNot`/`comment`) with justification. |
| **Accept** | The rule itself is wrong or a known false positive — the finding is acknowledged without code change; recurring acceptances signal the rule needs revision. |

A violation of the **same rule** that recurs across runs reinforces a single `arch-constraint` lesson (rule-identity dedup; retire-on-quiet / reinforce-on-recurrence), surfaced to planning through the architecture-hints pipe. The structural model and the full findings → triage → lesson loop are owned by the central standard — see [`arch-gate-fitness-functions.md`](../../../plan-marshall/skills/manage-architecture/standards/arch-gate-fitness-functions.md) and the JavaScript binding in [`pm-dev-frontend:arch-gate-js`](../arch-gate-js/SKILL.md).

## Related Documents


- `pm-dev-frontend:javascript` - Core JavaScript patterns
