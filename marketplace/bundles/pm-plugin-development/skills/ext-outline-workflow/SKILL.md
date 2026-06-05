---
name: ext-outline-workflow
description: Shared workflow steps and verification knowledge for plugin development outline, loaded by phase-3-outline skill
user-invocable: false
implements: plan-marshall:extension-api/standards/ext-point-outline
---

# Plugin Development Outline Workflow

Shared workflow steps for plugin development outline, loaded by the `phase-3-outline` skill when the domain is `plan-marshall-plugin-dev`. Change-type-specific instructions are in `standards/change-types.md` (consolidated document with sections for each type: bug_fix, enhancement, feature, tech_debt).

## Step 1: Load Foundational Practices

```
Skill: plan-marshall:dev-agent-behavior-rules
```

## Context Loading

Read request, domains, and compatibility:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} \
  --section clarified_request

python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get \
  --plan-id {plan_id} --field domains

python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-2-refine get --field compatibility --audit-plan-id {plan_id}
```

Derive `compatibility_description` from the compatibility value.

Log context:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "({agent_name}) Context loaded: compatibility={compatibility}"
```

## Inventory Scan

Create work directory and run full inventory scan:

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files mkdir \
  --plan-id {plan_id} --dir work
# Output includes: path: /absolute/path/to/.plan/plans/{plan_id}/work
# Use the returned `path` value as {work_dir_path} below

python3 .plan/execute-script.py \
  pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --audit-plan-id {plan_id} \
  --resource-types {comma_separated_types} \
  --bundles {bundle_scope} \
  --include-tests \
  --full \
  --output {work_dir_path}/inventory_raw.toon
```

**Important**: `{work_dir_path}` is the `path` value returned by the `mkdir` command above. Do NOT hardcode the path.

**Important**: `--resource-types` takes a **comma-separated** string (e.g., `skills,agents,commands`). Do NOT use spaces between types.

Omit `--bundles` only if scanning all bundles.

Read and extract file paths:

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files read \
  --plan-id {plan_id} --file work/inventory_raw.toon --audit-plan-id {plan_id}
```

Path conventions:
- **Skills**: `{bundle_path}/skills/{skill_name}/SKILL.md`
- **Commands**: `{bundle_path}/commands/{command_name}.md`
- **Agents**: `{bundle_path}/agents/{agent_name}.md`
- **Tests**: Use `path` field from inventory directly

## Assessment Pattern

### Clear stale assessments

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings assessment \
  clear --plan-id {plan_id} --agent {agent_name}
```

### Log assessment per file

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings assessment \
  add --plan-id {plan_id} --file-path {file_path} --certainty {CERTAINTY} --confidence {CONFIDENCE} \
  --agent {agent_name} --detail "{reasoning}" --evidence "{evidence}"
```

Where:
- `CERTAINTY`: CERTAIN_INCLUDE, CERTAIN_EXCLUDE, or UNCERTAIN
- `CONFIDENCE`: 0-100

### Assessment Gate

**STOP** before proceeding. Verify assessments were persisted:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings assessment \
  list --plan-id {plan_id}
```

Gate checks:
1. `total_count` MUST be > 0 — if zero, report failure
2. Compare against inventory `total_resources`
3. If `total_count < total_resources`: STOP — "Assessment incomplete: {total_count}/{total_resources}"

Log gate result:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "({agent_name}) Assessment gate: {total_count} assessments written"
```

## Uncertainty Resolution

Query UNCERTAIN assessments and ask user:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings assessment \
  list --plan-id {plan_id} --certainty UNCERTAIN
```

Group by pattern and use AskUserQuestion. Log resolution:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "({agent_name}) Resolved {N} uncertainties: {decision}"
```

## Deliverable Validation

**MANDATORY** before writing solution_outline.md — verify EVERY deliverable has ALL 6 required sections (from solution-outline-standard.md), plus the conditional `**Design notes:**` section when the deliverable touches an existing skill:

| Section | Check |
|---------|-------|
| `**Metadata:**` with change_type, execution_mode, domain, module, depends | Present and valid. `execution_mode` must be one of: `automated`, `manual`, `mixed` (NOTE: `verification` is a valid change_type but NOT a valid execution_mode) |
| `**Design notes:**` *(conditional — required when the deliverable touches an existing skill)* | Required for any deliverable whose `**Affected files:**` list includes at least one `marketplace/bundles/{bundle}/skills/{skill}/**` path (including `standards/**/*.md`), on EITHER the Simple or Complex track. The block MUST name the target skill's design model (`script-deterministic`, `LLM-driven`, or `hybrid`) and a specific one-sentence rationale showing the implementation extends, not contradicts, that model — per [Step 9c: Read Target Skill Design Intent](../../../plan-marshall/skills/phase-3-outline/standards/outline-workflow-detail.md#step-9c-read-target-skill-design-intent). Emitting it here guarantees the domain-composed deliverable self-satisfies the §2.17 Architecture-Mismatch validator on the first validation pass. Omit only for deliverables that do not touch an existing skill (brand-new skill, docs-only outside a skill). |
| `**Profiles:**` | At least one profile listed |
| `**Affected files:**` | Explicit paths, no wildcards, no glob patterns. **Every path MUST exist on disk** (verify with Glob tool). Use paths from inventory scan — do NOT guess or construct paths from component names. |
| `**Change per file:**` | Entry for each affected file |
| `**Verification:**` | Both Command and Criteria present |
| `**Success Criteria:**` | At least one criterion |

If ANY required section is missing — or the conditional `**Design notes:**` section is missing on a deliverable that touches an existing skill — add it before proceeding.

## Audit Checklist for Structural-Rule Audits

When a deliverable audits a structural rule (e.g., chain-shape compliance sweep, write-to-tmp anti-pattern sweep, hard-coded build command sweep), the deliverable's "Change per file" or "Verification" block MUST enumerate ALL THREE shell-marshalling families — not only the one literally named in the source request or lesson:

1. **Chain-shape family** — `&&`, `;`, `&`, newline-joined commands, `VAR=val cmd` inline env-var assignment.
2. **Bash-write-impersonation family** — `echo >>`, `cat <<EOF > file`, `printf > file`, `python3 -c "open(p).write(...)"` one-liners.
3. **Argument-marshalling family** — `$(...)` substitution combined with heredocs, embedded markdown inside `-m`/`--content`/`--message` args, multi-line shell-quoted content in tool args.

A one-line note in the deliverable's "Change per file" or "Verification" block is sufficient. Example:

```markdown
**Change per file:** Sweep all three shell-marshalling families (chain-shape, bash-write-impersonation, argument-marshalling) and replace with the documented safe alternative.
```

This rule prevents the recurring failure mode where structural-rule sweeps catch only the family named in the source lesson and miss adjacent families that trip the same harness shapes.

## Human-Gated Harness-Config Classification

This is a domain-specific classification dimension for the `plan-marshall-plugin-dev` domain — it fires whenever a deliverable being authored touches the Claude Code harness-configuration surface, which requires a human action to take effect. It is **track-agnostic**: phase-3-outline's thin special-deliverable-class trigger (the "Human-gated harness-config deliverable class") fires on both the Simple Track (Step 7) and the Complex Track (Step 10) and routes here for the substance. Apply the predicate to every deliverable's `**Affected files:**` (or the writes its narrative describes), regardless of change type.

### Predicate

