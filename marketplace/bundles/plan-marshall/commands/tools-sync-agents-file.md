---
name: tools-sync-agents-file
description: Create or update project-specific agents.md file following OpenAI specification
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - WebFetch
  - AskUserQuestion
  - Task
---

# Create/Update Agents.md

Creates or updates project-specific agents.md following OpenAI specification.

## PARAMETERS

### Standard Parameters

**push** (optional)
- Automatically commits and pushes changes after successful execution
- Usage: `/plan-marshall:tools-sync-agents-file push`
- If omitted: Changes remain uncommitted for manual review

### Usage Examples

```bash
# Basic execution - creates/updates agents.md
/plan-marshall:tools-sync-agents-file

# Execute and auto-commit/push changes
/plan-marshall:tools-sync-agents-file push
```

## PARAMETER VALIDATION

**Step: Validate Parameters**

1. Check if `push` parameter is provided
   - Store as boolean flag for later use
   - Valid values: presence of word "push" anywhere in arguments

2. Reject any unrecognized parameters
   - Only `push` is valid
   - Display error and exit if invalid parameters found

## WORKFLOW INSTRUCTIONS

### PRE-CONDITION VERIFICATION

**Step 0: Verify Pre-Conditions**

Before proceeding with the main workflow, verify:

1. **Git Repository Check**
   - Run: `git rev-parse --is-inside-work-tree`
   - If fails: Display error and exit
   - Error message: "This command requires the project to be a git repository"

### MAIN WORKFLOW

**Step 1: Research OpenAI agents.md Format**

1.1. Fetch OpenAI agents.md specification from https://github.com/openai/agents.md
   - Use WebFetch to retrieve specification
   - Store structure requirements for validation

1.2. **Error handling:** If WebFetch fails, use alternative research approach or proceed with basic structure (title, description, instructions)

**Step 2: Check Existing agents.md**

2.1. Check if agents.md exists in project root
   - Use Read tool on `./agents.md` (relative to project root)
   - If exists: Store current content for comparison
   - If not exists: Flag as "new creation" mode

**Step 3: Determine Source of Truth**

3.1. Check for CLAUDE.md
   - Use Read tool to check if `./CLAUDE.md` exists
   - If exists: Read its content

3.2. Ask user about CLAUDE.md usage (only if CLAUDE.md exists from Step 3.1)
   - If CLAUDE.md does NOT exist: Skip to Step 4
   - If CLAUDE.md exists: Use AskUserQuestion tool:
     - Question: "A CLAUDE.md file exists in the project. Should this be used as the primary source for agents.md content?"
     - Header: "Source Choice"
     - Options:
       1. "Yes, use CLAUDE.md" - Description: "Use CLAUDE.md as the most recent instruction set"
       2. "No, use other sources" - Description: "Analyze project and use doc/ai-rules.md or standards"
   - Store user's choice

**Step 4: Gather Content Sources**

4.1. Check for project-specific doc/ai-rules.md
   - Use Read tool on `./doc/ai-rules.md`
   - If exists:
     - Store content as PRIMARY content source
     - Skip to Step 4.3 (Note: file removed in Step 7)

4.2. If no project doc/ai-rules.md, check global standards
   - Check if creating new agents.md (from Step 2)
   - If creating new AND (no CLAUDE.md OR Step 3.2 chose "No, use other sources"):
     - Use Read tool on `~/git/plan-marshall/standards/ai-rules.md`
     - Store as BASELINE content source
     - **CRITICAL**: Never modify this global standards file

4.3. Analyze project for requirements
   - Use Task tool with Explore agent (thoroughness: "medium")
   - Goal: Understand project architecture, key files, technologies, conventions
   - Look for:
     - Build system (Maven, Gradle, npm, etc.)
     - Project structure and modules
     - Testing frameworks
     - Key technologies and dependencies
     - Coding standards or style guides

**Step 5: Create/Update agents.md**

5.1. Synthesize content from sources
   - Combine information from:
     - CLAUDE.md (if user selected in Step 3.2)
     - doc/ai-rules.md (if present) OR global standards baseline
     - Project analysis results (Step 4.3)
   - Organize according to OpenAI agents.md structure (from Step 1)

5.2. Apply structural standards
   - Follow format from https://github.com/openai/agents.md
   - Ensure all required sections present
   - Remove duplications
   - Maintain clear, concise language
   - Use proper markdown formatting

5.3. Write agents.md
   - If new creation: Use Write tool to create `./agents.md`
   - If update: Use Edit tool to update existing `./agents.md`
   - Ensure content is project-specific and actionable

**Error handling:** If Write/Edit fails, display error message with details and abort.

**Step 6: Review and Validate agents.md**

