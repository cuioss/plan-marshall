# Component Analysis Workflow

Semantic analysis of marketplace component files (skills, agents, commands, tests) against a request, with each file classified as CERTAIN_INCLUDE / CERTAIN_EXCLUDE / UNCERTAIN. Carved from the legacy `ext-outline-component-agent.md` (deleted in Phase 5 of the agents-to-execution-context refactor); dispatched via `Task: plan-marshall:execution-context-{level}` with this doc as `workflow`.

## Contract reference

Implements: [`plan-marshall:phase-3-outline/standards/component-analysis-contract.md`](../../../../plan-marshall/skills/phase-3-outline/standards/component-analysis-contract.md). That document carries the canonical input parameters, prompt structure, output format, and critical rules — this workflow doc adds the dispatch-side concerns and the per-component-type LLM-judgement context.

## Inputs

| Prompt-body field | Required | Description |
|-------------------|:--------:|-------------|
| `plan_id` | Yes | Plan identifier for assessment logging via `manage-findings assessment add`. |
| `WORKTREE` | Yes | Repo-relative working directory (`.` for main checkout). |
| `component_type` | Yes | One of `skills`, `agents`, `commands`, `tests`. |
| `request_text` | Yes | The clarified request describing what needs to be changed. |
| `files[]` | Yes | Explicit file paths to analyse (from inventory scan). |

Skills the caller MUST forward in `skills[]`: `plan-marshall:manage-findings` (assessment logging).

## Critical rules

- Execute bash commands EXACTLY as written below. NEVER substitute with equivalent commands (`cat`, `head`, `tail`, `echo`, etc.) — those trigger security prompts that block the dispatch.
- Use the `Read` tool ONLY for analysing component files, NOT for `.plan/` files. All `.plan/` access goes through `python3 .plan/execute-script.py` manage-* scripts.
- All assessment logging MUST use the exact command in [Logging command](#logging-command) below; do not invent alternate notations.

## Logging command

Log each assessment using this EXACT command:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings assessment add \
  --plan-id {plan_id} --file-path {file_path} \
  --certainty {CERTAIN_INCLUDE|CERTAIN_EXCLUDE|UNCERTAIN} \
  --confidence {0-100} \
  --agent execution-context/{component_type} \
  --detail "{reasoning}" \
  --evidence "{evidence}"
```

| Parameter | Source |
|-----------|--------|
| `{plan_id}` | From the dispatch prompt body |
| `{file_path}` | Current file being analysed |
| `{component_type}` | From the dispatch prompt body |
| `{CERTAINTY}` | Per-file classification result |
| `{CONFIDENCE}` | 0–100 |
| `{reasoning}` | Why this decision |
| `{evidence}` | Specific lines / sections |

The `--agent` value is `execution-context/{component_type}` (post-refactor); the legacy value `ext-outline-component-agent/{component_type}` is retired alongside the agent deletion in Phase 5.

## Component-specific context

Select context based on the `component_type` input:

### `component_type == skills`

SKILL.md files typically have these sections:

| Section | Purpose |
|---------|---------|
| `## Output`, `### Output` | Skill's output specification |
| `## Workflow` | Workflow steps with examples |
| `## Configuration` | Input / config, not output |
| `## Integration` | How skill connects to others |

**Key distinction**: content in "Output" sections defines what the skill produces; content in "Workflow" or example sections may show formats as documentation, not as the skill's own output.

### `component_type == agents`

Agent files typically have these sections:

| Section | Purpose |
|---------|---------|
| `## Output`, `### Return Results` | Agent's output specification |
| `## Input` | Input parameters |
| `## Task` | Task description |
| `Step N: Return` | Final step with return format |

**Key distinction**: content in "Output" or "Return Results" sections defines what the agent produces; agents may have both success and error output formats.

### `component_type == commands`

Command files typically have these sections:

| Section | Purpose |
|---------|---------|
| `## Output`, `### Output` | Command's output specification |
| `## Parameters` | Input parameters |
| `## Usage` | Usage examples |
| `## Workflow` | Implementation steps with examples |

**Key distinction**: content in "Output" sections defines what the command produces; content in "Usage" or workflow sections may show formats as examples.

### `component_type == tests`

Test files (`test_*.py`, `conftest.py`) have these patterns:

| Section | Purpose |
|---------|---------|
| Test functions (`def test_*`) | Individual test cases |
| Fixtures (`@pytest.fixture`) | Test setup / teardown |
| Parametrize decorators | Test data variations |
| Assert statements | Verification logic |

**Key distinction**: changes to tested components may require test updates. Look for tests that verify the behaviour being changed, tests that use formats / patterns being modified, and `conftest.py` fixtures that provide test data in affected formats.

## Migration Analysis Framework

For migration requests (change_type: `tech_debt` with migration pattern), load the migration analysis framework before processing files:

```
Read: marketplace/bundles/pm-plugin-development/skills/ext-outline-workflow/references/migration-analysis-framework.md
```

This provides evidence-based classification with format parameter extraction, per-file evidence collection, and a decision matrix for CERTAIN_INCLUDE / CERTAIN_EXCLUDE / UNCERTAIN classification.

## Task execution

Process each numbered file section IN ORDER as provided by the dispatch prompt body. For each `### File N:` section:

1. **Read** the file at the specified path.
2. **Extract format parameters** (once per batch, from `request_text`):
   - Identify `source_format` and its indicators.
   - Identify `target_format` and its indicators.
   - Identify `scope_indicator` (what content type is affected).
3. **Extract evidence** from the file:
   - Does the file have content in the scope area? (`scope_relevance`)
   - What source-format indicators are present? (`source_format_evidence`)
   - What target-format indicators are present? (`target_format_evidence`)
   - Document specific line numbers for each.
4. **Apply the decision matrix** from the Migration Analysis Framework — use the evidence to determine classification; follow the IF / ELSE logic exactly.
5. **Assess confidence** (0–100 %):
   - 90–100 %: clear evidence, single format present.
   - 80–89 %: good evidence, minor ambiguity.
   - 50–79 %: mixed signals, both formats present.
   - 20–49 %: weak evidence, format unclear.
6. **Execute the logging command** above, immediately after analysing each file, BEFORE moving to the next file section.
7. **Track counts** for the final summary.

## Output

```toon
status: success
display_detail: "<≤80 char ASCII summary>"
component_type: {component_type}
bundle: {bundle}
total_analyzed: {count}
certain_include: {count}
certain_exclude: {count}
uncertain: {count}
assessments_logged: {count}
```

**OUTPUT RULE**: Do NOT output any text except the final TOON summary. All analysis, reasoning, and assessments are logged to `assessments.jsonl` via bash commands; the parent workflow reads `assessments.jsonl` for details.
