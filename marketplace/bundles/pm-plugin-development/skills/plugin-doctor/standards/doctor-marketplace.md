# Doctor Marketplace Workflow

Full marketplace batch analysis using hybrid two-phase workflow.

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes `doctor-marketplace` — a `manage-*`-scoped convention leaves exactly those calls with no rule at all, which is the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The middle clause is what the `ci` family makes load-bearing: a `ci` verb reports failure as `status: error` at exit 0 **by design**, so a caller must branch on the payload `status` and never on the exit code. That rule is stated authoritatively in `plan-marshall:tools-integration-ci`; it is not restated here.

Step-level exceptions — calls whose non-zero exit is itself the signal — are documented inline in the step that issues them.

## Parameters

- `--no-fix` (optional): Generate report only, skip fix phase

## Phase 1: Script Batch Processing

**EXECUTE** the batch script to enumerate, analyze, and apply safe fixes.

If executor exists, use notation:
```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace fix
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace report
```

Otherwise, use the bootstrap pattern with `${PLUGIN_ROOT}` (see `script-executor` skill):
```bash
DOCTOR_SCRIPT=$(ls ${PLUGIN_ROOT}/pm-plugin-development/*/skills/plugin-doctor/scripts/doctor-marketplace.py | head -n 1)
python3 "$DOCTOR_SCRIPT" fix
python3 "$DOCTOR_SCRIPT" report
```

Parse the JSON output to get:
- `report_dir`: Directory containing report files
- `report_file`: Path to JSON report
- `findings_file`: Path where LLM should write findings.md
- `summary`: Issue counts and categorization

## Phase 2: LLM Analysis

1. **Read the JSON report**:
   ```text
   Read: {report_file}
   ```

2. **Tool Coverage Analysis via Agents** (for items in `components_for_tool_analysis`):

   Compute the dispatch target via the role resolver, **once per component about to be dispatched** — not once for the whole batch. The resolve carries the dispatch context (`--workflow`/`--plan-id`/`--caller`), and the resolve seam emits the `[DISPATCH]` work-log line and its paired decision-log record as a side-effect of each resolve (see [`plan-marshall:ref-workflow-architecture/standards/dispatch-logging.md`](../../../../plan-marshall/skills/ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract). Resolving once and reusing the `target` across N spawns would leave N−1 of them with no audit record at all — the per-role blind spot the seam exists to close. Do NOT hand-write a separate `[DISPATCH]` line, and do NOT capture the result with a `$(...)` substitution (forbidden by the no-`$()` Bash hard rule) — run the call and read `target` from its TOON output:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
     effort resolve-target --phase phase-6-finalize --role verification-feedback \
     --workflow pm-plugin-development:plugin-doctor/workflow/tool-coverage.md --plan-id {plan_id} \
     --caller pm-plugin-development:plugin-doctor
   ```

   Extract the `target` field from the TOON output. Then dispatch `plan-marshall:{target}` for each component in parallel (one Task call per file in a single message):

   ```text
   Task: plan-marshall:{target}
     prompt: |
       name: tool-coverage
       plan_id: {plan_id}
       skills[1]:
       - pm-plugin-development:plugin-doctor
       workflow: pm-plugin-development:plugin-doctor/workflow/tool-coverage.md
       WORKTREE: {worktree_path}

       file_path: {file}
       declared_tools: {declared_tools}
       component_type: {type}
   ```

   The agent semantically determines:
   - Which tools are actually USED (not just mentioned in docs)
   - Missing tools (used but not declared)
   - Unused tools (declared but not used)
   - False positives (tool mentioned in documentation, not actual usage)

   **Why agents?** Script-based regex detection causes false positives:
   - "Global settings" matched "Glob"
   - "task=" parameter matched "Task"
   - Documentation about tools matched as usage

3. **Aggregate results using TOON format**:

   Use `templates/tool-coverage-results.toon` template to aggregate agent results:
   ```toon
   analysis_timestamp: 2025-12-11T10:30:00Z
   total_components: 5

   results[5]{file,type,bundle,declared_tools,used_tools,missing_tools,unused_tools,confidence}:
   agents/foo.md,agent,pm-dev-java,"Read,Write","Read,Write",,Write,high
   commands/bar.md,command,plan-marshall,"Skill,Read","Skill,Read,Bash",,Bash,medium
   ...

   summary:
     components_analyzed: 5
     with_missing_tools: 1
     with_unused_tools: 2
     false_positives_detected: 3
   ```

   **Why TOON?** Uniform arrays of analysis results achieve ~50% token reduction vs JSON.

4. **Cross-Bundle Reference Validation**:

   Validate that all `Skill:` directives across components resolve to existing skills:

   a. `Skill:` directives are content tokens inside files, not first-class entries in the architecture inventory — Grep is the right tool here. Use it as the documented fallback for content-level cross-bundle scanning:
      ```text
      Grep: pattern="Skill:\\s+[\\w-]+:[\\w-]+" path="marketplace/bundles" output_mode="content"
      ```

   b. Extract each referenced skill notation (e.g., `plan-marshall:manage-lessons`)

   c. For each reference, verify the target skill directory exists:
      ```text
      Glob: pattern="marketplace/bundles/{bundle}/skills/{skill}/SKILL.md"
      ```

   d. Report broken references (renamed, removed, or misspelled skills) as **Needs Review** findings

   This catches cross-bundle breakage that per-component analysis misses — e.g., when a skill is renamed in bundle A but bundle B still references the old name.

5. **Create findings.md** with:
   - Executive summary with statistics
   - Bundle-by-bundle analysis
   - Issue categorization:
     - **Fixed**: Safe fixes already applied by script
     - **False Positive**: Rule violations that are intentional
     - **Intentional**: Design decisions (e.g., Task tool for orchestration)
     - **Needs Review**: Actual issues requiring attention
   - Tool coverage findings from aggregated TOON
   - Recommendations for manual review

5. **Write findings.md**:
   ```text
   Write: {findings_file}
   ```

## Phase 3: Process Risky Fixes

For each item in `llm_review_items` from the JSON report:

1. **Evaluate context** - Is this a real issue or false positive?
2. **If real issue, prompt for risky fix**:
   ```text
   AskUserQuestion:
     question: "Fix {issue_type} in {file}?"
     options:
       - label: "Yes" description: "Apply fix"
       - label: "No" description: "Skip"
       - label: "Skip All" description: "Skip remaining"
   ```
3. **Apply fix if approved** using Edit tool

## Phase 4: Report Summary

Display final summary:
```text
## Marketplace Health Report

**Report Location**: {report_dir}

| Metric | Value |
|--------|-------|
| Total Bundles | X |
| Total Components | X |
| Safe Fixes Applied | X |
| Issues Reviewed | X |
| False Positives | X |

**Files Created**:
- {report_file}
- {findings_file}
```
