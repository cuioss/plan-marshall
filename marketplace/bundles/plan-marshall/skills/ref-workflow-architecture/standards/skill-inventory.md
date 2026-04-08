# Skill Inventory

Complete inventory of all 49 skills in the plan-marshall bundle. Skills are either **registered** (listed in `plugin.json`, loaded by the skill system) or **script-only** (invoked exclusively via 3-part executor notation, never loaded as LLM context by the skill system).

See [glossary.md](glossary.md) for term definitions.

---

## Registration Categories

Per the plugin.json registration convention documented in `frontmatter-standards.md`:

1. **User-invocable** (`user-invocable: true`) — must register
2. **Context-loaded** (`user-invocable: false`, loaded via `Skill:` directive) — must register
3. **Script-only** (`user-invocable: false`, invoked only via 3-part notation) — do NOT register

---

## Phase Skills (6 registered)

| Skill | Registered | Purpose |
|-------|-----------|---------|
| phase-1-init | yes | Creates plan directory, request.md, references, status |
| phase-2-refine | yes | Iterative request clarification until confidence threshold |
| phase-3-outline | yes | Two-track solution outline creation (simple/complex) |
| phase-4-plan | yes | Task planning from deliverables with skill resolution |
| phase-5-execute | yes | Task execution with verification |
| phase-6-finalize | yes | Commit, push, PR, review, Sonar, knowledge capture |

## Data Layer — manage-* Skills (14 total, 6 registered)

| Skill | Registered | Scope | Purpose |
|-------|-----------|-------|---------|
| manage-architecture | yes | hybrid | Project module discovery and LLM enrichment |
| manage-findings | yes | plan | Findings, Q-Gate findings, assessments (JSONL) |
| manage-lessons | yes | global | Lessons learned with global scope |
| manage-memories | yes | global | Memory layer for persistent session storage |
| manage-run-config | yes | hybrid | Per-execution transient command configuration |
| manage-tasks | yes | plan | Implementation tasks with sequential sub-steps |
| manage-config | script-only | hybrid | Project-level marshal.json configuration |
| manage-files | script-only | plan | Generic plan file CRUD |
| manage-logging | script-only | hybrid | Work log, decision log, script log |
| manage-metrics | script-only | plan | Per-phase timing and token data |
| manage-plan-documents | script-only | plan | Typed document operations (request.md) |
| manage-references | script-only | plan | Plan references (branch, issue, files, domains) |
| manage-solution-outline | script-only | plan | Solution outline parsing and validation |
| manage-status | script-only | plan | Plan status lifecycle (phases, metadata) |

## Workflow Skills (5 registered)

| Skill | Registered | Purpose |
|-------|-----------|---------|
| workflow-integration-github | yes | CI monitoring, review handling (GitHub) |
| workflow-integration-gitlab | yes | CI monitoring, review handling (GitLab) |
| workflow-integration-git | yes | Commit, push with conventional commits |
| workflow-integration-sonar | yes | Sonar issue triage and fix/suppress |
| workflow-permission-web | yes | WebFetch domain permission consolidation |
| workflow-pr-doctor | yes | PR issue diagnosis and fix (build, reviews, Sonar) |

## Tools Skills (5 total, 3 registered)

| Skill | Registered | Purpose |
|-------|-----------|---------|
| tools-integration-ci | yes | CI provider abstraction (GitHub/GitLab API) |
| tools-permission-doctor | yes | Read-only permission analysis |
| tools-permission-fix | yes | Permission write operations (add, remove, consolidate) |
| tools-file-ops | script-only | Core shared utilities (file I/O, TOON output, atomic writes) |
| tools-input-validation | script-only | Plan ID validation, argparse helpers |
| tools-script-executor | script-only | Executor generation and script resolution |

## Build Skills (4, all script-only)

| Skill | Registered | Purpose |
|-------|-----------|---------|
| build-gradle | script-only | Gradle module discovery and command execution |
| build-maven | script-only | Maven module discovery and command execution |
| build-npm | script-only | npm/Node.js module discovery and command execution |
| build-python | script-only | Python (pyprojectx) module discovery and command execution |

## Reference & Development Skills (6 total, 5 registered)

| Skill | Registered | Purpose |
|-------|-----------|---------|
| dev-general-code-quality | yes | Language-agnostic code organization, error handling |
| dev-general-module-testing | yes | Language-agnostic testing methodology, coverage |
| dev-general-practices | yes | Foundational development rules, tool usage |
| ref-toon-format | yes | TOON output format specification |
| ref-workflow-architecture | yes | Central architecture documentation (this bundle) |
| shared-workflow-helpers | script-only | Python library: triage_helpers.py |

## Entry Points & Orchestration (3 total, 2 registered)

| Skill | Registered | Purpose |
|-------|-----------|---------|
| plan-marshall | yes | Unified user-facing entry point for plan lifecycle |
| task-executor | yes | Domain-agnostic task execution with profile routing |
| plan-marshall-plugin | script-only | User guide references for plan-marshall |

## Configuration & Recipes (3 total, 2 registered)

| Skill | Registered | Purpose |
|-------|-----------|---------|
| marshall-steward | yes | Project configuration wizard (init/maintenance) |
| recipe-refactor-to-profile-standards | yes | Recipe for refactoring code to profile standards |
| extension-api | yes | Extension API for domain bundles |

## Query Skills (2, all script-only)

| Skill | Registered | Purpose |
|-------|-----------|---------|
| query-architecture | script-only | Read-only architecture queries |
| query-config | script-only | Read-only configuration queries |

---

## Script Naming Convention

Entry-point script filenames must match the 3-part executor notation. Two patterns coexist:

- **Dash notation**: `manage-files.py` → `plan-marshall:manage-files:manage-files`
- **Underscore notation**: `manage_status.py` → `plan-marshall:manage-status:manage_status`

The filename is the authoritative notation. Do NOT rename existing scripts — it would break the executor mapping.

Internal modules (not invoked via executor) always use underscore prefix: `_tasks_core.py`, `_cmd_lifecycle.py`.

See [manage-contract.md](manage-contract.md) for the full naming specification.
