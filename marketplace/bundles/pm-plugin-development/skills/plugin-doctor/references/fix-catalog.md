# Fix Catalog Reference

Comprehensive catalog of all fixable issue types, their categorization, and fix strategies.

## Fixable Issue Types Overview

This catalog documents all issues that can be fixed by the plugin-fix skill, organized by category.

## Safe Fix Types

Safe fixes can be auto-applied without user confirmation. They are mechanical fixes that don't risk losing information or changing behavior.

### 1. missing-frontmatter

**Description**: File has no YAML frontmatter block.

**Detection**: File doesn't start with `---`

**Fix Strategy**:
- Determine component type from path (agents/, commands/, skills/)
- Generate appropriate frontmatter with defaults
- Prepend to file content

**Template (Agent)**:
```yaml
---
name: {filename}
description: [Description needed]
tools: Read, Write, Edit
model: sonnet
---
```

**Template (Command)**:
```yaml
---
name: {filename}
description: [Description needed]
---
```

**Why Safe**: Adding metadata doesn't change behavior, only improves documentation.

### 2. invalid-yaml

**Description**: YAML frontmatter has syntax errors.

**Detection**: YAML parsing fails between `---` markers

**Fix Strategy**:
- Common fixes: unclosed quotes, improper indentation
- Fix specific syntax errors
- Preserve all content

**Why Safe**: Fixing syntax doesn't change meaning.

### 3. missing-name-field

**Description**: Frontmatter exists but lacks `name` field.

**Detection**: Frontmatter present but no `^name:` line

**Fix Strategy**:
- Extract filename without extension
- Insert `name: {filename}` after opening `---`

**Why Safe**: Name is derived from filename, no judgment needed.

### 4. missing-description-field

**Description**: Frontmatter lacks `description` field.

**Detection**: Frontmatter present but no `^description:` line

**Fix Strategy**:
- Insert `description: [Description needed]` after name field
- Placeholder clearly indicates manual update needed

**Why Safe**: Placeholder doesn't claim false information.

### 5. missing-tools-field

**Description**: Agent/command frontmatter lacks `tools` field.

**Detection**: Frontmatter present but no `^tools:` line

**Fix Strategy**:
- Insert `tools: Read` as minimal default
- Actual tools should be added based on usage

**Why Safe**: Minimal default doesn't over-promise capabilities.

### 5b. missing-user-invocable-field

**Description**: Skill frontmatter lacks required `user-invocable` field.

**Detection**: Skill file frontmatter present but no `^user-invocable:` line

**Fix Strategy**:
- Determine appropriate value based on skill characteristics:
  - If skill name matches known internal patterns (ext-*, manage-*, ref-*, plan-marshall-plugin): use `false`
  - If skill has workflow logic and clear user-facing purpose: use `true`
  - Default to `false` if uncertain (safer option)
- Insert `user-invocable: {value}` after description field

**Why Safe**: Field is required and value can be inferred from skill characteristics. User can always override.

### 6. array-syntax-tools

**Description**: Tools declared with array syntax `[A, B]` instead of comma-separated.

**Detection**: `^tools:\s*\[` pattern in frontmatter

**Fix Strategy**:
- Convert `tools: [A, B, C]` to `tools: A, B, C`
- Preserve tool list

**Why Safe**: Purely syntactic change, same meaning.

### 7. trailing-whitespace

**Description**: Lines end with whitespace characters.

**Detection**: Lines matching `[[:space:]]$`

**Fix Strategy**:
- Strip trailing whitespace from all lines
- Preserve line endings

**Why Safe**: Whitespace at end of lines has no meaning.

### 8. improper-indentation

**Description**: Inconsistent indentation in YAML or lists.

**Detection**: Mixed tabs/spaces or inconsistent indent levels

**Fix Strategy**:
- Normalize to 2-space indentation for YAML
- Fix list item alignment

**Why Safe**: Indentation normalization is mechanical.

### 9. missing-blank-line-before-list

**Description**: List items immediately follow paragraph (AsciiDoc requirement).

**Detection**: Non-blank line followed by `* ` or `- ` list marker

