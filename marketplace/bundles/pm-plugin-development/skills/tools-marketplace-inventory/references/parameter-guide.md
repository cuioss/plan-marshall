# Marketplace Inventory Script Parameters

Detailed parameter documentation for `scan-marketplace-inventory.py`.

## --scope (optional)

Directory scope to scan. Default: `auto`

| Value | Description |
|-------|-------------|
| `auto` | **Default**. Tries `marketplace/bundles/` first, falls back to `plugin-cache` |
| `marketplace` | Explicit: scans marketplace/bundles/ directory only |
| `plugin-cache` | Explicit: scans ~/.claude/plugins/cache/plan-marshall/ only |
| `global` | Scans ~/.claude directory |
| `project` | Scans .claude directory in current working directory |

The `auto` default makes the script work in both the marketplace repo and other projects without specifying a scope.

**Example**:
```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory --scope marketplace
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory --scope project
```

## --resource-types (optional)

Filter which resource types to include in the inventory. Default: `all`

| Value | Description |
|-------|-------------|
| `all` | Include all resource types (default) |
| `agents` | Include only agents |
| `commands` | Include only commands |
| `skills` | Include only skills |
| `scripts` | Include only scripts |

Multiple types can be combined with commas:
```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory --resource-types agents,skills
```

## --include-descriptions (optional flag)

When specified, extracts description fields from YAML frontmatter of each resource file. Requires `--format json` to see structured output.

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --include-descriptions --format json
```

## --full (optional flag)

When specified, includes full details: frontmatter fields and skill subdirectory contents with nested file listings.

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --full --bundles plan-marshall
```

**Output with --full** (excerpt):
```toon
plan-marshall:
  path: marketplace/bundles/plan-marshall

  skills[18]:
    - name: tools-permission-doctor
      path: marketplace/bundles/plan-marshall/skills/tools-permission-doctor
      description: Diagnose permission issues across settings files
      user_invocable: true
      allowed_tools: Read, Grep, Bash
      standards[2]:
        - permission-syntax.md
        - security-patterns.md
      scripts[1]:
        - permission-doctor.py
```

**Full mode includes:**
- Skill frontmatter: `user_invocable`, `allowed_tools`, `model`
- Skill subdirectories with their files: `standards/`, `templates/`, `scripts/`, `references/`, `knowledge/`, `examples/`, `documents/`

## --name-pattern (optional)

Filter resources by name using fnmatch glob patterns. Use pipe (`|`) to separate multiple patterns.

| Pattern | Matches |
|---------|---------|
| `*-plan-*` | Names containing "-plan-" |
| `plan-*` | Names starting with "plan-" |
| `*-agent` | Names ending with "-agent" |

```bash
# Single pattern
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory --name-pattern "*-plan-*"

# Multiple patterns (pipe-separated)
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory --name-pattern "*-plan-*|*-specify-*|plan-*|manage-*"
```

## --content-pattern (optional)

Filter resources by content using regex patterns. Use pipe (`|`) to separate multiple patterns (OR logic). **Requires `--include-descriptions` or `--full`** to enable path resolution.

Uses Python `re.search()` with `re.MULTILINE` flag. Scripts (.py, .sh) are NOT content-filtered.

```bash
# Find files with JSON code blocks
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --resource-types agents,skills \
  --content-pattern '```json' \
  --include-descriptions \
  --direct-result

# Multiple patterns (OR logic)
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --resource-types skills \
  --content-pattern '```json|```toon' \
  --full \
  --direct-result
```

**Output with content filtering** includes filter stats:
```toon
status: success
scope: marketplace
content_pattern: "```json"
content_filter_stats:
  input_count: 188
  matched_count: 32
  excluded_count: 156
```

## --content-exclude (optional)

Exclude resources matching content patterns (OR logic). Use pipe (`|`) to separate multiple patterns. **Requires `--include-descriptions` or `--full`**.

```bash
# Find JSON blocks but exclude already-migrated files
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --resource-types agents \
  --content-pattern '```json' \
  --content-exclude 'format: toon|output-format: toon' \
  --include-descriptions \
  --direct-result
```

### Combining --content-pattern and --content-exclude

When both are specified:
1. **Include filter**: File must match at least one include pattern
2. **Exclude filter**: File must NOT match any exclude pattern

```bash
# Find files with JSON but not configuration JSON
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --bundles pm-dev-java,pm-plugin-development \
  --resource-types agents \
  --content-pattern '```json' \
  --content-exclude '## Configuration.*```json' \
  --full \
  --direct-result
```

## --bundles (optional)

Filter to specific bundles by name (comma-separated).

```bash
# Single bundle
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory --bundles planning

# Multiple bundles
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory --bundles "planning,pm-dev-java,pm-dev-frontend"
```

## --direct-result (optional flag)

Output full TOON directly to stdout instead of writing to file.

| Mode | Behavior |
|------|----------|
| Default (no flag) | Writes to `.plan/temp/tools-marketplace-inventory/inventory-{timestamp}.toon`, prints summary |
| `--direct-result` | Outputs full TOON inventory directly to stdout |

**When to use `--direct-result`**:
- Small inventories (filtered bundles/patterns)
- Piped usage where file I/O is not desired
- Script-to-script calls where caller parses TOON directly

## --format (optional)

Output format. Default: `toon`

| Value | Description |
|-------|-------------|
| `toon` | TOON format with bundles as top-level keys (default) |
| `json` | JSON format with `bundles` as dict keyed by bundle name |

## --include-tests (optional flag)

When specified, includes test files from `test/{bundle-name}/` directories. Discovers `test_*.py` and `conftest.py` files.

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --include-tests --bundles pm-plugin-development --direct-result
```

## --include-project-skills (optional flag)

When specified, includes project-level skills from `.claude/skills/` directory. Creates a `project-skills` pseudo-bundle.

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --include-project-skills --direct-result
```

## Combining Flags

Both `--include-tests` and `--include-project-skills` can be used together:

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --include-tests \
  --include-project-skills \
  --full \
  --direct-result
```
