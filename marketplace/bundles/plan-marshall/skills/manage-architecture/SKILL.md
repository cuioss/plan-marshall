---
name: manage-architecture
description: LLM-based architectural analysis that transforms raw project data into meaningful structure
user-invocable: false
scope: hybrid
---

# Manage Architecture Skill

**Scope: hybrid** means this skill manages both project-level data (`.plan/project-architecture/`) and integrates with plan-scoped workflows (solution-outline, task-plan).

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Execute all steps in sequence; only stop when all modules are enriched
- Do not leave `responsibility` or `key_packages` empty after enrichment
- Do not skip `--reasoning` parameters (traceability is required)
- Enrichment must cover every discovered module before completion
- Discovery must run before enrichment (Step 1 before Steps 4-8)

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

## Steps 5-8: Per-Module Enrichment

**For each module in the list**, execute Steps 5-8 in order (dependencies: Step 5 feeds Steps 6-7, Step 8 runs last):

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

Analyze to determine `purpose` value (see also `architecture-persistence.md` for full list):

| Signal | Purpose Value |
|--------|---------------|
| packaging=jar, no runtime deps | `library` |
| Quarkus extension annotations | `extension` |
| Build-time processor, deployment | `deployment` |
| Main class, application entry | `runtime` |
| packaging=pom at root | `parent` |
| Bill of Materials POM | `bom` |
| Only test files | `integration-tests` |
| JMH benchmarks | `benchmark` |

## Step 6: Write Responsibility

Write 1-3 sentences describing what the module does, with reasoning:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich module --name {module-name} \
  --responsibility "{1-3 sentence description}" \
  --responsibility-reasoning "{source}" \
  --purpose {purpose-value} \
  --purpose-reasoning "{signal}"
```

## Step 7: Key Packages & Dependencies

Select 2-4 architecturally significant packages per module (choose packages that represent the module's core abstractions, public API, or key implementation concerns):

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich package --module {module-name} \
  --package {full.package.name} \
  --description "{1-2 sentence description}"
```

Identify key dependencies (both `--key` and `--internal` are optional — omit either when not applicable):

```bash
# External + internal dependencies
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich dependencies --module {module-name} \
  --key "{comma-separated list of groupId:artifactId}" \
  --internal "{comma-separated list of internal module names}" \
  --reasoning "{why these are architecturally significant}"

# Internal dependencies only (no external deps)
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich dependencies --module {module-name} \
  --internal "{comma-separated list of internal module names}" \
  --reasoning "{why these are architecturally significant}"
```

## Step 8: Resolve Skill Domains

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

## Step 9: Verify & Summarize

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

If any module is incomplete → return to Steps 5-8 for that module.

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
| Partial discovery failure | Some extensions may fail while others succeed — check which modules are missing and re-run `discover --force` after fixing the failing extension |
| Interrupted enrichment | Safe to resume — `enrich module` overwrites per-module data; re-run Steps 5-8 for incomplete modules |
| `manage-maven-profiles` skill unavailable | Skip Step 2 entirely; unmatched profiles will remain as NO-MATCH-FOUND in derived data |

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

Load standards documents in the order listed — each builds on the previous:

| # | Reference | When to Load |
|---|-----------|--------------|
| 1 | [manage-api.md](standards/manage-api.md) | First — covers setup, raw data, and enrich commands used in Steps 1-8 |
| 2 | [architecture-persistence.md](standards/architecture-persistence.md) | When you need field schemas, purpose values, or skills_by_profile structure |
| 3 | [client-api.md](standards/client-api.md) | When consuming enriched data (Step 9 verification, or downstream skills) |
| 4 | [documentation-sources.md](standards/documentation-sources.md) | During Step 5 — details on which files to read and how to extract information |
| 5 | `pm-dev-java:manage-maven-profiles` | Only during Step 2, only for Maven projects with unmatched profiles |

---

## Integration

This skill is invoked by:
- **marshall-steward wizard** Step 13 (Project Structure Analysis)
- **Direct activation** when regenerating project structure

Output is consumed by:
- **solution-outline** Step 0 (module placement)
- **task-plan** (command resolution)

## Related Skills

- `manage-solution-outline` — Consumes architecture data for placement decisions
- `manage-config` — Project-level configuration used during analysis
