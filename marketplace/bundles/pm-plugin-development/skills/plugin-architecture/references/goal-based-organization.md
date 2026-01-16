Th# Goal-Based Marketplace Structure Analysis

## Key Insights from Claude Skills Deep Dive

### 1. Skills as Task-Focused Prompt Modifiers
**Critical Principle**: Skills should be organized around **what users want to accomplish** (goals/tasks), not around technical components or implementation details.

> "Agent skills function as specialized prompt templates that inject domain-specific instructions into conversation context"

### 2. Progressive Disclosure
**Pattern**: Minimize initial context load
- **Frontmatter**: Minimal metadata for discovery (~2-3 lines)
- **SKILL.md**: Full instructions loaded only when skill selected (~800 lines max)
- **References**: Detailed content loaded on-demand (thousands of lines)

> "Minimize initial information load. Frontmatter provides minimal metadata for skill discovery; full SKILL.md loads only after selection; helper resources load on-demand."

### 3. Narrow Focus with Composition
**Pattern**: Skills should be narrowly focused on specific capabilities, then compose together

> "Skills should be narrowly focused on specific capabilities rather than attempting universal solutions."

### 4. Resource Organization
**Standard Directories**:
- `scripts/`: Executable automation (Python/Bash)
- `references/`: Detailed documentation loaded on-demand
- `assets/`: Templates and binary files

### 5. Relative Path Pattern (Critical)
**Pattern**: All resource references use relative paths for portability

> "Use relative paths for paths, never hardcode absolute paths."

Examples:
```bash
bash scripts/analyzer.sh
Read references/detailed-guide.md
```

## Current Structure Analysis: Component-Centric (Wrong)

### Current Organization (By Component Type)
```
Current structure organized by WHAT it operates on:
├── diagnose-agent.md           (operates on agents)
├── diagnose-command.md         (operates on commands)
├── diagnose-skill.md           (operates on skills)
├── analyze-plugin-references.md (operates on references)
├── analyze-standards-file.md    (operates on standards)
└── ...
```

**Problems**:
1. **Component-focused, not goal-focused**: User thinks "I want to diagnose my marketplace" not "I want to run diagnose-agent then diagnose-command then diagnose-skill"
2. **No progressive disclosure**: All agent files loaded even when not needed
3. **Fragmentation**: 8 agents + 14 commands + 6 skills = 28 files for related functionality
4. **Unclear entry points**: Which file do I use for what task?
5. **Violation of narrow focus**: Each agent tries to do complete analysis instead of specific capability

## Target Structure: Goal-Centric (Correct)

### User Goals (Task-Based Thinking)

**Goal 1: CREATE**
"I want to create a new marketplace component"
- Subtasks: Create agent, command, skill, bundle
- User mental model: "Create something new"

**Goal 2: DIAGNOSE**
"I want to find and understand issues in my marketplace"
- Subtasks: Analyze specific component, analyze all components, get health report
- User mental model: "What's wrong?"

**Goal 3: FIX**
"I want to fix identified issues"
- Subtasks: Apply safe fixes, apply risky fixes with confirmation, verify fixes
- User mental model: "Make it better"

**Goal 4: MAINTAIN**
"I want to keep the marketplace healthy"
- Subtasks: Update docs, add knowledge, refactor components
- User mental model: "Keep it clean"

**Goal 5: LEARN**
"I want to understand marketplace architecture"
- Subtasks: Read patterns, understand rules, see examples
- User mental model: "How does this work?"

## Capability Mapping: Current → Goal-Based

### Current Commands → Goal Categories

**CREATE Goal** (4 commands):
- plugin-create-agent → plugin-create workflow
- plugin-create-command → plugin-create workflow
- plugin-create-skill → plugin-create workflow
- plugin-create-bundle → plugin-create workflow

**DIAGNOSE Goal** (5 commands):
- plugin-diagnose-agents → plugin-diagnose workflow
- plugin-diagnose-commands → plugin-diagnose workflow
- plugin-diagnose-skills → plugin-diagnose workflow
- plugin-diagnose-metadata → plugin-diagnose workflow
- plugin-diagnose-scripts → plugin-diagnose workflow

**FIX Goal** (implied in diagnose commands):
- Auto-fix logic embedded in diagnose commands → plugin-fix workflow

**MAINTAIN Goal** (4 commands):
- plugin-update-agent → plugin-maintain workflow
- plugin-update-command → plugin-maintain workflow
- plugin-add-skill-knowledge → plugin-maintain workflow
- plugin-maintain-readme → plugin-maintain workflow
- plugin-verify-marketplace → plugin-maintain workflow

**LEARN Goal** (0 commands currently):
- No explicit commands, just reference skills

### Current Agents → Workflows in Skills

