# Minimal Wrapper Pattern

## Overview

The **Minimal Wrapper Pattern** solves context handling challenges in AI assistants by reintroducing agents and commands as thin orchestration layers (< 150 lines) that delegate all business logic to specialized skills.

This pattern enables context isolation while maintaining clean separation of concerns.

## Problem Statement

### Pure Skill-Based Architecture Challenges

After migrating business logic from agents to skills, several context issues emerged:

**Context Pollution:**
- Skills loaded into main conversation context
- All skill knowledge accumulates in single context window
- Multiple large skills competing for limited context space
- No isolation between different tasks

**What Doesn't Work:**
- ❌ Agent-to-agent calls (architectural limitation in Claude Code)
- ❌ Pure skill delegation without wrappers (context pollution)
- ❌ Fat agents with embedded business logic (maintenance nightmare)

**What Does Work:**
- ✅ Agents calling skills (context isolation achieved)
- ✅ Commands calling skills (self-contained execution)
- ✅ Skills calling other skills (composition within isolated context)

## Solution: Minimal Wrapper Pattern

Reintroduce agents and commands as **thin orchestration wrappers** that:

1. **Parse user intent and parameters** (< 30 lines)
2. **Validate prerequisites** (build state, file existence) (< 20 lines)
3. **Delegate to specialized skills** for actual work (< 50 lines)
4. **Return structured results** to user (< 50 lines)

**Key Constraint**: Wrapper complexity < 150 lines total; all business logic lives in skills.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                          USER GOAL                          │
│              (e.g., "Implement feature X")                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   MINIMAL WRAPPER AGENT                      │
│                    (< 150 lines)                            │
│                                                              │
│  Responsibilities:                                          │
│  • Parse parameters and validate input                      │
│  • Determine user intent and goal                           │
│  • Check preconditions (build state, files exist)          │
│  • Select appropriate skill workflows                       │
│  • Invoke skill(s) with structured parameters              │
│  • Format and return results                                │
│                                                              │
│  Does NOT contain:                                          │
│  • Standards knowledge (lives in skills)                    │
│  • Implementation logic (lives in skills)                   │
│  • Verification logic (lives in skills)                     │
│  • Build/test knowledge (delegated to skills)              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼ Skill(goal-specific-skill)
┌─────────────────────────────────────────────────────────────┐
│                    SPECIALIZED SKILL                         │
│                  (Isolated Context)                         │
│                                                              │
│  Contains:                                                  │
│  • All standards knowledge for the domain                   │
│  • Step-by-step workflows                                   │
│  • Verification logic                                       │
│  • Quality checklists                                       │
│  • Integration with other skills                            │
│                                                              │
│  Skills can call other skills:                             │
│    Skill(pm-dev-builder:builder-maven-rules)                        │
│    Skill(plan-marshall:script-runner)                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Why This Pattern Works

### Context Isolation
- **Agent spawns in separate context** - skill knowledge loaded fresh per invocation
- **No context pollution** between different agent invocations
- **Scalable** - can have many specialized agents without context competition
- **Memory efficient** - only load knowledge needed for current goal

### Clear Separation of Concerns

**Agents (< 150 lines):**
- Intent parsing
- Parameter validation
- Orchestration
- Result formatting

**Commands (< 150 lines):**
- Parameter parsing
- Self-contained execution
- Iteration logic
- Result reporting

**Skills (400-800 lines):**
- Standards knowledge
- Workflows
- Business logic
- Verification
- Quality checklists

### Communication Pattern ✅

```
User → Agent (thin wrapper) → Skill (business logic) → Result
```

This pattern works because:
1. Agent spawns in isolated context
2. Skill loads in that isolated context
3. Skill knowledge doesn't pollute main conversation
4. Agent returns result and context is released

### What We Avoid ❌

```
User → Agent A → Agent B → Agent C  (doesn't work - no agent-to-agent calls)
User → Skill → Skill → Skill        (context pollution - no isolation)
User → Fat Agent (500+ lines)       (maintenance nightmare)
```

## Implementation Patterns

### Pattern 1: Minimal Command Wrapper

**Purpose**: Self-contained operations with clear inputs/outputs

