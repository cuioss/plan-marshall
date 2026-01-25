# Outline Extension Contract

Skill-based contract for domain-specific outline extensions loaded by `phase-3-outline`.

---

## Purpose

Outline extensions provide a **domain-specific outline skill** that phase-3-outline loads for Complex Track requests. The skill encapsulates all domain logic and writes results to sinks.

**Key Principle**: Extensions provide a SKILL, not an agent. The skill handles the complete Complex Track workflow internally and persists results to sinks. The skill can spawn sub-agents as needed (e.g., analysis agents).

---

## Track Selection (by phase-2-refine)

| Track | When Used | Extension Role |
|-------|-----------|----------------|
| **Simple** | Localized changes (single_file, single_module, few_files) | Not used - phase-3-outline handles directly |
| **Complex** | Codebase-wide changes (multi_module, codebase_wide) | Skill loaded by phase-3-outline |

---

## Extension Registration

Domains register outline skills via their `plan-marshall-plugin` extension:

```python
def provides_outline(self) -> str | None:
    """Return outline skill reference."""
    return 'pm-plugin-development:ext-outline-plugin'
```

**Resolution**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  resolve-workflow-skill-extension --domain plan-marshall-plugin-dev --type outline
```

Returns:
```toon
status: success
domain: plan-marshall-plugin-dev
type: outline
extension: pm-plugin-development:ext-outline-plugin
```

---

## Skill Contract

### Input

The skill receives only `plan_id`. All other data is read from sinks.

```toon
plan_id: {plan_id}
```

### Skill Reads From

| Sink | Data | Purpose |
|------|------|---------|
| `references.toon` | track, module_mapping | Track verification, mapping hints |
| `request.md` | body OR clarified_request | Request content for analysis |
| `config.toon` | domains | Domain verification |

### Skill Responsibilities

The skill MUST execute these steps in order:

#### 1. Discovery
- Use domain-specific scripts to find candidate files
- Example: marketplace-inventory for plugins, glob patterns for docs

#### 2. Analysis
- Analyze each candidate against request criteria
- Spawn sub-agents for parallel analysis if needed (via Task tool)
- Determine: CERTAIN_INCLUDE, CERTAIN_EXCLUDE, UNCERTAIN

#### 3. Persist Assessments
- Write ALL assessments to artifacts/assessments.jsonl:
```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-artifacts:manage-artifacts \
  assessment add {plan_id} {file} {certainty} {confidence} \
  --agent {skill_name} --detail "{reason}" --evidence "{evidence}"
```

#### 4. Confirm Uncertainties
- For UNCERTAIN assessments, use AskUserQuestion
- Log user decisions to decision.log:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "({skill}) User: {file} → {include/exclude}"
```

#### 5. Group into Deliverables
- Apply domain-specific grouping rules
- Log grouping decisions to decision.log:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "({skill}) Deliverable {N}: {files}"
```

#### 6. Write Solution Outline
- Write deliverables to solution_outline.md:
```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline write \
  --plan-id {plan_id} --deliverables "{deliverables_json}"
```

### Skill Returns

Minimal status only - all data is in sinks:

```toon
status: success
plan_id: {plan_id}
deliverable_count: {N}
```

### Sinks Written By Skill

| Sink | Content | Format |
|------|---------|--------|
| `artifacts/assessments.jsonl` | All component assessments | JSONL via artifact_store |
| `logs/decision.log` | Discovery, analysis, confirmation, grouping decisions | Log entries |
| `solution_outline.md` | Final deliverables document | Markdown via manage-solution-outline |

---

## Q-Gate (Run by phase-3-outline)

Q-Gate verification runs AFTER the skill completes, in phase-3-outline.

**Q-Gate reads from**:
- `solution_outline.md` (written by skill)
- `artifacts/assessments.jsonl` (written by skill)
- `request.md`

**Q-Gate verifies**:
- Each deliverable fulfills request intent
- Deliverables respect architecture constraints
- No false positives (files that shouldn't be changed)
- No missing coverage (files that should be changed but aren't)

**Q-Gate writes**:
- `artifacts/findings.jsonl` - Any triage findings
- `logs/decision.log` - Q-Gate verification results

---

## Example: Plugin Development Domain

### Skill Definition

File: `pm-plugin-development/skills/ext-outline-plugin/SKILL.md`

The skill contains the complete workflow logic:
- Step 1: Load Context (request, module_mapping, domains)
- Step 2: Discovery (spawn ext-outline-inventory-agent)
- Step 3: Determine Change Type
- Step 4: Execute Workflow (Create Flow or Modify Flow)
- Step 5: Write Solution Outline

The Modify Flow (Step 4) spawns analysis agents via Task tool for parallel component analysis.

### Registration

File: `pm-plugin-development/skills/plan-marshall-plugin/extension.py`

```python
def provides_outline(self) -> str | None:
    """Return outline skill reference."""
    return 'pm-plugin-development:ext-outline-plugin'
```

---

## Domains Without Extensions

For domains without outline extensions (e.g., Java, frontend), phase-3-outline uses the **generic module-based workflow**:

1. Read module_mapping from references.toon
2. For each module, create deliverable with appropriate profile
3. No discovery needed - modules already identified in phase-2-refine
4. Write solution_outline.md directly

---

## Related Documents

- [extension-mechanism.md](extension-mechanism.md) - How extensions work
- [phase-3-outline SKILL.md](../../../phase-3-outline/SKILL.md) - Phase that loads this skill
- [q-gate-validation-agent.md](../../../../agents/q-gate-validation-agent.md) - Q-Gate verification
