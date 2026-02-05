---
name: plugin-doctor
description: Diagnose and fix quality issues in marketplace components with automated safe fixes and prompted risky fixes
user-invocable: true
allowed-tools: Read, Edit, Write, Bash, AskUserQuestion, Glob, Grep, Skill
---

# Plugin Doctor Skill

Comprehensive diagnostic and fix skill for marketplace components. Combines diagnosis, automated safe fixes, prompted risky fixes, and verification into a single workflow.

## Purpose

Provides unified doctor workflows following the pattern: **Diagnose → Auto-Fix Safe → Prompt Risky → Verify**

## Workflow Decision Tree

**MANDATORY**: Select workflow based on input and execute IMMEDIATELY.

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

---

**8 Doctor Workflows**:
1. **doctor-agents**: Analyze and fix agent issues
2. **doctor-commands**: Analyze and fix command issues
3. **doctor-skills**: Analyze and fix skill issues
4. **doctor-metadata**: Analyze and fix plugin.json issues
5. **doctor-scripts**: Analyze and fix script issues
6. **doctor-skill-content**: Analyze and reorganize skill content files
7. **doctor-marketplace**: Full marketplace batch analysis with report
8. **doctor-pm-workflow**: Validate pm-workflow components and contract compliance

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

**Context Efficiency**: ~800 lines per workflow vs ~4,000 lines if loading everything.

## Common Workflow Pattern

All 5 workflows follow the same pattern:

### Phase 1: Discover and Analyze

1. **MANDATORY - Load Prerequisites**

   **EXECUTE** these skill loads before proceeding:
   ```
   Skill: plan-marshall:ref-development-standards
   Skill: pm-plugin-development:plugin-architecture
   Skill: pm-plugin-development:tools-marketplace-inventory
   ```

2. **MANDATORY - Load Component Reference** (progressive disclosure)

   **READ**: `references/{component}-guide.md`

3. **Discover Components** (based on scope parameter)
   - marketplace scope: Use marketplace-inventory
   - global scope: Glob ~/.claude/{component}/
   - project scope: Glob .claude/{component}/

4. **MANDATORY - Analyze Components** (using doctor-marketplace)

   Use the batch analyze command with appropriate filters:

   **EXECUTE**:
   ```bash
   python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace analyze \
     --bundles {bundle} --type {component_type}
   ```

   This performs markdown analysis, coverage extraction, and reference validation for all matching components. The output includes per-component analysis results in JSON format.

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
- Rule 6 violations (Task tool in agents)
- Rule 7 violations (Direct Maven usage - should use builder-maven skill)
- Rule 8 violations (Hardcoded script paths - should use script-runner)
- Rule 9 violations (Missing explicit script calls in workflows)
- Pattern 22 violations (self-invocation)
- Structural changes
- Content removal

### Phase 3: Apply Fixes

1. **Auto-Apply Safe Fixes (NO PROMPT)**

   **CRITICAL**: Safe fixes are applied automatically WITHOUT user confirmation.
   Do NOT use AskUserQuestion for safe fixes.

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

See [standards/doctor-agents.md](standards/doctor-agents.md) for the complete workflow.

## Workflow 2: doctor-commands

See [standards/doctor-commands.md](standards/doctor-commands.md) for the complete workflow.

## Workflow 3: doctor-skills

See [standards/doctor-skills.md](standards/doctor-skills.md) for the complete workflow.

## Workflow 4: doctor-metadata

See [standards/doctor-metadata.md](standards/doctor-metadata.md) for the complete workflow.

## Workflow 5: doctor-scripts

See [standards/doctor-scripts.md](standards/doctor-scripts.md) for the complete workflow.

## Workflow 6: doctor-skill-content

See [standards/doctor-skill-content.md](standards/doctor-skill-content.md) for the complete workflow.

## Workflow 7: doctor-marketplace

See [standards/doctor-marketplace.md](standards/doctor-marketplace.md) for the complete workflow.

## Workflow 8: doctor-pm-workflow

See [standards/doctor-pm-workflow.md](standards/doctor-pm-workflow.md) for the complete workflow.

---

## External Resources

### Scripts (scripts/)

**IMPORTANT**: Only `doctor-marketplace.py` is registered in the executor. The other scripts (`_analyze.py`, `_validate.py`, `_fix.py`) are internal modules with underscore prefix and are accessed via `doctor-marketplace` subcommands.

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
| `_analyze.py` | Structural analysis, bloat, Rule 6/7/Pattern 22 |
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

## Critical Rules

### Rule 6: Task Tool Prohibition in Agents
Agents CANNOT use Task tool (unavailable at runtime).

### Rule 7: Maven Execution Restriction
Only maven-builder agent may execute Maven commands.

### Pattern 22: Agent Lessons Learned Requirement
Agents MUST record lessons via manage-lessons skill, not self-invoke commands.

### Rule 9: Explicit Script Calls in Workflows
All script/tool invocations in workflow documentation MUST have explicit bash code blocks. Vague instructions like "read the file", "display the content", or "check the status" are NOT acceptable. Every operation requiring a script call MUST document the exact `python3 .plan/execute-script.py` command.

**Detection**: Scan workflow steps for action verbs (read, write, display, check, validate, get, list) without accompanying bash code blocks containing `execute-script.py`.

**Examples of violations**:
- "Display the solution outline for review" (missing bash block)
- "Read the config to get domains" (missing bash block)
- "Validate the output" (missing bash block)

**Correct pattern**:
```markdown
### Step N: Read the solution outline

```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline read \
  --plan-id {plan_id}
```
```

### Rule 10: Self-Contained Command Definition

Components that execute scripts MUST have the EXACT notation (`bundle:skill:script`) explicitly defined WITHIN themselves.

**Four Detection Modes**:

| Mode | Catches |
|------|---------|
| A: Delegation | "Execute command from section Nb" - parent-passed |
| B: Notation | `execute-script.py artifact_store` - missing bundle:skill |
| C: Missing Section | "Log the assessment" without ## Logging Command section |
| D: Parameters | `--plan-id` when should be positional (via --help) |

**Notation Format**:
- `pm-workflow:manage-assessments:manage-assessments`
- `pm-workflow:manage-findings:manage-findings`
- `artifact_store` (missing bundle:skill)
- `manage-files:artifact-store` (missing bundle)

**Required Pattern**:
- Explicit "## Logging Command" or "## Script Commands" section
- Full bash block with `python3 .plan/execute-script.py {bundle}:{skill}:{script}`
- Every notation MUST match format: `bundle:skill:script`
- Parameter table showing where values come from

**CRITICAL**: Do NOT invent notations. Use only documented notations from the skill being called.

### Rule 12: Prose-Parameter Consistency

Prose instructions adjacent to `execute-script.py` bash blocks MUST NOT reference parameter values that are inconsistent with the actual script API.

**Detection**: Scan prose near script call templates for fallback/alternative instructions that reference invalid or incorrect parameter values.

**Currently detected patterns**:
- `body` referenced as a section name near `manage-plan-documents` calls (`body` is not a valid section for description-sourced requests; the correct fallback is `original_input`)

**Examples of violations**:
- "If clarified_request is empty, fall back to body section" (should be `original_input`)
- "Read request (clarified_request falls back to body automatically):" (should be `original_input`)

**Correct pattern**:
```markdown
Read request (clarified_request falls back to original_input automatically):

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} \
  --section clarified_request
```
```

**Applies to**: All component types (agents, skills, commands).

**Fix**: Manual — update prose to reference the correct parameter values matching the script API.

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
