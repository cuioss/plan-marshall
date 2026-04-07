# Extension Point: Triage

> **Type**: Workflow Skill Extension | **Hook Method**: `provides_triage()` | **Implementations**: 7 | **Status**: Active

## Overview

Triage extensions declare domain-specific finding decision-making knowledge: suppression syntax, severity guidelines, and acceptable-to-accept criteria. When verification produces findings (build warnings, test failures, Sonar issues), the triage skill for the relevant domain is loaded to decide the appropriate action for each finding.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `domain` | str | Yes | Domain key (e.g., `java`, `python`, `documentation`) |
| `finding` | dict | Yes | Finding dict with `file`, `line`, `message`, `severity`, `source` |

## Pre-Conditions

- Domain is registered in `marshal.json` under `skill_domains.{domain_key}`
- Triage skill exists and is loadable via `resolve-workflow-skill-extension --domain {domain} --type triage`
- Findings have been collected from verification (build, test, lint, Sonar)

## Post-Conditions

- Each finding gets a decision: **FIX**, **SUPPRESS**, or **ACCEPT** with rationale
- Suppressions include syntax-correct annotation/comment for the domain
- Decisions are logged to `decision.log`

## Lifecycle

```
1. Run verification (build, test, lint, Sonar)
2. Collect findings
3. For each finding:
   a. Determine domain from file path/extension
   b. resolve-workflow-skill-extension --domain {domain} --type triage
   c. If extension exists: load skill, apply severity/suppression rules
   d. If no extension: use default severity mapping
   e. Decide: fix | suppress | accept
4. Apply fixes/suppressions -> re-run verification if changes made
```

## Python API

```python
def provides_triage(self) -> str | None:
    """Return triage skill reference as 'bundle:skill', or None.

    Default: None
    """
```

## Return Structure

Returns a skill reference string (`bundle:skill`) or `None`.

| Value | Meaning |
|-------|---------|
| `"pm-dev-java:ext-triage-java"` | Domain has a triage skill |
| `None` | No triage skill; use default severity mapping |

## Required Skill Sections

The referenced triage skill MUST include these sections in its `SKILL.md`:

| Section | Purpose | Content |
|---------|---------|---------|
| `## Suppression Syntax` | How to suppress findings | Annotation/comment syntax per finding type |
| `## Severity Guidelines` | When to fix vs suppress vs accept | Decision table by severity |
| `## Acceptable to Accept` | What can be accepted without fixing | Situations where accepting is appropriate |

## Storage in marshal.json

```json
{
  "skill_domains": {
    "java": {
      "bundle": "pm-dev-java",
      "workflow_skill_extensions": {
        "triage": "pm-dev-java:ext-triage-java"
      }
    }
  }
}
```

**Path**: `skill_domains.{domain_key}.workflow_skill_extensions.triage`

## Resolution Commands

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-workflow-skill-extension --domain {domain} --type triage
```

## Implementation Pattern

```python
class Extension(ExtensionBase):
    def provides_triage(self) -> str | None:
        return "pm-dev-java:ext-triage-java"
```

## Implementor Frontmatter

All triage implementor skills must include in their SKILL.md frontmatter:

```yaml
implements: plan-marshall:extension-api/standards/ext-point-triage
```

## Current Implementations

| Bundle | Skill | Domain |
|--------|-------|--------|
| pm-dev-java | ext-triage-java | java |
| pm-dev-frontend | ext-triage-js | javascript |
| pm-dev-python | ext-triage-python | python |
| pm-dev-oci | ext-triage-oci | oci-containers |
| pm-documents | ext-triage-docs | documentation |
| pm-requirements | ext-triage-reqs | requirements |
| pm-plugin-development | ext-triage-plugin | plan-marshall-plugin-dev |
