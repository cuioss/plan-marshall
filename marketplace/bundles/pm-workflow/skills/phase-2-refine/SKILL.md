---
name: phase-2-refine
description: Iterative request clarification until confidence threshold reached
user-invocable: false
allowed-tools: Read, Glob, Grep, Bash, AskUserQuestion
---

# Phase 2: Refine Request

Iterative workflow for analyzing and refining the request until requirements meet confidence threshold.

## Purpose

Before creating deliverables (phase-3-outline), ensure the request is:
- **Correct**: Requirements are technically valid
- **Complete**: All necessary information is present
- **Consistent**: No contradictory requirements
- **Non-duplicative**: No redundant requirements
- **Unambiguous**: Clear, single interpretation possible

---

## Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |

---

## Step 1: Check for Unresolved Q-Gate Findings

**Purpose**: On re-entry (after Q-Gate or user review flagged issues), address unresolved findings before re-running analysis.

### Query Unresolved Findings

```bash
python3 .plan/execute-script.py pm-workflow:manage-findings:manage-findings \
  qgate query {plan_id} --phase 2-refine --resolution pending
```

### Address Each Finding

If unresolved findings exist (filtered_count > 0):

For each pending finding:
1. Analyze the finding in context of current request and architecture
2. Address it (revise analysis, re-evaluate scope, etc.)
3. Resolve:
```bash
python3 .plan/execute-script.py pm-workflow:manage-findings:manage-findings \
  qgate resolve {plan_id} {hash_id} taken_into_account --phase 2-refine \
  --detail "{what was done to address this finding}"
```
4. Log resolution:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(pm-workflow:phase-2-refine:qgate) Finding {hash_id} [{source}]: taken_into_account — {resolution_detail}"
```

Then continue with normal Steps 2..12 (phase re-runs with corrections applied).

If no unresolved findings: Continue with normal Steps 2..12 (first entry).

---

## Step 2: Load Confidence Threshold

Read the confidence threshold from project configuration.

**EXECUTE**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-2-refine get --field confidence_threshold --trace-plan-id {plan_id}
```

**Default**: If not configured or field not found, use `95` (95% confidence required).

**Log**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[REFINE:2] (pm-workflow:phase-2-refine) Using confidence threshold: {confidence_threshold}%"
```

Store as `confidence_threshold` for use in Step 8.

---

## Step 3: Load Compatibility Strategy

Read the compatibility approach from project configuration and persist to references.json in Step 11.

**EXECUTE**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-2-refine get --field compatibility --trace-plan-id {plan_id}
```

**No fallback** — if not configured, fail with error: "compatibility not configured. Run /marshall-steward first".

**Valid values with descriptions**:

| Value | Description |
|-------|-------------|
| `breaking` | Clean-slate approach, no deprecation nor transitionary comments |
| `deprecation` | Add deprecation markers to old code, provide migration path |
| `smart_and_ask` | Assess impact and ask user when backward compatibility is uncertain |

**Log** (to decision.log - config read is a decision):
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(pm-workflow:phase-2-refine) Config: compatibility={compatibility}"
```

Store as `compatibility` and `compatibility_description` (the long description from the table above) for use in Step 11 return output.

---

## Step 4: Load Architecture Context

Query project architecture BEFORE any analysis. Architecture data is pre-computed and compact (~500 tokens).

**EXECUTE**:
```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture info \
  --trace-plan-id {plan_id}
```

Output format: `plan-marshall:analyze-project-architecture/standards/client-api.md`

**If status=error or architecture not found**: Return error and abort:
```toon
status: error
message: Run /marshall-steward first
```

### Extract Architecture Summary

From the `architecture info` output, extract and store:

| Field | Source | Use In |
|-------|--------|--------|
| `project_name` | `project.name` | Context for questions |
| `project_description` | `project.description` | Scope validation |
| `technologies` | `technologies[]` | Step 6 Correctness validation |
| `module_names` | `modules[].name` | Step 7 Module Mapping |
| `module_purposes` | `modules[].purpose` | Step 7 Feasibility Check |

**Store as** `arch_context` for use in Steps 6-7.

**Example extraction**:
```
arch_context:
  project_name: oauth-sheriff
  project_description: JWT validation library for Quarkus
  technologies: [maven]
  modules:
    - name: oauth-sheriff-core
      purpose: library
    - name: oauth-sheriff-quarkus
      purpose: extension
