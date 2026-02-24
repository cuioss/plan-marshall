---
name: plugin-doctor
description: Diagnose and fix quality issues in marketplace components with automated safe fixes and prompted risky fixes
user-invocable: true
allowed-tools: Read, Edit, Write, Bash, AskUserQuestion, Glob, Grep, Skill
---

# Plugin Doctor Skill

Comprehensive diagnostic and fix skill for marketplace components. Combines diagnosis, automated safe fixes, prompted risky fixes, and verification into a single workflow.

## Enforcement

**Execution mode**: Select workflow based on scope parameter and execute immediately. Do not explain — execute.

**Prohibited actions:**
- Do not prompt for safe fixes — apply them automatically without AskUserQuestion
- Agents cannot use the Task tool (agent-task-tool-prohibited — unavailable at runtime)
- Only maven-builder agent may execute Maven commands (agent-maven-restricted)
- Do not invent script notations — use only documented notations from the skill being called (command-self-contained-notation)

**Constraints:**
- Load prerequisite skills and the component reference guide before analyzing
- Every workflow step that performs a script operation must have an explicit bash code block with the full `python3 .plan/execute-script.py` command (workflow-explicit-script-calls)
- Agents must record lessons via manage-lessons skill, not self-invoke commands (agent-lessons-via-skill)
- Only `doctor-marketplace.py` is registered in the executor; other scripts (`_analyze.py`, `_validate.py`, `_fix.py`) are internal modules accessed via `doctor-marketplace` subcommands
- Prose instructions adjacent to script calls must reference parameter values consistent with the script API (workflow-prose-parameter-consistency)

## Purpose

Provides unified doctor workflows following the pattern: **Diagnose → Auto-Fix Safe → Prompt Risky → Verify**

## Workflow Decision Tree

Select workflow based on input and execute immediately.

### If scope = "agents" or agent-name specified
→ **EXECUTE** Workflow 1: doctor-agents (jump to that section)

### If scope = "commands" or command-name specified
→ **EXECUTE** Workflow 2: doctor-commands (jump to that section)

### If scope = "skills" or skill-name specified
→ **EXECUTE** Workflow 3: doctor-skills (jump to that section)

### If scope = "metadata"
→ **EXECUTE** Workflow 4: doctor-metadata (jump to that section)

### If scope = "scripts" or script-name specified
→ **EXECUTE** Workflow 5: doctor-scripts (jump to that section)

### If scope = "marketplace" (full marketplace health check)
→ **EXECUTE** Workflow 7: doctor-marketplace (jump to that section)

### If scope = "skill-content" or skill-path specified with content analysis
→ **EXECUTE** Workflow 6: doctor-skill-content (jump to that section)

### If scope = "skill-knowledge" or skill-path specified with knowledge review
→ **EXECUTE** Workflow 9: doctor-skill-knowledge (jump to that section)

---

## Progressive Disclosure Strategy

**Load ONE reference guide per workflow** (not all 10):

| Workflow | Diagnosis Reference | Fix Reference |
|----------|---------------------|---------------|
| doctor-agents | `agents-guide.md` | `fix-catalog.md` |
| doctor-commands | `commands-guide.md` | `fix-catalog.md` |
| doctor-skills | `skills-guide.md` | `fix-catalog.md` |
| doctor-metadata | `metadata-guide.md` | `fix-catalog.md` |
| doctor-scripts | `scripts-guide.md` | `fix-catalog.md` |
| doctor-pm-workflow | `pm-workflow-guide.md` | `fix-catalog.md` |
| doctor-skill-knowledge | `llm-optimization-guide.md` | `fix-catalog.md` |
| doctor-skill-content | `content-classification-guide.md` + `content-quality-guide.md` | `fix-catalog.md` |
| doctor-marketplace | (batch: uses all guides via report) | `fix-catalog.md` |

**Cross-cutting reference** (loaded by all workflows): `llm-optimization-guide.md`

**Context Efficiency**: ~800 lines per workflow vs ~4,000 lines if loading everything.

## Common Workflow Pattern

All 9 workflows follow the same pattern:

### Phase 1: Discover and Analyze

1. **Load Prerequisites**

   Load these skills before proceeding:
   ```
   Skill: plan-marshall:ref-development-standards
   Skill: pm-plugin-development:plugin-architecture
   Skill: pm-plugin-development:tools-marketplace-inventory
   ```

2. **Load Component Reference** (progressive disclosure)

   Read: `references/{component}-guide.md`

3. **Discover Components** (based on scope parameter)
   - marketplace scope: Use marketplace-inventory
   - global scope: Glob ~/.claude/{component}/
   - project scope: Glob .claude/{component}/

