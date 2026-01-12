# Metadata Quality Standards

Standards for plugin.json schema validation, component inventory, and bundle structure compliance.

## Overview

Metadata files (plugin.json) define marketplace bundles and their components (agents, commands, skills). Proper metadata ensures components are discoverable and correctly configured.

**Key File**: `plugin.json` in bundle root directory

**Location**: `marketplace/bundles/{bundle-name}/plugin.json`

## plugin.json Schema

### Required Structure

```json
{
  "name": "bundle-name",
  "version": "1.0.0",
  "description": "Brief description of bundle purpose",
  "agents": [
    {
      "name": "agent-name",
      "description": "Agent description",
      "path": "agents/agent-name.md"
    }
  ],
  "commands": [
    {
      "name": "command-name",
      "description": "Command description",
      "path": "commands/command-name.md"
    }
  ],
  "skills": [
    {
      "name": "skill-name",
      "description": "Skill description",
      "path": "skills/skill-name"
    }
  ]
}
```

### Required Fields

**Bundle Level**:
- `name` (string): Bundle identifier (kebab-case, matches directory name)
- `version` (string): Semantic version (e.g., "1.0.0", "2.1.3")
- `description` (string): Brief bundle purpose (1-2 sentences)

**Component Level** (agents, commands, skills arrays):
- `name` (string): Component identifier (kebab-case)
- `description` (string): Component purpose (1 sentence)
- `path` (string): Relative path from bundle root to component

### Optional Fields

**Bundle Level**:
- `author` (string): Bundle author
- `license` (string): License identifier (e.g., "MIT", "Apache-2.0")
- `repository` (string): Git repository URL

### Validation Rules

**Name Format**:
- ✅ kebab-case: "my-bundle-name"
- ❌ camelCase: "myBundleName"
- ❌ snake_case: "my_bundle_name"
- ❌ spaces: "my bundle name"

**Version Format** (Semantic Versioning):
- ✅ "1.0.0", "2.1.3", "0.5.0"
- ❌ "1.0", "v1.0.0", "1.0.0-beta"

**Path Format**:
- ✅ Relative from bundle root: "agents/agent.md"
- ❌ Absolute: "/Users/..."
- ❌ Traversing: "../../agents/agent.md"
- ✅ Skills: directory path without .md: "skills/skill-name"

**JSON Syntax**:
- Valid JSON (proper quotes, commas, brackets)
- No trailing commas
- Proper escaping of special characters

## Component Inventory Validation

**Purpose**: Ensure plugin.json matches actual files in bundle.

### Discovery Process

**Scan bundle directory**:
```bash
# Find all agents
Glob: pattern="agents/*.md", path="{bundle_dir}"

# Find all commands
Glob: pattern="commands/*.md", path="{bundle_dir}"

# Find all skills
Glob: pattern="skills/*/", path="{bundle_dir}"
```

### Validation Checks

**1. Missing Entries** (files exist but not in plugin.json):
```
# Files found:
agents/agent-a.md ✅ (in plugin.json)
agents/agent-b.md ❌ (NOT in plugin.json)

# Fix: Add agent-b to plugin.json agents array
```

