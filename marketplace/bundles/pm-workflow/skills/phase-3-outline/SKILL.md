---
name: phase-3-outline
description: Architecture-driven solution outline creation with intelligent module selection and profiles list
user-invocable: false
allowed-tools: Read, Glob, Grep, Bash
---

# Phase Outline Skill

**Role**: Architecture-driven workflow skill for creating solution outlines. Uses pre-computed architecture data to make intelligent module and package placement decisions.

**Key Insight**: Module and package matching is **semantic analysis** that requires LLM reasoning. Scripts provide DATA, the LLM provides REASONING.

**Prerequisite**: Request must be refined (phase-2-refine completed).

---

## Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `feedback` | string | No | User feedback from review (for revision iterations) |

---

## Workflow Overview

```
Step 1: Load Refined Request → Step 2: Load Extension → Steps 3-4: Create Deliverables → Step 5: Write Solution → Steps 6-8: Finalize
```

**Visual diagram**: `standards/workflow-overview.md` (for human reference)

---

## Step 1: Load Refined Request

**Purpose**: Load the refined request from phase-2-refine output.

The request has already been clarified during phase-2-refine. Load it for deliverable creation.

**EXECUTE**:
```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} \
  --section clarified_request
```

If clarified_request not found, read full request:
```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id}
```

**Log**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[STEP-1] (pm-workflow:phase-3-outline) Loaded refined request"
```

---

## Step 2: Load Outline Extension

For each domain from Step 1 output, check if an outline extension exists and load it.

**Purpose**: Outline extensions implement a **formal protocol** with defined sections that this workflow calls explicitly at Steps 3 and 4.

**For each domain** from Step 1 `domains` array:

**EXECUTE**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  resolve-workflow-skill-extension --domain {domain} --type outline \
  --trace-plan-id {plan_id}
```

**Output (TOON)**:
```toon
status: success
domain: {domain}
type: outline
extension: pm-plugin-development:ext-outline-plugin  # or null if no extension
```

**If extension exists (not null)**, load it:

```
Skill: {resolved_extension}
```

The extension implements these **protocol sections** (called in Steps 3-4):
- **## Assessment Protocol**: Determine scope and change_type before workflow starts
- **## Workflow**: Orchestrate complete outline workflow (routes internally based on change_type)
- **## Discovery Patterns**: Domain-specific Glob/Grep patterns (optional)

**Contract**: `pm-workflow:workflow-extension-api/standards/extensions/outline-extension.md`

**If no extension exists**: Continue with generic workflow (Steps 3-4 use built-in defaults).

---

## Step 3: Assess Complexity (via Extension Protocol)

**If extension loaded (from Step 2)**: Call the extension's `## Assessment Protocol` section.

The extension's Assessment Protocol determines:
- `change_type`: create, modify, migrate, or refactor
- Scope of affected components
- Any conditional standards to load

**If no extension**: Use generic assessment below.

### Generic Assessment (no extension)

| Scope | Workflow | Action |
|-------|----------|--------|
| Single module affected | **Simple** | Proceed to module selection |
| Multiple modules affected | **Complex** | Decompose first, then simple workflow per sub-task |

### Simple Workflow (single module)

```
┌───────────────────────────────┐
│       SIMPLE WORKFLOW         │
├───────────────────────────────┤
│ 1. Select target module       │
│ 2. Select target package      │
│ 3. Create deliverables        │
└───────────────────────────────┘
```

### Complex Workflow (multi-module)

```
┌───────────────────────────────┐
│       COMPLEX WORKFLOW        │
├───────────────────────────────┤
│ 1. Load dependency graph      │
│ 2. Decompose into sub-tasks   │
│ 3. Run simple workflow each   │
│ 4. Aggregate deliverables     │
│ 5. Order by layers (graph)    │
└───────────────────────────────┘
```

For complex tasks, load the complete dependency graph to determine execution ordering.

**EXECUTE**:
```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture graph \
  --trace-plan-id {plan_id}
```

Output format: `plan-marshall:analyze-project-architecture/standards/module-graph-format.md` (force load)

**Detail**: See `standards/module-selection.md` for decomposition patterns and dependency ordering.

---

## Step 4: Execute Workflow (via Extension Protocol)

**Purpose**: Call extension to orchestrate complete outline workflow.

**If extension loaded** (from Step 2):

  Call extension's `## Workflow` section (based on Step 3 assessment).

  Extension orchestrates complete workflow:
  - Discovery and analysis
  - Uncertainty resolution + Synthesize clarified request
  - Call Q-Gate agent (generic, reusable tool)
  - Build deliverables using affected_files from Q-Gate
  - Return deliverables

  Extension returns deliverables list.

