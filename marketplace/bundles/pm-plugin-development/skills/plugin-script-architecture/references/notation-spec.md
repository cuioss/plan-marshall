# Script Notation Specification

Portable notation format for referencing skill scripts across different installations.

## Format

```
bundle:skill/scripts/name.ext
```

### Components

| Component | Description | Example |
|-----------|-------------|---------|
| `bundle` | Bundle name (from plugin.json) | `pm-plugin-development` |
| `skill` | Skill directory name | `marketplace-inventory` |
| `scripts/` | Literal path segment (always `scripts/`) | `scripts/` |
| `name.ext` | Script filename with extension | `scan-marketplace-inventory.sh` |

### Valid Extensions

| Extension | Type | Execution |
|-----------|------|-----------|
| `.sh` | Bash script | `bash {path}` |
| `.py` | Python script | `python3 {path}` |

## Examples

### Bash Scripts

```
pm-documents:ref-documentation/scripts/asciidoc-validator.sh
pm-plugin-development:plugin-doctor/scripts/analyze-markdown-file.sh
```

### Python Scripts

```
pm-plugin-development:tools-marketplace-inventory/scripts/scan-marketplace-inventory.py
plan-marshall:permission-doctor/scripts/permission-doctor.py
pm-dev-java:java-core/scripts/analyze-logging-violations.py
pm-workflow:workflow-integration-github/scripts/fetch-pr-comments.py
```

## Resolution

The notation resolves to an absolute path based on the plugin's install location:

```
{install_path}/skills/{skill}/scripts/{name.ext}
```

Where `{install_path}` comes from `~/.claude/plugins/installed_plugins.json`.

### Example Resolution

Notation:
```
pm-plugin-development:tools-marketplace-inventory/scripts/scan-marketplace-inventory.py
```

Install path (from installed_plugins.json):
```
/Users/oliver/git/plan-marshall/marketplace/bundles/plan-marshall-core
```

Resolved absolute path:
```
/Users/oliver/git/plan-marshall/marketplace/bundles/plan-marshall-core/skills/tools-marketplace-inventory/scripts/scan-marketplace-inventory.py
```

## Validation Rules

1. **Bundle must exist**: Bundle name must match an installed plugin
2. **Skill must exist**: Skill directory must exist under `{install_path}/skills/`
3. **Script must exist**: Script file must exist in skill's `scripts/` directory
4. **Extension must be valid**: Only `.sh` and `.py` extensions are supported

## Error Cases

| Error | Cause | Resolution |
|-------|-------|------------|
| Bundle not found | Bundle not in installed_plugins.json | Install the plugin |
| Skill not found | Skill directory doesn't exist | Check skill name |
| Script not found | Script file doesn't exist | Check script name |
| Invalid extension | Extension not .sh or .py | Use supported extension |

## Permission Pattern

Each skill with scripts generates ONE permission wildcard per script type:

```
Bash(bash {install_path}/skills/{skill}/scripts/*.sh:*)
Bash(python3 {install_path}/skills/{skill}/scripts/*.py:*)
```

This allows all scripts in that skill to execute without individual permissions.