**Structure**:
```markdown
---
name: java-create-feature
description: Create new feature with implementation and tests
---

# Java Create Feature Command

## PARAMETERS
- **description** (required): Feature description and requirements
- **module** (optional): Module name for multi-module projects

## WORKFLOW

### Step 1: Parse and Validate Parameters (< 30 lines)
1. Validate description is clear and complete
2. Verify module exists (if specified)
3. Check build precondition is clean

### Step 2: Delegate to Implementation Skill (< 50 lines)
```
Skill: cui-java-core
Workflow: implement-feature
Parameters:
  description: {description}
  module: {module}
```

### Step 3: Delegate to Testing Skill (< 50 lines)
```
Skill: cui-java-unit-testing
Workflow: create-tests
Parameters:
  types: {implemented_types}
  module: {module}
```

### Step 4: Verify and Return Results (< 20 lines)
1. Format implementation summary
2. Format test coverage summary
3. Return structured result to user

## CRITICAL RULES
- Agent orchestrates only - no business logic
- All standards knowledge in skills
- All verification logic in skills
- Maximum 150 lines total
```

**Line Budget:**
- Step 1: 30 lines (validation)
- Step 2: 50 lines (skill delegation)
- Step 3: 50 lines (skill delegation)
- Step 4: 20 lines (result formatting)
- **Total**: 150 lines

### Pattern 2: Minimal Agent Wrapper

**Purpose**: Interactive exploration with user guidance

**Structure**:
```markdown
---
name: java-diagnose-agent
description: Diagnose Java code quality and coverage issues
allowed-tools: [Glob, Read, Grep]
---

# Java Diagnose Agent

**PURPOSE**: Analyze Java code for quality issues, coverage gaps, and standards violations.

## WORKFLOW

### Step 1: Identify Analysis Scope (< 30 lines)
1. Use Glob to find Java files
2. Read user request to determine focus area
3. Identify module if multi-module project

### Step 2: Delegate to Diagnostic Skills (< 70 lines)

For coverage analysis:
```
Skill: cui-java-unit-testing
Workflow: analyze-coverage-gaps
Parameters:
  report_path: {jacoco_xml}
  priority_filter: high
```

For quality analysis:
```
Skill: cui-java-core
Workflow: analyze-quality
Parameters:
  files: {java_files}
  module: {module}
```

### Step 3: Synthesize and Report (< 50 lines)
1. Combine results from multiple skills
2. Prioritize issues by severity
3. Return actionable recommendations

## CRITICAL RULES
- Agent coordinates analysis only
- Skills contain quality standards
- Skills perform actual analysis
- Maximum 150 lines total
```

**Line Budget:**
- Step 1: 30 lines (scope identification)
- Step 2: 70 lines (skill delegation)
- Step 3: 50 lines (synthesis)
- **Total**: 150 lines

## Skill Invocation Patterns

### From Commands (Self-Contained)

```markdown
Skill: cui-java-core
Workflow: implement-code
Parameters:
  description: "Add JWT validation"
  types: ["com.example.TokenValidator"]
  module: "auth-service"
```

**Characteristics:**
- Single skill invocation per step
- Structured parameters
- Clear workflow selection
- Self-contained execution

### From Agents (Interactive)

```markdown
Skill: cui-java-unit-testing
Workflow: analyze-coverage-gaps
Parameters:
  report_path: "target/site/jacoco/jacoco.xml"
  priority_filter: "high"
```

**Characteristics:**
- May invoke multiple skills
- Interactive parameter gathering
- Conversational flow
- Result synthesis

### Chained Skill Calls (Within Skills)

```markdown
# Inside cui-java-core skill:

Step 3: Verify Build
Skill: pm-dev-builder:builder-maven-rules
Workflow: Execute Maven Build
Parameters:
  goals: "clean test"
  module: {module}
  output_mode: structured
```

**Characteristics:**
- Skills compose other skills
- Dependency chain
- Isolated within skill context
- Reusable across agents/commands

## Line Budget Guidelines

### Command Wrapper Budget (150 lines max)

**Parameter Parsing** (20-30 lines):
- Frontmatter (5 lines)
- Parameter documentation (10-15 lines)
- Parse and validate logic (5-10 lines)

**Orchestration** (70-90 lines):
- Workflow steps (40-50 lines)
- Skill invocations (20-30 lines)
- Error handling (10 lines)

