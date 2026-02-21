# Doctor Skills Workflow

Analyze and fix skill quality issues.

## Parameters

- `scope` (optional, default: "marketplace"): "marketplace" | "global" | "project"
- `skill-name` (optional): Analyze specific skill
- `--no-fix` (optional): Diagnosis only, no fixes

## Step 1: Load Prerequisites and Standards

```
Skill: plan-marshall:ref-development-standards
Skill: pm-plugin-development:plugin-architecture
Read references/skills-guide.md
Read references/fix-catalog.md
```

## Step 2: Discover Skills

**marketplace scope**:
```
Skill: pm-plugin-development:tools-marketplace-inventory
```

## Step 3: Analyze Skills

Use the batch analyze command filtered to skills:

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace analyze \
  --bundles {bundle} --type skills
```

This returns JSON with per-skill analysis including structure validation, markdown analysis, and reference checking.

**Check against skills-guide.md**:
- Structure score >= 70 (good) or >= 90 (excellent)
- Progressive disclosure compliance
- Relative path usage
- No missing referenced files
- No unreferenced files
- **Foundation skill loading** (see below)
- **Rule 9 compliance** (explicit script calls in workflows)
- **Rule 10a compliance** (enforcement block existence for script-bearing skills)
- **Rule 11 compliance** (no banned enforcement keywords outside enforcement block)

### Validate Foundation Skill Loading

Skills with workflows load foundation skills.

**Required foundation skills**:
```
Skill: pm-plugin-development:plugin-architecture
Skill: plan-marshall:ref-development-standards
```

**Check criteria**:
1. Search SKILL.md for `Skill: pm-plugin-development:plugin-architecture`
2. Search SKILL.md for `Skill: plan-marshall:ref-development-standards`
3. **Exempt skills** (skip check):
   - `plugin-architecture` (is itself the architecture skill)
   - `marketplace-inventory` (pure Pattern 1 script automation, no component operations)
   - Skills with `allowed-tools: Read` only (pure reference libraries)

**If missing**: Flag as safe fix (auto-apply).

### Validate Rule 9 - Explicit Script Calls

Workflow steps that perform script operations have explicit bash code blocks.

**Detection logic**:
1. Find workflow steps (### Step N: ...)
2. For each step, check if it contains action verbs: "read", "write", "display", "check", "validate", "get", "list", "create", "update", "delete"
3. If action verb present WITHOUT a bash code block containing `execute-script.py`, flag as Rule 9 violation

**Violations examples**:
- "Display the solution outline for review" (no bash block)
- "Read the config to get domains" (no bash block)
- "Validate the output" (no bash block)

**Exempt patterns**:
- Steps that use `Task:` (agent delegation)
- Steps that use `Skill:` (skill loading)
- Steps that use `Read:` or `Glob:` (Claude Code tools)
- Steps with explicit bash blocks containing `execute-script.py`

**If violation found**: Flag as risky fix (requires manual intervention to add proper script call).

### Validate Rule 10a - Enforcement Block Existence

Script-bearing skills have a single `## Enforcement` block at the top of the SKILL.md (after frontmatter and title/description, before workflow content).

**Detection logic**:
1. Check if skill has a `scripts/` directory (use Glob)
2. If scripts exist, search SKILL.md for `## Enforcement` heading
3. Verify the enforcement block appears before any `## Workflow` or `## Step` headings

**Enforcement block contents** (validate presence of these subsections):
- `**Execution mode**:` — how the skill operates
- `**Prohibited actions:**` — what the skill must not do
- `**Constraints:**` — rules governing execution

**Exempt skills** (skip check):
- Skills without a `scripts/` directory (pure reference/knowledge skills)
- Skills with `allowed-tools: Read` only (pure reference libraries)

**If missing**: Flag as risky fix (requires manual creation of enforcement block with skill-specific rules).

### Validate Rule 11 - Banned Enforcement Keywords

Skills with an enforcement block do not use banned emphasis keywords outside that block.

**Banned keywords** (as ALL-CAPS standalone words, not inside code blocks or headings):
`CRITICAL`, `MUST`, `NEVER`, `REQUIRED`, `MANDATORY`, `FORBIDDEN`, `ALWAYS`, `DO NOT`, `IMPORTANT`

Also check for: `CANNOT` (use "cannot" lowercase instead)

**Detection logic**:
1. Locate the `## Enforcement` block boundaries (from `## Enforcement` heading to next `##` heading)
2. For all content OUTSIDE the enforcement block:
   - Scan for banned keywords as standalone ALL-CAPS words
   - Exclude matches inside fenced code blocks (``` ... ```)
   - Exclude matches inside inline code (backticks)
   - Exclude matches that are part of a section heading (## or ###)
3. Report each occurrence with line number and context

**If violations found**: Flag as risky fix (requires manual rephrasing to use lowercase equivalents).

### Validate plan-marshall-plugin Manifest

**Conditional**: Only execute if skill name is `plan-marshall-plugin`.

**Load reference**:
```
Read references/plan-marshall-plugin-validation.md
```

**Validation**:
1. Extract bundle name from skill path: `marketplace/bundles/{bundle}/skills/plan-marshall-plugin`
2. Run manifest validation:
   ```bash
   python3 .plan/execute-script.py plan-marshall:domain-extension-api:validate_manifest validate \
     --bundle {bundle}
   ```
3. Parse validation output for issues
4. Add findings to issue list with appropriate fix categories

**Issue categorization**:
- Schema/structure issues → Safe fix
- Missing extension skills → Risky fix
- Invalid skill references → Risky fix

## Step 4: Categorize and Fix

**Safe fixes** (auto-apply unless --no-fix):
- Missing frontmatter fields
- Unused tools in frontmatter
- Invalid YAML syntax
- **Missing foundation skill loading** (add Step 0 to each workflow)

**Risky fixes** (require confirmation):
- **Rule 9 violations** (missing explicit script calls in workflows)
- **Rule 10a violations** (missing enforcement block in script-bearing skills)
- **Rule 11 violations** (banned enforcement keywords outside enforcement block)

**Auto-fix pattern for missing foundation skills**:
```markdown
#### Step 0: Load Foundation Skills

\`\`\`
Skill: pm-plugin-development:plugin-architecture
Skill: plan-marshall:ref-development-standards
\`\`\`

These provide architecture principles and non-prompting tool usage patterns.
```

Insert this before the first step of each workflow section (after `### Steps` line).

## Step 5: Verify and Report

Same pattern with skill-specific checks.
