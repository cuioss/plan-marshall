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

## What This Skill Provides

### Workflows (Absorbs 2 Agents)

1. **Fetch Issues Workflow** - Retrieves Sonar issues for PR
   - Uses SonarQube MCP tool or API
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

### Workflow 1: Fetch Issues

**Purpose:** Fetch Sonar issues for a PR or project.

**Input:**
- **project**: SonarQube project key
- **pr** (optional): Pull request ID
- **severities** (optional): Filter by severity
- **types** (optional): Filter by type

**Steps:**

1. **Determine Context**
   ```bash
   python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr view
   ```

2. **Fetch Issues**

   The fetch script generates MCP tool call parameters — it does NOT fetch
   issues directly. Use it to construct the call, then execute via MCP:

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar fetch \
     --project {key} [--pr {id}] [--severities BLOCKER,CRITICAL] [--types BUG,VULNERABILITY]
   ```

   The script outputs an `mcp_instruction` with the tool name and parameters.
   Execute the returned instruction via the SonarQube MCP tool:

   ```
   mcp__sonarqube__search_sonar_issues_in_projects(
     projects: ["{project_key}"],
     pullRequestId: "{pr_number}",
     severities: "{filter}",
     types: "{types}"
   )
   ```

3. **Return Structured List**

**Output:**
```toon
project_key: ...
pull_request_id: ...
issues[1]{key,type,severity,file,line,rule,message}:
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

2. **Triage Each Issue**
   For each issue:

   Script: `plan-marshall:workflow-integration-sonar`

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar triage --issue '{json}'
   ```

   Script outputs decision:
   ```toon
   issue_key: ...
   action: fix|suppress
   reason: ...
   priority: critical|high|medium|low
   suggested_implementation: ...
   suppression_string: "// NOSONAR rule - reason"
   ```

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
   ```
   mcp__sonarqube__change_sonar_issue_status(
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

### sonar.py fetch

**Purpose:** Generate MCP tool call parameters for fetching Sonar issues. Does not fetch directly — returns the MCP instruction that the caller must execute via the SonarQube MCP tool.

**Usage:**
```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar fetch --project <key> [--pr <id>] [--severities <list>]
```

**Output:** TOON with MCP instruction and expected response structure

### sonar.py triage

**Purpose:** Analyze a single issue and determine fix vs suppress.

**Usage:**
```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar triage --issue '{"key":"...", "rule":"...", ...}'
```

**Output:** TOON with action decision

## Issue Classification

### Always Fix
- BLOCKER severity
- VULNERABILITY or SECURITY_HOTSPOT type
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

## Error Handling

When a script or step returns failure:
- **fetch script failure**: Report error. Verify SonarQube MCP server is connected and project key is correct.
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
