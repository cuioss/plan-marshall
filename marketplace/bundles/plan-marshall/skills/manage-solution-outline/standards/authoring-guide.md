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
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture module --module {module-name}
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

## Step 5: Write Solution Metadata Header

Every solution outline MUST include a top-level `## Solution Metadata` block placed immediately after the `## Summary` section. The block carries solution-level fields (distinct from per-deliverable metadata in the Deliverable Contract) that drive downstream workflow decisions.

**Required fields**:

| Field | Values | Purpose |
|-------|--------|---------|
| `scope_estimate` | `none\|surgical\|single_module\|multi_module\|broad` | Classifies change footprint; consumed by Q-Gate bypass and execution-manifest decisions |

**Authoring example**:

```markdown
## Solution Metadata

- scope_estimate: surgical
```

**Choosing `scope_estimate`** — derive from the union of `affected_files` across all deliverables (see [solution-outline-standard.md](solution-outline-standard.md#scope_estimate) for the authoritative derivation table):

1. Empty union (analysis-only) → `none`
2. ≤3 files in one module, no public API surface → `surgical`
3. ≤10 files in one module → `single_module`
4. >1 module touched → `multi_module`
5. Codebase-wide / glob-only file lists → `broad`

`phase-2-refine` produces an initial estimate from `module_mappings`. When authoring during `phase-3-outline`, refine the estimate after the deliverable list crystalizes (e.g., a Simple Track plan whose final deliverables touch ≤3 files in one module is downgraded to `surgical`).

**Downstream consumers**:

- **Q-Gate bypass** (`phase-6-finalize`): Plans with `scope_estimate: none` or `surgical` are eligible for reduced quality-gate scope.
- **Execution manifest** (`phase-4-plan`): The manifest builder uses `scope_estimate` to size verification scope (single-module test runs vs full-suite runs).
- **`get-field` API**: Downstream skills read the persisted value via `manage-solution-outline get-field --field scope_estimate`.

**Validator behavior**: `validate`/`write`/`update` reject the document when the `## Solution Metadata` block is missing, when `scope_estimate` is absent, or when its value is not in the enum above.

## Step 6: Write and Validate Document

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

**Note**: The `write` command validates the file already on disk — it does NOT read from stdin. Checks for required sections (Solution Metadata, Summary, Overview, Deliverables), the presence and enum-validity of `scope_estimate`, and numbered deliverable format (`### N. Title`). Returns `validation_failed` error if validation fails.

**Workflow clarification**: The Write tool creates/updates the file content. The script commands (`write`/`update`) only validate what's on disk. This separation allows the LLM to compose content freely while ensuring structural compliance.
