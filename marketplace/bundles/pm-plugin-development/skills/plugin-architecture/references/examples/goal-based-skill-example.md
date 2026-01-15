# Example: Goal-Based Skill (plugin-diagnose)

This example demonstrates a complete goal-based skill following Pattern 3 (Search-Analyze-Report) with multiple workflows.

## Skill Structure

```
plugin-diagnose/
├── SKILL.md                (~800 lines, 5 workflows)
├── scripts/
│   ├── analyze-structure.sh      (structural analysis)
│   ├── analyze-tools.sh           (tool coverage analysis)
│   ├── scan-inventory.sh          (conceptual - actual: scan-marketplace-inventory.py)
│   └── validate-references.sh     (reference compliance)
├── references/
│   ├── quality-standards.md       (comprehensive standards)
│   ├── analysis-patterns.md       (analysis strategies)
│   └── issue-catalog.md           (known issues + fixes)
└── assets/
    └── report-templates.json      (output templates)
```

## SKILL.md

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
- `component_path`: Absolute path to component file (required)
- `component_type`: "agent" | "command" | "skill" (required)
- `standards_preloaded`: Boolean (optional, default: false)

**Process**:

#### Step 1: Load Quality Standards (if not preloaded)

If standards_preloaded = false:
  Read references/quality-standards.md
  Read references/analysis-patterns.md

#### Step 2: Analyze Structure

bash scripts/analyze-structure.sh {component_path} {component_type}

Script outputs JSON:
```json
{
  "file_type": "agent" | "command" | "skill",
  "frontmatter": {...},
  "structure": {...},
  "issues": [
    {"type": "missing-section", "severity": "high", "message": "..."},
    {"type": "invalid-yaml", "severity": "critical", "message": "..."}
  ]
}
```

#### Step 3: Analyze Tool Coverage (for agents/commands)

If component_type = "agent" or "command":
  bash scripts/analyze-tools.sh {component_path}

Script outputs JSON with tool usage analysis.

#### Step 4: Validate References

bash scripts/validate-references.sh {component_path}

Checks for:
- Prohibited patterns (../../../../, absolute paths)
- Missing relative path
- Invalid skill references

#### Step 5: Apply Quality Standards Checks

Load detailed analysis patterns:
Read references/analysis-patterns.md

Apply standards-based checks:
- Workflow clarity
- Progressive disclosure
- Relative path usage
- Proper skill invocations

#### Step 6: Generate Report

Load report template:
Read assets/report-templates.json

Format structured report with:
- Component name and type
- Issues categorized by severity (critical, high, medium, low)
- Recommendations for each issue
- Overall quality score

**Output**: Structured quality report

```json
{
  "component": "my-agent.md",
  "type": "agent",
  "status": "issues_found",
  "score": 75,
  "issues": [
    {
      "severity": "high",
      "type": "missing-baseDir",
      "message": "Script path issue: bash ./scripts/analyzer.sh",
      "recommendation": "Use: bash scripts/analyzer.sh",
      "line": 45
    }
  ],
  "summary": "1 high, 2 medium, 3 low severity issues found"
}
```

### Workflow 2: analyze-all-of-type

Analyzes all components of a specific type.

**Input Parameters**:
- `component_type`: "agents" | "commands" | "skills" (required)
- `scope`: "marketplace" | "project" | "global" (optional, default: "marketplace")

**Process**:

#### Step 1: Discover Components

# Conceptual example - Actual API:
# python3 .plan/execute-script.py plan-marshall:tools-marketplace-inventory:scan-marketplace-inventory --scope {scope}
bash scripts/scan-inventory.sh --type {component_type} --scope {scope}

Script outputs JSON:
```json
{
  "scope": "marketplace",
  "type": "agents",
  "components": [
    "marketplace/bundles/bundle1/agents/agent1.md",
    "marketplace/bundles/bundle1/agents/agent2.md",
    "marketplace/bundles/bundle2/agents/agent3.md"
  ],
  "total_count": 3
}
```

#### Step 2: Pre-load Standards Once (token optimization)

Read references/quality-standards.md
Read references/analysis-patterns.md

#### Step 3: Analyze Each Component in Batches

Process components in batches of 5:

For each batch:
  For each component in batch:
    Invoke Workflow 1 (analyze-component) with standards_preloaded=true

  Report batch progress: "Processed [5/15] components"

#### Step 4: Aggregate Results

Combine all component results into summary:
```json
{
  "type": "agents",
  "total_analyzed": 15,
  "clean": 8,
  "issues_found": 7,
  "severity_breakdown": {
    "critical": 2,
    "high": 5,
    "medium": 12,
    "low": 8
  },
  "components_with_issues": [...]
}
```

**Output**: Aggregated report with statistics and issue summary

### Workflow 3: validate-marketplace

Complete marketplace health check.

**Input Parameters**: None

**Process**:

#### Step 1: Scan Complete Inventory

# Conceptual example - Actual API:
# python3 .plan/execute-script.py plan-marshall:tools-marketplace-inventory:scan-marketplace-inventory --scope marketplace
bash scripts/scan-inventory.sh --scope marketplace

Returns all bundles, agents, commands, skills.

#### Step 2: Pre-load All Standards

Read references/quality-standards.md
Read references/analysis-patterns.md
Read references/issue-catalog.md

#### Step 3: Analyze All Bundles in Parallel Batches

For each bundle:
  - Invoke Workflow 2 for bundle agents
  - Invoke Workflow 2 for bundle commands
  - Invoke Workflow 2 for bundle skills
  - Validate metadata (plugin.json)