```

### Log Completion

**Log**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[REFINE:4] (pm-workflow:phase-2-refine) Loaded architecture: {project_name} ({module_count} modules)"
```

---

## Step 5: Load Request

Load the request document.

**EXECUTE**:
```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id}
```

Output format: `pm-workflow:manage-plan-documents/documents/request.toon`

**Extract**:
- `title`: Request title
- `description`: Full request text
- `clarifications`: Any existing clarifications (from prior iterations)
- `clarified_request`: Synthesized request (if exists from prior iterations)

**Log**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[REFINE:5] (pm-workflow:phase-2-refine) Loaded request: {title}"
```

---

## Step 6: Analyze Request Quality

Evaluate the request against five quality dimensions.

### Correctness

**Check**: Are requirements technically valid? **Use `arch_context` from Step 4**.

| Aspect | Check | Architecture Data Used |
|--------|-------|------------------------|
| Technology references | Do mentioned technologies/frameworks exist? | `arch_context.technologies` |
| Module references | Do mentioned modules exist in the project? | `arch_context.modules[].name` |
| API references | Are referenced APIs/methods valid in the codebase? | Query if unclear |
| Pattern references | Are mentioned patterns appropriate for the domain? | `arch_context.project_description` |
| Constraint validity | Are constraints achievable (not mutually exclusive)? | Module purposes |

**Validation against architecture**:
- If request mentions "Maven" but `technologies` doesn't include `maven` → ISSUE
- If request mentions module "foo-bar" but it's not in `modules` → ISSUE
- If request mentions "Quarkus CDI" but project is plain Java library → ISSUE

**Finding format**:
```
CORRECTNESS: {PASS|ISSUE}
  - {specific finding with evidence}
  - Architecture reference: {what was checked against}
```

### Completeness

**Check**: Is all necessary information present?

| Aspect | Check |
|--------|-------|
| Scope clarity | Is it clear what IS and IS NOT in scope? |
| Success criteria | Are acceptance criteria defined or inferrable? |
| Test requirements | Are testing expectations stated (or can be inferred from domain)? |
| Dependencies | Are prerequisite changes or dependencies mentioned? |

**Finding format**:
```
COMPLETENESS: {PASS|MISSING}
  - {what is missing and why it matters}
```

### Consistency

**Check**: Are requirements internally consistent?

| Aspect | Check |
|--------|-------|
| No contradictions | Requirements don't conflict with each other |
| Aligned constraints | Technology choices don't conflict |
| Coherent scope | All parts work toward same goal |

**Finding format**:
```
CONSISTENCY: {PASS|CONFLICT}
  - {conflicting requirements with explanation}
```

### Non-Duplication

**Check**: Are there redundant requirements?

| Aspect | Check |
|--------|-------|
| No repeated asks | Same thing not requested multiple ways |
| No overlapping scope | Requirements don't cover same ground differently |

**Finding format**:
```
DUPLICATION: {PASS|REDUNDANT}
  - {duplicated requirements and recommendation}
```

### Ambiguity

**Check**: Is there only one valid interpretation?

| Aspect | Check |
|--------|-------|
| Clear terminology | Domain terms are unambiguous |
| Specific scope | "All X" or "some X" is clear |
| Measurable criteria | Success is objectively determinable |
| Clear boundaries | Where changes start/stop is explicit |

**Finding format**:
```
AMBIGUITY: {PASS|UNCLEAR}
  - {ambiguous element and possible interpretations}
```

---

## Step 7: Analyze Request in Architecture Context

With `arch_context` from Step 4, analyze how the request maps to the codebase.

### Module Mapping

**Question**: Which modules are affected by this request?

**Initial mapping** (use `arch_context.modules` from Step 4):

For each requirement, identify candidate modules:
- Does the request mention specific modules? → Check against `arch_context.modules[].name`
- Does the request mention functionality? → Match against `arch_context.modules[].purpose`
- Are there implicit module dependencies?

**When to query detailed module info**:

If mapping is unclear (confidence < 70%), query detailed module info:

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture module \
  --name {candidate_module} --trace-plan-id {plan_id}
```

This provides:
- `responsibility`: What the module does (e.g., "Core JWT validation logic")
- `key_packages`: Package structure and descriptions
- `key_dependencies`: External dependencies that indicate functionality
- `internal_dependencies`: Dependencies on other project modules