**Analysis Agents** (8 agents) → **plugin-diagnose skill workflows**:
- diagnose-agent → workflow: analyze-component (type=agent)
- diagnose-command → workflow: analyze-component (type=command)
- diagnose-skill → workflow: analyze-component (type=skill)
- analyze-plugin-references → workflow: validate-references
- analyze-standards-file → workflow: validate-standards
- analyze-integrated-standards → workflow: validate-integration
- analyze-cross-skill-duplication → workflow: detect-duplication
- architectural-validator → workflow: validate-architecture

**Key Insight**: All 8 agents are really just different workflows of the same goal: **diagnose quality issues**

### Current Skills → Reorganized

**Architecture Skills** (2 skills) → **plugin-architecture skill** (reference only):
- cui-marketplace-architecture → references/architecture-rules.md
- cui-marketplace-orchestration-patterns → references/orchestration-patterns.md

**Execution Skills** → **Absorb into goal-based skills**:
- marketplace-inventory → plugin-diagnose (internal utility)
- cui-fix-workflow → plugin-fix (main skill)
- bundle-orchestration-compliance → plugin-maintain (reference)
- diagnose-reporting-templates → plugin-diagnose/references/reporting-templates.md (DONE)

## Target Goal-Based Structure

```
marketplace/bundles/pm-plugin-development/
├── .claude-plugin/
│   └── plugin.json
├── README.md
├── commands/                    (User entry points - task-based)
│   ├── create.md               (Create new component - any type)
│   ├── diagnose.md             (Find issues - any scope)
│   ├── fix.md                  (Fix issues - guided workflow)
│   ├── maintain.md             (Maintain health - various tasks)
│   └── verify.md               (Verify marketplace - full check)
└── skills/                      (Goal-based capabilities)
    ├── plugin-create/           (GOAL: Create new components)
    │   ├── SKILL.md            (Workflows for creating)
    │   ├── scripts/
    │   │   └── validate-component.sh
    │   ├── references/
    │   │   ├── agent-template.md
    │   │   ├── command-template.md
    │   │   └── skill-template.md
    │   └── assets/
    │       └── frontmatter-examples.yaml
    │
    ├── plugin-diagnose/         (GOAL: Find and understand issues)
    │   ├── SKILL.md            (Workflows for analysis)
    │   ├── scripts/
    │   │   ├── analyze-structure.sh
    │   │   ├── analyze-tools.sh
    │   │   ├── scan-inventory.py       # Conceptual - actual: scan-marketplace-inventory.py
    │   │   └── validate-references.sh
    │   ├── references/
    │   │   ├── quality-standards.md
    │   │   ├── analysis-patterns.md
    │   │   └── issue-catalog.md
    │   └── assets/
    │       └── report-templates.json
    │
    ├── plugin-fix/              (GOAL: Fix identified issues)
    │   ├── SKILL.md            (Workflows for fixing)
    │   ├── scripts/
    │   │   └── apply-fixes.sh
    │   └── references/
    │       ├── fix-patterns.md
    │       ├── safe-fixes.md
    │       └── risky-fixes.md
    │
    ├── plugin-maintain/         (GOAL: Keep marketplace healthy)
    │   ├── SKILL.md            (Workflows for maintenance)
    │   ├── scripts/
    │   │   └── update-readme.sh
    │   └── references/
    │       ├── maintenance-checklist.md
    │       └── refactoring-patterns.md
    │
    └── plugin-architecture/     (GOAL: Learn and reference)
        ├── SKILL.md            (Learning guide)
        └── references/
            ├── architecture-rules.md
            ├── design-principles.md
            ├── orchestration-patterns.md
            ├── best-practices.md
            └── examples/
                ├── good-agent-example.md
                ├── good-command-example.md
                └── good-skill-example.md
```

## Command Simplification

### Before: 14 Component-Specific Commands
```
plugin-create-agent
plugin-create-command
plugin-create-skill
plugin-create-bundle
plugin-diagnose-agents
plugin-diagnose-commands
plugin-diagnose-skills
plugin-diagnose-metadata
plugin-diagnose-scripts
plugin-update-agent
plugin-update-command
plugin-add-skill-knowledge
plugin-maintain-readme
plugin-verify-marketplace
```

### After: 5 Goal-Based Commands
```
plugin-create       (replaces 4 create-* commands)
plugin-diagnose     (replaces 5 diagnose-* commands)
plugin-fix          (new - extracted from diagnose commands)
plugin-maintain     (replaces 4 update/maintain commands)
plugin-verify       (marketplace health check)
```

### Command Design Example: diagnose.md