**If no extension** (generic module-based workflow):

  Run module-based workflow (Steps 4a-4d below):

---

### Step 4a: Select Target Modules (Generic/Module-Based Domains)

For simple tasks: identify the single affected module. For complex tasks: select module for each sub-task.

### Get Module List

**EXECUTE**:
```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture modules \
  --trace-plan-id {plan_id}
```

Returns all module names. Use this list as candidates for evaluation.

### Module Selection Analysis

For each module returned, evaluate:

| Factor | Weight | Score Criteria |
|--------|--------|----------------|
| responsibility match | 3 | Keywords in task match responsibility |
| purpose fit | 2 | Purpose compatible with change type |
| key_packages match | 3 | Task aligns with package descriptions |
| dependency position | 2 | Correct layer for the change |

**Selection threshold**: Modules with weighted score >= 6 are candidates.

### Query Module Details

For each candidate module:

**EXECUTE**:
```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture module \
  --name {module} \
  --trace-plan-id {plan_id}
```

### Document Selection Reasoning

**Template**: `templates/module-selection-analysis.md` (force load)

---

### Step 4b: Determine Package Placement

For each selected module, determine where new code belongs.

### Load Complete Package Structure

**EXECUTE**:
```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture module \
  --name {module} --full \
  --trace-plan-id {plan_id}
```

### Package Selection Decision Matrix

| Scenario | Action |
|----------|--------|
| Task matches key_package description | Place in that key_package |
| Task needs utility location | Check for existing util package |
| New cross-cutting concern | Create new package (document reasoning) |
| Unclear placement | Check has_package_info packages first |

**Detail**: See `standards/module-selection.md` for key_packages guidance and validation checklist.

### Document Package Reasoning

**Template**: `templates/package-selection.md` (force load)

---

### Step 4c: Create Deliverables with Profiles List

Create deliverables with module context and a profiles list.

**Core constraint**: One deliverable = one module.

### Check Module Test Infrastructure

**EXECUTE**:
```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture modules \
  --command module-tests \
  --trace-plan-id {plan_id}
```

Returns list of module names that have unit test infrastructure.

### Profiles Block

Create `**Profiles:**` block listing which profiles apply:
- `implementation`: Always included
- `testing`: Only if module has test infrastructure

**Key Design**: Deliverables specify WHAT profiles apply (visible to user). Task-plan resolves WHICH skills from architecture (technical detail).

### Deliverable Structure

**Template**: `pm-workflow:manage-solution-outline/templates/deliverable-template.md` (force load)

For each deliverable, complete ALL fields in the template. **No field may be omitted.**

The template enforces:
- Metadata block (change_type, execution_mode, domain, module, depends)
- Profiles block (implementation; testing if module has test infra)
- Affected files (explicit paths - no wildcards)
- Verification section (command and criteria)
- Success Criteria section

### Validate Deliverables Against Request

Before writing solution document, verify each deliverable:

1. **Request alignment**: Does deliverable directly address a request requirement?
2. **Module verification**: Was module selected through per-candidate scoring (not assumed)?
3. **Profile accuracy**: Are listed profiles based on actual architecture query (not inferred)?

Log validation:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[VALIDATION] (pm-workflow:phase-3-outline) Deliverable {N} validated: module={module}, profiles={profiles}, request_criteria={matched}"
```

---

### Step 4d: Create IT Deliverable (Optional)

If integration tests are needed, create a **separate deliverable** targeting the IT module.

### When to Create IT Deliverable

| Change Type | IT Needed? | Rationale |
|-------------|------------|-----------|
| API endpoint (REST, GraphQL) | **YES** | External contract |
| UI component | **YES** | User-facing behavior |
| Public library API | **YES** | Consumer contract |
| Configuration/properties | **YES** | Runtime behavior |
| Internal implementation | NO | No external impact |
| Refactoring (same behavior) | NO | Behavior unchanged |
| Private/internal classes | NO | Not externally visible |

### Check IT Infrastructure

**EXECUTE**:
```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture modules \
  --command integration-tests \
  --trace-plan-id {plan_id}
