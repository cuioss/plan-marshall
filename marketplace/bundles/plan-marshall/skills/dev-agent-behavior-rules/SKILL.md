---
name: dev-agent-behavior-rules
description: Foundational agent behavior rules covering user interaction, tool usage, research, dependency management, and document proliferation
user-invocable: false
---

# Development Practices Skill

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

Foundational development practices applicable across all technology stacks and development activities. Covers when to ask users, how to research best practices, proper tool usage, document management, and dependency governance.

## Workflow

### Step 1: Load Core Development Rules

**Important**: Load this standard at the start of any development work.

```
Read: standards/agent-behavior-rules.md
```

Covers Boy Scout Rule, decision tree for when to ask users, research patterns, tool selection guide, document proliferation guidelines, and dependency approval.

### Step 2: Load Tool Usage Standards (As Needed)

**Tool usage patterns** (load for file operations, content search, or automation work):
```
Read: standards/tool-usage-patterns.md
```

Covers tool selection guide, file operations (discovery, existence checks, validation), content search patterns (Grep modes, filtering), Bash safety rules (one command per call, no shell constructs, no heredocs), and build command resolution via architecture API.

### Step 3: Load Script Argument Naming Conventions (As Needed)

**Script argument naming** (load when authoring or invoking `plan-marshall` `manage-*` scripts):
```
Read: standards/argument-naming.md
```

Covers typed-ID flags (`--lesson-id`, `--plan-id`, `--task-number`, `--module`, `--component`), read-verb canonicalization (`read` vs `get` vs `exists`), `--module` vs `--name`, and Python-stdlib log-level naming. Includes the canonical-forms table for in-scope `manage-*` scripts.

### Step 4: Load the Coverage Contract (As Needed)

**Scope × thoroughness** (load for any coverage-class work — sweeps, audits, refactors, refines, and any task whose value comes from how completely it covered a surface):
```
Read: standards/thoroughness.md
```

Covers the orthogonality of effort and thoroughness, the thoroughness ladder (T1–T5), the scope ladder, the grade-to-the-floor rule, the coupling constraint `reject thoroughness ≥ T4 ∧ scope < component`, and the floor-graded self-report.

### Step 5: Load the Coverage-Gathering Contract (As Needed)

**Coverage-gathering contract** (load when building or modifying a broad-pass component — a wide audit, compliance sweep, simplification/refactor campaign, or pre-submission review — that gathers a coverage cell from the user and consumes it to govern its breadth/depth):
```
Read: standards/coverage-gathering-contract.md
```

Covers the reusable two-dial contract that broad-pass components implement: the canonical `AskUserQuestion` gather shape, the static cell→instruction expansion table (the operational instruction per cell), the gather→expand→consume obligation, the status.json persistence + transport mechanism (identifier + expanded instruction, mirroring `compatibility` + `compatibility_description`), and the Current-Implementations table. `thoroughness.md` defines the LEVELS; this contract's expansion table defines the OPERATIONAL INSTRUCTION per cell (no duplication).

## Hard Rules (never override)

### Bash: One command per call

Each Bash tool call must contain exactly ONE command. Never combine with newlines, `&`, `&&`, `;`, or inline env-var assignment of the form `VAR=val cmd`.

The `VAR=val cmd` shape trips the host platform's permission UI and obscures the env-var contract. Pass values as flag args instead, or set the env var in a separate invocation header outside the command line. See [standards/tool-usage-patterns.md § Env-var dispatch in Bash](standards/tool-usage-patterns.md#env-var-dispatch-in-bash) for the full anti-pattern walkthrough and both safe alternatives.

### Bash: Timeout from architecture-resolved canonical command

When invoking a build/verify canonical command (resolved via `plan-marshall:manage-architecture:architecture resolve` or via a workflow step that surfaces the canonical envelope), inspect the resolved TOON for `bash_timeout_seconds` and `execution_tier` fields:

- **`execution_tier: per_task`** — the Bash call runs synchronously inside the current dispatch. Pass `timeout: bash_timeout_seconds * 1000` (milliseconds) on the Bash tool call. Never accept the default 2-minute Bash timeout for these commands; the host platform will silently auto-move the call to background and the dispatch will lose the synchronous-return path.
- **`execution_tier: orchestrator`** — the canonical command is owned by the orchestrator (e.g. long-running module-tests/verify/coverage on a worktree that the orchestrator drives). Sub-agents MUST NOT invoke the command via Bash from inside the dispatch. When the loaded workflow documents a hand-off step, follow it; otherwise return control to the orchestrator (with a TOON indicating the command cannot run within this dispatch) so the orchestrator can dispatch the build in its own envelope with the correct timeout.

