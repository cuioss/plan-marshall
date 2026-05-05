---
name: workflow-integration-sonar
description: SonarQube/SonarCloud issue workflow - fetch issues, triage, and fix or suppress based on context
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

- Credentials configured via `manage-providers` for `workflow-integration-sonar`
- Script imports `triage_helpers` from `ref-toon-format` at runtime (see `ref-workflow-architecture` → "Shared Infrastructure")

## Architecture

```
workflow-integration-sonar (Sonar issue workflow)
  ├─> sonar_rest.py (issue fetching, status changes via REST API)
  ├─> _credentials_core.get_authenticated_client() (credential loading)
  └─> triage_helpers (ref-toon-format) — shared triage, error handling
```

## Usage Examples

```bash
# Producer-side: fetch + pre-filter + store one sonar-issue finding per surviving issue
python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar fetch-and-store \
  --plan-id my-plan --project com.example:project --pr 123 --severities BLOCKER,CRITICAL

# LLM consumer reads stored findings via manage-findings
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings query --plan-id my-plan --type sonar-issue
```

## Workflows

### Workflow 1: Fetch & Store Issues (Producer-Side)

**Purpose:** Stage gate-blocking Sonar issues into the per-type finding store, then let the LLM consumer drive fix-vs-suppress decisions from the stored findings.

**Producer-side flow:** `sonar.py fetch-and-store` is the only callable surface. It fetches issues via the REST client, applies the `sonar-rules.json` pre-filter (drops issues already documented as suppressable via NOSONAR / test-acceptable rules), and writes one `sonar-issue` finding per surviving issue via `manage-findings add`. Severity is derived from the Sonar severity (BLOCKER/CRITICAL/MAJOR → error, MINOR → warning, INFO → info), the rule key is captured in the finding's `rule` field, and the project key is captured in `module`.

**Steps:**

1. **Fetch & Store**:
   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar fetch-and-store \
     --plan-id {plan_id} --project {project_key} [--pr {pr_number}] [--severities BLOCKER,CRITICAL] [--types BUG,VULNERABILITY]
   ```
   Output reports `count_fetched`, `count_skipped_suppressable`, `count_stored`, and `producer_mismatch_hash_id` (set when count_stored ≠ count_fetched − count_skipped_suppressable; the mismatch is also persisted as a Q-Gate finding under phase `5-execute` with title prefix `(producer-mismatch)`).

2. **Query Stored Findings**:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings query --plan-id {plan_id} --type sonar-issue
   ```

3. **Process** — the LLM reads each finding's `detail` (which carries `key`, `rule`, `sonar_severity`, `sonar_type`, `project`, `pull_request`, `component`, `file`, `line`, and the full message) and decides fix-vs-suppress per finding. After acting on each finding, call `manage-findings resolve --hash-id {hash} --resolution fixed|suppressed|accepted`.

### (Legacy) Workflow 1: Raw REST search

For ad-hoc inspection or non-finding-store integrations, `sonar_rest.py search` remains available as the raw REST surface. Producer-side flows MUST use `sonar.py fetch-and-store`.

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

2. **Fetch Issues via REST**

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar_rest search \
     --project {project_key} \
     [--pr {pr_number}] \
     [--severities BLOCKER,CRITICAL] \
     [--types BUG,VULNERABILITY]
   ```

3. **Parse the Response**

   The script outputs structured TOON directly.

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

**Purpose:** Process stored Sonar findings and resolve them.

**Input:** `sonar-issue` findings already populated in the per-type store via Workflow 1.

**Steps:**

1. **Query Findings**:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings query --plan-id {plan_id} --type sonar-issue
   ```

2. **LLM Decides Per Finding**
   The LLM reads each finding's `detail` (key, rule, sonar_severity, sonar_type, project, file, line, message) and decides fix-vs-suppress. There is no script-side classification call.

3. **Execute Actions**

   **For fix:**
   - Read file at issue location
   - Apply fix using Edit tool

   **For suppress:**
   - Read file
   - Add suppression comment at line using Edit (e.g., `// NOSONAR rule - reason`)
   - Include rule key and reason

4. **Mark Findings Resolved**:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings resolve \
     --plan-id {plan_id} --hash-id {hash} --resolution fixed|suppressed|accepted
   ```

5. **Mark Issues Resolved on Sonar (Optional)**:
   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar_rest transition \
     --issue-key {issue_key} --transition accept
   ```

---

## Scripts

Script: `plan-marshall:workflow-integration-sonar:sonar` → `sonar.py` (producer-side fetch + pre-filter + finding store)
Script: `plan-marshall:workflow-integration-sonar:sonar_rest` → `sonar_rest.py` (raw REST API client)

### sonar.py fetch-and-store

**Purpose:** Producer-side flow — fetch gate-blocking issues via the REST client, apply the pre-filter, and persist one `sonar-issue` finding per surviving issue.

**Usage:**
```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar fetch-and-store \
  --plan-id {plan_id} --project {project_key} [--pr {pr}] [--severities ...] [--types ...]
```

**Output:** TOON with counters (`count_fetched`, `count_skipped_suppressable`, `count_stored`), the list of stored finding hash_ids, and `producer_mismatch_hash_id` when applicable.

## Issue Classification

`standards/sonar-rules.json` is now a **pre-filter only** for the producer-side `fetch-and-store` flow. Suppressable rules (rules already documented as suppressable, test-acceptable rules) are dropped before findings are written; severity/type boost mappings derive the finding `severity` field. Final fix-vs-suppress classification of stored findings belongs to the LLM consumer reading the finding `detail`.

Key principles:

- **Always fix**: VULNERABILITY, SECURITY_HOTSPOT, and BLOCKER severity (enforced by script)
- **Fix preferred**: CRITICAL severity, BUG type, resource leaks
- **May suppress**: Rules listed in `suppressable_rules` (with documented justification)
- **Test exceptions**: Rules in `test_acceptable_rules` are acceptable in test files

**Supported languages:** Java, JavaScript, TypeScript, Python. Unrecognized rules fall back to the Sonar issue message for triage guidance.

For triage override guidance, see `ref-workflow-architecture` → "Triage Override Guidance".

## Suppression Format

Generated by `sonar.py:get_suppression_string()` based on file extension and rule prefix:

**Java:** `// NOSONAR java:S1234 - reason for suppression`

**JavaScript/TypeScript:** `// NOSONAR javascript:S1234 - reason for suppression`

**Python:** `# NOSONAR python:S1234 - reason for suppression`

## Error Handling

| Failure | Action |
|---------|--------|
| REST API failure | Report error with HTTP status. Verify credentials configured and project key is correct. |
| REST API returns empty | No issues found — report success with zero counts. |
| triage failure (invalid JSON) | Log warning, skip the issue, continue processing remaining. |
| Fix implementation failure | Report which file/line failed. Do not suppress as fallback — ask the caller. |
| REST status change failure | Log warning, continue — marking resolved is best-effort. |
| Build verification failure after fixes | Report failing tests/compilation. Do not commit broken fixes. |

## Standards (Load On-Demand)

| Standard | When to Load |
|----------|-------------|
| `standards/sonar-rules.json` | Adding/updating classification rules, always-fix types, suppressable rules, fix suggestions, or suppression_syntax templates |

## Related

See `ref-workflow-architecture` → "Workflow Skill Orchestration" for the full dependency graph and shared infrastructure documentation. Called by: `plan-marshall:workflow-pr-doctor` (Sonar issue handling).
