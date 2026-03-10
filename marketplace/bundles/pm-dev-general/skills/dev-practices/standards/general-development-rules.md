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

**DON'T GUESS:**
```
User says: "Add error handling"
Agent thinks: "I'll add try-catch blocks everywhere"
WRONG: User might want specific error handling strategy
```

**ASK FOR CLARIFICATION:**
```
User says: "Add error handling"
Agent asks: "What error handling approach would you prefer?
  1. Try-catch with logging
  2. Result pattern with error types
  3. Exception propagation to caller"
```

### Principle 2: Always Research Topics

**Rule:** Always research topics using the research-best-practices-agent. The goal is to find the most recent best practices for a given technology or framework.

**When to Research:**
- Need current best practices for a technology/framework
- Unfamiliar with a specific library or approach
- Want to validate approach against industry standards
- Need to find latest recommendations (2025+)
- Evaluating different implementation options

**How to Research:**

**Use research-best-practices-agent** (NOT web search tools directly):

```
Task:
  subagent_type: plan-marshall:research-best-practices-agent
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
- "Use MCP tools like Perplexity, DuckDuckGo" (Too generic, no structured research)
- "Search GitHub" (Not comprehensive, misses documentation)
- Direct WebSearch without structured analysis (Lacks synthesis)

**ALWAYS use research-best-practices-agent:**
- Structured comprehensive research
- Analyzes top 10+ sources
- Provides confidence levels
- Maintains reference trails
- Synthesizes findings from multiple sources

**Examples:**

**Researching Java Testing Practices:**
```
Task:
  subagent_type: plan-marshall:research-best-practices-agent
  prompt: Research best practices for Java unit testing with JUnit 5
```

**Researching CDI Patterns:**
```
Task:
  subagent_type: plan-marshall:research-best-practices-agent
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

**WRONG (Guessing):**
```
Agent thinks: "User didn't specify test coverage, I'll aim for 50%"
```

**CORRECT (Asking):**
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

| Operation | USE THIS | DON'T USE |
|-----------|----------|-----------|
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

For complete tool usage patterns, see the standards in this skill:
- `file-operations.md` — File discovery, existence checking, validation
- `search-operations.md` — Content search, pattern matching
- `tool-usage-patterns.md` — Tool selection guide, non-prompting alternatives

**Examples:**

**File Discovery:**
```
Glob: pattern="**/*.java", path="src/main/java"
```

**File Discovery (WRONG):**
```
Bash: find src/main/java -name "*.java"
```

**Check File Exists:**
```
Read: file_path="path/to/file.java"
# Handle error gracefully if file doesn't exist
```

**Check File Exists (WRONG):**
```
Bash: test -f "path/to/file.java"
```

**Search Content:**
```
Grep: pattern="TODO", path="src/", output_mode="files_with_matches"
```

**Search Content (WRONG):**
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

**WRONG (Proliferating):**
```
Agent creates: "feature-overview.md"
(When README.md already has feature documentation)
```

**CORRECT (Reusing):**
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
2. **Research alternatives** using research-best-practices-agent if needed
3. **Ask user** with specific recommendation:
   ```
   I need to add {functionality}. I recommend adding {dependency-name} because:
   - {reason 1}
   - {reason 2}

   Should I add this dependency?
   ```
4. **Wait for approval** before modifying pom.xml, package.json, etc.

**Examples:**

**WRONG (Adding without approval):**
```
Agent modifies pom.xml:
<dependency>
  <groupId>com.google.guava</groupId>
  <artifactId>guava</artifactId>
</dependency>
```

**CORRECT (Asking first):**
```
Agent: "I need collection utilities for {feature}. I recommend adding Google Guava because:
- Provides immutable collections
- Well-tested and widely used
- Actively maintained

Should I add Guava as a dependency?"
```

## Quick Reference

### Decision Matrix

| Situation | Action |
|-----------|--------|
| Uncertain about requirements | Ask user |
| Need current best practices | Use research-best-practices-agent |
| Would need to guess | Ask user |
| File operations (find/read/search/write/edit) | See Principle 4 for complete tool selection guide |
| Need to create document | Ask user first |
| Need to add dependency | Ask user first |

## Anti-Patterns

### DON'T: Guess at Requirements
```
User: "Add validation"
Agent: *adds generic validation without asking what to validate*
```

### DO: Ask for Clarification
```
User: "Add validation"
Agent: "What should I validate? (e.g., input format, business rules, data constraints)"
```

### DON'T: Use Outdated Research Methods
```
Agent: "Let me search GitHub for examples..."
```

### DO: Use Structured Research
```
Agent: "Using research-best-practices-agent to find current best practices..."
```

### DON'T: Use Bash for File Operations
```
Bash: cat file.txt
Bash: find . -name "*.java"
```

### DO: Use Proper Tools
```
Read: file_path="file.txt"
Glob: pattern="**/*.java"
```

### DON'T: Create Documents Without Asking
```
Agent: *creates new-feature-guide.md*
```

### DO: Ask Before Creating
```
Agent: "Should I create new-feature-guide.md or add to existing README.md?"
```

### DON'T: Add Dependencies Silently
```
Agent: *adds library to pom.xml*
```

### DO: Request Approval
```
Agent: "I recommend adding {library} for {reason}. Should I add this dependency?"
```
