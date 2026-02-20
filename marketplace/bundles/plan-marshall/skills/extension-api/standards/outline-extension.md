# Outline Extension Contract

Extension hook for declaring a domain-specific outline skill with change-type routing.

## Purpose

Provides a hook for extensions to declare an outline skill — a skill that provides domain-specific instructions for solution outline creation, routed by change type. This enables:

- Domain-specific discovery, analysis, and deliverable creation logic
- Change-type routing within a single skill (via `standards/change-{type}.md` files)
- Fallback to generic outline standards when no domain skill is configured

---

## Lifecycle Position

The hook is invoked by `marshall-steward` during domain configuration:

```
1. Extension discovery and loading
2. get_skill_domains() → domain metadata
3. ➤ provides_outline_skill() → outline skill reference per domain
4. Stored in marshal.json under skill_domains.{domain}.outline_skill
5. Resolved at runtime by phase-3-outline via outline-change-type skill
```

**Timing**: Called during `/marshall-steward` domain configuration (`skill-domains configure`). The returned skill reference is persisted in `marshal.json` and resolved at runtime during the outline phase.

---

## Method Signature

```python
def provides_outline_skill(self) -> str | None:
    """Return the domain-specific outline skill reference, or None.

    Returns:
        Skill reference as 'bundle:skill' (e.g.,
        'pm-plugin-development:ext-outline-workflow') or None.

        The skill's standards/change-{type}.md files contain
        domain-specific discovery, analysis, and deliverable
        creation logic. The change_type is passed to the skill
        for internal routing.

    Purpose:
        Loaded by the outline-change-type skill (via
        solution-outline-agent). Provides domain-specific outline
        instructions instead of generic pm-workflow:outline-change-type
        standards.

    Fallback:
        If a domain returns None, generic instructions from
        pm-workflow:outline-change-type/standards/change-{type}.md
        are used.
    """
    return None
```

---

## Skill Structure Convention

The referenced skill must provide `standards/change-{type}.md` files for supported change types:

```
{bundle}/skills/{skill}/
├── SKILL.md                       # Shared workflow steps and verification
└── standards/
    ├── change-feature.md          # Create new components
    ├── change-enhancement.md      # Improve existing components
    ├── change-bug_fix.md          # Fix component bugs
    └── change-tech_debt.md        # Refactor/cleanup components
```

Not all change types need coverage — unsupported types fall back to the generic `pm-workflow:outline-change-type/standards/change-{type}.md`.

### Change Types

| Change Type | Description |
|-------------|-------------|
| `feature` | New functionality or component |
| `enhancement` | Improve existing functionality |
| `bug_fix` | Fix a defect or issue |
| `tech_debt` | Refactoring, cleanup, removal |
| `analysis` | Investigate, research, understand |
| `verification` | Validate, check, confirm |

---

## Fallback Behavior

When `provides_outline_skill()` returns `None` (the default), the outline-change-type skill uses generic standards:

```
pm-workflow:outline-change-type/standards/change-{type}.md
```

This is the behavior for most domains. Only domains with highly specialized outline needs (e.g., marketplace plugin development with inventory agents) should provide a custom skill.

---

## Storage in marshal.json

The outline skill reference is stored directly on the domain object (not inside `workflow_skill_extensions`):

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

**Note**: `outline_skill` is stored at the domain level, while `triage` is nested under `workflow_skill_extensions`. This reflects the different resolution paths.

---

## Resolution Command

Runtime resolution of the outline skill for a domain:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  resolve-outline-skill --domain plan-marshall-plugin-dev
```

**Output (domain-specific)**:
```toon
status	success
domain	plan-marshall-plugin-dev
skill	pm-plugin-development:ext-outline-workflow
source	domain_specific
```

**Output (generic fallback)**:
```toon
status	success
domain	java
skill	pm-workflow:outline-change-type
source	generic_fallback
```

---

## Existing Implementations

| Bundle | Domain | Outline Skill |
|--------|--------|--------------|
| pm-plugin-development | plan-marshall-plugin-dev | `pm-plugin-development:ext-outline-workflow` |

All other domains return `None` and use the generic `pm-workflow:outline-change-type` standards.

---

## Design Rationale

### Why Optional?

Most domains work well with generic outline standards. Only domains with unique discovery needs (sub-agents, specialized inventory) benefit from a custom outline skill.

### Why Change-Type Routing?

A single skill with `change-{type}.md` sub-files allows:

1. **Shared context** — the SKILL.md contains shared workflow steps
2. **Type-specific logic** — each change type has its own instructions
3. **Selective coverage** — only implement types that need customization

---

## Related Specifications

- [extension-contract.md](extension-contract.md) — Extension API contract
- [extension-mechanism.md (workflow)](../../../../pm-workflow/skills/workflow-extension-api/standards/extensions/extension-mechanism.md) — Extension mechanism overview, change-type skill structure, resolution flow
- [change-types.md](../../../../pm-workflow/skills/workflow-architecture/standards/change-types.md) — Change type vocabulary
