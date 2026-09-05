# Marketplace Inventory Script Parameters

Detailed parameter documentation for `scan-marketplace-inventory.py`.

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes `scan-marketplace-inventory` — a `manage-*`-scoped convention leaves exactly those calls with no rule at all, which is the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The middle clause is what the `ci` family makes load-bearing: a `ci` verb reports failure as `status: error` at exit 0 **by design**, so a caller must branch on the payload `status` and never on the exit code. That rule is stated authoritatively in `plan-marshall:tools-integration-ci`; it is not restated here.

Step-level exceptions — calls whose non-zero exit is itself the signal — are documented inline in the step that issues them.

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
        - permission_doctor.py
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
