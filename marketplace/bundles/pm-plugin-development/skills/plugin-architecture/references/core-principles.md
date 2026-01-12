# Claude Skills: Core Principles

Foundational principles for building Claude Skills based on official Claude Skills architecture.

**Source**: [Claude Skills Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/)

## Fundamental Concepts

### Skills as Prompt Modifiers

Skills are **specialized prompt templates that inject domain-specific instructions into conversation context**. They operate through prompt expansion and context modification, not traditional function calling.

**Key Insight**: Skills modify the LLM's execution context by injecting instructions, not by executing code directly.

**Implications**:
- Skills don't "run" like functions - they expand into prompts
- Decision-making happens within Claude's reasoning based on skill descriptions
- No algorithmic skill selection or AI-powered intent detection at code level
- LLM reads all skill descriptions and selects based on semantic understanding

### The Meta-Tool Architecture

A single tool named "Skill" (capital S) acts as a dispatcher for individual skills.

**How It Works**:
1. System presents available skills to Claude through dynamic prompt generation
2. Claude evaluates skill descriptions against user intent
3. Claude chooses appropriate skill(s) based on language understanding
4. System injects chosen skill content into conversation
5. Claude follows skill instructions

**Benefits**:
- More flexible than keyword matching or rule-based routing
- Context-aware skill selection
- Natural language matching without brittle logic
- Can select multiple skills if needed

## SKILL.md Structure

Every skill centers on a `SKILL.md` file with two required sections:

### 1. Frontmatter (YAML Configuration)

**Required Fields**:
- `name`: Skill identifier for invocation (hyphen-case, lowercase alphanumeric)
- `description`: Brief summary helping Claude match user intent

**Optional Fields**:
- `allowed-tools`: Comma-separated list of permitted tools
- `model`: Override default model selection
- `license`: Attribution information
- `disable-model-invocation`: Prevents automatic Claude selection

**Example**:
```yaml
---
name: my-skill
description: Brief summary of what the skill does and when Claude should use it
allowed-tools: [Read, Write, Bash]
---
```

**Guidelines**:
- **name**: Use hyphen-case (not camelCase or snake_case)
- **description**: Focus on WHEN to use skill, not just WHAT it does
- **allowed-tools**: Only include tools actually needed (security scoping)

### 2. Content (Markdown Instructions)

**Structure**:
- Purpose statement
- Overview
- Prerequisites (if any)
- Step-by-step instructions
- Output format expectations
- Error handling guidance
- Examples

**Language Style**: Use imperative commands, not conversational guidance.

**Good**:
```markdown
Analyze code for security vulnerabilities:
1. Search for SQL injection patterns
2. Check for XSS vulnerabilities
3. Validate input sanitization
```

**Bad**:
```markdown
You should analyze the code to look for any security issues that might be present,
such as SQL injection or XSS vulnerabilities, and maybe check if inputs are sanitized.
```

**Size Limit**: Keep SKILL.md under 5,000 words (~800 lines) to prevent overwhelming context.

## The Relative Path Pattern

**Critical Principle**: Use relative paths from the skill directory for all resource paths. Never hardcode absolute paths.

### Why Relative Paths Matter

Skills can be installed in different locations:
- User settings: `~/.claude/skills/`
- Project directory: `.claude/skills/`
- Plugin bundles: `marketplace/bundles/{bundle}/skills/`

Using relative paths ensures the skill works in all contexts. When a skill is loaded, Claude knows its installation directory and resolves relative paths from there.

### Relative Path Usage

All paths in SKILL.md are relative to the skill's directory.

**Examples**:
```markdown
Read references/guide.md
bash scripts/analyzer.py
python scripts/processor.py input.txt
Load template: assets/template.html
```

### Relative Path Best Practices

**Always**:
- Use relative paths for scripts: `bash scripts/script.sh`
- Use relative paths for references: `Read references/guide.md`
- Use relative paths for assets: `Load: assets/template.html`

**Never**:
- Hardcode absolute paths: `~/git/project/scripts/script.sh`
- Use relative traversal: `../../../../scripts/script.sh`
- Assume installation location: `.claude/skills/my-skill/script.sh`

### Testing Portability

Test skills in different installation contexts:
1. Global installation: `~/.claude/skills/my-skill/`
2. Project installation: `.claude/skills/my-skill/`
3. Bundle installation: `marketplace/bundles/{bundle}/skills/my-skill/`

Verify relative paths resolve correctly in each context.

## Resource Organization

### Standard Directory Structure

```
my-skill/
├── SKILL.md                    (Required: entrypoint)
├── scripts/                    (Optional: executable automation)
│   ├── analyzer.py
│   └── validator.sh
├── references/                 (Optional: detailed documentation)
│   ├── detailed-guide.md
│   └── patterns-library.md
└── assets/                     (Optional: templates and binaries)
    ├── template.html
    └── config-example.json
```

