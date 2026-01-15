# General Development Rules

Core principles that guide all development work in CUI projects.

## Overview

These foundational rules apply across ALL development activities:
- Agent and command development
- Feature implementation
- Documentation creation
- Testing and quality assurance
- Architectural decisions

## Core Development Principles

### Principle 1: Ask When In Doubt

**Rule:** If in doubt, ask the user.

**When to Ask:**
- Uncertain about requirements or specifications
- Multiple valid approaches exist
- Unclear about user preferences or priorities
- Need clarification on acceptance criteria
- Ambiguous instructions or context

**When NOT to Ask:**
- Requirements are clear and unambiguous
- Best practices are well-established and documented
- Previous similar decisions provide clear guidance
- Standards and conventions clearly apply

**Examples:**

**❌ DON'T GUESS:**
```
User says: "Add error handling"
Agent thinks: "I'll add try-catch blocks everywhere"
WRONG: User might want specific error handling strategy
```

**✅ ASK FOR CLARIFICATION:**
```
User says: "Add error handling"
Agent asks: "What error handling approach would you prefer?
  1. Try-catch with logging
  2. Result pattern with error types
  3. Exception propagation to caller"
```

### Principle 2: Always Research Topics

**Rule:** Always research topics using the research-best-practices agent. The goal is to find the most recent best practices for a given technology or framework.

**When to Research:**
- Need current best practices for a technology/framework
- Unfamiliar with a specific library or approach
- Want to validate approach against industry standards
- Need to find latest recommendations (2025+)
- Evaluating different implementation options

**How to Research:**

**Use research-best-practices agent** (NOT web search tools directly):

```
Task:
  subagent_type: plan-marshall:research-best-practices
  description: Research {topic} best practices
  prompt: |
    Research current best practices for {specific topic}.

    Focus on:
    - Latest recommendations (2025+)
    - Industry standard approaches
    - Official documentation if available
    - Community consensus patterns
```

**DO NOT use these patterns** (outdated approaches):
- ❌ "Use MCP tools like Perplexity, DuckDuckGo" (Too generic, no structured research)
- ❌ "Search GitHub" (Not comprehensive, misses documentation)
- ❌ Direct WebSearch without structured analysis (Lacks synthesis)

**✅ ALWAYS use research-best-practices agent:**
- Structured comprehensive research
- Analyzes top 10+ sources
- Provides confidence levels
- Maintains reference trails
- Synthesizes findings from multiple sources

**Examples:**

**Researching Java Testing Practices:**
```
Task:
  subagent_type: plan-marshall:research-best-practices
  prompt: Research best practices for Java unit testing with JUnit 5
```

**Researching CDI Patterns:**
```
Task:
  subagent_type: plan-marshall:research-best-practices
  prompt: Research current CDI (Contexts and Dependency Injection) best practices for Quarkus applications
```

### Principle 3: Never Guess or Be Creative

**Rule:** If you cannot find best practices for a topic, ask the user.

**Prohibited Behaviors:**
- Guessing at requirements
- Making up standards or conventions
- Inventing approaches without research
- Being "creative" with unclear requirements

**Required Behaviors:**
- Ask for clarification when uncertain
- Research established best practices
- Follow documented standards
- Request user guidance when best practices unavailable

**Examples:**

**❌ WRONG (Guessing):**
```
Agent thinks: "User didn't specify test coverage, I'll aim for 50%"
```

**✅ CORRECT (Asking):**
```
Agent asks: "What test coverage threshold should I target?
CUI projects typically use 80% line/branch coverage."
```

### Principle 4: Use Proper Tools for File Operations

**Rule:** Always use Read, Write, Edit, Glob, Grep tools (NOT cat, tail, find, test, grep via Bash).

**Why This Matters:**
- Bash commands trigger user prompts for confirmation
- Non-prompting tools (Read, Write, Edit, Glob, Grep) execute automatically
- Agents/commands should run without interrupting users
- Better user experience and automated workflows

**Tool Selection Guide:**

| Operation | ✅ USE THIS | ❌ DON'T USE |
|-----------|------------|--------------|
| Find files by pattern | `Glob` | `find`, `ls` |
| Check if file exists | `Read` (with error handling) or `Glob` | `test -f`, `test -d` |
| Search file contents | `Grep` | `grep` via Bash, `awk` |
| Read file contents | `Read` | `cat`, `head`, `tail` |
| Write new file | `Write` | `echo >`, `cat <<EOF` |
| Edit existing file | `Edit` | `sed`, `awk` |

**Bash Should ONLY Be Used For:**
- Git operations (`git status`, `git commit`, etc.)
- Build commands (`mvn`, `./mvnw`, `npm`, etc.)
- Operations that truly require shell execution

**Detailed Patterns:**

