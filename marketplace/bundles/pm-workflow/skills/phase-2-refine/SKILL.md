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
| `feedback` | string | No | User feedback from review (for revision iterations) |

**Feedback handling**: When `feedback` is provided, it represents user feedback from a previous outline review. This feedback:
- Takes priority in the analysis (addresses user's explicit concerns first)
- Is logged at workflow start
- Is incorporated into the clarified request

---

## Step 1: Load Confidence Threshold

Read the confidence threshold from project configuration.

**EXECUTE**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  get --key plan.defaults.refine_confidence_threshold
```

**Default**: If not configured, use `95` (95% confidence required).

**Log**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[REFINE:1] (pm-workflow:phase-2-refine) Using confidence threshold: {confidence_threshold}%"
```

Store as `confidence_threshold` for use in Step 6.

---

## Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    REQUEST REFINE LOOP                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: Load Confidence Threshold                              │
│      ↓                                                          │
│  Step 2: Load Architecture Context ──────────────────────┐      │
│      ↓                                   arch_context    │      │
│  Step 3: Load Request                         │          │      │
│      ↓                                        ↓          ↓      │
│  Step 4: Analyze Request Quality ←── technologies, modules      │
│      ↓                                        │          │      │
│  Step 5: Analyze in Architecture Context ←────┘──────────┘      │
│      ↓                    (module details on demand)            │
│  Step 6: Evaluate Confidence                                    │
│      │                                                          │
│      ├── confidence >= threshold → Step 9: Return Results       │
│      │                                                          │
│      └── confidence < threshold → Step 7: Clarify with User     │
│              ↓                                                  │
│          Step 8: Update Request                                 │
│              ↓                                                  │
│          (loop back to Step 4)                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

| Step | Input | Output | Stored As |
|------|-------|--------|-----------|
| Step 1 | marshal.json | threshold value | `confidence_threshold` |
| Step 2 | architecture info | project + modules + technologies | `arch_context` |
| Step 3 | request.md | title, description, clarifications | `request` |
| Step 4 | `request` + `arch_context` | quality findings | `quality_findings` |
| Step 5 | `request` + `arch_context` + detailed queries | mapping findings | `mapping_findings` |
| Step 6 | all findings | confidence score | decision |

---

## Step 2: Load Architecture Context

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

### 2.1 Extract Architecture Summary

From the `architecture info` output, extract and store:

| Field | Source | Use In |
|-------|--------|--------|
| `project_name` | `project.name` | Context for questions |
| `project_description` | `project.description` | Scope validation |
| `technologies` | `technologies[]` | Step 4.1 Correctness validation |
| `module_names` | `modules[].name` | Step 5.1 Module Mapping |
| `module_purposes` | `modules[].purpose` | Step 5.2 Feasibility Check |

**Store as** `arch_context` for use in Steps 4-5.

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

### 2.2 Log Completion

**Log**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[REFINE:2] (pm-workflow:phase-2-refine) Loaded architecture: {project_name} ({module_count} modules)"
```

**If feedback provided**, log it:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[REFINE:2] (pm-workflow:phase-2-refine) Processing with feedback: {feedback}"
```

---

## Step 3: Load Request

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
  work {plan_id} INFO "[REFINE:3] (pm-workflow:phase-2-refine) Loaded request: {title}"
```

---

## Step 4: Analyze Request Quality

Evaluate the request against five quality dimensions.

### 4.0 Feedback Analysis (if feedback provided)

**When `feedback` parameter is present**, categorize it to determine handling:

| Feedback Type | Example | Action |
|---------------|---------|--------|
| **Requirement gap** | "You missed that it also needs X" | Treat as Completeness issue → clarify with user |
| **Scope correction** | "Module Y shouldn't be affected" | Pass to outline creation |
| **Approach preference** | "Use pattern Z instead" | Pass to outline creation |

**Finding format**:
```
FEEDBACK_TYPE: {REQUIREMENT_GAP|SCOPE_CORRECTION|APPROACH_PREFERENCE}
  - Issue raised: {feedback summary}
  - Action: {clarify_request | pass_to_outline}
```

**Note**: Only REQUIREMENT_GAP feedback affects request analysis (surfaces as Completeness issue). Other feedback types are passed through to outline creation without blocking request confidence.

### 4.1 Correctness

**Check**: Are requirements technically valid? **Use `arch_context` from Step 2**.

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

### 4.2 Completeness

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

### 4.3 Consistency

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

### 4.4 Non-Duplication

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

### 4.5 Ambiguity

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

## Step 5: Analyze Request in Architecture Context

With `arch_context` from Step 2, analyze how the request maps to the codebase.

### 5.1 Module Mapping

**Question**: Which modules are affected by this request?

**Initial mapping** (use `arch_context.modules` from Step 2):

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

### 5.2 Feasibility Check

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

### 5.3 Scope Size Estimation

**Question**: What is the approximate scope?

| Size | Criteria |
|------|----------|
| Small | 1 module, < 5 files |
| Medium | 1-2 modules, 5-15 files |
| Large | 3+ modules, 15+ files |
| Needs decomposition | Cross-cutting, unclear boundaries |

**Finding format**:
```
SCOPE_ESTIMATE: {Small|Medium|Large|Needs decomposition}
  - Modules affected: {count}
  - Estimated files: {range}
  - Rationale: {brief explanation}
```

---

## Step 6: Evaluate Confidence

Aggregate findings from Steps 4-5 into confidence score.

### Confidence Calculation

**If feedback was provided** (revision iteration):

| Dimension | Weight | Score |
|-----------|--------|-------|
| Feedback addressed | 30% | 100 if CLEAR and addressed, 0 if unresolved |
| Correctness | 15% | 100 if PASS, 0 if ISSUE |
| Completeness | 15% | 100 if PASS, 50 if minor missing, 0 if major missing |
| Consistency | 15% | 100 if PASS, 0 if CONFLICT |
| Ambiguity | 15% | 100 if PASS, 0 if UNCLEAR |
| Module Mapping | 10% | Use confidence from Step 5.1 |

**If no feedback** (initial analysis):

| Dimension | Weight | Score |
|-----------|--------|-------|
| Correctness | 20% | 100 if PASS, 0 if ISSUE |
| Completeness | 20% | 100 if PASS, 50 if minor missing, 0 if major missing |
| Consistency | 20% | 100 if PASS, 0 if CONFLICT |
| Non-Duplication | 10% | 100 if PASS, 80 if REDUNDANT |
| Ambiguity | 20% | 100 if PASS, 0 if UNCLEAR |
| Module Mapping | 10% | Use confidence from Step 5.1 |

**Confidence = weighted sum**

### Decision

```
IF confidence >= confidence_threshold:
  Log: "[REFINE:6] Request refinement complete. Confidence: {confidence}%"
  CONTINUE to Step 9 (Return Results)

ELSE:
  Log: "[REFINE:6] Request needs clarification. Confidence: {confidence}%"
  CONTINUE to Step 7
```

**Log**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[REFINE:6] (pm-workflow:phase-2-refine) Confidence: {confidence}%. Threshold: {confidence_threshold}%. Issues: {issue_summary}"
```

---

## Step 7: Clarify with User

For each issue found in Steps 4-5, formulate a clarification question.

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

## Step 8: Update Request

After receiving user answers, update request.md with clarifications.

### 8.1 Record Clarifications

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

### 8.2 Synthesize Clarified Request

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

### 8.3 Log and Loop

**Log**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[REFINE:8] (pm-workflow:phase-2-refine) Updated request with {N} clarifications. Returning to analysis."
```

**Loop**: Return to Step 4 with updated request.

---

## Step 9: Return Results

When confidence reaches threshold, log completion and return results.

### 9.1 Log Completion

**Log**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[REFINE:9] (pm-workflow:phase-2-refine) Refinement complete. Confidence: {confidence}%. Iterations: {iteration_count}. Domains: [{domains}]"
```

### 9.2 Return Output

Return the following TOON structure:

```toon
status: success
confidence: {achieved_confidence}
threshold: {confidence_threshold}
iterations: {count}
domains: [{detected domains}]
module_mapping:
  - requirement: "{req1}"
    modules: [{module1}]
  - requirement: "{req2}"
    modules: [{module2}]
scope_estimate: {Small|Medium|Large}
outline_guidance: [{feedback items for outline creation, if any}]
```

This output feeds into the next phase (phase-3-outline).

**outline_guidance**: Contains SCOPE_CORRECTION and APPROACH_PREFERENCE feedback (from revision iterations) that should influence outline creation but didn't affect request confidence.

---

## Error Handling

| Error | Action |
|-------|--------|
| Architecture not found | Return `{status: error, message: "Run /marshall-steward first"}` and abort |
| Request not found | Return `{status: error, message: "Request document missing"}` |
| Max iterations reached (5) | Return with current confidence, flag for manual review |

---

## Integration

**Invoked by**: `pm-workflow:request-refine-agent` (thin agent wrapper)

**Script Notations** (use EXACTLY as shown):
- `plan-marshall:analyze-project-architecture:architecture` - Architecture queries
- `pm-workflow:manage-plan-documents:manage-plan-documents` - Request operations
- `plan-marshall:manage-logging:manage-log` - Work logging
- `plan-marshall:manage-plan-marshall-config:plan-marshall-config` - Project config (threshold)

**Consumed By**:
- `pm-workflow:phase-3-outline` skill (receives refined request)
