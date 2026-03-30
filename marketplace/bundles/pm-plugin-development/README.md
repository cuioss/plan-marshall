# Plugin Development Tools

## Purpose

Complete toolchain for creating, diagnosing, fixing, and maintaining marketplace components. This bundle provides skills, agents, and a command for plugin developers to manage the full lifecycle of marketplace components (commands, skills, bundles).

## Architecture

This bundle follows the **goal-based organization** pattern where components are organized by user goals rather than technical types:

- **CREATE** - Create new components
- **DOCTOR** - Diagnose and fix issues (unified workflow)
- **MAINTAIN** - Keep marketplace healthy
- **ANALYZE** - Investigate failures and permission prompts

## Components

### Agents (3)

| Agent | Description |
|-------|-------------|
| `ext-outline-component-agent` | Analyze component files against request using semantic reasoning |
| `ext-outline-inventory-agent` | Load marketplace inventory and perform initial scope assessment |
| `tool-coverage-agent` | Analyze tool declarations vs actual usage in a component file |

### Commands (1)

| Command | Description |
|---------|-------------|
| `tools-analyze-user-prompted` | Analyze permission prompts to identify source and provide solutions |

### Skills - User-Invocable (5)

| Skill | Description |
|-------|-------------|
| `plugin-apply-lessons-learned` | Apply accumulated lessons learned to component documentation |
| `plugin-create` | Create new marketplace components (agents, commands, skills, bundles) with proper structure and standards compliance |
| `plugin-doctor` | Diagnose and fix quality issues with automated safe fixes and prompted risky fixes |
| `plugin-maintain` | Update components, manage knowledge, maintain READMEs, restructure, and apply orchestration compliance |
| `tools-analyze-script-failures` | Analyze script failures to identify source components and propose fixes |

### Skills - Context-Loaded (8)

These skills are not directly invocable. They are loaded automatically by other components via `Skill:` directives.

| Skill | Description |
|-------|-------------|
| `ext-outline-workflow` | Shared workflow steps for plugin development outline, loaded by `workflow-outline-change-type` |
| `ext-triage-plugin` | Triage extension for marketplace plugin findings during plan-finalize phase |
| `plugin-architecture` | Architecture principles, skill patterns, and design guidance for marketplace components |
| `plugin-plan-implement` | Implement plugin tasks from plan with step iteration and progress tracking |
| `plugin-script-architecture` | Script development standards covering implementation patterns, testing, and output contracts |
| `plugin-task-plan` | Create implementation tasks from deliverables using skill delegation |
| `tools-marketplace-inventory` | Scan and report complete marketplace inventory (bundles, agents, commands, skills, scripts) |
| `verification-mode` | Verification mode that stops and analyzes on failures, workarounds, or resolution issues |

## Dependencies

- **Inter-Bundle Dependencies**: `plan-marshall` — workflow skills use manage-tasks, manage-lessons, manage-logging, manage-config, and dev-general-practices
- **External Dependencies**: None - works with filesystem access only

## Standards Enforced

The diagnostic and creation workflows validate:

- **Architecture Rules**: Self-containment, relative path pattern, progressive disclosure
- **Goal-Based Organization**: Commands organized by user goals
- **Thin Orchestrator Pattern**: Commands <100 lines, delegate to skills
- **Skill Patterns**: Proper workflow structure, script automation, references
- **Quality Standards**: Frontmatter format, documentation completeness, cross-references