For complete tool usage patterns, see the **diagnostic-patterns skill**:
```
Skill: plan-marshall:ref-development-standards
```

This skill provides:
- File discovery patterns
- Existence checking with error handling
- Content search patterns
- Result parsing strategies
- Non-prompting alternatives for all common operations

**Examples:**

**✅ File Discovery:**
```
Glob: pattern="**/*.java", path="src/main/java"
```

**❌ File Discovery (WRONG):**
```
Bash: find src/main/java -name "*.java"
```

**✅ Check File Exists:**
```
Read: file_path="path/to/file.java"
# Handle error gracefully if file doesn't exist
```

**❌ Check File Exists (WRONG):**
```
Bash: test -f "path/to/file.java"
```

**✅ Search Content:**
```
Grep: pattern="TODO", path="src/", output_mode="files_with_matches"
```

**❌ Search Content (WRONG):**
```
Bash: grep -r "TODO" src/
```

### Principle 5: Don't Proliferate Documents

**Rule:** Always use context-relevant documents. Never create a document without user approval.

**Decision Tree:**

1. **Need to document something?**
   - Search for existing relevant documents first
   - Use Read/Grep to find existing documentation
   - Check standard document locations (README.md, doc/*.adoc)

2. **Found existing document?**
   - Use and update existing document
   - Don't create a new one

3. **No existing document found?**
   - Ask user: "Should I create a new document or update existing {related document}?"
   - Get explicit approval before creating

**Examples:**

**❌ WRONG (Proliferating):**
```
Agent creates: "feature-overview.md"
(When README.md already has feature documentation)
```

**✅ CORRECT (Reusing):**
```
Agent: "I found feature documentation in README.md. Should I:
  1. Update README.md with new feature details
  2. Create separate feature-overview.md document"
```

### Principle 6: Never Add Dependencies Without User Approval

**Rule:** Always ask the user before adding a dependency.

**What Counts as a Dependency:**
- External libraries (Maven dependencies, npm packages)
- Frameworks (Spring, Quarkus, React)
- Tools (build tools, testing frameworks)
- Services (databases, message queues, caching)

**Required Approval Process:**

1. **Identify need for dependency**
2. **Research alternatives** using research-best-practices agent if needed
3. **Ask user** with specific recommendation:
   ```
   I need to add {functionality}. I recommend adding {dependency-name} because:
   - {reason 1}
   - {reason 2}

   Should I add this dependency?
   ```
4. **Wait for approval** before modifying pom.xml, package.json, etc.

**Examples:**

**❌ WRONG (Adding without approval):**
```
Agent modifies pom.xml:
<dependency>
  <groupId>com.google.guava</groupId>
  <artifactId>guava</artifactId>
</dependency>
```

**✅ CORRECT (Asking first):**
```
Agent: "I need collection utilities for {feature}. I recommend adding Google Guava because:
- Provides immutable collections
- Well-tested and widely used
- Actively maintained

Should I add Guava as a dependency?"
```

### Principle 7: Execute SlashCommand Workflows

**Rule:** When a SlashCommand expands, you MUST execute its workflow steps using actual tools.

**How SlashCommand Works:**

SlashCommand is fundamentally different from Task and Skill tools:

| Tool | Behavior | Your Role |
|------|----------|-----------|
| **Task** | Launches autonomous agent | Wait for agent's results |
| **Skill** | Loads standards/context | Reference loaded standards |
| **SlashCommand** | Expands workflow instructions | **EXECUTE the workflow steps** |

**When you call:**
```
SlashCommand: /plugin-doctor agents
```

**What happens:**
1. ✅ System shows: `<command-message>plugin-doctor is running…</command-message>`
2. ✅ Workflow expands with Step 1, Step 2, Step 3, etc.
3. ❌ **CRITICAL:** You must NOW EXECUTE these steps - don't just read and stop!

**How to Execute:**

**Step 1: Read the First Step**
```
### Step 1: Validate Parameters
Check that command-name is provided...
```

**Step 2: Execute It Using Actual Tools**
```
Glob: pattern="foo.md", path="marketplace/bundles/*/commands"
# Check result
# Set variables
# Continue to next step
```

**Step 3: Complete All Steps Sequentially**
- Execute Step 1 fully
- Then execute Step 2
- Continue through all steps
- Display final results

**Common Mistakes:**

**❌ WRONG (Reading without executing):**
```
Agent sees: SlashCommand expands with 10 workflow steps
Agent thinks: "Okay, I see the workflow"
Agent does: Nothing - just stops
RESULT: Command doesn't execute, user sees no changes
```

**✅ CORRECT (Executing the workflow):**
```
Agent sees: SlashCommand expands with 10 workflow steps
Agent does Step 1: Glob to find command file
Agent does Step 2: Skill to load standards
Agent does Step 3: Read the command file
... executes all 10 steps ...
Agent displays: Final results
RESULT: Command fully executed, changes applied
```

**Sequential Execution Required:**

**❌ NEVER run SlashCommands in parallel:**
```
SlashCommand: /command-1
SlashCommand: /command-2
SlashCommand: /command-3
# All three expand, but you can't execute 3 workflows simultaneously
```

**✅ ALWAYS run SlashCommands sequentially:**
```
SlashCommand: /command-1
... execute all steps of command-1 ...
... wait for completion ...

SlashCommand: /command-2
... execute all steps of command-2 ...
... wait for completion ...
```

**Examples:**

**Executing /plugin-doctor:**

1. SlashCommand expands → See Step 1: "Parse scope"
2. Execute Step 1:
   ```
   # Detect component type (agents/commands/skills)
   # Set scope to "agents"
   ```
3. Execute Step 2: "Load plugin-doctor skill"
   ```
   Skill: pm-plugin-development:plugin-doctor
   ```
4. Execute Step 3: Execute diagnosis scripts
   ```
   Bash: analyze-skill-structure.sh...
   ```
5. ... continue through all steps ...
6. Execute final step: Display diagnosis results

**Verification:**

After executing a SlashCommand workflow, you should have:
- ✅ Concrete results from each step (file paths, data, confirmations)
- ✅ Tool calls made for file operations (Read, Edit, Glob, etc.)
- ✅ Final output displayed to user
- ✅ Changes applied (if applicable)

**If you only have:**
- ❌ Knowledge of what the workflow does
- ❌ No actual tool calls made
- ❌ No concrete results

**Then you FAILED to execute - you only READ the workflow!**

## Workflow Integration

### When Starting Any Development Work

**Step 0: Load General Development Rules**

```
Skill: plan-marshall:ref-development-standards
```

This loads all core principles to guide your work.

**Step 1: Assess Uncertainty**

- Is anything unclear? → Ask user (Principle 1)
- Need best practices? → Research (Principle 2)
- Would I be guessing? → Ask user (Principle 3)

**Step 2: Plan File Operations**

- Use proper tools (Principle 4)
- For patterns, reference: `Skill: plan-marshall:ref-development-standards`

**Step 3: Check Document Needs**

- Search for existing documents first (Principle 5)
- Get approval before creating new (Principle 5)

**Step 4: Evaluate Dependencies**

- Identify dependency needs (Principle 6)
- Get approval before adding (Principle 6)

## Quick Reference

### Decision Matrix

| Situation | Action |
|-----------|--------|
| Uncertain about requirements | Ask user |
| Need current best practices | Use research-best-practices agent |
| Would need to guess | Ask user |
| File operations (find/read/search/write/edit) | See Principle 4 for complete tool selection guide |
| Need to create document | Ask user first |
| Need to add dependency | Ask user first |

### Key Agents and Skills

**research-best-practices agent** - For comprehensive web research:
```
Task:
  subagent_type: plan-marshall:research-best-practices
  prompt: Research {topic}
```

**diagnostic-patterns skill** - For detailed tool usage patterns:
```
Skill: plan-marshall:ref-development-standards
```

## Anti-Patterns

### ❌ DON'T: Guess at Requirements
```
User: "Add validation"
Agent: *adds generic validation without asking what to validate*
```

### ✅ DO: Ask for Clarification
```
User: "Add validation"
Agent: "What should I validate? (e.g., input format, business rules, data constraints)"
```

### ❌ DON'T: Use Outdated Research Methods
```
Agent: "Let me search GitHub for examples..."
```

### ✅ DO: Use Structured Research
```
Agent: "Using research-best-practices agent to find current best practices..."
```

### ❌ DON'T: Use Bash for File Operations
```
Bash: cat file.txt
Bash: find . -name "*.java"
```

### ✅ DO: Use Proper Tools
```
Read: file_path="file.txt"
Glob: pattern="**/*.java"
```

### ❌ DON'T: Create Documents Without Asking
```
Agent: *creates new-feature-guide.md*
```

### ✅ DO: Ask Before Creating
```
Agent: "Should I create new-feature-guide.md or add to existing README.md?"
```

### ❌ DON'T: Add Dependencies Silently
```
Agent: *adds library to pom.xml*
```

### ✅ DO: Request Approval
```
Agent: "I recommend adding {library} for {reason}. Should I add this dependency?"
```

## Quality Standards

Following these rules ensures:
- Clear communication with users
- Current, researched approaches
- No guessing or creative interpretation
- Proper tool usage (non-prompting)
- Minimal document proliferation
- Controlled dependency management

## Related Standards

- **diagnostic-patterns skill** - Detailed tool usage patterns for file operations
- **research-best-practices agent** - Structured web research for current best practices
- **planning skills** - Development workflow integration
- **pm-plugin-development skills** - Creating components following these principles

