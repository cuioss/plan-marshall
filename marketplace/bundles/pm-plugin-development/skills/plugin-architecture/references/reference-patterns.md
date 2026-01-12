# Reference Patterns

Classification of allowed vs prohibited reference types in marketplace components, using relative paths for portability.

## The Relative Path Pattern

**Critical Principle**: All resource paths in skills use relative paths from the skill directory for portability across installation contexts.

**Why Relative Paths**:
- Skills installed in different locations (global, project, bundle)
- Claude resolves relative paths from the skill's installation directory
- Makes skills portable and distributable

**Installation Contexts**:
- Global: `~/.claude/skills/my-skill/`
- Project: `.claude/skills/my-skill/`
- Bundle: `marketplace/bundles/{bundle}/skills/my-skill/`

## Pattern 1: Internal References (references/)

**Purpose**: Documentation and knowledge loaded on-demand.

**Format**:
```markdown
Read references/filename.md
Read references/subdirectory/filename.md
```

**Rules**:
- Use relative path from skill directory
- Must be relative path within references/ directory
- File must exist in skill's references/ directory
- No `../` sequences allowed
- Path separator is forward slash `/`

**Examples**:
```markdown
✅ Read references/quality-standards.md
✅ Read references/testing/junit-patterns.md
✅ Read references/cdi/cdi-aspects.md
✅ Read references/examples/good-example.md
```

**Prohibited**:
```markdown
❌ Read: ../../../../other-skill/file.md       # Escape sequences
❌ Read: ~/git/plan-marshall/standards/file.md # Absolute path
```

**Validation**:
```bash
# Extract all Read: statements
grep "Read references/" skill/SKILL.md

# Verify each file exists
for file in $(extracted_paths); do
  test -f "skill/${file}" || echo "MISSING: $file"
done
```

## Pattern 2: Script Execution (via execute-script.py)

**Purpose**: Executable automation scripts (Python, Bash) for deterministic logic.

**Format**:
```markdown
python3 .plan/execute-script.py {bundle}:{skill}:{subcommand} {args}
```

**Rules**:
- Use the executor pattern with bundle:skill:subcommand notation
- Scripts must exist in skill's scripts/ directory
- Subcommand maps to script entry point

**Examples**:
```markdown
✅ python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:analyze {input_file}
✅ python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:validate {component_path}
✅ python3 .plan/execute-script.py pm-workflow:manage-files:manage-files add --plan-id {id} --file {file}
```

**Prohibited**:
```markdown
❌ python ~/project/scripts/analyzer.py        # Absolute path
❌ python3 scripts/analyzer.py                 # Direct script path (bypasses executor)
```

**Script Output**:
- Scripts should output structured data (JSON) for Claude to interpret
- Scripts should return exit code 0 for success, non-zero for failure
- Output to stdout, errors to stderr

## Pattern 3: Asset Templates (assets/)

**Purpose**: Templates and binary files used as input to scripts or for generation.

**Format**:
```markdown
Load template: assets/template-name.ext
Read assets/config-example.json
```

**Rules**:
- Use relative path from skill directory
- Assets must exist in skill's assets/ directory
- Typically used with "Load template:" or similar context
- Can be any file type (templates, configs, images)

**Examples**:
```markdown
✅ Load template: assets/template.html
✅ Read assets/config-example.json
✅ Use template: assets/templates/basic.txt
✅ Load image: assets/diagram.png
```

**Prohibited**:
```markdown
❌ Use: ~/git/project/assets/template.html    # Absolute path
❌ Load: ../other-skill/assets/template.html  # Cross-skill access
```

## Pattern 4: External URLs

**Purpose**: Link to authoritative specifications and official documentation.

**Format**:
```markdown
* Description: https://external-site.com/path
* Description: http://external-site.com/path
```

**Rules**:
- Must start with `https://` or `http://`
- Must be publicly accessible
- Typically in ## References section
- Not loaded via `Read:` statement
- Used for supplemental documentation

**Examples**:
```markdown
✅ * Java Spec: https://docs.oracle.com/javase/specs/
✅ * Maven Guide: https://maven.apache.org/guides/
✅ * CDI Spec: https://jakarta.ee/specifications/cdi/
✅ * Quarkus Guide: https://quarkus.io/guides/cdi
✅ * Claude Skills Deep Dive: https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/
```

**Purpose**:
- Link to authoritative specifications
- Reference official documentation
- Point to framework guides
- Provide supplemental reading

## Pattern 5: Skill Dependencies

**Purpose**: Invoke other skills for their knowledge and capabilities.

**Format**:
```markdown
Skill: cui-skill-name
Skill: bundle-name:skill-name  # For bundled skills
```

**Rules**:
- Must use `Skill:` prefix
- Must reference valid skill name
- Skill must exist (marketplace, bundle, or global)
- Used in workflows to load standards

