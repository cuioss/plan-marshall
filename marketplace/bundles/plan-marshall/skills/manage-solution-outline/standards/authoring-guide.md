# Authoring Guide: Writing a Solution Document

Step-by-step workflow for creating a solution outline document. This guide is used by `phase-3-outline` when composing the solution.

## Step 1: Load Project Architecture

Load project architecture knowledge via the `plan-marshall:manage-architecture` skill:

```
Skill: plan-marshall:manage-architecture
```

Then query module information:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture info
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture module --name {module-name}
```

Use the returned structure for:

| Section | Use For |
|---------|---------|
| `modules.{name}.responsibility` | Understand what each module does |
| `modules.{name}.purpose` | Understand module classification (library, extension, etc.) |
| `modules.{name}.key_packages` | Identify architecturally significant packages |
| `modules.{name}.skills_by_profile` | Know which skills apply per profile |
| `modules.{name}.tips` | Apply implementation guidance |
| `modules.{name}.insights` | Leverage learned knowledge |
| `internal_dependencies` | Know what depends on what |

## Step 2: Analyze Request

Read the request document to understand:
- What is being requested
- Scope and constraints
- Success criteria

## Step 3: Design Architecture

Before writing, determine:
- Components involved
- Dependencies between components
- Execution order

## Step 4: Create Diagram

Draw ASCII diagram showing:
- New components (boxed)
- Existing components (labeled)
- Dependencies (arrows)
- Package/file structure

See [solution-outline-standard.md](solution-outline-standard.md) for patterns and examples by task type.

## Step 5: Write and Validate Document

Use the resolve-path → Write → validate pattern:

```bash
# 1. Get target path
python3 .plan/execute-script.py \
  plan-marshall:manage-solution-outline:manage-solution-outline resolve-path \
  --plan-id {plan_id}
# Returns: path: .plan/plans/{plan_id}/solution_outline.md

# 2. Write content directly (Write tool — already permitted via Write(.plan/**))
Write({resolved_path}) with solution outline content

# 3. Validate
python3 .plan/execute-script.py \
  plan-marshall:manage-solution-outline:manage-solution-outline write \
  --plan-id {plan_id}
```

**Note**: The `write` command validates the file already on disk — it does NOT read from stdin. Checks for required sections (Summary, Overview, Deliverables) and numbered deliverable format (`### N. Title`). Returns `validation_failed` error if validation fails.

**Workflow clarification**: The Write tool creates/updates the file content. The script commands (`write`/`update`) only validate what's on disk. This separation allows the LLM to compose content freely while ensuring structural compliance.
