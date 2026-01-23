# Outline Extension Contract

Contract for domain-specific outline extensions loaded by `phase-2-outline`.

---

## Purpose

Outline extensions implement a **formal protocol** that phase-2-outline calls at defined points. They provide domain-specific knowledge for deliverable creation through explicit protocol sections.

**Key Principle**: Extensions are skills with required protocol sections. The phase explicitly calls each section at defined points - no "apply naturally" ambiguity.

---

## Scope Boundaries

**Extensions provide DELIVERABLE-CREATION knowledge only:**
- Assessment criteria (simple vs complex workflow selection)
- Workflow routing (which sub-workflow to load)
- File discovery patterns (Glob/Grep for finding affected files)
- Verification command templates

**Extensions do NOT provide:**
- Component structure rules → Domain reference skills (loaded during execute phase)
- Architecture patterns → Domain reference skills (loaded during execute phase)
- Implementation standards → Domain reference skills (loaded during execute phase)
- Frontmatter requirements → Domain reference skills (loaded during execute phase)

This separation is intentional: outline extensions know HOW TO CREATE DELIVERABLES, while reference skills (like `plugin-architecture`) know HOW TO IMPLEMENT components.

---

## Extension Registration

Domains register outline extensions via `provides_outline()` in their `extension.py`:

```python
class Extension(ExtensionBase):
    def provides_outline(self) -> str | None:
        return "pm-dev-java:ext-outline-java"  # or None if no extension
```

---

## Resolution

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  resolve-workflow-skill-extension --domain java --type outline
```

Returns:
```toon
status: success
domain: java
type: outline
extension: pm-dev-java:ext-outline-java
```

---

## Required Protocol Sections

Every outline extension MUST implement these sections:

| Section | Called By | Purpose | Required |
|---------|-----------|---------|----------|
| `## Assessment Protocol` | phase-2-outline Step 3 | Determine scope and change_type | **Yes** |
| `## Workflow` | phase-2-outline Step 4 | Orchestrate complete outline workflow | **Yes** |
| `## Discovery Patterns` | Within workflow | Domain-specific Glob/Grep patterns | No |

---

## Section: Assessment Protocol

**Called by**: phase-2-outline Step 3 (Assess Complexity)
**Purpose**: Determine scope and change_type BEFORE extension workflow starts

**Required subsections**:
- `### Load Reference Data` - Load domain-specific reference data (optional)
- `### Scope Determination` - Identify affected artifacts and bundles
- `### Change Type Classification` - Classify as create, modify, migrate, or refactor

**Output**:
- `change_type` - One of: create, modify, migrate, refactor
- `work/inventory_filtered.toon` - Persisted inventory with scope and file paths

---

## Section: Workflow (Complete Orchestration)

**Called by**: phase-2-outline Step 4 (Execute Workflow)
**Purpose**: Orchestrate complete outline workflow from discovery to deliverables

Extensions orchestrate the COMPLETE workflow in a single call. NO ping-pong between phase-2-outline and extension.

**Workflow MUST include these steps**:

### a. Discovery and Analysis
- Find files using domain-specific patterns
- Spawn domain analysis agents
- Collect assessments (CERTAIN_INCLUDE, CERTAIN_EXCLUDE, UNCERTAIN)

### b. Uncertainty Resolution
- Resolve UNCERTAIN assessments via user clarification (if any)
- Store clarifications via manage-plan-documents

### c. Synthesize Clarified Request
- Consolidate clarifications into clarified request
- Use manage-plan-documents API

### d. Call Q-Gate Agent (Generic Tool)
- Resolve domain skills for validation (resolve-workflow-skill --domain X --profile implementation)
- Spawn pm-workflow:q-gate-validation-agent with resolved skills
- Q-Gate loads provided skills, reads clarified request
- Q-Gate validates assessments, persists affected_files
- Returns CONFIRMED/FILTERED counts

### e. Build Deliverables
- Read affected_files from references.toon (persisted by Q-Gate)
- Apply domain-specific grouping (by bundle, module, etc.)
- Create deliverables list with metadata, profiles, verification

### f. Return Deliverables
- Return deliverables list to phase-2-outline
- phase-2-outline writes solution_outline.md

**Required subsections**:
- `### Load Persisted Inventory` - Read inventory from assessment phase
- `### Load Request Text` - Read request for analysis
- `### Parallel Component Analysis` - Spawn analysis agents
- `### Aggregate and Validate` - Collect assessment results
- `### Resolve Uncertainties` - User clarification (if needed)
- `### Synthesize Clarified Request` - Consolidate clarifications
- `### Call Q-Gate Agent` - Validate assessments
- `### Build Deliverables` - Create deliverables from affected_files
- `### Return Deliverables` - Return to phase-2-outline

---

## Section: Discovery Patterns (Optional)

**Called by**: Workflow during file enumeration
**Purpose**: Provide domain-specific Glob/Grep patterns for finding affected files

**Subsections** (if implemented):
- `### Grep Patterns` - Table of change type → discovery command
- `### Glob Patterns` - Table of component type → glob pattern

---

## Q-Gate Agent (Generic Tool)

Q-Gate is a GENERIC AGENT TOOL that extensions call during their workflow (Step d).

**Purpose**: Validate CERTAIN_INCLUDE assessments to filter false positives that uncertainty resolution didn't catch.

**How Extensions Call Q-Gate**:

1. First, resolve domain skills:
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  resolve-workflow-skill --domain {domain} --profile implementation
```

2. Then spawn Q-Gate with resolved skills:
```
Task: pm-workflow:q-gate-validation-agent
  Input:
    plan_id: {plan_id}
    skills: [{resolved_skill_1}, {resolved_skill_2}, ...]
  Output:
    confirmed_count: Files passing validation
    filtered_count: False positives caught
    assessments_validated: Count of validated assessments