6.1. Review for quality
   - Read the generated agents.md using Read tool
   - Check against OpenAI structure requirements (Step 1)

6.2. Structural validation
   - Verify all required sections from OpenAI spec present
   - Check markdown formatting is valid
   - Ensure proper heading hierarchy
   - Validate links and references

6.3. Content validation
   - Confirm project-specific details are accurate
   - Verify technical information matches project reality
   - Check that guidelines are practical and actionable
   - Ensure no contradictions or conflicts

**Step 7: Cleanup doc/ai-rules.md and References**

7.1. Remove references to doc/ai-rules.md from project files
   - Use Grep tool to search for references: `doc/ai-rules\.md|ai-rules\.md`
   - For each file containing references, use Edit tool to update references to point to `agents.md`
   - Verify all references removed using Grep again

7.2. Remove doc/ai-rules.md file (if exists)
   - Check if doc/ai-rules.md exists using Glob
   - If exists: Remove using `rm ./doc/ai-rules.md` and verify deletion
   - If not exists: Skip to Step 8

**Error handling:** If Edit fails during reference updates, log error and continue with remaining files.

**Step 8: Commit and Push (if push parameter provided)**

8.1. If push parameter NOT provided
   - Display summary of changes
   - Inform user to review agents.md
   - Exit successfully

8.2. If push parameter provided
   - Commit all changes with message:
     ```
     docs: create/update agents.md

     - Generated agents.md following OpenAI agents.md specification
     - Sourced from [list sources used]
     - Removed deprecated doc/ai-rules.md [if existed]
     - Updated references in [list files] to point to agents.md

     agents.md is now the single source of truth for AI agent guidance.

     🤖 Generated with [Claude Code](https://claude.com/claude-code)

     Co-Authored-By: Claude <noreply@anthropic.com>
     ```
   - Push the commit
   - Display commit and push status

### POST-CONDITION VERIFICATION

**Step 9: Verify Success**

9.1. Confirm agents.md exists and is readable (abort if not)

9.2. Verify doc/ai-rules.md removal (if it existed in Step 4.1)
   - Check that `./doc/ai-rules.md` does NOT exist
   - If still exists: Display error and instruct to remove manually

9.3. Display completion summary
   - Created/updated: agents.md
   - Sources used: {list sources}
   - Files modified: {list files where references updated}
   - doc/ai-rules.md status: {removed/not present}

## CRITICAL RULES

### File Modification Constraints

- **ALLOWED modifications**:
  - `agents.md` (create or update)
  - `doc/ai-rules.md` (removed if exists - see Step 7)
  - `CLAUDE.md` (update references to `agents.md`)
  - Other project documentation files (update references to `agents.md`)
- **NEVER modify** `~/git/plan-marshall/standards/ai-rules.md` (read-only baseline)
- **NEVER create** additional documentation files beyond agents.md

### Content Quality Standards

- **ALWAYS ensure** agents.md is concise and focused
- **ALWAYS remove** duplicate or redundant information
- **ALWAYS verify** project-specific details are accurate
- **NEVER include** generic boilerplate unless necessary
- **ALWAYS maintain** clear, unambiguous language

### Structural Compliance

- **ALWAYS follow** OpenAI agents.md structure specification
- **ALWAYS include** all required sections from OpenAI spec
- **ALWAYS use** proper markdown formatting
- **NEVER skip** structural validation (Step 6.2)

### Source Prioritization

- **IF** doc/ai-rules.md exists AND user chooses "No, use other sources": Use as PRIMARY source
- **IF** user selects CLAUDE.md: Use as PRIMARY source
- **IF** no project sources: Use global standards as BASELINE only
- **ALWAYS** combine with project analysis results

### Pre/Post Condition Enforcement

- **MUST verify** project is git repository before starting
- **MUST confirm** agents.md exists and is structurally correct after completion
- **NEVER proceed** if pre-conditions fail
- **NEVER complete** if post-conditions not met

## TOOL USAGE

- **WebFetch**: Retrieve OpenAI agents.md specification
- **Read**: Check existing agents.md, CLAUDE.md, doc/ai-rules.md
- **Write/Edit**: Create or update agents.md
- **Grep**: Find doc/ai-rules.md references
- **Bash**: Remove doc/ai-rules.md file, verify git repository
- **Task**: Invoke Explore agent for project analysis
- **AskUserQuestion**: Query user about CLAUDE.md usage

## STATISTICS TRACKING

Track throughout workflow:
- `sources_used`: List of sources (CLAUDE.md, doc/ai-rules.md, project analysis)
- `files_modified`: Count of files updated with reference changes
- `doc_ai_rules_removed`: Boolean flag

## RELATED

- OpenAI agents.md specification: https://github.com/openai/agents.md
