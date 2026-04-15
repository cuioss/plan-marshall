# Phase 2: Refine — Detailed Workflow Steps

Detailed step-by-step procedures for the phase-2-refine workflow. For overview and integration context, see [SKILL.md](../SKILL.md).

---

## Step 1: Check for Unresolved Q-Gate Findings

**Purpose**: On re-entry (after Q-Gate or user review flagged issues), address unresolved findings before re-running analysis.

### Query Unresolved Findings

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate query --plan-id {plan_id} --phase 2-refine --resolution pending
```

### Address Each Finding

If unresolved findings exist (filtered_count > 0):

For each pending finding:
1. Analyze the finding in context of current request and architecture
2. Address it (revise analysis, re-evaluate scope, etc.)
3. Resolve:
```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate resolve --plan-id {plan_id} --hash-id {hash_id} --resolution taken_into_account --phase 2-refine \
  --detail "{what was done to address this finding}"
```
4. Log resolution:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-2-refine:qgate) Finding {hash_id} [{source}]: taken_into_account — {resolution_detail}"
```

Then continue with normal Steps 4..14 (phase re-runs with corrections applied).

If no unresolved findings: Continue with normal Steps 4..14 (first entry).

---

## Step 2: Log Phase Start

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-2-refine) Starting refine phase"
```

---

## Step 3: Recipe Shortcut

**Purpose**: Recipe-sourced plans skip quality analysis and iterative refinement. They only need scope selection.

### Check for Recipe Source

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --get \
  --field plan_source
```

**If `plan_source == recipe`**:

1. Force `track = complex` (recipes always need codebase discovery):
```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --set \
  --field track \
  --value complex
```

2. Set confidence = 100 immediately:
```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --set \
  --field confidence \
  --value 100
```

3. Log decision:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-2-refine) Recipe plan — skipping quality analysis, setting confidence=100, track=complex"
```

4. **Skip Steps 4-14**. Transition phase and return.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status transition \
  --plan-id {plan_id} \
  --completed 2-refine
```

Log phase completion:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-2-refine) Recipe plan — refine phase complete (skipped quality analysis)"
```

Add visual separator:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  separator --plan-id {plan_id} --type work
```

Return success. Phase 3 will handle recipe-specific outline creation.

**If `plan_source != recipe` or field not found**: Continue with normal Steps 4..14.

---

## Step 4: Load Confidence Threshold

Read the confidence threshold from project configuration.

**EXECUTE**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-2-refine get --field confidence_threshold --trace-plan-id {plan_id}
```

**Default**: If not configured or field not found, use `95` (95% confidence required).

**Log**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[REFINE:2] (plan-marshall:phase-2-refine) Using confidence threshold: {confidence_threshold}%"
```

Store as `confidence_threshold` for use in Step 10.

---

## Step 5: Load Compatibility Strategy

Read the compatibility approach from project configuration and persist to references.json in Step 11.

**EXECUTE**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
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
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-2-refine) Config: compatibility={compatibility}"
```

Store as `compatibility` and `compatibility_description` (the long description from the table above) for use in Step 13 return output.

---

## Step 6: Load Architecture Context

Query project architecture BEFORE any analysis. Architecture data is pre-computed and compact (~500 tokens).

**EXECUTE**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture info \
  --trace-plan-id {plan_id}
```

Output format: `plan-marshall:manage-architecture/standards/client-api.md`

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

**Store as** `arch_context` for use in Steps 8-9.

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
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[REFINE:4] (plan-marshall:phase-2-refine) Loaded architecture: {project_name} ({module_count} modules)"
```

---

## Step 7: Load Request

Load the request document.

**EXECUTE**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id}
```

Output format: `plan-marshall:manage-plan-documents/documents/request.toon`

**Extract**:
- `title`: Request title
- `description`: Full request text
- `clarifications`: Any existing clarifications (from prior iterations)
- `clarified_request`: Synthesized request (if exists from prior iterations)

