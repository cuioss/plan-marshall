# Outline Extension Contract

Contract for domain-specific outline extensions loaded by `phase-2-outline`.

---

## Purpose

Outline extensions implement a **formal protocol** that phase-2-outline calls at defined points. They provide domain-specific knowledge for deliverable creation through explicit protocol sections.

**Key Principle**: Extensions are skills with required protocol sections. The phase explicitly calls each section at defined points - no "apply naturally" ambiguity.

---

## Scope Boundaries

**Extensions provide DELIVERABLE-CREATION knowledge only:**
- Assessment criteria (simple vs complex workflow selection)
- Workflow routing (which sub-workflow to load)
- File discovery patterns (Glob/Grep for finding affected files)
- Verification command templates

**Extensions do NOT provide:**
- Component structure rules → Domain reference skills (loaded during execute phase)
- Architecture patterns → Domain reference skills (loaded during execute phase)
- Implementation standards → Domain reference skills (loaded during execute phase)
- Frontmatter requirements → Domain reference skills (loaded during execute phase)

This separation is intentional: outline extensions know HOW TO CREATE DELIVERABLES, while reference skills (like `plugin-architecture`) know HOW TO IMPLEMENT components.

---

## Extension Registration

Domains register outline extensions via `provides_outline()` in their `extension.py`:

```python
class Extension(ExtensionBase):
    def provides_outline(self) -> str | None:
        return "pm-dev-java:ext-outline-java"  # or None if no extension
```

---

## Resolution

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  resolve-workflow-skill-extension --domain java --type outline
```

Returns:
```toon
status: success
domain: java
type: outline
extension: pm-dev-java:ext-outline-java
```

---

## Required Protocol Sections

Every outline extension MUST implement these sections:

| Section | Called By | Purpose | Required |
|---------|-----------|---------|----------|
| `## Assessment Protocol` | Step 3 | Criteria for simple vs complex | **Yes** |
| `## Simple Workflow` | Step 4 (if simple) | Reference to path-single-workflow.md | **Yes** |
| `## Complex Workflow` | Step 4 (if complex) | Reference to path-multi-workflow.md | **Yes** |
| `## Discovery Patterns` | Both workflows | Domain-specific Glob/Grep patterns | **Yes** |
| `## Domain Detection` | Step 2.5 | When this domain is relevant | No |

---

## Section: Domain Detection

**Called by**: phase-2-outline Step 2.5
**Purpose**: Determine if this domain is relevant to the current request.

**Required content**: List of conditions when this extension is relevant.

**Default behavior**: Domain is assumed relevant if configured in plan's config.toon.

---

## Section: Assessment Protocol

**Called by**: phase-2-outline Step 3
**Purpose**: Determine which workflow applies (simple vs complex)

**Required subsections**:
- `### Load Reference Data` - Load standards/reference-tables.md
- `### Workflow Selection Criteria` - Table of indicators → simple/complex
- `### Conditional Standards` - Table of conditions → additional standards to layer

---

## Section: Simple Workflow

**Called by**: phase-2-outline Step 4 (when assessment = simple)
**Purpose**: Create deliverables for isolated changes

**Required subsections**:
- `### Load Workflow` - `Read standards/path-single-workflow.md`
- `### Domain-Specific Patterns` - Grouping strategy, change type mappings, file paths, verification commands

---

## Section: Complex Workflow

**Called by**: phase-2-outline Step 4 (when assessment = complex)
**Purpose**: Create deliverables for cross-cutting changes with file enumeration

**Required subsections**:
- `### Load Workflow` - `Read standards/path-multi-workflow.md`
- `### Domain-Specific Patterns` - Grouping strategy, inventory script, batch analysis

---

## Section: Discovery Patterns

**Called by**: Both workflows during file enumeration
**Purpose**: Provide domain-specific Glob/Grep patterns for finding affected files

**Required subsections**:
- `### Grep Patterns` - Table of change type → discovery command
- `### Glob Patterns` - Table of component type → glob pattern

---

## Enforcement Requirements

Extensions implementing this protocol MUST follow these rules:

### Per-Component Analysis

When inventory returns components of a type (agents, commands, skills), the extension:
1. MUST analyze each component individually against request criteria
2. MUST NOT make blanket assumptions about component types
3. MUST log individual `[FINDING]` entries for each component (affected or not)

### Prohibited Patterns

Extensions MUST NOT:
- Exclude entire component types with a single decision (e.g., "skills don't have outputs")
- Use categorical statements as exclusion rationale
- Skip analysis steps for any component returned by inventory

**Anti-pattern (PROHIBITED):**
```
[FINDING] Skills analysis complete: Skills are knowledge documents without output formats
```

**Required pattern:**
```
[FINDING] Affected: bundle/skills/skill-a/SKILL.md
  detail: Contains output specification matching request criteria

[FINDING] Not affected: bundle/skills/skill-b/SKILL.md
  detail: No matching criteria found after checking sections X, Y, Z
```

### Batch Checkpoint Requirements

If inventory includes multiple component types (e.g., agents, commands, skills), ALL types must show batch progress logs:
```
[STATUS] Analyzed agents batch 1 of pm-workflow: 3 affected, 2 not affected
[STATUS] Analyzed commands batch 1 of pm-workflow: 0 affected, 5 not affected
[STATUS] Analyzed skills batch 1 of pm-workflow: 2 affected, 8 not affected
```

---

## Example Implementation

See: `pm-plugin-development:ext-outline-plugin`

This extension demonstrates the protocol pattern with:
- Assessment Protocol with complexity criteria
- Simple/Complex workflow routing to path-single/path-multi
- Discovery Patterns for marketplace components
- Conditional loading of script-verification.md

---

## Related Documents

- [extension-mechanism.md](extension-mechanism.md) - How extensions work
- [triage-extension.md](triage-extension.md) - Triage extension contract
- [phase-2-outline SKILL.md](../../../phase-2-outline/SKILL.md) - Phase that loads this extension