**Decision tree for detailed queries**:

| Situation | Action |
|-----------|--------|
| Request mentions specific module by name | No query needed (direct match) |
| Request mentions functionality, multiple modules possible | Query candidates to compare `responsibility` |
| Request is cross-cutting (affects multiple modules) | Query graph to understand dependencies |
| Request scope unclear | Query detailed info for all candidate modules |

**Graph query** (for cross-module changes):
```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture graph \
  --trace-plan-id {plan_id}
```

**Finding format**:
```
MODULE_MAPPING: {CLEAR|NEEDS_CLARIFICATION}
  - Requirement: "{requirement text}"
  - Candidate modules: [{module1}, {module2}]
  - Confidence: {percentage}
  - Reason: {why these modules, or why unclear}
  - Detailed query: {yes/no - whether module details were retrieved}
```

### Feasibility Check

**Question**: Can this request be implemented given the architecture?

**Use architecture data to validate**:

| Aspect | Check | Data Source |
|--------|-------|-------------|
| Module boundaries | Does request respect existing module boundaries? | `arch_context.modules[].purpose` |
| Dependency direction | Does request respect dependency flow? | `architecture graph` output |
| Extension points | Are there appropriate extension points for the change? | Module details `internal_dependencies` |
| Technology fit | Does request match project technologies? | `arch_context.technologies` |

**Common feasibility concerns**:
- Request asks to modify `library` module but change requires runtime context → CONCERN
- Request requires dependency from leaf module to root module (wrong direction) → CONCERN
- Request assumes framework feature not present in `technologies` → CONCERN

**Finding format**:
```
FEASIBILITY: {FEASIBLE|CONCERN}
  - {concern and architectural constraint}
  - Architecture check: {what was validated}
```

### Scope Size Estimation

**Question**: What is the approximate scope?

| Scope | Criteria |
|-------|----------|
| `single_file` | 1 specific file clearly identified |
| `single_module` | 1 module, < 5 files |
| `few_files` | 1-2 modules, 5-15 files with clear targets |
| `multi_module` | 3+ modules, 15+ files |
| `codebase_wide` | Cross-cutting, unclear boundaries, "all X" pattern |

**Finding format**:
```
SCOPE_ESTIMATE: {single_file|single_module|few_files|multi_module|codebase_wide}
  - Modules affected: {count}
  - Estimated files: {range}
  - Rationale: {brief explanation}
```

### Track Selection

**Question**: Does this request need complex discovery or can targets be determined directly?

**Track Selection Logic**:

```
Simple Track when ALL of:
  - scope_estimate is single_file, single_module, or few_files
  - module_mapping explicitly specifies target file(s)
  - Request is localized (add, create, implement specific thing)

Complex Track when ANY of:
  - scope_estimate is multi_module or codebase_wide
  - Request contains scope words: "all", "everywhere", "across", "migrate"
  - module_mapping is broad or missing
  - Domain requires discovery (plugins, documentation, requirements)
```

**Scope Words Detection**:
Scan request text for: `all`, `every`, `everywhere`, `across`, `migrate`, `update all`, `refactor`, `replace all`

**Domain Discovery Requirements**:
Some domains have no standard structure and always need discovery:
- `plan-marshall-plugin-dev` (marketplace plugins)
- `documentation` (AsciiDoc, ADR locations vary)
- `requirements` (specs can be anywhere)

**Finding format**:
```
TRACK_SELECTION: {simple|complex}
  - Scope: {scope_estimate}
  - Scope words found: {yes/no - which words}
  - Module mapping explicit: {yes/no}
  - Domain requires discovery: {yes/no}
  - Reasoning: {why this track}
```

**Log track decision** (to decision.log):
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(pm-workflow:phase-2-refine) Track: {track} - {reasoning}"
```

---

## Step 8: Evaluate Confidence

Aggregate findings from Steps 6-7 into confidence score.

If confidence >= threshold → go to Step 11. Otherwise continue.

### Confidence Calculation

| Dimension | Weight | Score |
|-----------|--------|-------|
| Correctness | 20% | 100 if PASS, 0 if ISSUE |
| Completeness | 20% | 100 if PASS, 50 if minor missing, 0 if major missing |
| Consistency | 20% | 100 if PASS, 0 if CONFLICT |
| Non-Duplication | 10% | 100 if PASS, 80 if REDUNDANT |
| Ambiguity | 20% | 100 if PASS, 0 if UNCLEAR |
| Module Mapping | 10% | Use confidence from Step 7 |

**Confidence = weighted sum**

### Decision

```
IF confidence >= confidence_threshold:
  Log: "[REFINE:8] Request refinement complete. Confidence: {confidence}%"
  CONTINUE to Step 11 (Persist and Return Results)

