---
name: workflow-integration-sonar
description: Sonar issue workflow - fetch issues, triage, and fix or suppress based on context
user-invocable: false
---

# Sonar Workflow Skill

Handles Sonar issue workflows - fetching issues from SonarQube, triaging them, and implementing fixes or suppressions.

## Enforcement

**Execution mode**: Fetch Sonar issues, triage each for fix or suppress, implement changes, verify build.

**Prohibited actions:**
- Never suppress Sonar issues without documented justification
- Never modify Sonar configuration or quality profiles
- Never skip build verification after implementing fixes

**Constraints:**
- Suppressions require inline comments explaining the rationale
- Fix-vs-suppress decisions must be logged

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project` | string | yes | — | SonarQube project key |
| `pr` | string | no | auto-detect | Pull request ID |
| `severities` | string | no | all | Filter by severity (comma-separated: BLOCKER,CRITICAL,MAJOR,MINOR,INFO) |
| `types` | string | no | all | Filter by type (comma-separated: BUG,CODE_SMELL,VULNERABILITY) |

## Prerequisites

No external skill dependencies. Workflow 1 uses the SonarQube MCP tool directly. Workflow 2 uses `triage_helpers` from `ref-toon-format` (see `ref-workflow-architecture` → "Shared Infrastructure" for the full API table).

## Architecture

```
workflow-integration-sonar (Sonar issue workflow)
  ├─> SonarQube MCP tool (issue fetching, status changes)
  └─> triage_helpers (ref-toon-format) — shared triage, error handling
```

## Workflows

### Workflow 1: Fetch Issues (MCP Delegation)

**Purpose:** Fetch Sonar issues via the SonarQube MCP tool. This workflow uses MCP directly — no script needed. The triage workflow (Workflow 2) uses `sonar.py`.

**Input:**
- **project**: SonarQube project key
- **pr** (optional): Pull request ID
- **severities** (optional): Filter by severity
- **types** (optional): Filter by type

**Steps:**

1. **Determine Context** (optional — get PR number if not provided)
   ```bash
   python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr view
   ```

2. **Fetch Issues via MCP**

   Call the SonarQube MCP tool directly with the assembled parameters.
   The tool name is configured in `marshal.json` under `sonar.mcp_tool_name`
   (default: `mcp__sonarqube__search_sonar_issues_in_projects`). The example
   below uses `{sonar_mcp_tool_name}` as a placeholder — resolve the actual
   name from `marshal.json` at runtime. If the configured name fails, discover
   available tools via MCP tool listing.

   ```
   {sonar_mcp_tool_name}(
     projects: ["{project_key}"],
     pullRequestId: "{pr_number}",       # omit if no PR filter
     severities: "{BLOCKER,CRITICAL}",   # omit if no severity filter
     types: "{BUG,VULNERABILITY}"        # omit if no type filter
   )
   ```

3. **Structure the Response**

   Parse the MCP response into a structured list for triage.

**Output:**
```toon
project_key: ...
pull_request_id: ...
issues[N]{key,type,severity,file,line,rule,message}:
  - key: ...
    type: BUG|CODE_SMELL|VULNERABILITY
    severity: BLOCKER|CRITICAL|MAJOR|MINOR|INFO
    file: ...
    line: N
    rule: java:S1234
    message: ...
statistics:
  total_issues_fetched: N
  by_severity: {}
  by_type: {}
```

---

### Workflow 2: Fix Issues

**Purpose:** Process Sonar issues and resolve them.

**Input:** Issue list from Fetch workflow or specific issue keys

**Steps:**

1. **Get Issues**
   If not provided, use Fetch Issues workflow first.

2. **Triage All Issues (Batch)**
   Collect all issues into a JSON array and triage in a single call:

   Script: `plan-marshall:workflow-integration-sonar`

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar triage-batch --issues '[{issue1}, {issue2}, ...]'
   ```

   Script outputs all decisions at once:
   ```toon
   results[N]:
     - issue_key: ...
       action: fix|suppress
       reason: ...
       priority: critical|high|medium|low
       suggested_implementation: ...
       suppression_string: "// NOSONAR rule - reason"
   summary:
     total: N
     fix: N
     suppress: N
   status: success
   ```

   For single-issue edge cases, `triage --issue '{json}'` is also available.

