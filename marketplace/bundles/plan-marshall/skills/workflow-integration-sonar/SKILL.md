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
- Each workflow step that invokes a script has an explicit bash code block with the full `python3 .plan/execute-script.py` command
- Suppressions require inline comments explaining the rationale
- Fix-vs-suppress decisions must be logged

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `project` | required | SonarQube project key |
| `pr` | optional | Pull request ID |
| `severities` | optional | Filter by severity (comma-separated: BLOCKER,CRITICAL,MAJOR,MINOR,INFO) |
| `types` | optional | Filter by type (comma-separated: BUG,CODE_SMELL,VULNERABILITY) |

## What This Skill Provides

### Workflows (Absorbs 2 Agents)

1. **Fetch Issues (MCP Delegation)** - Constructs and executes MCP tool call for Sonar issue retrieval
   - Assembles parameters inline (no script needed) and calls the SonarQube MCP tool
   - Replaces: sonar-issue-fetcher agent

2. **Fix Issues Workflow** - Processes and resolves issues
   - Triages each issue for fix vs suppress
   - Implements fixes or adds suppressions
   - Replaces: sonar-issue-triager agent

## When to Activate This Skill

- Fixing Sonar issues in PRs
- Processing SonarQube quality gate failures
- Implementing code fixes for violations
- Adding justified suppressions

## Workflows

### Workflow 1: Fetch Issues (MCP Delegation)

**Purpose:** Fetch Sonar issues via the SonarQube MCP tool. No script needed — construct the MCP call directly from the parameters.

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
   (default: `mcp__sonarqube__search_sonar_issues_in_projects`). If the
   connected MCP server uses a different tool name, update `marshal.json`
   rather than editing this skill. Discover available tools via MCP tool
   listing if the configured name fails.

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

### Always Fix (enforced by script)
- VULNERABILITY type (any severity — forced to `fix` action with `high`+ priority)
- SECURITY_HOTSPOT type (any severity — forced to `fix` action with `high`+ priority, requires review)
- BLOCKER severity
- Security rules (e.g., `java:S3649`, `java:S5131`, `javascript:S3649`, `python:S5131`)

### Fix Preferred
- CRITICAL severity
- BUG type
- Resource leaks (e.g., `java:S2095`)

### May Suppress
- INFO severity
- TODO comments (`*:S1135`) - if tracked in issue management
- Unused fields for reflection (`java:S1068`)
- Console/stdout in test code (`java:S106`, `javascript:S106`, `python:S106`)
- Missing assertions in tests (`java:S2699`)

**Supported languages:** Java, JavaScript, TypeScript, Python. Unrecognized rules fall back to the Sonar issue message for triage guidance.

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

## Triage Override Guidance

The script triage is rule-based and handles common Sonar rules well, but novel or project-specific rules may get a default "fix" action when suppression is more appropriate (or vice versa). When you have context about the codebase that the script lacks — such as knowing a field is used via reflection, or that a pattern is intentional — override the script's decision and document your reasoning in the suppression comment or commit message.

## Error Handling

When a script or step returns failure:
- **MCP tool failure**: Report error. Verify SonarQube MCP server is connected and project key is correct.
- **MCP tool returns empty**: No issues found — report success with zero counts.
- **triage failure** (invalid JSON): Log warning, skip the issue, continue processing remaining.
- **Fix implementation failure**: Report which file/line failed. Do not suppress as fallback — ask the caller.
- **MCP status change failure**: Log warning, continue — marking resolved is best-effort.
- **Build verification failure after fixes**: Report failing tests/compilation. Do not commit broken fixes.

## Integration

### Related Skills
- **workflow-integration-ci** - Often used together in PR workflows
- **workflow-integration-git** - Commits fixes
- **workflow-pr-doctor** - Orchestrates this skill with CI and git workflows
