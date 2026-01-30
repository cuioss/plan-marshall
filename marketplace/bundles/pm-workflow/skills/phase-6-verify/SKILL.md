---
name: phase-6-verify
description: Verification pipeline for quality checks before finalization
user-invocable: false
allowed-tools: Read, Bash, Glob, Skill, Task
---

# Phase Verify Skill

**Role**: Verify phase skill. Runs quality checks, build verification, and technical validation before finalization. Creates fix tasks if issues are found and loops back to execute phase.

**Key Pattern**: Verification pipeline with finding→task loop. Verification behavior determined by marshal.json phase config and domain extensions.

## When to Activate This Skill

Activate when:
- Execute phase has completed (all tasks done)
- Plan is in `6-verify` phase
- Quality verification required before finalization

---

## 7-Phase Model

```
1-init → 2-refine → 3-outline → 4-plan → 5-execute → 6-verify → 7-finalize
                                                       ↑ YOU ARE HERE
```

---

## Configuration Source

Verify configuration comes from two sources:

**Per-plan data** (from references.toon):
```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references get \
  --plan-id {plan_id} --field domains
```

**Project-level pipeline** (from marshal.json):
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-6-verify get --trace-plan-id {plan_id}
```

**Config Fields Used**:

| Source | Field | Description |
|--------|-------|-------------|
| references.toon | `domains` | Domains for this plan (java, documentation, etc.) |
| marshal.json | `max_iterations` | Maximum verify-execute-verify loops |
| marshal.json | `1_quality_check` | Whether to run quality gate |
| marshal.json | `2_build_verify` | Whether to run build verification |
| marshal.json | `domain_steps` | Per-domain agent verification steps |

---

## Operation: verify

**Input**: `plan_id`

### Step 0: Log Phase Start

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[STATUS] (pm-workflow:phase-6-verify) Starting verify phase"
```

### Step 1: Read Configuration

Read per-plan domains:
```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references get \
  --plan-id {plan_id} --field domains
```

Read project-level verify pipeline:
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-6-verify get --trace-plan-id {plan_id}
```

### Step 2: Check Iteration Counter

Read current verify iteration:

```bash
python3 .plan/execute-script.py pm-workflow:plan-marshall:manage-lifecycle read \
  --plan-id {plan_id}
```

Check `verify_iteration` field. If >= 5, fail with max iterations exceeded.

### Step 3: Load Domain Triage Extensions

For each domain in config:

```
Skill: pm-workflow:workflow-extension-api
  resolve {domain} triage
```

This loads domain-specific triage skills for handling findings.

### Step 4: Run Verification Pipeline

The default verification pipeline:

1. **Quality Check** - Lint, format, static analysis
2. **Build Verify** - Compile, test execution
3. **Technical Implementation** - Domain-specific checks
4. **Technical Test** - Test coverage, quality
5. **Doc Sync** - Documentation consistency (advisory)
6. **Formal Spec** - Specification drift check (advisory)

#### 4a: Quality Check

Run quality gate commands based on domain:

**Java**:
```bash
./pw quality-gate {module}
```

**JavaScript**:
```bash
npm run lint && npm run format:check
```

**Plugin**:
```
Skill: pm-plugin-development:plugin-doctor
```

#### 4b: Build Verify

Run build verification:

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references get \
  --plan-id {plan_id} --field build_system
```

Based on build_system:
- `maven` → `./pw verify {module}`
- `gradle` → `./gradlew check`
- `npm` → `npm test`

#### 4c: Technical Verification (Domain-Specific)

Invoke domain-specific verification agent if available:

**Java**:
```
Task: pm-dev-java:java-verify-agent
  Input: plan_id, target files from tasks
```

**JavaScript**:
```
Task: pm-dev-frontend:js-verify-agent (if exists)
```

#### 4d: Test Verification

Check test coverage meets threshold (if configured):

```bash
./pw coverage {module}
```

#### 4e: Doc Sync (Advisory)

Check for documentation drift:

```
Skill: pm-documents:ext-triage-docs
  Input: plan_id
```

Advisory only - logs findings but doesn't block.

#### 4f: Formal Spec Check (Advisory)

Check specification consistency:

```
Skill: pm-requirements:ext-triage-reqs
  Input: plan_id
```

Advisory only - logs findings but doesn't block.

### Step 5: Collect Findings

Aggregate findings from all verification steps:

```toon
findings[N]{id,source,rule,file,line,severity,message,auto_fixable}:
finding-001,quality_check,S1192,src/main/java/Example.java,42,major,String literal duplicated,true
finding-002,build_verify,compile,src/main/java/Other.java,15,blocker,Cannot find symbol,true
```

### Step 6: Triage Findings

For each finding, apply domain triage:

```
Skill: {domain}:ext-triage-{domain}
  Input: finding
  Output: decision (FIX, SUPPRESS, ACCEPT)
```

Decisions:
- **FIX** → Create fix task
- **SUPPRESS** → Add suppression annotation/comment
- **ACCEPT** → Log as accepted, continue

### Step 7: Create Fix Tasks (If Needed)

For each finding with decision=FIX:

```bash
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks add \
  --plan-id {plan_id} <<'EOF'
title: Fix {finding.rule}: {finding.message}
deliverable: 0
domain: {domain}
profile: implementation
type: FIX
origin: fix
skills:
  - {domain_skill}
steps:
  - {finding.file}
verification:
  commands:
    - {verification_command}
  criteria: Issue resolved
EOF
```

### Step 8: Loop or Continue

If fix tasks were created:

```bash
# Increment verify iteration and transition back to execute
python3 .plan/execute-script.py pm-workflow:plan-marshall:manage-lifecycle set-phase \
  --plan-id {plan_id} --phase 5-execute
```

Exit - plan-execute will run the fix tasks.

If no fix tasks (all passed or suppressed):

```bash
# Transition to finalize phase
python3 .plan/execute-script.py pm-workflow:plan-marshall:manage-lifecycle transition \
  --plan-id {plan_id} --completed 6-verify
```

Exit successfully.

### Step 9: Log Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[STATUS] (pm-workflow:phase-6-verify) Verify complete: {passed}/{total} checks, {fix_tasks} fix tasks"
```

---

## Output

**Success (No Fixes Needed)**:

```toon
status: success
plan_id: {plan_id}
iteration: {verify_iteration}

checks:
  quality_check: passed
  build_verify: passed
  technical_impl: passed
  technical_test: passed
  doc_sync: advisory_only
  formal_spec: advisory_only

findings_count: 0
fix_tasks_created: 0
next_phase: 7-finalize
```

**Loop Back (Fixes Needed)**:

```toon
status: loop_back
plan_id: {plan_id}
iteration: {verify_iteration}

checks:
  quality_check: passed
  build_verify: failed
  technical_impl: skipped
  technical_test: skipped

findings_count: 3
fix_tasks_created: 2
suppressed: 1
next_phase: 5-execute
```

**Error (Max Iterations)**:

```toon
status: error
plan_id: {plan_id}
iteration: 5
message: Maximum verify iterations (5) exceeded
remaining_findings: {count}
recovery: Manual intervention required
```

---

## Error Handling

On any error, **first log the error** to work-log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} ERROR "[ERROR] (pm-workflow:phase-6-verify) {step} failed - {error_type}: {error_context}"
```

---

## Iteration Limits

| Counter | Max | Description |
|---------|-----|-------------|
| `verify_iteration` | 5 | Max loops between verify→execute |

After max iterations, the skill fails with remaining findings listed for manual intervention.

---

## Standards (Load On-Demand)

### Verification Steps
```
Read standards/verification-steps.md
```
Contains: Step definitions, domain-specific checks, pass/fail criteria

### Triage Integration
```
Read standards/triage-integration.md
```
Contains: How to load domain-specific triage extensions, findings routing, decision flow

---

## Integration

### Phase Routing

This skill is invoked when plan is in `6-verify` phase:

```
pm-workflow:plan-marshall:manage-lifecycle route --phase 6-verify → pm-workflow:phase-6-verify
```

### Command Integration

- **/plan-marshall action=verify** - Invokes this skill
- **/plan-marshall** - Shows plans ready for verify

### Related Skills

- **phase-5-execute** - Previous phase (executes tasks)
- **phase-7-finalize** - Next phase (commit, PR)
- **manage-lifecycle** - Handles phase transitions
- **workflow-extension-api** - Domain extension resolution

### Domain Extensions

| Domain | Triage Extension |
|--------|------------------|
| java | pm-dev-java:ext-triage-java |
| javascript | pm-dev-frontend:ext-triage-js |
| plugin | pm-plugin-development:ext-triage-plugin |
| docs | pm-documents:ext-triage-docs |
| reqs | pm-requirements:ext-triage-reqs |
