# Doctor Skills Workflow

Follows the common workflow pattern (see SKILL.md). Reference guide: `skills-guide.md`.

## Parameters

- `scope` (optional, default: "marketplace"): "marketplace" | "global" | "project"
- `skill-name` (optional): Analyze specific skill
- `--no-fix` (optional): Diagnosis only, no fixes

## Skill-Specific Checks

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

### Validate workflow-explicit-script-calls

Workflow steps that perform script operations have explicit bash code blocks.

**Detection logic**:
1. Find workflow steps (### Step N: ...)
2. For each step, check if it contains action verbs: "read", "write", "display", "check", "validate", "get", "list", "create", "update", "delete"
3. If action verb present WITHOUT a bash code block containing `execute-script.py`, flag as violation

**Exempt patterns**:
- Steps that use `Task:` (agent delegation)
- Steps that use `Skill:` (skill loading)
- Steps that use `Read:` or `Glob:` (assistant tools)
- Steps with explicit bash blocks containing `execute-script.py`

**If violation found**: Flag as risky fix (requires manual intervention to add proper script call).

### Validate skill-enforcement-block-required

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

### Validate skill-banned-keywords-outside-enforcement

Skills with an enforcement block do not use banned emphasis keywords outside that block.

**Banned keywords** (as ALL-CAPS standalone words, not inside code blocks or headings):
`CRITICAL`, `MUST`, `NEVER`, `REQUIRED`, `MANDATORY`, `FORBIDDEN`, `ALWAYS`, `DO NOT`, `IMPORTANT`, `CANNOT`

**Detection logic**:
1. Locate the `## Enforcement` block boundaries (from `## Enforcement` heading to next `##` heading)
2. For all content OUTSIDE the enforcement block:
   - Scan for banned keywords as standalone ALL-CAPS words
   - Exclude matches inside fenced code blocks
   - Exclude matches inside inline code (backticks)
   - Exclude matches that are part of a section heading
3. Report each occurrence with line number and context

**If violations found**: Flag as risky fix (requires manual rephrasing to use lowercase equivalents).

### Validate plan-marshall-plugin Manifest

**Conditional**: Only execute if skill name is `plan-marshall-plugin`.

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

## Skill-Specific Fix Categories

**Safe fixes** (auto-apply):
- Missing foundation skill loading (add Step 0 to each workflow)

**Risky fixes** (require confirmation):
- workflow-explicit-script-calls violations (missing explicit script calls in workflows)
- skill-enforcement-block-required violations (missing enforcement block in script-bearing skills)
- skill-banned-keywords-outside-enforcement violations (banned enforcement keywords outside enforcement block)

### Auto-fix: Missing Foundation Skills

```markdown
#### Step 0: Load Foundation Skills

```
Skill: pm-plugin-development:plugin-architecture
Skill: plan-marshall:ref-development-standards
```

These provide architecture principles and non-prompting tool usage patterns.
```

Insert this before the first step of each workflow section (after `### Steps` line).