**2. Extra Entries** (in plugin.json but files don't exist):
```
# plugin.json lists:
agents/agent-a.md ✅ (file exists)
agents/agent-c.md ❌ (file NOT found)

# Fix: Remove agent-c from plugin.json or create the file
```

**3. Path Mismatches** (path in plugin.json doesn't match actual):
```
# plugin.json:
"path": "agents/my-agent.md"

# Actual file:
agents/my_agent.md  ❌ (name mismatch: hyphen vs underscore)

# Fix: Update plugin.json path or rename file
```

### Inventory Report Format

```
Component Inventory Validation

Bundle: {bundle-name}

Agents:
- Found: {count} files
- Declared: {count} entries
- Missing: {count} (files without entries)
- Extra: {count} (entries without files)
- Mismatches: {count} (path mismatches)

Commands:
[Same structure]

Skills:
[Same structure]

Issues:
- agents/new-agent.md not in plugin.json (missing entry)
- commands/old-command.md in plugin.json but file not found (extra entry)
- skills/my-skill path mismatch: declared "skills/my_skill", actual "skills/my-skill"
```

## Bundle Structure Requirements

### Standard Directory Layout

```
bundle-name/
├── plugin.json           (Required: bundle metadata)
├── README.md             (Optional: bundle documentation)
├── agents/               (Optional: agent definitions)
│   ├── agent-1.md
│   └── agent-2.md
├── commands/             (Optional: command definitions)
│   ├── command-1.md
│   └── command-2.md
└── skills/               (Optional: skill directories)
    ├── skill-1/
    │   ├── SKILL.md
    │   ├── scripts/
    │   └── references/
    └── skill-2/
        └── SKILL.md
```

### Naming Conventions

**Bundle Name**:
- Matches directory name
- Matches plugin.json "name" field
- kebab-case format

**Component Names**:
- Agents: filename without .md matches plugin.json name
- Commands: filename without .md matches plugin.json name
- Skills: directory name matches plugin.json name

**Examples**:
```
# ✅ Correct
Directory: marketplace/bundles/pm-dev-java/
plugin.json: {"name": "pm-dev-java"}

agents/diagnose-code.md
plugin.json: {"name": "diagnose-code", "path": "agents/diagnose-code.md"}

skills/cui-java-core/SKILL.md
plugin.json: {"name": "cui-java-core", "path": "skills/cui-java-core"}

# ❌ Incorrect
Directory: marketplace/bundles/cui_java_expert/  (underscore)
plugin.json: {"name": "pm-dev-java"}  (mismatch)
```

### Required Files

**Minimum**:
- `plugin.json` (MUST exist)
- At least one component (agent, command, or skill)

**Recommended**:
- `README.md` (bundle overview and usage)
- Component documentation (purpose, usage, examples)

## Validation Workflow

### Step 1: Schema Validation

```markdown
### Validate JSON Schema

Read {bundle_dir}/plugin.json

Check:
- ✅ Valid JSON syntax
- ✅ Required fields present (name, version, description)
- ✅ Field types correct (strings, arrays, objects)
- ✅ Name format valid (kebab-case)
- ✅ Version format valid (semantic versioning)
- ✅ Arrays present for agents, commands, skills
```

### Step 2: Component Inventory

```markdown
### Scan Bundle Directory

Glob: pattern="agents/*.md", path="{bundle_dir}"
Glob: pattern="commands/*.md", path="{bundle_dir}"
Glob: pattern="skills/*/", path="{bundle_dir}"

### Compare to plugin.json

For each component found:
  Check if entry exists in plugin.json
  If not: Report as "missing entry"

For each entry in plugin.json:
  Check if file exists
  If not: Report as "extra entry"

  Check if path matches
  If not: Report as "path mismatch"
```

### Step 3: Structure Validation

```markdown
### Verify Bundle Structure

Check:
- ✅ plugin.json exists
- ✅ Bundle name matches directory
- ✅ Component directories follow naming conventions
- ✅ At least one component exists
```

## Safe vs Risky Fixes

### Safe Fixes (Auto-Apply)

**1. Missing Entries**:
```json
// Add missing component to plugin.json
{
  "agents": [
    // ... existing agents
    {
      "name": "new-agent",
      "description": "TODO: Add description",
      "path": "agents/new-agent.md"
    }
  ]
}
```

**2. Path Corrections**:
```json
// Update path to match actual file
{
  "name": "my-agent",
  "path": "agents/my-agent.md"  // was "agents/my_agent.md"
}
```

**3. Missing Required Fields**:
```json
// Add missing description
{
  "name": "bundle-name",
  "version": "1.0.0",
  "description": "TODO: Add description"  // added
}
```

### Risky Fixes (Always Prompt)

**1. Extra Entries** (file doesn't exist):
- **Option A**: Remove entry from plugin.json
- **Option B**: Create missing file

**2. Version Conflicts**:
- Requires semantic versioning decision
- May affect dependencies

**3. Name Mismatches** (bundle name vs directory):
- Rename directory? (breaks references)
- Update plugin.json? (breaks installations)

## Common Issues and Fixes

### Issue 1: Invalid JSON Syntax

**Symptoms**:
- plugin.json fails to parse
- JSON validation errors

**Examples**:
```json
// ❌ Trailing comma
{
  "name": "bundle",
  "version": "1.0.0",  // trailing comma before }
}

// ❌ Missing quote
{
  name: "bundle",  // key not quoted
  "version": "1.0.0"
}

// ❌ Single quotes
{
  'name': 'bundle',  // must use double quotes
  'version': '1.0.0'
}
```

**Fix**:
```json
// ✅ Correct
{
  "name": "bundle",
  "version": "1.0.0"
}
```

### Issue 2: Missing Component Entries

**Symptoms**:
- Component files exist but not discoverable
- Marketplace doesn't show all components

**Diagnosis**:
```bash
# Find components not in plugin.json
Glob: pattern="agents/*.md", path="{bundle_dir}"
# Compare to plugin.json agents array
```

**Fix**:
Add missing entries to plugin.json.

### Issue 3: Path Mismatches

**Symptoms**:
- Components fail to load
- Broken references in marketplace

**Examples**:
```json
// plugin.json declares:
"path": "agents/my-agent.md"

// But actual file is:
agents/my_agent.md  (underscore instead of hyphen)
```

**Fix**:
- **Option 1**: Update plugin.json path to match file
- **Option 2**: Rename file to match plugin.json

### Issue 4: Invalid Version Format

**Symptoms**:
- Version doesn't follow semantic versioning
- Marketplace can't parse version

**Examples**:
```json
// ❌ Invalid
"version": "1.0"      // must be X.Y.Z
"version": "v1.0.0"   // no 'v' prefix
"version": "1"        // incomplete

// ✅ Valid
"version": "1.0.0"
"version": "2.1.3"
"version": "0.5.0"
```

**Fix**:
Update to semantic versioning format (MAJOR.MINOR.PATCH).

## Metadata Quality Checklist

**Before marking bundle metadata as "quality approved"**:
- ✅ plugin.json exists and is valid JSON
- ✅ Required fields present (name, version, description)
- ✅ Name matches bundle directory (kebab-case)
- ✅ Version follows semantic versioning (X.Y.Z)
- ✅ All component files have entries in plugin.json
- ✅ No extra entries (entries without files)
- ✅ All paths correct (match actual files)
- ✅ Bundle structure follows conventions
- ✅ Component names follow kebab-case
- ✅ At least one component (agent, command, or skill)

## Automated Validation Script

**Usage**:
```bash
Bash: scripts/scan-marketplace-inventory.sh {bundle_dir}
```

**Output**:
```json
{
  "bundle_name": "pm-dev-java",
  "plugin_json_path": "marketplace/bundles/pm-dev-java/plugin.json",
  "validation": {
    "schema_valid": true,
    "required_fields_present": true,
    "version_format_valid": true
  },
  "inventory": {
    "agents": {
      "found": 5,
      "declared": 4,
      "missing_entries": ["agent-new"],
      "extra_entries": [],
      "path_mismatches": []
    },
    "commands": {
      "found": 3,
      "declared": 3,
      "missing_entries": [],
      "extra_entries": [],
      "path_mismatches": []
    },
    "skills": {
      "found": 2,
      "declared": 2,
      "missing_entries": [],
      "extra_entries": [],
      "path_mismatches": []
    }
  }
}
```

Parse JSON output and categorize issues for fixing.