```

**If result is empty**: Skip IT deliverable (no IT module exists).

**Detail**: See `standards/integration-tests.md` for IT decision flow, module patterns, and verification commands.

### IT Deliverable Structure

IT deliverables use the same template as implementation deliverables.

**Template**: `pm-workflow:manage-solution-outline/templates/deliverable-template.md`

**Key Differences**:
- IT is always a **separate deliverable** - not embedded in implementation deliverable
- IT targets the **IT module** - found via `architecture modules --command integration-tests`
- IT depends on implementation - set `depends:` to reference the implementation deliverable
- IT has only `implementation` profile - IT code is "implementation" of test code

**Return deliverables list** from generic workflow.

---

## Step 5: Write Solution Document

**Purpose**: Write solution_outline.md using deliverables from extension (or generic workflow).

Write the solution document using heredoc with deliverables from Step 4.

**Skill**: `pm-workflow:manage-solution-outline` (force load)

Provides complete guidance on solution document structure, diagram patterns, and examples by task type.

### CRITICAL Format Requirements

The write command validates automatically. To pass validation:

**Document Structure** (required sections):
```markdown
# Solution: {title}

## Summary        ← REQUIRED (2-3 sentences)

## Overview       ← REQUIRED (ASCII diagram)

## Deliverables   ← REQUIRED (numbered ### headings)
```

**Deliverable Heading Format**:
```markdown
### 1. First Deliverable Title   ← Format: ### N. Title
### 2. Second Deliverable Title  ← Numbers must be sequential
```

**Affected Files - NO WILDCARDS**:
```markdown
**Affected files:**
- `path/to/specific/file1.md`     ← CORRECT: explicit path
- `path/to/specific/file2.md`     ← CORRECT: explicit path
- `path/to/agents/*.md`           ← INVALID: wildcard pattern
- All files in path/to/agents/    ← INVALID: vague reference
```

You MUST enumerate every file explicitly. Use Glob tool to discover files, then list each one.

**EXECUTE**:
```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline \
  write \
  --plan-id {plan_id} <<'EOF'
{content per manage-solution-outline skill with deliverables per deliverable-contract.md}
EOF
```

Validation runs automatically on every write.

---

## Step 6: Set Detected Domains

**EXECUTE**:
```bash
python3 .plan/execute-script.py pm-workflow:manage-config:manage-config set \
  --plan-id {plan_id} --field domains --value '["domain1", "domain2"]'
```

This is an **intelligent decision output** - not a copy of marshal.json domains, but Claude's analysis of which domains are relevant to the specific request.

---

## Step 7: Record Issues as Lessons

**EXECUTE**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lesson add \
  --component-type skill \
  --component-name phase-3-outline \
  --category observation \
  --title "{issue summary}" \
  --detail "{context and resolution approach}" \
  --trace-plan-id {plan_id}
```

---

## Step 8: Return Results

Return structured output:
```toon
status: success
plan_id: {plan_id}
deliverable_count: {N}
domains_detected: [{detected_domains}]
lessons_recorded: {count}
message: {error message if status=error}
```

---

## Error Handling

| Scenario | Action |
|----------|--------|
| Architecture not found | Return `{status: error, message: "Run /marshall-steward first"}` and abort |
| Request not found | Return `{status: error, message: "Request not found"}` |
| Validation fails | Fix issues or return partial with error list |
| Domain unknown | Return error with valid domains |
| Script execution fails | Record lesson-learned, return error |

---

## Integration

**Invoked by**: `pm-workflow:solution-outline-agent` (thin agent)

**Script Notations** (use EXACTLY as shown):
- `plan-marshall:analyze-project-architecture:architecture` - Architecture queries
- `pm-workflow:manage-solution-outline:manage-solution-outline` - Write solution document
- `pm-workflow:manage-plan-documents:manage-plan-documents` - Request operations
- `pm-workflow:manage-config:manage-config` - Plan config operations
- `pm-workflow:manage-references:manage-references` - Plan references
- `plan-marshall:manage-lessons:manage-lesson` - Record lessons on issues

**Consumed By**:
- `pm-workflow:phase-4-plan` skill (reads deliverables for task creation)

---

## Output Validation

The workflow skill MUST validate that each deliverable contains all required fields from the deliverable contract:

- [ ] `change_type` metadata
- [ ] `execution_mode` metadata
- [ ] `domain` metadata (valid domain from marshal.json)
- [ ] `module` metadata (module name from architecture)
- [ ] `depends` field (`none` or valid deliverable references)
- [ ] `**Profiles:**` block with valid profiles (`implementation` always; `testing` if module has test infra)
- [ ] Explicit file list (not "all files matching X")
- [ ] Verification command and criteria

---

## Related Documents

- `pm-workflow:workflow-extension-api/standards/extensions/outline-extension.md` - Outline extension contract
- `pm-workflow:manage-solution-outline/standards/deliverable-contract.md` - Deliverable structure
- `pm-workflow:workflow-architecture` - Workflow architecture overview
- `plan-marshall:analyze-project-architecture` - Architecture API documentation
- `plan-marshall:analyze-project-architecture/standards/module-graph-format.md` - Module dependency graph format
