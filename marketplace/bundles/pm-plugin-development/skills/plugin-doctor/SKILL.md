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

**9 Doctor Workflows**:
1. **doctor-agents**: Analyze and fix agent issues
2. **doctor-commands**: Analyze and fix command issues
3. **doctor-skills**: Analyze and fix skill issues
4. **doctor-metadata**: Analyze and fix plugin.json issues
5. **doctor-scripts**: Analyze and fix script issues
6. **doctor-skill-content**: Analyze and reorganize skill content files
7. **doctor-marketplace**: Full marketplace batch analysis with report
8. **doctor-pm-workflow**: Validate pm-workflow components and contract compliance
9. **doctor-skill-knowledge**: Review knowledge skill content quality

Each workflow performs the complete cycle: discover → analyze → categorize → fix → verify.

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

   This performs markdown analysis, coverage extraction, and reference validation for all matching components. For skills, it also analyzes all sub-documents (`references/*.md`, `standards/*.md`, `workflows/*.md`, `templates/*.md`) for bloat, forbidden metadata, banned ALL-CAPS keywords, and hardcoded script paths. The output includes per-component analysis results in JSON format with a `subdocuments` key for skills.

### Phase 1.5: LLM Optimization Check

Load `references/llm-optimization-guide.md` and review the analyzed components for low-value patterns. For skills, this includes SKILL.md and all sub-documents reported in the `subdocuments` key of the analysis output. Flag motivational text, redundant emphasis, obvious checklists, verbose examples, and duplicated content.

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

#### Hybrid Batch Processing (doctor-marketplace.py)

The `doctor-marketplace.py` script provides Phase 1 of the hybrid doctor workflow for full marketplace operations:

**Phase 1 (Script - Deterministic)**:
```bash
# Scan entire marketplace
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace scan

# Analyze all components
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace analyze

# Preview safe fixes (dry run)
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace fix --dry-run

# Apply safe fixes
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace fix

# Generate report for LLM review (writes to: .plan/temp/plugin-doctor-report/)
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace report

# Or specify custom output directory
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace report --output .plan/temp/my-review
```

**Report Output**: Reports are written to a fixed directory with timestamped, scoped files:
```
.plan/temp/plugin-doctor-report/
├── 20251213-155927-pm-plugin-development-report.json   # Single bundle
├── 20251213-155927-pm-plugin-development-findings.md
├── 20251213-160530-marketplace-report.json             # All bundles
└── 20251213-160530-marketplace-findings.md
```

Filename includes scope: single bundle name, multiple bundle names (up to 3), or "marketplace" for all.
Use `--output` to specify a custom directory path. Multiple reports accumulate in the directory.

**Phase 2 (LLM - Semantic)**:
After Phase 1 creates the report directory and JSON, the LLM:
1. Reads `{timestamp}-{scope}-report.json` for structured data
2. Applies contextual judgment (identifies false positives, priorities)
3. Creates `{timestamp}-{scope}-findings.md` in the same directory with:
   - Executive summary and statistics
   - Bundle-by-bundle analysis
   - Categorization of remaining issues (fixed, false positive, intentional)
   - Recommendations for manual review
4. Processes risky fixes with user confirmation
5. Documents complex refactoring recommendations

**Workflow for `/plugin-doctor marketplace`**:
1. Run `doctor-marketplace scan` to discover components
2. Run `doctor-marketplace analyze` to find issues
3. Run `doctor-marketplace fix` to auto-apply safe fixes
4. Run `doctor-marketplace report` to generate LLM review items
5. LLM processes remaining risky/unfixable issues

### References (references/)

**Cross-Cutting References** (1) - **READ** for all workflows:
- `llm-optimization-guide.md` - LLM consumption efficiency patterns

**Diagnosis References** (8) - **READ** before analyzing:
- `agents-guide.md` - Agent quality standards
- `commands-guide.md` - Command quality standards
- `skills-guide.md` - Skill structure standards
- `metadata-guide.md` - plugin.json schema
- `content-classification-guide.md` - Content type classification criteria (for doctor-skill-content)
- `content-quality-guide.md` - Content quality analysis dimensions (for doctor-skill-content)
- `plan-marshall-plugin-validation.md` - Domain manifest validation (for plan-marshall-plugin skills)
- `pm-workflow-guide.md` - pm-workflow component validation (for doctor-pm-workflow)

