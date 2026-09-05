# Aspect: Script Failure Analysis

Analyze script failures from the plan to identify source components, trace how instructions led to the failed call, and propose fixes. Content absorbed from the original `pm-plugin-development:tools-analyze-script-failures` skill.

**Conditional**: only meaningful when `log_analysis.counts.errors_script > 0`.

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes `collect-fragments` — a `manage-*`-scoped convention leaves exactly those calls with no rule at all, which is the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The middle clause is what the `ci` family makes load-bearing: a `ci` verb reports failure as `status: error` at exit 0 **by design**, so a caller must branch on the payload `status` and never on the exit code. That rule is stated authoritatively in `plan-marshall:tools-integration-ci`; it is not restated here.

Step-level exceptions — calls whose non-zero exit is itself the signal — are documented inline in the step that issues them.

## Inputs

- `script.log` — complete list of script invocations and outcomes (via `manage-logging read --type script`).
- `work.log` — surrounding `[ERROR]` entries that reference the failed notation.
- Source components referenced in the failed calls (skill/agent/command markdown files).

## Workflow (LLM)

### Step 1: Extract failure details

For each non-zero-exit script call found in `script.log`:
- Complete notation (`{bundle}:{skill}:{script}`).
- Subcommand and argument string.
- Exit code and error message.

### Step 2: Trace origin

Determine the source component type using surrounding `work.log` `[SKILL]`/`[STEP]` entries:

| Source Type | How to Identify |
|-------------|-----------------|
| **Command** | `[SKILL] (command:/{name})` just above the failure |
| **Agent** | `[SKILL] (agent:{name})` just above the failure |
| **Skill** | `[SKILL] (plan-marshall:{skill-name})` just above the failure |

Read the source component file to find the instruction context.

### Step 3: Root cause classification

| Category | Description | Fix Location |
|----------|-------------|--------------|
| **Missing Script Instruction** | Script not documented in component | Add to component |
| **Wrong Script Parameters** | Parameters incorrect or missing | Fix component instruction |
| **LLM Invented Script** | No instruction, LLM guessed script call | Add flow step to component |
| **Missing API** | Operation needed but no script exists | Create new script |
| **Script Bug** | Script exists but has bug | Fix script implementation |
| **Script Not Found** | Notation invalid or script missing | Fix notation or add script |

## TOON Fragment Shape

```toon
aspect: script_failure_analysis
status: success
plan_id: {plan_id}
failures[*]{notation,exit_code,category,source_component,source_file,proposal}:
  "plan-marshall:manage-files:manage-files",2,wrong_parameters,"plan-marshall:phase-4-plan","marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md","fix --file argument name"
findings[*]{severity,message}:
  error,"1 script failure traced to phase-4-plan instruction"
```

## LLM Interpretation Rules

- Every failure MUST be traced to an exact source file; otherwise mark `source_component: unknown` and `category: llm_invented_script`.
- Propose a fix ONLY when the category is one of: `missing_instruction`, `wrong_parameters`, `llm_invented_script`. `script_bug` and `missing_api` require a separate plan.
- Each failure becomes a finding with `severity: error`.

## Finding Shape

```toon
aspect: script_failure_analysis
severity: error
category: {category}
notation: {notation}
source_file: {path}
message: "{one-line}"
```

## Interactive Resolution (user-invocable mode only)

In user-invocable mode, for each failure use `AskUserQuestion`:

```text
question: "How would you like to handle {notation} failure?"
options:
  - "Apply fix"      — Edit the source component to add/correct the instruction
  - "Record lesson"  — Allocate a lesson via manage-lessons add (category=bug)
  - "Skip"           — No action
```

In finalize-step mode, always record lessons for `severity: error` failures; never auto-edit components.

## Out of Scope

- Fixing the underlying script bug — the retrospective surfaces the category and proposal only.
- Analyzing non-failed scripts — that is llm-to-script-opportunities.

## Persistence

After synthesizing the TOON fragment per the shape documented above, the orchestrator writes the fragment to `work/fragment-script-failure-analysis.toon` via the `Write` tool and registers it with the bundle:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments add \
  --plan-id {plan_id} --aspect script-failure-analysis --fragment-file work/fragment-script-failure-analysis.toon
```

`compile-report run --fragments-file` consumes the assembled bundle in Step 4 of SKILL.md. The bundle file is auto-deleted on successful report write; on failure it is retained for debugging.