```markdown
---
name: plugin-diagnose
description: Find and understand quality issues in marketplace components
---

# Diagnose Marketplace Issues

Interactive command to analyze marketplace components and identify issues.

## Usage

**Diagnose specific component**:
```
/plugin-diagnose agent=my-agent
/plugin-diagnose command=my-command
/plugin-diagnose skill=my-skill
```

**Diagnose all components of a type**:
```
/plugin-diagnose agents
/plugin-diagnose commands
/plugin-diagnose skills
```

**Diagnose entire marketplace**:
```
/plugin-diagnose marketplace
```

**Diagnose with auto-fix**:
```
/plugin-diagnose marketplace --fix
```

## Workflow

### Step 1: Determine Scope
Parse parameters to determine what to analyze.

### Step 2: Invoke Diagnostic Skill
```
Skill: pm-plugin-development:plugin-diagnose
Workflow: {appropriate workflow based on scope}
Parameters: {parsed from command}
```

### Step 3: Display Results
Show analysis results with severity categorization.

### Step 4: Offer Fix Option (if --fix not provided)
Ask user if they want to apply fixes.

### Step 5: Apply Fixes (if confirmed)
```
Skill: pm-plugin-development:plugin-fix
Workflow: apply-fixes
Parameters: {issues from diagnosis}
```
```

## Skill Design Pattern: Goal-Based with Workflows

### Example: plugin-diagnose/SKILL.md

```markdown
---
name: plugin-diagnose
description: Find and understand quality issues in marketplace components (agents, commands, skills, metadata, scripts)
allowed-tools: [Read, Bash, Glob, Grep, Skill]
---

# Plugin Diagnose Skill

Comprehensive diagnostic workflows for marketplace component quality analysis.

## When to Use This Skill

Invoke when you need to:
- Analyze a specific component for issues
- Scan all components of a type
- Generate marketplace health report
- Validate references and standards
- Detect duplication across components

## Workflows

### Workflow 1: analyze-component
Analyzes a single component (agent/command/skill) for quality issues.

**Input Parameters**:
- `component_path`: Absolute path to component file
- `component_type`: "agent" | "command" | "skill"
- `standards_preloaded`: Boolean (optional)

**Process**:
1. Load quality standards (if not preloaded)
   ```
   Read references/quality-standards.md
   Read references/analysis-patterns.md
   ```

2. Analyze structure
   ```
   bash scripts/analyze-structure.sh {component_path} {component_type}
   ```

3. Analyze tool coverage (for agents/commands)
   ```
   bash scripts/analyze-tools.sh {component_path}
   ```

4. Validate references
   ```
   bash scripts/validate-references.sh {component_path}
   ```

5. Apply quality standards checks

6. Generate report
   ```
   Read assets/report-templates.json
   ```

**Output**: Structured quality report with issues categorized by severity

### Workflow 2: analyze-all-of-type
Analyzes all components of a specific type.

**Input Parameters**:
- `component_type`: "agents" | "commands" | "skills"
- `scope`: "marketplace" | "project" | "global"

**Process**:
1. Discover components (conceptual example)
   ```bash
   # Actual API: python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory --scope {scope}
   bash scripts/scan-inventory.sh --type {component_type} --scope {scope}
   ```

2. Pre-load standards once (token optimization)
   ```
   Read references/quality-standards.md
   ```

3. Analyze each component in batches of 5
   - For each component: invoke workflow analyze-component with standards_preloaded=true

4. Aggregate results

5. Generate summary report

**Output**: Aggregated report with statistics and issue summary

### Workflow 3: validate-marketplace
Complete marketplace health check.

**Input Parameters**: None

**Process**:
1. Scan complete inventory (conceptual example)
   ```bash
   # Actual API: python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory --scope marketplace
   bash scripts/scan-inventory.sh --scope marketplace
   ```

2. Pre-load all standards

3. Analyze all bundles in parallel batches
   - For each bundle:
     - Analyze all agents
     - Analyze all commands
     - Analyze all skills
     - Validate metadata
     - Check scripts

4. Detect cross-bundle issues
   - Duplication
   - Reference violations
   - Integration problems

5. Generate comprehensive health report

**Output**: Marketplace health report with scores and recommendations

### Workflow 4: validate-references
Validates all references in a component.

**Input Parameters**:
- `component_path`: Path to component file

**Process**:
1. Extract all references (Read:, Skill:, URLs)
2. Validate each reference exists/accessible
3. Check for prohibited patterns (../../../../, absolute paths)
4. Verify relative path usage in skills
5. Report violations

**Output**: Reference validation report

### Workflow 5: detect-duplication
Detects duplicate content across components.

**Input Parameters**:
- `scope`: "marketplace" | "bundle" | specific paths

**Process**:
1. Scan all components in scope
2. Extract content blocks
3. Compare using similarity heuristics
4. Identify duplication candidates
5. Recommend consolidation strategies

**Output**: Duplication analysis with recommendations

## Progressive Disclosure

**Minimal Load** (always):
- SKILL.md with workflow descriptions

**On-Demand Load** (per workflow):
- References only when needed for specific workflow
- Scripts executed as needed
- Templates loaded when generating reports

## Script Contracts

All scripts return JSON for structured parsing.

**analyze-structure.sh**:
```json
{
  "file_type": "agent" | "command" | "skill",
  "frontmatter": {...},
  "structure": {...},
  "bloat": {...},
  "issues": [...]
}
```

**scan-inventory.sh** (conceptual - actual script: `pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory`):
```json
{
  "scope": "marketplace",
  "bundles": [...],
  "statistics": {...}
}
```

## References

* Quality standards: references/quality-standards.md
* Analysis patterns: references/analysis-patterns.md
* Issue catalog: references/issue-catalog.md
```

