# Glossary

Canonical definitions for terms used across the plan-marshall bundle. When a term appears in multiple contexts, this document provides the authoritative meaning.

---

## Plan Lifecycle

| Term | Definition |
|------|-----------|
| **plan** | A structured unit of work managed through 6 sequential phases. Stored under `.plan/plans/{plan_id}/`. |
| **plan_id** | Unique kebab-case identifier for a plan (max 50 chars). Derived from the input source during phase-1-init (Step 2) or provided explicitly. |
| **phase** | One of 6 sequential lifecycle stages: `1-init`, `2-refine`, `3-outline`, `4-plan`, `5-execute`, `6-finalize`. Phases execute in order; skipping is not allowed. |
| **track** | Outline creation strategy determined during phase-2-refine. **Simple track**: localized changes with known targets. **Complex track**: codebase-wide discovery requiring domain skill involvement. |
| **Q-Gate** | Quality gate — a verification checkpoint between phases. See [findings-pipeline.md § Store](findings-pipeline.md#store) for storage and [findings-pipeline.md § Invariant Gate](findings-pipeline.md#invariant-gate) for resolution before phase advance. |
| **worktree** | The git worktree a plan executes in during phases 5-6 (or the main checkout when `use_worktree=false`). At phase-5 start the plan directory and executor MOVE into the worktree and the orchestrator pins its cwd there; every `.plan/` lookup resolves cwd-relatively from that point. cwd-pinning is an implementation detail of how the right tree is targeted — callers do not pass worktree paths. See [`../../workflow-integration-git/standards/worktree-handling.md`](../../workflow-integration-git/standards/worktree-handling.md) for the lifecycle and [`../../tools-script-executor/standards/cwd-policy.md`](../../tools-script-executor/standards/cwd-policy.md) for the resolution rule. |

## Work Artifacts

| Term | Definition |
|------|-----------|
| **deliverable** | A scoped unit of change produced by phase-3-outline. Each deliverable maps to 1:N tasks (one per profile). Stored in `solution_outline.md` as numbered `###` sections. |
| **task** | An executable work unit created by phase-4-plan from a deliverable. Stored as `TASK-{NNN}.json`. Each task belongs to exactly one deliverable and one profile. |
| **finding** | An observation recorded during any phase. Types include: bug, improvement, anti-pattern, triage, tip, insight, best-practice, build-error, test-failure, lint-issue, sonar-issue, pr-comment. See [findings-pipeline.md](findings-pipeline.md) for the producer→store→consumer→gate flow. |
| **assessment** | A file-level evaluation produced during phase-3-outline (complex track). Certainty levels: `CERTAIN_INCLUDE`, `CERTAIN_EXCLUDE`, `UNCERTAIN` (with 0-100 confidence). See [findings-pipeline.md § Store](findings-pipeline.md#store). |

## Task Execution

| Term | Definition |
|------|-----------|
| **profile** | A task execution category that determines which skills are loaded and what verification is performed. Values: `implementation`, `module_testing`, `integration_testing`, `quality`, `verification`, `standalone`. |
| **change_type** | Classification of the requested change, detected during phase-3-outline. Values: `feature`, `enhancement`, `bug_fix`, `tech_debt`, `analysis`, `verification`. Each type has a corresponding outline template (`change-{type}.md`). |
| **compatibility mode** | Strategy for handling breaking changes during tech_debt/refactoring. Values: `breaking` (remove old API), `deprecation` (keep old with warnings), `smart_and_ask` (analyze impact and ask user). Configured in `marshal.json`. |
| **verification step** | A check executed after task implementation. Types: built-in (`quality_check`, `build_verify`, `coverage_check`), project (`project:*`), skill-based (`bundle:skill`). |

## Architecture & Configuration

| Term | Definition |
|------|-----------|
| **module** (project) | A build system unit (Maven module, Gradle subproject, npm workspace, Python package). Discovered by `manage-architecture` and stored per-module under `.plan/architecture/<module>/derived.json` (raw facts) and `.plan/architecture/<module>/enriched.json` (LLM-enriched view), with the canonical module set declared by `.plan/architecture/_project.json["modules"]`. Not to be confused with Python modules or marketplace components. |
| **domain** (skill) | A technology area that determines which development skills are loaded. Standard domains: `system`, `java`, `javascript`, `plan-marshall-plugin-dev`, `documentation`. Configured in `marshal.json` under `skill_domains`. |
| **marshal.json** | Project-level configuration file (`.plan/marshal.json`) managed by `manage-config`. Contains skill domains, phase-specific settings, and CI configuration. |
| **run-config** | Per-execution transient configuration (`.plan/run-config.json`) managed by `manage-run-config`. Stores resolved build commands and runtime state. Distinct from the persistent `marshal.json`. |

## Component Model

| Term | Definition |
|------|-----------|
| **skill** | A marketplace component providing domain knowledge, standards, or workflow instructions. Loaded as LLM context via `Skill:` directives or invoked via 3-part script notation. |
| **agent** | A marketplace component that executes tasks autonomously in a subagent. Follows the thin agent pattern — loads a skill and delegates all logic to it. |
| **manage-* skill** | A data-layer skill providing CRUD operations on plan artifacts via Python scripts. All follow the shared contract in `manage-contract.md`. |
| **extension** | A domain-specific implementation of `ExtensionBase` that provides module discovery, canonical commands, and build execution for a particular build system. |

## Output & Communication

| Term | Definition |
|------|-----------|
| **TOON** | Text-Oriented Object Notation — the standard output format for all plan-marshall scripts. Key-value pairs with `status: success` or `status: error` envelope. See `ref-toon-format` skill for full specification. |
| **thin agent pattern** | Architectural pattern where every `Task:` dispatch targets the generic `execution-context-{level}` dispatcher with the workflow doc, the skill load list, and the plan id passed through the prompt body. Keeps the agent surface to a single canonical body emitted as five level variants. See [agents.md](agents.md) for the full contract. |
| **executor** | The `execute-script.py` entry point that resolves 3-part notation (`bundle:skill:script`) to file paths and runs scripts with proper PYTHONPATH setup. |
| **3-part notation** | Script invocation format: `{bundle}:{skill}:{script}` (e.g., `plan-marshall:manage-status:manage-status`). The script name matches the Python filename without `.py` extension. |
