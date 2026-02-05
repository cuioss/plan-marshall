# Doctor Marketplace Workflow

Full marketplace batch analysis using hybrid two-phase workflow.

## Parameters

- `--no-fix` (optional): Generate report only, skip fix phase

## Step 1: Phase 1 - Script Batch Processing

**EXECUTE** the batch script to scan, analyze, and apply safe fixes.

If executor exists, use notation:
```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace fix
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace report
```

Otherwise, use bootstrap pattern with `${PLUGIN_ROOT}` (see `script-executor` skill):
```bash
python3 ${PLUGIN_ROOT}/pm-plugin-development/*/skills/plugin-doctor/scripts/doctor-marketplace.py fix
python3 ${PLUGIN_ROOT}/pm-plugin-development/*/skills/plugin-doctor/scripts/doctor-marketplace.py report
```

Parse the JSON output to get:
- `report_dir`: Directory containing report files
- `report_file`: Path to JSON report
- `findings_file`: Path where LLM should write findings.md
- `summary`: Issue counts and categorization

## Step 2: Phase 2 - LLM Analysis

1. **Read the JSON report**:
   ```
   Read: {report_file}
   ```

2. **Tool Coverage Analysis via Agents** (for items in `components_for_tool_analysis`):

   Spawn `tool-coverage-agent` for each component. **Use parallel spawning** for efficiency:
   ```
   # Spawn multiple agents in parallel (single message with multiple Task calls)
   Task: tool-coverage-agent (file1)
   Task: tool-coverage-agent (file2)
   Task: tool-coverage-agent (file3)
   ...
   ```

   Each agent receives:
   - file_path: {file}
   - declared_tools: {declared_tools}
   - component_type: {type}

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
   commands/bar.md,command,pm-workflow,"Skill,Read","Skill,Read,Bash",,Bash,medium
   ...

   summary:
     components_analyzed: 5
     with_missing_tools: 1
     with_unused_tools: 2
     false_positives_detected: 3
   ```

   **Why TOON?** Uniform arrays of analysis results achieve ~50% token reduction vs JSON.

4. **Create findings.md** with:
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
   ```
   Write: {findings_file}
   ```

## Step 3: Process Risky Fixes

For each item in `llm_review_items` from the JSON report:

1. **Evaluate context** - Is this a real issue or false positive?
2. **If real issue, prompt for risky fix**:
   ```
   AskUserQuestion:
     question: "Fix {issue_type} in {file}?"
     options:
       - label: "Yes" description: "Apply fix"
       - label: "No" description: "Skip"
       - label: "Skip All" description: "Skip remaining"
   ```
3. **Apply fix if approved** using Edit tool

## Step 4: Report Summary

Display final summary:
```
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