A deliverable is **human-gated** when its `Affected files` (or its narrative's described writes) match any of the concrete path / pattern rows below. Match on the path first, then — for the settings-file rows — on the named key being added or edited:

| Surface (concrete path / pattern) | Trigger key (within the path) | Why it is human-gated |
|-----------------------------------|-------------------------------|------------------------|
| `.claude/settings.json` | any write | Harness configuration the runtime reads at startup; a write does not take effect until the session is restarted / reloaded, and writing it during an unattended run trips the permission UI. |
| `.claude/settings.local.json` | any write | Per-machine harness override with the same startup-reload activation latency and permission characteristics as `settings.json`. |
| `.claude/settings.json` or `.claude/settings.local.json` | the `hooks` block (a `SessionStart` / `UserPromptSubmit` / `Stop` entry), OR a new hook script under `.claude/hooks/**` | Registering a lifecycle hook arms code the harness executes on its own schedule; the user must trust/activate the hook, and the registration write hits the same permission gate. |
| `.claude/settings.json` or `.claude/settings.local.json` | the `permissions.allow` / `permissions.deny` arrays | Widening or narrowing what the harness may run is a security-relevant action that requires an explicit human grant; an unattended task cannot self-approve it. |

The two activation characteristics that define the dimension are (1) the **permission-prompt** gate — an unattended task cannot satisfy the harness's permission UI when it writes these files — and (2) the **startup-reload activation latency** — the write has no effect until the session is restarted/reloaded, so an automated verification step in the same run cannot observe its effect.

### Required Action

When the predicate fires, the outline MUST **split the unattended marketplace work from the human-gated activation step**, OR explicitly annotate the confirmation-gated path on the single deliverable:

- **Split (preferred)**: the unattended deliverable authors the marketplace source that *defines* the hook / config / permission shape (the skill body, the hook script, the documented allow-list entry). A separate, explicitly human-gated activation step writes `.claude/settings.json` (or installs the hook, or grants the permission). Phase-5-execute runs the unattended deliverable to completion; the activation step is surfaced to the user rather than attempted by an automated task.
- **Annotate (single-deliverable alternative)**: when the work genuinely cannot be split, the deliverable carries a `**Human-gated activation:**` note naming the exact harness write the user must perform and stating that phase-5-execute will pause for confirmation at that point.

The failure mode this dimension prevents: an unattended phase-5-execute task that tries to write `.claude/settings.json` (or install a hook, or edit an allow-list) hits a permission wall it cannot satisfy, returns a verification failure, and loop-backs — burning iterations on a step that was never automatable. Classifying the surface as human-gated at outline time splits the automatable authoring from the non-automatable activation so the loop never stalls.

## Verification Commands

### Component Verification (Plugin-Doctor)

| Component Type | Scope | Parameter | Full Command |
|----------------|-------|-----------|--------------|
| Skills | `scope=skills` | `skill-name={name}` | `/pm-plugin-development:plugin-doctor scope=skills skill-name={name}` |
| Agents | `scope=agents` | `agent-name={name}` | `/pm-plugin-development:plugin-doctor scope=agents agent-name={name}` |
| Commands | `scope=commands` | `command-name={name}` | `/pm-plugin-development:plugin-doctor scope=commands command-name={name}` |
| Scripts | `scope=scripts` | `script-name={name}` | `/pm-plugin-development:plugin-doctor scope=scripts script-name={name}` |

Parameter values: `{name}` is the component name without path or extension.

Common mistakes: Do NOT use `--component {path}`, file paths as scope parameters, or omit the scope parameter.

### Test and Bundle Verification

| Purpose | Command |
|---------|---------|
| Run module tests | `./pw module-tests {bundle}` |
| Full bundle verification | `./pw verify {bundle}` |

### Decision Guide

**Primary factor**: The deliverable's **Profiles** list determines verification. Since `phase-4-plan` copies verification verbatim to ALL tasks from a deliverable, choose the command that covers the most demanding profile.

**Profile-based priority** (highest wins):

| Profiles Include | Verification Command | Rationale |
|------------------|---------------------|-----------|
| `module_testing` | Resolve `module-tests` from architecture | Tests passing implicitly verifies implementation |
| `implementation` only (scripts) | Resolve `compile` from architecture | Type-check without running tests |
| `implementation` only (markdown) | Plugin-doctor for the component | Structural/standards check |
| `verification` only | Deliverable-specific command | As defined in deliverable |

**Scope-based secondary guidance** (when profile-based priority doesn't differentiate):

| Deliverable Scope | Verification Pattern |
|-------------------|---------------------|
| Single component (markdown only) | Plugin-doctor for specific component type |
| Single component (scripts + tests) | Resolve `module-tests` from architecture |
| Multiple components in one bundle | `./pw verify {bundle}` for final deliverable |
| Cross-bundle changes | `./pw verify {bundle}` per affected bundle |
| Plugin.json registration | Plugin-doctor for the registered component |

### Deliverable Verification Templates

**Markdown-only deliverable** (implementation profile, no tests):
```markdown
**Verification:**
- Command: `/pm-plugin-development:plugin-doctor scope={component_type}s {component_type}-name={name}`
- Criteria: No errors, structure compliant
```

**Script deliverable with tests** (implementation + module_testing profiles):
```markdown
**Verification:**
- Command: `{resolved module-tests command from architecture}`
- Criteria: All tests pass, no regressions
```

## Test Deliverable vs module_testing Profile

**CRITICAL**: Do NOT create a separate "update tests" or "consolidate tests" deliverable when individual deliverables already have `module_testing` in their Profiles block.

The 1:N profile mapping (solution-outline-standard.md) means each deliverable with `module_testing` profile automatically generates a separate test task. Creating an additional test deliverable for the same test files causes **redundant tasks** that modify identical files.

| Scenario | Correct Approach |
|----------|-----------------|
| D1-D4 each have `Profiles: implementation, module_testing` | Do NOT add D5 "Update all tests" — D1-D4 already generate test tasks |
| Tests span multiple deliverables and need cross-cutting integration | Create a separate integration test deliverable (different test files) |
| A final verification-only deliverable (no file changes) | Use `change_type: verification` with `Profiles: verification` — this is NOT redundant |

**Anti-pattern**:
```
D1: Migrate component A (Profiles: implementation, module_testing)
D2: Migrate component B (Profiles: implementation, module_testing)
D3: Update tests for A and B  ← REDUNDANT — D1 and D2 already cover testing
```

**Correct pattern**:
```
D1: Migrate component A (Profiles: implementation, module_testing)
D2: Migrate component B (Profiles: implementation, module_testing)
D3: Verify bundle integrity (Profiles: verification)  ← OK — verification only, no file overlap
```

## Markdown vs Script Verification

Plugin development deliverables have different verification depending on content type:

| Deliverable Content | Profiles | Implementation Verification | Module_testing Verification |
|---------------------|----------|---------------------------|----------------------------|
| Markdown components (skills/agents/commands) | `implementation` only | plugin-doctor | N/A |
| Scripts without test files | `implementation` only | `plan-marshall:manage-architecture:architecture resolve --command compile --module {module} --audit-plan-id {plan_id}` | N/A |
| Scripts with test files | `implementation`, `module_testing` | `plan-marshall:manage-architecture:architecture resolve --command compile --module {module} --audit-plan-id {plan_id}` | `plan-marshall:manage-architecture:architecture resolve --command module-tests --module {module} --audit-plan-id {plan_id}` |

Resolve commands from architecture (`plan-marshall:manage-architecture:architecture`) — do NOT hardcode build tool invocations. Always pass `--audit-plan-id {plan_id}` for execution logging.

**Key rule**: Markdown-only deliverables never get `module_testing` — there are no tests to run. Only deliverables that create or modify Python/Bash test files should include the `module_testing` profile.

## Write Solution Outline

Use `write` on first entry (solution_outline.md does not exist yet).
Use `update` on re-entry (Q-Gate loop — solution_outline.md already exists).

**CRITICAL — Deliverable Heading Format**: Each deliverable MUST use exactly `### N. Title` (e.g., `### 1. Migrate component X`). The validation regex is `^### \d+\. .+$`. Any other heading format (e.g., `## Deliverable 1:`, `**1. Title**`, `### Deliverable 1`) will fail validation.

Check first:
```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline exists \
  --plan-id {plan_id}
```

If `exists: false`:
```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline write \
  --plan-id {plan_id} <<'EOF'
# Solution: {Title}

plan_id: {plan_id}
compatibility: {compatibility} — {compatibility_description}

## Summary

{2-3 sentence summary}

## Overview

{Concise description of the change approach and architecture.}

**ASCII Diagram** (required for multi-deliverable outlines, optional for single-deliverable):
Include a text-based diagram that visually communicates the change architecture. Appropriate diagram types:
- **Flow diagram**: Show the sequence of changes or data flow
- **Before/after comparison**: Show structural changes side-by-side
- **Dependency graph**: Show how components relate after the change
- **Component diagram**: Show which modules/files are affected and how they connect

## Deliverables

### 1. {First deliverable title}

**Metadata:**
- change_type: {analysis|feature|enhancement|bug_fix|tech_debt|verification}
- execution_mode: {automated|manual|mixed}
- domain: {single domain from config.domains}
- module: {module name from architecture}
- depends: {none|N|N,M}

**Profiles:**
- implementation
- {module_testing - only if this deliverable creates/modifies test files (e.g., pytest scripts)}

**Affected files:**
- `{explicit/path/to/file1.ext}`
- `{explicit/path/to/file2.ext}`

**Change per file:** {What changes in these files}

**Verification:**
- Command: `{resolved command from architecture}`
- Criteria: {success criteria}

**Success Criteria:**
- {criterion 1}
- {criterion 2}

### 2. {Second deliverable title}

{Same structure — ALL 6 sections above are MANDATORY for every deliverable}
EOF
```

If `exists: true`:
```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline update \
  --plan-id {plan_id} <<'EOF'
{updated solution document}
EOF
```

## Completion

Log completion and return TOON output:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "({agent_name}) Complete: {N} deliverables"
```

```toon
status: success
plan_id: {plan_id}
deliverable_count: {N}
change_type: {type}
domain: plan-marshall-plugin-dev
```

## Shared Constraints

- Log assessments to assessments.jsonl for Q-Gate verification
- Select verification commands using the profile-based priority (see Decision Guide above)
- Return structured TOON output
- Every deliverable MUST include ALL required fields from solution-outline-standard.md
