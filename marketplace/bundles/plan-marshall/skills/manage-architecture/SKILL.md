---
name: manage-architecture
description: LLM-based architectural analysis that transforms raw project data into meaningful structure
user-invocable: false
---

# Analyze Project Architecture Skill

## Enforcement

- Run scripts EXACTLY as documented using `python3 .plan/execute-script.py {notation} ...`
- Complete all steps in sequence; only stop when all modules are enriched
- Never leave `responsibility` or `key_packages` empty
- Always provide `--reasoning` parameters (traceability is required)

---

## What This Skill Provides

**Discovery**: Run extension API to collect raw module data

**Enrichment**: LLM analyzes documentation and code to add semantic understanding

**Persistence**: Store enriched data for solution-outline consumption

---

## Scripts

| Script | Notation | Purpose |
|--------|----------|---------|
| architecture | `plan-marshall:manage-architecture:architecture` | Main CLI for all operations |

### Command Groups

| Group | API | Purpose |
|-------|-----|---------|
| `discover`, `init` | [manage-api](standards/manage-api.md) | Setup commands |
| `derived`, `derived-module` | [manage-api](standards/manage-api.md) | Read raw discovered data |
| `enrich *` | [manage-api](standards/manage-api.md) | Write enrichment data |
| `suggest-domains` | — | Suggest applicable skill domains for a module |
| `info`, `module`, `modules`, `commands`, `resolve` | [client-api](standards/client-api.md) | Consumer queries |

---

## Step 1: Discover Modules

Run extension API discovery:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture discover --force
```

**Output**: `.plan/project-architecture/derived-data.json`

Always overwrites existing data to ensure fresh discovery.

---

## Step 2: Review Build Profiles (Maven Only)

**Condition**: Only if any module has `build_systems` containing `maven`.

Check derived-data.json for NO-MATCH-FOUND profiles in `modules.*.metadata.profiles`.

**If Maven modules exist AND unmatched profiles found**:

Load skill `pm-dev-java:manage-maven-profiles` and follow its workflow to:
1. Ask user about each unmatched profile (Ignore/Skip/Map)
2. Apply configuration via `run_config` commands
3. Re-run discovery to apply changes

**If no Maven modules OR no unmatched profiles** → Skip to Step 3.

---

## Step 3: Initialize Enrichment

Check if `llm-enriched.json` already exists:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture init --check
```

**If file exists**, ask user:

```yaml
AskUserQuestion:
  question: "llm-enriched.json already exists. What do you want to do?"
  header: "Enrichment"
  options:
    - label: "Skip"
      description: "Keep existing enrichments, continue to next step"
    - label: "Replace"
      description: "Discard existing enrichments, start fresh"
  multiSelect: false
```

| Choice | Command |
|--------|---------|
| Skip | Proceed to Step 4 |
| Replace | `architecture init --force` |

**If file does not exist**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture init
```

---

## Step 4: Load Data & Enrich Project

Load the raw discovered data:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture derived
```

Read referenced READMEs for modules that have them. Based on the README and module descriptions, write a 1-2 sentence project description:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich project --description "{extracted project description}" \
  --reasoning "{source: README.md introduction | inferred from module names}"
```

Get the module list:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture modules
```

---

## Step 5: Enrich Each Module

**For each module in the list**, execute Steps 5a-5d:

### Step 5a: Read Documentation & Determine Purpose

Get raw discovered data for the module:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture derived-module --name {module-name}
```

Read the referenced documentation:
```bash
Read {paths.readme}
Read {package_info path}  # for packages with package_info
```

If no documentation available, sample 2-3 source files from packages.

Analyze to determine `purpose` value:

| Signal | Purpose Value |
|--------|---------------|
| packaging=jar, no runtime deps | `library` |
| Quarkus extension annotations | `extension` |
| Build-time processor, deployment | `deployment` |
| Main class, application entry | `runtime` |
| packaging=pom at root | `parent` |
| Only test files | `integration-tests` |
| JMH benchmarks | `benchmark` |

### Step 5b: Write Responsibility

Write 1-3 sentences describing what the module does, with reasoning:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich module --name {module-name} \
  --responsibility "{1-3 sentence description}" \
  --responsibility-reasoning "{source}" \
  --purpose {purpose-value} \
  --purpose-reasoning "{signal}"
```