```

**What Q-Gate Does**:

1. Loads domain skills (via resolve-workflow-skill)
2. Reads clarified request (via manage-plan-documents)
3. Validates each CERTAIN_INCLUDE assessment using validation criteria:
   - **Output Ownership**: Component documents another's output
   - **Consumer vs Producer**: Component consumes, not produces
   - **Request Intent Match**: Modification fulfills request
   - **Duplicate Detection**: Not already covered
4. Writes CONFIRMED/FILTERED assessments to assessments.jsonl
5. Persists affected_files to references.toon (only Q-Gate knows final decisions)
6. Logs its own lifecycle (agent logs itself, not orchestrator)
7. Returns statistics

**Why Generic**:
- Same validation criteria across all domains
- Reusable by all extensions
- Loads domain skills for context (but validation logic is generic)

**Extension Responsibilities**:
- Call Q-Gate as a tool during workflow (Step d)
- Use affected_files from Q-Gate (not CERTAIN_INCLUDE assessments)
- Build deliverables using only CONFIRMED files

**phase-2-outline Responsibilities**:
- Call extension once (Step 4)
- Write solution_outline.md with deliverables from extension (Step 5)
- Set domains, record lessons, return results (Steps 6-8)

---

## Uncertainty Resolution Pattern

**Implemented by**: Domain extension workflow (Step b - between analysis and Q-Gate)
**Purpose**: Resolve UNCERTAIN findings from analysis agents through user clarification

**Trigger**: Run when analysis agents return UNCERTAIN findings (confidence < 80%).

**Pattern components**:
- Uncertainty Grouping - How to group similar uncertainties for efficient questioning
- Question Templates - AskUserQuestion templates for each uncertainty type
- Resolution Application - How user answers resolve UNCERTAIN → CERTAIN_INCLUDE or CERTAIN_EXCLUDE

### Uncertainty Grouping

Group UNCERTAIN findings by similar patterns to minimize questions. Common groupings:

| Grouping Type | Description |
|---------------|-------------|
| Same ambiguity reason | e.g., "JSON in workflow context" |
| Same file section | e.g., "Content in ## Workflow steps" |
| Same bundle | e.g., "All findings in pm-workflow" |

### Question Templates

Use AskUserQuestion with specific examples from findings:

```
"Should files with JSON in workflow context be included?"

Examples found:
- manage-adr/SKILL.md (45%): JSON in "## Create ADR" workflow step
- workflow-integration-ci/SKILL.md (52%): JSON in "## Fetch Comments" step

Options:
1. Exclude workflow JSON (Recommended) - Only include explicit ## Output sections
2. Include all JSON - Include any ```json regardless of context
```

### Resolution Application

After user answers:
1. Update each UNCERTAIN finding in the group to CERTAIN_INCLUDE or CERTAIN_EXCLUDE
2. Set confidence to 85% (reflects user clarification)
3. Log resolution decision with hash ID reference

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "[RESOLUTION:{finding_hash_id}] (ext-outline-plugin) {file_path}: UNCERTAIN ({old_confidence}%) → {new_certainty} (85%)
  detail: User clarified: {user_choice}"
```

### Storage

Store clarifications in request.md via manage-plan-documents:

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents \
  request clarify \
  --plan-id {plan_id} \
  --clarifications "{formatted Q&A pairs}" \
  --clarified-request "{synthesized request with scope and exclusions}"
```

---

## Enforcement Requirements

Extensions implementing this protocol MUST follow these rules:

### Per-Component Analysis

When inventory returns components of a type (agents, commands, skills), the extension:
1. MUST analyze each component individually against request criteria
2. MUST NOT make blanket assumptions about component types
3. MUST log individual `[FINDING]` entries for each component (affected or not)

### Prohibited Patterns

Extensions MUST NOT:
- Exclude entire component types with a single decision (e.g., "skills don't have outputs")
- Use categorical statements as exclusion rationale
- Skip analysis steps for any component returned by inventory

**Anti-pattern (PROHIBITED):**
```
[FINDING] Skills analysis complete: Skills are knowledge documents without output formats
```

**Required pattern:**
```
[FINDING] Affected: bundle/skills/skill-a/SKILL.md
  detail: Contains output specification matching request criteria

[FINDING] Not affected: bundle/skills/skill-b/SKILL.md
  detail: No matching criteria found after checking sections X, Y, Z
```

### Batch Checkpoint Requirements

If inventory includes multiple component types (e.g., agents, commands, skills), ALL types must show batch progress logs:
```
[STATUS] Analyzed agents batch 1 of pm-workflow: 3 affected, 2 not affected
[STATUS] Analyzed commands batch 1 of pm-workflow: 0 affected, 5 not affected
[STATUS] Analyzed skills batch 1 of pm-workflow: 2 affected, 8 not affected
```

---

## Example Implementation

See: `pm-plugin-development:ext-outline-plugin`

This extension demonstrates the protocol pattern with:
- Assessment Protocol with change_type classification (create, modify, migrate, refactor)
- Unified Workflow section with internal routing based on change_type
- Conditional loading of script-verification.md for script changes

---

## Related Documents

- [extension-mechanism.md](extension-mechanism.md) - How extensions work
- [triage-extension.md](triage-extension.md) - Triage extension contract
- [phase-2-outline SKILL.md](../../../phase-2-outline/SKILL.md) - Phase that loads this extension