**Log**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[REFINE:5] (plan-marshall:phase-2-refine) Loaded request: {title}"
```

---

## Step 8: Analyze Request Quality

Evaluate the request against five quality dimensions, using `arch_context` from Step 6 wherever applicable.

- **Correctness** — Are technology, module, API, and pattern references valid against `arch_context.technologies`, `arch_context.modules[].name`, and `arch_context.project_description`? Are stated constraints achievable (not mutually exclusive)? Flag as `CORRECTNESS: ISSUE` with the mismatched evidence and the architecture reference that was checked.
- **Completeness** — Is scope clear (in and out), are acceptance criteria inferrable, are testing expectations stated, are prerequisite changes/dependencies mentioned? Flag gaps as `COMPLETENESS: MISSING`.
- **Consistency** — Do requirements contradict each other or combine conflicting technology choices? Do all parts work toward the same goal? Flag conflicts as `CONSISTENCY: CONFLICT`.
- **Non-duplication** — Is the same ask repeated or are requirements overlapping? Flag as `DUPLICATION: REDUNDANT` with a consolidation recommendation.
- **Ambiguity** — Does each requirement have exactly one valid interpretation? Check terminology, quantifiers ("all X" vs "some X"), measurable criteria, boundary clarity, and — critically — the analysis intent when the request uses verbs like "analyze", "investigate", or "review" (report-only vs report-plus-fix). Flag as `AMBIGUITY: UNCLEAR` with each alternative interpretation enumerated.

---

## Step 9: Analyze Request in Architecture Context

With `arch_context` from Step 6, analyze how the request maps to the codebase.

### Module Mapping

Identify candidate modules for each requirement using `arch_context.modules[].name` (direct name mentions) and `arch_context.modules[].purpose` (functionality matches); also capture implicit module dependencies. When confidence is below 70 %, query detailed module info:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture module \
  --name {candidate_module} --trace-plan-id {plan_id}
```

The response exposes `responsibility`, `key_packages`, `key_dependencies`, and `internal_dependencies`. For cross-cutting changes, also run `architecture graph` to understand the dependency flow between candidate modules. Query detailed info only when the request is not already a direct module-name match.

Emit a `MODULE_MAPPING: {CLEAR|NEEDS_CLARIFICATION}` finding containing the requirement text, candidate modules, confidence, the rationale, and whether a detailed query was required.

### Feasibility Check

Validate that the request respects module boundaries (`arch_context.modules[].purpose`), follows dependency direction (`architecture graph` output), aligns with existing extension points (`internal_dependencies`), and fits the project technologies (`arch_context.technologies`). Flag concerns such as runtime-context changes inside a library module, reverse dependency flows, or missing framework features as `FEASIBILITY: CONCERN` with the architectural constraint that was violated.

### Scope Size Estimation

Classify the scope as `single_file` (one file), `single_module` (<5 files in one module), `few_files` (1-2 modules with 5-15 files), `multi_module` (3+ modules or 15+ files), or `codebase_wide` (cross-cutting or "all X" patterns). Emit `SCOPE_ESTIMATE: {class}` with modules affected, estimated file count, and rationale.

### Track Selection

**Question**: Does this request need complex discovery or can targets be determined directly?

**Track Selection Logic**:

**CRITICAL**: Complex Track triggers are hard gates — if ANY trigger fires, the track MUST be complex. Do NOT override with subjective reasoning. Evaluate each trigger mechanically. T4 has an escape hatch for cases where discovery has already been completed by phase-2-refine.

```
Step A — Check Complex Track triggers (hard gates, OR logic):
  [T1] scope_estimate is multi_module or codebase_wide
  [T2] Request contains scope words (see list below)
  [T3] module_mapping uses patterns/globs instead of explicit file paths
  [T4] Domain requires discovery (see list below)
       (This trigger is skipped if the T4 Escape Hatch conditions are met. See details below.)

  → If ANY of T1-T4 is true (after escape hatch) → track = complex (STOP, do not evaluate Simple)

Step B — Only if ALL of T1-T4 are false, check Simple Track:
  [S1] scope_estimate is single_file, single_module, or few_files
  [S2] module_mapping explicitly specifies target file(s) by full path
  [S3] Request is localized (add, create, implement specific thing)

  → If ALL of S1-S3 are true → track = simple
  → Otherwise → track = complex
```

