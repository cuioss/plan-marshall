# Architecture Rules

Core architectural principles for marketplace components following goal-based organization.

## Rule 1: Skills Must Be Self-Contained

All skills must contain ALL content within their own directory structure using the relative paths pattern.

**Rationale**: Skills may be distributed independently, installed globally, or bundled. External dependencies break portability and marketplace distribution.

**Requirements**:
- All content in skill directory (references/, scripts/, assets/)
- All resource paths use relative paths pattern
- No references escaping skill directory (`../../../`)
- No absolute paths (`~/git/plan-marshall/`)
- External references only via URLs or `Skill:` invocations

**Examples**:

✅ CORRECT (relative path pattern):
```markdown
Read references/java-core-patterns.md
bash scripts/analyzer.py {input_file}
Load template: assets/template.html
Skill: cui-java-unit-testing
```

❌ INCORRECT (hardcoded paths):
```markdown
Read: ../../../../standards/java/java-core.adoc
Read: ~/git/plan-marshall/standards/logging.adoc
bash ./scripts/analyzer.py  # Unnecessary ./ prefix
```

**Relative Path Benefits**:
- Portable across installation contexts (global, project, bundle)
- Works when skill distributed independently
- No machine-specific or user-specific paths
- Clear resource references

**Impact of Violation**:
- Skill cannot be distributed independently
- Breaks when skill installed outside plan-marshall repo
- Fails in global skill installation
- Breaks marketplace distribution

## Rule 2: Components Must Use Skills

Commands and workflows requiring standards must invoke Skills via the Skill tool, not read files directly.

**Rationale**: Skills provide curated, versioned standards with conditional loading logic. Direct file access bypasses skill workflow, breaks abstraction layer, and couples components to file structure.

**Requirements**:
- Include `Skill` in allowed-tools list (if using skills)
- Invoke `Skill: cui-skill-name` in workflow
- No direct `Read:` of standards files from main repo
- Let skill handle conditional loading and standards selection

**Examples**:

✅ CORRECT (skill invocation):
```yaml
---
name: code-reviewer
allowed-tools: [Read, Edit, Write, Skill]
---

Step 1: Activate Required Standards
Skill: cui-java-core
Skill: cui-javadoc

Step 2: Review Code
Apply standards loaded from skills
```

❌ INCORRECT (direct file access):
```markdown
Step 1: Load Standards
Read: ~/git/plan-marshall/standards/java-core.adoc
Read: ~/git/plan-marshall/standards/javadoc.adoc
```

**Impact of Violation**:
- Bypasses skill conditional loading logic
- Hard-codes file paths in component
- Breaks when standards reorganized
- Loses skill versioning benefits

## Rule 3: Reference Categorization

Only specific reference types allowed in skills and commands.

**Allowed References**:

### 1. Internal Resources (skills only)
**Format**:
```markdown
Read references/file.md
bash scripts/analyzer.py
Load: assets/template.html
```

**Rules**:
- Must use relative paths pattern
- File must exist in skill directory
- No `../` sequences
- Path separator is forward slash `/`

**Examples**:
```markdown
✅ Read references/quality-standards.md
✅ bash scripts/validate.sh {input}
✅ Load template: assets/report-template.json
```

### 2. External URLs (all components)
**Format**:
```markdown
* Description: https://external-site.com/path
```

**Rules**:
- Must start with `https://` or `http://`
- Must be publicly accessible
- Typically in ## References section
- Not loaded via `Read:` statement

**Examples**:
```markdown
✅ * Java Spec: https://docs.oracle.com/javase/specs/
✅ * Maven Guide: https://maven.apache.org/guides/
✅ * Quarkus Guide: https://quarkus.io/guides/cdi
```

### 3. Skill Dependencies (all components)
**Format**:
```markdown
Skill: cui-skill-name
```

**Rules**:
- Must use `Skill:` prefix
- Must reference valid skill name
- Skill must exist (marketplace, bundle, or global)

**Examples**:
```markdown
✅ Skill: cui-java-core
✅ Skill: cui-java-unit-testing
✅ Skill: cui-javadoc
```

**Prohibited References**:

❌ **Escape sequences**:
```markdown
Read: ../../../../standards/java/java-core.adoc
```
- Breaks portability
- Assumes specific directory structure

❌ **Absolute paths**:
```markdown
Read: ~/git/plan-marshall/standards/java-core.adoc
```
- Machine-specific
- User-specific
- Not portable

