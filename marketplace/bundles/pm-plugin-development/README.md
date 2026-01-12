# CUI Plugin Development Tools

## Purpose

Complete toolchain for creating, diagnosing, fixing, and maintaining Claude Code marketplace components. This bundle provides goal-based commands and skills for plugin developers to manage the full lifecycle of marketplace components (commands, skills, bundles).

## Architecture

This bundle follows the **goal-based organization** pattern where components are organized by user goals rather than technical types:

- **CREATE** - Create new components
- **DOCTOR** - Diagnose and fix issues (unified workflow)
- **MAINTAIN** - Keep marketplace healthy
- **VERIFY** - Validate complete marketplace

## Components

### Commands (4 goal-based thin orchestrators)

| Command | Description |
|---------|-------------|
| `/plugin-create` | Create new marketplace component (agent, command, skill, or bundle) |
| `/plugin-doctor` | Diagnose and fix quality issues with automated safe fixes and prompted risky fixes |
| `/plugin-maintain` | Maintain marketplace health (update, add-knowledge, readme, refactor) |
| `/plugin-verify` | Run comprehensive marketplace verification |

### Skills (5)

| Skill | Description |
|-------|-------------|
| `plugin-architecture` | Architecture principles, skill patterns, and design guidance |
| `plugin-create` | Workflows for creating new marketplace components |
| `plugin-doctor` | Unified diagnose → auto-fix → prompt risky → verify workflow |
| `plugin-maintain` | Maintenance workflows (update, readme, refactor) |
| `marketplace-inventory` | Scan and report complete marketplace inventory |

### Agents

None - All agent functionality has been consolidated into skills following the goal-based architecture pattern.

## Installation

```
/plugin install pm-plugin-development
```

## Usage Examples

### Create a New Component

```
/plugin-create agent
/plugin-create command
/plugin-create skill
/plugin-create bundle
```

The workflow guides you through:
- Interactive questionnaire for component details
- Duplication detection against existing components
- Generation with proper structure and frontmatter
- Validation against architecture rules
- Summary with next steps

### Doctor Components (Diagnose + Fix)

```
# Doctor specific component
/plugin-doctor agent=my-agent
/plugin-doctor command=my-command
/plugin-doctor skill=my-skill

# Doctor all components of a type
/plugin-doctor agents
/plugin-doctor commands
/plugin-doctor skills

# Doctor entire marketplace
/plugin-doctor marketplace

# Diagnosis only (no fixes)
/plugin-doctor agents --no-fix
```

The doctor workflow:
1. **Diagnose**: Analyze components for issues
2. **Auto-fix**: Apply safe fixes automatically
3. **Prompt**: Ask for confirmation on risky fixes
4. **Verify**: Confirm fixes resolved issues

### Maintain Components

```
# Update components
/plugin-maintain update agent=my-agent
/plugin-maintain update command=my-command

# Add knowledge to skill
/plugin-maintain add-knowledge skill=my-skill source=url

# Update READMEs
/plugin-maintain readme
/plugin-maintain readme bundle=my-bundle

# Refactor structure
/plugin-maintain refactor
```

### Verify Marketplace

```
/plugin-verify

# Runs comprehensive health check across all components
# Reports issues by severity
# Offers fix option
```

## Dependencies

- **Inter-Bundle Dependencies**: None - self-contained
- **External Dependencies**: None - works with filesystem access only

## Standards Enforced

The diagnostic and creation workflows validate:

- **Architecture Rules**: Self-containment, relative path pattern, progressive disclosure
- **Goal-Based Organization**: Commands organized by user goals
- **Thin Orchestrator Pattern**: Commands <100 lines, delegate to skills
- **Skill Patterns**: Proper workflow structure, script automation, references
- **Quality Standards**: Frontmatter format, documentation completeness, cross-references
