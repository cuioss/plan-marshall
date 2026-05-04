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

If no unresolved findings: Continue with normal Steps 3b..14 (first entry).

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

**If `plan_source != recipe` or field not found**: Continue with normal Steps 3b..14.

---

## Step 3b: Source Premise Verification

**Purpose**: Verify that code references in the request narrative are still valid against the current codebase. Catches stale or invalid premises before quality analysis begins.

**Trigger**: This step activates when the request narrative (from Step 7, or from prior context on first entry) contains verifiable code references -- file paths, flag/option names, API references, or specific behavior descriptions tied to identifiable code. If no verifiable references are present, skip to Step 4.

For the complete claim extraction rules, verification procedure, and result handling, see [source-premise-verification.md](source-premise-verification.md).

### Execute Verification

1. Scan the request `description` and `clarified_request` for verifiable claims (at most 5, prioritized by load-bearing impact)
2. For each claim, probe the architecture inventory first (`architecture files --module X`, `architecture which-module --path P`, `architecture find --pattern P`) to confirm the claimed file/module/symbol exists. Only fall back to a targeted shell-tool call (`Glob`, `Grep`, or `Read`) when narrowing to sub-module components, scanning content inside an already-known file, or when the architecture verb returns elision.
3. Classify each claim as Valid, Stale, Invalid, or Inconclusive

### Handle Results

**If all claims are valid**: Log and continue to Step 4.

**If any claim is stale or invalid**: Emit a `CORRECTNESS: ISSUE` finding per invalid claim. These findings feed into Step 8 (Analyze Request Quality) under the Correctness dimension and impact the confidence score in Step 10.

### Log Verification

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[REFINE:3b] (plan-marshall:phase-2-refine) Source premise verification: {N} claims checked, {M} valid, {K} invalid"
```

When claims are invalid, also log to decision.log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level WARNING --message "(plan-marshall:phase-2-refine) Invalid premise: {claim_summary} — actual: {evidence_summary}"
```

---

## Step 3c: Proposed-Fix Verification

**Purpose**: Challenge whether a proposed fix actually solves the documented symptom. Source premise verification (Step 3b) confirms that claims about existing code are accurate; Step 3c confirms that the proposed change is **sufficient** to address the symptom. Runs after Step 3b and before confidence aggregation.

**Trigger**: Activates via **semantic LLM judgment** when the request narrative proposes a specific code change — concrete command strings, regex substitutions, function bodies, patch snippets, or config keys with new values. Source-agnostic (lesson, issue, PR review, free-form). Do **not** gate activation on header tokens like `## Proposed fix` — judge on semantic content. If the narrative only describes a symptom without proposing a change, skip to Step 4.

For the complete extraction rules, probe construction, and worked example, see [proposed-fix-verification.md](proposed-fix-verification.md).

### Execute Verification