### Step 5c: Key Packages & Dependencies

Select 2-4 architecturally significant packages per module:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich package --module {module-name} \
  --package {full.package.name} \
  --description "{1-2 sentence description}"
```

Identify key dependencies:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich dependencies --module {module-name} \
  --key "{comma-separated list of groupId:artifactId}" \
  --internal "{comma-separated list of internal module names}" \
  --reasoning "{why these are architecturally significant}"
```

### Step 5d: Resolve Skill Domains

Get applicable domains for this module:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  suggest-domains --module {module-name}
```

Present suggestions to user for confirmation:

```yaml
AskUserQuestion:
  question: "Which skill domains apply to '{module-name}'?"
  header: "Skill Domains"
  options: [{domain} ({confidence}) — {signals}]
  multiSelect: true
```

For each confirmed domain, add its default skills:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich add-domain --module {module-name} --domain {domain-key} \
  --reasoning "{domain}: {signals}"
```

For domains where optional skills also apply (e.g., CDI detected, Lombok used),
add with `--include-optionals`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich add-domain --module {module-name} --domain {domain-key} \
  --include-optionals --reasoning "{domain}: all skills apply based on {signals}"
```

To override profile filtering for a specific module (e.g., force integration_testing on a module
that lacks automatic signals), use `--profiles`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich add-domain --module {module-name} --domain {domain-key} \
  --profiles implementation,module_testing,integration_testing \
  --reasoning "explicit IT profile for {reason}"
```

Profile resolution order: `--profiles` flag > `marshal.json active_profiles` > extension signal detection > all defined profiles.

---

## Step 6: Verify & Summarize

After all modules are enriched, verify completeness:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture info
```

Check that:
- Every module has non-empty `responsibility`
- Every module has valid `purpose`
- Every module has 2-4 `key_packages` with descriptions
- Every module has `key_dependencies` identified (unless no compile-scope deps)
- Every module has `skills_by_profile` with at least `implementation` and `module_testing`

If any module is incomplete → return to Step 5 for that module.

Display completion summary:

```
Architecture analysis complete.

Project: {project name}
Modules enriched: {count}

Files created:
  - .plan/project-architecture/derived-data.json
  - .plan/project-architecture/llm-enriched.json

Next steps:
  - Solution outline will use this data for placement decisions
  - Run 'architecture.py module --name X' to query module details
```

---

## Error Handling

| Error | Resolution |
|-------|------------|
| Extension API not found | Verify domain bundles installed, run `/marshall-steward` |
| No modules discovered | Verify build files exist and domain bundle matches project |
| Documentation not found | Analyze source code directly, note "Inferred from source analysis" |

---

## Post-Implementation Enrichment

During verification or after implementation, capture learnings:

| Command | Usage |
|---------|-------|
| `enrich tip` | `--module {name} --tip "Use @ApplicationScoped for singleton services"` |
| `enrich insight` | `--module {name} --insight "Heavy validation happens in boundary layer"` |
| `enrich best-practice` | `--module {name} --practice "Always validate tokens before extracting claims"` |

---

## Deferred Loading

| Reference | When to Load |
|-----------|--------------|
| [manage-api.md](standards/manage-api.md) | Manage commands (setup, read raw, enrich) |
| [client-api.md](standards/client-api.md) | Client commands (merged data for consumers) |
| [architecture-persistence.md](standards/architecture-persistence.md) | Field schemas and formats |
| [documentation-sources.md](standards/documentation-sources.md) | Reading strategy details |
| `pm-dev-java:manage-maven-profiles` | Maven profile classification (Step 2) |

---

## Integration

This skill is invoked by:
- **marshall-steward wizard** Step 13 (Project Structure Analysis)
- **Direct activation** when regenerating project structure

Output is consumed by:
- **solution-outline** Step 0 (module placement)
- **task-plan** (command resolution)
