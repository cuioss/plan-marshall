---
name: workflow-permission-web
description: Analyze and consolidate WebFetch domain permissions across projects with security research and validation
user-invocable: true
---

# Manage Web Permissions Skill

Analyzes WebFetch domains across global and project settings, researches domains for security, consolidates permissions, and provides recommendations.

## Enforcement

**Execution mode**: Analyze permissions, research unknown domains, present recommendations, apply with user approval.

**Prohibited actions:**
- Never auto-remove permissions without explicit user approval
- Never suggest overly broad permissions (e.g., `Bash(*)`)
- Do not skip security research for unknown domains

**Constraints:**
- Always research unknown domains before categorizing them
- Prefer project-local permissions over global when appropriate
- All user interactions use `AskUserQuestion` tool with proper YAML structure
- Track all statistics (domains_analyzed, permissions_added/removed, security_checks, files_read/modified) throughout workflow

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `scope` | string | no | both | Which settings to analyze: `global`, `local`, or `both`. Controls which `--global-file` and `--local-file` arguments are passed to the `analyze` script. |

## Prerequisites

No external `Skill:` dependencies. Script imports `triage_helpers` from `ref-toon-format` at runtime (see `ref-workflow-architecture` → "Shared Infrastructure"). WebSearch tool access is optional (Step 4).

## Architecture

```
workflow-permission-web (WebFetch permission analysis)
  ├─> standards/domain-lists.json (domain categorization rules)
  ├─> standards/domain-security-assessment.md (research methodology)
  └─> triage_helpers (ref-toon-format) — error handling, TOON serialization
```

## Usage Examples

```
/workflow-permission-web           # Analyze all settings
/workflow-permission-web scope=global
/workflow-permission-web scope=local
```

## Workflow

### Step 1: Load Web Security Standards

Read: standards/trusted-domains.md
Read: standards/domain-security-assessment.md

Loads trusted domains, security assessment patterns, and research methodology.

### Step 2: Collect and Analyze WebFetch Permissions

Run the analysis script to collect domains from both settings files, categorize them, detect duplicates, and generate recommendations:

```bash
python3 .plan/execute-script.py plan-marshall:workflow-permission-web:permission_web analyze \
    --global-file ~/.claude/settings.json \
    --local-file ./.claude/settings.local.json
```

The script handles missing files gracefully (reports them in output). On invalid JSON, it returns a failure status with the parse error.

**Error handling for missing/invalid files**: Ask the user via `AskUserQuestion` with options to create defaults, skip the file, or abort.

The script categorizes domains into: universal (`*`), major (from `standards/domain-lists.json`), high_reach (github.com, stackoverflow.com, etc.), suspicious (red flag patterns), and unknown (need research).

### Step 3: Detect Duplicate and Redundant Permissions

The analysis script output includes `duplicates` (domains in both global and local) and `redundant` (wildcard-covered or subdomain-covered domains). Review these in the script output.

### Step 4: Research Unknown Domains

> **Prerequisite:** This step requires `WebSearch` tool access. If unavailable, skip research and present unknown domains to the user for manual assessment.

For each domain in the script's `unknown` category:

1. **Web research** — `WebSearch: "domain-name.com reputation security"`
2. **Assess security** — check against red flags from `standards/domain-security-assessment.md`
3. **Categorize** — classify as project-specific, suspicious, or suitable for global

After researching, optionally use the `categorize` subcommand to verify classification against the static known-domain lists (this does NOT perform web research — it only checks against `domain-lists.json`):

```bash
python3 .plan/execute-script.py plan-marshall:workflow-permission-web:permission_web categorize \
    --domains '["already-researched.com", "another-known.io"]'
```

### Step 5: Generate Consolidation Recommendations

**A. If domain:* exists globally**:
```
Recommendation: Remove all specific domains (redundant)
- Remove {count} specific domains from global
- Remove {count} specific domains from local
```

**B. If no domain:***:
```
Recommendations by Category:

MAJOR_DOMAINS ({count}):
> Move to global settings (docs.oracle.com, maven.apache.org, ...)

HIGH_REACH ({count}):
> Move to global settings (github.com, stackoverflow.com, ...)

PROJECT_SPECIFIC ({count}):
> Keep in local settings

SUSPICIOUS ({count}):
> Review for removal: {list with reasons}
```

### Step 6: Display Analysis Report

Present the script's TOON output to the user in this format:

```
WebFetch Permission Analysis
────────────────────────────────────────

Global Settings:
- WebFetch permissions: {count}
- Universal access (domain:*): {yes/no}

Local Settings:
- WebFetch permissions: {count}

Total Unique Domains: {count}

By Category:
- Major domains: {count}
- High-reach domains: {count}
- Project-specific: {count}
- Suspicious: {count}
- Unknown: {count}

Duplicates Found: {count}
Redundant (if domain:* exists): {count}

Recommendations:
{detailed recommendations}
```

