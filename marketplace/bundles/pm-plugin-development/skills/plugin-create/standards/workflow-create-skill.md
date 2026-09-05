# Workflow: create-skill

**Parameters**:
- `scope` - Where to create (marketplace/global/project, default: marketplace)
- `bundle` - Target bundle (optional, will prompt if not provided)

**Steps**:

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes `component` — a `manage-*`-scoped convention leaves exactly those calls with no rule at all, which is the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The middle clause is what the `ci` family makes load-bearing: a `ci` verb reports failure as `status: error` at exit 0 **by design**, so a caller must branch on the payload `status` and never on the exit code. That rule is stated authoritatively in `plan-marshall:tools-integration-ci`; it is not restated here.

Step-level exceptions — calls whose non-zero exit is itself the signal — are documented inline in the step that issues them.

## Step 1: Load Foundation Skills

```text
Skill: pm-plugin-development:plugin-architecture
Skill: plan-marshall:persona-plan-marshall-agent
```

These provide architecture principles and non-prompting tool usage patterns.

## Step 2: Load Skill Standards

```text
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

```text
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

Same pattern: prefer `architecture files --module {bundle}` for module-scoped enumeration of registered components; fall back to Glob/Grep for sub-component discovery and content-level name/description matching.

## Step 5: Create Skill Structure

**Create directories:**
```text
bash mkdir -p {bundle}/skills/{skill-name}/standards
```

**Generate SKILL.md:**

Generate frontmatter:
```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-create:component generate --type "skill" --config "{answers_json}"
```

Load template:
```text
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
```text
Write: {bundle}/skills/{skill-name}/SKILL.md
```

**Generate README.md:**

Create skill overview README with:
- Skill overview
- Standards list
- Usage examples
- Integration notes

Write README:
```text
Write: {bundle}/skills/{skill-name}/README.md
```

**Create placeholder standards files:**

For each standards file user specified:
```text
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

```text
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

```text
SlashCommand: /pm-plugin-development:plugin-doctor skills skill-name={skill-name}
```
