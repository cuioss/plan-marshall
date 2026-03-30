# Workflow: create-bundle

**Parameters**:
- `scope` - Where to create (marketplace/global/project, default: marketplace)

**Steps**:

## Step 1: Load Foundation Skills

```
Skill: pm-plugin-development:plugin-architecture
Skill: plan-marshall:dev-general-practices
```

These provide architecture principles and non-prompting tool usage patterns.

## Step 2: Load Bundle Standards

```
Read references/bundle-guide.md
```

This provides bundle structure requirements, plugin.json configuration, naming conventions, and validation guidelines.

## Step 3: Interactive Questionnaire

Ask user for:

**A. Bundle name** (kebab-case)
- Example: `java-development-standards`
- Validation: Must match kebab-case pattern

**B. Display name** (human-readable)
- Example: "Java Development Standards"

**C. Description** (one sentence)

**D. Version** (semantic version, default: 1.0.0)

**E. Author** (bundle author name)

**F. Bundle type** — Present using `AskUserQuestion`:

```
AskUserQuestion:
  questions:
    - question: "What type of bundle is this?"
      header: "Type"
      options:
        - label: "Standards bundle"
          description: "Provides development standards"
        - label: "Tool bundle"
          description: "Provides commands/agents"
        - label: "Mixed bundle"
          description: "Standards + tools"
      multiSelect: false
```

**G. Initial components**
- Skills? (y/n) - If yes, how many initially?
- Commands? (y/n) - If yes, how many initially?
- Agents? (y/n) - If yes, how many initially?

Track `questions_answered` counter.

## Step 4: Create Bundle Structure

**Load bundle structure template:**
```
Read assets/templates/bundle-structure.json
```

Use this template for directories and plugin.json structure.

**Create directories:**
```
bash mkdir -p {scope}/bundles/{bundle-name}/{skills,commands,agents}
```

**Generate plugin.json:**

Create plugin.json using template from bundle-structure.json:
```json
{
  "name": "bundle-name",
  "display_name": "Display Name",
  "description": "Bundle description",
  "version": "1.0.0",
  "author": "Author Name",
  "components": []
}
```

Write:
```
Write: {scope}/bundles/{bundle-name}/plugin.json
```

**Generate README.md:**

Create bundle README with:
- Bundle overview and purpose
- What this bundle provides
- Components list (initially empty)
- Installation instructions
- Usage examples
- Integration notes

Write:
```
Write: {scope}/bundles/{bundle-name}/README.md
```

**Create component READMEs** (if requested):
```
Write: {scope}/bundles/{bundle-name}/skills/README.md
Write: {scope}/bundles/{bundle-name}/commands/README.md
Write: {scope}/bundles/{bundle-name}/agents/README.md
```

Track `files_created` counter.

## Step 5: Create Initial Components

For each component type user requested:

**Skills**: For each skill count:
```
# Recursively invoke workflow 3 (create-skill)
# Pass scope and bundle-name parameters
```

**Commands**: For each command count:
```
# Recursively invoke workflow 2 (create-command)
# Pass scope and bundle-name parameters
```

**Agents**: For each agent count:
```
# Recursively invoke workflow 1 (create-agent)
# Pass scope and bundle-name parameters
```

## Step 6: Update plugin.json

After components created, read plugin.json and update components array with created items.

Track `components_created` counter.

## Step 7: Display Summary

```
╔════════════════════════════════════════════════════════════╗
║          Bundle Created Successfully                       ║
╚════════════════════════════════════════════════════════════╝

Bundle: {bundle-name}
Location: {bundle-path}
Type: {bundle-type}

Components created:
- Skills: {skills_count}
- Commands: {commands_count}
- Agents: {agents_count}

Statistics:
- Questions answered: {questions_answered}
- Files created: {files_created}

Next steps:
1. Review bundle: {bundle-path}
2. Add more components: Use /plugin-create
3. Test bundle
4. Run diagnosis: /plugin-doctor metadata
```

## Step 8: Run Metadata Validation

```
SlashCommand: /pm-plugin-development:plugin-doctor metadata
```

Review results and offer to fix any metadata issues found.