**Fix Strategy**:
- Insert blank line before list
- Preserve content

**Why Safe**: Adding whitespace doesn't change content.

### 10. rule-11-violation

**Description**: Agent declares explicit tools but omits `Skill`, making it invisible to Task dispatcher.

**Detection**: Agent frontmatter has `tools:` or `allowed-tools:` field without `Skill` in the list. No violation if tools field is absent (inherits all).

**Fix Strategy**:
- Find the `tools:` or `allowed-tools:` line in frontmatter
- Append `, Skill` to the end of the tools list
- Preserve existing tools

**Why Safe**: Purely additive — appending `Skill` never removes capabilities or changes behavior, only makes the agent discoverable by the Task dispatcher.

### SCR-009. positional-argument

**Description**: Script uses positional arguments instead of named `--kebab-case` flags.

**Detection**: `add_argument()` calls without `--` prefix (excluding subparser dest args like `dest='command'`)

**Fix Strategy**:
- Convert `parser.add_argument('name')` to `parser.add_argument('--name', required=True, dest='name')`
- If name contains underscores, use kebab-case flag: `--plan-id` with `dest='plan_id'`
- Update all callers (tests, SKILL.md docs, agent .md files) to use flag syntax

**Why Safe**: Mechanical transformation — same data, different CLI syntax.

### SCR-010. camelcase-flag

**Description**: Script uses camelCase flag name instead of kebab-case.

**Detection**: `add_argument('--camelCase')` pattern (uppercase letter after lowercase)

**Fix Strategy**:
- Rename flag: `--commandArgs` → `--command-args`
- Add `dest='command_args'` to preserve attribute access
- Update all callers and string literals referencing the old flag name

**Why Safe**: Mechanical rename — same behavior, consistent naming.

### SCR-011. missing-subparser-required

**Description**: `add_subparsers()` call missing `required=True`, causing confusing `None` error when subcommand is omitted.

**Detection**: `add_subparsers(dest='...')` without `required=True`

**Fix Strategy**:
- Add `required=True` to the `add_subparsers()` call
- No test or doc changes needed (tests always provide subcommands)

**Why Safe**: Only changes error message when subcommand is missing — no behavioral change for valid invocations.

## Risky Fix Types

Risky fixes require user confirmation because they involve judgment calls or may change behavior.

### 1. unused-tool-declared

**Description**: Tool declared in frontmatter but never referenced in content.

**Detection**: Tool in frontmatter not found in body text

**Fix Strategy**:
- Remove tool from declaration
- Present user with which tools will be removed

**Why Risky**:
- Tool may be intentionally declared for future use
- Tool may be referenced in ways not detected (dynamic invocation)
- User should confirm intent

### 2. tool-not-declared

**Description**: Tool used in content but not declared in frontmatter.

**Detection**: Common tool names found in body but not in frontmatter

**Fix Strategy**:
- Add missing tool to declaration
- Present user with which tools will be added

**Why Risky**:
- Adding tools changes component capabilities
- May indicate accidental tool usage that should be removed instead
- User should confirm desired tools

### 3. rule-6-violation

**Description**: Agent declares Task tool (prohibited by Rule 6).

**Detection**: `Task` in agent's tools declaration

**Fix Strategy**:
- Remove Task from tools list
- If Task was only tool, replace with Read

**Why Risky**:
- Removal changes agent design fundamentally
- Agent may need restructuring to work without Task
- User should understand implications

### 4. rule-7-violation

**Description**: Component uses Maven directly instead of builder-maven skill.

**Detection**: Direct `mvn`, `maven`, or `./mvnw` usage in commands/skills/agents (excluding builder-maven bundle)

**Fix Strategy**:
- Replace direct Maven invocations with builder-maven skill calls
- Use workflow: `Skill: pm-dev-builder:builder-maven-rules` with appropriate workflow name
- Example: Replace `mvn clean compile` with workflow: Execute Maven Build

**Why Risky**:
- Changes build execution mechanism
- May break functionality if not properly migrated
- User should verify build still works
- Requires builder-maven skill to be available

### 5. rule-8-violation

**Description**: Component uses hardcoded script paths instead of the executor pattern.

