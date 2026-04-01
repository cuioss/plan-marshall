---
name: recipe-verify-architecture-diagrams
description: Recipe for verifying and updating PlantUML diagrams to reflect current codebase state and regenerating PNG images
user-invocable: false
---

# Recipe: Verify and Update Architecture Diagrams

Recipe for verifying PlantUML diagrams against the current codebase, updating outdated diagrams, and regenerating PNG images. Discovers diagrams, checks references, creates one deliverable per diagram or group.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `recipe_domain` | string | Yes | Domain key (auto-assigned: `documentation`) |
| `recipe_profile` | string | No | Not used |
| `recipe_package_source` | string | No | Not used |

---

## Step 1: Resolve Skills

Documentation skills provide formatting and content standards:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-domain-skills --domain documentation --profile core
```

Store all resolved skill names. Deliverables use profile `implementation` since `.puml` and `.png` files are modified.

---

## Step 2: Discover Diagrams

### 2a. Locate PlantUML Files

Use Glob to find all `.puml` files in the PlantUML directory (default: `doc/plantuml`):

```
Glob: {plantuml_dir}/**/*.puml
```

If no `.puml` files found, report empty scope and return.

### 2b. Check References for Each Diagram

For each `.puml` file, check if its corresponding PNG is referenced in documentation:

- Search `**/*.adoc`, `**/*.md`, and `**/*.java` for the PNG filename
- Classify each diagram as:
  - **Referenced**: PNG found in documentation — include in deliverables
  - **Orphaned**: PNG not referenced anywhere — present to user for decision

### 2c. Present Discovery to User

Show the discovered diagrams with their reference status. For orphaned diagrams, ask the user whether to:
- **Remove**: Delete both `.puml` and `.png` (creates a cleanup deliverable)
- **Keep**: Skip — do not include in deliverables
- **Include anyway**: Verify and update despite no references

---

## Step 3: Collect Deliverable Data

Create deliverables based on discovery results:

### 3a. Diagram Update Deliverables

One deliverable per referenced (or explicitly included) diagram:

- **Title**: `Verify and update diagram: {diagram_name}`
- **Metadata**:
  - `change_type`: `tech_debt`
  - `execution_mode`: `automated`
  - `domain`: `documentation`
  - `module`: `documentation`
  - `depends`: `none`
- **Profiles**: `implementation`
- **Affected files**:
  - `{plantuml_dir}/{diagram}.puml`
  - `{plantuml_dir}/{diagram}.png`
- **Change per file**: Analyze diagram against codebase, update `.puml` if outdated, regenerate `.png`
- **Verification**: `plantuml {plantuml_dir}/{diagram}.puml` (exit code 0 + visual check of PNG)
- **Success Criteria**:
  - Diagram accurately reflects current codebase (classes, methods, relationships)
  - PNG renders without visual errors (no black boxes, overlapping elements)
  - PlantUML syntax is correct
  - Consistent styling with existing diagrams

### 3b. Orphan Cleanup Deliverables (if approved)

One deliverable for all approved orphan removals:

- **Title**: `Remove orphaned diagrams`
- **Metadata**:
  - `change_type`: `tech_debt`
  - `execution_mode`: `automated`
  - `domain`: `documentation`
  - `module`: `documentation`
  - `depends`: `none`
- **Profiles**: `implementation`
- **Affected files**: All `.puml` and `.png` files approved for removal (explicit paths)
- **Change per file**: Delete orphaned diagram files
- **Verification**: Glob confirms files no longer exist
- **Success Criteria**:
  - Approved orphaned files removed
  - No documentation references broken by removal

### 3c. Diagram Split Deliverables (if needed)

During discovery, if a diagram is overly complex, analyze splitting strategies:

1. Consider multiple splitting approaches (by layer, feature, lifecycle)
2. Evaluate pros and cons of each
3. Present analysis and recommendation to user

If user approves a split:

- **Title**: `Split diagram: {diagram_name}`
- **Metadata**: same as 3a, with `depends` on the original diagram's deliverable number
- **Affected files**: New `.puml` files + updated documentation references
- **Change per file**: Create split diagrams, update doc references to include new diagrams

---

## Step 4: Outline Writing

**4a. Read the deliverable template**:

```
Read: marketplace/bundles/plan-marshall/skills/manage-solution-outline/templates/deliverable-template.md
```

**4b. Resolve the target path**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  resolve-path --plan-id {plan_id}
```

**4c. Resolve verification commands** — PlantUML is invoked directly (not via architecture):

```bash
plantuml {plantuml_dir}/{diagram}.puml
```

Verify `plantuml` is available: `which plantuml`. If not installed, note in the outline that installation is required (`brew install plantuml` on macOS, `apt-get install plantuml` on Linux).

**4d. Write the solution outline** using the Write tool to `{resolved_path}`:
- `# Solution: Verify Architecture Diagrams` header with `plan_id`, `created`, `compatibility` metadata
- `## Summary` — scope description ({N} diagrams, {M} orphaned, {K} splits)
- `## Overview` — resolved skills, PlantUML directory, diagram inventory
- `## Deliverables` — all deliverables from Step 3, using the template structure from 4a

**4e. Validate** the written outline:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  write --plan-id {plan_id}
```

---

## Diagram Update Workflow

This section defines how the task executor updates each diagram. Loaded skills provide documentation standards.

### Analysis Phase

For each diagram:

1. **Read the `.puml` file** — identify what it represents (architecture, sequence, class hierarchy)
2. **Identify codebase components** — determine which classes, flows, or structures the diagram should show
3. **Search codebase** — use Grep and Read to find the actual classes, methods, relationships
4. **Compare** — document mismatches:
   - Missing components/classes/methods
   - Renamed or removed elements
   - Changed relationships or flows
   - New architecture patterns

### Update Phase

1. **Edit `.puml`** — reflect current architecture using Edit tool
   - Maintain consistent styling (use `!include plantuml.skin` if present)
   - Ensure correct PlantUML syntax
2. **Generate PNG** — run `plantuml {file}.puml`
3. **Verify PNG** — read the generated image to check for:
   - Clear, readable rendering
   - No visual errors (black boxes indicate missing color settings in `plantuml.skin`)
   - No overlapping elements
   - If errors found: fix `.puml` or skin file, regenerate, verify again

### Complexity Assessment

Before updating, evaluate if the diagram is becoming too large. If so:
- Analyze splitting strategies (by layer, feature, lifecycle)
- Document pros/cons of each approach
- This analysis feeds back into Step 3c for the next iteration

### Constraints

- Only update diagrams where mismatches are found — skip diagrams that already match the codebase
- Preserve existing styling conventions
- When uncertain about any aspect, document the uncertainty in the task output for user review

---

## Related

- `pm-documents:ref-asciidoc` — AsciiDoc formatting and cross-reference standards
- `pm-documents:recipe-doc-verify` — Documentation quality verification recipe
- `plan-marshall:recipe-refactor-to-profile-standards` — Built-in recipe (same 4-step pattern)
- `plan-marshall:phase-3-outline` Step 3 — Loads this skill with input parameters
