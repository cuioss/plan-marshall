---
name: plugin-doctor
description: Diagnose and fix quality issues in marketplace components with automated safe fixes and prompted risky fixes
user-invocable: true
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

### If scope = "skill-content" or skill-path specified with content analysis
→ **EXECUTE** Workflow 6: doctor-skill-content (jump to that section)

### If scope = "marketplace" (full marketplace health check)
→ **EXECUTE** Workflow 7: doctor-marketplace (jump to that section)

### If scope = "plan-marshall"
→ **EXECUTE** Workflow 8: doctor-plan-marshall (jump to that section)

### If scope = "skill-knowledge" or skill-path specified with knowledge review
→ **EXECUTE** Workflow 9: doctor-skill-knowledge (jump to that section)

---

## Progressive Disclosure Strategy

**Load only the reference guide(s) needed per workflow** (not all at once):

| Workflow | Diagnosis Reference | Fix Reference |
|----------|---------------------|---------------|
| doctor-agents | `agents-guide.md` | `fix-catalog.md` |
| doctor-commands | `commands-guide.md` | `fix-catalog.md` |
| doctor-skills | `skills-guide.md` | `fix-catalog.md` |
| doctor-metadata | `metadata-guide.md` | `fix-catalog.md` |
| doctor-scripts | `scripts-guide.md` | `fix-catalog.md` |
| doctor-plan-marshall | `plan-marshall-guide.md` (in plan-marshall bundle) | `fix-catalog.md` |
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
   Skill: plan-marshall:dev-general-practices
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
     --bundles {bundle} --type {component_type} [--name {name}]
   ```

   Use `--name` to filter by component name (e.g., `--name phase-4-plan`) instead of fetching all components and filtering manually.

   This performs markdown analysis, coverage extraction, and reference validation for all matching components. For skills, it also analyzes sub-documents (`references/*.md`, `standards/*.md`, `workflows/*.md`, `templates/*.md`) for bloat, forbidden metadata, and hardcoded script paths. The output includes per-component analysis results in TOON format with a `subdocuments` key for skills.

### Phase 1.5: LLM Optimization Check

Load `references/llm-optimization-guide.md` and review analyzed components for low-value patterns (checklists of obvious rules, motivational text, redundant emphasis, duplicated content). For skills, review both SKILL.md and sub-documents from the `subdocuments` key.

### Phase 2: Categorize Issues

Categorize each issue as safe or risky per `references/fix-catalog.md`. Safe fixes are auto-applied; risky fixes require user confirmation.

### Phase 3: Apply Fixes

1. **Auto-Apply Safe Fixes** — Apply immediately using Edit tool without AskUserQuestion. Track success/failure.

2. **Prompt for Risky Fixes ONLY**
   ```
   AskUserQuestion:
     question: "Apply fix for {issue}?"
     options:
       - label: "Yes" description: "Apply this fix"
       - label: "No" description: "Skip this fix"
       - label: "Skip All" description: "Skip remaining risky fixes"
   ```

### Phase 4: Verify and Report

1. **Verify Fixes**

   Re-run analysis to verify fixes resolved issues:

   ```bash
   python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace analyze \
     --bundles {bundle} --type {component_type} [--name {name}]
   ```

   Compare issue counts before and after to verify resolution.

2. **Generate Summary**
   Generate a cross-bundle summary report with metrics: bundles processed, total components, issues by severity (clean/warnings/critical), fixes applied (safe/risky), and per-bundle breakdown.

---

## Workflow 1: doctor-agents

Follows common workflow pattern. See [standards/doctor-agents.md](standards/doctor-agents.md) for agent-specific checks and thresholds.

## Workflow 2: doctor-commands

Follows common workflow pattern. See [standards/doctor-commands.md](standards/doctor-commands.md) for command-thin-wrapper checks and fix patterns.

## Workflow 3: doctor-skills

Follows common workflow pattern. See [standards/doctor-skills.md](standards/doctor-skills.md) for enforcement block, foundation skill, and skill-naming-noun-suffix validations.

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

## Workflow 8: doctor-plan-marshall

Follows common workflow pattern. PM-001 through PM-006 validation rules and reference guide have moved to `plan-marshall:plan-marshall-plugin` bundle (see `doctor-plan-marshall.md` and `plan-marshall-guide.md` there).

## Workflow 9: doctor-skill-knowledge

Reviews knowledge skill content quality. See [standards/doctor-skill-knowledge.md](standards/doctor-skill-knowledge.md) for correctness, consistency, structure, and LLM optimization checks.

---

## External Resources

### Scripts (scripts/)

Only `doctor-marketplace.py` is registered in the executor. The other scripts (`_analyze.py`, `_validate.py`, `_fix.py`) are internal modules with underscore prefix and are accessed via `doctor-marketplace` subcommands.

**Registered Script** (callable via executor):

| Script | Subcommand | Mode | Purpose |
|--------|------------|------|---------|
| `doctor-marketplace.py` | `scan` | **EXECUTE** | Batch discovery of all marketplace components (`--bundles`, `--paths`) |
| `doctor-marketplace.py` | `analyze` | **EXECUTE** | Batch analysis of all components for issues (`--bundles`, `--type`, `--name`) |
| `doctor-marketplace.py` | `fix` | **EXECUTE** | Auto-apply safe fixes across marketplace (`--bundles`, `--type`, `--name`, `--dry-run`) |
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

#### `scan --paths` (Explicit Path Mode)

The `scan` subcommand accepts `--paths` to scan explicit component paths instead of discovering from the marketplace. This is mutually exclusive with `--bundles`.

```bash
# Scan a marketplace skill by path
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace scan \
  --paths marketplace/bundles/plan-marshall/skills/phase-4-plan

# Scan project-local skills
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace scan \
  --paths .claude/skills/my-custom-skill

# Scan multiple paths (mixed marketplace and project-local)
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace scan \
  --paths marketplace/bundles/plan-marshall/skills/phase-4-plan \
         marketplace/bundles/pm-dev-java/agents/java-verify-agent.md \
         .claude/skills/project-local-skill
```

When `--paths` is provided:

- Each path is resolved to absolute (relative paths resolve against cwd)
- Component type is auto-detected from directory structure (SKILL.md presence, frontmatter patterns, parent directory name)
- Marketplace root validation is skipped entirely
- Invalid or missing paths produce a warning on stderr and are skipped

**Note**: `--paths` and `--bundles` are mutually exclusive. Use `--bundles` for bundle-scoped discovery, `--paths` for targeting specific components.

#### Worktree-Aware Invocation

Use the `--marketplace-root` flag when verifying SKILL.md / agent.md / command.md edits made inside a plan worktree mid-execution, before the worktree merges back to main. The flag pins discovery to the worktree's marketplace tree so analysis sees the in-progress edits instead of the main checkout.

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace verify \
  --marketplace-root /abs/path/to/.claude/worktrees/{plan_id}/marketplace \
  --skill-name foo
```

**Important**: the value passed to `--marketplace-root` is the marketplace root, i.e., the **parent directory of `bundles/`** (e.g., `/abs/path/to/.claude/worktrees/{plan_id}/marketplace`), NOT `bundles/` itself. The script validates this by checking for a `bundles/` subdirectory under the supplied path; if missing, it errors out with a clear message. Resolution precedence is: `--marketplace-root` flag → `PM_MARKETPLACE_ROOT` env var → script-relative discovery → cwd fallback.

### References (references/)

Loaded per workflow via Progressive Disclosure table above. Key files:
- `rule-catalog.md` - Rule definitions for all validated rules
- `llm-optimization-guide.md` - Cross-cutting LLM optimization patterns
- `fix-catalog.md`, `safe-fixes-guide.md`, `risky-fixes-guide.md`, `verification-guide.md` - Fix workflow
- Per-component guides: `agents-guide.md`, `commands-guide.md`, `skills-guide.md`, `metadata-guide.md`
- plan-marshall-specific: `plan-marshall-guide.md` (in `plan-marshall:plan-marshall-plugin/references/`, includes extension validation)
- Content analysis: `content-classification-guide.md`, `content-quality-guide.md`

### Assets (assets/)

- `fix-templates.json` - Fix templates and rules

### Templates (templates/)

- `tool-coverage-results.toon` - TOON template for aggregating tool-coverage-agent results

---

## Rule Definitions

See [references/rule-catalog.md](references/rule-catalog.md) for the complete catalog of rules that plugin-doctor validates (agent, workflow, command, skill, script, content, and PM-workflow rules).

Representative rule ids by category:

- **Agent**: `agent-task-tool-prohibited`, `agent-maven-restricted`, `agent-lessons-via-skill`, `agent-skill-tool-visibility`
- **Workflow**: `workflow-explicit-script-calls`, `workflow-hardcoded-script-path`, `workflow-prose-parameter-consistency`, `prose-verb-chain-consistency`
- **Command**: `command-self-contained-notation`, `command-thin-wrapper`, `command-progressive-disclosure`, `command-completion-checks`, `command-no-embedded-standards`
- **Skill**: `skill-enforcement-block-required`, `skill-unused-tools-declared`, `skill-naming-noun-suffix`
- **Script**: `argparse_safety`
- **Content**: `checklist-pattern`
- **PM-Workflow**: `pm-implicit-script-call` through `pm-contract-non-compliance`

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
