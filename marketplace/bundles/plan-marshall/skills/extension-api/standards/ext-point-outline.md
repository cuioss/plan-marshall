# Extension Point: Outline

> **Type**: Workflow Skill Extension | **Hook Method**: `provides_outline_skill()` | **Implementations**: 1 | **Status**: Active

## Overview

Outline extensions declare domain-specific outline skills with change-type routing for solution outline creation. The skill provides `standards/change-types.md` (or individual `standards/change-{type}.md` files) with domain-specific discovery, analysis, and deliverable logic. When no domain outline skill exists, the generic `plan-marshall:phase-3-outline` standards are used as fallback.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | str | Yes | Plan identifier |
| `change_type` | enum | Yes | One of: `feature`, `enhancement`, `bug_fix`, `tech_debt`, `analysis`, `verification` |
| `domain` | str | Yes | Domain key from `skill_domains` |

## Pre-Conditions

- Plan initialized with `request.md`
- Change type detected by `detect-change-type-agent`
- Domain has a registered outline skill via `provides_outline_skill()`, or falls back to generic `plan-marshall:phase-3-outline` standards

## Post-Conditions

- `solution_outline.md` written with deliverables
- Each deliverable has scope, description, acceptance criteria, affected files, verification commands
- Assessments logged to `artifacts/assessments.jsonl`

## Lifecycle

```
1. phase-3-outline detects change type
2. resolve-outline-skill --domain {domain}
3. If domain_specific: load domain skill, read change-type instructions
4. If generic: read plan-marshall:phase-3-outline/standards/change-{type}.md
5. Execute discovery, analysis, deliverable creation
6. Write solution_outline.md
7. Q-Gate verification
```

## Python API

```python
def provides_outline_skill(self) -> str | None:
    """Return domain-specific outline skill reference as 'bundle:skill', or None.

    Fallback: If None, generic plan-marshall:phase-3-outline
    standards are used.

    Default: None
    """
```

## Return Structure

Returns a skill reference string (`bundle:skill`) or `None`.

| Value | Meaning |
|-------|---------|
| `"pm-plugin-development:ext-outline-workflow"` | Domain has a custom outline skill |
| `None` | Use generic `plan-marshall:phase-3-outline` standards |

## Skill Structure Convention

```
{bundle}/skills/{skill}/
├── SKILL.md                       # Shared workflow steps
└── standards/
    └── change-types.md            # All change types (bug_fix, enhancement, feature, tech_debt)
```

| Change Type | Description |
|-------------|-------------|
| `feature` | New functionality or component |
| `enhancement` | Improve existing functionality |
| `bug_fix` | Fix a defect or issue |
| `tech_debt` | Refactoring, cleanup, removal |
| `analysis` | Investigate, research, understand |
| `verification` | Validate, check, confirm |

Not all change types need coverage — unsupported types fall back to generic standards.

## Storage in marshal.json

```json
{
  "skill_domains": {
    "plan-marshall-plugin-dev": {
      "bundle": "pm-plugin-development",
      "outline_skill": "pm-plugin-development:ext-outline-workflow",
      "workflow_skill_extensions": {
        "triage": "pm-plugin-development:ext-triage-plugin"
      }
    }
  }
}
```

**Path**: `skill_domains.{domain_key}.outline_skill`

## Resolution Commands

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-outline-skill --domain {domain}
```

Returns `source: domain_specific` when a custom skill exists, or `source: generic_fallback` when using defaults.

## Implementation Pattern

```python
class Extension(ExtensionBase):
    def provides_outline_skill(self) -> str | None:
        return "pm-plugin-development:ext-outline-workflow"
```

## Implementor Frontmatter

All outline implementor skills must include in their SKILL.md frontmatter:

```yaml
implements: plan-marshall:extension-api/standards/ext-point-outline
```

## Current Implementations

| Bundle | Skill | Domain |
|--------|-------|--------|
| pm-plugin-development | ext-outline-workflow | plan-marshall-plugin-dev |

All other domains return `None` and use the generic `plan-marshall:phase-3-outline` standards.
