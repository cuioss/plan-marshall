# Workflow: create-skill

**Parameters**:
- `scope` - Where to create (marketplace/global/project, default: marketplace)
- `bundle` - Target bundle (optional, will prompt if not provided)

**Steps**:

## Step 1: Load Foundation Skills

```
Skill: pm-plugin-development:plugin-architecture
Skill: plan-marshall:dev-general-practices
```

These provide architecture principles and non-prompting tool usage patterns.

## Step 2: Load Skill Standards

```
Read references/skill-guide.md
```

This provides skill patterns, resource organization, and progressive disclosure guidance.

## Step 3: Interactive Questionnaire

Ask user for:

**A. Skill name** (kebab-case, descriptive)
- Example: `java-unit-testing-patterns`
- Validation: Must match kebab-case pattern

**B. Bundle selection** (same as agent workflow)

**C. Short description** (1 sentence, <100 chars)

**D. Detailed description** (2-3 sentences, what standards/knowledge skill provides)
- Validation: Must be at least 100 chars
- Error if too short: "Detailed description must be at least 100 characters: {current_length}/100" and retry

**E. Skill type** — Present using `AskUserQuestion`:

```
AskUserQuestion:
  questions:
    - question: "What type of skill is this?"
      header: "Type"
      options:
        - label: "Standards skill"
          description: "Provides coding/process standards"
        - label: "Reference skill"
          description: "Provides reference material"
        - label: "Diagnostic skill"
          description: "Provides diagnostic patterns/tools"
      multiSelect: false
```

**F. Standards categories** (if standards skill)
- What domains does this cover? (e.g., Java, Testing, Documentation)

**G. Target audience**
- Who uses these standards? (developers, documentation writers, etc.)

**H. Standards files** (what standards files will be included)
- Prompt user to list main standards documents
- Suggest organization structure based on categories

Track `questions_answered` counter.

## Step 4: Duplication Detection

Same pattern, using Glob/Grep to find similar skills.

## Step 5: Create Skill Structure

**Create directories:**
```
bash mkdir -p {bundle}/skills/{skill-name}/standards
```

**Generate SKILL.md:**

Generate frontmatter:
```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-create:component generate --type "skill" --config "{answers_json}"
```

Load template:
```
Read assets/templates/skill-template.md
```

Fill template with:
- Generated frontmatter
- Overview
- What This Skill Provides
- When to Activate
- Workflow (how to use standards)
- Standards Organization (list of standards files)
- Tool Access requirements

Write SKILL.md:
```
Write: {bundle}/skills/{skill-name}/SKILL.md
```

**Generate README.md:**

Create skill overview README with:
- Skill overview
- Standards list
- Usage examples
- Integration notes

Write README:
```
Write: {bundle}/skills/{skill-name}/README.md
```

**Create placeholder standards files:**

For each standards file user specified:
```
Write: {bundle}/skills/{skill-name}/standards/{file-name}.md
```

With placeholder content:
```markdown
# {Title}

[Content to be added]

## Overview

## Standards

## References
```

Track `files_created` and `standards_files_created` counters.

## Step 6: Validate Generated Component

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-create:component validate --file "{skill_path}/SKILL.md" --type "skill"
```

Validation checks:
- Frontmatter format correct
- SKILL.md structure valid
- No CONTINUOUS IMPROVEMENT RULE (skills don't have this)

## Step 7: Display Summary

```
╔════════════════════════════════════════════════════════════╗
║          Skill Created Successfully                        ║
╚════════════════════════════════════════════════════════════╝

Skill: {skill-name}
Location: {file-path}
Bundle: {bundle-name}
Type: {skill-type}

Statistics:
- Questions answered: {questions_answered}
- Validations performed: {validations_performed}
- Duplication checks: {duplication_checks}
- Files created: {files_created}
- Standards files created: {standards_files_created}

Next steps:
1. Review skill file: {file-path}
2. Populate standards files in standards/ directory
3. Run diagnosis: /plugin-doctor skills skill-name={skill-name}
4. Test skill activation
```

## Step 8: Run Skill Diagnosis

```
SlashCommand: /pm-plugin-development:plugin-doctor skills skill-name={skill-name}
```
