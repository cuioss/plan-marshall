# General Development Rules

Core principles that guide all development work.

## Overview

These foundational rules apply across ALL development activities:
- Agent and command development
- Feature implementation
- Documentation creation
- Testing and quality assurance
- Architectural decisions

## Core Development Principles

### Boy Scout Rule

Leave code cleaner than you found it. When modifying a file, fix existing quality issues you encounter — poor naming, SRP violations, dead code, missing error handling, missing assertions, hardcoded test data, poor documentation. Never dismiss code smells with "not introduced by current changes" — always fix them. If fixes cascade beyond reasonable scope, stop and ask the user how to proceed.

This applies equally to production code, test code, and documentation.

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

**Example:** User says "Add error handling" → don't guess the strategy, ask: "What error handling approach would you prefer? (try-catch with logging, Result pattern, exception propagation)"

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

**Example:** Need Java testing best practices → spawn `plan-marshall:research-best-practices-agent` with prompt "Research best practices for Java unit testing with JUnit 5"

### Principle 3: Apply Judgment Within Constraints

**Rule:** Use good judgment, but don't invent requirements or conventions. When the path forward is unclear, research first, then ask the user.

**Use judgment for:**
- Choosing between well-established approaches when the result is equivalent
- Applying documented standards to specific situations
- Making reasonable implementation decisions within clear requirements

**Ask the user when:**
- Requirements are ambiguous or underspecified
- Multiple valid approaches exist with different trade-offs
- No established best practice exists for the situation
- The decision has significant downstream impact

**Example:** User says "Add validation" → don't guess, ask: "What should I validate? (input format, business rules, data constraints)"

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

For complete patterns including file operations, content search, and Bash safety rules, see `tool-usage-patterns.md`.

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

**Example:** Don't create `feature-overview.md` when README.md already covers features — ask the user whether to update the existing document or create a new one.

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

**Example:** Don't silently add Guava to pom.xml — ask: "I need collection utilities for {feature}. I recommend Google Guava because {reasons}. Should I add this dependency?"

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