ELSE:
  Log: "[REFINE:8] Request needs clarification. Confidence: {confidence}%"
  CONTINUE to Step 9
```

**Log**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[REFINE:8] (pm-workflow:phase-2-refine) Confidence: {confidence}%. Threshold: {confidence_threshold}%. Issues: {issue_summary}"
```

---

## Step 9: Clarify with User

For each issue found in Steps 6-7, formulate a clarification question.

### Question Formulation

**From Correctness issues**: "Is {X} the correct {technology/API/pattern}?"
**From Completeness issues**: "What should happen when {missing scenario}?"
**From Consistency issues**: "You mentioned both {A} and {B} which conflict. Which takes priority?"
**From Ambiguity issues**: "When you say {ambiguous term}, do you mean {interpretation A} or {interpretation B}?"
**From Module Mapping issues**: "Should this change affect {module A}, {module B}, or both?"

### Ask User

Use AskUserQuestion with specific options derived from the analysis:

```
AskUserQuestion:
  questions:
    - question: "{formulated question based on issue}"
      header: "{dimension}" # e.g., "Scope", "Behavior", "Priority"
      options:
        - label: "{option 1}"
          description: "{what this option means for implementation}"
        - label: "{option 2}"
          description: "{what this option means for implementation}"
      multiSelect: false
```

**Guidelines**:
- Ask at most 4 questions per iteration (AskUserQuestion limit)
- Prioritize: Correctness > Consistency > Completeness > Ambiguity > Duplication
- Provide concrete examples from the codebase when possible

---

## Step 10: Update Request

After receiving user answers, update request.md with clarifications.

### Record Clarifications

**EXECUTE**:
```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents \
  request clarify \
  --plan-id {plan_id} \
  --clarifications "{formatted Q&A pairs}"
```

**Format for clarifications**:
```
Q: {question asked}
A: {user's answer}
```

### Synthesize Clarified Request

If significant clarifications were made, synthesize an updated request:

**EXECUTE**:
```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents \
  request clarify \
  --plan-id {plan_id} \
  --clarified-request "{synthesized request incorporating clarifications}"
```

**Synthesis pattern**:
```
{Original intent restated clearly}

**Scope:**
- {Specific inclusion from clarification}
- {Specific inclusion from clarification}

**Exclusions:**
- {Specific exclusion from clarification}

**Constraints:**
- {Constraint from clarification}
```

### Log and Loop

**Log**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[REFINE:10] (pm-workflow:phase-2-refine) Updated request with {N} clarifications. Returning to analysis."
```

Go back to Step 6.

---

## Step 11: Persist and Return Results

When confidence reaches threshold, persist results to sinks and return minimal status.

### Persist Module Mapping to Work Directory

**Persist module mapping** (intermediate analysis state, not a reference):
```bash
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files write \
  --plan-id {plan_id} \
  --file work/module_mapping.toon \
  --content "# Module Mapping

{module_mapping_toon_content}
"
```

**Note**: Track, scope, and compatibility are NOT persisted to references.json:
- **Track/scope**: Already logged to decision.log (Step 7, Step 11)
- **Compatibility**: Read directly from marshal.json by consumers

### Log Decisions (with duplicate guard)

**Note**: Track decision was already logged in Step 7. Only log scope and domains here if this is the first successful completion (iteration_count == 1 or first time reaching Step 11).

**Log to decision.log** (scope decision - only on first completion):
```bash
# Only log if not already logged (check iteration_count)
IF iteration_count == 1:
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
    decision {plan_id} INFO "(pm-workflow:phase-2-refine) Scope: {scope_estimate} - Modules: {module_count}, Files: {file_estimate}"

  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
    decision {plan_id} INFO "(pm-workflow:phase-2-refine) Domains: {domains}"