The floor for ad-hoc build/verify invocations outside the architecture-resolved envelope is 600000ms (10 minutes); the architecture-resolved `bash_timeout_seconds` always supersedes the floor.

The recurrence signature and orchestrator-tier rationale are documented in the adaptive-timeout infrastructure design.

### Bash: No file operations

Never use Bash for file discovery or reading. Use the structured architecture inventory first (`architecture files --module X`, `architecture which-module --path P`, `architecture find --pattern P`); fall back to Glob, Grep, Read when narrowing to sub-module components, scanning content inside an already-known file, or when the architecture verb returns elision. See "Structured queries first" below for the full rule.

### Skill workflow: No improvisation

Execute ONLY the commands documented in the loaded skill's workflow. Never add discovery steps, invent arguments, or skip documented steps.

### Structured queries first

Before reaching for `Glob` or `Grep` for codebase navigation (file discovery, module identification, path resolution), consult the structured architecture inventory via `architecture files --module X`, `architecture which-module --path P`, or `architecture find --pattern P`. `Glob`/`Grep` are the fallback for sub-module component lookup, content searches inside an already-known file, or when the architecture verb returns elision — not the routine first choice. See [`agent-behavior-rules.md` § Structured queries first](standards/agent-behavior-rules.md#structured-queries-first) for the full rule and a worked example.

### Never invent script subcommands

When issuing `python3 .plan/execute-script.py {notation} {subcmd} ...` calls, quote the subcommand and flag names verbatim from the executor mappings or the script's `--help` output. Never extrapolate plausible-sounding verbs (`add-fix-task`, `read-context`, `tail`, `--filter-status`, `--tail`) from surrounding workflow prose. Plausible names that match the workflow's narrative but not the actual argparse declaration produce silent `exit_code: 2` failures that bypass the script body and corrupt downstream behaviour.

**Why:** Multiple recurrences across skill workflows and orchestrators have confirmed this failure is structural: skill workflows and orchestrators that reference renamed or removed CLI shapes produce silent `exit_code: 2` failures that bypass the script body and corrupt downstream behaviour. The same failure mode has hit phase skills, the retrospective orchestrator, and the execute-task fix-and-retry path.

**Recurrence signatures (self-audit checklist):** Before issuing any `manage-*` call, run the call against these four canonical argparse-rejection signatures observed across phase-6-finalize workflow steps and other plan phases. Each entry names the wrong shape, a concrete invented-vs-canonical example from the lesson catalogue, and the correct shape per the live argparse declaration:

1. **Verb-paraphrase** — synthesizing a verb that *names the goal* rather than quoting the declared subcommand. The invented verb reads naturally in workflow prose but does not exist in the argparse `choices`. Examples: `qgate query` → canonical `qgate list`; `update-status` → canonical `update --status {value}`; `show` / `status` / `start` → canonical `read` / `list` (`manage-tasks` has no `start`; mark a task running with `update --status in_progress`).
2. **Top-level `--plan-id` / `--project-dir` where the flag is verb-scoped** — placing `--plan-id` or `--project-dir` immediately after the notation on `manage-architecture` / `manage-config`, where those flags are declared on the subcommand (or named `--audit-plan-id`), not at the top level. Example: `manage-architecture --plan-id X resolve …` → canonical `manage-architecture resolve --command quality-gate --audit-plan-id X`.
3. **Doubled bundle-prefix** — repeating the trailing notation segment as the first positional. The notation already ends in `:ci`, so the first positional must be the domain verb, not a second `ci`. Example: `tools-integration-ci:ci ci pr create …` → canonical `tools-integration-ci:ci pr create …` (first positional is one of `pr` / `checks` / `issue` / `branch`).
4. **Missing required `--phase`, and `--resolution` vs `--status` confusion** — omitting the mandatory `--phase` on phase-scoped finding verbs, or substituting a plausible-but-wrong flag name. Examples: `manage-findings qgate list --plan-id X` → canonical `manage-findings qgate list --plan-id X --phase {phase}` (`--phase` is required); `--status resolved` → canonical `--resolution {value}` where the verb declares `--resolution`, not `--status`.

**How to apply:** When in doubt, invoke the script with `--help` first (`python3 .plan/execute-script.py {notation} --help` and `python3 .plan/execute-script.py {notation} {subcmd} --help`), or grep `.plan/execute-script.py`'s embedded `SCRIPTS = { ... }` mapping. The `ARGUMENT_NAMING_*` plugin-doctor rule cluster (unconditionally active under `quality-gate`) catches drift at edit time as the structural guard against this class of failure.

**Authoring contract:** This rule operationalizes the explicit-call-or-xref authoring standard — see `marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md` § "Script invocation in documentation" for the canonical contract (exact inline call vs xref to the owning skill's `## Canonical invocations` section) and the `manage-invocation-invalid` / `missing-canonical-block` rules that enforce it.

### Subagents are leaves — no further dispatch

You may be running inside a dispatched `execution-context` envelope. A dispatched subagent is a **leaf** — it cannot spawn further subagents (no `Task:` dispatches). All cross-envelope dispatch originates only from the main-context orchestrator. When a workflow step calls for a further dispatch, return control to the orchestrator with the signal it needs (the workflow's declared return payload); do not attempt the dispatch yourself. Loading `Skill:` directives in-context is permitted — that is in-context skill loading, not subagent dispatch.

Canonical contract: [`ref-workflow-architecture/standards/agents.md`](../ref-workflow-architecture/standards/agents.md) is the single source of truth for the leaf/dispatch-topology invariant. Do not restate the topology diagram here — see that document for the normative statement.

### Git targeting: plain `git` in a cwd-pinned context, `git -C {path}` cross-tree, never `cd {path} && git ...`

The `cd {path} && git <subcommand>` compound form is **always forbidden** — even when the target path is a worktree absolute path that the model already has in context. Two reasons, both load-bearing:

1. **Security prompt**: the host platform treats `cd` followed by `git` in the same Bash call as a potential bare-repository-attack pattern and pops a permission prompt that disrupts the user.
2. **One-command-per-call**: `cd {path} && git ...` is two commands joined by `&&`, which already violates the [Bash: One command per call](#bash-one-command-per-call) rule above.

The git-targeting form to use depends on the execution context:

- **Phase-5+ cwd-pinned context** (the move-based, cwd-pinned model, ADR-002): cwd is pinned to the plan's worktree (or to the main checkout when `use_worktree=false`), so plain `git <subcommand>` already acts on the correct tree. Use plain `git` — do NOT route through `git -C {worktree_path}`. The pinned cwd is the resolution anchor; explicit path forwarding is redundant and re-leaks the worktree absolute path the cwd-pinned model deliberately removed. See [`tools-script-executor/standards/cwd-policy.md`](../tools-script-executor/standards/cwd-policy.md) § "Worktree-path passing is unnecessary under cwd-pinning".
- **Cross-tree or non-pinned context**: when a git command must target a tree that is NOT the pinned cwd — a genuinely cross-tree operation, a main-checkout-from-worktree read, or any caller invoked outside a pinned-cwd context (phases 1-4, post-worktree-removal cleanup, fixture-driven invocations) — use the explicit `git -C {path} <subcommand>` form. This is the only surviving use of `git -C`.

When operating against the main checkout outside a pinned context, plain `git` (cwd already the main checkout) or `git -C .` are both acceptable — never `cd && git`. See `workflow-integration-git/standards/worktree-handling.md` for the worktree-specific application of this rule.

## Related

- `dev-general-code-quality` — Complementary quality standards (SRP, CQS, complexity)
- `dev-general-module-testing` — Testing methodology standards (AAA pattern, coverage)

## Standards Reference

| Standard | Purpose |
|----------|---------|
| agent-behavior-rules.md | Boy Scout Rule, ask users, research, tool usage, dependencies |
| tool-usage-patterns.md | Tool selection, file operations, content search, Bash safety, build resolution |
| argument-naming.md | Typed-ID flags, read-verb canonicalization, `--module` over `--name`, stdlib log-level names for `manage-*` scripts |
| thoroughness.md | Scope × thoroughness coverage contract: thoroughness ladder (T1–T5), scope ladder, grade-to-the-floor rule, coupling constraint `reject thoroughness ≥ T4 ∧ scope < component`, floor-graded self-report |
| coverage-gathering-contract.md | The reusable coverage-gathering contract: canonical `AskUserQuestion` gather shape, the static cell→instruction expansion table, the gather→expand→consume implementor obligation, status.json persistence (identifier + expanded instruction), Current-Implementations table |

## See Also

- [`extension-api:dispatch-granularity`](../extension-api/standards/dispatch-granularity.md) — Dispatch granularity heuristics (10K rule, script-over-dispatch, bundle-over-iterate, per-iteration only when models differ or parallel; find the LLM core). Lives in `extension-api` because it governs decisions about the `execution-context` extension point.