4. **Analyze Components** (using doctor-marketplace)

   Use the batch analyze command with appropriate filters:

   ```bash
   python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace analyze \
     --bundles {bundle} --type {component_type}
   ```

   This performs markdown analysis, coverage extraction, and reference validation for all matching components. For skills, it also analyzes sub-documents (`references/*.md`, `standards/*.md`, `workflows/*.md`, `templates/*.md`) for bloat, forbidden metadata, and hardcoded script paths. The output includes per-component analysis results in JSON format with a `subdocuments` key for skills.

### Phase 1.5: LLM Optimization Check

Load `references/llm-optimization-guide.md` and review the analyzed components for low-value patterns (motivational text, redundant emphasis, verbose examples, duplicated content). For skills, review both SKILL.md and sub-documents from the `subdocuments` key.

### Phase 2: Categorize Issues

**Safe Fixes** (auto-apply):
- Missing frontmatter fields
- Invalid YAML syntax
- Unused tools in frontmatter
- Trailing whitespace
- Missing blank lines
- Missing foundation skill loading (plugin-architecture, diagnostic-patterns)
- Incorrect section header case (e.g., `## Workflow` → `## WORKFLOW`)
- Missing CONTINUOUS IMPROVEMENT RULE section (commands only)
- Legacy CONTINUOUS IMPROVEMENT RULE (uses /plugin-update-* or /plugin-maintain instead of manage-lessons)

**Risky Fixes** (require confirmation):
- agent-task-tool-prohibited (Task tool in agents)
- agent-maven-restricted (Direct Maven usage - should use builder-maven skill)
- workflow-hardcoded-script-path (Hardcoded script paths - should use executor notation)
- workflow-explicit-script-calls (Missing explicit script calls in workflows)
- agent-lessons-via-skill (self-invocation instead of manage-lessons)
- Structural changes
- Content removal

### Phase 3: Apply Fixes

1. **Auto-Apply Safe Fixes (no prompt)**

   Safe fixes are applied automatically without user confirmation.
   Do not use AskUserQuestion for safe fixes.

   - Apply each safe fix immediately using Edit tool
   - Track success/failure
   - Log: "Fixed: {description}"

2. **Prompt for Risky Fixes ONLY**
   ```
   AskUserQuestion:
     question: "Apply fix for {issue}?"
     options:
       - label: "Yes" description: "Apply this fix"
       - label: "No" description: "Skip this fix"
       - label: "Skip All" description: "Skip remaining risky fixes"
   ```

   **Only risky fixes prompt** - safe fixes never prompt.

### Phase 4: Verify and Report

1. **Verify Fixes**

   Re-run analysis to verify fixes resolved issues:

   ```bash
   python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace analyze \
     --bundles {bundle} --type {component_type}
   ```

   Compare issue counts before and after to verify resolution.

2. **Generate Summary**
   ```
   Read references/reporting-templates.md
   ```
   Use summary template with metrics.

---

## Workflow 1: doctor-agents

Follows common workflow pattern. See [standards/doctor-agents.md](standards/doctor-agents.md) for agent-specific checks and thresholds.

## Workflow 2: doctor-commands

Follows common workflow pattern. See [standards/doctor-commands.md](standards/doctor-commands.md) for command-thin-wrapper checks and fix patterns.

## Workflow 3: doctor-skills

Follows common workflow pattern. See [standards/doctor-skills.md](standards/doctor-skills.md) for enforcement block, keyword, and foundation skill validations.

## Workflow 4: doctor-metadata

Follows the common workflow pattern. Reference guide: `metadata-guide.md`.

**Metadata-specific checks**:
- Verify JSON syntax of each `plugin.json`
- Check required fields (name, version, description)
- Validate component arrays (commands, skills, agents)
- Cross-check declared components vs actual files on disk

**Discovery**: `Glob: pattern="**/plugin.json", path="marketplace/bundles"`