```

**Log to work.log** (completion status):
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[REFINE:11] (pm-workflow:phase-2-refine) Complete. Confidence: {confidence}%. Track: {track}. Iterations: {iteration_count}"
```

### Return Output with Decisions

Return status with decision values - track, scope, and compatibility are included in output for consumers:

```toon
status: success
plan_id: {plan_id}
confidence: {achieved_confidence}
track: {simple|complex}
track_reasoning: {track_reasoning}
scope_estimate: {scope_estimate}
compatibility: {compatibility}
compatibility_description: {compatibility_description}
domains: [{detected domains}]
qgate_pending_count: {0 if no findings}
```

**Data Location Reference**:
- Track/scope decisions: `decision.log` filtered by `(pm-workflow:phase-2-refine)`
- Module mapping: `work/module_mapping.toon`
- Compatibility: marshal.json (phase-2-refine config)
- Clarifications: `request.md` → `clarifications`, `clarified_request`

This output feeds into the next phase (phase-3-outline).

### Q-Gate Verification Checks

**Purpose**: Verify refine output meets quality standards before transitioning.

After persisting results, run lightweight verification:

1. **Module Mapping Completeness**: Every requirement maps to >= 1 module? Every module exists in architecture?
2. **Track Selection Consistency**: Track matches scope? (`codebase_wide` scope but `simple` track → flag)
3. **Scope Realism**: `single_file` but multiple modules → flag; `codebase_wide` but only 1 module → flag
4. **Confidence Justification**: All dimensions scored 100% → suspicious → flag

For each issue found:

```bash
python3 .plan/execute-script.py pm-workflow:manage-findings:manage-findings \
  qgate add {plan_id} --phase 2-refine --source qgate \
  --type triage --title "{check}: {issue_title}" \
  --detail "{detailed_reason}"
```

**Log Q-Gate Result**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(pm-workflow:phase-2-refine:qgate) Verification: {passed_count} passed, {flagged_count} flagged"
```

Add to return output:
```toon
qgate_pending_count: {count}
```

If `qgate_pending_count > 0`, the orchestrator (planning.md) decides whether to re-enter the phase or present findings to the user.

---

## Step 12: Transition Phase

The phase transitions from refine → outline after confidence reaches the threshold:

```bash
python3 .plan/execute-script.py pm-workflow:plan-marshall:manage-lifecycle transition \
  --plan-id {plan_id} \
  --completed 2-refine
```

**After successful transition**, log phase completion:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[STATUS] (pm-workflow:phase-2-refine) Refine phase complete - confidence: {confidence}%, track: {track}"
```

---

## Error Handling

| Error | Action |
|-------|--------|
| Architecture not found | Return `{status: error, message: "Run /marshall-steward first"}` and abort |
| Compatibility not configured | Return `{status: error, message: "compatibility not configured. Run /marshall-steward first"}` and abort |
| Request not found | Return `{status: error, message: "Request document missing"}` |
| Max iterations reached (5) | Return with current confidence, flag for manual review |

---

## Related Documents

- [workflow-overview.md](references/workflow-overview.md) - Visual workflow diagrams and data flow

---

## Integration

**Invoked by**: `pm-workflow:request-refine-agent` (thin agent wrapper)

**Script Notations** (use EXACTLY as shown):
- `plan-marshall:analyze-project-architecture:architecture` - Architecture queries
- `pm-workflow:manage-plan-documents:manage-plan-documents` - Request operations
- `pm-workflow:manage-references:manage-references` - References persistence (track, scope, module_mapping, compatibility)
- `pm-workflow:manage-findings:manage-findings` - Q-Gate findings (qgate add/query/resolve)
- `plan-marshall:manage-logging:manage-log` - Work and decision logging
- `plan-marshall:manage-plan-marshall-config:plan-marshall-config` - Project config (threshold, compatibility)
- `pm-workflow:plan-marshall:manage-lifecycle` - Phase transition management

**Persistence Locations**:
- `work/module_mapping.toon`: Module mapping analysis state
- `decision.log`: Track/scope decisions, config reads, domain detection
- `work.log`: Workflow progress (REFINE:N entries)
- `request.md`: clarifications, clarified_request

**Consumed By**:
- `pm-workflow:phase-3-outline` skill (receives track/scope/compatibility in return output; reads module_mapping from work/)