### Step 7: Apply Recommendations (Optional)

Ask the user via `AskUserQuestion`:

```
AskUserQuestion:
  questions:
    - question: "How would you like to apply the recommendations?"
      header: "Apply Changes"
      options:
        - label: "Apply all"
          description: "Apply all recommended changes automatically"
        - label: "Review each change"
          description: "Review and confirm each change individually"
        - label: "Skip"
          description: "Do not apply changes"
      multiSelect: false
```

If applying, use the `apply` subcommand for deterministic modification:

```bash
python3 .plan/execute-script.py plan-marshall:workflow-permission-web:permission_web apply \
    --file ~/.claude/settings.json \
    --add '["docs.oracle.com"]' \
    --remove '["redundant-domain.com"]'
```

Repeat for local settings file if needed. Track counts from script output in permissions_added and permissions_removed counters.

**Error handling:** If apply returns failure, ask the user (retry, skip file, abort). Track all successful updates in files_modified counter.

### Step 8: Report Results

Display summary of changes made and final state:

```
WebFetch Permission Update Complete
────────────────────────────────────────

Statistics:
- Domains analyzed: {domains_analyzed}
- Permissions added: {permissions_added}
- Permissions removed: {permissions_removed}
- Security checks performed: {security_checks_performed}
- Files read: {files_read}
- Files modified: {files_modified}

Final State:
- Global permissions: {count}
- Local permissions: {count}
- Total unique domains: {count}
```

## Scripts

Script: `plan-marshall:workflow-permission-web` → `permission_web.py`

| Command | Parameters | Description |
|---------|------------|-------------|
| `analyze` | `--global-file <path> --local-file <path>` | Analyze WebFetch permissions from settings files |
| `categorize` | `--domains <json-array>` | Categorize domains against trusted/known lists |
| `apply` | `--file <path> [--add <json-array>] [--remove <json-array>]` | Apply domain changes to a settings file |

### permission_web.py analyze

Reads global and local settings, extracts WebFetch domains, categorizes them, detects duplicates and redundancy, and generates consolidation recommendations. Missing files are reported but do not cause failure.

### permission_web.py categorize

Categorizes a list of domains into: universal, major, high_reach, suspicious, unknown. Also checks for red flag patterns in domain names.

### permission_web.py apply

Applies domain changes to a settings file deterministically. Adds and/or removes WebFetch domain permissions without touching other permission entries.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-permission-web:permission_web apply \
    --file ~/.claude/settings.json \
    [--add '["docs.oracle.com", "github.com"]'] \
    [--remove '["old-domain.com"]']
```

At least one of `--add` or `--remove` is required. The script reads the file, modifies only `permissions.allow` WebFetch entries, and writes back with `indent=2` formatting.

**Output** (TOON):
```toon
file: /path/to/settings.json
added: 2
removed: 1
final_domains[N]:
  - docs.oracle.com
  - github.com
status: success
```

## Error Handling

| Failure | Action |
|---------|--------|
| Settings file not found | Report as missing in statistics. Ask user via `AskUserQuestion` (create defaults, skip, abort). |
| Settings file invalid JSON | Return failure with parse error. Do not proceed with that file. |
| WebSearch unavailable | Skip domain research. Present unknowns to user for manual assessment. |
| Apply returns failure | Ask user (retry, skip file, abort). Track in files_modified counter. |
| Red flag domain detected | Flag for review. Never auto-approve suspicious domains. |

## Standards (Load On-Demand)

| Standard | When to Load |
|----------|-------------|
| `standards/domain-lists.json` | Adding/updating domain categorization, red flag patterns, or trusted domain lists |
| `standards/trusted-domains.md` | Human-readable domain reference and maintenance procedures |
| `standards/domain-security-assessment.md` | Deep security assessment for ambiguous domains |

Domain categorization is data-driven — loaded from `standards/domain-lists.json` (the source of truth for scripts). The companion `standards/trusted-domains.md` provides human-readable documentation and must be kept in sync manually when domains are added or removed. To add or update domain categorization, edit `standards/domain-lists.json` instead of the script.

## Related

See `ref-workflow-architecture` → "Workflow Skill Orchestration" for the full dependency graph and shared infrastructure documentation. Related skills: `plan-marshall:marshall-steward` (permission management wizard), `plan-marshall:tools-permission-doctor` (permission analysis), `plan-marshall:tools-permission-fix` (permission fixes).