**Safe fixes**: Missing required fields, extra entries (files don't exist), missing entries (files exist but not listed).

## Workflow 5: doctor-scripts

Follows the common workflow pattern. Additional prerequisite: `Skill: pm-plugin-development:plugin-script-architecture`.

**Script-specific checks**:
- Verify SKILL.md documents the script
- Check test file exists in `test/` directory
- Verify `--help` output is functional
- Check stdlib-only compliance (no external dependencies)

**Discovery**: `Glob: pattern="scripts/*.{sh,py}", path="marketplace/bundles/*/skills"`

## Workflow 6: doctor-skill-content

See [standards/doctor-skill-content.md](standards/doctor-skill-content.md) for the complete workflow.

## Workflow 7: doctor-marketplace

See [standards/doctor-marketplace.md](standards/doctor-marketplace.md) for the complete workflow.

## Workflow 8: doctor-pm-workflow

Follows common workflow pattern. See [standards/doctor-pm-workflow.md](standards/doctor-pm-workflow.md) for PM-001 through PM-006 validation rules.

## Workflow 9: doctor-skill-knowledge

Reviews knowledge skill content quality. See [standards/doctor-skill-knowledge.md](standards/doctor-skill-knowledge.md) for correctness, consistency, structure, and LLM optimization checks.

---

## External Resources

### Scripts (scripts/)

Only `doctor-marketplace.py` is registered in the executor. The other scripts (`_analyze.py`, `_validate.py`, `_fix.py`) are internal modules with underscore prefix and are accessed via `doctor-marketplace` subcommands.

**Registered Script** (callable via executor):

| Script | Subcommand | Mode | Purpose |
|--------|------------|------|---------|
| `doctor-marketplace.py` | `scan` | **EXECUTE** | Batch discovery of all marketplace components |
| `doctor-marketplace.py` | `analyze` | **EXECUTE** | Batch analysis of all components for issues |
| `doctor-marketplace.py` | `fix` | **EXECUTE** | Auto-apply safe fixes across marketplace |
| `doctor-marketplace.py` | `report` | **EXECUTE** | Generate comprehensive report for LLM review |

**Notation**: `pm-plugin-development:plugin-doctor:doctor-marketplace {subcommand}`

**Internal Modules** (NOT directly callable - used internally by doctor-marketplace):

| Module | Purpose |
|--------|---------|
| `_analyze.py` | Structural analysis, bloat, agent-task-tool-prohibited/maven-restricted/lessons-via-skill |
| `_analyze_markdown.py` | Markdown structure analysis |
| `_analyze_coverage.py` | Tool coverage extraction |
| `_analyze_structure.py` | Skill directory structure validation |
| `_analyze_crossfile.py` | Cross-file duplication analysis |
| `_validate.py` | Reference extraction and validation |
| `_fix.py` | Fix application and verification |

#### Hybrid Batch Processing

Subcommands: `scan` → `analyze` → `fix` → `report`. See [standards/doctor-marketplace.md](standards/doctor-marketplace.md) for the complete two-phase (script + LLM) workflow, report output format, and directory structure.

### References (references/)

Loaded per workflow via Progressive Disclosure table above. Key files:
- `rule-catalog.md` - Rule definitions for all validated rules
- `llm-optimization-guide.md` - Cross-cutting LLM optimization patterns
- `fix-catalog.md`, `safe-fixes-guide.md`, `risky-fixes-guide.md`, `verification-guide.md` - Fix workflow
- `plan-marshall-plugin-validation.md` - Domain manifest validation
- Per-component guides: `agents-guide.md`, `commands-guide.md`, `skills-guide.md`, `metadata-guide.md`, `pm-workflow-guide.md`
- Content analysis: `content-classification-guide.md`, `content-quality-guide.md`
- `reporting-templates.md` - Summary report templates

### Assets (assets/)

- `fix-templates.json` - Fix templates and rules

### Templates (templates/)

- `tool-coverage-results.toon` - TOON template for aggregating tool-coverage-agent results

---

## Rule Definitions

See [references/rule-catalog.md](references/rule-catalog.md) for the complete catalog of rules that plugin-doctor validates (agent, workflow, command, skill, and PM-workflow rules).

---

## Non-Prompting Requirements

This skill is designed to run without user prompts for safe operations. Required permissions:

**Skill Invocations (covered by bundle wildcards):**
- `Skill(plan-marshall:*)` - diagnostic-patterns
- `Skill(pm-plugin-development:*)` - plugin-architecture, marketplace-inventory

**Script Execution:**
- Script paths resolved from `.plan/scripts-library.toon` (system convention)
- Permissions managed by `tools-setup-project-permissions`

**File Operations (covered by project permissions):**
- `Read(//marketplace/**)` - Read marketplace files
- `Edit(//marketplace/**)` - Apply fixes to components
- `Glob(//marketplace/**)` - Discover components

**Prompting Behavior:**
- **Safe fixes**: Applied automatically WITHOUT prompts (no AskUserQuestion)
- **Risky fixes**: ONLY these require AskUserQuestion confirmation
- All other operations (read, analyze, glob) are non-prompting

**Ensuring Non-Prompting for Safe Operations:**
- All file reads/edits use relative paths within marketplace/
- Script paths resolved from `.plan/scripts-library.toon` (system convention)
- Skill invocations use bundle-qualified names covered by `Skill({bundle}:*)` wildcards
- AskUserQuestion is ONLY used for risky fix confirmations