**Scope Words [T2]**:
Scan request text for: `all`, `every`, `everywhere`, `across`, `migrate`, `update all`, `refactor`, `replace all`

**Domain Discovery Requirements [T4]**:
These domains have no standard structure and always need discovery:
- `plan-marshall-plugin-dev` (marketplace plugins)
- `documentation` (AsciiDoc, ADR locations vary)
- `requirements` (specs can be anywhere)

**T4 Escape Hatch**:
T4 is skipped (does not fire) when BOTH conditions are true:
1. `module_mapping` contains only explicit file paths (no patterns, globs, or approximate counts)
2. `scope_estimate` is `single_file` or `single_module`

When the escape hatch applies, phase-2-refine has already identified the exact targets — the codebase discovery that T4 mandates would be redundant. The escape hatch does NOT apply when T1, T2, or T3 have already fired (those are evaluated first).

**Module mapping explicitness [T3]**:
- Explicit: `affected_files: [path/to/file1.md, path/to/file2.md]` → does NOT trigger T3
- Broad: `file_pattern: {agents,commands}/*.md` or `agents: ~13 files` → TRIGGERS T3

**Finding format**:
```
TRACK_SELECTION: {simple|complex}
  - [T1] Scope multi_module/codebase_wide: {yes/no}
  - [T2] Scope words found: {yes/no - which words}
  - [T3] Module mapping broad/patterns: {yes/no}
  - [T4] Domain requires discovery: {yes/no}
  - [T4 escape hatch] Explicit paths + narrow scope: {yes/no - skipped T4 if yes}
  - Triggers fired: {T1,T2,T3,T4 or none}
  - Track: {complex if any trigger | simple if none}
```

**Log track decision** (to decision.log):
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-2-refine) Track: {track} - {reasoning}"
```

---

## Step 10: Evaluate Confidence

Aggregate findings from Steps 8-9 into confidence score.

If confidence >= threshold → go to Step 13. Otherwise continue.

### Confidence Calculation

| Dimension | Weight | Score |
|-----------|--------|-------|
| Correctness | 20% | 100 if PASS, 0 if ISSUE |
| Completeness | 20% | 100 if PASS, 50 if minor missing, 0 if major missing |
| Consistency | 20% | 100 if PASS, 0 if CONFLICT |
| Non-Duplication | 10% | 100 if PASS, 80 if REDUNDANT |
| Ambiguity | 20% | 100 if PASS, 0 if UNCLEAR |
| Module Mapping | 10% | Use confidence from Step 9 |

**Confidence = weighted sum**

### Decision

```
IF confidence >= confidence_threshold:
  Log: "[REFINE:8] Request refinement complete. Confidence: {confidence}%"
  CONTINUE to Step 13 (Persist and Return Results)

ELSE:
  Log: "[REFINE:8] Request needs clarification. Confidence: {confidence}%"
  CONTINUE to Step 11
```

**Log**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[REFINE:8] (plan-marshall:phase-2-refine) Confidence: {confidence}%. Threshold: {confidence_threshold}%. Issues: {issue_summary}"
```

---

## Step 11: Clarify with User

For each issue found in Steps 8-9, formulate a clarification question mapped to its dimension:

- **Correctness**: "Is {X} the correct {technology/API/pattern}?"
- **Completeness**: "What should happen when {missing scenario}?"
- **Consistency**: "You mentioned both {A} and {B} which conflict. Which takes priority?"
- **Ambiguity**: "When you say {ambiguous term}, do you mean {interpretation A} or {interpretation B}?"
- **Analysis intent**: "Your request uses 'analyze'. Is the expected outcome a findings-only report, or analysis plus implementation of fixes?"
- **Module mapping**: "Should this change affect {module A}, {module B}, or both?"

