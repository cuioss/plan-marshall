---
name: pm-dev-java-ext-triage-java
description: Triage extension for Java findings during plan-finalize phase
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# Java Triage Extension

Provides decision-making knowledge for triaging Java-related findings during the finalize phase.

## Purpose

This skill is a **triage extension** loaded by the plan-finalize workflow skill when processing Java-related findings. It provides domain-specific knowledge for deciding whether to fix, suppress, or accept findings.

**Key Principle**: This skill provides **knowledge**, not workflow control. The finalize skill owns the process.

## When This Skill is Loaded

Loaded via `resolve-workflow-skill-extension --domain java --type triage` during finalize phase when:

1. Build/test verification produces findings
2. Sonar analysis reports issues
3. PR review comments reference Java code
4. Lint/format checks fail
5. PR review comment disposition is required (FIX, REPLY-AND-RESOLVE, or ESCALATE on bot review threads)
6. The Java arch-gate (ArchUnit) emits `arch-constraint` findings for structural-boundary violations

## Standards

| Document | Purpose |
|----------|---------|
| [suppression.md](standards/suppression.md) | Java suppression syntax (@SuppressWarnings, NOSONAR) |
| [severity.md](standards/severity.md) | Java-specific severity guidelines and decision criteria |
| [pr-comment-disposition.md](standards/pr-comment-disposition.md) | PR review comment disposition (FIX / REPLY-AND-RESOLVE / ESCALATE) for Java |

## Extension Registration

Registered in marshal.json under the java domain:

```json
"java": {
  "workflow_skill_extensions": {
    "triage": "pm-dev-java:ext-triage-java"
  }
}
```

## Quick Reference

### Suppression Methods

| Finding Type | Syntax |
|--------------|--------|
| Sonar rule | `@SuppressWarnings("java:S1234")` |
| Deprecation | `@SuppressWarnings("deprecation")` |
| Unchecked cast | `@SuppressWarnings("unchecked")` |
| Null warning | `@SuppressWarnings("null")` or JSpecify annotations |
| All warnings | `// NOSONAR` (line comment, use sparingly) |

### Decision Guidelines

| Severity | Default Action |
|----------|----------------|
| BLOCKER | **Fix** (mandatory) |
| CRITICAL | **Fix** (mandatory for vulnerabilities) |
| MAJOR | Fix or suppress with justification |
| MINOR | Fix, suppress, or accept |
| INFO | Accept (low priority) |

### Acceptable to Accept

- Generated code in `**/generated/**`
- Test data builders with intentionally permissive patterns
- Legacy code with documented migration plan
- Framework-mandated patterns (e.g., Serializable)
- Documented false positives

### arch-constraint Findings (ArchUnit arch-gate)

The Java arch-gate runs the `@ArchTest` rules as a dedicated ArchUnit-only invocation and emits one `arch-constraint`-typed finding per structural-boundary violation (a layering rule, a directional import contract, a module-boundary constraint), carrying the violated rule's identity in the finding's `rule` field. These findings route here for the per-finding disposition exactly as `lint-issue` / `sonar-issue` findings do:

| Disposition | When |
|-------------|------|
| **Fix** | The violation is a genuine structural-boundary breach — correct the dependency direction, move the offending type, or remove the forbidden import. This is the default for an `arch-constraint` finding. |
| **Suppress** | The rule does not apply to this specific case and the exception is documented — narrow the ArchUnit rule (e.g. `.ignoreDependency(...)`) or annotate the architecturally-sanctioned exception, with justification. |
| **Accept** | The rule itself is wrong or a known false positive — the finding is acknowledged without code change; recurring acceptances signal the rule needs revision. |

A violation of the **same rule** that recurs across runs reinforces a single `arch-constraint` lesson (rule-identity dedup; retire-on-quiet / reinforce-on-recurrence), surfaced to planning through the architecture-hints pipe. The structural model and the full findings → triage → lesson loop are owned by the central standard — see [`arch-gate-fitness-functions.md`](../../../plan-marshall/skills/manage-architecture/standards/arch-gate-fitness-functions.md) and the Java binding in [`pm-dev-java:arch-gate-java`](../arch-gate-java/SKILL.md).

## Related Documents


- `pm-dev-java:java-core` - Core Java patterns