**Result Formatting** (30-40 lines):
- Success response format (20-25 lines)
- Error response format (10-15 lines)

**Critical Rules Section** (10 lines)

### Agent Wrapper Budget (150 lines max)

**Scope Identification** (30-40 lines):
- Tool usage (Glob/Read/Grep) (15-20 lines)
- Context gathering (10-15 lines)
- User clarification (5 lines)

**Skill Delegation** (60-80 lines):
- Primary skill invocation (25-35 lines)
- Secondary skill invocations (20-30 lines)
- Parameter mapping (15-20 lines)

**Synthesis** (40-50 lines):
- Result aggregation (20-25 lines)
- Prioritization logic (10-15 lines)
- Recommendation generation (10 lines)

**Critical Rules Section** (10 lines)

## Benefits of Minimal Wrapper Pattern

### For Context Management
- ✅ Each agent spawns with isolated context
- ✅ Skills loaded only when needed
- ✅ No cross-contamination between tasks
- ✅ Scalable to many specialized agents
- ✅ Predictable memory usage

### For Maintainability
- ✅ Business logic centralized in skills
- ✅ Wrappers are simple and easy to understand
- ✅ Standards updates happen in one place (skills)
- ✅ Clear separation of concerns
- ✅ Easy to test independently

### For User Experience
- ✅ Goal-based commands match user intent
- ✅ Specialized agents for specific tasks
- ✅ Consistent structured output
- ✅ Clear delegation model
- ✅ Predictable behavior

### For Development
- ✅ Easy to add new agents (copy pattern)
- ✅ Easy to test (thin wrappers)
- ✅ Easy to debug (clear delegation)
- ✅ Skills reusable across agents
- ✅ Parallel development possible

## Anti-Patterns to Avoid

### ❌ Fat Wrappers (> 150 lines)

**Problem:**
```markdown
# BAD: Agent contains 500 lines of standards knowledge
# BAD: Command implements complex verification logic
# BAD: Wrapper duplicates skill functionality
```

**Why Bad:**
- Context pollution (defeats purpose)
- Maintenance burden (logic in two places)
- Hard to test (too much responsibility)
- Not reusable (logic locked in wrapper)

**Solution:**
```markdown
# GOOD: Agent validates and delegates (< 150 lines)
# GOOD: All standards in skill (single source)
# GOOD: Wrapper orchestrates only
```

### ❌ Agent-to-Agent Calls

**Problem:**
```markdown
# BAD: Agent calling another agent
Agent: java-create-agent
  └─→ Agent: java-test-agent (doesn't work)
```

**Why Bad:**
- Not supported by Claude Code architecture
- Context confusion
- Unpredictable behavior
- No isolation benefits

**Solution:**
```markdown
# GOOD: Agent uses skills for work
Agent: java-create-agent
  ├─→ Skill: cui-java-core
  └─→ Skill: cui-java-unit-testing
```

### ❌ Duplicate Logic

**Problem:**
```markdown
# BAD: Same verification logic in agent AND skill
Agent: validates build state (50 lines)
Skill: validates build state (50 lines)
```

**Why Bad:**
- Maintenance nightmare (update two places)
- Inconsistency risk (versions drift)
- Wasted context (duplicate loading)

**Solution:**
```markdown
# GOOD: Verification only in skill
Agent: checks if verification needed
Skill: performs actual verification
```

### ❌ Direct Tool Usage for Business Logic

**Problem:**
```markdown
# BAD: Agent implements complex Maven parsing
Agent reads Maven log, parses errors, categorizes... (100 lines)
```

**Why Bad:**
- Business logic in wrapper (wrong layer)
- Not reusable (locked in agent)
- Hard to test (mixed concerns)

**Solution:**
```markdown
# GOOD: Agent delegates to builder-maven skill
Agent: Skill: pm-dev-builder:builder-maven-rules
       Workflow: parse-build-output
```

## Correct Patterns (Best Practices)

### ✅ Thin Orchestration

