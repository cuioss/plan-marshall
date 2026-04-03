---
name: query-config
description: Read-only skill resolution and discovery queries against marshal.json configuration. Resolves domain skills, task executors, workflow extensions, recipes, and phase steps.
user-invocable: false
tools:
  - Bash
---

# Query Config Skill

Read-only queries against `.plan/marshal.json` for skill resolution, recipe discovery, and phase step enumeration. These commands consume configuration but never modify it.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- All commands are read-only -- they never write to marshal.json
- marshal.json must exist before queries (initialization via manage-config)

## Available Commands

### Resolve Domain Skills

Resolve skills for a domain and profile, aggregating core + profile skills with descriptions.

```bash
python3 .plan/execute-script.py plan-marshall:query-config:query-config resolve-domain-skills --domain java --profile implementation
```

### Resolve Workflow Skill Extension

Resolve workflow skill extension for a domain and type (outline or triage).

```bash
python3 .plan/execute-script.py plan-marshall:query-config:query-config resolve-workflow-skill-extension --domain java --type outline
```

### Get Skills by Profile

Get skills organized by profile for architecture enrichment.

```bash
python3 .plan/execute-script.py plan-marshall:query-config:query-config get-skills-by-profile --domain java
```

### Configure Task Executors

Configure task executors from discovered profiles.

```bash
python3 .plan/execute-script.py plan-marshall:query-config:query-config configure-task-executors
```

### Resolve Task Executor

Resolve task executor skill for a given profile.

```bash
python3 .plan/execute-script.py plan-marshall:query-config:query-config resolve-task-executor --profile implementation
```

### List Recipes

List all available recipes from configured domains and project skills.

```bash
python3 .plan/execute-script.py plan-marshall:query-config:query-config list-recipes
```

### Resolve Recipe

Resolve a specific recipe by key.

```bash
python3 .plan/execute-script.py plan-marshall:query-config:query-config resolve-recipe --recipe refactor-to-standards
```

### Resolve Outline Skill

Resolve outline skill for a domain.

```bash
python3 .plan/execute-script.py plan-marshall:query-config:query-config resolve-outline-skill --domain java
```

### List Finalize Steps

List all available finalize steps from built-in, project, and extension sources.

```bash
python3 .plan/execute-script.py plan-marshall:query-config:query-config list-finalize-steps
```

### List Verify Steps

List all available verify steps from built-in, project, and extension sources.

```bash
python3 .plan/execute-script.py plan-marshall:query-config:query-config list-verify-steps
```