1. Extract up to 3 proposed fixes from the request, prioritizing load-bearing changes (the plan's intent depends on them succeeding)
2. For each fix, construct a synthetic probe:
   - Re-read the symptom and enumerate triggering inputs
   - Construct a concrete scenario that reflects those inputs
   - Reason about the fix's command/code semantics against the scenario — do not execute code
3. Classify each probe as Valid, Insufficient, or Inconclusive

### Handle Results

**If all probes are valid**: Log and continue to Step 4.

**If any probe is insufficient**: Emit a `CORRECTNESS: ISSUE — Proposed fix incomplete` finding per insufficient fix. These findings feed into Step 8 (Analyze Request Quality) under the same Correctness dimension as Step 3b (20% weight, shared) and impact the confidence score in Step 10.

**Finding format**:

```
CORRECTNESS: ISSUE — Proposed fix incomplete
  Fix: "{fix_description}"
  Mechanism: {fix_mechanism}
  Scenario: {concrete scenario from probe}
  Gap: {what the probe showed is missing}
  Impact: {how this affects the plan's intent}
```

### Example Probe

Request proposes: *change `git diff --name-only {base}...HEAD` to `git diff --name-only {base}` to capture working-tree changes*.

Probe: construct a working tree with one modified tracked file AND one untracked new file. Reason about `git diff --name-only {base}`: it reports only modifications to tracked files; untracked files are invisible. Phase-5-execute `Write` operations create untracked files — the fix misses them.

Evaluation: **insufficient**. Emit finding, drop Correctness, route to Step 11 clarification.

### Log Verification

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[REFINE:3c] (plan-marshall:phase-2-refine) Proposed-fix verification: {N} fixes probed, {M} valid, {K} insufficient"
```

When probes are insufficient, also log to decision.log at WARNING:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level WARNING --message "(plan-marshall:phase-2-refine) Insufficient proposed fix: {fix_summary} — gap: {gap_summary}"
```

---

## Step 4: Load Confidence Threshold

Read the confidence threshold from project configuration.

**EXECUTE**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-2-refine get --field confidence_threshold --audit-plan-id {plan_id}
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
  plan phase-2-refine get --field compatibility --audit-plan-id {plan_id}
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
  --audit-plan-id {plan_id}
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
  --name {candidate_module} --audit-plan-id {plan_id}
```

The response exposes `responsibility`, `key_packages`, `key_dependencies`, and `internal_dependencies`. For cross-cutting changes, also run `architecture graph` to understand the dependency flow between candidate modules. Query detailed info only when the request is not already a direct module-name match.

Emit a `MODULE_MAPPING: {CLEAR|NEEDS_CLARIFICATION}` finding containing the requirement text, candidate modules, confidence, the rationale, and whether a detailed query was required.

### Feasibility Check

Validate that the request respects module boundaries (`arch_context.modules[].purpose`), follows dependency direction (`architecture graph` output), aligns with existing extension points (`internal_dependencies`), and fits the project technologies (`arch_context.technologies`). Flag concerns such as runtime-context changes inside a library module, reverse dependency flows, or missing framework features as `FEASIBILITY: CONCERN` with the architectural constraint that was violated.

### Scope Size Estimation

Derive `scope_estimate` from the `module_mapping` produced earlier in this step. The value is a single enum drawn from `none | surgical | single_module | multi_module | broad`. The same enum is consumed by `manage-solution-outline` (see `manage-solution-outline:standards/solution-outline-standard.md` § Solution Metadata) and by the surgical Q-Gate bypass in `phase-3-outline`, so the derivation rules below must be applied verbatim — no synonyms, no intermediate vocabulary.

#### Derivation Rules

Apply the rules in order; the first match wins. The "files" referenced below are the union of every concrete file path captured in `module_mapping` (patterns and globs are NOT counted as files for the count comparisons — they trigger the `broad` branch directly).

1. **`none`** — Pure analysis with no affected files. The request describes a report-only outcome (verbs like "analyze", "investigate", "review" with explicit report-only intent) AND `module_mapping` lists no concrete file paths.
2. **`surgical`** — All affected files map to a single module AND the count is ≤3 AND no file is in a public API surface (e.g., a published package's `__init__.py`, exported header, `index.{ts,js}`, or any file documented as a stable interface). When the request is ambiguous about public surface, default to `single_module`.
3. **`single_module`** — All affected files map to a single module AND the count is ≤10 (and the surgical rule did not match because count > 3 or a public API surface is touched).
4. **`multi_module`** — Affected files map to more than one module.
5. **`broad`** — Codebase-wide changes: `module_mapping` uses globs/patterns instead of explicit file paths, OR the affected file set is unbounded (e.g., "all *.py", sweeping refactor across the repo).

Emit a `SCOPE_ESTIMATE: {value}` finding containing `value` (one of the five enum strings), the modules affected, the concrete-file count (or `glob_only`/`unbounded`), and the rationale identifying which rule fired.

#### Persistence

Persist the derived value to `references.json` immediately so phase-3-outline and the manifest composer read a single source of truth:

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references \
  set --plan-id {plan_id} --field scope_estimate --value {scope_estimate}
```

The same value MUST appear in the Step 13 return TOON under the key `scope_estimate`. `phase-3-outline` MAY refine the value after deliverables crystalize (e.g., a Simple Track plan whose final deliverable list collapses to ≤3 files in one module is downgraded to `surgical`); when it does, it overwrites the field via the same `manage-references set` call.

### Track Selection

**Question**: Does this request need complex discovery or can targets be determined directly?

**Track Selection Logic**:

**CRITICAL**: Complex Track triggers are hard gates — if ANY trigger fires, the track MUST be complex. Do NOT override with subjective reasoning. Evaluate each trigger mechanically. T4 has an escape hatch for cases where discovery has already been completed by phase-2-refine.

```
Step A — Check Complex Track triggers (hard gates, OR logic):
  [T1] scope_estimate is multi_module or broad
  [T2] Request contains scope words (see list below)
  [T3] module_mapping uses patterns/globs instead of explicit file paths
  [T4] Domain requires discovery (see list below)
       (This trigger is skipped if the T4 Escape Hatch conditions are met. See details below.)

  → If ANY of T1-T4 is true (after escape hatch) → track = complex (STOP, do not evaluate Simple)

Step B — Only if ALL of T1-T4 are false, check Simple Track:
  [S1] scope_estimate is none, surgical, or single_module
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
2. `scope_estimate` is `none`, `surgical`, or `single_module`

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

### Persist scope_estimate to references.json

Persist the `scope_estimate` value derived in Step 9 so phase-3-outline, the manifest composer, and the surgical Q-Gate bypass read a single source of truth:

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references \
  set --plan-id {plan_id} --field scope_estimate --value {scope_estimate}
```

The accepted enum values are `none | surgical | single_module | multi_module | broad` — the same enum documented in `manage-solution-outline:standards/solution-outline-standard.md`. The value is also returned in the Step 13 TOON below.

**Note**: Track and compatibility are NOT persisted to references.json:
- **Track**: Already logged to decision.log (Step 9, Step 13)
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

### Step 13.5: Spawn q-gate-validation-agent — lesson-derived plans only

**Purpose**: Run the `narrative-vs-code-validator` (q-gate-validation-agent.md § 2.14) over the source lesson narrative so concrete code claims (file paths, profile→target mappings, function names, argument shapes, behavioral assertions) are reconciled against current code state at refine time. Catches silent baseline drift between lesson capture and plan execution before the outline locks intent.

**Activation guard**: Runs only when `status.json` reports `plan_source: lesson`. For free-form, issue-derived, or recipe-derived plans, skip this step entirely.

**Read activation guard**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
  --plan-id {plan_id} --get --field plan_source
```

If `status: not_found` or `value != lesson`, skip Step 13.5 — log nothing and continue to Step 14.

**Dispatch the validator agent** (lesson-derived plans only):

```
Task: plan-marshall:q-gate-validation-agent
  Input:
    plan_id: {plan_id}
    activation_context: 2-refine
    validators: [narrative-vs-code-validator]
```

The agent reads the source lesson body from the plan directory (`lesson-{id}.md` archived alongside `request.md`), extracts concrete code claims, probes the current code state for each, and emits a finding per `stale` or `invalid` claim using `--source qgate-narrative-vs-code`. See q-gate-validation-agent.md § 2.14 for the canonical detection logic and finding emission template.

**Aggregate the findings** — read pending findings to update the running count returned in Step 13:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate query --plan-id {plan_id} --phase 2-refine --resolution pending
```

Parse `filtered_count` from the output and ADD it to the `qgate_pending_count` already aggregated in the inline-checks step above. Both finding sources (inline lightweight checks and the validator agent) flow into the same `qgate_pending_count` aggregate that is returned in the phase TOON, so the orchestrator's existing 3-iteration auto-loop handles re-entry uniformly.

**Log dispatch outcome**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-2-refine:qgate) Spawned q-gate-validation-agent for narrative-vs-code-validator (lesson plan); pending findings now {qgate_pending_count}"
```

This step runs AFTER the inline lightweight Q-Gate checks (above) and BEFORE Step 14 (Transition Phase). The placement is load-bearing: inline checks first means cheap structural findings are recorded before the more expensive narrative cross-check; validator second ensures lesson-driven findings can re-enter refine alongside the inline ones.

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
