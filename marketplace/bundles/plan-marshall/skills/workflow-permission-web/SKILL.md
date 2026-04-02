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
- Each workflow step that invokes a script has an explicit bash code block with the full `python3 .plan/execute-script.py` command
- Always research unknown domains before categorizing them
- Prefer project-local permissions over global when appropriate
- All user interactions use `AskUserQuestion` tool with proper YAML structure
- Track all statistics (domains_analyzed, permissions_added/removed, security_checks, files_read/modified) throughout workflow

## Parameters

**scope** - Which settings to analyze (global/local/both, default: both). Controls which `--global-file` and `--local-file` arguments are passed to the `analyze` script:
   - `global` → pass only `--global-file`
   - `local` → pass only `--local-file`
   - `both` → pass both `--global-file` and `--local-file`
   - **Validation**: Must be one of: global, local, both
   - **Error**: If invalid: "Invalid scope '{value}'. Must be: global, local, or both" and retry

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

```
WebFetch Permission Analysis
========================================

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
========================================

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

## Statistics Tracking

> **Design note:** These counters are tracked by the LLM at workflow level because the scripts are stateless per-invocation. Each script reports its own counts in TOON output — the LLM sums them across steps.

The following counters must be maintained by the LLM during workflow execution:

- `domains_analyzed`: Total unique domains discovered and analyzed (from `analyze` output)
- `permissions_added`: Sum of `added` counts from `apply` calls
- `permissions_removed`: Sum of `removed` counts from `apply` calls
- `security_checks_performed`: Count of unknown domains researched via WebSearch
- `files_read`: Count of settings files successfully read (from `analyze` output)
- `files_modified`: Count of settings files successfully updated (from `apply` calls)

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

## Rule Configuration

Domain categorization is data-driven — loaded from `standards/domain-lists.json` (the source of truth for scripts). The companion `standards/trusted-domains.md` provides human-readable documentation and must be kept in sync manually when domains are added or removed.

- **major_domains**: Fully trusted documentation and tool domains
- **high_reach_domains**: Developer platforms commonly needed across projects
- **red_flag_patterns**: Regex patterns that flag suspicious domains

To add or update domain categorization, edit `standards/domain-lists.json` instead of the script.

## Critical Rules

**Security:**
- Always research unknown domains before approval
- Flag suspicious domains for review
- Check against red flags from standards

**Consolidation:**
- If domain:* exists, remove all specific domains
- Move major/high-reach domains to global
- Keep project-specific domains in local
- Remove duplicates

**User Control:**
- Never auto-remove without user approval
- Provide clear rationale for recommendations
- Allow review mode for granular control

## Related

| Skill | Purpose |
|-------|---------|
| `plan-marshall:marshall-steward` | Permission management wizard |
| `plan-marshall:tools-permission-doctor` | Permission analysis |
| `plan-marshall:tools-permission-fix` | Permission fixes |
