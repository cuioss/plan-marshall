# CUI Java Expert

Comprehensive Java development expertise bundle with agent-first architecture for autonomous code implementation, testing, and standards compliance.

## Purpose

This bundle provides a complete Java development knowledge base with an **agent-first architecture**. Agents handle autonomous execution while commands orchestrate complex workflows. Skills contain all business logic and standards.

## Architecture

```
pm-dev-java/
├── agents/                  # 9 autonomous agents
│   ├── java-implement-agent.md      # Implement features
│   ├── java-implement-tests-agent.md # Implement tests
│   ├── java-fix-build-agent.md      # Fix compilation errors
│   ├── java-fix-tests-agent.md      # Fix test failures
│   ├── java-fix-javadoc-agent.md    # Fix JavaDoc errors
│   ├── java-refactor-agent.md       # Refactor code
│   ├── java-coverage-agent.md       # Analyze coverage (read-only)
│   ├── java-quality-agent.md        # Analyze quality (read-only)
│   └── java-verify-agent.md         # Verify compliance (read-only)
├── commands/                # 6 orchestration commands
│   ├── java-analyze-all.md          # Parallel analysis (Task tool)
│   ├── java-full-workflow.md        # Complete implement-test-verify
│   ├── java-create.md               # Interactive component creation
│   ├── java-enforce-logrecords.md   # Logging standards enforcement
│   ├── java-maintain-logger.md      # Logger maintenance workflow
│   └── java-optimize-quarkus-native.md # Native image optimization
└── skills/                  # 12 skills with workflows
    ├── java-core/           # Core Java patterns, modern features
    ├── java-null-safety/    # JSpecify null annotations
    ├── java-lombok/         # Lombok patterns (@Delegate, @Builder)
    ├── junit-core/          # JUnit 5 testing, AAA structure
    ├── junit-integration/   # Integration testing with Failsafe
    ├── java-cdi/            # Core CDI patterns, constructor injection
    ├── java-cdi-quarkus/    # Quarkus-specific CDI, @QuarkusTest
    ├── javadoc/             # JavaDoc documentation standards
    └── java-maintenance/    # Maintenance prioritization
```

## Agent-First Design

### Why Agents?

1. **Better Context Management**: Agents run in isolated contexts, reducing noise
2. **Skill Delegation**: Agents invoke skills that contain all business logic
3. **Thin Wrappers**: Each agent is < 85 lines - pure parameter routing

### Agent Types

| Agent | Purpose | Model |
|-------|---------|-------|
| java-implement-agent | Feature implementation | sonnet |
| java-implement-tests-agent | Test implementation | sonnet |
| java-fix-build-agent | Fix compilation errors | sonnet |
| java-fix-tests-agent | Fix test failures | sonnet |
| java-fix-javadoc-agent | Fix JavaDoc errors | haiku |
| java-refactor-agent | Code refactoring | sonnet |
| java-coverage-agent | Coverage analysis (read-only) | haiku |
| java-quality-agent | Quality analysis (read-only) | haiku |
| java-verify-agent | Standards verification (read-only) | haiku |

### Commands for Orchestration

Commands use the Task tool to coordinate multiple agents:

```
/java-analyze-all target=src/main/java/
    ├─> Task: java-quality-agent (parallel)
    ├─> Task: java-coverage-agent (parallel)
    └─> Task: java-verify-agent (parallel)

/java-full-workflow description="Add auth service"
    ├─> Task: java-implement-agent
    ├─> Task: java-fix-build-agent (if needed)
    ├─> Task: java-implement-tests-agent
    ├─> Task: java-fix-tests-agent (if needed)
    └─> Task: java-verify-agent
```

## Components

### Skills (9 skills)

**Core Development:**
- **java-core** - Core Java patterns, modern features, performance
- **java-null-safety** - JSpecify null annotations, @Nullable/@NonNull
- **java-lombok** - Lombok patterns (@Delegate, @Builder, @Value)

**Testing:**
- **junit-core** - JUnit 5 patterns, AAA structure, assertions
- **junit-integration** - Integration testing with Maven Failsafe

**CDI/Quarkus:**
- **java-cdi** - Core CDI patterns, constructor injection, scopes
- **java-cdi-quarkus** - Quarkus-specific CDI, @QuarkusTest, native image

**Documentation & Maintenance:**
- **javadoc** - JavaDoc documentation standards
- **java-maintenance** - Maintenance prioritization, refactoring triggers

> **Note**: CUI library-specific patterns (CuiLogger, test generators) are in the separate `pm-dev-java-cui` bundle.
>
> **Planning Integration**: Java domain skills are loaded by `pm-workflow` thin agents during plan execution via `task.skills` array.

### Agents (9 autonomous agents)

**Execution Agents** (modify code):
- java-implement-agent - Implement features
- java-implement-tests-agent - Write tests
- java-fix-build-agent - Fix compilation
- java-fix-tests-agent - Fix tests
- java-fix-javadoc-agent - Fix documentation
- java-refactor-agent - Refactor code

**Analysis Agents** (read-only):
- java-coverage-agent - Coverage analysis
- java-quality-agent - Quality analysis
- java-verify-agent - Standards verification

### Commands (6 orchestration commands)

**Orchestration Commands** (use Task tool):
- java-analyze-all - Parallel analysis agents
- java-full-workflow - Complete implement→test→verify
- java-create - Interactive wizard

**Specialized Commands** (complex workflows):
- java-enforce-logrecords - Logging enforcement
- java-maintain-logger - Logger maintenance
- java-optimize-quarkus-native - Native optimization

## Installation

```bash
/plugin install pm-dev-java
```

## Usage Examples

### Quick Analysis

```
/java-analyze-all target=src/main/java/auth/
```

### Full Feature Implementation

```
/java-full-workflow description="Add user authentication service" module=auth-service
```

### Interactive Creation

```
/java-create
```

### Direct Agent Invocation

Agents can be invoked via Task tool from other commands:

```
Task:
  subagent_type: pm-dev-java:java-implement-agent
  description: Implement feature
  prompt: |
    description="Add token validation"
    module=auth-service
```

## Bundle Statistics

- **Agents**: 9 (autonomous execution)
- **Commands**: 6 (orchestration)
- **Skills**: 9 (core development, testing, CDI, documentation)
- **Scripts**: 3+ (Python automation)

## Dependencies

- **builder-maven** - For Maven build operations (builder-maven-rules skill)
- Python 3 for automation scripts

## Support

- Repository: https://github.com/cuioss/plan-marshall
- Bundle: marketplace/bundles/pm-dev-java/