**Examples**:
```markdown
✅ Skill: cui-java-core
✅ Skill: cui-java-unit-testing
✅ Skill: cui-javadoc
✅ Skill: plan-marshall:diagnostic-patterns
✅ Skill: pm-plugin-development:plugin-architecture
```

**Usage Contexts**:

In skill workflows:
```markdown
## Step 1: Load Prerequisites

Skill: cui-java-core
Skill: cui-javadoc

## Step 2: Apply Standards

Apply standards loaded from skills in Step 1
```

In command workflows:
```markdown
## Step 1: Load Architecture Principles

Skill: pm-plugin-development:plugin-architecture

## Step 2: Create Component

Follow architecture rules from loaded skill
```

**Prohibited**:
```markdown
❌ Read ../other-skill/SKILL.md     # Direct file access
❌ bash ../other-skill/scripts/*.sh # Cross-skill script
```

## Prohibited Patterns

### ❌ Escape Sequences
**Problem**: Breaks portability, assumes specific directory structure.

```markdown
❌ Read: ../../../../standards/java/java-core.adoc
❌ bash ../../scripts/analyzer.sh
❌ * Guide: ../../../standards/requirements/guide.adoc
```

**Why Wrong**:
- Assumes specific directory depth
- Breaks when skill installed elsewhere
- Fails in distribution

**Fix**: Use appropriate pattern (Skill: for other skills, relative paths for own resources).

### ❌ Absolute Paths
**Problem**: Machine-specific, user-specific, not portable.

```markdown
❌ Read: ~/git/plan-marshall/standards/java-core.adoc
❌ bash /Users/oliver/scripts/analyzer.sh
❌ Source: /opt/project/standards/logging.adoc
```

**Why Wrong**:
- User-specific home directory
- Machine-specific file system
- Not portable across installations

**Fix**: Use relative paths or Skill: invocation.

### ❌ Cross-Skill File Access
**Problem**: Breaks skill encapsulation, couples skills together.

```markdown
❌ Read ../cui-other-skill/references/file.md
❌ bash ../other-skill/scripts/script.sh
```

**Why Wrong**:
- Bypasses skill interface
- Couples implementations
- Breaks when other skill reorganized
- Not validated by skill system

**Fix**: Use `Skill: other-skill` to invoke skill properly.

## Portability Testing

### Test in Different Contexts

**1. Global Installation**:
```bash
cp -r my-skill ~/.claude/skills/
# Test that relative paths resolve from ~/.claude/skills/my-skill/
```

**2. Project Installation**:
```bash
cp -r my-skill .claude/skills/
# Test that relative paths resolve from .claude/skills/my-skill/
```

**3. Bundle Installation**:
```bash
# Skill already in bundle
# Test that relative paths resolve from marketplace/bundles/{bundle}/skills/my-skill/
```

### Validation Checklist

- [ ] All `Read:` statements use relative paths
- [ ] All script executions use relative paths
- [ ] All asset references use relative paths
- [ ] No `../` escape sequences found
- [ ] No absolute paths found
- [ ] No hardcoded paths found
- [ ] Skill works when installed globally
- [ ] Skill works when installed in project
- [ ] Skill works when bundled

### Automated Validation

```bash
# Check for prohibited patterns
grep -r "Read: \.\." skill/              # Escape sequences
grep -r "bash \.\." skill/               # Escape sequences
grep -r "Read: ~" skill/                 # Absolute paths
grep -r "Read: /" skill/ | grep -v http # Absolute paths (exclude URLs)
```

## Reference Summary

**Pattern 1**: `Read references/file.md` - On-demand documentation
**Pattern 2**: `bash scripts/script.sh` - Executable automation
**Pattern 3**: `Load assets/template.html` - Templates and binaries
**Pattern 4**: `* URL: https://example.com` - External documentation
**Pattern 5**: `Skill: skill-name` - Other skill invocation

**Key Principle**: Always use relative paths for all internal resources to ensure portability.

## Examples

### Complete Skill with All Patterns

```markdown
---
name: example-skill
description: Example using all reference patterns
allowed-tools: [Read, Bash, Skill]
---

# Example Skill

## Step 1: Load Prerequisites

Skill: plan-marshall:general-development-rules  # Pattern 5

## Step 2: Load Reference Documentation

Read references/core-principles.md        # Pattern 1
Read references/examples/example-1.md     # Pattern 1

## Step 3: Execute Analysis Script

bash scripts/analyzer.sh {input_file}     # Pattern 2

## Step 4: Generate Output

Load template: assets/report-template.md  # Pattern 3
Fill template with analysis results
Write output to {output_file}

## References

* Official Spec: https://example.com/spec           # Pattern 4
* Framework Guide: https://example.com/guide         # Pattern 4
```

## Related References

- Core Principles: references/core-principles.md
- Architecture Rules: references/architecture-rules.md
- Skill Design: references/skill-design.md