**Detection**: Direct script invocations with hardcoded paths (e.g., `python3 /path/to/script.py`, `bash {bundle}/scripts/foo.sh`)

**Fix Strategy**:
- Replace hardcoded paths with executor pattern
- Use notation: `python3 .plan/execute-script.py {bundle}:{skill}:{script} {subcommand} {args}`
- Example: Replace `python3 marketplace/.../scripts/verify.py --input x` with `python3 .plan/execute-script.py pm-dev-java:java-core:java-core verify --input x`

**Why Risky**:
- Changes script resolution mechanism
- May break if executor is not generated (run `/marshall-steward` first)
- User should verify script notation and subcommands

### 6. rule-9-violation

**Description**: Skill workflow step contains action verbs without explicit script call.

**Detection**: Workflow steps (### Step N:) containing action verbs like "read the", "display the", "check the", "validate the" without a bash code block containing `execute-script.py`

**Fix Strategy**:
- Add explicit bash code block with the correct script call
- Example: If step says "Display the solution outline for review", add:
  ```bash
  python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline read \
    --plan-id {plan_id}
  ```

**Why Risky**:
- Requires knowledge of correct script notation and subcommand
- May need to identify which manage-* script handles the operation
- User should verify the correct script and parameters

**Exempt Patterns** (no violation):
- Steps using `Task:` (agent delegation)
- Steps using `Skill:` (skill loading)
- Steps using Claude Code tools (`Read:`, `Glob:`, `Grep:`)
- Steps that already have `execute-script.py` bash blocks

### 7. pattern-22-violation

**Description**: Agent uses self-update pattern instead of caller reporting.

**Detection**: `/plugin-update-agent` or `/plugin-update-command` in agent content

**Fix Strategy**:
- Replace self-update commands with "report to caller" language
- Update CONTINUOUS IMPROVEMENT section

**Why Risky**:
- Structural change to agent behavior
- May require rethinking improvement workflow
- User should understand new pattern

### 8. backup-file-pattern

**Description**: Content references backup file patterns (.bak, .backup, etc.).

**Detection**: `.backup`, `.bak`, `.old`, `.orig` patterns in content

**Fix Strategy**:
- Remove backup file references
- Or document them properly

**Why Risky**:
- May be intentional documentation of backup strategy
- Removal might lose important information
- User should decide if references are needed

### 9. ci-rule-self-update

**Description**: CONTINUOUS IMPROVEMENT section uses prohibited self-update.

**Detection**: CI section with self-update commands

**Fix Strategy**:
- Rewrite CI section to use caller-reporting pattern
- Preserve improvement intent

**Why Risky**:
- Significant content change
- User should review new wording
- May affect how improvements are communicated

### 10. implicit-script-call (PM-001)

**Description**: Script call with missing or placeholder parameters.

**Detection**: Bash blocks containing `execute-script.py` with:
- Ellipsis (`...`) at end of command
- Comments like "See API" or "see documentation"
- Placeholder notation without explicit parameters

**Fix Strategy**:
- Look up script's `--help` output or skill documentation
- Replace ellipsis/reference with explicit parameters
- Use `{variable_name}` for dynamic values

**Why Risky**:
- Requires knowledge of correct script parameters
- May need to consult script documentation
- User should verify parameter completeness

### 11. generic-api-reference (PM-002)

**Description**: References API documentation instead of explicit script call.

**Detection**: Text patterns near bash blocks:
- "see * API"
- "refer to * documentation"
- "parameters documented in"
- "see * for available options"

**Fix Strategy**:
- Identify what operation is being referenced
- Find the correct script command
- Write complete bash block with all parameters
- Remove generic reference text

**Why Risky**:
- Requires understanding the intended operation
- Must determine correct script and parameters
- User should verify the replacement is accurate

### 12. wrong-plan-parameter (PM-003)

**Description**: Uses `--plan-id` where `--trace-plan-id` required or vice versa.

**Detection**: Script calls with incorrect plan parameter based on script type:
- `manage-plan-marshall-config` should use `--trace-plan-id`
- `manage-log` should use `--trace-plan-id`
- `manage-files`, `manage-tasks`, `manage-references` should use `--plan-id`

**Fix Strategy**:
- Swap `--plan-id` to `--trace-plan-id` or vice versa
- Consult parameter matrix in pm-workflow-guide.md

**Why Safe** (when pattern is clear):
- Mechanical swap based on known script requirements
- Parameter name change doesn't alter intent

### 13. missing-plan-parameter (PM-004)

**Description**: Plan-related script call without required plan identifier.

**Detection**: Script calls to plan-related scripts missing both `--plan-id` and `--trace-plan-id`

**Fix Strategy**:
- Determine which parameter is needed from matrix
- Add appropriate `--plan-id {plan_id}` or `--trace-plan-id {plan_id}`

**Why Safe** (when context is clear):
- Adding required parameter makes call complete
- Variable name can be inferred from context

### 14. invalid-contract-path (PM-005)

**Description**: `implements:` frontmatter points to non-existent file.

**Detection**: Resolve path from `implements:` field and check file existence

**Fix Strategy**:
- Verify the intended contract exists
- Fix path typos or outdated references
- If contract doesn't exist, either create it or remove `implements:`

**Why Risky**:
- May indicate structural changes in codebase
- User should decide whether to fix path or remove declaration
- Removing `implements:` changes component semantics

## Non-Fixable Issue Types

These issues are detected but cannot be automatically fixed:

### bloat-critical / bloat-high

**Why Not Fixable**: Requires human judgment about what content to extract or remove.

**Recommendation**: Manual refactoring, potentially extracting to skill.

### architectural-restructure-needed

**Why Not Fixable**: Requires creating new components and reorganizing structure.

**Recommendation**: Create refactoring plan, execute manually.

### external-dependency-issue

**Why Not Fixable**: Requires code changes to remove external dependencies.

**Recommendation**: Replace with stdlib alternatives.

## Categorization Algorithm

```python
def categorize(issue_type):
    SAFE = {
        "missing-frontmatter", "invalid-yaml", "missing-name-field",
        "missing-description-field", "missing-tools-field",
        "missing-user-invocable-field",
        "array-syntax-tools", "trailing-whitespace",
        "improper-indentation", "missing-blank-line-before-list",
        "rule-11-violation",         # Rule 11: additive Skill append
        "wrong-plan-parameter",      # PM-003: mechanical swap
        "missing-plan-parameter",    # PM-004: add required param
        "positional-argument",       # SCR-009: convert to named flag
        "camelcase-flag",            # SCR-010: rename to kebab-case
        "missing-subparser-required" # SCR-011: add required=True
    }
    RISKY = {
        "unused-tool-declared", "tool-not-declared",
        "rule-6-violation", "rule-7-violation", "rule-8-violation",
        "rule-9-violation",
        "pattern-22-violation", "backup-file-pattern",
        "ci-rule-self-update",
        "implicit-script-call",      # PM-001: needs param lookup
        "generic-api-reference",     # PM-002: needs script identification
        "invalid-contract-path"      # PM-005: path resolution needed
    }

    if issue_type in SAFE:
        return "safe"
    elif issue_type in RISKY:
        return "risky"
    else:
        return "risky"  # Default to risky for unknown types
```

## Fix Priority Order

When multiple fixes needed for same file:

1. **missing-frontmatter** (must exist for other fixes)
2. **invalid-yaml** (must be valid for field fixes)
3. **missing-*-field** (complete frontmatter - name, description, user-invocable, tools/allowed-tools)
4. **array-syntax-tools** (syntax normalization)
5. **trailing-whitespace** (cleanup)
6. **Rule violations** (architectural - Rules 6, 7, 8, 9, 11)
7. **Pattern violations** (behavioral - Pattern 22)
8. **pm-workflow violations** (PM-001 through PM-005 - script call compliance)
9. **Script argument violations** (SCR-009 through SCR-011 - argparse conventions)

## See Also

- `safe-fixes-guide.md` - Detailed safe fix strategies
- `risky-fixes-guide.md` - Risky fix handling
- `verification-guide.md` - Verifying fixes worked