### Directory Purposes

**scripts/**:
- Executable Python/Bash scripts
- Automation scripts, data processors, validators, code generators
- Deterministic logic that Claude orchestrates
- Output structured data (JSON/XML) for Claude to interpret

**references/**:
- Text content loaded into Claude's context on-demand
- Detailed documentation, large pattern libraries, checklists
- Loaded via `Read references/file.md`
- Can be any size (loaded progressively)

**assets/**:
- Templates and binary files that Claude references by path
- HTML/CSS templates, images, configuration boilerplate
- Claude generates content using these as templates
- Not loaded into context - used as input to scripts or templates

### When to Use Which Directory

**Use scripts/** when:
- Logic is deterministic and complex
- Need fast, consistent execution
- Parsing structured data
- Generating reports or inventories
- Validation that doesn't require judgment

**Use references/** when:
- Content is documentation or knowledge
- Claude needs to interpret and apply
- Information should load on-demand
- Content helps Claude make decisions

**Use assets/** when:
- Files are templates for generation
- Binary files (images, configs)
- Used as input to scripts
- Referenced by path, not loaded into context

## Progressive Disclosure

**Principle**: Minimize initial information load. Load details only when needed.

### Three-Level Loading

1. **Frontmatter** (~2-3 lines)
   - Minimal metadata for skill discovery
   - Only name and description loaded initially
   - Helps Claude decide whether to select skill

2. **SKILL.md** (~400-800 lines)
   - Full instructions loaded only after skill selection
   - Contains workflow steps and reference pointers
   - Never loads all references upfront

3. **References** (unlimited size)
   - Loaded on-demand when workflow reaches specific step
   - Can be thousands of lines
   - Only loads what's needed for current step

### Progressive Loading Pattern

**In SKILL.md**:
```markdown
## Step 1: Analyze Code

For detailed quality standards, load reference:
Read references/quality-standards.md

# Only loads when Step 1 executes, not upfront
```

**Benefits**:
- Reduces context usage by 60-80% compared to eager loading
- Allows very large knowledge bases
- Claude only sees what's relevant to current step
- Faster skill selection (smaller frontmatter)

### Design for Progressive Disclosure

**Anti-Pattern** (Eager Loading):
```yaml
---
name: code-analyzer
description: |
  Analyzes code for quality issues.

  Quality Standards:
  - Standard 1: Detailed explanation...
  - Standard 2: Detailed explanation...
  - Standard 3: Detailed explanation...
  [5000 lines of standards in frontmatter]
---
```

**Good Pattern** (Progressive):
```yaml
---
name: code-analyzer
description: Analyzes code for quality issues using on-demand quality standards
---

# Code Analyzer

## Step 1: Load Quality Standards

Read references/quality-standards.md

# Loaded only when skill executes, not during selection
```

## Tool Permissions

### Scope Carefully

**Principle**: Only include tools your skill actually needs.

**Why**:
- Security: Limits what skill can do
- Clarity: Shows skill's capabilities
- Validation: Can verify skill doesn't exceed permissions

**Examples**:
- Analysis skill: `[Read, Grep, Glob]`
- Code generation: `[Read, Write, Edit]`
- Build automation: `[Read, Write, Bash]`
- Diagnostic: `[Read, Bash, Grep, Glob]`
- Reference library: `[Read]` only

### allowed-tools Frontmatter

```yaml
---
name: my-skill
description: Analyzes code for quality issues
allowed-tools: [Read, Grep, Glob]
---
```

When this skill is invoked, only the listed tools are pre-approved.

**Permissions are scoped** to the skill invocation, not persisting globally.

### Choosing Tools

**Ask**:
- Does skill need to read files? → `Read`
- Does skill need to search content? → `Grep`
- Does skill need to find files? → `Glob`
- Does skill need to modify files? → `Edit` or `Write`
- Does skill need to run commands? → `Bash`
- Does skill invoke other skills? → `Skill`
- Does skill ask user questions? → `AskUserQuestion`

**Include only what's actually used** - Don't request tools "just in case".

## Scripts for Deterministic Logic

### Separation of Concerns

**Principle**: Execute deterministic logic in scripts while Claude processes results.

**What Goes in Scripts**:
- File parsing and analysis
- Data transformation
- Validation checks
- Report generation
- Inventory scanning
- Complex algorithms

**What Stays in SKILL.md**:
- Workflow orchestration
- Context interpretation
- Decision making
- User interaction
- Quality judgment

### Script Execution Pattern

**In SKILL.md**:
```markdown
## Step 2: Analyze File Structure

bash scripts/analyze-structure.sh {file_path}

# Script outputs JSON
# Claude interprets the JSON and makes decisions
```

**Script Output** (structured data):
```json
{
  "status": "success",
  "findings": [
    {"type": "missing-section", "severity": "high"},
    {"type": "outdated-reference", "severity": "low"}
  ],
  "metrics": {
    "total_lines": 350,
    "complexity_score": 7.2
  }
}
```

**Claude's Role**:
- Interpret JSON findings
- Apply judgment to severity
- Decide next actions
- Format user-friendly output

### Benefits

**Faster execution**: Native code vs LLM generation
**Consistent results**: Deterministic algorithms
**Easier testing**: Standard unit tests for scripts
**Separation of concerns**: Logic (script) vs orchestration (Claude)

### Script Best Practices

**Output Format**: Always JSON for structured parsing
**Error Handling**: Return error status in JSON, don't fail silently
**Documentation**: Include script usage in SKILL.md
**Testing**: Write unit tests for scripts
**Portability**: Use relative paths in script paths

## Dual-Message Pattern

Skills inject two user messages into conversation:

### 1. Visible Message (User-Facing)
- `isMeta: false`
- Shows metadata to user for transparency
- Brief notification of skill activation

**User sees**:
```
🎯 Skill loaded: code-analyzer
Purpose: Analyzes code for quality issues
```

### 2. Hidden Message (Claude-Facing)
- `isMeta: true`
- Provides full instructions to Claude
- Contains complete SKILL.md content

**Claude sees** (additionally):
```markdown
# Code Analyzer Skill

Complete instructions for analyzing code...
[Full SKILL.md content]
```

**Purpose**: Separates human-facing transparency from AI-facing guidance.

## Execution Context Modification

Beyond conversation injection, skills modify execution context:

**Pre-approve specific tools**: `allowed-tools` list
**Override model selection**: `model` field (optional)
**Scope permissions**: Tools available only during skill invocation

**Important**: Permissions are scoped to the skill invocation, not persisting globally.

## Skill Discovery

### Discovery Process

System scans multiple sources and aggregates skills:
1. User settings: `~/.claude/skills/`
2. Project directories: `.claude/skills/`
3. Plugins: `marketplace/bundles/{bundle}/skills/`
4. Built-in skills

**Character Budget Constraints**: Skills are loaded with character limits to prevent context overflow.

### Skill Selection Process

1. **Discovery**: System scans all skill locations
2. **Metadata Extraction**: Reads YAML frontmatter
3. **Description Matching**: Claude evaluates descriptions against user intent
4. **Selection**: Claude chooses appropriate skill(s)
5. **Injection**: System injects skill content into conversation
6. **Context Modification**: Applies tool permissions and model overrides
7. **Execution**: Claude follows skill instructions

## Best Practices Summary

### 1. Progressive Disclosure
- Minimize upfront information
- Load references on-demand
- Keep SKILL.md under 800 lines

### 2. Relative Paths for Portability
- Always use relative paths
- Never hardcode absolute paths
- Test in different installation contexts

### 3. Scope Permissions Carefully
- Only request needed tools
- Use `allowed-tools` frontmatter
- Avoid unnecessary tool surface area

### 4. Scripts for Deterministic Logic
- Move complex logic to scripts
- Output structured data (JSON)
- Claude orchestrates and interprets

### 5. Keep Prompts Focused
- SKILL.md under 5,000 words
- Single, clear purpose
- Reference external files for details

### 6. Use Imperative Language
- Direct commands ("Analyze...")
- Not conversational ("You should...")
- Clear, actionable steps

### 7. Organize Resources Properly
- scripts/ for automation
- references/ for documentation
- assets/ for templates

### 8. Enable Composition
- Narrow skill focus
- Skills can invoke other skills
- Build complex capabilities from simple skills

## Anti-Patterns to Avoid

### ❌ Hardcoded Paths
Never use absolute paths or relative traversal (`../../../../`).

**Why**: Breaks when skill installed in different location.

**Fix**: Use relative paths.

### ❌ Eager Loading
Loading all references in SKILL.md upfront.

**Why**: Wastes context, slow skill selection.

**Fix**: Load references on-demand when workflow reaches specific step.

### ❌ Over-Permissioning
Requesting more tools than needed.

**Why**: Security risk, unclear capabilities.

**Fix**: Only request tools actually used.

### ❌ Large SKILL.md
Embedding all documentation in main file.

**Why**: Context overflow, slow skill selection.

**Fix**: Move detailed content to references/, load on-demand.

### ❌ Conversational Instructions
Vague, conversational guidance.

**Why**: Ambiguous, hard to follow.

**Fix**: Use imperative commands, clear steps.

### ❌ Universal Mega-Skills
Trying to do everything in one skill.

**Why**: Hard to maintain, violates progressive disclosure.

**Fix**: Narrow focus, compose multiple skills for complex tasks.

## References

- Claude Skills Deep Dive: https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/
- Anthropic Agent Skills Spec: agent_skills_spec.md
- Claude Code Plugin Documentation: https://docs.claude.com/en/docs/claude-code/plugins