❌ **Improper Path Reference**:
```markdown
bash ./scripts/analyzer.py  # Should use scripts/analyzer.py
```
- Unnecessary ./ prefix, just use relative path directly

## Rule 4: Progressive Disclosure

Skills must implement progressive disclosure to minimize context usage.

**Rationale**: Loading all content upfront wastes context and slows skill selection. Progressive disclosure loads only what's needed when needed.

**Requirements**:
- Minimal frontmatter (~2-3 lines: name, description)
- SKILL.md focuses on workflow guidance (~400-800 lines)
- References loaded on-demand when workflow reaches specific step
- Never load all references upfront

**Three-Level Loading**:

**Level 1: Frontmatter** (discovery)
```yaml
---
name: my-skill
description: Brief summary for skill selection
---
```

**Level 2: SKILL.md** (workflow)
```markdown
## Step 1: Analyze Code

For detailed quality standards, load reference:
Read references/quality-standards.md

# Only loads when Step 1 executes
```

**Level 3: References** (details on-demand)
- Loaded only when workflow reaches specific step
- Can be thousands of lines
- Multiple references per skill

**Examples**:

✅ CORRECT (progressive loading):
```markdown
## Step 1: Load Core Principles

Read references/core-principles.md

## Step 2: Apply Specific Pattern

If using Pattern 1:
  Read references/pattern-1-details.md

# Each reference loads only when needed
```

❌ INCORRECT (eager loading):
```yaml
---
name: my-skill
description: |
  Detailed description with embedded standards...
  [5000 lines of content in frontmatter]
---
```

**Benefits**:
- 60-80% reduction in context usage
- Faster skill selection
- Allows very large knowledge bases
- Claude only sees what's relevant to current step

## Rule 5: Goal-Based Organization

Components must be organized by user goals, not technical component types.

**Rationale**: Users think in terms of goals (CREATE, DIAGNOSE, FIX) not component types (agent, command, skill). Goal-based organization aligns with user mental models.

**User Goals**:
- **CREATE** - Create new marketplace components
- **DIAGNOSE** - Find and understand issues
- **FIX** - Fix identified issues
- **MAINTAIN** - Keep marketplace healthy
- **LEARN** - Understand architecture and patterns

**Requirements**:
- Skills organized by capability, not component type
- Commands organized by goal, not operation
- Workflows within skills handle different scenarios
- Composition over duplication

**Examples**:

✅ CORRECT (goal-based):
```
plugin-create/           # CREATE goal
  ├── SKILL.md
  └── workflows:
      - create-agent
      - create-command
      - create-skill
      - create-bundle

plugin-diagnose/         # DIAGNOSE goal
  ├── SKILL.md
  └── workflows:
      - analyze-component
      - analyze-all-of-type
      - validate-marketplace

commands/
  ├── create.md          # Routes to plugin-create skill
  ├── diagnose.md        # Routes to plugin-diagnose skill
  └── fix.md             # Routes to plugin-fix skill
```

❌ INCORRECT (component-centric):
```
commands/
  ├── plugin-create-agent.md        # Component-specific
  ├── plugin-create-command.md      # Component-specific
  ├── plugin-diagnose-agents.md     # Component-specific
  └── plugin-diagnose-commands.md   # Component-specific
```

**Benefits**:
- Aligns with user mental models
- Reduces number of components (consolidation)
- Enables workflow composition
- Simpler discovery
- Better reusability

## Enforcement

These rules are enforced through:
- **Creation Time**: `/plugin-create` command ensures compliance for new components
- **Validation & Fix**: `/plugin-doctor` command detects and fixes violations in existing components

All diagnostic and creation workflows reference this skill to apply consistent architecture rules.

## Summary

**Core Principles**:
1. Self-containment with relative path pattern
2. Skill invocation over direct file access
3. Proper reference categorization
4. Progressive disclosure for context efficiency
5. Goal-based organization for user alignment

**These rules apply to**:
- Skills (knowledge layer)
- Commands (orchestration layer)
- All marketplace components

**Why These Rules Matter**:
- **Portability**: Components work across installation contexts
- **Maintainability**: Clear boundaries and responsibilities
- **Efficiency**: Minimize context usage
- **Usability**: Align with user mental models
- **Quality**: Consistent architecture across marketplace