3. **Process by Priority**
   Order: critical → high → medium → low

4. **Execute Actions**

   **For fix:**
   - Read file at issue location
   - Apply fix using Edit tool
   - Verify fix with Grep

   **For suppress:**
   - Read file
   - Add suppression comment at line using Edit
   - Include rule key and reason

5. **Mark Issues Resolved (Optional)**

   The status-change tool name is configured in `marshal.json` under
   `sonar.mcp_status_tool_name` (default: `mcp__sonarqube__change_sonar_issue_status`):
   ```
   {sonar_mcp_status_tool_name}(
     key: "{issue_key}",
     status: ["accept"]  # or ["falsepositive"]
   )
   ```

6. **Return Summary**

**Output:**
```toon
processed:
  fixed: 4
  suppressed: 1
  failed: 0
files_modified[1]:
  - ...
status: success
```

---

## Scripts

Script: `plan-marshall:workflow-integration-sonar` → `sonar.py`

### sonar.py triage

**Purpose:** Analyze a single issue and determine fix vs suppress.

**Usage:**
```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar triage --issue '{"key":"...", "rule":"...", ...}'
```

**Output:** TOON with action decision

### sonar.py triage-batch

**Purpose:** Triage multiple issues in a single call, reducing subprocess overhead.

**Usage:**
```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar triage-batch --issues '[{"key":"I1", "rule":"java:S1234", ...}, ...]'
```

**Output:** TOON with results array and summary counts

## Issue Classification

Classification rules are data-driven — loaded from `standards/sonar-rules.json`. Key principles:

- **Always fix**: VULNERABILITY, SECURITY_HOTSPOT, and BLOCKER severity (enforced by script)
- **Fix preferred**: CRITICAL severity, BUG type, resource leaks
- **May suppress**: Rules listed in `suppressable_rules` (with documented justification)
- **Test exceptions**: Rules in `test_acceptable_rules` are acceptable in test files

**Supported languages:** Java, JavaScript, TypeScript, Python. Unrecognized rules fall back to the Sonar issue message for triage guidance.

To add or update classification, edit `standards/sonar-rules.json` instead of the script.

## Suppression Format

**Java:**
```java
// NOSONAR java:S1234 - reason for suppression
```

**JavaScript/TypeScript:**
```javascript
// NOSONAR javascript:S1234 - reason for suppression
```

**Python:**
```python
# NOSONAR python:S1234 - reason for suppression
```

## Rule Configuration

Triage rules are data-driven — loaded from `standards/sonar-rules.json`:

- **suppressable_rules**: Rules that may be suppressed with justification
- **fix_suggestions**: Rule-specific fix guidance
- **test_acceptable_rules**: Rules acceptable in test files

To add or update Sonar rule handling, edit `standards/sonar-rules.json` instead of the script.

For triage override guidance, see `ref-workflow-architecture` → "Triage Override Guidance".

## Error Handling

| Failure | Action |
|---------|--------|
| MCP tool failure | Report error. Verify SonarQube MCP server is connected and project key is correct. |
| MCP tool returns empty | No issues found — report success with zero counts. |
| triage failure (invalid JSON) | Log warning, skip the issue, continue processing remaining. |
| Fix implementation failure | Report which file/line failed. Do not suppress as fallback — ask the caller. |
| MCP status change failure | Log warning, continue — marking resolved is best-effort. |
| Build verification failure after fixes | Report failing tests/compilation. Do not commit broken fixes. |

## Related

See `ref-workflow-architecture` → "Workflow Skill Orchestration" for the full dependency graph and shared infrastructure documentation.
