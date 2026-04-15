---
name: plugin-apply-lessons-learned
description: Apply accumulated lessons learned to component documentation
user-invocable: true
---

# Apply Lessons Learned Skill

Read lessons learned via `manage-lessons` skill and apply them to component documentation.

**Lesson lifecycle**: Unapplied lessons live as files in `.plan/local/lessons-learned/`. Once a lesson is applied, it is moved into a plan directory (the plan that consumes it carries the `lesson-{id}.md` file along when archived). Therefore, "unapplied lessons" is simply "the set of files currently in `.plan/local/lessons-learned/`".

## Usage

```
# Apply lessons to specific component
/plugin-apply-lessons-learned command=maven-build-and-fix
/plugin-apply-lessons-learned agent=maven-builder
/plugin-apply-lessons-learned skill=builder-maven-rules

# Apply all unapplied lessons across components
/plugin-apply-lessons-learned --all

# List unapplied lessons (dry-run)
/plugin-apply-lessons-learned --list

# Show usage
/plugin-apply-lessons-learned
```

## WORKFLOW

### Step 1: Parse Parameters

- Extract component type and name, or flags (--all, --list)
- Validate parameter syntax

### Step 2: Load Lessons Learned Skill

```
Skill: plan-marshall:manage-lessons
```

### Step 3: List Unapplied Lessons

Unapplied lessons are the files currently in `.plan/local/lessons-learned/`. List them via the manage-lessons script:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list [--component-name {name}]
```

- For specific component: Add `--component-name {name}`
- For --all: List everything returned (all files in `.plan/local/lessons-learned/`)
- For --list: Display results without applying

### Step 4: For Each Unapplied Lesson

a. **Locate component source**:
   - Commands: `marketplace/bundles/{bundle}/commands/{name}.md`
   - Agents: `marketplace/bundles/{bundle}/agents/{name}.md`
   - Skills: `marketplace/bundles/{bundle}/skills/{name}/SKILL.md`

b. **Analyze lesson category**:
   - `bug`: Add to CRITICAL RULES or error handling section
   - `improvement`: Add to workflow or suggest enhancement
   - `pattern`: Add to best practices or examples
   - `anti-pattern`: Add to warnings or "do not" section

c. **Determine appropriate placement**:
   - Read component documentation
   - Find relevant section for lesson category
   - Prepare edit that integrates lesson naturally

d. **Apply lesson**:
   - Edit component documentation
   - Integrate lesson content (not raw JSON, but natural prose)
   - Maintain document structure and formatting

e. **Mark lesson applied**:
   - The lesson is considered applied once the originating plan archives. Within this skill, no `applied` flag exists — applying the lesson here means editing the target component documentation. The lesson file remains in `.plan/local/lessons-learned/` until a plan picks it up and carries it through archive.

### Step 5: Report Results

- Number of lessons applied per component
- Any lessons that couldn't be applied (with reason)
- Components updated

## PARAMETERS

**Component targeting** (mutually exclusive with flags):
- `command={name}` - Apply lessons for specific command
- `agent={name}` - Apply lessons for specific agent
- `skill={name}` - Apply lessons for specific skill

**Flags**:
- `--all` - Apply all unapplied lessons across all components
- `--list` - List unapplied lessons without applying (dry-run)

**Error Handling**:
- No parameters → Display usage
- Component not found → Error with suggestion
- No lessons file → Report "no lessons recorded"
- No unapplied lessons → Report "nothing to apply"

## LESSON APPLICATION RULES

### Bug Lessons

Add to component's error handling or critical rules section:

```markdown
## CRITICAL RULES

- **Paths with spaces**: Quote all paths in Bash calls to handle spaces correctly
```

### Improvement Lessons

Add as enhancement notes or workflow refinements:

```markdown
### Step 3: Process Files

**Enhancement**: Add progress indicator every 50 files for large batches.
```

### Pattern Lessons

Add to examples or best practices:

```markdown
## Best Practices

- Validate all inputs in Step 1 before processing to catch errors early
```

### Anti-Pattern Lessons

Add to warnings or "avoid" sections:

```markdown
## CRITICAL RULES

**Avoid:**
- Do NOT modify files during glob iteration - collect list first, then process
```

## OUTPUT FORMAT

```
## Applied Lessons

### command/maven-build-and-fix
- [2025-11-25-001] bug: Paths with spaces → Added to CRITICAL RULES
- [2025-11-25-002] improvement: Progress indicator → Added enhancement note

### agent/maven-builder
- [2025-11-24-001] pattern: Verify phase → Added to best practices

## Summary
- Components updated: 2
- Lessons applied: 3
- Lessons skipped: 0
```

## Dependencies

**Cross-bundle dependency**: This skill relies on `plan-marshall:manage-lessons` for lesson storage, retrieval, and the `query-lessons.py` script used in Step 3. The manage-lessons skill must be available and its script registered in the executor.

```
Skill: plan-marshall:manage-lessons
```

## Related

- `/plugin-maintain` - General component maintenance
- `/plugin-doctor` - Diagnose component issues