```markdown
# GOOD: Agent validates, delegates, returns (< 150 lines)

Step 1: Validate Parameters (30 lines)
  - Check description is clear
  - Verify module exists
  - Confirm build precondition

Step 2: Delegate to Skill (50 lines)
  Skill: cui-java-core
  Workflow: implement-feature
  Parameters: {validated}

Step 3: Format and Return (20 lines)
  - Success summary
  - Files modified
  - Standards compliance
```

**Why Good:**
- Clear separation of concerns
- Reusable business logic (in skill)
- Easy to test (thin wrapper)
- Context efficient (< 150 lines)

### ✅ Agent-to-Skill Delegation

```markdown
# GOOD: Agent uses skills for work

Agent: java-create-agent (120 lines)
  ├─→ Skill: cui-java-core (600 lines)
  │   └─→ Skill: pm-dev-builder:builder-maven-rules (400 lines)
  └─→ Skill: cui-java-unit-testing (500 lines)
      └─→ Skill: pm-dev-builder:builder-maven-rules (400 lines)
```

**Why Good:**
- Context isolation (agent spawns separately)
- Skills compose naturally
- Reusable across agents
- Clean delegation hierarchy

### ✅ Single Source of Truth

```markdown
# GOOD: Standards only in skills

Agent (thin wrapper - 100 lines):
  - Parse parameters
  - Validate inputs
  - Delegate to skill

Skill (business logic - 600 lines):
  - Standards knowledge
  - Verification logic
  - Quality checklists
  - Implementation patterns
```

**Why Good:**
- Update standards once (in skill)
- All agents benefit from updates
- Consistent behavior
- Easy maintenance

### ✅ Skill-to-Skill Composition

```markdown
# GOOD: Skills coordinate other skills

Skill: cui-java-core (600 lines)
  Step 3: Verify Build
    Skill: pm-dev-builder:builder-maven-rules
    Workflow: Execute Maven Build

  Step 7: Run Tests
    Skill: pm-dev-builder:builder-maven-rules
    Workflow: Execute Maven Build

  Step 9: Analyze Coverage
    Skill: cui-java-unit-testing
    Workflow: analyze-coverage-gaps
```

**Why Good:**
- Reusable composition
- Isolated within skill context
- Clear dependency chain
- Testable independently

## Integration with Goal-Based Organization

Minimal wrapper pattern complements goal-based organization:

**Goal-Based Structure:**
- Organize agents/commands by user goals (CREATE, DIAGNOSE, FIX, REFACTOR, VERIFY)
- Each goal has specialized wrappers
- All wrappers delegate to same skill set

**Minimal Wrapper Pattern:**
- Each wrapper is thin (< 150 lines)
- Wrappers parse intent and delegate
- Skills contain domain knowledge
- Context isolation per invocation

**Combined Benefits:**
```
User Goal → Goal-Based Agent (< 150 lines, context isolated)
              ↓
          Specialized Skill (600 lines, loaded on-demand)
              ↓
          Result (context released)
```

### Example: CREATE Goal

```
CREATE Goal Structure:
├─ java-create-agent (120 lines) → cui-java-core skill
├─ /java-create-feature (145 lines) → cui-java-core + cui-java-unit-testing
├─ /java-create-tests (135 lines) → cui-java-unit-testing
└─ /java-create-class (80 lines) → cui-java-core

All delegate to same skills, all maintain context isolation.
```

## Migration Guide

### From Fat Agents to Minimal Wrappers

**Before (Fat Agent - 500 lines):**
```markdown
Agent: java-create-agent (500 lines)
  - Standards knowledge (200 lines)
  - Implementation logic (150 lines)
  - Verification logic (100 lines)
  - Result formatting (50 lines)
```

**After (Minimal Wrapper + Skill):**
```markdown
Agent: java-create-agent (120 lines)
  - Parse parameters (30 lines)
  - Delegate to skill (50 lines)
  - Format results (40 lines)

Skill: cui-java-core (600 lines)
  - Standards knowledge (200 lines)
  - Implementation logic (200 lines)
  - Verification logic (150 lines)
  - Quality checklists (50 lines)
```

**Benefits:**
- Agent: 500 → 120 lines (76% reduction)
- Skill reusable across all agents
- Context isolation achieved
- Maintenance simplified

### Migration Steps

1. **Identify Fat Agents** (> 150 lines)
2. **Extract Business Logic** to skills
3. **Create Minimal Wrapper** (< 150 lines)
4. **Test Delegation** pattern
5. **Verify Context Isolation**
6. **Document New Structure**