#### Step 4: Detect Cross-Bundle Issues

Invoke Workflow 5 (detect-duplication) with scope=marketplace

Check for:
- Duplicate content across components
- Inconsistent reference patterns
- Integration issues

#### Step 5: Generate Comprehensive Health Report

```
MARKETPLACE HEALTH REPORT

## Overall Status: 85/100

### Statistics
- Total Bundles: 5
- Total Components: 78
- Clean: 52 (67%)
- Issues: 26 (33%)

### Severity Breakdown
- Critical: 3
- High: 8
- Medium: 22
- Low: 15

### Top Issues
1. Path issues in scripts (12 occurrences)
2. Prohibited reference patterns (8 occurrences)
3. Missing progressive disclosure (6 occurrences)

### Recommendations
[Prioritized fix recommendations]
```

**Output**: Marketplace health report with scores and recommendations

### Workflow 4: validate-references

Validates all references in a component.

**Input Parameters**:
- `component_path`: Path to component file (required)

**Process**:

#### Step 1: Extract All References

Parse component file for:
- Read: statements
- bash/python script executions
- Skill: invocations
- External URLs

#### Step 2: Validate Each Reference

For each reference:
  - Check type (internal, script, asset, skill, URL)
  - Validate against allowed patterns
  - Check relative path usage for internal refs
  - Verify file existence for internal refs

#### Step 3: Check for Prohibited Patterns

Search for:
- `../../../../` (escape sequences)
- `~/` or absolute paths
- Missing relative paths in internal refs

bash scripts/validate-references.sh {component_path}

#### Step 4: Report Violations

```json
{
  "component": "my-agent.md",
  "total_references": 15,
  "valid": 12,
  "violations": [
    {
      "line": 45,
      "type": "missing-baseDir",
      "reference": "bash ./scripts/analyzer.sh",
      "fix": "bash scripts/analyzer.sh"
    }
  ]
}
```

**Output**: Reference validation report

### Workflow 5: detect-duplication

Detects duplicate content across components.

**Input Parameters**:
- `scope`: "marketplace" | "bundle" | specific paths (required)

**Process**:

#### Step 1: Scan All Components in Scope

# Conceptual example - Actual API:
# python3 .plan/execute-script.py plan-marshall:tools-marketplace-inventory:scan-marketplace-inventory --scope {scope}
bash scripts/scan-inventory.sh --scope {scope}

#### Step 2: Extract Content Blocks

For each component:
  - Extract code examples
  - Extract documentation sections
  - Extract workflow patterns

#### Step 3: Compare Using Similarity Heuristics

Apply similarity detection:
- Exact matches (100% duplicate)
- High similarity (>80% similar)
- Moderate similarity (60-80% similar)

#### Step 4: Identify Duplication Candidates

```json
{
  "duplicates_found": 5,
  "exact_matches": 2,
  "high_similarity": 3,
  "details": [
    {
      "source": "bundle1/agents/agent1.md",
      "duplicate": "bundle2/agents/agent2.md",
      "similarity": 95,
      "content": "Code example for JavaDoc pattern",
      "recommendation": "Move to cui-javadoc skill, reference from both agents"
    }
  ]
}
```

#### Step 5: Recommend Consolidation Strategies

For each duplicate:
  - Suggest skill extraction
  - Recommend reference pattern
  - Estimate consolidation benefit

**Output**: Duplication analysis with recommendations

## Progressive Disclosure

**Minimal Load** (always):
- SKILL.md with workflow descriptions (~800 lines)

**On-Demand Load** (per workflow):
- Workflow 1: quality-standards.md, analysis-patterns.md (only if standards_preloaded=false)
- Workflow 2: Same standards pre-loaded once for all components (token optimization)
- Workflow 3: All standards + issue-catalog.md
- Workflow 4: (no additional refs, uses scripts)
- Workflow 5: (no additional refs, uses scripts)

**Templates**: report-templates.json loaded only when generating reports

## Script Contracts

All scripts return JSON for structured parsing:

**analyze-structure.sh**:
```bash
#!/bin/bash
# Usage: analyze-structure.sh <file_path> <file_type>
# Output: JSON with structure analysis
```

**scan-inventory.sh** (conceptual - actual script: `plan-marshall:tools-marketplace-inventory:scan-marketplace-inventory`):
```bash
#!/bin/bash
# Conceptual example script
# Actual API: python3 .plan/execute-script.py plan-marshall:tools-marketplace-inventory:scan-marketplace-inventory
# Usage: scan-inventory.sh --type <type> --scope <scope>
# Output: JSON with component inventory
```

## Key Patterns Demonstrated

1. **Goal-Based Organization**: Skill serves DIAGNOSE goal with multiple workflows
2. **Progressive Disclosure**: References loaded on-demand based on workflow
3. **Relative Path Pattern**: All resource use relative paths
4. **Script Automation (Pattern 1)**: Deterministic logic in scripts, Claude interprets
5. **Workflow Composition**: Workflows build on each other (Workflow 2 uses Workflow 1)
6. **Token Optimization**: Pre-load standards once for batch processing (Workflow 2, 3)
7. **Structured Output**: All workflows return structured JSON/reports

## Usage Example

```
# Command invokes skill
/plugin-diagnose agent=my-agent

# Command workflow:
Step 1: Parse parameters → component_path="my-agent.md", component_type="agent"
Step 2: Invoke skill
  Skill: plugin-diagnose
  Workflow: analyze-component
  Parameters: {component_path: "...", component_type: "agent"}
Step 3: Display results from skill
```