Ask the user via `AskUserQuestion` with explicit options that describe the implementation consequence of each choice. Ask at most 4 questions per iteration (AskUserQuestion limit), prioritize by Correctness > Consistency > Completeness > Ambiguity > Duplication, and provide concrete codebase examples when possible.

---

## Step 12: Update Request

After receiving user answers, update request.md using the three-step path-allocate
pattern. The script allocates the canonical artifact path, the main context edits
the file directly with its native Edit/Write tools, and a second subcommand records
the clarification transition. No multi-line content crosses the shell boundary.

### Step 12a: Allocate Canonical Path

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request path --plan-id {plan_id}
```

The returned `path` field is the absolute location of `request.md`. Pass it to
the Edit/Write tools in Step 12b — never hand-craft a path under `.plan/`.

### Step 12b: Edit request.md Directly

Use the Edit/Write tools to append a `## Clarifications` section and, if
significant, a `## Clarified Request` section to the file returned by
`request path`. Format:

```
## Clarifications

Q: {question asked}
A: {user's answer}

## Clarified Request

{Original intent restated clearly}

**Scope:**
- {Specific inclusion from clarification}
- {Specific inclusion from clarification}

**Exclusions:**
- {Specific exclusion from clarification}

**Constraints:**
- {Constraint from clarification}
```

No shell marshalling — the Edit tool writes the exact markdown you intend, free
of shell-escape concerns.

### Step 12c: Record the Clarification Transition

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request mark-clarified --plan-id {plan_id}
```

This validates that the Clarified Request section is present and records the
transition in the script's response. Returns `status: error, error: not_clarified`
if Step 12b did not add the section — a hard signal that the direct edit was
skipped or incomplete.

**Synthesis pattern** (for the Clarified Request section you write in 12b):
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
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[REFINE:10] (plan-marshall:phase-2-refine) Updated request with {N} clarifications. Returning to analysis."
```

Go back to Step 8.

---

## Step 13: Persist and Return Results

When confidence reaches threshold, persist results to sinks and return minimal status.

### Persist Module Mapping to Work Directory

**Persist module mapping** (intermediate analysis state, not a reference):
```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files write \
  --plan-id {plan_id} \
  --file work/module_mapping.toon \
  --content "# Module Mapping

{module_mapping_toon_content}
"
```

**Note**: Track, scope, and compatibility are NOT persisted to references.json:
- **Track/scope**: Already logged to decision.log (Step 9, Step 13)
- **Compatibility**: Read directly from marshal.json by consumers

### Log Decisions (with duplicate guard)

**Note**: Track decision was already logged in Step 9. Only log scope and domains here if this is the first successful completion (iteration_count == 1 or first time reaching Step 13).

**Log to decision.log** (scope decision - only on first completion):
```bash
# Only log if not already logged (check iteration_count)
IF iteration_count == 1:
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-2-refine) Scope: {scope_estimate} - Modules: {module_count}, Files: {file_estimate}"

  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-2-refine) Domains: {domains}"
```

**Log to work.log** (completion status):
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[REFINE:11] (plan-marshall:phase-2-refine) Complete. Confidence: {confidence}%. Track: {track}. Iterations: {iteration_count}"
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
- Track/scope decisions: `decision.log` filtered by `(plan-marshall:phase-2-refine)`
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
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase 2-refine --source qgate \
  --type triage --title "{check}: {issue_title}" \
  --detail "{detailed_reason}"
```

**Log Q-Gate Result**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-2-refine:qgate) Verification: {passed_count} passed, {flagged_count} flagged"
```

Add to return output:
```toon
qgate_pending_count: {count}
```

If `qgate_pending_count > 0`, the orchestrator (planning.md) decides whether to re-enter the phase or present findings to the user.

---

## Step 14: Transition Phase

The phase transitions from refine → outline after confidence reaches the threshold:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status transition \
  --plan-id {plan_id} \
  --completed 2-refine
```

**After successful transition**, log phase completion:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-2-refine) Refine phase complete - confidence: {confidence}%, track: {track}"
```

**Add visual separator** after END log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  separator --plan-id {plan_id} --type work
```