## Quality Checklist

Use this checklist to verify minimal wrapper compliance:

### Wrapper Quality (Agents/Commands)
- [ ] Total lines < 150 (including comments)
- [ ] No standards knowledge (delegated to skills)
- [ ] No implementation logic (delegated to skills)
- [ ] No verification logic (delegated to skills)
- [ ] Clear parameter parsing (< 30 lines)
- [ ] Structured skill invocation (< 70 lines)
- [ ] Clean result formatting (< 50 lines)
- [ ] No duplicate logic from skills

### Delegation Quality
- [ ] All business logic in skills
- [ ] Clear skill workflow selection
- [ ] Structured parameters passed
- [ ] Result properly formatted
- [ ] Error handling delegated
- [ ] No agent-to-agent calls

### Context Isolation
- [ ] Agent spawns separately
- [ ] Skills load on-demand
- [ ] No context pollution
- [ ] Predictable memory usage
- [ ] Clean context release

### Maintainability
- [ ] Single source of truth (skills)
- [ ] Easy to test (thin wrapper)
- [ ] Easy to debug (clear flow)
- [ ] Reusable skills
- [ ] Clear separation of concerns

## Real-World Example

### Before: Fat Agent (500 lines)

```markdown
---
name: java-implement-agent
description: Implement Java features
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# Java Implement Agent

## Standards (200 lines of embedded knowledge)
- Java coding standards
- Testing standards
- Build requirements
- Coverage thresholds

## Workflow (300 lines of implementation)
1. Parse requirements (50 lines)
2. Implement code (100 lines of logic)
3. Create tests (100 lines of logic)
4. Verify build (50 lines of Maven logic)

## Total: 500 lines
```

**Problems:**
- Standards embedded (not reusable)
- Implementation logic in agent (wrong layer)
- Context pollution (always loaded)
- Hard to maintain (large file)

### After: Minimal Wrapper + Skills (120 + 600 lines)

**Agent (120 lines):**
```markdown
---
name: java-create-agent
description: Create Java features with implementation and tests
allowed-tools: [Glob, Read, Grep, AskUserQuestion]
---

# Java Create Agent

## Workflow (120 lines total)

### Step 1: Parse Requirements (30 lines)
1. Read user request
2. Use Glob/Grep to understand scope
3. Ask clarifying questions if needed

### Step 2: Delegate to Implementation Skill (40 lines)
```
Skill: cui-java-core
Workflow: implement-feature
Parameters:
  description: {parsed_description}
  module: {identified_module}
```

### Step 3: Delegate to Testing Skill (30 lines)
```
Skill: cui-java-unit-testing
Workflow: create-tests
Parameters:
  types: {implemented_types}
  module: {module}
```

### Step 4: Return Results (20 lines)
Format and return comprehensive summary
```

**Skill: cui-java-core (600 lines):**
```markdown
# CUI Java Core Skill

## Standards (200 lines)
- Java coding standards
- Implementation patterns
- Verification rules

## Workflows (400 lines)
- implement-feature workflow (200 lines)
- verify-build workflow (100 lines)
- analyze-quality workflow (100 lines)
```

**Benefits:**
- Agent: 500 → 120 lines (76% reduction)
- Skills reusable by all agents
- Standards in one place
- Context isolation achieved
- Easy to maintain

## Summary

**Minimal Wrapper Pattern** = Thin Orchestration (< 150 lines) + Skill Delegation + Context Isolation

**Key Formula:**
```
User Goal → Minimal Wrapper (< 150 lines) → Specialized Skill (standards + logic) → Result
```

**Success Criteria:**
- ✅ Wrappers < 150 lines
- ✅ No business logic in wrappers
- ✅ All standards in skills
- ✅ Context isolation working
- ✅ Skills reusable across wrappers
- ✅ Easy to maintain and test

**Integration Points:**
- Complements goal-based organization (xref:goal-based-organization.md[Goal-Based Organization])
- Uses skill delegation patterns (xref:skill-design.md[Skill Design])
- Follows command orchestration (xref:command-design.md[Command Design])
- Enables token optimization (xref:token-optimization.md[Token Optimization])
