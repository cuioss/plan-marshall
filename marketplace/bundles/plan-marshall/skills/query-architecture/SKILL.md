---
name: query-architecture
description: Read-only project architecture queries. Provides module info, dependency graphs, command resolution, and sibling discovery from architecture data.
user-invocable: false
tools:
  - Bash
---

# Query Architecture Skill

Read-only consumer API for querying project architecture data. All commands are non-destructive and return TOON-formatted output.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- All commands are read-only; no data is modified
- Requires prior discovery (`manage-architecture:architecture discover`) to have run
- Commands merge derived + enriched data for consumer output

---

## Scripts

| Script | Notation | Purpose |
|--------|----------|---------|
| query-architecture | `plan-marshall:query-architecture:query-architecture` | Read-only architecture queries |

### Available Commands

| Command | Purpose |
|---------|---------|
| `info` | Project summary with metadata and module overview |
| `modules` | List module names, optionally filtered by command or physical path |
| `graph` | Module dependency graph with topological layers |
| `module` | Module information (merged derived + enriched) |
| `commands` | List available commands for a module |
| `resolve` | Resolve command name to executable form |
| `siblings` | Find sibling virtual modules |
| `profiles` | Extract unique profile keys from module enrichment |

---

## Usage Examples

### Project summary

```bash
python3 .plan/execute-script.py plan-marshall:query-architecture:query-architecture info
```

### List modules

```bash
python3 .plan/execute-script.py plan-marshall:query-architecture:query-architecture modules
python3 .plan/execute-script.py plan-marshall:query-architecture:query-architecture modules --command compile
python3 .plan/execute-script.py plan-marshall:query-architecture:query-architecture modules --physical-path modules/core
```

### Dependency graph

```bash
python3 .plan/execute-script.py plan-marshall:query-architecture:query-architecture graph
python3 .plan/execute-script.py plan-marshall:query-architecture:query-architecture graph --full
```

### Module details

```bash
python3 .plan/execute-script.py plan-marshall:query-architecture:query-architecture module --name my-module
python3 .plan/execute-script.py plan-marshall:query-architecture:query-architecture module --name my-module --full
```

### Resolve a build command

```bash
python3 .plan/execute-script.py plan-marshall:query-architecture:query-architecture resolve --command compile
python3 .plan/execute-script.py plan-marshall:query-architecture:query-architecture resolve --command compile --name my-module
```

### Find siblings

```bash
python3 .plan/execute-script.py plan-marshall:query-architecture:query-architecture siblings --name my-module
```

### Extract profiles

```bash
python3 .plan/execute-script.py plan-marshall:query-architecture:query-architecture profiles
python3 .plan/execute-script.py plan-marshall:query-architecture:query-architecture profiles --modules mod-a,mod-b
```
