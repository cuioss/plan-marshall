# Decision Quality Criteria: migrate-json-to-toon

## Scope Decision

**Expected**: Analyze agents, commands, AND skills + scripts in pm-workflow bundle ONLY

**User clarification handling**:
The request requires user clarification during refine phase:
- Output type: "Both docs and scripts"
- Bundles in scope: "pm-workflow only"
- Script migration: "Yes - full migration"

**Rationale should explain**:
- Request mentions "agents/commands/skills outputs" - all component types
- User clarified "pm-workflow only" - single bundle scope
- User clarified "both docs and scripts" - includes Python scripts, not just SKILL.md
- "Full migration" means scripts should emit TOON, docs should document TOON

**Acceptable variations**:
- May mention "token efficiency" as goal context
- May note that scripts need their json.dumps() calls migrated

**NOT acceptable**:
- Analyzing all bundles (ignores user clarification)
- Analyzing only documentation (ignores "both docs and scripts")
- Skipping script discovery

## Component Type Identification

**Expected pattern for identifying affected components**:

For agents:
- Check pm-workflow agents for JSON output sections
- Exclude agents using TOON format (all pm-workflow agents already use TOON)

For commands:
- Check pm-workflow commands for JSON output specs
- Note: pm-workflow has no commands with JSON output specs

For skills:
- Look for "Output", "JSON Output", "Return...Results" sections with ```json blocks
- Check standards/ and references/ subdirectories for JSON examples
- Include if skill documents JSON output specification

For scripts:
- Search for `print(json.dumps())` patterns - stdout output consumed by callers
- Exclude `f.write(json.dumps())` - file writes for internal storage
- Exclude `json.loads()` (input parsing)

**Key distinction**:
- `print(json.dumps(...))` = script OUTPUT (in scope)
- `f.write(json.dumps(...))` = internal file storage (NOT in scope)

**Decision trail should show**:

In decision.log:
```
(pm-plugin-development:ext-outline-plugin) Component scope: [skills, agents, commands, scripts, tests]
(pm-plugin-development:ext-outline-plugin) Context loaded: domains=[plan-marshall-plugin-dev], bundle=pm-workflow
```

In work.log:
```
[PROGRESS] (pm-plugin-development:ext-outline-plugin) Inventory: 4-5 skills with JSON code blocks in pm-workflow
```

## Script Migration Decision

**Expected**: Full migration of scripts (not just documentation)

**Key decision point**:
- Scripts should emit TOON format instead of JSON
- Documentation should reflect the TOON output format
- Tests should assert on TOON output

**Decision log should include**:
```
(pm-plugin-development:ext-outline-plugin) Migration type: full
  detail: Scripts will emit TOON, docs will document TOON, tests will verify TOON
```

## False Positive Handling

**Expected**: Explicit logging of excluded files

**Must document exclusions for**:

### pm-workflow agents (all use TOON already):
- `pm-workflow/agents/plan-init-agent.md`
- `pm-workflow/agents/task-plan-agent.md`
- `pm-workflow/agents/task-execute-agent.md`
- `pm-workflow/agents/solution-outline-agent.md`
- `pm-workflow/agents/q-gate-validation-agent.md`
- `pm-workflow/agents/request-refine-agent.md`

### Other bundles (out of scope):
- `pm-dev-java/agents/*` - per user clarification
- `plan-marshall/skills/*` - per user clarification

### pm-workflow scripts using TOON already:
- `manage-config/scripts/manage-config.py` - Outputs TOON
- `manage-tasks/scripts/manage-tasks.py` - Outputs TOON
- `manage-references/scripts/manage-references.py` - Outputs TOON
- `manage-solution-outline/scripts/manage_solution_outline.py` - Outputs TOON

### pm-workflow scripts that write JSON to files (not stdout):
- `manage-plan-artifacts/scripts/artifact_store.py` - Uses f.write(json.dumps())
  - This writes to JSONL files for internal storage, NOT script output

**Format** (in work.log):
```
[ARTIFACT] (pm-plugin-development:ext-outline-plugin) Created solution_outline.md - 4 deliverables
```

## Deliverable Grouping Decision

**Expected**: Group by component type and change nature

**Rationale**:
- Skills documentation → 1 deliverable (same change pattern)
- Python scripts → 1 deliverable (same change pattern)
- Test files → 1 deliverable (same change pattern)
- OR grouped by skill if changes are interrelated

**Total**: 3-4 deliverables covering 12 files

**Acceptable variations**:
- May split scripts into separate deliverables if complex
- May combine docs + scripts for same skill if tightly coupled
- Total deliverables in range 2-6

**NOT acceptable**:
- 12 separate deliverables (one per file)
- Including files from other bundles
- Including pm-workflow agents (all use TOON already)

## Clarification Handling Decision

**Expected**: Proper clarification flow during refine phase

**Required clarifications**:
1. Output type (docs only vs docs+scripts)
2. Bundle scope (all vs specific)
3. Migration type (docs only vs full migration)

**Decision should show**:
- Clarification questions asked
- User answers recorded in request.md
- Clarified request reflects narrowed scope

**Format** (in request.md):
```markdown
## Clarifications

Q: Should the migration include Python script outputs in addition to documentation?
A: Both docs and scripts

Q: Which bundles are in scope for this migration?
A: pm-workflow only

Q: Should scripts be modified to emit TOON, or only documentation updated?
A: Yes - full migration
```
