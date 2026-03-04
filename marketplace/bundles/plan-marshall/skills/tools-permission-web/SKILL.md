---
name: tools-permission-web
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

**scope** - Which settings to analyze (global/local/both, default: both)
   - **Validation**: Must be one of: global, local, both
   - **Error**: If invalid: "Invalid scope '{value}'. Must be: global, local, or both" and retry

## Usage Examples

```
/tools-permission-web           # Analyze all settings
/tools-permission-web scope=global
/tools-permission-web scope=local
```

## Workflow

### Step 1: Load Web Security Standards

Read: standards/trusted-domains.md
Read: standards/domain-security-assessment.md

Loads trusted domains, security assessment patterns, and research methodology.

### Step 2: Collect All WebFetch Permissions

**A. Read global settings** (`~/.claude/settings.json`)
   - **Error handling**: If Read fails (file not found):
     - Display: "Global settings not found: ~/.claude/settings.json"
     - Present using `AskUserQuestion`:
       ```
       AskUserQuestion:
         questions:
           - question: "Global settings file not found. How would you like to proceed?"
             header: "Global"
             options:
               - label: "Create default settings"
                 description: "Create a new ~/.claude/settings.json with defaults"
               - label: "Skip global analysis"
                 description: "Continue with local settings only"
               - label: "Abort"
                 description: "Cancel permission analysis"
             multiSelect: false
       ```
     - Track in files_read counter

**B. Read local settings** (`./.claude/settings.local.json`)
   - **Error handling**: If Read fails (file not found):
     - Display: "Local settings not found: ./.claude/settings.local.json"
     - Present using `AskUserQuestion`:
       ```
       AskUserQuestion:
         questions:
           - question: "Local settings file not found. How would you like to proceed?"
             header: "Local"
             options:
               - label: "Create default settings"
                 description: "Create a new .claude/settings.local.json with defaults"
               - label: "Skip local analysis"
                 description: "Continue with global settings only"
               - label: "Abort"
                 description: "Cancel permission analysis"
             multiSelect: false
       ```
     - Track in files_read counter

**C. Extract all WebFetch permissions** from both sources
   - **Error handling**: If JSON parsing fails:
     - Display: "Invalid JSON in {file}: {error}"
     - Present using `AskUserQuestion`:
       ```
       AskUserQuestion:
         questions:
           - question: "Settings file has invalid JSON. How would you like to proceed?"
             header: "JSON"
             options:
               - label: "Fix manually"
                 description: "Open the file and fix JSON syntax"
               - label: "Skip this file"
                 description: "Continue without this settings file"
               - label: "Abort"
                 description: "Cancel permission analysis"
             multiSelect: false
       ```

**D. Categorize domains**:
- Universal (domain:*)
- Major domains (from trusted-domains standards)
- High-reach domains (github.com, stackoverflow.com, etc.)
- Project-specific domains
- Unknown domains (need research)

### Step 3: Detect Duplicate and Redundant Permissions

**A. Check for domain:*** - If present globally, all specific domains are redundant

**B. Find exact duplicates** across global and local

**C. Identify redundant patterns**:
- Subdomain when parent domain approved
- Multiple entries for same domain

### Step 4: Research Unknown Domains

For each unknown domain:

**A. Web research** using WebSearch or WebFetch:
```
WebSearch: "domain-name.com reputation security"
WebFetch: https://domain-name.com (check if accessible)
```

**B. Assess security** using standards from web-permissions skill:
- Check against red flags
- Evaluate purpose and trustworthiness
- Categorize risk level (LOW/MEDIUM/HIGH)

**C. Determine categorization**:
- MAJOR_DOMAINS - Documentation, official sites
- HIGH_REACH - Popular developer resources
- PROJECT_SPECIFIC - Project dependencies
- SUSPICIOUS - Security concerns
- UNKNOWN - Unable to assess

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

Present options using `AskUserQuestion`:

```
AskUserQuestion:
  questions:
    - question: "How would you like to apply the recommendations?"
      header: "Apply"
      options:
        - label: "Apply all"
          description: "Apply all recommended permission changes"
        - label: "Review each change"
          description: "Review and approve each change individually"
        - label: "Skip"
          description: "Display recommendations only, make no changes"
      multiSelect: false
```

If "Apply all" or "Review each change":
- Update global settings (track in permissions_added and permissions_removed counters)
- Update local settings (track in permissions_added and permissions_removed counters)
- Remove duplicates and redundant permissions
- Consolidate domains per recommendations

**Error handling:**
- **If Write fails**: Display "Failed to update {file}: {error}" and present using `AskUserQuestion`:
  ```
  AskUserQuestion:
    questions:
      - question: "Failed to write settings file. How would you like to proceed?"
        header: "Write"
        options:
          - label: "Retry"
            description: "Attempt the write again"
          - label: "Skip file"
            description: "Skip this file, continue with others"
          - label: "Abort"
            description: "Stop applying changes"
        multiSelect: false
  ```
- **If Edit fails**: Display "Failed to edit {file}: {error}" and present using `AskUserQuestion`:
  ```
  AskUserQuestion:
    questions:
      - question: "Failed to edit settings file. How would you like to proceed?"
        header: "Edit"
        options:
          - label: "Retry"
            description: "Attempt the edit again"
          - label: "Skip change"
            description: "Skip this change, continue with others"
          - label: "Abort"
            description: "Stop applying changes"
        multiSelect: false
  ```
- Track all successful updates in files_modified counter

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

Track throughout workflow:
- `domains_analyzed`: Total unique domains discovered and analyzed
- `permissions_added`: Count of new permissions added to settings
- `permissions_removed`: Count of redundant/duplicate permissions removed
- `security_checks_performed`: Count of unknown domains researched
- `files_read`: Count of settings files successfully read
- `files_modified`: Count of settings files successfully updated

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

- `/marshall-steward` - Permission management wizard
- `plan-marshall:tools-permission-doctor` skill - Permission analysis
- `plan-marshall:tools-permission-fix` skill - Permission fixes
