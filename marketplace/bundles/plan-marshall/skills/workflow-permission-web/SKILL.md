---
name: workflow-permission-web
description: Analyze and consolidate WebFetch domain permissions across projects with security research and validation
user-invocable: true
mode: workflow
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
| `scope` | string | no | both | Which settings to analyze: `global`, `project`, or `both`. Passed as `--scope` to the platform-routed web-permission ops; the runtime resolves the active platform's settings location. |

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

### Step 1: Load Trusted Domain Reference

Read: standards/trusted-domains.md

Loads trusted domain lists and categorization criteria. The security assessment methodology (`standards/domain-security-assessment.md`) is loaded on-demand in Step 4 only when unknown domains require research.

### Step 2: Collect and Analyze WebFetch Permissions

Run the platform-routed web-permission audit. The runtime resolves the active platform's settings, extracts the WebFetch domains, and reports them by scope — no settings path is named in the body:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime permission web-analyze \
    --scope both
```

The runtime handles missing settings gracefully. On a platform with no validated permission backend (e.g. OpenCode), it returns an honest `no-op` with a `reason` and `alternative` instead of a fabricated domain set.

Feed the returned domain list into the categorization, duplicate, and redundancy analysis below (the `categorize` subcommand classifies a domain list against the static known-domain lists without naming any settings file).

**Error handling for missing/invalid files**: Ask the user via `AskUserQuestion` with options to create defaults, skip the file, or abort.

The script categorizes domains into: universal (`*`), major (from `standards/domain-lists.json`), high_reach (github.com, stackoverflow.com, etc.), suspicious (red flag patterns), and unknown (need research).

### Step 3: Detect Duplicate and Redundant Permissions

The analysis script output includes `duplicates` (domains in both global and local) and `redundant` (wildcard-covered or subdomain-covered domains). Review these in the script output.

### Step 4: Research Unknown Domains

> **Prerequisite:** This step requires `WebSearch` tool access. If unavailable, skip research and present unknown domains to the user for manual assessment.

Read: standards/domain-security-assessment.md

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

If applying, route the change through the platform-neutral web-apply op. The runtime targets the active platform's settings for the given `--scope`; the body names no settings file:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime permission web-apply \
    --scope global \
    --add '["docs.oracle.com"]' \
    --remove '["redundant-domain.com"]'
```

Repeat with `--scope project` for project-local domains if needed. Track counts from the runtime output in permissions_added and permissions_removed counters. On a platform with no validated permission backend, the op returns an honest `no-op` (reason + alternative) rather than reporting a write that did not happen.

**Error handling:** If the op returns failure, ask the user (retry, skip scope, abort). Track all successful updates in files_modified counter.

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

Script: `plan-marshall:workflow-permission-web` → `permission_web.py`. Invocation surfaces are declared under Canonical invocations.

| Command | Behaviour |
|---------|-----------|
| `analyze` | Reads global and local settings, extracts WebFetch domains, categorizes them, detects duplicates and redundancy, and generates consolidation recommendations. Missing files are reported but do not cause failure. |
| `categorize` | Categorizes a list of domains into universal, major, high_reach, suspicious, unknown. Also checks for red flag patterns in domain names. |
| `apply` | Applies domain changes to a settings file deterministically. At least one of `--add`/`--remove` is required; the script modifies only `permissions.allow` WebFetch entries and writes back with `indent=2` formatting. |

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

## Canonical invocations

The canonical argparse surface for `permission_web.py`. The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### analyze

```bash
python3 .plan/execute-script.py plan-marshall:workflow-permission-web:permission_web analyze \
  [--global-file GLOBAL_FILE] [--local-file LOCAL_FILE]
```

### categorize

```bash
python3 .plan/execute-script.py plan-marshall:workflow-permission-web:permission_web categorize \
  --domains DOMAINS
```

### apply

```bash
python3 .plan/execute-script.py plan-marshall:workflow-permission-web:permission_web apply \
  --file FILE [--add ADD] [--remove REMOVE]
```

## Related

See `ref-workflow-architecture` → "Workflow Skill Orchestration" for the full dependency graph and shared infrastructure documentation. Related skills: `plan-marshall:marshall-steward` (permission management wizard), `plan-marshall:tools-permission-doctor` (permission analysis), `plan-marshall:tools-permission-fix` (permission fixes).