## Benefits of Goal-Based Structure

### 1. User-Centric Organization
- **Before**: "Which diagnose command do I use? diagnose-agents or diagnose-commands?"
- **After**: "I want to diagnose → Use /plugin-diagnose command with appropriate parameters"

### 2. Massive Simplification
- **Before**: 8 agents + 14 commands + 6 skills = 28 files
- **After**: 0 agents + 5 commands + 5 skills = 10 files
- **Reduction**: 64% fewer files

### 3. Progressive Disclosure
- **Before**: All agent files potentially loaded
- **After**: Only relevant workflow in skill loaded, references on-demand

### 4. Composition Over Duplication
- **Before**: Each diagnose-* agent duplicates structure analysis logic
- **After**: Single analyze-component workflow used with different parameters

### 5. Clear Mental Model
- **Before**: Component types (agent/command/skill) as primary organization
- **After**: User goals (create/diagnose/fix/maintain/learn) as primary organization

### 6. Better Reusability
- **Before**: diagnose-agent can only diagnose agents
- **After**: plugin-diagnose:analyze-component works for any component type

### 7. Simpler Discovery
- **Before**: Browse through 14 commands to find what you need
- **After**: 5 commands named after user goals

## Progressive Disclosure in Action

### Example: User wants to diagnose one agent

**Step 1: Command invocation** (minimal context)
```
/plugin-diagnose agent=my-agent
```

**Step 2: Command loads** (~100 lines)
```
Command parses parameters, determines scope
```

**Step 3: Skill frontmatter loaded** (~5 lines)
```yaml
name: plugin-diagnose
description: Find and understand quality issues...
allowed-tools: [Read, Bash, Glob, Grep, Skill]
```

**Step 4: Skill content loaded** (~800 lines)
```
Workflow descriptions and instructions
```

**Step 5: Reference loaded on-demand** (~2000 lines)
```
Read references/quality-standards.md
(Only when workflow needs it)
```

**Total context used**: ~2905 lines
**Total available**: ~10,000+ lines (if loaded all references)
**Savings**: ~70% context reduction through progressive disclosure

## Key Design Principles from Blog

### 1. Skills = Capabilities, Not Components
**Wrong**: skill-for-agents, skill-for-commands, skill-for-skills
**Right**: skill-for-creation, skill-for-diagnosis, skill-for-fixing

### 2. Workflows = Variants of Capability
**Wrong**: Separate skills for each variant
**Right**: Single skill with multiple workflows for variants

### 3. relative paths for All Resources
**Wrong**: Hardcoded paths, ./.claude/skills/...
**Right**: scripts/..., references/...

### 4. Scripts = Deterministic Logic
**Wrong**: Complex logic in markdown workflows
**Right**: Complex logic in scripts, markdown orchestrates

### 5. References = On-Demand Knowledge
**Wrong**: All standards embedded in SKILL.md
**Right**: Standards in references/, loaded when needed

### 6. Progressive Disclosure Always
**Wrong**: Front-load all information in frontmatter/SKILL.md
**Right**: Minimal → Specific → Detailed as needed

## Related Patterns

### Minimal Wrapper Pattern
For implementing goal-based agents and commands as thin orchestrators, see:
- **xref:minimal-wrapper-pattern.md[Minimal Wrapper Pattern]** - Context isolation strategy using thin wrappers (< 150 lines) that delegate to skills

**Integration**: Goal-based organization defines WHAT to build (user goals); minimal wrapper pattern defines HOW to build it (thin orchestration with skill delegation).

**Example**:
```
Goal: CREATE (from goal-based organization)
  ↓
Agent: java-create-agent (< 150 lines, minimal wrapper pattern)
  ↓
Skill: cui-java-core (600 lines, business logic)
```

### Command Design
For designing thin orchestrator commands, see:
- **xref:command-design.md[Command Design]** - Thin orchestrator pattern for self-contained commands

### Skill Design
For designing workflow-focused skills, see:
- **xref:skill-design.md[Skill Design]** - Workflow-focused design principles