**External Standards** (from plugin-architecture) - **READ** for script analysis:
- `script-standards.md` - Script documentation, testing, and quality standards

**Fix References** (4) - **READ** before applying fixes:
- `fix-catalog.md` - Fix categorization rules
- `safe-fixes-guide.md` - Safe fix patterns
- `risky-fixes-guide.md` - Risky fix patterns
- `verification-guide.md` - Verification procedures

**Reporting** (1) - **REFERENCE** for output formatting:
- `reporting-templates.md` - Summary report templates

### Assets (assets/)

- `fix-templates.json` - Fix templates and rules

### Templates (templates/)

- `tool-coverage-results.toon` - TOON template for aggregating tool-coverage-agent results

---

## Rule Definitions

Rules that plugin-doctor validates in other components. See Enforcement block for this skill's own constraints.

### Agent Rules

**agent-task-tool-prohibited**: Agents cannot declare the Task tool (unavailable at runtime).

**agent-maven-restricted**: Only the maven-builder agent may execute Maven commands.

**agent-lessons-via-skill**: Agents record lessons via manage-lessons skill, not self-invoke commands.

**agent-skill-tool-visibility**: Agents declaring explicit tools must include Skill, otherwise invisible to Task dispatcher.

### Workflow Rules

**workflow-explicit-script-calls**: All script/tool invocations in workflow documentation have explicit bash code blocks. Vague instructions like "read the file" or "check the status" are not acceptable — every operation requiring a script call documents the exact `python3 .plan/execute-script.py` command.

**Detection**: Scan workflow steps for action verbs (read, write, display, check, validate, get, list) without accompanying bash code blocks containing `execute-script.py`.

**Example violation**: "Display the solution outline for review" (missing bash block)

**Correct pattern**:
```markdown
### Step N: Read the solution outline

```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline read \
  --plan-id {plan_id}
```
```

**workflow-hardcoded-script-path**: Use executor notation (`bundle:skill:script`) instead of hardcoded file paths.

**workflow-prose-parameter-consistency**: Prose instructions adjacent to `execute-script.py` bash blocks must reference parameter values consistent with the actual script API.

**Currently detected**: `body` referenced as section name near `manage-plan-documents` calls (correct fallback is `original_input`).

### Command Rules

**command-self-contained-notation**: Components that execute scripts have the exact notation (`bundle:skill:script`) explicitly defined within themselves.

**Four Detection Modes**:

| Mode | Catches |
|------|---------|
| A: Delegation | "Execute command from section Nb" - parent-passed |
| B: Notation | `execute-script.py artifact_store` - missing bundle:skill |
| C: Missing Section | "Log the assessment" without ## Logging Command section |
| D: Parameters | `--plan-id` when should be positional (via --help) |

Do not invent notations. Use only documented notations from the skill being called.

**command-thin-wrapper**: Commands delegate all logic to skills; they are thin orchestrators.

**command-progressive-disclosure**: Load skills on-demand, not all at once.

**command-completion-checks**: Mandatory post-fix verification after applying changes.

**command-no-embedded-standards**: No standards blocks in commands; standards belong in skills.

### Skill Rules

**skill-enforcement-block-required**: Script-bearing skills need an `## Enforcement` block.

**skill-banned-keywords-outside-enforcement**: ALL-CAPS keywords (CRITICAL, MUST, NEVER, etc.) only appear inside enforcement blocks.

### PM-Workflow Rules

**pm-implicit-script-call** (PM-001): Script operations without explicit bash code blocks.

**pm-generic-api-reference** (PM-002): Generic API references instead of specific script notation.

**pm-wrong-plan-parameter** (PM-003): Incorrect plan parameter values in script calls.

**pm-missing-plan-parameter** (PM-004): Missing required plan parameters.

**pm-invalid-contract-path** (PM-005): Invalid contract file path references.

**pm-contract-non-compliance** (PM-006): Contract specification violations.

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

## Notes

- **Unified workflow**: Diagnose → Auto-Fix → Prompt Risky → Verify
- **Progressive disclosure**: Load 2 references per workflow (~800 lines)
- **Stdlib-only scripts**: No external dependencies
- **Backup before modify**: `fix apply` creates backups
- **User control**: Risky fixes require explicit approval
- **Non-prompting safe fixes**: Safe fixes never prompt - applied automatically
